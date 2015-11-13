__FILENAME__ = bzr
from datetime import datetime, timedelta
import os
import StringIO
from time import mktime

from bzrlib import branch, diff, errors

from pyvcs.commit import Commit
from pyvcs.exceptions import CommitDoesNotExist, FileDoesNotExist, FolderDoesNotExist
from pyvcs.repository import BaseRepository

class Repository(BaseRepository):
    def __init__(self, *args, **kwargs):
        super(Repository, self).__init__(*args, **kwargs)

        # API-wise, pyvcs's notion of a "repository" probably maps more closely
        # to bzr's notion of a branch than of a bzr repository so, self._branch
        # is the bzrlib Branch structure mapping to the path in question.
        self._branch = branch.Branch.open(self.path.rstrip(os.path.sep))

    # for purposes of naming, "commit ID" is used as pyvcs uses it: to describe
    # the user-facing name for a revision ("revision number" or "revno" in bzr
    # terms); "revision_id" or "rev_id" is used here to describe bzrlib's
    # internal string names for revisions. Finally, "rev" refers to an actual
    # bzrlib revision structure.
    def _rev_to_commit(self, rev):
        # TODO: this doesn't yet handle the case of multiple parent revisions
        current = self._branch.repository.revision_tree(rev.revision_id)
        if len(rev.parent_ids):
            prev = self._branch.repository.revision_tree(rev.parent_ids[0])
        else:
            prev = self._branch.repository.revision_tree('null:')

        delta = current.changes_from(prev)
        files = [f[0] for f in delta.added + delta.removed + delta.renamed + delta.kind_changed + delta.modified]

        diff_file = StringIO.StringIO()

        diff_tree = diff.DiffTree(prev, current, diff_file)

        self._branch.lock_read()
        diff_tree.show_diff('')
        self._branch.unlock()

        diff_out = diff_file.getvalue()
        diff_file.close()

        return Commit(self._get_commit_id(rev.revision_id), rev.committer,
            datetime.fromtimestamp(rev.timestamp), rev.message, files, diff_out)

    def _get_rev_id(self, commit_id):
        return self._branch.get_rev_id(int(commit_id))

    def _get_commit_id(self, rev_id):
        return self._branch.revision_id_to_revno(rev_id)

    def _get_commit_by_rev_id(self, rev_id):
        rev = self._branch.repository.get_revision(rev_id)
        return self._rev_to_commit(rev)

    def get_commit_by_id(self, commit_id):
        rev_id = self._get_rev_id(commit_id)
        return self._get_commit_by_rev_id(rev_id)

    def _get_tree(self, revision=None):
        if revision:
            return self._branch.repository.revision_tree(self._get_rev_id(revision))
        else:
            return self._branch.repository.revision_tree(self._branch.last_revision())

    def get_recent_commits(self, since=None):
        hist = self._branch.revision_history()
        hist.reverse()
        head = hist[0]

        if since is None:
            since = datetime.fromtimestamp(head.timestamp) - timedelta(days=5)

        since_ts = mktime(since.timetuple())

        commits = []
        for rev_id in hist:
            rev = self._branch.repository.get_revision(rev_id)
            if rev.timestamp < since_ts:
                break
            commits.append(self._rev_to_commit(rev))

        return commits

    def list_directory(self, path, revision=None):
        path = path.rstrip(os.path.sep)
        tree = self._get_tree(revision)
        dir_iter = tree.walkdirs(path)
        try:
            entries = dir_iter.next()
        except StopIteration:
            raise FolderDoesNotExist

        plen = len(path)
        if plen != 0:
            plen += 1
        files, folders = [], []
        for item in entries[1]:
            if item[2] == 'file':
                files.append(item[0][plen:])
            elif item[2] == 'directory':
                folders.append(item[0][plen:])

        return files, folders

    def file_contents(self, path, revision=None):
        tree = self._get_tree(revision)

        try:
            self._branch.lock_read()
            file_id = tree.path2id(path)
            if tree.kind(file_id) != 'file':
                # Django VCS expects file_contents to raise an exception on
                # directories, while bzrlib returns an empty string so check
                # explicitly, and raise an exception
                raise FileDoesNotExist
            out = tree.get_file(file_id).read()
            self._branch.unlock()
        except:
            raise FileDoesNotExist

        return out

########NEW FILE########
__FILENAME__ = git
from datetime import datetime, timedelta
from operator import itemgetter, attrgetter
import os

from dulwich.repo import Repo
from dulwich import objects
from dulwich.errors import NotCommitError

from pyvcs.commit import Commit
from pyvcs.exceptions import CommitDoesNotExist, FileDoesNotExist, FolderDoesNotExist
from pyvcs.repository import BaseRepository
from pyvcs.utils import generate_unified_diff


def traverse_tree(repo, tree):
    for mode, name, sha in tree.entries():
        if isinstance(repo.get_object(sha), objects.Tree):
            for item in traverse_tree(repo, repo.get_object(sha)):
                yield os.path.join(name, item)
        else:
            yield name

def get_differing_files(repo, past, current):
    past_files = {}
    current_files = {}
    if past is not None:
        past_files = dict([(name, sha) for mode, name, sha in past.entries()])
    if current is not None:
        current_files = dict([(name, sha) for mode, name, sha in current.entries()])

    added = set(current_files) - set(past_files)
    removed = set(past_files) - set(current_files)
    changed = [o for o in past_files if o in current_files and past_files[o] != current_files[o]]

    for name in added:
        sha = current_files[name]
        yield name
        if isinstance(repo.get_object(sha), objects.Tree):
            for item in get_differing_files(repo, None, repo.get_object(sha)):
                yield os.path.join(name, item)

    for name in removed:
        sha = past_files[name]
        yield name
        if isinstance(repo.get_object(sha), objects.Tree):
            for item in get_differing_files(repo, repo.get_object(sha), None):
                yield os.path.join(name, item)

    for name in changed:
        past_sha = past_files[name]
        current_sha = current_files[name]
        if isinstance(repo.get_object(past_sha), objects.Tree):
            for item in get_differing_files(repo, repo.get_object(past_sha), repo.get_object(current_sha)):
                yield os.path.join(name, item)
        else:
            yield name


class Repository(BaseRepository):
    def __init__(self, *args, **kwargs):
        super(Repository, self).__init__(*args, **kwargs)

        self._repo = Repo(self.path)

    def _get_commit(self, commit_id):
        try:
            return self._repo[commit_id]
        except Exception, e:
            raise CommitDoesNotExist("%s is not a commit" % commit_id)

    def _get_obj(self, sha):
        return self._repo.get_object(sha)

    def _diff_files(self, commit_id1, commit_id2):
        if commit_id1 == 'NULL':
            commit_id1 = None
        if commit_id2 == 'NULL':
            commit_id2 = None
        tree1 = self._get_obj(self._get_obj(commit_id1).tree) if commit_id1 else None
        tree2 = self._get_obj(self._get_obj(commit_id2).tree) if commit_id2 else None
        return sorted(get_differing_files(
            self._repo,
            tree1,
            tree2,
        ))

    def get_commit_by_id(self, commit_id):
        commit = self._get_commit(commit_id)
        parent = commit.parents[0] if len(commit.parents) else 'NULL'
        files = self._diff_files(commit.id, parent)
        return Commit(commit.id, commit.committer,
            datetime.fromtimestamp(commit.commit_time), commit.message, files,
            lambda: generate_unified_diff(self, files, parent, commit.id))

    def get_recent_commits(self, since=None):
        if since is None:
            #since = datetime.fromtimestamp(self._repo.commit(self._repo.head()).commit_time) - timedelta(days=5)
            since = datetime.fromtimestamp(self._repo[self._repo.head()].commit_time) - timedelta(days=5)
        pending_commits = self._repo.get_refs().values()#[self._repo.head()]
        history = {}
        while pending_commits:
            head = pending_commits.pop(0)
            try:
                commit = self._repo[head]
            except KeyError:
                raise CommitDoesNotExist
            if not isinstance(commit, objects.Commit) or commit.id in history or\
               datetime.fromtimestamp(commit.commit_time) <= since:
                continue
            history[commit.id] = commit
            pending_commits.extend(commit.parents)
        commits = filter(lambda o: datetime.fromtimestamp(o.commit_time) >= since, history.values())
        commits = map(lambda o: self.get_commit_by_id(o.id), commits)
        return sorted(commits, key=attrgetter('time'), reverse=True)

    def list_directory(self, path, revision=None):
        if revision is None:
            commit = self._get_commit(self._repo.head())
        elif revision is 'NULL':
            return ([],[])
        else:
            commit = self._get_commit(revision)
        tree = self._repo[commit.tree]
        path = filter(bool, path.split(os.path.sep))
        while path:
            part = path.pop(0)
            found = False
            for mode, name, hexsha in self._repo[tree.id].entries():
                if part == name:
                    found = True
                    tree = self._repo[hexsha]
                    break
            if not found:
                raise FolderDoesNotExist
        files, folders = [], []
        for mode, name, hexsha in tree.entries():
            if isinstance(self._repo.get_object(hexsha), objects.Tree):
                folders.append(name)
            elif isinstance(self._repo.get_object(hexsha), objects.Blob):
                files.append(name)
        return files, folders

    def file_contents(self, path, revision=None):
        if revision is None:
            commit = self._get_commit(self._repo.head())
        elif revision is 'NULL':
            return ''
        else:
            commit = self._get_commit(revision)
        tree = self._repo[commit.tree]
        path = path.split(os.path.sep)
        path, filename = path[:-1], path[-1]
        while path:
            part = path.pop(0)
            for mode, name, hexsha in self._repo[tree.id].entries():
                if part == name:
                    tree = self._repo[hexsha]
                    break
        for mode, name, hexsha in tree.entries():
            if name == filename:
                return self._repo[hexsha].as_pretty_string()
        raise FileDoesNotExist

########NEW FILE########
__FILENAME__ = hg
from datetime import datetime, timedelta
from difflib import unified_diff
import os

from mercurial import ui
from mercurial.localrepo import localrepository as hg_repo
from mercurial.util import matchdate, Abort

from pyvcs.commit import Commit
from pyvcs.exceptions import CommitDoesNotExist, FileDoesNotExist, FolderDoesNotExist
from pyvcs.repository import BaseRepository
from pyvcs.utils import generate_unified_diff

class Repository(BaseRepository):
    def __init__(self, path, **kwargs):
        """
        path is the filesystem path where the repo exists, **kwargs are
        anything extra fnor accessing the repo
        """
        self.repo = hg_repo(ui.ui(), path=path)
        self.path = path
        self.extra = kwargs

    def _ctx_to_commit(self, ctx):
        diff = generate_unified_diff(self, ctx.files(), ctx.parents()[0].rev(), ctx.rev())

        return Commit(ctx.rev(),
                      ctx.user(),
                      datetime.fromtimestamp(ctx.date()[0]),
                      ctx.description(),
                      ctx.files(),
                      diff)

    def _latest_from_parents(self, parent_list):
        pass

    def get_commit_by_id(self, commit_id):
        """
        Returns a commit by it's id (nature of the ID is VCS dependent).
        """
        changeset = self.repo.changectx(commit_id)
        return self._ctx_to_commit(changeset)

    def get_recent_commits(self, since=None):
        """
        Returns all commits since since.  If since is None returns all commits
        from the last 5 days of commits.
        """
        cur_ctx = self.repo.changectx(self.repo.changelog.rev(self.repo.changelog.tip()))

        if since is None:
            since = datetime.fromtimestamp(cur_ctx.date()[0]) - timedelta(5)

        changesets = []
        to_look_at = [cur_ctx]

        while to_look_at:
            head = to_look_at.pop(0)
            to_look_at.extend(head.parents())
            if datetime.fromtimestamp(head.date()[0]) >= since:
                changesets.append(head)
            else:
                break

        return [self._ctx_to_commit(ctx) for ctx in changesets]

    def list_directory(self, path, revision=None):
        """
        Returns a list of files in a directory (list of strings) at a given
        revision, or HEAD if revision is None.
        """
        if revision is None:
            chgctx = self.repo.changectx('tip')
        else:
            chgctx = self.repo.changectx(revision)
        file_list = []
        folder_list = set()
        found_path = False
        for file, node in chgctx.manifest().items():
            if not file.startswith(path):
                continue
            found_path = True
            file = file[len(path):]
            if file.count(os.path.sep) >= 1:
                folder_list.add(file[:file.find(os.path.sep)])
            else:
                file_list.append(file)
        if not found_path:
            # If we never found the path within the manifest, it does not exist.
            raise FolderDoesNotExist
        return file_list, sorted(list(folder_list))

    def file_contents(self, path, revision=None):
        """
        Returns the contents of a file as a string at a given revision, or
        HEAD if revision is None.
        """
        if revision is None:
            chgctx = self.repo.changectx('tip')
        else:
            chgctx = self.repo.changectx(revision)
        try:
            return chgctx.filectx(path).data()
        except KeyError:
            raise FileDoesNotExist

########NEW FILE########
__FILENAME__ = subversion
from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile
from time import mktime
import os

import pysvn

from pyvcs.commit import Commit
from pyvcs.exceptions import CommitDoesNotExist, FileDoesNotExist, FolderDoesNotExist
from pyvcs.repository import BaseRepository
from pyvcs.utils import generate_unified_diff

class Repository(BaseRepository):
    def __init__(self, *args, **kwargs):
        super(Repository, self).__init__(*args, **kwargs)

        self._repo = pysvn.Client(self.path.rstrip(os.path.sep))

    def _log_to_commit(self, log):
        info = self._repo.info(self.path)
        base, url = info['repos'], info['url']
        at = url[len(base):]
        commit_files = [cp_dict['path'][len(at)+1:] for cp_dict in log['changed_paths']]

        def get_diff():
            # Here we go back through history, 5 commits at a time, searching
            # for the first point at which there is a change along our path.
            oldrev_log = None
            i = 1
            # the start of our search is always at the previous commit
            while oldrev_log is None:
                i += 5
                diff_rev_start = pysvn.Revision(pysvn.opt_revision_kind.number,
                    log['revision'].number - (i - 5))
                diff_rev_end = pysvn.Revision(pysvn.opt_revision_kind.number,
                    log['revision'].number - i)
                log_list = self._repo.log(self.path,
                    revision_start=diff_rev_start, revision_end=diff_rev_end,
                    discover_changed_paths=True)
                try:
                    oldrev_log = log_list.pop(0)
                except IndexError:
                    # If we've gone back through the entirety of history and
                    # still not found anything, bail out, this commit doesn't
                    # exist along our path (or perhaps at all)
                    if i >= log['revision'].number:
                        raise CommitDoesNotExist

            diff = self._repo.diff(NamedTemporaryFile().name,
                url_or_path=self.path, revision1=oldrev_log['revision'],
                revision2=log['revision'],
            )
            return diff

        return Commit(log['revision'].number, log['author'],
            datetime.fromtimestamp(log['date']), log['message'],
            commit_files, get_diff)

    def get_commit_by_id(self, commit_id):
        rev = pysvn.Revision(pysvn.opt_revision_kind.number, commit_id)

        try:
            log_list = self._repo.log(self.path, revision_start=rev,
                revision_end=rev, discover_changed_paths=True)
        except pysvn.ClientError:
            raise CommitDoesNotExist

        # If log list is empty most probably the commit does not exists for a
        # given path or branch.
        try:
            log = log_list.pop(0)
        except IndexError:
            raise CommitDoesNotExist

        return self._log_to_commit(log)


    def get_recent_commits(self, since=None):
        revhead = pysvn.Revision(pysvn.opt_revision_kind.head)
        log = self._repo.log(self.path, revision_start=revhead, revision_end=revhead)

        if since is None:
            since = datetime.fromtimestamp(log['date']) - timedelta(days=5)

        # Convert from datetime to float (seconds since unix epoch)
        utime = mktime(since.timetuple())

        rev = pysvn.Revision(pysvn.opt_revision_kind.date, utime)

        log_list = self._repo.log(self.path, revision_start=revhead,
            revision_end=rev, discover_changed_paths=True)

        commits = [self._log_to_commit(log) for log in log_list]
        return commits

    def list_directory(self, path, revision=None):
        if revision:
            rev = pysvn.Revision(pysvn.opt_revision_kind.number, revision)
        else:
            rev = pysvn.Revision(pysvn.opt_revision_kind.head)

        dir_path = os.path.join(self.path, path)

        try:
            entries = self._repo.list(dir_path, revision=rev, recurse=False)
        except pysvn.ClientError:
            raise FolderDoesNotExist

        files, folders = [], []
        for file_info, file_pops in entries:
            if file_info['kind'] == pysvn.node_kind.dir:
                # TODO: Path is not always present, only repos_path
                # is guaranteed, in case of looking at a remote
                # repository (with no local working copy) we should
                # check against repos_path.
                if not dir_path.startswith(file_info['path']):
                    folders.append(os.path.basename(file_info['repos_path']))
            else:
                files.append(os.path.basename(file_info['repos_path']))

        return files, folders

    def file_contents(self, path, revision=None):
        if revision:
            rev = pysvn.Revision(pysvn.opt_revision_kind.number, revision)
        else:
            rev = pysvn.Revision(pysvn.opt_revision_kind.head)

        file_path = os.path.join(self.path, path)

        try:
            return self._repo.cat(file_path, rev)
        except pysvn.ClientError:
            raise FileDoesNotExist

########NEW FILE########
__FILENAME__ = commit
class Commit(object):
    def __init__(self, commit_id, author, time, message, files, diff):
        """
        commit_id should be a string, author a string, time a datetime object,
        message a string, files a list of filenames (strings), and diff a
        string
        """
        self.commit_id = commit_id
        self.author = author
        self.time = time
        self.message = message
        self.files = files
        self.diff = diff

    def _get_diff(self):
        if callable(self._diff):
            self._diff = self._diff()
        return self._diff

    def _set_diff(self, diff):
        self._diff = diff

    diff = property(_get_diff, _set_diff)

    def __str__(self):
        return "<Commit %s by %s on %s>" % (self.commit_id, self.author, self.time)

    __repr__ = __str__

########NEW FILE########
__FILENAME__ = exceptions
class CommitDoesNotExist(Exception):
    pass

class FileDoesNotExist(Exception):
    pass

class FolderDoesNotExist(Exception):
    pass

########NEW FILE########
__FILENAME__ = repository
class BaseRepository(object):
    def __init__(self, path, **kwargs):
        """
        path is the filesystem path where the repo exists, **kwargs are
        anything extra for accessing the repo
        """
        self.path = path
        self.extra = kwargs

    def get_commit_by_id(self, commit_id):
        """
        Returns a commit by its id (nature of the ID is VCS dependent).
        """
        raise NotImplementedError

    def get_recent_commits(self, since=None):
        """
        Returns all commits since since.  If since is None returns all commits
        from the last 5 days.
        """
        raise NotImplementedError

    def list_directory(self, path, revision=None):
        """
        Returns a tuple of lists of files and folders in a given directory at a
        given revision, or HEAD if revision is None.
        """
        raise NotImplementedError

    def file_contents(self, path, revision=None):
        """
        Returns the contents of a file as a string at a given revision, or
        HEAD if revision is None.
        """
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = utils
from difflib import unified_diff

from pyvcs.exceptions import FileDoesNotExist

def generate_unified_diff(repository, changed_files, commit1, commit2):
    diffs = []
    for file_name in changed_files:
        try:
            file1 = repository.file_contents(file_name, commit1)
        except FileDoesNotExist:
            file1 = ''
        try:
            file2 = repository.file_contents(file_name, commit2)
        except FileDoesNotExist:
            file2 = ''
        diffs.append(unified_diff(
            file1.splitlines(), file2.splitlines(), fromfile=file_name,
            tofile=file_name, fromfiledate=commit1, tofiledate=commit2
        ))
    return '\n'.join('\n'.join(map(lambda s: s.rstrip('\n'), diff)) for diff in diffs)

########NEW FILE########
__FILENAME__ = alex_tests
#!/usr/bin/env python
from datetime import datetime
import unittest

from pyvcs.backends import get_backend
from pyvcs.exceptions import FileDoesNotExist, FolderDoesNotExist

class GitTest(unittest.TestCase):
    def setUp(self):
        git = get_backend('git')
        self.repo = git.Repository('/home/alex/django_src/')

    def test_commits(self):
        commit = self.repo.get_commit_by_id('c3699190186561d5c216b2a77ecbfc487d42a734')
        self.assert_(commit.author.startswith('ubernostrum'))
        self.assertEqual(commit.time, datetime(2009, 6, 30, 13, 40, 29))
        self.assert_(commit.message.startswith('Fixed #11357: contrib.admindocs'))
        self.assertEqual(commit.files, ['django/contrib/admindocs/views.py'])

    def test_recent_commits(self):
        results = self.repo.get_recent_commits()

    def test_list_directory(self):
        files, folders = self.repo.list_directory('tests/', 'c3699190186561d5c216b2a77ecbfc487d42a734')
        self.assertEqual(files, ['runtests.py', 'urls.py'])
        self.assertEqual(folders, ['modeltests', 'regressiontests', 'templates'])
        self.assertRaises(FolderDoesNotExist, self.repo.list_directory, 'tests/awesometests/')

    def test_file_contents(self):
        contents = self.repo.file_contents('django/db/models/fields/related.py',
            'c3699190186561d5c216b2a77ecbfc487d42a734')
        self.assertEqual(contents.splitlines()[:2], [
            'from django.db import connection, transaction',
            'from django.db.backends import util'
        ])
        self.assertRaises(FileDoesNotExist, self.repo.file_contents, 'django/db/models/jesus.py')

    def test_diffs(self):
        self.assertEqual(self.repo._diff_files(
            '35fa967a05d54d5159eb1c620544e050114ab0ed',
            'c3699190186561d5c216b2a77ecbfc487d42a734'
        ), ['django/contrib/admindocs/views.py'])
        files = [
            'AUTHORS',
            'django/contrib/gis/db/models/aggregates.py',
            'django/contrib/gis/db/models/query.py',
            'django/contrib/gis/db/models/sql/aggregates.py',
            'django/contrib/gis/db/models/sql/query.py',
            'django/db/backends/__init__.py',
            'django/db/backends/mysql/base.py',
            'django/db/backends/oracle/query.py',
            'django/db/backends/sqlite3/base.py',
            'django/db/models/aggregates.py',
            'django/db/models/__init__.py',
            'django/db/models/manager.py',
            'django/db/models/query.py',
            'django/db/models/query_utils.py',
            'django/db/models/sql/aggregates.py',
            'django/db/models/sql/datastructures.py',
            'django/db/models/sql/query.py',
            'django/db/models/sql/subqueries.py',
            'django/test/testcases.py',
            'docs/index.txt',
            'docs/ref/models/index.txt',
            'docs/ref/models/querysets.txt',
            'docs/topics/db/aggregation.txt',
            'docs/topics/db/index.txt',
            'tests/modeltests/aggregation',
            'tests/modeltests/aggregation/fixtures',
            'tests/modeltests/aggregation/fixtures/initial_data.json',
            'tests/modeltests/aggregation/__init__.py',
            'tests/modeltests/aggregation/models.py',
            'tests/regressiontests/aggregation_regress',
            'tests/regressiontests/aggregation_regress/fixtures',
            'tests/regressiontests/aggregation_regress/fixtures/initial_data.json',
            'tests/regressiontests/aggregation_regress/__init__.py',
            'tests/regressiontests/aggregation_regress/models.py'
        ]
        self.assertEqual(set(self.repo._diff_files(
            '842e1d0dabfe057c1eeb4b6b83de0b2eb7dcb9e6',
            'a6195888efe947f7b23c61248f43f4cab3c5200c',
        )), set(files))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = andrew_tests
#!/usr/bin/env python
from datetime import datetime
import unittest

from pyvcs.backends import get_backend
from pyvcs.exceptions import FileDoesNotExist, FolderDoesNotExist

class BzrTest(unittest.TestCase):
    def setUp(self):
        bzr = get_backend('bzr')
        self.repo = bzr.Repository('/home/andrew/junk/django/')

    def test_commits(self):
        commit = self.repo.get_commit_by_id('6460')
        self.assert_(commit.author.startswith('gwilson'))
        self.assertEqual(commit.time, datetime(2008, 12, 23, 18, 25, 24, 19000))
        self.assert_(commit.message.startswith('Fixed #8245 -- Added a LOADING flag'))
        self.assertEqual(commit.files, ['tests/regressiontests/bug8245', 'tests/regressiontests/bug8245/__init__.py', 'tests/regressiontests/bug8245/admin.py', 'tests/regressiontests/bug8245/models.py', 'tests/regressiontests/bug8245/tests.py', 'django/contrib/admin/__init__.py'])

    def test_recent_commits(self):
        results = self.repo.get_recent_commits()

    def test_list_directory(self):
        files, folders = self.repo.list_directory('tests/', '7254')
        self.assertEqual(files, ['runtests.py', 'urls.py'])
        self.assertEqual(folders, ['modeltests', 'regressiontests', 'templates'])
        self.assertRaises(FolderDoesNotExist, self.repo.list_directory, 'tests/awesometests/')

    def test_file_contents(self):
        contents = self.repo.file_contents('django/db/models/fields/related.py',
            '7254')
        self.assertEqual(contents.splitlines()[:2], [
            'from django.db import connection, transaction',
            'from django.db.backends import util'
        ])
        self.assertRaises(FileDoesNotExist, self.repo.file_contents, 'django/db/models/jesus.py')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = carlos_tests
#!/usr/bin/env python
from datetime import datetime
import unittest

from pyvcs.backends import get_backend
from pyvcs.exceptions import FileDoesNotExist, FolderDoesNotExist


class SVNTest(unittest.TestCase):
    def setUp(self):
        svn = get_backend('svn')
        self.repo = svn.Repository('/home/clsdaniel/Development/django')
        
    def test_commits(self):
        commit = self.repo.get_commit_by_id(11127)
        self.assert_(commit.author.startswith('ubernostrum'))
        self.assertEqual(commit.time, datetime(2009, 6, 30, 11, 40, 29, 647241))
        self.assert_(commit.message.startswith('Fixed #11357: contrib.admindocs'))
        self.assertEqual(commit.files, ['/django/trunk/django/contrib/admindocs/views.py'])
        
    def test_recent_commits(self):
        results = self.repo.get_recent_commits()

    def test_list_directory(self):
        files, folders = self.repo.list_directory('tests/', 11127)
        self.assertEqual(files, ['runtests.py', 'urls.py'])
        self.assertEqual(folders, ['modeltests', 'regressiontests', 'templates'])
        self.assertRaises(FolderDoesNotExist, self.repo.list_directory, 'tests/awesometests/')

    def test_file_contents(self):
        contents = self.repo.file_contents('django/db/models/fields/related.py', 11127)
        self.assertEqual(contents.splitlines()[:2], [
            'from django.db import connection, transaction',
            'from django.db.backends import util'
        ])
        self.assertRaises(FileDoesNotExist, self.repo.file_contents, 'django/db/models/jesus.py')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = justin_tests
#!/usr/bin/env python
from datetime import datetime
import unittest

from pyvcs.backends import get_backend
from pyvcs.exceptions import FileDoesNotExist, FolderDoesNotExist


class HGTest(unittest.TestCase):
    def setUp(self):
        hg = get_backend('hg')
        self.repo = hg.Repository('/home/jlilly/Code/python/pyvcs/src/mercurial')
        
    def test_commits(self):
        commit = self.repo.get_commit_by_id(45)
        self.assert_(commit.author.startswith('mpm'))
        self.assertEqual(commit.time, datetime(2005, 5, 10, 4, 34, 57))
        self.assert_(commit.message.startswith('Fix recursion depth'))
        
    def test_recent_commits(self):
        results = self.repo.get_recent_commits()
        
    def test_list_directory(self):
        files, folders = self.repo.list_directory('contrib/', 450)
        self.assertEqual(len(files), 3)
        self.assertEqual(folders, ['git-viz'])
        
    def test_file_contents(self):
        contents = self.repo.file_contents('tests/test-up-local-change', 450)
        self.assertEqual(contents.splitlines()[:1], ['#!/bin/bash'])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = simple_git_tests
#!/usr/bin/env python
from datetime import datetime
import unittest
import os
import subprocess

from pyvcs.backends import get_backend
from pyvcs.exceptions import FileDoesNotExist, FolderDoesNotExist, CommitDoesNotExist

class GitSimpleTest(unittest.TestCase):

    def setUp(self):
        git = get_backend('git')
        ret = subprocess.call('./setup_git_test.sh')
        self.repo = git.Repository('/tmp/pyvcs-test/git-test/')

    def tearDown(self):
        ret = subprocess.call('./teardown_git_test.sh')

    def test_recent_commits(self):
        recent_commits = self.repo.get_recent_commits()
        self.assertEqual(len(recent_commits),2)

    def test_commits(self):
        recent_commits = self.repo.get_recent_commits()
        commit = self.repo.get_commit_by_id(recent_commits[1].commit_id)
        self.assert_(commit.message.startswith('initial add of files'))
        self.assertEqual(commit.time.date(), datetime.today().date())
        self.assertEqual(commit.files, ['README', 'hello_world.py'])
        self.assert_('this is a test README file for a mock project' in commit.diff)
        self.assertRaises(CommitDoesNotExist,self.repo.get_commit_by_id,'crap')

    def test_list_directory(self):
        files, folders = self.repo.list_directory('')
        self.assertEqual(files, ['README', 'hello_world.py'])
        self.assertEqual(folders, [])
        self.assertRaises(FolderDoesNotExist, self.repo.list_directory, 'tests/awesometests/')

    def test_file_contents(self):
        contents = self.repo.file_contents('hello_world.py')
        self.assertEqual(contents,'print hello, world!\n')
        self.assertRaises(FileDoesNotExist, self.repo.file_contents, 'waybettertest.py')

    def test_diffs(self):
        recent_commits = self.repo.get_recent_commits()
        self.assertEqual(self.repo._diff_files(recent_commits[0].commit_id,recent_commits[1].commit_id),['README'])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
