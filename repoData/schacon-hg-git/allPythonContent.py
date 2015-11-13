__FILENAME__ = gitdirstate
import os, stat, re, errno

from mercurial import dirstate
from mercurial import hg
from mercurial import ignore
from mercurial import match as matchmod
from mercurial import osutil
from mercurial import scmutil
# pathauditor moved to pathutil in 2.8
try:
    from mercurial import pathutil
    pathutil.pathauditor
except:
    pathutil = scmutil
from mercurial import util
from mercurial.i18n import _

def gignorepats(orig, lines, root = None):
    '''parse lines (iterable) of .gitignore text, returning a tuple of
    (patterns, parse errors). These patterns should be given to compile()
    to be validated and converted into a match function.'''
    syntaxes = {'re': 'relre:', 'regexp': 'relre:', 'glob': 'relglob:'}
    syntax = 'glob:'

    patterns = []
    warnings = []

    for line in lines:
        if "#" in line:
            _commentre = re.compile(r'((^|[^\\])(\\\\)*)#.*')
            # remove comments prefixed by an even number of escapes
            line = _commentre.sub(r'\1', line)
            # fixup properly escaped comments that survived the above
            line = line.replace("\\#", "#")
        line = line.rstrip()
        if not line:
            continue

        if line.startswith('!'):
            warnings.append(_("unsupported ignore pattern '%s'") % line)
            continue
        if re.match(r'(:?.*/)?\.hg(:?/|$)', line):
            continue
        rootprefix = '%s/' % root if root else ''
        if line.startswith('/'):
            line = line[1:]
            rootsuffixes = ['']
        else:
            rootsuffixes = ['','**/']
        for rootsuffix in rootsuffixes:
            pat = syntax + rootprefix + rootsuffix + line
            for s, rels in syntaxes.iteritems():
                if line.startswith(rels):
                    pat = line
                    break
                elif line.startswith(s+':'):
                    pat = rels + line[len(s) + 1:]
                    break
            patterns.append(pat)

    return patterns, warnings

def gignore(orig, root, files, warn, extrapatterns=None):
    pats = ignore.readpats(root, files, warn)
    allpats = []
    if extrapatterns:
        allpats.extend(extrapatterns)
    for f, patlist in pats:
        allpats.extend(patlist)
    if not allpats:
        return util.never
    try:
        ignorefunc = matchmod.match(root, '', [], allpats)
    except util.Abort:
        for f, patlist in pats:
            try:
                matchmod.match(root, '', [], patlist)
            except util.Abort, inst:
                raise util.Abort('%s: %s' % (f, inst[0]))
        if extrapatterns:
            try:
                matchmod.match(root, '', [], extrapatterns)
            except util.Abort, inst:
                raise util.Abort('%s: %s' % ('extra patterns', inst[0]))
    return ignorefunc

class gitdirstate(dirstate.dirstate):
    @dirstate.rootcache('.hgignore')
    def _ignore(self):
        files = [self._join('.hgignore')]
        for name, path in self._ui.configitems("ui"):
            if name == 'ignore' or name.startswith('ignore.'):
                  files.append(util.expandpath(path))
        patterns = []
        # Only use .gitignore if there's no .hgignore 
        try:
            fp = open(files[0])
            fp.close()
        except:
            fns = self._finddotgitignores()
            for fn in fns:
                d = os.path.dirname(fn)
                fn = self.pathto(fn)
                fp = open(fn)
                pats, warnings = gignorepats(None,fp,root=d)
                for warning in warnings:
                    self._ui.warn("%s: %s\n" % (fn, warning))
                patterns.extend(pats)
        return ignore.ignore(self._root, files, self._ui.warn, extrapatterns=patterns)
    
    def _finddotgitignores(self):
        """A copy of dirstate.walk. This is called from the new _ignore method,
        which is called by dirstate.walk, which would cause infinite recursion, 
        except _finddotgitignores calls the superclass _ignore directly."""
        match = matchmod.match(self._root, self.getcwd(), ['relglob:.gitignore'])
        #TODO: need subrepos?
        subrepos = []
        unknown = True
        ignored = False
        full=True

        def fwarn(f, msg):
            self._ui.warn('%s: %s\n' % (self.pathto(f), msg))
            return False

        ignore = super(gitdirstate,self)._ignore
        dirignore = self._dirignore
        if ignored:
            ignore = util.never
            dirignore = util.never
        elif not unknown:
            # if unknown and ignored are False, skip step 2
            ignore = util.always
            dirignore = util.always

        matchfn = match.matchfn
        matchalways = match.always()
        matchtdir = match.traversedir
        dmap = self._map
        listdir = osutil.listdir
        lstat = os.lstat
        dirkind = stat.S_IFDIR
        regkind = stat.S_IFREG
        lnkkind = stat.S_IFLNK
        join = self._join

        exact = skipstep3 = False
        if matchfn == match.exact: # match.exact
            exact = True
            dirignore = util.always # skip step 2
        elif match.files() and not match.anypats(): # match.match, no patterns
            skipstep3 = True

        if not exact and self._checkcase:
            normalize = self._normalize
            skipstep3 = False
        else:
            normalize = None

        # step 1: find all explicit files
        results, work, dirsnotfound = self._walkexplicit(match, subrepos)

        skipstep3 = skipstep3 and not (work or dirsnotfound)
        work = [d for d in work if not dirignore(d)]
        wadd = work.append

        # step 2: visit subdirectories
        while work:
            nd = work.pop()
            skip = None
            if nd == '.':
                nd = ''
            else:
                skip = '.hg'
            try:
                entries = listdir(join(nd), stat=True, skip=skip)
            except OSError, inst:
                if inst.errno in (errno.EACCES, errno.ENOENT):
                    fwarn(nd, inst.strerror)
                    continue
                raise
            for f, kind, st in entries:
                if normalize:
                    nf = normalize(nd and (nd + "/" + f) or f, True, True)
                else:
                    nf = nd and (nd + "/" + f) or f
                if nf not in results:
                    if kind == dirkind:
                        if not ignore(nf):
                            if matchtdir:
                                matchtdir(nf)
                            wadd(nf)
                        if nf in dmap and (matchalways or matchfn(nf)):
                            results[nf] = None
                    elif kind == regkind or kind == lnkkind:
                        if nf in dmap:
                            if matchalways or matchfn(nf):
                                results[nf] = st
                        elif (matchalways or matchfn(nf)) and not ignore(nf):
                            results[nf] = st
                    elif nf in dmap and (matchalways or matchfn(nf)):
                        results[nf] = None

        for s in subrepos:
            del results[s]
        del results['.hg']

        # step 3: report unseen items in the dmap hash
        if not skipstep3 and not exact:
            if not results and matchalways:
                visit = dmap.keys()
            else:
                visit = [f for f in dmap if f not in results and matchfn(f)]
            visit.sort()

            if unknown:
                # unknown == True means we walked the full directory tree above.
                # So if a file is not seen it was either a) not matching matchfn
                # b) ignored, c) missing, or d) under a symlink directory.
                audit_path = pathutil.pathauditor(self._root)

                for nf in iter(visit):
                    # Report ignored items in the dmap as long as they are not
                    # under a symlink directory.
                    if audit_path.check(nf):
                        try:
                            results[nf] = lstat(join(nf))
                        except OSError:
                            # file doesn't exist
                            results[nf] = None
                    else:
                        # It's either missing or under a symlink directory
                        results[nf] = None
            else:
                # We may not have walked the full directory tree above,
                # so stat everything we missed.
                nf = iter(visit).next
                for st in util.statfiles([join(i) for i in visit]):
                    results[nf()] = st
        return results.keys()

########NEW FILE########
__FILENAME__ = gitrepo
import os
from mercurial import util
try:
    from mercurial.error import RepoError
except ImportError:
    from mercurial.repo import RepoError

try:
    from mercurial.peer import peerrepository
except ImportError:
    from mercurial.repo import repository as peerrepository

from overlay import overlayrepo

from mercurial.node import bin

class gitrepo(peerrepository):
    capabilities = ['lookup']

    def _capabilities(self):
        return self.capabilities

    def __init__(self, ui, path, create):
        if create: # pragma: no cover
            raise util.Abort('Cannot create a git repository.')
        self.ui = ui
        self.path = path
        self.localrepo = None

    def url(self):
        return self.path

    def lookup(self, key):
        if isinstance(key, str):
            return key

    def local(self):
        if not self.path:
            raise RepoError

    def heads(self):
        return []

    def listkeys(self, namespace):
        if namespace == 'namespaces':
            return {'bookmarks':''}
        elif namespace == 'bookmarks':
            if self.localrepo is not None:
                handler = self.localrepo.githandler
                handler.export_commits()
                refs = handler.fetch_pack(self.path, heads=[])
                # map any git shas that exist in hg to hg shas
                stripped_refs = dict([
                    (ref[11:], handler.map_hg_get(refs[ref]) or refs[ref])
                        for ref in refs.keys()
                            if ref.startswith('refs/heads/')])
                return stripped_refs
        return {}

    def pushkey(self, namespace, key, old, new):
        return False

instance = gitrepo

def islocal(path):
    u = util.url(path)
    return not u.scheme or u.scheme == 'file'

########NEW FILE########
__FILENAME__ = git_handler
import os, math, urllib, urllib2, re
import stat, posixpath, StringIO

from dulwich.errors import HangupException, GitProtocolError, UpdateRefsError
from dulwich.objects import Blob, Commit, Tag, Tree, parse_timezone, S_IFGITLINK
from dulwich.pack import create_delta, apply_delta
from dulwich.repo import Repo, check_ref_format
from dulwich import client
from dulwich import config as dul_config

try:
    from mercurial import bookmarks
    bookmarks.update
    from mercurial import commands
except ImportError:
    from hgext import bookmarks
try:
    from mercurial.error import RepoError
except ImportError:
    from mercurial.repo import RepoError

from mercurial.i18n import _
from mercurial.node import hex, bin, nullid
from mercurial import context, util as hgutil
from mercurial import error

import _ssh
import hg2git
import util
from overlay import overlayrepo


RE_GIT_AUTHOR = re.compile('^(.*?) ?\<(.*?)(?:\>(.*))?$')

RE_GIT_SANITIZE_AUTHOR = re.compile('[<>\n]')

RE_GIT_AUTHOR_EXTRA = re.compile('^(.*?)\ ext:\((.*)\) <(.*)\>$')

# Test for git:// and git+ssh:// URI.
# Support several URL forms, including separating the
# host and path with either a / or : (sepr)
RE_GIT_URI = re.compile(
    r'^(?P<scheme>git([+]ssh)?://)(?P<host>.*?)(:(?P<port>\d+))?'
    r'(?P<sepr>[:/])(?P<path>.*)$')

RE_NEWLINES = re.compile('[\r\n]')
RE_GIT_PROGRESS = re.compile('\((\d+)/(\d+)\)')

RE_AUTHOR_FILE = re.compile('\s*=\s*')

class GitProgress(object):
    """convert git server progress strings into mercurial progress"""
    def __init__(self, ui):
        self.ui = ui

        self.lasttopic = None
        self.msgbuf = ''

    def progress(self, msg):
        # 'Counting objects: 33640, done.\n'
        # 'Compressing objects:   0% (1/9955)   \r
        msgs = RE_NEWLINES.split(self.msgbuf + msg)
        self.msgbuf = msgs.pop()

        for msg in msgs:
            td = msg.split(':', 1)
            data = td.pop()
            if not td:
                self.flush(data)
                continue
            topic = td[0]

            m = RE_GIT_PROGRESS.search(data)
            if m:
                if self.lasttopic and self.lasttopic != topic:
                    self.flush()
                self.lasttopic = topic

                pos, total = map(int, m.group(1, 2))
                self.ui.progress(topic, pos, total=total)
            else:
                self.flush(msg)

    def flush(self, msg=None):
        if self.lasttopic:
            self.ui.progress(self.lasttopic, None)
        self.lasttopic = None
        if msg:
            self.ui.note(msg + '\n')

class GitHandler(object):
    mapfile = 'git-mapfile'
    tagsfile = 'git-tags'

    def __init__(self, dest_repo, ui):
        self.repo = dest_repo
        self.ui = ui

        if ui.configbool('git', 'intree'):
            self.gitdir = self.repo.wjoin('.git')
        else:
            self.gitdir = self.repo.join('git')

        self.init_author_file()

        self.paths = ui.configitems('paths')

        self.branch_bookmark_suffix = ui.config('git', 'branch_bookmark_suffix')

        self._map_git_real = {}
        self._map_hg_real = {}
        self.load_tags()

    @property
    def _map_git(self):
      if not self._map_git_real:
        self.load_map()
      return self._map_git_real

    @property
    def _map_hg(self):
      if not self._map_hg_real:
        self.load_map()
      return self._map_hg_real

    @hgutil.propertycache
    def git(self):
        # make the git data directory
        if os.path.exists(self.gitdir):
            return Repo(self.gitdir)
        else:
            os.mkdir(self.gitdir)
            return Repo.init_bare(self.gitdir)

    def init_author_file(self):
        self.author_map = {}
        if self.ui.config('git', 'authors'):
            f = open(self.repo.wjoin(
                self.ui.config('git', 'authors')))
            try:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    from_, to = RE_AUTHOR_FILE.split(line, 2)
                    self.author_map[from_] = to
            finally:
                f.close()

    ## FILE LOAD AND SAVE METHODS

    def map_set(self, gitsha, hgsha):
        self._map_git[gitsha] = hgsha
        self._map_hg[hgsha] = gitsha

    def map_hg_get(self, gitsha):
        return self._map_git.get(gitsha)

    def map_git_get(self, hgsha):
        return self._map_hg.get(hgsha)

    def load_map(self):
        if os.path.exists(self.repo.join(self.mapfile)):
            for line in self.repo.opener(self.mapfile):
                gitsha, hgsha = line.strip().split(' ', 1)
                self._map_git_real[gitsha] = hgsha
                self._map_hg_real[hgsha] = gitsha

    def save_map(self):
        file = self.repo.opener(self.mapfile, 'w+', atomictemp=True)
        for hgsha, gitsha in sorted(self._map_hg.iteritems()):
            file.write("%s %s\n" % (gitsha, hgsha))
        # If this complains, atomictempfile no longer has close
        file.close()

    def load_tags(self):
        self.tags = {}
        if os.path.exists(self.repo.join(self.tagsfile)):
            for line in self.repo.opener(self.tagsfile):
                sha, name = line.strip().split(' ', 1)
                self.tags[name] = sha

    def save_tags(self):
        file = self.repo.opener(self.tagsfile, 'w+', atomictemp=True)
        for name, sha in sorted(self.tags.iteritems()):
            if not self.repo.tagtype(name) == 'global':
                file.write("%s %s\n" % (sha, name))
        # If this complains, atomictempfile no longer has close
        file.close()

    ## END FILE LOAD AND SAVE METHODS

    ## COMMANDS METHODS

    def import_commits(self, remote_name):
        self.import_git_objects(remote_name)
        self.update_hg_bookmarks(self.git.get_refs())
        self.save_map()

    def fetch(self, remote, heads):
        self.export_commits()
        refs = self.fetch_pack(remote, heads)
        remote_name = self.remote_name(remote)

        oldrefs = self.git.get_refs()
        oldheads = self.repo.changelog.heads()
        imported = 0
        if refs:
            filteredrefs = self.filter_refs(refs, heads)
            imported = self.import_git_objects(remote_name, filteredrefs)
            self.import_tags(refs)
            self.update_hg_bookmarks(refs)
            if remote_name:
                self.update_remote_branches(remote_name, refs)
            elif not self.paths:
                # intial cloning
                self.update_remote_branches('default', refs)

                # "Activate" a tipmost bookmark.
                bms = getattr(self.repo['tip'], 'bookmarks',
                              lambda : None)()
                if bms:
                    bookmarks.setcurrent(self.repo, bms[0])

        def remoteref(ref):
            rn = remote_name or 'default'
            return 'refs/remotes/' + rn + ref[10:]

        self.save_map()

        if imported == 0:
            return 0

        # code taken from localrepo.py:addchangegroup
        dh = 0
        if oldheads:
            heads = self.repo.changelog.heads()
            dh = len(heads) - len(oldheads)
            for h in heads:
                if h not in oldheads and self.repo[h].closesbranch():
                    dh -= 1

        if dh < 0:
            return dh - 1
        else:
            return dh + 1

    def export_commits(self):
        try:
            self.export_git_objects()
            self.export_hg_tags()
            self.update_references()
        finally:
            self.save_map()

    def get_refs(self, remote):
        self.export_commits()
        client, path = self.get_transport_and_path(remote)
        old_refs = {}
        new_refs = {}
        def changed(refs):
            old_refs.update(refs)
            to_push = set(self.local_heads().values() + self.tags.values())
            new_refs.update(self.get_changed_refs(refs, to_push, True))
            return refs # always return the same refs to make the send a no-op

        try:
            client.send_pack(path, changed, lambda have, want: [])

            changed_refs = [ref for ref, sha in new_refs.iteritems()
                            if sha != old_refs.get(ref)]
            new = [bin(self.map_hg_get(new_refs[ref])) for ref in changed_refs]
            old = {}
            for r in old_refs:
                old_ref = self.map_hg_get(old_refs[r])
                if old_ref:
                    old[bin(old_ref)] = 1

            return old, new
        except (HangupException, GitProtocolError), e:
            raise hgutil.Abort(_("git remote error: ") + str(e))

    def push(self, remote, revs, force):
        self.export_commits()
        old_refs, new_refs = self.upload_pack(remote, revs, force)
        remote_name = self.remote_name(remote)

        if remote_name and new_refs:
            for ref, new_sha in sorted(new_refs.iteritems()):
                old_sha = old_refs.get(ref)
                if old_sha is None:
                    if self.ui.verbose:
                        self.ui.note("adding reference %s::%s => GIT:%s\n" %
                                   (remote_name, ref, new_sha[0:8]))
                    else:
                        self.ui.status("adding reference %s\n" % ref)
                elif new_sha != old_sha:
                    if self.ui.verbose:
                        self.ui.note("updating reference %s::%s => GIT:%s\n" %
                                   (remote_name, ref, new_sha[0:8]))
                    else:
                        self.ui.status("updating reference %s\n" % ref)
                else:
                    self.ui.debug("unchanged reference %s::%s => GIT:%s\n" %
                                   (remote_name, ref, new_sha[0:8]))

            self.update_remote_branches(remote_name, new_refs)
        if old_refs == new_refs:
            self.ui.status(_("no changes found\n"))
            ret = None
        elif len(new_refs) > len(old_refs):
            ret = 1 + (len(new_refs) - len(old_refs))
        elif len(old_refs) > len(new_refs):
            ret = -1 - (len(new_refs) - len(old_refs))
        else:
            ret = 1
        return ret

    def clear(self):
        mapfile = self.repo.join(self.mapfile)
        if os.path.exists(self.gitdir):
            for root, dirs, files in os.walk(self.gitdir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(self.gitdir)
        if os.path.exists(mapfile):
            os.remove(mapfile)

    # incoming support
    def getremotechanges(self, remote, revs):
        self.export_commits()
        refs = self.fetch_pack(remote.path, revs)

        # refs contains all remote refs. Prune to only those requested.
        if revs:
            reqrefs = {}
            for rev in revs:
                for n in ('refs/heads/' + rev, 'refs/tags/' + rev):
                    if n in refs:
                        reqrefs[n] = refs[n]
        else:
            reqrefs = refs

        commits = [bin(c) for c in self.getnewgitcommits(reqrefs)[1]]

        b = overlayrepo(self, commits, refs)

        return (b, commits, lambda: None)

    ## CHANGESET CONVERSION METHODS

    def export_git_objects(self):
        clnode = self.repo.changelog.node
        nodes = [clnode(n) for n in self.repo]
        export = [node for node in nodes if not hex(node) in self._map_hg]
        total = len(export)
        if not total:
            return

        self.ui.note(_("exporting hg objects to git\n"))

        # By only exporting deltas, the assertion is that all previous objects
        # for all other changesets are already present in the Git repository.
        # This assertion is necessary to prevent redundant work. Here, nodes,
        # and therefore export, is in topological order. By definition,
        # export[0]'s parents must be present in Git, so we start the
        # incremental exporter from there.
        pctx = self.repo[export[0]].p1()
        pnode = pctx.node()
        if pnode == nullid:
            gitcommit = None
        else:
            gitsha = self._map_hg[hex(pnode)]
            try:
                gitcommit = self.git[gitsha]
            except KeyError:
                raise hgutil.Abort(_('Parent SHA-1 not present in Git'
                                     'repo: %s' % gitsha))

        exporter = hg2git.IncrementalChangesetExporter(
            self.repo, pctx, self.git.object_store, gitcommit)

        for i, rev in enumerate(export):
            self.ui.progress('exporting', i, total=total)
            ctx = self.repo.changectx(rev)
            state = ctx.extra().get('hg-git', None)
            if state == 'octopus':
                self.ui.debug("revision %d is a part "
                              "of octopus explosion\n" % ctx.rev())
                continue
            self.export_hg_commit(rev, exporter)
        self.ui.progress('exporting', None, total=total)


    # convert this commit into git objects
    # go through the manifest, convert all blobs/trees we don't have
    # write the commit object (with metadata info)
    def export_hg_commit(self, rev, exporter):
        self.ui.note(_("converting revision %s\n") % hex(rev))

        oldenc = self.swap_out_encoding()

        ctx = self.repo.changectx(rev)
        extra = ctx.extra()

        commit = Commit()

        (time, timezone) = ctx.date()
        # work around to bad timezone offets - dulwich does not handle
        # sub minute based timezones. In the one known case, it was a
        # manual edit that led to the unusual value. Based on that,
        # there is no reason to round one way or the other, so do the
        # simplest and round down.
        timezone -= (timezone % 60)
        commit.author = self.get_git_author(ctx)
        commit.author_time = int(time)
        commit.author_timezone = -timezone

        if 'committer' in extra:
            # fixup timezone
            (name, timestamp, timezone) = extra['committer'].rsplit(' ', 2)
            commit.committer = name
            commit.commit_time = timestamp

            # work around a timezone format change
            if int(timezone) % 60 != 0: #pragma: no cover
                timezone = parse_timezone(timezone)
                # Newer versions of Dulwich return a tuple here
                if isinstance(timezone, tuple):
                    timezone, neg_utc = timezone
                    commit._commit_timezone_neg_utc = neg_utc
            else:
                timezone = -int(timezone)
            commit.commit_timezone = timezone
        else:
            commit.committer = commit.author
            commit.commit_time = commit.author_time
            commit.commit_timezone = commit.author_timezone

        commit.parents = []
        for parent in self.get_git_parents(ctx):
            hgsha = hex(parent.node())
            git_sha = self.map_git_get(hgsha)
            if git_sha:
                if git_sha not in self.git.object_store:
                    raise hgutil.Abort(_('Parent SHA-1 not present in Git'
                                         'repo: %s' % git_sha))

                commit.parents.append(git_sha)

        commit.message = self.get_git_message(ctx)

        if 'encoding' in extra:
            commit.encoding = extra['encoding']

        for obj, nodeid in exporter.update_changeset(ctx):
            if obj.id not in self.git.object_store:
                self.git.object_store.add_object(obj)

        tree_sha = exporter.root_tree_sha

        if tree_sha not in self.git.object_store:
            raise hgutil.Abort(_('Tree SHA-1 not present in Git repo: %s' %
                tree_sha))

        commit.tree = tree_sha

        if commit.id not in self.git.object_store:
            self.git.object_store.add_object(commit)
        self.map_set(commit.id, ctx.hex())

        self.swap_out_encoding(oldenc)
        return commit.id

    def get_valid_git_username_email(self, name):
        r"""Sanitize usernames and emails to fit git's restrictions.

        The following is taken from the man page of git's fast-import
        command:

            [...] Likewise LF means one (and only one) linefeed [...]

            committer
                The committer command indicates who made this commit,
                and when they made it.

                Here <name> is the person's display name (for example
                "Com M Itter") and <email> is the person's email address
                ("cm@example.com[1]"). LT and GT are the literal
                less-than (\x3c) and greater-than (\x3e) symbols. These
                are required to delimit the email address from the other
                fields in the line. Note that <name> and <email> are
                free-form and may contain any sequence of bytes, except
                LT, GT and LF. <name> is typically UTF-8 encoded.

        Accordingly, this function makes sure that there are none of the
        characters <, >, or \n in any string which will be used for
        a git username or email. Before this, it first removes left
        angle brackets and spaces from the beginning, and right angle
        brackets and spaces from the end, of this string, to convert
        such things as " <john@doe.com> " to "john@doe.com" for
        convenience.

        TESTS:

        >>> from mercurial.ui import ui
        >>> g = GitHandler('', ui()).get_valid_git_username_email
        >>> g('John Doe')
        'John Doe'
        >>> g('john@doe.com')
        'john@doe.com'
        >>> g(' <john@doe.com> ')
        'john@doe.com'
        >>> g('    <random<\n<garbage\n>  > > ')
        'random???garbage?'
        >>> g('Typo in hgrc >but.hg-git@handles.it.gracefully>')
        'Typo in hgrc ?but.hg-git@handles.it.gracefully'
        """
        return RE_GIT_SANITIZE_AUTHOR.sub('?', name.lstrip('< ').rstrip('> '))

    def get_git_author(self, ctx):
        # hg authors might not have emails
        author = ctx.user()

        # see if a translation exists
        author = self.author_map.get(author, author)

        # check for git author pattern compliance
        a = RE_GIT_AUTHOR.match(author)

        if a:
            name = self.get_valid_git_username_email(a.group(1))
            email = self.get_valid_git_username_email(a.group(2))
            if a.group(3) != None and len(a.group(3)) != 0:
                name += ' ext:(' + urllib.quote(a.group(3)) + ')'
            author = self.get_valid_git_username_email(name) + ' <' + self.get_valid_git_username_email(email) + '>'
        elif '@' in author:
            author = self.get_valid_git_username_email(author) + ' <' + self.get_valid_git_username_email(author) + '>'
        else:
            author = self.get_valid_git_username_email(author) + ' <none@none>'

        if 'author' in ctx.extra():
            author = "".join(apply_delta(author, ctx.extra()['author']))

        return author

    def get_git_parents(self, ctx):
        def is_octopus_part(ctx):
            return ctx.extra().get('hg-git', None) in ('octopus', 'octopus-done')

        parents = []
        if ctx.extra().get('hg-git', None) == 'octopus-done':
            # implode octopus parents
            part = ctx
            while is_octopus_part(part):
                (p1, p2) = part.parents()
                assert ctx.extra().get('hg-git', None) != 'octopus'
                parents.append(p1)
                part = p2
            parents.append(p2)
        else:
            parents = ctx.parents()

        return parents

    def get_git_message(self, ctx):
        extra = ctx.extra()

        message = ctx.description() + "\n"
        if 'message' in extra:
            message = "".join(apply_delta(message, extra['message']))

        # HG EXTRA INFORMATION
        add_extras = False
        extra_message = ''
        if not ctx.branch() == 'default':
            add_extras = True
            extra_message += "branch : " + ctx.branch() + "\n"

        renames = []
        for f in ctx.files():
            if f not in ctx.manifest():
                continue
            rename = ctx.filectx(f).renamed()
            if rename:
                renames.append((rename[0], f))

        if renames:
            add_extras = True
            for oldfile, newfile in renames:
                extra_message += "rename : " + oldfile + " => " + newfile + "\n"

        for key, value in extra.iteritems():
            if key in ('author', 'committer', 'encoding', 'message', 'branch', 'hg-git'):
                continue
            else:
                add_extras = True
                extra_message += "extra : " + key + " : " +  urllib.quote(value) + "\n"

        if add_extras:
            message += "\n--HG--\n" + extra_message

        return message

    def getnewgitcommits(self, refs=None):
        # import heads and fetched tags as remote references
        todo = []
        done = set()
        convert_list = {}

        # get a list of all the head shas
        seenheads = set()
        if refs is None:
            refs = self.git.refs.as_dict()
        if refs:
            for sha in refs.itervalues():
                # refs contains all the refs in the server, not just the ones
                # we are pulling
                if sha in self.git.object_store:
                    obj = self.git.get_object(sha)
                    while isinstance(obj, Tag):
                        obj_type, sha = obj.object
                        obj = self.git.get_object(sha)
                    if isinstance (obj, Commit) and sha not in seenheads:
                        seenheads.add(sha)
                        todo.append(sha)

        # sort by commit date
        def commitdate(sha):
            obj = self.git.get_object(sha)
            return obj.commit_time-obj.commit_timezone

        todo.sort(key=commitdate, reverse=True)

        # traverse the heads getting a list of all the unique commits in
        # topological order
        commits = []
        seen = set(todo)
        while todo:
            sha = todo[-1]
            if sha in done or sha in self._map_git:
                todo.pop()
                continue
            assert isinstance(sha, str)
            if sha in convert_list:
                obj = convert_list[sha]
            else:
                obj = self.git.get_object(sha)
                convert_list[sha] = obj
            assert isinstance(obj, Commit)
            for p in obj.parents:
                if p not in done and p not in self._map_git:
                    todo.append(p)
                    # process parents of a commit before processing the
                    # commit itself, and come back to this commit later
                    break
            else:
                commits.append(sha)
                done.add(sha)
                todo.pop()

        return convert_list, commits

    def import_git_objects(self, remote_name=None, refs=None):
        convert_list, commits = self.getnewgitcommits(refs)
        # import each of the commits, oldest first
        total = len(commits)
        if total:
            self.ui.status(_("importing git objects into hg\n"))
        else:
            self.ui.status(_("no changes found\n"))

        for i, csha in enumerate(commits):
            self.ui.progress('importing', i, total=total, unit='commits')
            commit = convert_list[csha]
            self.import_git_commit(commit)
        self.ui.progress('importing', None, total=total, unit='commits')

        # TODO if the tags cache is used, remove any dangling tag references
        return total

    def import_git_commit(self, commit):
        self.ui.debug(_("importing: %s\n") % commit.id)

        (strip_message, hg_renames,
         hg_branch, extra) = self.extract_hg_metadata(commit.message)

        gparents = map(self.map_hg_get, commit.parents)

        for parent in gparents:
            if parent not in self.repo:
                raise hgutil.Abort(_('you appear to have run strip - '
                                     'please run hg git-cleanup'))

        # get a list of the changed, added, removed files and gitlinks
        files, gitlinks = self.get_files_changed(commit)

        git_commit_tree = self.git[commit.tree]

        # Analyze hgsubstate and build an updated version using SHAs from
        # gitlinks. Order of application:
        # - preexisting .hgsubstate in git tree
        # - .hgsubstate from hg parent
        # - changes in gitlinks
        hgsubstate = util.parse_hgsubstate(
            self.git_file_readlines(git_commit_tree, '.hgsubstate'))
        parentsubdata = ''
        if gparents:
            p1ctx = self.repo.changectx(gparents[0])
            if '.hgsubstate' in p1ctx:
                parentsubdata = p1ctx.filectx('.hgsubstate').data().splitlines()
                parentsubstate = util.parse_hgsubstate(parentsubdata)
                for path, sha in parentsubstate.iteritems():
                    hgsubstate[path] = sha
        for path, sha in gitlinks.iteritems():
            if sha is None:
                hgsubstate.pop(path, None)
            else:
                hgsubstate[path] = sha
        # in case .hgsubstate wasn't among changed files
        # force its inclusion
        if not hgsubstate and parentsubdata:
            files['.hgsubstate'] = True, None, None
        elif util.serialize_hgsubstate(hgsubstate) != parentsubdata:
            files['.hgsubstate'] = False, 0100644, None

        # Analyze .hgsub and merge with .gitmodules
        hgsub = None
        gitmodules = self.parse_gitmodules(git_commit_tree)
        if gitmodules:
            hgsub = util.parse_hgsub(self.git_file_readlines(git_commit_tree, '.hgsub'))
            for (sm_path, sm_url, sm_name) in gitmodules:
                hgsub[sm_path] = '[git]' + sm_url
            files['.hgsub'] = (False, 0100644, None)
        elif commit.parents and '.gitmodules' in self.git[self.git[commit.parents[0]].tree]:
            # no .gitmodules in this commit, however present in the parent
            # mark its hg counterpart as deleted (assuming .hgsub is there
            # due to the same import_git_commit process
            files['.hgsub'] = (True, 0100644, None)

        date = (commit.author_time, -commit.author_timezone)
        text = strip_message

        origtext = text
        try:
            text.decode('utf-8')
        except UnicodeDecodeError:
            text = self.decode_guess(text, commit.encoding)

        text = '\n'.join([l.rstrip() for l in text.splitlines()]).strip('\n')
        if text + '\n' != origtext:
            extra['message'] = create_delta(text +'\n', origtext)

        author = commit.author

        # convert extra data back to the end
        if ' ext:' in commit.author:
            m = RE_GIT_AUTHOR_EXTRA.match(commit.author)
            if m:
                name = m.group(1)
                ex = urllib.unquote(m.group(2))
                email = m.group(3)
                author = name + ' <' + email + '>' + ex

        if ' <none@none>' in commit.author:
            author = commit.author[:-12]

        try:
            author.decode('utf-8')
        except UnicodeDecodeError:
            origauthor = author
            author = self.decode_guess(author, commit.encoding)
            extra['author'] = create_delta(author, origauthor)

        oldenc = self.swap_out_encoding()

        def findconvergedfiles(p1, p2):
            # If any files have the same contents in both parents of a merge
            # (and are therefore not reported as changed by Git) but are at
            # different file revisions in Mercurial (because they arrived at
            # those contents in different ways), we need to include them in
            # the list of changed files so that Mercurial can join up their
            # filelog histories (same as if the merge was done in Mercurial to
            # begin with).
            if p2 == nullid:
                return []
            manifest1 = self.repo.changectx(p1).manifest()
            manifest2 = self.repo.changectx(p2).manifest()
            return [path for path, node1 in manifest1.iteritems()
                    if path not in files and manifest2.get(path, node1) != node1]

        def getfilectx(repo, memctx, f):
            info = files.get(f)
            if info != None:
                # it's a file reported as modified from Git
                delete, mode, sha = info
                if delete:
                    raise IOError

                if not sha: # indicates there's no git counterpart
                    e = ''
                    copied_path = None
                    if '.hgsubstate' == f:
                        data = util.serialize_hgsubstate(hgsubstate)
                    elif '.hgsub' == f:
                        data = util.serialize_hgsub(hgsub)
                else:
                    data = self.git[sha].data
                    copied_path = hg_renames.get(f)
                    e = self.convert_git_int_mode(mode)
            else:
                # it's a converged file
                fc = context.filectx(self.repo, f, changeid=memctx.p1().rev())
                data = fc.data()
                e = fc.flags()
                copied_path = fc.renamed()

            return context.memfilectx(f, data, 'l' in e, 'x' in e, copied_path)

        p1, p2 = (nullid, nullid)
        octopus = False

        if len(gparents) > 1:
            # merge, possibly octopus
            def commit_octopus(p1, p2):
                ctx = context.memctx(self.repo, (p1, p2), text,
                                     list(files) + findconvergedfiles(p1, p2),
                                     getfilectx, author, date, {'hg-git': 'octopus'})
                return hex(self.repo.commitctx(ctx))

            octopus = len(gparents) > 2
            p2 = gparents.pop()
            p1 = gparents.pop()
            while len(gparents) > 0:
                p2 = commit_octopus(p1, p2)
                p1 = gparents.pop()
        else:
            if gparents:
                p1 = gparents.pop()

        pa = None
        if not (p2 == nullid):
            node1 = self.repo.changectx(p1)
            node2 = self.repo.changectx(p2)
            pa = node1.ancestor(node2)

        # if named branch, add to extra
        if hg_branch:
            extra['branch'] = hg_branch

        # if committer is different than author, add it to extra
        if commit.author != commit.committer \
               or commit.author_time != commit.commit_time \
               or commit.author_timezone != commit.commit_timezone:
            extra['committer'] = "%s %d %d" % (
                commit.committer, commit.commit_time, -commit.commit_timezone)

        if commit.encoding:
            extra['encoding'] = commit.encoding

        if hg_branch:
            extra['branch'] = hg_branch

        if octopus:
            extra['hg-git'] ='octopus-done'

        ctx = context.memctx(self.repo, (p1, p2), text,
                             list(files) + findconvergedfiles(p1, p2),
                             getfilectx, author, date, extra)

        node = self.repo.commitctx(ctx)

        self.swap_out_encoding(oldenc)

        # save changeset to mapping file
        cs = hex(node)
        self.map_set(commit.id, cs)

    ## PACK UPLOADING AND FETCHING

    def upload_pack(self, remote, revs, force):
        client, path = self.get_transport_and_path(remote)
        old_refs = {}
        change_totals = {}

        def changed(refs):
            self.ui.status(_("searching for changes\n"))
            old_refs.update(refs)
            to_push = revs or set(self.local_heads().values() + self.tags.values())
            return self.get_changed_refs(refs, to_push, force)

        def genpack(have, want):
            commits = []
            for mo in self.git.object_store.find_missing_objects(have, want):
                (sha, name) = mo
                o = self.git.object_store[sha]
                t = type(o)
                change_totals[t] = change_totals.get(t, 0) + 1
                if isinstance(o, Commit):
                    commits.append(sha)
            commit_count = len(commits)
            self.ui.note(_("%d commits found\n") % commit_count)
            if commit_count > 0:
                self.ui.debug(_("list of commits:\n"))
                for commit in commits:
                    self.ui.debug("%s\n" % commit)
                self.ui.status(_("adding objects\n"))
            return self.git.object_store.generate_pack_contents(have, want)

        try:
            new_refs = client.send_pack(path, changed, genpack)
            if len(change_totals) > 0:
                self.ui.status(_("added %d commits with %d trees"
                                 " and %d blobs\n") %
                               (change_totals.get(Commit, 0),
                                change_totals.get(Tree, 0),
                                change_totals.get(Blob, 0)))
            return old_refs, new_refs
        except (HangupException, GitProtocolError), e:
            raise hgutil.Abort(_("git remote error: ") + str(e))

    def get_changed_refs(self, refs, revs, force):
        new_refs = refs.copy()

        #The remote repo is empty and the local one doesn't have bookmarks/tags
        if refs.keys()[0] == 'capabilities^{}':
            if not self.local_heads():
                tip = self.repo.lookup('tip')
                if tip != nullid:
                    del new_refs['capabilities^{}']
                    tip = hex(tip)
                    try:
                        commands.bookmark(self.ui, self.repo, 'master', tip, force=True)
                    except NameError:
                        bookmarks.bookmark(self.ui, self.repo, 'master', tip, force=True)
                    bookmarks.setcurrent(self.repo, 'master')
                    new_refs['refs/heads/master'] = self.map_git_get(tip)

        for rev in revs:
            ctx = self.repo[rev]
            if getattr(ctx, 'bookmarks', None):
                labels = lambda c: ctx.tags() + [
                                fltr for fltr, bm
                                in self._filter_for_bookmarks(ctx.bookmarks())
                            ]
            else:
                labels = lambda c: ctx.tags()
            prep = lambda itr: [i.replace(' ', '_') for i in itr]

            heads = [t for t in prep(labels(ctx)) if t in self.local_heads()]
            tags = [t for t in prep(labels(ctx)) if t in self.tags]

            if not (heads or tags):
                raise hgutil.Abort("revision %s cannot be pushed since"
                                   " it doesn't have a ref" % ctx)

            # Check if the tags the server is advertising are annotated tags,
            # by attempting to retrieve it from the our git repo, and building a
            # list of these tags.
            #
            # This is possible, even though (currently) annotated tags are
            # dereferenced and stored as lightweight ones, as the annotated tag
            # is still stored in the git repo.
            uptodate_annotated_tags = []
            for r in tags:
                ref = 'refs/tags/'+r
                # Check tag.
                if not ref in refs:
                    continue
                try:
                    # We're not using Repo.tag(), as it's deprecated.
                    tag = self.git.get_object(refs[ref])
                    if not isinstance(tag, Tag):
                        continue
                except KeyError:
                    continue

                # If we've reached here, the tag's good.
                uptodate_annotated_tags.append(ref)

            for r in heads + tags:
                if r in heads:
                    ref = 'refs/heads/'+r
                else:
                    ref = 'refs/tags/'+r

                if ref not in refs:
                    new_refs[ref] = self.map_git_get(ctx.hex())
                elif new_refs[ref] in self._map_git:
                    rctx = self.repo[self.map_hg_get(new_refs[ref])]
                    if rctx.ancestor(ctx) == rctx or force:
                        new_refs[ref] = self.map_git_get(ctx.hex())
                    else:
                        raise hgutil.Abort("pushing %s overwrites %s"
                                           % (ref, ctx))
                elif ref in uptodate_annotated_tags:
                    # we already have the annotated tag.
                    pass
                else:
                    raise hgutil.Abort(
                        "branch '%s' changed on the server, "
                        "please pull and merge before pushing" % ref)

        return new_refs

    def fetch_pack(self, remote_name, heads=None):
        client, path = self.get_transport_and_path(remote_name)
        graphwalker = self.git.get_graph_walker()

        def determine_wants(refs):
            filteredrefs = self.filter_refs(refs, heads)
            return [x for x in filteredrefs.itervalues() if x not in self.git]

        try:
            progress = GitProgress(self.ui)
            f = StringIO.StringIO()
            ret = client.fetch_pack(path, determine_wants, graphwalker, f.write, progress.progress)
            if(f.pos != 0):
                f.seek(0)
                po =  self.git.object_store.add_thin_pack(f.read, None)
            progress.flush()

            # For empty repos dulwich gives us None, but since later
            # we want to iterate over this, we really want an empty
            # iterable
            return ret if ret else {}
        except (HangupException, GitProtocolError), e:
            raise hgutil.Abort(_("git remote error: ") + str(e))

    ## REFERENCES HANDLING

    def filter_refs(self, refs, heads):
        '''For a dictionary of refs: shas, if heads is None then return refs
        that match the heads. Otherwise, return refs that are heads or tags.

        '''
        filteredrefs = {}
        if heads is not None:
            # contains pairs of ('refs/(heads|tags|...)/foo', 'foo')
            # if ref is just '<foo>', then we get ('foo', 'foo')
            stripped_refs = [
                (r, r[r.find('/', r.find('/')+1)+1:])
                    for r in refs]
            for h in heads:
                r = [pair[0] for pair in stripped_refs if pair[1] == h]
                if not r:
                    raise hgutil.Abort("ref %s not found on remote server" % h)
                elif len(r) == 1:
                    filteredrefs[r[0]] = refs[r[0]]
                else:
                    raise hgutil.Abort("ambiguous reference %s: %r" % (h, r))
        else:
            for ref, sha in refs.iteritems():
                if (not ref.endswith('^{}')
                    and (ref.startswith('refs/heads/')
                         or ref.startswith('refs/tags/'))):
                    filteredrefs[ref] = sha
        return filteredrefs

    def update_references(self):
        heads = self.local_heads()

        # Create a local Git branch name for each
        # Mercurial bookmark.
        for key in heads:
            git_ref = self.map_git_get(heads[key])
            if git_ref:
                self.git.refs['refs/heads/' + key] = self.map_git_get(heads[key])

    def export_hg_tags(self):
        for tag, sha in self.repo.tags().iteritems():
            if self.repo.tagtype(tag) in ('global', 'git'):
                tag = tag.replace(' ', '_')
                target = self.map_git_get(hex(sha))
                if target is not None:
                    tag_refname = 'refs/tags/' + tag
                    if(check_ref_format(tag_refname)):
                      self.git.refs[tag_refname] = target
                      self.tags[tag] = hex(sha)
                    else:
                      self.repo.ui.warn(
                        'Skipping export of tag %s because it '
                        'has invalid name as a git refname.\n' % tag)
                else:
                    self.repo.ui.warn(
                        'Skipping export of tag %s because it '
                        'has no matching git revision.\n' % tag)

    def _filter_for_bookmarks(self, bms):
        if not self.branch_bookmark_suffix:
            return [(bm, bm) for bm in bms]
        else:
            def _filter_bm(bm):
                if bm.endswith(self.branch_bookmark_suffix):
                    return bm[0:-(len(self.branch_bookmark_suffix))]
                else:
                    return bm
            return [(_filter_bm(bm), bm) for bm in bms]

    def local_heads(self):
        try:
            if getattr(bookmarks, 'parse', None):
                bms = bookmarks.parse(self.repo)
            else:
                bms = self.repo._bookmarks
            return dict([(filtered_bm, hex(bms[bm])) for
                        filtered_bm, bm in self._filter_for_bookmarks(bms)])
        except AttributeError: #pragma: no cover
            return {}

    def import_tags(self, refs):
        keys = refs.keys()
        if not keys:
            return
        repotags = self.repo.tags()
        for k in keys[:]:
            ref_name = k
            parts = k.split('/')
            if parts[0] == 'refs' and parts[1] == 'tags':
                ref_name = "/".join([v for v in parts[2:]])
                # refs contains all the refs in the server, not just
                # the ones we are pulling
                if refs[k] not in self.git.object_store:
                    continue
                if ref_name[-3:] == '^{}':
                    ref_name = ref_name[:-3]
                if not ref_name in repotags:
                    obj = self.git.get_object(refs[k])
                    sha = None
                    if isinstance (obj, Commit): # lightweight
                        sha = self.map_hg_get(refs[k])
                        if sha is not None:
                            self.tags[ref_name] = sha
                    elif isinstance (obj, Tag): # annotated
                        (obj_type, obj_sha) = obj.object
                        obj = self.git.get_object(obj_sha)
                        if isinstance (obj, Commit):
                            sha = self.map_hg_get(obj_sha)
                            # TODO: better handling for annotated tags
                            if sha is not None:
                                self.tags[ref_name] = sha
        self.save_tags()

    def update_hg_bookmarks(self, refs):
        try:
            oldbm = getattr(bookmarks, 'parse', None)
            if oldbm:
                bms = bookmarks.parse(self.repo)
            else:
                bms = self.repo._bookmarks

            heads = dict([(ref[11:],refs[ref]) for ref in refs
                          if ref.startswith('refs/heads/')])

            suffix = self.branch_bookmark_suffix or ''
            for head, sha in heads.iteritems():
                # refs contains all the refs in the server, not just
                # the ones we are pulling
                hgsha = self.map_hg_get(sha)
                if hgsha is None:
                    continue
                hgsha = bin(hgsha)
                if not head in bms:
                    # new branch
                    bms[head + suffix] = hgsha
                else:
                    bm = self.repo[bms[head]]
                    if bm.ancestor(self.repo[hgsha]) == bm:
                        # fast forward
                        bms[head + suffix] = hgsha

            if heads:
                if oldbm:
                    bookmarks.write(self.repo, bms)
                else:
                    self.repo._bookmarks = bms
                    if getattr(bms, 'write', None): # hg >= 2.5
                        bms.write()
                    else: # hg < 2.5
                        bookmarks.write(self.repo)

        except AttributeError:
            self.ui.warn(_('creating bookmarks failed, do you have'
                         ' bookmarks enabled?\n'))

    def update_remote_branches(self, remote_name, refs):
        tagfile = self.repo.join(os.path.join('git-remote-refs'))
        tags = self.repo.gitrefs()
        # since we re-write all refs for this remote each time, prune
        # all entries matching this remote from our tags list now so
        # that we avoid any stale refs hanging around forever
        for t in list(tags):
            if t.startswith(remote_name + '/'):
                del tags[t]
        tags = dict((k, hex(v)) for k, v in tags.iteritems())
        store = self.git.object_store
        for ref_name, sha in refs.iteritems():
            if ref_name.startswith('refs/heads'):
                hgsha = self.map_hg_get(sha)
                if hgsha is None or hgsha not in self.repo:
                    continue
                head = ref_name[11:]
                tags['/'.join((remote_name, head))] = hgsha
                # TODO(durin42): what is this doing?
                new_ref = 'refs/remotes/%s/%s' % (remote_name, head)
                self.git.refs[new_ref] = sha
            elif (ref_name.startswith('refs/tags')
                  and not ref_name.endswith('^{}')):
                self.git.refs[ref_name] = sha

        tf = open(tagfile, 'wb')
        for tag, node in tags.iteritems():
            tf.write('%s %s\n' % (node, tag))
        tf.close()


    ## UTILITY FUNCTIONS

    def convert_git_int_mode(self, mode):
        # TODO: make these into constants
        convert = {
         0100644: '',
         0100755: 'x',
         0120000: 'l'}
        if mode in convert:
            return convert[mode]
        return ''

    def extract_hg_metadata(self, message):
        split = message.split("\n--HG--\n", 1)
        renames = {}
        extra = {}
        branch = False
        if len(split) == 2:
            message, meta = split
            lines = meta.split("\n")
            for line in lines:
                if line == '':
                    continue

                if ' : ' not in line:
                    break
                command, data = line.split(" : ", 1)

                if command == 'rename':
                    before, after = data.split(" => ", 1)
                    renames[after] = before
                if command == 'branch':
                    branch = data
                if command == 'extra':
                    before, after = data.split(" : ", 1)
                    extra[before] = urllib.unquote(after)
        return (message, renames, branch, extra)

    def get_file(self, commit, f):
        otree = self.git.tree(commit.tree)
        parts = f.split('/')
        for part in parts:
            (mode, sha) = otree[part]
            obj = self.git.get_object(sha)
            if isinstance (obj, Blob):
                return (mode, sha, obj._text)
            elif isinstance(obj, Tree):
                otree = obj

    def get_files_changed(self, commit):
        tree = commit.tree
        btree = None

        if commit.parents:
            btree = self.git[commit.parents[0]].tree

        changes = self.git.object_store.tree_changes(btree, tree)
        files = {}
        gitlinks = {}
        for (oldfile, newfile), (oldmode, newmode), (oldsha, newsha) in changes:
            # actions are described by the following table ('no' means 'does not
            # exist'):
            #    old        new     |    action
            #     no        file    |  record file
            #     no      gitlink   |  record gitlink
            #    file        no     |  delete file
            #    file       file    |  record file
            #    file     gitlink   |  delete file and record gitlink
            #  gitlink       no     |  delete gitlink
            #  gitlink      file    |  delete gitlink and record file
            #  gitlink    gitlink   |  record gitlink
            if newmode == 0160000:
                # new = gitlink
                gitlinks[newfile] = newsha
                if oldmode is not None and oldmode != 0160000:
                    # file -> gitlink
                    files[oldfile] = True, None, None
                continue
            if oldmode == 0160000 and newmode != 0160000:
                # gitlink -> no/file (gitlink -> gitlink is covered above)
                gitlinks[oldfile] = None
                continue
            if newfile is not None:
                # new = file
                files[newfile] = False, newmode, newsha
            else:
                # old = file
                files[oldfile] = True, None, None

        return files, gitlinks

    def parse_gitmodules(self, tree_obj):
        """Parse .gitmodules from a git tree specified by tree_obj

           :return: list of tuples (submodule path, url, name),
           where name is quoted part of the section's name, or
           empty list if nothing found
        """
        rv = []
        try:
            unused_mode,gitmodules_sha = tree_obj['.gitmodules']
        except KeyError:
            return rv
        gitmodules_content = self.git[gitmodules_sha].data
        fo = StringIO.StringIO(gitmodules_content)
        tt = dul_config.ConfigFile.from_file(fo)
        for section in tt.keys():
            section_kind, section_name = section
            if section_kind == 'submodule':
                sm_path = tt.get(section, 'path')
                sm_url  = tt.get(section, 'url')
                rv.append((sm_path, sm_url, section_name))
        return rv

    def git_file_readlines(self, tree_obj, fname):
        """Read content of a named entry from the git commit tree

           :return: list of lines
        """
        if fname in tree_obj:
            unused_mode, sha = tree_obj[fname]
            content = self.git[sha].data
            return content.splitlines()
        return []

    def remote_name(self, remote):
        names = [name for name, path in self.paths if path == remote]
        if names:
            return names[0]

    # Stolen from hgsubversion
    def swap_out_encoding(self, new_encoding='UTF-8'):
        try:
            from mercurial import encoding
            old = encoding.encoding
            encoding.encoding = new_encoding
        except ImportError:
            old = hgutil._encoding
            hgutil._encoding = new_encoding
        return old

    def decode_guess(self, string, encoding):
        # text is not valid utf-8, try to make sense of it
        if encoding:
            try:
                return string.decode(encoding).encode('utf-8')
            except UnicodeDecodeError:
                pass

        try:
            return string.decode('latin-1').encode('utf-8')
        except UnicodeDecodeError:
            return string.decode('ascii', 'replace').encode('utf-8')

    def get_transport_and_path(self, uri):
        # pass hg's ui.ssh config to dulwich
        if not issubclass(client.get_ssh_vendor, _ssh.SSHVendor):
            client.get_ssh_vendor = _ssh.generate_ssh_vendor(self.ui)

        git_match = RE_GIT_URI.match(uri)
        if git_match:
            res = git_match.groupdict()
            transport = client.SSHGitClient if 'ssh' in res['scheme'] else client.TCPGitClient
            host, port, sepr, path = res['host'], res['port'], res['sepr'], res['path']
            if sepr == '/' and not path.startswith('~'):
                path = '/' + path
            # strip trailing slash for heroku-style URLs
            # ssh+git://git@heroku.com:project.git/
            if sepr == ':' and path.endswith('.git/'):
                path = path.rstrip('/')
            if port:
                client.port = port

            return transport(host, thin_packs=False, port=port), path

        httpclient = getattr(client, 'HttpGitClient', None)

        if uri.startswith('git+http://') or uri.startswith('git+https://'):
            uri = uri[4:]

        if uri.startswith('http://') or uri.startswith('https://'):
            if not httpclient:
                raise RepoError('git via HTTP requires dulwich 0.8.1 or later')
            else:
                auth_handler = urllib2.HTTPBasicAuthHandler(AuthManager(self.ui))
                opener = urllib2.build_opener(auth_handler)
                try:
                    return client.HttpGitClient(uri, opener=opener, thin_packs=False), uri
                except TypeError as e:
                    if e.message.find("unexpected keyword argument 'opener'") >= 0:
                        # using a version of dulwich that doesn't support
                        # http(s) authentication -- try without authentication
                        return client.HttpGitClient(uri, thin_packs=False), uri
                    else:
                        raise

        # if its not git or git+ssh, try a local url..
        return client.SubprocessGitClient(thin_packs=False), uri

class AuthManager(object):
    def __init__(self, ui):
        self.ui = ui

    def add_password(self, realm, uri, user, passwd):
        raise NotImplementedError(
            'AuthManager currently gets passwords from hg repo config')

    def find_user_password(self, realm, authuri):

        # find a stanza in the auth section which matches this uri
        for item in self.ui.configitems('auth'):
            if len(item) < 2:
                continue
            if item[0].endswith('.prefix') and authuri.startswith(item[1]):
                prefix = item[0][:-len('.prefix')]
                break
        else:
            # no matching stanza found!
            return (None,None)

        self.ui.note(_('using "%s" auth credentials\n') % (prefix,))
        username = self.ui.config('auth', '%s.username' % prefix)
        password = self.ui.config('auth', '%s.password' % prefix)

        return (username,password)


########NEW FILE########
__FILENAME__ = hg2git
# This file contains code dealing specifically with converting Mercurial
# repositories to Git repositories. Code in this file is meant to be a generic
# library and should be usable outside the context of hg-git or an hg command.

import os
import stat

import dulwich.objects as dulobjs
from dulwich import diff_tree

import util

def parse_subrepos(ctx):
    sub = util.OrderedDict()
    if '.hgsub' in ctx:
        sub = util.parse_hgsub(ctx['.hgsub'].data().splitlines())
    substate = util.OrderedDict()
    if '.hgsubstate' in ctx:
        substate = util.parse_hgsubstate(
            ctx['.hgsubstate'].data().splitlines())
    return sub, substate

class IncrementalChangesetExporter(object):
    """Incrementally export Mercurial changesets to Git trees.

    The purpose of this class is to facilitate Git tree export that is more
    optimal than brute force.

    A "dumb" implementations of Mercurial to Git export would iterate over
    every file present in a Mercurial changeset and would convert each to
    a Git blob and then conditionally add it to a Git repository if it didn't
    yet exist. This is suboptimal because the overhead associated with
    obtaining every file's raw content and converting it to a Git blob is
    not trivial!

    This class works around the suboptimality of brute force export by
    leveraging the information stored in Mercurial - the knowledge of what
    changed between changesets - to only export Git objects corresponding to
    changes in Mercurial. In the context of converting Mercurial repositories
    to Git repositories, we only export objects Git (possibly) hasn't seen yet.
    This prevents a lot of redundant work and is thus faster.

    Callers instantiate an instance of this class against a mercurial.localrepo
    instance. They then associate it with a specific changesets by calling
    update_changeset(). On each call to update_changeset(), the instance
    computes the difference between the current and new changesets and emits
    Git objects that haven't yet been encountered during the lifetime of the
    class instance. In other words, it expresses Mercurial changeset deltas in
    terms of Git objects. Callers then (usually) take this set of Git objects
    and add them to the Git repository.

    This class only emits Git blobs and trees, not commits.

    The tree calculation part of this class is essentially a reimplementation
    of dulwich.index.commit_tree. However, since our implementation reuses
    Tree instances and only recalculates SHA-1 when things change, we are
    more efficient.
    """

    def __init__(self, hg_repo, start_ctx, git_store, git_commit):
        """Create an instance against a mercurial.localrepo.

        start_ctx is the context for a Mercurial commit that has a Git
        equivalent, passed in as git_commit. The incremental computation will be
        started from this commit. git_store is the Git object store the commit
        comes from. start_ctx can be repo[nullid], in which case git_commit
        should be None.
        """
        self._hg = hg_repo

        # Our current revision's context.
        self._ctx = start_ctx

        # Path to dulwich.objects.Tree.
        self._init_dirs(git_store, git_commit)

        # Mercurial file nodeid to Git blob SHA-1. Used to prevent redundant
        # blob calculation.
        self._blob_cache = {}

    def _init_dirs(self, store, commit):
        """Initialize self._dirs for a Git object store and commit."""
        self._dirs = {}
        if commit is None:
            return
        dirkind = stat.S_IFDIR
        # depth-first order, chosen arbitrarily
        todo = [('', store[commit.tree])]
        while todo:
            path, tree = todo.pop()
            self._dirs[path] = tree
            for entry in tree.iteritems():
                if entry.mode == dirkind:
                    if path == '':
                        newpath = entry.path
                    else:
                        newpath = path + '/' + entry.path
                    todo.append((newpath, store[entry.sha]))

    @property
    def root_tree_sha(self):
        """The SHA-1 of the root Git tree.

        This is needed to construct a Git commit object.
        """
        return self._dirs[''].id

    def update_changeset(self, newctx):
        """Set the tree to track a new Mercurial changeset.

        This is a generator of 2-tuples. The first item in each tuple is a
        dulwich object, either a Blob or a Tree. The second item is the
        corresponding Mercurial nodeid for the item, if any. Only blobs will
        have nodeids. Trees do not correspond to a specific nodeid, so it does
        not make sense to emit a nodeid for them.

        When exporting trees from Mercurial, callers typically write the
        returned dulwich object to the Git repo via the store's add_object().

        Some emitted objects may already exist in the Git repository. This
        class does not know about the Git repository, so it's up to the caller
        to conditionally add the object, etc.

        Emitted objects are those that have changed since the last call to
        update_changeset. If this is the first call to update_chanageset, all
        objects in the tree are emitted.
        """
        # Our general strategy is to accumulate dulwich.objects.Blob and
        # dulwich.objects.Tree instances for the current Mercurial changeset.
        # We do this incremental by iterating over the Mercurial-reported
        # changeset delta. We rely on the behavior of Mercurial to lazy
        # calculate a Tree's SHA-1 when we modify it. This is critical to
        # performance.

        # In theory we should be able to look at changectx.files(). This is
        # *much* faster. However, it may not be accurate, especially with older
        # repositories, which may not record things like deleted files
        # explicitly in the manifest (which is where files() gets its data).
        # The only reliable way to get the full set of changes is by looking at
        # the full manifest. And, the easy way to compare two manifests is
        # localrepo.status().
        modified, added, removed = self._hg.status(self._ctx, newctx)[0:3]

        # We track which directories/trees have modified in this update and we
        # only export those.
        dirty_trees = set()

        subadded, subremoved = [], []

        for s in modified, added, removed:
            if '.hgsub' in s or '.hgsubstate' in s:
                subadded, subremoved = self._handle_subrepos(newctx)
                break

        # We first process subrepo and file removals so we can prune dead trees.
        for path in subremoved:
            self._remove_path(path, dirty_trees)

        for path in removed:
            if path == '.hgsubstate' or path == '.hgsub':
                continue

            self._remove_path(path, dirty_trees)

        for path, sha in subadded:
            d = os.path.dirname(path)
            tree = self._dirs.setdefault(d, dulobjs.Tree())
            dirty_trees.add(d)
            tree.add(os.path.basename(path), dulobjs.S_IFGITLINK, sha)

        # For every file that changed or was added, we need to calculate the
        # corresponding Git blob and its tree entry. We emit the blob
        # immediately and update trees to be aware of its presence.
        for path in set(modified) | set(added):
            if path == '.hgsubstate' or path == '.hgsub':
                continue

            d = os.path.dirname(path)
            tree = self._dirs.setdefault(d, dulobjs.Tree())
            dirty_trees.add(d)

            fctx = newctx[path]

            entry, blob = IncrementalChangesetExporter.tree_entry(fctx,
                self._blob_cache)
            if blob is not None:
                yield (blob, fctx.filenode())

            tree.add(*entry)

        # Now that all the trees represent the current changeset, recalculate
        # the tree IDs and emit them. Note that we wait until now to calculate
        # tree SHA-1s. This is an important difference between us and
        # dulwich.index.commit_tree(), which builds new Tree instances for each
        # series of blobs.
        for obj in self._populate_tree_entries(dirty_trees):
            yield (obj, None)

        self._ctx = newctx

    def _remove_path(self, path, dirty_trees):
        """Remove a path (file or git link) from the current changeset.

        If the tree containing this path is empty, it might be removed."""
        d = os.path.dirname(path)
        tree = self._dirs.get(d, dulobjs.Tree())

        del tree[os.path.basename(path)]
        dirty_trees.add(d)

        # If removing this file made the tree empty, we should delete this
        # tree. This could result in parent trees losing their only child
        # and so on.
        if not len(tree):
            self._remove_tree(d)
        else:
            self._dirs[d] = tree

    def _remove_tree(self, path):
        """Remove a (presumably empty) tree from the current changeset.

        A now-empty tree may be the only child of its parent. So, we traverse
        up the chain to the root tree, deleting any empty trees along the way.
        """
        try:
            del self._dirs[path]
        except KeyError:
            return

        # Now we traverse up to the parent and delete any references.
        if path == '':
            return

        basename = os.path.basename(path)
        parent = os.path.dirname(path)
        while True:
            tree = self._dirs.get(parent, None)

            # No parent entry. Nothing to remove or update.
            if tree is None:
                return

            try:
                del tree[basename]
            except KeyError:
                return

            if len(tree):
                return

            # The parent tree is empty. Se, we can delete it.
            del self._dirs[parent]

            if parent == '':
                return

            basename = os.path.basename(parent)
            parent = os.path.dirname(parent)

    def _populate_tree_entries(self, dirty_trees):
        self._dirs.setdefault('', dulobjs.Tree())

        # Fill in missing directories.
        for path in self._dirs.keys():
            parent = os.path.dirname(path)

            while parent != '':
                parent_tree = self._dirs.get(parent, None)

                if parent_tree is not None:
                    break

                self._dirs[parent] = dulobjs.Tree()
                parent = os.path.dirname(parent)

        for dirty in list(dirty_trees):
            parent = os.path.dirname(dirty)

            while parent != '':
                if parent in dirty_trees:
                    break

                dirty_trees.add(parent)
                parent = os.path.dirname(parent)

        # The root tree is always dirty but doesn't always get updated.
        dirty_trees.add('')

        # We only need to recalculate and export dirty trees.
        for d in sorted(dirty_trees, key=len, reverse=True):
            # Only happens for deleted directories.
            try:
                tree = self._dirs[d]
            except KeyError:
                continue

            yield tree

            if d == '':
                continue

            parent_tree = self._dirs[os.path.dirname(d)]

            # Accessing the tree's ID is what triggers SHA-1 calculation and is
            # the expensive part (at least if the tree has been modified since
            # the last time we retrieved its ID). Also, assigning an entry to a
            # tree (even if it already exists) invalidates the existing tree
            # and incurs SHA-1 recalculation. So, it's in our interest to avoid
            # invalidating trees. Since we only update the entries of dirty
            # trees, this should hold true.
            parent_tree[os.path.basename(d)] = (stat.S_IFDIR, tree.id)

    def _handle_subrepos(self, newctx):
        sub, substate = parse_subrepos(self._ctx)
        newsub, newsubstate = parse_subrepos(newctx)

        # For each path, the logic is described by the following table. 'no'
        # stands for 'the subrepo doesn't exist', 'git' stands for 'git
        # subrepo', and 'hg' stands for 'hg or other subrepo'.
        #
        #  old  new  |  action
        #   *   git  |   link    (1)
        #  git   hg  |  delete   (2)
        #  git   no  |  delete   (3)
        #
        # All other combinations are 'do nothing'.
        #
        # git links without corresponding submodule paths are stored as subrepos
        # with a substate but without an entry in .hgsub.

        # 'added' is both modified and added
        added, removed = [], []

        def isgit(sub, path):
            return path not in sub or sub[path].startswith('[git]')

        for path, sha in substate.iteritems():
            if not isgit(sub, path):
                # old = hg -- will be handled in next loop
                continue
            # old = git
            if path not in newsubstate or not isgit(newsub, path):
                # new = hg or no, case (2) or (3)
                removed.append(path)

        for path, sha in newsubstate.iteritems():
            if not isgit(newsub, path):
                # new = hg or no; the only cases we care about are handled above
                continue

            # case (1)
            added.append((path, sha))

        return added, removed

    @staticmethod
    def tree_entry(fctx, blob_cache):
        """Compute a dulwich TreeEntry from a filectx.

        A side effect is the TreeEntry is stored in the passed cache.

        Returns a 2-tuple of (dulwich.objects.TreeEntry, dulwich.objects.Blob).
        """
        blob_id = blob_cache.get(fctx.filenode(), None)
        blob = None

        if blob_id is None:
            blob = dulobjs.Blob.from_string(fctx.data())
            blob_id = blob.id
            blob_cache[fctx.filenode()] = blob_id

        flags = fctx.flags()

        if 'l' in flags:
            mode = 0120000
        elif 'x' in flags:
            mode = 0100755
        else:
            mode = 0100644

        return (dulobjs.TreeEntry(os.path.basename(fctx.path()), mode, blob_id),
                blob)


########NEW FILE########
__FILENAME__ = hgrepo
import os

from mercurial.node import bin
from mercurial import util

from git_handler import GitHandler
from gitrepo import gitrepo


def generate_repo_subclass(baseclass):
    class hgrepo(baseclass):
        def pull(self, remote, heads=None, force=False):
            if isinstance(remote, gitrepo):
                return self.githandler.fetch(remote.path, heads)
            else: #pragma: no cover
                return super(hgrepo, self).pull(remote, heads, force)

        # TODO figure out something useful to do with the newbranch param
        def push(self, remote, force=False, revs=None, newbranch=False):
            if isinstance(remote, gitrepo):
                return self.githandler.push(remote.path, revs, force)
            else: #pragma: no cover
                return super(hgrepo, self).push(remote, force, revs, newbranch)

        def findoutgoing(self, remote, base=None, heads=None, force=False):
            if isinstance(remote, gitrepo):
                base, heads = self.githandler.get_refs(remote.path)
                out, h = super(hgrepo, self).findoutgoing(remote, base, heads, force)
                return out
            else: #pragma: no cover
                return super(hgrepo, self).findoutgoing(remote, base, heads, force)

        def _findtags(self):
            (tags, tagtypes) = super(hgrepo, self)._findtags()

            for tag, rev in self.githandler.tags.iteritems():
                tags[tag] = bin(rev)
                tagtypes[tag] = 'git'

            tags.update(self.gitrefs())
            return (tags, tagtypes)

        @util.propertycache
        def githandler(self):
            '''get the GitHandler for an hg repo

            This only makes sense if the repo talks to at least one git remote.
            '''
            return GitHandler(self, self.ui)

        def gitrefs(self):
            tagfile = self.join(os.path.join('git-remote-refs'))
            if os.path.exists(tagfile):
                tf = open(tagfile, 'rb')
                tagdata = tf.read().split('\n')
                td = [line.split(' ', 1) for line in tagdata if line]
                return dict([(name, bin(sha)) for sha, name in td])
            return {}

        def tags(self):
            # TODO consider using self._tagscache
            tagscache = super(hgrepo, self).tags()
            tagscache.update(self.gitrefs())
            for tag, rev in self.githandler.tags.iteritems():
                if tag in tagscache:
                    continue

                tagscache[tag] = bin(rev)

            return tagscache

    return hgrepo

########NEW FILE########
__FILENAME__ = overlay
# overlay classes for repositories
# unifies access to unimported git objects and committed hg objects
# designed to support incoming
#
# incomplete, implemented on demand

from mercurial import ancestor
from mercurial import manifest
from mercurial import context
from mercurial.node import bin, hex, nullid
from mercurial import localrepo

def _maybehex(n):
    if len(n) == 20:
        return hex(n)
    return n

class overlaymanifest(object):
    def __init__(self, repo, sha):
        self.repo = repo
        self.tree = repo.handler.git.get_object(sha)
        self._map = None
        self._flagmap = None

    def withflags(self):
        self.load()
        return set([path for path, flag in self._flagmap.iteritems()
                    if flag & 020100])

    def copy(self):
        return overlaymanifest(self.repo, self.tree.id)

    def keys(self):
        self.load()
        return self._map.keys()

    def iterkeys(self):
        return iter(self.keys())

    def flags(self, path):
        self.load()

        def hgflag(gitflag):
            if gitflag & 0100:
                return 'x'
            elif gitflag & 020000:
                return 'l'
            else:
                return ''

        return hgflag(self._flagmap[path])

    def load(self):
        if self._map is not None:
            return

        self._map = {}
        self._flagmap = {}

        def addtree(tree, dirname):
            for entry in tree.iteritems():
                if entry.mode & 040000:
                    # expand directory
                    subtree = self.repo.handler.git.get_object(entry.sha)
                    addtree(subtree, dirname + entry.path + '/')
                else:
                    path = dirname + entry.path
                    self._map[path] = bin(entry.sha)
                    self._flagmap[path] = entry.mode

        addtree(self.tree, '')

    def iteritems(self):
        self.load()
        return self._map.iteritems()

    def __iter__(self):
        self.load()
        return self._map.__iter__()

    def __getitem__(self, path):
        self.load()
        return self._map[path]

    def __delitem__(self, path):
        del self._map[path]

class overlayfilectx(object):
    def __init__(self, repo, path, fileid=None):
        self.repo = repo
        self._path = path
        self.fileid = fileid

    # this is a hack to skip copy detection
    def ancestors(self):
        return [self, self]

    def filenode(self):
        return nullid

    def rev(self):
        return -1

    def path(self):
        return self._path

    def filelog(self):
        return self.fileid

    def data(self):
        blob = self.repo.handler.git.get_object(_maybehex(self.fileid))
        return blob.data

class overlaychangectx(context.changectx):
    def __init__(self, repo, sha):
        self.repo = repo
        if not isinstance(sha, basestring):
          sha = sha.hex()
        self.commit = repo.handler.git.get_object(_maybehex(sha))
        self._overlay = getattr(repo, 'gitoverlay', repo)
        self._rev = self._overlay.rev(bin(self.commit.id))

    def node(self):
        return bin(self.commit.id)

    def rev(self):
        return self._rev

    def date(self):
        return self.commit.author_time, self.commit.author_timezone

    def branch(self):
        return 'default'

    def user(self):
        return self.commit.author

    def files(self):
        return []

    def extra(self):
        return {}

    def description(self):
        return self.commit.message

    def parents(self):
        return [overlaychangectx(self.repo, sha) for sha in self.commit.parents]

    def manifestnode(self):
        return bin(self.commit.tree)

    def hex(self):
        return self.commit.id

    def tags(self):
        return []

    def bookmarks(self):
        return []

    def manifest(self):
        return overlaymanifest(self._overlay, self.commit.tree)

    def filectx(self, path, filelog=None):
        mf = self.manifest()
        return overlayfilectx(self._overlay, path, mf[path])

    def flags(self, path):
        mf = self.manifest()
        return mf.flags(path)

    def __nonzero__(self):
        return True

    def phase(self):
        try:
            from mercurial import phases
            return phases.draft
        except ImportError:
            return 1

class overlayrevlog(object):
    def __init__(self, repo, base):
        self.repo = repo
        self.base = base

    def parents(self, n):
        gitrev = self.repo.revmap.get(n)
        if gitrev is None:
            # we've reached a revision we have
            return self.base.parents(n)
        commit = self.repo.handler.git.get_object(_maybehex(n))

        if not commit.parents:
            return [nullid, nullid]

        def gitorhg(n):
            hn = self.repo.handler.map_hg_get(hex(n))
            if hn is not None:
                return bin(hn)
            return n

        # currently ignores the octopus
        p1 = gitorhg(bin(commit.parents[0]))
        if len(commit.parents) > 1:
            p2 = gitorhg(bin(commit.parents[1]))
        else:
            p2 = nullid

        return [p1, p2]

    def ancestor(self, a, b):
        anode = self.repo.nodemap.get(a)
        bnode = self.repo.nodemap.get(b)
        if anode is None and bnode is None:
          return self.base.ancestor(a, b)
        ancs = ancestor.ancestors(self.parentrevs, a, b)
        if ancs:
          return min(map(self.node, ancs))
        return nullid

    def parentrevs(self, rev):
        return [self.rev(p) for p in self.parents(self.node(rev))]

    def node(self, rev):
        gitnode = self.repo.nodemap.get(rev)
        if gitnode is None:
            return self.base.node(rev)
        return gitnode

    def rev(self, n):
        gitrev = self.repo.revmap.get(n)
        if gitrev is None:
             return self.base.rev(n)
        return gitrev

    def __len__(self):
        return len(self.repo.handler.repo) + len(self.repo.revmap)

class overlaymanifestlog(overlayrevlog):
    def read(self, sha):
        if sha == nullid:
            return manifest.manifestdict()
        return overlaymanifest(self.repo, sha)

class overlaychangelog(overlayrevlog):
    def read(self, sha):
        if isinstance(sha, int):
            sha = self.node(sha)
        if sha == nullid:
            return (nullid, "", (0, 0), [], "", {})
        return overlaychangectx(self.repo, sha)


class overlayrepo(object):
    def __init__(self, handler, commits, refs):
        self.handler = handler

        self.changelog = overlaychangelog(self, handler.repo.changelog)
        self.manifest = overlaymanifestlog(self, handler.repo.manifest)

        # for incoming -p
        self.root = handler.repo.root
        self.getcwd = handler.repo.getcwd
        # self.status = handler.repo.status
        self.ui = handler.repo.ui

        self.revmap = None
        self.nodemap = None
        self.refmap = None
        self.tagmap = None

        self._makemaps(commits, refs)

    def __getitem__(self, n):
        if n not in self.revmap:
            return self.handler.repo[n]
        return overlaychangectx(self, n)

    def _handlerhack(self, method, *args, **kwargs):
        nothing = object()
        r = self.handler.repo
        oldhandler = getattr(r, 'handler', nothing)
        oldoverlay = getattr(r, 'gitoverlay', nothing)
        r.handler = self.handler
        r.gitoverlay = self
        try:
          return getattr(r, method)(*args, **kwargs)
        finally:
          if oldhandler is nothing:
            del r.handler
          else:
            r.handler = oldhandler
          if oldoverlay is nothing:
            del r.gitoverlay
          else:
            r.gitoverlay = oldoverlay

    def status(self, *args, **kwargs):
      return self._handlerhack('status', *args, **kwargs)

    def node(self, n):
        """Returns an Hg or Git hash for the specified Git hash"""
        if bin(n) in self.revmap:
            return n
        return self.handler.map_hg_get(n)

    def nodebookmarks(self, n):
        return self.refmap.get(n, [])

    def nodetags(self, n):
        return self.tagmap.get(n, [])

    def rev(self, n):
        return self.revmap[n]

    def filectx(self, path, fileid=None):
        return overlayfilectx(self, path, fileid=fileid)

    def _makemaps(self, commits, refs):
        baserev = self.handler.repo['tip'].rev()
        self.revmap = {}
        self.nodemap = {}
        for i, n in enumerate(commits):
            rev = baserev + i + 1
            self.revmap[n] = rev
            self.nodemap[rev] = n

        self.refmap = {}
        self.tagmap = {}
        for ref in refs:
            if ref.startswith('refs/heads/'):
                refname = ref[11:]
                self.refmap.setdefault(bin(refs[ref]), []).append(refname)
            elif ref.startswith('refs/tags/'):
                tagname = ref[10:]
                self.tagmap.setdefault(bin(refs[ref]), []).append(tagname)

########NEW FILE########
__FILENAME__ = util
"""Compatability functions for old Mercurial versions."""
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

def parse_hgsub(lines):
    """Fills OrderedDict with hgsub file content passed as list of lines"""
    rv = OrderedDict()
    for l in lines:
        ls = l.strip();
        if not ls or ls[0] == '#': continue
        name, value = l.split('=', 1)
        rv[name.strip()] = value.strip()
    return rv

def serialize_hgsub(data):
    """Produces a string from OrderedDict hgsub content"""
    return ''.join(['%s = %s\n' % (n,v) for n,v in data.iteritems()])

def parse_hgsubstate(lines):
    """Fills OrderedDict with hgsubtate file content passed as list of lines"""
    rv = OrderedDict()
    for l in lines:
        ls = l.strip();
        if not ls or ls[0] == '#': continue
        value, name = l.split(' ', 1)
        rv[name.strip()] = value.strip()
    return rv

def serialize_hgsubstate(data):
    """Produces a string from OrderedDict hgsubstate content"""
    return ''.join(['%s %s\n' % (data[n], n) for n in sorted(data)])

########NEW FILE########
__FILENAME__ = verify
# verify.py - verify Mercurial revisions
#
# Copyright 2014 Facebook.
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

import stat

from mercurial import error
from mercurial import util as hgutil
from mercurial.node import hex, bin, nullid
from mercurial.i18n import _
from mercurial import scmutil

from dulwich import diff_tree
from dulwich.objects import Commit, S_IFGITLINK

def verify(ui, repo, **opts):
    '''verify that a Mercurial rev matches the corresponding Git rev

    Given a Mercurial revision that has a corresponding Git revision in the map,
    this attempts to answer whether that revision has the same contents as the
    corresponding Git revision.

    '''
    hgctx = scmutil.revsingle(repo, opts.get('rev'), '.')

    handler = repo.githandler

    gitsha = handler.map_git_get(hgctx.hex())
    if not gitsha:
        # TODO deal better with commits in the middle of octopus merges
        raise hgutil.Abort(_('no git commit found for rev %s') % hgctx,
                           hint=_('if this is an octopus merge, verify against the last rev'))

    try:
        gitcommit = handler.git.get_object(gitsha)
    except KeyError:
        raise hgutil.Abort(_('git equivalent %s for rev %s not found!') %
                           (gitsha, hgctx))
    if not isinstance(gitcommit, Commit):
        raise hgutil.Abort(_('git equivalent %s for rev %s is not a commit!') %
                           (gitsha, hgctx))

    ui.status(_('verifying rev %s against git commit %s\n') % (hgctx, gitsha))
    failed = False

    # TODO check commit message and other metadata

    dirkind = stat.S_IFDIR

    hgfiles = set(hgctx)
    # TODO deal with submodules
    hgfiles.discard('.hgsubstate')
    hgfiles.discard('.hgsub')
    gitfiles = set()

    i = 0
    for gitfile, dummy in diff_tree.walk_trees(handler.git.object_store,
                                               gitcommit.tree, None):
        if gitfile.mode == dirkind:
            continue
        # TODO deal with submodules
        if (gitfile.mode == S_IFGITLINK or gitfile.path == '.hgsubstate'
            or gitfile.path == '.hgsub'):
            continue
        ui.progress('verify', i, total=len(hgfiles))
        i += 1
        gitfiles.add(gitfile.path)

        try:
            fctx = hgctx[gitfile.path]
        except error.LookupError:
            # we'll deal with this at the end
            continue

        hgflags = fctx.flags()
        gitflags = handler.convert_git_int_mode(gitfile.mode)
        if hgflags != gitflags:
            ui.write(_("file has different flags: %s (hg '%s', git '%s')\n") %
                     (gitfile.path, hgflags, gitflags))
            failed = True
        if fctx.data() != handler.git[gitfile.sha].data:
            ui.write(_('difference in: %s\n') % gitfile.path)
            failed = True

    ui.progress('verify', None, total=len(hgfiles))

    if hgfiles != gitfiles:
        failed = True
        missing = gitfiles - hgfiles
        for f in sorted(missing):
            ui.write(_('file found in git but not hg: %s\n') % f)
        unexpected = hgfiles - gitfiles
        for f in sorted(unexpected):
            ui.write(_('file found in hg but not git: %s\n') % f)

    if failed:
        return 1
    else:
        return 0

########NEW FILE########
__FILENAME__ = _ssh
from mercurial import util

class SSHVendor(object):
    """Parent class for ui-linked Vendor classes."""


def generate_ssh_vendor(ui):
    """
    Allows dulwich to use hg's ui.ssh config. The dulwich.client.get_ssh_vendor
    property should point to the return value.
    """

    class _Vendor(SSHVendor):
        def run_command(self, host, command, username=None, port=None):
            from dulwich.client import SubprocessWrapper
            from mercurial import util
            import subprocess

            sshcmd = ui.config("ui", "ssh", "ssh")
            args = util.sshargs(sshcmd, host, username, port)
            cmd = '%s %s %s' % (sshcmd, args, 
                                util.shellquote(' '.join(command)))
            ui.debug('calling ssh: %s\n' % cmd)
            print command
            proc = subprocess.Popen(util.quotecommand(cmd), shell=True,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE)
            return SubprocessWrapper(proc)

    return _Vendor

########NEW FILE########
__FILENAME__ = hghave
import os, stat, socket
import re
import sys
import tempfile

tempprefix = 'hg-hghave-'

def matchoutput(cmd, regexp, ignorestatus=False):
    """Return True if cmd executes successfully and its output
    is matched by the supplied regular expression.
    """
    r = re.compile(regexp)
    fh = os.popen(cmd)
    s = fh.read()
    try:
        ret = fh.close()
    except IOError:
        # Happen in Windows test environment
        ret = 1
    return (ignorestatus or ret is None) and r.search(s)

def has_baz():
    return matchoutput('baz --version 2>&1', r'baz Bazaar version')

def has_bzr():
    try:
        import bzrlib
        return bzrlib.__doc__ is not None
    except ImportError:
        return False

def has_bzr114():
    try:
        import bzrlib
        return (bzrlib.__doc__ is not None
                and bzrlib.version_info[:2] >= (1, 14))
    except ImportError:
        return False

def has_cvs():
    re = r'Concurrent Versions System.*?server'
    return matchoutput('cvs --version 2>&1', re) and not has_msys()

def has_darcs():
    return matchoutput('darcs --version', r'2\.[2-9]', True)

def has_mtn():
    return matchoutput('mtn --version', r'monotone', True) and not matchoutput(
        'mtn --version', r'monotone 0\.', True)

def has_eol_in_paths():
    try:
        fd, path = tempfile.mkstemp(dir='.', prefix=tempprefix, suffix='\n\r')
        os.close(fd)
        os.remove(path)
        return True
    except (IOError, OSError):
        return False

def has_executablebit():
    try:
        EXECFLAGS = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        fh, fn = tempfile.mkstemp(dir='.', prefix=tempprefix)
        try:
            os.close(fh)
            m = os.stat(fn).st_mode & 0777
            new_file_has_exec = m & EXECFLAGS
            os.chmod(fn, m ^ EXECFLAGS)
            exec_flags_cannot_flip = ((os.stat(fn).st_mode & 0777) == m)
        finally:
            os.unlink(fn)
    except (IOError, OSError):
        # we don't care, the user probably won't be able to commit anyway
        return False
    return not (new_file_has_exec or exec_flags_cannot_flip)

def has_icasefs():
    # Stolen from mercurial.util
    fd, path = tempfile.mkstemp(dir='.', prefix=tempprefix)
    os.close(fd)
    try:
        s1 = os.stat(path)
        d, b = os.path.split(path)
        p2 = os.path.join(d, b.upper())
        if path == p2:
            p2 = os.path.join(d, b.lower())
        try:
            s2 = os.stat(p2)
            return s2 == s1
        except OSError:
            return False
    finally:
        os.remove(path)

def has_inotify():
    try:
        import hgext.inotify.linux.watcher
    except ImportError:
        return False
    name = tempfile.mktemp(dir='.', prefix=tempprefix)
    sock = socket.socket(socket.AF_UNIX)
    try:
        sock.bind(name)
    except socket.error, err:
        return False
    sock.close()
    os.unlink(name)
    return True

def has_fifo():
    if getattr(os, "mkfifo", None) is None:
        return False
    name = tempfile.mktemp(dir='.', prefix=tempprefix)
    try:
        os.mkfifo(name)
        os.unlink(name)
        return True
    except OSError:
        return False

def has_cacheable_fs():
    from mercurial import util

    fd, path = tempfile.mkstemp(dir='.', prefix=tempprefix)
    os.close(fd)
    try:
        return util.cachestat(path).cacheable()
    finally:
        os.remove(path)

def has_lsprof():
    try:
        import _lsprof
        return True
    except ImportError:
        return False

def has_gettext():
    return matchoutput('msgfmt --version', 'GNU gettext-tools')

def has_git():
    return matchoutput('git --version 2>&1', r'^git version')

def has_docutils():
    try:
        from docutils.core import publish_cmdline
        return True
    except ImportError:
        return False

def getsvnversion():
    m = matchoutput('svn --version 2>&1', r'^svn,\s+version\s+(\d+)\.(\d+)')
    if not m:
        return (0, 0)
    return (int(m.group(1)), int(m.group(2)))

def has_svn15():
    return getsvnversion() >= (1, 5)

def has_svn13():
    return getsvnversion() >= (1, 3)

def has_svn():
    return matchoutput('svn --version 2>&1', r'^svn, version') and \
        matchoutput('svnadmin --version 2>&1', r'^svnadmin, version')

def has_svn_bindings():
    try:
        import svn.core
        version = svn.core.SVN_VER_MAJOR, svn.core.SVN_VER_MINOR
        if version < (1, 4):
            return False
        return True
    except ImportError:
        return False

def has_p4():
    return (matchoutput('p4 -V', r'Rev\. P4/') and
            matchoutput('p4d -V', r'Rev\. P4D/'))

def has_symlink():
    if getattr(os, "symlink", None) is None:
        return False
    name = tempfile.mktemp(dir='.', prefix=tempprefix)
    try:
        os.symlink(".", name)
        os.unlink(name)
        return True
    except (OSError, AttributeError):
        return False

def has_hardlink():
    from mercurial import util
    fh, fn = tempfile.mkstemp(dir='.', prefix=tempprefix)
    os.close(fh)
    name = tempfile.mktemp(dir='.', prefix=tempprefix)
    try:
        try:
            util.oslink(fn, name)
            os.unlink(name)
            return True
        except OSError:
            return False
    finally:
        os.unlink(fn)

def has_tla():
    return matchoutput('tla --version 2>&1', r'The GNU Arch Revision')

def has_gpg():
    return matchoutput('gpg --version 2>&1', r'GnuPG')

def has_unix_permissions():
    d = tempfile.mkdtemp(dir='.', prefix=tempprefix)
    try:
        fname = os.path.join(d, 'foo')
        for umask in (077, 007, 022):
            os.umask(umask)
            f = open(fname, 'w')
            f.close()
            mode = os.stat(fname).st_mode
            os.unlink(fname)
            if mode & 0777 != ~umask & 0666:
                return False
        return True
    finally:
        os.rmdir(d)

def has_pyflakes():
    return matchoutput("sh -c \"echo 'import re' 2>&1 | pyflakes\"",
                       r"<stdin>:1: 're' imported but unused",
                       True)

def has_pygments():
    try:
        import pygments
        return True
    except ImportError:
        return False

def has_outer_repo():
    # failing for other reasons than 'no repo' imply that there is a repo
    return not matchoutput('hg root 2>&1',
                           r'abort: no repository found', True)

def has_ssl():
    try:
        import ssl
        import OpenSSL
        OpenSSL.SSL.Context
        return True
    except ImportError:
        return False

def has_windows():
    return os.name == 'nt'

def has_system_sh():
    return os.name != 'nt'

def has_serve():
    return os.name != 'nt' # gross approximation

def has_tic():
    return matchoutput('test -x "`which tic`"', '')

def has_msys():
    return os.getenv('MSYSTEM')

checks = {
    "true": (lambda: True, "yak shaving"),
    "false": (lambda: False, "nail clipper"),
    "baz": (has_baz, "GNU Arch baz client"),
    "bzr": (has_bzr, "Canonical's Bazaar client"),
    "bzr114": (has_bzr114, "Canonical's Bazaar client >= 1.14"),
    "cacheable": (has_cacheable_fs, "cacheable filesystem"),
    "cvs": (has_cvs, "cvs client/server"),
    "darcs": (has_darcs, "darcs client"),
    "docutils": (has_docutils, "Docutils text processing library"),
    "eol-in-paths": (has_eol_in_paths, "end-of-lines in paths"),
    "execbit": (has_executablebit, "executable bit"),
    "fifo": (has_fifo, "named pipes"),
    "gettext": (has_gettext, "GNU Gettext (msgfmt)"),
    "git": (has_git, "git command line client"),
    "gpg": (has_gpg, "gpg client"),
    "hardlink": (has_hardlink, "hardlinks"),
    "icasefs": (has_icasefs, "case insensitive file system"),
    "inotify": (has_inotify, "inotify extension support"),
    "lsprof": (has_lsprof, "python lsprof module"),
    "mtn": (has_mtn, "monotone client (>= 1.0)"),
    "outer-repo": (has_outer_repo, "outer repo"),
    "p4": (has_p4, "Perforce server and client"),
    "pyflakes": (has_pyflakes, "Pyflakes python linter"),
    "pygments": (has_pygments, "Pygments source highlighting library"),
    "serve": (has_serve, "platform and python can manage 'hg serve -d'"),
    "ssl": (has_ssl, "python >= 2.6 ssl module and python OpenSSL"),
    "svn": (has_svn, "subversion client and admin tools"),
    "svn13": (has_svn13, "subversion client and admin tools >= 1.3"),
    "svn15": (has_svn15, "subversion client and admin tools >= 1.5"),
    "svn-bindings": (has_svn_bindings, "subversion python bindings"),
    "symlink": (has_symlink, "symbolic links"),
    "system-sh": (has_system_sh, "system() uses sh"),
    "tic": (has_tic, "terminfo compiler"),
    "tla": (has_tla, "GNU Arch tla client"),
    "unix-permissions": (has_unix_permissions, "unix-style permissions"),
    "windows": (has_windows, "Windows"),
    "msys": (has_msys, "Windows with MSYS"),
}

########NEW FILE########
__FILENAME__ = killdaemons
#!/usr/bin/env python

import os, sys, time, errno, signal

if os.name =='nt':
    import ctypes

    def _check(ret, expectederr=None):
        if ret == 0:
            winerrno = ctypes.GetLastError()
            if winerrno == expectederr:
                return True
            raise ctypes.WinError(winerrno)

    def kill(pid, logfn, tryhard=True):
        logfn('# Killing daemon process %d' % pid)
        PROCESS_TERMINATE = 1
        PROCESS_QUERY_INFORMATION = 0x400
        SYNCHRONIZE = 0x00100000L
        WAIT_OBJECT_0 = 0
        WAIT_TIMEOUT = 258
        handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_TERMINATE|SYNCHRONIZE|PROCESS_QUERY_INFORMATION,
                False, pid)
        if handle == 0:
            _check(0, 87) # err 87 when process not found
            return # process not found, already finished
        try:
            r = ctypes.windll.kernel32.WaitForSingleObject(handle, 100)
            if r == WAIT_OBJECT_0:
                pass # terminated, but process handle still available
            elif r == WAIT_TIMEOUT:
                _check(ctypes.windll.kernel32.TerminateProcess(handle, -1))
            else:
                _check(r)

            # TODO?: forcefully kill when timeout
            #        and ?shorter waiting time? when tryhard==True
            r = ctypes.windll.kernel32.WaitForSingleObject(handle, 100)
                                                       # timeout = 100 ms
            if r == WAIT_OBJECT_0:
                pass # process is terminated
            elif r == WAIT_TIMEOUT:
                logfn('# Daemon process %d is stuck')
            else:
                check(r) # any error
        except: #re-raises
            ctypes.windll.kernel32.CloseHandle(handle) # no _check, keep error
            raise
        _check(ctypes.windll.kernel32.CloseHandle(handle))

else:
    def kill(pid, logfn, tryhard=True):
        try:
            os.kill(pid, 0)
            logfn('# Killing daemon process %d' % pid)
            os.kill(pid, signal.SIGTERM)
            if tryhard:
                for i in range(10):
                    time.sleep(0.05)
                    os.kill(pid, 0)
            else:
                time.sleep(0.1)
                os.kill(pid, 0)
            logfn('# Daemon process %d is stuck - really killing it' % pid)
            os.kill(pid, signal.SIGKILL)
        except OSError, err:
            if err.errno != errno.ESRCH:
                raise

def killdaemons(pidfile, tryhard=True, remove=False, logfn=None):
    if not logfn:
        logfn = lambda s: s
    # Kill off any leftover daemon processes
    try:
        fp = open(pidfile)
        for line in fp:
            try:
                pid = int(line)
            except ValueError:
                continue
            kill(pid, logfn, tryhard)
        fp.close()
        if remove:
            os.unlink(pidfile)
    except IOError:
        pass

if __name__ == '__main__':
    path, = sys.argv[1:]
    killdaemons(path)


########NEW FILE########
__FILENAME__ = run-tests
#!/usr/bin/env python
#
# run-tests.py - Run a set of tests on Mercurial
#
# Copyright 2006 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

# Modifying this script is tricky because it has many modes:
#   - serial (default) vs parallel (-jN, N > 1)
#   - no coverage (default) vs coverage (-c, -C, -s)
#   - temp install (default) vs specific hg script (--with-hg, --local)
#   - tests are a mix of shell scripts and Python scripts
#
# If you change this script, it is recommended that you ensure you
# haven't broken it by running it in various modes with a representative
# sample of test scripts.  For example:
#
#  1) serial, no coverage, temp install:
#      ./run-tests.py test-s*
#  2) serial, no coverage, local hg:
#      ./run-tests.py --local test-s*
#  3) serial, coverage, temp install:
#      ./run-tests.py -c test-s*
#  4) serial, coverage, local hg:
#      ./run-tests.py -c --local test-s*      # unsupported
#  5) parallel, no coverage, temp install:
#      ./run-tests.py -j2 test-s*
#  6) parallel, no coverage, local hg:
#      ./run-tests.py -j2 --local test-s*
#  7) parallel, coverage, temp install:
#      ./run-tests.py -j2 -c test-s*          # currently broken
#  8) parallel, coverage, local install:
#      ./run-tests.py -j2 -c --local test-s*  # unsupported (and broken)
#  9) parallel, custom tmp dir:
#      ./run-tests.py -j2 --tmpdir /tmp/myhgtests
#
# (You could use any subset of the tests: test-s* happens to match
# enough that it's worth doing parallel runs, few enough that it
# completes fairly quickly, includes both shell and Python scripts, and
# includes some scripts that run daemon processes.)

from distutils import version
import difflib
import errno
import optparse
import os
import shutil
import subprocess
import signal
import sys
import tempfile
import time
import random
import re
import threading
import killdaemons as killmod
import Queue as queue

processlock = threading.Lock()

# subprocess._cleanup can race with any Popen.wait or Popen.poll on py24
# http://bugs.python.org/issue1731717 for details. We shouldn't be producing
# zombies but it's pretty harmless even if we do.
if sys.version_info < (2, 5):
    subprocess._cleanup = lambda: None

closefds = os.name == 'posix'
def Popen4(cmd, wd, timeout, env=None):
    processlock.acquire()
    p = subprocess.Popen(cmd, shell=True, bufsize=-1, cwd=wd, env=env,
                         close_fds=closefds,
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    processlock.release()

    p.fromchild = p.stdout
    p.tochild = p.stdin
    p.childerr = p.stderr

    p.timeout = False
    if timeout:
        def t():
            start = time.time()
            while time.time() - start < timeout and p.returncode is None:
                time.sleep(.1)
            p.timeout = True
            if p.returncode is None:
                terminate(p)
        threading.Thread(target=t).start()

    return p

# reserved exit code to skip test (used by hghave)
SKIPPED_STATUS = 80
SKIPPED_PREFIX = 'skipped: '
FAILED_PREFIX  = 'hghave check failed: '
PYTHON = sys.executable.replace('\\', '/')
IMPL_PATH = 'PYTHONPATH'
if 'java' in sys.platform:
    IMPL_PATH = 'JYTHONPATH'

requiredtools = [os.path.basename(sys.executable), "diff", "grep", "unzip",
                 "gunzip", "bunzip2", "sed"]
createdfiles = []

defaults = {
    'jobs': ('HGTEST_JOBS', 1),
    'timeout': ('HGTEST_TIMEOUT', 180),
    'port': ('HGTEST_PORT', 20059),
    'shell': ('HGTEST_SHELL', 'sh'),
}

def parselistfiles(files, listtype, warn=True):
    entries = dict()
    for filename in files:
        try:
            path = os.path.expanduser(os.path.expandvars(filename))
            f = open(path, "r")
        except IOError, err:
            if err.errno != errno.ENOENT:
                raise
            if warn:
                print "warning: no such %s file: %s" % (listtype, filename)
            continue

        for line in f.readlines():
            line = line.split('#', 1)[0].strip()
            if line:
                entries[line] = filename

        f.close()
    return entries

def parseargs():
    parser = optparse.OptionParser("%prog [options] [tests]")

    # keep these sorted
    parser.add_option("--blacklist", action="append",
        help="skip tests listed in the specified blacklist file")
    parser.add_option("--whitelist", action="append",
        help="always run tests listed in the specified whitelist file")
    parser.add_option("-C", "--annotate", action="store_true",
        help="output files annotated with coverage")
    parser.add_option("-c", "--cover", action="store_true",
        help="print a test coverage report")
    parser.add_option("-d", "--debug", action="store_true",
        help="debug mode: write output of test scripts to console"
             " rather than capturing and diff'ing it (disables timeout)")
    parser.add_option("-f", "--first", action="store_true",
        help="exit on the first test failure")
    parser.add_option("-H", "--htmlcov", action="store_true",
        help="create an HTML report of the coverage of the files")
    parser.add_option("--inotify", action="store_true",
        help="enable inotify extension when running tests")
    parser.add_option("-i", "--interactive", action="store_true",
        help="prompt to accept changed output")
    parser.add_option("-j", "--jobs", type="int",
        help="number of jobs to run in parallel"
             " (default: $%s or %d)" % defaults['jobs'])
    parser.add_option("--keep-tmpdir", action="store_true",
        help="keep temporary directory after running tests")
    parser.add_option("-k", "--keywords",
        help="run tests matching keywords")
    parser.add_option("-l", "--local", action="store_true",
        help="shortcut for --with-hg=<testdir>/../hg")
    parser.add_option("--loop", action="store_true",
        help="loop tests repeatedly")
    parser.add_option("-n", "--nodiff", action="store_true",
        help="skip showing test changes")
    parser.add_option("-p", "--port", type="int",
        help="port on which servers should listen"
             " (default: $%s or %d)" % defaults['port'])
    parser.add_option("--compiler", type="string",
        help="compiler to build with")
    parser.add_option("--pure", action="store_true",
        help="use pure Python code instead of C extensions")
    parser.add_option("-R", "--restart", action="store_true",
        help="restart at last error")
    parser.add_option("-r", "--retest", action="store_true",
        help="retest failed tests")
    parser.add_option("-S", "--noskips", action="store_true",
        help="don't report skip tests verbosely")
    parser.add_option("--shell", type="string",
        help="shell to use (default: $%s or %s)" % defaults['shell'])
    parser.add_option("-t", "--timeout", type="int",
        help="kill errant tests after TIMEOUT seconds"
             " (default: $%s or %d)" % defaults['timeout'])
    parser.add_option("--time", action="store_true",
        help="time how long each test takes")
    parser.add_option("--tmpdir", type="string",
        help="run tests in the given temporary directory"
             " (implies --keep-tmpdir)")
    parser.add_option("-v", "--verbose", action="store_true",
        help="output verbose messages")
    parser.add_option("--view", type="string",
        help="external diff viewer")
    parser.add_option("--with-hg", type="string",
        metavar="HG",
        help="test using specified hg script rather than a "
             "temporary installation")
    parser.add_option("-3", "--py3k-warnings", action="store_true",
        help="enable Py3k warnings on Python 2.6+")
    parser.add_option('--extra-config-opt', action="append",
                      help='set the given config opt in the test hgrc')
    parser.add_option('--random', action="store_true",
                      help='run tests in random order')

    for option, (envvar, default) in defaults.items():
        defaults[option] = type(default)(os.environ.get(envvar, default))
    parser.set_defaults(**defaults)
    (options, args) = parser.parse_args()

    # jython is always pure
    if 'java' in sys.platform or '__pypy__' in sys.modules:
        options.pure = True

    if options.with_hg:
        options.with_hg = os.path.expanduser(options.with_hg)
        if not (os.path.isfile(options.with_hg) and
                os.access(options.with_hg, os.X_OK)):
            parser.error('--with-hg must specify an executable hg script')
        if not os.path.basename(options.with_hg) == 'hg':
            sys.stderr.write('warning: --with-hg should specify an hg script\n')
    if options.local:
        testdir = os.path.dirname(os.path.realpath(sys.argv[0]))
        hgbin = os.path.join(os.path.dirname(testdir), 'hg')
        if os.name != 'nt' and not os.access(hgbin, os.X_OK):
            parser.error('--local specified, but %r not found or not executable'
                         % hgbin)
        options.with_hg = hgbin

    options.anycoverage = options.cover or options.annotate or options.htmlcov
    if options.anycoverage:
        try:
            import coverage
            covver = version.StrictVersion(coverage.__version__).version
            if covver < (3, 3):
                parser.error('coverage options require coverage 3.3 or later')
        except ImportError:
            parser.error('coverage options now require the coverage package')

    if options.anycoverage and options.local:
        # this needs some path mangling somewhere, I guess
        parser.error("sorry, coverage options do not work when --local "
                     "is specified")

    global verbose
    if options.verbose:
        verbose = ''

    if options.tmpdir:
        options.tmpdir = os.path.expanduser(options.tmpdir)

    if options.jobs < 1:
        parser.error('--jobs must be positive')
    if options.interactive and options.debug:
        parser.error("-i/--interactive and -d/--debug are incompatible")
    if options.debug:
        if options.timeout != defaults['timeout']:
            sys.stderr.write(
                'warning: --timeout option ignored with --debug\n')
        options.timeout = 0
    if options.py3k_warnings:
        if sys.version_info[:2] < (2, 6) or sys.version_info[:2] >= (3, 0):
            parser.error('--py3k-warnings can only be used on Python 2.6+')
    if options.blacklist:
        options.blacklist = parselistfiles(options.blacklist, 'blacklist')
    if options.whitelist:
        options.whitelisted = parselistfiles(options.whitelist, 'whitelist')
    else:
        options.whitelisted = {}

    return (options, args)

def rename(src, dst):
    """Like os.rename(), trade atomicity and opened files friendliness
    for existing destination support.
    """
    shutil.copy(src, dst)
    os.remove(src)

def parsehghaveoutput(lines):
    '''Parse hghave log lines.
    Return tuple of lists (missing, failed):
      * the missing/unknown features
      * the features for which existence check failed'''
    missing = []
    failed = []
    for line in lines:
        if line.startswith(SKIPPED_PREFIX):
            line = line.splitlines()[0]
            missing.append(line[len(SKIPPED_PREFIX):])
        elif line.startswith(FAILED_PREFIX):
            line = line.splitlines()[0]
            failed.append(line[len(FAILED_PREFIX):])

    return missing, failed

def showdiff(expected, output, ref, err):
    print
    for line in difflib.unified_diff(expected, output, ref, err):
        sys.stdout.write(line)

verbose = False
def vlog(*msg):
    if verbose is not False:
        iolock.acquire()
        if verbose:
            print verbose,
        for m in msg:
            print m,
        print
        sys.stdout.flush()
        iolock.release()

def log(*msg):
    iolock.acquire()
    if verbose:
        print verbose,
    for m in msg:
        print m,
    print
    sys.stdout.flush()
    iolock.release()

def findprogram(program):
    """Search PATH for a executable program"""
    for p in os.environ.get('PATH', os.defpath).split(os.pathsep):
        name = os.path.join(p, program)
        if os.name == 'nt' or os.access(name, os.X_OK):
            return name
    return None

def createhgrc(path, options):
    # create a fresh hgrc
    hgrc = open(path, 'w')
    hgrc.write('[ui]\n')
    hgrc.write('slash = True\n')
    hgrc.write('interactive = False\n')
    hgrc.write('[defaults]\n')
    hgrc.write('backout = -d "0 0"\n')
    hgrc.write('commit = -d "0 0"\n')
    hgrc.write('shelve = --date "0 0"\n')
    hgrc.write('tag = -d "0 0"\n')
    if options.inotify:
        hgrc.write('[extensions]\n')
        hgrc.write('inotify=\n')
        hgrc.write('[inotify]\n')
        hgrc.write('pidfile=daemon.pids')
        hgrc.write('appendpid=True\n')
    if options.extra_config_opt:
        for opt in options.extra_config_opt:
            section, key = opt.split('.', 1)
            assert '=' in key, ('extra config opt %s must '
                                'have an = for assignment' % opt)
            hgrc.write('[%s]\n%s\n' % (section, key))
    hgrc.close()

def createenv(options, testtmp, threadtmp, port):
    env = os.environ.copy()
    env['TESTTMP'] = testtmp
    env['HOME'] = testtmp
    env["HGPORT"] = str(port)
    env["HGPORT1"] = str(port + 1)
    env["HGPORT2"] = str(port + 2)
    env["HGRCPATH"] = os.path.join(threadtmp, '.hgrc')
    env["DAEMON_PIDS"] = os.path.join(threadtmp, 'daemon.pids')
    env["HGEDITOR"] = sys.executable + ' -c "import sys; sys.exit(0)"'
    env["HGMERGE"] = "internal:merge"
    env["HGUSER"]   = "test"
    env["HGENCODING"] = "ascii"
    env["HGENCODINGMODE"] = "strict"

    # Reset some environment variables to well-known values so that
    # the tests produce repeatable output.
    env['LANG'] = env['LC_ALL'] = env['LANGUAGE'] = 'C'
    env['TZ'] = 'GMT'
    env["EMAIL"] = "Foo Bar <foo.bar@example.com>"
    env['COLUMNS'] = '80'
    env['TERM'] = 'xterm'

    for k in ('HG HGPROF CDPATH GREP_OPTIONS http_proxy no_proxy ' +
              'NO_PROXY').split():
        if k in env:
            del env[k]

    # unset env related to hooks
    for k in env.keys():
        if k.startswith('HG_'):
            del env[k]

    return env

def checktools():
    # Before we go any further, check for pre-requisite tools
    # stuff from coreutils (cat, rm, etc) are not tested
    for p in requiredtools:
        if os.name == 'nt' and not p.endswith('.exe'):
            p += '.exe'
        found = findprogram(p)
        if found:
            vlog("# Found prerequisite", p, "at", found)
        else:
            print "WARNING: Did not find prerequisite tool: "+p

def terminate(proc):
    """Terminate subprocess (with fallback for Python versions < 2.6)"""
    vlog('# Terminating process %d' % proc.pid)
    try:
        getattr(proc, 'terminate', lambda : os.kill(proc.pid, signal.SIGTERM))()
    except OSError:
        pass

def killdaemons(pidfile):
    return killmod.killdaemons(pidfile, tryhard=False, remove=True,
                               logfn=vlog)

def cleanup(options):
    if not options.keep_tmpdir:
        vlog("# Cleaning up HGTMP", HGTMP)
        shutil.rmtree(HGTMP, True)
        for f in createdfiles:
            try:
                os.remove(f)
            except OSError:
                pass

def usecorrectpython():
    # some tests run python interpreter. they must use same
    # interpreter we use or bad things will happen.
    pyexename = sys.platform == 'win32' and 'python.exe' or 'python'
    if getattr(os, 'symlink', None):
        vlog("# Making python executable in test path a symlink to '%s'" %
             sys.executable)
        mypython = os.path.join(TMPBINDIR, pyexename)
        try:
            if os.readlink(mypython) == sys.executable:
                return
            os.unlink(mypython)
        except OSError, err:
            if err.errno != errno.ENOENT:
                raise
        if findprogram(pyexename) != sys.executable:
            try:
                os.symlink(sys.executable, mypython)
                createdfiles.append(mypython)
            except OSError, err:
                # child processes may race, which is harmless
                if err.errno != errno.EEXIST:
                    raise
    else:
        exedir, exename = os.path.split(sys.executable)
        vlog("# Modifying search path to find %s as %s in '%s'" %
             (exename, pyexename, exedir))
        path = os.environ['PATH'].split(os.pathsep)
        while exedir in path:
            path.remove(exedir)
        os.environ['PATH'] = os.pathsep.join([exedir] + path)
        if not findprogram(pyexename):
            print "WARNING: Cannot find %s in search path" % pyexename

def installhg(options):
    vlog("# Performing temporary installation of HG")
    installerrs = os.path.join("tests", "install.err")
    compiler = ''
    if options.compiler:
        compiler = '--compiler ' + options.compiler
    pure = options.pure and "--pure" or ""
    py3 = ''
    if sys.version_info[0] == 3:
        py3 = '--c2to3'

    # Run installer in hg root
    script = os.path.realpath(sys.argv[0])
    hgroot = os.path.dirname(os.path.dirname(script))
    os.chdir(hgroot)
    nohome = '--home=""'
    if os.name == 'nt':
        # The --home="" trick works only on OS where os.sep == '/'
        # because of a distutils convert_path() fast-path. Avoid it at
        # least on Windows for now, deal with .pydistutils.cfg bugs
        # when they happen.
        nohome = ''
    cmd = ('%(exe)s setup.py %(py3)s %(pure)s clean --all'
           ' build %(compiler)s --build-base="%(base)s"'
           ' install --force --prefix="%(prefix)s" --install-lib="%(libdir)s"'
           ' --install-scripts="%(bindir)s" %(nohome)s >%(logfile)s 2>&1'
           % dict(exe=sys.executable, py3=py3, pure=pure, compiler=compiler,
                  base=os.path.join(HGTMP, "build"),
                  prefix=INST, libdir=PYTHONDIR, bindir=BINDIR,
                  nohome=nohome, logfile=installerrs))
    vlog("# Running", cmd)
    if os.system(cmd) == 0:
        if not options.verbose:
            os.remove(installerrs)
    else:
        f = open(installerrs)
        for line in f:
            print line,
        f.close()
        sys.exit(1)
    os.chdir(TESTDIR)

    usecorrectpython()

    if options.py3k_warnings and not options.anycoverage:
        vlog("# Updating hg command to enable Py3k Warnings switch")
        f = open(os.path.join(BINDIR, 'hg'), 'r')
        lines = [line.rstrip() for line in f]
        lines[0] += ' -3'
        f.close()
        f = open(os.path.join(BINDIR, 'hg'), 'w')
        for line in lines:
            f.write(line + '\n')
        f.close()

    hgbat = os.path.join(BINDIR, 'hg.bat')
    if os.path.isfile(hgbat):
        # hg.bat expects to be put in bin/scripts while run-tests.py
        # installation layout put it in bin/ directly. Fix it
        f = open(hgbat, 'rb')
        data = f.read()
        f.close()
        if '"%~dp0..\python" "%~dp0hg" %*' in data:
            data = data.replace('"%~dp0..\python" "%~dp0hg" %*',
                                '"%~dp0python" "%~dp0hg" %*')
            f = open(hgbat, 'wb')
            f.write(data)
            f.close()
        else:
            print 'WARNING: cannot fix hg.bat reference to python.exe'

    if options.anycoverage:
        custom = os.path.join(TESTDIR, 'sitecustomize.py')
        target = os.path.join(PYTHONDIR, 'sitecustomize.py')
        vlog('# Installing coverage trigger to %s' % target)
        shutil.copyfile(custom, target)
        rc = os.path.join(TESTDIR, '.coveragerc')
        vlog('# Installing coverage rc to %s' % rc)
        os.environ['COVERAGE_PROCESS_START'] = rc
        fn = os.path.join(INST, '..', '.coverage')
        os.environ['COVERAGE_FILE'] = fn

def outputtimes(options):
    vlog('# Producing time report')
    times.sort(key=lambda t: (t[1], t[0]), reverse=True)
    cols = '%7.3f   %s'
    print '\n%-7s   %s' % ('Time', 'Test')
    for test, timetaken in times:
        print cols % (timetaken, test)

def outputcoverage(options):

    vlog('# Producing coverage report')
    os.chdir(PYTHONDIR)

    def covrun(*args):
        cmd = 'coverage %s' % ' '.join(args)
        vlog('# Running: %s' % cmd)
        os.system(cmd)

    covrun('-c')
    omit = ','.join(os.path.join(x, '*') for x in [BINDIR, TESTDIR])
    covrun('-i', '-r', '"--omit=%s"' % omit) # report
    if options.htmlcov:
        htmldir = os.path.join(TESTDIR, 'htmlcov')
        covrun('-i', '-b', '"--directory=%s"' % htmldir, '"--omit=%s"' % omit)
    if options.annotate:
        adir = os.path.join(TESTDIR, 'annotated')
        if not os.path.isdir(adir):
            os.mkdir(adir)
        covrun('-i', '-a', '"--directory=%s"' % adir, '"--omit=%s"' % omit)

def pytest(test, wd, options, replacements, env):
    py3kswitch = options.py3k_warnings and ' -3' or ''
    cmd = '%s%s "%s"' % (PYTHON, py3kswitch, test)
    vlog("# Running", cmd)
    if os.name == 'nt':
        replacements.append((r'\r\n', '\n'))
    return run(cmd, wd, options, replacements, env)

needescape = re.compile(r'[\x00-\x08\x0b-\x1f\x7f-\xff]').search
escapesub = re.compile(r'[\x00-\x08\x0b-\x1f\\\x7f-\xff]').sub
escapemap = dict((chr(i), r'\x%02x' % i) for i in range(256))
escapemap.update({'\\': '\\\\', '\r': r'\r'})
def escapef(m):
    return escapemap[m.group(0)]
def stringescape(s):
    return escapesub(escapef, s)

def rematch(el, l):
    try:
        # use \Z to ensure that the regex matches to the end of the string
        if os.name == 'nt':
            return re.match(el + r'\r?\n\Z', l)
        return re.match(el + r'\n\Z', l)
    except re.error:
        # el is an invalid regex
        return False

def globmatch(el, l):
    # The only supported special characters are * and ? plus / which also
    # matches \ on windows. Escaping of these caracters is supported.
    if el + '\n' == l:
        if os.altsep:
            # matching on "/" is not needed for this line
            return '-glob'
        return True
    i, n = 0, len(el)
    res = ''
    while i < n:
        c = el[i]
        i += 1
        if c == '\\' and el[i] in '*?\\/':
            res += el[i - 1:i + 1]
            i += 1
        elif c == '*':
            res += '.*'
        elif c == '?':
            res += '.'
        elif c == '/' and os.altsep:
            res += '[/\\\\]'
        else:
            res += re.escape(c)
    return rematch(res, l)

def linematch(el, l):
    if el == l: # perfect match (fast)
        return True
    if el:
        if el.endswith(" (esc)\n"):
            el = el[:-7].decode('string-escape') + '\n'
        if el == l or os.name == 'nt' and el[:-1] + '\r\n' == l:
            return True
        if el.endswith(" (re)\n"):
            return rematch(el[:-6], l)
        if el.endswith(" (glob)\n"):
            return globmatch(el[:-8], l)
        if os.altsep and l.replace('\\', '/') == el:
            return '+glob'
    return False

def tsttest(test, wd, options, replacements, env):
    # We generate a shell script which outputs unique markers to line
    # up script results with our source. These markers include input
    # line number and the last return code
    salt = "SALT" + str(time.time())
    def addsalt(line, inpython):
        if inpython:
            script.append('%s %d 0\n' % (salt, line))
        else:
            script.append('echo %s %s $?\n' % (salt, line))

    # After we run the shell script, we re-unify the script output
    # with non-active parts of the source, with synchronization by our
    # SALT line number markers. The after table contains the
    # non-active components, ordered by line number
    after = {}
    pos = prepos = -1

    # Expected shellscript output
    expected = {}

    # We keep track of whether or not we're in a Python block so we
    # can generate the surrounding doctest magic
    inpython = False

    # True or False when in a true or false conditional section
    skipping = None

    def hghave(reqs):
        # TODO: do something smarter when all other uses of hghave is gone
        tdir = TESTDIR.replace('\\', '/')
        proc = Popen4('%s -c "%s/hghave %s"' %
                      (options.shell, tdir, ' '.join(reqs)), wd, 0)
        stdout, stderr = proc.communicate()
        ret = proc.wait()
        if wifexited(ret):
            ret = os.WEXITSTATUS(ret)
        if ret == 2:
            print stdout
            sys.exit(1)
        return ret == 0

    f = open(test)
    t = f.readlines()
    f.close()

    script = []
    if options.debug:
        script.append('set -x\n')
    if os.getenv('MSYSTEM'):
        script.append('alias pwd="pwd -W"\n')
    n = 0
    for n, l in enumerate(t):
        if not l.endswith('\n'):
            l += '\n'
        if l.startswith('#if'):
            if skipping is not None:
                after.setdefault(pos, []).append('  !!! nested #if\n')
            skipping = not hghave(l.split()[1:])
            after.setdefault(pos, []).append(l)
        elif l.startswith('#else'):
            if skipping is None:
                after.setdefault(pos, []).append('  !!! missing #if\n')
            skipping = not skipping
            after.setdefault(pos, []).append(l)
        elif l.startswith('#endif'):
            if skipping is None:
                after.setdefault(pos, []).append('  !!! missing #if\n')
            skipping = None
            after.setdefault(pos, []).append(l)
        elif skipping:
            after.setdefault(pos, []).append(l)
        elif l.startswith('  >>> '): # python inlines
            after.setdefault(pos, []).append(l)
            prepos = pos
            pos = n
            if not inpython:
                # we've just entered a Python block, add the header
                inpython = True
                addsalt(prepos, False) # make sure we report the exit code
                script.append('%s -m heredoctest <<EOF\n' % PYTHON)
            addsalt(n, True)
            script.append(l[2:])
        elif l.startswith('  ... '): # python inlines
            after.setdefault(prepos, []).append(l)
            script.append(l[2:])
        elif l.startswith('  $ '): # commands
            if inpython:
                script.append("EOF\n")
                inpython = False
            after.setdefault(pos, []).append(l)
            prepos = pos
            pos = n
            addsalt(n, False)
            cmd = l[4:].split()
            if len(cmd) == 2 and cmd[0] == 'cd':
                l = '  $ cd %s || exit 1\n' % cmd[1]
            script.append(l[4:])
        elif l.startswith('  > '): # continuations
            after.setdefault(prepos, []).append(l)
            script.append(l[4:])
        elif l.startswith('  '): # results
            # queue up a list of expected results
            expected.setdefault(pos, []).append(l[2:])
        else:
            if inpython:
                script.append("EOF\n")
                inpython = False
            # non-command/result - queue up for merged output
            after.setdefault(pos, []).append(l)

    if inpython:
        script.append("EOF\n")
    if skipping is not None:
        after.setdefault(pos, []).append('  !!! missing #endif\n')
    addsalt(n + 1, False)

    # Write out the script and execute it
    name = wd + '.sh'
    f = open(name, 'w')
    for l in script:
        f.write(l)
    f.close()

    cmd = '%s "%s"' % (options.shell, name)
    vlog("# Running", cmd)
    exitcode, output = run(cmd, wd, options, replacements, env)
    # do not merge output if skipped, return hghave message instead
    # similarly, with --debug, output is None
    if exitcode == SKIPPED_STATUS or output is None:
        return exitcode, output

    # Merge the script output back into a unified test

    warnonly = True
    pos = -1
    postout = []
    for l in output:
        lout, lcmd = l, None
        if salt in l:
            lout, lcmd = l.split(salt, 1)

        if lout:
            if not lout.endswith('\n'):
                lout += ' (no-eol)\n'

            # find the expected output at the current position
            el = None
            if pos in expected and expected[pos]:
                el = expected[pos].pop(0)

            r = linematch(el, lout)
            if isinstance(r, str):
                if r == '+glob':
                    lout = el[:-1] + ' (glob)\n'
                    r = 0 # warn only
                elif r == '-glob':
                    lout = ''.join(el.rsplit(' (glob)', 1))
                    r = 0 # warn only
                else:
                    log('\ninfo, unknown linematch result: %r\n' % r)
                    r = False
            if r:
                postout.append("  " + el)
            else:
                if needescape(lout):
                    lout = stringescape(lout.rstrip('\n')) + " (esc)\n"
                postout.append("  " + lout) # let diff deal with it
                if r != 0: # != warn only
                    warnonly = False

        if lcmd:
            # add on last return code
            ret = int(lcmd.split()[1])
            if ret != 0:
                postout.append("  [%s]\n" % ret)
            if pos in after:
                # merge in non-active test bits
                postout += after.pop(pos)
            pos = int(lcmd.split()[0])

    if pos in after:
        postout += after.pop(pos)

    if warnonly and exitcode == 0:
        exitcode = False
    return exitcode, postout

wifexited = getattr(os, "WIFEXITED", lambda x: False)
def run(cmd, wd, options, replacements, env):
    """Run command in a sub-process, capturing the output (stdout and stderr).
    Return a tuple (exitcode, output).  output is None in debug mode."""
    # TODO: Use subprocess.Popen if we're running on Python 2.4
    if options.debug:
        proc = subprocess.Popen(cmd, shell=True, cwd=wd, env=env)
        ret = proc.wait()
        return (ret, None)

    proc = Popen4(cmd, wd, options.timeout, env)
    def cleanup():
        terminate(proc)
        ret = proc.wait()
        if ret == 0:
            ret = signal.SIGTERM << 8
        killdaemons(env['DAEMON_PIDS'])
        return ret

    output = ''
    proc.tochild.close()

    try:
        output = proc.fromchild.read()
    except KeyboardInterrupt:
        vlog('# Handling keyboard interrupt')
        cleanup()
        raise

    ret = proc.wait()
    if wifexited(ret):
        ret = os.WEXITSTATUS(ret)

    if proc.timeout:
        ret = 'timeout'

    if ret:
        killdaemons(env['DAEMON_PIDS'])

    if abort:
        raise KeyboardInterrupt()

    for s, r in replacements:
        output = re.sub(s, r, output)
    return ret, output.splitlines(True)

def runone(options, test, count):
    '''returns a result element: (code, test, msg)'''

    def skip(msg):
        if options.verbose:
            log("\nSkipping %s: %s" % (testpath, msg))
        return 's', test, msg

    def fail(msg, ret):
        warned = ret is False
        if not options.nodiff:
            log("\n%s: %s %s" % (warned and 'Warning' or 'ERROR', test, msg))
        if (not ret and options.interactive
            and os.path.exists(testpath + ".err")):
            iolock.acquire()
            print "Accept this change? [n] ",
            answer = sys.stdin.readline().strip()
            iolock.release()
            if answer.lower() in "y yes".split():
                if test.endswith(".t"):
                    rename(testpath + ".err", testpath)
                else:
                    rename(testpath + ".err", testpath + ".out")
                return '.', test, ''
        return warned and '~' or '!', test, msg

    def success():
        return '.', test, ''

    def ignore(msg):
        return 'i', test, msg

    def describe(ret):
        if ret < 0:
            return 'killed by signal %d' % -ret
        return 'returned error code %d' % ret

    testpath = os.path.join(TESTDIR, test)
    err = os.path.join(TESTDIR, test + ".err")
    lctest = test.lower()

    if not os.path.exists(testpath):
            return skip("doesn't exist")

    if not (options.whitelisted and test in options.whitelisted):
        if options.blacklist and test in options.blacklist:
            return skip("blacklisted")

        if options.retest and not os.path.exists(test + ".err"):
            return ignore("not retesting")

        if options.keywords:
            fp = open(test)
            t = fp.read().lower() + test.lower()
            fp.close()
            for k in options.keywords.lower().split():
                if k in t:
                    break
                else:
                    return ignore("doesn't match keyword")

    if not lctest.startswith("test-"):
        return skip("not a test file")
    for ext, func, out in testtypes:
        if lctest.endswith(ext):
            runner = func
            ref = os.path.join(TESTDIR, test + out)
            break
    else:
        return skip("unknown test type")

    vlog("# Test", test)

    if os.path.exists(err):
        os.remove(err)       # Remove any previous output files

    # Make a tmp subdirectory to work in
    threadtmp = os.path.join(HGTMP, "child%d" % count)
    testtmp = os.path.join(threadtmp, os.path.basename(test))
    os.mkdir(threadtmp)
    os.mkdir(testtmp)

    port = options.port + count * 3
    replacements = [
        (r':%s\b' % port, ':$HGPORT'),
        (r':%s\b' % (port + 1), ':$HGPORT1'),
        (r':%s\b' % (port + 2), ':$HGPORT2'),
        ]
    if os.name == 'nt':
        replacements.append(
            (''.join(c.isalpha() and '[%s%s]' % (c.lower(), c.upper()) or
                     c in '/\\' and r'[/\\]' or
                     c.isdigit() and c or
                     '\\' + c
                     for c in testtmp), '$TESTTMP'))
    else:
        replacements.append((re.escape(testtmp), '$TESTTMP'))

    env = createenv(options, testtmp, threadtmp, port)
    createhgrc(env['HGRCPATH'], options)

    starttime = time.time()
    try:
        ret, out = runner(testpath, testtmp, options, replacements, env)
    except KeyboardInterrupt:
        endtime = time.time()
        log('INTERRUPTED: %s (after %d seconds)' % (test, endtime - starttime))
        raise
    endtime = time.time()
    times.append((test, endtime - starttime))
    vlog("# Ret was:", ret)

    killdaemons(env['DAEMON_PIDS'])

    skipped = (ret == SKIPPED_STATUS)

    # If we're not in --debug mode and reference output file exists,
    # check test output against it.
    if options.debug:
        refout = None                   # to match "out is None"
    elif os.path.exists(ref):
        f = open(ref, "r")
        refout = f.read().splitlines(True)
        f.close()
    else:
        refout = []

    if (ret != 0 or out != refout) and not skipped and not options.debug:
        # Save errors to a file for diagnosis
        f = open(err, "wb")
        for line in out:
            f.write(line)
        f.close()

    if skipped:
        if out is None:                 # debug mode: nothing to parse
            missing = ['unknown']
            failed = None
        else:
            missing, failed = parsehghaveoutput(out)
        if not missing:
            missing = ['irrelevant']
        if failed:
            result = fail("hghave failed checking for %s" % failed[-1], ret)
            skipped = False
        else:
            result = skip(missing[-1])
    elif ret == 'timeout':
        result = fail("timed out", ret)
    elif out != refout:
        if not options.nodiff:
            iolock.acquire()
            if options.view:
                os.system("%s %s %s" % (options.view, ref, err))
            else:
                showdiff(refout, out, ref, err)
            iolock.release()
        if ret:
            result = fail("output changed and " + describe(ret), ret)
        else:
            result = fail("output changed", ret)
    elif ret:
        result = fail(describe(ret), ret)
    else:
        result = success()

    if not options.verbose:
        iolock.acquire()
        sys.stdout.write(result[0])
        sys.stdout.flush()
        iolock.release()

    if not options.keep_tmpdir:
        shutil.rmtree(threadtmp, True)
    return result

_hgpath = None

def _gethgpath():
    """Return the path to the mercurial package that is actually found by
    the current Python interpreter."""
    global _hgpath
    if _hgpath is not None:
        return _hgpath

    cmd = '%s -c "import mercurial; print (mercurial.__path__[0])"'
    pipe = os.popen(cmd % PYTHON)
    try:
        _hgpath = pipe.read().strip()
    finally:
        pipe.close()
    return _hgpath

def _checkhglib(verb):
    """Ensure that the 'mercurial' package imported by python is
    the one we expect it to be.  If not, print a warning to stderr."""
    expecthg = os.path.join(PYTHONDIR, 'mercurial')
    actualhg = _gethgpath()
    if os.path.abspath(actualhg) != os.path.abspath(expecthg):
        sys.stderr.write('warning: %s with unexpected mercurial lib: %s\n'
                         '         (expected %s)\n'
                         % (verb, actualhg, expecthg))

results = {'.':[], '!':[], '~': [], 's':[], 'i':[]}
times = []
iolock = threading.Lock()
abort = False

def scheduletests(options, tests):
    jobs = options.jobs
    done = queue.Queue()
    running = 0
    count = 0
    global abort

    def job(test, count):
        try:
            done.put(runone(options, test, count))
        except KeyboardInterrupt:
            pass
        except: # re-raises
            done.put(('!', test, 'run-test raised an error, see traceback'))
            raise

    try:
        while tests or running:
            if not done.empty() or running == jobs or not tests:
                try:
                    code, test, msg = done.get(True, 1)
                    results[code].append((test, msg))
                    if options.first and code not in '.si':
                        break
                except queue.Empty:
                    continue
                running -= 1
            if tests and not running == jobs:
                test = tests.pop(0)
                if options.loop:
                    tests.append(test)
                t = threading.Thread(target=job, name=test, args=(test, count))
                t.start()
                running += 1
                count += 1
    except KeyboardInterrupt:
        abort = True

def runtests(options, tests):
    try:
        if INST:
            installhg(options)
            _checkhglib("Testing")
        else:
            usecorrectpython()

        if options.restart:
            orig = list(tests)
            while tests:
                if os.path.exists(tests[0] + ".err"):
                    break
                tests.pop(0)
            if not tests:
                print "running all tests"
                tests = orig

        scheduletests(options, tests)

        failed = len(results['!'])
        warned = len(results['~'])
        tested = len(results['.']) + failed + warned
        skipped = len(results['s'])
        ignored = len(results['i'])

        print
        if not options.noskips:
            for s in results['s']:
                print "Skipped %s: %s" % s
        for s in results['~']:
            print "Warned %s: %s" % s
        for s in results['!']:
            print "Failed %s: %s" % s
        _checkhglib("Tested")
        print "# Ran %d tests, %d skipped, %d warned, %d failed." % (
            tested, skipped + ignored, warned, failed)
        if results['!']:
            print 'python hash seed:', os.environ['PYTHONHASHSEED']
        if options.time:
            outputtimes(options)

        if options.anycoverage:
            outputcoverage(options)
    except KeyboardInterrupt:
        failed = True
        print "\ninterrupted!"

    if failed:
        return 1
    if warned:
        return 80

testtypes = [('.py', pytest, '.out'),
             ('.t', tsttest, '')]

def main():
    (options, args) = parseargs()
    os.umask(022)

    checktools()

    if len(args) == 0:
        args = [t for t in os.listdir(".")
                if t.startswith("test-")
                and (t.endswith(".py") or t.endswith(".t"))]

    tests = args

    if options.random:
        random.shuffle(tests)
    else:
        # keywords for slow tests
        slow = 'svn gendoc check-code-hg'.split()
        def sortkey(f):
            # run largest tests first, as they tend to take the longest
            try:
                val = -os.stat(f).st_size
            except OSError, e:
                if e.errno != errno.ENOENT:
                    raise
                return -1e9 # file does not exist, tell early
            for kw in slow:
                if kw in f:
                    val *= 10
            return val
        tests.sort(key=sortkey)

    if 'PYTHONHASHSEED' not in os.environ:
        # use a random python hash seed all the time
        # we do the randomness ourself to know what seed is used
        os.environ['PYTHONHASHSEED'] = str(random.getrandbits(32))

    global TESTDIR, HGTMP, INST, BINDIR, TMPBINDIR, PYTHONDIR, COVERAGE_FILE
    TESTDIR = os.environ["TESTDIR"] = os.getcwd()
    if options.tmpdir:
        options.keep_tmpdir = True
        tmpdir = options.tmpdir
        if os.path.exists(tmpdir):
            # Meaning of tmpdir has changed since 1.3: we used to create
            # HGTMP inside tmpdir; now HGTMP is tmpdir.  So fail if
            # tmpdir already exists.
            sys.exit("error: temp dir %r already exists" % tmpdir)

            # Automatically removing tmpdir sounds convenient, but could
            # really annoy anyone in the habit of using "--tmpdir=/tmp"
            # or "--tmpdir=$HOME".
            #vlog("# Removing temp dir", tmpdir)
            #shutil.rmtree(tmpdir)
        os.makedirs(tmpdir)
    else:
        d = None
        if os.name == 'nt':
            # without this, we get the default temp dir location, but
            # in all lowercase, which causes troubles with paths (issue3490)
            d = os.getenv('TMP')
        tmpdir = tempfile.mkdtemp('', 'hgtests.', d)
    HGTMP = os.environ['HGTMP'] = os.path.realpath(tmpdir)

    if options.with_hg:
        INST = None
        BINDIR = os.path.dirname(os.path.realpath(options.with_hg))
        TMPBINDIR = os.path.join(HGTMP, 'install', 'bin')
        os.makedirs(TMPBINDIR)

        # This looks redundant with how Python initializes sys.path from
        # the location of the script being executed.  Needed because the
        # "hg" specified by --with-hg is not the only Python script
        # executed in the test suite that needs to import 'mercurial'
        # ... which means it's not really redundant at all.
        PYTHONDIR = BINDIR
    else:
        INST = os.path.join(HGTMP, "install")
        BINDIR = os.environ["BINDIR"] = os.path.join(INST, "bin")
        TMPBINDIR = BINDIR
        PYTHONDIR = os.path.join(INST, "lib", "python")

    os.environ["BINDIR"] = BINDIR
    os.environ["PYTHON"] = PYTHON

    path = [BINDIR] + os.environ["PATH"].split(os.pathsep)
    if TMPBINDIR != BINDIR:
        path = [TMPBINDIR] + path
    os.environ["PATH"] = os.pathsep.join(path)

    # Include TESTDIR in PYTHONPATH so that out-of-tree extensions
    # can run .../tests/run-tests.py test-foo where test-foo
    # adds an extension to HGRC. Also include run-test.py directory to import
    # modules like heredoctest.
    pypath = [PYTHONDIR, TESTDIR, os.path.abspath(os.path.dirname(__file__))]
    # We have to augment PYTHONPATH, rather than simply replacing
    # it, in case external libraries are only available via current
    # PYTHONPATH.  (In particular, the Subversion bindings on OS X
    # are in /opt/subversion.)
    oldpypath = os.environ.get(IMPL_PATH)
    if oldpypath:
        pypath.append(oldpypath)
    os.environ[IMPL_PATH] = os.pathsep.join(pypath)

    COVERAGE_FILE = os.path.join(TESTDIR, ".coverage")

    vlog("# Using TESTDIR", TESTDIR)
    vlog("# Using HGTMP", HGTMP)
    vlog("# Using PATH", os.environ["PATH"])
    vlog("# Using", IMPL_PATH, os.environ[IMPL_PATH])

    try:
        sys.exit(runtests(options, tests) or 0)
    finally:
        time.sleep(.1)
        cleanup(options)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test-url-parsing
import sys

try:
    import dulwich
except ImportError:
    print "skipped: missing feature: dulwich"
    sys.exit(80)

import os, tempfile, unittest, shutil
from mercurial import ui, hg, commands

sys.path.append(os.path.join(os.path.dirname(__file__), os.path.pardir))

from hggit.git_handler import GitHandler


class TestUrlParsing(object):
    def setUp(self):
        # create a test repo location.
        self.tmpdir = tempfile.mkdtemp('hg-git_url-test')
        commands.init(ui.ui(), self.tmpdir)
        repo = hg.repository(ui.ui(), self.tmpdir)
        self.handler = GitHandler(repo, ui.ui())

    def tearDown(self):
        # remove the temp repo
        shutil.rmtree(self.tmpdir)

    def assertEquals(self, l, r):
        print '%% expect %r' % (r, )
        print l
        assert l == r

    def test_ssh_github_style_slash(self):
        url = "git+ssh://git@github.com/webjam/webjam.git"
        client, path = self.handler.get_transport_and_path(url)
        self.assertEquals(path, '/webjam/webjam.git')
        self.assertEquals(client.host, 'git@github.com')

    def test_ssh_github_style_colon_number_starting_username(self):
        url = "git+ssh://git@github.com:42qu/vps.git"
        client, path = self.handler.get_transport_and_path(url)
        self.assertEquals(path, '42qu/vps.git')
        self.assertEquals(client.host, 'git@github.com')

    def test_ssh_github_style_colon(self):
        url = "git+ssh://git@github.com:webjam/webjam.git"
        client, path = self.handler.get_transport_and_path(url)
        self.assertEquals(path, 'webjam/webjam.git')
        self.assertEquals(client.host, 'git@github.com')

    def test_ssh_heroku_style(self):
        url = "git+ssh://git@heroku.com:webjam.git"
        client, path = self.handler.get_transport_and_path(url)
        self.assertEquals(path, 'webjam.git')
        self.assertEquals(client.host, 'git@heroku.com')
        # also test that it works even if heroku isn't in the name
        url = "git+ssh://git@compatible.com:webjam.git"
        client, path = self.handler.get_transport_and_path(url)
        self.assertEquals(path, 'webjam.git')
        self.assertEquals(client.host, 'git@compatible.com')

    def test_ssh_heroku_style_with_trailing_slash(self):
        # some versions of mercurial add a trailing slash even if
        #  the user didn't supply one.
        url = "git+ssh://git@heroku.com:webjam.git/"
        client, path = self.handler.get_transport_and_path(url)
        self.assertEquals(path, 'webjam.git')
        self.assertEquals(client.host, 'git@heroku.com')

    def test_heroku_style_with_port(self):
        url = "git+ssh://git@heroku.com:999:webjam.git"
        client, path = self.handler.get_transport_and_path(url)
        self.assertEquals(path, 'webjam.git')
        self.assertEquals(client.host, 'git@heroku.com')
        self.assertEquals(client.port, '999')

    def test_gitdaemon_style(self):
        url = "git://github.com/webjam/webjam.git"
        client, path = self.handler.get_transport_and_path(url)
        self.assertEquals(path, '/webjam/webjam.git')
        try:
            self.assertEquals(client._host, 'github.com')
        except AttributeError:
            self.assertEquals(client.host, 'github.com')

    def test_ssh_github_style_slash_with_port(self):
        url = "git+ssh://git@github.com:10022/webjam/webjam.git"
        client, path = self.handler.get_transport_and_path(url)
        self.assertEquals(path, '/webjam/webjam.git')
        self.assertEquals(client.host, 'git@github.com')
        self.assertEquals(client.port, '10022')

    def test_gitdaemon_style_with_port(self):
        url = "git://github.com:19418/webjam/webjam.git"
        client, path = self.handler.get_transport_and_path(url)
        self.assertEquals(path, '/webjam/webjam.git')
        try:
            self.assertEquals(client._host, 'github.com')
        except AttributeError:
            self.assertEquals(client.host, 'github.com')
        self.assertEquals(client._port, '19418')

if __name__ == '__main__':
    tc = TestUrlParsing()
    for test in sorted([t for t in dir(tc) if t.startswith('test_')]):
        tc.setUp()
        getattr(tc, test)()
        tc.tearDown()

########NEW FILE########
