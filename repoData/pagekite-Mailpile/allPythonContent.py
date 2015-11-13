__FILENAME__ = app
import getopt
import gettext
import locale
import os
import sys
from gettext import gettext as _

import mailpile.util
import mailpile.defaults
from mailpile.commands import COMMANDS, Action, Help, HelpSplash, Load, Rescan
from mailpile.config import ConfigManager, getLocaleDirectory
from mailpile.ui import ANSIColors, Session, UserInteraction, Completer
from mailpile.util import *

# This makes sure mailbox "plugins" get loaded... has to go somewhere?
from mailpile.mailboxes import *

# This is also a bit silly, should be somewhere else?
Help.ABOUT = mailpile.defaults.ABOUT

# We may try to load readline later on... maybe?
readline = None


##[ Main ]####################################################################


def Interact(session):
    global readline
    try:
        import readline as rl  # Unix-only
        readline = rl
    except ImportError:
        pass

    try:
        if readline:
            readline.read_history_file(session.config.history_file())
            readline.set_completer_delims(Completer.DELIMS)
            readline.set_completer(Completer(session).get_completer())
            for opt in ["tab: complete", "set show-all-if-ambiguous on"]:
                readline.parse_and_bind(opt)
    except IOError:
        pass

    # Negative history means no saving state to disk.
    history_length = session.config.sys.history_length
    if readline is None:
        pass  # history currently not supported under Windows / Mac
    elif history_length >= 0:
        readline.set_history_length(history_length)
    else:
        readline.set_history_length(-history_length)

    try:
        prompt = session.ui.palette.color('mailpile> ',
                                          color=session.ui.palette.BLACK,
                                          weight=session.ui.palette.BOLD)
        while True:
            session.ui.block()
            opt = raw_input(prompt).decode('utf-8').strip()
            session.ui.unblock()
            if opt:
                if ' ' in opt:
                    opt, arg = opt.split(' ', 1)
                else:
                    arg = ''
                try:
                    session.ui.display_result(Action(session, opt, arg))
                except UsageError, e:
                    session.error(unicode(e))
                except UrlRedirectException, e:
                    session.error('Tried to redirect to: %s' % e.url)
    except EOFError:
        print

    try:
        if session.config.sys.history_length > 0:
            readline.write_history_file(session.config.history_file())
        else:
            os.remove(session.config.history_file())
    except OSError:
        pass


def Main(args):
    # Bootstrap translations until we've loaded everything else
    translation = gettext.translation("mailpile", getLocaleDirectory(),
                                      fallback=True)
    translation.install(unicode=True)

    try:
        # Create our global config manager and the default (CLI) session
        config = ConfigManager(rules=mailpile.defaults.CONFIG_RULES)
        session = Session(config)
        session.config.load(session)
        session.main = True
        session.ui = UserInteraction(config)
        if sys.stdout.isatty():
            session.ui.palette = ANSIColors()
    except AccessError, e:
        sys.stderr.write('Access denied: %s\n' % e)
        sys.exit(1)

    try:
        # Create and start (most) worker threads
        config.prepare_workers(session)

        try:
            shorta, longa = '', []
            for cls in COMMANDS:
                shortn, longn, urlpath, arglist = cls.SYNOPSIS[:4]
                if arglist:
                    if shortn:
                        shortn += ':'
                    if longn:
                        longn += '='
                if shortn:
                    shorta += shortn
                if longn:
                    longa.append(longn.replace(' ', '_'))

            opts, args = getopt.getopt(args, shorta, longa)
            for opt, arg in opts:
                Action(session, opt.replace('-', ''), arg.decode('utf-8'))
            if args:
                Action(session, args[0], ' '.join(args[1:]).decode('utf-8'))

        except (getopt.GetoptError, UsageError), e:
            session.error(e)

        if not opts and not args:
            # Create and start the rest of the threads, load the index.
            session.interactive = session.ui.interactive = True
            config.prepare_workers(session, daemons=True)
            Load(session, '').run(quiet=True)
            session.ui.display_result(HelpSplash(session, 'help', []).run())
            Interact(session)

    except KeyboardInterrupt:
        pass

    finally:
        mailpile.util.QUITTING = True
        config.stop_workers()
        if readline:
            readline.write_history_file(session.config.history_file())
        if config.index:
            config.index.save_changes()
        config.plugins.process_shutdown_hooks()

if __name__ == "__main__":
    Main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = commands
# These are the Mailpile commands, the public "API" we expose for searching,
# tagging and editing e-mail.
#
import copy
import datetime
import json
import os
import os.path
import re
import shlex
import traceback
import time
from gettext import gettext as _

import mailpile.util
import mailpile.ui
from mailpile.eventlog import Event
from mailpile.mailboxes import IsMailbox
from mailpile.mailutils import ExtractEmails, ExtractEmailAndName, Email
from mailpile.postinglist import GlobalPostingList
from mailpile.search import MailIndex
from mailpile.util import *
from mailpile.vcard import AddressInfo


class Command:
    """Generic command object all others inherit from"""
    SYNOPSIS = (None,     # CLI shortcode, e.g. A:
                None,     # CLI shortname, e.g. add
                None,     # API endpoint, e.g. sys/addmailbox
                None)     # Positional argument list
    SYNOPSIS_ARGS = None  # New-style positional argument list
    API_VERSION = None
    UI_CONTEXT = None

    FAILURE = 'Failed: %(name)s %(args)s'
    ORDER = (None, 0)
    SERIALIZE = False
    SPLIT_ARG = True  # Uses shlex by default
    RAISES = (UsageError, UrlRedirectException)

    # Event logging settings
    LOG_NOTHING = False
    LOG_PROGRESS = False
    LOG_STARTING = '%(name)s: Starting'
    LOG_FINISHED = '%(name)s: %(message)s'

    # HTTP settings (note: security!)
    HTTP_CALLABLE = ('GET', )
    HTTP_POST_VARS = {}
    HTTP_QUERY_VARS = {}
    HTTP_BANNED_VARS = {}
    HTTP_STRICT_VARS = True

    class CommandResult:
        def __init__(self, command_obj, session,
                     command_name, doc, result, status, message,
                     template_id=None, kwargs={}, error_info={}):
            self.session = session
            self.command_obj = command_obj
            self.command_name = command_name
            self.kwargs = {}
            self.kwargs.update(kwargs)
            self.template_id = template_id
            self.doc = doc
            self.result = result
            self.status = status
            self.error_info = {}
            self.error_info.update(error_info)
            self.message = message

        def __nonzero__(self):
            return (self.result and True or False)

        def as_text(self):
            if isinstance(self.result, bool):
                happy = '%s: %s' % (self.result and _('OK') or _('Failed'),
                                    self.message or self.doc)
                if not self.result and self.error_info:
                    return '%s\n%s' % (happy, json.dumps(self.error_info,
                                                         indent=4))
                else:
                    return happy
            elif isinstance(self.result, (dict, list, tuple)):
                return json.dumps(self.result, indent=4, sort_keys=True)
            else:
                return unicode(self.result)

        __str__ = lambda self: self.as_text()

        __unicode__ = lambda self: self.as_text()

        def as_dict(self):
            from mailpile.urlmap import UrlMap
            rv = {
                'command': self.command_name,
                'state': {
                    'command_url': UrlMap.ui_url(self.command_obj),
                    'context_url': UrlMap.context_url(self.command_obj),
                    'query_args': self.command_obj.state_as_query_args()
                },
                'status': self.status,
                'message': self.message,
                'result': self.result,
                'elapsed': '%.3f' % self.session.ui.time_elapsed,
            }
            if self.error_info:
                rv['error'] = self.error_info
            for ui_key in [k for k in self.kwargs.keys()
                           if k.startswith('ui_')]:
                rv[ui_key] = self.kwargs[ui_key]
            return rv

        def as_json(self):
            return self.session.ui.render_json(self.as_dict())

        def as_html(self, template=None):
            return self.as_template('html', template)

        def as_js(self, template=None):
            return self.as_template('js', template)

        def as_css(self, template=None):
            return self.as_template('css', template)

        def as_rss(self, template=None):
            return self.as_template('rss', template)

        def as_xml(self, template=None):
            return self.as_template('xml', template)

        def as_txt(self, template=None):
            return self.as_template('txt', template)

        def as_template(self, etype, template=None):
            tpath = self.command_obj.template_path(
                etype, template_id=self.template_id, template=template)

            data = self.as_dict()
            data['title'] = self.message
            data['render_mode'] = 'full'

            def render():
                return self.session.ui.render_web(
                    self.session.config, [tpath], data)

            for e in ('jhtml', 'jjs', 'jcss', 'jxml', 'jrss'):
                if self.session.ui.render_mode.endswith(e):
                    data['render_mode'] = 'content'
                    data['result'] = render()
                    return self.session.ui.render_json(data)

            return render()

    def __init__(self, session, name=None, arg=None, data=None):
        self.session = session
        self.serialize = self.SERIALIZE
        self.name = self.SYNOPSIS[1] or self.SYNOPSIS[2] or name
        self.data = data or {}
        self.status = 'unknown'
        self.message = name
        self.error_info = {}
        self.result = None
        if type(arg) in (type(list()), type(tuple())):
            self.args = tuple(arg)
        elif arg:
            if self.SPLIT_ARG is True:
                self.args = tuple(shlex.split(arg))
            else:
                self.args = (arg, )
        else:
            self.args = tuple([])
        if 'arg' in self.data:
            self.args = tuple(list(self.args) + self.data['arg'])
        self._create_event()

    def state_as_query_args(self):
        args = {}
        if self.args:
            args['arg'] = self.args
        args.update(self.data)
        return args

    def template_path(self, etype, template_id=None, template=None):
        path_parts = (template_id or self.SYNOPSIS[2] or 'command').split('/')
        if len(path_parts) == 1:
            path_parts.append('index')
        if template not in (None, etype, 'as.' + etype):
            # Security: The template request may come from the URL, so we
            #           sanitize it very aggressively before heading off
            #           to the filesystem.
            clean_tpl = CleanText(template.replace('.%s' % etype, ''),
                                  banned=(CleanText.FS +
                                          CleanText.WHITESPACE))
            path_parts[-1] += '-%s' % clean_tpl
        path_parts[-1] += '.' + etype
        return os.path.join(*path_parts)

    def _idx(self, reset=False, wait=True, wait_all=True, quiet=False):
        session, config = self.session, self.session.config
        if not reset and config.index:
            return config.index

        def __do_load2():
            config.vcards.load_vcards(session)
            if not wait_all:
                session.ui.report_marks(quiet=quiet)

        def __do_load1():
            if reset:
                config.index = None
                session.results = []
                session.searched = []
                session.displayed = {'start': 1, 'count': 0}
            idx = config.get_index(session)
            if wait_all:
                __do_load2()
            if not wait:
                session.ui.report_marks(quiet=quiet)
            return idx

        if wait:
            rv = config.slow_worker.do(session, 'Load', __do_load1)
            session.ui.reset_marks(quiet=quiet)
        else:
            config.slow_worker.add_task(session, 'Load', __do_load1)
            rv = None

        if not wait_all:
            config.slow_worker.add_task(session, 'Load2', __do_load2)

        return rv

    def _choose_messages(self, words, allow_ephemeral=False):
        msg_ids = set()
        all_words = []
        for word in words:
            all_words.extend(word.split(','))
        for what in all_words:
            if what.lower() == 'these':
                b = self.session.displayed['stats']['start'] - 1
                c = self.session.displayed['stats']['count']
                msg_ids |= set(self.session.results[b:b + c])
            elif what.lower() == 'all':
                msg_ids |= set(self.session.results)
            elif what.startswith('='):
                try:
                    msg_id = int(what[1:], 36)
                    if msg_id >= 0 and msg_id < len(self._idx().INDEX):
                        msg_ids.add(msg_id)
                    else:
                        self.session.ui.warning((_('No such ID: %s')
                                                 ) % (what[1:], ))
                except ValueError:
                    if allow_ephemeral and '-' in what:
                        msg_ids.add(what[1:])
                    else:
                        self.session.ui.warning(_('What message is %s?'
                                                  ) % (what, ))
            elif '-' in what:
                try:
                    b, e = what.split('-')
                    msg_ids |= set(self.session.results[int(b) - 1:int(e)])
                except:
                    self.session.ui.warning(_('What message is %s?'
                                              ) % (what, ))
            else:
                try:
                    msg_ids.add(self.session.results[int(what) - 1])
                except:
                    self.session.ui.warning(_('What message is %s?'
                                              ) % (what, ))
        return msg_ids

    def _error(self, message, info=None):
        self.status = 'error'
        self.message = message

        ui_message = _('%s error: %s') % (self.name, message)
        if info:
            self.error_info.update(info)
            details = ' '.join(['%s=%s' % (k, info[k]) for k in info])
            ui_message += ' (%s)' % details
        self.session.ui.mark(self.name)
        self.session.ui.error(ui_message)

        return False

    def _success(self, message, result=True):
        self.status = 'success'
        self.message = message

        ui_message = _('%s: %s') % (self.name, message)
        self.session.ui.mark(ui_message)

        return self.view(result)

    def _read_file_or_data(self, fn):
        if fn in self.data:
            return self.data[fn]
        else:
            return open(fn, 'rb').read()

    def _ignore_exception(self):
        self.session.ui.debug(traceback.format_exc())

    def _serialize(self, name, function):
        session, config = self.session, self.session.config
        return config.slow_worker.do(session, name, function)

    def _background(self, name, function):
        session, config = self.session, self.session.config
        return config.slow_worker.add_task(session, name, function)

    def _update_event_state(self, state, log=False):
        self.event.flags = state
        self.event.data['elapsed'] = int(1000 * (time.time()-self._start_time))

        if (log or self.LOG_PROGRESS) and not self.LOG_NOTHING:
            ui = str(self.session.ui.__class__).replace('mailpile.', '.')
            self.event.data['ui'] = ui
            self.event.data['output'] = self.session.ui.render_mode
            self.session.config.event_log.log_event(self.event)

    def _starting(self):
        self._start_time = time.time()
        self._update_event_state(Event.RUNNING)
        if self.name:
            self.session.ui.start_command(self.name, self.args, self.data)

    def _fmt_msg(self, message):
        return message % {'name': self.name,
                          'status': self.status or '',
                          'message': self.message or ''}

    def _create_event(self):
        private_data = {}
        if self.data:
            private_data['data'] = copy.copy(self.data)
        if self.args:
            private_data['args'] = copy.copy(self.args)

        self.event = Event(source=self,
                           message=self._fmt_msg(self.LOG_STARTING),
                           data={},
                           private_data=private_data)

    def _finishing(self, command, rv):
        # FIXME: Remove this when stuff is up to date
        if self.status == 'unknown':
            self.session.ui.warning('FIXME: %s should use self._success'
                                    ' etc. (issue #383)' % self.__class__)
            self.status = 'success'

        self.session.ui.mark(_('Generating result'))
        result = self.CommandResult(self, self.session, self.name,
                                    command.__doc__ or self.__doc__,
                                    rv, self.status, self.message,
                                    error_info=self.error_info)

        # Update the event!
        if self.message:
            self.event.message = self.message
        if self.error_info:
            self.event.private_data['error_info'] = self.error_info
        self.event.message = self._fmt_msg(self.LOG_FINISHED)
        self._update_event_state(Event.COMPLETE, log=True)

        self.session.ui.mark(self.event.message)
        self.session.ui.report_marks(
            details=('timing' in self.session.config.sys.debug))
        if self.name:
            self.session.ui.finish_command(self.name)
        return result

    def _run(self, *args, **kwargs):
        def command(self, *args, **kwargs):
            return self.command(*args, **kwargs)
        try:
            self._starting()
            return self._finishing(command, command(self, *args, **kwargs))
        except self.RAISES:
            raise
        except:
            self._ignore_exception()
            self._error(self.FAILURE % {'name': self.name,
                                        'args': ' '.join(self.args)})
            return self._finishing(command, False)

    def run(self, *args, **kwargs):
        if self.serialize:
            # Some functions we always run in the slow worker, to make sure
            # they don't get run in parallel with other things.
            return self._serialize(self.serialize,
                                   lambda: self._run(*args, **kwargs))
        else:
            return self._run(*args, **kwargs)

    def command(self):
        return None

    @classmethod
    def view(cls, result):
        return result


##[ Shared basic Search Result class]#########################################

class SearchResults(dict):

    _NAME_TITLES = ('the', 'mr', 'ms', 'mrs', 'sir', 'dr', 'lord')

    def _name(self, sender, short=True, full_email=False):
        words = re.sub('["<>]', '', sender).split()
        nomail = [w for w in words if not '@' in w]
        if nomail:
            if short:
                if len(nomail) > 1 and nomail[0].lower() in self._NAME_TITLES:
                    return nomail[1]
                return nomail[0]
            return ' '.join(nomail)
        elif words:
            if not full_email:
                return words[0].split('@', 1)[0]
            return words[0]
        return '(nobody)'

    def _names(self, senders):
        if len(senders) > 1:
            names = {}
            for sender in senders:
                sname = self._name(sender)
                names[sname] = names.get(sname, 0) + 1
            namelist = names.keys()
            namelist.sort(key=lambda n: -names[n])
            return ', '.join(namelist)
        if len(senders) < 1:
            return '(no sender)'
        if senders:
            return self._name(senders[0], short=False)
        return ''

    def _compact(self, namelist, maxlen):
        l = len(namelist)
        while l > maxlen:
            namelist = re.sub(', *[^, \.]+, *', ',,', namelist, 1)
            if l == len(namelist):
                break
            l = len(namelist)
        namelist = re.sub(',,,+, *', ' .. ', namelist, 1)
        return namelist

    TAG_TYPE_FLAG_MAP = {
        'trash': 'trash',
        'spam': 'spam',
        'ham': 'ham',
        'drafts': 'draft',
        'blank': 'draft',
        'sent': 'from_me',
        'outbox': 'from_me',
        'replied': 'replied',
        'fwded': 'forwarded'
    }

    def _metadata(self, msg_info):
        import mailpile.urlmap
        nz = lambda l: [v for v in l if v]
        msg_ts = long(msg_info[MailIndex.MSG_DATE], 36)
        msg_date = datetime.datetime.fromtimestamp(msg_ts)

        fe, fn = ExtractEmailAndName(msg_info[MailIndex.MSG_FROM])
        f_info = self._address(e=fe, n=fn)
        f_info['aid'] = (self._msg_addresses(msg_info, no_to=True, no_cc=True)
                         or [''])[0]
        expl = {
            'mid': msg_info[MailIndex.MSG_MID],
            'id': msg_info[MailIndex.MSG_ID],
            'timestamp': msg_ts,
            'from': f_info,
            'to_aids': self._msg_addresses(msg_info, no_from=True, no_cc=True),
            'cc_aids': self._msg_addresses(msg_info, no_from=True, no_to=True),
            'msg_kb': int(msg_info[MailIndex.MSG_KB], 36),
            'tag_tids': self._msg_tags(msg_info),
            'thread_mid': msg_info[MailIndex.MSG_THREAD_MID],
            'subject': msg_info[MailIndex.MSG_SUBJECT],
            'body': MailIndex.get_body(msg_info),
            'flags': {
            },
            'crypto': {
            }
        }

        # Ephemeral messages do not have URLs
        if '-' not in msg_info[MailIndex.MSG_MID]:
            expl['urls'] = {
                'thread': self.urlmap.url_thread(msg_info[MailIndex.MSG_MID]),
                'source': self.urlmap.url_source(msg_info[MailIndex.MSG_MID]),
            }
        else:
            expl['flags']['ephemeral'] = True

        # Support rich snippets
        if expl['body']['snippet'].startswith('{'):
            try:
                expl['body'] = json.loads(expl['body']['snippet'])
            except ValueError:
                pass

        # Misc flags
        if [e for e in self.idx.config.profiles if (e.email.lower()
                                                    == fe.lower())]:
            expl['flags']['from_me'] = True
        tag_types = [self.idx.config.get_tag(t).type for t in expl['tag_tids']]
        for t in self.TAG_TYPE_FLAG_MAP:
            if t in tag_types:
                expl['flags'][self.TAG_TYPE_FLAG_MAP[t]] = True

        # Check tags for signs of encryption or signatures
        tag_slugs = [self.idx.config.get_tag(t).slug for t in expl['tag_tids']]
        for t in tag_slugs:
            if t.startswith('mp_sig'):
                expl['crypto']['signature'] = t[7:]
            elif t.startswith('mp_enc'):
                expl['crypto']['encryption'] = t[7:]

        # Extra behavior for editable messages
        if 'draft' in expl['flags']:
            if self.idx.config.is_editable_message(msg_info):
                expl['urls']['editing'] = self.urlmap.url_edit(expl['mid'])
            else:
                del expl['flags']['draft']

        return expl

    def _msg_addresses(self, msg_info,
                       no_from=False, no_to=False, no_cc=False):
        if no_to:
            cids = set()
        else:
            to = [t for t in msg_info[MailIndex.MSG_TO].split(',') if t]
            cids = set(to)
        if not no_cc:
            cc = [t for t in msg_info[MailIndex.MSG_CC].split(',') if t]
            cids |= set(cc)
        if not no_from:
            fe, fn = ExtractEmailAndName(msg_info[MailIndex.MSG_FROM])
            if fe:
                try:
                    cids.add(b36(self.idx.EMAIL_IDS[fe.lower()]))
                except KeyError:
                    cids.add(b36(self.idx._add_email(fe, name=fn)))
        return sorted(list(cids))

    def _address(self, cid=None, e=None, n=None):
        if cid and not (e and n):
            e, n = ExtractEmailAndName(self.idx.EMAILS[int(cid, 36)])
        vcard = self.session.config.vcards.get_vcard(e)
        return AddressInfo(e, n, vcard=vcard)

    def _msg_tags(self, msg_info):
        tids = [t for t in msg_info[MailIndex.MSG_TAGS].split(',')
                if t and t in self.session.config.tags]
        return tids

    def _tag(self, tid, attributes={}):
        return dict_merge(self.session.config.get_tag_info(tid), attributes)

    def _thread(self, thread_mid):
        msg_info = self.idx.get_msg_at_idx_pos(int(thread_mid, 36))
        thread = [i for i in msg_info[MailIndex.MSG_REPLIES].split(',') if i]

        # FIXME: This is a hack, the indexer should just keep things
        #        in the right order on rescan. Fixing threading is a bigger
        #        problem though, so we do this for now.
        def thread_sort_key(idx):
            info = self.idx.get_msg_at_idx_pos(int(thread_mid, 36))
            return int(info[self.idx.MSG_DATE], 36)
        thread.sort(key=thread_sort_key)

        return thread

    WANT_MSG_TREE = ('attachments', 'html_parts', 'text_parts', 'header_list',
                     'editing_strings', 'crypto')
    PRUNE_MSG_TREE = ('headers', )  # Added by editing_strings

    def _prune_msg_tree(self, tree):
        for k in tree.keys():
            if k not in self.WANT_MSG_TREE or k in self.PRUNE_MSG_TREE:
                del tree[k]
        return tree

    def _message(self, email):
        tree = email.get_message_tree(want=(email.WANT_MSG_TREE_PGP +
                                            self.WANT_MSG_TREE))
        email.evaluate_pgp(tree, decrypt=True)
        return self._prune_msg_tree(tree)

    def __init__(self, session, idx,
                 results=None, start=0, end=None, num=None,
                 emails=None, people=None,
                 suppress_data=False, full_threads=True):
        dict.__init__(self)
        self.session = session
        self.people = people
        self.emails = emails
        self.idx = idx
        self.urlmap = mailpile.urlmap.UrlMap(self.session)

        results = self.results = results or session.results or []

        num = num or session.config.prefs.num_results
        if end:
            start = end - num
        if start > len(results):
            start = len(results)
        if start < 0:
            start = 0

        self.session.ui.mark(_('Parsing metadata for %d results '
                               '(full_threads=%s)') % (num, full_threads))

        try:
            threads = [b36(r) for r in results[start:start + num]]
        except TypeError:
            results = threads = []
            start = end = 0

        self.update({
            'summary': _('Search: %s') % ' '.join(session.searched),
            'stats': {
                'count': len(threads),
                'start': start + 1,
                'end': start + num,
                'total': len(results),
            },
            'search_terms': session.searched,
            'address_ids': [],
            'message_ids': [],
            'thread_ids': threads,
        })
        if 'tags' in self.session.config:
            search_tags = [idx.config.get_tag(t.split(':')[1], {})
                           for t in session.searched
                           if t.startswith('in:') or t.startswith('tag:')]
            search_tag_ids = [t._key for t in search_tags if t]
            self.update({
                'search_tag_ids': search_tag_ids,
            })
            if search_tag_ids:
                self['summary'] = ' & '.join([t.name for t
                                              in search_tags if t])
        else:
            search_tag_ids = []

        if suppress_data or (not results and not emails):
            return

        self.update({
            'data': {
                'addresses': {},
                'metadata': {},
                'messages': {},
                'threads': {}
            }
        })
        if 'tags' in self.session.config:
            th = self['data']['tags'] = {}
            for tid in search_tag_ids:
                if tid not in th:
                    th[tid] = self._tag(tid, {'searched': True})

        idxs = results[start:start + num]
        while idxs:
            idx_pos = idxs.pop(0)
            msg_info = idx.get_msg_at_idx_pos(idx_pos)
            self.add_msg_info(b36(idx_pos), msg_info,
                              full_threads=full_threads, idxs=idxs)

        if emails and len(emails) == 1:
            self['summary'] = emails[0].get_msg_info(MailIndex.MSG_SUBJECT)

        for e in emails or []:
            self.add_email(e)

    def add_msg_info(self, mid, msg_info, full_threads=False, idxs=None):
        # Populate data.metadata
        self['data']['metadata'][mid] = self._metadata(msg_info)

        # Populate data.thread
        thread_mid = msg_info[self.idx.MSG_THREAD_MID]
        if thread_mid not in self['data']['threads']:
            thread = self._thread(thread_mid)
            self['data']['threads'][thread_mid] = thread
            if full_threads and idxs:
                idxs.extend([int(t, 36) for t in thread
                             if t not in self['data']['metadata']])

        # Populate data.person
        for cid in self._msg_addresses(msg_info):
            if cid not in self['data']['addresses']:
                self['data']['addresses'][cid] = self._address(cid=cid)

        # Populate data.tag
        if 'tags' in self.session.config:
            for tid in self._msg_tags(msg_info):
                if tid not in self['data']['tags']:
                    self['data']['tags'][tid] = self._tag(tid,
                                                          {"searched": False})

    def add_email(self, e):
        if e not in self.emails:
            self.emails.append(e)
        mid = e.msg_mid()
        self.add_msg_info(mid, e.get_msg_info())
        if mid not in self['data']['messages']:
            self['data']['messages'][mid] = self._message(e)
        if mid not in self['message_ids']:
            self['message_ids'].append(mid)

    def __nonzero__(self):
        return True

    def next_set(self):
        stats = self['stats']
        return SearchResults(self.session, self.idx,
                             start=stats['start'] - 1 + stats['count'])

    def previous_set(self):
        stats = self['stats']
        return SearchResults(self.session, self.idx,
                             end=stats['start'] - 1)

    def as_text(self):
        from mailpile.jinjaextensions import MailpileCommand as JE
        clen = max(3, len('%d' % len(self.session.results)))
        cfmt = '%%%d.%ds' % (clen, clen)
        text = []
        count = self['stats']['start']
        expand_ids = [e.msg_idx_pos for e in (self.emails or [])]
        addresses = self.get('data', {}).get('addresses', {})
        for mid in self['thread_ids']:
            m = self['data']['metadata'][mid]
            tags = [self['data']['tags'][t] for t in m['tag_tids']]
            tag_names = [t['name'] for t in tags
                         if not t.get('searched', False)
                         and t.get('label', True)
                         and t.get('display', '') != 'invisible']
            tag_new = [t for t in tags if t.get('type') == 'unread']
            tag_names.sort()
            msg_meta = tag_names and ('  (' + '('.join(tag_names)) or ''

            # FIXME: this is a bit ugly, but useful for development
            es = ['', '']
            for t in [t['slug'] for t in tags]:
                if t.startswith('mp_enc') and 'none' not in t:
                    es[1] = 'E'
                if t.startswith('mp_sig') and 'none' not in t:
                    es[0] = 'S'
            es = ''.join([e for e in es if e])
            if es:
                msg_meta = (msg_meta or '  ') + ('[%s]' % es)
            elif msg_meta:
                msg_meta += ')'
            else:
                msg_meta += '  '
            msg_meta += elapsed_datetime(m['timestamp'])

            from_info = (m['from'].get('fn') or m['from'].get('email')
                         or '(anonymous)')
            if from_info[:1] in ('<', '"', '\''):
                from_info = from_info[1:]
                if from_info[-1:] in ('>', '"', '\''):
                    from_info = from_info[:-1]
            if '@' in from_info and len(from_info) > 18:
                e, d = from_info.split('@', 1)
                if d in ('gmail.com', 'yahoo.com', 'hotmail.com'):
                    from_info = '%s@%s..' % (e, d[0])
                else:
                    from_info = '%s..@%s' % (e[0], d)

            if not expand_ids:
                def gg(pos):
                    return (pos < 10) and pos or '>'
                thread = [m['thread_mid']]
                thread += self['data']['threads'][m['thread_mid']]
                if m['mid'] not in thread:
                    thread.append(m['mid'])
                pos = thread.index(m['mid']) + 1
                if pos > 1:
                    from_info = '%s>%s' % (gg(pos-1), from_info)
                else:
                    from_info = '  ' + from_info
                if pos < len(thread):
                    from_info = '%s>%s' % (from_info[:20], gg(len(thread)-pos))

            subject = re.sub('^(\\[[^\\]]{6})[^\\]]{3,}\\]\\s*', '\\1..] ',
                             JE._nice_subject(m['subject']))

            sfmt = '%%-%d.%ds%%s' % (53 - (clen + len(msg_meta)),
                                     53 - (clen + len(msg_meta)))
            text.append((cfmt + ' %-22.22s %s' + sfmt
                         ) % (count, from_info, tag_new and '*' or ' ',
                              subject, msg_meta))

            if mid in self['data'].get('messages', {}):
                exp_email = self.emails[expand_ids.index(int(mid, 36))]
                msg_tree = exp_email.get_message_tree()
                text.append('-' * 79)
                text.append(exp_email.get_editing_string(msg_tree).strip())
                if msg_tree['attachments']:
                    text.append('\nAttachments:')
                    for a in msg_tree['attachments']:
                        text.append('%5.5s %s' % ('#%s' % a['count'],
                                                  a['filename']))
                text.append('-' * 79)

            count += 1
        if not count:
            text = ['(No messages found)']
        return '\n'.join(text) + '\n'


##[ Internals ]###############################################################

class Load(Command):
    """Load or reload the metadata index"""
    SYNOPSIS = (None, 'load', None, None)
    ORDER = ('Internals', 1)

    def command(self, reset=True, wait=True, wait_all=False, quiet=False):
        if self._idx(reset=reset,
                     wait=wait,
                     wait_all=wait_all,
                     quiet=quiet):
            return self._success(_('Loaded metadata index'))
        else:
            return self._error(_('Failed to loaded metadata index'))


class Rescan(Command):
    """Add new messages to index"""
    SYNOPSIS = (None, 'rescan', None, '[full|vcards|mailboxes|sources|<msgs>]')
    ORDER = ('Internals', 2)
    SERIALIZE = 'Rescan'
    LOG_PROGRESS = True

    def command(self):
        session, config, idx = self.session, self.session.config, self._idx()
        args = list(self.args)

        if config.sys.lockdown:
            return self._error(_('In lockdown, doing nothing.'))

        delay = play_nice_with_threads()
        if delay > 0:
            session.ui.notify((
                _('Note: periodic delay is %ss, run from shell to '
                  'speed up: mp --rescan=...')
            ) % delay)

        if args and args[0].lower() == 'vcards':
            return self._success(_('Rescanned vcards'),
                                 result=self._rescan_vcards(session))
        elif args and args[0].lower() in ('mailboxes', 'sources'):
            which = args[0].lower()
            return self._success(_('Rescanned mailboxes'),
                                 result=self._rescan_mailboxes(session,
                                                               which=which))
        elif args and args[0].lower() == 'full':
            config.clear_mbox_cache()
            args.pop(0)

        msg_idxs = self._choose_messages(args)
        if msg_idxs:
            for msg_idx_pos in msg_idxs:
                e = Email(idx, msg_idx_pos)
                try:
                    session.ui.mark('Re-indexing %s' % e.msg_mid())
                    idx.index_email(self.session, e)
                except KeyboardInterrupt:
                    raise
                except:
                    self._ignore_exception()
                    session.ui.warning(_('Failed to reindex: %s'
                                         ) % e.msg_mid())
            return self._success(_('Indexed %d messages') % len(msg_idxs),
                                 result={'messages': len(msg_idxs)})

        else:
            # FIXME: Need a lock here?
            if 'rescan' in config._running:
                return self._success(_('Rescan already in progress'))
            config._running['rescan'] = True
            try:
                results = {}
                results.update(self._rescan_vcards(session))
                results.update(self._rescan_mailboxes(session))
                if 'aborted' in results:
                    raise KeyboardInterrupt()
                return self._success(_('Rescanned vcards and mailboxes'),
                                     result=results)
            except (KeyboardInterrupt), e:
                return self._error(_('User aborted'), info=results)
            finally:
                del config._running['rescan']

    def _rescan_vcards(self, session):
        from mailpile.plugins import PluginManager
        config = session.config
        imported = 0
        importer_cfgs = config.prefs.vcard.importers
        for importer in PluginManager.VCARD_IMPORTERS.values():
            for cfg in importer_cfgs.get(importer.SHORT_NAME, []):
                if cfg:
                    imp = importer(session, cfg)
                    imported += imp.import_vcards(session, config.vcards)
        return {'vcards': imported}

    def _rescan_mailboxes(self, session, which='both'):
        config = session.config
        idx = self._idx()
        msg_count = 0
        mbox_count = 0
        rv = True
        try:
            pre_command = config.prefs.rescan_command
            if pre_command:
                session.ui.mark(_('Running: %s') % pre_command)
                subprocess.check_call(pre_command, shell=True)
            msg_count = 1

            if which in ('both', 'sources'):
                for src in config.mail_sources.values():
                    if mailpile.util.QUITTING:
                        break
                    count = src.rescan_now(session)
                    if count > 0:
                        msg_count += count
                        mbox_count += 1
                    session.ui.mark('\n')

            if which in ('both', 'mailboxes'):
                for fid, fpath, sc in config.get_mailboxes(mail_sources=False):
                    if mailpile.util.QUITTING:
                        break
                    if fpath == '/dev/null':
                        continue
                    try:
                        count = idx.scan_mailbox(session, fid, fpath,
                                                 config.open_mailbox)
                    except ValueError:
                        count = -1
                    if count < 0:
                        session.ui.warning(_('Failed to rescan: %s') % fpath)
                    elif count > 0:
                        msg_count += count
                        mbox_count += 1
                    session.ui.mark('\n')

            msg_count -= 1
            if msg_count:
                if not mailpile.util.QUITTING:
                    idx.cache_sort_orders(session)
                if not mailpile.util.QUITTING:
                    GlobalPostingList.Optimize(session, idx, quick=True)
            else:
                session.ui.mark(_('Nothing changed'))
        except (KeyboardInterrupt, subprocess.CalledProcessError), e:
            return {'aborted': True,
                    'messages': msg_count,
                    'mailboxes': mbox_count}
        finally:
            if msg_count:
                session.ui.mark('\n')
                if msg_count < 500:
                    idx.save_changes(session)
                else:
                    idx.save(session)
        return {'messages': msg_count,
                'mailboxes': mbox_count}


class Optimize(Command):
    """Optimize the keyword search index"""
    SYNOPSIS = (None, 'optimize', None, '[harder]')
    ORDER = ('Internals', 3)
    SERIALIZE = 'Optimize'

    def command(self):
        try:
            self._idx().save(self.session)
            GlobalPostingList.Optimize(self.session, self._idx(),
                                       force=('harder' in self.args))
            return self._success(_('Optimized search engine'))
        except KeyboardInterrupt:
            return self._error(_('Aborted'))


class RunWWW(Command):
    """Just run the web server"""
    SYNOPSIS = (None, 'www', None, None)
    ORDER = ('Internals', 5)

    def command(self):
        self.session.config.prepare_workers(self.session, daemons=True)
        while not mailpile.util.QUITTING:
            time.sleep(1)
        return self_success(_('Started the web server'))


class WritePID(Command):
    """Write the PID to a file"""
    SYNOPSIS = (None, 'pidfile', None, "</path/to/pidfile>")
    ORDER = ('Internals', 5)
    SPLIT_ARG = False

    def command(self):
        with open(self.args[0], 'w') as fd:
            fd.write('%d' % os.getpid())
        return self._success(_('Wrote PID to %s') % self.args)


class RenderPage(Command):
    """Does nothing, for use by semi-static jinja2 pages"""
    SYNOPSIS = (None, None, 'page', None)
    ORDER = ('Internals', 6)
    SPLIT_ARG = False
    HTTP_STRICT_VARS = False

    class CommandResult(Command.CommandResult):
        def __init__(self, *args, **kwargs):
            Command.CommandResult.__init__(self, *args, **kwargs)
            if self.result and 'path' in self.result:
                self.template_id = 'page/' + self.result['path'] + '/index'

    def command(self):
        return self._success(_('Rendered the page'), result={
            'path': (self.args and self.args[0] or ''),
            'data': self.data
        })


class ListDir(Command):
    """Display working directory listing"""
    SYNOPSIS = (None, 'ls', None, "<.../new/path/...>")
    ORDER = ('Internals', 5)

    class CommandResult(Command.CommandResult):
        def as_text(self):
            if self.result:
                lines = []
                for fn, sz, isdir in self.result:
                    lines.append(('%10.10s  %s%s'
                                  ) % (sz, fn, isdir and '/' or ''))
                return '\n'.join(lines)
            else:
                return _('Nothing Found')

    def command(self, args=None):
        args = list((args is None) and self.args or args or [])
        try:
            file_list = [(f.decode('utf-8'),
                          os.path.getsize(f),
                          os.path.isdir(f))
                         for f in os.listdir('.') if not f.startswith('.')
                         and not args or [a for a in args if a in f]]
            file_list.sort(key=lambda i: i[0].lower())
            return self._success(_('Current directory is %s') % os.getcwd(),
                                 result=file_list)
        except (OSError, IOError, UnicodeDecodeError), e:
            return self._error(_('Failed to list directory: %s') % e)


class ChangeDir(ListDir):
    """Change working directory"""
    SYNOPSIS = (None, 'cd', None, "<.../new/path/...>")
    ORDER = ('Internals', 5)

    def command(self, args=None):
        args = list((args is None) and self.args or args or [])
        try:
            os.chdir(args.pop(0).encode('utf-8'))
            return ListDir.command(self, args=args)
        except (OSError, IOError, UnicodeEncodeError), e:
            return self._error(_('Failed to change directories: %s') % e)


##[ Configuration commands ]###################################################

class ConfigSet(Command):
    """Change a setting"""
    SYNOPSIS = ('S', 'set', 'settings/set', '<section.variable> <value>')
    ORDER = ('Config', 1)
    SPLIT_ARG = False
    HTTP_CALLABLE = ('POST', 'UPDATE')
    HTTP_STRICT_VARS = False
    HTTP_POST_VARS = {
        'section.variable': 'value|json-string',
    }

    def command(self):
        config = self.session.config
        args = list(self.args)
        ops = []

        if config.sys.lockdown:
            return self._error(_('In lockdown, doing nothing.'))

        for var in self.data.keys():
            parts = ('.' in var) and var.split('.') or var.split('/')
            if parts[0] in config.rules:
                ops.append((var, self.data[var][0]))

        if self.args:
            arg = ' '.join(self.args)
            if '=' in arg:
                # Backwards compatiblity with the old 'var = value' syntax.
                var, value = [s.strip() for s in arg.split('=', 1)]
                var = var.replace(': ', '.').replace(':', '.').replace(' ', '')
            else:
                var, value = arg.split(' ', 1)
            ops.append((var, value))

        updated = {}
        for path, value in ops:
            value = value.strip()
            if value.startswith('{') or value.startswith('['):
                value = json.loads(value)
            try:
                cfg, var = config.walk(path.strip(), parent=1)
                cfg[var] = value
                updated[path] = value
            except IndexError:
                cfg, v1, v2 = config.walk(path.strip(), parent=2)
                cfg[v1] = {v2: value}

        self._serialize('Save config', lambda: config.save())
        return self._success(_('Updated your settings'), result=updated)


class ConfigAdd(Command):
    """Add a new value to a list (or ordered dict) setting"""
    SYNOPSIS = (None, 'append', 'settings/add', '<section.variable> <value>')
    ORDER = ('Config', 1)
    SPLIT_ARG = False
    HTTP_CALLABLE = ('POST', 'UPDATE')
    HTTP_STRICT_VARS = False
    HTTP_POST_VARS = {
        'section.variable': 'value|json-string',
    }

    def command(self):
        config = self.session.config
        ops = []

        if config.sys.lockdown:
            return self._error(_('In lockdown, doing nothing.'))

        for var in self.data.keys():
            parts = ('.' in var) and var.split('.') or var.split('/')
            if parts[0] in config.rules:
                ops.append((var, self.data[var][0]))

        if self.args:
            arg = ' '.join(self.args)
            if '=' in arg:
                # Backwards compatible with the old 'var = value' syntax.
                var, value = [s.strip() for s in arg.split('=', 1)]
                var = var.replace(': ', '.').replace(':', '.').replace(' ', '')
            else:
                var, value = arg.split(' ', 1)
            ops.append((var, value))

        updated = {}
        for path, value in ops:
            value = value.strip()
            if value.startswith('{') or value.startswith('['):
                value = json.loads(value)
            cfg, var = config.walk(path.strip(), parent=1)
            cfg[var].append(value)
            updated[path] = value

        self._serialize('Save config', lambda: config.save())
        return self._success(_('Updated your settings'), result=updated)


class ConfigUnset(Command):
    """Reset one or more settings to their defaults"""
    SYNOPSIS = ('U', 'unset', 'settings/unset', '<var>')
    ORDER = ('Config', 2)
    HTTP_CALLABLE = ('POST', )
    HTTP_POST_VARS = {
        'var': 'section.variables'
    }

    def command(self):
        session, config = self.session, self.session.config

        if config.sys.lockdown:
            return self._error(_('In lockdown, doing nothing.'))

        updated = []
        vlist = list(self.args) + (self.data.get('var', None) or [])
        for v in vlist:
            cfg, vn = config.walk(v, parent=True)
            if vn in cfg:
                del cfg[vn]
                updated.append(v)

        self._serialize('Save config', lambda: config.save())
        return self._success(_('Reset to default values'), result=updated)


class ConfigPrint(Command):
    """Print one or more settings"""
    SYNOPSIS = ('P', 'print', 'settings', '<var>')
    ORDER = ('Config', 3)
    HTTP_QUERY_VARS = {
        'var': 'section.variable'
    }

    def command(self):
        session, config = self.session, self.session.config
        result = {}
        invalid = []
        # FIXME: Are there privacy implications here somewhere?
        for key in (self.args + tuple(self.data.get('var', []))):
            try:
                result[key] = config.walk(key)
            except KeyError:
                invalid.append(key)
        if invalid:
            return self._error(_('Invalid keys'), info={'keys': invalid})
        else:
            return self._success(_('Displayed settings'), result=result)


class AddMailboxes(Command):
    """Add one or more mailboxes"""
    SYNOPSIS = ('A', 'add', None, '<path/to/mailbox>')
    ORDER = ('Config', 4)
    SPLIT_ARG = False
    HTTP_CALLABLE = ('POST', 'UPDATE')

    MAX_PATHS = 50000

    def command(self):
        session, config = self.session, self.session.config
        adding = []
        existing = config.sys.mailbox
        paths = list(self.args)

        if config.sys.lockdown:
            return self._error(_('In lockdown, doing nothing.'))

        try:
            while paths:
                raw_fn = paths.pop(0)
                fn = os.path.normpath(os.path.expanduser(raw_fn))
                fn = os.path.abspath(fn)
                if raw_fn in existing or fn in existing:
                    session.ui.warning('Already in the pile: %s' % raw_fn)
                elif raw_fn.startswith("imap://"):
                    adding.append(raw_fn)
                elif IsMailbox(fn, config):
                    adding.append(raw_fn)
                elif os.path.exists(fn) and os.path.isdir(fn):
                        session.ui.mark('Scanning %s for mailboxes' % fn)
                        try:
                            for f in [f for f in os.listdir(fn)
                                      if not f.startswith('.')]:
                                paths.append(os.path.join(fn, f))
                                if len(paths) > self.MAX_PATHS:
                                    return self._error(_('Too many files'))
                        except OSError:
                            if raw_fn in self.args:
                                return self._error(_('Failed to read: %s'
                                                     ) % raw_fn)
                elif raw_fn in self.args:
                    return self._error(_('No such file or directory: %s'
                                         ) % raw_fn)
        except KeyboardInterrupt:
            return self._error(_('User aborted'))

        added = {}
        for arg in adding:
            added[config.sys.mailbox.append(arg)] = arg
        if added:
            self._serialize('Save config', lambda: config.save())
            return self._success(_('Added %d mailboxes') % len(added),
                                 result={'added': added})
        else:
            return self._success(_('Nothing was added'))


###############################################################################

class Output(Command):
    """Choose format for command results."""
    SYNOPSIS = (None, 'output', None, '[json|text|html|<template>.html|...]')
    ORDER = ('Internals', 7)
    HTTP_STRICT_VARS = False
    LOG_NOTHING = True

    def get_render_mode(self):
        return self.args and self.args[0] or 'text'

    def command(self):
        m = self.session.ui.render_mode = self.get_render_mode()
        return self._success(_('Set output mode to: %s') % m,
                             result={'output': m})


class Quit(Command):
    """Exit Mailpile """
    SYNOPSIS = ("q", "quit", None, None)
    ABOUT = ("Quit mailpile")
    ORDER = ("Internals", 2)
    RAISES = (KeyboardInterrupt,)

    def command(self):
        config = self.session.config
        mailpile.util.QUITTING = True
        raise KeyboardInterrupt()


class Help(Command):
    """Print help on Mailpile or individual commands."""
    SYNOPSIS = ('h', 'help', 'help', '[<command-group>]')
    ABOUT = ('This is Mailpile!')
    ORDER = ('Config', 9)

    class CommandResult(Command.CommandResult):

        def splash_as_text(self):
            if self.result['http_url']:
                web_interface = _('The Web interface address is: %s'
                                  ) % self.result['http_url']
            else:
                web_interface = _('The Web interface is disabled.')
            return '\n'.join([
                self.result['splash'],
                web_interface,
                '',
                _('Type `help` for instructions or press <Ctrl-d> to quit.'),
                ''
            ])

        def variables_as_text(self):
            text = []
            for group in self.result['variables']:
                text.append(group['name'])
                for var in group['variables']:
                    sep = ('=' in var['type']) and ': ' or ' = '
                    text.append(('  %-35s %s'
                                 ) % (('%s%s<%s>'
                                       ) % (var['var'], sep,
                                            var['type'].replace('=', '> = <')),
                                      var['desc']))
                text.append('')
            return '\n'.join(text)

        def commands_as_text(self):
            text = [_('Commands:')]
            last_rank = None
            cmds = self.result['commands']
            width = self.result.get('width', 8)
            ckeys = cmds.keys()
            ckeys.sort(key=lambda k: cmds[k][3])
            for c in ckeys:
                cmd, args, explanation, rank = cmds[c]
                if not rank or not cmd:
                    continue
                if last_rank and int(rank / 10) != last_rank:
                    text.append('')
                last_rank = int(rank / 10)
                if c[0] == '_':
                    c = '  '
                else:
                    c = '%s|' % c[0]
                fmt = '  %%s%%-%d.%ds' % (width, width)
                if explanation:
                    if len(args or '') <= 15:
                        fmt += ' %-15.15s %s'
                    else:
                        fmt += ' %%s\n%s %%s' % (' ' * (len(c) + width + 18))
                else:
                    explanation = ''
                    fmt += ' %s %s '
                text.append(fmt % (c, cmd.replace('=', ''),
                                   args and ('%s' % (args, )) or '',
                                   (explanation.splitlines() or [''])[0]))
            if 'tags' in self.result:
                text.extend([
                    '',
                    _('Tags:  (use a tag as a command to display tagged '
                      'messages)'),
                    '',
                    self.result['tags'].as_text()
                ])
            return '\n'.join(text)

        def as_text(self):
            if not self.result:
                return _('Error')
            return ''.join([
                ('splash' in self.result) and self.splash_as_text() or '',
                (('variables' in self.result) and self.variables_as_text()
                 or ''),
                ('commands' in self.result) and self.commands_as_text() or '',
            ])

    def command(self):
        self.session.ui.reset_marks(quiet=True)
        if self.args:
            command = self.args[0]
            for cls in COMMANDS:
                name = cls.SYNOPSIS[1] or cls.SYNOPSIS[2]
                width = len(name)
                if name and name == command:
                    order = 1
                    cmd_list = {'_main': (name, cls.SYNOPSIS[3],
                                          cls.__doc__, order)}
                    subs = [c for c in COMMANDS
                            if (c.SYNOPSIS[1] or c.SYNOPSIS[2]
                                ).startswith(name + '/')]
                    for scls in sorted(subs):
                        sc, scmd, surl, ssynopsis = scls.SYNOPSIS[:4]
                        order += 1
                        cmd_list['_%s' % scmd] = (scmd, ssynopsis,
                                                  scls.__doc__, order)
                        width = max(len(scmd or surl), width)
                    return self._success(_('Displayed help'), result={
                        'pre': cls.__doc__,
                        'commands': cmd_list,
                        'width': width
                    })
            return self._error(_('Unknown command'))

        else:
            cmd_list = {}
            count = 0
            for grp in COMMAND_GROUPS:
                count += 10
                for cls in COMMANDS:
                    c, name, url, synopsis = cls.SYNOPSIS[:4]
                    if cls.ORDER[0] == grp and '/' not in (name or ''):
                        cmd_list[c or '_%s' % name] = (name, synopsis,
                                                       cls.__doc__,
                                                       count + cls.ORDER[1])
            return self._success(_('Displayed help'), result={
                'commands': cmd_list,
                'tags': GetCommand('tags')(self.session).run(),
                'index': self._idx()
            })

    def _starting(self):
        pass

    def _finishing(self, command, rv):
        return self.CommandResult(self, self.session, self.name,
                                  command.__doc__ or self.__doc__, rv,
                                  self.status, self.message)


class HelpVars(Help):
    """Print help on Mailpile variables"""
    SYNOPSIS = (None, 'help/variables', 'help/variables', None)
    ABOUT = ('The available mailpile variables')
    ORDER = ('Config', 9)

    def command(self):
        config = self.session.config.rules
        result = []
        categories = ["sys", "prefs", "profiles"]
        for cat in categories:
            variables = []
            what = config[cat]
            if isinstance(what[2], dict):
                for ii, i in what[2].iteritems():
                    variables.append({
                        'var': ii,
                        'type': str(i[1]),
                        'desc': i[0]
                    })
            variables.sort(key=lambda k: k['var'])
            result.append({
                'category': cat,
                'name': config[cat][0],
                'variables': variables
            })
        result.sort(key=lambda k: config[k['category']][0])
        return self._success(_('Displayed variables'),
                             result={'variables': result})


class HelpSplash(Help):
    """Print Mailpile splash screen"""
    SYNOPSIS = (None, 'help/splash', 'help/splash', None)
    ORDER = ('Config', 9)

    def command(self):
        http_worker = self.session.config.http_worker
        if http_worker:
            http_url = 'http://%s:%s/' % http_worker.httpd.sspec
        else:
            http_url = ''
        return self._success(_('Displayed welcome message'), result={
            'splash': self.ABOUT,
            'http_url': http_url,
        })


def GetCommand(name):
    match = [c for c in COMMANDS if name in c.SYNOPSIS[:3]]
    if len(match) == 1:
        return match[0]
    return None


def Action(session, opt, arg, data=None):
    session.ui.reset_marks(quiet=True)
    config = session.config

    if not opt:
        return Help(session, 'help').run()

    # Use the COMMANDS dict by default.
    command = GetCommand(opt)
    if command:
        return command(session, opt, arg, data=data).run()

    # Tags are commands
    tag = config.get_tag(opt)
    if tag:
        return GetCommand('search')(session, opt, arg=arg, data=data
                                    ).run(search=['in:%s' % tag._key])

    # OK, give up!
    raise UsageError(_('Unknown command: %s') % opt)


# Commands starting with _ don't get single-letter shortcodes...
COMMANDS = [
    Optimize, Rescan, RunWWW, ListDir, ChangeDir, WritePID, RenderPage,
    ConfigPrint, ConfigSet, ConfigAdd, ConfigUnset, AddMailboxes,
    Output, Help, HelpVars, HelpSplash, Quit
]
COMMAND_GROUPS = ['Internals', 'Config', 'Searching', 'Tagging', 'Composing']

########NEW FILE########
__FILENAME__ = config
import copy
import cPickle
import io
import json
import os
import random
import re
import threading
import traceback
import ConfigParser
from gettext import translation, gettext, NullTranslations
from gettext import gettext as _

from jinja2 import Environment, BaseLoader, TemplateNotFound

from urllib import quote, unquote
from mailpile.crypto.streamer import DecryptingStreamer

try:
    import ssl
except ImportError:
    ssl = None

try:
    import sockschain as socks
except ImportError:
    try:
        import socks
    except ImportError:
        socks = None

from mailpile.commands import Rescan
from mailpile.eventlog import EventLog
from mailpile.httpd import HttpWorker
from mailpile.mailboxes import MBX_ID_LEN, OpenMailbox, NoSuchMailboxError
from mailpile.mailboxes import wervd
from mailpile.search import MailIndex
from mailpile.util import *
from mailpile.ui import Session, BackgroundInteraction
from mailpile.vcard import SimpleVCard, VCardStore
from mailpile.workers import Worker, DumbWorker, Cron


def ConfigPrinter(cfg, indent=''):
    rv = []
    if isinstance(cfg, dict):
        pairer = cfg.iteritems()
    else:
        pairer = enumerate(cfg)
    for key, val in pairer:
        if hasattr(val, 'rules'):
            preamble = '[%s: %s] ' % (val._NAME, val._COMMENT)
        else:
            preamble = ''
        if isinstance(val, (dict, list, tuple)):
            if isinstance(val, dict):
                b, e = '{', '}'
            else:
                b, e = '[', ']'
            rv.append(('%s: %s%s\n%s\n%s'
                       '' % (key, preamble, b, ConfigPrinter(val, '  '), e)
                       ).replace('\n  \n', ''))
        elif isinstance(val, (str, unicode)):
            rv.append('%s: "%s"' % (key, val))
        else:
            rv.append('%s: %s' % (key, val))
    return indent + ',\n'.join(rv).replace('\n', '\n'+indent)


def getLocaleDirectory():
    """Get the gettext translation object, no matter where our CWD is"""
    # NOTE: MO files are loaded from the directory where the scripts reside in
    return os.path.join(os.path.dirname(__file__), "..", "locale")


class InvalidKeyError(ValueError):
    pass


class CommentedEscapedConfigParser(ConfigParser.RawConfigParser):
    """
    This is a ConfigParser that allows embedded comments and safely escapes
    and encodes/decodes values that include funky characters.

    >>> cfg.sys.debug = u'm\\xe1ny\\nlines\\nof\\nbelching  '
    >>> cecp = CommentedEscapedConfigParser()
    >>> cecp.readfp(io.BytesIO(cfg.as_config_bytes()))
    >>> cecp.get('config/sys: Technical system settings', 'debug'
    ...          ) == cfg.sys.debug
    True

    >>> cecp.items('config/sys: Technical system settings')
    [(u'debug', u'm\\xe1ny\\nlines\\nof\\nbelching  ')]
    """
    def set(self, section, key, value, comment):
        key = unicode(key).encode('utf-8')
        section = unicode(section).encode('utf-8')
        value = quote(unicode(value).encode('utf-8'), safe=' /')
        if value.endswith(' '):
            value = value[:-1] + '%20'
        if comment:
            pad = ' ' * (25 - len(key) - len(value)) + ' ; '
            value = '%s%s%s' % (value, pad, comment)
        return ConfigParser.RawConfigParser.set(self, section, key, value)

    def get(self, section, key):
        key = unicode(key).encode('utf-8')
        section = unicode(section).encode('utf-8')
        value = ConfigParser.RawConfigParser.get(self, section, key)
        return unquote(value).decode('utf-8')

    def items(self, section):
        return [(k.decode('utf-8'), unquote(i).decode('utf-8')) for k, i
                in ConfigParser.RawConfigParser.items(self, section)]


def _MakeCheck(pcls, name, comment, rules):
    class Checker(pcls):
        _NAME = name
        _RULES = rules
        _COMMENT = comment
    return Checker


def _BoolCheck(value):
    """
    Convert common yes/no strings into booleal values.

    >>> _BoolCheck('yes')
    True
    >>> _BoolCheck('no')
    False

    >>> _BoolCheck('true')
    True
    >>> _BoolCheck('false')
    False

    >>> _BoolCheck('on')
    True
    >>> _BoolCheck('off')
    False

    >>> _BoolCheck('wiggle')
    Traceback (most recent call last):
        ...
    ValueError: Invalid boolean: wiggle
    """
    if value in (True, False):
        return value
    if value.lower() in ('1', 'true', 'yes', 'on',
                         _('true'), _('yes'), _('on')):
        return True
    if value.lower() in ('0', 'false', 'no', 'off',
                         _('false'), _('no'), _('off')):
        return False
    raise ValueError(_('Invalid boolean: %s') % value)


def _SlugCheck(slug, allow=''):
    """
    Verify that a string is a valid URL slug.

    >>> _SlugCheck('_Foo-bar.5')
    '_foo-bar.5'

    >>> _SlugCheck('Bad Slug')
    Traceback (most recent call last):
        ...
    ValueError: Invalid URL slug: Bad Slug

    >>> _SlugCheck('Bad/Slug')
    Traceback (most recent call last):
        ...
    ValueError: Invalid URL slug: Bad/Slug
    """
    if not slug == CleanText(unicode(slug),
                             banned=(CleanText.NONDNS.replace(allow, ''))
                             ).clean:
        raise ValueError(_('Invalid URL slug: %s') % slug)
    return slug.lower()


def _SlashSlugCheck(slug):
    """
    Verify that a string is a valid URL slug (slashes allowed).

    >>> _SlashSlugCheck('Okay/Slug')
    'okay/slug'
    """
    return _SlugCheck(slug, allow='/')


def _HostNameCheck(host):
    """
    Verify that a string is a valid host-name, return it lowercased.

    >>> _HostNameCheck('foo.BAR.baz')
    'foo.bar.baz'

    >>> _HostNameCheck('127.0.0.1')
    '127.0.0.1'

    >>> _HostNameCheck('not/a/hostname')
    Traceback (most recent call last):
        ...
    ValueError: Invalid hostname: not/a/hostname
    """
    # FIXME: We do not want to check the network, but rules for DNS are
    #        still stricter than this so a static check could do more.
    if not unicode(host) == CleanText(unicode(host),
                                      banned=CleanText.NONDNS).clean:
        raise ValueError(_('Invalid hostname: %s') % host)
    return str(host).lower()


def _B36Check(b36val):
    """
    Verify that a string is a valid path base-36 integer.

    >>> _B36Check('aa')
    'aa'

    >>> _B36Check('.')
    Traceback (most recent call last):
        ...
    ValueError: invalid ...
    """
    int(b36val, 36)
    return str(b36val).lower()


def _PathCheck(path):
    """
    Verify that a string is a valid path, make it absolute.

    >>> _PathCheck('/etc/../')
    '/'

    >>> _PathCheck('/no/such/path')
    Traceback (most recent call last):
        ...
    ValueError: File/directory does not exist: /no/such/path
    """
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        raise ValueError(_('File/directory does not exist: %s') % path)
    return os.path.abspath(path)


def _FileCheck(path):
    """
    Verify that a string is a valid path to a file, make it absolute.

    >>> _FileCheck('/etc/../etc/passwd')
    '/etc/passwd'

    >>> _FileCheck('/')
    Traceback (most recent call last):
        ...
    ValueError: Not a file: /
    """
    path = _PathCheck(path)
    if not os.path.isfile(path):
        raise ValueError(_('Not a file: %s') % path)
    return path


def _DirCheck(path):
    """
    Verify that a string is a valid path to a directory, make it absolute.

    >>> _DirCheck('/etc/../')
    '/'

    >>> _DirCheck('/etc/passwd')
    Traceback (most recent call last):
        ...
    ValueError: Not a directory: /etc/passwd
    """
    path = _PathCheck(path)
    if not os.path.isdir(path):
        raise ValueError(_('Not a directory: %s') % path)
    return path


def _NewPathCheck(path):
    """
    Verify that a string is a valid path to a directory, make it absolute.

    >>> _NewPathCheck('/magic')
    '/magic'

    >>> _NewPathCheck('/no/such/path/magic')
    Traceback (most recent call last):
        ...
    ValueError: File/directory does not exist: /no/such/path
    """
    _PathCheck(os.path.dirname(path))
    return os.path.abspath(path)


class IgnoreValue(Exception):
    pass


def _IgnoreCheck(data):
    raise IgnoreValue()


def RuledContainer(pcls):
    """
    Factory for abstract 'container with rules' class. See ConfigDict for
    details, examples and tests.
    """

    class _RuledContainer(pcls):
        RULE_COMMENT = 0
        RULE_CHECKER = 1
        # Reserved ...
        RULE_DEFAULT = -1
        RULE_CHECK_MAP = {
            bool: _BoolCheck,
            'bool': _BoolCheck,
            'b36': _B36Check,
            'dir': _DirCheck,
            'directory': _DirCheck,
            'ignore': _IgnoreCheck,
            'email': unicode,  # FIXME: Make more strict
            'False': False, 'false': False,
            'file': _FileCheck,
            'float': float,
            'hostname': _HostNameCheck,
            'int': int,
            'long': long,
            'multiline': unicode,
            'new file': _NewPathCheck,
            'new dir': _NewPathCheck,
            'new directory': _NewPathCheck,
            'path': _PathCheck,
            str: unicode,
            'slashslug': _SlashSlugCheck,
            'slug': _SlugCheck,
            'str': unicode,
            'True': True, 'true': True,
            'timestamp': long,
            'unicode': unicode,
            'url': unicode,  # FIXME: Make more strict
        }
        _NAME = 'container'
        _RULES = None
        _COMMENT = None
        _MAGIC = True

        def __init__(self, *args, **kwargs):
            rules = kwargs.get('_rules', self._RULES or {})
            self._name = kwargs.get('_name', self._NAME)
            self._comment = kwargs.get('_comment', self._COMMENT)
            enable_magic = kwargs.get('_magic', self._MAGIC)
            for kw in ('_rules', '_comment', '_name', '_magic'):
                if kw in kwargs:
                    del kwargs[kw]

            pcls.__init__(self)
            self._key = self._name
            self._rules_source = rules
            self.rules = {}
            self.set_rules(rules)
            self.update(*args, **kwargs)

            self._magic = enable_magic  # Enable the getitem/getattr magic

        def __str__(self):
            return json.dumps(self, sort_keys=True, indent=2)

        def __unicode__(self):
            return json.dumps(self, sort_keys=True, indent=2)

        def as_config_bytes(self, private=True):
            of = io.BytesIO()
            self.as_config(private=private).write(of)
            return of.getvalue()

        def as_config(self, config=None, private=True):
            config = config or CommentedEscapedConfigParser()
            section = self._name
            if self._comment:
                section += ': %s' % self._comment
            added_section = False

            keys = self.rules.keys()
            ignore = self.ignored_keys() | set(['_any'])
            if not keys or '_any' in keys:
                keys.extend(self.keys())
            keys = [k for k in sorted(set(keys)) if k not in ignore]
            set_keys = set(self.keys())

            for key in keys:
                if not hasattr(self[key], 'as_config'):
                    if key in self.rules:
                        comment = _(self.rules[key][self.RULE_COMMENT])
                    else:
                        comment = ''
                    value = unicode(self[key])
                    if value is not None and value != '':
                        if key not in set_keys:
                            key = ';' + key
                            comment = '(default) ' + comment
                        if comment:
                            pad = ' ' * (30 - len(key) - len(value)) + ' ; '
                        else:
                            pad = ''
                        if not added_section:
                            config.add_section(str(section))
                            added_section = True
                        config.set(section, key, value, comment)
            for key in keys:
                if hasattr(self[key], 'as_config'):
                    self[key].as_config(config=config)

            return config

        def reset(self, rules=True, data=True):
            raise Exception(_('Please override this method'))

        def set_rules(self, rules):
            assert(isinstance(rules, dict))
            self.reset()
            for key, rule in rules.iteritems():
                self.add_rule(key, rule)

        def add_rule(self, key, rule):
            if not ((isinstance(rule, (list, tuple))) and
                    (key == CleanText(key, banned=CleanText.NONVARS).clean) and
                    (not self.real_hasattr(key))):
                raise TypeError('add_rule(%s, %s): Bad key or rule.'
                                % (key, rule))

            rule = list(rule[:])
            self.rules[key] = rule
            check = rule[self.RULE_CHECKER]
            try:
                check = self.RULE_CHECK_MAP.get(check, check)
                rule[self.RULE_CHECKER] = check
            except TypeError:
                pass

            name = '%s/%s' % (self._name, key)
            comment = rule[self.RULE_COMMENT]
            value = rule[self.RULE_DEFAULT]

            if (isinstance(check, dict) and value is not None
                    and not isinstance(value, (dict, list))):
                raise TypeError(_('Only lists or dictionaries can contain '
                                  'dictionary values (key %s).') % name)

            if isinstance(value, dict) and check is False:
                pcls.__setitem__(self, key, ConfigDict(_name=name,
                                                       _comment=comment,
                                                       _rules=value))

            elif isinstance(value, dict):
                if value:
                    raise ValueError(_('Subsections must be immutable '
                                       '(key %s).') % name)
                sub_rule = {'_any': [rule[self.RULE_COMMENT], check, None]}
                checker = _MakeCheck(ConfigDict, name, check, sub_rule)
                pcls.__setitem__(self, key, checker())
                rule[self.RULE_CHECKER] = checker

            elif isinstance(value, list):
                if value:
                    raise ValueError(_('Lists cannot have default values '
                                       '(key %s).') % name)
                sub_rule = {'_any': [rule[self.RULE_COMMENT], check, None]}
                checker = _MakeCheck(ConfigList, name, comment, sub_rule)
                pcls.__setitem__(self, key, checker())
                rule[self.RULE_CHECKER] = checker

            elif not isinstance(value, (type(None), int, long, bool,
                                        float, str, unicode)):
                raise TypeError(_('Invalid type "%s" for key "%s" (value: %s)'
                                  ) % (type(value), name, repr(value)))

        def __fixkey__(self, key):
            return key

        def fmt_key(self, key):
            return key

        def get_rule(self, key):
            key = self.__fixkey__(key)
            rule = self.rules.get(key, None)
            if rule is None:
                if '_any' in self.rules:
                    rule = self.rules['_any']
                else:
                    raise InvalidKeyError(_('Invalid key for %s: %s'
                                            ) % (self._name, key))
            if isinstance(rule[self.RULE_CHECKER], dict):
                rule = rule[:]
                rule[self.RULE_CHECKER] = _MakeCheck(
                    ConfigDict,
                    '%s/%s' % (self._name, key),
                    rule[self.RULE_COMMENT],
                    rule[self.RULE_CHECKER])
            return rule

        def ignored_keys(self):
            return set([k for k in self.rules
                        if self.rules[k][self.RULE_CHECKER] == _IgnoreCheck])

        def walk(self, path, parent=0):
            if '.' in path:
                sep = '.'
            else:
                sep = '/'
            path_parts = path.split(sep)
            cfg = self
            if parent:
                vlist = path_parts[-parent:]
                path_parts[-parent:] = []
            else:
                vlist = []
            for part in path_parts:
                cfg = cfg[part]
            if parent:
                return tuple([cfg] + vlist)
            else:
                return cfg

        def get(self, key, default=None):
            key = self.__fixkey__(key)
            if key in self:
                return pcls.__getitem__(self, key)
            if default is None and key in self.rules:
                return self.rules[key][self.RULE_DEFAULT]
            return default

        def __getitem__(self, key):
            key = self.__fixkey__(key)
            if key in self.rules or '_any' in self.rules:
                return self.get(key)
            return pcls.__getitem__(self, key)

        def real_getattr(self, attr):
            try:
                return pcls.__getattribute__(self, attr)
            except AttributeError:
                return False

        def real_hasattr(self, attr):
            try:
                pcls.__getattribute__(self, attr)
                return True
            except AttributeError:
                return False

        def real_setattr(self, attr, value):
            return pcls.__setattr__(self, attr, value)

        def __getattr__(self, attr, default=None):
            if self.real_hasattr(attr) or not self.real_getattr('_magic'):
                return pcls.__getattribute__(self, attr)
            return self[attr]

        def __setattr__(self, attr, value):
            if self.real_hasattr(attr) or not self.real_getattr('_magic'):
                return self.real_setattr(attr, value)
            self.__setitem__(attr, value)

        def __passkey__(self, key, value):
            if hasattr(value, '__passkey__'):
                value._key = key
                value._name = '%s/%s' % (self._name, key)

        def __passkey_recurse__(self, key, value):
            if hasattr(value, '__passkey__'):
                if isinstance(value, (list, tuple)):
                    for k in range(0, len(value)):
                        value.__passkey__(value.__fixkey__(k), value[k])
                elif isinstance(value, dict):
                    for k in value:
                        value.__passkey__(value.__fixkey__(k), value[k])

        def __createkey_and_setitem__(self, key, value):
            pcls.__setitem__(self, key, value)

        def __setitem__(self, key, value):
            key = self.__fixkey__(key)
            checker = self.get_rule(key)[self.RULE_CHECKER]
            if not checker is True:
                if checker is False:
                    raise ValueError(_('Modifying %s/%s is not allowed'
                                       ) % (self._name, key))
                if isinstance(checker, (list, set, tuple)):
                    if value not in checker:
                        raise ValueError(_('Invalid value for %s/%s: %s'
                                           ) % (self._name, key, value))
                elif isinstance(checker, (type, type(RuledContainer))):
                    try:
                        if value is None:
                            value = checker()
                        else:
                            value = checker(value)
                    except (IgnoreValue):
                        return
                    except (ValueError, TypeError):
                        raise ValueError(_('Invalid value for %s/%s: %s'
                                           ) % (self._name, key, value))
                else:
                    raise Exception(_('Unknown constraint for %s/%s: %s'
                                      ) % (self._name, key, checker))
            self.__passkey__(key, value)
            self.__createkey_and_setitem__(key, value)
            self.__passkey_recurse__(key, value)

        def extend(self, src):
            for val in src:
                self.append(val)

        def __iadd__(self, src):
            self.extend(src)
            return self

    return _RuledContainer


class ConfigList(RuledContainer(list)):
    """
    A sanity-checking, self-documenting list of program settings.

    Instances of this class are usually contained within a ConfigDict.

    >>> lst = ConfigList(_rules={'_any': ['We only like ints', int, 0]})
    >>> lst.append('1')
    '0'
    >>> lst.extend([2, '3'])
    >>> lst
    [1, 2, 3]

    >>> lst += ['1', '2']
    >>> lst
    [1, 2, 3, 1, 2]

    >>> lst.extend(range(0, 100))
    >>> lst['c'] == lst[int('c', 36)]
    True
    """
    def reset(self, rules=True, data=True):
        if rules:
            self.rules = {}
        if data:
            self[:] = []

    def __createkey_and_setitem__(self, key, value):
        while key > len(self):
            self.append(self.rules['_any'][self.RULE_DEFAULT])
        if key == len(self):
            self.append(value)
        else:
            list.__setitem__(self, key, value)

    def append(self, value):
        list.append(self, None)
        try:
            self[len(self) - 1] = value
            return b36(len(self) - 1)
        except:
            self[len(self) - 1:] = []
            raise

    def __passkey__(self, key, value):
        if hasattr(value, '__passkey__'):
            key = b36(key).lower()
            value._key = key
            value._name = '%s/%s' % (self._name, key)

    def __fixkey__(self, key):
        if isinstance(key, (str, unicode)):
            try:
                key = int(key, 36)
            except ValueError:
                pass
        return key

    def __getitem__(self, key):
        return list.__getitem__(self, self.__fixkey__(key))

    def fmt_key(self, key):
        f = b36(self.__fixkey__(key)).lower()
        return ('0000' + f)[-4:] if (len(f) < 4) else f

    def keys(self):
        return [self.fmt_key(i) for i in range(0, len(self))]

    def iteritems(self):
        for k in self.keys():
            yield (k, self[k])

    def values(self):
        return self[:]

    def update(self, *args):
        for l in args:
            l = list(l)
            for i in range(0, len(self)):
                self[i] = l[i]
            for i in range(len(self), len(l)):
                self.append(l[i])


class ConfigDict(RuledContainer(dict)):
    """
    A sanity-checking, self-documenting dictionary of program settings.

    The object must be initialized with a dictionary which describes in
    a structured way what variables exist, what their legal values are,
    and what their defaults are and what they are for.

    Each variable definition expects three values:
       1. A human readable description of what the variable is
       2. A data type / sanity check
       3. A default value

    If the sanity check is itself a dictionary of rules, values are expected
    to be dictionaries or lists of items that match the rules defined. This
    should be used with an empty list or dictionary as a default value.

    Configuration data can be nested by including a dictionary of further
    rules in place of the default value.

    If the default value is an empty list, it is assumed to be a list of
    values of the type specified.

    Examples:

    >>> pot = ConfigDict(_rules={'potatoes': ['How many potatoes?', 'int', 0],
    ...                          'carrots': ['How many carrots?', int, 99],
    ...                          'liquids': ['Fluids we like', False, {
    ...                                         'water': ['Liters', int, 0],
    ...                                         'vodka': ['Liters', int, 12]
    ...                                      }],
    ...                          'tags': ['Tags', {'c': ['C', int, 0],
    ...                                            'x': ['X', str, '']}, []],
    ...                          'colors': ['Colors', ('red', 'blue'), []]})
    >>> sorted(pot.keys()), sorted(pot.values())
    (['colors', 'liquids', 'tags'], [[], [], {}])

    >>> pot['potatoes'] = pot['liquids']['vodka'] = "123"
    >>> pot['potatoes']
    123
    >>> pot['liquids']['vodka']
    123
    >>> pot['carrots']
    99

    >>> pot.walk('liquids.vodka')
    123
    >>> pot.walk('liquids/vodka', parent=True)
    ({...}, 'vodka')

    >>> pot['colors'].append('red')
    '0'
    >>> pot['colors'].extend(['blue', 'red', 'red'])
    >>> pot['colors']
    ['red', 'blue', 'red', 'red']

    >>> pot['tags'].append({'c': '123', 'x': 'woots'})
    '0'
    >>> pot['tags'][0]['c']
    123
    >>> pot['tags'].append({'z': 'invalid'})
    Traceback (most recent call last):
        ...
    ValueError: Invalid value for config/tags/1: ...

    >>> pot['evil'] = 123
    Traceback (most recent call last):
        ...
    InvalidKeyError: Invalid key for config: evil
    >>> pot['liquids']['evil'] = 123
    Traceback (most recent call last):
        ...
    InvalidKeyError: Invalid key for config/liquids: evil
    >>> pot['potatoes'] = "moo"
    Traceback (most recent call last):
        ...
    ValueError: Invalid value for config/potatoes: moo
    >>> pot['colors'].append('green')
    Traceback (most recent call last):
        ...
    ValueError: Invalid value for config/colors/4: green

    >>> pot.rules['potatoes']
    ['How many potatoes?', <type 'int'>, 0]

    >>> isinstance(pot['liquids'], ConfigDict)
    True
    """
    _NAME = 'config'

    def reset(self, rules=True, data=True):
        if rules:
            self.rules = {}
        if data:
            for key in self.keys():
                if hasattr(self[key], 'reset'):
                    self[key].reset(rules=rules, data=data)
                else:
                    dict.__delitem__(self, key)

    def all_keys(self):
        return list(set(self.keys()) | set(self.rules.keys())
                    - self.ignored_keys() - set(['_any']))

    def append(self, value):
        """Add to the dict using an autoselected key"""
        if '_any' in self.rules:
            k = b36(max([int(k, 36) for k in self.keys()] + [-1]) + 1).lower()
            self[k] = value
            return k
        else:
            raise UsageError(_('Cannot append to fixed dict'))

    def update(self, *args, **kwargs):
        """Reimplement update, so it goes through our sanity checks."""
        for src in args:
            if hasattr(src, 'keys'):
                for key in src:
                    self[key] = src[key]
            else:
                for key, val in src:
                    self[key] = val
        for key in kwargs:
            self[key] = kwargs[key]


class PathDict(ConfigDict):
    _RULES = {
        '_any': ['Data directory', 'directory', '']
    }


class MailpileJinjaLoader(BaseLoader):
    """
    A Jinja2 template loader which uses the Mailpile configuration
    and plugin system to find template files.
    """
    def __init__(self, config):
        self.config = config

    def get_source(self, environment, template):
        tpl = os.path.join('html', template)
        path, mt = self.config.data_file_and_mimetype('html_theme', tpl)
        if not path:
            raise TemplateNotFound(tpl)

        mtime = os.path.getmtime(path)
        unchanged = lambda: (
            path == self.config.data_file_and_mimetype('html_theme', tpl)[0]
            and mtime == os.path.getmtime(path))

        with file(path) as f:
            source = f.read().decode('utf-8')

        return source, path, unchanged


class ConfigManager(ConfigDict):
    """
    This class manages the live global mailpile configuration. This includes
    the settings themselves, as well as global objects like the index and
    references to any background worker threads.
    """
    DEFAULT_WORKDIR = os.environ.get('MAILPILE_HOME',
                                     os.path.expanduser('~/.mailpile'))

    def __init__(self, workdir=None, rules={}):
        ConfigDict.__init__(self, _rules=rules, _magic=False)

        self.workdir = workdir or self.DEFAULT_WORKDIR
        self.conffile = os.path.join(self.workdir, 'mailpile.cfg')

        self.plugins = None
        self.background = None
        self.cron_worker = None
        self.http_worker = None
        self.dumb_worker = self.slow_worker = DumbWorker('Dumb worker', None)
        self.other_workers = []
        self.mail_sources = {}

        self.jinja_env = None

        self.event_log = None
        self.index = None
        self.vcards = {}
        self._mbox_cache = {}
        self._running = {}
        self._lock = threading.RLock()

        self._magic = True  # Enable the getattr/getitem magic

    def _mkworkdir(self, session):
        if not os.path.exists(self.workdir):
            if session:
                session.ui.notify(_('Creating: %s') % self.workdir)
            os.mkdir(self.workdir)

    def parse_config(self, session, data, source='internal'):
        """
        Parse a config file fragment. Invalid data will be ignored, but will
        generate warnings in the session UI. Returns True on a clean parse,
        False if any of the settings were bogus.

        >>> cfg.parse_config(session, '[config/sys]\\nfd_cache_size = 123\\n')
        True
        >>> cfg.sys.fd_cache_size
        123

        >>> cfg.parse_config(session, '[config/bogus]\\nblabla = bla\\n')
        False
        >>> [l[1] for l in session.ui.log_buffer if 'bogus' in l[1]][0]
        'Invalid (internal): section config/bogus does not exist'

        >>> cfg.parse_config(session, '[config/sys]\\nhistory_length = 321\\n'
        ...                                          'bogus_variable = 456\\n')
        False
        >>> cfg.sys.history_length
        321
        >>> [l[1] for l in session.ui.log_buffer if 'bogus_var' in l[1]][0]
        u'Invalid (internal): section config/sys, ...

        >>> cfg.parse_config(session, '[config/tags/a]\\nname = TagName\\n')
        True
        >>> cfg.tags['a']._key
        'a'
        >>> cfg.tags['a'].name
        u'TagName'
        """
        parser = CommentedEscapedConfigParser()
        parser.readfp(io.BytesIO(str(data)))

        def item_sorter(i):
            try:
                return (int(i[0], 36), i[1])
            except (ValueError, IndexError, KeyError, TypeError):
                return i

        all_okay = True
        for section in parser.sections():
            okay = True
            cfgpath = section.split(':')[0].split('/')[1:]
            cfg = self
            added_parts = []
            for part in cfgpath:
                if cfg.fmt_key(part) in cfg.keys():
                    cfg = cfg[part]
                elif '_any' in cfg.rules:
                    cfg[part] = {}
                    cfg = cfg[part]
                else:
                    if session:
                        msg = _('Invalid (%s): section %s does not '
                                'exist') % (source, section)
                        session.ui.warning(msg)
                    all_okay = okay = False
            items = parser.items(section) if okay else []
            items.sort(key=item_sorter)
            for var, val in items:
                try:
                    cfg[var] = val
                except (ValueError, KeyError, IndexError):
                    if session:
                        msg = _(u'Invalid (%s): section %s, variable %s=%s'
                                ) % (source, section, var, val)
                        session.ui.warning(msg)
                    all_okay = okay = False
        return all_okay

    def load(self, *args, **kwargs):
        self._lock.acquire()
        try:
            return self._unlocked_load(*args, **kwargs)
        finally:
            self._lock.release()

    def _unlocked_load(self, session, filename=None):
        self._mkworkdir(session)
        self.index = None
        self.reset(rules=False, data=True)

        filename = filename or self.conffile
        lines = []
        try:
            with open(filename, 'rb') as fd:
                decrypt_and_parse_lines(fd, lambda l: lines.append(l), None)
        except ValueError:
            pass
        except IOError:
            pass

        # Discover plugins and update the config rule to match
        from mailpile.plugins import PluginManager
        self.plugins = PluginManager(config=self, builtin=True).discover([
            os.path.join(os.path.dirname(os.path.realpath(__file__)),
                         '..', 'plugins'),
            os.path.join(self.workdir, 'plugins')
        ])
        self.sys.plugins.rules['_any'][self.RULE_CHECKER
                                       ] = [None] + self.plugins.available()

        # Parse once (silently), to figure out which plugins to load...
        self.parse_config(None, '\n'.join(lines), source=filename)

        if len(self.sys.plugins) == 0:
            self.sys.plugins.extend(self.plugins.DEFAULT)
        self.load_plugins(session)

        # Now all the plugins are loaded, reset and parse again!
        self.reset_rules_from_source()
        self.parse_config(session, '\n'.join(lines), source=filename)

        # Open event log
        self.event_log = EventLog(self.data_directory('event_log',
                                                      mode='rw', mkdir=True),
                                  # FIXME: Disbled encryption for now
                                  lambda: False and self.prefs.obfuscate_index
                                  ).load()

        # Enable translations
        translation = self.get_i18n_translation(session)

        # Configure jinja2
        self.jinja_env = Environment(
            loader=MailpileJinjaLoader(self),
            autoescape=True,
            trim_blocks=True,
            extensions=['jinja2.ext.i18n', 'jinja2.ext.with_',
                        'jinja2.ext.do', 'jinja2.ext.autoescape',
                        'mailpile.jinjaextensions.MailpileCommand']
        )
        self.jinja_env.install_gettext_translations(translation,
                                                    newstyle=True)

        # Load VCards
        self.vcards = VCardStore(self, self.data_directory('vcards',
                                                           mode='rw',
                                                           mkdir=True))

    def reset_rules_from_source(self):
        self._lock.acquire()
        try:
            self.set_rules(self._rules_source)
            self.sys.plugins.rules['_any'][self.RULE_CHECKER
                                           ] = [None] + self.plugins.available()
        finally:
            self._lock.release()

    def load_plugins(self, session):
        self._lock.acquire()
        try:
            from mailpile.plugins import PluginManager
            plugin_list = set(PluginManager.REQUIRED + self.sys.plugins)
            for plugin in plugin_list:
                if plugin is not None:
                    session.ui.mark(_('Loading plugin: %s') % plugin)
                    self.plugins.load(plugin)
            session.ui.mark(_('Processing manifests'))
            self.plugins.process_manifests()
            self.prepare_workers(session)
        finally:
            self._lock.release()

    def save(self, *args, **kwargs):
        self._lock.acquire()
        try:
            self._unlocked_save(*args, **kwargs)
        finally:
            self._lock.release()

    def _unlocked_save(self):
        self._mkworkdir(None)
        newfile = '%s.new' % self.conffile
        fd = gpg_open(newfile, self.prefs.get('gpg_recipient'), 'wb')
        fd.write(self.as_config_bytes(private=True))
        fd.close()

        # Keep the last 5 config files around... just in case.
        backup_file(self.conffile, backups=5, min_age_delta=10)
        os.rename(newfile, self.conffile)

        self.get_i18n_translation()
        self.prepare_workers()

    def clear_mbox_cache(self):
        self._mbox_cache = {}

    def _find_mail_source(self, mbx_id):
        for src in self.sources.values():
            if mbx_id in src.mailbox:
                return src
        return None

    def get_mailboxes(self, standalone=True, mail_sources=False):
        def fmt_mbxid(k):
            k = b36(int(k, 36))
            if len(k) > MBX_ID_LEN:
                raise ValueError(_('Mailbox ID too large: %s') % k)
            return (('0' * MBX_ID_LEN) + k)[-MBX_ID_LEN:]
        mailboxes = [(fmt_mbxid(k),
                      self.sys.mailbox[k],
                      self._find_mail_source(k))
                     for k in self.sys.mailbox.keys()]

        if not standalone:
            mailboxes = [(i, p, s) for i, p, s in mailboxes if s]

        if mail_sources:
            for i in range(0, len(mailboxes)):
                mid, path, src = mailboxes[i]
                mailboxes[i] = (mid,
                                src and src.mailbox[mid].local or path,
                                src)
        else:
            mailboxes = [(i, p, s) for i, p, s in mailboxes if not s]

        mailboxes.sort()
        return mailboxes

    def is_editable_message(self, msg_info):
        for ptr in msg_info[MailIndex.MSG_PTRS].split(','):
            if not self.is_editable_mailbox(ptr[: MBX_ID_LEN]):
                return False
        editable = False
        for tid in msg_info[MailIndex.MSG_TAGS].split(','):
            try:
                if self.tags and self.tags[tid].flag_editable:
                    editable = True
            except (KeyError, AttributeError):
                pass
        return editable

    def is_editable_mailbox(self, mailbox_id):
        mailbox_id = ((mailbox_id is None and -1) or
                      (mailbox_id == '' and -1) or
                      int(mailbox_id, 36))
        local_mailbox_id = int(self.sys.get('local_mailbox_id', 'ZZZZZ'), 36)
        return (mailbox_id == local_mailbox_id)

    def load_pickle(self, pfn):
        with open(os.path.join(self.workdir, pfn), 'rb') as fd:
            if self.prefs.obfuscate_index:
                from mailpile.crypto.streamer import DecryptingStreamer
                with DecryptingStreamer(self.prefs.obfuscate_index,
                                        fd) as streamer:
                    return cPickle.loads(streamer.read())
            else:
                return cPickle.loads(fd.read())

    def save_pickle(self, obj, pfn):
        try:
            if self.prefs.obfuscate_index:
                from mailpile.crypto.streamer import EncryptingStreamer
                fd = EncryptingStreamer(self.prefs.obfuscate_index,
                                        dir=self.workdir)
                cPickle.dump(obj, fd, protocol=0)
                fd.save(os.path.join(self.workdir, pfn))
            else:
                fd = open(os.path.join(self.workdir, pfn), 'wb')
                cPickle.dump(obj, fd, protocol=0)
        finally:
            fd.close()

    def open_mailbox(self, session, mailbox_id, prefer_local=True):
        try:
            mbx_id = mailbox_id.lower()
            mfn = self.sys.mailbox[mbx_id]
            if prefer_local:
                src = self._find_mail_source(mbx_id)
                mfn = src and src.mailbox[mbx_id].local or mfn
            pfn = 'pickled-mailbox.%s' % mbx_id
        except KeyError:
            raise NoSuchMailboxError(_('No such mailbox: %s') % mbx_id)

        self._lock.acquire()
        try:
            if mbx_id not in self._mbox_cache:
                if session:
                    session.ui.mark(_('%s: Updating: %s') % (mbx_id, mfn))
                self._mbox_cache[mbx_id] = self.load_pickle(pfn)
            self._mbox_cache[mbx_id].update_toc()
        except KeyboardInterrupt:
            raise
        except:
            if self.sys.debug:
                import traceback
                traceback.print_exc()
            if session:
                session.ui.mark(_('%s: Opening: %s (may take a while)'
                                  ) % (mbx_id, mfn))
            editable = self.is_editable_mailbox(mbx_id)
            mbox = OpenMailbox(mfn, self, create=editable)
            mbox.editable = editable
            mbox.save(session,
                      to=pfn,
                      pickler=lambda o, f: self.save_pickle(o, f))
            self._mbox_cache[mbx_id] = mbox
        finally:
            self._lock.release()

        # Always set this, it can't be pickled
        self._mbox_cache[mbx_id]._encryption_key_func = \
            lambda: self.prefs.obfuscate_index

        return self._mbox_cache[mbx_id]

    def create_local_mailstore(self, session, name=None):
        self._lock.acquire()
        try:
            path = os.path.join(self.workdir, 'mail')
            if name is None:
                name = '%5.5x' % random.randint(0, 16**5)
                while os.path.exists(os.path.join(path, name)):
                    name = '%5.5x' % random.randint(0, 16**5)
            if name != '':
                path = os.path.join(path, name)

            mbx = wervd.MailpileMailbox(path)
            mbx._encryption_key_func = lambda: self.prefs.obfuscate_index
            return path, mbx
        finally:
            self._lock.release()

    def open_local_mailbox(self, session):
        self._lock.acquire()
        local_id = self.sys.get('local_mailbox_id', None)
        try:
            if not local_id:
                mailbox, mbx = self.create_local_mailstore(session, name='')
                local_id = self.sys.mailbox.append(mailbox)
                local_id = (('0' * MBX_ID_LEN) + local_id)[-MBX_ID_LEN:]
                self.sys.local_mailbox_id = local_id
            else:
                local_id = (('0' * MBX_ID_LEN) + local_id)[-MBX_ID_LEN:]
        finally:
            self._lock.release()
        return local_id, self.open_mailbox(session, local_id)

    def get_profile(self, email=None):
        find = email or self.prefs.get('default_email', None)
        default_profile = {
            'name': None,
            'email': find,
            'signature': None,
            'messageroute': self.prefs.default_messageroute
        }
        for profile in self.profiles:
            if profile.email == find or not find:
                if not email:
                    self.prefs.default_email = profile.email
                return dict_merge(default_profile, profile)
        return default_profile

    def get_sendmail(self, frm, rcpts=['-t']):
        if len(rcpts) == 1:
            if rcpts[0].lower().endswith('.onion'):
                return {"protocol": "smtorp",
                        "host": rcpts[0].split('@')[-1],
                        "port": 25,
                        "username": "",
                        "password": ""}
        routeid = self.get_profile(frm)['messageroute']
        if self.routes[routeid] is not None:
            return self.routes[routeid]
        else:
            print "Migration notice: Try running 'setup/migrate'."
            raise ValueError(_("Route %s does not exist.") % routeid)

    def data_directory(self, ftype, mode='rb', mkdir=False):
        """
        Return the path to a data directory for a particular type of file
        data, optionally creating the directory if it is missing.

        >>> p = cfg.data_directory('html_theme', mode='r', mkdir=False)
        >>> p == os.path.abspath('static/default')
        True
        """
        self._lock.acquire()
        try:
            # This should raise a KeyError if the ftype is unrecognized
            bpath = self.sys.path.get(ftype)
            if not bpath.startswith('/'):
                cpath = os.path.join(self.workdir, bpath)
                if os.path.exists(cpath) or 'w' in mode:
                    bpath = cpath
                    if mkdir and not os.path.exists(cpath):
                        os.mkdir(cpath)
                else:
                    bpath = os.path.join(os.path.dirname(__file__),
                                         '..', bpath)
            return os.path.abspath(bpath)
        finally:
            self._lock.release()

    def data_file_and_mimetype(self, ftype, fpath, *args, **kwargs):
        # The theme gets precedence
        core_path = self.data_directory(ftype, *args, **kwargs)
        path, mimetype = os.path.join(core_path, fpath), None

        # If there's nothing there, check our plugins
        if not os.path.exists(path):
            from mailpile.plugins import PluginManager
            path, mimetype = PluginManager().get_web_asset(fpath, path)

        if os.path.exists(path):
            return path, mimetype
        else:
            return None, None

    def history_file(self):
        return os.path.join(self.workdir, 'history')

    def mailindex_file(self):
        return os.path.join(self.workdir, 'mailpile.idx')

    def postinglist_dir(self, prefix):
        self._lock.acquire()
        try:
            d = os.path.join(self.workdir, 'search')
            if not os.path.exists(d):
                os.mkdir(d)
            d = os.path.join(d, prefix and prefix[0] or '_')
            if not os.path.exists(d):
                os.mkdir(d)
            return d
        finally:
            self._lock.release()

    def get_index(self, session):
        self._lock.acquire()
        try:
            if self.index:
                return self.index
            idx = MailIndex(self)
            idx.load(session)
            self.index = idx
            return idx
        finally:
            self._lock.release()

    def get_tor_socket(self):
        if socks:
            socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5,
                                  'localhost', 9050, True)
        return socks.socksocket

    def get_i18n_translation(self, session=None):
        self._lock.acquire()
        try:
            language = self.prefs.language
            trans = None
            if language != "":
                try:
                    trans = translation("mailpile", getLocaleDirectory(),
                                        [language], codeset="utf-8")
                except IOError:
                    if session:
                        session.ui.warning(('Failed to load language %s'
                                            ) % language)
            if not trans:
                trans = translation("mailpile", getLocaleDirectory(),
                                    codeset='utf-8', fallback=True)
                if session and isinstance(trans, NullTranslations):
                    session.ui.warning('Failed to configure i18n. '
                                       'Using fallback.')
            if trans:
                trans.set_output_charset("utf-8")
                trans.install(unicode=True)
            return trans
        finally:
            self._lock.release()

    def open_file(self, ftype, fpath, mode='rb', mkdir=False):
        if '..' in fpath:
            raise ValueError(_('Parent paths are not allowed'))
        fpath, mt = self.data_file_and_mimetype(ftype, fpath,
                                                mode=mode, mkdir=mkdir)
        if not fpath:
            raise IOError(2, 'Not Found')
        return fpath, open(fpath, mode), mt

    def prepare_workers(self, *args, **kwargs):
        self._lock.acquire()
        try:
            return self._unlocked_prepare_workers(*args, **kwargs)
        finally:
            self._lock.release()

    def _unlocked_prepare_workers(config, session=None, daemons=False):
        # Set globals from config first...
        import mailpile.util

        # Make sure we have a silent background session
        if not config.background:
            config.background = Session(config)
            config.background.ui = BackgroundInteraction(config)
            config.background.ui.block()

        # Start the workers
        if daemons:
            for src_id, src_config in config.sources.iteritems():
                if src_id not in config.mail_sources:
                    from mailpile.mail_source import MailSource
                    try:
                        config.mail_sources[src_id] = MailSource(
                            session or config.background, src_config)
                        config.mail_sources[src_id].start()
                    except ValueError:
                        traceback.print_exc()

            if config.slow_worker == config.dumb_worker:
                config.slow_worker = Worker('Slow worker', session)
                config.slow_worker.start()
            if not config.cron_worker:
                config.cron_worker = Cron('Cron worker', session)
                config.cron_worker.start()
            if not config.http_worker:
                # Start the HTTP worker if requested
                sspec = (config.sys.http_host, config.sys.http_port)
                if sspec[0].lower() != 'disabled' and sspec[1] >= 0:
                    config.http_worker = HttpWorker(session, sspec)
                    config.http_worker.start()
            if not config.other_workers:
                from mailpile.plugins import PluginManager
                for worker in PluginManager.WORKERS:
                    w = worker(session)
                    w.start()
                    config.other_workers.append(w)

        # Update the cron jobs, if necessary
        if config.cron_worker:
            session = session or config.background

            # Schedule periodic rescanning, if requested.
            rescan_interval = config.prefs.rescan_interval
            if rescan_interval:
                def rescan():
                    if 'rescan' not in config._running:
                        rsc = Rescan(session, 'rescan')
                        rsc.serialize = False
                        config.slow_worker.add_task(session, 'Rescan', rsc.run)
                config.cron_worker.add_task('rescan', rescan_interval, rescan)

            # Schedule plugin jobs
            from mailpile.plugins import PluginManager

            def interval(i):
                if isinstance(i, (str, unicode)):
                    i = config.walk(i)
                return int(i)

            def wrap_fast(func):
                def wrapped():
                    return func(session)
                return wrapped

            def wrap_slow(func):
                def wrapped():
                    config.slow_worker.add_task(session, job,
                                                lambda: func(session))
                return wrapped
            for job, (i, f) in PluginManager.FAST_PERIODIC_JOBS.iteritems():
                config.cron_worker.add_task(job, interval(i), wrap_fast(f))
            for job, (i, f) in PluginManager.SLOW_PERIODIC_JOBS.iteritems():
                config.cron_worker.add_task(job, interval(i), wrap_slow(f))

    def stop_workers(config):
        config._lock.acquire()
        try:
            for wait in (False, True):
                for w in ([config.http_worker,
                           config.slow_worker,
                           config.cron_worker] +
                          config.other_workers +
                          config.mail_sources.values()):
                    if w:
                        w.quit(join=wait)
            config.other_workers = []
            config.http_worker = config.cron_worker = None
            config.slow_worker = config.dumb_worker
        finally:
            config._lock.release()


##############################################################################

if __name__ == "__main__":
    import copy
    import doctest
    import sys
    import mailpile.config
    import mailpile.defaults
    import mailpile.plugins.tags
    import mailpile.ui

    rules = copy.deepcopy(mailpile.defaults.CONFIG_RULES)
    rules.update({
        'nest1': ['Nest1', {
            'nest2': ['Nest2', str, []],
            'nest3': ['Nest3', {
                'nest4': ['Nest4', str, []]
            }, []],
        }, {}]
    })
    cfg = mailpile.config.ConfigManager(rules=rules)
    session = mailpile.ui.Session(cfg)
    session.ui.block()

    for tries in (1, 2):
        # This tests that we can set (and reset) dicts of unnested objects
        cfg.tags = {}
        assert(cfg.tags.a is None)
        for tn in range(0, 11):
            cfg.tags.append({'name': 'Test Tag %s' % tn})
        assert(cfg.tags.a['name'] == 'Test Tag 10')

        # This tests the same thing for lists
        cfg.profiles = []
        assert(len(cfg.profiles) == 0)
        cfg.profiles.append({'name': 'Test Profile'})
        assert(len(cfg.profiles) == 1)
        assert(cfg.profiles[0].name == 'Test Profile')

        # This is the complicated one: multiple nesting layers
        cfg.nest1 = {}
        assert(cfg.nest1.a is None)
        cfg.nest1.a = {
            'nest2': ['hello', 'world'],
            'nest3': [{'nest4': ['Hooray']}]
        }
        cfg.nest1.b = {
            'nest2': ['hello', 'world'],
            'nest3': [{'nest4': ['Hooray', 'Bravo']}]
        }
        assert(cfg.nest1.a.nest3[0].nest4[0] == 'Hooray')
        assert(cfg.nest1.b.nest3[0].nest4[1] == 'Bravo')

    assert(cfg.sys.http_port ==
           mailpile.defaults.CONFIG_RULES['sys'][-1]['http_port'][-1])
    assert(cfg.sys.path.vcards == 'vcards')
    assert(cfg.walk('sys.path.vcards') == 'vcards')

    # Verify that the tricky nested stuff from above persists and
    # load/save doesn't change lists.
    for passes in (1, 2, 3):
        cfg2 = mailpile.config.ConfigManager(rules=rules)
        cfg2.parse_config(session, cfg.as_config_bytes())
        cfg.parse_config(session, cfg2.as_config_bytes())
        assert(cfg2.nest1.a.nest3[0].nest4[0] == 'Hooray')
        assert(cfg2.nest1.b.nest3[0].nest4[1] == 'Bravo')
        assert(len(cfg2.nest1) == 2)
        assert(len(cfg.nest1) == 2)
        assert(len(cfg.profiles) == 1)
        assert(len(cfg.tags) == 11)

    results = doctest.testmod(optionflags=doctest.ELLIPSIS,
                              extraglobs={'cfg': cfg,
                                          'session': session})
    print '%s' % (results, )
    if results.failed:
        sys.exit(1)

########NEW FILE########
__FILENAME__ = dnspka
import DNS
import urllib2

from mailpile.crypto.gpgi import GnuPG

#
#  Support for DNS PKA (_pka) entries.
#  See http://www.gushi.org/make-dns-cert/HOWTO.html
#

class DNSPKALookup:
	def __init__(self):
		DNS.ParseResolvConf()
		self.req = DNS.Request(qtype="TXT")

	def lookup(self, address):
		"""
		>>> from mailpile.crypto.dnspka import *
		>>> d = DNSPKALookup()
		>>> res = d.lookup("smari@immi.is")
		>>> res["result"]["count"] == 1
		"""
		dom = address.replace("@", "._pka.")
		result = self.req.req(dom)
		for res in result.answers:
			if res["typename"] != "TXT":
				continue
			for entry in res["data"]:
				return self._getkey(entry)

	def _getkey(self, entry):
		pkaver = None
		fingerprint = None
		url = None

		for stmt in entry.split(";"):
			key, value = stmt.split("=", 1)
			if key == "v":
				pkaver = value
			elif key == "fpr":
				fingerprint = value
			elif key == "uri":
				url = value

		if pkaver != "pka1":
			raise ValueError("We only know how to deal with pka version 1")

		if fingerprint and not url:
			g = GnuPG()
			res = g.recv_key(fingerprint)
		elif url:
			r = urllib2.urlopen(url)
			result = r.readlines()
			start = 0
			end = len(result)
			# Hack to deal with possible HTML results from keyservers:
			for i in range(len(result)):
				if result[i].startswith("-----BEGIN PGP"):
					start = i
				elif result[i].startswith("-----END PGP"):
					end = i
			result = "".join(result[start:end])
			g = GnuPG()
			res = g.import_keys(result)
			return res
		else:
			raise ValueError("Need a fingerprint or a URL")


########NEW FILE########
__FILENAME__ = gpgi
#coding:utf-8
import os
import string
import sys
import time
import re
import StringIO
import tempfile
import traceback
import select
from datetime import datetime
from email.parser import Parser
from email.message import Message
from gettext import gettext as _
from subprocess import Popen, PIPE
from threading import Thread

from mailpile.crypto.state import *
from mailpile.crypto.mime import MimeSigningWrapper, MimeEncryptingWrapper

DEFAULT_SERVER = "pool.sks-keyservers.net"
GPG_KEYID_LENGTH = 8
GNUPG_HOMEDIR = None  # None=use what gpg uses
BLOCKSIZE = 65536

openpgp_trust = {"-": _("Trust not calculated"),
                 "o": _("Unknown trust"),
                 "q": _("Undefined trust"),
                 "n": _("Never trust"),
                 "m": _("Marginally trust"),
                 "f": _("Full trust"),
                 "u": _("Ultimate trust"),
                 "e": _("Expired key, not trusted"),
                 "d": _("Disabled key, not trusted"),  # Deprecated flag.
                 "r": _("Revoked key, not trusted")}

openpgp_algorithms = {1: _("RSA"),
                      2: _("RSA (encrypt only)"),
                      3: _("RSA (sign only)"),
                      16: _("Elgamal (encrypt only)"),
                      17: _("DSA"),
                      20: _("Elgamal (encrypt/sign) [COMPROMISED]")}
# For details on type 20 compromisation, see
# http://lists.gnupg.org/pipermail/gnupg-announce/2003q4/000160.html

class GnuPGResultParser:
    """
    Parse the GPG response into EncryptionInfo and SignatureInfo.
    """
    def __init__(rp):
        rp.signature_info = SignatureInfo()
        rp.signature_info["protocol"] = "openpgp"

        rp.encryption_info = EncryptionInfo()
        rp.encryption_info["protocol"] = "openpgp"

        rp.plaintext = ""

    def parse(rp, retvals):
        signature_info = rp.signature_info
        encryption_info = rp.encryption_info
        from mailpile.mailutils import ExtractEmailAndName

        # First pass, set some initial state.
        for data in retvals[1]["status"]:
            keyword = data[0].strip()
            if keyword == "DECRYPTION_FAILED":
                missing = [x[1] for x in retvals[1]["status"]
                           if x[0] == "NO_SECKEY"]
                if missing:
                    encryption_info["status"] = "missingkey"
                    encryption_info["missing_keys"] = missing
                else:
                    encryption_info["status"] = "error"

            elif keyword == "DECRYPTION_OKAY":
                encryption_info["status"] = "decrypted"
                rp.plaintext = "".join(retvals[1]["stdout"])

            elif keyword == "ENC_TO":
                keylist = encryption_info.get("have_keys", [])
                if data[0] not in keylist:
                    keylist.append(data[1])
                encryption_info["have_keys"] = keylist

            elif signature_info["status"] == "none":
                # Only one of these will ever be emitted per key, use
                # this to set initial state. We may end up revising
                # the status depending on more info later.
                if keyword in ("GOODSIG", "BADSIG"):
                    email, fn = ExtractEmailAndName(
                        " ".join(data[2:]).decode('utf-8'))
                    signature_info["name"] = fn
                    signature_info["email"] = email
                    signature_info["status"] = ((keyword == "GOODSIG")
                                                and "unverified"
                                                or "invalid")
                elif keyword == "ERRSIG":
                    signature_info["status"] = "error"
                    signature_info["keyinfo"] = data[1]
                    signature_info["timestamp"] = int(data[5])

        # Second pass, this may update/mutate the state set above
        for data in retvals[1]["status"]:
            keyword = data[0]

            if keyword == "NO_SECKEY":
                if "missing_keys" not in encryption_info:
                    encryption_info["missing_keys"] = [data[1]]
                else:
                    encryption_info["missing_keys"].append(data[1])
                try:
                    encryption_info["have_keys"].remove(data[1])
                except (KeyError, ValueError):
                    pass

            elif keyword == "VALIDSIG":
                # FIXME: Determine trust level, between new, unverified,
                #        verified, untrusted.
                signature_info["keyinfo"] = data[1]
                signature_info["timestamp"] = int(data[3])

            elif keyword in ("EXPKEYSIG", "REVKEYSIG"):
                email, fn = ExtractEmailAndName(
                    " ".join(data[2:]).decode('utf-8'))
                signature_info["name"] = fn
                signature_info["email"] = email
                signature_info["status"] = ((keyword == "EXPKEYSIG")
                                            and "expired"
                                            or "revoked")

          # FIXME: This appears to be spammy. Is my key borked, or
          #        is GnuPG being stupid?
          #
          # elif keyword == "KEYEXPIRED":  # Ignoring: SIGEXPIRED
          #     signature_info["status"] = "expired"
            elif keyword == "KEYREVOKED":
                signature_info["status"] = "revoked"
            elif keyword == "NO_PUBKEY":
                signature_info["status"] = "unknown"

            elif keyword in ["TRUST_ULTIMATE", "TRUST_FULLY"]:
                if signature_info["status"] == "unverified":
                    signature_info["status"] = "verified"

        return rp

class GnuPGRecordParser:
    def __init__(self):
        self.keys = {}
        self.curkey = None

        self.record_fields = ["record", "validity", "keysize", "keytype", 
                              "keyid", "creation_date", "expiration_date", 
                              "uidhash", "ownertrust", "uid", "sigclass", 
                              "capabilities", "flag", "sn", "hashtype", "curve"]
        self.record_types = ["pub", "sub", "ssb", "fpr", "uat", "sec", "tru", 
                             "sig", "rev", "uid", "gpg"]
        self.record_parsers = [self.parse_pubkey, self.parse_subkey, 
                          self.parse_subkey, self.parse_fingerprint,
                          self.parse_userattribute, self.parse_privkey, 
                          self.parse_trust, self.parse_signature, 
                          self.parse_revoke, self.parse_uidline, self.parse_none]

        self.dispatch = dict(zip(self.record_types, self.record_parsers))

    def parse(self, lines):
        for line in lines:
            self.parse_line(line)
        return self.keys

    def parse_line(self, line):
        line = dict(zip(self.record_fields, line.strip().split(":")))
        r = self.dispatch.get(line["record"], self.parse_unknown)
        r(line)

    def parse_pubkey(self, line):
        self.curkey = line["keyid"]
        line["keytype_name"] = openpgp_algorithms[int(line["keytype"])]
        line["capabilities_map"] = {
            "encrypt": "E" in line["capabilities"],
            "sign": "S" in line["capabilities"],
            "certify": "C" in line["capabilities"],
            "authenticate": "A" in line["capabilities"],
        },
        line["disabled"] = "D" in line["capabilities"]
        line["private_key"] = False
        line["subkeys"] = []
        line["uids"] = []

        if line["record"] == "sec":
            line["secret"] = True

        self.keys[self.curkey] = line
        self.parse_uidline(line)

    def parse_subkey(self, line):
        subkey = {"id": line["keyid"], "keysize": line["keysize"],
                  "creation_date": line["creation_date"],
                  "keytype_name": openpgp_algorithms[int(line["keytype"])]}
        self.keys[self.curkey]["subkeys"].append(subkey)

    def parse_fingerprint(self, line):
        self.keys[self.curkey]["fingerprint"] = line["keyid"]

    def parse_userattribute(self, line):
        # TODO: We are currently ignoring user attributes as not useful.
        #       We may at some point want to use --attribute-fd and read
        #       in user photos and such?
        pass

    def parse_privkey(self, line):
        self.parse_pubkey(line)

    def parse_uidline(self, line):
        email, name, comment = parse_uid(line["uid"])
        self.keys[self.curkey]["uids"].append({"email": email,
                                     "name": name,
                                     "comment": comment,
                                     "creation_date": line["creation_date"]})

    def parse_trust(self, line):
        # TODO: We are currently ignoring commentary from the Trust DB.
        pass

    def parse_signature(self, line):
        if "signatures" not in self.keys[self.curkey]:
            self.keys[self.curkey]["signatures"] = []
        sig = {"signer": line[9], "signature_date": line[5],
               "keyid": line[4], "trust": line[10], "keytype": line[4]}

        self.keys[self.curkey]["signatures"].append(sig)

    def parse_revoke(self, line):
        # FIXME: Do something more to this
        print line

    def parse_unknown(self, line):
        print "Unknown line with code '%s'" % line[0]

    def parse_none(line):
        pass

UID_PARSE_RE = "([^\(\<]+){0,1}( \((.+)\)){0,1} (\<(.+)\>){0,1}"
def parse_uid(uidstr):
    matches = re.match(UID_PARSE_RE, uidstr)
    if matches:
        email = matches.groups(0)[4] or ""
        comment = matches.groups(0)[2] or ""
        name = matches.groups(0)[0] or ""
    else:
        email = uidstr
        name = ""
        comment = ""

    try:
        name = name.decode("utf-8")
    except UnicodeDecodeError:
        try:
            name = name.decode("iso-8859-1")
        except UnicodeDecodeError:
            name = name.decode("utf-8", "replace")

    try:
        comment = comment.decode("utf-8")
    except UnicodeDecodeError:
        try:
            comment = comment.decode("iso-8859-1")
        except UnicodeDecodeError:
            comment = comment.decode("utf-8", "replace")

    return email, name, comment

class StreamReader(Thread):
    def __init__(self, fd, callback, lines=True):
        Thread.__init__(self, target=self.readin, args=(fd, callback))
        self.lines = lines
        self.start()

    def readin(self, fd, callback):
        try:
            if self.lines:
                for line in iter(fd.readline, b''):
                    callback(line)
            else:
                while True:
                    buf = fd.read(BLOCKSIZE)
                    callback(buf)
                    if buf == "":
                        break
        except:
            traceback.print_exc()
        finally:
            fd.close()

class StreamWriter(Thread):
    def __init__(self, fd, output):
        Thread.__init__(self, target=self.writeout, args=(fd, output))
        self.start()

    def writeout(self, fd, output):
        if isinstance(output, (str, unicode)):
            output = StringIO.StringIO(output)
        try:
            while True:
                line = output.read(BLOCKSIZE)
                if line == "":
                    break
                fd.write(line)
            output.close()
        except:
            traceback.print_exc()
        finally:
            fd.close()

class GnuPG:
    """
    Wrap GnuPG and make all functionality feel Pythonic.
    """
    def __init__(self):
        self.available = None
        self.gpgbinary = 'gpg'
        self.passphrase = None
        self.outputfds = ["stdout", "stderr", "status"]
        self.errors = []
        self.homedir = None

    def set_home(self, path):
        self.homedir = path

    def version(self):
        retvals = self.run(["--version"])
        return retvals[1]["stdout"][0].split('\n')[0]

    def is_available(self):
        try:
            retvals = self.run(["--version"])
            self.available = True
        except OSError:
            self.available = False

        return self.available

    def run(self, args=[], output=None, outputfd=None):
        self.outputbuffers = dict([(x, []) for x in self.outputfds])
        self.pipes = {}
        args.insert(0, self.gpgbinary)
        args.insert(1, "--utf8-strings")
        args.insert(1, "--with-colons")
        args.insert(1, "--verbose")
        args.insert(1, "--batch")
        args.insert(1, "--enable-progress-filter")

        if self.homedir:
            args.insert(1, "--homedir=%s" % self.homedir)

        self.statuspipe = os.pipe()
        self.status = os.fdopen(self.statuspipe[0], "r")
        args.insert(1, "--status-fd")
        args.insert(2, "%d" % self.statuspipe[1])
        if self.passphrase:
            self.passphrase_pipe = os.pipe()
            self.passphrase_handle = os.fdopen(self.passphrase_pipe[1], "w")
            args.insert(1, "--passphrase-fd")
            args.insert(2, "%d" % self.statuspipe[0])

        proc = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE, 
            bufsize=1, close_fds=False)

        self.threads = {
            "stderr": StreamReader(proc.stderr, self.parse_stderr),
            "status": StreamReader(self.status, self.parse_status),
        }
        if self.passphrase:
            self.threads["passphrase"] = StreamWriter(self.passphrase_handle, 
                                                      self.passphrase)

        if outputfd:
            self.threads["stdout"] = StreamReader(proc.stdout, outputfd.write,
                                                  lines=False)
        else:
            self.threads["stdout"] = StreamReader(proc.stdout,
                                                  self.parse_stdout)

        if output:
            # If we have output, we just stream it. Technically, this
            # doesn't really need to be a thread at the moment.
            StreamWriter(proc.stdin, output).join()
        else:
            proc.stdin.close()

        # Reap GnuPG
        proc.wait()

        # Close our pipes so the threads finish
        os.close(self.statuspipe[1])
        if self.passphrase:
            os.close(self.passphrase_pipe[1])

        # Reap the threads
        for name, thr in self.threads.iteritems():
            thr.join()

        if outputfd:
            outputfd.close()

        return proc.returncode, self.outputbuffers

    def parse_status(self, line, *args):
        line = line.replace("[GNUPG:] ", "")
        if line == "":
            return
        elems = line.split(" ")
        self.outputbuffers["status"].append(elems)

    def parse_stdout(self, line):
        self.outputbuffers["stdout"].append(line)

    def parse_stderr(self, line):
        self.outputbuffers["stderr"].append(line)

    def parse_keylist(self, keylist):
        rlp = GnuPGRecordParser()
        return rlp.parse(keylist)

    def list_keys(self):
        """
        >>> g = GnuPG()
        >>> g.list_keys()[0]
        0
        """
        retvals = self.run(["--list-keys", "--fingerprint"])
        return self.parse_keylist(retvals[1]["stdout"])

    def list_secret_keys(self):
        #
        # Note: The "." parameter that is passed is to work around a bug
        #       in GnuPG < 2.1, where --list-secret-keys does not list
        #       details about key capabilities or expiry for 
        #       --list-secret-keys unless a selector is provided. A dot
        #       is reasonably likely to appear in all PGP keys, as it is
        #       a common component of e-mail addresses (and @ does not
        #       work as a selector for some reason...)
        #
        #       The downside of this workaround is that keys with no e-mail
        #       address or an address like alice@localhost won't be found.
        #       Therefore, this paramter should be removed when GnuPG >= 2.1
        #       becomes commonplace.
        #
        #       (This is a better workaround than doing an additional 
        #       --list-keys and trying to aggregate it though...)
        #
        retvals = self.run(["--list-secret-keys", ".", "--fingerprint"])
        return self.parse_keylist(retvals[1]["stdout"])

    def import_keys(self, key_data=None):
        """
        Imports gpg keys from a file object or string.
        >>> key_data = open("testing/pub.key").read()
        >>> g = GnuPG()
        >>> g.import_keys(key_data)
        {'failed': [], 'updated': [{'details_text': 'unchanged', 'details': 0, 'fingerprint': '08A650B8E2CBC1B02297915DC65626EED13C70DA'}], 'imported': [], 'results': {'sec_dups': 0, 'unchanged': 1, 'num_uids': 0, 'skipped_new_keys': 0, 'no_userids': 0, 'num_signatures': 0, 'num_revoked': 0, 'sec_imported': 0, 'sec_read': 0, 'not_imported': 0, 'count': 1, 'imported_rsa': 0, 'imported': 0, 'num_subkeys': 0}}
        """
        retvals = self.run(["--import"], output=key_data)
        return self.parse_import(retvals[1]["status"])

    def decrypt(self, data, outputfd=None, passphrase=None, as_lines=False):
        """
        Note that this test will fail if you don't replace the recipient with
        one whose key you control.
        >>> g = GnuPG()
        >>> ct = g.encrypt("Hello, World", to=["smari@mailpile.is"])[1]
        >>> g.decrypt(ct)["text"]
        'Hello, World'
        """
        if passphrase:
            self.passphrase = passphrase
        action = ["--decrypt"]
        retvals = self.run(action, output=data, outputfd=outputfd)
        self.passphrase = None

        if as_lines:
            as_lines = retvals[1]["stdout"]
            retvals[1]["stdout"] = []

        rp = GnuPGResultParser().parse(retvals)

        return (rp.signature_info, rp.encryption_info,
                as_lines or rp.plaintext)

    def verify(self, data, signature=None):
        """
        >>> g = GnuPG()
        >>> s = g.sign("Hello, World", _from="smari@mailpile.is",
            clearsign=True)[1]
        >>> g.verify(s)
        """
        params = ["--verify"]
        if signature:
            sig = tempfile.NamedTemporaryFile()
            sig.write(signature)
            sig.flush()
            params.append(sig.name)
            params.append("-")

        ret, retvals = self.run(params, output=data)

        return GnuPGResultParser().parse([None, retvals]).signature_info

    def encrypt(self, data, tokeys=[], armor=True):
        """
        >>> g = GnuPG()
        >>> g.encrypt("Hello, World", to=["smari@mailpile.is"])[0]
        0
        """
        action = ["--encrypt", "--yes", "--expert", "--trust-model", "always"]
        if armor:
            action.append("--armor")
        for r in tokeys:
            action.append("--recipient")
            action.append(r)
        retvals = self.run(action, output=data)
        return retvals[0], "".join(retvals[1]["stdout"])

    def sign(self, data,
             fromkey=None, armor=True, detatch=True, clearsign=False,
             passphrase=None):
        """
        >>> g = GnuPG()
        >>> g.sign("Hello, World", fromkey="smari@mailpile.is")[0]
        0
        """
        if passphrase:
            self.passphrase = passphrase
        if detatch and not clearsign:
            action = ["--detach-sign"]
        elif clearsign:
            action = ["--clearsign"]
        else:
            action = ["--sign"]
        if armor:
            action.append("--armor")
        if fromkey:
            action.append("--local-user")
            action.append(fromkey)

        retvals = self.run(action, output=data)
        self.passphrase = None
        return retvals[0], retvals[1]["stdout"][0]

    def sign_encrypt(self, data, fromkey=None, tokeys=[], armor=True,
                     detatch=False, clearsign=True):
        retval, signblock = self.sign(data, fromkey=fromkey, armor=armor,
                                      detatch=detatch, clearsign=clearsign)
        if detatch:
            # TODO: Deal with detached signature.
            retval, cryptblock = self.encrypt(data, tokeys=tokeys,
                                              armor=armor)
        else:
            retval, cryptblock = self.encrypt(signblock, tokeys=tokeys,
                                              armor=armor)

        return cryptblock

    def sign_key(self, keyid, signingkey=None):
        action = ["--yes", "--sign-key", keyid]
        if signingkey:
            action.insert(1, "-u")
            action.insert(2, signingkey)
        retvals = self.run(action)
        return retvals

    def recv_key(self, keyid, keyserver=DEFAULT_SERVER):
        retvals = self.run(['--keyserver', keyserver, '--recv-key', keyid])
        return self.parse_import(retvals[1]["status"])

    def search_key(self, term, keyserver=DEFAULT_SERVER):
        retvals = self.run(['--keyserver', keyserver,
                            '--search-key', self._escape_hex_keyid_term(term)]
                            )[1]["stdout"]
        results = {}
        lines = [x.strip().split(":") for x in retvals]
        curpub = None
        for line in lines:
            if line[0] == "info":
                pass
            elif line[0] == "pub":
                curpub = line[1]
                results[curpub] = {"created": datetime.fromtimestamp(int(line[4])),
                                   "keytype_name": openpgp_algorithms[int(line[2])],
                                   "keysize": line[3],
                                   "uids": []}
            elif line[0] == "uid":
                email, name, comment = parse_uid(line[1])
                results[curpub]["uids"].append({"name": name,
                                                "email": email,
                                                "comment": comment})
        return results

    def address_to_keys(self, address):
        res = {}
        keys = self.list_keys()
        for key, props in keys.iteritems():
            if any([x["email"] == address for x in props["uids"]]):
                res[key] = props

        return res

    def _escape_hex_keyid_term(self, term):
        """Prepends a 0x to hexadecimal key ids, e.g. D13C70DA is converted to 0xD13C70DA.

            This is necessary because version 1 and 2 of GnuPG show a different behavior here,
            version 1 allows to search without 0x while version 2 requires 0x in front of the key id.
        """
        is_hex_keyid = False
        if len(term) == GPG_KEYID_LENGTH or len(term) == 2*GPG_KEYID_LENGTH:
            hex_digits = set(string.hexdigits)
            is_hex_keyid = all(c in hex_digits for c in term)

        if is_hex_keyid:
            return '0x%s' % term
        else:
            return term

def GetKeys(gnupg, config, people):
    keys = []
    missing = []

    # First, we go to the contact database and get a list of keys.
    for person in set(people):
        if '#' in person:
            keys.append(person.rsplit('#', 1)[1])
        else:
            vcard = config.vcards.get_vcard(person)
            if vcard:
                # FIXME: Rather than get_all, we should give the vcard the
                #        option of providing us with its favorite key.
                lines = [vcl for vcl in vcard.get_all('KEY')
                         if vcl.value.startswith('data:application'
                                                 '/x-pgp-fingerprint,')]
                if len(lines) == 1:
                    keys.append(lines[0].value.split(',', 1)[1])
                else:
                    missing.append(person)
            else:
                missing.append(person)

    # FIXME: This doesn't really feel scalable...
    all_keys = gnupg.list_keys()
    for key in all_keys.values():
        for uid in key["uids"]:
            if uid["email"] in missing:
                missing.remove(uid["email"])
                keys.append(key["fingerprint"])

    # Next, we go make sure all those keys are really in our keychain.
    fprints = [k["fingerprint"] for k in all_keys.values()]
    for key in keys:
        if key not in keys and key not in fprints:
            missing.append(key)

    if missing:
        raise KeyLookupError(_('Keys missing or ambiguous for %s'
                               ) % ', '.join(missing), missing)
    return keys

class OpenPGPMimeSigningWrapper(MimeSigningWrapper):
    CRYPTO_CLASS = GnuPG
    CONTAINER_PARAMS = (('micalg', 'pgp-sha1'),
                        ('protocol', 'application/pgp-signature'))
    SIGNATURE_TYPE = 'application/pgp-signature'
    SIGNATURE_DESC = 'OpenPGP Digital Signature'

    def get_keys(self, who):
        return GetKeys(self.crypto, self.config, who)

class OpenPGPMimeEncryptingWrapper(MimeEncryptingWrapper):
    CRYPTO_CLASS = GnuPG
    CONTAINER_PARAMS = (('protocol', 'application/pgp-encrypted'), )
    ENCRYPTION_TYPE = 'application/pgp-encrypted'
    ENCRYPTION_VERSION = 1

    def get_keys(self, who):
        return GetKeys(self.crypto, self.config, who)

########NEW FILE########
__FILENAME__ = mime
# These are methods to do with MIME and crypto, implementing PGP/MIME.

import re
import StringIO
import email.parser

from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase

from mailpile.crypto.state import EncryptionInfo, SignatureInfo
from mailpile.mail_generator import Generator

##[ Common utilities ]#########################################################

def Normalize(payload):
    return re.sub(r'\r?\n', '\r\n', payload)


class EncryptionFailureError(ValueError):
    pass


class SignatureFailureError(ValueError):
    pass


##[ Methods for unwrapping encrypted parts ]###################################

def UnwrapMimeCrypto(part, protocols=None, si=None, ei=None):
    """
    This method will replace encrypted and signed parts with their
    contents and set part attributes describing the security properties
    instead.
    """
    part.signature_info = si or SignatureInfo()
    part.encryption_info = ei or EncryptionInfo()
    mimetype = part.get_content_type()
    if part.is_multipart():

        # FIXME: Check the protocol. PGP? Something else?
        # FIXME: This is where we add hooks for other MIME encryption
        #        schemes, so route to callbacks by protocol.
        crypto_cls = protocols['openpgp']

        if mimetype == 'multipart/signed':
            try:
                gpg = crypto_cls()
                boundary = part.get_boundary()
                payload, signature = part.get_payload()

                # The Python get_payload() method likes to rewrite headers,
                # which breaks signature verification. So we manually parse
                # out the raw payload here.
                head, raw_payload, junk = part.as_string(
                    ).replace('\r\n', '\n').split('\n--%s\n' % boundary, 2)

                part.signature_info = gpg.verify(
                    Normalize(raw_payload), signature.get_payload())

                # Reparent the contents up, removing the signature wrapper
                part.set_payload(payload.get_payload())
                for h in payload.keys():
                    del part[h]
                for h, v in payload.items():
                    part.add_header(h, v)

                # Try again, in case we just unwrapped another layer
                # of multipart/something.
                return UnwrapMimeCrypto(part,
                                        protocols=protocols,
                                        si=part.signature_info,
                                        ei=part.encryption_info)

            except (IOError, OSError, ValueError, IndexError, KeyError):
                part.signature_info = SignatureInfo()
                part.signature_info["status"] = "error"

        elif mimetype == 'multipart/encrypted':
            try:
                gpg = crypto_cls()
                preamble, payload = part.get_payload()

                (part.signature_info, part.encryption_info, decrypted
                 ) = gpg.decrypt(payload.as_string())
            except (IOError, OSError, ValueError, IndexError, KeyError):
                part.encryption_info = EncryptionInfo()
                part.encryption_info["status"] = "error"

            if part.encryption_info['status'] == 'decrypted':
                newpart = email.parser.Parser().parse(
                    StringIO.StringIO(decrypted))

                # Reparent the contents up, removing the encryption wrapper
                part.set_payload(newpart.get_payload())
                for h in newpart.keys():
                    del part[h]
                for h, v in newpart.items():
                    part.add_header(h, v)

                # Try again, in case we just unwrapped another layer
                # of multipart/something.
                return UnwrapMimeCrypto(part,
                                        protocols=protocols,
                                        si=part.signature_info,
                                        ei=part.encryption_info)

        # If we are still multipart after the above shenanigans, recurse
        # into our subparts and unwrap them too.
        if part.is_multipart():
            for subpart in part.get_payload():
                UnwrapMimeCrypto(subpart,
                                 protocols=protocols,
                                 si=part.signature_info,
                                 ei=part.encryption_info)

    else:
        # FIXME: This is where we would handle cryptoschemes that don't
        #        appear as multipart/...
        pass


##[ Methods for encrypting and signing ]#######################################

class MimeWrapper:
    CONTAINER_TYPE = 'multipart/mixed'
    CONTAINER_PARAMS = ()
    CRYTPO_CLASS = None

    def __init__(self, config, cleaner=None, sender=None, recipients=None):
        self.config = config
        self.crypto = self.CRYPTO_CLASS()
        self.sender = sender
        self.cleaner = cleaner
        self.recipients = recipients or []
        self.container = MIMEMultipart()
        self.container.set_type(self.CONTAINER_TYPE)
        for pn, pv in self.CONTAINER_PARAMS:
            self.container.set_param(pn, pv)

    def attach(self, part):
        self.container.attach(part)
        if self.cleaner:
            self.cleaner(part)
        del part['MIME-Version']
        return self

    def get_keys(self, people):
        return people

    def flatten(self, msg, unixfrom=False):
        buf = StringIO.StringIO()
        Generator(buf).flatten(msg, unixfrom=unixfrom, linesep='\r\n')
        return buf.getvalue()

    def wrap(self, msg):
        for h in msg.keys():
            hl = h.lower()
            if not hl.startswith('content-') and not hl.startswith('mime-'):
                self.container[h] = msg[h]
                del msg[h]
        return self.container


class MimeSigningWrapper(MimeWrapper):
    CONTAINER_TYPE = 'multipart/signed'
    CONTAINER_PARAMS = ()
    SIGNATURE_TYPE = 'application/x-signature'
    SIGNATURE_DESC = 'Abstract Digital Signature'

    def __init__(self, *args, **kwargs):
        MimeWrapper.__init__(self, *args, **kwargs)

        self.sigblock = MIMEBase(*self.SIGNATURE_TYPE.split('/'))
        self.sigblock.set_param("name", "signature.asc")
        for h, v in (("Content-Description", self.SIGNATURE_DESC),
                     ("Content-Disposition",
                      "attachment; filename=\"signature.asc\"")):
            self.sigblock.add_header(h, v)

    def wrap(self, msg):
        MimeWrapper.wrap(self, msg)
        self.attach(msg)
        self.attach(self.sigblock)

        message_text = Normalize(self.flatten(msg))
        from_key = self.get_keys([self.sender])[0]
        status, sig = self.crypto.sign(message_text,
                                       fromkey=from_key, armor=True)
        if status == 0:
            self.sigblock.set_payload(sig)
            return self.container
        else:
            raise SignatureFailureError(_('Failed to sign message!'))


class MimeEncryptingWrapper(MimeWrapper):
    CONTAINER_TYPE = 'multipart/encrypted'
    CONTAINER_PARAMS = ()
    ENCRYPTION_TYPE = 'application/x-encrypted'
    ENCRYPTION_VERSION = 0

    def __init__(self, *args, **kwargs):
        MimeWrapper.__init__(self, *args, **kwargs)

        self.version = MIMEBase(*self.ENCRYPTION_TYPE.split('/'))
        self.version.set_payload('Version: %s\n' % self.ENCRYPTION_VERSION)
        for h, v in (("Content-Disposition", "attachment"), ):
            self.version.add_header(h, v)

        self.enc_data = MIMEBase('application', 'octet-stream')
        for h, v in (("Content-Disposition",
                      "attachment; filename=\"msg.asc\""), ):
            self.enc_data.add_header(h, v)

        self.attach(self.version)
        self.attach(self.enc_data)

    def wrap(self, msg):
        MimeWrapper.wrap(self, msg)

        del msg['MIME-Version']
        if self.cleaner:
            self.cleaner(msg)
        message_text = Normalize(self.flatten(msg))

        to_keys = set(self.get_keys(self.recipients + [self.sender]))
        status, enc = self.crypto.encrypt(message_text,
                                          tokeys=to_keys, armor=True)
        if status == 0:
            self.enc_data.set_payload(enc)
            return self.container
        else:
            raise EncryptionFailureError(_('Failed to sign message!'))

########NEW FILE########
__FILENAME__ = nicknym
#coding:utf-8

# from mailpile.crypto.state import *
from mailpile.crypto.gpgi import GnuPG

import httplib
import re
import socket
import sys
import urllib
import urllib2
import ssl
import json

# TODO:
# * SSL certificate validation
# * Check nicknym server for a given host
# * Store provider keys on first discovery
# * Verify provider key signature


class Nicknym:
	def __init__(self, config):
		self.config = config

	def get_key(self, address, keytype="openpgp", server=None):
		"""
		Request a key for address.
		"""
		result, signature = self._nickserver_get_key(address, keytype, server)
		if self._verify_result(result, signature):
			return self._import_key(result, keytype)
		return False

	def refresh_keys(self):
		"""
		Refresh all known keys.
		"""
		for addr, keytype in self._get_managed_keys():
			result, signature = self._nickserver_get_key(addr, keytype)
			# TODO: Check whether it needs refreshing and is valid
			if self._verify_result(result, signature):
				self._import_key(result, keytype)

	def send_key(self, address, public_key, type):
		"""
		Send a new key to the nickserver
		"""
		# TODO: Unimplemented. There is currently no authentication mechanism
		#       defined in Nicknym standard
		raise NotImplementedError()


	def _parse_result(self, result):
		"""Parse the result into a JSON blob and a signature"""
		# TODO: No signature implemented on server side yet.
		#       See https://leap.se/code/issues/5340
		return json.loads(result), ""

	def _nickserver_get_key(self, address, keytype="openpgp", server=None):
		if server == None: server = self._discover_server(address)

		data = urllib.urlencode({"address": address})
		r = urllib2.urlopen(server, data)
		result = r.read()
		result, signature = self._parse_result(result)
		return result, signature

	def _import_key(self, result, keytype):
		if keytype == "openpgp":
			g = GnuPG()
			res = g.import_keys(result[keytype])
			if len(res["updated"]):
				self._managed_keys_add(result["address"], keytype)
			return res
		else:
			# We currently only support OpenPGP keys
			return False

	def _get_providerkey(self, domain):
		"""
		Request a provider key for the appropriate domain.
		This is equivalent to get_key() with address=domain,
		except it should store the provider key in an 
		appropriate key store
		"""
		pass

	def _verify_providerkey(self, domain):
		"""
		...
		"""
		pass

	def _verify_result(self, result, signature):
		"""
		Verify that the JSON result blob is correctly signed,
		and that the signature is from the correct provider key.
		"""
		# No signature. See https://leap.se/code/issues/5340
		return True

	def _discover_server(self, address):
		"""
		Automatically detect which nicknym server to query
		based on the address.
		"""
		# TODO: Actually perform some form of lookup
		addr = address.split("@")
		addr.reverse()
		domain = addr[0]
		return "https://nicknym.%s:6425/" % domain

	def _audit_key(self, address, keytype, server):
		"""
		Ask an alternative server for a key to verify that
		the same result is being provided.
		"""
		result, signature = self._nickserver_get_key(address, keytype, server)
		if self._verify_result(result, signature):
			# TODO: verify that the result is acceptable
			pass
		return True

	def _managed_keys_add(self, address, keytype):
		try:
			data = self.config.load_pickle("nicknym.cache")
		except IOError:
			data = []
		data.append((address, keytype))
		data = list(set(data))
		self.config.save_pickle(data, "nicknym.cache")

	def _managed_keys_remove(self, address, keytype):
		try:
			data = self.config.load_pickle("nicknym.cache")
		except IOError:
			data = []
		data.remove((address, keytype))
		self.config.save_pickle(data, "nicknym.cache")

	def _get_managed_keys(self):
		try:
			return self.config.load_pickle("nicknym.cache")
		except IOError:
			return []



if __name__ == "__main__":
	n = Nicknym()
	print n.get_key("varac@bitmask.net")

########NEW FILE########
__FILENAME__ = state
# Common crypto state and structure


class KeyLookupError(ValueError):
    def __init__(self, message, missing):
        ValueError.__init__(self, message)
        self.missing = missing


STATE_CONTEXT_ID = 0


def NewContextID():
    global STATE_CONTEXT_ID
    context = STATE_CONTEXT_ID
    STATE_CONTEXT_ID += 1
    STATE_CONTEXT_ID %= 1000
    return context


class CryptoInfo(dict):
    """Base class for crypto-info classes"""
    KEYS = ["protocol", "context", "status", "description"]
    STATUSES = ["none", "mixed-error", "error"]
    DEFAULTS = {"status": "none"}

    def __init__(self, copy=None):
        self.update(copy or self.DEFAULTS)
        self["context"] = NewContextID()

    def __setitem__(self, item, value):
        assert(item in self.KEYS)
        if item == "status":
            assert(value in self.STATUSES)
        dict.__setitem__(self, item, value)

    def mix(self, ci):
        """
        This generates a mixed state for the message. The most exciting state
        is returned/explained, the status prfixed with "mixed-". How exciting
        states are, is determined by the order of the STATUSES attribute.

        Yes, this is a bit dumb.
        """
        if ci["status"] == "none":
            return
        elif (self.STATUSES.index(self["status"])
                < self.STATUSES.index(ci["status"])):
            for k in self.keys():
                del self[k]
            context = self.get("context") or NewContextID()
            self.update(ci)
            if not ci["status"].startswith('mixed-'):
                self["status"] = "mixed-%s" % ci["status"]
                self["context"] = context
        elif self["status"] != "none":
            self["status"] = 'mixed-%s' % self["status"]


class EncryptionInfo(CryptoInfo):
    """Contains information about the encryption status of a MIME part"""
    KEYS = (CryptoInfo.KEYS + ["have_keys", "missing_keys"])
    STATUSES = (CryptoInfo.STATUSES +
                ["mixed-decrypted", "decrypted",
                 "mixed-missingkey", "missingkey"])


class SignatureInfo(CryptoInfo):
    """Contains information about the signature status of a MIME part"""
    KEYS = (CryptoInfo.KEYS + ["name", "email", "keyinfo", "timestamp"])
    STATUSES = (CryptoInfo.STATUSES +
                ["mixed-error", "error",
                 "mixed-unknown", "unknown",
                 "mixed-expired", "expired",
                 "mixed-revoked", "revoked",
                 "mixed-unverified", "unverified",
                 "mixed-verified", "verified",
                 "mixed-invalid", "invalid"])

########NEW FILE########
__FILENAME__ = streamer
import os
import hashlib
import random
import sys
import threading
from datetime import datetime
from subprocess import Popen, PIPE
from tempfile import NamedTemporaryFile

from mailpile.util import sha512b64 as genkey


class IOFilter(threading.Thread):
    """
    This class will wrap a filehandle and spawn a background thread to
    filter either the input or output.
    """
    BLOCKSIZE = 8192

    def __init__(self, fd, callback):
        threading.Thread.__init__(self)
        self.fd = fd
        self.callback = callback
        self.writing = None
        self.pipe = os.pipe()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def writer(self):
        if self.writing is None:
            self.writing = True
            self.start()
        return os.fdopen(self.pipe[1], 'w')

    def reader(self):
        if self.writing is None:
            self.writing = False
            self.start()
        return os.fdopen(self.pipe[0], 'r')

    def _do_write(self):
        while True:
            data = os.read(self.pipe[0], self.BLOCKSIZE)
            if len(data) == 0:
                self.fd.write(self.callback(None))
                self.fd.flush()
                return
            else:
                self.fd.write(self.callback(data))

    def _do_read(self):
        while True:
            data = self.fd.read(self.BLOCKSIZE)
            if len(data) == 0:
                os.write(self.pipe[1], self.callback(None))
                os.close(self.pipe[1])
                return
            else:
                os.write(self.pipe[1], self.callback(data))

    def close(self):
        self._close_pipe_fd(self.pipe[0])
        self._close_pipe_fd(self.pipe[1])

    def _close_pipe_fd(self, pipe_fd):
        try:
            os.close(pipe_fd)
        except OSError:
            pass

    def run(self):
        if self.writing is True:
            self._do_write()
        elif self.writing is False:
            self._do_read()


class IOCoprocess(object):
    def __init__(self, command, fd):
        self.stderr = ''
        self._retval = None
        if command:
            self._proc, self._fd = self._popen(command, fd)
        else:
            self._proc, self._fd = None, fd

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self, *args):
        if self._retval is None:
            self._fd.close(*args)
            if self._proc:
                self.stderr = self._proc.stderr.read()
                self._retval = self._proc.wait()
                self._proc = None
            else:
                self._retval = 0
        return self._retval


class OutputCoprocess(IOCoprocess):
    """
    This class will stream data to an external coprocess.
    """
    def _popen(self, command, fd):
         proc = Popen(command, stdin=PIPE, stderr=PIPE, stdout=fd,
                      bufsize=0, close_fds=True)
         return proc, proc.stdin

    def write(self, *args):
        return self._fd.write(*args)


class InputCoprocess(IOCoprocess):
    """
    This class will stream data from an external coprocess.
    """
    def _popen(self, command, fd):
        proc = Popen(command, stdin=fd, stderr=PIPE, stdout=PIPE,
                     bufsize=0, close_fds=True)
        return proc, proc.stdout

    def read(self, *args):
        return self._fd.read(*args)


class ChecksummingStreamer(OutputCoprocess):
    """
    This checksums and streams data a named temporary file on disk, which
    can then be read back or linked to a final location.
    """
    def __init__(self, dir=None):
        self.tempfile = NamedTemporaryFile(dir=dir, delete=False)

        self.outer_md5sum = None
        self.outer_md5 = hashlib.md5()
        self.md5filter = IOFilter(self.tempfile, self._outer_md5_callback)
        self.fd = self.md5filter.writer()

        self.saved = False
        self.finished = False
        self._write_preamble()
        OutputCoprocess.__init__(self, self._mk_command(), self.fd)

    def _mk_command(self):
        return None

    def finish(self):
        if self.finished:
            return
        self.finished = True
        OutputCoprocess.close(self)
        self._write_postamble()
        self.fd.close()
        self.md5filter.join()
        self.md5filter.close()
        self.tempfile.seek(0, 0)

    def close(self):
        self.finish()
        self.tempfile.close()

    def save(self, filename, finish=True):
        if finish:
            self.finish()
        if not self.saved:
            # 1st save just renames the tempfile
            os.rename(self.tempfile.name, filename)
            self.saved = True
        else:
            # 2nd save creates a copy
            with open(filename, 'wb') as out:
                self.save_copy(out)

    def save_copy(self, ofd):
        self.tempfile.seek(0, 0)
        data = self.tempfile.read(4096)
        while data != '':
            ofd.write(data)
            data = self.tempfile.read(4096)

    def _outer_md5_callback(self, data):
        if data is None:
            # EOF...
            self.outer_md5sum = self.outer_md5.hexdigest()
            return ''
        else:
            # We calculate the MD5 sum as if the data used the CRLF linefeed
            # convention, whether it's actually using that or not.
            self.outer_md5.update(data.replace('\r', '').replace('\n', '\r\n'))
            return data

    def _write_preamble(self):
        pass

    def _write_postamble(self):
        pass


class EncryptingStreamer(ChecksummingStreamer):
    """
    This class creates a coprocess for encrypting data. The data will
    be streamed to a named temporary file on disk, which can then be
    read back or linked to a final location.
    """
    BEGIN_DATA = "-----BEGIN MAILPILE ENCRYPTED DATA-----\n"
    END_DATA = "-----END MAILPILE ENCRYPTED DATA-----\n"

    # We would prefer AES-256-GCM, but unfortunately openssl does not
    # (yet) behave well with it.
    DEFAULT_CIPHER = "aes-256-cbc"

    def __init__(self, key, dir=None, cipher=None):
        self.cipher = cipher or self.DEFAULT_CIPHER
        self.nonce, self.key = self._mutate_key(key)
        ChecksummingStreamer.__init__(self, dir=dir)
        self._send_key()

    def _mutate_key(self, key):
        nonce = genkey(str(random.getrandbits(512)))[:32].strip()
        return nonce, genkey(key, nonce)[:32].strip()

    def _send_key(self):
        self.write('%s\n' % self.key)

    def _mk_command(self):
        return ["openssl", "enc", "-e", "-a", "-%s" % self.cipher,
                "-pass", "stdin"]

    def _write_preamble(self):
        self.fd.write(self.BEGIN_DATA)
        self.fd.write('cipher: %s\n' % self.cipher)
        self.fd.write('nonce: %s\n' % self.nonce)
        self.fd.write('\n')
        self.fd.flush()

    def _write_postamble(self):
        self.fd.write('\n')
        self.fd.write(self.END_DATA)
        self.fd.flush()


class DecryptingStreamer(InputCoprocess):
    """
    This class creates a coprocess for decrypting data.
    """
    BEGIN_PGP = "-----BEGIN PGP MESSAGE-----"
    BEGIN_MED = "-----BEGIN MAILPILE ENCRYPTED DATA-----\n"
    END_MED = "-----END MAILPILE ENCRYPTED DATA-----\n"
    DEFAULT_CIPHER = "aes-256-cbc"

    STATE_BEGIN = 0
    STATE_HEADER = 1
    STATE_DATA = 2
    STATE_END = 3
    STATE_RAW_DATA = 4
    STATE_PGP_DATA = 5
    STATE_ERROR = -1

    def __init__(self, key, fd, md5sum=None, cipher=None):
        self.expected_outer_md5sum = md5sum
        self.outer_md5 = hashlib.md5()
        self.data_filter = IOFilter(fd, self._read_data)
        self.cipher = self.DEFAULT_CIPHER
        self.state = self.STATE_BEGIN
        self.buffered = ''
        self.key = key

        # Start reading our data...
        self.startup_lock = threading.Lock()
        self.startup_lock.acquire()
        self.read_fd = self.data_filter.reader()

        # Once the header has been processed (_read_data() will release the
        # lock), fork out our coprocess.
        self.startup_lock.acquire()
        InputCoprocess.__init__(self, self._mk_command(), self.read_fd)
        self.startup_lock = None

    def verify(self):
        if self.close() != 0:
            return False
        if not self.expected_outer_md5sum:
            return False
        return (self.expected_outer_md5sum == self.outer_md5.hexdigest())

    def _read_data(self, data):
        if data is None:
            if self.state in (self.STATE_BEGIN, self.STATE_HEADER):
                self.state = self.STATE_RAW_DATA
                self.startup_lock.release()
                data, self.buffered = self.buffered, ''
                return data
            return ''

        self.outer_md5.update(data.replace('\r', '').replace('\n', '\r\n'))

        if self.state == self.STATE_RAW_DATA:
            return data

        if self.state == self.STATE_BEGIN:
            self.buffered += data
            if (len(self.buffered) >= len(self.BEGIN_PGP)
                    and self.buffered.startswith(self.BEGIN_PGP)):
                self.state = self.STATE_PGP_DATA
                self.startup_lock.release()
                return self.buffered
            if len(self.buffered) >= len(self.BEGIN_MED):
                if not self.buffered.startswith(self.BEGIN_MED):
                    self.state = self.STATE_RAW_DATA
                    self.startup_lock.release()
                    return self.buffered
                if '\r\n\r\n' in self.buffered:
                    header, data = self.buffered.split('\r\n\r\n', 1)
                    headlines = header.strip().split('\r\n')
                    self.state = self.STATE_HEADER
                elif '\n\n' in self.buffered:
                    header, data = self.buffered.split('\n\n', 1)
                    headlines = header.strip().split('\n')
                    self.state = self.STATE_HEADER
                else:
                    return ''
            else:
                return ''

        if self.state == self.STATE_HEADER:
            headers = dict([l.split(': ', 1) for l in headlines[1:]])
            self.cipher = headers.get('cipher', self.cipher)
            nonce = headers.get('nonce')
            mutated = self._mutate_key(self.key, nonce)
            data = '\n'.join((mutated, data))
            self.state = self.STATE_DATA
            self.startup_lock.release()

        if self.state == self.STATE_DATA:
            if '\n\n-' in data:
                data = data.split('\n\n-', 1)[0]
                self.state = self.STATE_END
            elif '\r\n\r\n-' in data:
                data = data.split('\r\n\r\n-', 1)[0]
                self.state = self.STATE_END
            return data

        # Error, end and unknown states...
        return ''

    def _mutate_key(self, key, nonce):
        return genkey(key, nonce)[:32].strip()

    def _mk_command(self):
        if self.state == self.STATE_RAW_DATA:
            return None
        elif self.state == self.STATE_PGP_DATA:
            return ["gpg", "--batch"]
        return ["openssl", "enc", "-d", "-a", "-%s" % self.cipher,
                "-pass", "stdin"]


if __name__ == "__main__":

     bc = [0]
     def counter(data):
         bc[0] += len(data or '')
         return data or ''

     # Test the IOFilter in write mode
     iof = IOFilter(open('/tmp/iofilter.tmp', 'w'), counter)
     fd = iof.writer()
     fd.write('Hello world!')
     fd.close()
     iof.join()
     assert(open('/tmp/iofilter.tmp', 'r').read() == 'Hello world!')
     assert(bc[0] == 12)

     # Test the IOFilter in read mode
     bc[0] = 0
     iof = IOFilter(open('/tmp/iofilter.tmp', 'r'), counter)
     data = iof.reader().read()
     assert(data == 'Hello world!')
     assert(bc[0] == 12)

     # Encryption test
     data = 'Hello world! This is great!\nHooray, lalalalla!\n'
     es = EncryptingStreamer('test key', dir='/tmp')
     es.write(data)
     es.finish()
     fn = '/tmp/%s.aes' % es.outer_md5sum
     open(fn, 'wb').write('junk')  # Make sure overwriting works
     es.save(fn)

     # Decryption test!
     ds = DecryptingStreamer('test key', open(fn, 'rb'),
                             md5sum=es.outer_md5sum)
     new_data = ds.read()
     assert(ds.verify())
     assert(data == new_data)

     # Null decryption test, md5 verification only
     ds = DecryptingStreamer('test key', open('/tmp/iofilter.tmp', 'rb'),
                             md5sum='86fb269d190d2c85f6e0468ceca42a20')
     assert('Hello world!' == ds.read())
     assert(ds.verify())

     # Cleanup
     os.unlink('/tmp/iofilter.tmp')
     os.unlink(fn)

########NEW FILE########
__FILENAME__ = symencrypt
import os
import sys
import random
from subprocess import Popen, PIPE
from datetime import datetime

from mailpile.util import sha512b64 as genkey


class SymmetricEncrypter:
    """
    Symmetric encryption/decryption. Currently wraps OpenSSL's command line.
    """
    BEGIN_DATA = "-----BEGIN MAILPILE ENCRYPTED DATA-----"
    END_DATA = "-----END MAILPILE ENCRYPTED DATA-----"
    DEFAULT_CIPHER = "aes-256-gcm"

    def __init__(self, secret=None):
        self.available = None
        self.binary = 'openssl'
        self.handles = {}
        self.pipes = {}
        self.fds = ["stdout", "stderr"]
        self.errors = []
        self.statuscallbacks = {}
        self.secret = secret

    def run(self, args=[], output=None, passphrase=None, debug=False):
        self.pipes = {}
        args.insert(0, self.binary)

        if debug:
            print "Running openssl as: %s" % " ".join(args)

        proc = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)

        self.handles["stdout"] = proc.stdout
        self.handles["stderr"] = proc.stderr
        self.handles["stdin"] = proc.stdin

        if passphrase:
            self.handles["stdin"].write(passphrase + "\n")

        if output:
            self.handles["stdin"].write(output)

        self.handles["stdin"].close()

        retvals = dict([(fd, "") for fd in self.fds])
        while True:
            proc.poll()
            for fd in self.fds:
                try:
                    buf = self.handles[fd].read()
                except IOError:
                    continue
                if buf == "":
                    continue
                retvals[fd] += buf
            if proc.returncode is not None:
                break

        return proc.returncode, retvals

    def encrypt(self, data, cipher=None):
        if not cipher:
            cipher = self.DEFAULT_CIPHER
        nonce = genkey(str(random.getrandbits(512)))[:32].strip()
        enckey = genkey(self.secret, nonce)[:32].strip()
        params = ["enc", "-e", "-a", "-%s" % cipher,
                  "-pass", "stdin"]
        retval, res = self.run(params, output=data, passphrase=enckey)
        ret = "%s\ncipher: %s\nnonce: %s\n\n%s\n%s" % (
            self.BEGIN_DATA, cipher, nonce, res["stdout"], self.END_DATA)
        return ret

    def decrypt(self, data):
        try:
            head, enc, tail = data.split("\n\n")
            head = [h.strip() for h in head.split("\n")]
        except:
            try:
                head, enc, tail = data.split("\r\n\r\n")
                head = [h.strip() for h in head.split("\r\n")]
            except:
                raise ValueError("Not a valid OpenSSL encrypted block.")

        if (not head or not enc or not tail
                or head[0] != self.BEGIN_DATA
                or tail.strip() != self.END_DATA):
            raise ValueError("Not a valid OpenSSL encrypted block.")

        try:
            headers = dict([l.split(': ', 1) for l in head[1:]])
        except:
            raise ValueError("Message contained invalid parameter.")

        cipher = headers.get('cipher', self.DEFAULT_CIPHER)
        nonce = headers.get('nonce')
        if not nonce:
            raise ValueError("Encryption nonce not known.")

        enckey = genkey(self.secret, nonce)[:32].strip()
        params = ["enc", "-d", "-a", "-%s" % cipher, "-pass", "stdin"]
        retval, res = self.run(params, output=enc, passphrase=enckey)
        return res["stdout"]

    def decrypt_fd(self, lines, fd):
        for line in fd:
            lines.append(line)
            if line.startswith(self.END_DATA):
                break

        ret = self.decrypt("".join(lines))
        return ret.split("\n")


class EncryptedFile(object):
    def __init__(self, filename, secret, mode="w"):
        self.encrypter = SymmetricEncrypter(secret)
        self.filename = filename
        self.fd = open(filename, mode)
        self.data = ""

    def write(self, data):
        self.data += data

    def read(self):
        return self.encrypter.decrypt(self.fd.read())

    def close(self):
        self.fd.write(self.encrypter.encrypt(self.data))
        self.fd.close()


if __name__ == "__main__":
    s = SymmetricEncrypter("d3944bfea1e882dfc2e4878fa8905c6a2c")
    teststr = "Hello! This is a longish thing." * 50
    print "Example encrypted format:"
    print s.encrypt(teststr)
    if teststr == s.decrypt(s.encrypt(teststr)):
        print "Basic decryption worked"
    else:
        print "Encryption test failed"

    t0 = datetime.now()
    enc = s.encrypt(teststr)
    print "Speed test:"
    for i in range(5000):
        s.decrypt(enc)
        if i % 50 == 0:
            print "\r %-3d%% %s>" % (int(i / 50.0), "-" * (i//100)),
            sys.stdout.flush()
    t1 = datetime.now()
    print "\n5000 decrypt ops took %s => %s/op" % ((t1-t0), (t1-t0)/5000)

########NEW FILE########
__FILENAME__ = defaults
APPVER = "0.1.0"
ABOUT = """\
Mailpile.py          a tool                 Copyright 2013-2014, Mailpile ehf
               for searching and                   <https://www.mailpile.is/>
           organizing piles of e-mail

This program is free software: you can redistribute it and/or modify it under
the terms of either the GNU Affero General Public License as published by the
Free Software Foundation or the Apache License 2.0 as published by the Apache
Software Foundation. See the file COPYING.md for details.
"""
#############################################################################
import os
import time
from gettext import gettext as _

from mailpile.config import PathDict


DEFAULT_SENDMAIL = '|/usr/sbin/sendmail -i %(rcpt)s'
CONFIG_PLUGINS = []
CONFIG_RULES = {
    'version': [_('Mailpile program version'), False, APPVER],
    'timestamp': [_('Configuration timestamp'), int, int(time.time())],
    'sys': [_('Technical system settings'), False, {
        'fd_cache_size':  (_('Max files kept open at once'), int,         500),
        'history_length': (_('History length (lines, <0=no save)'), int,  100),
        'http_port':      (_('Listening port for web UI'), int,         33411),
        'postinglist_kb': (_('Posting list target size in KB'), int,       64),
        'sort_max':       (_('Max results we sort "well"'), int,         2500),
        'snippet_max':    (_('Max length of metadata snippets'), int,     250),
        'debug':          (_('Debugging flags'), str,                      ''),
        'gpg_keyserver':  (_('Host:port of PGP keyserver'),
                           str, 'pool.sks-keyservers.net'),
        'http_host':      (_('Listening host for web UI'),
                           'hostname', 'localhost'),
        'local_mailbox_id': (_('Local read/write Maildir'), 'b36',         ''),
        'mailindex_file': (_('Metadata index file'), 'file',               ''),
        'postinglist_dir': (_('Search index directory'), 'dir',            ''),
        'mailbox':        [_('Mailboxes we index'), 'str',                 []],
        'plugins':        [_('Plugins to load on startup'),
                           CONFIG_PLUGINS, []],
        'path':           [_('Locations of assorted data'), False, {
            'html_theme': [_('Default theme'),
                           'dir', os.path.join('static', 'default')],
            'vcards':     [_('Location of vcards'), 'dir', 'vcards'],
            'event_log':  [_('Location of event log'), 'dir', 'logs'],
        }],
        'lockdown':       [_('Demo mode, disallow changes'), bool,      False],
    }],
    'prefs': [_("User preferences"), False, {
        'num_results':     (_('Search results per page'), int,             20),
        'rescan_interval': (_('New mail check frequency'), int,             0),
        'gpg_clearsign':   (_('Inline PGP signatures or attached'),
                            bool, False),
        'gpg_recipient':   (_('Encrypt local data to ...'), str,           ''),
        'openpgp_header':  (_('Advertise GPG preferences in a header?'),
                            ['', 'sign', 'encrypt', 'signencrypt'],
                            'signencrypt'),
        'crypto_policy':   (_('Default encryption policy for outgoing mail'),
                            str, 'none'),
        'default_order':   (_('Default sort order'), str,          'rev-date'),
        'obfuscate_index': (_('Key to use to scramble the index'), str,    ''),
        'index_encrypted': (_('Make encrypted content searchable'),
                            bool, False),
        'rescan_command':  (_('Command run before rescanning'), str,       ''),
        'default_email':   (_('Default outgoing e-mail address'), 'email', ''),
        'default_route':   (_('Default outgoing mail route'), str, ''),
        'always_bcc_self': (_('Always BCC self on outgoing mail'), bool, True),
        'default_messageroute': (_('Default outgoing mail route'), str,    ''),
        'language':        (_('User interface language'), str,             ''),
        'vcard':           [_("VCard import/export settings"), False, {
            'importers':   [_("VCard import settings"), False,             {}],
            'exporters':   [_("VCard export settings"), False,             {}],
            'context':     [_("VCard context helper settings"), False,     {}],
        }],
    }],
    'profiles': [_('User profiles and personalities'), {
        'name':            (_('Account name'), 'str', ''),
        'email':           (_('E-mail address'), 'email', ''),
        'signature':       (_('Message signature'), 'multiline', ''),
        'route':           (_('DEPRECATED, DO NOT USE'), str, ''),
        'messageroute':    (_('Outgoing mail route'), str, ''),
    }, []],
    'routes': [_('Outgoing message routes'), {
        'name':            (_('Route name'), str, ''),
        'protocol':        (_('Messaging protocol'),
                            ["smtp", "smtptls", "smtpssl", "local"],
                            'smtp'),
        'username':        (_('User name'), str, ''),
        'password':        (_('Password'), str, ''),
        'command':         (_('Shell command'), str, ''),
        'host':            (_('Host'), str, ''),
        'port':            (_('Port'), int, 587)
    }, {}],
    'sources': [_('Incoming message sources'), {
        'name':            (_('Source name'), str, ''),
        'protocol':        (_('Mailbox protocol or format'),
                            ["mbox", "maildir", "macmaildir", "gmvault",
                             "imap", "pop3"],
                            ''),
        'pre_command':     (_('Shell command run before syncing'), str, ''),
        'post_command':    (_('Shell command run after syncing'), str, ''),
        'interval':        (_('How frequently to check for mail'), int, 300),
        'username':        (_('User name'), str, ''),
        'password':        (_('Password'), str, ''),
        'host':            (_('Host'), str, ''),
        'port':            (_('Port'), int, 993),
        'discovery':       (_('Mailbox discovery policy'), False, {
            'policy':      (_('Default mailbox policy'),
                            ['unknown', 'ignore', 'watch',
                             'read', 'move', 'sync'], 'unknown'),
            'local_copy':  (_('Copy mail to a local mailbox?'), bool, False),
            'create_tag':  (_('Create a tag for each mailbox?'), bool, True),
            'process_new': (_('Is a potential source of new mail'), bool, True),
            'apply_tags':  (_('Tags applied to messages'), str, []),
        }),
        'mailbox': (_('Mailboxes'), {
            'path':        (_('Mailbox source path'), str, ''),
            'policy':      (_('Mailbox policy'),
                            ['unknown', 'ignore', 'watch',
                             'read', 'move', 'sync'], 'ignore'),
            'local':       (_('Local mailbox path'), str, ''),
            'process_new': (_('Is a source of new mail'), bool, True),
            'primary_tag': (_('A tag representing this mailbox'), str, ''),
            'apply_tags':  (_('Tags applied to messages'), str, []),
        }, {})
    }, {}]
}


if __name__ == "__main__":
    import mailpile.defaults
    from mailpile.config import ConfigDict

    print '%s' % (ConfigDict(_name='mailpile',
                             _comment='Base configuration',
                             _rules=mailpile.defaults.CONFIG_RULES
                             ).as_config_bytes(), )

########NEW FILE########
__FILENAME__ = eventlog
import copy
import datetime
import json
import os
import threading
import time
from email.utils import formatdate, parsedate_tz, mktime_tz

from mailpile.crypto.streamer import EncryptingStreamer, DecryptingStreamer
from mailpile.util import CleanText


EVENT_COUNTER_LOCK = threading.Lock()
EVENT_COUNTER = 0


def NewEventId():
    """
    This is guaranteed to generate unique event IDs for up to 1 million
    events per second. Beyond that, all bets are off. :-P
    """
    global EVENT_COUNTER
    try:
        EVENT_COUNTER_LOCK.acquire()
        EVENT_COUNTER = EVENT_COUNTER+1
        EVENT_COUNTER %= 0x100000
        return '%8.8x.%5.5x.%x' % (time.time(), EVENT_COUNTER, os.getpid())
    finally:
        EVENT_COUNTER_LOCK.release()


def _ClassName(obj):
    if isinstance(obj, (str, unicode)):
        return str(obj).replace('mailpile.', '.')
    elif hasattr(obj, '__classname__'):
        return str(obj.__classname__).replace('mailpile.', '.')
    else:
        return str(obj.__class__).replace('mailpile.', '.')


class Event(object):
    """
    This is a single event in the event log. Actual interpretation and
    rendering of events should be handled by the respective source class.
    """
    RUNNING = 'R'
    COMPLETE = 'c'
    INCOMPLETE = 'i'
    FUTURE = 'F'

    # For now these live here, we may templatize this later.
    PREAMBLE_HTML = '<ul class="events">'
    PUBLIC_HTML = ('<li><span class="event_date">%(date)s</span> '
                   '<b class="event_message">%(message)s</b></li>')
    PRIVATE_HTML = PUBLIC_HTML
    POSTAMBLE_HTML = '</ul>'

    @classmethod
    def Parse(cls, json_string):
        try:
            return cls(*json.loads(json_string))
        except:
            return cls()

    def __init__(self,
                 ts=None, event_id=None, flags='C', message='',
                 source=None, data=None, private_data=None):
        self._data = [
            '',
            event_id or NewEventId(),
            flags,
            message,
            _ClassName(source),
            data or {},
            private_data or {},
        ]
        self._set_ts(ts or time.time())

    def __str__(self):
        return json.dumps(self._data)

    def _set_ts(self, ts):
        if hasattr(ts, 'timetuple'):
            self._ts = int(time.mktime(ts.timetuple()))
        elif isinstance(ts, (str, unicode)):
            self._ts = int(mktime_tz(parsedate_tz(ts)))
        else:
            self._ts = float(ts)
        self._data[0] = formatdate(self._ts)

    def _set(self, col, value):
        self._set_ts(time.time())
        self._data[col] = value

    def _get_source_class(self):
        module_name, class_name = CleanText(self.source,
                                            banned=CleanText.NONDNS
                                            ).clean.rsplit('.', 1)
        if module_name.startswith('.'):
            module_name = 'mailpile' + module_name
        module = __import__(module_name, globals(), locals(), class_name)
        return getattr(module, class_name)

    date = property(lambda s: s._data[0], lambda s, v: s._set_ts(v))
    ts = property(lambda s: s._ts, lambda s, v: s._set_ts(v))
    event_id = property(lambda s: s._data[1], lambda s, v: s._set(1, v))
    flags = property(lambda s: s._data[2], lambda s, v: s._set(2, v))
    message = property(lambda s: s._data[3], lambda s, v: s._set(3, v))
    source = property(lambda s: s._data[4],
                      lambda s, v: s._set(4, _ClassName(v)))
    data = property(lambda s: s._data[5], lambda s, v: s._set(5, v))
    private_data = property(lambda s: s._data[6], lambda s, v: s._set(6, v))
    source_class = property(_get_source_class)

    def as_dict(self, private=True):
        try:
            return self.source_class.EventAsDict(self, private=private)
        except (AttributeError, NameError):
            data = {
                'ts': self.ts,
                'date': self.date,
                'event_id': self.event_id,
                'message': self.message,
                'flags': self.flags,
                'source': self.source,
                'data': self.data
            }
            if private:
                data['private_data'] = self.private_data
            return data

    def as_json(self, private=True):
        try:
            return self.source_class.EventAsJson(self, private=private)
        except (AttributeError, NameError):
            return json.dumps(self.as_dict(private=private))

    def as_html(self, private=True):
        try:
            return self.source_class.EventAsHtml(self, private=private)
        except (AttributeError, NameError):
            if private:
                return self.PRIVATE_HTML % self.as_dict(private=True)
            else:
                return self.PUBLIC_HTML % self.as_dict(private=False)


class EventLog(object):
    """
    This is the Mailpile Event Log.

    The log is written encrypted to disk on an ongoing basis (rotated
    every N lines), but entries are kept in RAM as well. The event log
    allows for recording of incomplete events, to help different parts
    of the app "remember" tasks which have yet to complete or may need
    to be retried.
    """
    KEEP_LOGS = 2

    def __init__(self, logdir, encryption_key_func, rollover=10240):
        self.logdir = logdir
        self.encryption_key_func = encryption_key_func
        self.rollover = rollover

        self._events = {}

        # Internals...
        self._waiter = threading.Condition()
        self._lock = threading.Lock()
        self._log_fd = None

    def _notify_waiters(self):
        self._waiter.acquire()
        self._waiter.notifyAll()
        self._waiter.release()

    def wait(self, timeout=None):
        self._waiter.acquire()
        self._waiter.wait(timeout)
        self._waiter.release()

    def _save_filename(self):
        return os.path.join(self.logdir, self._log_start_id)

    def _open_log(self):
        if self._log_fd:
            self._log_fd.close()

        if not os.path.exists(self.logdir):
            os.mkdir(self.logdir)

        self._log_start_id = NewEventId()
        enc_key = self.encryption_key_func()
        if enc_key:
            self._log_fd = EncryptingStreamer(enc_key, dir=self.logdir)
            self._log_fd.save(self._save_filename(), finish=False)
        else:
            self._log_fd = open(self._save_filename(), 'w', 0)

        # Write any incomplete events to the new file
        for e in self.incomplete():
            self._log_fd.write('%s\n' % e)

        # We're starting over, incomplete events don't count
        self._logged = 0

    def _maybe_rotate_log(self):
        if self._logged > self.rollover:
            self._log_fd.close()
            kept_events = {}
            for e in self.incomplete():
                kept_events[e.event_id] = e
            self._events = kept_events
            self._open_log()
            self.purge_old_logfiles()

    def _list_logfiles(self):
        return sorted([l for l in os.listdir(self.logdir)
                       if not l.startswith('.')])

    def _save_events(self, events):
        if not self._log_fd:
            self._open_log()
        events.sort(key=lambda ev: ev.ts)
        for event in events:
            self._log_fd.write('%s\n' % event)
            self._events[event.event_id] = event

    def _load_logfile(self, lfn):
        enc_key = self.encryption_key_func()
        with open(os.path.join(self.logdir, lfn)) as fd:
            if enc_key:
                lines = fd.read()
            else:
                with DecryptingStreamer(enc_key, fd) as streamer:
                    lines = streamer.read()
            if lines:
                for line in lines.splitlines():
                    event = Event.Parse(line)
                    if Event.COMPLETE in event.flags:
                        if event.event_id in self._events:
                            del self._events[event.event_id]
                    else:
                        self._events[event.event_id] = event
        self._save_events(self._events.values())

    def _match(self, event, filters):
        for kw, rule in filters.iteritems():
            if kw.endswith('!'):
                truth, okw, kw = False, kw, kw[:-1]
            else:
                truth, okw = True, kw
            if kw == 'source':
                if truth != (event.source == _ClassName(rule)):
                    return False
            elif kw == 'flag':
                if truth != (rule in event.flags):
                    return False
            elif kw == 'flags':
                if truth != (event.flags == rule):
                    return False
            elif kw == 'since':
                if truth != (event.ts > float(rule)):
                    return False
            elif kw.startswith('data_'):
                if truth != (str(event.data.get(kw[5:])) == str(rule)):
                    return False
            elif kw.startswith('private_data_'):
                if truth != (str(event.data.get(kw[13:])) == str(rule)):
                    return False
            else:
                # Unknown keywords match nothing...
                print 'Unknown keyword: `%s=%s`' % (okw, rule)
                return False
        return True

    def incomplete(self, **filters):
        """Return all the incomplete events, in order."""
        for ek in sorted(self._events.keys()):
            e = self._events.get(ek, None)
            if (e is not None and
                    Event.COMPLETE not in e.flags and
                    self._match(e, filters)):
                yield e

    def since(self, ts, **filters):
        """Return all events since a given time, in order."""
        for ek in sorted(self._events.keys()):
            e = self._events.get(ek, None)
            if (e is not None and
                    e.ts >= ts and
                    self._match(e, filters)):
                yield e

    def events(self, **filters):
        return self.since(0, **filters)

    def log_event(self, event):
        """Log an Event object."""
        self._lock.acquire()
        try:
            self._save_events([event])
            self._logged += 1
            self._maybe_rotate_log()
            self._notify_waiters()
        finally:
            self._lock.release()
        return event

    def log(self, *args, **kwargs):
        """Log a new event."""
        return self.log_event(Event(*args, **kwargs))

    def close(self):
        self._lock.acquire()
        try:
            self._log_fd.close()
            self._log_fd = None
        finally:
            self._lock.release()

    def load(self):
        self._lock.acquire()
        try:
            self._open_log()
            for lf in self._list_logfiles()[-4:]:
                try:
                    self._load_logfile(lf)
                except (OSError, IOError):
                    import traceback
                    traceback.print_exc()
            return self
        finally:
            self._lock.release()

    def purge_old_logfiles(self, keep=None):
        keep = keep or self.KEEP_LOGS
        for lf in self._list_logfiles()[:-keep]:
            try:
                os.remove(os.path.join(self.logdir, lf))
            except OSError:
                pass

########NEW FILE########
__FILENAME__ = httpd
#
# Mailpile's built-in HTTPD
#
###############################################################################
import mimetypes
import os
import socket
import SocketServer
from gettext import gettext as _
from SimpleXMLRPCServer import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
from urllib import quote, unquote
from urlparse import parse_qs, urlparse

import mailpile.util
from mailpile.commands import Action
from mailpile.urlmap import UrlMap
from mailpile.util import *
from mailpile.ui import *

global WORD_REGEXP, STOPLIST, BORING_HEADERS, DEFAULT_PORT

DEFAULT_PORT = 33411


class HttpRequestHandler(SimpleXMLRPCRequestHandler):

    # We always recognize these extensions, no matter what the Python
    # mimetype module thinks.
    _MIMETYPE_MAP = dict([(ext, 'text/plain') for ext in (
        'c', 'cfg', 'conf', 'cpp', 'csv', 'h', 'hpp', 'log', 'md', 'me',
        'py', 'rb', 'rc', 'txt'
    )] + [(ext, 'application/x-font') for ext in (
        'pfa', 'pfb', 'gsf', 'pcf'
    )] + [
        ('css', 'text/css'),
        ('eot', 'application/vnd.ms-fontobject'),
        ('gif', 'image/gif'),
        ('html', 'text/html'),
        ('htm', 'text/html'),
        ('ico', 'image/x-icon'),
        ('jpg', 'image/jpeg'),
        ('jpeg', 'image/jpeg'),
        ('js', 'text/javascript'),
        ('json', 'application/json'),
        ('otf', 'font/otf'),
        ('png', 'image/png'),
        ('rss', 'application/rss+xml'),
        ('tif', 'image/tiff'),
        ('tiff', 'image/tiff'),
        ('ttf', 'font/ttf'),
        ('svg', 'image/svg+xml'),
        ('svgz', 'image/svg+xml'),
        ('woff', 'application/font-woff'),
    ])

    _ERROR_CONTEXT = {'lastq': '', 'csrf': '', 'path': ''},

    def http_host(self):
        """Return the current server host, e.g. 'localhost'"""
        #rsplit removes port
        return self.headers.get('host', 'localhost').rsplit(':', 1)[0]

    def server_url(self):
        """Return the current server URL, e.g. 'http://localhost:33411/'"""
        return '%s://%s' % (self.headers.get('x-forwarded-proto', 'http'),
                            self.headers.get('host', 'localhost'))

    def send_http_response(self, code, msg):
        """Send the HTTP response header"""
        self.wfile.write('HTTP/1.1 %s %s\r\n' % (code, msg))

    def send_http_redirect(self, destination):
        if '//' not in destination:
            destination = '%s%s' % (self.server_url(), destination)
        self.send_http_response(302, 'Found')
        self.wfile.write(('Location: %s\r\n\r\n'
                          '<h1><a href="%s">Please look here!</a></h1>\n'
                          ) % (destination, destination))

    def send_standard_headers(self,
                              header_list=[],
                              cachectrl='private',
                              mimetype='text/html'):
        """
        Send common HTTP headers plus a list of custom headers:
        - Cache-Control
        - Content-Type

        This function does not send the HTTP/1.1 header, so
        ensure self.send_http_response() was called before

        Keyword arguments:
        header_list  -- A list of custom headers to send, containing
                        key-value tuples
        cachectrl    -- The value of the 'Cache-Control' header field
        mimetype     -- The MIME type to send as 'Content-Type' value
        """
        if mimetype.startswith('text/') and ';' not in mimetype:
            mimetype += ('; charset = utf-8')
        self.send_header('Cache-Control', cachectrl)
        self.send_header('Content-Type', mimetype)
        for header in header_list:
            self.send_header(header[0], header[1])
        self.end_headers()

    def send_full_response(self, message,
                           code=200, msg='OK',
                           mimetype='text/html', header_list=[],
                           suppress_body=False):
        """
        Sends the HTTP header and a response list

        message       -- The body of the response to send
        header_list   -- A list of custom headers to send,
                         containing key-value tuples
        code          -- The HTTP response code to send
        mimetype      -- The MIME type to send as 'Content-Type' value
        suppress_body -- Set this to True to ignore the message parameter
                              and not send any response body
        """
        message = unicode(message).encode('utf-8')
        self.log_request(code, message and len(message) or '-')
        # Send HTTP/1.1 header
        self.send_http_response(code, msg)
        # Send all headers
        if code == 401:
            self.send_header('WWW-Authenticate',
                             'Basic realm = MP%d' % (time.time() / 3600))
        # If suppress_body == True, we don't know the content length
        contentLengthHeaders = []
        if not suppress_body:
            contentLengthHeaders = [('Content-Length', len(message or ''))]
        self.send_standard_headers(header_list=(header_list +
                                                contentLengthHeaders),
                                   mimetype=mimetype,
                                   cachectrl="no-cache")
        # Response body
        if not suppress_body:
            self.wfile.write(message or '')

    def guess_mimetype(self, fpath):
        ext = os.path.basename(fpath).rsplit('.')[-1]
        return (self._MIMETYPE_MAP.get(ext.lower()) or
                mimetypes.guess_type(fpath, strict=False)[0] or
                'application/octet-stream')

    def send_file(self, config, filename):
        # FIXME: Do we need more security checks?
        if '..' in filename:
            code, msg = 403, "Access denied"
        else:
            try:
                tpl = config.sys.path.get(self.http_host(), 'html_theme')
                fpath, fd, mt = config.open_file(tpl, filename)
                mimetype = mt or self.guess_mimetype(fpath)
                message = fd.read()
                fd.close()
                code, msg = 200, "OK"
            except IOError, e:
                mimetype = 'text/plain'
                if e.errno == 2:
                    code, msg = 404, "File not found"
                elif e.errno == 13:
                    code, msg = 403, "Access denied"
                else:
                    code, msg = 500, "Internal server error"
                message = ""

        self.log_request(code, message and len(message) or '-')
        self.send_http_response(code, msg)
        self.send_standard_headers(header_list=[('Content-Length',
                                                len(message or ''))],
                                   mimetype=mimetype,
                                   cachectrl=("must-revalidate = False, "
                                              "max-age = 3600"))
        self.wfile.write(message or '')

    def csrf(self):
        """
        Generate a hashed token from the current timestamp
        and the server secret to avoid CSRF attacks
        """
        ts = '%x' % int(time.time() / 60)
        return '%s-%s' % (ts, b64w(sha1b64('-'.join([self.server.secret,
                                                     ts]))))

    def do_POST(self, method='POST'):
        (scheme, netloc, path, params, query, frag) = urlparse(self.path)
        if path.startswith('/::XMLRPC::/'):
            raise ValueError(_('XMLRPC has been disabled for now.'))
            #return SimpleXMLRPCRequestHandler.do_POST(self)

        config = self.server.session.config
        post_data = {}
        try:
            ue = 'application/x-www-form-urlencoded'
            clength = int(self.headers.get('content-length', 0))
            ctype, pdict = cgi.parse_header(self.headers.get('content-type',
                                                             ue))
            if ctype == 'multipart/form-data':
                post_data = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={'REQUEST_METHOD': method,
                             'CONTENT_TYPE': self.headers['Content-Type']}
                )
            elif ctype == ue:
                if clength > 5 * 1024 * 1024:
                    raise ValueError(_('OMG, input too big'))
                post_data = cgi.parse_qs(self.rfile.read(clength), 1)
            else:
                raise ValueError(_('Unknown content-type'))

        except (IOError, ValueError), e:
            self.send_full_response(self.server.session.ui.render_page(
                config, self._ERROR_CONTEXT,
                body='POST geborked: %s' % e,
                title=_('Internal Error')
            ), code=500)
            return None
        return self.do_GET(post_data=post_data, method=method)

    def do_GET(self, post_data={}, suppress_body=False, method='GET'):
        (scheme, netloc, path, params, query, frag) = urlparse(self.path)
        query_data = parse_qs(query)
        path = unquote(path)

        # HTTP is stateless, so we create a new session for each request.
        config = self.server.session.config

        if 'http' in config.sys.debug:
            sys.stderr.write(('%s: %s qs = %s post = %s\n'
                              ) % (method, path, query_data, post_data))
        if 'httpdata' in config.sys.debug:
            self.wfile = DebugFileWrapper(sys.stderr, self.wfile)

        # Static things!
        if path == '/favicon.ico':
            path = '/static/favicon.ico'
        if path.startswith('/_/'):
            path = path[2:]
        if path.startswith('/static/'):
            return self.send_file(config, path[len('/static/'):])

        session = Session(config)
        session.ui = HttpUserInteraction(self, config)

        idx = session.config.index
        name = session.config.get_profile().get('name', 'Chelsea Manning')
        session.ui.html_variables = {
            'csrf': self.csrf(),
            'http_host': self.headers.get('host', 'localhost'),
            'http_hostname': self.http_host(),
            'http_method': method,
            'message_count': (idx and len(idx.INDEX) or 0),
            'name': name,
            'title': 'Mailpile dummy title',
            'url_protocol': self.headers.get('x-forwarded-proto', 'http'),
            'mailpile_size': idx and len(idx.INDEX) or 0
        }

        try:
            try:
                commands = UrlMap(session).map(self, method, path,
                                               query_data, post_data)
            except UsageError:
                if (not path.endswith('/') and
                        not session.config.sys.debug and
                        method == 'GET'):
                    commands = UrlMap(session).map(self, method, path + '/',
                                                   query_data, post_data)
                    url = quote(path) + '/'
                    if query:
                        url += '?' + query
                    return self.send_http_redirect(url)
                else:
                    raise

            results = [cmd.run() for cmd in commands]
            session.ui.display_result(results[-1])
        except UrlRedirectException, e:
            return self.send_http_redirect(e.url)
        except SuppressHtmlOutput:
            return
        except:
            e = traceback.format_exc()
            print e
            if not session.config.sys.debug:
                e = _('Internal error')
            self.send_full_response(e, code=500, mimetype='text/plain')
            return None

        mimetype, content = session.ui.render_response(session.config)
        self.send_full_response(content, mimetype=mimetype)

    def do_PUT(self):
        return self.do_POST(method='PUT')

    def do_UPDATE(self):
        return self.do_POST(method='UPDATE')

    def do_HEAD(self):
        return self.do_GET(suppress_body=True, method='HEAD')

    def log_message(self, fmt, *args):
        self.server.session.ui.notify(self.server_url() +
                                      ' ' + (fmt % args))


class HttpServer(SocketServer.ThreadingMixIn, SimpleXMLRPCServer):
    def __init__(self, session, sspec, handler):
        SimpleXMLRPCServer.__init__(self, sspec, handler)
        self.session = session
        self.sessions = {}
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sspec = (sspec[0] or 'localhost', self.socket.getsockname()[1])
        # FIXME: This could be more securely random
        self.secret = '-'.join([str(x) for x in [self.socket, self.sspec,
                                                 time.time(), self.session]])

    def finish_request(self, request, client_address):
        try:
            SimpleXMLRPCServer.finish_request(self, request, client_address)
        except socket.error:
            pass
        if mailpile.util.QUITTING:
            self.shutdown()


class HttpWorker(threading.Thread):
    def __init__(self, session, sspec):
        threading.Thread.__init__(self)
        self.httpd = HttpServer(session, sspec, HttpRequestHandler)
        self.session = session

    def run(self):
        self.httpd.serve_forever()

    def quit(self, join=False):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
        self.httpd = None

########NEW FILE########
__FILENAME__ = jinjaextensions
import copy
import datetime
import hashlib
import re
import urllib
import json
import shlex
from gettext import gettext as _
from jinja2 import nodes, UndefinedError, Markup
from jinja2.ext import Extension
from jinja2.utils import contextfunction, import_string
#from markdown import markdown

from mailpile.commands import Action
from mailpile.util import *
from mailpile.ui import HttpUserInteraction
from mailpile.urlmap import UrlMap
from mailpile.plugins import PluginManager


class MailpileCommand(Extension):
    """Run Mailpile Commands, """
    tags = set(['mpcmd'])

    def __init__(self, environment):
        Extension.__init__(self, environment)
        self.env = environment
        environment.globals['mailpile'] = self._command
        environment.globals['mailpile_render'] = self._command_render
        environment.globals['use_data_view'] = self._use_data_view
        environment.globals['regex_replace'] = self._regex_replace
        environment.filters['regex_replace'] = self._regex_replace
        environment.globals['friendly_bytes'] = self._friendly_bytes
        environment.filters['friendly_bytes'] = self._friendly_bytes
        environment.globals['friendly_number'] = self._friendly_number
        environment.filters['friendly_number'] = self._friendly_number
        environment.globals['show_avatar'] = self._show_avatar
        environment.filters['show_avatar'] = self._show_avatar
        environment.globals['navigation_on'] = self._navigation_on
        environment.filters['navigation_on'] = self._navigation_on
        environment.globals['has_label_tags'] = self._has_label_tags
        environment.filters['has_label_tags'] = self._has_label_tags
        environment.globals['show_message_signature'
                            ] = self._show_message_signature
        environment.filters['show_message_signature'
                            ] = self._show_message_signature
        environment.globals['show_message_encryption'
                            ] = self._show_message_encryption
        environment.filters['show_message_encryption'
                            ] = self._show_message_encryption
        environment.globals['contact_url'] = self._contact_url
        environment.filters['contact_url'] = self._contact_url
        environment.globals['contact_name'] = self._contact_name
        environment.filters['contact_name'] = self._contact_name
        environment.globals['fix_urls'] = self._fix_urls
        environment.filters['fix_urls'] = self._fix_urls

        # See utils.py for these functions:
        environment.globals['elapsed_datetime'] = elapsed_datetime
        environment.filters['elapsed_datetime'] = elapsed_datetime
        environment.globals['friendly_datetime'] = friendly_datetime
        environment.filters['friendly_datetime'] = friendly_datetime
        environment.globals['friendly_time'] = friendly_time
        environment.filters['friendly_time'] = friendly_time

        # These are helpers for injecting plugin elements
        environment.globals['get_ui_elements'] = self._get_ui_elements
        environment.globals['ui_elements_setup'] = self._ui_elements_setup
        environment.filters['add_state_query_string'] = self._add_state_query_string

        # This is a worse versin of urlencode, but without it we require
        # Jinja 2.7, which isn't apt-get installable.
        environment.globals['urlencode'] = self._urlencode
        environment.filters['urlencode'] = self._urlencode

        # Make a function-version of the safe command
        environment.globals['safe'] = self._safe
        environment.filters['json'] = self._json

        # Strip trailing blank lines from email
        environment.globals['nice_text'] = self._nice_text
        environment.filters['nice_text'] = self._nice_text

        # Strip Re: Fwd: from subject lines
        environment.globals['nice_subject'] = self._nice_subject
        environment.filters['nice_subject'] = self._nice_subject

        # Make unruly names a lil bit nicer
        environment.globals['nice_name'] = self._nice_name
        environment.filters['nice_name'] = self._nice_name

        # Makes a UI usable classification of attachment from mimetype
        environment.globals['attachment_type'] = self._attachment_type
        environment.filters['attachment_type'] = self._attachment_type

        # Loads theme settings JSON manifest
        environment.globals['theme_settings'] = self._theme_settings
        environment.filters['theme_settings'] = self._theme_settings

        # Separates Fingerprint in 4 char groups
        environment.globals['nice_fingerprint'] = self._nice_fingerprint
        environment.filters['nice_fingerprint'] = self._nice_fingerprint

        # Converts Filter +/- tags into arrays
        environment.globals['make_filter_groups'] = self._make_filter_groups
        environment.filters['make_filter_groups'] = self._make_filter_groups

    def _command(self, command, *args, **kwargs):
        rv = Action(self.env.session, command, args, data=kwargs).as_dict()
        if 'jinja' in self.env.session.config.sys.debug:
            sys.stderr.write('mailpile(%s, %s, %s) -> %s' % (
                command, args, kwargs, rv))
        return rv

    def _command_render(self, how, command, *args, **kwargs):
        old_ui, config = self.env.session.ui, self.env.session.config
        try:
            ui = self.env.session.ui = HttpUserInteraction(None, config)
            ui.html_variables = copy.deepcopy(old_ui.html_variables)
            ui.render_mode = how
            ui.display_result(Action(self.env.session, command, args,
                                     data=kwargs))
            return ui.render_response(config)
        finally:
            self.env.session.ui = old_ui

    def _use_data_view(self, view_name, result):
        dv = UrlMap(self.env.session).map(None, 'GET', view_name, {}, {})[-1]
        return dv.view(result)

    def _get_ui_elements(self, ui_type, state, context=None):
        ctx = context or state.get('context_url', '')
        return copy.deepcopy(PluginManager().get_ui_elements(ui_type, ctx))

    def _add_state_query_string(self, url, state, elem=None):
        if not url:
            url = state.get('command_url', '')
        if '#' in url:
            url, frag = url.split('#', 1)
            frag = '#' + frag
        else:
            frag = ''
        if url:
            args = []
            query_args = state.get('query_args', {})
            for key in sorted(query_args.keys()):
                if key.startswith('_'):
                    continue
                values = query_args[key]
                if elem:
                    for rk, rv in elem.get('url_args_remove', []):
                        if rk == key:
                            values = [v for v in values if rv and (v != rv)]
                if elem:
                    for ak, av in elem.get('url_args_add', []):
                        if ak == key and av not in values:
                            values.append(av)
                args.extend([(key, v.encode("utf-8")) for v in values])
            return url + '?' + urllib.urlencode(args) + frag
        else:
            return url + frag

    def _ui_elements_setup(self, classfmt, elements):
        setups = []
        for elem in elements:
            if elem.get('javascript_setup'):
                setups.append('$("%s").each(function(){%s(this);});'
                              % (classfmt % elem, elem['javascript_setup']))
            if elem.get('javascript_events'):
                for event, call in elem.get('javascript_events').iteritems():
                    setups.append('$("%s").bind("%s", %s);' %
                        (classfmt % elem, event, call))
        return Markup("function(){%s}" % ''.join(setups))

    def _regex_replace(self, s, find, replace):
        """A non-optimal implementation of a regex filter"""
        return re.sub(find, replace, s)

    def _friendly_number(self, number, decimals=0):
        # See mailpile/util.py:friendly_number if this needs fixing
        return friendly_number(number, decimals=decimals, base=1000)

    def _friendly_bytes(self, number, decimals=0):
        # See mailpile/util.py:friendly_number if this needs fixing
        return friendly_number(number,
                               decimals=decimals, base=1024, suffix='B')

    def _show_avatar(self, contact):
        if "photo" in contact:
            photo = contact['photo']
        else:
            photo = '/static/img/avatar-default.png'
        return photo

    def _navigation_on(self, search_tag_ids, on_tid):
        if search_tag_ids:
            for tid in search_tag_ids:
                if tid == on_tid:
                    return "navigation-on"
                else:
                    return ""

    def _has_label_tags(self, tags, tag_tids):
        count = 0
        for tid in tag_tids:
            if tags[tid]["label"] and not tags[tid]["searched"]:
                count += 1
        return count

    _DEFAULT_SIGNATURE = [
            "crypto-color-gray",
            "icon-signature-none",
            _("Unknown"),
            _("There is something unknown or wrong with this signature")]
    _STATUS_SIGNATURE = {
        "none": [
            "crypto-color-gray",
            "icon-signature-none",
            _("Not Signed"),
            _("This message contains no signature, which means it could "
              "have come from anyone, not necessarily the real sender")],
        "error": [
            "crypto-color-red",
            "icon-signature-error",
            _("Error"),
            _("There was a weird error with this signature")],
        "mixed-error": [
            "crypto-color-red",
            "icon-signature-error",
            _("Mixed Error"),
            _("Parts of this message have a signature with a weird error")],
        "invalid": [
            "crypto-color-red",
            "icon-signature-invalid",
            _("Invalid"),
            _("The signature was invalid or bad")],
        "mixed-invalid": [
            "crypto-color-red",
            "icon-signature-invalid",
            _("Mixed Invalid"),
            _("Parts of this message has a signature that are invalid"
              " or bad")],
        "revoked": [
            "crypto-color-red",
            "icon-signature-revoked",
            _("Revoked"),
            _("Watch out, the signature was made with a key that has been"
              "revoked- this is not a good thing")],
        "mixed-revoked": [
            "crypto-color-red",
            "icon-signature-revoked",
            _("Mixed Revoked"),
            _("Watch out, parts of this message were signed from a key that "
              "has been revoked")],
        "expired": [
            "crypto-color-red",
            "icon-signature-expired",
            _("Expired"),
            _("The signature was made with an expired key")],
        "mixed-expired": [
            "crypto-color-red",
            "icon-signature-expired",
            _("Mixed Expired"),
            _("Parts of this message have a signature made with an "
              "expired key")],
        "unknown": [
            "crypto-color-orange",
            "icon-signature-unknown",
            _("Unknown"),
            _("The signature was made with an unknown key, so we can not "
              "verify it")],
        "mixed-unknown": [
            "crypto-color-orange",
            "icon-signature-unknown",
            _("Mixed Unknown"),
            _("Parts of this message have a signature made with an unknown "
              "key which we can not verify")],
        "unverified": [
            "crypto-color-blue",
            "icon-signature-unverified",
            _("Unverified"),
            _("The signature was good but it came from a key that is not "
              "verified yet")],
        "mixed-unverified": [
            "crypto-color-blue",
            "icon-signature-unverified",
            _("Mixed Unverified"),
            _("Parts of this message have an unverified signature")],
        "verified": [
            "crypto-color-green",
            "icon-signature-verified",
            _("Verified"),
            _("The signature was good and came from a verified key, w00t!")],
        "mixed-verified": [
            "crypto-color-blue",
            "icon-signature-verified",
            _("Mixed Verified"),
            _("Parts of the message have a verified signature, but other "
              "parts do not")]
    }

    @classmethod
    def _show_message_signature(self, status):
        # This avoids crashes when attributes are missing.
        try:
            if status.startswith('hack the planet'):
                pass
        except UndefinedError:
            status = ''

        color, icon, text, message = self._STATUS_SIGNATURE.get(status, self._DEFAULT_SIGNATURE)

        return {
            'color': color,
            'icon': icon,
            'text': text,
            'message': message
        }

    _DEFAULT_ENCRYPTION = [
        "crypto-color-gray",
        "icon-lock-open",
        _("Unknown"),
        _("There is some unknown thing wrong with this encryption")]
    _STATUS_ENCRYPTION = {
        "none": [
            "crypto-color-gray",
            "icon-lock-open",
            _("Not Encrypted"),
            _("This message was not encrypted. It may have been intercepted "
              "and read by an unauthorized party")],
        "decrypted": [
            "crypto-color-green",
            "icon-lock-closed",
            _("Encrypted"),
            _("This message was encrypted, great job being secure")],
        "mixed-decrypted": [
            "crypto-color-blue",
            "icon-lock-closed",
            _("Mixed Encrypted"),
            _("Part of this message were encrypted, but other parts were not "
              "encrypted")],
        "missingkey": [
            "crypto-color-red",
            "icon-lock-closed",
            _("Missing Key"),
            _("You don't have any of the private keys that will decrypt this "
              "message. Perhaps it was encrypted to an old key you don't have "
              "anymore?")],
        "mixed-missingkey": [
            "crypto-color-red",
            "icon-lock-closed",
            _("Mixed Missing Key"),
            _("Parts of the message were unable to be decrypted because you "
              "are missing the private key. Perhaps it was encrypted to an "
              "old key you don't have anymore?")],
        "error": [
            "crypto-color-red",
            "icon-lock-error",
            _("Error"),
            _("We failed to decrypt message and are unsure why.")],
        "mixed-error": [
            "crypto-color-red",
            "icon-lock-error",
            _("Mixed Error"),
            _("We failed to decrypt parts of this message and are unsure why")]
    }

    @classmethod
    def _show_message_encryption(self, status):
        # This avoids crashes when attributes are missing.
        try:
            if status.startswith('hack the planet'):
                pass
        except UndefinedError:
            status = ''

        color, icon, text, message = self._STATUS_ENCRYPTION.get(status, self._DEFAULT_ENCRYPTION)

        return {
            'color': color,
            'icon': icon,
            'text': text,
            'message': message
        }

        return classes

    @classmethod
    def _contact_url(self, person):
        if 'contact' in person['flags']:
            url = "/contact/" + person['address'] + "/"
        else:
            url = "/contact/add/" + person['address'] + "/"
        return url

    @classmethod
    def _contact_name(self, profiles, person):
        name = person['fn']
        for profile in profiles:
            if profile['email'] == person['address']:
                name = _('You')
                break
        return name

    URL_RE_HTTP = re.compile('(<a [^>]*?)'            # 1: <a
                             '(href=["\'])'           # 2:    href="
                             '(https?:[^>]+)'         # 3:  URL!
                             '(["\'][^>]*>)'          # 4:          ">
                             '(.*?)'                  # 5:  Description!
                             '(</a>)')                # 6: </a>

    # We deliberately leave the https:// prefix on, because it is both
    # rare and worth drawing attention to.
    URL_RE_HTTP_PROTO = re.compile('(?i)^https?://((w+\d*|[a-z]+\d+)\.)?')

    URL_RE_MAILTO = re.compile('(<a [^>]*?)'          # 1: <a
                               '(href=["\']mailto:)'  # 2:    href="mailto:
                               '([^"]+)'              # 3:  Email address!
                               '(["\'][^>]*>)'        # 4:          ">
                               '(.*?)'                # 5:  Description!
                               '(</a>)')              # 6: </a>

    URL_DANGER_ALERT = ('onclick=\'return confirm("' +
                        _("Mailpile security tip: \\n\\n"
                          "  Uh oh! This web site may be dangerous!\\n"
                          "  Are you sure you want to continue?\\n") +
                        '");\'')

    @classmethod
    def _fix_urls(self, text, truncate=45, danger=False):
        def http_fixer(m):
            url = m.group(3)
            odesc = desc = m.group(5)
            url_danger = danger

            if len(desc) > truncate:
                desc = desc[:truncate-3] + '...'
                noproto = re.sub(self.URL_RE_HTTP_PROTO, '', desc)
                if ('/' not in noproto) and ('?' not in noproto):
                    # Phishers sometimes create subdomains that look like
                    # something legit: yourbank.evil.com.
                    # So, if the domain was getting truncated reveal the TLD
                    # even if that means overflowing our truncation request.
                    noproto = re.sub(self.URL_RE_HTTP_PROTO, '', odesc)
                    if '/' in noproto:
                        desc = '.'.join(noproto.split('/')[0]
                                        .rsplit('.', 3)[-2:]) + '/...'
                    else:
                        desc = '.'.join(noproto.split('?')[0]
                                        .rsplit('.', 3)[-2:]) + '/...'
                    url_danger = True

            return ''.join([m.group(1),
                            url_danger and self.URL_DANGER_ALERT or '',
                            ' target=_blank ',
                            m.group(2), url, m.group(4), desc, m.group(6)])

        # FIXME: Disabled for now, we will instead grab the mailto: URLs
        #        using javascript. A mailto: link is a reasonable fallback
        #        until we have a GET'able compose dialog.
        #
        #def mailto_fixer(m):
        #    return ''.join([m.group(1), 'href=\'javascript:compose("',
        #                    m.group(3), '")\'>', m.group(5), m.group(6)])
        #
        #return Markup(re.sub(self.URL_RE_HTTP, http_fixer,
        #                     re.sub(self.URL_RE_MAILTO, mailto_fixer,
        #                            text)))

        return Markup(re.sub(self.URL_RE_HTTP, http_fixer, text))

    def _urlencode(self, s):
        if type(s) == 'Markup':
            s = s.unescape()
        return Markup(urllib.quote_plus(s.encode('utf-8')))

    def _safe(self, s):
        if type(s) == 'Markup':
            return s.unescape()
        else:
            return Markup(s).unescape()

    def _json(self, d):
        return self.env.session.ui.render_json(d)

    def _nice_text(self, text):
        # trim starting & ending empty lines
        output = text.strip()
        # render markdown
        # output = markdown(output)
        return output

    @classmethod
    def _nice_subject(self, subject):
        output = re.sub('(?i)^((re|fw|fwd|aw|wg):\s+)+', '', subject)
        return output

    def _nice_name(self, name, truncate=100):
        if len(name) > truncate:
            name = name[:truncate-3] + '...'
        return name
        
    def _attachment_type(self, mime):
        if mime in [
            "application/octet-stream",
            "application/mac-binhex40",
            "application/x-shockwave-flash",
            "application/x-director",
            "application/x-x509-ca-cert",
            "application/x-director",
            "application/x-msdownload",
            "application/x-director"
            ]:
            attachment = "application"
        elif mime in [
            "application/x-compress",
            "application/x-compressed",
            "application/x-tar",
            "application/zip",
            "application/x-stuffit",
            "application/x-gzip",
            "application/x-gzip-compressed",
            "application/x-tar",
            "application/x-winzip",
            "application/x-zip",
            "application/x-zip-compressed"
            ]:
            attachment = "archive"
        elif mime in [
            "audio/midi",
            "audio/mid",
            "audio/mpeg",
            "audio/basic",
            "audio/x-aiff",
            "audio/x-pn-realaudio",
            "audio/x-pn-realaudio",
            "audio/mid",
            "audio/basic",
            "audio/x-wav",
            "audio/x-mpegurl",
            "audio/wave",
            "audio/wav"
            ]:
            attachment = "audio"
        elif mime in [
            "text/x-vcard"
            ]:
            attachment = "contact"
        elif mime in [
            "image/bmp",
            "image/gif",
            "image/jpeg",
            "image/pjpeg",
            "image/svg+xml",
            "image/x-png",
            "image/png"
            ]:
            attachment = "image-visible"
        elif mime in [
            "image/cis-cod",
            "image/ief",
            "image/pipeg",
            "image/tiff",
            "image/x-cmx",
            "image/x-cmu-raster",
            "image/x-rgb",
            "image/x-icon",
            "image/x-xbitmap",
            "image/x-xpixmap",
            "image/x-xwindowdump",
            "image/x-portable-anymap",
            "image/x-portable-graymap",
            "image/x-portable-pixmap",
            "image/x-portable-bitmap",
            "application/x-photoshop",
            "application/postscript"
            ]:
            attachment = "image"
        elif mime in [
            "application/pgp-signature"
            ]:
            attachment = "signature" 
        elif mime in [
            "application/pgp-keys"
            ]:
            attachment = "keys"
        elif mime in [
            "application/rtf",
            "application/vnd.ms-works",
            "application/msword",
            "application/pdf",
            "application/x-download",
            "message/rfc822",
            "text/scriptlet",
            "text/plain",
            "text/iuls",
            "text/plain",
            "text/richtext",
            "text/x-setext",
            "text/x-component",
            "text/webviewhtml",
            "text/h323"
            ]:
            attachment = "document"
        elif mime in [
            "application/x-javascript",
            "text/html",
            "text/css",
            "text/xml",
            "text/json"
            ]:
            attachment = "code"
        elif mime in [
            "application/excel",
            "application/msexcel",
            "application/vnd.ms-excel",
            "application/vnd.msexcel",
            "application/csv",
            "application/x-csv",
            "text/tab-separated-values",
            "text/x-comma-separated-values",
            "text/comma-separated-values",
            "text/csv",
            "text/x-csv"
            ]:
            attachment = "spreadsheet"
        elif mime in [
            "application/powerpoint",
            "application/vnd.ms-powerpoint"
            ]:
            attachment = "slideshow"
        elif mime in [
            "video/quicktime",
            "video/x-sgi-movie",
            "video/mpeg",
            "video/x-la-asf",
            "video/x-ms-asf",
            "video/x-msvideo"
            ]:
            attachment = "video"
        else:
            attachment = "unknown"
        return attachment

    def _theme_settings(self):
        path, handle, mime = self.env.session.config.open_file('html_theme', 'theme.json')
        return json.load(handle)

    def _nice_fingerprint(self, fingerprint):
        slices = [fingerprint[i:i + 4] for i in range(0, len(fingerprint), 4)]
        return slices[0] + " " + slices[1] + " " + slices[2] + " " + slices[3]

    def _make_filter_groups(self, tags):
        split = shlex.split(tags)
        output = dict();
        add = []
        remove = []
        for item in split:
            out = item.strip('+-')
            if item[0] == "+":
                add.append(out)
            elif item[0] == "-":
                remove.append(out)
        output['add'] = add
        output['remove'] = remove
        return output
########NEW FILE########
__FILENAME__ = gmvault
import mailbox
import os
import gzip
import rfc822

import mailpile.mailboxes
import mailpile.mailboxes.maildir as maildir


class MailpileMailbox(maildir.MailpileMailbox):
    """A Gmvault class that supports pickling and a few mailpile specifics."""

    @classmethod
    def parse_path(cls, config, fn, create=False):
        if os.path.isdir(fn) and os.path.exists(os.path.join(fn, 'db')):
            return (fn, )
        raise ValueError('Not a Gmvault: %s' % fn)

    def __init__(self, dirname, factory=rfc822.Message, create=True):
        maildir.MailpileMailbox.__init__(self, dirname, factory, create)
        self._paths = {'db': os.path.join(self._path, 'db')}
        self._toc_mtimes = {'db': 0}

    def get_file(self, key):
        """Return a file-like representation or raise a KeyError."""
        fname = self._lookup(key)
        if fname.endswith('.gz'):
            f = gzip.open(os.path.join(self._path, fname), 'rb')
        else:
            f = open(os.path.join(self._path, fname), 'rb')
        return mailbox._ProxyFile(f)

    def _refresh(self):
        """Update table of contents mapping."""
        # Refresh toc
        self._toc = {}
        for path in self._paths:
            for dirpath, dirnames, filenames in os.walk(self._paths[path]):
                for filename in [f for f in filenames
                                 if f.endswith(".eml.gz")
                                 or f.endswith(".eml")]:
                    self._toc[filename] = os.path.join(dirpath, filename)


mailpile.mailboxes.register(50, MailpileMailbox)

########NEW FILE########
__FILENAME__ = imap
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

from imaplib import IMAP4, IMAP4_SSL
from mailbox import Mailbox, Message

import mailpile.mailboxes
from mailpile.mailboxes import UnorderedPicklable


class IMAPMailbox(Mailbox):
    """
    Basic implementation of IMAP Mailbox. Needs a lot of work.

    As of now only get_* is implemented.
    """
    def __init__(self, host,
                 port=993, user=None, password=None, mailbox=None,
                 use_ssl=True, factory=None):
        """Initialize a Mailbox instance."""
        if use_ssl:
            self._mailbox = IMAP4_SSL(host, port)
        else:
            self._mailbox = IMAP4(host, port)
        self._mailbox.login(user, password)
        if not mailbox:
            mailbox = "INBOX"
        self.mailbox = mailbox
        self._mailbox.select(mailbox)
        self._factory = factory

    def add(self, message):
        """Add message and return assigned key."""
        # TODO(halldor): not tested...
        self._mailbox.append(self.mailbox, message=message)

    def remove(self, key):
        """Remove the keyed message; raise KeyError if it doesn't exist."""
        # TODO(halldor): not tested...
        self._mailbox.store(key, "+FLAGS", r"\Deleted")

    def __setitem__(self, key, message):
        """Replace the keyed message; raise KeyError if it doesn't exist."""
        raise NotImplementedError('Method must be implemented by subclass')

    def _get(self, key):
        typ, data = self._mailbox.fetch(key, '(RFC822)')
        response = data[0]
        if typ != "OK" or response is None:
            raise KeyError
        return response[1]

    def get_message(self, key):
        """Return a Message representation or raise a KeyError."""
        return Message(self._get(key))

    def get_bytes(self, key):
        """Return a byte string representation or raise a KeyError."""
        raise NotImplementedError('Method must be implemented by subclass')

    def get_file(self, key):
        """Return a file-like representation or raise a KeyError."""
        message = self._get(key)
        fd = StringIO.StringIO()
        fd.write(message)
        fd.seek(0)
        return fd

    def iterkeys(self):
        """Return an iterator over keys."""
        typ, data = self._mailbox.search(None, "ALL")
        return data[0].split()

    def __contains__(self, key):
        """Return True if the keyed message exists, False otherwise."""
        typ, data = self._mailbox.fetch(key, '(RFC822)')
        response = data[0]
        if response is None:
            return False
        return True

    def __len__(self):
        """Return a count of messages in the mailbox."""
        return len(self.iterkeys())

    def flush(self):
        """Write any pending changes to the disk."""
        raise NotImplementedError('Method must be implemented by subclass')

    def lock(self):
        """Lock the mailbox."""
        raise NotImplementedError('Method must be implemented by subclass')

    def unlock(self):
        """Unlock the mailbox if it is locked."""
        raise NotImplementedError('Method must be implemented by subclass')

    def close(self):
        """Flush and close the mailbox."""
        self._mailbox.close()
        self._mailbox.logout()

    # Whether each message must end in a newline
    _append_newline = False


class MailpileMailbox(UnorderedPicklable(IMAPMailbox)):
    @classmethod
    def parse_path(cls, config, path, create=False):
        if path.startswith("imap://"):
            url = path[7:]
            try:
                serverpart, mailbox = url.split("/")
            except ValueError:
                serverpart = url
                mailbox = None
            userpart, server = serverpart.split("@")
            user, password = userpart.split(":")
            # WARNING: Order must match IMAPMailbox.__init__(...)
            return (server, 993, user, password)
        raise ValueError('Not an IMAP url: %s' % path)

    def __getstate__(self):
        odict = self.__dict__.copy()
        # Pickle can't handle file and function objects.
        del odict['_mailbox']
        del odict['_save_to']
        return odict

    def get_msg_size(self, toc_id):
        # FIXME: We should make this less horrible.
        fd = self.get_file(toc_id)
        fd.seek(0, 2)
        return fd.tell()


mailpile.mailboxes.register(10, MailpileMailbox)

########NEW FILE########
__FILENAME__ = macmail
import mailbox
import sys
import os
import warnings
import rfc822
import time
import errno

import mailpile.mailboxes
from mailpile.mailboxes import UnorderedPicklable


class _MacMaildirPartialFile(mailbox._PartialFile):
    def __init__(self, fd):
        length = int(fd.readline().strip())
        start = fd.tell()
        stop = start+length
        mailbox._PartialFile.__init__(self, fd, start=start, stop=stop)


class MacMaildirMessage(mailbox.Message):
    def __init__(self, message=None):
        if hasattr(message, "read"):
            length = int(message.readline().strip())
            message = message.read(length)

        mailbox.Message.__init__(self, message)


class MacMaildir(mailbox.Mailbox):
    def __init__(self, dirname, factory=rfc822.Message, create=True):
        mailbox.Mailbox.__init__(self, dirname, factory, create)
        if not os.path.exists(self._path):
            if create:
                raise NotImplemented("Why would we support creation of "
                                     "silly mailboxes?")
            else:
                raise mailbox.NoSuchMailboxError(self._path)

        # What have we here?
        ds = os.listdir(self._path)

        # Okay, MacMaildirs have Info.plist files
        if not 'Info.plist' in ds:
            raise mailbox.FormatError(self._path)

        # Now ignore all the files and dotfiles...
        ds = [d for d in ds if not d.startswith('.')
              and os.path.isdir(os.path.join(self._path, d))]

        # There should be exactly one directory left, which is our "ID".
        if len(ds) == 1:
            self._id = ds[0]
        else:
            raise mailbox.FormatError(self._path)

        # And finally, there's a Data folder (with .emlx files  in it)
        self._mailroot = "%s/%s/Data/" % (self._path, self._id)
        if not os.path.isdir(self._mailroot):
            raise mailbox.FormatError(self._path)

        self._toc = {}
        self._last_read = 0

    def remove(self, key):
        """Remove the message or raise error if nonexistent."""
        raise NotImplemented("Mailpile is readonly, for now.")
        # FIXME: Hmm?
        #os.remove(os.path.join(self._mailroot, self._lookup(key)))

    def discard(self, key):
        """If the message exists, remove it."""
        try:
            self.remove(key)
        except KeyError:
            pass
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise

    def __setitem__(self, key, message):
        """Replace a message"""
        raise NotImplemented("Mailpile is readonly, for now.")

    def iterkeys(self):
        self._refresh()
        for key in self._toc:
            try:
                self._lookup(key)
            except KeyError:
                continue
            yield key

    def has_key(self, key):
        self._refresh()
        return key in self._toc

    def __len__(self):
        self._refresh()
        return len(self._toc)

    def _refresh(self):
        self._toc = {}
        paths = [""]

        while not paths == []:
            curpath = paths.pop(0)
            fullpath = os.path.join(self._mailroot, curpath)
            try:
                for entry in os.listdir(fullpath):
                    p = os.path.join(fullpath, entry)
                    if os.path.isdir(p):
                        paths.append(os.path.join(curpath, entry))
                    elif entry[-5:] == ".emlx":
                        self._toc[entry[:-5]] = os.path.join(curpath, entry)
            except (OSError, IOError):
                pass  # Ignore difficulties reading individual folders

    def _lookup(self, key):
        try:
            if os.path.exists(os.path.join(self._mailroot, self._toc[key])):
                return self._toc[key]
        except KeyError:
            pass
        self._refresh()
        try:
            return self._toc[key]
        except KeyError:
            raise KeyError("No message with key %s" % key)

    def get_message(self, key):
        f = open(os.path.join(self._mailroot, self._lookup(key)), 'r')
        msg = MacMaildirMessage(f)
        f.close()
        return msg

    def get_file(self, key):
        f = open(os.path.join(self._mailroot, self._lookup(key)), 'r')
        return _MacMaildirPartialFile(f)


class MailpileMailbox(UnorderedPicklable(MacMaildir)):
    """A Mac Mail.app maildir class that supports pickling etc."""
    @classmethod
    def parse_path(cls, config, fn, create=False):
        if (os.path.isdir(fn)
                and os.path.exists(os.path.join(fn, 'Info.plist'))):
            return (fn, )
        raise ValueError('Not a Mac Mail.app Maildir: %s' % fn)


mailpile.mailboxes.register(50, MailpileMailbox)

########NEW FILE########
__FILENAME__ = maildir
import mailbox
import os

import mailpile.mailboxes
from mailpile.mailboxes import UnorderedPicklable


class MailpileMailbox(UnorderedPicklable(mailbox.Maildir, editable=True)):
    """A Maildir class that supports pickling and a few mailpile specifics."""
    supported_platform = None

    @classmethod
    def parse_path(cls, config, fn, create=False):
        if (((cls.supported_platform is None) or
             (cls.supported_platform in system().lower())) and
                ((os.path.isdir(fn) and
                  os.path.exists(os.path.join(fn, 'cur'))) or
                 (create and not os.path.exists(fn)))):
            return (fn, )
        raise ValueError('Not a Maildir: %s' % fn)

    def _refresh(self):
        mailbox.Maildir._refresh(self)
        # Dotfiles are not mail. Ignore them.
        for t in [k for k in self._toc.keys() if k.startswith('.')]:
            del self._toc[t]


mailpile.mailboxes.register(25, MailpileMailbox)

########NEW FILE########
__FILENAME__ = maildirwin
import mailpile.mailboxes
import mailpile.mailboxes.maildir as maildir


class MailpileMailbox(maildir.MailpileMailbox):
    """A Maildir class for Windows (using ! instead of : in filenames)"""
    supported_platform = 'win'
    colon = '!'


mailpile.mailboxes.register(20, MailpileMailbox)

########NEW FILE########
__FILENAME__ = mbox
import mailbox
import os
import threading

import mailpile.mailboxes
from mailpile.mailboxes import MBX_ID_LEN, NoSuchMailboxError
from mailpile.util import *


class MailpileMailbox(mailbox.mbox):
    """A mbox class that supports pickling and a few mailpile specifics."""

    @classmethod
    def parse_path(cls, config, fn, create=False):
        try:
            firstline = open(fn, 'r').readline()
            if firstline.startswith('From '):
                return (fn, )
        except:
            if create and not os.path.exists(fn):
                return (fn, )
            pass
        raise ValueError('Not an mbox: %s' % fn)

    def __init__(self, *args, **kwargs):
        mailbox.mbox.__init__(self, *args, **kwargs)
        self.editable = False
        self._mtime = 0
        self._save_to = None
        self._encryption_key_func = lambda: None
        self._lock = threading.Lock()

    def _get_fd(self):
        return open(self._path, 'rb+')

    def __setstate__(self, dict):
        self.__dict__.update(dict)
        self._lock = threading.Lock()
        self._lock.acquire()
        self._save_to = None
        self._encryption_key_func = lambda: None
        try:
            try:
                if not os.path.exists(self._path):
                    raise NoSuchMailboxError(self._path)
                self._file = self._get_fd()
            except IOError, e:
                if e.errno == errno.ENOENT:
                    raise NoSuchMailboxError(self._path)
                elif e.errno == errno.EACCES:
                    self._file = self._get_fd()
                else:
                    raise
        finally:
            self._lock.release()
        self.update_toc()

    def __getstate__(self):
        odict = self.__dict__.copy()
        # Pickle can't handle function objects.
        for dk in ('_save_to', '_encryption_key_func',
                   '_file', '_lock', 'parsed'):
            if dk in odict:
                del odict[dk]
        return odict

    def update_toc(self):
        self._lock.acquire()
        try:
            fd = self._file

            # FIXME: Should also check the mtime.
            fd.seek(0, 2)
            cur_length = fd.tell()
            cur_mtime = os.path.getmtime(self._path)
            try:
                if (self._file_length == cur_length and
                        self._mtime == cur_mtime):
                    return
            except (NameError, AttributeError):
                pass

            fd.seek(0)
            self._next_key = 0
            self._toc = {}
            start = None
            while True:
                line_pos = fd.tell()
                line = fd.readline()
                if line.startswith('From '):
                    if start is not None:
                        len_nl = ('\r' == line[-2]) and 2 or 1
                        self._toc[self._next_key] = (start, line_pos - len_nl)
                        self._next_key += 1
                    start = line_pos
                elif line == '':
                    if (start is not None) and (start != line_pos):
                        self._toc[self._next_key] = (start, line_pos)
                        self._next_key += 1
                    break

            self._file_length = fd.tell()
            self._mtime = cur_mtime
        finally:
            self._lock.release()
        self.save(None)

    def save(self, session=None, to=None, pickler=None):
        if to and pickler:
            self._save_to = (pickler, to)
        if self._save_to and len(self) > 0:
            self._lock.acquire()
            try:
                pickler, fn = self._save_to
                if session:
                    session.ui.mark(_('Saving %s state to %s') % (self, fn))
                pickler(self, fn)
            finally:
                self._lock.release()

    def get_msg_size(self, toc_id):
        try:
            return self._toc[toc_id][1] - self._toc[toc_id][0]
        except (IndexError, KeyError, IndexError, TypeError):
            return 0

    def get_msg_cs(self, start, cs_size, max_length):
        self._lock.acquire()
        try:
            if start is None:
                raise IOError(_('No data found'))
            fd = self._file
            fd.seek(start, 0)
            firstKB = fd.read(min(cs_size, max_length))
            if firstKB == '':
                raise IOError(_('No data found'))
            return b64w(sha1b64(firstKB)[:4])
        finally:
            self._lock.release()

    def get_msg_cs1k(self, start, max_length):
        return self.get_msg_cs(start, 1024, max_length)

    def get_msg_cs80b(self, start, max_length):
        return self.get_msg_cs(start, 80, max_length)

    def get_msg_ptr(self, mboxid, toc_id):
        msg_start = self._toc[toc_id][0]
        msg_size = self.get_msg_size(toc_id)
        return '%s%s:%s:%s' % (mboxid,
                               b36(msg_start),
                               b36(msg_size),
                               self.get_msg_cs80b(msg_start, msg_size))

    def get_file_by_ptr(self, msg_ptr):
        parts = msg_ptr[MBX_ID_LEN:].split(':')
        start = int(parts[0], 36)
        length = int(parts[1], 36)

        # Make sure we can actually read the message
        cs80b = self.get_msg_cs80b(start, length)
        if len(parts) > 2:
            cs1k = self.get_msg_cs1k(start, length)
            cs = parts[2][:4]
            if (cs1k != cs and cs80b != cs):
                raise IOError(_('Message not found'))

        # We duplicate the file descriptor here, in case other threads are
        # accessing the same mailbox and moving it around, or in case we have
        # multiple PartialFile objects in flight at once.
        return mailbox._PartialFile(self._get_fd(), start, start + length)


mailpile.mailboxes.register(90, MailpileMailbox)

########NEW FILE########
__FILENAME__ = wervd
import email.generator
import email.message
import mailbox
import StringIO
from gettext import gettext as _

import mailpile.mailboxes
from mailpile.mailboxes import UnorderedPicklable
from mailpile.crypto.streamer import *


class MailpileMailbox(UnorderedPicklable(mailbox.Maildir, editable=True)):
    """A Maildir class that supports pickling and a few mailpile specifics."""
    supported_platform = None

    @classmethod
    def parse_path(cls, config, fn, create=False):
        if (((cls.supported_platform is None) or
             (cls.supported_platform in system().lower())) and
                ((os.path.isdir(fn) and
                  os.path.exists(os.path.join(fn, 'cur')) and
                  os.path.exists(os.path.join(fn, 'wervd.ver'))) or
                 (create and not os.path.exists(fn)))):
            return (fn, )
        raise ValueError('Not a Maildir: %s' % fn)

    def __init__(self, *args, **kwargs):
        mailbox.Maildir.__init__(self, *args, **kwargs)
        open(os.path.join(self._path, 'wervd.ver'), 'w+b').write('0')

    def remove(self, key):
        # FIXME: Remove all the copies of this message!
        os.remove(os.path.join(self._path, self._lookup(key)))

    def _refresh(self):
        mailbox.Maildir._refresh(self)
        # WERVD mail names don't have dots in them
        for t in [k for k in self._toc.keys() if '.' in k]:
            del self._toc[t]

    def _get_fd(self, key):
        fd = open(os.path.join(self._path, self._lookup(key)), 'rb')
        key = self._encryption_key_func()
        if key:
            fd = DecryptingStreamer(key, fd)
        return fd

    def get_message(self, key):
        """Return a Message representation or raise a KeyError."""
        fd = self._get_fd(key)
        try:
            if self._factory:
                return self._factory(fd)
            else:
                return mailbox.MaildirMessage(fd)
        finally:
            fd.close()

    def get_string(self, key):
        fd = None
        try:
            fd = self._get_fd(key)
            return fd.read()
        finally:
            if fd:
                fd.close()

    def get_file(self, key):
        return StringIO.StringIO(self.get_string(key))

    def add(self, message, copies=1):
        """Add message and return assigned key."""
        key = self._encryption_key_func()
        try:
            if key:
                es = EncryptingStreamer(key,
                                        dir=os.path.join(self._path, 'tmp'))
            else:
                es = ChecksummingStreamer(dir=os.path.join(self._path, 'tmp'))
            self._dump_message(message, es)
            es.finish()

            # We are using the MD5 to detect file system corruption, not in a
            # security context - so using as little as 40 bits should be fine.
            saved = False
            key = None
            for l in range(10, len(es.outer_md5sum)):
                key = es.outer_md5sum[:l]
                fn = os.path.join(self._path, 'new', key)
                if not os.path.exists(fn):
                    es.save(fn)
                    saved = self._toc[key] = os.path.join('new', key)
                    break
            if not saved:
                raise mailbox.ExternalClashError(_('Could not find a filename '
                                                   'for the message.'))

            for cpn in range(1, copies):
                fn = os.path.join(self._path, 'new', '%s.%s' % (key, cpn))
                with mailbox._create_carefully(fn) as ofd:
                    es.save_copy(ofd)

            return key
        finally:
            es.close()

    def _dump_message(self, message, target):
        if isinstance(message, email.message.Message):
            gen = email.generator.Generator(target, False, 0)
            gen.flatten(message)
        elif isinstance(message, str):
            target.write(message)
        else:
            raise TypeError(_('Invalid message type: %s') % type(message))

    def __setitem__(self, key, message):
        raise IOError(_('Mailbox messages are immutable'))


mailpile.mailboxes.register(15, MailpileMailbox)

########NEW FILE########
__FILENAME__ = mailutils
import base64
import copy
import email.header
import email.parser
import email.utils
import errno
import lxml.html
import mailbox
import mimetypes
import os
import quopri
import re
import StringIO
import threading
import traceback
from gettext import gettext as _
from email import encoders
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from lxml.html.clean import Cleaner
from mailpile.util import *
from platform import system
from urllib import quote, unquote

from mailpile.crypto.gpgi import GnuPG
from mailpile.crypto.gpgi import OpenPGPMimeSigningWrapper
from mailpile.crypto.gpgi import OpenPGPMimeEncryptingWrapper
from mailpile.crypto.mime import UnwrapMimeCrypto
from mailpile.crypto.state import EncryptionInfo, SignatureInfo
from mailpile.mail_generator import Generator
from mailpile.vcard import AddressInfo


MBX_ID_LEN = 4  # 4x36 == 1.6 million mailboxes


class NotEditableError(ValueError):
    pass


class NoFromAddressError(ValueError):
    pass


class NoRecipientError(ValueError):
    pass


class InsecureSmtpError(ValueError):
    pass


class NoSuchMailboxError(OSError):
    pass


def ParseMessage(fd, pgpmime=True):
    message = email.parser.Parser().parse(fd)
    if pgpmime and GnuPG:
        UnwrapMimeCrypto(message, protocols={
            'openpgp': GnuPG
        })
    else:
        for part in message.walk():
            part.signature_info = SignatureInfo()
            part.encryption_info = EncryptionInfo()
    return message


def ExtractEmails(string, strip_keys=True):
    emails = []
    startcrap = re.compile('^[\'\"<(]')
    endcrap = re.compile('[\'\">);]$')
    string = string.replace('<', ' <').replace('(', ' (')
    for w in [sw.strip() for sw in re.compile('[,\s]+').split(string)]:
        atpos = w.find('@')
        if atpos >= 0:
            while startcrap.search(w):
                w = w[1:]
            while endcrap.search(w):
                w = w[:-1]
            if strip_keys and '#' in w[atpos:]:
                w = w[:atpos] + w[atpos:].split('#', 1)[0]
            # E-mail addresses are only allowed to contain ASCII
            # characters, so we just strip everything else away.
            emails.append(CleanText(w,
                                    banned=CleanText.WHITESPACE,
                                    replace='_').clean)
    return emails


def ExtractEmailAndName(string):
    email = (ExtractEmails(string) or [''])[0]
    name = (string
            .replace(email, '')
            .replace('<>', '')
            .replace('"', '')
            .replace('(', '')
            .replace(')', '')).strip()
    return email, (name or email)


def MessageAsString(part, unixfrom=False):
    buf = StringIO.StringIO()
    Generator(buf).flatten(part, unixfrom=unixfrom, linesep='\r\n')
    return buf.getvalue()


def CleanMessage(config, msg):
    replacements = []
    for key, value in msg.items():
        lkey = key.lower()

        # Remove headers we don't want to expose
        if (lkey.startswith('x-mp-internal-') or
                lkey in ('bcc', 'encryption')):
            replacements.append((key, None))

        # Strip the #key part off any e-mail addresses:
        elif lkey in ('to', 'from', 'cc'):
            if '#' in value:
                replacements.append((key, re.sub(
                    r'(@[^<>\s#]+)#[a-fxA-F0-9]+([>,\s]|$)', r'\1\2', value)))

    for key, val in replacements:
        del msg[key]
    for key, val in replacements:
        if val:
            msg[key] = val

    return msg


def PrepareMessage(config, msg, sender=None, rcpts=None, events=None):
    msg = copy.deepcopy(msg)

    # Short circuit if this message has already been prepared.
    if 'x-mp-internal-sender' in msg and 'x-mp-internal-rcpts' in msg:
        return (sender or msg['x-mp-internal-sender'],
                rcpts or [r.strip()
                          for r in msg['x-mp-internal-rcpts'].split(',')],
                msg,
                events)

    crypto_policy = config.prefs.crypto_policy.lower()
    rcpts = rcpts or []

    # Iterate through headers to figure out what we want to do...
    need_rcpts = not rcpts
    for hdr, val in msg.items():
        lhdr = hdr.lower()
        if lhdr == 'from':
            sender = sender or val
        elif lhdr == 'encryption':
            crypto_policy = val.lower()
        elif need_rcpts and lhdr in ('to', 'cc', 'bcc'):
            rcpts += ExtractEmails(val, strip_keys=False)

    # Are we sane?
    if not sender:
        raise NoFromAddressError()
    if not rcpts:
        raise NoRecipientError()

    # Are we encrypting? Signing?
    if crypto_policy == 'default':
        crypto_policy = config.prefs.crypto_policy

    # This is the BCC hack that Brennan hates!
    if config.prefs.always_bcc_self:
        rcpts += [sender]

    sender = ExtractEmails(sender, strip_keys=False)[0]
    sender_keyid = None
    if config.prefs.openpgp_header:
        try:
            gnupg = GnuPG()
            seckeys = dict([(uid["email"], fp) for fp, key
                            in gnupg.list_secret_keys().iteritems()
                            if key["capabilities_map"][0].get("encrypt")
                            and key["capabilities_map"][0].get("sign")
                            for uid in key["uids"]])
            sender_keyid = seckeys.get(sender)
        except (KeyError, TypeError, IndexError, ValueError):
            traceback.print_exc()

    rcpts, rr = [sender], rcpts
    for r in rr:
        for e in ExtractEmails(r, strip_keys=False):
            if e not in rcpts:
                rcpts.append(e)

    # Add headers we require
    if 'date' not in msg:
        msg['Date'] = email.utils.formatdate()

    if sender_keyid and config.prefs.openpgp_header:
        msg["OpenPGP"] = "id=%s; preference=%s" % (sender_keyid,
                                                   config.prefs.openpgp_header)

    if 'openpgp' in crypto_policy:

        # FIXME: Make a more efficient sign+encrypt wrapper

        cleaner = lambda m: CleanMessage(config, m)
        if 'sign' in crypto_policy:
            msg = OpenPGPMimeSigningWrapper(config,
                                            sender=sender,
                                            cleaner=cleaner,
                                            recipients=rcpts).wrap(msg)
        if 'encrypt' in crypto_policy:
            msg = OpenPGPMimeEncryptingWrapper(config,
                                               sender=sender,
                                               cleaner=cleaner,
                                               recipients=rcpts).wrap(msg)

    rcpts = set([r.rsplit('#', 1)[0] for r in rcpts])
    msg['x-mp-internal-readonly'] = str(int(time.time()))
    msg['x-mp-internal-sender'] = sender
    msg['x-mp-internal-rcpts'] = ', '.join(rcpts)
    return (sender, rcpts, msg, events)


MUA_HEADERS = ('date', 'from', 'to', 'cc', 'subject', 'message-id', 'reply-to',
               'mime-version', 'content-disposition', 'content-type',
               'user-agent', 'list-id', 'list-subscribe', 'list-unsubscribe',
               'x-ms-tnef-correlator', 'x-ms-has-attach')
DULL_HEADERS = ('in-reply-to', 'references')


def HeaderPrintHeaders(message):
    """Extract message headers which identify the MUA."""
    headers = [k for k, v in message.items()]

    # The idea here, is that MTAs will probably either prepend or append
    # headers, not insert them in the middle. So we strip things off the
    # top and bottom of the header until we see something we are pretty
    # comes from the MUA itself.
    while headers and headers[0].lower() not in MUA_HEADERS:
        headers.pop(0)
    while headers and headers[-1].lower() not in MUA_HEADERS:
        headers.pop(-1)

    # Finally, we return the "non-dull" headers, the ones we think will
    # uniquely identify this particular mailer and won't vary too much
    # from message-to-message.
    return [h for h in headers if h.lower() not in DULL_HEADERS]


def HeaderPrint(message):
    """Generate a fingerprint from message headers which identifies the MUA."""
    return b64w(sha1b64('\n'.join(HeaderPrintHeaders(message)))).lower()


class Email(object):
    """This is a lazy-loading object representing a single email."""

    def __init__(self, idx, msg_idx_pos,
                 msg_parsed=None, msg_parsed_pgpmime=None,
                 msg_info=None, ephemeral_mid=None):
        self.index = idx
        self.config = idx.config
        self.msg_idx_pos = msg_idx_pos
        self.ephemeral_mid = ephemeral_mid
        self.reset_caches(msg_parsed=msg_parsed,
                          msg_parsed_pgpmime=msg_parsed_pgpmime,
                          msg_info=msg_info)

    def msg_mid(self):
        return self.ephemeral_mid or b36(self.msg_idx_pos)

    @classmethod
    def encoded_hdr(self, msg, hdr, value=None):
        hdr_value = value or (msg and msg.get(hdr)) or ''
        try:
            hdr_value.encode('us-ascii')
        except:
            if hdr.lower() in ('from', 'to', 'cc', 'bcc'):
                addrs = []
                for addr in [a.strip() for a in hdr_value.split(',')]:
                    name, part = [], []
                    words = addr.split()
                    for w in words:
                        if w[0] == '<' or '@' in w:
                            part.append((w, 'us-ascii'))
                        else:
                            name.append(w)
                    if name:
                        name = ' '.join(name)
                        try:
                            part[0:0] = [(name.encode('us-ascii'), 'us-ascii')]
                        except:
                            part[0:0] = [(name, 'utf-8')]
                        addrs.append(email.header.make_header(part).encode())
                hdr_value = ', '.join(addrs)
            else:
                parts = [(hdr_value, 'utf-8')]
                hdr_value = email.header.make_header(parts).encode()
        return hdr_value

    @classmethod
    def Create(cls, idx, mbox_id, mbx,
               msg_to=None, msg_cc=None, msg_bcc=None, msg_from=None,
               msg_subject=None, msg_text=None, msg_references=None,
               save=True, ephemeral_mid='not-saved', append_sig=True):
        msg = MIMEMultipart()
        msg.signature_info = SignatureInfo()
        msg.encryption_info = EncryptionInfo()
        msg_ts = int(time.time())

        if not msg_from:
            msg_from = idx.config.get_profile().get('email', None)
            from_name = idx.config.get_profile().get('name', None)
            if msg_from and from_name:
                msg_from = '%s <%s>' % (from_name, msg_from)
        if not msg_from:
            raise NoFromAddressError()

        msg['From'] = cls.encoded_hdr(None, 'from', value=msg_from)
        msg['Date'] = email.utils.formatdate(msg_ts)
        msg['Message-Id'] = email.utils.make_msgid('mailpile')
        msg_subj = (msg_subject or '')
        msg['Subject'] = cls.encoded_hdr(None, 'subject', value=msg_subj)
        if msg_to:
            msg['To'] = cls.encoded_hdr(None, 'to',
                                        value=', '.join(set(msg_to)))
        if msg_cc:
            msg['Cc'] = cls.encoded_hdr(None, 'cc',
                                        value=', '.join(set(msg_cc)))
        if msg_bcc:
            msg['Bcc'] = cls.encoded_hdr(None, 'bcc',
                                         value=', '.join(set(msg_bcc)))
        if msg_references:
            msg['In-Reply-To'] = msg_references[-1]
            msg['References'] = ', '.join(msg_references)

        if msg_text:
            try:
                msg_text.encode('us-ascii')
                charset = 'us-ascii'
            except UnicodeEncodeError:
                charset = 'utf-8'
            textpart = MIMEText(msg_text, _subtype='plain', _charset=charset)
            textpart.signature_info = SignatureInfo()
            textpart.encryption_info = EncryptionInfo()
            msg.attach(textpart)
            del textpart['MIME-Version']

        if append_sig:
            sig = idx.config.get_profile().get('signature', '')
            if sig not in ['', None]:
                try:
                    sig.encode('us-ascii')
                    charset = 'us-ascii'
                except UnicodeEncodeError:
                    charset = 'utf-8'
                textpart = MIMEText(sig, _subtype='plain', _charset=charset)
                textpart.signature_info = SignatureInfo()
                textpart.encryption_info = EncryptionInfo()
                msg.attach(textpart)
                del textpart['MIME-Version']

        if save:
            msg_key = mbx.add(msg)
            msg_to = msg_cc = []
            msg_ptr = mbx.get_msg_ptr(mbox_id, msg_key)
            msg_id = idx.get_msg_id(msg, msg_ptr)
            msg_idx, msg_info = idx.add_new_msg(msg_ptr, msg_id, msg_ts,
                                                msg_from, msg_to, msg_cc, 0,
                                                msg_subj, '', [])
            idx.set_conversation_ids(msg_info[idx.MSG_MID], msg,
                                     subject_threading=False)
            return cls(idx, msg_idx)
        else:
            msg_info = idx.edit_msg_info(idx.BOGUS_METADATA[:],
                                         msg_mid=ephemeral_mid or '',
                                         msg_id=msg['Message-ID'],
                                         msg_ts=msg_ts,
                                         msg_subject=msg_subj,
                                         msg_from=msg_from,
                                         msg_to=msg_to,
                                         msg_cc=msg_cc)
            return cls(idx, -1,
                       msg_info=msg_info,
                       msg_parsed=msg, msg_parsed_pgpmime=msg,
                       ephemeral_mid=ephemeral_mid)

    def is_editable(self):
        return (self.ephemeral_mid or
                self.config.is_editable_message(self.get_msg_info()))

    MIME_HEADERS = ('mime-version', 'content-type', 'content-disposition',
                    'content-transfer-encoding')
    UNEDITABLE_HEADERS = ('message-id', ) + MIME_HEADERS
    MANDATORY_HEADERS = ('From', 'To', 'Cc', 'Bcc', 'Subject', 'Encryption')
    HEADER_ORDER = {
        'in-reply-to': -2,
        'references': -1,
        'date': 1,
        'from': 2,
        'subject': 3,
        'to': 4,
        'cc': 5,
        'bcc': 6,
        'encryption': 99,
    }

    def get_editing_strings(self, tree=None):
        tree = tree or self.get_message_tree()
        strings = {
            'from': '', 'to': '', 'cc': '', 'bcc': '', 'subject': '',
            'encryption': '', 'attachments': {}
        }
        header_lines = []
        body_lines = []

        # We care about header order and such things...
        hdrs = dict([(h.lower(), h) for h in tree['headers'].keys()
                     if h.lower() not in self.UNEDITABLE_HEADERS])
        for mandate in self.MANDATORY_HEADERS:
            hdrs[mandate.lower()] = hdrs.get(mandate.lower(), mandate)
        keys = hdrs.keys()
        keys.sort(key=lambda k: (self.HEADER_ORDER.get(k, 99), k))
        lowman = [m.lower() for m in self.MANDATORY_HEADERS]
        for hdr in [hdrs[k] for k in keys]:
            data = tree['headers'].get(hdr, '')
            if hdr.lower() in lowman:
                strings[hdr.lower()] = unicode(data)
            else:
                header_lines.append(unicode('%s: %s' % (hdr, data)))

        for att in tree['attachments']:
            strings['attachments'][att['count']] = (att['filename']
                                                    or '(unnamed)')

        if not strings['encryption']:
            strings['encryption'] = unicode(self.config.prefs.crypto_policy)

        def _fixup(t):
            try:
                return unicode(t)
            except UnicodeDecodeError:
                return t.decode('utf-8')

        strings['headers'] = '\n'.join(header_lines).replace('\r\n', '\n')
        strings['body'] = unicode(''.join([_fixup(t['data'])
                                           for t in tree['text_parts']])
                                  ).replace('\r\n', '\n')
        return strings

    def get_editing_string(self, tree=None):
        tree = tree or self.get_message_tree()
        estrings = self.get_editing_strings(tree)
        bits = [estrings['headers']]
        for mh in self.MANDATORY_HEADERS:
            bits.append('%s: %s' % (mh, estrings[mh.lower()]))
        bits.append('')
        bits.append(estrings['body'])
        return '\n'.join(bits)

    def make_attachment(self, fn, filedata=None):
        if filedata and fn in filedata:
            data = filedata[fn]
        else:
            data = open(fn, 'rb').read()
        ctype, encoding = mimetypes.guess_type(fn)
        maintype, subtype = (ctype or 'application/octet-stream').split('/', 1)
        if maintype == 'image':
            att = MIMEImage(data, _subtype=subtype)
        else:
            att = MIMEBase(maintype, subtype)
            att.set_payload(data)
            encoders.encode_base64(att)
        att.add_header('Content-Disposition', 'attachment',
                       filename=os.path.basename(fn))
        return att

    def add_attachments(self, session, filenames, filedata=None):
        if not self.is_editable():
            raise NotEditableError(_('Mailbox is read-only.'))
        msg = self.get_msg()
        if 'x-mp-internal-readonly' in msg:
            raise NotEditableError(_('Message is read-only.'))
        for fn in filenames:
            msg.attach(self.make_attachment(fn, filedata=filedata))
        return self.update_from_msg(session, msg)

    def update_from_string(self, session, data, final=False):
        if not self.is_editable():
            raise NotEditableError(_('Mailbox is read-only.'))

        oldmsg = self.get_msg()
        if 'x-mp-internal-readonly' in oldmsg:
            raise NotEditableError(_('Message is read-only.'))

        if not data:
            outmsg = oldmsg

        else:
            newmsg = email.parser.Parser().parsestr(data.encode('utf-8'))
            outmsg = MIMEMultipart()

            # Copy over editable headers from the input string, skipping blanks
            for hdr in newmsg.keys():
                if hdr.startswith('Attachment-'):
                    pass
                else:
                    encoded_hdr = self.encoded_hdr(newmsg, hdr)
                    if len(encoded_hdr.strip()) > 0:
                        outmsg[hdr] = encoded_hdr

            # Copy over the uneditable headers from the old message
            for hdr in oldmsg.keys():
                if ((hdr.lower() not in self.MIME_HEADERS)
                        and (hdr.lower() in self.UNEDITABLE_HEADERS)):
                    outmsg[hdr] = oldmsg[hdr]

            # Copy the message text
            new_body = newmsg.get_payload().decode('utf-8')
            if final:
                new_body = split_long_lines(new_body)
            try:
                new_body.encode('us-ascii')
                charset = 'us-ascii'
            except:
                charset = 'utf-8'
            textbody = MIMEText(new_body, _subtype='plain', _charset=charset)
            outmsg.attach(textbody)
            del textbody['MIME-Version']

            # FIXME: Use markdown and template to generate fancy HTML part

            # Copy the attachments we are keeping
            attachments = [h for h in newmsg.keys()
                           if h.startswith('Attachment-')]
            if attachments:
                oldtree = self.get_message_tree()
                for att in oldtree['attachments']:
                    hdr = 'Attachment-%s' % att['count']
                    if hdr in attachments:
                        # FIXME: Update the filename to match whatever
                        #        the user typed
                        outmsg.attach(att['part'])
                        attachments.remove(hdr)

            # Attach some new files?
            for hdr in attachments:
                try:
                    outmsg.attach(self.make_attachment(newmsg[hdr]))
                except:
                    pass  # FIXME: Warn user that failed...

        # Save result back to mailbox
        if final:
            sender, rcpts, outmsg, ev = PrepareMessage(self.config, outmsg)
        return self.update_from_msg(session, outmsg)

    def update_from_msg(self, session, newmsg):
        if not self.is_editable():
            raise NotEditableError(_('Mailbox is read-only.'))

        mbx, ptr, fd = self.get_mbox_ptr_and_fd()

        # OK, adding to the mailbox worked
        newptr = ptr[:MBX_ID_LEN] + mbx.add(newmsg)

        # Remove the old message...
        mbx.remove(ptr[MBX_ID_LEN:])

        # FIXME: We should DELETE the old version from the index first.

        # Update the in-memory-index
        mi = self.get_msg_info()
        mi[self.index.MSG_PTRS] = newptr
        self.index.set_msg_at_idx_pos(self.msg_idx_pos, mi)
        self.index.index_email(session, Email(self.index, self.msg_idx_pos))

        self.reset_caches()
        return self

    def reset_caches(self,
                     msg_info=None, msg_parsed=None, msg_parsed_pgpmime=None):
        self.msg_info = msg_info
        self.msg_parsed = msg_parsed
        self.msg_parsed_pgpmime = msg_parsed_pgpmime

    def get_msg_info(self, field=None):
        if not self.msg_info:
            self.msg_info = self.index.get_msg_at_idx_pos(self.msg_idx_pos)
        if field is None:
            return self.msg_info
        else:
            return self.msg_info[field]

    def get_mbox_ptr_and_fd(self):
        for msg_ptr in self.get_msg_info(self.index.MSG_PTRS).split(','):
            if msg_ptr == '':
                continue
            try:
                mbox = self.config.open_mailbox(None, msg_ptr[:MBX_ID_LEN])
                fd = mbox.get_file_by_ptr(msg_ptr)
                # FIXME: How do we know we have the right message?
                return mbox, msg_ptr, fd
            except (IOError, OSError, KeyError, ValueError, IndexError):
                # FIXME: If this pointer is wrong, should we fix the index?
                print 'WARNING: %s not found' % msg_ptr
        return None, None, None

    def get_file(self):
        return self.get_mbox_ptr_and_fd()[2]

    def get_msg_size(self):
        mbox, ptr, fd = self.get_mbox_ptr_and_fd()
        fd.seek(0, 2)
        return fd.tell()

    def _get_parsed_msg(self, pgpmime):
        fd = self.get_file()
        if fd:
            return ParseMessage(fd, pgpmime=pgpmime)

    def get_msg(self, pgpmime=True):
        if pgpmime:
            if not self.msg_parsed_pgpmime:
                self.msg_parsed_pgpmime = self._get_parsed_msg(pgpmime)
            result = self.msg_parsed_pgpmime
        else:
            if not self.msg_parsed:
                self.msg_parsed = self._get_parsed_msg(pgpmime)
            result = self.msg_parsed
        if not result:
            raise IndexError(_('Message not found?'))
        return result

    def get_headerprint(self):
        return HeaderPrint(self.get_msg())

    def is_thread(self):
        return ((self.get_msg_info(self.index.MSG_THREAD_MID)) or
                (0 < len(self.get_msg_info(self.index.MSG_REPLIES))))

    def get(self, field, default=''):
        """Get one (or all) indexed fields for this mail."""
        field = field.lower()
        if field == 'subject':
            return self.get_msg_info(self.index.MSG_SUBJECT)
        elif field == 'from':
            return self.get_msg_info(self.index.MSG_FROM)
        else:
            raw = ' '.join(self.get_msg().get_all(field, default))
            return self.index.hdr(0, 0, value=raw) or raw

    def get_msg_summary(self):
        # We do this first to make sure self.msg_info is loaded
        msg_mid = self.get_msg_info(self.index.MSG_MID)
        return [
            msg_mid,
            self.get_msg_info(self.index.MSG_ID),
            self.get_msg_info(self.index.MSG_FROM),
            self.index.expand_to_list(self.msg_info),
            self.get_msg_info(self.index.MSG_SUBJECT),
            self.get_msg_info(self.index.MSG_BODY),
            self.get_msg_info(self.index.MSG_DATE),
            self.get_msg_info(self.index.MSG_TAGS).split(','),
            self.is_editable()
        ]

    def extract_attachment(self, session, att_id,
                           name_fmt=None, mode='download'):
        msg = self.get_msg()
        count = 0
        extracted = 0
        filename, attributes = '', {}
        for part in (msg.walk() if msg else []):
            mimetype = part.get_content_type()
            if mimetype.startswith('multipart/'):
                continue

            content_id = part.get('content-id', '')
            pfn = part.get_filename() or ''
            count += 1

            if (('*' == att_id)
                    or ('#%s' % count == att_id)
                    or ('part:%s' % count == att_id)
                    or (content_id == att_id)
                    or (mimetype == att_id)
                    or (pfn.lower().endswith('.%s' % att_id))
                    or (pfn == att_id)):

                payload = part.get_payload(None, True) or ''
                attributes = {
                    'msg_mid': self.msg_mid(),
                    'count': count,
                    'length': len(payload),
                    'content-id': content_id,
                    'filename': pfn,
                }
                if pfn:
                    if '.' in pfn:
                        pfn, attributes['att_ext'] = pfn.rsplit('.', 1)
                        attributes['att_ext'] = attributes['att_ext'].lower()
                    attributes['att_name'] = pfn
                if mimetype:
                    attributes['mimetype'] = mimetype

                filesize = len(payload)
                if mode.startswith('inline'):
                    attributes['data'] = payload
                    session.ui.notify(_('Extracted attachment %s') % att_id)
                elif mode.startswith('preview'):
                    attributes['thumb'] = True
                    attributes['mimetype'] = 'image/jpeg'
                    attributes['disposition'] = 'inline'
                    thumb = StringIO.StringIO()
                    if thumbnail(payload, thumb, height=250):
                        session.ui.notify(_('Wrote preview to: %s') % filename)
                        attributes['length'] = thumb.tell()
                        filename, fd = session.ui.open_for_data(
                            name_fmt=name_fmt, attributes=attributes)
                        thumb.seek(0)
                        fd.write(thumb.read())
                        fd.close()
                    else:
                        session.ui.notify(_('Failed to generate thumbnail'))
                        raise UrlRedirectException('/static/img/image-default.png')
                else:
                    filename, fd = session.ui.open_for_data(
                        name_fmt=name_fmt, attributes=attributes)
                    fd.write(payload)
                    session.ui.notify(_('Wrote attachment to: %s') % filename)
                    fd.close()
                extracted += 1
        if 0 == extracted:
            session.ui.notify(_('No attachments found for: %s') % att_id)
            return None, None
        else:
            return filename, attributes

    def get_message_tags(self):
        tids = self.get_msg_info(self.index.MSG_TAGS).split(',')
        return [self.config.get_tag(t) for t in tids]

    RE_HTML_BORING = re.compile('(\s+|<style[^>]*>[^<>]*</style>)')
    RE_EXCESS_WHITESPACE = re.compile('\n\s*\n\s*')
    RE_HTML_NEWLINES = re.compile('(<br|</(tr|table))')
    RE_HTML_PARAGRAPHS = re.compile('(</?p|</?(title|div|html|body))')
    RE_HTML_LINKS = re.compile('<a\s+[^>]*href=[\'"]?([^\'">]+)[^>]*>'
                               '([^<]*)</a>')
    RE_HTML_IMGS = re.compile('<img\s+[^>]*src=[\'"]?([^\'">]+)[^>]*>')
    RE_HTML_IMG_ALT = re.compile('<img\s+[^>]*alt=[\'"]?([^\'">]+)[^>]*>')

    def _extract_text_from_html(self, html):
        try:
            # We compensate for some of the limitations of lxml...
            links, imgs = [], []
            def delink(m):
                url, txt = m.group(1), m.group(2).strip()
                if txt[:4] in ('http', 'www.'):
                    return txt
                elif url.startswith('mailto:'):
                    if '@' in txt:
                        return txt
                    else:
                        return '%s (%s)' % (txt, url.split(':', 1)[1])
                else:
                    links.append(' [%d] %s%s' % (len(links) + 1,
                                                 txt and (txt + ': ') or '',
                                                 url))
                    return '%s[%d]' % (txt, len(links))
            def deimg(m):
                tag, url = m.group(0), m.group(1)
                if ' alt=' in tag:
                    return re.sub(self.RE_HTML_IMG_ALT, '\1', tag).strip()
                else:
                    imgs.append(' [%d] %s' % (len(imgs)+1, url))
                    return '[Image %d]' % len(imgs)
            html = re.sub(self.RE_HTML_PARAGRAPHS, '\n\n\\1',
                       re.sub(self.RE_HTML_NEWLINES, '\n\\1',
                           re.sub(self.RE_HTML_BORING, ' ',
                               re.sub(self.RE_HTML_LINKS, delink,
                                   re.sub(self.RE_HTML_IMGS, deimg, html)))))
            text = (lxml.html.fromstring(html).text_content() +
                    (links and '\n\nLinks:\n' or '') + '\n'.join(links) +
                    (imgs and '\n\nImages:\n' or '') + '\n'.join(imgs))
            return re.sub(self.RE_EXCESS_WHITESPACE, '\n\n', text).strip()
        except:
            import traceback
            traceback.print_exc()
            return html

    def get_message_tree(self, want=None):
        msg = self.get_msg()
        tree = {
            'id': self.get_msg_info(self.index.MSG_ID)
        }

        for p in 'text_parts', 'html_parts', 'attachments':
            if want is None or p in want:
                tree[p] = []

        if want is None or 'summary' in want:
            tree['summary'] = self.get_msg_summary()

        if want is None or 'tags' in want:
            tree['tags'] = self.get_msg_info(self.index.MSG_TAGS).split(',')

        if want is None or 'conversation' in want:
            tree['conversation'] = {}
            conv_id = self.get_msg_info(self.index.MSG_THREAD_MID)
            if conv_id:
                conv = Email(self.index, int(conv_id, 36))
                tree['conversation'] = convs = [conv.get_msg_summary()]
                for rid in conv.get_msg_info(self.index.MSG_REPLIES
                                             ).split(','):
                    if rid:
                        convs.append(Email(self.index, int(rid, 36)
                                           ).get_msg_summary())

        if (want is None
                or 'headers' in want
                or 'editing_string' in want
                or 'editing_strings' in want):
            tree['headers'] = {}
            for hdr in msg.keys():
                tree['headers'][hdr] = self.index.hdr(msg, hdr)

        if want is None or 'headers_lc' in want:
            tree['headers_lc'] = {}
            for hdr in msg.keys():
                tree['headers_lc'][hdr.lower()] = self.index.hdr(msg, hdr)

        if want is None or 'header_list' in want:
            tree['header_list'] = [(k, self.index.hdr(msg, k, value=v))
                                   for k, v in msg.items()]

        if want is None or 'addresses' in want:
            tree['addresses'] = {}
            for hdr in msg.keys():
                hdrl = hdr.lower()
                if hdrl in ('reply-to', 'from', 'to', 'cc', 'bcc'):
                    tree['addresses'][hdrl] = AddressHeaderParser(msg[hdr])

        # FIXME: Decide if this is strict enough or too strict...?
        html_cleaner = Cleaner(page_structure=True, meta=True, links=True,
                               javascript=True, scripts=True, frames=True,
                               embedded=True, safe_attrs_only=True)

        # Note: count algorithm must match that used in extract_attachment
        #       above
        count = 0
        for part in msg.walk():
            mimetype = part.get_content_type()
            if (mimetype.startswith('multipart/')
                    or mimetype == "application/pgp-encrypted"):
                continue
            try:
                if (mimetype == "application/octet-stream"
                        and part.cryptedcontainer is True):
                    continue
            except:
                pass

            count += 1
            if (part.get('content-disposition', 'inline') == 'inline'
                    and mimetype in ('text/plain', 'text/html')):
                payload, charset = self.decode_payload(part)
                start = payload[:100].strip()

                if mimetype == 'text/html':
                    if want is None or 'html_parts' in want:
                        tree['html_parts'].append({
                            'charset': charset,
                            'type': 'html',
                            'data': ((payload.strip()
                                      and html_cleaner.clean_html(payload))
                                     or '')
                        })

                elif want is None or 'text_parts' in want:
                    if start[:3] in ('<di', '<ht', '<p>', '<p ', '<ta', '<bo'):
                        payload = self._extract_text_from_html(payload)
                    # Ignore white-space only text parts, they usually mean
                    # the message is HTML only and we want the code below
                    # to try and extract meaning from it.
                    if (start or payload.strip()) != '':
                        text_parts = self.parse_text_part(payload, charset)
                        tree['text_parts'].extend(text_parts)

            elif want is None or 'attachments' in want:
                tree['attachments'].append({
                    'mimetype': mimetype,
                    'count': count,
                    'part': part,
                    'length': len(part.get_payload(None, True) or ''),
                    'content-id': part.get('content-id', ''),
                    'filename': part.get_filename() or ''
                })

        if want is None or 'text_parts' in want:
            if tree.get('html_parts') and not tree.get('text_parts'):
                html_part = tree['html_parts'][0]
                payload = self._extract_text_from_html(html_part['data'])
                text_parts = self.parse_text_part(payload,
                                                  html_part['charset'])
                tree['text_parts'].extend(text_parts)

        if self.is_editable():
            if not want or 'editing_strings' in want:
                tree['editing_strings'] = self.get_editing_strings(tree)
            if not want or 'editing_string' in want:
                tree['editing_string'] = self.get_editing_string(tree)

        if want is None or 'crypto' in want:
            if 'crypto' not in tree:
                tree['crypto'] = {'encryption': msg.encryption_info,
                                  'signature': msg.signature_info}
            else:
                tree['crypto']['encryption'] = msg.encryption_info
                tree['crypto']['signature'] = msg.signature_info

        return tree

    # FIXME: This should be configurable by the user, depending on where
    #        he lives and what kind of e-mail he gets.
    CHARSET_PRIORITY_LIST = ['utf-8', 'iso-8859-1']

    def decode_text(self, payload, charset='utf-8', binary=True):
        if charset:
            charsets = [charset] + [c for c in self.CHARSET_PRIORITY_LIST
                                    if charset.lower() != c]
        else:
            charsets = self.CHARSET_PRIORITY_LIST

        for charset in charsets:
            try:
                payload = payload.decode(charset)
                return payload, charset
            except (UnicodeDecodeError, TypeError, LookupError):
                pass

        if binary:
            return payload, '8bit'
        else:
            return _('[Binary data suppressed]\n'), 'utf-8'

    def decode_payload(self, part):
        charset = part.get_content_charset() or None
        payload = part.get_payload(None, True) or ''
        return self.decode_text(payload, charset=charset)

    def parse_text_part(self, data, charset):
        current = {
            'type': 'bogus',
            'charset': charset,
        }
        parse = []
        block = 'body'
        clines = []
        for line in data.splitlines(True):
            block, ltype = self.parse_line_type(line, block)
            if ltype != current['type']:

                # This is not great, it's a hack to move the preamble
                # before a quote section into the quote itself.
                if ltype == 'quote' and clines and '@' in clines[-1]:
                    current['data'] = ''.join(clines[:-1])
                    clines = clines[-1:]
                elif (ltype == 'quote' and len(clines) > 2
                        and '@' in clines[-2] and '' == clines[-1].strip()):
                    current['data'] = ''.join(clines[:-2])
                    clines = clines[-2:]
                else:
                    clines = []

                current = {
                    'type': ltype,
                    'data': ''.join(clines),
                    'charset': charset,
                }
                parse.append(current)
            current['data'] += line
            clines.append(line)
        return parse

    def parse_line_type(self, line, block):
        # FIXME: Detect forwarded messages, ...

        if block in ('body', 'quote') and line in ('-- \n', '-- \r\n'):
            return 'signature', 'signature'

        if block == 'signature':
            return 'signature', 'signature'

        stripped = line.rstrip()

        if stripped == '-----BEGIN PGP SIGNED MESSAGE-----':
            return 'pgpbeginsigned', 'pgpbeginsigned'
        if block == 'pgpbeginsigned':
            if line.startswith('Hash: ') or stripped == '':
                return 'pgpbeginsigned', 'pgpbeginsigned'
            else:
                return 'pgpsignedtext', 'pgpsignedtext'
        if block == 'pgpsignedtext':
            if (stripped == '-----BEGIN PGP SIGNATURE-----'):
                return 'pgpsignature', 'pgpsignature'
            else:
                return 'pgpsignedtext', 'pgpsignedtext'
        if block == 'pgpsignature':
            if stripped == '-----END PGP SIGNATURE-----':
                return 'pgpend', 'pgpsignature'
            else:
                return 'pgpsignature', 'pgpsignature'

        if stripped == '-----BEGIN PGP MESSAGE-----':
            return 'pgpbegin', 'pgpbegin'
        if block == 'pgpbegin':
            if ':' in line or stripped == '':
                return 'pgpbegin', 'pgpbegin'
            else:
                return 'pgptext', 'pgptext'
        if block == 'pgptext':
            if stripped == '-----END PGP MESSAGE-----':
                return 'pgpend', 'pgpend'
            else:
                return 'pgptext', 'pgptext'

        if block == 'quote':
            if stripped == '':
                return 'quote', 'quote'
        if line.startswith('>'):
            return 'quote', 'quote'

        return 'body', 'text'

    WANT_MSG_TREE_PGP = ('text_parts', 'crypto')
    PGP_OK = {
        'pgpbeginsigned': 'pgpbeginverified',
        'pgpsignedtext': 'pgpverifiedtext',
        'pgpsignature': 'pgpverification',
        'pgpbegin': 'pgpbeginverified',
        'pgptext': 'pgpsecuretext',
        'pgpend': 'pgpverification',
    }

    def evaluate_pgp(self, tree, check_sigs=True, decrypt=False):
        if 'text_parts' not in tree:
            return tree

        pgpdata = []
        for part in tree['text_parts']:
            if 'crypto' not in part:
                part['crypto'] = {}

            ei = si = None
            if check_sigs:
                if part['type'] == 'pgpbeginsigned':
                    pgpdata = [part]
                elif part['type'] == 'pgpsignedtext':
                    pgpdata.append(part)
                elif part['type'] == 'pgpsignature':
                    pgpdata.append(part)
                    try:
                        gpg = GnuPG()
                        message = ''.join([p['data'].encode(p['charset'])
                                           for p in pgpdata])
                        si = pgpdata[1]['crypto']['signature'
                                                  ] = gpg.verify(message)
                        pgpdata[0]['data'] = ''
                        pgpdata[2]['data'] = ''

                    except Exception, e:
                        print e

            if decrypt:
                if part['type'] in ('pgpbegin', 'pgptext'):
                    pgpdata.append(part)
                elif part['type'] == 'pgpend':
                    pgpdata.append(part)

                    gpg = GnuPG()
                    (signature_info, encryption_info, text
                     ) = gpg.decrypt(''.join([p['data'] for p in pgpdata]))

                    # FIXME: If the data is binary, we should provide some
                    #        sort of download link or maybe leave the PGP
                    #        blob entirely intact, undecoded.
                    text, charset = self.decode_text(text, binary=False)

                    ei = pgpdata[1]['crypto']['encryption'] = encryption_info
                    si = pgpdata[1]['crypto']['signature'] = signature_info
                    if encryption_info["status"] == "decrypted":
                        pgpdata[1]['data'] = text
                        pgpdata[0]['data'] = ""
                        pgpdata[2]['data'] = ""

            # Bubbling up!
            if (si or ei) and 'crypto' not in tree:
                tree['crypto'] = {'signature': SignatureInfo(),
                                  'encryption': EncryptionInfo()}
            if si:
                tree['crypto']['signature'].mix(si)
            if ei:
                tree['crypto']['encryption'].mix(ei)

        # Cleanup, remove empty 'crypto': {} blocks.
        for part in tree['text_parts']:
            if not part['crypto']:
                del part['crypto']

        return tree

    def _decode_gpg(self, message, decrypted):
        header, body = message.replace('\r\n', '\n').split('\n\n', 1)
        for line in header.lower().split('\n'):
            if line.startswith('charset:'):
                return decrypted.decode(line.split()[1])
        return decrypted.decode('utf-8')


class AddressHeaderParser(list):
    """
    This is a class which tries very hard to interpret the From:, To:
    and Cc: lines found in real-world e-mail and make sense of them.

    The general strategy of this parser is to:
       1. parse header data into tokens
       2. group tokens together into address + name constructs.

    And optionaly,
       3. normalize each group to a standard format

    In practice, we do this in multiple passes: first a strict pass where
    we try to parse things semi-sensibly, followed by fuzzier heuristics.

    Ideally, if folks format things correctly we should parse correctly.
    But if that fails, there are are other passes where we try to cope
    with various types of weirdness we've seen in the wild. The wild can
    be pretty wild.

    This parser is NOT (yet) fully RFC2822 compliant - in particular it
    will get confused by nested comments (see FIXME in tests below).

    Examples:

    >>> ahp = AddressHeaderParser(AddressHeaderParser.TEST_HEADER_DATA)
    >>> ai = ahp[1]
    >>> ai.fn
    u'Bjarni'
    >>> ai.address
    u'bre@klaki.net'
    >>> ahp.normalized_addresses() == ahp.TEST_EXPECT_NORMALIZED_ADDRESSES
    True

    >>> AddressHeaderParser('Weird email@somewhere.com Header').normalized()
    u'"Weird Header" <email@somewhere.com>'
    """

    TEST_HEADER_DATA = """
        bre@klaki.net  ,
        bre@klaki.net Bjarni ,
        bre@klaki.net bre@klaki.net,
        bre@klaki.net (bre@notmail.com),
        bre@klaki.net ((nested) bre@notmail.com comment),
        (FIXME: (nested) bre@wrongmail.com parser breaker) bre@klaki.net,
        undisclosed-recipients-gets-ignored:,
        Bjarni [mailto:bre@klaki.net],
        "This is a key test" <bre@klaki.net#123456789>,
        bre@klaki.net (Bjarni Runar Einar's son);
        Bjarni is bre @klaki.net,
        Bjarni =?iso-8859-1?Q?Runar?=Einarsson<' bre'@ klaki.net>,
    """
    TEST_EXPECT_NORMALIZED_ADDRESSES = [
        '<bre@klaki.net>',
        '"Bjarni" <bre@klaki.net>',
        '"bre@klaki.net" <bre@klaki.net>',
        '"bre@notmail.com" <bre@klaki.net>',
        '"(nested bre@notmail.com comment)" <bre@klaki.net>',
        '"(FIXME: nested parser breaker) bre@klaki.net" <bre@wrongmail.com>',
        '"Bjarni" <bre@klaki.net>',
        '"This is a key test" <bre@klaki.net>',
        '"Bjarni Runar Einar\\\'s son" <bre@klaki.net>',
        '"Bjarni is" <bre@klaki.net>',
        '"Bjarni Runar Einarsson" <bre@klaki.net>']

    # Escaping and quoting
    TXT_RE_QUOTE = '=\\?([^\\?\\s]+)\\?([QqBb])\\?([^\\?\\s]+)\\?='
    TXT_RE_QUOTE_NG = TXT_RE_QUOTE.replace('(', '(?:')
    RE_ESCAPES = re.compile('\\\\([\\\\"\'])')
    RE_QUOTED = re.compile(TXT_RE_QUOTE)
    RE_SHOULD_ESCAPE = re.compile('([\\\\"\'])')
    RE_SHOULD_QUOTE = re.compile('[^a-zA-Z0-9()\.:/_ \'"+@-]')

    # This is how we normally break a header line into tokens
    RE_TOKENIZER = re.compile('(<[^<>]*>'                    # <stuff>
                              '|\\([^\\(\\)]*\\)'            # (stuff)
                              '|\\[[^\\[\\]]*\\]'            # [stuff]
                              '|"(?:\\\\\\\\|\\\\"|[^"])*"'  # "stuff"
                              "|'(?:\\\\\\\\|\\\\'|[^'])*'"  # 'stuff'
                              '|' + TXT_RE_QUOTE_NG +        # =?stuff?=
                              '|,'                           # ,
                              '|;'                           # ;
                              '|\\s+'                        # white space
                              '|[^\\s;,]+'                   # non-white space
                              ')')

    # Where to insert spaces to help the tokenizer parse bad data
    RE_MUNGE_TOKENSPACERS = (re.compile('(\S)(<)'), re.compile('(\S)(=\\?)'))

    # Characters to strip aware entirely when tokenizing munged data
    RE_MUNGE_TOKENSTRIPPERS = (re.compile('[<>"]'),)

    # This is stuff we ignore (undisclosed-recipients, etc)
    RE_IGNORED_GROUP_TOKENS = re.compile('(?i)undisclosed')

    # Things we strip out to try and un-mangle e-mail addresses when
    # working with bad data.
    RE_MUNGE_STRIP = re.compile('(?i)(?:\\bmailto:|[\\s"\']|\?$)')

    # This a simple regular expression for detecting e-mail addresses.
    RE_MAYBE_EMAIL = re.compile('^[^()<>@,;:\\\\"\\[\\]\\s\000-\031]+'
                                '@[a-zA-Z0-9_\\.-]+(?:#[A-Za-z0-9]+)?$')

    # We try and interpret non-ascii data as a particular charset, in
    # this order by default. Should be overridden whenever we have more
    # useful info from the message itself.
    DEFAULT_CHARSET_ORDER = ('iso-8859-1', 'utf-8')

    def __init__(self, data=None, charset_order=None, **kwargs):
        self.charset_order = charset_order or self.DEFAULT_CHARSET_ORDER
        self._parse_args = kwargs
        if data is None:
            self._reset(**kwargs)
        else:
            self.parse(data)

    def _reset(self, _raw_data=None, strict=False, _raise=False):
        self._raw_data = _raw_data
        self._tokens = []
        self._groups = []
        self[:] = []

    def parse(self, data):
        return self._parse(data, **self._parse_args)

    def _parse(self, data, strict=False, _raise=False):
        self._reset(_raw_data=data)

        # 1st pass, strict
        try:
            self._tokens = self._tokenize(self._raw_data)
            self._groups = self._group(self._tokens)
            self[:] = self._find_addresses(self._groups,
                                           _raise=(not strict))
            return self
        except ValueError:
            if strict and _raise:
                raise
        if strict:
            return self

        # 2nd & 3rd passes; various types of sloppy
        for _pass in ('2', '3'):
            try:
                self._tokens = self._tokenize(self._raw_data, munge=_pass)
                self._groups = self._group(self._tokens, munge=_pass)
                self[:] = self._find_addresses(self._groups,
                                               munge=_pass,
                                               _raise=_raise)
                return self
            except ValueError:
                if _pass == 3 and _raise:
                    raise
        return self

    def unquote(self, string, charset_order=None):
        def uq(m):
            cs, how, data = m.group(1), m.group(2), m.group(3)
            if how in ('b', 'B'):
                return base64.b64decode(data).decode(cs)
            else:
                return quopri.decodestring(data, header=True).decode(cs)

        for cs in charset_order or self.charset_order:
             try:
                 string = string.decode(cs)
                 break
             except UnicodeDecodeError:
                 pass

        return re.sub(self.RE_QUOTED, uq, string)

    @classmethod
    def unescape(self, string):
        return re.sub(self.RE_ESCAPES, lambda m: m.group(1), string)

    @classmethod
    def escape(self, strng):
        return re.sub(self.RE_SHOULD_ESCAPE, lambda m: '\\'+m.group(0), strng)

    @classmethod
    def quote(self, strng):
        if re.search(self.RE_SHOULD_QUOTE, strng):
            enc = quopri.encodestring(strng.encode('utf-8'), False,
                                      header=True)
            return '=?utf-8?Q?%s?=' % enc
        else:
            return '"%s"' % self.escape(strng)

    def _tokenize(self, string, munge=False):
        if munge:
            for ts in self.RE_MUNGE_TOKENSPACERS:
                string = re.sub(ts, '\\1 \\2', string)
            if munge == 3:
                for ts in self.RE_MUNGE_TOKENSTRIPPERS:
                    string = re.sub(ts, '', string)
        return re.findall(self.RE_TOKENIZER, string)

    def _clean(self, token):
        if token[:1] in ('"', "'"):
            if token[:1] == token[-1:]:
                return self.unescape(token[1:-1])
        elif token.startswith('[mailto:') and token[-1:] == ']':
            # Just convert [mailto:...] crap into a <address>
            return '<%s>' % token[8:-1]
        elif (token[:1] == '[' and token[-1:] == ']'):
            return token[1:-1]
        return token

    def _group(self, tokens, munge=False):
        groups = [[]]
        for token in tokens:
            token = token.strip()
            if token in (',', ';'):
                # Those tokens SHOULD separate groups, but we don't like to
                # create groups that have no e-mail addresses at all.
                if groups[-1]:
                    if [g for g in groups[-1] if '@' in g]:
                        groups.append([])
                        continue
                    # However, this stuff is just begging to be ignored.
                    elif [g for g in groups[-1]
                          if re.match(self.RE_IGNORED_GROUP_TOKENS, g)]:
                        groups[-1] = []
                        continue
            if token:
                groups[-1].append(self.unquote(self._clean(token)))
        if not groups[-1]:
            groups.pop(-1)
        return groups

    def _find_addresses(self, groups, **fa_kwargs):
        alist = [self._find_address(g, **fa_kwargs) for g in groups]
        return [a for a in alist if a]

    def _find_address(self, g, _raise=False, munge=False):
        if g:
            g = g[:]
        else:
            return []

        def email_at(i):
            for j in range(0, len(g)):
                if g[j][:1] == '(' and g[j][-1:] == ')':
                    g[j] = g[j][1:-1]
            rest = ' '.join([g[j] for j in range(0, len(g)) if j != i
                             ]).replace(' ,', ',').replace(' ;', ';')
            email, keys = g[i], None
            if '#' in email[email.index('@'):]:
                email, key = email.rsplit('#', 1)
                keys = [{'fingerprint': key}]
            return AddressInfo(email, rest.strip(), keys=keys)

        def munger(string):
            if munge:
                return re.sub(self.RE_MUNGE_STRIP, '', string)
            else:
                return string

        # If munging, look for email @domain.com in two parts, rejoin
        if munge:
            for i in range(0, len(g)):
                if i > 0 and i < len(g) and g[i][:1] == '@':
                    g[i-1:i+1] = [g[i-1]+g[i]]
                elif i < len(g)-1 and g[i][-1:] == '@':
                    g[i:i+2] = [g[i]+g[i+1]]

        # 1st, look for <email@domain.com>
        for i in range(0, len(g)):
            if g[i][:1] == '<' and g[i][-1:] == '>':
                maybemail = munger(g[i][1:-1])
                if re.match(self.RE_MAYBE_EMAIL, maybemail):
                    g[i] = maybemail
                    return email_at(i)

        # 2nd, look for bare email@domain.com
        for i in range(0, len(g)):
            maybemail = munger(g[i])
            if re.match(self.RE_MAYBE_EMAIL, maybemail):
                g[i] = maybemail
                return email_at(i)

        if _raise:
            raise ValueError('No email found in %s' % (g,))
        else:
            return None

    def normalized_addresses(self,
                             addresses=None, quote=True, with_keys=False,
                             force_name=False):
        if addresses is None:
            addresses = self
        def fmt(ai):
            email = ai.address
            if with_keys and ai.keys:
                fp = ai.keys[0].get('fingerprint')
                epart = '<%s%s>' % (email, fp and ('#%s' % fp) or '')
            else:
                epart = '<%s>' % email
            if ai.fn:
                 return ' '.join([quote and self.quote(ai.fn) or ai.fn, epart])
            elif force_name:
                 return ' '.join([quote and self.quote(email) or email, epart])
            else:
                 return epart
        return [fmt(ai) for ai in (addresses or [])]

    def normalized(self, **kwargs):
        return ', '.join(self.normalized_addresses(**kwargs))


if __name__ == "__main__":
    import doctest
    import sys

    results = doctest.testmod(optionflags=doctest.ELLIPSIS,
                              extraglobs={})
    print
    print '%s' % (results, )
    if results.failed:
        sys.exit(1)

########NEW FILE########
__FILENAME__ = mail_generator
# Copyright (C) 2001-2010 Python Software Foundation
# Contact: email-sig@python.org
#
# Updated/forked January 2014 by Bjarni R. Einarsson <bre@mailpile.is>
# to match the python 3.x email.generator CRLF control API (linesep=...).
#

"""Classes to generate plain text from a message object tree."""

__all__ = ['Generator', 'DecodedGenerator']

import re
import sys
import time
import random
import warnings

from cStringIO import StringIO
from email.header import Header

UNDERSCORE = '_'
NL = '\n'

fcre = re.compile(r'^From ', re.MULTILINE)


def _is8bitstring(s):
    if isinstance(s, str):
        try:
            unicode(s, 'us-ascii')
        except UnicodeError:
            return True
    return False


class Generator:
    """Generates output from a Message object tree.

    This basic generator writes the message to the given file object as plain
    text.
    """
    #
    # Public interface
    #

    def __init__(self, outfp,
                 mangle_from_=True, maxheaderlen=78, linesep=None):
        """Create the generator for message flattening.

        outfp is the output file-like object for writing the message to.  It
        must have a write() method.

        Optional mangle_from_ is a flag that, when True (the default), escapes
        From_ lines in the body of the message by putting a `>' in front of
        them.

        Optional maxheaderlen specifies the longest length for a non-continued
        header.  When a header line is longer (in characters, with tabs
        expanded to 8 spaces) than maxheaderlen, the header will split as
        defined in the Header class.  Set maxheaderlen to zero to disable
        header wrapping.  The default is 78, as recommended (but not required)
        by RFC 2822.
        """
        self._fp = outfp
        self._mangle_from_ = mangle_from_
        self._maxheaderlen = maxheaderlen
        self._NL = linesep or NL

    def write(self, s):
        # Just delegate to the file object
        self._fp.write(s)

    def flatten(self, msg, unixfrom=False, linesep=None):
        """Print the message object tree rooted at msg to the output file
        specified when the Generator instance was created.

        unixfrom is a flag that forces the printing of a Unix From_ delimiter
        before the first object in the message tree.  If the original message
        has no From_ delimiter, a `standard' one is crafted.  By default, this
        is False to inhibit the printing of any From_ delimiter.

        linesep specifies the characters used to indicate a new line in the
        output. The default value is LF (not the standard CRLF).

        Note that for subobjects, no From_ line is printed.
        """
        if linesep:
            self._NL = linesep
        if unixfrom:
            ufrom = msg.get_unixfrom()
            if not ufrom:
                ufrom = 'From nobody ' + time.ctime(time.time())
            print >> self._fp, ufrom + self._NL,
        self._write(msg)

    def clone(self, fp):
        """Clone this generator with the exact same options."""
        return self.__class__(fp, self._mangle_from_, self._maxheaderlen)

    #
    # Protected interface - undocumented ;/
    #

    def _write(self, msg):
        # We can't write the headers yet because of the following scenario:
        # say a multipart message includes the boundary string somewhere in
        # its body.  We'd have to calculate the new boundary /before/ we write
        # the headers so that we can write the correct Content-Type:
        # parameter.
        #
        # The way we do this, so as to make the _handle_*() methods simpler,
        # is to cache any subpart writes into a StringIO.  The we write the
        # headers and the StringIO contents.  That way, subpart handlers can
        # Do The Right Thing, and can still modify the Content-Type: header if
        # necessary.
        oldfp = self._fp
        try:
            self._fp = sfp = StringIO()
            self._dispatch(msg)
        finally:
            self._fp = oldfp
        # Write the headers.  First we see if the message object wants to
        # handle that itself.  If not, we'll do it generically.
        meth = getattr(msg, '_write_headers', None)
        if meth is None:
            self._write_headers(msg)
        else:
            meth(self)
        self._fp.write(sfp.getvalue())

    def _dispatch(self, msg):
        # Get the Content-Type: for the message, then try to dispatch to
        # self._handle_<maintype>_<subtype>().  If there's no handler for the
        # full MIME type, then dispatch to self._handle_<maintype>().  If
        # that's missing too, then dispatch to self._writeBody().
        main = msg.get_content_maintype()
        sub = msg.get_content_subtype()
        specific = UNDERSCORE.join((main, sub)).replace('-', '_')
        meth = getattr(self, '_handle_' + specific, None)
        if meth is None:
            generic = main.replace('-', '_')
            meth = getattr(self, '_handle_' + generic, None)
            if meth is None:
                meth = self._writeBody
        meth(msg)

    #
    # Default handlers
    #

    def _write_headers(self, msg):
        for h, v in msg.items():
            print >> self._fp, '%s:' % h,
            if self._maxheaderlen == 0:
                # Explicit no-wrapping
                print >> self._fp, v + self._NL,
            elif isinstance(v, Header):
                # Header instances know what to do
                hdr = v.encode().replace('\n', self._NL)
                print >> self._fp, hdr + self._NL,
            elif _is8bitstring(v):
                # If we have raw 8bit data in a byte string, we have no idea
                # what the encoding is.  There is no safe way to split this
                # string.  If it's ascii-subset, then we could do a normal
                # ascii split, but if it's multibyte then we could break the
                # string.  There's no way to know so the least harm seems to
                # be to not split the string and risk it being too long.
                print >> self._fp, v + self._NL,
            else:
                # Header's got lots of smarts, so use it.  Note that this is
                # fundamentally broken though because we lose idempotency when
                # the header string is continued with tabs.  It will now be
                # continued with spaces.  This was reversedly broken before we
                # fixed bug 1974.  Either way, we lose.
                hdr = Header(v, maxlinelen=self._maxheaderlen, header_name=h
                             ).encode().replace('\n', self._NL)
                print >> self._fp, hdr + self._NL,
        # A blank line always separates headers from body
        print >> self._fp, self._NL,

    #
    # Handlers for writing types and subtypes
    #

    def _handle_text(self, msg):
        payload = msg.get_payload()
        if payload is None:
            return
        if not isinstance(payload, basestring):
            raise TypeError('string payload expected: %s' % type(payload))
        if self._mangle_from_:
            payload = fcre.sub('>From ', payload)
        self._fp.write(payload)

    # Default body handler
    _writeBody = _handle_text

    def _handle_multipart(self, msg):
        # The trick here is to write out each part separately, merge them all
        # together, and then make sure that the boundary we've chosen isn't
        # present in the payload.
        msgtexts = []
        subparts = msg.get_payload()
        if subparts is None:
            subparts = []
        elif isinstance(subparts, basestring):
            # e.g. a non-strict parse of a message with no starting boundary.
            self._fp.write(subparts)
            return
        elif not isinstance(subparts, list):
            # Scalar payload
            subparts = [subparts]
        for part in subparts:
            s = StringIO()
            g = self.clone(s)
            g.flatten(part, unixfrom=False, linesep=self._NL)
            msgtexts.append(s.getvalue())
        # BAW: What about boundaries that are wrapped in double-quotes?
        boundary = msg.get_boundary()
        if not boundary:
            # Create a boundary that doesn't appear in any of the
            # message texts.
            alltext = self._NL.join(msgtexts)
            boundary = _make_boundary(alltext)
            msg.set_boundary(boundary)
        # If there's a preamble, write it out, with a trailing CRLF
        if msg.preamble is not None:
            if self._mangle_from_:
                preamble = fcre.sub('>From ', msg.preamble)
            else:
                preamble = msg.preamble
            print >> self._fp, preamble + self._NL,
        # dash-boundary transport-padding CRLF
        print >> self._fp, '--' + boundary + self._NL,
        # body-part
        if msgtexts:
            self._fp.write(msgtexts.pop(0))
        # *encapsulation
        # --> delimiter transport-padding
        # --> CRLF body-part
        for body_part in msgtexts:
            # delimiter transport-padding CRLF
            print >> self._fp, self._NL + '--' + boundary + self._NL,
            # body-part
            self._fp.write(body_part)
        # close-delimiter transport-padding
        self._fp.write(self._NL + '--' + boundary + '--')
        if msg.epilogue is not None:
            print >> self._fp, self._NL,
            if self._mangle_from_:
                epilogue = fcre.sub('>From ', msg.epilogue)
            else:
                epilogue = msg.epilogue
            self._fp.write(epilogue)

    def _handle_multipart_signed(self, msg):
        # The contents of signed parts has to stay unmodified in order to keep
        # the signature intact per RFC1847 2.1, so we disable header wrapping.
        # RDM: This isn't enough to completely preserve the part, but it helps.
        old_maxheaderlen = self._maxheaderlen
        try:
            self._maxheaderlen = 0
            self._handle_multipart(msg)
        finally:
            self._maxheaderlen = old_maxheaderlen

    def _handle_message_delivery_status(self, msg):
        # We can't just write the headers directly to self's file object
        # because this will leave an extra newline between the last header
        # block and the boundary.  Sigh.
        blocks = []
        for part in msg.get_payload():
            s = StringIO()
            g = self.clone(s)
            g.flatten(part, unixfrom=False, linesep=self._NL)
            text = s.getvalue()
            lines = text.split(self._NL)
            # Strip off the unnecessary trailing empty line
            if lines and lines[-1] == '':
                blocks.append(self._NL.join(lines[:-1]))
            else:
                blocks.append(text)
        # Now join all the blocks with an empty line.  This has the lovely
        # effect of separating each block with an empty line, but not adding
        # an extra one after the last one.
        self._fp.write(self._NL.join(blocks))

    def _handle_message(self, msg):
        s = StringIO()
        g = self.clone(s)
        # The payload of a message/rfc822 part should be a multipart sequence
        # of length 1.  The zeroth element of the list should be the Message
        # object for the subpart.  Extract that object, stringify it, and
        # write it out.
        # Except, it turns out, when it's a string instead, which happens when
        # and only when HeaderParser is used on a message of mime type
        # message/rfc822.  Such messages are generated by, for example,
        # Groupwise when forwarding unadorned messages.  (Issue 7970.)  So
        # in that case we just emit the string body.
        payload = msg.get_payload()
        if isinstance(payload, list):
            g.flatten(msg.get_payload(0), unixfrom=False, linesep=self._NL)
            payload = s.getvalue()
        self._fp.write(payload)


_FMT = '[Non-text (%(type)s) part of message omitted, filename %(filename)s]'


class DecodedGenerator(Generator):
    """Generates a text representation of a message.

    Like the Generator base class, except that non-text parts are substituted
    with a format string representing the part.
    """
    def __init__(self, outfp,
                 mangle_from_=True, maxheaderlen=78, fmt=None, linesep=None):
        """Like Generator.__init__() except that an additional optional
        argument is allowed.

        Walks through all subparts of a message.  If the subpart is of main
        type `text', then it prints the decoded payload of the subpart.

        Otherwise, fmt is a format string that is used instead of the message
        payload.  fmt is expanded with the following keywords (in
        %(keyword)s format):

        type       : Full MIME type of the non-text part
        maintype   : Main MIME type of the non-text part
        subtype    : Sub-MIME type of the non-text part
        filename   : Filename of the non-text part
        description: Description associated with the non-text part
        encoding   : Content transfer encoding of the non-text part

        The default value for fmt is None, meaning

        [Non-text (%(type)s) part of message omitted, filename %(filename)s]
        """
        Generator.__init__(self, outfp, mangle_from_, maxheaderlen, linesep)
        if fmt is None:
            self._fmt = _FMT
        else:
            self._fmt = fmt

    def _dispatch(self, msg):
        for part in msg.walk():
            maintype = part.get_content_maintype()
            if maintype == 'text':
                print >> self, part.get_payload(decode=True) + self._NL,
            elif maintype == 'multipart':
                # Just skip this
                pass
            else:
                print >> self, self._fmt % {
                    'type': part.get_content_type(),
                    'maintype': part.get_content_maintype(),
                    'subtype': part.get_content_subtype(),
                    'filename': part.get_filename('[no filename]'),
                    'description': part.get('Content-Description',
                                            '[no description]'),
                    'encoding': part.get('Content-Transfer-Encoding',
                                         '[no encoding]'),
                    } + self._NL,


# Helper
_width = len(repr(sys.maxint-1))
_fmt = '%%0%dd' % _width


def _make_boundary(text=None):
    # Craft a random boundary.  If text is given, ensure that the chosen
    # boundary doesn't appear in the text.
    token = random.randrange(sys.maxint)
    boundary = ('=' * 15) + (_fmt % token) + '=='
    if text is None:
        return boundary
    b = boundary
    counter = 0
    while True:
        cre = re.compile('^--' + re.escape(b) + '(--)?$', re.MULTILINE)
        if not cre.search(text):
            break
        b = boundary + '.' + str(counter)
        counter += 1
    return b

########NEW FILE########
__FILENAME__ = maildir
import os
from gettext import gettext as _

from mailpile.mail_source import BaseMailSource


class MaildirMailSource(BaseMailSource):
    """
    This is a mail source that watches over one or more Maildirs.
    """
    # This is a helper for the events.
    __classname__ = 'mailpile.mail_source.maildir.MaildirMailSource'

    def __init__(self, *args, **kwargs):
        BaseMailSource.__init__(self, *args, **kwargs)
        self.watching = -1

    def _unlocked_open(self):
        mailboxes = self.my_config.mailbox.values()
        if self.watching == len(mailboxes):
            return True
        else:
            self.watching = len(mailboxes)

        for d in ('mtimes_cur', 'mtimes_new', 'mtimes_tmp'):
            if d not in self.event.data:
                self.event.data[d] = {}

        self._log_status(_('Watching %d maildir mailboxes') % self.watching)
        return True

    def _has_mailbox_changed(self, mbx, state):
        for sub in ('cur', 'new', 'tmp'):
            state[sub] = long(os.path.getmtime(os.path.join(self._path(mbx),
                                                            sub)))
        for sub in ('cur', 'new', 'tmp'):
            if state[sub] != self.event.data['mtimes_%s' % sub].get(mbx._key):
                return True
        return False

    def _mark_mailbox_rescanned(self, mbx, state):
        for sub in ('cur', 'new', 'tmp'):
            self.event.data['mtimes_%s' % sub][mbx._key] = state[sub]

    def is_mailbox(self, fn):
        if not os.path.isdir(fn):
            return False
        for sub in ('cur', 'new', 'tmp'):
            subdir = os.path.join(fn, sub)
            if not os.path.exists(subdir) or not os.path.isdir(subdir):
                return False
        return True

########NEW FILE########
__FILENAME__ = mbox
import os
from gettext import gettext as _

from mailpile.mail_source import BaseMailSource


class MboxMailSource(BaseMailSource):
    """
    This is a mail source that watches over one or more Unix mboxes.
    """
    # This is a helper for the events.
    __classname__ = 'mailpile.mail_source.mbox.MboxMailSource'

    def __init__(self, *args, **kwargs):
        BaseMailSource.__init__(self, *args, **kwargs)
        self.watching = -1

    def _unlocked_open(self):
        mailboxes = self.my_config.mailbox.values()
        if self.watching == len(mailboxes):
            return True
        else:
            self.watching = len(mailboxes)

        # Prepare the data section of our event, for keeping state.
        for d in ('mtimes', 'sizes'):
            if d not in self.event.data:
                self.event.data[d] = {}

        self._log_status(_('Watching %d mbox mailboxes') % self.watching)
        return True

    def _has_mailbox_changed(self, mbx, state):
        mt = state['mt'] = long(os.path.getmtime(self._path(mbx)))
        sz = state['sz'] = long(os.path.getsize(self._path(mbx)))
        return (mt != self.event.data['mtimes'].get(mbx._key) or
                sz != self.event.data['sizes'].get(mbx._key))

    def _mark_mailbox_rescanned(self, mbx, state):
        self.event.data['mtimes'][mbx._key] = state['mt']
        self.event.data['sizes'][mbx._key] = state['sz']

    def is_mailbox(self, fn):
        try:
            with open(fn, 'rb') as fd:
                data = fd.read(2048)  # No point reading less...
                if data.startswith('From '):
                    # OK, this might be an mbox! Let's check if the first
                    # few lines look like RFC2822 headers...
                    headcount = 0
                    for line in data.splitlines(True)[1:]:
                        if (headcount > 3) and line in ('\n', '\r\n'):
                            return True
                        if line[-1:] == '\n' and line[:1] not in (' ', '\t'):
                            parts = line.split(':')
                            if (len(parts) < 2 or
                                    ' ' in parts[0] or '\t' in parts[0]):
                                return False
                            headcount += 1
                    return (headcount > 3)
        except (IOError, OSError):
            pass
        return False

########NEW FILE########
__FILENAME__ = autotag
# This is the generic auto-tagging plugin.
#
# We feed the classifier the same terms as go into the search engine,
# which should allow us to actually introspect a bit into the behavior
# of the classifier.

import math
import time
import datetime
from gettext import gettext as _

import mailpile.config
from mailpile.plugins import PluginManager
from mailpile.commands import Command
from mailpile.mailutils import Email
from mailpile.util import *


_plugins = PluginManager(builtin=__file__)


##[ Configuration ]###########################################################

TAGGERS = {}
TRAINERS = {}

_plugins.register_config_section(
    'prefs', 'autotag', ["Auto-tagging", {
        'match_tag': ['Tag we are adding to automatically', str, ''],
        'unsure_tag': ['If unsure, add to this tag', str, ''],
        'exclude_tags': ['Tags on messages we should never match (ham)',
                         str, []],
        'ignore_kws': ['Ignore messages with these keywords', str, []],
        'corpus_size': ['How many messages do we train on?', int, 1000],
        'threshold': ['Size of the sure/unsure ranges', float, 0.1],
        'tagger': ['Internal class name or |shell command', str, ''],
        'trainer': ['Internal class name or |shell commant', str, ''],
    }, []])


def at_identify(at_config):
    return md5_hex(at_config.match_tag,
                   at_config.tagger,
                   at_config.trainer)[:12]


class AutoTagger(object):
    def __init__(self, tagger, trainer):
        self.tagger = tagger
        self.trainer = trainer
        self.trained = False

    def reset(self, at_config):
        """Reset to an untrained state"""
        self.trainer.reset(self, at_config)
        self.trained = False

    def learn(self, *args):
        self.trained = True
        return self.trainer.learn(self, *args)

    def should_tag(self, *args):
        return self.tagger.should_tag(self, *args)


def SaveAutoTagger(config, at_config):
    aid = at_identify(at_config)
    at = config.autotag.get(aid)
    if at and at.trained:
        config.save_pickle(at, 'pickled-autotag.%s' % aid)


def LoadAutoTagger(config, at_config):
    if not config.real_hasattr('autotag'):
        config.real_setattr('autotag', {})
    aid = at_identify(at_config)
    at = config.autotag.get(aid)
    if aid not in config.autotag:
        cfn = 'pickled-autotag.%s' % aid
        try:
            config.autotag[aid] = config.load_pickle(cfn)
        except (IOError, EOFError):
            tagger = at_config.tagger
            trainer = at_config.trainer
            config.autotag[aid] = AutoTagger(
                TAGGERS.get(tagger, TAGGERS['_default'])(tagger),
                TRAINERS.get(trainer, TRAINERS['_default'])(trainer),
            )
            SaveAutoTagger(config, at_config)
    return config.autotag[aid]


mailpile.config.ConfigManager.load_auto_tagger = LoadAutoTagger
mailpile.config.ConfigManager.save_auto_tagger = SaveAutoTagger


##[ Internal classes ]########################################################

class AutoTagCommand(object):
    def __init__(self, command):
        self.command = command


class Tagger(AutoTagCommand):
    def should_tag(self, atagger, at_config, msg, keywords):
        """Returns (result, evidence), result =True, False or None"""
        return (False, None)


class Trainer(AutoTagCommand):
    def learn(self, atagger, at_config, msg, keywords, should_tag):
        """Learn that this message should (or should not) be tagged"""
        pass

    def reset(self, atagger, at_config):
        """Reset to an untrained state (called by AutoTagger.reset)"""
        pass


TAGGERS['_default'] = Tagger
TRAINERS['_default'] = Trainer


##[ Commands ]################################################################


class AutoTagCommand(Command):
    ORDER = ('Tagging', 9)

    def _get_keywords(self, e):
        idx = self._idx()
        if not hasattr(self, 'rcache'):
            self.rcache = {}
        mid = e.msg_mid()
        if mid not in self.rcache:
            kws, snippet = idx.read_message(
                self.session,
                mid,
                e.get_msg_info(field=idx.MSG_ID),
                e.get_msg(),
                e.get_msg_size(),
                int(e.get_msg_info(field=idx.MSG_DATE), 36))
            self.rcache[mid] = kws
        return self.rcache[mid]


class Retrain(AutoTagCommand):
    SYNOPSIS = (None, 'autotag/retrain', None, '[<tags>]')

    def command(self):
        self._retrain(tags=self.args)

    def _retrain(self, tags=None):
        "Retrain autotaggers"
        session, config, idx = self.session, self.session.config, self._idx()
        tags = tags or [asb.match_tag for asb in config.prefs.autotag]
        tids = [config.get_tag(t)._key for t in tags if t]

        session.ui.mark(_('Retraining SpamBayes autotaggers'))
        if not config.real_hasattr('autotag'):
            config.real_setattr('autotag', {})

        # Find all the interesting messages! We don't look in the trash,
        # but we do look at interesting spam.
        #
        # Note: By specifically stating that we DON'T want trash, we
        #       disable the search engine's default result suppression
        #       and guarantee these results don't corrupt the somewhat
        #       lame/broken result cache.
        #
        no_trash = ['-in:%s' % t._key for t in config.get_tags(type='trash')]
        interest = {}
        for ttype in ('replied', 'fwded', 'read', 'tagged'):
            interest[ttype] = set()
            for tag in config.get_tags(type=ttype):
                interest[ttype] |= idx.search(session,
                                              ['in:%s' % tag.slug] + no_trash
                                              ).as_set()
            session.ui.notify(_('Have %d interesting %s messages'
                                ) % (len(interest[ttype]), ttype))

        retrained, unreadable = [], []
        count_all = 0
        for at_config in config.prefs.autotag:
            at_tag = config.get_tag(at_config.match_tag)
            if at_tag and at_tag._key in tids:
                session.ui.mark('Retraining: %s' % at_tag.name)

                yn = [(set(), set(), 'in:%s' % at_tag.slug, True),
                      (set(), set(), '-in:%s' % at_tag.slug, False)]

                # Get the current message sets: tagged and untagged messages
                # excluding trash.
                for tset, mset, srch, which in yn:
                    mset |= idx.search(session, [srch] + no_trash).as_set()

                # If we have any exclude_tags, they are particularly
                # interesting, so we'll look at them first.
                interesting = []
                for etagid in at_config.exclude_tags:
                    etag = config.get_tag(etagid)
                    if etag._key not in interest:
                        srch = ['in:%s' % etag._key] + no_trash
                        interest[etag._key] = idx.search(session, srch
                                                         ).as_set()
                    interesting.append(etag._key)
                interesting.extend(['replied', 'fwded', 'read', 'tagged',
                                    None])

                # Go through the interest types in order of preference and
                # while we still lack training data, add to the training set.
                for ttype in interesting:
                    for tset, mset, srch, which in yn:
                        # FIXME: Is this a good idea? No single data source
                        # is allowed to be more than 50% of the corpus, to
                        # try and encourage diversity.
                        want = min(at_config.corpus_size / 4,
                                   max(0,
                                       at_config.corpus_size / 2 - len(tset)))
                        if want:
                            if ttype:
                                adding = sorted(list(mset & interest[ttype]))
                            else:
                                adding = sorted(list(mset))
                            adding = set(list(reversed(adding))[:want])
                            tset |= adding
                            mset -= adding

                # Load classifier, reset
                atagger = config.load_auto_tagger(at_config)
                atagger.reset(at_config)
                for tset, mset, srch, which in yn:
                    count = 0
                    for msg_idx in tset:
                        try:
                            e = Email(idx, msg_idx)
                            count += 1
                            count_all += 1
                            session.ui.mark(
                                _('Reading %s (%d/%d, %s=%s)'
                                  ) % (e.msg_mid(), count, len(tset),
                                       at_tag.name, which))
                            atagger.learn(at_config,
                                          e.get_msg(),
                                          self._get_keywords(e),
                                          which)
                        except (IndexError, TypeError, ValueError,
                                OSError, IOError):
                            if session.config.sys.debug:
                                import traceback
                                traceback.print_exc()
                            unreadable.append(msg_idx)
                            session.ui.warning(
                                _('Failed to process message at =%s'
                                  ) % (b36(msg_idx)))

                # We got this far without crashing, so save the result.
                config.save_auto_tagger(at_config)
                retrained.append(at_tag.name)

        message = _('Retrained SpamBayes auto-tagging for %s'
                    ) % ', '.join(retrained)
        session.ui.mark(message)
        return self._success(message, result={
            'retrained': retrained,
            'unreadable': unreadable,
            'read_messages': count_all
        })

    @classmethod
    def interval_retrain(cls, session):
        """
        Retrains autotaggers

        Classmethod used for periodic automatic retraining
        """
        result = cls(session)._retrain()
        if result:
            return True
        else:
            return False


_plugins.register_config_variables('prefs', {
    'autotag_retrain_interval': [_('Periodically retrain autotagger (seconds)'),
                                  int, 24*60*60],
})

_plugins.register_slow_periodic_job('retrain_autotag',
                                    'prefs.autotag_retrain_interval',
                                    Retrain.interval_retrain)

class Classify(AutoTagCommand):
    SYNOPSIS = (None, 'autotag/classify', None, '<msgs>')
    ORDER = ('Tagging', 9)

    def _classify(self, emails):
        session, config, idx = self.session, self.session.config, self._idx()
        results = {}
        unknown = []
        for e in emails:
            kws = self._get_keywords(e)
            result = results[e.msg_mid()] = {}
            for at_config in config.prefs.autotag:
                if not at_config.match_tag:
                    continue
                at_tag = config.get_tag(at_config.match_tag)
                if not at_tag and at_config.match_tag not in unknown:
                    session.ui.error(_('Unknown tag: %s'
                                       ) % at_config.match_tag)
                    unknown.append(at_config.match_tag)
                    continue

                atagger = config.load_auto_tagger(at_config)
                if atagger.trained:
                    result[at_tag._key] = result.get(at_tag._key, [])
                    result[at_tag._key].append(atagger.should_tag(
                        at_config, e.get_msg(), kws
                    ))
        return results

    def command(self):
        session, config, idx = self.session, self.session.config, self._idx()
        emails = [Email(idx, mid) for mid in self._choose_messages(self.args)]
        return self._success(_('Classified %d messages') % len(emails),
                             self._classify(emails))


class AutoTag(Classify):
    SYNOPSIS = (None, 'autotag', None, '<msgs>')
    ORDER = ('Tagging', 9)

    def command(self):
        session, config, idx = self.session, self.session.config, self._idx()
        emails = [Email(idx, mid) for mid in self._choose_messages(self.args)]
        scores = self._classify(emails)
        tag = {}
        for mid in scores:
            for at_config in config.prefs.autotag:
                at_tag = config.get_tag(at_config.match_tag)
                if not at_tag:
                    continue
                want = scores[mid].get(at_tag._key, (False, ))[0]

                if want is True:
                    if at_config.match_tag not in tag:
                        tag[at_config.match_tag] = [mid]
                    else:
                        tag[at_config.match_tag].append(mid)

                elif at_config.unsure_tag and want is None:
                    if at_config.unsure_tag not in tag:
                        tag[at_config.unsure_tag] = [mid]
                    else:
                        tag[at_config.unsure_tag].append(mid)

        for tid in tag:
            idx.add_tag(session, tid, msg_idxs=[int(i, 36) for i in tag[tid]])

        return self._success(_('Auto-tagged %d messages') % len(emails), tag)


_plugins.register_commands(Retrain, Classify, AutoTag)


##[ Keywords ]################################################################

def filter_hook(session, msg_mid, msg, keywords, **ignored_kwargs):
    """Classify this message."""
    config = session.config
    for at_config in config.prefs.autotag:
        try:
            at_tag = config.get_tag(at_config.match_tag)
            atagger = config.load_auto_tagger(at_config)
            if not atagger.trained:
                continue
            want, info = atagger.should_tag(at_config, msg, keywords)
            if want is True:
                if 'autotag' in config.sys.debug:
                    session.ui.debug(('Autotagging %s with %s (w=%s, i=%s)'
                                      ) % (msg_mid, at_tag.name, want, info))
                keywords.add('%s:in' % at_tag._key)
            elif at_config.unsure_tag and want is None:
                unsure_tag = config.get_tag(at_config.unsure_tag)
                if 'autotag' in config.sys.debug:
                    session.ui.debug(('Autotagging %s with %s (w=%s, i=%s)'
                                      ) % (msg_mid, unsure_tag.name,
                                           want, info))
                keywords.add('%s:in' % unsure_tag._key)
        except (KeyError, AttributeError, ValueError):
            pass

    return keywords


# We add a filter pre-hook with a high (late) priority.  Late priority to
# maximize the amount of data we are feeding to the classifier, but a
# pre-hook so normal filter rules will override the autotagging.
_plugins.register_filter_hook_pre('90-autotag', filter_hook)

########NEW FILE########
__FILENAME__ = autotag_sb
# Add SpamBayes as an option to the autotagger. We like SpamBayes.
#
# We feed the classifier the same terms as go into the search engine,
# which should allow us to actually introspect a bit into the behavior
# of the classifier.

from gettext import gettext as _

from spambayes.classifier import Classifier

import mailpile.plugins.autotag


def _classifier(autotagger):
    if not hasattr(autotagger, 'spambayes'):
        autotagger.spambayes = Classifier()
    return autotagger.spambayes


class SpamBayesTagger(mailpile.plugins.autotag.Trainer):
    def should_tag(self, atagger, at_config, msg, keywords):
        score, evidence = _classifier(atagger).chi2_spamprob(keywords,
                                                             evidence=True)
        if score >= 1 - at_config.threshold:
            want = True
        elif score > at_config.threshold:
            want = None
        else:
            want = False
        return (want, score)


class SpamBayesTrainer(mailpile.plugins.autotag.Trainer):
    def learn(self, atagger, at_config, msg, keywords, should_tag):
        _classifier(atagger).learn(keywords, should_tag)

    def reset(self, atagger, at_config):
        atagger.spambayes = Classifier()


mailpile.plugins.autotag.TAGGERS['spambayes'] = SpamBayesTagger
mailpile.plugins.autotag.TRAINERS['spambayes'] = SpamBayesTrainer

########NEW FILE########
__FILENAME__ = compose
import datetime
import os
import os.path
import re
import traceback
from gettext import gettext as _

from mailpile.plugins import PluginManager
from mailpile.commands import Command
from mailpile.crypto.state import *
from mailpile.eventlog import Event
from mailpile.plugins.tags import Tag
from mailpile.mailutils import ExtractEmails, ExtractEmailAndName, Email
from mailpile.mailutils import NotEditableError, AddressHeaderParser
from mailpile.mailutils import NoFromAddressError, PrepareMessage
from mailpile.smtp_client import SendMail
from mailpile.search import MailIndex
from mailpile.urlmap import UrlMap
from mailpile.util import *
from mailpile.vcard import AddressInfo

from mailpile.plugins.search import Search, SearchResults, View


_plugins = PluginManager(builtin=__file__)


class EditableSearchResults(SearchResults):
    def __init__(self, session, idx, new, sent, **kwargs):
        SearchResults.__init__(self, session, idx, **kwargs)
        self.new_messages = new
        self.sent_messages = sent
        if new:
            self['created'] = [m.msg_mid() for m in new]
        if sent:
            self['sent'] = [m.msg_mid() for m in new]
            self['summary'] = _('Sent: %s') % self['summary']


def AddComposeMethods(cls):
    class newcls(cls):
        def _tag_emails(self, emails, tag):
            try:
                idx = self._idx()
                idx.add_tag(self.session,
                            self.session.config.get_tag_id(tag),
                            msg_idxs=[e.msg_idx_pos for e in emails],
                            conversation=False)
            except (TypeError, ValueError, IndexError):
                self._ignore_exception()

        def _untag_emails(self, emails, tag):
            try:
                idx = self._idx()
                idx.remove_tag(self.session,
                               self.session.config.get_tag_id(tag),
                               msg_idxs=[e.msg_idx_pos for e in emails],
                               conversation=False)
            except (TypeError, ValueError, IndexError):
                self._ignore_exception()

        def _tagger(self, emails, untag, **kwargs):
            tag = self.session.config.get_tags(**kwargs)
            if tag and untag:
                return self._untag_emails(emails, tag[0]._key)
            elif tag:
                return self._tag_emails(emails, tag[0]._key)

        def _tag_blank(self, emails, untag=False):
            return self._tagger(emails, untag, type='blank')

        def _tag_drafts(self, emails, untag=False):
            return self._tagger(emails, untag, type='drafts')

        def _tag_outbox(self, emails, untag=False):
            return self._tagger(emails, untag, type='outbox')

        def _tag_sent(self, emails, untag=False):
            return self._tagger(emails, untag, type='sent')

        def _track_action(self, action_type, refs):
            session, idx = self.session, self._idx()
            for tag in session.config.get_tags(type=action_type):
                idx.add_tag(session, tag._key,
                            msg_idxs=[m.msg_idx_pos for m in refs])

        def _actualize_ephemeral(self, ephemeral_mid):
            if isinstance(ephemeral_mid, int):
                # Not actually ephemeral, just return a normal Email
                return Email(self._idx(), ephemeral_mid)

            etype, mid = ephemeral_mid.rsplit('-', 1)
            etype = etype.lower()

            if etype in ('forward', 'forward-att'):
                refs = [Email(self._idx(), int(mid, 36))]
                e = Forward.CreateForward(self._idx(), self.session, refs,
                                          with_atts=('att' in etype))[0]
                self._track_action('fwded', refs)

            elif etype in ('reply', 'reply-all'):
                refs = [Email(self._idx(), int(mid, 36))]
                e = Reply.CreateReply(self._idx(), self.session, refs,
                                      reply_all=('all' in etype))[0]
                self._track_action('replied', refs)

            else:
                e = Compose.CreateMessage(self._idx(), self.session)[0]

            self._tag_blank([e])
            self.session.ui.debug('Actualized: %s' % e.msg_mid())

            return Email(self._idx(), e.msg_idx_pos)

    return newcls


class CompositionCommand(AddComposeMethods(Search)):
    HTTP_QUERY_VARS = {}
    HTTP_POST_VARS = {}
    UPDATE_STRING_DATA = {
        'mid': 'metadata-ID',
        'subject': '..',
        'from': '..',
        'to': '..',
        'cc': '..',
        'bcc': '..',
        'body': '..',
        'encryption': '..',
    }

    UPDATE_HEADERS = ('Subject', 'From', 'To', 'Cc', 'Bcc', 'Encryption')

    def _get_email_updates(self, idx, create=False, noneok=False, emails=None):
        # Split the argument list into files and message IDs
        files = [f[1:].strip() for f in self.args if f.startswith('<')]
        args = [a for a in self.args if not a.startswith('<')]

        # Message IDs can come from post data
        for mid in self.data.get('mid', []):
            args.append('=%s' % mid)
        emails = emails or [self._actualize_ephemeral(mid) for mid in
                            self._choose_messages(args, allow_ephemeral=True)]

        update_header_set = (set(self.data.keys()) &
                             set([k.lower() for k in self.UPDATE_HEADERS]))
        updates, fofs = [], 0
        for e in (emails or (create and [None]) or []):
            # If we don't have a file, check for posted data
            if len(files) not in (0, 1, len(emails)):
                return (self._error(_('Cannot update from multiple files')),
                        None)
            elif len(files) == 1:
                updates.append((e, self._read_file_or_data(files[0])))
            elif files and (len(files) == len(emails)):
                updates.append((e, self._read_file_or_data(files[fofs])))
            elif update_header_set:
                # No file name, construct an update string from the POST data.
                up = []
                etree = e and e.get_message_tree() or {}
                defaults = etree.get('editing_strings', {})
                for hdr in self.UPDATE_HEADERS:
                    if hdr.lower() in self.data:
                        data = ', '.join(self.data[hdr.lower()])
                    else:
                        data = defaults.get(hdr.lower(), '')
                    up.append('%s: %s' % (hdr, data))
                updates.append((e, '\n'.join(
                    up +
                    ['', '\n'.join(self.data.get('body',
                                                 defaults.get('body', '')))]
                )))
            elif noneok:
                updates.append((e, None))
            elif 'compose' in self.session.config.sys.debug:
                sys.stderr.write('Doing nothing with %s' % update_header_set)
            fofs += 1

        if 'compose' in self.session.config.sys.debug:
            for e, up in updates:
                sys.stderr.write(('compose/update: Update %s with:\n%s\n--\n'
                                  ) % ((e and e.msg_mid() or '(new'), up))
            if not updates:
                sys.stderr.write('compose/update: No updates!\n')

        return updates

    def _return_search_results(self, message, emails,
                               expand=None, new=[], sent=[], ephemeral=False):
        session, idx = self.session, self._idx()
        if not ephemeral:
            session.results = [e.msg_idx_pos for e in emails]
        else:
            session.results = ephemeral
        session.displayed = EditableSearchResults(session, idx,
                                                  new, sent,
                                                  results=session.results,
                                                  num=len(emails),
                                                  emails=expand)
        return self._success(message, result=session.displayed)

    def _edit_messages(self, emails, new=True, tag=True, ephemeral=False):
        session, idx = self.session, self._idx()
        if (not ephemeral and
                (session.ui.edit_messages(session, emails) or not new)):
            if tag:
                self._tag_blank(emails, untag=True)
                self._tag_drafts(emails)
                idx.save_changes()
            self.message = _('%d message(s) edited') % len(emails)
        else:
            self.message = _('%d message(s) created') % len(emails)
        session.ui.mark(self.message)
        return self._return_search_results(self.message, emails,
                                           expand=emails,
                                           new=(new and emails),
                                           ephemeral=ephemeral)


class Draft(AddComposeMethods(View)):
    """Edit an existing draft"""
    SYNOPSIS = ('E', 'edit', 'message/draft', '[<messages>]')
    ORDER = ('Composing', 0)
    HTTP_QUERY_VARS = {
        'mid': 'metadata-ID'
    }

    # FIXME: This command should raise an error if the message being
    #        displayed is not editable.

    def _side_effects(self, emails):
        session, idx = self.session, self._idx()
        try:
            if not emails:
                session.ui.mark(_('No messages!'))
            elif session.ui.edit_messages(session, emails):
                self._tag_blank(emails, untag=True)
                self._tag_drafts(emails)
                idx.save_changes()
                self.message = _('%d message(s) edited') % len(emails)
            else:
                self.message = _('%d message(s) unchanged') % len(emails)
            session.ui.mark(self.message)
        except:
            # FIXME: Shutup
            import traceback
            traceback.print_exc()
        return None


class Compose(CompositionCommand):
    """Create a new blank e-mail for editing"""
    SYNOPSIS = ('C', 'compose', 'message/compose', "[ephemeral]")
    ORDER = ('Composing', 0)
    HTTP_CALLABLE = ('POST', )
    HTTP_POST_VARS = dict_merge(CompositionCommand.UPDATE_STRING_DATA, {
        'cid': 'canned response metadata-ID',
    })

    @classmethod
    def _get_canned(cls, idx, cid):
        try:
            return Email(idx, int(cid, 36)
                         ).get_editing_strings().get('body', '')
        except (ValueError, IndexError, TypeError, OSError, IOError):
            traceback.print_exc()  # FIXME, ugly
            return ''

    @classmethod
    def CreateMessage(cls, idx, session, cid=None, ephemeral=False):
        if not ephemeral:
            local_id, lmbox = session.config.open_local_mailbox(session)
        else:
            local_id, lmbox = -1, None
            ephemeral = ['new-mail']
        return (Email.Create(idx, local_id, lmbox,
                             save=(not ephemeral),
                             msg_text=(cid and cls._get_canned(idx, cid)
                                       or ''),
                             ephemeral_mid=ephemeral and ephemeral[0]),
                ephemeral)

    def command(self):
        if 'mid' in self.data:
            return self._error(_('Please use update for editing messages'))

        session, idx = self.session, self._idx()
        ephemeral = (self.args and "ephemeral" in self.args)
        cid = self.data.get('cid', [None])[0]

        email, ephemeral = self.CreateMessage(idx, session,
                                              cid=cid,
                                              ephemeral=ephemeral)
        email_updates = self._get_email_updates(idx,
                                                emails=[email],
                                                create=True)
        update_string = email_updates and email_updates[0][1]
        if update_string:
            email.update_from_string(session, update_string)

        if not ephemeral:
            self._tag_blank([email])
        return self._edit_messages([email], ephemeral=ephemeral, new=True)


class RelativeCompose(Compose):
    _ATT_MIMETYPES = ('application/pgp-signature', )
    _TEXT_PARTTYPES = ('text', 'quote', 'pgpsignedtext', 'pgpsecuretext',
                       'pgpverifiedtext')


class Reply(RelativeCompose):
    """Create reply(-all) drafts to one or more messages"""
    SYNOPSIS = ('r', 'reply', 'message/reply', '[all|ephemeral] <messages>')
    ORDER = ('Composing', 3)
    HTTP_QUERY_VARS = {
        'mid': 'metadata-ID',
        'cid': 'canned response metadata-ID',
        'reply_all': 'reply to all',
        'ephemeral': 'ephemerality',
    }
    HTTP_POST_VARS = {}

    @classmethod
    def _add_gpg_key(cls, idx, session, addr):
        fe, fn = ExtractEmailAndName(addr)
        vcard = session.config.vcards.get_vcard(fe)
        if vcard:
            keys = vcard.get_all('KEY')
            if keys:
                mime, fp = keys[0].value.split('data:')[1].split(',', 1)
                return "%s <%s#%s>" % (fn, fe, fp)
        return "%s <%s>" % (fn, fe)

    @classmethod
    def _create_from_to_cc(cls, idx, session, trees):
        config = session.config
        ahp = AddressHeaderParser()
        ref_from, ref_to, ref_cc = [], [], []
        result = {'from': '', 'to': [], 'cc': []}

        def merge_contact(ai):
            vcard = session.config.vcards.get_vcard(ai.address)
            if vcard:
                ai.merge_vcard(vcard)
            return ai

        # Parse the headers, so we know what we're working with. We prune
        # some of the duplicates at this stage.
        for addrs in [t['addresses'] for t in trees]:
            alist = []
            for dst, addresses in (
                    (ref_from, addrs.get('reply-to') or addrs.get('from', [])),
                    (ref_to, addrs.get('to', [])),
                    (ref_cc, addrs.get('cc', []))):
                alist += [d.address for d in dst]
                dst.extend([a for a in addresses if a.address not in alist])

        # 1st, choose a from address. We'll use the system default if
        # nothing is found, but hopefully we'll find an address we
        # recognize in one of the headers.
        from_address = (session.config.prefs.default_email or
                        session.config.profiles[0].email)
        profile_emails = [p.email for p in session.config.profiles if p.email]
        for src in (ref_from, ref_to, ref_cc):
            matches = [s for s in src if s.address in profile_emails]
            if matches:
                from_address = matches[0].address
                break
        result['from'] = ahp.normalized(addresses=[AddressInfo(p.email, p.name)
            for p in session.config.profiles if p.email == from_address],
                                        force_name=True)

        def addresses(addrs, exclude=[]):
            alist = [from_address] + [a.address for a in exclude]
            return ahp.normalized_addresses(addresses=[merge_contact(a)
                for a in addrs if a.address not in alist
                and not a.address.startswith('noreply@')
                and '@noreply' not in a.address],
                                            with_keys=True,
                                            force_name=True)

        # If only replying to messages sent from chosen from, then this is
        # a follow-up or clarification, so just use the same headers.
        if len([e for e in ref_from if e.address == from_address]
               ) == len(ref_from):
            if ref_to:
                result['to'] = addresses(ref_to)
            if ref_cc:
                result['cc'] = addresses(ref_cc)

        # Else, if replying to other people:
        #   - Construct To from the From lines, excluding own from
        #   - Construct Cc from the To and CC lines, except new To/From
        else:
            result['to'] = addresses(ref_from)
            result['cc'] = addresses(ref_to + ref_cc, exclude=ref_from)

        return result

    @classmethod
    def CreateReply(cls, idx, session, refs,
                    reply_all=False, cid=None, ephemeral=False):
        trees = [m.evaluate_pgp(m.get_message_tree(), decrypt=True)
                 for m in refs]

        headers = cls._create_from_to_cc(idx, session, trees)
        if not reply_all and 'cc' in headers:
            del headers['cc']

        ref_ids = [t['headers_lc'].get('message-id') for t in trees]
        ref_subjs = [t['headers_lc'].get('subject') for t in trees]
        msg_bodies = []
        for t in trees:
            # FIXME: Templates/settings for how we quote replies?
            text = split_long_lines(
                (_('%s wrote:') % t['headers_lc']['from']) + '\n' +
                ''.join([p['data'] for p in t['text_parts']
                         if p['type'] in cls._TEXT_PARTTYPES]))
            msg_bodies.append('\n\n' + text.replace('\n', '\n> '))

        if not ephemeral:
            local_id, lmbox = session.config.open_local_mailbox(session)
        else:
            local_id, lmbox = -1, None
            if reply_all:
                ephemeral = ['reply-all-%s' % refs[0].msg_mid()]
            else:
                ephemeral = ['reply-%s' % refs[0].msg_mid()]

        if 'cc' in headers:
            fmt = _('Composing a reply from %(from)s to %(to)s, cc %(cc)s')
        else:
            fmt = _('Composing a reply from %(from)s to %(to)s')
        session.ui.debug(fmt % headers)

        if cid:
            # FIXME: Instead, we should use placeholders in the template
            #        and insert the quoted bits in the right place (or
            #        nowhere if the template doesn't want them).
            msg_bodies[:0] = [cls._get_canned(idx, cid)]

        return (Email.Create(idx, local_id, lmbox,
                             msg_text='\n\n'.join(msg_bodies),
                             msg_subject=('Re: %s' % ref_subjs[-1]),
                             msg_from=headers.get('from', None),
                             msg_to=headers.get('to', []),
                             msg_cc=headers.get('cc', []),
                             msg_references=[i for i in ref_ids if i],
                             save=(not ephemeral),
                             ephemeral_mid=ephemeral and ephemeral[0]),
                ephemeral)

    def command(self):
        session, config, idx = self.session, self.session.config, self._idx()

        reply_all = False
        ephemeral = False
        args = list(self.args)
        if not args:
            args = ["=%s" % x for x in self.data.get('mid', [])]
            ephemeral = bool(self.data.get('ephemeral', False))
            reply_all = bool(self.data.get('reply_all', False))
        else:
            while args:
                if args[0].lower() == 'all':
                    reply_all = args.pop(0) or True
                elif args[0].lower() == 'ephemeral':
                    ephemeral = args.pop(0) or True
                else:
                    break

        refs = [Email(idx, i) for i in self._choose_messages(args)]
        if refs:
            try:
                cid = self.data.get('cid', [None])[0]
                email, ephemeral = self.CreateReply(idx, session, refs,
                                                    reply_all=reply_all,
                                                    cid=cid,
                                                    ephemeral=ephemeral)
            except NoFromAddressError:
                return self._error(_('You must configure a '
                                     'From address first.'))

            if not ephemeral:
                self._track_action('replied', refs)
                self._tag_blank([email])

            return self._edit_messages([email], ephemeral=ephemeral)
        else:
            return self._error(_('No message found'))


class Forward(RelativeCompose):
    """Create forwarding drafts of one or more messages"""
    SYNOPSIS = ('f', 'forward', 'message/forward', '[att|ephemeral] <messages>')
    ORDER = ('Composing', 4)
    HTTP_QUERY_VARS = {
        'mid': 'metadata-ID',
        'cid': 'canned response metadata-ID',
        'ephemeral': 'ephemerality',
        'atts': 'forward attachments'
    }
    HTTP_POST_VARS = {}

    @classmethod
    def CreateForward(cls, idx, session, refs,
                      with_atts=False, cid=None, ephemeral=False):
        trees = [m.evaluate_pgp(m.get_message_tree(), decrypt=True)
                 for m in refs]
        ref_subjs = [t['headers_lc']['subject'] for t in trees]
        msg_bodies = []
        msg_atts = []
        for t in trees:
            # FIXME: Templates/settings for how we quote forwards?
            text = '-------- Original Message --------\n'
            for h in ('Date', 'Subject', 'From', 'To'):
                v = t['headers_lc'].get(h.lower(), None)
                if v:
                    text += '%s: %s\n' % (h, v)
            text += '\n'
            text += ''.join([p['data'] for p in t['text_parts']
                             if p['type'] in cls._TEXT_PARTTYPES])
            msg_bodies.append(text)
            if with_atts:
                for att in t['attachments']:
                    if att['mimetype'] not in cls._ATT_MIMETYPES:
                        msg_atts.append(att['part'])

        if not ephemeral:
            local_id, lmbox = session.config.open_local_mailbox(session)
        else:
            local_id, lmbox = -1, None
            if msg_atts:
                ephemeral = ['forward-att-%s' % refs[0].msg_mid()]
            else:
                ephemeral = ['forward-%s' % refs[0].msg_mid()]

        if cid:
            # FIXME: Instead, we should use placeholders in the template
            #        and insert the quoted bits in the right place (or
            #        nowhere if the template doesn't want them).
            msg_bodies[:0] = [cls._get_canned(idx, cid)]

        email = Email.Create(idx, local_id, lmbox,
                             msg_text='\n\n'.join(msg_bodies),
                             msg_subject=('Fwd: %s' % ref_subjs[-1]),
                             save=(not ephemeral),
                             ephemeral_mid=ephemeral and ephemeral[0])

        if msg_atts:
            msg = email.get_msg()
            for att in msg_atts:
                msg.attach(att)
            email.update_from_msg(session, msg)

        return email, ephemeral

    def command(self):
        session, config, idx = self.session, self.session.config, self._idx()

        with_atts = False
        ephemeral = False
        args = list(self.args)
        if not args:
            args = ["=%s" % x for x in self.data.get('mid', [])]
            ephemeral = bool(self.data.get('ephemeral', False))
            with_atts = bool(self.data.get('atts', False))
        else:
            while args:
                if args[0].lower() == 'att':
                    with_atts = args.pop(0) or True
                elif args[0].lower() == 'ephemeral':
                    ephemeral = args.pop(0) or True
                else:
                    break

        if ephemeral and with_atts:
            raise UsageError(_('Sorry, ephemeral messages cannot have '
                               'attachments at this time.'))

        refs = [Email(idx, i) for i in self._choose_messages(args)]
        if refs:
            cid = self.data.get('cid', [None])[0]
            email, ephemeral = self.CreateForward(idx, session, refs,
                                                  with_atts=with_atts,
                                                  cid=cid,
                                                  ephemeral=ephemeral)

            if not ephemeral:
                self._track_action('fwded', refs)
                self._tag_blank([email])

            return self._edit_messages([email], ephemeral=ephemeral)
        else:
            return self._error(_('No message found'))


class Attach(CompositionCommand):
    """Attach a file to a message"""
    SYNOPSIS = ('a', 'attach', 'message/attach', '<messages> [<path/to/file>]')
    ORDER = ('Composing', 2)
    HTTP_CALLABLE = ('POST', 'UPDATE')
    HTTP_QUERY_VARS = {}
    HTTP_POST_VARS = {
        'mid': 'metadata-ID',
        'file-data': 'file data'
    }

    def command(self, emails=None):
        session, idx = self.session, self._idx()
        args = list(self.args)

        files = []
        filedata = {}
        if 'file-data' in self.data:
            count = 0
            for fd in self.data['file-data']:
                fn = (hasattr(fd, 'filename')
                      and fd.filename or 'attach-%d.dat' % count)
                filedata[fn] = fd
                files.append(fn)
                count += 1
        else:
            while os.path.exists(args[-1]):
                files.append(args.pop(-1))

        if not files:
            return self._error(_('No files found'))

        if not emails:
            emails = [self._actualize_ephemeral(i) for i in
                      self._choose_messages(args, allow_ephemeral=True)]
        if not emails:
            return self._error(_('No messages selected'))

        updated = []
        for email in emails:
            subject = email.get_msg_info(MailIndex.MSG_SUBJECT)
            try:
                email.add_attachments(session, files, filedata=filedata)
                updated.append(email)
            except NotEditableError:
                session.ui.error(_('Read-only message: %s') % subject)
            except:
                session.ui.error(_('Error attaching to %s') % subject)
                self._ignore_exception()

        self.message = _('Attached %s to %d messages'
                         ) % (', '.join(files), len(updated))
        session.ui.notify(self.message)
        return self._return_search_results(self.message, updated,
                                           expand=updated)


class Sendit(CompositionCommand):
    """Mail/bounce a message (to someone)"""
    SYNOPSIS = (None, 'bounce', 'message/send', '<messages> [<emails>]')
    ORDER = ('Composing', 5)
    HTTP_CALLABLE = ('POST', )
    HTTP_QUERY_VARS = {}
    HTTP_POST_VARS = {
        'mid': 'metadata-ID',
        'to': 'recipients'
    }

    def command(self, emails=None):
        session, config, idx = self.session, self.session.config, self._idx()
        args = list(self.args)

        bounce_to = []
        while args and '@' in args[-1]:
            bounce_to.append(args.pop(-1))
        for rcpt in (self.data.get('to', []) +
                     self.data.get('cc', []) +
                     self.data.get('bcc', [])):
            bounce_to.extend(ExtractEmails(rcpt))

        if not emails:
            args.extend(['=%s' % mid for mid in self.data.get('mid', [])])
            mids = self._choose_messages(args)
            emails = [Email(idx, i) for i in mids]

        # Process one at a time so we don't eat too much memory
        sent = []
        missing_keys = []
        for email in emails:
            events = []
            try:
                msg_mid = email.get_msg_info(idx.MSG_MID)

                # This is a unique sending-ID. This goes in the public (meant
                # for debugging help) section of the event-log, so we take
                # care to not reveal details about the message or recipients.
                msg_sid = sha1b64(email.get_msg_info(idx.MSG_ID),
                                  *sorted(bounce_to))[:8]

                # We load up any incomplete events for sending this message
                # to this set of recipients. If nothing is in flight, create
                # a new event for tracking this operation.
                events = list(config.event_log.incomplete(source=self,
                                                          data_mid=msg_mid,
                                                          data_sid=msg_sid))
                if not events:
                    events.append(config.event_log.log(
                        source=self,
                        flags=Event.RUNNING,
                        message=_('Sending message'),
                        data={'mid': msg_mid, 'sid': msg_sid}))

                SendMail(session, [PrepareMessage(config,
                                                  email.get_msg(pgpmime=False),
                                                  rcpts=(bounce_to or None),
                                                  events=events)])
                for ev in events:
                    ev.flags = Event.COMPLETE
                    config.event_log.log_event(ev)
                sent.append(email)
            except KeyLookupError, kle:
                # This is fatal, we don't retry
                message = _('Missing keys %s') % kle.missing
                for ev in events:
                    ev.flags = Event.COMPLETE
                    ev.message = message
                    config.event_log.log_event(ev)
                session.ui.warning(message)
                missing_keys.extend(kle.missing)
                self._ignore_exception()
            except:
                # We want to try that again!
                message = _('Failed to send %s') % email
                for ev in events:
                    ev.flags = Event.INCOMPLETE
                    ev.message = message
                    config.event_log.log_event(ev)
                session.ui.error(message)
                self._ignore_exception()

        if 'compose' in config.sys.debug:
            sys.stderr.write(('compose/Sendit: Send %s to %s (sent: %s)\n'
                              ) % (len(emails),
                                   bounce_to or '(header folks)', sent))

        if missing_keys:
            self.error_info['missing_keys'] = missing_keys
        if sent:
            self._tag_sent(sent)
            self._tag_outbox(sent, untag=True)
            self._tag_drafts(sent, untag=True)
            self._tag_blank(sent, untag=True)
            for email in sent:
                email.reset_caches()
                idx.index_email(self.session, email)

            return self._return_search_results(
                _('Sent %d messages') % len(sent), sent, sent=sent)
        else:
            return self._error(_('Nothing was sent'))


class Update(CompositionCommand):
    """Update message from a file or HTTP upload."""
    SYNOPSIS = ('u', 'update', 'message/update', '<messages> <<filename>')
    ORDER = ('Composing', 1)
    HTTP_CALLABLE = ('POST', 'UPDATE')
    HTTP_POST_VARS = dict_merge(CompositionCommand.UPDATE_STRING_DATA,
                                Attach.HTTP_POST_VARS)

    def command(self, create=True, outbox=False):
        session, config, idx = self.session, self.session.config, self._idx()
        email_updates = self._get_email_updates(idx,
                                                create=create,
                                                noneok=outbox)

        if not email_updates:
            return self._error(_('Nothing to do!'))
        try:
            if (self.data.get('file-data') or [''])[0]:
                if not Attach(session, data=self.data).command(emails=emails):
                    return False

            for email, update_string in email_updates:
                email.update_from_string(session, update_string, final=outbox)

            emails = [e for e, u in email_updates]
            message = _('%d message(s) updated') % len(email_updates)

            self._tag_blank(emails, untag=True)
            self._tag_drafts(emails, untag=outbox)
            self._tag_outbox(emails, untag=(not outbox))

            if outbox:
                return self._return_search_results(message, emails,
                                                   sent=emails)
            else:
                return self._edit_messages(emails, new=False, tag=False)
        except KeyLookupError, kle:
            return self._error(_('Missing encryption keys'),
                               info={'missing_keys': kle.missing})


class UnThread(CompositionCommand):
    """Remove a message from a thread."""
    SYNOPSIS = (None, 'unthread', 'message/unthread', None)
    HTTP_CALLABLE = ('POST', 'UPDATE')
    HTTP_POST_VARS = {'mid': 'message-id'}

    def command(self):
        session, config, idx = self.session, self.session.config, self._idx()

        # Message IDs can come from post data
        args = list(self.args)
        for mid in self.data.get('mid', []):
            args.append('=%s' % mid)
        emails = [Email(idx, mid) for mid in self._choose_messages(args)]

        if emails:
            for email in emails:
                idx.unthread_message(email.msg_mid())
            return self._return_search_results(
                _('Unthreaded %d messaages') % len(emails), emails)
        else:
            return self._error(_('Nothing to do!'))


class UpdateAndSendit(Update):
    """Update message from an HTTP upload and move to outbox."""
    SYNOPSIS = ('m', 'mail', 'message/update/send', None)

    def command(self, create=True, outbox=True):
        return Update.command(self, create=create, outbox=outbox)


class EmptyOutbox(Command):
    """Try to empty the outbox."""
    SYNOPSIS = (None, 'sendmail', None, None)

    @classmethod
    def sendmail(cls, session):
        cfg, idx = session.config, session.config.index
        messages = []
        for tag in cfg.get_tags(type='outbox'):
            search = ['in:%s' % tag._key]
            for msg_idx_pos in idx.search(session, search,
                                          order='flat-index').as_set():
                messages.append('=%s' % b36(msg_idx_pos))
        if messages:
            return Sendit(session, arg=messages).run()
        else:
            return True

    def command(self):
        return self.sendmail(self.session)


_plugins.register_config_variables('prefs', {
    'empty_outbox_interval': [_('Delay between attempts to send mail'),
                              int, 90]
})
_plugins.register_slow_periodic_job('sendmail',
                                    'prefs.empty_outbox_interval',
                                    EmptyOutbox.sendmail)
_plugins.register_commands(Compose, Reply, Forward,  # Create
                           Draft, Update, Attach,    # Manipulate
                           UnThread,                 # ...
                           Sendit, UpdateAndSendit,  # Send
                           EmptyOutbox)              # ...

########NEW FILE########
__FILENAME__ = contacts
from gettext import gettext as _

from mailpile.plugins import PluginManager
from mailpile.commands import Command, Action
from mailpile.mailutils import Email, ExtractEmails, ExtractEmailAndName
from mailpile.vcard import SimpleVCard, VCardLine, AddressInfo
from mailpile.util import *


_plugins = PluginManager(builtin=__file__)


##[ VCards ]########################################

class VCardCommand(Command):
    VCARD = "vcard"

    def _make_new_vcard(self, handle, name):
        l = [VCardLine(name='fn', value=name),
             VCardLine(name='kind', value=self.KIND)]
        if self.KIND == 'individual':
            return SimpleVCard(VCardLine(name='email', value=handle), *l)
        else:
            return SimpleVCard(VCardLine(name='nickname', value=handle), *l)

    def _valid_vcard_handle(self, vc_handle):
        return (vc_handle and '@' in vc_handle[1:])

    def _add_from_messages(self):
        pairs, idx = [], self._idx()
        for email in [Email(idx, i) for i in self._choose_messages(self.args)]:
            pairs.append(ExtractEmailAndName(email.get_msg_info(idx.MSG_FROM)))
        return pairs

    def _pre_delete_vcard(self, vcard):
        pass

    def _vcard_list(self, vcards, mode='mpCard', info=None):
        info = info or {}
        if mode == 'lines':
            data = [x.as_lines() for x in vcards if x]
        else:
            data = [x.as_mpCard() for x in vcards if x]
        info.update({
            self.VCARD + 's': data,
            "count": len(vcards)
        })
        return info


class VCard(VCardCommand):
    """Add/remove/list/edit vcards"""
    SYNOPSIS = (None, 'vcard', None, '<nickname>')
    ORDER = ('Internals', 6)
    KIND = ''

    def command(self, save=True):
        session, config = self.session, self.session.config
        vcards = []
        for email in self.args:
            vcard = config.vcards.get_vcard(email)
            if vcard:
                vcards.append(vcard)
            else:
                session.ui.warning('No such %s: %s' % (self.VCARD, email))
        if len(vcards) == 1:
            return {"contact": vcards[0].as_mpCard()}
        else:
            return {"contacts": [x.as_mpCard() for x in vcards]}


class AddVCard(VCardCommand):
    """Add one or more vcards"""
    SYNOPSIS = (None, 'vcard/add', None, '<msgs>', '<email> = <name>')
    ORDER = ('Internals', 6)
    KIND = ''
    HTTP_CALLABLE = ('POST', 'PUT', 'GET')
    HTTP_QUERY_VARS = {
        '@contactemail': 'e-mail address',
        '@contactname': 'Contact name',
    }

    def command(self):
        session, config, idx = self.session, self.session.config, self._idx()

        # FIXME: This method SHOULD NOT make changes on GET.
        #        It shouldn't really allow GET at all.

        if (len(self.args) > 2
                and self.args[1] == '='
                and self._valid_vcard_handle(self.args[0])):
            pairs = [(self.args[0], ' '.join(self.args[2:]))]
        elif self.data:
            if "@contactname" in self.data and "@contactemail" in self.data:
                pairs = [(self.data["@contactemail"][0],
                          self.data["@contactname"][0])]
            elif "contactnames" in self.data and "contactemails" in self.data:
                pairs = zip(self.data["contactemails"],
                            self.data["contactnames"])
        else:
            pairs = self._add_from_messages()

        if pairs:
            vcards = []
            for handle, name in pairs:
                if handle.lower() not in config.vcards:
                    vcard = self._make_new_vcard(handle.lower(), name)
                    config.vcards.index_vcard(vcard)
                    vcards.append(vcard)
                else:
                    session.ui.warning('Already exists: %s' % handle)
        else:
            return self._error('Nothing to do!')
        return {"contacts": [x.as_mpCard() for x in vcards]}


class VCardAddLines(VCardCommand):
    """Add a lines to a VCard"""
    SYNOPSIS = (None, 'vcard/addline', None, '<email> <lines>')
    ORDER = ('Internals', 6)
    KIND = ''
    HTTP_CALLABLE = ('POST', 'UPDATE')

    def command(self):
        session, config = self.session, self.session.config
        handle, var, lines = self.args[0], self.args[1], self.args[2:]
        vcard = config.vcards.get_vcard(handle)
        if not vcard:
            return self._error('%s not found: %s' % (self.VCARD, handle))
        config.vcards.deindex_vcard(vcard)
        try:
            vcard.add(*[VCardLine(l) for l in lines])
            vcard.save()
            return self._vcard_list([vcard], info={
                'updated': handle,
                'added': len(lines)
            })
        except:
            config.vcards.index_vcard(vcard)
            self._ignore_exception()
            return self._error('Error setting %s = %s' % (var, val))
        finally:
            config.vcards.index_vcard(vcard)


class RemoveVCard(VCardCommand):
    """Delete vcards"""
    SYNOPSIS = (None, 'vcard/remove', None, '<email>')
    ORDER = ('Internals', 6)
    KIND = ''
    HTTP_CALLABLE = ('POST', 'DELETE')

    def command(self):
        session, config = self.session, self.session.config
        for handle in self.args:
            vcard = config.vcards.get_vcard(handle)
            if vcard:
                self._pre_delete_vcard(vcard)
                config.vcards.del_vcard(handle)
            else:
                session.ui.error('No such contact: %s' % handle)
        return True


class ListVCards(VCardCommand):
    """Find vcards"""
    SYNOPSIS = (None, 'vcard/list', None, '[--lines] [<terms>]')
    ORDER = ('Internals', 6)
    KIND = ''
    HTTP_QUERY_VARS = {
        'q': 'search terms',
        'format': 'lines or mpCard (default)',
        'count': 'how many to display (default=40)',
        'offset': 'skip how many in the display (default=0)',
    }
    HTTP_CALLABLE = ('GET')

    def command(self):
        session, config = self.session, self.session.config
        kinds = self.KIND and [self.KIND] or []
        args = list(self.args)

        if 'format' in self.data:
            fmt = self.data['format'][0]
        elif args and args[0] == '--lines':
            args.pop(0)
            fmt = 'lines'
        else:
            fmt = 'mpCard'

        if 'q' in self.data:
            terms = self.data['q']
        else:
            terms = args

        if 'count' in self.data:
            count = int(self.data['count'][0])
        else:
            count = 120

        if 'offset' in self.data:
            offset = int(self.data['offset'][0])
        else:
            offset = 0

        vcards = config.vcards.find_vcards(terms, kinds=kinds)
        total = len(vcards)
        vcards = vcards[offset:offset + count]
        return self._vcard_list(vcards, mode=fmt, info={
            'terms': args,
            'offset': offset,
            'count': count,
            'total': total,
            'start': offset,
            'end': offset + count,
        })


def ContactVCard(parent):
    """A factory for generating contact commands"""
    synopsis = [(t and t.replace('vcard', 'contact') or t)
                for t in parent.SYNOPSIS]
    synopsis[2] = synopsis[1]

    class ContactVCardCommand(parent):
        SYNOPSIS = tuple(synopsis)
        KIND = 'individual'
        ORDER = ('Tagging', 3)
        VCARD = "contact"

    return ContactVCardCommand


class Contact(ContactVCard(VCard)):
    """View contacts"""
    SYNOPSIS = (None, 'contact', 'contact', '[<email>]')

    def command(self, save=True):
        contact = VCard.command(self, save)
        # Tee-hee, monkeypatching results.
        contact["sent_messages"] = 0
        contact["received_messages"] = 0
        contact["last_contact_from"] = 10000000000000
        contact["last_contact_to"] = 10000000000000

        for email in contact["contact"]["email"]:
            s = Action(self.session, "search",
                       ["in:Sent", "to:%s" % (email["email"])]).as_dict()
            contact["sent_messages"] += s["result"]["stats"]["total"]
            for mid in s["result"]["thread_ids"]:
                msg = s["result"]["data"]["metadata"][mid]
                if msg["timestamp"] < contact["last_contact_to"]:
                    contact["last_contact_to"] = msg["timestamp"]
                    contact["last_contact_to_msg_url"] = msg["urls"]["thread"]

            s = Action(self.session, "search",
                       ["from:%s" % (email["email"])]).as_dict()
            contact["received_messages"] += s["result"]["stats"]["total"]
            for mid in s["result"]["thread_ids"]:
                msg = s["result"]["data"]["metadata"][mid]
                if msg["timestamp"] < contact["last_contact_from"]:
                    contact["last_contact_from"] = msg["timestamp"]
                    contact["last_contact_from_msg_url"
                            ] = msg["urls"]["thread"]

        if contact["last_contact_to"] == 10000000000000:
            contact["last_contact_to"] = False
            contact["last_contact_to_msg_url"] = ""

        if contact["last_contact_from"] == 10000000000000:
            contact["last_contact_from"] = False
            contact["last_contact_from_msg_url"] = ""

        return contact


class AddContact(ContactVCard(AddVCard)):
    """Add contacts"""


class ContactAddLines(ContactVCard(VCardAddLines)):
    """Set contact variables"""


class RemoveContact(ContactVCard(RemoveVCard)):
    """Remove a contact"""


class ListContacts(ContactVCard(ListVCards)):
    SYNOPSIS = (None, 'contact/list', 'contact/list', '[--lines] [<terms>]')
    """Find contacts"""


class ContactImport(Command):
    """Import contacts"""
    SYNOPSIS = (None, 'contact/import', 'contact/import', '[<parameters>]')
    ORDER = ('Internals', 6)
    HTTP_CALLABLE = ('GET', )

    def command(self, format, terms=None, **kwargs):
        session, config = self.session, self.session.config

        if not format in PluginManager.CONTACT_IMPORTERS.keys():
            session.ui.error("No such import format")
            return False

        importer = PluginManager.CONTACT_IMPORTERS[format]

        if not all([x in kwargs.keys() for x in importer.required_parameters]):
            session.ui.error(
                _("Required paramter missing. Required parameters "
                  "are: %s") % ", ".join(importer.required_parameters))
            return False

        allparams = importer.required_parameters + importer.optional_parameters

        if not all([x in allparams for x in kwargs.keys()]):
            session.ui.error(
                _("Unknown parameter passed to importer. "
                  "Provided %s; but known parameters are: %s"
                  ) % (", ".join(kwargs), ", ".join(allparams)))
            return False

        imp = importer(kwargs)
        if terms:
            contacts = imp.filter_contacts(terms)
        else:
            contacts = imp.get_contacts()

        for importedcontact in contacts:
            # Check if contact exists. If yes, then update. Else create.
            pass


class ContactImporters(Command):
    """Return a list of contact importers"""
    SYNOPSIS = (None, 'contact/importers', 'contact/importers', '')
    ORDER = ('Internals', 6)
    HTTP_CALLABLE = ('GET', )

    def command(self):
        res = []
        for iname, importer in CONTACT_IMPORTERS.iteritems():
            r = {}
            r["short_name"] = iname
            r["format_name"] = importer.format_name
            r["format_description"] = importer.format_description
            r["optional_parameters"] = importer.optional_parameters
            r["required_parameters"] = importer.required_parameters
            res.append(r)

        return res


class AddressSearch(VCardCommand):
    """Find addresses (in contacts or mail index)"""
    SYNOPSIS = (None, 'search/address', 'search/address', '[<terms>]')
    ORDER = ('Searching', 6)
    HTTP_QUERY_VARS = {
        'q': 'search terms',
        'count': 'number of results',
        'offset': 'offset results'
    }

    def _boost_rank(self, term, *matches):
        boost = 0.0
        for match in matches:
            match = match.lower()
            if term in match:
                if match.startswith(term):
                    boost += 25 * (float(len(term)) / len(match))
                else:
                    boost += 5 * (float(len(term)) / len(match))
        return int(boost)

    def _vcard_addresses(self, cfg, terms):
        addresses = {}
        for vcard in cfg.vcards.find_vcards(terms, kinds='individual'):
            fn = vcard.get('fn')
            for email_vcl in vcard.get_all('email'):
                info = addresses.get(email_vcl.value) or {}
                info.update(AddressInfo(email_vcl.value, fn.value,
                                        vcard=vcard))
                addresses[email_vcl.value] = info
                for term in terms:
                    info['rank'] += self._boost_rank(term, fn.value,
                                                     email_vcl.value)

        return addresses.values()

    def _index_addresses(self, cfg, terms, vcard_addresses):
        existing = dict([(k['address'].lower(), k) for k in vcard_addresses])
        index = self._idx()

        # Figure out which tags are invisible so we can skip messages marked
        # with those tags.
        invisible = set([t._key for t in cfg.get_tags(flag_hides=True)])

        # 1st, go through the last 1000 or so messages in the index and search
        # for matching senders or recipients, give medium priority.
        matches = {}
        addresses = []
        for msg_idx in index.INDEX_SORT['date_fwd'][-2500:]:
            msg_info = index.get_msg_at_idx_pos(msg_idx)
            tags = set(msg_info[index.MSG_TAGS].split(','))
            frm = msg_info[index.MSG_FROM]
            match = not (tags & invisible)
            if match:
                for term in terms:
                    if term not in frm.lower():
                        match = False
            if match:
                matches[frm] = matches.get(frm, 0) + 1
            if len(matches) > 1000:
                break

        # FIXME: 2nd, search the social graph for matches, give low priority.
        for frm in index.EMAILS:
            match = True
            for term in terms:
                if term not in frm.lower():
                    match = False
            if match:
                matches[frm] = matches.get(frm, 0) + 1

        # Assign info & scores!
        for frm in matches:
            email, fn = ExtractEmailAndName(frm)

            boost = min(10, matches[frm])
            for term in terms:
                boost += self._boost_rank(term, fn, email)

            if not email or '@' not in email:
                # FIXME: This may not be the right thing for alternate
                #        message transports.
                pass
            elif email.lower() in existing:
                existing[email.lower()]['rank'] += min(20, boost)
            else:
                info = AddressInfo(email, fn)
                existing[email.lower()] = info
                addresses.append(info)

        return addresses

    def command(self):
        session, config = self.session, self.session.config
        if 'q' in self.data:
            terms = [t.lower() for t in self.data['q']]
        else:
            terms = [t.lower() for t in self.args]
        count = int(self.data.get('count', 10))
        offset = int(self.data.get('offset', 0))

        vcard_addrs = self._vcard_addresses(config, terms)
        index_addrs = self._index_addresses(config, terms, vcard_addrs)
        addresses = vcard_addrs + index_addrs
        addresses.sort(key=lambda k: -k['rank'])
        total = len(addresses)
        return {
            'addresses': addresses[offset:min(offset+count, total)],
            'displayed': min(count, total),
            'total': total,
            'offset': offset,
            'count': count,
            'start': offset,
            'end': offset+count,
        }


_plugins.register_commands(VCard, AddVCard, VCardAddLines,
                           RemoveVCard, ListVCards)
_plugins.register_commands(Contact, AddContact, ContactAddLines,
                           RemoveContact, ListContacts,
                           AddressSearch)
_plugins.register_commands(ContactImport, ContactImporters)

########NEW FILE########
__FILENAME__ = cryptostate
from gettext import gettext as _

from mailpile.plugins import PluginManager
from mailpile.crypto.state import EncryptionInfo, SignatureInfo


_plugins = PluginManager(builtin=__file__)


##[ Keywords ]################################################################

def text_kw_extractor(index, msg, ctype, text):
    kw = set()
    if ('-----BEGIN PGP' in text and '\n-----END PGP' in text):
        kw.add('pgp:has')
        kw.add('crypto:has')
    return kw


def meta_kw_extractor(index, msg_mid, msg, msg_size, msg_ts):
    kw, enc, sig = set(), set(), set()
    def crypto_eval(part):
        # This is generic
        if part.encryption_info.get('status') != 'none':
            enc.add('mp_%s-%s' % ('enc', part.encryption_info['status']))
            kw.add('crypto:has')
        if part.signature_info.get('status') != 'none':
            sig.add('mp_%s-%s' % ('sig', part.signature_info['status']))
            kw.add('crypto:has')
        if 'cryptostate' in index.config.sys.debug:
            print 'part status(=%s): enc=%s sig=%s' % (msg_mid,
                part.encryption_info.get('status'),
                part.signature_info.get('status')
            )

        # This is OpenPGP-specific
        if (part.encryption_info.get('protocol') == 'openpgp'
                or part.signature_info.get('protocol') == 'openpgp'):
            kw.add('pgp:has')

        # FIXME: Other encryption protocols?

    def choose_one(fmt, statuses, ordering):
        for o in ordering:
            for mix in ('', 'mixed-'):
                status = (fmt % (mix+o))
                if status in statuses:
                    return set([status])
        return set(list(statuses)[:1])

    # Evaluate all the message parts
    crypto_eval(msg)
    for p in msg.walk():
        crypto_eval(p)

    # OK, we should have exactly encryption state...
    if len(enc) < 1:
        enc.add('mp_enc-none')
    elif len(enc) > 1:
        enc = choose_one('mp_enc-%s', enc, EncryptionInfo.STATUSES)

    # ... and exactly one signature state.
    if len(sig) < 1:
        sig.add('mp_sig-none')
    elif len(sig) > 1:
        sig = choose_one('mp_sig-%s', sig, SignatureInfo.STATUSES)

    # Emit tags for our states
    for tname in (enc | sig):
        tag = index.config.get_tags(slug=tname)
        if tag:
            kw.add('%s:in' % tag[0]._key)

    if 'cryptostate' in index.config.sys.debug:
        print 'part crypto state(=%s): %s' % (msg_mid, ','.join(list(kw)))

    return list(kw)

_plugins.register_text_kw_extractor('crypto_tkwe', text_kw_extractor)
_plugins.register_meta_kw_extractor('crypto_mkwe', meta_kw_extractor)


##[ Search helpers ]##########################################################

def search(config, idx, term, hits):
    #
    # FIXME: Translate things like pgp:signed into a search for all the
    #        tags that have signatures (good or bad).
    #
    return []

_plugins.register_search_term('crypto', search)
_plugins.register_search_term('pgp', search)

########NEW FILE########
__FILENAME__ = crypto_policy
import mailpile.plugins
from mailpile.vcard import VCardLine
from mailpile.commands import Command
from mailpile.mailutils import Email


VCARD_CRYPTO_POLICY = 'X-MAILPILE-CRYPTO-POLICY'
CRYPTO_POLICIES = ['none', 'sign', 'encrypt', 'sign-encrypt', 'default']

##[ Commands ]################################################################

class CryptoPolicyBaseAction(Command):
    """ Base class for crypto policy commands """

    def _get_keywords(self, e):
        idx = self._idx()
        mid = e.msg_mid()
        kws, snippet = idx.read_message(
            self.session,
            mid,
            e.get_msg_info(field=idx.MSG_ID),
            e.get_msg(),
            e.get_msg_size(),
            int(e.get_msg_info(field=idx.MSG_DATE), 36))
        return kws

    def _search(self, email):
        idx = self._idx()
        return idx.search(self.session, ['to:' + email, 'has:crypto', 'has:pgp'], order='date_fwd')

    def _find_policy_based_on_mails(self, mail_idxs):
        idx = self._idx()
        for mail_idx in mail_idxs.as_set():
            mail = Email(idx, mail_idx).get_msg()

            if mail.encryption_info.get('status') != 'none':
                return 'encrypt'
            if mail.signature_info.get('status') != 'none':
                return 'sign'

        return 'none'

    def _find_policy(self, email):
        mail_idxs = self._search(email)

        if mail_idxs:
            return self._find_policy_based_on_mails(mail_idxs)
        else:
            return 'none'

    def _update_vcard(self, vcard, policy):
        if 'default' == policy:
            for line in vcard.get_all(VCARD_CRYPTO_POLICY):
                vcard.remove(line.line_id)
        else:
            if len(vcard.get_all(VCARD_CRYPTO_POLICY)) > 0:
                vcard.get(VCARD_CRYPTO_POLICY).value = policy
            else:
                vcard.add(VCardLine(name=VCARD_CRYPTO_POLICY, value=policy))


class AutoDiscoverCryptoPolicy(CryptoPolicyBaseAction):
    """ Auto discovers crypto policy for all known contacts """
    SYNOPSIS = (None, 'discover_crypto_policy', None, None)
    ORDER = ('AutoDiscover', 0)

    def _set_crypto_policy(self, email, policy):
        if policy != 'none':
            vcard = self.session.config.vcards.get_vcard(email)
            if vcard:
                self._update_vcard(vcard, policy)
                self.session.ui.mark('policy for %s will be %s' % (email, policy))
                return True
            else:
                self.session.ui.mark('skipped setting policy for %s to policy,  no vcard entry found' % email)
        return False

    def _update_crypto_state(self, email):
        policy = self._find_policy(email)

        return self._set_crypto_policy(email, policy)

    def command(self):
        idx = self._idx()

        updated = set()
        for email in idx.EMAIL_IDS:
            if self._update_crypto_state(email):
                updated.add(email)

        return updated


class UpdateCryptoPolicyForUser(CryptoPolicyBaseAction):
    """ Update crypto policy for a single user """
    SYNOPSIS = (None, 'crypto_policy/set', 'crypto_policy/set', '<email address> none|sign|encrypt|sign-encrypt|default')
    ORDER = ('Internals', 9)
    HTTP_CALLABLE = ('POST',)
    HTTP_QUERY_VARS = {'email': 'contact email', 'policy': 'new policy'}

    def command(self):
        email, policy = self._parse_args()

        if policy not in CRYPTO_POLICIES:
            return self._error('Policy has to be one of %s' % '|'.join(CRYPTO_POLICIES))

        vcard = self.session.config.vcards.get_vcard(email)
        if vcard:
            self._update_vcard(vcard, policy)
            return {'email': email, 'policy:': policy}
        else:
            return self._error('No vcard for email %s!' % email)

    def _parse_args(self):
        if self.data:
            email = unicode(self.data['email'][0])
            policy = unicode(self.data['policy'][0])
        else:
            if len(self.args) != 2:
                return self._error('Please provide email address and policy!')

            email = self.args[0]
            policy = self.args[1]
        return email, policy


class CryptoPolicyForUser(CryptoPolicyBaseAction):
    """ Retrieve the current crypto policy for a user """
    SYNOPSIS = (None, 'crypto_policy', 'crypto_policy', '[<emailaddresses>]')
    ORDER = ('Internals', 9)
    HTTP_CALLABLE = ('GET',)

    def command(self):
        if len(self.args) != 1:
            return self._error('Please provide a single email address!')

        email = self.args[0]

        policy_from_vcard = self._vcard_policy(email)
        if policy_from_vcard:
            return policy_from_vcard
        else:
            return self._find_policy(email)

    def _vcard_policy(self, email):
        vcard = self.session.config.vcards.get_vcard(email)
        if vcard and len(vcard.get_all(VCARD_CRYPTO_POLICY)) > 0:
            return vcard.get(VCARD_CRYPTO_POLICY).value
        else:
            return None


mailpile.plugins.register_commands(AutoDiscoverCryptoPolicy, CryptoPolicyForUser, UpdateCryptoPolicyForUser)

########NEW FILE########
__FILENAME__ = crypto_utils
import datetime
import re
import time
from gettext import gettext as _

from mailpile.plugins import PluginManager
from mailpile.commands import Command
from mailpile.plugins.search import Search
from mailpile.mailutils import Email, MBX_ID_LEN

from mailpile.crypto.gpgi import GnuPG
from mailpile.crypto.nicknym import Nicknym


_plugins = PluginManager(builtin=__file__)


class GPGKeySearch(Command):
    """Search for a GPG Key."""
    ORDER = ('', 0)
    SYNOPSIS = (None, 'crypto/gpg/searchkey', 'crypto/gpg/searchkey', '<terms>')
    HTTP_CALLABLE = ('GET', )
    HTTP_QUERY_VARS = {'q': 'search terms'}

    class CommandResult(Command.CommandResult):
        def as_text(self):
            if self.result:
                return '\n'.join(["%s: %s <%s>" % (keyid, x["name"], x["email"]) for keyid, det in self.result.iteritems() for x in det["uids"]])
            else:
                return _("No results")

    def command(self):
        args = list(self.args)
        for q in self.data.get('q', []):
            args.extend(q.split())

        g = GnuPG()
        return g.search_key(" ".join(args))

class GPGKeyReceive(Command):
    """Fetch a GPG Key."""
    ORDER = ('', 0)
    SYNOPSIS = (None, 'crypto/gpg/receivekey', 'crypto/gpg/receivekey', '<keyid>')
    HTTP_CALLABLE = ('POST', )
    HTTP_QUERY_VARS = {'keyid': 'ID of key to fetch'}


    def command(self):
        keyid = self.data.get("keyid", self.args)
        g = GnuPG()
        res = []
        for key in keyid:
            res.append(g.recv_key(key))

        return res

class GPGKeyImport(Command):
    """Import a GPG Key."""
    ORDER = ('', 0)
    SYNOPSIS = (None, 'crypto/gpg/importkey', 'crypto/gpg/importkey',
                '<key_file>')
    HTTP_CALLABLE = ('POST', )
    HTTP_QUERY_VARS = {'key_data': 'Contents of public key to be imported',
                       'key_file': 'Location of file containing the public key'}

    def command(self):
        key_data = ""
        if len(self.args) != 0:
            key_file = self.data.get("key_file", self.args[0])
            with  open(key_file) as file:
                key_data = file.read()
        if "key_data" in self.data:
            key_data = self.data.get("key_data")
        elif "key_file" in self.data:
            pass
        g = GnuPG()
        return g.import_keys(key_data)

class GPGKeySign(Command):
    """Sign a key."""
    ORDER = ('', 0)
    SYNOPSIS = (None, 'crypto/gpg/signkey', 'crypto/gpg/signkey', '<keyid> [<signingkey>]')
    HTTP_CALLABLE = ('POST',)
    HTTP_QUERY_VARS = {'keyid': 'The key to sign',
                       'signingkey': 'The key to sign with'}

    def command(self):
        signingkey = None
        keyid = None
        args = list(self.args)
        try: keyid = args.pop(0)
        except: keyid = self.data.get("keyid", None)
        try: signingkey = args.pop(0)
        except: signingkey = self.data.get("signingkey", None)

        print keyid
        if not keyid:
            return self._error("You must supply a keyid", None)

        g = GnuPG()
        return g.sign_key(keyid, signingkey)


class GPGKeyImportFromMail(Search):
    """Import a GPG Key."""
    ORDER = ('', 0)
    SYNOPSIS = (None, 'crypto/gpg/importkeyfrommail', 
                'crypto/gpg/importkeyfrommail', '<mid>')
    HTTP_CALLABLE = ('POST', )
    HTTP_QUERY_VARS = {'mid': 'Message ID', 'att': 'Attachment ID'}

    class CommandResult(Command.CommandResult):
        def __init__(self, *args, **kwargs):
            Command.CommandResult.__init__(self, *args, **kwargs)

        def as_text(self):
            if self.result:
                return "Imported %d keys (%d updated, %d unchanged) from the mail" % (
                    self.result["results"]["count"],
                    self.result["results"]["imported"],
                    self.result["results"]["unchanged"])
            return ""

    def command(self):
        session, config, idx = self.session, self.session.config, self._idx()
        args = list(self.args)
        if args and args[-1][0] == "#":
            attid = args.pop()
        else:
            attid = self.data.get("att", 'application/pgp-keys')
        args.extend(["=%s" % x for x in self.data.get("mid", [])])
        eids = self._choose_messages(args)
        if len(eids) < 0:
            return self._error("No messages selected", None)
        elif len(eids) > 1:
            return self._error("One message at a time, please", None)

        email = Email(idx, list(eids)[0])
        fn, attr = email.extract_attachment(session, attid, mode='inline')
        if attr and attr["data"]:
            g = GnuPG()
            res = g.import_keys(attr["data"])
            return self._success("Imported key", res)

        return self._error("No results found", None)


class GPGKeyList(Command):
    """Import a GPG Key."""
    ORDER = ('', 0)
    SYNOPSIS = (None, 'crypto/gpg/keylist', 
                'crypto/gpg/keylist', '<address>')
    HTTP_CALLABLE = ('GET', )
    HTTP_QUERY_VARS = {'address': 'E-mail address'}

    def command(self):
        args = list(self.args)
        if len(args) >= 0:
            addr = args[0]
        else:
            addr = self.data.get("address", None)

        if addr is None:
            return self._error("Must supply e-mail address", None)

        g = GnuPG()
        res = g.address_to_keys(args[0])
        return self._success("Searched for keys for e-mail address", res)




class GPGUsageStatistics(Search):
    """Get usage statistics from mail, given an address"""
    ORDER = ('', 0)
    SYNOPSIS = (None, 'crypto/gpg/statistics', 
                'crypto/gpg/statistics', '<address>')
    HTTP_CALLABLE = ('GET', )
    HTTP_QUERY_VARS = {'address': 'E-mail address'}

    class CommandResult(Command.CommandResult):
        def __init__(self, *args, **kwargs):
            Command.CommandResult.__init__(self, *args, **kwargs)

        def as_text(self):
            if self.result:
                return "%d%% of e-mail from %s has PGP signatures (%d/%d)" % (
                    100*self.result["ratio"],
                    self.result["address"],
                    self.result["pgpsigned"],
                    self.result["messages"])
            return ""

    def command(self):
        args = list(self.args)
        if len(args) >= 0:
            addr = args[0]
        else:
            addr = self.data.get("address", None)

        if addr is None:
            return self._error("Must supply an address", None)

        session, idx, _, _ = self._do_search(search=["from:%s" % addr])
        total = 0
        for messageid in session.results:
            total += 1

        session, idx, _, _ = self._do_search(search=["from:%s" % addr, 
            "has:pgp"])
        pgp = 0
        for messageid in session.results:
            pgp += 1

        if total > 0:
            ratio = float(pgp)/total
        else:
            ratio = 0

        res = {"messages": total, 
               "pgpsigned": pgp, 
               "ratio": ratio,
               "address": addr}

        return self._success("Got statistics for address", res)



class NicknymGetKey(Command):
    """Get a key from a nickserver"""
    ORDER = ('', 0)
    SYNOPSIS = (None, 'crypto/nicknym/getkey', 'crypto/nicknym/getkey', 
        '<address> [<keytype>] [<server>]')

    HTTP_CALLABLE = ('POST',)
    HTTP_QUERY_VARS = {
        'address': 'The nick/address to fetch a key for',
       'keytype': 'What type of key to import (defaults to OpenPGP)',
       'server': 'The Nicknym server to use (defaults to autodetect)'}

    def command(self):
        address = self.data.get('address', self.args[0])
        keytype = self.data.get('keytype', None)
        server = self.data.get('server', None)
        if len(self.args) > 1:
            keytype = self.args[1]
        else:
            keytype = 'openpgp'

        if len(self.args) > 2:
            server = self.args[2]

        n = Nicknym(self.session.config)
        return n.get_key(address, keytype, server)

class NicknymRefreshKeys(Command):
    """Get a key from a nickserver"""
    ORDER = ('', 0)
    SYNOPSIS = (None, 'crypto/nicknym/refreshkeys', 
        'crypto/nicknym/refreshkeys', '')

    HTTP_CALLABLE = ('POST',)

    def command(self):
        n = Nicknym(self.session.config)
        n.refresh_keys()
        return True

_plugins.register_commands(GPGKeySearch)
_plugins.register_commands(GPGKeyReceive)
_plugins.register_commands(GPGKeyImport)
_plugins.register_commands(GPGKeyImportFromMail)
_plugins.register_commands(GPGKeySign)
_plugins.register_commands(GPGKeyList)
_plugins.register_commands(GPGUsageStatistics)
_plugins.register_commands(NicknymGetKey)
_plugins.register_commands(NicknymRefreshKeys)

########NEW FILE########
__FILENAME__ = dates
import time
import datetime
from gettext import gettext as _

from mailpile.plugins import PluginManager


_plugins = PluginManager(builtin=__name__)


##[ Keywords ]################################################################

def meta_kw_extractor(index, msg_mid, msg, msg_size, msg_ts):
    mdate = datetime.date.fromtimestamp(msg_ts)
    keywords = [
        '%s:year' % mdate.year,
        '%s:month' % mdate.month,
        '%s:day' % mdate.day,
        '%s-%s:yearmonth' % (mdate.year, mdate.month),
        '%s-%s-%s:date' % (mdate.year, mdate.month, mdate.day)
    ]
    return keywords

_plugins.register_meta_kw_extractor('dates', meta_kw_extractor)


##[ Search terms ]############################################################

def _adjust(d):
    if d[2] > 31:
        d[1] += 1
        d[2] -= 31
    if d[1] > 12:
        d[0] += 1
        d[1] -= 12


def _mk_date(ts):
    mdate = datetime.date.fromtimestamp(ts)
    return '%d-%d-%d' % (mdate.year, mdate.month, mdate.day)


_date_offsets = {
    'today': 0,
    'yesterday': 1
}


def search(config, idx, term, hits):
    try:
        word = term.split(':', 1)[1].lower()
        if '..' in term:
            start, end = word.split('..')
        else:
            start = end = word

        if start in _date_offsets:
            start = _mk_date(time.time() - _date_offsets[start]*24*3600)
        if end in _date_offsets:
            end = _mk_date(time.time() - _date_offsets[end]*24*3600)

        start = [int(p) for p in start.split('-')][:3]
        end = [int(p) for p in end.split('-')[:3]]
        while len(start) < 3:
            start.append(1)
        if len(end) == 1:
            end.extend([12, 31])
        elif len(end) == 2:
            end.append(31)
        if not start <= end:
            raise ValueError()

        terms = []
        while start <= end:
            # Move forward one year?
            if start[1:] == [1, 1]:
                ny = [start[0], 12, 31]
                if ny <= end:
                    terms.append('%d:year' % start[0])
                    start[0] += 1
                    continue

            # Move forward one month?
            if start[2] == 1:
                nm = [start[0], start[1], 31]
                if nm <= end:
                    terms.append('%d-%d:yearmonth' % (start[0], start[1]))
                    start[1] += 1
                    _adjust(start)
                    continue

            # Move forward one day...
            terms.append('%d-%d-%d:date' % tuple(start))
            start[2] += 1
            _adjust(start)

        rt = []
        for t in terms:
            rt.extend(hits(t))
        return rt
    except:
        raise ValueError('Invalid date range: %s' % term)


_plugins.register_search_term('dates', search)
_plugins.register_search_term('date', search)

########NEW FILE########
__FILENAME__ = eventlog
import time
from gettext import gettext as _

from mailpile.plugins import PluginManager
from mailpile.commands import Command
from mailpile.util import *


_plugins = PluginManager(builtin=__file__)


class Events(Command):
    """Display events from the event log"""
    SYNOPSIS = (None, 'eventlog', 'eventlog',
                '[incomplete] [wait] [<count>] [<field>=<val> ...]')
    ORDER = ('Internals', 9)
    HTTP_CALLABLE = ('GET', )
    HTTP_QUERY_VARS = {
        'wait': 'wait for new data?',
        'incomplete': 'incomplete events only?',
        # Filtering by event attributes
        'flag': 'require a flag',
        'flags': 'match all flags',
        'since': 'wait for new data?',
        'source': 'source class',
        # Filtering by event data (syntax is a bit weird)
        'data': 'var:value',
        'private_data': 'var:value'
    }

    WAIT_TIME = 10.0
    GATHER_TIME = 0.1

    _FALSE = ('0', 'off', 'no', 'false')

    def command(self):
        session, config, index = self.session, self.session.config, self._idx()
        event_log = config.event_log

        incomplete = (self.data.get('incomplete', ['no']
                                    )[0].lower() not in self._FALSE)
        waiting = (self.data.get('wait', ['no']
                                 )[0].lower() not in self._FALSE)
        limit = 0
        filters = {}
        for arg in self.args:
            if arg.lower() == 'incomplete':
                incomplete = True
            elif arg.lower() == 'wait':
                waiting = True
            elif '=' in arg:
                field, value = arg.split('=', 1)
                filters[str(field)] = str(value)
            else:
                try:
                    limit = int(arg)
                except ValueError:
                    raise UsageError('Bad argument: %s' % arg)

        # Handle args from the web
        def fset(arg, val):
            if val.startswith('!'):
                filters[arg+'!'] = val[1:]
            else:
                filters[arg] = val
        for arg in self.data:
            if arg in ('source', 'flags', 'flag', 'since'):
                fset(arg, self.data[arg][0])
            elif arg in ('data', 'private_data'):
                for data in self.data[arg]:
                    var, val = data.split(':', 1)
                    fset('%s_%s' % (arg, var), val)

        if waiting:
            tries = 2
            if 'since' not in filters:
                filters['since'] = time.time()
        else:
            tries = 1

        expire = time.time() + self.WAIT_TIME - self.GATHER_TIME
        while expire > time.time():
            if incomplete:
                events = list(config.event_log.incomplete(**filters))
            else:
                events = list(config.event_log.events(**filters))
            if events or not waiting:
                break
            else:
                config.event_log.wait(expire - time.time())
                time.sleep(self.GATHER_TIME)

        result = [e.as_dict() for e in events[-limit:]]
        return self._success(_('Found %d events') % len(result),
                             result=result)


_plugins.register_commands(Events)

########NEW FILE########
__FILENAME__ = exporters
import mailbox
import os
import time
from gettext import gettext as _

import mailpile.config
from mailpile.plugins import PluginManager
from mailpile.util import *
from mailpile.commands import Command
from mailpile.mailutils import Email


_plugins = PluginManager(builtin=os.path.basename(__file__)[:-3])


##[ Configuration ]###########################################################

MAILBOX_FORMATS = ('mbox', 'maildir')

_plugins.register_config_variables('prefs', {
    'export_format': ['Default format for exporting mail',
                      MAILBOX_FORMATS, 'mbox'],
})


##[ Commands ]################################################################

class ExportMail(Command):
    """Export messages to an external mailbox"""
    SYNOPSIS = (None, 'export', None, '<msgs> [flat] [<fmt>:<path>]')
    ORDER = ('Searching', 99)

    def export_path(self, mbox_type):
        if mbox_type == 'mbox':
            return 'mailpile-%d.mbx' % time.time()
        else:
            return 'mailpile-%d'

    def create_mailbox(self, mbox_type, path):
        if mbox_type == 'mbox':
            return mailbox.mbox(path)
        elif mbox_type == 'maildir':
            return mailbox.Maildir(path)
        raise UsageError('Invalid mailbox type: %s' % mbox_type)

    def command(self, save=True):
        session, config, idx = self.session, self.session.config, self._idx()
        mbox_type = config.prefs.export_format

        args = list(self.args)
        if args and ':' in args[-1]:
            mbox_type, path = args.pop(-1).split(':', 1)
        else:
            path = self.export_path(mbox_type)

        if args and args[-1] == 'flat':
            flat = True
            args.pop(-1)
        else:
            flat = False

        if os.path.exists(path):
            return self._error('Already exists: %s' % path)

        msg_idxs = list(self._choose_messages(args))
        if not msg_idxs:
            session.ui.warning('No messages selected')
            return False

        # Exporting messages without their threads barely makes any
        # sense.
        if not flat:
            for i in reversed(range(0, len(msg_idxs))):
                mi = msg_idxs[i]
                msg_idxs[i:i+1] = [int(m[idx.MSG_MID], 36)
                                   for m in idx.get_conversation(msg_idx=mi)]

        # Let's always export in the same order. Stability is nice.
        msg_idxs.sort()

        mbox = self.create_mailbox(mbox_type, path)
        exported = {}
        while msg_idxs:
            msg_idx = msg_idxs.pop(0)
            if msg_idx not in exported:
                e = Email(idx, msg_idx)
                session.ui.mark('Exporting =%s ...' % e.msg_mid())
                mbox.add(e.get_msg())
                exported[msg_idx] = 1

        mbox.flush()

        return self._success(
            _('Exported %d messages to %s') % (len(exported), path),
            {
                'exported': len(exported),
                'created': path
            })

_plugins.register_commands(ExportMail)

########NEW FILE########
__FILENAME__ = groups
from gettext import gettext as _

from mailpile.plugins import PluginManager
from mailpile.commands import Command

from mailpile.plugins.tags import AddTag, DeleteTag, Filter
from mailpile.plugins.contacts import *


_plugins = PluginManager(builtin=__file__)


##[ Search terms ]############################################################

def search(config, idx, term, hits):
    group = config._vcards.get(term.split(':', 1)[1])
    rt, emails = [], []
    if group and group.kind == 'group':
        for email, attrs in group.get('EMAIL', []):
            group = config._vcards.get(email.lower(), None)
            if group:
                emails.extend([e[0].lower() for e in group.get('EMAIL', [])])
            else:
                emails.append(email.lower())
    fromto = term.startswith('group:') and 'from' or 'to'
    for email in set(emails):
        rt.extend(hits('%s:%s' % (email, fromto)))
    return rt

_plugins.register_search_term('group', search)
_plugins.register_search_term('togroup', search)


##[ Commands ]################################################################

def GroupVCard(parent):
    """A factory for generating group commands"""

    class GroupVCardCommand(parent):
        SYNOPSIS = tuple([(t and t.replace('vcard', 'group') or t)
                          for t in parent.SYNOPSIS])
        KIND = 'group'
        ORDER = ('Tagging', 4)

        def _valid_vcard_handle(self, vc_handle):
            # If there is already a tag by this name, complain.
            return (vc_handle and
                   ('-' != vc_handle[0]) and
                   ('@' not in vc_handle) and
                   (not self.session.config.get_tag_id(vc_handle)))

        def _prepare_new_vcard(self, vcard):
            session, handle = self.session, vcard.nickname
            return (AddTag(session, arg=[handle]).run() and
                    Filter(session, arg=['add', 'group:%s' % handle,
                                         '+%s' % handle, vcard.fn]).run())

        def _add_from_messages(self):
            raise ValueError('Invalid group ids: %s' % self.args)

        def _pre_delete_vcard(self, vcard):
            session, handle = self.session, vcard.nickname
            return (Filter(session, arg=['delete',
                                         'group:%s' % handle]).run() and
                    DeleteTag(session, arg=[handle]).run())

    return GroupVCardCommand


class Group(GroupVCard(VCard)):
    """View groups"""


class AddGroup(GroupVCard(AddVCard)):
    """Add groups"""


class GroupAddLines(GroupVCard(VCardAddLines)):
    """Add lines to a group VCard"""


class RemoveGroup(GroupVCard(RemoveVCard)):
    """Remove groups"""


class ListGroups(GroupVCard(ListVCards)):
    """Find groups"""


_plugins.register_commands(Group, AddGroup, GroupAddLines,
                           RemoveGroup, ListGroups)

########NEW FILE########
__FILENAME__ = html_magic
# This plugin generates Javascript, HTML or CSS fragments based on the
# current theme, skin and active plugins.
#
from gettext import gettext as _

import mailpile.config
from mailpile.plugins import PluginManager
from mailpile.commands import Command
from mailpile.urlmap import UrlMap
from mailpile.util import *


_plugins = PluginManager(builtin=__file__)


##[ Configuration ]###########################################################

#mailpile.plugins.register_config_section('tags', ["Tags", {
#    'name': ['Tag name', 'str', ''],
#}, {}])
#
#mailpile.plugins.register_config_variables('sys', {
#    'writable_tags': ['DEPRECATED', 'str', []],
#})


##[ Commands ]################################################################


class JsApi(Command):
    """Output API bindings, plugin code and CSS as CSS or Javascript"""
    SYNOPSIS = (None, None, 'jsapi', None)
    ORDER = ('Internals', 0)
    HTTP_CALLABLE = ('GET', )

    def command(self, save=True, auto=False):
        session, config = self.session, self.session.config

        urlmap = UrlMap(session)
        res = {
            'api_methods': [],
            'javascript_classes': [],
            'css_files': []
        }

        for method in ('GET', 'POST', 'UPDATE', 'DELETE'):
            for cmd in urlmap._api_commands(method, strict=True):
                cmdinfo = {
                    "url": cmd.SYNOPSIS[2],
                    "method": method
                }
                if hasattr(cmd, 'HTTP_QUERY_VARS'):
                    cmdinfo["query_vars"] = cmd.HTTP_QUERY_VARS
                if hasattr(cmd, 'HTTP_POST_VARS'):
                    cmdinfo["post_vars"] = cmd.HTTP_POST_VARS
                if hasattr(cmd, 'HTTP_OPTIONAL_VARS'):
                    cmdinfo["optional_vars"] = cmd.OPTIONAL_VARS
                res['api_methods'].append(cmdinfo)

        created_js = []
        for cls, filename in sorted(list(
                config.plugins.get_js_classes().iteritems())):
            try:
                parts = cls.split('.')[:-1]
                for i in range(1, len(parts)):
                    parent = '.'.join(parts[:i+1])
                    if parent not in created_js:
                        res['javascript_classes'].append({
                            'classname': parent,
                            'code': ''
                        })
                        created_js.append(parent)
                with open(filename, 'rb') as fd:
                    res['javascript_classes'].append({
                        'classname': cls,
                        'code': fd.read().decode('utf-8')
                    })
                    created_js.append(cls)
            except (OSError, IOError, UnicodeDecodeError):
                self._ignore_exception()

        for cls, filename in sorted(list(
                config.plugins.get_css_files().iteritems())):
            try:
                with open(filename, 'rb') as fd:
                    res['css_files'].append({
                        'classname': cls,
                        'css': fd.read().decode('utf-8')
                    })
            except (OSError, IOError, UnicodeDecodeError):
                self._ignore_exception()

        return self._success(_('Generated Javascript API'), result=res)


_plugins.register_commands(JsApi)

########NEW FILE########
__FILENAME__ = migrate
from gettext import gettext as _

import mailpile.config
from mailpile.plugins import PluginManager
from mailpile.commands import Command
from mailpile.util import *
from mailpile.mail_source.mbox import MboxMailSource
from mailpile.mail_source.maildir import MaildirMailSource


_plugins = PluginManager(builtin=__file__)

# We might want to do this differently at some point, but
# for now it's fine.


def migrate_routes(session):
    # Migration from route string to messageroute structure
    def route_parse(route):
        if route.startswith('|'):
            command = route[1:].strip()
            return {
                "name": command.split()[0],
                "protocol": "local",
                "command": command
            }
        else:
            res = re.split(
                "([\w]+)://([^:]+):([^@]+)@([\w\d.]+):([\d]+)[/]{0,1}", route)
            if len(res) >= 5:
                return {
                    "name": _("%(user)s on %(host)s"
                              ) % {"user": res[2], "host": res[4]},
                    "protocol": res[1],
                    "username": res[2],
                    "password": res[3],
                    "host": res[4],
                    "port": res[5]
                }
            else:
                session.ui.warning(_('Could not migrate route: %s') % route)
        return None

    def make_route_name(route_dict):
        # This will always return the same hash, no matter how Python
        # decides to order the dict internally.
        return md5_hex(str(sorted(list(route_dict.iteritems()))))[:8]

    if session.config.prefs.get('default_route'):
        route_dict = route_parse(session.config.prefs.default_route)
        if route_dict:
            route_name = make_route_name(route_dict)
            session.config.routes[route_name] = route_dict
            session.config.prefs.default_messageroute = route_name

    for profile in session.config.profiles:
        if profile.get('route'):
            route_dict = route_parse(profile.route)
            if route_dict:
                route_name = make_route_name(route_dict)
                session.config.routes[route_name] = route_dict
                profile.messageroute = route_name

    return True


def migrate_mailboxes(session):
    config = session.config

    def _common_path(paths):
        common_head, junk = os.path.split(paths[0])
        for path in paths:
            head, junk = os.path.split(path)
            while (common_head and common_head != '/' and
                   head and head != '/' and
                   head != common_head):
                # First we try shortening the target path...
                while head and head != '/' and head != common_head:
                    head, junk = os.path.split(head)
                # If that failed, lop one off the common path and try again
                if head != common_head:
                    common_head, junk = os.path.split(common_head)
                    head, junk = os.path.split(path)
        return common_head

    mboxes = []
    maildirs = []
    macmaildirs = []
    thunderbird = []

    spam_tids = [tag._key for tag in config.get_tags(type='spam')]
    trash_tids = [tag._key for tag in config.get_tags(type='trash')]
    inbox_tids = [tag._key for tag in config.get_tags(type='inbox')]

    # Iterate through config.sys.mailbox, sort mailboxes by type
    for mbx_id, path, src in config.get_mailboxes():
        if path == '/dev/null' or src is not None:
            continue
        elif os.path.exists(os.path.join(path, 'Info.plist')):
            macmaildirs.append((mbx_id, path))
        elif os.path.isdir(path):
            maildirs.append((mbx_id, path))
        elif 'thunderbird' in path.lower():
            thunderbird.append((mbx_id, path))
        else:
            mboxes.append((mbx_id, path))

    # macmail: library/mail/v2

    if thunderbird:
        # Create basic mail source...
        if 'tbird' not in config.sources:
            config.sources['tbird'] = {
                'name': 'Thunderbird',
                'protocol': 'mbox',
            }
            config.sources.tbird.discovery.create_tag = True

        config.sources.tbird.discovery.policy = 'read'
        config.sources.tbird.discovery.process_new = True
        tbird_src = MboxMailSource(session, config.sources.tbird)

        # Configure discovery policy?
        root = _common_path([path for mbx_id, path in thunderbird])
        if 'thunderbird' in root.lower():
            # FIXME: This is wrong, we should create a mailbox entry
            #        with the policy 'watch'.
            tbird_src.my_config.discovery.path = root

        # Take over all the mailboxes
        for mbx_id, path in thunderbird:
            mbx = tbird_src.take_over_mailbox(mbx_id)
            if 'inbox' in path.lower():
                mbx.apply_tags.extend(inbox_tids)
            elif 'spam' in path.lower() or 'junk' in path.lower():
                mbx.apply_tags.extend(spam_tids)
            elif 'trash' in path.lower():
                mbx.apply_tags.extend(trash_tids)

        tbird_src.my_config.discovery.policy = 'unknown'

    for name, mailboxes, proto, description, cls in (
        ('mboxes', mboxes, 'mbox', 'Unix mbox files', MboxMailSource),
        ('maildirs', maildirs, 'maildir', 'Maildirs', MaildirMailSource),
    ):
        if mailboxes:
            # Create basic mail source...
            if name not in config.sources:
                config.sources[name] = {
                    'name': description,
                    'protocol': proto
                }
                config.sources[name].discovery.create_tag = False
            config.sources[name].discovery.policy = 'read'
            config.sources[name].discovery.process_new = True
            config.sources[name].discovery.apply_tags = inbox_tids[:]
            src = cls(session, config.sources[name])
            for mbx_id, path in mailboxes:
                mbx = src.take_over_mailbox(mbx_id)
            config.sources[name].discovery.policy = 'unknown'

    return True


def migrate_cleanup(session):
    config = session.config

    autotaggers = [t for t in config.prefs.autotag.values() if t.tagger]
    config.prefs.autotag = autotaggers

    return True


MIGRATIONS_BEFORE_SETUP = [migrate_routes]
MIGRATIONS_AFTER_SETUP = [migrate_cleanup]
MIGRATIONS = {
    'routes': migrate_routes,
    'sources': migrate_mailboxes,
    'cleanup': migrate_cleanup
}


class Migrate(Command):
    """Perform any needed migrations"""
    SYNOPSIS = (None, 'setup/migrate', None, None)
    ORDER = ('Internals', 0)

    def command(self, before_setup=True, after_setup=True):
        session = self.session
        err = cnt = 0

        migrations = []
        for a in self.args:
            if a in MIGRATIONS:
                migrations.append(MIGRATIONS[a])
            else:
                raise UsageError(_('Unknown migration: %s (available: %s)'
                                   ) % (a, ', '.join(MIGRATIONS.keys())))

        if not migrations:
            migrations = ((before_setup and MIGRATIONS_BEFORE_SETUP or []) +
                          (after_setup and MIGRATIONS_AFTER_SETUP or []))

        for mig in migrations:
            try:
                if mig(session):
                    cnt += 1
                else:
                    err += 1
            except:
                self._ignore_exception()
                err += 1

        if cnt:
            session.config.save()
        return self._success(_('Performed %d migrations, failed %d.'
                               ) % (cnt, err))


_plugins.register_commands(Migrate)

########NEW FILE########
__FILENAME__ = plugins
import os
from gettext import gettext as _

import mailpile.commands
from mailpile.plugins import PluginManager


_plugins = PluginManager(builtin=__file__)


class Plugins(mailpile.commands.Command):
    """List the currently available plugins."""
    SYNOPSIS = (None, 'plugins', 'plugins', '[<plugins>]')
    ORDER = ('Config', 9)

    def command(self):
        pm = self.session.config.plugins
        wanted = self.args

        info = dict((d, {
            'loaded': d in pm.LOADED,
            'builtin': d not in pm.DISCOVERED
        }) for d in pm.available() if (not wanted or d in wanted))

        for plugin in info:
            if plugin in pm.DISCOVERED:
                info[plugin]['manifest'] = pm.DISCOVERED[plugin][1]

        return self._success(_('Listed available plugins'), info)


class LoadPlugin(mailpile.commands.Command):
    """Load and enable a given plugin."""
    SYNOPSIS = (None, 'plugins/load', 'plugins/load', '<plugin>')
    ORDER = ('Config', 9)

    def command(self):
        config = self.session.config
        plugins = config.plugins
        for plugin in self.args:
            if plugin in plugins.LOADED:
                return self._error(_('Already loaded: %s') % plugin,
                                   info={'loaded': plugin})

        for plugin in self.args:
            try:
                # FIXME: This fails to update the ConfigManger
                plugins.load(plugin, process_manifest=True, config=config)
                config.sys.plugins.append(plugin)
            except Exception, e:
                self._ignore_exception()
                return self._error(_('Failed to load plugin: %s') % plugin,
                                   info={'failed': plugin})

        self._serialize('Save config', lambda: config.save())
        return self._success(_('Loaded plugins: %s') % ', '.join(self.args),
                             {'loaded': self.args})


class DisablePlugin(mailpile.commands.Command):
    """Disable a plugin."""
    SYNOPSIS = (None, 'plugins/disable', 'plugins/disable', '<plugin>')
    ORDER = ('Config', 9)

    def command(self):
        config = self.session.config
        plugins = config.plugins
        for plugin in self.args:
            if plugin in plugins.REQUIRED:
                return self._error(_('Required plugins can not be disabled: %s'
                                     ) % plugin)
            if plugin not in config.sys.plugins:
                return self._error(_('Plugin not loaded: %s') % plugin)

        for plugin in self.args:
            while plugin in config.sys.plugins:
                config.sys.plugins.remove(plugin)

        self._serialize('Save config', lambda: config.save())
        return self._success(_('Disabled plugins: %s (restart required)'
                               ) % ', '.join(self.args),
                             {'disabled': self.args})


_plugins.register_commands(Plugins, LoadPlugin, DisablePlugin)

########NEW FILE########
__FILENAME__ = search
import datetime
import re
import time
from gettext import gettext as _

from mailpile.commands import Command, SearchResults
from mailpile.mailutils import Email, MBX_ID_LEN
from mailpile.mailutils import ExtractEmails, ExtractEmailAndName
from mailpile.plugins import PluginManager
from mailpile.search import MailIndex
from mailpile.urlmap import UrlMap
from mailpile.util import *
from mailpile.ui import SuppressHtmlOutput


_plugins = PluginManager(builtin=__file__)


##[ Commands ]################################################################

class Search(Command):
    """Search your mail!"""
    SYNOPSIS = ('s', 'search', 'search', '[@<start>] <terms>')
    ORDER = ('Searching', 0)
    HTTP_CALLABLE = ('GET', )
    HTTP_QUERY_VARS = {
        'q': 'search terms',
        'qr': 'search refinements',
        'order': 'sort order',
        'start': 'start position',
        'end': 'end position',
        'full': 'return all metadata'
    }

    class CommandResult(Command.CommandResult):
        def __init__(self, *args, **kwargs):
            Command.CommandResult.__init__(self, *args, **kwargs)
            self.fixed_up = False
            if isinstance(self.result, dict):
                self.message = self.result.get('summary', '')
            elif isinstance(self.result, list):
                self.message = ', '.join([r.get('summary', '')
                                          for r in self.result])

        def _fixup(self):
            if self.fixed_up:
                return self
            self.fixed_up = True
            return self

        def as_text(self):
            if self.result:
                if isinstance(self.result, (list, set)):
                    return '\n'.join([r.as_text() for r in self.result])
                else:
                    return self.result.as_text()
            else:
                return _('No results')

        def as_html(self, *args, **kwargs):
            return Command.CommandResult.as_html(self._fixup(),
                                                 *args, **kwargs)

        def as_dict(self, *args, **kwargs):
            return Command.CommandResult.as_dict(self._fixup(),
                                                 *args, **kwargs)

    def state_as_query_args(self):
        try:
            return self._search_state
        except (AttributeError, NameError):
            return Command.state_as_query_args(self)

    def _do_search(self, search=None):
        session, idx = self.session, self._idx()
        session.searched = search or []
        args = list(self.args)

        for q in self.data.get('q', []):
            args.extend(q.split())

        # Query refinements...
        qrs = []
        for qr in self.data.get('qr', []):
            qrs.extend(qr.split())
        args.extend(qrs)

        for order in self.data.get('order', []):
            session.order = order

        num = session.config.prefs.num_results
        d_start = int(self.data.get('start', [0])[0])
        d_end = int(self.data.get('end', [0])[0])
        if d_start and d_end:
            args[:0] = ['@%s' % d_start]
            num = d_end - d_start + 1
        elif d_start:
            args[:0] = ['@%s' % d_start]
        elif d_end:
            args[:0] = ['@%s' % (d_end - num + 1)]

        if args and args[0].startswith('@'):
            spoint = args.pop(0)[1:]
            try:
                start = int(spoint) - 1
            except ValueError:
                raise UsageError(_('Weird starting point: %s') % spoint)
        else:
            start = 0

        # FIXME: Is this dumb?
        for arg in args:
            if ':' in arg or (arg and arg[0] in ('-', '+')):
                session.searched.append(arg.lower())
            else:
                session.searched.extend(re.findall(WORD_REGEXP, arg.lower()))

        session.order = session.order or session.config.prefs.default_order
        session.results = list(idx.search(session, session.searched).as_set())
        idx.sort_results(session, session.results, session.order)

        self._search_state = {
            'q': [a for a in args if not (a.startswith('@') or a in qrs)],
            'qr': qrs,
            'start': [a for a in args if a.startswith('@')],
            'order': [session.order]
        }
        return session, idx, start, num

    def command(self, search=None):
        session, idx, start, num = self._do_search(search=search)
        full_threads = self.data.get('full', False)
        session.displayed = SearchResults(session, idx,
                                          start=start, num=num,
                                          full_threads=full_threads)
        session.ui.mark(_('Prepared %d search results') % len(session.results))
        return self._success(_('Found %d results in %.3fs'
                               ) % (len(session.results),
                                    session.ui.report_marks(quiet=True)),
                             result=session.displayed)


class Next(Search):
    """Display next page of results"""
    SYNOPSIS = ('n', 'next', None, None)
    ORDER = ('Searching', 1)
    HTTP_CALLABLE = ()

    def command(self):
        session = self.session
        try:
            session.displayed = session.displayed.next_set()
        except AttributeError:
            session.ui.error(_("You must perform a search before "
                               "requesting the next page."))
            return False
        return self._success(_('Displayed next page of results.'),
                             result=session.displayed)


class Previous(Search):
    """Display previous page of results"""
    SYNOPSIS = ('p', 'previous', None, None)
    ORDER = ('Searching', 2)
    HTTP_CALLABLE = ()

    def command(self):
        session = self.session
        try:
            session.displayed = session.displayed.previous_set()
        except AttributeError:
            session.ui.error(_("You must perform a search before "
                               "requesting the previous page."))
            return False
        return self._success(_('Displayed previous page of results.'),
                             result=session.displayed)


class Order(Search):
    """Sort by: date, from, subject, random or index"""
    SYNOPSIS = ('o', 'order', None, '<how>')
    ORDER = ('Searching', 3)
    HTTP_CALLABLE = ()

    def command(self):
        session, idx = self.session, self._idx()
        session.order = self.args and self.args[0] or None
        idx.sort_results(session, session.results, session.order)
        session.displayed = SearchResults(session, idx)
        return self._success(_('Changed sort order to %s') % session.order,
                             result=session.displayed)


class View(Search):
    """View one or more messages"""
    SYNOPSIS = ('v', 'view', 'message', '[raw] <message>')
    ORDER = ('Searching', 4)
    HTTP_QUERY_VARS = {
        'mid': 'metadata-ID'
    }

    class RawResult(dict):
        def _decode(self):
            try:
                return self['source'].decode('utf-8')
            except UnicodeDecodeError:
                try:
                    return self['source'].decode('iso-8859-1')
                except:
                    return '(MAILPILE FAILED TO DECODE MESSAGE)'

        def as_text(self, *args, **kwargs):
            return self._decode()

        def as_html(self, *args, **kwargs):
            return '<pre>%s</pre>' % escape_html(self._decode())

    def _side_effects(self, emails):
        session, config, idx = self.session, self.session.config, self._idx()
        msg_idxs = [e.msg_idx_pos for e in emails]
        if 'tags' in config:
            for tag in config.get_tags(type='unread'):
                idx.remove_tag(session, tag._key, msg_idxs=msg_idxs)
            for tag in config.get_tags(type='read'):
                idx.add_tag(session, tag._key, msg_idxs=msg_idxs)

        idx.apply_filters(session, '@read',
                          msg_idxs=[e.msg_idx_pos for e in emails])
        return None

    def state_as_query_args(self):
        return Command.state_as_query_args(self)

    def command(self):
        session, config, idx = self.session, self.session.config, self._idx()
        results = []
        args = list(self.args)
        if args and args[0].lower() == 'raw':
            raw = args.pop(0)
        else:
            raw = False
        emails = [Email(idx, mid) for mid in self._choose_messages(args)]

        rv = self._side_effects(emails)
        if rv is not None:
            # This is here so derived classes can do funky things.
            return rv

        for email in emails:
            if raw:
                subject = email.get_msg_info(idx.MSG_SUBJECT)
                results.append(self.RawResult({
                    'summary': _('Raw message: %s') % subject,
                    'source': email.get_file().read()
                }))
            else:
                old_result = None
                for result in results:
                    if email.msg_idx_pos in result.results:
                        old_result = result
                if old_result:
                    old_result.add_email(email)
                    continue

                conv = [int(c[0], 36) for c
                        in idx.get_conversation(msg_idx=email.msg_idx_pos)]
                if email.msg_idx_pos not in conv:
                    conv.append(email.msg_idx_pos)

                # FIXME: This is a hack. The indexer should just keep things
                #        in the right order on rescan. Fixing threading is a
                #        bigger problem though, so we do this for now.
                def sort_conv_key(msg_idx_pos):
                    info = idx.get_msg_at_idx_pos(msg_idx_pos)
                    return -int(info[idx.MSG_DATE], 36)
                conv.sort(key=sort_conv_key)

                session.results = conv
                results.append(SearchResults(session, idx, emails=[email]))
        if len(results) == 1:
            return self._success(_('Displayed a single message'),
                                 result=results[0])
        else:
            session.results = []
            return self._success(_('Displayed %d messages') % len(results),
                                 result=results)


class Extract(Command):
    """Extract attachment(s) to file(s)"""
    SYNOPSIS = ('e', 'extract', 'message/download', '<msgs> <att> [><fn>]')
    ORDER = ('Searching', 5)
    RAISES = (SuppressHtmlOutput, UrlRedirectException)

    class CommandResult(Command.CommandResult):
        def __init__(self, *args, **kwargs):
            self.fixed_up = False
            return Command.CommandResult.__init__(self, *args, **kwargs)

        def _fixup(self):
            if self.fixed_up:
                return self
            for result in (self.result or []):
                if 'data' in result:
                    result['data'] = result['data'].encode('base64'
                                                           ).replace('\n', '')
            self.fixed_up = True
            return self

        def as_html(self, *args, **kwargs):
            return Command.CommandResult.as_html(self._fixup(),
                                                 *args, **kwargs)

        def as_dict(self, *args, **kwargs):
            return Command.CommandResult.as_dict(self._fixup(),
                                                 *args, **kwargs)

    def command(self):
        session, config, idx = self.session, self.session.config, self._idx()
        mode = 'download'
        name_fmt = None

        args = list(self.args)
        if args[0] in ('inline', 'inline-preview', 'preview', 'download'):
            mode = args.pop(0)

        if len(args) > 0 and args[-1].startswith('>'):
            name_fmt = args.pop(-1)[1:]

        if (args[0].startswith('#') or
                args[0].startswith('part:') or
                args[0].startswith('ext:')):
            cid = args.pop(0)
        else:
            cid = args.pop(-1)

        eids = self._choose_messages(args)
        emails = [Email(idx, i) for i in eids]

        print 'Download %s from %s as %s/%s' % (cid, eids, mode, name_fmt)

        results = []
        for e in emails:
            if cid[0] == '*':
                tree = e.get_message_tree(want=['attachments'])
                cids = [('#%s' % a['count']) for a in tree['attachments']
                        if a['filename'].lower().endswith(cid[1:].lower())]
            else:
                cids = [cid]

            for c in cids:
                fn, info = e.extract_attachment(session, c,
                                                name_fmt=name_fmt, mode=mode)
                if info:
                    info['idx'] = e.msg_idx_pos
                    if fn:
                        info['created_file'] = fn
                    results.append(info)
        return results


_plugins.register_commands(Extract, Next, Order, Previous, Search, View)


##[ Search terms ]############################################################

def mailbox_search(config, idx, term, hits):
    word = term.split(':', 1)[1].lower()
    try:
        mbox_id = (('0' * MBX_ID_LEN) + b36(int(word, 36)))[-MBX_ID_LEN:]
    except ValueError:
        mbox_id = None

    mailboxes = [m for m in config.sys.mailbox.keys()
                 if (mbox_id == m) or word in config.sys.mailbox[m].lower()]
    rt = []
    for mbox_id in mailboxes:
        mbox_id = (('0' * MBX_ID_LEN) + mbox_id)[-MBX_ID_LEN:]
        rt.extend(hits('%s:mailbox' % mbox_id))
    return rt


_plugins.register_search_term('mailbox', mailbox_search)

########NEW FILE########
__FILENAME__ = sizes
import math
import time
import datetime
from gettext import gettext as _

from mailpile.plugins import PluginManager


_plugins = PluginManager(builtin=__file__)


##[ Keywords ]################################################################

def meta_kw_extractor(index, msg_mid, msg, msg_size, msg_ts):
    """Create a search term with the floored log2 size of the message."""
    if msg_size <= 0:
        return []
    return ['%s:ln2sz' % int(math.log(msg_size, 2))]

_plugins.register_meta_kw_extractor('sizes', meta_kw_extractor)


##[ Search terms ]############################################################


_size_units = {
    't': 40,
    'g': 30,
    'm': 20,
    'k': 10,
    'b': 0
}
_range_keywords = [
    '..',
    '-'
]


def _mk_logsize(size, default_unit=0):
    if not size:
        return 0
    unit = 0
    size = size.lower()
    if size[-1].isdigit():  # ends with a number
        unit = default_unit
    elif len(size) >= 2 and size[-2] in _size_units and size[-1] == 'b':
        unit = _size_units[size[-2]]
        size = size[:-2]
    elif size[-1] in _size_units:
        unit = _size_units[size[-1]]
        size = size[:-1]
    try:
        return int(math.log(float(size), 2) + unit)
    except ValueError:
        return 1 + unit


def search(config, idx, term, hits):
    try:
        word = term.split(':', 1)[1].lower()

        for range_keyword in _range_keywords:
            if range_keyword in term:
                start, end = word.split(range_keyword)
                break
        else:
            start = end = word

        # if no unit is setup in the start term, use the unit from the end term
        end_unit_size = end.lower()[-1]
        end_unit = 0
        if end_unit_size in _size_units:
            end_unit = _size_units[end_unit_size]

        start = _mk_logsize(start, end_unit)
        end = _mk_logsize(end)
        terms = ['%s:ln2sz' % sz for sz in range(start, end+1)]

        rt = []
        for t in terms:
            rt.extend(hits(t))
        return rt
    except:
        raise ValueError('Invalid size: %s' % term)


_plugins.register_search_term('size', search)

########NEW FILE########
__FILENAME__ = smtp_server
import asyncore
import email.parser
import smtpd
import threading
import traceback
from gettext import gettext as _

import mailpile.config
from mailpile.plugins import PluginManager
from mailpile.commands import Command
from mailpile.mailutils import Email
from mailpile.util import *


_plugins = PluginManager(builtin=__file__)


##[ Configuration ]##########################################################

_plugins.register_config_section(
    'sys', 'smtpd', [_('SMTP Daemon'), False, {
        'host': (_('Listening host for SMTP daemon'), 'hostname', 'localhost'),
        'port': (_('Listening port for SMTP daemon'), int, 0),
    }])


class SMTPChannel(smtpd.SMTPChannel):
    def __init__(self, session, *args, **kwargs):
        smtpd.SMTPChannel.__init__(self, *args, **kwargs)
        self.session = session
        # Lie lie lie lie...
        self.__fqdn = 'cs.utah.edu'

    def push(self, msg):
        if msg.startswith('220'):
            # This is a hack, because these days it is no longer considered
            # reasonable to tell everyone your hostname and version number.
            # Lie lie lie lie! ... https://snowplow.org/tom/worm/worm.html
            smtpd.SMTPChannel.push(self, ('220 cs.utah.edu SMTP '
                                          'Sendmail 5.67; '
                                          'Wed, 2 Nov 1988 20:49'))
        else:
            smtpd.SMTPChannel.push(self, msg)

    # FIXME: We need to override MAIL and RCPT, so we can abort early if
    #        addresses are invalid. We may also want to implement a type of
    #        hashcash in the SMTP dialog.

    # FIXME: We need to put bounds on things so people cannot feed us mail
    #        of unreasonable size and asplode our RAM.


class SMTPServer(smtpd.SMTPServer):
    def __init__(self, session, localaddr):
        self.session = session
        smtpd.SMTPServer.__init__(self, localaddr, None)

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            conn, addr = pair
            channel = SMTPChannel(self.session, self, conn, addr)

    def process_message(self, peer, mailfrom, rcpttos, data):
        # We can assume that the mailfrom and rcpttos have checked out
        # and this message is indeed intended for us. Spool it to disk
        # and add to the index!
        session, config = self.session, self.session.config
        blank_tid = config.get_tags(type='blank')[0]._key
        idx = config.index
        try:
            message = email.parser.Parser().parsestr(data)
            lid, lmbox = config.open_local_mailbox(session)
            e = Email.Create(idx, lid, lmbox, ephemeral_mid=False)
            idx.add_tag(session, blank_tid, msg_idxs=[e.msg_idx_pos],
                        conversation=False)
            e.update_from_msg(session, message)
            idx.remove_tag(session, blank_tid, msg_idxs=[e.msg_idx_pos],
                           conversation=False)
            return None
        except:
            traceback.print_exc()
            return '400 Oops wtf'


class SMTPWorker(threading.Thread):
    def __init__(self, session):
        self.session = session
        self.quitting = False
        threading.Thread.__init__(self)

    def run(self):
        cfg = self.session.config.sys.smtpd
        if cfg.host and cfg.port:
            server = SMTPServer(self.session, (cfg.host, cfg.port))
            while not self.quitting:
                asyncore.poll(timeout=1.0)
            asyncore.close_all()

    def quit(self, join=True):
        self.quitting = True
        if join:
            try:
                self.join()
            except RuntimeError:
                pass


_plugins.register_worker(SMTPWorker)

########NEW FILE########
__FILENAME__ = source_imap
# This is the IMAP mail source

from mailpile.mail_source import MailSource


class IMAPMailSource(MailSource):
    pass

########NEW FILE########
__FILENAME__ = tags
from gettext import gettext as _

import mailpile.config
from mailpile.commands import Command
from mailpile.plugins import PluginManager
from mailpile.urlmap import UrlMap
from mailpile.util import *

from mailpile.plugins.search import Search


_plugins = PluginManager(builtin=__file__)


##[ Configuration ]###########################################################


FILTER_TYPES = ('user',      # These are the default, user-created filters
                'incoming',  # These filters are only applied to new messages
                'system',    # Mailpile core internal filters
                'plugin')    # Filters created by plugins

_plugins.register_config_section('tags', ["Tags", {
    'name': ['Tag name', 'str', ''],
    'slug': ['URL slug', 'slashslug', ''],

    # Functional attributes
    'type': ['Tag type', [
        'tag', 'group', 'attribute', 'unread', 'inbox',
        # Maybe TODO: 'folder', 'shadow',
        'drafts', 'blank', 'outbox', 'sent',          # composing and sending
        'replied', 'fwded', 'tagged', 'read', 'ham',  # behavior tracking tags
        'trash', 'spam'                               # junk mail tags
    ], 'tag'],
    'flag_hides': ['Hide tagged messages from searches?', 'bool', False],
    'flag_editable': ['Mark tagged messages as editable?', 'bool', False],

    # Tag display attributes for /in/tag or searching in:tag
    'template': ['Default tag display template', 'str', 'index'],
    'search_terms': ['Terms to search for on /in/tag/', 'str', 'in:%(slug)s'],
    'search_order': ['Default search order for /in/tag/', 'str', ''],
    'magic_terms': ['Extra terms to search for', 'str', ''],

    # Tag display attributes for search results/lists/UI placement
    'icon': ['URL to default tag icon', 'url', 'icon-tag'],
    'label': ['Display as label in results', 'bool', True],
    'label_color': ['Color to use in label', 'str', '#4D4D4D'],
    'display': ['Display context in UI', ['priority', 'tag', 'subtag',
                                          'archive', 'invisible'], 'tag'],
    'display_order': ['Order in lists', 'float', 0],
    'parent': ['ID of parent tag, if any', 'str', ''],

    # Outdated crap
    'hides_flag': ['DEPRECATED', 'ignore', None],
    'write_flag': ['DEPRECATED', 'ignore', None],
}, {}])

_plugins.register_config_section('filters', ["Filters", {
    'tags': ['Tag/untag actions', 'str', ''],
    'terms': ['Search terms', 'str', ''],
    'comment': ['Human readable description', 'str', ''],
    'type': ['Filter type', FILTER_TYPES, FILTER_TYPES[0]],
}, {}])

_plugins.register_config_variables('sys', {
    'writable_tags': ['DEPRECATED', 'str', []],
    'invisible_tags': ['DEPRECATED', 'str', []],
})

#INFO_HIDES_TAG_METADATA = ('flag_editable', 'flag_hides')


def GetFilters(cfg, filter_on=None, types=FILTER_TYPES[:1]):
    filters = cfg.filters.keys()
    filters.sort(key=lambda k: int(k, 36))
    flist = []
    tset = set(types)
    for fid in filters:
        terms = cfg.filters[fid].get('terms', '')
        ftype = cfg.filters[fid]['type']
        if not (set([ftype, 'any', 'all', None]) & tset):
            continue
        if filter_on is not None and terms != filter_on:
            continue
        flist.append((fid, terms,
                      cfg.filters[fid].get('tags', ''),
                      cfg.filters[fid].get('comment', ''),
                      ftype))
    return flist


def MoveFilter(cfg, filter_id, filter_new_id):
    def swap(f1, f2):
        tmp = cfg.filters[f1]
        cfg.filters[f1] = cfg.filters[f2]
        cfg.filters[f2] = tmp
    ffrm = int(filter_id, 36)
    fto = int(filter_new_id, 36)
    if ffrm > fto:
        for fid in reversed(range(fto, ffrm)):
            swap(b36(fid + 1), b36(fid))
    elif ffrm < fto:
        for fid in range(ffrm, fto):
            swap(b36(fid), b36(fid + 1))


def GetTags(cfg, tn=None, default=None, **kwargs):
    results = []
    if tn is not None:
        # Hack, allow the tn= to be any of: TID, name or slug.
        tn = tn.lower()
        try:
            if tn in cfg.tags:
                results.append([cfg.tags[tn]._key])
        except (KeyError, IndexError, AttributeError):
            pass
        if not results:
            tv = cfg.tags.values()
            tags = ([t._key for t in tv if t.slug.lower() == tn] or
                    [t._key for t in tv if t.name.lower() == tn])
            results.append(tags)

    if kwargs:
        tv = cfg.tags.values()
        for kw in kwargs:
            want = unicode(kwargs[kw]).lower()
            results.append([t._key for t in tv
                            if (want == '*' or
                                unicode(t[kw]).lower() == want)])

    if (tn or kwargs) and not results:
        return default
    else:
        tags = set(cfg.tags.keys())
        for r in results:
            tags &= set(r)
        tags = [cfg.tags[t] for t in tags]
        if 'display' in kwargs:
            tags.sort(key=lambda k: (k.get('display_order', 0), k.slug))
        else:
            tags.sort(key=lambda k: k.slug)
        return tags


def GetTag(cfg, tn, default=None):
    return (GetTags(cfg, tn, default=None) or [default])[0]


def GetTagID(cfg, tn):
    tags = GetTags(cfg, tn=tn, default=[None])
    return tags and (len(tags) == 1) and tags[0]._key or None


def GetTagInfo(cfg, tn, stats=False, unread=None, exclude=None, subtags=None):
    tag = GetTag(cfg, tn)
    tid = tag._key
    info = {
        'tid': tid,
        'url': UrlMap(config=cfg).url_tag(tid),
    }
    for k in tag.all_keys():
#       if k not in INFO_HIDES_TAG_METADATA:
            info[k] = tag[k]
    if subtags:
        info['subtag_ids'] = [t._key for t in subtags]
    exclude = exclude or set()
    if stats and (unread is not None):
        messages = (cfg.index.TAGS.get(tid, set()) - exclude)
        stats_all = len(messages)
        info['stats'] = {
            'all': stats_all,
            'new': len(messages & unread),
            'not': len(cfg.index.INDEX) - stats_all
        }
        if subtags:
            for subtag in subtags:
                messages |= cfg.index.TAGS.get(subtag._key, set())
            info['stats'].update({
                'sum_all': len(messages),
                'sum_new': len(messages & unread),
            })

    return info


# FIXME: Is this bad form or awesome?  This is used in a few places by
#        commands.py and search.py, but might be a hint that the plugin
#        architecture needs a little more polishing.
mailpile.config.ConfigManager.get_tag = GetTag
mailpile.config.ConfigManager.get_tags = GetTags
mailpile.config.ConfigManager.get_tag_id = GetTagID
mailpile.config.ConfigManager.get_tag_info = GetTagInfo
mailpile.config.ConfigManager.get_filters = GetFilters
mailpile.config.ConfigManager.filter_move = MoveFilter


##[ Commands ]################################################################

class TagCommand(Command):
    def slugify(self, tag_name):
        return CleanText(tag_name.lower().replace(' ', '-'),
                         banned=CleanText.NONDNS.replace('/', '')
                         ).clean.lower()

    def _reorder_all_tags(self):
        taglist = [(t.display, t.display_order, t.slug, t._key)
                   for t in self.session.config.tags.values()]
        taglist.sort()
        order = 1
        for td, tdo, ts, tid in taglist:
            self.session.config.tags[tid].display_order = order
            order += 1

    def finish(self, save=True):
        idx = self._idx()
        if save:
            # Background save makes things feel fast!
            def background():
                if idx:
                    idx.save_changes()
                self.session.config.save()
            self._background('Save index', background)


class Tag(TagCommand):
    """Add or remove tags on a set of messages"""
    SYNOPSIS = (None, 'tag', 'tag', '<[+|-]tags> <msgs>')
    ORDER = ('Tagging', 0)
    HTTP_CALLABLE = ('POST', )
    HTTP_POST_VARS = {
        'mid': 'message-ids',
        'add': 'tags',
        'del': 'tags'
    }

    class CommandResult(TagCommand.CommandResult):
        def as_text(self):
            if not self.result:
                return 'Failed'
            if not self.result['msg_ids']:
                return 'Nothing happened'
            what = []
            if self.result['tagged']:
                what.append('Tagged ' +
                            ', '.join([k['name'] for k
                                       in self.result['tagged']]))
            if self.result['untagged']:
                what.append('Untagged ' +
                            ', '.join([k['name'] for k
                                       in self.result['untagged']]))
            return '%s (%d messages)' % (', '.join(what),
                                         len(self.result['msg_ids']))

    def command(self, save=True, auto=False):
        idx = self._idx()

        if 'mid' in self.data:
            msg_ids = [int(m.replace('=', ''), 36) for m in self.data['mid']]
            ops = (['+%s' % t for t in self.data.get('add', []) if t] +
                   ['-%s' % t for t in self.data.get('del', []) if t])
        else:
            words = list(self.args)
            ops = []
            while words and words[0][0] in ('-', '+'):
                ops.append(words.pop(0))
            msg_ids = self._choose_messages(words)

        rv = {'msg_ids': [], 'tagged': [], 'untagged': []}
        rv['msg_ids'] = [b36(i) for i in msg_ids]
        for op in ops:
            tag = self.session.config.get_tag(op[1:])
            if tag:
                tag_id = tag._key
                tag = tag.copy()
                tag["tid"] = tag_id
                conversation = ('flat' not in (self.session.order or ''))
                if op[0] == '-':
                    idx.remove_tag(self.session, tag_id, msg_idxs=msg_ids,
                                   conversation=conversation)
                    rv['untagged'].append(tag)
                else:
                    idx.add_tag(self.session, tag_id, msg_idxs=msg_ids,
                                conversation=conversation)
                    rv['tagged'].append(tag)
                # Record behavior
                if len(msg_ids) < 15:
                    for t in self.session.config.get_tags(type='tagged'):
                        idx.add_tag(self.session, t._key, msg_idxs=msg_ids)
            else:
                self.session.ui.warning('Unknown tag: %s' % op)

        self.finish(save=save)
        return self._success(_('Tagged %d messagse') % len(msg_ids), rv)


class AddTag(TagCommand):
    """Create a new tag"""
    SYNOPSIS = (None, 'tags/add', 'tags/add', '<tag>')
    ORDER = ('Tagging', 0)
    HTTP_CALLABLE = ('GET', 'POST')
    HTTP_POST_VARS = {
        'name': 'tag name',
        'slug': 'tag slug',
        # Optional initial attributes of tags
        'icon': 'icon-tag',
        'label': 'display as label in search results, or not',
        'label_color': '03-gray-dark',
        'display': 'tag display type',
        'template': 'tag template type',
        'search_terms': 'default search associated with this tag',
        'magic_terms': 'magic search terms associated with this tag',
        'parent': 'parent tag ID',
    }
    OPTIONAL_VARS = ['icon', 'label', 'label_color', 'display', 'template',
                     'search_terms', 'parent']

    class CommandResult(TagCommand.CommandResult):
        def as_text(self):
            if not self.result:
                return 'Failed'
            if not self.result['added']:
                return 'Nothing happened'
            return ('Added tags: ' +
                    ', '.join([k['name'] for k in self.result['added']]))

    def command(self, save=True):
        config = self.session.config

        if self.data.get('_method', 'not-http').upper() == 'GET':
            return self._success(_('Add tags here!'), {
                'form': self.HTTP_POST_VARS,
                'rules': self.session.config.tags.rules['_any'][1]._RULES
            })

        slugs = self.data.get('slug', [])
        names = self.data.get('name', [])
        if slugs and len(names) != len(slugs):
            return self._error('Name/slug pairs do not match')
        elif names and not slugs:
            slugs = [self.slugify(n) for n in names]
        slugs.extend([self.slugify(s) for s in self.args])
        names.extend(self.args)

        for slug in slugs:
            if slug != self.slugify(slug):
                return self._error('Invalid tag slug: %s' % slug)

        for tag in config.tags.values():
            if tag.slug in slugs:
                return self._error('Tag already exists: %s/%s' % (tag.slug,
                                                                  tag.name))

        tags = [{'name': n, 'slug': s} for (n, s) in zip(names, slugs)]
        for v in self.OPTIONAL_VARS:
            for i in range(0, len(tags)):
                vlist = self.data.get(v, [])
                if len(vlist) > i and vlist[i]:
                    tags[i][v] = vlist[i]
        if tags:
            config.tags.extend(tags)
            self._reorder_all_tags()
            self.finish(save=save)

        return self._success(_('Added %d tags') % len(tags),
                             {'added': tags})


class ListTags(TagCommand):
    """List tags"""
    SYNOPSIS = (None, 'tags', 'tags', '[<wanted>|!<wanted>] [...]')
    ORDER = ('Tagging', 0)
    HTTP_STRICT_VARS = False

    class CommandResult(TagCommand.CommandResult):
        def as_text(self):
            if not self.result:
                return 'Failed'
            tags = self.result['tags']
            wrap = int(78 / 23)  # FIXME: Magic number
            text = []
            for i in range(0, len(tags)):
                stats = tags[i]['stats']
                text.append(('%s%5.5s %-18.18s'
                             ) % ((i % wrap) == 0 and '  ' or '',
                                  '%s' % (stats.get('sum_new', stats['new'])
                                          or ''),
                                  tags[i]['name'])
                            + ((i % wrap) == (wrap - 1) and '\n' or ''))
            return ''.join(text) + '\n'

    def command(self):
        result, idx = [], self._idx()

        args = []
        search = {}
        for arg in self.args:
            if '=' in arg:
                kw, val = arg.split('=', 1)
                search[kw.strip()] = val.strip()
            else:
                args.append(arg)
        for kw in self.data:
            if kw in self.session.config.tags.rules:
                search[kw] = self.data[kw]

        wanted = [t.lower() for t in args if not t.startswith('!')]
        unwanted = [t[1:].lower() for t in args if t.startswith('!')]
        wanted.extend([t.lower() for t in self.data.get('only', [])])
        unwanted.extend([t.lower() for t in self.data.get('not', [])])

        unread_messages = set()
        for tag in self.session.config.get_tags(type='unread'):
            unread_messages |= idx.TAGS.get(tag._key, set())

        excluded_messages = set()
        for tag in self.session.config.get_tags(flag_hides=True):
            excluded_messages |= idx.TAGS.get(tag._key, set())

        mode = search.get('mode', 'default')
        if 'mode' in search:
            del search['mode']

        for tag in self.session.config.get_tags(**search):
            if wanted and tag.slug.lower() not in wanted:
                continue
            if unwanted and tag.slug.lower() in unwanted:
                continue
            if mode == 'tree' and tag.parent and not wanted:
                continue

            # Hide invisible tags by default, any search terms at all will
            # disable this behavior
            if (not wanted and not unwanted and not search
                    and tag.display == 'invisible'):
                continue

            recursion = self.data.get('_recursion', 0)
            tid = tag._key

            # List subtags...
            if recursion == 0:
                subtags = self.session.config.get_tags(parent=tid)
                subtags.sort(key=lambda k: (k.get('display_order', 0), k.slug))
            else:
                subtags = None

            # Get tag info (how depends on whether this is a hiding tag)
            if tag.flag_hides:
                info = GetTagInfo(self.session.config, tid, stats=True,
                                  unread=unread_messages,
                                  subtags=subtags)
            else:
                info = GetTagInfo(self.session.config, tid, stats=True,
                                  unread=unread_messages,
                                  exclude=excluded_messages,
                                  subtags=subtags)

            # This expands out the full tree
            if subtags and recursion == 0:
                if mode in ('both', 'tree') or (wanted and mode != 'flat'):
                    info['subtags'] = ListTags(self.session,
                                               arg=[t.slug for t in subtags],
                                               data={'_recursion': 1}
                                               ).run().result['tags']

            result.append(info)
        return self._success(_('Listed %d tags') % len(result), {
            'search': search,
            'wanted': wanted,
            'unwanted': unwanted,
            'tags': result
        })


class DeleteTag(TagCommand):
    """Delete a tag"""
    SYNOPSIS = (None, 'tags/delete', 'tags/delete', '<tag>')
    ORDER = ('Tagging', 0)
    HTTP_CALLABLE = ('POST', 'DELETE')
    HTTP_POST_VARS = {
        "tag" : "tag(s) to delete"
    }

    class CommandResult(TagCommand.CommandResult):
        def as_text(self):
            if not self.result:
                return 'Failed'
            if not self.result['removed']:
                return 'Nothing happened'
            return ('Removed tags: ' +
                    ', '.join([k['name'] for k in self.result['removed']]))

    def command(self):
        session, config = self.session, self.session.config
        clean_session = mailpile.ui.Session(config)
        clean_session.ui = session.ui
        result = []

        tag_names = []
        if self.args:
            tag_names = list(self.args)
        elif self.data.get('tag', []):
            tag_names = self.data.get('tag', [])

        for tag_name in tag_names:

            tag = config.get_tag(tag_name)

            if tag:
                tag_id = tag._key

                # FIXME: Refuse to delete tag if in use by filters

                rv = (Search(clean_session, arg=['tag:%s' % tag_id]).run() and
                      Tag(clean_session, arg=['-%s' % tag_id, 'all']).run())
                if rv:
                    del config.tags[tag_id]
                    result.append({'name': tag.name, 'tid': tag_id})
                else:
                    raise Exception('That failed: %s' % rv)
            else:
                self._error('No such tag %s' % tag_name)
        if result:
            self._reorder_all_tags()
            self.finish(save=True)
        return self._success(_('Deleted %d tags') % len(result),
                             {'removed': result})


class FilterCommand(Command):
    def finish(self, save=True):
        def save_filter():
            self.session.config.save()
            if self.session.config.index:
                self.session.config.index.save_changes()
            return True
        if save:
            self._serialize('Save filter', save_filter)


class Filter(FilterCommand):
    """Add auto-tag rule for current search or terms"""
    SYNOPSIS = (None, 'filter', None, '[new|read] [notag] [=<mid>] '
                                      '[<terms>] [+<tag>] [-<tag>] '
                                      '[<comment>]')
    ORDER = ('Tagging', 1)
    HTTP_CALLABLE = ('POST', )

    def command(self, save=True):
        session, config = self.session, self.session.config
        args = list(self.args)

        flags = []
        while args and args[0] in ('add', 'set', 'new', 'read', 'notag'):
            flags.append(args.pop(0))

        if args and args[0] and args[0][0] == '=':
            filter_id = args.pop(0)[1:]
        else:
            filter_id = None

        if args and args[0] and args[0][0] == '@':
            filter_type = args.pop(0)[1:]
        else:
            filter_type = FILTER_TYPES[0]

        auto_tag = False
        if 'read' in flags:
            terms = ['@read']
        elif 'new' in flags:
            terms = ['*']
        elif args[0] and args[0][0] not in ('-', '+'):
            terms = []
            while args and args[0][0] not in ('-', '+'):
                terms.append(args.pop(0))
        else:
            terms = session.searched
            auto_tag = True

        if not terms or (len(args) < 1):
            raise UsageError('Need flags and search terms or a hook')

        tags, tids = [], []
        while args and args[0][0] in ('-', '+'):
            tag = args.pop(0)
            tags.append(tag)
            tids.append(tag[0] + config.get_tag_id(tag[1:]))

        if not args:
            args = ['Filter for %s' % ' '.join(tags)]

        if auto_tag and 'notag' not in flags:
            if not Tag(session, arg=tags + ['all']).run(save=False):
                raise UsageError()

        filter_dict = {
            'comment': ' '.join(args),
            'terms': ' '.join(terms),
            'tags': ' '.join(tids),
            'type': filter_type
        }
        if filter_id:
            config.filters[filter_id] = filter_dict
        else:
            config.filters.append(filter_dict)

        self.finish(save=save)
        return True


class DeleteFilter(FilterCommand):
    """Delete an auto-tagging rule"""
    SYNOPSIS = (None, 'filter/delete', None, '<filter-id>')
    ORDER = ('Tagging', 1)
    HTTP_CALLABLE = ('POST', 'DELETE')

    def command(self):
        session, config = self.session, self.session.config
        if len(self.args) < 1:
            raise UsageError('Delete what?')

        removed = 0
        filters = config.get('filter', {})
        filter_terms = config.get('filter_terms', {})
        args = list(self.args)
        for fid in self.args:
            if fid not in filters:
                match = [f for f in filters if filter_terms[f] == fid]
                if match:
                    args.remove(fid)
                    args.extend(match)

        for fid in args:
            if (config.parse_unset(session, 'filter:%s' % fid)
                    and config.parse_unset(session, 'filter_tags:%s' % fid)
                    and config.parse_unset(session, 'filter_terms:%s' % fid)):
                removed += 1
            else:
                session.ui.warning('Failed to remove %s' % fid)
        if removed:
            self.finish()
        return True


class ListFilters(Command):
    """List (all) auto-tagging rules"""
    SYNOPSIS = (None, 'filter/list', 'filter/list', '[<search>|=<id>|@<type>]')
    ORDER = ('Tagging', 1)
    HTTP_CALLABLE = ('GET', 'POST')
    HTTP_QUERY_VARS = {
        'search': 'Text to search for',
        'id': 'Filter ID',
        'type': 'Filter type'
    }

    class CommandResult(Command.CommandResult):
        def as_text(self):
            if self.result is False:
                return unicode(self.result)
            return '\n'.join([('%3.3s %-10s %-18s %-18s %s'
                               ) % (r['fid'], r['type'],
                                    r['terms'], r['human_tags'], r['comment'])
                              for r in self.result])

    def command(self, want_fid=None):
        results = []
        for (fid, trms, tags, cmnt, ftype
             ) in self.session.config.get_filters(filter_on=None,
                                                  types=['all']):
            if want_fid and fid != want_fid:
                continue

            human_tags = []
            for tterm in tags.split():
                tagname = self.session.config.tags.get(
                    tterm[1:], {}).get('slug', '(None)')
                human_tags.append('%s%s' % (tterm[0], tagname))

            skip = False
            args = list(self.args)
            args.extend([t for t in self.data.get('search', [])])
            args.extend(['='+t for t in self.data.get('id', [])])
            args.extend(['@'+t for t in self.data.get('type', [])])
            if args and not want_fid:
                for term in args:
                    term = term.lower()
                    if term.startswith('='):
                        if (term[1:] != fid):
                            skip = True
                    elif term.startswith('@'):
                        if (term[1:] != ftype):
                            skip = True
                    elif ((term not in ' '.join(human_tags).lower())
                            and (term not in trms.lower())
                            and (term not in cmnt.lower())):
                        skip = True
            if skip:
                continue

            results.append({
                'fid': fid,
                'terms': trms,
                'tags': tags,
                'human_tags': ' '.join(human_tags),
                'comment': cmnt,
                'type': ftype
            })
        return results


class MoveFilter(ListFilters):
    """Move an auto-tagging rule"""
    SYNOPSIS = (None, 'filter/move', None, '<filter-id> <position>')
    ORDER = ('Tagging', 1)
    HTTP_CALLABLE = ('POST', 'UPDATE')

    def command(self):
        self.session.config.filter_move(self.args[0], self.args[1])
        self.session.config.save()
        return ListFilters.command(self, want_fid=self.args[1])


_plugins.register_commands(Tag, AddTag, DeleteTag, ListTags,
                           Filter, DeleteFilter,
                           MoveFilter, ListFilters)

########NEW FILE########
__FILENAME__ = vcard_carddav
#coding:utf-8
import base64
import httplib
import sys
import re
import getopt
from gettext import gettext as _
from lxml import etree

from mailpile.plugins import PluginManager
from mailpile.vcard import *
from mailpile.util import *


_plugins = PluginManager(builtin=__file__)


class DAVClient:
    def __init__(self, host,
                 port=None, username=None, password=None, protocol='https'):
        if not port:
            if protocol == 'https':
                port = 443
            elif protocol == 'http':
                port = 80
            else:
                raise Exception("Can't determine port from protocol. "
                                "Please specifiy a port.")
        self.cwd = "/"
        self.baseurl = "%s://%s:%d" % (protocol, host, port)
        self.host = host
        self.port = port
        self.protocol = protocol
        self.username = username
        self.password = password
        if username and password:
            self.auth = base64.encodestring('%s:%s' % (username, password)
                                            ).replace('\n', '')
        else:
            self.auth = None

    def request(self, url, method, headers={}, body=""):
        if self.protocol == "https":
            req = httplib.HTTPSConnection(self.host, self.port)
            # FIXME: Verify HTTPS certificate
        else:
            req = httplib.HTTPConnection(self.host, self.port)

        req.putrequest(method, url)
        req.putheader("Host", self.host)
        req.putheader("User-Agent", "Mailpile")
        if self.auth:
            req.putheader("Authorization", "Basic %s" % self.auth)

        for key, value in headers.iteritems():
            req.putheader(key, value)

        req.endheaders()
        req.send(body)
        res = req.getresponse()

        self.last_status = res.status
        self.last_statusmessage = res.reason
        self.last_headers = dict(res.getheaders())
        self.last_body = res.read()

        if self.last_status >= 300:
            raise Exception(("HTTP %d: %s\n(%s %s)\n>>>%s<<<"
                             ) % (self.last_status, self.last_statusmessage,
                                  method, url, self.last_body))
        return (self.last_status, self.last_statusmessage,
                self.last_headers, self.last_body)

    def options(self, url):
        status, msg, header, resbody = self.request(url, "OPTIONS")
        return header["allow"].split(", ")


class CardDAV(DAVClient):
    def __init__(self, host, url,
                 port=None, username=None, password=None, protocol='https'):
        DAVClient.__init__(self, host, port, username, password, protocol)
        self.url = url

        if not self._check_capability():
            raise Exception("No CardDAV support on server")

    def cd(self, url):
        self.url = url

    def _check_capability(self):
        result = self.options(self.url)
        return "addressbook" in self.last_headers["dav"].split(", ")

    def get_vcard(self, url):
        status, msg, header, resbody = self.request(url, "GET")
        card = SimpleVCard()
        card.load(data=resbody)
        return card

    def put_vcard(self, url, vcard):
        raise Exception('Unimplemented')

    def list_vcards(self):
        stat, msg, hdr, resbody = self.request(self.url, "PROPFIND", {}, {})
        tr = etree.fromstring(resbody)
        urls = [x.text for x in tr.xpath("/d:multistatus/d:response/d:href",
                                         namespaces={"d": "DAV:"})
                if x.text not in ("", None) and x.text[-3:] == "vcf"]
        return urls


class CardDAVImporter(VCardImporter):
    REQUIRED_PARAMETERS = ["host", "url"]
    OPTIONAL_PARAMETERS = ["port", "username", "password", "protocol"]
    FORMAT_NAME = "CardDAV Server"
    FORMAT_DESCRIPTION = "CardDAV HTTP contact server."
    SHORT_NAME = "carddav"
    CONFIG_RULES = {
        'host': ('Host name', 'hostname', None),
        'port': ('Port number', int, None),
        'url': ('CardDAV URL', 'url', None),
        'protcol': ('Connection protocol', 'string', 'https'),
        'password': ('CardDAV URL', 'url', None),
        'username': ('CardDAV URL', 'url', None)
    }

    def get_contacts(self):
        self.carddav = CardDAV(host, url, port, username, password, protocol)
        results = []
        cards = self.carddav.list_vcards()
        for card in cards:
            results.append(self.carddav.get_vcard(card))

        return results

    def filter_contacts(self, terms):
        pass


_plugins.register_vcard_importers(CardDAVImporter)

########NEW FILE########
__FILENAME__ = vcard_gnupg
#coding:utf-8
import os
from gettext import gettext as _

from mailpile.plugins import PluginManager
from mailpile.crypto.gpgi import GnuPG
from mailpile.vcard import *


_plugins = PluginManager(builtin=__file__)


# User default GnuPG key file
DEF_GNUPG_HOME = os.path.expanduser('~/.gnupg')


class GnuPGImporter(VCardImporter):
    FORMAT_NAME = 'GnuPG'
    FORMAT_DESCRIPTION = _('Import contacts from GnuPG keyring')
    SHORT_NAME = 'gpg'
    CONFIG_RULES = {
        'active': [_('Enable this importer'), bool, True],
        'gpg_home': [_('Location of keyring'), 'path', DEF_GNUPG_HOME],
    }
    VCL_KEY_FMT = "data:application/x-pgp-fingerprint,%(fingerprint)s"

    def get_vcards(self):
        if not self.config.active:
            return []

        gnupg = GnuPG()
        keys = gnupg.list_keys()
        results = []
        vcards = {}
        for key in keys.values():
            vcls = [VCardLine(name="KEY",
                              value=self.VCL_KEY_FMT % key)]
            card = None
            emails = []
            for uid in key["uids"]:
                if "email" in uid and uid["email"]:
                    vcls.append(VCardLine(name="email", value=uid["email"]))
                    card = card or vcards.get(uid['email'])
                    emails.append(uid["email"])
                if "name" in uid and uid["name"]:
                    name = uid["name"]
                    vcls.append(VCardLine(name="fn", value=name))
            if card and emails:
                card.add(*vcls)
            elif emails:
                # This is us taking care to only create one card for each
                # set of e-mail addresses.
                card = SimpleVCard(*vcls)
                for email in emails:
                    vcards[email] = card
                results.append(card)

        return results


_plugins.register_vcard_importers(GnuPGImporter)

########NEW FILE########
__FILENAME__ = vcard_gravatar
#coding:utf-8
import os
import random
import time
from gettext import gettext as _
from urllib2 import urlopen

from mailpile.plugins import PluginManager
from mailpile.util import *
from mailpile.vcard import *


_plugins = PluginManager(builtin=__file__)


class GravatarImporter(VCardImporter):
    """
    This importer will pull contact details down from a central server,
    using the Gravatar JSON API and caching thumbnail data locally.

    For details, see https://secure.gravatar.com/site/implement/

    The importer will only pull down a few contacts at a time, to limit
    the impact on Gravatar's servers and prevent network traffic from
    stalling the rescan process too much.
    """
    FORMAT_NAME = 'Gravatar'
    FORMAT_DESCRIPTION = _('Import contact info from a Gravatar server')
    SHORT_NAME = 'gravatar'
    CONFIG_RULES = {
        'active': [_('Enable this importer'), bool, True],
        'interval': [_('Minimum days between refreshing'), 'int', 7],
        'batch': [_('Max batch size per update'), 'int', 30],
        'default': [_('Default thumbnail style'), str, 'retro'],
        'rating': [_('Preferred thumbnail rating'),
                   ['g', 'pg', 'r', 'x'], 'g'],
        'size': [_('Preferred thumbnail size'), 'int', 80],
        'url': [_('Gravatar server URL'), 'url', 'https://en.gravatar.com'],
    }
    VCARD_TS = 'x-gravatar-ts'
    VCARD_IMG = ''

    def _want_update(self):
        def _jittery_time():
            # This introduces 5 hours of jitter into the time check below,
            # biased towards extending the delay by an average of 1.5 hours
            # each time. This is mostly done to spread out the load on the
            # Gravatar server over time, as to begin with all contacts will
            # be checked at roughly the same time.
            return time.time() + random.randrange(-14400, 3600)

        want = []
        vcards = self.session.config.vcards
        for vcard in vcards.find_vcards([]):
            try:
                ts = int(vcard.get(self.VCARD_TS).value)
            except IndexError:
                ts = 0
            if ts < _jittery_time() - (self.config.interval * 24 * 3600):
                want.append(vcard)
            if len(want) >= self.config.batch:
                break
        return want

    def get_vcards(self):
        if not self.config.active:
            return []

        def _b64(data):
            return data.encode('base64').replace('\n', '')

        def _get(url):
            self.session.ui.mark('Getting: %s' % url)
            return urlopen(url).read()

        results = []
        for contact in self._want_update():
            vcls = [VCardLine(name=self.VCARD_TS, value=int(time.time()))]

            email = contact.email
            if not email:
                continue

            img = json = None
            for vcl in contact.get_all('email'):
                digest = md5_hex(vcl.value.lower())
                try:
                    if not img:
                        img = _get(('%s/avatar/%s.jpg?s=%s&r=%s&d=404'
                                    ) % (self.config.url,
                                         digest,
                                         self.config.size,
                                         self.config.rating))
                    if not json:
                        json = _get('%s/%s.json' % (self.config.url, digest))
                        email = vcl.value
                except IOError:
                    pass

            if json:
                pass  # FIXME: parse the JSON

            if (self.config.default != '404') and not img:
                try:
                    img = _get(('%s/avatar/%s.jpg?s=%s&d=%s'
                                ) % (self.config.url,
                                     md5_hex(email.lower()),
                                     self.config.size,
                                     self.config.default))
                except IOError:
                    pass

            if img:
                vcls.append(VCardLine(
                    name='photo',
                    value='data:image/jpeg;base64,%s' % _b64(img),
                    mediatype='image/jpeg'
                ))

            vcls.append(VCardLine(name='email', value=email))
            results.append(SimpleVCard(*vcls))
        return results


_plugins.register_vcard_importers(GravatarImporter)

########NEW FILE########
__FILENAME__ = vcard_mork
#!/usr/bin/python
#coding:utf-8
import sys
import re
import getopt
from gettext import gettext as _
from sys import stdin, stdout, stderr

from mailpile.plugins import PluginManager
from mailpile.vcard import *


_plugins = PluginManager(builtin=__file__)


def hexcmp(x, y):
    try:
        a = int(x, 16)
        b = int(y, 16)
        if a < b:
            return -1
        if a > b:
            return 1
        return 0

    except:
        return cmp(x, y)


class MorkImporter(VCardImporter):
    # Based on Demork by Mike Hoye <mhoye@off.net>
    # Which is based on Mindy by Kumaran Santhanam <kumaran@alumni.stanford.org>
    #
    # To understand the insanity that is Mork, read these:
    #  http://www-archive.mozilla.org/mailnews/arch/mork/primer.txt
    #  http://www.jwz.org/blog/2004/03/when-the-database-worms-eat-into-your-brain/
    #
    FORMAT_NAME = "Mork Database"
    FORMAT_DESCRPTION = "Thunderbird contacts database format."
    SHORT_NAME = "mork"
    CONFIG_RULES = {
        'filename': [_('Location of Mork database'), 'path', ""],
    }

    class Database:
        def __init__(self):
            self.cdict = {}
            self.adict = {}
            self.tables = {}

    class Table:
        def __init__(self):
            self.id = None
            self.scope = None
            self.kind = None
            self.rows = {}

    class Row:
        def __init__(self):
            self.id = None
            self.scope = None
            self.cells = []

    class Cell:
        def __init__(self):
            self.column = None
            self.atom = None

    def escapeData(self, match):
        return match.group() \
            .replace('\\\\n', '$0A') \
            .replace('\\)', '$29') \
            .replace('>', '$3E') \
            .replace('}', '$7D') \
            .replace(']', '$5D')

    pCellText = re.compile(r'\^(.+?)=(.*)')
    pCellOid = re.compile(r'\^(.+?)\^(.+)')
    pCellEscape = re.compile(r'((?:\\[\$\0abtnvfr])|(?:\$..))')
    pMindyEscape = re.compile('([\x00-\x1f\x80-\xff\\\\])')

    def escapeMindy(self, match):
        s = match.group()
        if s == '\\':
            return '\\\\'
        if s == '\0':
            return '\\0'
        if s == '\r':
            return '\\r'
        if s == '\n':
            return '\\n'
        return "\\x%02x" % ord(s)

    def encodeMindyValue(self, value):
        return self.pMindyEscape.sub(self.escapeMindy, value)

    backslash = {'\\\\': '\\',
                 '\\$': '$',
                 '\\0': chr(0),
                 '\\a': chr(7),
                 '\\b': chr(8),
                 '\\t': chr(9),
                 '\\n': chr(10),
                 '\\v': chr(11),
                 '\\f': chr(12),
                 '\\r': chr(13)}

    def unescapeMork(self, match):
        s = match.group()
        if s[0] == '\\':
            return self.backslash[s]
        else:
            return chr(int(s[1:], 16))

    def decodeMorkValue(self, value):
        m = self.pCellEscape.sub(self.unescapeMork, value)
        m = m.decode("utf-8")
        return m

    def addToDict(self, dict, cells):
        for cell in cells:
            eq = cell.find('=')
            key = cell[1:eq]
            val = cell[eq+1:-1]
            dict[key] = self.decodeMorkValue(val)

    def getRowIdScope(self, rowid, cdict):
        idx = rowid.find(':')
        if idx > 0:
            return (rowid[:idx], cdict[rowid[idx+2:]])
        else:
            return (rowid, None)

    def delRow(self, db, table, rowid):
        (rowid, scope) = self.getRowIdScope(rowid, db.cdict)
        if scope:
            rowkey = rowid + "/" + scope
        else:
            rowkey = rowid + "/" + table.scope

        if rowkey in table.rows:
            del table.rows[rowkey]

    def addRow(self, db, table, rowid, cells):
        row = self.Row()
        row.id, row.scope = self.getRowIdScope(rowid, db.cdict)

        for cell in cells:
            obj = self.Cell()
            cell = cell[1:-1]

            match = self.pCellText.match(cell)
            if match:
                obj.column = db.cdict[match.group(1)]
                obj.atom = self.decodeMorkValue(match.group(2))

            else:
                match = self.pCellOid.match(cell)
                if match:
                    obj.column = db.cdict[match.group(1)]
                    obj.atom = db.adict[match.group(2)]

            if obj.column and obj.atom:
                row.cells.append(obj)

        if row.scope:
            rowkey = row.id + "/" + row.scope
        else:
            rowkey = row.id + "/" + table.scope

        if rowkey in table.rows:
            print >>stderr, "ERROR: duplicate rowid/scope %s" % rowkey
            print >>stderr, cells

        table.rows[rowkey] = row

    def inputMork(self, data):
        # Remove beginning comment
        pComment = re.compile('//.*')
        data = pComment.sub('', data, 1)

        # Remove line continuation backslashes
        pContinue = re.compile(r'(\\(?:\r|\n))')
        data = pContinue.sub('', data)

        # Remove line termination
        pLine = re.compile(r'(\n\s*)|(\r\s*)|(\r\n\s*)')
        data = pLine.sub('', data)

        # Create a database object
        db = self.Database()

        # Compile the appropriate regular expressions
        pCell = re.compile(r'(\(.+?\))')
        pSpace = re.compile(r'\s+')
        pColumnDict = re.compile(r'<\s*<\(a=c\)>\s*(?:\/\/)?\s*'
                                 '(\(.+?\))\s*>')
        pAtomDict = re.compile(r'<\s*(\(.+?\))\s*>')
        pTable = re.compile(r'\{-?(\d+):\^(..)\s*\{\(k\^(..):c\)'
                            '\(s=9u?\)\s*(.*?)\}\s*(.+?)\}')
        pRow = re.compile(r'(-?)\s*\[(.+?)((\(.+?\)\s*)*)\]')

        pTranBegin = re.compile(r'@\$\$\{.+?\{\@')
        pTranEnd = re.compile(r'@\$\$\}.+?\}\@')

        # Escape all '%)>}]' characters within () cells
        data = pCell.sub(self.escapeData, data)

        # Iterate through the data
        index = 0
        length = len(data)
        match = None
        tran = 0
        while True:
            if match:
                index += match.span()[1]
            if index >= length:
                break
            sub = data[index:]

            # Skip whitespace
            match = pSpace.match(sub)
            if match:
                index += match.span()[1]
                continue

            # Parse a column dictionary
            match = pColumnDict.match(sub)
            if match:
                m = pCell.findall(match.group())
                # Remove extraneous '(f=iso-8859-1)'
                if len(m) >= 2 and m[1].find('(f=') == 0:
                    m = m[1:]
                self.addToDict(db.cdict, m[1:])
                continue

            # Parse an atom dictionary
            match = pAtomDict.match(sub)
            if match:
                cells = pCell.findall(match.group())
                self.addToDict(db.adict, cells)
                continue

            # Parse a table
            match = pTable.match(sub)
            if match:
                id = match.group(1) + ':' + match.group(2)

                try:
                    table = db.tables[id]

                except KeyError:
                    table = self.Table()
                    table.id = match.group(1)
                    table.scope = db.cdict[match.group(2)]
                    table.kind = db.cdict[match.group(3)]
                    db.tables[id] = table

                rows = pRow.findall(match.group())
                for row in rows:
                    cells = pCell.findall(row[2])
                    rowid = row[1]
                    if tran and rowid[0] == '-':
                        rowid = rowid[1:]
                        self.delRow(db, db.tables[id], rowid)

                    if tran and row[0] == '-':
                        pass

                    else:
                        self.addRow(db, db.tables[id], rowid, cells)
                continue

            # Transaction support
            match = pTranBegin.match(sub)
            if match:
                tran = 1
                continue

            match = pTranEnd.match(sub)
            if match:
                tran = 0
                continue

            match = pRow.match(sub)
            if match and tran:
                # print >>stderr, ("WARNING: using table '1:^80' "
                #                  "for dangling row: %s") % match.group()
                rowid = match.group(2)
                if rowid[0] == '-':
                    rowid = rowid[1:]

                cells = pCell.findall(match.group(3))
                self.delRow(db, db.tables['1:80'], rowid)
                if row[0] != '-':
                    self.addRow(db, db.tables['1:80'], rowid, cells)
                continue

            # Syntax error
            print >>stderr, "ERROR: syntax error while parsing MORK file"
            print >>stderr, "context[%d]: %s" % (index, sub[:40])
            index += 1

        # Return the database
        self.db = db
        return db

    def morkToHash(self):
        results = []
        columns = self.db.cdict.keys()
        columns.sort(hexcmp)

        tables = self.db.tables.keys()
        tables.sort(hexcmp)

        for table in [self.db.tables[k] for k in tables]:
            rows = table.rows.keys()
            rows.sort(hexcmp)
            for row in [table.rows[k] for k in rows]:
                email = name = ""
                result = {}
                for cell in row.cells:
                    result[cell.column] = cell.atom
                    if cell.column == "PrimaryEmail":
                        result["email"] = cell.atom.lower()
                    elif cell.column == "DisplayName":
                        result["name"] = cell.atom.strip("'")
                results.append(result)

        return results

    def load(self):
        with open(self.config.filename, "r") as fh:
            data = fh.read()

            if data.find("<mdb:mork") < 0:
                raise ValueError("Mork file required")

            self.inputMork(data)

    def get_vcards(self):
        self.load()
        people = self.morkToHash()
        # print people

        results = []
        vcards = {}
        for person in people:
            card = SimpleVCard()
            if "name" in person:
                card.add(VCardLine(name="FN", value=person["name"]))
            if "email" in person:
                card.add(VCardLine(name="EMAIL", value=person["email"]))
            results.append(card)

        return results


if __name__ == "__main__":
    import json
    filename = sys.argv[1]

    m = MorkImporter(filename=filename)
    m.load()
    print m.get_contacts(data)
else:
    _plugins.register_vcard_importers(MorkImporter)

########NEW FILE########
__FILENAME__ = postinglist
import os
import random
import threading
from gettext import gettext as _

import mailpile.util
from mailpile.util import *


GLOBAL_POSTING_LIST = None

GLOBAL_POSTING_LOCK = threading.Lock()
GLOBAL_OPTIMIZE_LOCK = threading.Lock()


# FIXME: Create a tiny cache for PostingList objects, so we can start
#        encrypting them.  We should have a read-cache of moderate size,
# and a one-element write cache which only writes to disk when a PostingList
# gets evicted OR the cache in its entirety is flushed. Due to how keywords
# are grouped into posting lists and the fact that they are flushed to
# disk in sorted order, this should be enough to group everything together
# that can actually be grouped.


class PostingList(object):
    """A posting list is a map of search terms to message IDs."""

    CHARACTERS = 'abcdefghijklmnopqrstuvwxyz0123456789+_'

    MAX_SIZE = 60    # perftest gives: 75% below 500ms, 50% below 100ms
    HASH_LEN = 24

    @classmethod
    def _Optimize(cls, session, idx, force=False):
        postinglist_kb = session.config.sys.postinglist_kb

        # Pass 1: Compact all files that are 90% or more of our target size
        for c in cls.CHARACTERS:
            postinglist_dir = session.config.postinglist_dir(c)
            for fn in sorted(os.listdir(postinglist_dir)):
                if mailpile.util.QUITTING:
                    break
                filesize = os.path.getsize(os.path.join(postinglist_dir, fn))
                if force or (filesize > 900 * postinglist_kb):
                    session.ui.mark('Pass 1: Compacting >%s<' % fn)
                    play_nice_with_threads()
                    try:
                        GLOBAL_POSTING_LOCK.acquire()
                        # FIXME: Remove invalid and deleted messages from
                        #        posting lists.
                        cls(session, fn, sig=fn).save()
                    finally:
                        GLOBAL_POSTING_LOCK.release()

        # Pass 2: While mergable pair exists: merge them!
        for c in cls.CHARACTERS:
            postinglist_dir = session.config.postinglist_dir(c)
            files = [n for n in os.listdir(postinglist_dir) if len(n) > 1]
            files.sort(key=lambda a: -len(a))
            for fn in files:
                if mailpile.util.QUITTING:
                    break
                size = os.path.getsize(os.path.join(postinglist_dir, fn))
                fnp = fn[:-1]
                while not os.path.exists(os.path.join(postinglist_dir, fnp)):
                    fnp = fnp[:-1]
                size += os.path.getsize(os.path.join(postinglist_dir, fnp))
                if (size < (1024 * postinglist_kb - (cls.HASH_LEN * 6))):
                    session.ui.mark('Pass 2: Merging %s into %s' % (fn, fnp))
                    play_nice_with_threads()
                    try:
                        GLOBAL_POSTING_LOCK.acquire()
                        with open(os.path.join(postinglist_dir, fn), 'r') as fd, \
                                open(os.path.join(postinglist_dir, fnp), 'a') as fdp:
                            for line in fd:
                                fdp.write(line)
                    finally:
                        os.remove(os.path.join(postinglist_dir, fn))
                        GLOBAL_POSTING_LOCK.release()

        filecount = 0
        for c in cls.CHARACTERS:
            filecount += len(os.listdir(session.config.postinglist_dir(c)))
        session.ui.mark('Optimized %s posting lists' % filecount)
        return filecount

    @classmethod
    def _Append(cls, session, word, mail_ids, compact=True, sig=None):
        config = session.config
        sig = sig or cls.WordSig(word, config)
        fd, fn = cls.GetFile(session, sig, mode='a')
        try:
            if (compact
                    and (os.path.getsize(os.path.join(config.postinglist_dir(fn),
                         fn)) > ((1024 * config.sys.postinglist_kb) -
                                 (cls.HASH_LEN * 6)))
                    and (random.randint(0, 50) == 1)):
                # This will compact the files and split out hot-spots, but we
                # only bother "once in a while" when the files are "big".
                fd.close()
                pls = cls(session, word, sig=sig)
                for mail_id in mail_ids:
                    pls.append(mail_id)
                pls.save()
            else:
                # Quick and dirty append is the default.
                fd.write('%s\t%s\n' % (sig, '\t'.join(mail_ids)))
        finally:
            if not fd.closed:
                fd.close()

    @classmethod
    def Lock(cls, lock, method, *args, **kwargs):
        lock.acquire()
        try:
            return method(*args, **kwargs)
        finally:
            lock.release()

    @classmethod
    def Optimize(cls, *args, **kwargs):
        return cls.Lock(GLOBAL_OPTIMIZE_LOCK, cls._Optimize, *args, **kwargs)

    @classmethod
    def Append(cls, *args, **kwargs):
        return cls.Lock(GLOBAL_POSTING_LOCK, cls._Append, *args, **kwargs)

    @classmethod
    def WordSig(cls, word, config):
        return strhash(word, cls.HASH_LEN,
                       obfuscate=config.prefs.obfuscate_index)

    @classmethod
    def SaveFile(cls, session, prefix):
        return os.path.join(session.config.postinglist_dir(prefix), prefix)

    @classmethod
    def GetFile(cls, session, sig, mode='r'):
        sig = sig[:cls.HASH_LEN]
        while len(sig) > 0:
            fn = cls.SaveFile(session, sig)
            try:
                if os.path.exists(fn):
                    return (open(fn, mode), sig)
            except (IOError, OSError):
                pass

            if len(sig) > 1:
                sig = sig[:-1]
            else:
                if 'r' in mode:
                    return (None, sig)
                else:
                    return (open(fn, mode), sig)
        # Not reached
        return (None, None)

    def __init__(self, session, word, sig=None, config=None):
        self.config = config or session.config
        self.session = session
        self.sig = sig or self.WordSig(word, self.config)
        self.word = word
        self.WORDS = {self.sig: set()}
        self.lock = threading.Lock()
        self.load()

    def _parse_line(self, line):
        words = line.strip().split('\t')
        if len(words) > 1:
            wset = set(words[1:])
            if words[0] in self.WORDS:
                self.WORDS[words[0]] |= wset
            else:
                self.WORDS[words[0]] = wset

    def load(self):
        self.size = 0
        fd, self.filename = self.GetFile(self.session, self.sig)
        if fd:
            try:
                self.lock.acquire()
                self.size = decrypt_and_parse_lines(fd, self._parse_line,
                                                    self.config)
            except ValueError:
                pass
            finally:
                fd.close()
                self.lock.release()

    def _fmt_file(self, prefix):
        output = []
        self.session.ui.mark('Formatting prefix %s' % unicode(prefix))
        for word in self.WORDS.keys():
            data = self.WORDS.get(word, [])
            if ((prefix == 'ALL' or word.startswith(prefix))
                    and len(data) > 0):
                output.append(('%s\t%s\n'
                               ) % (word, '\t'.join(['%s' % x for x in data])))
        return ''.join(output)

    def _compact(self, prefix, output, locked=False):
        while ((len(output) > 1024 * self.config.sys.postinglist_kb) and
               (len(prefix) < self.HASH_LEN)):
            biggest = self.sig
            for word in self.WORDS:
                if (len(self.WORDS.get(word, []))
                        > len(self.WORDS.get(biggest, []))):
                    biggest = word
            if len(biggest) > len(prefix):
                biggest = biggest[:len(prefix) + 1]
                self.save(prefix=biggest, mode='a', locked=locked)
                for key in [k for k in self.WORDS if k.startswith(biggest)]:
                    del self.WORDS[key]
                output = self._fmt_file(prefix)
        return prefix, output

    def save(self, prefix=None, compact=True, mode='w', locked=False):
        if not locked:
            self.lock.acquire()
        try:
            prefix = prefix or self.filename
            output = self._fmt_file(prefix)
            if compact:
                prefix, output = self._compact(prefix, output, locked=True)
            try:
                outfile = self.SaveFile(self.session, prefix)
                self.session.ui.mark('Writing %d bytes to %s' % (len(output),
                                                                 outfile))
                if output:
                    with open(outfile, mode) as fd:
                        fd.write(output)
                        return len(output)
                elif os.path.exists(outfile):
                    os.remove(outfile)
            except:
                self.session.ui.warning('%s' % (sys.exc_info(), ))
            return 0
        finally:
            if not locked:
                self.lock.release()

    def hits(self):
        return self.WORDS[self.sig]

    def append(self, eid):
        self.lock.acquire()
        try:
            if self.sig not in self.WORDS:
                self.WORDS[self.sig] = set()
            self.WORDS[self.sig].add(eid)
            return self
        finally:
            self.lock.release()

    def remove(self, eids):
        self.lock.acquire()
        try:
            for eid in eids:
                try:
                    self.WORDS[self.sig].remove(eid)
                except KeyError:
                    pass
            return self
        finally:
            self.lock.release()


GLOBAL_GPL_LOCK = threading.Lock()


class GlobalPostingList(PostingList):

    @classmethod
    def _Optimize(cls, session, idx, force=False, lazy=False, quick=False):
        count = 0
        global GLOBAL_POSTING_LIST
        if (GLOBAL_POSTING_LIST
                and (not lazy or len(GLOBAL_POSTING_LIST) > 40*1024)):
            keys = sorted(GLOBAL_POSTING_LIST.keys())
            pls = GlobalPostingList(session, '')
            for sig in keys:
                if (count % 25) == 0:
                    play_nice_with_threads()
                    session.ui.mark(('Updating search index... %d%% (%s)'
                                     ) % (count * 100 / len(keys), sig))
                # If we're doing a full optimize later, we disable the
                # compaction here. Otherwise it follows the normal
                # rules (compacts as necessary).
                pls._migrate(sig, compact=quick)
                count += 1
            pls.save()

        if quick:
            return count
        else:
            return PostingList._Optimize(session, idx, force=force)

    @classmethod
    def SaveFile(cls, session, prefix):
        return os.path.join(session.config.workdir, 'kw-journal.dat')

    @classmethod
    def GetFile(cls, session, sig, mode='r'):
        try:
            return (open(cls.SaveFile(session, sig), mode),
                    'kw-journal.dat')
        except (IOError, OSError):
            return (None, 'kw-journal.dat')

    @classmethod
    def _Append(cls, session, word, mail_ids, compact=True):
        super(GlobalPostingList, cls)._Append(session, word, mail_ids,
                                              compact=compact)
        global GLOBAL_POSTING_LIST
        GLOBAL_GPL_LOCK.acquire()
        try:
            sig = cls.WordSig(word, session.config)
            if GLOBAL_POSTING_LIST is None:
                GLOBAL_POSTING_LIST = {}
            if sig not in GLOBAL_POSTING_LIST:
                GLOBAL_POSTING_LIST[sig] = set()
            for mail_id in mail_ids:
                GLOBAL_POSTING_LIST[sig].add(mail_id)
        finally:
            GLOBAL_GPL_LOCK.release()

    def __init__(self, *args, **kwargs):
        PostingList.__init__(self, *args, **kwargs)
        self.lock = GLOBAL_GPL_LOCK

    def _fmt_file(self, prefix):
        return PostingList._fmt_file(self, 'ALL')

    def _compact(self, prefix, output, **kwargs):
        return prefix, output

    def load(self):
        self.filename = 'kw-journal.dat'
        global GLOBAL_POSTING_LIST
        if GLOBAL_POSTING_LIST:
            self.WORDS = GLOBAL_POSTING_LIST
        else:
            PostingList.load(self)
            GLOBAL_POSTING_LIST = self.WORDS

    def _migrate(self, sig=None, compact=True):
        self.lock.acquire()
        try:
            sig = sig or self.sig
            if sig in self.WORDS and len(self.WORDS[sig]) > 0:
                PostingList.Append(self.session, sig, self.WORDS[sig],
                                   sig=sig, compact=compact)
                del self.WORDS[sig]
        finally:
            self.lock.release()

    def remove(self, eids):
        PostingList(self.session, self.word,
                    sig=self.sig, config=self.config).remove(eids).save()
        return PostingList.remove(self, eids)

    def hits(self):
        return (self.WORDS.get(self.sig, set())
                | PostingList(self.session, self.word,
                              sig=self.sig, config=self.config).hits())

########NEW FILE########
__FILENAME__ = search
import email
import lxml.html
import re
import rfc822
import time
import threading
import traceback
from gettext import gettext as _
from gettext import ngettext as _n
from urllib import quote, unquote

import mailpile.util
from mailpile.util import *
from mailpile.plugins import PluginManager
from mailpile.mailutils import MBX_ID_LEN, NoSuchMailboxError
from mailpile.mailutils import ExtractEmails, ExtractEmailAndName
from mailpile.mailutils import Email, ParseMessage, HeaderPrint
from mailpile.postinglist import GlobalPostingList
from mailpile.ui import *


_plugins = PluginManager()


class SearchResultSet:
    """
    Search results!
    """
    def __init__(self, idx, terms, results, exclude):
        self.terms = set(terms)
        self._index = idx
        self.set_results(results, exclude)

    def set_results(self, results, exclude):
        self._results = {
            'raw': set(results),
            'excluded': set(exclude) & set(results)
        }
        return self

    def __len__(self):
        return len(self._results.get('raw', []))

    def as_set(self, order='raw'):
        return self._results[order] - self._results['excluded']

    def excluded(self):
        return self._results['excluded']


SEARCH_RESULT_CACHE = {}


class CachedSearchResultSet(SearchResultSet):
    """
    Cached search result.
    """
    def __init__(self, idx, terms):
        global SEARCH_RESULT_CACHE
        self.terms = set(terms)
        self._index = idx
        self._results = SEARCH_RESULT_CACHE.get(self._skey(), {})
        self._results['_last_used'] = time.time()

    def _skey(self):
        return ' '.join(self.terms)

    def set_results(self, *args):
        global SEARCH_RESULT_CACHE
        SearchResultSet.set_results(self, *args)
        SEARCH_RESULT_CACHE[self._skey()] = self._results
        self._results['_last_used'] = time.time()
        return self

    @classmethod
    def DropCaches(cls, msg_idxs=None, tags=None):
        # FIXME: Make this more granular
        global SEARCH_RESULT_CACHE
        SEARCH_RESULT_CACHE = {}


class MailIndex:
    """This is a lazily parsing object representing a mailpile index."""

    MSG_MID = 0
    MSG_PTRS = 1
    MSG_ID = 2
    MSG_DATE = 3
    MSG_FROM = 4
    MSG_TO = 5
    MSG_CC = 6
    MSG_KB = 7
    MSG_SUBJECT = 8
    MSG_BODY = 9
    MSG_TAGS = 10
    MSG_REPLIES = 11
    MSG_THREAD_MID = 12

    MSG_FIELDS_V1 = 11
    MSG_FIELDS_V2 = 13

    BOGUS_METADATA = [None, '', None, '0', '(no sender)', '', '', '0',
                      '(not in index)', '', '', '', '-1']

    MAX_INCREMENTAL_SAVES = 25

    def __init__(self, config):
        self.config = config
        self.interrupt = None
        self.INDEX = []
        self.INDEX_SORT = {}
        self.INDEX_THR = []
        self.PTRS = {}
        self.TAGS = {}
        self.MSGIDS = {}
        self.EMAILS = []
        self.EMAIL_IDS = {}
        self.CACHE = {}
        self.MODIFIED = set()
        self.EMAILS_SAVED = 0
        self._scanned = {}
        self._saved_changes = 0
        self._lock = threading.RLock()

    @classmethod
    def l2m(self, line):
        return line.decode('utf-8').split(u'\t')

    # A translation table for message parts stored in the index, consists of
    # a mapping from unicode ordinals to either another unicode ordinal or
    # None, to remove a character. By default it removes the ASCII control
    # characters and replaces tabs and newlines with spaces.
    NORM_TABLE = dict([(i, None) for i in range(0, 0x20)], **{
        ord(u'\t'): ord(u' '),
        ord(u'\r'): ord(u' '),
        ord(u'\n'): ord(u' '),
        0x7F: None
    })

    @classmethod
    def m2l(self, message):
        # Normalize the message before saving it so we can be sure that we will
        # be able to read it back later.
        parts = [unicode(p).translate(self.NORM_TABLE) for p in message]
        return (u'\t'.join(parts)).encode('utf-8')

    @classmethod
    def get_body(self, msg_info):
        if msg_info[self.MSG_BODY].startswith('{'):
            return json.loads(msg_info[self.MSG_BODY])
        else:
            return {
                'snippet': msg_info[self.MSG_BODY]
            }

    @classmethod
    def truncate_body_snippet(self, body, max_chars):
        if 'snippet' in body:
            delta = len(self.encode_body(body)) - max_chars
            if delta > 0:
                body['snippet'] = body['snippet'][:-delta].rsplit(' ', 1)[0]

    @classmethod
    def encode_body(self, d, **kwargs):
        for k, v in kwargs:
            if v is None:
                if k in d:
                    del d[k]
            else:
                d[k] = v
        if len(d) == 1 and 'snippet' in d:
            return d['snippet']
        else:
            return json.dumps(d)

    @classmethod
    def set_body(self, msg_info, **kwargs):
        d = self.get_body(msg_info)
        msg_info[self.MSG_BODY] = self.encode_body(d, **kwargs)

    def load(self, session=None):
        self.INDEX = []
        self.CACHE = {}
        self.PTRS = {}
        self.MSGIDS = {}
        self.EMAILS = []
        self.EMAIL_IDS = {}
        CachedSearchResultSet.DropCaches()

        def process_line(line):
            try:
                line = line.strip()
                if line.startswith('#'):
                    pass
                elif line.startswith('@'):
                    pos, email = line[1:].split('\t', 1)
                    pos = int(pos, 36)
                    while len(self.EMAILS) < pos + 1:
                        self.EMAILS.append('')
                    unquoted_email = unquote(email).decode('utf-8')
                    self.EMAILS[pos] = unquoted_email
                    self.EMAIL_IDS[unquoted_email.split()[0].lower()] = pos
                elif line:
                    words = line.split('\t')

                    # Migration: converting old metadata into new!
                    if len(words) != self.MSG_FIELDS_V2:

                        # V1 -> V2 adds MSG_CC and MSG_KB
                        if len(words) == self.MSG_FIELDS_V1:
                            words[self.MSG_CC:self.MSG_CC] = ['']
                            words[self.MSG_KB:self.MSG_KB] = ['0']

                        # Add V2 -> V3 here, etc. etc.

                        if len(words) == self.MSG_FIELDS_V2:
                            line = '\t'.join(words)
                        else:
                            raise Exception(_('Your metadata index is either '
                                              'too old, too new or corrupt!'))

                    pos = int(words[self.MSG_MID], 36)
                    while len(self.INDEX) < pos + 1:
                        self.INDEX.append('')

                    self.INDEX[pos] = line
                    self.MSGIDS[words[self.MSG_ID]] = pos
                    self.update_msg_tags(pos, words)
                    for msg_ptr in words[self.MSG_PTRS].split(','):
                        self.PTRS[msg_ptr] = pos

            except ValueError:
                pass

        if session:
            session.ui.mark(_('Loading metadata index...'))
        try:
            self._lock.acquire()
            with open(self.config.mailindex_file(), 'r') as fd:
                for line in fd:
                    if line.startswith(GPG_BEGIN_MESSAGE):
                        for line in decrypt_gpg([line], fd):
                            process_line(line)
                    else:
                        process_line(line)
        except IOError:
            if session:
                session.ui.warning(_('Metadata index not found: %s'
                                     ) % self.config.mailindex_file())
        finally:
            self._lock.release()
            play_nice_with_threads()

        self.cache_sort_orders(session)
        if session:
            session.ui.mark(_n('Loaded metadata, %d message',
                               'Loaded metadata, %d messages',
                               len(self.INDEX)
                               ) % len(self.INDEX))
        self.EMAILS_SAVED = len(self.EMAILS)

    def update_msg_tags(self, msg_idx_pos, msg_info):
        tags = set([t for t in msg_info[self.MSG_TAGS].split(',') if t])
        for tid in (set(self.TAGS.keys()) - tags):
            self.TAGS[tid] -= set([msg_idx_pos])
        for tid in tags:
            if tid not in self.TAGS:
                self.TAGS[tid] = set()
            self.TAGS[tid].add(msg_idx_pos)

    def save_changes(self, session=None):
        mods, self.MODIFIED = self.MODIFIED, set()
        if mods or len(self.EMAILS) > self.EMAILS_SAVED:
            if self._saved_changes >= self.MAX_INCREMENTAL_SAVES:
                return self.save(session=session)
            try:
                self._lock.acquire()
                if session:
                    session.ui.mark(_("Saving metadata index changes..."))
                with gpg_open(self.config.mailindex_file(),
                              self.config.prefs.gpg_recipient, 'a') as fd:
                    for eid in range(self.EMAILS_SAVED, len(self.EMAILS)):
                        quoted_email = quote(self.EMAILS[eid].encode('utf-8'))
                        fd.write('@%s\t%s\n' % (b36(eid), quoted_email))
                    for pos in mods:
                        fd.write(self.INDEX[pos] + '\n')
                if session:
                    session.ui.mark(_("Saved metadata index changes"))
                self.EMAILS_SAVED = len(self.EMAILS)
                self._saved_changes += 1
            finally:
                self._lock.release()

    def save(self, session=None):
        try:
            self._lock.acquire()
            self.MODIFIED = set()
            if session:
                session.ui.mark(_("Saving metadata index..."))

            idxfile = self.config.mailindex_file()
            newfile = '%s.new' % idxfile

            with gpg_open(newfile, self.config.prefs.gpg_recipient, 'w') as fd:
                fd.write('# This is the mailpile.py index file.\n')
                fd.write('# We have %d messages!\n' % len(self.INDEX))
                for eid in range(0, len(self.EMAILS)):
                    quoted_email = quote(self.EMAILS[eid].encode('utf-8'))
                    fd.write('@%s\t%s\n' % (b36(eid), quoted_email))
                for item in self.INDEX:
                    fd.write(item + '\n')

            # Keep the last 5 index files around... just in case.
            backup_file(idxfile, backups=5, min_age_delta=10)
            os.rename(newfile, idxfile)

            self._saved_changes = 0
            if session:
                session.ui.mark(_("Saved metadata index"))
        finally:
            self._lock.release()

    def update_ptrs_and_msgids(self, session):
        session.ui.mark(_('Updating high level indexes'))
        for offset in range(0, len(self.INDEX)):
            message = self.l2m(self.INDEX[offset])
            if len(message) == self.MSG_FIELDS_V2:
                self.MSGIDS[message[self.MSG_ID]] = offset
                for msg_ptr in message[self.MSG_PTRS].split(','):
                    self.PTRS[msg_ptr] = offset
            else:
                session.ui.warning(_('Bogus line: %s') % line)

    def try_decode(self, text, charset):
        for cs in (charset, 'iso-8859-1', 'utf-8'):
            if cs:
                try:
                    return text.decode(cs)
                except (UnicodeEncodeError, UnicodeDecodeError, LookupError):
                    pass
        return "".join(i for i in text if ord(i) < 128)

    def hdr(self, msg, name, value=None):
        try:
            if value is None and msg:
                # Security: RFC822 headers are not allowed to have (unencoded)
                # non-ascii characters in them, so we just strip them all out
                # before parsing.
                # FIXME: This is "safe", but can we be smarter/gentler?
                value = CleanText(msg[name], replace='_').clean
            # Note: decode_header does the wrong thing with "quoted" data.
            decoded = email.header.decode_header((value or ''
                                                  ).replace('"', ''))
            return (' '.join([self.try_decode(t[0], t[1]) for t in decoded])
                    ).replace('\r', ' ').replace('\t', ' ').replace('\n', ' ')
        except email.errors.HeaderParseError:
            return ''

    def _remove_location(self, session, msg_ptr):
        msg_idx_pos = self.PTRS[msg_ptr]
        del self.PTRS[msg_ptr]

        msg_info = self.get_msg_at_idx_pos(msg_idx_pos)
        msg_ptrs = [p for p in msg_info[self.MSG_PTRS].split(',')
                    if p != msg_ptr]

        msg_info[self.MSG_PTRS] = ','.join(msg_ptrs)
        self.set_msg_at_idx_pos(msg_idx_pos, msg_info)

    def _update_location(self, session, msg_idx_pos, msg_ptr):
        if 'rescan' in session.config.sys.debug:
            session.ui.debug('Moved? %s -> %s' % (msg_idx_pos, msg_ptr))

        msg_info = self.get_msg_at_idx_pos(msg_idx_pos)
        msg_ptrs = msg_info[self.MSG_PTRS].split(',')
        self.PTRS[msg_ptr] = msg_idx_pos

        # If message was seen in this mailbox before, update the location
        for i in range(0, len(msg_ptrs)):
            if msg_ptrs[i][:MBX_ID_LEN] == msg_ptr[:MBX_ID_LEN]:
                msg_ptrs[i] = msg_ptr
                msg_ptr = None
                break
        # Otherwise, this is a new mailbox, record this sighting as well!
        if msg_ptr:
            msg_ptrs.append(msg_ptr)

        msg_info[self.MSG_PTRS] = ','.join(msg_ptrs)
        self.set_msg_at_idx_pos(msg_idx_pos, msg_info)

    def _parse_date(self, date_hdr):
        """Parse a Date: or Received: header into a unix timestamp."""
        try:
            if ';' in date_hdr:
                date_hdr = date_hdr.split(';')[-1].strip()
            msg_ts = long(rfc822.mktime_tz(rfc822.parsedate_tz(date_hdr)))
            if (msg_ts > (time.time() + 24 * 3600)) or (msg_ts < 1):
                return None
            else:
                return msg_ts
        except (ValueError, TypeError, OverflowError):
            return None

    def _extract_date_ts(self, session, msg_mid, msg_id, msg, default):
        """Extract a date, sanity checking against the Received: headers."""
        hdrs = [self.hdr(msg, 'date')] + (msg.get_all('received') or [])
        dates = [self._parse_date(date_hdr) for date_hdr in hdrs]
        msg_ts = dates[0]
        nz_dates = sorted([d for d in dates if d])

        if nz_dates:
            a_week = 7 * 24 * 3600

            # Ideally, we compare with the date on the 2nd SMTP relay, as
            # the first will often be the same host as composed the mail
            # itself. If we don't have enough hops, just use the last one.
            #
            # We don't want to use a median or average, because if the
            # message bounces around lots of relays or gets resent, we
            # want to ignore the latter additions.
            #
            rcv_ts = nz_dates[min(len(nz_dates)-1, 2)]

            # Now, if everything is normal, the msg_ts will be at nz_dates[0]
            # and it won't be too far away from our reference date.
            if (msg_ts == nz_dates[0]) and (abs(msg_ts - rcv_ts) < a_week):
                # Note: Trivially true for len(nz_dates) in (1, 2)
                return msg_ts

            # Damn, dates are screwy!
            #
            # Maybe one of the SMTP servers has a wrong clock?  If the Date:
            # header falls within the range of all detected dates (plus a
            # week towards the past), still trust it.
            elif ((msg_ts >= (nz_dates[0]-a_week))
                    and (msg_ts <= nz_dates[-1])):
                return msg_ts

            # OK, Date: is insane, use one of the early Received: lines
            # instead.  We picked the 2nd one above, that should do.
            else:
                session.ui.warning(_('=%s/%s using Received: instead of Date:'
                                     ) % (msg_mid, msg_id))
                return rcv_ts
        else:
            # If the above fails, we assume the messages in the mailbox are in
            # chronological order and just add 1 second to the date of the last
            # message if date parsing fails for some reason.
            session.ui.warning(_('=%s/%s has a bogus date'
                                 ) % (msg_mid, msg_id))
            return (default or int(time.time()-1))

    def encode_msg_id(self, msg_id):
        return b64c(sha1b64(msg_id.strip()))

    def get_msg_id(self, msg, msg_ptr):
        raw_msg_id = self.hdr(msg, 'message-id')
        if not raw_msg_id:
            # Create a very long pseudo-msgid for messages without a
            # Message-ID. This was a very badly behaved mailer, so if
            # we create duplicates this way, we are probably only
            # losing spam. Even then the Received line should save us.
            raw_msg_id = ('\t'.join([self.hdr(msg, 'date'),
                                     self.hdr(msg, 'subject'),
                                     self.hdr(msg, 'received'),
                                     self.hdr(msg, 'from'),
                                     self.hdr(msg, 'to')])).strip()
        # Fall back to the msg_ptr if all else fails.
        if not raw_msg_id:
            print _('WARNING: No proper Message-ID for %s') % msg_ptr
        return self.encode_msg_id(raw_msg_id or msg_ptr)

    def scan_mailbox(self, session, mailbox_idx, mailbox_fn, mailbox_opener,
                     process_new=None, apply_tags=None, stop_after=None):
        try:
            self._lock.acquire()
            mbox = mailbox_opener(session, mailbox_idx)
            if mbox.editable:
                session.ui.mark(_('%s: Skipped: %s'
                                  ) % (mailbox_idx, mailbox_fn))
                return 0
            else:
                session.ui.mark(_('%s: Checking: %s'
                                  ) % (mailbox_idx, mailbox_fn))
                mbox.update_toc()
        except (IOError, OSError, NoSuchMailboxError), e:
            session.ui.mark(_('%s: Error opening: %s (%s)'
                              ) % (mailbox_idx, mailbox_fn, e))
            return -1
        finally:
            self._lock.release()

        if len(self.PTRS.keys()) == 0:
            self.update_ptrs_and_msgids(session)

        existing_ptrs = set()
        messages = sorted(mbox.keys())
        messages_md5 = md5_hex(str(messages))
        if messages_md5 == self._scanned.get(mailbox_idx, ''):
            return 0

        parse_fmt1 = _('%s: Reading your mail: %d%% (%d/%d message)')
        parse_fmtn = _('%s: Reading your mail: %d%% (%d/%d messages)')
        def parse_status(ui):
            n = len(messages)
            return ((n == 1) and parse_fmt1 or parse_fmtn
                    ) % (mailbox_idx, 100 * ui / n, ui, n)

        added = updated = 0
        last_date = long(time.time())
        for ui in range(0, len(messages)):
            if mailpile.util.QUITTING or self.interrupt:
                session.ui.debug(_('Rescan interrupted: %s') % self.interrupt)
                self.interrupt = None
                return -1
            if stop_after and added >= stop_after:
                break

            i = messages[ui]
            msg_ptr = mbox.get_msg_ptr(mailbox_idx, i)
            existing_ptrs.add(msg_ptr)
            if msg_ptr in self.PTRS:
                if (ui % 317) == 0:
                    session.ui.mark(parse_status(ui))
                    play_nice_with_threads()
                continue
            else:
                session.ui.mark(parse_status(ui))

            # Message new or modified, let's parse it.
            if 'rescan' in session.config.sys.debug:
                session.ui.debug('Reading message %s/%s' % (mailbox_idx, i))
            try:
                msg_fd = mbox.get_file(i)
                msg = ParseMessage(msg_fd,
                                   pgpmime=session.config.prefs.index_encrypted)
            except (IOError, OSError, ValueError, IndexError, KeyError):
                if session.config.sys.debug:
                    traceback.print_exc()
                session.ui.warning(('Reading message %s/%s FAILED, skipping'
                                    ) % (mailbox_idx, i))
                continue

            self._lock.acquire()
            try:
                msg_id = self.get_msg_id(msg, msg_ptr)
                if msg_id in self.MSGIDS:
                    self._update_location(session, self.MSGIDS[msg_id], msg_ptr)
                    updated += 1
                else:
                    msg_info = self._index_incoming_message(
                        session, msg_id, msg_ptr, msg_fd.tell(), msg,
                        last_date + 1, mailbox_idx, process_new, apply_tags)
                    last_date = long(msg_info[self.MSG_DATE], 36)
                    GlobalPostingList.Optimize(session, self,
                                               lazy=True, quick=True)
                    added += 1
            finally:
                self._lock.release()
                play_nice_with_threads()

        self._lock.acquire()
        try:
            for msg_ptr in self.PTRS.keys():
                if (msg_ptr[:MBX_ID_LEN] == mailbox_idx and
                        msg_ptr not in existing_ptrs):
                    self._remove_location(session, msg_ptr)
                    updated += 1
        finally:
            self._lock.release()
            play_nice_with_threads()

        if added or updated:
            mbox.save(session)
        self._scanned[mailbox_idx] = messages_md5
        short_fn = '/'.join(mailbox_fn.split('/')[-2:])
        session.ui.mark(_('%s: Indexed mailbox: ...%s (%d new, %d updated)'
                          ) % (mailbox_idx, short_fn, added, updated))
        return added

    def edit_msg_info(self, msg_info,
                      msg_mid=None, raw_msg_id=None, msg_id=None, msg_ts=None,
                      msg_from=None, msg_subject=None, msg_body=None,
                      msg_to=None, msg_cc=None, msg_tags=None):
        if msg_mid:
            msg_info[self.MSG_MID] = msg_mid
        if raw_msg_id:
            msg_info[self.MSG_ID] = self.encode_msg_id(raw_msg_id)
        if msg_id:
            msg_info[self.MSG_ID] = msg_id
        if msg_ts:
            msg_info[self.MSG_DATE] = b36(msg_ts)
        if msg_from:
            msg_info[self.MSG_FROM] = msg_from
        if msg_subject:
            msg_info[self.MSG_SUBJECT] = msg_subject
        if msg_body:
            msg_info[self.MSG_BODY] = msg_body
        if msg_to is not None:
            msg_info[self.MSG_TO] = self.compact_to_list(msg_to or [])
        if msg_cc is not None:
            msg_info[self.MSG_CC] = self.compact_to_list(msg_cc or [])
        if msg_tags is not None:
            msg_info[self.MSG_TAGS] = ','.join(msg_tags or [])
        return msg_info

    # FIXME: Finish merging this function with the one below it...
    def _extract_info_and_index(self, session, mailbox_idx,
                                msg_mid, msg_id,
                                msg_size, msg, default_date,
                                **index_kwargs):
        # Extract info from the message headers
        msg_ts = self._extract_date_ts(session, msg_mid, msg_id, msg,
                                       default_date)
        msg_to = ExtractEmails(self.hdr(msg, 'to'))
        msg_cc = (ExtractEmails(self.hdr(msg, 'cc')) +
                  ExtractEmails(self.hdr(msg, 'bcc')))
        msg_subj = self.hdr(msg, 'subject')

        filters = _plugins.get_filter_hooks([self.filter_keywords])
        kw, bi = self.index_message(session, msg_mid, msg_id,
                                    msg, msg_size, msg_ts,
                                    mailbox=mailbox_idx,
                                    compact=False,
                                    filter_hooks=filters,
                                    **index_kwargs)

        snippet_max = session.config.sys.snippet_max
        self.truncate_body_snippet(bi, max(0, snippet_max - len(msg_subj)))
        msg_body = self.encode_body(bi)

        tags = [k.split(':')[0] for k in kw
                if k.endswith(':in') or k.endswith(':tag')]

        return (msg_ts, msg_to, msg_cc, msg_subj, msg_body, tags)

    def _index_incoming_message(self, session,
                                msg_id, msg_ptr, msg_size, msg, default_date,
                                mailbox_idx, process_new, apply_tags):
        msg_mid = b36(len(self.INDEX))
        (msg_ts, msg_to, msg_cc, msg_subj, msg_body, tags
         ) = self._extract_info_and_index(session, mailbox_idx,
                                          msg_mid, msg_id, msg_size, msg,
                                          default_date,
                                          process_new=process_new,
                                          apply_tags=apply_tags,
                                          incoming=True)
        msg_idx_pos, msg_info = self.add_new_msg(
            msg_ptr, msg_id, msg_ts, self.hdr(msg, 'from'),
            msg_to, msg_cc, msg_size, msg_subj, msg_body,
            tags
        )
        self.set_conversation_ids(msg_info[self.MSG_MID], msg)
        return msg_info

    def index_email(self, session, email):
        # Extract info from the email object...
        msg = email.get_msg(pgpmime=session.config.prefs.index_encrypted)
        msg_mid = email.msg_mid()
        msg_info = email.get_msg_info()
        msg_size = email.get_msg_size()
        msg_id = msg_info[self.MSG_ID]
        mailbox_idx = msg_info[self.MSG_PTRS].split(',')[0][:MBX_ID_LEN]
        default_date = long(msg_info[self.MSG_DATE], 36)

        (msg_ts, msg_to, msg_cc, msg_subj, msg_body, tags
         ) = self._extract_info_and_index(session, mailbox_idx,
                                          msg_mid, msg_id, msg_size, msg,
                                          default_date,
                                          incoming=False)
        self.edit_msg_info(msg_info,
                           msg_from=self.hdr(msg, 'from'),
                           msg_to=msg_to,
                           msg_cc=msg_cc,
                           msg_subject=msg_subj,
                           msg_body=msg_body)

        self.set_msg_at_idx_pos(email.msg_idx_pos, msg_info)

        # Reset the internal tags on this message
        for tag_id in [t for t in msg_info[self.MSG_TAGS].split(',') if t]:
            tag = session.config.get_tag(tag_id)
            if tag and tag.slug.startswith('mp_'):
                self.remove_tag(session, tag_id, msg_idxs=[email.msg_idx_pos])

        # Add normal tags implied by a rescan
        for tag_id in tags:
            self.add_tag(session, tag_id, msg_idxs=[email.msg_idx_pos])

    def set_conversation_ids(self, msg_mid, msg, subject_threading=True):
        msg_thr_mid = None
        refs = set((self.hdr(msg, 'references') + ' ' +
                    self.hdr(msg, 'in-reply-to')
                    ).replace(',', ' ').strip().split())
        for ref_id in [self.encode_msg_id(r) for r in refs if r]:
            try:
                # Get conversation ID ...
                ref_idx_pos = self.MSGIDS[ref_id]
                msg_thr_mid = self.get_msg_at_idx_pos(ref_idx_pos
                                                      )[self.MSG_THREAD_MID]
                # Update root of conversation thread
                parent = self.get_msg_at_idx_pos(int(msg_thr_mid, 36))
                replies = parent[self.MSG_REPLIES][:-1].split(',')
                if msg_mid not in replies:
                    replies.append(msg_mid)
                parent[self.MSG_REPLIES] = ','.join(replies) + ','
                self.set_msg_at_idx_pos(int(msg_thr_mid, 36), parent)
                break
            except (KeyError, ValueError, IndexError):
                pass

        msg_idx_pos = int(msg_mid, 36)
        msg_info = self.get_msg_at_idx_pos(msg_idx_pos)

        if subject_threading and not msg_thr_mid and not refs:
            # Can we do plain GMail style subject-based threading?
            # FIXME: Is this too aggressive? Make configurable?
            subj = msg_info[self.MSG_SUBJECT].lower()
            subj = subj.replace('re: ', '').replace('fwd: ', '')
            date = long(msg_info[self.MSG_DATE], 36)
            if subj.strip() != '':
                for midx in reversed(range(max(0, msg_idx_pos - 250),
                                           msg_idx_pos)):
                    try:
                        m_info = self.get_msg_at_idx_pos(midx)
                        if m_info[self.MSG_SUBJECT
                                  ].lower().replace('re: ', '') == subj:
                            msg_thr_mid = m_info[self.MSG_THREAD_MID]
                            parent = self.get_msg_at_idx_pos(int(msg_thr_mid,
                                                                 36))
                            replies = parent[self.MSG_REPLIES][:-1].split(',')
                            if len(replies) < 100:
                                if msg_mid not in replies:
                                    replies.append(msg_mid)
                                parent[self.MSG_REPLIES] = (','.join(replies)
                                                            + ',')
                                self.set_msg_at_idx_pos(int(msg_thr_mid, 36),
                                                        parent)
                                break
                        if date - long(m_info[self.MSG_DATE],
                                       36) > 5 * 24 * 3600:
                            break
                    except (KeyError, ValueError, IndexError):
                        pass

        if not msg_thr_mid:
            # OK, we are our own conversation root.
            msg_thr_mid = msg_mid

        msg_info[self.MSG_THREAD_MID] = msg_thr_mid
        self.set_msg_at_idx_pos(msg_idx_pos, msg_info)

    def unthread_message(self, msg_mid):
        msg_idx_pos = int(msg_mid, 36)
        msg_info = self.get_msg_at_idx_pos(msg_idx_pos)
        par_idx_pos = int(msg_info[self.MSG_THREAD_MID], 36)

        if par_idx_pos == msg_idx_pos:
            # Message is head of thread, chop head off!
            thread = msg_info[self.MSG_REPLIES][:-1].split(',')
            msg_info[self.MSG_REPLIES] = ''
            if msg_mid in thread:
                thread.remove(msg_mid)
            if thread and thread[0]:
                head_mid = thread[0]
                head_idx_pos = int(head_mid, 36)
                head_info = self.get_msg_at_idx_pos(head_idx_pos)
                head_info[self.MSG_REPLIES] = ','.join(thread) + ','
                self.set_msg_at_idx_pos(head_idx_pos, head_info)
                for msg_mid in thread:
                    kid_idx_pos = int(thread[0], 36)
                    kid_info = self.get_msg_at_idx_pos(head_idx_pos)
                    kid_info[self.MSG_THREAD_MID] = head_mid
                    kid.set_msg_at_idx_pos(head_idx_pos, head_info)
        else:
            # Message is a reply, remove it from thread
            par_info = self.get_msg_at_idx_pos(par_idx_pos)
            thread = par_info[self.MSG_REPLIES][:-1].split(',')
            if msg_mid in thread:
                thread.remove(msg_mid)
                par_info[self.MSG_REPLIES] = ','.join(thread) + ','
                self.set_msg_at_idx_pos(par_idx_pos, par_info)

        msg_info[self.MSG_THREAD_MID] = msg_mid
        self.set_msg_at_idx_pos(msg_idx_pos, msg_info)

    def _add_email(self, email, name=None, eid=None):
        if eid is None:
            eid = len(self.EMAILS)
            self.EMAILS.append('')
        self.EMAILS[eid] = '%s (%s)' % (email, name or email)
        self.EMAIL_IDS[email.lower()] = eid
        # FIXME: This needs to get written out...
        return eid

    def update_email(self, email, name=None):
        eid = self.EMAIL_IDS.get(email.lower())
        return self._add_email(email, name=name, eid=eid)

    def compact_to_list(self, msg_to):
        eids = []
        for email in msg_to:
            eid = self.EMAIL_IDS.get(email.lower())
            if eid is None:
                eid = self._add_email(email)
            eids.append(eid)
        return ','.join([b36(e) for e in set(eids)])

    def expand_to_list(self, msg_info):
        eids = msg_info[self.MSG_TO]
        return [self.EMAILS[int(e, 36)] for e in eids.split(',') if e]

    def add_new_msg(self, msg_ptr, msg_id, msg_ts, msg_from,
                    msg_to, msg_cc, msg_bytes, msg_subject, msg_body,
                    tags):
        msg_idx_pos = len(self.INDEX)
        msg_mid = b36(msg_idx_pos)
        # FIXME: Refactor this to use edit_msg_info.
        msg_info = [
            msg_mid,                                     # Index ID
            msg_ptr,                                     # Location on disk
            msg_id,                                      # Message ID
            b36(msg_ts),                                 # Date as UTC timstamp
            msg_from,                                    # From:
            self.compact_to_list(msg_to or []),          # To:
            self.compact_to_list(msg_cc or []),          # Cc:
            b36(msg_bytes // 1024),                      # KB
            msg_subject,                                 # Subject:
            msg_body,                                    # Snippet etc.
            ','.join(tags),                              # Initial tags
            '',                                          # No replies for now
            msg_mid                                      # Conversation ID
        ]
        email, fn = ExtractEmailAndName(msg_from)
        if email and fn:
            self.update_email(email, name=fn)
        self.set_msg_at_idx_pos(msg_idx_pos, msg_info)
        return msg_idx_pos, msg_info

    def filter_keywords(self, session, msg_mid, msg, keywords, incoming=True):
        keywordmap = {}
        msg_idx_list = [msg_mid]
        for kw in keywords:
            keywordmap[unicode(kw)] = msg_idx_list

        import mailpile.plugins.tags
        ftypes = set(mailpile.plugins.tags.FILTER_TYPES)
        if not incoming:
            ftypes -= set(['incoming'])

        for (fid, terms, tags, comment, ftype
             ) in session.config.get_filters(types=ftypes):
            if (terms == '*' or
                    len(self.search(None, terms.split(),
                                    keywords=keywordmap)) > 0):
                for t in tags.split():
                    for fmt in ('%s:in', '%s:tag'):
                        kw = unicode(fmt % t[1:])
                        if kw in keywordmap:
                            del keywordmap[kw]
                    if t[0] != '-':
                        keywordmap[unicode('%s:in' % t[1:])] = msg_idx_list

        return set(keywordmap.keys())

    def apply_filters(self, session, filter_on, msg_mids=None, msg_idxs=None):
        if msg_idxs is None:
            msg_idxs = [int(mid, 36) for mid in msg_mids]
        if not msg_idxs:
            return
        for fid, trms, tags, c, t in session.config.get_filters(
                filter_on=filter_on):
            for t in tags.split():
                tag_id = t[1:].split(':')[0]
                if t[0] == '-':
                    self.remove_tag(session, tag_id, msg_idxs=set(msg_idxs))
                else:
                    self.add_tag(session, tag_id, msg_idxs=set(msg_idxs))

    def read_message(self, session, msg_mid, msg_id, msg, msg_size, msg_ts,
                     mailbox=None):
        keywords = []
        snippet_text = snippet_html = ''
        body_info = {}
        payload = [None]
        textparts = 0
        for part in msg.walk():
            textpart = payload[0] = None
            ctype = part.get_content_type()
            charset = part.get_content_charset() or 'iso-8859-1'

            def _loader(p):
                if payload[0] is None:
                    payload[0] = self.try_decode(p.get_payload(None, True),
                                                 charset)
                return payload[0]

            if ctype == 'text/plain':
                textpart = _loader(part)
                if textpart[:3] in ('<di', '<ht', '<p>', '<p '):
                    ctype = 'text/html'
                else:
                    textparts += 1

            if ctype == 'text/html':
                _loader(part)
                if len(payload[0]) > 3:
                    try:
                        textpart = lxml.html.fromstring(payload[0]
                                                        ).text_content()
                    except:
                        session.ui.warning(_('=%s/%s has bogus HTML.'
                                             ) % (msg_mid, msg_id))
                        textpart = payload[0]
                else:
                    textpart = payload[0]

            if 'pgp' in part.get_content_type().lower():
                keywords.append('pgp:has')
                keywords.append('crypto:has')

            att = part.get_filename()
            if att:
                att = self.try_decode(att, charset)
                # FIXME: These should be tags!
                keywords.append('attachment:has')
                keywords.extend([t + ':att' for t
                                 in re.findall(WORD_REGEXP, att.lower())])
                textpart = (textpart or '') + ' ' + att

            if textpart:
                # FIXME: Does this lowercase non-ASCII characters correctly?
                keywords.extend(re.findall(WORD_REGEXP, textpart.lower()))

                # NOTE: As a side effect here, the cryptostate plugin will
                #       add a 'crypto:has' keyword which we check for below
                #       before performing further processing.
                for kwe in _plugins.get_text_kw_extractors():
                    keywords.extend(kwe(self, msg, ctype, textpart))

                if ctype == 'text/plain':
                    snippet_text += textpart.strip() + '\n'
                else:
                    snippet_html += textpart.strip() + '\n'

            for extract in _plugins.get_data_kw_extractors():
                keywords.extend(extract(self, msg, ctype, att, part,
                                        lambda: _loader(part)))

        if textparts == 0:
            keywords.append('text:missing')

        if 'crypto:has' in keywords:
            e = Email(self, -1,
                      msg_parsed=msg,
                      msg_parsed_pgpmime=msg,
                      msg_info=self.BOGUS_METADATA[:])
            tree = e.get_message_tree(want=(e.WANT_MSG_TREE_PGP +
                                            ('text_parts', )))

            # Look for inline PGP parts, update our status if found
            e.evaluate_pgp(tree, decrypt=session.config.prefs.index_encrypted)
            msg.signature_info = tree['crypto']['signature']
            msg.encryption_info = tree['crypto']['encryption']

            # Index the contents, if configured to do so
            if session.config.prefs.index_encrypted:
                for text in [t['data'] for t in tree['text_parts']]:
                    keywords.extend(re.findall(WORD_REGEXP, text.lower()))
                    for kwe in _plugins.get_text_kw_extractors():
                        keywords.extend(kwe(self, msg, 'text/plain', text))

        keywords.append('%s:id' % msg_id)
        keywords.extend(re.findall(WORD_REGEXP,
                                   self.hdr(msg, 'subject').lower()))
        keywords.extend(re.findall(WORD_REGEXP,
                                   self.hdr(msg, 'from').lower()))
        if mailbox:
            keywords.append('%s:mailbox' % mailbox.lower())
        keywords.append('%s:hp' % HeaderPrint(msg))

        for key in msg.keys():
            key_lower = key.lower()
            if key_lower not in BORING_HEADERS:
                emails = ExtractEmails(self.hdr(msg, key).lower())
                words = set(re.findall(WORD_REGEXP,
                                       self.hdr(msg, key).lower()))
                words -= STOPLIST
                keywords.extend(['%s:%s' % (t, key_lower) for t in words])
                keywords.extend(['%s:%s' % (e, key_lower) for e in emails])
                keywords.extend(['%s:email' % e for e in emails])
                if 'list' in key_lower:
                    keywords.extend(['%s:list' % t for t in words])
        for key in EXPECTED_HEADERS:
            if not msg[key]:
                keywords.append('%s:missing' % key)

        for extract in _plugins.get_meta_kw_extractors():
            keywords.extend(extract(self, msg_mid, msg, msg_size, msg_ts))

        # FIXME: Allow plugins to augment the body_info

        if snippet_text.strip() != '':
            body_info['snippet'] = self.clean_snippet(snippet_text[:1024])
        else:
            body_info['snippet'] = self.clean_snippet(snippet_html[:1024])

        return (set(keywords) - STOPLIST), body_info

    # FIXME: Here it would be nice to recognize more boilerplate junk in
    #        more languages!
    SNIPPET_JUNK_RE = re.compile(
        '(\n[^\s]+ [^\n]+(@[^\n]+|(wrote|crit|schreib)):\s+>[^\n]+'
                                                          # On .. X wrote:
        '|\n>[^\n]*'                                      # Quoted content
        '|\n--[^\n]+BEGIN PGP[^\n]+--\s+(\S+:[^\n]+\n)*'  # PGP header
        ')+')
    SNIPPET_SPACE_RE = re.compile('\s+')

    @classmethod
    def clean_snippet(self, snippet):
        # FIXME: Can we do better than this? Probably!
        return (re.sub(self.SNIPPET_SPACE_RE, ' ',
                       re.sub(self.SNIPPET_JUNK_RE, '',
                              '\n' + snippet.replace('\r', '')
                              ).split('\n--')[0])
                ).strip()

    def index_message(self, session, msg_mid, msg_id, msg, msg_size, msg_ts,
                      mailbox=None, compact=True, filter_hooks=None,
                      process_new=None, apply_tags=None, incoming=False):
        keywords, snippet = self.read_message(session,
                                              msg_mid, msg_id, msg,
                                              msg_size, msg_ts,
                                              mailbox=mailbox)

        # Apply the defaults for this mail source / mailbox.
        if apply_tags:
            keywords |= set(['%s:in' % tid for tid in apply_tags])
        if process_new:
            process_new(msg, msg_ts, keywords, snippet)
        elif incoming:
            # This is the default behavior if the above are undefined.
            if process_new is None:
                keywords |= set(['%s:in' % tag._key for tag in
                                 self.config.get_tags(type='unread')])
            if apply_tags is None:
                keywords |= set(['%s:in' % tag._key for tag in
                                 self.config.get_tags(type='inbox')])

        for hook in filter_hooks or []:
            keywords = hook(session, msg_mid, msg, keywords,
                            incoming=incoming)

        for word in keywords:
            if (word.startswith('__') or
                    # Tags are now handled outside the posting lists
                    word.endswith(':tag') or word.endswith(':in')):
                continue
            try:
                GlobalPostingList.Append(session, word, [msg_mid],
                                         compact=compact)
            except UnicodeDecodeError:
                # FIXME: we just ignore garbage
                pass

        return keywords, snippet

    def get_msg_at_idx_pos(self, msg_idx):
        try:
            rv = self.CACHE.get(msg_idx)
            if rv is None:
                if len(self.CACHE) > 20000:
                    self.CACHE = {}
                rv = self.CACHE[msg_idx] = self.l2m(self.INDEX[msg_idx])
            return rv
        except IndexError:
            return self.BOGUS_METADATA[:]

    def set_msg_at_idx_pos(self, msg_idx, msg_info):
        if msg_idx < len(self.INDEX):
            self.INDEX[msg_idx] = self.m2l(msg_info)
            self.INDEX_THR[msg_idx] = int(msg_info[self.MSG_THREAD_MID], 36)
        elif msg_idx == len(self.INDEX):
            self.INDEX.append(self.m2l(msg_info))
            self.INDEX_THR.append(int(msg_info[self.MSG_THREAD_MID], 36))
        else:
            raise IndexError(_('%s is outside the index') % msg_idx)

        CachedSearchResultSet.DropCaches(msg_idxs=[msg_idx])
        self.MODIFIED.add(msg_idx)
        if msg_idx in self.CACHE:
            del(self.CACHE[msg_idx])

        for order in self.INDEX_SORT:
            # FIXME: This is where we should insert, not append.
            while msg_idx >= len(self.INDEX_SORT[order]):
                self.INDEX_SORT[order].append(msg_idx)

        self.MSGIDS[msg_info[self.MSG_ID]] = msg_idx
        for msg_ptr in msg_info[self.MSG_PTRS].split(','):
            self.PTRS[msg_ptr] = msg_idx
        self.update_msg_tags(msg_idx, msg_info)

    def get_conversation(self, msg_info=None, msg_idx=None):
        if not msg_info:
            msg_info = self.get_msg_at_idx_pos(msg_idx)
        conv_mid = msg_info[self.MSG_THREAD_MID]
        if conv_mid:
            return ([self.get_msg_at_idx_pos(int(conv_mid, 36))] +
                    self.get_replies(msg_idx=int(conv_mid, 36)))
        else:
            return [msg_info]

    def get_replies(self, msg_info=None, msg_idx=None):
        if not msg_info:
            msg_info = self.get_msg_at_idx_pos(msg_idx)
        return [self.get_msg_at_idx_pos(int(r, 36)) for r
                in msg_info[self.MSG_REPLIES].split(',') if r]

    def get_tags(self, msg_info=None, msg_idx=None):
        if not msg_info:
            msg_info = self.get_msg_at_idx_pos(msg_idx)
        return [r for r in msg_info[self.MSG_TAGS].split(',') if r]

    def add_tag(self, session, tag_id,
                msg_info=None, msg_idxs=None, conversation=False):
        if msg_info and msg_idxs is None:
            msg_idxs = set([int(msg_info[self.MSG_MID], 36)])
        else:
            msg_idxs = set(msg_idxs)
        if not msg_idxs:
            return
        CachedSearchResultSet.DropCaches()
        session.ui.mark(_n('Tagging %d message (%s)',
                           'Tagging %d messages (%s)',
                           len(msg_idxs)
                           ) % (len(msg_idxs), tag_id))
        for msg_idx in list(msg_idxs):
            if conversation:
                for reply in self.get_conversation(msg_idx=msg_idx):
                    if reply[self.MSG_MID]:
                        msg_idxs.add(int(reply[self.MSG_MID], 36))
        eids = set()
        for msg_idx in msg_idxs:
            if msg_idx >= 0 and msg_idx < len(self.INDEX):
                msg_info = self.get_msg_at_idx_pos(msg_idx)
                tags = set([r for r in msg_info[self.MSG_TAGS].split(',')
                            if r])
                tags.add(tag_id)
                msg_info[self.MSG_TAGS] = ','.join(list(tags))
                self.INDEX[msg_idx] = self.m2l(msg_info)
                self.MODIFIED.add(msg_idx)
                eids.add(msg_idx)
        if tag_id in self.TAGS:
            self.TAGS[tag_id] |= eids
        elif eids:
            self.TAGS[tag_id] = eids

    def remove_tag(self, session, tag_id,
                   msg_info=None, msg_idxs=None, conversation=False):
        if msg_info and msg_idxs is None:
            msg_idxs = set([int(msg_info[self.MSG_MID], 36)])
        else:
            msg_idxs = set(msg_idxs)
        if not msg_idxs:
            return
        CachedSearchResultSet.DropCaches()
        session.ui.mark(_n('Untagging conversation (%s)',
                           'Untagging conversations (%s)',
                           len(msg_idxs)
                           ) % (tag_id, ))
        for msg_idx in list(msg_idxs):
            if conversation:
                for reply in self.get_conversation(msg_idx=msg_idx):
                    if reply[self.MSG_MID]:
                        msg_idxs.add(int(reply[self.MSG_MID], 36))
        session.ui.mark(_n('Untagging %d message (%s)',
                           'Untagging %d messages (%s)',
                           len(msg_idxs)
                           ) % (len(msg_idxs), tag_id))
        eids = set()
        for msg_idx in msg_idxs:
            if msg_idx >= 0 and msg_idx < len(self.INDEX):
                msg_info = self.get_msg_at_idx_pos(msg_idx)
                tags = set([r for r in msg_info[self.MSG_TAGS].split(',')
                            if r])
                if tag_id in tags:
                    tags.remove(tag_id)
                    msg_info[self.MSG_TAGS] = ','.join(list(tags))
                    self.INDEX[msg_idx] = self.m2l(msg_info)
                    self.MODIFIED.add(msg_idx)
                eids.add(msg_idx)
        if tag_id in self.TAGS:
            self.TAGS[tag_id] -= eids

    def search_tag(self, session, term, hits, recursion=0):
        t = term.split(':', 1)
        tag_id, tag = t[1], self.config.get_tag(t[1])
        results = []
        if tag:
            tag_id = tag._key
            for subtag in self.config.get_tags(parent=tag_id):
                results.extend(hits('%s:in' % subtag._key))
            if tag.magic_terms and recursion < 5:
                results.extend(self.search(session, [tag.magic_terms],
                                           recursion=recursion+1).as_set())
        results.extend(hits('%s:in' % tag_id))
        return results

    def search(self, session, searchterms,
               keywords=None, order=None, recursion=0):
        # Stash the raw search terms, decide if this is cached or not
        raw_terms = searchterms[:]
        if keywords is None:
            srs = CachedSearchResultSet(self, raw_terms)
            if len(srs) > 0:
                return srs
        else:
            srs = SearchResultSet(self, raw_terms, [], [])

        # Choose how we are going to search
        if keywords is not None:
            def hits(term):
                return [int(h, 36) for h in keywords.get(term, [])]
        else:
            def hits(term):
                if term.endswith(':in'):
                    return self.TAGS.get(term.rsplit(':', 1)[0], [])
                else:
                    session.ui.mark(_('Searching for %s') % term)
                    return [int(h, 36) for h
                            in GlobalPostingList(session, term).hits()]

        # Replace some GMail-compatible terms with what we really use
        if 'tags' in self.config:
            for p in ('', '+', '-'):
                while p + 'is:unread' in searchterms:
                    where = searchterms.index(p + 'is:unread')
                    new = session.config.get_tags(type='unread')
                    if new:
                        searchterms[where] = p + 'in:%s' % new[0].slug
                for t in [term for term in searchterms
                          if term.startswith(p + 'tag:')]:
                    where = searchterms.index(t)
                    searchterms[where] = p + 'in:' + t.split(':', 1)[1]

        # If first term is a negative search, prepend an all:mail
        if searchterms and searchterms[0] and searchterms[0][0] == '-':
            searchterms[:0] = ['all:mail']

        r = []
        for term in searchterms:
            if term in STOPLIST:
                if session:
                    session.ui.warning(_('Ignoring common word: %s') % term)
                continue

            if term[0] in ('-', '+'):
                op = term[0]
                term = term[1:]
            else:
                op = None

            r.append((op, []))
            rt = r[-1][1]
            term = term.lower()

            if ':' in term:
                if term.startswith('body:'):
                    rt.extend(hits(term[5:]))
                elif term == 'all:mail':
                    rt.extend(range(0, len(self.INDEX)))
                elif term.startswith('in:'):
                    rt.extend(self.search_tag(session, term, hits,
                                              recursion=recursion))
                else:
                    t = term.split(':', 1)
                    fnc = _plugins.get_search_term(t[0])
                    if fnc:
                        rt.extend(fnc(self.config, self, term, hits))
                    else:
                        rt.extend(hits('%s:%s' % (t[1], t[0])))
            else:
                rt.extend(hits(term))

        if r:
            results = set(r[0][1])
            for (op, rt) in r[1:]:
                if op == '+':
                    results |= set(rt)
                elif op == '-':
                    results -= set(rt)
                else:
                    results &= set(rt)
            # Sometimes the scan gets aborted...
            if keywords is None:
                results -= set([len(self.INDEX)])
        else:
            results = set()

        # Unless we are searching for invisible things, remove them from
        # results by default.
        exclude = []
        order = order or (session and session.order) or 'flat-index'
        if (results and (keywords is None) and
                ('tags' in self.config) and
                (not session or 'all' not in order)):
            invisible = self.config.get_tags(flag_hides=True)
            exclude_terms = ['in:%s' % i._key for i in invisible]
            for tag in invisible:
                tid = tag._key
                for p in ('in:%s', '+in:%s', '-in:%s'):
                    if ((p % tid) in searchterms or
                            (p % tag.name) in searchterms or
                            (p % tag.slug) in searchterms):
                        exclude_terms = []
            if len(exclude_terms) > 1:
                exclude_terms = ([exclude_terms[0]] +
                                 ['+%s' % e for e in exclude_terms[1:]])
            # Recursing to pull the excluded terms from cache as well
            exclude = self.search(session, exclude_terms).as_set()

        srs.set_results(results, exclude)
        if session:
            session.ui.mark(_n('Found %d result ',
                               'Found %d results ',
                               len(results)) % (len(results), ) +
                            _n('%d suppressed',
                               '%d suppressed',
                               len(srs.excluded())
                               ) % (len(srs.excluded()), ))
        return srs

    def _order_freshness(self, pos):
        msg_info = self.get_msg_at_idx_pos(pos)
        ts = long(msg_info[self.MSG_DATE], 36)
        if ts > self._fresh_cutoff:
            for tid in msg_info[self.MSG_TAGS].split(','):
                if tid in self._fresh_tags:
                    return ts + self.FRESHNESS_SORT_BOOST
        return ts

    FRESHNESS_SORT_BOOST = (5 * 24 * 3600)
    CACHED_SORT_ORDERS = [
        ('freshness', True, _order_freshness),
        ('date', True,
         lambda s, k: long(s.get_msg_at_idx_pos(k)[s.MSG_DATE], 36)),
        # FIXME: The following are effectively disabled for now
        ('from', False,
         lambda s, k: s.get_msg_at_idx_pos(k)[s.MSG_FROM]),
        ('subject', False,
         lambda s, k: s.get_msg_at_idx_pos(k)[s.MSG_SUBJECT]),
    ]

    def cache_sort_orders(self, session, wanted=None):
        self._fresh_cutoff = time.time() - self.FRESHNESS_SORT_BOOST
        self._fresh_tags = [tag._key for tag in
                            session.config.get_tags(type='unread')]
        try:
            self._lock.acquire()
            keys = range(0, len(self.INDEX))
            if session:
                session.ui.mark(_n('Finding conversations (%d message)...',
                                   'Finding conversations (%d messages)...',
                                   len(keys)
                                   ) % len(keys))
            self.INDEX_THR = [
                int(self.get_msg_at_idx_pos(r)[self.MSG_THREAD_MID], 36)
                for r in keys]
            for order, by_default, sorter in self.CACHED_SORT_ORDERS:
                if (not by_default) and not (wanted and order in wanted):
                    continue
                if session:
                    session.ui.mark(_n('Sorting %d message by %s...',
                                       'Sorting %d messages by %s...',
                                       len(keys)
                                       ) % (len(keys), _(order)))

                play_nice_with_threads()
                o = keys[:]
                o.sort(key=lambda k: sorter(self, k))
                self.INDEX_SORT[order] = keys[:]
                self.INDEX_SORT[order+'_fwd'] = o

                play_nice_with_threads()
                for i in range(0, len(o)):
                    self.INDEX_SORT[order][o[i]] = i
        finally:
            self._lock.release()

    def sort_results(self, session, results, how):
        if not results:
            return

        count = len(results)
        session.ui.mark(_n('Sorting %d message by %s...',
                           'Sorting %d messages by %s...',
                           count
                           ) % (count, _(how)))
        try:
            if how.endswith('unsorted'):
                pass
            elif how.endswith('index'):
                results.sort()
            elif how.endswith('random'):
                now = time.time()
                results.sort(key=lambda k: sha1b64('%s%s' % (now, k)))
            else:
                did_sort = False
                for order in self.INDEX_SORT:
                    if how.endswith(order):
                        try:
                            results.sort(
                                key=self.INDEX_SORT[order].__getitem__)
                        except IndexError:
                            say = session.ui.error
                            if session.config.sys.debug:
                                traceback.print_exc()
                            for result in results:
                                if result >= len(self.INDEX) or result < 0:
                                    say(('Bogus message index: %s'
                                         ) % result)
                            say(_('Recovering from bogus sort, '
                                  'corrupt index?'))
                            say(_('Please tell team@mailpile.is !'))
                            clean_results = [r for r in results
                                             if r >= 0 and r < len(self.INDEX)]
                            clean_results.sort(
                                key=self.INDEX_SORT[order].__getitem__)
                            results[:] = clean_results
                        did_sort = True
                        break
                if not did_sort:
                    session.ui.warning(_('Unknown sort order: %s') % how)
                    return False
        except:
            if session.config.sys.debug:
                traceback.print_exc()
            session.ui.warning(_('Sort failed, sorting badly. Partial index?'))
            results.sort()

        if how.startswith('rev'):
            results.reverse()

        if 'flat' not in how:
            # This filters away all but the first result in each conversation.
            session.ui.mark(_('Collapsing conversations...'))
            seen, r2 = {}, []
            for i in range(0, len(results)):
                if self.INDEX_THR[results[i]] not in seen:
                    r2.append(results[i])
                    seen[self.INDEX_THR[results[i]]] = True
            results[:] = r2
            session.ui.mark(_n('Sorted %d message by %s',
                               'Sorted %d messages by %s',
                               count
                               ) % (count, how) +
                            _n('%d conversation',
                               '%d conversations',
                               len(results)
                               ) % (len(results), ))
        else:
            session.ui.mark(_n('Sorted %d message by %s',
                               'Sorted %d messages by %s',
                               count
                               ) % (count, _(how)))

        return True

########NEW FILE########
__FILENAME__ = smtp_client
import random
import smtplib
import socket
import subprocess
import sys
from gettext import ngettext as _n

from mailpile.config import ssl, socks
from mailpile.mailutils import CleanMessage, MessageAsString
from mailpile.eventlog import Event


def _AddSocksHooks(cls, SSL=False):

    class Socksified(cls):
        def _get_socket(self, host, port, timeout):
            print ('Creating socket -> %s:%s/%s using %s, SSL=%s'
                   ) % (host, port, timeout, self.socket, SSL)

            new_socket = self.socket()
            new_socket.connect((host, port))

            if SSL and ssl is not None:
                new_socket = ssl.wrap_socket(new_socket,
                                             self.keyfile, self.certfile)
                self.file = smtplib.SSLFakeFile(new_socket)

            return new_socket

        def connect(self, host='localhost', port=0, socket_cls=None):
            self.socket = socket_cls or socket.socket
            return cls.connect(self, host=host, port=port)

    return Socksified


class SMTP(_AddSocksHooks(smtplib.SMTP)):
    pass

if ssl is not None:
    class SMTP_SSL(_AddSocksHooks(smtplib.SMTP_SSL, SSL=True)):
        pass
else:
    SMTP_SSL = SMTP


def _RouteTuples(session, from_to_msg_ev_tuples):
    tuples = []
    for frm, to, msg, events in from_to_msg_ev_tuples:
        dest = {}
        for recipient in to:
            # If any of the events thinks this message has been delivered,
            # then don't try to send it again.
            frm_to = '>'.join([frm, recipient])
            for ev in (events or []):
                if ev.private_data.get(frm_to, False):
                    recipient = None
                    break
            if recipient:
                route = {"protocol": "",
                         "username": "",
                         "password": "",
                         "command": "",
                         "host": "",
                         "port": 25
                         }
                route.update(session.config.get_sendmail(frm, [recipient]))
                if route["command"]:
                    txtroute = "|%(command)s" % route
                else:
                    txtroute = "%(protocol)s://%(username)s:%(password)s@" \
                               + "%(host)s:%(port)d"
                    txtroute %= route

                dest[txtroute] = dest.get(txtroute, [])
                dest[txtroute].append(recipient)
        for route in dest:
            tuples.append((frm, route, dest[route], msg, events))
    return tuples


def SendMail(session, from_to_msg_ev_tuples):
    routes = _RouteTuples(session, from_to_msg_ev_tuples)

    # Randomize order of routes, so we don't always try the broken
    # one first. Any failure will bail out, but we do keep track of
    # our successes via. the event, so eventually everything sendable
    # should get sent.
    routes.sort(key=lambda k: random.randint(0, 10))

    # Update initial event state before we go through and start
    # trying to deliver stuff.
    for frm, sendmail, to, msg, events in routes:
        for ev in (events or []):
            for rcpt in to:
                ev.private_data['>'.join([frm, rcpt])] = False

    for frm, sendmail, to, msg, events in routes:
        for ev in events:
            ev.data['recipients'] = len(ev.private_data.keys())
            ev.data['delivered'] = len([k for k in ev.private_data
                                        if ev.private_data[k]])

    def mark(msg, events, log=True):
        for ev in events:
            ev.flags = Event.RUNNING
            ev.message = msg
            if log:
                session.config.event_log.log_event(ev)
        session.ui.mark(msg)

    # Do the actual delivering...
    for frm, sendmail, to, msg, events in routes:

        if 'sendmail' in session.config.sys.debug:
            sys.stderr.write(_('SendMail: from %s, to %s via %s\n'
                               ) % (frm, to, sendmail))
        sm_write = sm_close = lambda: True
        mark(_('Connecting to %s') % sendmail, events)

        if sendmail.startswith('|'):
            sendmail %= {"rcpt": ",".join(to)}
            cmd = sendmail[1:].strip().split()
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            sm_write = proc.stdin.write
            sm_close = proc.stdin.close
            sm_cleanup = lambda: proc.wait()
            # FIXME: Update session UI with progress info
            for ev in events:
                ev.data['proto'] = 'subprocess'
                ev.data['command'] = cmd[0]

        elif (sendmail.startswith('smtp:') or
              sendmail.startswith('smtorp:') or
              sendmail.startswith('smtpssl:') or
              sendmail.startswith('smtptls:')):
            proto = sendmail.split(':', 1)[0]
            host, port = sendmail.split(':', 1
                                        )[1].replace('/', '').rsplit(':', 1)
            smtp_ssl = proto in ('smtpssl', )  # FIXME: 'smtorp'
            if '@' in host:
                userpass, host = host.rsplit('@', 1)
                user, pwd = userpass.split(':', 1)
            else:
                user = pwd = None

            for ev in events:
                ev.data['proto'] = proto
                ev.data['host'] = host
                ev.data['auth'] = bool(user and pwd)

            if 'sendmail' in session.config.sys.debug:
                sys.stderr.write(_('SMTP connection to: %s:%s as %s@%s\n'
                                   ) % (host, port, user, pwd))

            server = smtp_ssl and SMTP_SSL() or SMTP()
            if proto == 'smtorp':
                server.connect(host, int(port),
                               socket_cls=session.config.get_tor_socket())
            else:
                server.connect(host, int(port))
            server.ehlo()
            if not smtp_ssl:
                # We always try to enable TLS, even if the user just requested
                # plain-text smtp.  But we only throw errors if the user asked
                # for encryption.
                try:
                    server.starttls()
                    server.ehlo()
                except:
                    if sendmail.startswith('smtptls'):
                        raise InsecureSmtpError()
            if user and pwd:
                server.login(user, pwd)

            server.mail(frm)
            for rcpt in to:
                server.rcpt(rcpt)
            server.docmd('DATA')

            def sender(data):
                for line in data.splitlines(1):
                    if line.startswith('.'):
                        server.send('.')
                    server.send(line)

            def closer():
                server.send('\r\n.\r\n')
                server.quit()

            sm_write = sender
            sm_close = closer
            sm_cleanup = lambda: True
        else:
            raise Exception(_('Invalid sendmail command/SMTP server: %s'
                              ) % sendmail)

        mark(_('Preparing message...'), events)
        msg_string = MessageAsString(CleanMessage(session.config, msg))
        total = len(msg_string)
        while msg_string:
            sm_write(msg_string[:20480])
            msg_string = msg_string[20480:]
            mark(('Sending message... (%d%%)'
                  ) % (100 * (total-len(msg_string))/total), events,
                 log=False)
        sm_close()
        sm_cleanup()
        for ev in events:
            for rcpt in to:
                ev.private_data['>'.join([frm, rcpt])] = True
            ev.data['bytes'] = total
            ev.data['delivered'] = len([k for k in ev.private_data
                                        if ev.private_data[k]])
        mark(_n('Message sent, %d byte',
                'Message sent, %d bytes',
                total
                ) % total, events)

########NEW FILE########
__FILENAME__ = ui
#
# This file contains the UserInteraction and Session classes.
#
# The Session encapsulates settings and command results, allowing commands
# to be chanined in an interactive environment.
#
# The UserInteraction classes log the progress and performance of individual
# operations and assist with rendering the results in various formats (text,
# HTML, JSON, etc.).
#
###############################################################################
import datetime
import os
import random
import re
import sys
import tempfile
import traceback
import json
import urllib
from collections import defaultdict
from gettext import gettext as _
from json import JSONEncoder
from jinja2 import TemplateError, TemplateSyntaxError, TemplateNotFound
from jinja2 import TemplatesNotFound, TemplateAssertionError, UndefinedError

import mailpile.commands
from mailpile.util import *
from mailpile.search import MailIndex


class SuppressHtmlOutput(Exception):
    pass


def default_dict(*args):
    d = defaultdict(str)
    for arg in args:
        d.update(arg)
    return d


class NoColors:
    """Dummy color constants"""
    NORMAL = ''
    BOLD = ''
    NONE = ''
    BLACK = ''
    RED = ''
    YELLOW = ''
    BLUE = ''
    FORMAT = "%s%s"
    RESET = ''

    def color(self, text, color='', weight=''):
        return '%s%s%s' % (self.FORMAT % (color, weight), text, self.RESET)


class ANSIColors(NoColors):
    """ANSI color constants"""
    NORMAL = ''
    BOLD = ';1'
    NONE = '0'
    BLACK = "30"
    RED = "31"
    YELLOW = "33"
    BLUE = "34"
    RESET = "\x1B[0m"
    FORMAT = "\x1B[%s%sm"


class Completer(object):
    """Readline autocompler"""
    DELIMS = ' \t\n`~!@#$%^&*()-=+[{]}\\|;:\'",<>?'

    def __init__(self, session):
        self.session = session

    def _available_opts(self, text):
        opts = ([s.SYNOPSIS[1] for s in mailpile.commands.COMMANDS] +
                [s.SYNOPSIS[2] for s in mailpile.commands.COMMANDS] +
                [t.name.lower() for t in self.session.config.tags.values()])
        return sorted([o for o in opts if o and o.startswith(text)])

    def _autocomplete(self, text, state):
        try:
            return self._available_opts(text)[state] + ' '
        except IndexError:
            return None

    def get_completer(self):
        return lambda t, s: self._autocomplete(t, s)


class UserInteraction:
    """Log the progress and performance of individual operations"""
    MAX_BUFFER_LEN = 150
    MAX_WIDTH = 79

    LOG_URGENT = 0
    LOG_RESULT = 5
    LOG_ERROR = 10
    LOG_NOTIFY = 20
    LOG_WARNING = 30
    LOG_PROGRESS = 40
    LOG_DEBUG = 50
    LOG_ALL = 99

    def __init__(self, config, log_parent=None):
        self.log_parent = log_parent
        self.log_buffer = []
        self.log_buffering = False
        self.log_level = self.LOG_ALL
        self.interactive = False
        self.time_tracking = [('Main', [])]
        self.time_elapsed = 0.0
        self.last_display = [self.LOG_PROGRESS, 0]
        self.render_mode = 'text'
        self.palette = NoColors()
        self.config = config
        self.html_variables = {
            'title': 'Mailpile',
            'name': 'Chelsea Manning',
            'csrf': '',
            'even_odd': 'odd',
            'mailpile_size': 0
        }

    # Logging
    def _debug_log(self, text, level, prefix=''):
        if 'log' in self.config.sys.debug:
            sys.stderr.write('%slog(%s): %s\n' % (prefix, level, text))

    def _display_log(self, text, level=LOG_URGENT):
        pad = ' ' * max(0, min(self.MAX_WIDTH,
                               self.MAX_WIDTH-len(unicode(text))))
        if self.last_display[0] not in (self.LOG_PROGRESS, ):
            sys.stderr.write('\n')

        c, w, clip = self.palette.NONE, self.palette.NORMAL, 2048
        if level == self.LOG_URGENT:
            c, w = self.palette.RED, self.palette.BOLD
        elif level == self.LOG_ERROR:
            c = self.palette.RED
        elif level == self.LOG_WARNING:
            c = self.palette.YELLOW
        elif level == self.LOG_PROGRESS:
            c, clip = self.palette.BLUE, 78

        sys.stderr.write('%s%s\r' % (
            self.palette.color(unicode(text[:clip]).encode('utf-8'),
                               color=c, weight=w), pad))

        if level == self.LOG_ERROR:
            sys.stderr.write('\n')
        self.last_display = [level, len(unicode(text))]

    def clear_log(self):
        self.log_buffer = []

    def flush_log(self):
        try:
            while len(self.log_buffer) > 0:
                level, message = self.log_buffer.pop(0)
                if level <= self.log_level:
                    self._display_log(message, level)
        except IndexError:
            pass

    def block(self):
        self._display_log('')
        self.log_buffering = True

    def unblock(self):
        self.log_buffering = False
        self.last_display = [self.LOG_RESULT, 0]
        self.flush_log()

    def log(self, level, message):
        if self.log_buffering:
            self.log_buffer.append((level, message))
            while len(self.log_buffer) > self.MAX_BUFFER_LEN:
                self.log_buffer[0:(self.MAX_BUFFER_LEN/10)] = []
        elif level <= self.log_level:
            self._display_log(message, level)

    def finish_command(self):
        pass

    def start_command(self):
        pass

    error = lambda self, msg: self.log(self.LOG_ERROR, msg)
    notify = lambda self, msg: self.log(self.LOG_NOTIFY, msg)
    warning = lambda self, msg: self.log(self.LOG_WARNING, msg)
    progress = lambda self, msg: self.log(self.LOG_PROGRESS, msg)
    debug = lambda self, msg: self.log(self.LOG_DEBUG, msg)

    # Progress indication and performance tracking
    times = property(lambda self: self.time_tracking[-1][1])

    def mark(self, action=None, percent=None):
        """Note that we are about to perform an action."""
        if not action:
            action = self.times and self.times[-1][1] or 'mark'
        self.progress(action)
        self.times.append((time.time(), action))

    def report_marks(self, quiet=False, details=False):
        t = self.times
        if t and t[0]:
            self.time_elapsed = elapsed = t[-1][0] - t[0][0]
            if not quiet:
                self.notify(_('Elapsed: %.3fs (%s)') % (elapsed, t[-1][1]))
                if details:
                    for i in range(0, len(self.times)-1):
                        e = t[i+1][0] - t[i][0]
                        self.notify(' -> %.3fs (%s)' % (e, t[i][1]))
            return elapsed
        return 0

    def reset_marks(self, mark=True, quiet=False, details=False):
        """This sequence of actions is complete."""
        if self.times and mark:
            self.mark()
        elapsed = self.report_marks(quiet=quiet, details=details)
        self.times[:] = []
        return elapsed

    def push_marks(self, subtask):
        """Start tracking a new sub-task."""
        self.time_tracking.append((subtask, []))

    def pop_marks(self, name=None, quiet=True):
        """Sub-task ended!"""
        elapsed = self.report_marks(quiet=quiet)
        if len(self.time_tracking) > 1:
            if not name or (self.time_tracking[-1][0] == name):
                self.time_tracking.pop(-1)
        return elapsed

    # Higher level command-related methods
    def _display_result(self, result):
        sys.stdout.write(unicode(result)+'\n')

    def start_command(self, cmd, args, kwargs):
        self.flush_log()
        self.push_marks(cmd)
        self.mark(('%s(%s)'
                   ) % (cmd, ', '.join((args or tuple()) +
                                       ('%s' % kwargs, ))))

    def finish_command(self, cmd):
        self.pop_marks(name=cmd)

    def display_result(self, result):
        """Render command result objects to the user"""
        self._display_log('', level=self.LOG_RESULT)
        if self.render_mode == 'json':
            return self._display_result(result.as_json())
        for suffix in ('css', 'html', 'js', 'rss', 'txt', 'xml'):
            if self.render_mode.endswith(suffix):
                if self.render_mode in (suffix, 'j' + suffix):
                    template = 'as.' + suffix
                else:
                    template = self.render_mode.replace('.j' + suffix,
                                                        '.' + suffix)
                return self._display_result(
                    result.as_template(suffix, template=template))
        return self._display_result(unicode(result))

    # Creating output files
    DEFAULT_DATA_NAME_FMT = '%(msg_mid)s.%(count)s_%(att_name)s.%(att_ext)s'
    DEFAULT_DATA_ATTRS = {
        'msg_mid': 'file',
        'mimetype': 'application/octet-stream',
        'att_name': 'unnamed',
        'att_ext': 'dat',
        'rand': '0000'
    }
    DEFAULT_DATA_EXTS = {
        # FIXME: Add more!
        'text/plain': 'txt',
        'text/html': 'html',
        'image/gif': 'gif',
        'image/jpeg': 'jpg',
        'image/png': 'png'
    }

    def _make_data_filename(self, name_fmt, attributes):
        return (name_fmt or self.DEFAULT_DATA_NAME_FMT) % attributes

    def _make_data_attributes(self, attributes={}):
        attrs = self.DEFAULT_DATA_ATTRS.copy()
        attrs.update(attributes)
        attrs['rand'] = '%4.4x' % random.randint(0, 0xffff)
        if attrs['att_ext'] == self.DEFAULT_DATA_ATTRS['att_ext']:
            if attrs['mimetype'] in self.DEFAULT_DATA_EXTS:
                attrs['att_ext'] = self.DEFAULT_DATA_EXTS[attrs['mimetype']]
        return attrs

    def open_for_data(self, name_fmt=None, attributes={}):
        filename = self._make_data_filename(
            name_fmt, self._make_data_attributes(attributes))
        return filename, open(filename, 'w')

    # Rendering helpers for templating and such
    def render_json(self, data):
        """Render data as JSON"""
        class NoFailEncoder(JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (list, dict, str, unicode,
                                    int, float, bool, type(None))):
                    return JSONEncoder.default(self, obj)
                return "COMPLEXBLOB"

        return json.dumps(data, indent=1, cls=NoFailEncoder, sort_keys=True)

    def _web_template(self, config, tpl_names, elems=None):
        env = config.jinja_env
        env.session = Session(config)
        env.session.ui = HttpUserInteraction(None, config)
        for fn in tpl_names:
            try:
                # FIXME(Security): Here we need to sanitize the file name
                #                  very strictly in case it somehow came
                #                  from user data.
                return env.get_template(fn)
            except (IOError, OSError, AttributeError), e:
                pass
        return None

    def render_web(self, cfg, tpl_names, data):
        """Render data as HTML"""
        alldata = default_dict(self.html_variables)
        alldata["config"] = cfg
        alldata.update(data)
        try:
            template = self._web_template(cfg, tpl_names)
            if template:
                return template.render(alldata)
            else:
                emsg = _("<h1>Template not found</h1>\n<p>%s</p><p>"
                         "<b>DATA:</b> %s</p>")
                tpl_esc_names = [escape_html(tn) for tn in tpl_names]
                return emsg % (' or '.join(tpl_esc_names),
                               escape_html('%s' % alldata))
        except (UndefinedError, ):
            emsg = _("<h1>Template error</h1>\n"
                     "<pre>%s</pre>\n<p>%s</p><p><b>DATA:</b> %s</p>")
            return emsg % (escape_html(traceback.format_exc()),
                           ' or '.join([escape_html(tn) for tn in tpl_names]),
                           escape_html('%.4096s' % alldata))
        except (TemplateNotFound, TemplatesNotFound), e:
            emsg = _("<h1>Template not found in %s</h1>\n"
                     "<b>%s</b><br/>"
                     "<div><hr><p><b>DATA:</b> %s</p></div>")
            return emsg % tuple([escape_html(unicode(v))
                                 for v in (e.name, e.message,
                                           '%.4096s' % alldata)])
        except (TemplateError, TemplateSyntaxError,
                TemplateAssertionError,), e:
            emsg = _("<h1>Template error in %s</h1>\n"
                     "Parsing template %s: <b>%s</b> on line %s<br/>"
                     "<div><xmp>%s</xmp><hr><p><b>DATA:</b> %s</p></div>")
            return emsg % tuple([escape_html(unicode(v))
                                 for v in (e.name, e.filename, e.message,
                                           e.lineno, e.source,
                                           '%.4096s' % alldata)])

    def edit_messages(self, session, emails):
        if not self.interactive:
            return False

        sep = '-' * 79 + '\n'
        edit_this = ('\n'+sep).join([e.get_editing_string() for e in emails])

        tf = tempfile.NamedTemporaryFile()
        tf.write(edit_this.encode('utf-8'))
        tf.flush()
        os.system('%s %s' % (os.getenv('VISUAL', default='vi'), tf.name))
        tf.seek(0, 0)
        edited = tf.read().decode('utf-8')
        tf.close()

        if edited == edit_this:
            return False

        updates = [t.strip() for t in edited.split(sep)]
        if len(updates) != len(emails):
            raise ValueError(_('Number of edit messages does not match!'))
        for i in range(0, len(updates)):
            emails[i].update_from_string(session, updates[i])
        return True


class HttpUserInteraction(UserInteraction):
    def __init__(self, request, *args, **kwargs):
        UserInteraction.__init__(self, *args, **kwargs)
        self.request = request
        self.logged = []
        self.results = []

    # Just buffer up rendered data
    def _display_log(self, text, level=UserInteraction.LOG_URGENT):
        self._debug_log(text, level, prefix='http/')
        self.logged.append((level, text))

    def _display_result(self, result):
        self.results.append(result)

    # Stream raw data to the client on open_for_data
    def open_for_data(self, name_fmt=None, attributes={}):
        return 'HTTP Client', RawHttpResponder(self.request, attributes)

    def _render_text_responses(self, config):
        if config.sys.debug:
            return '%s\n%s' % (
                '\n'.join([l[1] for l in self.logged]),
                ('\n%s\n' % ('=' * 79)).join(self.results)
            )
        else:
            return ('\n%s\n' % ('=' * 79)).join(self.results)

    def _render_single_response(self, config):
        if len(self.results) == 1:
            return self.results[0]
        if len(self.results) > 1:
            raise Exception(_('FIXME: Multiple results, OMG WTF'))
        return ""

    def render_response(self, config):
        if (self.render_mode == 'json' or
                self.render_mode.split('.')[-1] in ('jcss', 'jhtml', 'jjs',
                                                    'jrss', 'jtxt', 'jxml')):
            if len(self.results) == 1:
                return ('application/json', self.results[0])
            else:
                return ('application/json', '[%s]' % ','.join(self.results))
        elif self.render_mode.endswith('html'):
            return ('text/html', self._render_single_response(config))
        elif self.render_mode.endswith('js'):
            return ('text/javascript', self._render_single_response(config))
        elif self.render_mode.endswith('css'):
            return ('text/css', self._render_single_response(config))
        elif self.render_mode.endswith('txt'):
            return ('text/plain', self._render_single_response(config))
        elif self.render_mode.endswith('rss'):
            return ('application/rss+xml',
                    self._render_single_response(config))
        elif self.render_mode.endswith('xml'):
            return ('application/xml', self._render_single_response(config))
        else:
            return ('text/plain', self._render_text_responses(config))

    def edit_messages(self, session, emails):
        return False

    def print_filters(self, args):
        print args
        return args


class BackgroundInteraction(UserInteraction):
    def _display_log(self, text, level=UserInteraction.LOG_URGENT):
        self._debug_log(text, level, prefix='bg/')

    def edit_messages(self, session, emails):
        return False


class SilentInteraction(UserInteraction):
    def _display_log(self, text, level=UserInteraction.LOG_URGENT):
        self._debug_log(text, level, prefix='silent/')

    def _display_result(self, result):
        return result

    def edit_messages(self, session, emails):
        return False


class RawHttpResponder:

    def __init__(self, request, attributes={}):
        self.raised = False
        self.request = request
        #
        # FIXME: Security risks here, untrusted content may find its way into
        #                our raw HTTP headers etc.
        #
        mimetype = attributes.get('mimetype', 'application/octet-stream')
        filename = attributes.get('filename', 'attachment.dat'
                                  ).replace('"', '')
        disposition = attributes.get('disposition', 'attachment')
        length = attributes['length']
        request.send_http_response(200, 'OK')
        headers = [
            ('Content-Length', length),
        ]
        if disposition and filename:
            encfilename = urllib.quote(filename.encode("utf-8"))
            headers.append(('Content-Disposition',
                            '%s; filename*=UTF-8\'\'%s' % (disposition,
                                                           encfilename)))
        elif disposition:
            headers.append(('Content-Disposition', disposition))
        request.send_standard_headers(header_list=headers,
                                      mimetype=mimetype)

    def write(self, data):
        self.request.wfile.write(data)

    def close(self):
        if not self.raised:
            self.raised = True
            raise SuppressHtmlOutput()


class Session(object):

    def __init__(self, config):
        self.config = config
        self.interactive = False
        self.main = False
        self.order = None
        self.wait_lock = threading.Condition()
        self.results = []
        self.searched = []
        self.displayed = (0, 0)
        self.task_results = []
        self.ui = UserInteraction(config)

    def report_task_completed(self, name, result):
        self.wait_lock.acquire()
        self.task_results.append((name, result))
        self.wait_lock.notify_all()
        self.wait_lock.release()

    def report_task_failed(self, name):
        self.report_task_completed(name, None)

    def wait_for_task(self, wait_for, quiet=False):
        while True:
            self.wait_lock.acquire()
            for i in range(0, len(self.task_results)):
                if self.task_results[i][0] == wait_for:
                    tn, rv = self.task_results.pop(i)
                    self.wait_lock.release()
                    self.ui.reset_marks(quiet=quiet)
                    return rv

            self.wait_lock.wait()
            self.wait_lock.release()

    def error(self, message):
        self.ui.error(message)
        if not self.interactive:
            sys.exit(1)

########NEW FILE########
__FILENAME__ = urlmap
import cgi
from gettext import gettext as _
from urlparse import parse_qs, urlparse
from urllib import quote

from mailpile.commands import Command, COMMANDS
from mailpile.plugins import PluginManager
from mailpile.util import *


class BadMethodError(Exception):
    pass


class BadDataError(Exception):
    pass


class _FancyString(str):
    def __init__(self, *args):
        str.__init__(self, *args)
        self.filename = None


class UrlMap:
    """
    This class will map URLs/requests to Mailpile commands and back.

    The URL space is divided into three main classes:

       1. Versioned API endpoints
       2. Nice looking shortcuts to common data
       3. Shorthand paths to API endpoints (current version only)

    Depending on the endpoint, it is often possible to request alternate
    rendering templates or generate output in a variety of machine readable
    formats, such as JSON, XML or VCard. This is done by appending a
    psuedo-filename to the path. If ending in `.html`, the full filename is
    used to choose an alternate rendering template, for other extensions the
    name is ignored but the extension used to choose an output format.

    The default rendering for API endpoints is JSON, for other endpoints
    it is HTML. It is strongly recommended that only the versioned API
    endpoints be used for automation.
    """
    API_VERSIONS = (0, )

    def __init__(self, session=None, config=None):
        self.config = config or session.config
        self.session = session

    def _prefix_to_query(self, path, query_data, post_data):
        """
        Turns the /var/value prefix into a query-string argument.
        Returns a new path with the prefix stripped.

        >>> query_data = {}
        >>> path = urlmap._prefix_to_query('/var/val/stuff', query_data, {})
        >>> path, query_data
        ('/stuff', {'var': ['val']})
        """
        which, value, path = path[1:].split('/', 2)
        query_data[which] = [value]
        return '/' + path

    def _api_commands(self, method, strict=False):
        return [c for c in COMMANDS
                if ((not method)
                    or (c.SYNOPSIS[2] and (method in c.HTTP_CALLABLE
                                           or not strict)))]

    def _command(self, name,
                 args=None, query_data=None, post_data=None, method='GET'):
        """
        Return an instantiated mailpile.command object or raise a UsageError.

        >>> urlmap._command('output', args=['html'], method=False)
        <mailpile.commands.Output instance at 0x...>
        >>> urlmap._command('bogus')
        Traceback (most recent call last):
            ...
        UsageError: Unknown command: bogus
        >>> urlmap._command('message/update', method='GET')
        Traceback (most recent call last):
            ...
        BadMethodError: Invalid method (GET): message/update
        >>> urlmap._command('message/update', method='POST',
        ...                                   query_data={'evil': '1'})
        Traceback (most recent call last):
            ...
        BadDataError: Bad variable (evil): message/update
        >>> urlmap._command('search', args=['html'],
        ...                 query_data={'ui_': '1', 'q[]': 'foobar'})
        <mailpile.plugins.search.Search instance at 0x...>
        """
        try:
            match = [c for c in self._api_commands(method, strict=False)
                     if ((method and name == c.SYNOPSIS[2]) or
                         (not method and name == c.SYNOPSIS[1]))]
            if len(match) != 1:
                raise UsageError('Unknown command: %s' % name)
        except ValueError, e:
            raise UsageError(str(e))
        command = match[0]

        if method and (method not in command.HTTP_CALLABLE):
            raise BadMethodError('Invalid method (%s): %s' % (method, name))

        # FIXME: Move this somewhere smarter
        SPECIAL_VARS = ('csrf', 'arg')

        if command.HTTP_STRICT_VARS:
            for var in (post_data or []):
                var = var.replace('[]', '')
                if ((var not in command.HTTP_QUERY_VARS) and
                        (var not in command.HTTP_POST_VARS) and
                        (not var.startswith('ui_')) and
                        (var not in SPECIAL_VARS)):
                    raise BadDataError('Bad variable (%s): %s' % (var, name))
            for var in (query_data or []):
                var = var.replace('[]', '')
                if (var not in command.HTTP_QUERY_VARS and
                        (not var.startswith('ui_')) and
                        (var not in SPECIAL_VARS)):
                    raise BadDataError('Bad variable (%s): %s' % (var, name))

            ui_keys = [k for k in ((query_data or {}).keys() +
                                   (post_data or {}).keys())
                       if k.startswith('ui_')]
            copy_vars = ((ui_keys, query_data),
                         (ui_keys, post_data),
                         (command.HTTP_QUERY_VARS, query_data),
                         (command.HTTP_QUERY_VARS, post_data),
                         (command.HTTP_POST_VARS, post_data),
                         (['arg'], query_data))
        else:
            for var in command.HTTP_BANNED_VARS:
                var = var.replace('[]', '')
                if ((query_data and var in query_data) or
                        (post_data and var in post_data)):
                    raise BadDataError('Bad variable (%s): %s' % (var, name))

            copy_vars = (((query_data or {}).keys(), query_data),
                         ((post_data or {}).keys(), post_data),
                         (['arg'], query_data))

        data = {
            '_method': method
        }
        for vlist, src in copy_vars:
            for var in vlist:
                varBB = var + '[]'
                if src and (var in src or varBB in src):
                    sdata = (var in src) and src[var] or src.get(varBB, '')
                    if isinstance(sdata, cgi.FieldStorage):
                        data[var] = [_FancyString(sdata.value.decode('utf-8'))]
                        if hasattr(sdata, 'filename'):
                            data[var][0].filename = sdata.filename
                    else:
                        data[var] = [d.decode('utf-8') for d in sdata]

        return command(self.session, name, args, data=data)

    OUTPUT_SUFFIXES = ['.css', '.html', '.js',  '.json', '.rss', '.txt',
                       '.text', '.vcf', '.xml',
                       # These are the template-based ones which can
                       # be embedded in JSON.
                       '.jcss', '.jhtml', '.jjs', '.jrss', '.jtxt',
                       '.jxml']

    def _choose_output(self, path_parts, fmt='html'):
        """
        Return an output command based on the URL filename component.

        As a side-effect, the filename component will be removed from the
        path_parts list.
        >>> path_parts = '/a/b/as.json'.split('/')
        >>> command = urlmap._choose_output(path_parts)
        >>> (path_parts, command)
        (['', 'a', 'b'], <mailpile.commands.Output instance at 0x...>)

        If there is no filename part, the path_parts list is unchanged
        aside from stripping off the trailing empty string if present.
        >>> path_parts = '/a/b/'.split('/')
        >>> command = urlmap._choose_output(path_parts)
        >>> (path_parts, command)
        (['', 'a', 'b'], <mailpile.commands.Output instance at 0x...>)
        >>> path_parts = '/a/b'.split('/')
        >>> command = urlmap._choose_output(path_parts)
        Traceback (most recent call last):
          ...
        UsageError: Invalid output format: b
        """
        if len(path_parts) > 1 and not path_parts[-1]:
            path_parts.pop(-1)
        else:
            fn = path_parts.pop(-1)
            for suffix in self.OUTPUT_SUFFIXES:
                if suffix == '.' + fn:
                    return self._command('output', [suffix[1:]], method=False)
                if fn.endswith(suffix):
                    if fn == 'as' + suffix:
                        return self._command('output', [fn[3:]], method=False)
                    else:
                        # FIXME: We are passing user input here which may
                        #        have security implications.
                        return self._command('output', [fn], method=False)
            raise UsageError('Invalid output format: %s' % fn)
        return self._command('output', [fmt], method=False)

    def _map_root(self, request, path_parts, query_data, post_data):
        """Redirects to /in/inbox/ for now.  (FIXME)"""
        return [UrlRedirect(self.session, 'redirect', arg=['/in/inbox/'])]

    def _map_tag(self, request, path_parts, query_data, post_data):
        """
        Map /in/TAG_NAME/[@<pos>]/ to tag searches.

        >>> path = '/in/inbox/@20/as.json'
        >>> commands = urlmap._map_tag(request, path[1:].split('/'), {}, {})
        >>> commands
        [<mailpile.commands.Output...>, <mailpile.plugins.search.Search...>]
        >>> commands[0].args
        ('json',)
        >>> commands[1].args
        ('@20', 'in:inbox')
        """
        output = self._choose_output(path_parts)

        pos = None
        while path_parts and (path_parts[-1][0] in ('@', )):
            pos = path_parts[-1].startswith('@') and path_parts.pop(-1)

        tag_slug = '/'.join([p for p in path_parts[1:] if p])
        tag = self.config.get_tag(tag_slug)
        tag_search = [tag.search_terms % tag] if tag is not None else [""]
        if tag is not None and tag.search_order and 'order' not in query_data:
            query_data['order'] = [tag.search_order]

        if pos:
            tag_search[:0] = [pos]

        return [
            output,
            self._command('search',
                          args=tag_search,
                          query_data=query_data,
                          post_data=post_data)
        ]

    def _map_thread(self, request, path_parts, query_data, post_data):
        """
        Map /thread/METADATA_ID/... to view or extract commands.

        >>> path = '/thread/=123/'
        >>> commands = urlmap._map_thread(request, path[1:].split('/'), {}, {})
        >>> commands
        [<mailpile.commands.Output...>, <mailpile.plugins.search.View...>]
        >>> commands[1].args
        ('=123',)
        """
        message_mids, i = [], 1
        while path_parts[i].startswith('='):
            message_mids.append(path_parts[i])
            i += 1
        return [
            self._choose_output(path_parts),
            self._command('message',
                          args=message_mids,
                          query_data=query_data,
                          post_data=post_data)
        ]

    def _map_RESERVED(self, *args):
        """RESERVED FOR LATER."""

    def _map_api_command(self, method, path_parts,
                         query_data, post_data, fmt='html'):
        """Map a path to a command list, prefering the longest match.

        >>> urlmap._map_api_command('GET', ['message', 'draft', ''], {}, {})
        [<mailpile.commands.Output...>, <...Draft...>]
        >>> urlmap._map_api_command('POST', ['message', 'update', ''], {}, {})
        [<mailpile.commands.Output...>, <...Update...>]
        >>> urlmap._map_api_command('GET', ['message', 'update', ''], {}, {})
        Traceback (most recent call last):
            ...
        UsageError: Not available for GET: message/update
        """
        output = self._choose_output(path_parts, fmt=fmt)
        for bp in reversed(range(1, len(path_parts) + 1)):
            try:
                return [
                    output,
                    self._command('/'.join(path_parts[:bp]),
                                  args=path_parts[bp:],
                                  query_data=query_data,
                                  post_data=post_data,
                                  method=method)
                ]
            except UsageError:
                pass
            except BadMethodError:
                break
        raise UsageError('Not available for %s: %s' % (method,
                                                       '/'.join(path_parts)))

    MAP_API = 'api'
    MAP_PATHS = {
        '': _map_root,
        'in': _map_tag,
        'thread': _map_thread,
        'static': _map_RESERVED,
    }

    def map(self, request, method, path, query_data, post_data):
        """
        Convert an HTTP request to a list of mailpile.command objects.

        >>> urlmap.map(request, 'GET', '/in/inbox/', {}, {})
        [<mailpile.commands.Output...>, <mailpile.plugins.search.Search...>]

        The /api/ URL space is versioned and provides access to all the
        built-in commands. Requesting the wrong version or a bogus command
        throws exceptions.
        >>> urlmap.map(request, 'GET', '/api/999/bogus/', {}, {})
        Traceback (most recent call last):
            ...
        UsageError: Unknown API level: 999
        >>> urlmap.map(request, 'GET', '/api/0/bogus/', {}, {})
        Traceback (most recent call last):
            ...
        UsageError: Not available for GET: bogus

        The root currently just redirects to /in/inbox/:
        >>> r = urlmap.map(request, 'GET', '/', {}, {})[0]
        >>> r, r.args
        (<...UrlRedirect instance at 0x...>, ('/in/inbox/',))

        Tag searches have an /in/TAGNAME shorthand:
        >>> urlmap.map(request, 'GET', '/in/inbox/', {}, {})
        [<mailpile.commands.Output...>, <mailpile.plugins.search.Search...>]

        Thread shortcuts are /thread/METADATAID/:
        >>> urlmap.map(request, 'GET', '/thread/123/', {}, {})
        [<mailpile.commands.Output...>, <mailpile.plugins.search.View...>]

        Other commands use the command name as the first path component:
        >>> urlmap.map(request, 'GET', '/search/bjarni/', {}, {})
        [<mailpile.commands.Output...>, <mailpile.plugins.search.Search...>]
        >>> urlmap.map(request, 'GET', '/message/draft/=123/', {}, {})
        [<mailpile.commands.Output...>, <mailpile.plugins.compose.Draft...>]
        """

        # Check the API first.
        if path.startswith('/%s/' % self.MAP_API):
            path_parts = path.split('/')
            if int(path_parts[2]) not in self.API_VERSIONS:
                raise UsageError('Unknown API level: %s' % path_parts[2])
            return self._map_api_command(method, path_parts[3:],
                                         query_data, post_data, fmt='json')

        path_parts = path[1:].split('/')
        try:
            return self._map_api_command(method, path_parts[:],
                                         query_data, post_data)
        except UsageError:
            # Finally check for the registered shortcuts
            if path_parts[0] in self.MAP_PATHS:
                mapper = self.MAP_PATHS[path_parts[0]]
                return mapper(self, request, path_parts, query_data, post_data)
            raise

    def _url(self, url, output='', qs=''):
        if output and '.' not in output:
            output = 'as.%s' % output
        return ''.join([url, output, qs and '?' or '', qs])

    def url_thread(self, message_id, output=''):
        """Map a message to it's short-hand thread URL."""
        return self._url('/thread/=%s/' % message_id, output)

    def url_source(self, message_id, output=''):
        """Map a message to it's raw message source URL."""
        return self._url('/message/raw/=%s/as.text' % message_id, output)

    def url_edit(self, message_id, output=''):
        """Map a message to it's short-hand editing URL."""
        return self._url('/message/draft/=%s/' % message_id, output)

    def url_tag(self, tag_id, output=''):
        """
        Map a tag to it's short-hand URL.

        >>> urlmap.url_tag('Inbox')
        '/in/inbox/'
        >>> urlmap.url_tag('inbox', output='json')
        '/in/inbox/as.json'
        >>> urlmap.url_tag('1')
        '/in/inbox/'

        Unknown tags raise an exception.
        >>> urlmap.url_tag('99')
        Traceback (most recent call last):
            ...
        ValueError: Unknown tag: 99
        """
        try:
            tag = self.config.tags[tag_id]
            if tag is None:
                raise KeyError('oops')
        except (KeyError, IndexError):
            tag = [t for t in self.config.tags.values()
                   if t.slug == tag_id.lower()]
            tag = tag and tag[0]
        if tag:
            return self._url('/in/%s/' % tag.slug, output)
        raise ValueError('Unknown tag: %s' % tag_id)

    def url_sent(self, output=''):
        """Return the URL of the Sent tag"""
        return self.url_tag('Sent', output=output)

    def url_search(self, search_terms, tag=None, output=''):
        """
        Map a search query to it's short-hand URL, using Tag prefixes if
        there is exactly one tag in the search terms or we have tag context.

        >>> urlmap.url_search(['foo', 'bar', 'baz'])
        '/search/?q=foo%20bar%20baz'
        >>> urlmap.url_search(['foo', 'tag:Inbox', 'wtf'], output='json')
        '/in/inbox/as.json?q=foo%20wtf'
        >>> urlmap.url_search(['foo', 'in:Inbox', 'wtf'], output='json')
        '/in/inbox/as.json?q=foo%20wtf'
        >>> urlmap.url_search(['foo', 'in:Inbox', 'tag:New'], output='xml')
        '/search/as.xml?q=foo%20in%3AInbox%20tag%3ANew'
        >>> urlmap.url_search(['foo', 'tag:Inbox', 'in:New'], tag='Inbox')
        '/in/inbox/?q=foo%20in%3ANew'
        """
        tags = tag and [tag] or [t for t in search_terms
                                 if (t.startswith('tag:') or
                                     t.startswith('in:'))]
        if len(tags) == 1:
            prefix = self.url_tag(
                tags[0].replace('tag:', '').replace('in:', ''))
            search_terms = [t for t in search_terms
                            if (t not in tags and
                                t.replace('tag:', '').replace('in:', '')
                                not in tags)]
        else:
            prefix = '/search/'
        return self._url(prefix, output, 'q=' + quote(' '.join(search_terms)))

    @classmethod
    def canonical_url(self, cls):
        """Return the full versioned URL for a command"""
        return '/api/%s/%s/' % (cls.API_VERSION or self.API_VERSIONS[-1],
                                cls.SYNOPSIS[2])
    @classmethod
    def ui_url(self, cls):
        """Return the full user-facing URL for a command"""
        return '/%s/' % cls.SYNOPSIS[2]

    @classmethod
    def context_url(self, cls):
        """Return the UI context URL for a command"""
        return '/%s/' % (cls.UI_CONTEXT or cls.SYNOPSIS[2])

    def map_as_markdown(self):
        """Describe the current URL map as markdown"""

        api_version = self.API_VERSIONS[-1]
        text = []

        def cmds(method):
            return sorted([(c.SYNOPSIS[2], c)
                           for c in self._api_commands(method, strict=True)])

        text.extend([
            '# Mailpile URL map (autogenerated by %s)' % __file__,
            '',
            '\n'.join([line.strip() for line
                       in UrlMap.__doc__.strip().splitlines()[2:]]),
            '',
            '## The API paths (version=%s, JSON output)' % api_version,
            '',
        ])
        api = '/api/%s' % api_version
        for method in ('GET', 'POST', 'UPDATE', 'DELETE'):
            commands = cmds(method)
            if commands:
                text.extend([
                    '### %s%s' % (method, method == 'GET' and
                                  ' (also accept POST)' or ''),
                    '',
                ])
            commands.sort()
            for command in commands:
                cls = command[1]
                query_vars = cls.HTTP_QUERY_VARS
                pos_args = (cls.SYNOPSIS[3] and
                            unicode(cls.SYNOPSIS[3]).replace(' ', '/') or '')
                padding = ' ' * (18 - len(command[0]))
                newline = '\n' + ' ' * (len(api) + len(command[0]) + 6)
                if query_vars:
                    qs = '?' + '&'.join(['%s=[%s]' % (v, query_vars[v])
                                         for v in query_vars])
                else:
                    qs = ''
                if qs:
                    qs = '%s%s' % (padding, qs)
                if pos_args:
                    pos_args = '%s%s/' % (padding, pos_args)
                    if qs:
                        qs = newline + qs
                text.append('    %s%s%s' % (self.canonical_url(command[1]),
                                            pos_args, qs))
                if cls.HTTP_POST_VARS:
                    ps = '&'.join(['%s=[%s]' % (v, cls.HTTP_POST_VARS[v])
                                   for v in cls.HTTP_POST_VARS])
                    text.append('    ... POST only: %s' % ps)
            text.append('')
        text.extend([
            '',
            '## Pretty shortcuts (HTML output)',
            '',
        ])
        for path in sorted(self.MAP_PATHS.keys()):
            doc = self.MAP_PATHS[path].__doc__.strip().split('\n')[0]
            path = ('/%s/' % path).replace('//', '/')
            text.append('    %s %s %s' % (path, ' ' * (10 - len(path)), doc))
        text.extend([
            '',
            '## Default command URLs (HTML output)',
            '',
            '*These accept the same arguments as the API calls above.*',
            '',
        ])
        for command in sorted(list(set(cmds('GET') + cmds('POST')))):
            text.append('    /%s/' % (command[0], ))
        text.append('')
        return '\n'.join(text)

    def print_map_markdown(self):
        """Prints the current URL map to stdout in markdown"""
        print self.map_as_markdown()


class UrlRedirect(Command):
    """A stub command which just throws UrlRedirectException."""
    SYNOPSIS = (None, None, 'http/redirect', '<url>')
    HTTP_CALLABLE = ()

    def command(self):
        raise UrlRedirectException(self.args[0])


class UrlRedirectEdit(Command):
    """A stub command which just throws UrlRedirectException."""
    SYNOPSIS = (None, None, 'http/redirect/url_edit', '<mid>')
    HTTP_CALLABLE = ()

    def command(self):
        mid = self.args[0]
        raise UrlRedirectException(UrlMap(self.session).url_edit(mid))


class UrlRedirectThread(Command):
    """A stub command which just throws UrlRedirectException."""
    SYNOPSIS = (None, None, 'http/redirect/url_thread', '<mid>')
    HTTP_CALLABLE = ()

    def command(self):
        mid = self.args[0]
        raise UrlRedirectException(UrlMap(self.session).url_thread(mid))


class HelpUrlMap(Command):
    """Describe the current API and URL mapping"""
    SYNOPSIS = (None, 'help/urlmap', 'help/urlmap', None)

    class CommandResult(Command.CommandResult):
        def as_text(self):
            return self.result.get('urlmap', 'Missing')

        def as_html(self, *args, **kwargs):
            try:
                from markdown import markdown
                html = markdown(str(self.result['urlmap']))
            except:
                import traceback
                print traceback.format_exc()
                html = '<pre>%s</pre>' % escape_html(self.result['urlmap'])
            self.result['markdown'] = html
            return Command.CommandResult.as_html(self, *args, **kwargs)

    def command(self):
        return {'urlmap': UrlMap(self.session).map_as_markdown()}


plugin_manager = PluginManager(builtin=True)
if __name__ != "__main__":
    plugin_manager.register_commands(HelpUrlMap, UrlRedirect,
                                     UrlRedirectEdit, UrlRedirectThread)

else:
    # If run as a python script, print map and run doctests.
    import doctest
    import sys
    import mailpile.app
    import mailpile.config
    import mailpile.plugins
    import mailpile.defaults
    import mailpile.ui

    # Import all the default plugins
    from mailpile.plugins import *

    rules = mailpile.defaults.CONFIG_RULES
    config = mailpile.config.ConfigManager(rules=rules)
    config.tags.extend([
        {'name': 'New',   'slug': 'New'},
        {'name': 'Inbox', 'slug': 'Inbox'},
    ])
    session = mailpile.ui.Session(config)
    urlmap = UrlMap(session)
    urlmap.print_map_markdown()

    # For the UrlMap._map_api_command test
    plugin_manager.register_commands(UrlRedirect)

    results = doctest.testmod(optionflags=doctest.ELLIPSIS,
                              extraglobs={'urlmap': urlmap,
                                          'request': None})
    print
    print '<!-- %s -->' % (results, )
    if results.failed:
        sys.exit(1)

########NEW FILE########
__FILENAME__ = util
# coding: utf-8
#
# Misc. utility functions for Mailpile.
#
import cgi
import datetime
import hashlib
import locale
import re
import subprocess
import os
import sys
import string
import tempfile
import threading
import time
import StringIO
from distutils import spawn
from gettext import gettext as _
from mailpile.crypto.gpgi import GnuPG

try:
    from PIL import Image
except:
    Image = None


global WORD_REGEXP, STOPLIST, BORING_HEADERS, DEFAULT_PORT, QUITTING


QUITTING = False

DEFAULT_PORT = 33411

WORD_REGEXP = re.compile('[^\s!@#$%^&*\(\)_+=\{\}\[\]'
                         ':\"|;\'\\\<\>\?,\.\/\-]{2,}')

PROSE_REGEXP = re.compile('[^\s!@#$%^&*\(\)_+=\{\}\[\]'
                          ':\"|;\'\\\<\>\?,\.\/\-]{1,}')

STOPLIST = set(['an', 'and', 'are', 'as', 'at', 'by', 'for', 'from',
                'has', 'http', 'https', 'i', 'in', 'is', 'it',
                'mailto', 'me',
                'og', 'or', 're', 'so', 'the', 'to', 'was', 'you'])

BORING_HEADERS = ('received', 'date',
                  'content-type', 'content-disposition', 'mime-version',
                  'dkim-signature', 'domainkey-signature', 'received-spf')

EXPECTED_HEADERS = ('from', 'to', 'subject', 'date')

B64C_STRIP = '\n='

B64C_TRANSLATE = string.maketrans('/', '_')

B64W_TRANSLATE = string.maketrans('/+', '_-')

STRHASH_RE = re.compile('[^0-9a-z]+')

B36_ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'

RE_LONG_LINE_SPLITTER = re.compile('([^\n]{,72}) ')


class WorkerError(Exception):
    pass


class UsageError(Exception):
    pass


class AccessError(Exception):
    pass


class UrlRedirectException(Exception):
    """An exception indicating we need to redirecting to another URL."""
    def __init__(self, url):
        Exception.__init__(self, 'Should redirect to: %s' % url)
        self.url = url


def b64c(b):
    """
    Rewrite a base64 string:
        - Remove LF and = characters
        - Replace slashes by underscores

    >>> b64c("abc123456def")
    'abc123456def'
    >>> b64c("\\na/=b=c/")
    'a_bc_'
    >>> b64c("a+b+c+123+")
    'a+b+c+123+'
    """
    return string.translate(b, B64C_TRANSLATE, B64C_STRIP)


def b64w(b):
    """
    Rewrite a base64 string by replacing
    "+" by "-" (e.g. for URLs).

    >>> b64w("abc123456def")
    'abc123456def'
    >>> b64w("a+b+c+123+")
    'a-b-c-123-'
    """
    return string.translate(b, B64W_TRANSLATE, B64C_STRIP)


def escape_html(t):
    """
    Replace characters that have a special meaning in HTML
    by their entity equivalents. Return the replaced
    string.

    >>> escape_html("Hello, Goodbye.")
    'Hello, Goodbye.'
    >>> escape_html("Hello<>World")
    'Hello&lt;&gt;World'
    >>> escape_html("<&>")
    '&lt;&amp;&gt;'

    Keyword arguments:
    t -- The string to escape
    """
    return cgi.escape(t)


def _hash(cls, data):
    h = cls()
    for s in data:
        if isinstance(s, unicode):
            h.update(s.encode('utf-8'))
        else:
            h.update(s)
    return h


def sha1b64(*data):
    """
    Apply the SHA1 hash algorithm to a string
    and return the base64-encoded hash value

    >>> sha1b64("Hello")
    '9/+ei3uy4Jtwk1pdeF4MxdnQq/A=\\n'

    >>> sha1b64(u"Hello")
    '9/+ei3uy4Jtwk1pdeF4MxdnQq/A=\\n'

    Keyword arguments:
    s -- The string to hash
    """
    return _hash(hashlib.sha1, data).digest().encode('base64')


def sha512b64(*data):
    """
    Apply the SHA512 hash algorithm to a string
    and return the base64-encoded hash value

    >>> sha512b64("Hello")[:64]
    'NhX4DJ0pPtdAJof5SyLVjlKbjMeRb4+sf933+9WvTPd309eVp6AKFr9+fz+5Vh7p'
    >>> sha512b64(u"Hello")[:64]
    'NhX4DJ0pPtdAJof5SyLVjlKbjMeRb4+sf933+9WvTPd309eVp6AKFr9+fz+5Vh7p'

    Keyword arguments:
    s -- The string to hash
    """
    return _hash(hashlib.sha512, data).digest().encode('base64')


def md5_hex(*data):
    return _hash(hashlib.md5, data).hexdigest()


def strhash(s, length, obfuscate=None):
    """
    Create a hash of

    >>> strhash("Hello", 10)
    'hello9_+ei'
    >>> strhash("Goodbye", 5, obfuscate="mysalt")
    'voxpj'

    Keyword arguments:
    s -- The string to be hashed
    length -- The length of the hash to create.
                        Might be limited by the hash method
    obfuscate -- None to disable SHA512 obfuscation,
                             or a salt to append to the string
                             before hashing
    """
    if obfuscate:
        hashedStr = b64c(sha512b64(s, obfuscate).lower())
    else:  # Don't obfuscate
        hashedStr = re.sub(STRHASH_RE, '', s.lower())[:(length - 4)]
        while len(hashedStr) < length:
            hashedStr += b64c(sha1b64(s)).lower()
    return hashedStr[:length]


def b36(number):
    """
    Convert a number to base36

    >>> b36(2701)
    '231'
    >>> b36(12345)
    '9IX'
    >>> b36(None)
    '0'

    Keyword arguments:
    number -- An integer to convert to base36
    """
    if not number or number < 0:
        return B36_ALPHABET[0]
    base36 = []
    while number:
        number, i = divmod(number, 36)
        base36.append(B36_ALPHABET[i])
    return ''.join(reversed(base36))


def split_long_lines(text):
    """
    Split long lines of text into shorter ones, ignoring ascii art.

    >>> test_string = (('abcd efgh ijkl mnop ' + ('q' * 72) + ' ') * 2)[:-1]
    >>> print split_long_lines(test_string)
    abcd efgh ijkl mnop
    qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq
    abcd efgh ijkl mnop
    qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq

    >>> print split_long_lines('> ' + ('q' * 72))
    > qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq

    The function should be stable:

    >>> split_long_lines(test_string) == split_long_lines(
    ...                                    split_long_lines(test_string))
    True
    """
    lines = text.splitlines()
    for i in range(0, len(lines)):
        buffered, done = [], False
        while (not done and
               len(lines[i]) > 72 and
               re.match(PROSE_REGEXP, lines[i])):
            n = re.sub(RE_LONG_LINE_SPLITTER, '\\1\n', lines[i], 1
                       ).split('\n')
            if len(n) == 1:
                done = True
            else:
                buffered.append(n[0])
                lines[i] = n[1]
        if buffered:
            lines[i] = '\n'.join(buffered + [lines[i]])
    return '\n'.join(lines)


def elapsed_datetime(timestamp):
    """
    Return "X days ago" style relative dates for recent dates.
    """
    ts = datetime.datetime.fromtimestamp(timestamp)
    elapsed = datetime.datetime.today() - ts
    days_ago = elapsed.days
    hours_ago, remainder = divmod(elapsed.seconds, 3600)
    minutes_ago, seconds_ago = divmod(remainder, 60)

    if days_ago < 1:
        if hours_ago < 1:
            if minutes_ago < 3:
                return _('now')
            elif minutes_ago >= 3:
                return _('%d mins') % minutes_ago
        elif hours_ago < 2:
            return _('%d hour') % hours_ago
        else:
            return _('%d hours') % hours_ago
    elif days_ago < 2:
        return _('%d day') % days_ago
    elif days_ago < 7:
        return _('%d days') % days_ago
    elif days_ago < 366:
        return ts.strftime("%b %d")
    else:
        return ts.strftime("%b %d %Y")


def friendly_datetime(timestamp):
    date = datetime.date.fromtimestamp(timestamp)
    return date.strftime("%b %d, %Y")


def friendly_time(timestamp):
    date = datetime.datetime.fromtimestamp(timestamp)
    return date.strftime("%H:%M")


def friendly_number(number, base=1000, decimals=0, suffix='',
                    powers=['', 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']):
    """
    Format a number as friendly text, using common suffixes.

    >>> friendly_number(102)
    '102'
    >>> friendly_number(10240)
    '10k'
    >>> friendly_number(12341234, decimals=1)
    '12.3M'
    >>> friendly_number(1024000000, base=1024, suffix='iB')
    '976MiB'
    """
    count = 0
    number = float(number)
    while number > base and count < len(powers):
        number /= base
        count += 1
    if decimals:
        fmt = '%%.%df%%s%%s' % decimals
    else:
        fmt = '%d%s%s'
    return fmt % (number, powers[count], suffix)


GPG_BEGIN_MESSAGE = '-----BEGIN PGP MESSAGE'
GPG_END_MESSAGE = '-----END PGP MESSAGE'


def decrypt_gpg(lines, fd):
    for line in fd:
        lines.append(line)
        if line.startswith(GPG_END_MESSAGE):
            break

    gpg = GnuPG()
    _, encryption_info, plaintext = gpg.decrypt(''.join(lines), as_lines=True)

    if encryption_info['status'] != 'decrypted':
        gpg_exec = spawn.find_executable('gpg')
        gpg_version = gpg.version()
        raise AccessError("GPG (version: %s, location: %s) was unable "
                          "to decrypt the data: %s"
                          % (gpg_version, gpg_exec, encryption_info['status']))

    return plaintext


def decrypt_and_parse_lines(fd, parser, config, newlines=False):
    import mailpile.crypto.symencrypt as symencrypt
    if not newlines:
        _parser = lambda l: parser(l.rstrip('\r\n'))
    else:
        _parser = parser
    size = 0
    while True:
        line = fd.readline(102400)
        if line == '':
            break
        size += len(line)
        if line.startswith(GPG_BEGIN_MESSAGE):
            for line in decrypt_gpg([line], fd):
                _parser(line.decode('utf-8'))
        elif line.startswith(symencrypt.SymmetricEncrypter.BEGIN_DATA):
            if not config or not config.prefs.obfuscate_index:
                raise ValueError(_("Symmetric decryption is not available "
                                   "without config and key."))
            for line in symencrypt.SymmetricEncrypter(
                    config.prefs.obfuscate_index).decrypt_fd([line], fd):
                _parser(line.decode('utf-8'))
        else:
            _parser(line.decode('utf-8'))
    return size


def backup_file(filename, backups=5, min_age_delta=0):
    if os.path.exists(filename):
        if os.stat(filename).st_mtime >= time.time() - min_age_delta:
            return

        for ver in reversed(range(1, backups)):
            bf = '%s.%d' % (filename, ver)
            if os.path.exists(bf):
                nbf = '%s.%d' % (filename, ver+1)
                if os.path.exists(nbf):
                    os.remove(nbf)
                os.rename(bf, nbf)
        os.rename(filename, '%s.1' % filename)


class GpgWriter(object):
    def __init__(self, gpg):
        self.fd = gpg.stdin
        self.gpg = gpg

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def write(self, data):
        self.fd.write(data)

    def close(self):
        self.fd.close()
        self.gpg.wait()


def gpg_open(filename, recipient, mode):
    fd = open(filename, mode)
    if recipient and ('a' in mode or 'w' in mode):
        gpg = subprocess.Popen(['gpg', '--batch', '-aer', recipient],
                               stdin=subprocess.PIPE,
                               stdout=fd)
        return GpgWriter(gpg)
    return fd


def dict_merge(*dicts):
    """
    Merge one or more dicts into one.

    >>> d = dict_merge({'a': 'A'}, {'b': 'B'}, {'c': 'C'})
    >>> sorted(d.keys()), sorted(d.values())
    (['a', 'b', 'c'], ['A', 'B', 'C'])
    """
    final = {}
    for d in dicts:
        final.update(d)
    return final


def play_nice_with_threads():
    """
    Long-running batch jobs should call this now and then to pause
    their activities if there are other threads that would like to
    run. This is a bit of a hack!
    """
    delay = max(0, 0.01 * (threading.activeCount() - 2))
    if delay:
        time.sleep(delay)
    return delay


def thumbnail(fileobj, output_fd, height=None, width=None):
    """
    Generates a thumbnail image , which should be a file,
    StringIO, or string, containing a PIL-supported image.
    FIXME: Failure modes unmanaged.

    Keyword arguments:
    fileobj -- Either a StringIO instance, a file object or
                         a string (containing the image) to
                         read the source image from
    output_fd -- A file object or filename, or StringIO to
    """
    if not Image:
        # If we don't have PIL, we just return the supplied filename in
        # the hopes that somebody had the good sense to extract the
        # right attachment to that filename...
        return None

    # Ensure the source image is either a file-like object or a StringIO
    if (not isinstance(fileobj, (file, StringIO.StringIO))):
        fileobj = StringIO.StringIO(fileobj)

    image = Image.open(fileobj)

    # defining the size
    if height is None and width is None:
        raise Exception("Must supply width or height!")
    # If only one coordinate is given, calculate the
    # missing one in order to make the thumbnail
    # have the same proportions as the source img
    if height and not width:
        x = height
        y = int((float(height) / image.size[0]) * image.size[1])
    elif width and not height:
        y = width
        x = int((float(width) / image.size[1]) * image.size[0])
    else:  # We have both sizes
        y = width
        x = height
    try:
        image.thumbnail([x, y], Image.ANTIALIAS)
    except IOError:
        return None

    # If saving an optimized image fails, save it unoptimized
    # Keep the format (png, jpg) of the source image
    try:
        image.save(output_fd, format=image.format, quality=90, optimize=1)
    except:
        image.save(output_fd, format=image.format, quality=90)

    return image


class CleanText:
    """
    This is a helper class for aggressively cleaning text, dumbing it
    down to just ASCII and optionally forbidding some characters.

    >>> CleanText(u'clean up\\xfe', banned='up ').clean
    'clean'
    >>> CleanText(u'clean\\xfe', replace='_').clean
    'clean_'
    >>> CleanText(u'clean\\t').clean
    'clean\\t'
    >>> str(CleanText(u'c:\\\\l/e.an', banned=CleanText.FS))
    'clean'
    >>> CleanText(u'c_(l e$ a) n!', banned=CleanText.NONALNUM).clean
    'clean'
    """
    FS = ':/.\'\"\\'
    CRLF = '\r\n'
    WHITESPACE = '\r\n\t '
    NONALNUM = ''.join([chr(c) for c in (set(range(32, 127)) -
                                         set(range(ord('0'), ord('9') + 1)) -
                                         set(range(ord('a'), ord('z') + 1)) -
                                         set(range(ord('A'), ord('Z') + 1)))])
    NONDNS = ''.join([chr(c) for c in (set(range(32, 127)) -
                                       set(range(ord('0'), ord('9') + 1)) -
                                       set(range(ord('a'), ord('z') + 1)) -
                                       set(range(ord('A'), ord('Z') + 1)) -
                                       set([ord('-'), ord('_'), ord('.')]))])
    NONVARS = ''.join([chr(c) for c in (set(range(32, 127)) -
                                        set(range(ord('0'), ord('9') + 1)) -
                                        set(range(ord('a'), ord('z') + 1)) -
                                        set([ord('_')]))])

    def __init__(self, text, banned='', replace=''):
        self.clean = str("".join([i if (((ord(i) > 31 and ord(i) < 127) or
                                         (i in self.WHITESPACE)) and
                                        i not in banned) else replace
                                  for i in (text or '')]))

    def __str__(self):
        return str(self.clean)

    def __unicode__(self):
        return unicode(self.clean)


def HideBinary(text):
    try:
        text.decode('utf-8')
        return text
    except UnicodeDecodeError:
        return '[BINARY DATA, %d BYTES]' % len(text)


class DebugFileWrapper(object):
    def __init__(self, dbg, fd):
        self.fd = fd
        self.dbg = dbg

    def __getattribute__(self, name):
        if name in ('fd', 'dbg', 'write', 'flush', 'close'):
            return object.__getattribute__(self, name)
        else:
            self.dbg.write('==(%d.%s)\n' % (self.fd.fileno(), name))
            return object.__getattribute__(self.fd, name)

    def write(self, data, *args, **kwargs):
        self.dbg.write('<=(%d.write)= %s\n' % (self.fd.fileno(),
                                               HideBinary(data).rstrip()))
        return self.fd.write(data, *args, **kwargs)

    def flush(self, *args, **kwargs):
        self.dbg.write('==(%d.flush)\n' % self.fd.fileno())
        return self.fd.flush(*args, **kwargs)

    def close(self, *args, **kwargs):
        self.dbg.write('==(%d.close)\n' % self.fd.fileno())
        return self.fd.close(*args, **kwargs)


# If 'python util.py' is executed, start the doctest unittest
if __name__ == "__main__":
    import doctest
    import sys
    if doctest.testmod().failed:
        sys.exit(1)

########NEW FILE########
__FILENAME__ = vcard
import random
from gettext import gettext as _

import mailpile.util
from mailpile.util import *


class VCardLine(dict):
    """
    This class represents a single line in a VCard file. It knows how
    to parse the most common "structured" lines into attributes and
    values and also convert a name, attributes and value into a properly
    encoded/escaped VCard line.

    For specific values, the object can be initialized directly.
    >>> vcl = VCardLine(name='name', value='The Dude', pref=None)
    >>> vcl.as_vcardline()
    'NAME;PREF:The Dude'

    Alternately, the name and value attributes can be set after the fact.
    >>> vcl.name = 'FN'
    >>> vcl.value = 'Lebowski'
    >>> vcl.attrs = []
    >>> vcl.as_vcardline()
    'FN:Lebowski'

    The object mostly behaves like a read-only dict.
    >>> print vcl
    {u'fn': u'Lebowski'}
    >>> print vcl.value
    Lebowski

    VCardLine objects can also be initialized by passing in a line of VCard
    data, which will then be parsed:
    >>> vcl = VCardLine('FN;TYPE=Nickname:Bjarni')
    >>> vcl.name
    u'fn'
    >>> vcl.value
    u'Bjarni'
    >>> vcl.get('type')
    u'Nickname'

    Note that the as_vcardline() method may return more than one actual line
    of text, as RFC6350 mandates that lines over 75 characters be wrapped:
    >>> print VCardLine(name='bogus', value=('B' * 100)+'C').as_vcardline()
    BOGUS:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB
     BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBC
    """
    QUOTE_MAP = {
        "\\": "\\\\",
        ",": "\\,",
        ";": "\\;",
        "\n": "\\n",
    }
    QUOTE_RMAP = dict([(v, k) for k, v in QUOTE_MAP.iteritems()])

    def __init__(self, line=None, name=None, value=None, **attrs):
        self._name = name and unicode(name).lower() or None
        self._value = unicode(value)
        self._attrs = []
        self._line_id = 0
        for k in attrs:
            self._attrs.append((k.lower(), attrs[k]))
        if line is not None:
            self.parse(line)
        else:
            self._update_dict()

    def set_line_id(self, value):
        self._line_id = value
        self._update_dict()

    line_id = property(lambda self: self._line_id, set_line_id)

    def set_name(self, value):
        self._name = unicode(value).lower()
        self._update_dict()

    def set_value(self, value):
        self._value = unicode(value)
        self._update_dict()

    def set_attrs(self, value):
        self._attrs = value
        self._update_dict()

    def set_attr(self, attr, value):
        try:
            for av in self._attrs:
                if av[0] == attr:
                    nav = (av[0], value)
                    av = nav
                    return
            self._attrs.append((attr, value))
        finally:
            self._update_dict()

    name = property(lambda self: self._name,
                    lambda self, v: self.set_name(v))

    value = property(lambda self: self._value,
                     lambda self, v: self.set_value(v))

    attrs = property(lambda self: self._attrs,
                     lambda self, v: self.set_attrs(v))

    def parse(self, line):
        self._name, self._attrs, self._value = self.ParseLine(line)
        self._update_dict()

    def _update_dict(self):
        for key in self.keys():
            dict.__delitem__(self, key)
        dict.update(self, dict(reversed(self._attrs)))
        if self.name:
            dict.__setitem__(self, self._name, self._value)
        if self._line_id:
            dict.__setitem__(self, 'line_id', self._line_id)

    def __delitem__(self, *args, **kwargs):
        raise ValueError('This dict is read-only')

    def __setitem__(self, *args, **kwargs):
        raise ValueError('This dict is read-only')

    def update(self, *args, **kwargs):
        raise ValueError('This dict is read-only')

    def as_vcardline(self):
        key = self.Quote(self._name.upper())
        for k, v in self._attrs:
            k = k.upper()
            if v is None:
                key += ';%s' % (self.Quote(k))
            else:
                key += ';%s=%s' % (self.Quote(k), self.Quote(unicode(v)))

        wrapped, line = '', '%s:%s' % (key, self.Quote(self._value))
        llen = 0
        for char in line:
            char = char.encode('utf-8')
            clen = len(char)
            if llen + clen >= 75:
                wrapped += '\n '
                llen = 0
            wrapped += char
            llen += clen

        return wrapped

    @classmethod
    def Quote(self, text):
        """
        Quote values so they can be safely represented in a VCard.

        >>> print VCardLine.Quote('Comma, semicolon; backslash\\ newline\\n')
        Comma\\, semicolon\\; backslash\\\\ newline\\n
        """
        return unicode(''.join([self.QUOTE_MAP.get(c, c) for c in text]))

    @classmethod
    def ParseLine(self, text):
        """
        Parse a single line, respecting to the VCard (RFC6350) quoting.

        >>> VCardLine.ParseLine('foo:val;ue')
        (u'foo', [], u'val;ue')
        >>> VCardLine.ParseLine('foo;BAR;\\\\baz:value')
        (u'foo', [(u'bar', None), (u'\\\\baz', None)], u'value')
        >>> VCardLine.ParseLine('FOO;bar=comma\\,semicolon\\;'
        ...                     'backslash\\\\\\\\:value')
        (u'foo', [(u'bar', u'comma,semicolon;backslash\\\\')], u'value')
        """
        # The parser is a state machine with two main states: quoted or
        # unquoted data. The unquoted data has three sub-states, to track
        # which part of the line is being parsed.

        def parse_quoted(char, state, parsed, name, attrs):
            pair = "\\" + char
            parsed = parsed[:-1] + self.QUOTE_RMAP.get(pair, pair)
            return parse_char, state, parsed, name, attrs

        def parse_char(char, state, parsed, name, attrs):
            if char == "\\":
                parsed += char
                return parse_quoted, state, parsed, name, attrs
            else:
                if state == 0 and char in (';', ':'):
                    name = parsed.lower()
                    parsed = ''
                    state += (char == ';') and 1 or 2
                elif state == 1 and char in (';', ':'):
                    if '=' in parsed:
                        k, v = parsed.split('=', 1)
                    else:
                        k = parsed
                        v = None
                    attrs.append((k.lower(), v))
                    parsed = ''
                    if char == ':':
                        state += 1
                else:
                    parsed += char
                return parse_char, state, parsed, name, attrs

        parser, state, parsed, name, attrs = parse_char, 0, '', None, []
        for char in unicode(text):
            parser, state, parsed, name, attrs = parser(
                char, state, parsed, name, attrs)

        return name, attrs, parsed


class SimpleVCard(object):
    """
    This is a very simplistic implementation of VCard 4.0.

    The card can be initialized with a series of VCardLine objects.
    >>> vcard = SimpleVCard(VCardLine(name='fn', value='Bjarni'),
    ...                     VCardLine(name='email', value='bre@example.com'),
    ...                     VCardLine(name='email', value='bre2@example.com'),
    ...                     VCardLine('EMAIL;TYPE=PREF:bre@evil.com'))

    The preferred (or Nth) line of any type can be retrieved using
    the get method. Lines are sorted by (preference, card order).
    >>> vcard.get('email').value
    u'bre@evil.com'
    >>> vcard.get('email', n=2).value
    u'bre2@example.com'
    >>> vcard.get('email', n=4).value
    Traceback (most recent call last):
        ...
    IndexError: ...

    There are shorthand methods for accessing or setting the values of
    the full name and e-mail lines:
    >>> vcard.email
    u'bre@evil.com'
    >>> vcard.fn = 'Bjarni R. E.'
    >>> vcard.get('fn').value
    u'Bjarni R. E.'

    To fetch all lines, use the get_all method. In this case no
    sorting is performed and lines are simply returned in card order.
    >>> [vcl.value for vcl in vcard.get_all('email')]
    [u'bre@example.com', u'bre2@example.com', u'bre@evil.com']

    """
    VCARD_OTHER_KEYS = {
        'AGENT': '',
        'CLASS': '',
        'EXPERTISE': '',
        'HOBBY': '',
        'INTEREST': '',
        'LABEL': '',
        'MAILER': '',
        'NAME': '',
        'ORG-DIRECTORY': '',
        'PROFILE': '',
        'SORT-STRING': '',
    }
    VCARD4_KEYS = {
        # General properties
        # .. BEGIN
        # .. END
        'SOURCE': ['*', None, None],
        'KIND': ['*1', None, 'individual'],
        'XML': ['*', None, None],
        # Identification properties
        'FN': ['1*', None, 'Anonymous'],
        'N': ['*1', None, None],
        'NICKNAME': ['*', None, None],
        'PHOTO': ['*', None, None],
        'BDAY': ['*1', None, None],
        'ANNIVERSARY': ['*1', None, None],
        'GENDER': ['*1', None, None],
        # Delivery Addressing Properties
        'ADR': ['*', None, None],
        # Communications Properties
        'TEL': ['*', None, None],
        'EMAIL': ['*', None, None],
        'IMPP': ['*', None, None],
        'LANG': ['*', None, None],
        # Geographical Properties
        'TZ': ['*', None, None],
        'GEO': ['*', None, None],
        # Organizational Properties
        'TITLE': ['*', None, None],
        'ROLE': ['*', None, None],
        'LOGO': ['*', None, None],
        'ORG': ['*', None, None],
        'MEMBER': ['*', None, None],
        'RELATED': ['*', None, None],
        # Explanitory Properties
        'VERSION': ['1', None, '4.0'],
        'CATEGORIES': ['*', None, None],
        'NOTE': ['*', None, None],
        'PRODID': ['*', None, None],
        'REV': ['*1', None, None],
        'SOUND': ['*', None, None],
        'UID': ['*1', None, None],
        'CLIENTPIDMAP': ['*', None, None],
        'URL': ['*', None, None],
        # Security Properties
        'KEY': ['*', None, None],
        # Calendar Properties
        'FBURL': ['*', None, None],
        'CALADRURI': ['*', None, None],
        'CALURI': ['*', None, None],
    }
    VCARD4_REQUIRED = ('VERSION', 'FN')

    def __init__(self, *lines, **kwargs):
        self.gpg_recipient = lambda: None
        self.encryption_key = lambda: None
        self.filename = None
        self._lines = []
        if 'data' in kwargs and kwargs['data'] is not None:
            self.load(data=kwargs['data'])
        self.add(*lines)

    def _cardinality(self, vcl):
        if vcl.name.startswith('x-'):
            return '*'
        else:
            return self.VCARD4_KEYS.get(vcl.name.upper(), [''])[0]

    def remove(self, *line_ids):
        """
        Remove one or more lines from the VCard.

        >>> vc = SimpleVCard(VCardLine(name='fn', value='Houdini'))
        >>> vc.remove(vc.get('fn').line_id)
        >>> vc.get('fn')
        Traceback (most recent call last):
            ...
        IndexError: ...
        """
        for index in range(0, len(self._lines)):
            vcl = self._lines[index]
            if vcl and vcl.line_id in line_ids:
                self._lines[index] = None

    def add(self, *vcls):
        """
        Add one or more lines to a VCard.

        >>> vc = SimpleVCard()
        >>> vc.add(VCardLine(name='fn', value='Bjarni'))
        >>> vc.get('fn').value
        u'Bjarni'

        Line types are checked against VCard 4.0 for validity.
        >>> vc.add(VCardLine(name='evil', value='Bjarni'))
        Traceback (most recent call last):
            ...
        ValueError: Not allowed on card: evil
        """
        for vcl in vcls:
            cardinality = self._cardinality(vcl)
            count = len([l for l in self._lines if l and l.name == vcl.name])
            if not cardinality:
                raise ValueError('Not allowed on card: %s' % vcl.name)
            if cardinality in ('1', '*1'):
                if count:
                    raise ValueError('Already on card: %s' % vcl.name)
            self._lines.append(vcl)
            vcl.line_id = len(self._lines)

    def get_clientpidmap(self):
        """
        Return a dictionary representing the CLIENTPIDMAP, grouping VCard
        lines by data sources.

        >>> vc = SimpleVCard(VCardLine(name='fn', value='Bjarni', pid='1.2'),
        ...                  VCardLine(name='clientpidmap',
        ...                            value='1;thisisauid'))
        >>> vc.get_clientpidmap()['thisisauid']['pid']
        1
        >>> vc.get_clientpidmap()[1]['lines'][0][0]
        2
        >>> vc.get_clientpidmap()[1]['lines'][0][1].value
        u'Bjarni'
        """
        cpm = {}
        for pm in self.get_all('clientpidmap'):
            pid, guid = pm.value.split(';')
            cpm[guid] = cpm[int(pid)] = {
                'pid': int(pid),
                'lines': []
            }
        for vcl in self.as_lines():
            if 'pid' in vcl:
                pv = [v.split('.', 1) for v in vcl['pid'].split(',')]
                for pid, version in pv:
                    try:
                        cpm[int(pid)]['lines'].append((int(version), vcl))
                    except KeyError, e:
                        print ("KNOWN BUG IN VERSIONING CODE. "
                               "[%s] [pid: %s] [cpm: %s]") % (e, pid, cpm)
        return cpm

    def merge(self, src_id, lines):
        """
        Merge a set of VCard lines from a given source into this card.

        >>> vc = SimpleVCard(VCardLine(name='fn', value='Bjarni', pid='1.2'),
        ...                  VCardLine(name='clientpidmap',
        ...                            value='1;thisisauid'))
        >>> vc.merge('thisisauid', [VCardLine(name='fn', value='Bjarni'),
        ...                         VCardLine(name='x-a', value='b')])
        >>> vc.get('x-a')['pid']
        '1.3'
        >>> vc.get('fn')['pid']
        '1.2'

        >>> vc.merge('otheruid', [VCardLine(name='x-b', value='c')])
        >>> vc.get('x-b')['pid']
        '2.1'

        >>> vc.merge('thisisauid', [VCardLine(name='fn', value='Inrajb')])
        >>> vc.get('fn')['pid']
        '1.4'
        >>> vc.fn
        u'Inrajb'
        >>> vc.get('x-a')
        Traceback (most recent call last):
           ...
        IndexError: ...

        >>> print vc.as_vCard()
        BEGIN:VCARD
        VERSION:4.0
        CLIENTPIDMAP:2\\;otheruid
        CLIENTPIDMAP:1\\;thisisauid
        FN;PID=1.4:Inrajb
        X-B;PID=2.1:c
        END:VCARD
        """
        if not lines:
            return

        # First, we figure out which CLIENTPIDMAP applies, if any
        cpm = self.get_clientpidmap()
        pidmap = cpm.get(src_id)
        if pidmap:
            src_pid = pidmap['pid']
        else:
            pids = [p['pid'] for p in cpm.values()]
            src_pid = max([int(p) for p in pids] + [0]) + 1
            self.add(VCardLine(name='clientpidmap',
                               value='%s;%s' % (src_pid, src_id)))
            pidmap = cpm[src_pid] = cpm[src_id] = {'lines': []}

        # Deduplicate the lines, but give them a rank if they are repeated
        lines.sort(key=lambda k: (k.name, k.value))
        dedup = [lines[0]]
        rank = 0

        def rankit(rank):
            if rank:
                dedup[-1].set_attr('x-rank', rank)

        for line in lines[1:]:
            if dedup[-1].name == line.name and dedup[-1].value == line.value:
                rank += 1
            else:
                rankit(rank)
                rank = 0
                dedup.append(line)
        rankit(rank)
        lines = dedup

        # 1st, iterate through existing lines for this source, removing
        # all that differ from our input. Remove any input lines which are
        # identical to those already on this card.
        this_version = 0
        for ver, ol in cpm[src_pid]['lines'][:]:
            this_version = max(ver, this_version)
            match = [l for l in lines if (l
                                          and l.name == ol.name
                                          and l.value == ol.value)]
            for l in match:
                lines.remove(l)
            if not match:
                # FIXME: Actually, we should JUST remove our pid and if no
                #        pids are left, remove the line itself.
                self.remove(ol.line_id)

        # 2nd, iterate through provided lines and copy them.
        this_version += 1
        for vcl in lines:
            pids = [pid for pid in vcl.get('pid', '').split(',')
                    if pid and pid.split('.')[0] != src_pid]
            pids.append('%s.%s' % (src_pid, this_version))
            vcl.set_attr('pid', ','.join(pids))
            self.add(vcl)

        # FIXME: 3rd, collapse lines from multiple sources that have
        #        identical values?

    def get_all(self, key):
        return [l for l in self._lines if l and l.name == key.lower()]

    def get(self, key, n=0):
        lines = self.get_all(key)
        lines.sort(key=lambda l: 1 - (int(l.get('x-rank', 0)) or
                                      (('pref' in l or
                                        'pref' in l.get('type', '').lower()
                                        ) and 100 or 0)))
        return lines[n]

    def as_jCard(self):
        card = [[key.lower(), {}, "text", self[key][0][0]]
                for key in self.order]
        stream = ["vcardstream", ["vcard", card]]
        return stream

    def _mpcdict(self, vcl):
        d = {}
        for k in vcl.keys():
            if k not in ('line_id', ):
                if k.startswith('x-mailpile-'):
                    d[k.replace('x-mailpile-', '')] = vcl[k]
                else:
                    d[k] = vcl[k]
        return d

    MPCARD_SINGLETONS = ('fn', 'kind', 'x-mailpile-crypto-policy')
    MPCARD_SUPPRESSED = ('version', 'x-mailpile-rid')

    def as_mpCard(self):
        mpCard, ln, lv = {}, None, None
        self._sort_lines()
        for vcl in self._lines:
            if not vcl or vcl.name in self.MPCARD_SUPPRESSED:
                continue
            if ln == vcl.name and lv == vcl.value:
                continue
            name = vcl.name.replace('x-mailpile-', '')
            if name not in mpCard:
                if vcl.name in self.MPCARD_SINGLETONS:
                    mpCard[name] = vcl.value
                else:
                    mpCard[name] = [self._mpcdict(vcl)]
            elif vcl.name not in self.MPCARD_SINGLETONS:
                mpCard[name].append(self._mpcdict(vcl))
            ln, lv = vcl.name, vcl.value
        return mpCard

    def _sort_lines(self):
        self._lines.sort(key=lambda k: ((k and k.name == 'version') and 1 or 2,
                                        k and k.name,
                                        k and len(k.value),
                                        k and k.value))

    def as_vCard(self):
        """
        This method returns the VCard data in its native format.
        Note: the output is a string of bytes, not unicode characters.

        >>> print SimpleVCard().as_vCard()
        BEGIN:VCARD
        VERSION:4.0
        FN:Anonymous
        END:VCARD
        """
        # Add any missing required keys...
        for key in self.VCARD4_REQUIRED:
            if not self.get_all(key):
                default = self.VCARD4_KEYS[key][2]
                self._lines[:0] = [VCardLine(name=key, value=default)]

        # Make sure VERSION is first, order is stable.
        self._sort_lines()

        return '\n'.join(['BEGIN:VCARD'] +
                         [l.as_vcardline() for l in self._lines if l] +
                         ['END:VCARD'])

    def as_lines(self):
        self._sort_lines()
        return [vcl for vcl in self._lines if vcl]

    def _vcard_get(self, key):
        try:
            return self.get(key).value
        except IndexError:
            default = self.VCARD4_KEYS.get(key.upper(), ['', '', None])[2]
            return default

    def _vcard_set(self, key, value):
        try:
            self.get(key).value = value
        except IndexError:
            self.add(VCardLine(name=key, value=value, pref=None))

    nickname = property(lambda self: self._vcard_get('nickname'),
                        lambda self, e: self._vcard_set('nickname', e))

    email = property(lambda self: self._vcard_get('email'),
                     lambda self, e: self._vcard_set('email', e))

    kind = property(lambda self: self._vcard_get('kind'),
                    lambda self, e: self._vcard_set('kind', e))

    fn = property(lambda self: self._vcard_get('fn'),
                  lambda self, e: self._vcard_set('fn', e))

    def _random_uid(self):
        try:
            rid = self.get('x-mailpile-rid').value
        except IndexError:
            crap = '%s %s' % (self.email, random.randint(0, 0x1fffffff))
            rid = b64w(sha1b64(crap)).lower()
            self.add(VCardLine(name='x-mailpile-rid', value=rid))
        return rid

    random_uid = property(_random_uid)

    def load(self, filename=None, data=None, config=None):
        """
        Load VCard lines from a file on disk or data in memory.
        """
        if data:
            pass
        elif filename:
            from mailpile.crypto.streamer import DecryptingStreamer
            self.filename = filename or self.filename
            with open(self.filename, 'rb') as fd:
                with DecryptingStreamer(config.prefs.obfuscate_index,
                                        fd) as streamer:
                    data = streamer.read().decode('utf-8')
        else:
            raise ValueError('Need data or a filename!')

        def unwrap(text):
            # This undoes the VCard standard line wrapping
            return text.replace('\n ', '').replace('\n\t', '')

        lines = [l.strip() for l in unwrap(data.strip()).splitlines()]
        if (not len(lines) >= 2 or
                not lines.pop(0).upper() == 'BEGIN:VCARD' or
                not lines.pop(-1).upper() == 'END:VCARD'):
            raise ValueError('Not a valid VCard: %s' % '\n'.join(lines))

        for line in lines:
            self.add(VCardLine(line))

        return self

    def save(self, filename=None, gpg_recipient=None, encryption_key=None):
        filename = filename or self.filename
        if filename:
            gpg_recipient = gpg_recipient or self.gpg_recipient()
            encryption_key = encryption_key or self.encryption_key()
            if encryption_key:
                from mailpile.crypto.streamer import EncryptingStreamer
                with EncryptingStreamer(encryption_key,
                                        dir=os.path.dirname(filename)) as es:
                    es.write(self.as_vCard())
                    es.save(filename)
            else:
                with gpg_open(filename, gpg_recipient, 'wb') as gpg:
                    gpg.write(self.as_vCard())
            return self
        else:
            raise ValueError('Save to what file?')


class AddressInfo(dict):

    fn = property(lambda s: s['fn'],
                  lambda s, v: s.__setitem__('fn', v))
    address = property(lambda s: s['address'],
                       lambda s, v: s.__setitem__('address', v))
    rank = property(lambda s: s['rank'],
                    lambda s, v: s.__setitem__('rank', v))
    protocol = property(lambda s: s['protocol'],
                        lambda s, v: s.__setitem__('protocol', v))
    flags = property(lambda s: s['flags'],
                     lambda s, v: s.__setitem__('flags', v))
    keys = property(lambda s: s.get('keys'),
                    lambda s, v: s.__setitem__('keys', v))

    def __init__(self, addr, fn, vcard=None, rank=0, proto='smtp', keys=None):
        info = {
            'fn': fn,
            'address': addr,
            'rank': rank,
            'protocol': proto,
            'flags': {}
        }
        if keys:
            info['keys'] = keys
            info['flags']['secure'] = True
        self.update(info)
        if vcard:
            self.merge_vcard(vcard)

    def merge_vcard(self, vcard):
        self['flags']['contact'] = True

        keys = []
        for k in vcard.get_all('KEY'):
            val = k.value.split("data:")[1]
            mime, fp = val.split(",")
            keys.append({'fingerprint': fp, 'type': 'openpgp', 'mime': mime})
        if keys:
            self['keys'] = self.get('keys', []) + [k for k in keys[:1]]
            self['flags']['secure'] = True

        photos = vcard.get_all('photo')
        if photos:
            self['photo'] = photos[0].value

        self['rank'] += 10.0 + 25 * len(keys) + 5 * len(photos)


class VCardStore(dict):
    """
    This is a disk-backed in-memory collection of VCards.

    >>> vcs = VCardStore(cfg, '/tmp')

    # VCards are added to the collection using add_vcard. This will
    # create a file for the card on disk, using a random name.
    >>> vcs.add_vcards(SimpleVCard(VCardLine('FN:Dude'),
    ...                            VCardLine('EMAIL:d@evil.com')),
    ...                SimpleVCard(VCardLine('FN:Guy')))

    VCards can be looked up directly by e-mail.
    >>> vcs.get_vcard('d@evil.com').fn
    u'Dude'

    Or they can be found using searches...
    >>> vcs.find_vcards(['guy'])[0].fn
    u'Guy'

    Cards can be removed using del_vcards
    >>> vcs.del_vcards(vcs.get_vcard('d@evil.com'))
    >>> vcs.get_vcard('d@evil.com') is None
    True
    >>> vcs.del_vcards(*vcs.find_vcards(['guy']))
    >>> vcs.find_vcards(['guy'])
    []
    """
    def __init__(self, config, vcard_dir):
        dict.__init__(self)
        self.config = config
        self.vcard_dir = vcard_dir
        self.loaded = False

    def index_vcard(self, card):
        attr = (card.kind == 'individual') and 'email' or 'nickname'
        for vcl in card.get_all(attr):
            self[vcl.value.lower()] = card
        self[card.random_uid] = card

    def deindex_vcard(self, card):
        attr = (card.kind == 'individual') and 'email' or 'nickname'
        for vcl in card.get_all(attr):
            if vcl.value.lower() in self:
                del self[vcl.value.lower()]
        if card.random_uid in self:
            del self[card.random_uid]

    def load_vcards(self, session=None):
        if self.loaded:
            return
        try:
            self.loaded = True
            prefs = self.config.prefs
            for fn in os.listdir(self.vcard_dir):
                if mailpile.util.QUITTING:
                    return
                try:
                    c = SimpleVCard().load(os.path.join(self.vcard_dir, fn),
                                           config=(session and session.config))
                    c.gpg_recipient = lambda: prefs.get('gpg_recipient')
                    c.encryption_key = lambda: prefs.get('obfuscate_index')
                    self.index_vcard(c)
                    if session:
                        session.ui.mark('Loaded %s from %s' % (c.email, fn))
                except:
                    if session:
                        if 'vcard' in self.config.sys.debug:
                            import traceback
                            traceback.print_exc()
                        session.ui.warning('Failed to load vcard %s' % fn)
        except OSError:
            pass

    def get_vcard(self, email):
        return self.get(email.lower(), None)

    def find_vcards(vcards, terms, kinds=['individual']):
        results = []
        if not terms:
            results = [set([vcards[k].random_uid for k in vcards
                            if (vcards[k].kind in kinds) or not kinds])]
        for term in terms:
            term = term.lower()
            results.append(set([vcards[k].random_uid for k in vcards
                                if (term in k or term in vcards[k].fn.lower())
                                and ((vcards[k].kind in kinds) or not kinds)]))
        while len(results) > 1:
            results[0] &= results.pop(-1)
        results = [vcards[rid] for rid in results[0]]
        results.sort(key=lambda card: card.fn)
        return results

    def add_vcards(self, *cards):
        prefs = self.config.prefs
        for card in cards:
            card.filename = os.path.join(self.vcard_dir,
                                         card.random_uid) + '.vcf'
            card.gpg_recipient = lambda: prefs.get('gpg_recipient')
            card.encryption_key = lambda: prefs.get('obfuscate_index')
            card.save()
            self.index_vcard(card)

    def del_vcards(self, *cards):
        for card in cards:
            self.deindex_vcard(card)
            try:
                os.remove(card.filename)
            except (OSError, IOError):
                pass


GUID_COUNTER = 0


class VCardPluginClass:
    REQUIRED_PARAMETERS = []
    OPTIONAL_PARAMETERS = []
    FORMAT_NAME = None
    FORMAT_DESCRIPTION = 'VCard Import/Export plugin'
    SHORT_NAME = None
    CONFIG_RULES = None

    def __init__(self, session, config, guid=None):
        self.session = session
        self.config = config
        if not self.config.guid:
            if not guid:
                global GUID_COUNTER
                guid = 'urn:uuid:mp-%s-%x-%x' % (self.SHORT_NAME, time.time(),
                                                 GUID_COUNTER)
                GUID_COUNTER += 1
            self.config.guid = guid
            self.session.config.save()


class VCardImporter(VCardPluginClass):

    def import_vcards(self, session, vcard_store):
        all_vcards = self.get_vcards()
        updated = []
        for vcard in all_vcards:
            existing = None
            for email in vcard.get_all('email'):
                existing = vcard_store.get_vcard(email.value)
                if existing:
                    existing.merge(self.config.guid, vcard.as_lines())
                    updated.append(existing)
                if session.config and session.config.index:
                    session.config.index.update_email(email.value,
                                                      name=vcard.fn)
            if existing is None:
                new_vcard = SimpleVCard()
                new_vcard.merge(self.config.guid, vcard.as_lines())
                vcard_store.add_vcards(new_vcard)
                updated.append(new_vcard)
                play_nice_with_threads()
        for vcard in set(updated):
            vcard.save()
            play_nice_with_threads()
        return len(updated)

    def get_vcards(self):
        raise Exception('Please override this function')


class VCardExporter(VCardPluginClass):

    def __init__(self):
        self.exporting = []

    def add_contact(self, contact):
        self.exporting.append(contact)

    def remove_contact(self, contact):
        self.exporting.remove(contact)

    def save(self):
        pass


class VCardContextProvider(VCardPluginClass):

    def __init__(self, contact):
        self.contact = contact

    def get_recent_context(self, max=10):
        pass

    def get_related_context(self, query, max=10):
        pass


if __name__ == "__main__":
    import doctest
    import mailpile.config
    import mailpile.defaults
    cfg = mailpile.config.ConfigManager(rules=mailpile.defaults.CONFIG_RULES)
    results = doctest.testmod(optionflags=doctest.ELLIPSIS,
                              extraglobs={'cfg': cfg})
    print '%s' % (results, )
    if results.failed:
        sys.exit(1)

########NEW FILE########
__FILENAME__ = workers
import threading
import time
from gettext import gettext as _

import mailpile.util
from mailpile.util import *


##[ Specialized threads ]######################################################

class Cron(threading.Thread):
    """
    An instance of this class represents a cron-like worker thread
    that manages and executes tasks in regular intervals
    """

    def __init__(self, name=None, session=None):
        """
        Initializes a new Cron instance.
        Note that the thread will not be started automatically, so
        you need to call start() manually.

        Keyword arguments:
        name -- The name of the Cron instance
        session -- Currently unused
        """
        threading.Thread.__init__(self)
        self.ALIVE = False
        self.name = name
        self.session = session
        self.schedule = {}
        self.sleep = 10
        # This lock is used to synchronize
        self.lock = threading.Lock()

    def add_task(self, name, interval, task):
        """
        Add a task to the cron worker queue

        Keyword arguments:
        name -- The name of the task to add
        interval -- The interval (in seconds) of the task
        task    -- A task function
        """
        self.lock.acquire()
        try:
            self.schedule[name] = [name, interval, task, time.time()]
            self.sleep = 1
            self.__recalculateSleep()
        finally:
            # Not releasing the lock will block the entire cron thread
            self.lock.release()

    def __recalculateSleep(self):
        """
        Recalculate the maximum sleep delay.
        This shall be called from a lock zone only
        """
        # (Re)alculate how long we can sleep between tasks
        #    (sleep min. 1 sec, max. 61 sec)
        # --> Calculate the GCD of the task intervals
        for i in range(2, 61):  # i = second
            # Check if any scheduled task intervals are != 0 mod i
            filteredTasks = [True for task in self.schedule.values()
                             if int(task[1]) % i != 0]
            # We can sleep for i seconds if i divides all intervals
            if (len(filteredTasks) == 0):
                self.sleep = i

    def cancel_task(self, name):
        """
        Cancel a task in the current Cron instance.
        If a task with the given name does not exist,
        ignore the request.

        Keyword arguments:
        name -- The name of the task to cancel
        """
        if name in self.schedule:
            self.lock.acquire()
            try:
                del self.schedule[name]
                self.__recalculateSleep()
            finally:
                self.lock.release()

    def run(self):
        """
        Thread main function for a Cron instance.

        """
        self.ALIVE = True
        # Main thread loop
        while self.ALIVE and not mailpile.util.QUITTING:
            now = time.time()
            # Check if any of the task is (over)due
            self.lock.acquire()
            tasksToBeExecuted = []  # Contains tuples (name, func)
            for task_spec in self.schedule.values():
                name, interval, task, last = task_spec
                if last + interval <= now:
                    tasksToBeExecuted.append((name, task))
            self.lock.release()
            #Execute the tasks
            for name, task in tasksToBeExecuted:
                # Set last_executed
                self.schedule[name][3] = time.time()
                try:
                    task()
                except Exception, e:
                    self.session.ui.error(('%s failed in %s: %s'
                                           ) % (name, self.name, e))

            # Some tasks take longer than others, so use the time before
            # executing tasks as reference for the delay
            sleepTime = self.sleep
            delay = time.time() - now + sleepTime

            # Sleep for max. 1 sec to react to the quit signal in time
            while delay > 0 and self.ALIVE:
                # self.sleep might change during loop (if tasks are modified)
                # In that case, just wake up and check if any tasks need
                # to be executed
                if self.sleep != sleepTime:
                    delay = 0
                else:
                    # Sleep for max 1 second to check self.ALIVE
                    time.sleep(max(0, min(1, delay)))
                    delay -= 1

    def quit(self, session=None, join=True):
        """
        Send a signal to the current Cron instance
        to stop operation.

        Keyword arguments:
        join -- If this is True, this method will wait until
                        the Cron thread exits.
        """
        self.ALIVE = False
        if join:
            try:
                self.join()
            except RuntimeError:
                pass


class Worker(threading.Thread):

    def __init__(self, name, session):
        threading.Thread.__init__(self)
        self.NAME = name or 'Worker'
        self.ALIVE = False
        self.JOBS = []
        self.LOCK = threading.Condition()
        self.pauses = 0
        self.session = session

    def add_task(self, session, name, task):
        self.LOCK.acquire()
        self.JOBS.append((session, name, task))
        self.LOCK.notify()
        self.LOCK.release()

    def do(self, session, name, task):
        if session and session.main:
            # We run this in the foreground on the main interactive session,
            # so CTRL-C has a chance to work.
            try:
                self.pause(session)
                rv = task()
            finally:
                self.unpause(session)
        else:
            self.add_task(session, name, task)
            if session:
                rv = session.wait_for_task(name)
            else:
                rv = True
        return rv

    def run(self):
        self.ALIVE = True
        while self.ALIVE and not mailpile.util.QUITTING:
            self.LOCK.acquire()
            while len(self.JOBS) < 1:
                self.LOCK.wait()
            session, name, task = self.JOBS.pop(0)
            self.LOCK.release()

            try:
                if session:
                    session.ui.mark('Starting: %s' % name)
                    session.report_task_completed(name, task())
                else:
                    task()
            except Exception, e:
                self.session.ui.error(('%s failed in %s: %s'
                                       ) % (name, self.NAME, e))
                if session:
                    session.report_task_failed(name)

    def pause(self, session):
        self.LOCK.acquire()
        self.pauses += 1
        if self.pauses == 1:
            self.LOCK.release()

            def pause_task():
                session.report_task_completed('Pause', True)
                session.wait_for_task('Unpause', quiet=True)

            self.add_task(None, 'Pause', pause_task)
            session.wait_for_task('Pause', quiet=True)
        else:
            self.LOCK.release()

    def unpause(self, session):
        self.LOCK.acquire()
        self.pauses -= 1
        if self.pauses == 0:
            session.report_task_completed('Unpause', True)
        self.LOCK.release()

    def die_soon(self, session=None):
        def die():
            self.ALIVE = False
        self.add_task(session, '%s shutdown' % self.NAME, die)

    def quit(self, session=None, join=True):
        self.die_soon(session=session)
        if join:
            try:
                self.join()
            except RuntimeError:
                pass


class DumbWorker(Worker):
    def add_task(self, session, name, task):
        try:
            self.LOCK.acquire()
            return task()
        finally:
            self.LOCK.release()

    def do(self, session, name, task):
        return self.add_task(session, name, task)

    def run(self):
        pass


if __name__ == "__main__":
    import doctest
    import sys
    result = doctest.testmod(optionflags=doctest.ELLIPSIS,
                             extraglobs={'junk': {}})
    print '%s' % (result, )
    if result.failed:
        sys.exit(1)

########NEW FILE########
__FILENAME__ = __main__
import sys
from mailpile.app import Main


def main():
    Main(sys.argv[1:])


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = demos
# This is a collection of very short demo-plugins to illustrate how
# to create and register hooks into the various parts of Mailpile
#
# To start creating a new plugin, it may make sense to copy this file,
# globally search/replace the word "Demo" with your preferred plugin
# name and then go delete sections you aren't going to use.
#
# Happy hacking!

from gettext import gettext as _
from mailpile.plugins import PluginManager


##[ Pluggable configuration ]#################################################

# FIXME


##[ Pluggable keyword extractors ]############################################

# FIXME


##[ Pluggable search terms ]##################################################

# Pluggable search terms allow plugins to enhance the behavior of the
# search engine in various ways. Examples of basic enhanced search terms
# are the date: and size: keywords, which accept human-friendly ranges
# and input, and convert those to a list of "low level" keywords to
# actually search for.

# FIXME


##[ Pluggable vcard functions ]###############################################
from mailpile.vcard import *


class DemoVCardImporter(VCardImporter):
    """
    This VCard importer simply generates VCards based on data in the
    configuration. This is not particularly useful, but it demonstrates
    how each importer can define (and use) its own settings.
    """
    FORMAT_NAME = _('Demo Contacts')
    FORMAT_DESCRPTION = _('This is the demo importer')
    SHORT_NAME = 'demo'
    CONFIG_RULES = {
        'active': [_('Activate demo importer'), bool, True],
        'name': [_('Contact name'), str, 'Mr. Rogers'],
        'email': [_('Contact email'), 'email', 'mr@rogers.com']
    }

    def get_vcards(self):
        """Returns just a single contact, based on data from the config."""
        # Notes to implementors:
        #
        #  - It is important to only return one card per (set of)
        #    e-mail addresses, as internal overwriting may cause
        #    unexpected results.
        #  - If data is to be deleted from the contact list, it
        #    is important to return a VCard for that e-mail address
        #    which has the relevant data removed.
        #
        if not self.config.active:
            return []
        return [SimpleVCard(
            VCardLine(name='fn', value=self.config.name),
            VCardLine(name='email', value=self.config.email)
        )]


##[ Pluggable cron jobs ]#####################################################

def TickJob(session):
    """
    This is a very minimal cron job - just a function that runs within
    a session.

    Note that generally it is a better pattern to create a Command which
    is then invoked by the cron job, so power users can access the
    functionality directly.  It is also a good idea to make the interval
    configurable by registering a setting and referencing that instead of
    a fixed number.  See compose.py for an example of how this is done.
    """
    session.ui.notify('Tick!')


##[ Pluggable commands and data views ]#######################################

from mailpile.commands import Command
from mailpile.util import md5_hex


class md5sumCommand(Command):
    """This command calculates MD5 sums"""
    SYNOPSIS_ARGS = '[<data to hash>]'
    SPLIT_ARG = False
    HTTP_CALLABLE = ('GET', 'POST')
    HTTP_QUERY_VARS = {
       'data': 'Data to hash'
    }

    def command(self):
        if 'data' in self.data:
            data = self.data['data'][0]
        else:
            data = ''.join(self.args)

        for gross in self.session.config.sys.md5sum_blacklist.split():
            if gross in data or not data:
                return self._error(_('I refuse to work with empty '
                                     'or gross data'),
                                   info={'data': data})

        return self._success(_('I hashed your data for you, yay!'),
                             result=md5_hex(data))


class md5sumWordyView(md5sumCommand):
    """Represent MD5 sums in a more wordy way."""
    @classmethod
    def view(cls, result):
        return 'MD5:%s' % result


def on_plugin_start(config):
    """Called once after plugin is loaded.

    You can initialize external or expensive dependencies here.

    Args:
        config: The Mailpile configuration dictionary

    Returns:
        void
    """
    # initialize some external dependencies
    pass


def on_plugin_shutdown(config):
    """Called before plugin is stopped.

    Shutdown external dependencies here, especially if they created some threads.

    Args:
        config: The Mailpile configuration dictionary

    Returns:
        void
    """
    # properly shutdown external dependencies
    pass


class DemoMailbox(object):
    """A dysfunctional demo mailbox. See mailpile.mailboxes.* for proper mailbox examples"""
    @classmethod
    def parse_path(cls, config, fn, create=False):
        raise ValueError('This is only a demo mailbox class!')

########NEW FILE########
__FILENAME__ = forcegrapher
import datetime
import re
import time
from gettext import gettext as _

from mailpile.commands import Command
from mailpile.mailutils import Email, ExtractEmails
from mailpile.search import MailIndex
from mailpile.util import *

from mailpile.plugins.search import Search


class Graph(Search):
    """Get a graph of the network in the current search results."""
    ORDER = ('Searching', 1)
    SYNOPSIS = (None, 'getgraph', 'getgraph', '<terms>')
    HTTP_CALLABLE = ('GET', )
    UI_CONTEXT = "search"

    def command(self, search=None):
        session, idx, start, num = self._do_search(search=search)

        nodes = []
        links = []
        res = {}

        for messageid in session.results:
            msg = self._idx().get_msg_at_idx_pos(messageid)
            msgfrom = msg[self._idx().MSG_FROM]
            msgto = [self._idx().EMAILS[int(x, 36)]
                     for x in msg[self._idx().MSG_TO].split(",") if x != ""]
            m = re.match("((.*) ){0,1}\<(.*)\>", msgfrom)
            if m:
                name = m.groups(0)[1]
                email = m.groups(0)[2]
            else:
                name = None
                email = msgfrom

            if email not in [m["email"] for m in nodes]:
                n = {"email": email}
                if name:
                    n["name"] = name
                nodes.append(n)

            for address in msgto:
                if address not in [m["email"] for m in nodes]:
                    nodes.append({"email": address})

            curnodes = [x["email"] for x in nodes]
            fromid = curnodes.index(email)
            searchspace = [m for m in links if m["source"] == fromid]
            for address in msgto:
                index = curnodes.index(address)
                link = [m for m in searchspace if m["target"] == index]
                if len(link) == 0:
                    links.append({"source": fromid,
                                  "target": index,
                                  "value": 1})
                elif len(link) == 1:
                    link[0]["value"] += 1
                else:
                    raise ValueError("Too many links! - This should never "
                                     "happen.")

            if len(nodes) >= 300:
                # Let's put a hard upper limit on how many nodes we can
                # have, for performance reasons.
                # There might be a better way to do this though...
                res["limit_hit"] = True
                break

        res["nodes"] = nodes
        res["links"] = links
        res["searched"] = session.searched
        if "limit_hit" not in res:
            res["limit_hit"] = False
        return res


# mailpile.plugins.register_display_mode("search", "graph",
#                                       "mailpile.results_graph();",
#                                       "Graph",
#                                       url="#", icon="graph")
#mailpile.plugins.register_asset("javascript", "js/libraries/d3.v3.min.js")
#mailpile.plugins.register_asset("javascript", "plugins/forcegrapher/forcegrapher.js")
#mailpile.plugins.register_asset("content-view_block", "forcegrapher/search.html")

########NEW FILE########
__FILENAME__ = hacks
import json
from gettext import gettext as _
from urllib import urlencode, URLopener

from mailpile.commands import Command, Help
from mailpile.mailutils import *
from mailpile.search import *
from mailpile.util import *
from mailpile.vcard import *


class Hacks(Command):
    """Various hacks ..."""
    SYNOPSIS = (None, 'hacks', None, None)
    ORDER = ('Internals', 9)
    HTTP_CALLABLE = ()

    def command(self):
        return self._success('OK', Help(self.session, arg=['hacks']).run())


class FixIndex(Hacks):
    """Do various things to try and fix broken indexes"""
    SYNOPSIS = (None, 'hacks/fixindex', None, None)
    LOG_PROGRESS = True

    def command(self):
        session, index = self.session, self._idx()

        session.ui.mark('Checking index for duplicate MSG IDs...')
        found = {}
        for i in range(0, len(index.INDEX)):
            msg_id = index.get_msg_at_idx_pos(i)[index.MSG_ID]
            if msg_id in found:
                found[msg_id].append(i)
            else:
                found[msg_id] = [i]

        session.ui.mark('Attempting to fix dups with bad location...')
        for msg_id in found:
            if len(found[msg_id]) > 1:
                good, bad = [], []
                for idx_pos in found[msg_id]:
                    msg = Email(index, idx_pos).get_msg()
                    if msg:
                        good.append(idx_pos)
                    else:
                        bad.append(idx_pos)
                if good and bad:
                    good_info = index.get_msg_at_idx_pos(good[0])
                    for bad_idx in bad:
                        bad_info = index.get_msg_at_idx_pos(bad_idx)
                        bad_info[index.MSG_PTRS] = good_info[index.MSG_PTRS]
                        index.set_msg_at_idx_pos(bad_idx, bad_info)

        return self._success(_('Tried to fix metadata index'))


class PyCLI(Hacks):
    """Launch a Python REPL"""
    SYNOPSIS = (None, 'hacks/pycli', None, None)
    LOG_PROGRESS = True

    def command(self):
        import code
        import readline
        from mailpile import Mailpile

        variables = globals()
        variables['session'] = self.session
        variables['config'] = self.session.config
        variables['index'] = self.session.config.index
        variables['mp'] = Mailpile(session=self.session)

        self.session.config.stop_workers()
        self.session.ui.block()
        code.InteractiveConsole(locals=variables).interact("""\
This is Python inside of Mailpile inside of Python.

   - The `mp` variable is a Pythonic API to the current pile of mail.
   - The `session` variable is the current UI session.
   - The `config` variable contains the current configuration.
   - Press CTRL+D to return to the normal CLI.
""")
        self.session.ui.unblock()
        self.session.config.prepare_workers(self.session, daemons=True)

        return self._success(_('That was fun!'))


class ViewMetadata(Hacks):
    """Display the raw metadata for a message"""
    SYNOPSIS = (None, 'hacks/metadata', None, '[<message>]')

    def _explain(self, i):
        idx = self._idx()
        info = idx.get_msg_at_idx_pos(i)
        return {
            'mid': info[idx.MSG_MID],
            'ptrs': info[idx.MSG_PTRS],
            'id': info[idx.MSG_ID],
            'date': info[idx.MSG_DATE],
            'from': info[idx.MSG_FROM],
            'to': info[idx.MSG_TO],
            'cc': info[idx.MSG_CC],
            'kb': info[idx.MSG_KB],
            'subject': info[idx.MSG_SUBJECT],
            'body': info[idx.MSG_BODY],
            'tags': info[idx.MSG_TAGS],
            'replies': info[idx.MSG_REPLIES],
            'thread_mid': info[idx.MSG_THREAD_MID],
        }

    def command(self):
        return self._success(_('Displayed raw metadata'),
            [self._explain(i) for i in self._choose_messages(self.args)])


class Http(Hacks):
    """Send HTTP requests to the web server"""
    SYNOPSIS = (None, 'hacks/http', None,
                '<GET|POST> </url/> [<Q|P> <var>=<val> ...]')

#    class CommandResult(Hacks.CommandResult):
#        def as_text(self):
#            pass

    def command(self):
        args = list(self.args)
        method, url = args[0:2]

        if not url.startswith('http'):
            url = 'http://%s:%s%s' % (self.session.config.sys.http_host,
                                      self.session.config.sys.http_port,
                                      ('/' + url).replace('//', '/'))

        # FIXME: The python URLopener doesn't seem to support other verbs,
        #        which is really quite lame.
        method = method.upper()
        assert(method in ('GET', 'POST'))

        qv, pv = [], []
        if method == 'POST':
            which = pv
        else:
            which = qv
        for arg in args[2:]:
            if '=' in arg:
                which.append(tuple(arg.split('=', 1)))
            elif arg.upper()[0] == 'P':
                which = pv
            elif arg.upper()[0] == 'Q':
                which = qv

        if qv:
            qv = urlencode(qv)
            url += ('?' in url and '&' or '?') + qv

        try:
            uo = URLopener()
            if method == 'POST':
                (fn, hdrs) = uo.retrieve(url, data=urlencode(pv))
            else:
                (fn, hdrs) = uo.retrieve(url)
            hdrs = unicode(hdrs)
            data = open(fn, 'rb').read().strip()
            if data.startswith('{') and 'application/json' in hdrs:
                data = json.loads(data)
            return self._success('%s %s' % (method, url), result={
                'headers': hdrs.splitlines(),
                'data': data
            })
        except:
            self._ignore_exception()
            return self._error('%s %s' % (method, url))

########NEW FILE########
__FILENAME__ = maildeck
from mailpile.commands import Command

class maildeckCommand(Command):
           HTTP_CALLABLE = ('GET',)
########NEW FILE########
__FILENAME__ = twilio_sms
from twilio.rest import TwilioRestClient

account = "AC######################"
token = "***************************"
client = TwilioRestClient(account, token)

message = client.messages.create(to="+15031112222", from_="+13101112222",
                                 body="Hello there!")
########NEW FILE########
__FILENAME__ = create-debian-changelog
#!/usr/bin/env python2
#This script builds a DCH changelog from the git commit log
from subprocess import check_output, call
from multiprocessing import Pool
import os

def getLogMessage(commitSHA):
    """Get the log message for a given commit hash"""
    output = check_output(["git","log","--format=%B","-n","1",commitSHA])
    return output.strip()

def versionFromCommitNo(commitNo):
    """Generate a version string from a numerical commit no"""
    return "0.0.0-dev%d" % commitNo

#Execute git rev-list $(git rev-parse HEAD) to get list of revisions
head = check_output(["git","rev-parse","HEAD"]).strip()
revisions = check_output(["git","rev-list",head]).strip().split("\n")
#Revisions now contains rev identifiers, newest revisions first.
print "Found %d revisions" % len(revisions)
revisions.reverse() #In-place reverse, to make oldest revision first
#Map the revisions to their log msgs
print "Mapping revisions to log messages"
threadpool = p = Pool(10)
revLogMsgs = threadpool.map(getLogMessage, revisions)
#(Re)create the changelog for the first revision (= the oldest one)
try:
    os.unlink("debian/changelog")
except OSError:
    pass #Don't care if the file does not exist
firstCommitMsg = revLogMsgs[0]
call(["dch","--create","-v",versionFromCommitNo(0),"--package","mailpile",firstCommitMsg])
#Create the changelog entry for all other commits
for i in range(1, len(revisions)):
    print "Generating changelog for revision %d" % i
    commitMsg = revLogMsgs[i]
    call(["dch","-v",versionFromCommitNo(i),"--package","mailpile",commitMsg])

########NEW FILE########
__FILENAME__ = email-parsing-test
#!/usr/bin/python
#
# This is code which tries very hard to interpret the From:, To: and Cc:
# lines found in real-world e-mail addresses and make sense of them.
#
# The general strategy of this script is to:
#    1. parse header into tokens
#    2. group tokens together into address + name constructs
#    3. normalize each group to a standard format
#
# In practice, we do this in two passes - first a strict pass where we try
# to parse things semi-sensibly.  If that fails, there is a second pass
# where we try to cope with certain types of weirdness we've seen in the
# wild. The wild can be pretty wild.
#
# This parser is NOT fully RFC2822 compliant - in particular it will get
# confused by nested comments (see FIXME in tests below).
#
import sys
import traceback

from mailpile.mailutils import AddressHeaderParser as AHP


ahp_tests = AHP(AHP.TEST_HEADER_DATA)
print '_tokens: %s' % ahp_tests._tokens
print '_groups: %s' % ahp_tests._groups
print '%s' % ahp_tests
print 'normalized: %s' % ahp_tests.normalized()


headers, header, inheader = {}, None, False
for line in sys.stdin:
    if inheader:
        if line in ('\n', '\r\n'):
            for hdr in ('from', 'to', 'cc'):
                val = headers.get(hdr, '').replace('\n', ' ').strip()
                if val:
                    try:
                        nv = AHP(val, _raise=True).normalized()
                        if '\\' in nv:
                            print 'ESCAPED: %s: %s (was %s)' % (hdr, nv, val)
                        else:
                            print '%s' % (nv,)
                    except ValueError:
                        print 'FAILED: %s: %s -- %s' % (hdr, val,
                            traceback.format_exc().replace('\n', '  '))
            headers, header, inheader = {}, None, False
        elif line[:1] in (' ', '\t') and header:
            headers[header] = headers[header].rstrip() + line[1:]
        else:
            try:
                header, value = line.split(': ', 1)
                header = header.lower()
                headers[header] = headers.get(header, '') + ' ' + value
            except ValueError:
                headers, header, inheader = {}, None, False
    else:
        if line.startswith('From '):
            inheader = True

########NEW FILE########
__FILENAME__ = mailpile-pyside
#!/usr/bin/env python2
#
# This is a proof-of-concept quick hack, copy-pasted from code found here:
#
#   http://agateau.com/2012/02/03/pyqtwebkit-experiments-part-2-debugging/
#
import sys
from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtWebKit import *

class Window(QWidget):
    def __init__(self):
        super(Window, self).__init__()
        self.view = QWebView(self)

        self.setupInspector()

        self.splitter = QSplitter(self)
        self.splitter.setOrientation(Qt.Vertical)

        layout = QVBoxLayout(self)
        #layout.setMargin(0)
        layout.addWidget(self.splitter)

        self.splitter.addWidget(self.view)
        self.splitter.addWidget(self.webInspector)

    def setupInspector(self):
        page = self.view.page()
        page.settings().setAttribute(QWebSettings.DeveloperExtrasEnabled, True)
        self.webInspector = QWebInspector(self)
        self.webInspector.setPage(page)

        #shortcut = QShortcut(self)
        #shortcut.setKey(Qt.Key_F12)
        #shortcut.activated.connect(self.toggleInspector)
        self.webInspector.setVisible(True)

    def toggleInspector(self):
        self.webInspector.setVisible(not self.webInspector.isVisible())

def main():
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    window.view.load('http://localhost:33511/')
    return app.exec_()

sys.exit(main())

########NEW FILE########
__FILENAME__ = mailpile-test
#!/usr/bin/env python2
#
# This script runs a set of black-box tests on Mailpile using the test
# messages found in `testing/`.
#
# If run with -i as the first argument, it will then drop to an interactive
# python shell for experimenting and manual testing.
#
import os
import sys
import time
import traceback


# Set up some paths
mailpile_root = os.path.join(os.path.dirname(__file__), '..')
mailpile_test = os.path.join(mailpile_root, 'testing')
mailpile_send = os.path.join(mailpile_root, 'scripts', 'test-sendmail.sh')
mailpile_home = os.path.join(mailpile_test, 'tmp')
mailpile_gpgh = os.path.join(mailpile_test, 'gpg-keyring')
mailpile_sent = os.path.join(mailpile_home, 'sent.mbx')

# Set the GNUGPHOME variable to our test key
os.environ['GNUPGHOME'] = mailpile_gpgh

# Add the root to our import path, import API and demo plugins
sys.path.append(mailpile_root)
from mailpile.mail_source.mbox import MboxMailSource
from mailpile.mail_source.maildir import MaildirMailSource
from mailpile import Mailpile


##[ Black-box test script ]###################################################

FROM_BRE = [u'from:r\xfanar', u'from:bjarni']
MY_FROM = 'team+testing@mailpile.is'
MY_NAME = 'Mailpile Team'
MY_KEYID = '0x7848252F'

# First, we set up a pristine Mailpile
os.system('rm -rf %s' % mailpile_home)
mp = Mailpile(workdir=mailpile_home)
cfg = config = mp._session.config
cfg.plugins.load('demos', process_manifest=True)


def contents(fn):
    return open(fn, 'r').read()


def grep(w, fn):
    return '\n'.join([l for l in open(fn, 'r').readlines() if w in l])


def grepv(w, fn):
    return '\n'.join([l for l in open(fn, 'r').readlines() if w not in l])


def say(stuff):
    mp._session.ui.mark(stuff)
    mp._session.ui.reset_marks()


def do_setup():
    # Set up initial tags and such
    mp.setup()

    # Configure our fake mail sending setup
    config.profiles['0'].email = MY_FROM
    config.profiles['0'].name = MY_NAME
    config.sys.http_port = 33414
    config.sys.debug = 'rescan sendmail log compose'
    config.prefs.openpgp_header = 'encrypt'
    config.prefs.crypto_policy = 'openpgp-sign'

    # Set up dummy conctact importer fortesting, disable Gravatar
    mp.set('prefs/vcard/importers/demo/0/name = Mr. Rogers')
    mp.set('prefs/vcard/importers/gravatar/0/active = false')
    mp.set('prefs/vcard/importers/gpg/0/active = false')

    # Make sure that actually worked
    assert(not mp._config.prefs.vcard.importers.gpg[0].active)
    assert(not mp._config.prefs.vcard.importers.gravatar[0].active)

    # Copy the test Maildir...
    for mailbox in ('Maildir', 'Maildir2'):
        path = os.path.join(mailpile_home, mailbox)
        os.system('cp -a %s/Maildir %s' % (mailpile_test, path))

    # Add the test mailboxes
    for mailbox in ('tests.mbx', ):
        mp.add(os.path.join(mailpile_test, mailbox))
    mp.add(os.path.join(mailpile_home, 'Maildir'))

    mp.setup_migrate()


def test_vcards():
    # Do we have a Mr. Rogers contact?
    mp.rescan('vcards')
    assert(mp.contact('mr@rogers.com'
                      ).result['contact']['fn'] == u'Mr. Rogers')
    assert(len(mp.contact_list('rogers').result['contacts']) == 1)

def test_load_save_rescan():
    mp.rescan()

    # Save and load the index, just for kicks
    messages = len(mp._config.index.INDEX)
    assert(messages > 5)
    mp._config.index.save(mp._session)
    mp._session.ui.reset_marks()
    mp._config.index.load(mp._session)
    mp._session.ui.reset_marks()
    assert(len(mp._config.index.INDEX) == messages)

    # Rescan AGAIN, so we can test for the presence of duplicates and
    # verify that the move-detection code actually works.
    os.system('rm -f %s/Maildir/*/*' % mailpile_home)
    mp.add(os.path.join(mailpile_home, 'Maildir2'))
    mp.rescan()

    # Search for things, there should be exactly one match for each.
    mp.order('rev-date')
    for search in (FROM_BRE,
                   ['agirorn'],
                   ['subject:emerging'],
                   ['from:twitter', 'brennan'],
                   ['dates:2013-09-17', 'feministinn'],
                   ['mailbox:tests.mbx'] + FROM_BRE,
                   ['att:jpg', 'fimmtudaginn'],
                   ['subject:Moderation', 'kde-isl'],
                   ['from:bjarni', 'subject:testing', 'subject:encryption',
                    'should', 'encrypted', 'message', 'tag:mp_enc-decrypted'],
                   ['from:bjarni', 'subject:inline', 'subject:encryption',
                    'grand', 'tag:mp_enc-mixed-decrypted'],
                   ['from:bjarni', 'subject:signatures',
                    'tag:mp_sig-unverified'],
                   ['from:brennan', 'subject:encrypted',
                    'testing', 'purposes', 'only', 'tag:mp_enc-decrypted'],
                   ['from:brennan', 'subject:signed',
                    'tag:mp_sig-unverified'],
                   ['from:barnaby', 'subject:testing', 'soup',
                    'tag:mp_sig-unknown', 'tag:mp_enc-decrypted'],
                   ['from:square', 'subject:here', '-has:attachment'],
                   ):
        say('Searching for: %s' % search)
        results = mp.search(*search)
        assert(results.result['stats']['count'] == 1)

    say('Checking size of inbox')
    mp.order('flat-date')
    assert(mp.search('tag:inbox').result['stats']['count'] == 17)

    say('FIXME: Make sure message signatures verified')

def test_message_data():
    # Load up a message and take a look at it...
    search_md = mp.search('subject:emerging').result
    result_md = search_md['data']['metadata'][search_md['thread_ids'][0]]
    view_md = mp.view('=%s' % result_md['mid']).result

    # That loaded?
    message_md = view_md['data']['messages'][result_md['mid']]
    assert('athygli' in message_md['text_parts'][0]['data'])

    # Load up another message and take a look at it...
    search_bre = mp.search(*FROM_BRE).result
    result_bre = search_bre['data']['metadata'][search_bre['thread_ids'][0]]
    view_bre = mp.view('=%s' % result_bre['mid']).result

    # Make sure message threading is working (there are message-ids and
    # references in the test data).
    assert(len(view_bre['thread_ids']) == 3)

    # Make sure we are decoding weird headers correctly
    metadata_bre = view_bre['data']['metadata'][view_bre['message_ids'][0]]
    message_bre = view_bre['data']['messages'][view_bre['message_ids'][0]]
    from_bre = search_bre['data']['addresses'][metadata_bre['from']['aid']]
    say('Checking encoding: %s' % from_bre)
    assert('=C3' not in from_bre['fn'])
    assert('=C3' not in from_bre['address'])
    for key, val in message_bre['header_list']:
        if key.lower() not in ('from', 'to', 'cc'):
            continue
        say('Checking encoding: %s: %s' % (key, val))
        assert('utf' not in val)

    # This message broke our HTML engine that one time
    search_md = mp.search('from:heretic', 'subject:outcome').result
    result_md = search_md['data']['metadata'][search_md['thread_ids'][0]]
    view_md = mp.view('=%s' % result_md['mid'])
    assert('Outcome' in view_md.as_html())


def test_composition():
    # Create a message...
    new_mid = mp.message_compose().result['thread_ids'][0]
    assert(mp.search('tag:drafts').result['stats']['count'] == 0)
    assert(mp.search('tag:blank').result['stats']['count'] == 1)
    assert(mp.search('tag:sent').result['stats']['count'] == 0)
    assert(not os.path.exists(mailpile_sent))

    # Edit the message (moves from Blank to Draft, not findable in index)
    msg_data = {
        'to': ['%s#%s' % (MY_FROM, MY_KEYID)],
        'bcc': ['secret@test.com#%s' % MY_KEYID],
        'mid': [new_mid],
        'subject': ['This the TESTMSG subject'],
        'body': ['Hello world!']
    }
    mp.message_update(**msg_data)
    assert(mp.search('tag:drafts').result['stats']['count'] == 1)
    assert(mp.search('tag:blank').result['stats']['count'] == 0)
    assert(mp.search('TESTMSG').result['stats']['count'] == 1)
    assert(not os.path.exists(mailpile_sent))

    # Send the message (moves from Draft to Sent, is findable via. search)
    del msg_data['subject']
    msg_data['body'] = ['Hello world: thisisauniquestring :)']
    mp.message_update_send(**msg_data)
    assert(mp.search('tag:drafts').result['stats']['count'] == 0)
    assert(mp.search('tag:blank').result['stats']['count'] == 0)

    # First attempt to send should fail & record failure to event log
    config.routes['default'] = {"command": '/no/such/file'}
    config.profiles['0'].messageroute = 'default'
    mp.sendmail()
    events = mp.eventlog('source=mailpile.plugins.compose.Sendit',
                         'data_mid=%s' % new_mid).result
    assert(len(events) == 1)
    assert(events[0]['flags'] == 'i')
    assert(len(mp.eventlog('incomplete').result) == 1)

    # Second attempt should succeed!
    config.routes.default.command = '%s -i %%(rcpt)s' % mailpile_send
    mp.sendmail()
    events = mp.eventlog('source=mailpile.plugins.compose.Sendit',
                         'data_mid=%s' % new_mid).result
    assert(len(events) == 1)
    assert(events[0]['flags'] == 'c')
    assert(len(mp.eventlog('incomplete').result) == 0)

    # Verify that it actually got sent correctly
    assert('the TESTMSG subject' in contents(mailpile_sent))
    assert('thisisauniquestring' in contents(mailpile_sent))
    assert(MY_KEYID not in contents(mailpile_sent))
    assert(MY_FROM in grep('X-Args', mailpile_sent))
    assert('secret@test.com' in grep('X-Args', mailpile_sent))
    assert('secret@test.com' not in grepv('X-Args', mailpile_sent))
    for search in (['tag:sent'],
                   ['bcc:secret@test.com'],
                   ['thisisauniquestring'],
                   ['thisisauniquestring'] + MY_FROM.split(),
                   ['subject:TESTMSG']):
        say('Searching for: %s' % search)
        assert(mp.search(*search).result['stats']['count'] == 1)
    assert('thisisauniquestring' in contents(mailpile_sent))
    assert('OpenPGP: id=3D95' in contents(mailpile_sent))
    assert('; preference=encrypt' in contents(mailpile_sent))
    assert('secret@test.com' not in grepv('X-Args', mailpile_sent))
    os.remove(mailpile_sent)

    # Test the send method's "bounce" capability
    mp.message_send(mid=[new_mid], to=['nasty@test.com'])
    mp.sendmail()
    assert('thisisauniquestring' in contents(mailpile_sent))
    assert('OpenPGP: id=3D95' in contents(mailpile_sent))
    assert('; preference=encrypt' in contents(mailpile_sent))
    assert('secret@test.com' not in grepv('X-Args', mailpile_sent))
    assert('-i nasty@test.com' in contents(mailpile_sent))

def test_html():
    mp.output("jhtml")
    assert('&lt;bang&gt;' in '%s' % mp.search('in:inbox').as_html())
    mp.output("text")


try:
    do_setup()
    if '-n' in sys.argv:
        say("Skipping tests...")
    else:
        test_vcards()
        test_load_save_rescan()
        test_message_data()
        test_html()
        test_composition()
        say("Tests passed, woot!")
except:
    say("Tests FAILED!")
    print
    traceback.print_exc()


##[ Interactive mode ]########################################################

if '-i' in sys.argv:
    mp.set('prefs/vcard/importers/gravatar/0/active = true')
    mp.set('prefs/vcard/importers/gpg/0/active = true')
    mp.Interact()


##[ Cleanup ]#################################################################
os.system('rm -rf %s' % mailpile_home)

########NEW FILE########
__FILENAME__ = unsent-mail-finder
#!/usr/bin/env python2

import json
import sys

print ("""I am an unsent mail finder, due to buggy bug bugness.
Run me like so:

    cat /home/USER/.mailpile/logs/* | %s

... and I might tell you which messages didn't get sent. Adjust the
path above to match where your mailpile really is. Sorry this is so
lame!  If you ran me wrong, press CTRL+C to abort right about now.

""") % sys.argv[0]

sendits = {}
for line in sys.stdin.readlines():
  try:
    data = json.loads(line)

    d, eid, status, msg, cls = data[:5]
    if cls == '.plugins.compose.Sendit':
        if eid not in sendits and 'mid' in data[5]:
            sendits[eid] = data
        elif msg.startswith('Connecting'):
            sendits[eid][5]['OK'] = True
  except ValueError:
    print 'Unparsable: %s' % line

for eid, data in sendits.iteritems():
    if 'OK' not in data[5]:
        print 'On %s, failed to send %s' % (data[0], data[5]['mid'])

########NEW FILE########
__FILENAME__ = test_contacts
from tests.gui import MailpileSeleniumTest


class ContactsGuiTest(MailpileSeleniumTest):
    def test_add_new_contact(self):
        self.go_to_mailpile_home()
        self.navigate_to('Contacts')

        self.click_element_with_class('btn-activity-contact_add')

        self.fill_form_field('@contactname', 'Foo Bar')
        self.fill_form_field('@contactemail', 'foo.bar@test.local')
        self.submit_form('form-contact-add')

        self.navigate_to('Contacts')

        # we now should find a contact with name Foo Bar
        self.assert_link_with_text('Foo Bar')
        self.assert_link_with_text('foo.bar@test.local')

########NEW FILE########
__FILENAME__ = test_mail
from tests.gui import MailpileSeleniumTest


class MailGuiTest(MailpileSeleniumTest):
    def test_read_mail(self):
        self.go_to_mailpile_home()

        self.wait_until_element_is_visible('pile-message-8')
        self.click_element_with_link_text('Bjarni R. Einarsson, you have '
                                          'new followers on Twitter!')

        self.wait_until_element_is_visible('content-view')
        self.assertEqual("Bjarni R. Einarsson, you have new followers "
                         "on Twitter! | None's mailpile", self.page_title())
        self.assert_text('Samuel Faunt')

########NEW FILE########
__FILENAME__ = test_tags
from selenium.webdriver.common.by import By
from tests.gui import MailpileSeleniumTest


class TagGuiTest(MailpileSeleniumTest):
    def test_mark_read_unread(self):
        self.go_to_mailpile_home()
        self.wait_until_element_is_visible('pile-message-2')
        self._assert_element_has_class('pile-message-2', 'in_new')
        self._toggle_tag_bar()
        self._click_on_visible_element_with_class_name('bulk-action-read')
        self._assert_element_not_class('pile-message-2', 'in_new')
        self._toggle_tag_bar()
        self.wait_until_element_is_invisible_by_locator((By.CLASS_NAME, 'bulk-action-read'))
        self._toggle_tag_bar()
        self._click_on_visible_element_with_class_name('bulk-action-unread')
        self._assert_element_has_class('pile-message-2', 'in_new')
        self._toggle_tag_bar()
        self.wait_until_element_is_invisible_by_locator((By.CLASS_NAME, 'bulk-action-unread'))

    def _click_on_visible_element_with_class_name(self, class_name):
        self.wait_until_element_is_visible_by_locator((By.CLASS_NAME, class_name))
        unread_btn = self.find_element_by_class_name(class_name)
        unread_btn.click()

    def _toggle_tag_bar(self):
        checkbox = self.find_element_by_xpath('//*[@id="pile-message-2"]/td[6]/input')
        checkbox.click()
        return checkbox

    def _assert_element_has_class(self, element_id, class_name):
        self.wait_until_element_has_class((By.ID, element_id), class_name)

    def _assert_element_not_class(self, element_id, class_name):
        self.wait_until_element_has_not_class((By.ID, element_id), class_name)

########NEW FILE########
__FILENAME__ = test_command
import unittest
import mailpile
from mock import patch
from mailpile.commands import Action as action

from tests import MailPileUnittest


class TestCommands(MailPileUnittest):
    def test_index(self):
        res = self.mp.rescan()
        self.assertEqual(res.as_dict()["status"], 'success')

    def test_search(self):
        # A random search must return results in less than 0.2 seconds.
        res = self.mp.search("foo")
        self.assertLess(float(res.as_dict()["elapsed"]), 0.2)

    def test_optimize(self):
        res = self.mp.optimize()
        self.assertEqual(res.as_dict()["result"], True)

    def test_set(self):
        self.mp.set("prefs.num_results=1")
        results = self.mp.search("twitter")
        self.assertEqual(results.result['stats']['count'], 1)

    def test_unset(self):
        self.mp.unset("prefs.num_results")
        results = self.mp.search("twitter")
        self.assertEqual(results.result['stats']['count'], 3)

    def test_add(self):
        res = self.mp.add("tests")
        self.assertEqual(res.as_dict()["result"], True)

    def test_add_mailbox_already_in_pile(self):
        res = self.mp.add("tests")
        self.assertEqual(res.as_dict()["result"], True)

    def test_add_mailbox_no_such_directory(self):
        res = self.mp.add("wut?")
        self.assertEqual(res.as_dict()["result"], False)

    def test_output(self):
        res = self.mp.output("json")
        self.assertEqual(res.as_dict()["result"], {'output': 'json'})

    def test_help(self):
        res = self.mp.help()
        self.assertEqual(len(res.result), 3)

    def test_help_variables(self):
        res = self.mp.help_variables()
        self.assertGreater(len(res.result['variables']), 1)

    def test_help_with_param_search(self):
        res = self.mp.help('search')
        self.assertEqual(res.result['pre'], 'Search your mail!')

    def test_help_splash(self):
        res = self.mp.help_splash()
        self.assertEqual(len(res.result), 2)
        self.assertGreater(res.result['splash'], 0)
        self.assertGreater(res.as_text(), 0)

    def test_help_urlmap_as_text(self):
        res = self.mp.help_urlmap()
        self.assertEqual(len(res.result), 1)
        self.assertGreater(res.as_text(), 0)

    def test_autodiscover_crypto_action(self):
        res = self.mp.discover_crypto_policy()
        self.assertEqual(res.as_dict()["message"], 'discover_crypto_policy')
        self.assertEqual(set(), res.as_dict()['result'])

    def test_crypto_policy_action(self):
        res = self.mp.crypto_policy("foobar")
        self.assertEqual(res.as_dict()["message"], 'crypto_policy')


class TestCommandResult(MailPileUnittest):
    def test_command_result_as_dict(self):
        res = self.mp.help_splash()
        self.assertGreater(len(res.as_dict()), 0)

    def test_command_result_as_text(self):
        res = self.mp.help_splash()
        self.assertGreater(res.as_text(), 0)

    def test_command_result_as_text_for_boolean_result(self):
        res = self.mp.rescan()
        self.assertEquals(res.result['messages'], 0)
        self.assertEquals(res.result['mailboxes'], 0)
        self.assertEquals(res.result['vcards'], 0)

    def test_command_result_non_zero(self):
        res = self.mp.help_splash()
        self.assertTrue(res)

    def test_command_result_as_json(self):
        res = self.mp.help_splash()
        self.assertGreater(res.as_json(), 0)

    def test_command_result_as_html(self):
        res = self.mp.help_splash()
        self.assertGreater(res.as_html(), 0)


class TestTagging(MailPileUnittest):
    def test_addtag(self):
        pass


class TestGPG(MailPileUnittest):
    def test_key_search(self):
        gpg_result = {
            "D13C70DA": {
                "uids": [
                    {
                        "email": "smari@mailpile.is"
                    }
                ]
            }
        }

        with patch('mailpile.plugins.crypto_utils.GnuPG') as gpg_mock:
            gpg_mock.return_value.search_key.return_value = gpg_result

            res = action(self.mp._session, "crypto/gpg/searchkey", "D13C70DA")
            email = res.result["D13C70DA"]["uids"][0]["email"]
            self.assertEqual(email, "smari@mailpile.is")
            gpg_mock.return_value.search_key.assert_called_with("D13C70DA")

    def test_key_receive(self):
        gpg_result = {
            "updated": [
                {
                    "fingerprint": "08A650B8E2CBC1B02297915DC65626EED13C70DA"
                }
            ]
        }

        with patch('mailpile.plugins.crypto_utils.GnuPG') as gpg_mock:
            gpg_mock.return_value.recv_key.return_value = gpg_result

            res = action(self.mp._session, "crypto/gpg/receivekey", "D13C70DA")
            self.assertEqual(res.result[0]["updated"][0]["fingerprint"],
                             "08A650B8E2CBC1B02297915DC65626EED13C70DA")
            gpg_mock.return_value.recv_key.assert_called_with("D13C70DA")

    def test_key_import(self):
        res = action(self.mp._session, "crypto/gpg/importkey", 'testing/pub.key')
        self.assertEqual(res.result["results"]["count"], 1)

    def test_nicknym_get_key(self):
        pass

    def test_nicknym_refresh_key(self):
        pass


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_crypto_policy
from mailpile.vcard import SimpleVCard, VCardLine
from tests import MailPileUnittest

VCARD_CRYPTO_POLICY = 'X-MAILPILE-CRYPTO-POLICY'


class CryptoPolicyBaseTest(MailPileUnittest):
    def setUp(self):
        self.config.vcards.clear()
        pass

    def _add_vcard(self, full_name, email):
        card = SimpleVCard(VCardLine(name='fn', value=full_name), VCardLine(name='email', value=email))
        self.config.vcards.index_vcard(card)
        return card


class AutoDiscoverCryptoActionTest(CryptoPolicyBaseTest):
    def test_command_is_executable(self):
        res = self.mp.discover_crypto_policy()
        self.assertIsNotNone(res)

    def test_vcard_gets_updated(self):
        self._add_vcard('Signer', 'signer@test.local')
        self._add_vcard('Encrypter', 'encrypter@test.local')

        res = self.mp.discover_crypto_policy()

        self.assertEqual({'signer@test.local', 'encrypter@test.local'}, res.as_dict()['result'])
        signer_vcard = self.config.vcards.get_vcard('signer@test.local')
        encrypter_vcard = self.config.vcards.get_vcard('encrypter@test.local')
        self.assertEqual('sign', signer_vcard.get(VCARD_CRYPTO_POLICY).value)
        self.assertEqual('encrypt', encrypter_vcard.get(VCARD_CRYPTO_POLICY).value)


class UpdateCryptoPolicyForUserTest(CryptoPolicyBaseTest):
    def test_args_are_checked(self):
        self.assertEqual('error', self.mp.crypto_policy_set().as_dict()['status'])
        self.assertEqual('error', self.mp.crypto_policy_set('one arg').as_dict()['status'])

    def test_policies_are_validated(self):
        self._add_vcard('Test', 'test@test.local')

        for policy in ['default', 'none', 'sign', 'encrypt']:
            self.assertEqual('success', self.mp.crypto_policy_set('test@test.local', policy).as_dict()['status'])

        for policy in ['anything', 'else']:
            res = self.mp.crypto_policy_set('test@test.local', policy).as_dict()
            self.assertEqual('error', res['status'])
            self.assertEqual('Policy has to be one of none|sign|encrypt|sign-encrypt|default',
                             res['message'])

    def test_vcard_has_to_exist(self):
        res = self.mp.crypto_policy_set('test@test.local', 'sign').as_dict()
        self.assertEqual('error', res['status'])
        self.assertEqual('No vcard for email test@test.local!', res['message'])

    def test_vcard_is_updated(self):
        vcard = self._add_vcard('Test', 'test@test.local')
        for policy in ['none', 'sign', 'encrypt']:
            self.mp.crypto_policy_set('test@test.local', policy)
            self.assertEqual(policy, vcard.get(VCARD_CRYPTO_POLICY).value)

    def test_default_policy_removes_vcard_line(self):
        vcard = self._add_vcard('Test', 'test@test.local')
        vcard.add(VCardLine(name=VCARD_CRYPTO_POLICY, value='sign'))

        self.mp.crypto_policy_set('test@test.local', 'default')
        self.assertEqual(0, len(vcard.get_all(VCARD_CRYPTO_POLICY)))


class CryptoPolicyForUserTest(CryptoPolicyBaseTest):
    def test_no_email_provided(self):
        res = self.mp.crypto_policy().as_dict()
        self.assertEqual('error', res['status'])
        self.assertEqual('Please provide a single email address!', res['message'])

    def test_no_msg_with_email_(self):
        res = self.mp.crypto_policy('undefined@test.local').as_dict()
        self.assertEqual('success', res['status'])
        self.assertEqual('none', res['result'])

    def test_with_signed_email(self):
        res = self.mp.crypto_policy('signer@test.local').as_dict()
        self.assertEqual('success', res['status'])
        self.assertEqual('sign', res['result'])

    def test_with_encrypted_email(self):
        res = self.mp.crypto_policy('encrypter@test.local').as_dict()
        self.assertEqual('success', res['status'])
        self.assertEqual('encrypt', res['result'])

    def test_vcard_overrides_mail_history(self):
        vcard = self._add_vcard('Encrypter', 'encrypter@test.local')
        vcard.add(VCardLine(name=VCARD_CRYPTO_POLICY, value='sign'))

        res = self.mp.crypto_policy('encrypter@test.local').as_dict()

        self.assertEqual('success', res['status'])
        self.assertEqual('sign', res['result'])

########NEW FILE########
__FILENAME__ = test_performance
import unittest
from nose.tools import assert_equal, assert_less

from tests import get_shared_mailpile, MailPileUnittest


def checkSearch(postinglist_kb, query):
    class TestSearch(object):
        def __init__(self):
            self.mp = get_shared_mailpile()[0]
            self.mp.set("sys.postinglist_kb=%s" % postinglist_kb)
            self.mp.set("prefs.num_results=50")
            self.mp.set("prefs.default_order=rev-date")
            results = self.mp.search(*query)
            assert_less(float(results.as_dict()["elapsed"]), 0.2)
    return TestSearch


def test_generator():
    postinglist_kbs = [126, 62, 46, 30]
    search_queries = ['http', 'bjarni', 'ewelina', 'att:pdf',
                      'subject:bjarni', 'cowboy', 'unknown', 'zyxel']
    for postinglist_kb in postinglist_kbs:
        for search_query in search_queries:
            yield checkSearch(postinglist_kb, [search_query])

########NEW FILE########
__FILENAME__ = test_search
import unittest
from nose.tools import assert_equal, assert_less

from tests import get_shared_mailpile


def checkSearch(query, expected_count=1):
    class TestSearch(object):
        def __init__(self):
            self.mp = get_shared_mailpile()[0]
            results = self.mp.search(*query)
            assert_equal(results.result['stats']['count'], expected_count)
            assert_less(float(results.as_dict()["elapsed"]), 0.2)
    TestSearch.description = "Searching for %s" % str(query)
    return TestSearch


def test_generator():
    # All mail
    yield checkSearch(['all:mail'], 8)
    # Full match
    yield checkSearch(['brennan'])
    # Partial match
    yield checkSearch(['agirorn'])
    # Subject
    yield checkSearch(['subject:emerging'])
    # From
    yield checkSearch(['from:twitter'], 2)
    # From date
    yield checkSearch(['dates:2013-09-17', 'feministinn'])
    # with attachment
    yield checkSearch(['has:attachment'], 2)
    # In attachment name
    yield checkSearch(['att:jpg'])
    # term + term
    yield checkSearch(['brennan', 'twitter'])
    # term + special
    yield checkSearch(['brennan', 'from:twitter'])
    # Not found
    yield checkSearch(['subject:Moderation', 'kde-isl'], 0)
    yield checkSearch(['has:crypto'], 2)

########NEW FILE########
__FILENAME__ = test_ui
import unittest
import mailpile
from mailpile.ui import UserInteraction

from tests import capture, MailPileUnittest


class TestUI(MailPileUnittest):
    def _ui_swap(self):
        o, self.mp._ui = self.mp._ui, UserInteraction(self.mp._session.config)
        return o

    def test_ui_debug_log_debug_not_set(self):
        old_ui = self._ui_swap()
        try:
            with capture() as out:
                self.mp._ui._debug_log("text", UserInteraction.LOG_ALL,
                                       prefix='testprefix')
            self.assertNotIn("testprefixlog(99): text", ''.join(out))
        finally:
            self.mp._ui = old_ui

    def test_ui_debug_log_debug_set(self):
        old_ui = self._ui_swap()
        try:
            with capture() as out:
                self.mp.set("sys.debug=log")
                self.mp._ui._debug_log("text", UserInteraction.LOG_ALL,
                                       prefix='testprefix')
            self.assertIn("testprefixlog(99): text", ''.join(out))
        finally:
            self.mp._ui = old_ui

    def test_ui_log_block(self):
        old_ui = self._ui_swap()
        try:
            self.mp._ui.block()
            with capture() as out:
                self.mp._ui.log(UserInteraction.LOG_URGENT, "urgent")
                self.mp._ui.log(UserInteraction.LOG_RESULT, "result")
                self.mp._ui.log(UserInteraction.LOG_ERROR, "error")
                self.mp._ui.log(UserInteraction.LOG_NOTIFY, "notify")
                self.mp._ui.log(UserInteraction.LOG_WARNING, "warning")
                self.mp._ui.log(UserInteraction.LOG_PROGRESS, "progress")
                self.mp._ui.log(UserInteraction.LOG_DEBUG, "debug")
                self.mp._ui.log(UserInteraction.LOG_ALL, "all")
            self.assertEquals(out, ['', ''])
            with capture() as out:
                self.mp._ui.unblock()
            self.assertEquals(len(out), 2)
            self.assertEquals(out[0], '')
            # Check stripped output
            output = [x.strip() for x in out[1].split('\r')]
            self.assertEquals(output, ['urgent', 'result', 'error',
                                       'notify', 'warning', 'progress',
                                       'debug', 'all', ''])
            # Progress has \r in the end instead of \n
            progress_str = [x for x in out[1].split('\r\n')
                            if 'progress' in x][0].strip()
            self.assertEquals(progress_str,
                              ''.join(['progress', ' ' * 71, '\rdebug']))
        finally:
            self.mp._ui = old_ui

    def test_ui_clear_log(self):
        old_ui = self._ui_swap()
        try:
            self.mp._ui.block()
            with capture() as out:
                self.mp._ui.log(UserInteraction.LOG_URGENT, "urgent")
                self.mp._ui.log(UserInteraction.LOG_RESULT, "result")
                self.mp._ui.log(UserInteraction.LOG_ERROR, "error")
                self.mp._ui.log(UserInteraction.LOG_NOTIFY, "notify")
                self.mp._ui.log(UserInteraction.LOG_WARNING, "warning")
                self.mp._ui.log(UserInteraction.LOG_PROGRESS, "progress")
                self.mp._ui.log(UserInteraction.LOG_DEBUG, "debug")
                self.mp._ui.log(UserInteraction.LOG_ALL, "all")
                self.mp._ui.clear_log()
                self.mp._ui.unblock()
            self.assertEquals(out, ['', ''])
        finally:
            self.mp._ui = old_ui

    def test_ui_display_result_text(self):
        old_ui = self._ui_swap()
        try:
            with capture() as out:
                self.mp._ui.render_mode = 'text'
                result = self.mp.rescan()
                self.mp._ui.display_result(result)
            self.assertEquals(out[0], ('{\n'
                                       '    "mailboxes": 0, \n'
                                       '    "messages": 0, \n'
                                       '    "vcards": 0\n'
                                       '}\n'))
        finally:
            self.mp._ui = old_ui

########NEW FILE########
