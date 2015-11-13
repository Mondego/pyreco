__FILENAME__ = future27
# Copyright (C) 2001-2010 Python Software Foundation; All Rights Reserved

# This file contains backports for Python 2.5 based on Python 2.7's standard library

__all__ = ['namedtuple']

from operator import itemgetter as _itemgetter
from keyword import iskeyword as _iskeyword
import sys as _sys

#################################################################
# collections.namedtuple

try:
  # try to use the standard library's namedtuple...
  from collections import namedtuple

except ImportError:
  # use namedtuple backport

  # the factory function
  def namedtuple(typename, field_names, verbose=False):
    """Returns a new subclass of tuple with named fields.

    >>> Point = namedtuple('Point', 'x y')
    >>> Point.__doc__                   # docstring for the new class
    'Point(x, y)'
    >>> p = Point(11, y=22)             # instantiate with positional args or keywords
    >>> p[0] + p[1]                     # indexable like a plain tuple
    33
    >>> x, y = p                        # unpack like a regular tuple
    >>> x, y
    (11, 22)
    >>> p.x + p.y                       # fields also accessable by name
    33
    >>> d = p._asdict()                 # convert to a dictionary
    >>> d['x']
    11
    >>> Point(**d)                      # convert from a dictionary
    Point(x=11, y=22)
    >>> p._replace(x=100)               # _replace() is like str.replace() but targets named fields
    Point(x=100, y=22)

    """

    # Parse and validate the field names.  Validation serves two purposes,
    # generating informative error messages and preventing template injection attacks.
    if isinstance(field_names, basestring):
        field_names = field_names.replace(',', ' ').split() # names separated by whitespace and/or commas
    field_names = tuple(map(str, field_names))
    for name in (typename,) + field_names:
        if not all(c.isalnum() or c=='_' for c in name):
            raise ValueError('Type names and field names can only contain alphanumeric characters and underscores: %r' % name)
        if _iskeyword(name):
            raise ValueError('Type names and field names cannot be a keyword: %r' % name)
        if name[0].isdigit():
            raise ValueError('Type names and field names cannot start with a number: %r' % name)
    seen_names = set()
    for name in field_names:
        if name.startswith('_'):
            raise ValueError('Field names cannot start with an underscore: %r' % name)
        if name in seen_names:
            raise ValueError('Encountered duplicate field name: %r' % name)
        seen_names.add(name)

    # Create and fill-in the class template
    numfields = len(field_names)
    argtxt = repr(field_names).replace("'", "")[1:-1]   # tuple repr without parens or quotes
    reprtxt = ', '.join('%s=%%r' % name for name in field_names)
    dicttxt = ', '.join('%r: t[%d]' % (name, pos) for pos, name in enumerate(field_names))
    template = '''class %(typename)s(tuple):
        '%(typename)s(%(argtxt)s)' \n
        __slots__ = () \n
        _fields = %(field_names)r \n
        def __new__(cls, %(argtxt)s):
            return tuple.__new__(cls, (%(argtxt)s)) \n
        @classmethod
        def _make(cls, iterable, new=tuple.__new__, len=len):
            'Make a new %(typename)s object from a sequence or iterable'
            result = new(cls, iterable)
            if len(result) != %(numfields)d:
                raise TypeError('Expected %(numfields)d arguments, got %%d' %% len(result))
            return result \n
        def __repr__(self):
            return '%(typename)s(%(reprtxt)s)' %% self \n
        def _asdict(t):
            'Return a new dict which maps field names to their values'
            return {%(dicttxt)s} \n
        def _replace(self, **kwds):
            'Return a new %(typename)s object replacing specified fields with new values'
            result = self._make(map(kwds.pop, %(field_names)r, self))
            if kwds:
                raise ValueError('Got unexpected field names: %%r' %% kwds.keys())
            return result \n
        def __getnewargs__(self):
            return tuple(self) \n\n''' % locals()
    for i, name in enumerate(field_names):
        template += '        %s = property(itemgetter(%d))\n' % (name, i)
    if verbose:
        print template

    # Execute the template string in a temporary namespace and
    # support tracing utilities by setting a value for frame.f_globals['__name__']
    namespace = dict(itemgetter=_itemgetter, __name__='namedtuple_%s' % typename)
    try:
        exec template in namespace
    except SyntaxError, e:
        raise SyntaxError(e.message + ':\n' + template)
    result = namespace[typename]

    # For pickling to work, the __module__ variable needs to be set to the frame
    # where the named tuple is created.  Bypass this step in enviroments where
    # sys._getframe is not defined (Jython for example).
    if hasattr(_sys, '_getframe'):
        result.__module__ = _sys._getframe(1).f_globals['__name__']

    return result



############################################################################
# unit test

if __name__ == '__main__':
    # verify that instances can be pickled
    from cPickle import loads, dumps
    Point = namedtuple('Point', 'x, y', True)
    p = Point(x=10, y=20)
    assert p == loads(dumps(p))

    # test and demonstrate ability to override methods
    class Point(namedtuple('Point', 'x y')):
        __slots__ = ()
        @property
        def hypot(self):
            return (self.x ** 2 + self.y ** 2) ** 0.5
        def __str__(self):
            return 'Point: x=%6.3f  y=%6.3f  hypot=%6.3f' % (self.x, self.y, self.hypot)

    for p in Point(3, 4), Point(14, 5/7.):
        print p

    class Point(namedtuple('Point', 'x y')):
        'Point class with optimized _make() and _replace() without error-checking'
        __slots__ = ()
        _make = classmethod(tuple.__new__)
        def _replace(self, _map=map, **kwds):
            return self._make(_map(kwds.get, ('x', 'y'), self))

    print Point(11, 22)._replace(x=100)

    Point3D = namedtuple('Point3D', Point._fields + ('z',))
    print Point3D.__doc__

    import doctest
    TestResults = namedtuple('TestResults', 'failed attempted')
    print TestResults(*doctest.testmod())

########NEW FILE########
__FILENAME__ = git_fs
# -*- coding: iso-8859-1 -*-
#
# Copyright (C) 2006-2011, Herbert Valerio Riedel <hvr@gnu.org>
#
# See COPYING for distribution information

from trac.core import *
from trac.util import TracError, shorten_line
from trac.util.datefmt import FixedOffset, to_timestamp, format_datetime
from trac.util.text import to_unicode
from trac.versioncontrol.api import \
     Changeset, Node, Repository, IRepositoryConnector, NoSuchChangeset, NoSuchNode, \
     IRepositoryProvider
from trac.wiki import IWikiSyntaxProvider
from trac.versioncontrol.cache import CachedRepository, CachedChangeset
from trac.versioncontrol.web_ui import IPropertyRenderer
from trac.config import BoolOption, IntOption, PathOption, Option
from trac.web.chrome import Chrome

from genshi.builder import tag

from datetime import datetime
import sys
import os

if not sys.version_info[:2] >= (2, 5):
    raise TracError("Python >= 2.5 dependancy not met")

import PyGIT


class GitCachedRepository(CachedRepository):
    """
    Git-specific cached repository

    Passes through {display,short,normalize}_rev
    """

    def display_rev(self, rev):
        return self.short_rev(rev)

    def short_rev(self, path):
        return self.repos.short_rev(path)

    def normalize_rev(self, rev):
        if not rev:
            return self.repos.get_youngest_rev()
        normrev = self.repos.git.verifyrev(rev)
        if normrev is None:
            raise NoSuchChangeset(rev)
        return normrev

    def get_changeset(self, rev):
        return GitCachedChangeset(self, self.normalize_rev(rev), self.env)


class GitCachedChangeset(CachedChangeset):
    """
    Git-specific cached changeset

    Handles get_branches()
    """
    def get_branches(self):
        _rev = self.rev

        return [ (k, v == _rev) for k, v in
                 self.repos.repos.git.get_branch_contains(_rev, resolve=True) ]


def _last_iterable(iterable):
    "helper for detecting last iteration in for-loop"
    i = iter(iterable)
    v = i.next()
    for nextv in i:
        yield False, v
        v = nextv
    yield True, v

def intersperse(sep, iterable):
    """
    The 'intersperse' generator takes an element and an iterable and
    intersperses that element between the elements of the iterable.

    inspired by Haskell's Data.List.intersperse
    """

    for i, item in enumerate(iterable):
        if i: yield sep
        yield item

# helper
def _parse_user_time(s):
    """
    parse author/committer attribute lines and return
    (user,timestamp)
    """

    user, time, tz_str = s.rsplit(None, 2)
    tz = FixedOffset((int(tz_str)*6)/10, tz_str)
    time = datetime.fromtimestamp(float(time), tz)
    return user, time

class GitConnector(Component):
    implements(IRepositoryConnector, IWikiSyntaxProvider)

    def __init__(self):
        self._version = None

        try:
            self._version = PyGIT.Storage.git_version(git_bin=self._git_bin)
        except PyGIT.GitError, e:
            self.log.error("GitError: " + str(e))

        if self._version:
            self.log.info("detected GIT version %s" % self._version['v_str'])
            self.env.systeminfo.append(('GIT', self._version['v_str']))
            if not self._version['v_compatible']:
                self.log.error("GIT version %s installed not compatible (need >= %s)" %
                               (self._version['v_str'], self._version['v_min_str']))

    #######################
    # IWikiSyntaxProvider

    def _format_sha_link(self, formatter, sha, label):
        # FIXME: this function needs serious rethinking...

        reponame = ''

        context = formatter.context
        while context:
            if context.resource.realm in ('source', 'changeset'):
                reponame = context.resource.parent.id
                break
            context = context.parent

        try:
            repos = self.env.get_repository(reponame)

            if not repos:
                raise Exception("Repository '%s' not found" % reponame)

            sha = repos.normalize_rev(sha) # in case it was abbreviated
            changeset = repos.get_changeset(sha)
            return tag.a(label, class_="changeset",
                         title=shorten_line(changeset.message),
                         href=formatter.href.changeset(sha, repos.reponame))
        except Exception, e:
            return tag.a(label, class_="missing changeset",
                         title=to_unicode(e), rel="nofollow")

    def get_wiki_syntax(self):
        yield (r'(?:\b|!)r?[0-9a-fA-F]{%d,40}\b' % self._wiki_shortrev_len,
               lambda fmt, sha, match: self._format_sha_link(fmt, sha.startswith('r') and sha[1:] or sha, sha))

    def get_link_resolvers(self):
        yield 'sha', lambda fmt, _, sha, label, match=None: self._format_sha_link(fmt, sha, label)

    #######################
    # IRepositoryConnector

    _persistent_cache = BoolOption('git', 'persistent_cache', 'false',
                                   "enable persistent caching of commit tree")

    _cached_repository = BoolOption('git', 'cached_repository', 'false',
                                    "wrap `GitRepository` in `CachedRepository`")

    _shortrev_len = IntOption('git', 'shortrev_len', 7,
                              "length rev sha sums should be tried to be abbreviated to"
                              " (must be >= 4 and <= 40)")

    _wiki_shortrev_len = IntOption('git', 'wiki_shortrev_len', 40,
                                   "minimum length of hex-string for which auto-detection as sha id is performed"
                                   " (must be >= 4 and <= 40)")

    _trac_user_rlookup = BoolOption('git', 'trac_user_rlookup', 'false',
                                    "enable reverse mapping of git email addresses to trac user ids")

    _use_committer_id = BoolOption('git', 'use_committer_id', 'true',
                                   "use git-committer id instead of git-author id as changeset owner")

    _use_committer_time = BoolOption('git', 'use_committer_time', 'true',
                                     "use git-committer-author timestamp instead of git-author timestamp"
                                     " as changeset timestamp")

    _git_fs_encoding = Option('git', 'git_fs_encoding', 'utf-8',
                              "define charset encoding of paths within git repository")

    _git_bin = PathOption('git', 'git_bin', '/usr/bin/git',
                          "path to git executable (relative to trac project folder!)")


    def get_supported_types(self):
        yield ("git", 8)

    def get_repository(self, type, dir, params):
        """GitRepository factory method"""
        assert type == "git"

        if not (4 <= self._shortrev_len <= 40):
            raise TracError("shortrev_len must be withing [4..40]")

        if not (4 <= self._wiki_shortrev_len <= 40):
            raise TracError("wiki_shortrev_len must be withing [4..40]")

        if not self._version:
            raise TracError("GIT backend not available")
        elif not self._version['v_compatible']:
            raise TracError("GIT version %s installed not compatible (need >= %s)" %
                            (self._version['v_str'], self._version['v_min_str']))

        if self._trac_user_rlookup:
            def rlookup_uid(email):
                """
                reverse map 'real name <user@domain.tld>' addresses to trac user ids

                returns None if lookup failed
                """

                try:
                    _, email = email.rsplit('<', 1)
                    email, _ = email.split('>', 1)
                    email = email.lower()
                except Exception:
                    return None

                for _uid, _name, _email in self.env.get_known_users():
                    try:
                        if email == _email.lower():
                            return _uid
                    except Exception:
                        continue

        else:
            def rlookup_uid(_):
                return None

        repos = GitRepository(dir, params, self.log,
                              persistent_cache=self._persistent_cache,
                              git_bin=self._git_bin,
                              git_fs_encoding=self._git_fs_encoding,
                              shortrev_len=self._shortrev_len,
                              rlookup_uid=rlookup_uid,
                              use_committer_id=self._use_committer_id,
                              use_committer_time=self._use_committer_time,
                              )

        if self._cached_repository:
            repos = GitCachedRepository(self.env, repos, self.log)
            self.log.debug("enabled CachedRepository for '%s'" % dir)
        else:
            self.log.debug("disabled CachedRepository for '%s'" % dir)

        return repos


class CsetPropertyRenderer(Component):
    implements(IPropertyRenderer)

    # relied upon by GitChangeset
    def match_property(self, name, mode):
        # default renderer has priority 1
        return (name in ('Parents',
                         'Children',
                         'Branches',
                         'git-committer',
                         'git-author',
                         ) and mode == 'revprop') and 4 or 0

    def render_property(self, name, mode, context, props):

        def sha_link(sha, label=None):
            # sha is assumed to be a non-abbreviated 40-chars sha id
            try:
                reponame = context.resource.parent.id
                repos = self.env.get_repository(reponame)
                cset = repos.get_changeset(sha)
                if label is None:
                    label = repos.display_rev(sha)

                return tag.a(label, class_="changeset",
                             title=shorten_line(cset.message),
                             href=context.href.changeset(sha, repos.reponame))

            except Exception, e:
                return tag.a(sha, class_="missing changeset",
                             title=to_unicode(e), rel="nofollow")

        if name == 'Branches':
            branches = props[name]

            # simple non-merge commit
            return tag(*intersperse(', ', (sha_link(rev, label) for label, rev in branches)))

        elif name in ('Parents', 'Children'):
            revs = props[name] # list of commit ids

            if name == 'Parents' and len(revs) > 1:
                # we got a merge...
                current_sha = context.resource.id
                reponame = context.resource.parent.id

                parent_links = intersperse(', ', \
                    ((sha_link(rev),
                      ' (',
                      tag.a('diff',
                            title="Diff against this parent (show the changes merged from the other parents)",
                            href=context.href.changeset(current_sha, reponame, old=rev)),
                      ')')
                     for rev in revs))

                return tag(list(parent_links),
                           tag.br(),
                           tag.span(tag("Note: this is a ", tag.strong('merge'), " changeset, "
                                        "the changes displayed below correspond "
                                        "to the merge itself."),
                                    class_='hint'),
                           tag.br(),
                           tag.span(tag("Use the ", tag.tt('(diff)'), " links above"
                                        " to see all the changes relative to each parent."),
                                    class_='hint'))

            # simple non-merge commit
            return tag(*intersperse(', ', map(sha_link, revs)))

        elif name in ('git-committer', 'git-author'):
            user_, time_ = props[name]
            _str = "%s (%s)" % (Chrome(self.env).format_author(context.req, user_),
                                format_datetime(time_, tzinfo=context.req.tz))
            return unicode(_str)

        raise TracError("Internal error")



class GitRepository(Repository):
    """
    Git repository
    """

    def __init__(self, path, params, log,
                 persistent_cache=False,
                 git_bin='git',
                 git_fs_encoding='utf-8',
                 shortrev_len=7,
                 rlookup_uid=lambda _: None,
                 use_committer_id=False,
                 use_committer_time=False,
                 ):

        self.logger = log
        self.gitrepo = path
        self.params = params
        self._shortrev_len = max(4, min(shortrev_len, 40))
        self.rlookup_uid = rlookup_uid
        self._use_committer_time = use_committer_time
        self._use_committer_id = use_committer_id

        self.git = PyGIT.StorageFactory(path, log, not persistent_cache,
                                        git_bin=git_bin,
                                        git_fs_encoding=git_fs_encoding).getInstance()

        Repository.__init__(self, "git:"+path, self.params, log)

    def close(self):
        self.git = None

    def get_youngest_rev(self):
        return self.git.youngest_rev()

    def get_oldest_rev(self):
        return self.git.oldest_rev()

    def normalize_path(self, path):
        return path and path.strip('/') or '/'

    def normalize_rev(self, rev):
        if not rev:
            return self.get_youngest_rev()
        normrev = self.git.verifyrev(rev)
        if normrev is None:
            raise NoSuchChangeset(rev)
        return normrev

    def display_rev(self, rev):
        return self.short_rev(rev)

    def short_rev(self, rev):
        return self.git.shortrev(self.normalize_rev(rev), min_len=self._shortrev_len)

    def get_node(self, path, rev=None, historian=None):
        return GitNode(self, path, rev, self.log, None, historian)

    def get_quickjump_entries(self, rev):
        for bname, bsha in self.git.get_branches():
            yield 'branches', bname, '/', bsha
        for t in self.git.get_tags():
            yield 'tags', t, '/', t

    def get_path_url(self, path, rev):
        return self.params.get('url')

    def get_changesets(self, start, stop):
        for rev in self.git.history_timerange(to_timestamp(start), to_timestamp(stop)):
            yield self.get_changeset(rev)

    def get_changeset(self, rev):
        """GitChangeset factory method"""
        return GitChangeset(self, rev)

    def get_changes(self, old_path, old_rev, new_path, new_rev, ignore_ancestry=0):
        # TODO: handle renames/copies, ignore_ancestry
        if old_path != new_path:
            raise TracError("not supported in git_fs")

        with self.git.get_historian(old_rev, old_path.strip('/')) as old_historian:
            with self.git.get_historian(new_rev, new_path.strip('/')) as new_historian:
                for chg in self.git.diff_tree(old_rev, new_rev, self.normalize_path(new_path)):
                    mode1, mode2, obj1, obj2, action, path, path2 = chg

                    kind = Node.FILE
                    if mode2.startswith('04') or mode1.startswith('04'):
                        kind = Node.DIRECTORY

                    change = GitChangeset.action_map[action]

                    old_node = None
                    new_node = None

                    if change != Changeset.ADD:
                        old_node = self.get_node(path, old_rev, old_historian)
                    if change != Changeset.DELETE:
                        new_node = self.get_node(path, new_rev, new_historian)

                    yield old_node, new_node, kind, change

    def next_rev(self, rev, path=''):
        return self.git.hist_next_revision(rev)

    def previous_rev(self, rev, path=''):
        return self.git.hist_prev_revision(rev)

    def parent_revs(self, rev):
        return self.git.parents(rev)

    def child_revs(self, rev):
        return self.git.children(rev)

    def rev_older_than(self, rev1, rev2):
        rc = self.git.rev_is_anchestor_of(rev1, rev2)
        return rc

    # def clear(self, youngest_rev=None):
    #     self.youngest = None
    #     if youngest_rev is not None:
    #         self.youngest = self.normalize_rev(youngest_rev)
    #     self.oldest = None

    def clear(self, youngest_rev=None):
        self.sync()

    def sync(self, rev_callback=None, clean=None):
        if rev_callback:
            revs = set(self.git.all_revs())

        if not self.git.sync():
            return None # nothing expected to change

        if rev_callback:
            revs = set(self.git.all_revs()) - revs
            for rev in revs:
                rev_callback(rev)

class GitNode(Node):
    def __init__(self, repos, path, rev, log, ls_tree_info=None, historian=None):
        self.log = log
        self.repos = repos
        self.fs_sha = None # points to either tree or blobs
        self.fs_perm = None
        self.fs_size = None
        rev = rev and str(rev) or 'HEAD'

        kind = Node.DIRECTORY
        p = path.strip('/')
        if p: # ie. not the root-tree
            if not ls_tree_info:
                ls_tree_info = repos.git.ls_tree(rev, p) or None
                if ls_tree_info:
                    [ls_tree_info] = ls_tree_info

            if not ls_tree_info:
                raise NoSuchNode(path, rev)

            self.fs_perm, k, self.fs_sha, self.fs_size, _ = ls_tree_info

            # fix-up to the last commit-rev that touched this node
            rev = repos.git.last_change(rev, p, historian)

            if k == 'tree':
                pass
            elif k == 'commit':
                pass # FIXME: this is a workaround for missing git submodule support in the plugin
            elif k == 'blob':
                kind = Node.FILE
            else:
                raise TracError("Internal error (got unexpected object kind '%s')" % k)

        self.created_path = path
        self.created_rev = rev

        Node.__init__(self, repos, path, rev, kind)

    def __git_path(self):
        "return path as expected by PyGIT"
        p = self.path.strip('/')
        if self.isfile:
            assert p
            return p
        if self.isdir:
            return p and (p + '/')

        raise TracError("internal error")

    def get_content(self):
        if not self.isfile:
            return None

        return self.repos.git.get_file(self.fs_sha)

    def get_properties(self):
        return self.fs_perm and {'mode': self.fs_perm } or {}

    def get_annotations(self):
        if not self.isfile:
            return

        return [ rev for rev, lineno in self.repos.git.blame(self.rev, self.__git_path()) ]

    def get_entries(self):
        if not self.isdir:
            return

        with self.repos.git.get_historian(self.rev, self.path.strip('/')) as historian:
            for ent in self.repos.git.ls_tree(self.rev, self.__git_path()):
                yield GitNode(self.repos, ent[-1], self.rev, self.log, ent, historian)

    def get_content_type(self):
        if self.isdir:
            return None

        return ''

    def get_content_length(self):
        if not self.isfile:
            return None

        if self.fs_size is None:
            self.fs_size = self.repos.git.get_obj_size(self.fs_sha)

        return self.fs_size

    def get_history(self, limit=None):
        # TODO: find a way to follow renames/copies
        for is_last, rev in _last_iterable(self.repos.git.history(self.rev, self.__git_path(), limit)):
            yield (self.path, rev, Changeset.EDIT if not is_last else Changeset.ADD)

    def get_last_modified(self):
        if not self.isfile:
            return None

        try:
            msg, props = self.repos.git.read_commit(self.rev)
            user, ts = _parse_user_time(props['committer'][0])
        except:
            self.log.error("internal error (could not get timestamp from commit '%s')" % self.rev)
            return None

        return ts


class GitChangeset(Changeset):
    """
    A Git changeset in the Git repository.

    Corresponds to a Git commit blob.
    """

    action_map = { # see also git-diff-tree(1) --diff-filter
        'A': Changeset.ADD,
        'M': Changeset.EDIT, # modified
        'T': Changeset.EDIT, # file type (mode) change
        'D': Changeset.DELETE,
        'R': Changeset.MOVE, # renamed
        'C': Changeset.COPY
        } # TODO: U, X, B

    def __init__(self, repos, sha):
        if sha is None:
            raise NoSuchChangeset(sha)
        
        try:
            msg, props = repos.git.read_commit(sha)
        except PyGIT.GitErrorSha:
            raise NoSuchChangeset(sha)

        self.props = props

        assert 'children' not in props
        _children = list(repos.git.children(sha))
        if _children:
            props['children'] = _children

        # use 1st author/committer as changeset owner/timestamp
        if repos._use_committer_time:
            _, time_ = _parse_user_time(props['committer'][0])
        else:
            _, time_ = _parse_user_time(props['author'][0])

        if repos._use_committer_id:
            user_, _ = _parse_user_time(props['committer'][0])
        else:
            user_, _ = _parse_user_time(props['author'][0])

        # try to resolve email address to trac uid
        user_ = repos.rlookup_uid(user_) or user_

        Changeset.__init__(self, repos, rev=sha, message=msg, author=user_, date=time_)

    def get_properties(self):
        properties = {}

        if 'parent' in self.props:
            properties['Parents'] = self.props['parent']

        if 'children' in self.props:
            properties['Children'] = self.props['children']

        if 'committer' in self.props:
            properties['git-committer'] = \
                    _parse_user_time(self.props['committer'][0])

        if 'author' in self.props:
            properties['git-author'] = \
                    _parse_user_time(self.props['author'][0])

        branches = list(self.repos.git.get_branch_contains(self.rev, resolve=True))
        if branches:
            properties['Branches'] = branches

        return properties

    def get_changes(self):
        paths_seen = set()
        for parent in self.props.get('parent', [None]):
            for mode1, mode2, obj1, obj2, action, path1, path2 in \
                    self.repos.git.diff_tree(parent, self.rev, find_renames=True):
                path = path2 or path1
                p_path, p_rev = path1, parent

                kind = Node.FILE
                if mode2.startswith('04') or mode1.startswith('04'):
                    kind = Node.DIRECTORY

                action = GitChangeset.action_map[action[0]]

                if action == Changeset.ADD:
                    p_path = ''
                    p_rev = None

                # CachedRepository expects unique (rev, path, change_type) key
                # this is only an issue in case of merges where files required editing
                if path in paths_seen:
                    continue

                paths_seen.add(path)

                yield path, kind, action, p_path, p_rev


    def get_branches(self):
        _rev = self.rev

        return [ (k, v == _rev)
                 for k, v in self.repos.git.get_branch_contains(_rev, resolve=True) ]

class GitwebProjectsRepositoryProvider(Component):
    implements(IRepositoryProvider)

    projects_list = PathOption('git', 'projects_list', doc='Path to a gitweb-formatted projects.list')
    projects_base = PathOption('git', 'projects_base', doc='Path to the base of your git projects')
    projects_url = Option('git', 'projects_url', doc='Template for project URLs. %s will be replaced with the repo name')

    def get_repositories(self):
        if not self.projects_list:
            return

        for line in open(self.projects_list):
            line = line.strip()
            name = line
            if name.endswith('.git'):
                name = name[:-4]
            repo = {
                'dir': os.path.join(self.projects_base, line),
                'type': 'git',
            }
            description_path = os.path.join(repo['dir'], 'description')
            if os.path.exists(description_path):
                repo['description'] = open(description_path).read().strip()
            if self.projects_url:
                repo['url'] = self.projects_url % name
            yield name, repo

########NEW FILE########
__FILENAME__ = PyGIT
# -*- coding: iso-8859-1 -*-
#
# Copyright (C) 2006-2011, Herbert Valerio Riedel <hvr@gnu.org>
#
# See COPYING for distribution information

from __future__ import with_statement

from future27 import namedtuple

import os, re, sys, time, weakref
from collections import deque
from functools import partial
from threading import Lock
from subprocess import Popen, PIPE
from operator import itemgetter
from contextlib import contextmanager
import cStringIO
import codecs

__all__ = ["git_version", "GitError", "GitErrorSha", "Storage", "StorageFactory"]

class GitError(Exception):
    pass

class GitErrorSha(GitError):
    pass

class GitCore(object):
    """
    Low-level wrapper around git executable
    """

    def __init__(self, git_dir=None, git_bin="git"):
        self.__git_bin = git_bin
        self.__git_dir = git_dir

    def __repr__(self):
        return '<GitCore bin="%s" dir="%s">' % (self.__git_bin, self.__git_dir)

    def __build_git_cmd(self, gitcmd, *args):
        "construct command tuple for git call suitable for Popen()"

        cmd = [self.__git_bin]
        if self.__git_dir:
            cmd.append('--git-dir=%s' % self.__git_dir)
        cmd.append(gitcmd)
        cmd.extend(args)

        return cmd

    def __pipe(self, git_cmd, *cmd_args, **kw):
        if sys.platform == "win32":
            return Popen(self.__build_git_cmd(git_cmd, *cmd_args), **kw)
        else:
            return Popen(self.__build_git_cmd(git_cmd, *cmd_args),
                         close_fds=True, **kw)

    def __execute(self, git_cmd, *cmd_args):
        "execute git command and return file-like object of stdout"

        #print >>sys.stderr, "DEBUG:", git_cmd, cmd_args

        p = self.__pipe(git_cmd, *cmd_args, stdout=PIPE, stderr=PIPE)

        stdout_data, stderr_data = p.communicate()
        #TODO, do something with p.returncode, e.g. raise exception

        return stdout_data

    def cat_file_batch(self):
        return self.__pipe('cat-file', '--batch', stdin=PIPE, stdout=PIPE)

    def log_pipe(self, *cmd_args):
        return self.__pipe('log', *cmd_args, stdout=PIPE)

    def __getattr__(self, name):
        if name[0] == '_' or name in ['cat_file_batch', 'log_pipe']:
            raise AttributeError, name
        return partial(self.__execute, name.replace('_','-'))

    __is_sha_pat = re.compile(r'[0-9A-Fa-f]*$')

    @classmethod
    def is_sha(cls, sha):
        """
        returns whether sha is a potential sha id
        (i.e. proper hexstring between 4 and 40 characters)
        """

        # quick test before starting up regexp matcher
        if not (4 <= len(sha) <= 40):
            return False

        return bool(cls.__is_sha_pat.match(sha))

class SizedDict(dict):
    """
    Size-bounded dictionary with FIFO replacement strategy
    """

    def __init__(self, max_size=0):
        dict.__init__(self)
        self.__max_size = max_size
        self.__key_fifo = deque()
        self.__lock = Lock()

    def __setitem__(self, name, value):
        with self.__lock:
            assert len(self) == len(self.__key_fifo) # invariant

            if not self.__contains__(name):
                self.__key_fifo.append(name)

            rc = dict.__setitem__(self, name, value)

            while len(self.__key_fifo) > self.__max_size:
                self.__delitem__(self.__key_fifo.popleft())

            assert len(self) == len(self.__key_fifo) # invariant

            return rc

    def setdefault(self, *_):
        raise NotImplemented("SizedDict has no setdefault() method")

class StorageFactory(object):
    __dict = weakref.WeakValueDictionary()
    __dict_nonweak = dict()
    __dict_lock = Lock()

    def __init__(self, repo, log, weak=True, git_bin='git', git_fs_encoding=None):
        self.logger = log

        with StorageFactory.__dict_lock:
            try:
                i = StorageFactory.__dict[repo]
            except KeyError:
                i = Storage(repo, log, git_bin, git_fs_encoding)
                StorageFactory.__dict[repo] = i

                # create or remove additional reference depending on 'weak' argument
                if weak:
                    try:
                        del StorageFactory.__dict_nonweak[repo]
                    except KeyError:
                        pass
                else:
                    StorageFactory.__dict_nonweak[repo] = i

        self.__inst = i
        self.__repo = repo

    def getInstance(self):
        is_weak = self.__repo not in StorageFactory.__dict_nonweak
        self.logger.debug("requested %sPyGIT.Storage instance %d for '%s'"
                          % (("","weak ")[is_weak], id(self.__inst), self.__repo))
        return self.__inst


class Storage(object):
    """
    High-level wrapper around GitCore with in-memory caching
    """

    __SREV_MIN = 4 # minimum short-rev length

    RevCache = namedtuple('RevCache', 'youngest_rev oldest_rev rev_dict tag_set srev_dict branch_dict')

    @staticmethod
    def __rev_key(rev):
        assert len(rev) >= 4
        #assert GitCore.is_sha(rev)
        srev_key = int(rev[:4], 16)
        assert srev_key >= 0 and srev_key <= 0xffff
        return srev_key

    @staticmethod
    def git_version(git_bin="git"):
        GIT_VERSION_MIN_REQUIRED = (1, 5, 6)
        try:
            g = GitCore(git_bin=git_bin)
            [v] = g.version().splitlines()
            _, _, version = v.strip().split()
            # 'version' has usually at least 3 numeric version components, e.g.::
            #  1.5.4.2
            #  1.5.4.3.230.g2db511
            #  1.5.4.GIT

            def try_int(s):
                try:
                    return int(s)
                except ValueError:
                    return s

            split_version = tuple(map(try_int, version.split('.')))

            result = {}
            result['v_str'] = version
            result['v_tuple'] = split_version
            result['v_min_tuple'] = GIT_VERSION_MIN_REQUIRED
            result['v_min_str'] = ".".join(map(str, GIT_VERSION_MIN_REQUIRED))
            result['v_compatible'] = split_version >= GIT_VERSION_MIN_REQUIRED
            return result

        except Exception, e:
            raise GitError("Could not retrieve GIT version"
                           " (tried to execute/parse '%s --version' but got %s)"
                           % (git_bin, repr(e)))

    def __init__(self, git_dir, log, git_bin='git', git_fs_encoding=None):
        """
        Initialize PyGit.Storage instance

        `git_dir`: path to .git folder;
                this setting is not affected by the `git_fs_encoding` setting

        `log`: logger instance

        `git_bin`: path to executable
                this setting is not affected by the `git_fs_encoding` setting

        `git_fs_encoding`: encoding used for paths stored in git repository;
                if `None`, no implicit decoding/encoding to/from
                unicode objects is performed, and bytestrings are
                returned instead

        """

        self.logger = log

        if git_fs_encoding is not None:
            # validate encoding name
            codecs.lookup(git_fs_encoding)

            # setup conversion functions
            self._fs_to_unicode = lambda s: s.decode(git_fs_encoding)
            self._fs_from_unicode = lambda s: s.encode(git_fs_encoding)
        else:
            # pass bytestrings as-is w/o any conversion
            self._fs_to_unicode = self._fs_from_unicode = lambda s: s

        # simple sanity checking
        __git_file_path = partial(os.path.join, git_dir)
        if not all(map(os.path.exists,
                       map(__git_file_path,
                           ['HEAD','objects','refs']))):
            self.logger.error("GIT control files missing in '%s'" % git_dir)
            if os.path.exists(__git_file_path('.git')):
                self.logger.error("entry '.git' found in '%s'"
                                  " -- maybe use that folder instead..." % git_dir)
            raise GitError("GIT control files not found, maybe wrong directory?")

        self.logger.debug("PyGIT.Storage instance %d constructed" % id(self))

        self.repo = GitCore(git_dir, git_bin=git_bin)

        self.commit_encoding = None

        # caches
        self.__rev_cache = None
        self.__rev_cache_lock = Lock()

        # cache the last 200 commit messages
        self.__commit_msg_cache = SizedDict(200)
        self.__commit_msg_lock = Lock()

        self.__cat_file_pipe = None

    def __del__(self):
        if self.__cat_file_pipe is not None:
            self.__cat_file_pipe.stdin.close()
            self.__cat_file_pipe.wait()

    #
    # cache handling
    #

    # called by Storage.sync()
    def __rev_cache_sync(self, youngest_rev=None):
        "invalidates revision db cache if necessary"

        with self.__rev_cache_lock:
            need_update = False
            if self.__rev_cache:
                last_youngest_rev = self.__rev_cache.youngest_rev
                if last_youngest_rev != youngest_rev:
                    self.logger.debug("invalidated caches (%s != %s)" % (last_youngest_rev, youngest_rev))
                    need_update = True
            else:
                need_update = True # almost NOOP

            if need_update:
                self.__rev_cache = None

            return need_update

    def get_rev_cache(self):
        """
        Retrieve revision cache

        may rebuild cache on the fly if required

        returns RevCache tuple
        """

        with self.__rev_cache_lock:
            if self.__rev_cache is None: # can be cleared by Storage.__rev_cache_sync()
                self.logger.debug("triggered rebuild of commit tree db for %d" % id(self))
                ts0 = time.time()

                youngest = None
                oldest = None
                new_db = {} # db
                new_sdb = {} # short_rev db

                # helper for reusing strings
                __rev_seen = {}
                def __rev_reuse(rev):
                    rev = str(rev)
                    return __rev_seen.setdefault(rev, rev)

                new_tags = set(__rev_reuse(rev.strip()) for rev in self.repo.rev_parse("--tags").splitlines())

                new_branches = [(k, __rev_reuse(v)) for k, v in self._get_branches()]
                head_revs = set(v for _, v in new_branches)

                rev = ord_rev = 0
                for ord_rev, revs in enumerate(self.repo.rev_list("--parents",
                                                                  "--topo-order",
                                                                  "--all").splitlines()):
                    revs = map(__rev_reuse, revs.strip().split())

                    rev = revs[0]

                    # first rev seen is assumed to be the youngest one
                    if not ord_rev:
                        youngest = rev

                    # shortrev "hash" map
                    srev_key = self.__rev_key(rev)
                    new_sdb.setdefault(srev_key, []).append(rev)

                    # parents
                    parents = tuple(revs[1:])

                    # new_db[rev] = (children(rev), parents(rev), ordinal_id(rev), rheads(rev))
                    if rev in new_db:
                        # (incomplete) entry was already created by children
                        _children, _parents, _ord_rev, _rheads = new_db[rev]
                        assert _children
                        assert not _parents
                        assert _ord_rev == 0

                        if rev in head_revs and rev not in _rheads:
                            _rheads.append(rev)

                    else: # new entry
                        _children = []
                        _rheads = [rev] if rev in head_revs else []

                    # create/update entry -- transform lists into tuples since entry will be final
                    new_db[rev] = tuple(_children), tuple(parents), ord_rev + 1, tuple(_rheads)

                    # update parents(rev)s
                    for parent in parents:
                        # by default, a dummy ordinal_id is used for the mean-time
                        _children, _parents, _ord_rev, _rheads2 = new_db.setdefault(parent, ([], [], 0, []))

                        # update parent(rev)'s children
                        if rev not in _children:
                            _children.append(rev)

                        # update parent(rev)'s rheads
                        for rev in _rheads:
                            if rev not in _rheads2:
                                _rheads2.append(rev)

                # last rev seen is assumed to be the oldest one (with highest ord_rev)
                oldest = rev

                __rev_seen = None

                # convert sdb either to dict or array depending on size
                tmp = [()]*(max(new_sdb.keys())+1) if len(new_sdb) > 5000 else {}

                try:
                    while True:
                        k, v = new_sdb.popitem()
                        tmp[k] = tuple(v)
                except KeyError:
                    pass

                assert len(new_sdb) == 0
                new_sdb = tmp

                # atomically update self.__rev_cache
                self.__rev_cache = Storage.RevCache(youngest, oldest, new_db, new_tags, new_sdb, new_branches)
                ts1 = time.time()
                self.logger.debug("rebuilt commit tree db for %d with %d entries (took %.1f ms)"
                                  % (id(self), len(new_db), 1000*(ts1-ts0)))

            assert all(e is not None for e in self.__rev_cache) or not any(self.__rev_cache)

            return self.__rev_cache
        # with self.__rev_cache_lock

    # see RevCache namedtuple
    rev_cache = property(get_rev_cache)

    def _get_branches(self):
        "returns list of (local) branches, with active (= HEAD) one being the first item"

        result = []
        for e in self.repo.branch("-v", "--no-abbrev").splitlines():
            bname, bsha = e[1:].strip().split()[:2]
            if e.startswith('*'):
                result.insert(0, (bname, bsha))
            else:
                result.append((bname, bsha))

        return result

    def get_branches(self):
        "returns list of (local) branches, with active (= HEAD) one being the first item"
        return self.rev_cache.branch_dict

    def get_commits(self):
        return self.rev_cache.rev_dict

    def oldest_rev(self):
        return self.rev_cache.oldest_rev

    def youngest_rev(self):
        return self.rev_cache.youngest_rev

    def get_branch_contains(self, sha, resolve=False):
        """
        return list of reachable head sha ids or (names, sha) pairs if resolve is true

        see also get_branches()
        """

        _rev_cache = self.rev_cache

        try:
            rheads = _rev_cache.rev_dict[sha][3]
        except KeyError:
            return []

        if resolve:
            return [ (k, v) for k, v in _rev_cache.branch_dict if v in rheads ]

        return rheads

    def history_relative_rev(self, sha, rel_pos):
        db = self.get_commits()

        if sha not in db:
            raise GitErrorSha()

        if rel_pos == 0:
            return sha

        lin_rev = db[sha][2] + rel_pos

        if lin_rev < 1 or lin_rev > len(db):
            return None

        for k, v in db.iteritems():
            if v[2] == lin_rev:
                return k

        # should never be reached if db is consistent
        raise GitError("internal inconsistency detected")

    def hist_next_revision(self, sha):
        return self.history_relative_rev(sha, -1)

    def hist_prev_revision(self, sha):
        return self.history_relative_rev(sha, +1)

    def get_commit_encoding(self):
        if self.commit_encoding is None:
            self.commit_encoding = \
                self.repo.repo_config("--get", "i18n.commitEncoding").strip() or 'utf-8'

        return self.commit_encoding

    def head(self):
        "get current HEAD commit id"
        return self.verifyrev("HEAD")

    def cat_file(self, kind, sha):
        if self.__cat_file_pipe is None:
            self.__cat_file_pipe = self.repo.cat_file_batch()

        self.__cat_file_pipe.stdin.write(sha + '\n')
        self.__cat_file_pipe.stdin.flush()
        _sha, _type, _size = self.__cat_file_pipe.stdout.readline().split()

        if _type != kind:
            raise TracError("internal error (got unexpected object kind '%s')" % k)

        size = int(_size)
        return self.__cat_file_pipe.stdout.read(size + 1)[:size]

    def verifyrev(self, rev):
        "verify/lookup given revision object and return a sha id or None if lookup failed"
        rev = str(rev)

        _rev_cache = self.rev_cache

        if GitCore.is_sha(rev):
            # maybe it's a short or full rev
            fullrev = self.fullrev(rev)
            if fullrev:
                return fullrev

        # fall back to external git calls
        rc = self.repo.rev_parse("--verify", rev).strip()
        if not rc:
            return None

        if rc in _rev_cache.rev_dict:
            return rc

        if rc in _rev_cache.tag_set:
            sha = self.cat_file("tag", rc).split(None, 2)[:2]
            if sha[0] != 'object':
                self.logger.debug("unexpected result from 'git-cat-file tag %s'" % rc)
                return None
            return sha[1]

        return None

    def shortrev(self, rev, min_len=7):
        "try to shorten sha id"
        #try to emulate the following:
        #return self.repo.rev_parse("--short", str(rev)).strip()
        rev = str(rev)

        if min_len < self.__SREV_MIN:
            min_len = self.__SREV_MIN

        _rev_cache = self.rev_cache

        if rev not in _rev_cache.rev_dict:
            return None

        srev = rev[:min_len]
        srevs = set(_rev_cache.srev_dict[self.__rev_key(rev)])

        if len(srevs) == 1:
            return srev # we already got a unique id

        # find a shortened id for which rev doesn't conflict with
        # the other ones from srevs
        crevs = srevs - set([rev])

        for l in range(min_len+1, 40):
            srev = rev[:l]
            if srev not in [ r[:l] for r in crevs ]:
                return srev

        return rev # worst-case, all except the last character match

    def fullrev(self, srev):
        "try to reverse shortrev()"
        srev = str(srev)

        _rev_cache = self.rev_cache

        # short-cut
        if len(srev) == 40 and srev in _rev_cache.rev_dict:
            return srev

        if not GitCore.is_sha(srev):
            return None

        try:
            srevs = _rev_cache.srev_dict[self.__rev_key(srev)]
        except KeyError:
            return None

        srevs = filter(lambda s: s.startswith(srev), srevs)
        if len(srevs) == 1:
            return srevs[0]

        return None

    def get_tags(self):
        return [ e.strip() for e in self.repo.tag("-l").splitlines() ]

    def ls_tree(self, rev, path=""):
        rev = rev and str(rev) or 'HEAD' # paranoia

        path = self._fs_from_unicode(path)

        if path.startswith('/'):
            path = path[1:]

        tree = self.repo.ls_tree("-z", "-l", rev, "--", path).split('\0')

        def split_ls_tree_line(l):
            "split according to '<mode> <type> <sha> <size>\t<fname>'"

            meta, fname = l.split('\t', 1)
            _mode, _type, _sha, _size = meta.split()

            if _size == '-':
                _size = None
            else:
                _size = int(_size)

            return _mode, _type, _sha, _size, self._fs_to_unicode(fname)

        return [ split_ls_tree_line(e) for e in tree if e ]

    def read_commit(self, commit_id):
        if not commit_id:
            raise GitError("read_commit called with empty commit_id")

        commit_id, commit_id_orig = self.fullrev(commit_id), commit_id

        db = self.get_commits()
        if commit_id not in db:
            self.logger.info("read_commit failed for '%s' ('%s')" %
                             (commit_id, commit_id_orig))
            raise GitErrorSha

        with self.__commit_msg_lock:
            if self.__commit_msg_cache.has_key(commit_id):
                # cache hit
                result = self.__commit_msg_cache[commit_id]
                return result[0], dict(result[1])

            # cache miss
            raw = self.cat_file("commit", commit_id)
            raw = unicode(raw, self.get_commit_encoding(), 'replace')
            lines = raw.splitlines()

            if not lines:
                raise GitErrorSha

            line = lines.pop(0)
            props = {}
            while line:
                key, value = line.split(None, 1)
                props.setdefault(key, []).append(value.strip())
                line = lines.pop(0)

            result = ("\n".join(lines), props)

            self.__commit_msg_cache[commit_id] = result

            return result[0], dict(result[1])

    def get_file(self, sha):
        return cStringIO.StringIO(self.cat_file("blob", str(sha)))

    def get_obj_size(self, sha):
        sha = str(sha)

        try:
            obj_size = int(self.repo.cat_file("-s", sha).strip())
        except ValueError:
            raise GitErrorSha("object '%s' not found" % sha)

        return obj_size

    def children(self, sha):
        db = self.get_commits()

        try:
            return list(db[sha][0])
        except KeyError:
            return []

    def children_recursive(self, sha, rev_dict=None):
        """
        Recursively traverse children in breadth-first order
        """

        if rev_dict is None:
            rev_dict = self.get_commits()

        work_list = deque()
        seen = set()

        seen.update(rev_dict[sha][0])
        work_list.extend(rev_dict[sha][0])

        while work_list:
            p = work_list.popleft()
            yield p

            _children = set(rev_dict[p][0]) - seen

            seen.update(_children)
            work_list.extend(_children)

        assert len(work_list) == 0

    def parents(self, sha):
        db = self.get_commits()

        try:
            return list(db[sha][1])
        except KeyError:
            return []

    def all_revs(self):
        return self.get_commits().iterkeys()

    def sync(self):
        rev = self.repo.rev_list("--max-count=1", "--topo-order", "--all").strip()
        return self.__rev_cache_sync(rev)

    @contextmanager
    def get_historian(self, sha, base_path):
        p = []
        change = {}
        next_path = []

        def name_status_gen():
            p[:] = [self.repo.log_pipe('--pretty=format:%n%H', '--name-status',
                                       sha, '--', base_path)]
            f = p[0].stdout
            for l in f:
                if l == '\n': continue
                old_sha = l.rstrip('\n')
                for l in f:
                    if l == '\n': break
                    _, path = l.rstrip('\n').split('\t', 1)
                    while path not in change:
                        change[path] = old_sha
                        if next_path == [path]: yield old_sha
                        try:
                            path, _ = path.rsplit('/', 1)
                        except ValueError:
                            break
            f.close()
            p[0].terminate()
            p[0].wait()
            p[:] = []
            while True: yield None
        gen = name_status_gen()

        def historian(path):
            try:
                return change[path]
            except KeyError:
                next_path[:] = [path]
                return gen.next()
        yield historian

        if p:
            p[0].stdout.close()
            p[0].terminate()
            p[0].wait()

    def last_change(self, sha, path, historian=None):
        if historian is not None:
            return historian(path)
        return self.repo.rev_list("--max-count=1",
                                  sha, "--",
                                  self._fs_from_unicode(path)).strip() or None

    def history(self, sha, path, limit=None):
        if limit is None:
            limit = -1

        tmp = self.repo.rev_list("--max-count=%d" % limit, str(sha), "--",
                                 self._fs_from_unicode(path))

        return [ rev.strip() for rev in tmp.splitlines() ]

    def history_timerange(self, start, stop):
        return [ rev.strip() for rev in \
                     self.repo.rev_list("--reverse",
                                        "--max-age=%d" % start,
                                        "--min-age=%d" % stop,
                                        "--all").splitlines() ]

    def rev_is_anchestor_of(self, rev1, rev2):
        """return True if rev2 is successor of rev1"""

        rev1 = rev1.strip()
        rev2 = rev2.strip()

        rev_dict = self.get_commits()

        return (rev2 in rev_dict and
                rev2 in self.children_recursive(rev1, rev_dict))

    def blame(self, commit_sha, path):
        in_metadata = False

        path = self._fs_from_unicode(path)

        for line in self.repo.blame("-p", "--", path, str(commit_sha)).splitlines():
            assert line
            if in_metadata:
                in_metadata = not line.startswith('\t')
            else:
                split_line = line.split()
                if len(split_line) == 4:
                    (sha, orig_lineno, lineno, group_size) = split_line
                else:
                    (sha, orig_lineno, lineno) = split_line

                assert len(sha) == 40
                yield (sha, lineno)
                in_metadata = True

        assert not in_metadata

    def diff_tree(self, tree1, tree2, path="", find_renames=False):
        """calls `git diff-tree` and returns tuples of the kind
        (mode1,mode2,obj1,obj2,action,path1,path2)"""

        # diff-tree returns records with the following structure:
        # :<old-mode> <new-mode> <old-sha> <new-sha> <change> NUL <old-path> NUL [ <new-path> NUL ]

        path = self._fs_from_unicode(path).strip("/")
        diff_tree_args = ["-z", "-r"]
        if find_renames:
            diff_tree_args.append("-M")
        diff_tree_args.extend([str(tree1) if tree1 else "--root",
                               str(tree2),
                               "--", path])

        lines = self.repo.diff_tree(*diff_tree_args).split('\0')

        assert lines[-1] == ""
        del lines[-1]

        if tree1 is None and lines:
            # if only one tree-sha is given on commandline,
            # the first line is just the redundant tree-sha itself...
            assert not lines[0].startswith(':')
            del lines[0]

        # FIXME: the following code is ugly, needs rewrite

        chg = None

        def __chg_tuple():
            if len(chg) == 6:
                chg.append(None)
            else:
                chg[6] = self._fs_to_unicode(chg[6])
            chg[5] = self._fs_to_unicode(chg[5])

            assert len(chg) == 7
            return tuple(chg)

        for line in lines:
            if line.startswith(':'):
                if chg:
                    yield __chg_tuple()

                chg = line[1:].split()
                assert len(chg) == 5
            else:
                chg.append(line)

        # handle left-over chg entry
        if chg:
            yield __chg_tuple()

############################################################################
############################################################################
############################################################################

def main():
    import logging, timeit

    assert not GitCore.is_sha("123")
    assert GitCore.is_sha("1a3f")
    assert GitCore.is_sha("f"*40)
    assert not GitCore.is_sha("x"+"f"*39)
    assert not GitCore.is_sha("f"*41)

    print "git version [%s]" % str(Storage.git_version())

    # custom linux hack reading `/proc/<PID>/statm`
    if sys.platform == "linux2":
        __pagesize = os.sysconf('SC_PAGESIZE')

        def proc_statm(pid = os.getpid()):
            __proc_statm = '/proc/%d/statm' % pid
            try:
                t = open(__proc_statm)
                result = t.read().split()
                t.close()
                assert len(result) == 7
                return tuple([ __pagesize*int(p) for p in result ])
            except:
                raise RuntimeError("failed to get memory stats")

    else: # not linux2
        print "WARNING - meminfo.proc_statm() not available"
        def proc_statm():
            return (0,)*7

    print "statm =", proc_statm()
    __data_size = proc_statm()[5]
    __data_size_last = [__data_size]

    def print_data_usage():
        __tmp = proc_statm()[5]
        print "DATA: %6d %+6d" % (__tmp - __data_size, __tmp - __data_size_last[0])
        __data_size_last[0] = __tmp

    print_data_usage()

    g = Storage(sys.argv[1], logging)

    print_data_usage()

    print "[%s]" % g.head()
    print g.ls_tree(g.head())
    print "--------------"
    print_data_usage()
    print g.read_commit(g.head())
    print "--------------"
    print_data_usage()
    p = g.parents(g.head())
    print list(p)
    print "--------------"
    print list(g.children(list(p)[0]))
    print list(g.children(list(p)[0]))
    print "--------------"
    print g.get_commit_encoding()
    print "--------------"
    print g.get_branches()
    print "--------------"
    print g.hist_prev_revision(g.oldest_rev()), g.oldest_rev(), g.hist_next_revision(g.oldest_rev())
    print_data_usage()
    print "--------------"
    p = g.youngest_rev()
    print g.hist_prev_revision(p), p, g.hist_next_revision(p)
    print "--------------"

    p = g.head()
    for i in range(-5, 5):
        print i, g.history_relative_rev(p, i)

    # check for loops
    def check4loops(head):
        print "check4loops", head
        seen = set([head])
        for _sha in g.children_recursive(head):
            if _sha in seen:
                print "dupe detected :-/", _sha, len(seen)
            seen.add(_sha)
        return seen

    print len(check4loops(g.parents(g.head())[0]))

    #p = g.head()
    #revs = [ g.history_relative_rev(p, i) for i in range(0,10) ]
    print_data_usage()
    revs = g.get_commits().keys()
    print_data_usage()

    def shortrev_test():
        for i in revs:
            i = str(i)
            s = g.shortrev(i, min_len=4)
            assert i.startswith(s)
            assert g.fullrev(s) == i

    # iters = 1
    # print "timing %d*shortrev_test()..." % len(revs)
    # t = timeit.Timer("shortrev_test()", "from __main__ import shortrev_test")
    # print "%.2f usec/rev" % (1000000 * t.timeit(number=iters)/len(revs))

    #print len(check4loops(g.oldest_rev()))
    #print len(list(g.children_recursive(g.oldest_rev())))

    print_data_usage()

    # perform typical trac operations:

    if 1:
        print "--------------"
        rev = g.head()
        for mode, _type, sha, _size, name in g.ls_tree(rev):
            [last_rev] = g.history(rev, name, limit=1)
            s = g.get_obj_size(sha) if _type == "blob" else 0
            msg = g.read_commit(last_rev)

            print "%s %s %10d [%s]" % (_type, last_rev, s, name)

    print "allocating 2nd instance"
    print_data_usage()
    g2 = Storage(sys.argv[1], logging)
    g2.head()
    print_data_usage()

    print "allocating 3rd instance"
    g3 = Storage(sys.argv[1], logging)
    g3.head()
    print_data_usage()

if __name__ == '__main__':
    main()

########NEW FILE########
