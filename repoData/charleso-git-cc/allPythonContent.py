__FILENAME__ = cache
from os.path import join, exists
from common import *

FILE = '.gitcc'

def getCache():
    if cfg.getCore('cache', True) == 'False':
        return NoCache()
    return Cache(GIT_DIR)

class Cache(object):
    def __init__(self, dir):
        self.map = {}
        self.file = FILE
        self.dir = dir
        self.empty = Version('/main/0')
    def start(self):
        f = join(self.dir, self.file)
        if exists(f):
            self.load(f)
        else:
            self.initial()
    def load(self, file):
        f = open(file, 'r')
        try:
            self.read(f.read())
        finally:
            f.close()
    def initial(self):
        ls = ['ls', '-recurse', '-short']
        ls.extend(cfg.getInclude())
        self.read(cc_exec(ls))
    def read(self, lines):
        for line in lines.splitlines():
            if line.find('@@') < 0:
                continue
            self.update(CCFile2(line))
    def update(self, path):
        isChild = self.map.get(path.file, self.empty).isChild(path.version)
        if isChild:
            self.map[path.file] = path.version
        return isChild or path.version.endswith(cfg.getBranches()[0])
    def remove(self, file):
        if file in self.map:
            del self.map[file]
    def write(self):
        lines = []
        keys = self.map.keys()
        keys = sorted(keys)
        for file in keys:
            lines.append(file + '@@' + self.map[file].full)
        f = open(join(self.dir, self.file), 'w')
        try:
            f.write('\n'.join(lines))
            f.write('\n')
        finally:
            f.close()
        git_exec(['add', self.file])
    def list(self):
        values = []
        for file, version in self.map.items():
            values.append(CCFile(file, version.full))
        return values
    def contains(self, path):
        return self.map.get(path.file, self.empty).full == path.version.full

class NoCache(object):
    def start(self):
        pass
    def write(self):
        pass
    def update(self, path):
        return True
    def remove(self, file):
        pass

class CCFile(object):
    def __init__(self, file, version):
        if file.startswith('./') or file.startswith('.\\'):
            file = file[2:]
        self.file = file
        self.version = Version(version)

class CCFile2(CCFile):
    def __init__(self, line):
        [file, version] = line.rsplit('@@', 1)
        super(CCFile2, self).__init__(file, version)

class Version(object):
    def __init__(self, version):
        self.full = version.replace('\\', '/')
        self.version = '/'.join(self.full.split('/')[0:-1])
    def isChild(self, version):
        return version.version.startswith(self.version)
    def endswith(self, version):
        return self.version.endswith('/' + version)

########NEW FILE########
__FILENAME__ = checkin
"""Checkin new git changesets to Clearcase"""

from common import *
from clearcase import cc
from status import Modify, Add, Delete, Rename, SymLink
import filecmp
from os import listdir
from os.path import isdir
import cache, reset

IGNORE_CONFLICTS=False
LOG_FORMAT = '%H%x01%B'
CC_LABEL = ''

ARGS = {
    'force': 'ignore conflicts and check-in anyway',
    'no_deliver': 'do not deliver in UCM mode',
    'initial': 'checkin everything from the beginning',
    'all': 'checkin all parents, not just the first',
    'cclabel': 'optionally specify an existing Clearcase label type to apply to each element checked in',
}

def main(force=False, no_deliver=False, initial=False, all=False, cclabel=''):
    validateCC()
    global IGNORE_CONFLICTS
    global CC_LABEL
    if cclabel:
        CC_LABEL=cclabel
    if force:
        IGNORE_CONFLICTS=True
    cc_exec(['update', '.'], errors=False)
    log = ['log', '-z', '--reverse', '--pretty=format:'+ LOG_FORMAT ]
    if not all:
        log.append('--first-parent')
    if not initial:
        log.append(CI_TAG + '..')
    log = git_exec(log)
    if not log:
        return
    cc.rebase()
    for line in log.split('\x00'):
        id, comment = line.split('\x01')
        statuses = getStatuses(id, initial)
        checkout(statuses, comment.strip(), initial)
        tag(CI_TAG, id)
    if not no_deliver:
        cc.commit()
    if initial:
        git_exec(['commit', '--allow-empty', '-m', 'Empty commit'])
        reset.main('HEAD')

def getStatuses(id, initial):
    cmd = ['diff','--name-status', '-M', '-z', '--ignore-submodules', '%s^..%s' % (id, id)]
    if initial:
        cmd = cmd[:-1]
        cmd[0] = 'show'
        cmd.extend(['--pretty=format:', id])
    status = git_exec(cmd)
    status = status.strip()
    status = status.strip("\x00")
    types = {'M':Modify, 'R':Rename, 'D':Delete, 'A':Add, 'C':Add, 'S':SymLink}
    list = []
    split = status.split('\x00')
    while len(split) > 1:
        char = split.pop(0)[0] # first char
        args = [split.pop(0)]
        # check if file is really a symlink
        cmd = ['ls-tree', '-z', id, '--', args[0]]
        if git_exec(cmd).split(' ')[0] == '120000':
            char = 'S'
            args.append(id)
        if char == 'R':
            args.append(split.pop(0))
        elif char == 'C':
            args = [split.pop(0)]
        if args[0] == cache.FILE:
            continue
        type = types[char](args)
        type.id = id
        list.append(type)
    return list

def checkout(stats, comment, initial):
    """Poor mans two-phase commit"""
    transaction = ITransaction(comment) if initial else Transaction(comment)
    for stat in stats:
        try:
            stat.stage(transaction)
        except:
            transaction.rollback()
            raise

    for stat in stats:
         stat.commit(transaction)
    transaction.commit(comment);

class ITransaction(object):
    def __init__(self, comment):
        self.checkedout = []
        self.cc_label = CC_LABEL
        cc.mkact(comment)
    def add(self, file):
        self.checkedout.append(file)
    def co(self, file):
        cc_exec(['co', '-reserved', '-nc', file])
        if CC_LABEL:
            cc_exec(['mklabel', '-replace', '-nc', CC_LABEL, file])
        self.add(file)
    def stageDir(self, file):
        file = file if file else '.'
        if file not in self.checkedout:
            self.co(file)
    def stage(self, file):
        self.co(file)
    def rollback(self):
        for file in self.checkedout:
            cc_exec(['unco', '-rm', file])
        cc.rmactivity()
    def commit(self, comment):
        for file in self.checkedout:
            cc_exec(['ci', '-identical', '-c', comment, file])

class Transaction(ITransaction):
    def __init__(self, comment):
        super(Transaction, self).__init__(comment)
        self.base = git_exec(['merge-base', CI_TAG, 'HEAD']).strip()
    def stage(self, file):
        super(Transaction, self).stage(file)
        ccid = git_exec(['hash-object', join(CC_DIR, file)])[0:-1]
        gitid = getBlob(self.base, file)
        if ccid != gitid:
            if not IGNORE_CONFLICTS:
                raise Exception('File has been modified: %s. Try rebasing.' % file)
            else:
                print ('WARNING: Detected possible confilct with',file,'...ignoring...')

########NEW FILE########
__FILENAME__ = clearcase
from common import *

class Clearcase:
    def rebase(self):
        pass
    def mkact(self, comment):
        pass
    def rmactivity(self):
        pass
    def commit(self):
        pass
    def getCommentFmt(self):
        return '%Nc'
    def getRealComment(self, comment):
        return comment

class UCM:
    def __init__(self):
        self.activities = {}
    def rebase(self):
        out = cc_exec(['rebase', '-rec', '-f'])
        if not out.startswith('No rebase needed'):
            debug(out)
            debug(cc_exec(['rebase', '-complete']))
    def mkact(self, comment):
        self.activity = self._getActivities().get(comment)
        if self.activity:
            cc_exec(['setact', self.activity])
            return
        _comment = cc_exec(['mkact', '-f', '-headline', comment])
        _comment = _comment.split('\n')[0]
        self.activity = _comment[_comment.find('"')+1:_comment.rfind('"')]
        self._getActivities()[comment] = self.activity
    def rmactivity(self):
        cc_exec(['setact', '-none'])
        cc_exec(['rmactivity', '-f', self.activity], errors=False)
    def commit(self):
        cc_exec(['setact', '-none'])
        debug(cc_exec(['deliver','-f']))
        debug(cc_exec(['deliver', '-com', '-f']))
    def getCommentFmt(self):
        return '%[activity]p'
    def getRealComment(self, activity):
        return cc_exec(['lsactivity', '-fmt', '%[headline]p', activity]) if activity else activity
    def _getActivities(self):
        if not self.activities:
            sep = '@@@'
            for line in cc_exec(['lsactivity', '-fmt', '%[headline]p|%n' + sep]).split(sep):
                if line:
                    line = line.strip().split('|')
                    self.activities[line[0]] = line[1]
        return self.activities

cc = (UCM if cfg.getCore('type') == 'UCM' else Clearcase)();

########NEW FILE########
__FILENAME__ = common
from distutils import __version__
v30 = __version__.find("3.") == 0

from subprocess import Popen, PIPE
import os, sys
from os.path import join, exists, abspath, dirname
if v30:
    from configparser import SafeConfigParser
else:
    from ConfigParser import SafeConfigParser

IS_CYGWIN = sys.platform == 'cygwin'

if IS_CYGWIN:
    FS = '\\'
else:
    FS = os.sep

CFG_CC = 'clearcase'
CC_DIR = None
ENCODING = None
if hasattr(sys.stdin, 'encoding'):
    ENCODING = sys.stdin.encoding
if ENCODING is None:
    import locale
    locale_name, ENCODING = locale.getdefaultlocale()
if ENCODING is None:
    ENCODING = "ISO8859-1"
DEBUG = False

def fail(string):
    print(string)
    sys.exit(2)

def doStash(f, stash):
    if(stash):
        git_exec(['stash'])
    f()
    if(stash):
        git_exec(['stash', 'pop'])

def debug(string):
    if DEBUG:
        print(string)

def git_exec(cmd, **args):
    return popen('git', cmd, GIT_DIR, **args)

def cc_exec(cmd, **args):
    return popen('cleartool', cmd, CC_DIR, **args)

def popen(exe, cmd, cwd, env=None, decode=True, errors=True):
    cmd.insert(0, exe)
    if DEBUG:
        f = lambda a: a if not a.count(' ') else '"%s"' % a
        debug('> ' + ' '.join(map(f, cmd)))
    pipe = Popen(cmd, cwd=cwd, stdout=PIPE, stderr=PIPE, env=env)
    (stdout, stderr) = pipe.communicate()
    if errors and pipe.returncode > 0:
        raise Exception((stderr + stdout).decode(ENCODING))
    return stdout if not decode else stdout.decode(ENCODING)

def tag(tag, id="HEAD"):
    git_exec(['tag', '-f', tag, id])

def reset(tag=None):
    git_exec(['reset', '--hard', tag or CC_TAG])

def getBlob(sha, file):
    return git_exec(['ls-tree', '-z', sha, file]).split(' ')[2].split('\t')[0]

def gitDir():
    def findGitDir(dir):
        if not exists(dir) or dirname(dir) == dir:
            return '.'
        if exists(join(dir, '.git')):
            return dir
        return findGitDir(dirname(dir))
    return findGitDir(abspath('.'))

def getCurrentBranch():
    for branch in git_exec(['branch']).split('\n'):
        if branch.startswith('*'):
            branch = branch[2:]
            if branch == '(no branch)':
                fail("Why aren't you on a branch?")
            return branch
    return ""

class GitConfigParser():
    CORE = 'core'
    def __init__(self, branch):
        self.section = branch
        self.file = join(GIT_DIR, '.git', 'gitcc')
        self.parser = SafeConfigParser();
        self.parser.add_section(self.section)
    def set(self, name, value):
        self.parser.set(self.section, name, value)
    def read(self):
        self.parser.read(self.file)
    def write(self):
        self.parser.write(open(self.file, 'w'))
    def getCore(self, name, *args):
        return self._get(self.CORE, name, *args)
    def get(self, name, *args):
        return self._get(self.section, name, *args)
    def _get(self, section, name, default=None):
        if not self.parser.has_option(section, name):
            return default
        return self.parser.get(section, name)
    def getList(self, name, default=None):
        return self.get(name, default).split('|')
    def getInclude(self):
        return self.getCore('include', '.').split('|')
    def getExclude(self):
        return self.getCore('exclude', '.').split('|')
    def getBranches(self):
        return self.getList('branches', 'main')
    def getExtraBranches(self):
        return self.getList('_branches', 'main')

def write(file, blob):
    _write(file, blob)

def _write(file, blob):
    f = open(file, 'wb')
    f.write(blob)
    f.close()

def mkdirs(file):
    dir = dirname(file)
    if not exists(dir):
        os.makedirs(dir)

def removeFile(file):
    if exists(file):
        os.remove(file)

def validateCC():
    if not CC_DIR:
        fail("No 'clearcase' variable found for branch '%s'" % CURRENT_BRANCH)
        
def path(path, args='-m'):
    if IS_CYGWIN:
        return os.popen('cygpath %s "%s"' %(args, path)).readlines()[0].strip()
    else:
        return path

GIT_DIR = path(gitDir())
if not exists(join(GIT_DIR, '.git')):
    fail("fatal: Not a git repository (or any of the parent directories): .git")
CURRENT_BRANCH = getCurrentBranch() or 'master'
cfg = GitConfigParser(CURRENT_BRANCH)
cfg.read()
CC_DIR = path(cfg.get(CFG_CC))
DEBUG = cfg.getCore('debug', True)
CC_TAG = CURRENT_BRANCH + '_cc'
CI_TAG = CURRENT_BRANCH + '_ci'


########NEW FILE########
__FILENAME__ = init
"""Initialise gitcc with a clearcase directory"""

from common import *
from os import open
from os.path import join, exists

def main(ccdir):
    git_exec(['config', 'core.autocrlf', 'false'])
    cfg.set(CFG_CC, ccdir)
    cfg.write()

########NEW FILE########
__FILENAME__ = rebase
"""Rebase from Clearcase"""

from os.path import join, dirname, exists, isdir
import os, stat
from common import *
from datetime import datetime, timedelta
from users import users, mailSuffix
from fnmatch import fnmatch
from clearcase import cc
from cache import getCache, CCFile
from re import search

"""
Things remaining:
1. Renames with no content change. Tricky.
"""

CC_LSH = ['lsh', '-fmt', '%o%m|%Nd|%u|%En|%Vn|'+cc.getCommentFmt()+'\\n', '-recurse']
DELIM = '|'

ARGS = {
    'stash': 'Wraps the rebase in a stash to avoid file changes being lost',
    'dry_run': 'Prints a list of changesets to be imported',
    'lshistory': 'Prints the raw output of lshistory to be cached for load',
    'load': 'Loads the contents of a previously saved lshistory file',
}

cache = getCache()

def main(stash=False, dry_run=False, lshistory=False, load=None):
    validateCC()
    if not (stash or dry_run or lshistory):
        checkPristine()
    since = getSince()
    cache.start()
    if load:
        history = open(load, 'r').read().decode(ENCODING)
    else:
        cc.rebase()
        history = getHistory(since)
        write(join(GIT_DIR, '.git', 'lshistory.bak'), history.encode(ENCODING))
    if lshistory:
        print(history)
    else:
        cs = parseHistory(history)
        cs = reversed(cs)
        cs = mergeHistory(cs)
        if dry_run:
            return printGroups(cs)
        if not len(cs):
            return
        doStash(lambda: doCommit(cs), stash)

def checkPristine():
    if(len(git_exec(['ls-files', '--modified']).splitlines()) > 0):
        fail('There are uncommitted files in your git directory')

def doCommit(cs):
    branch = getCurrentBranch()
    if branch:
        git_exec(['checkout', CC_TAG])
    try:
        commit(cs)
    finally:
        if branch:
            git_exec(['rebase', CI_TAG, CC_TAG])
            git_exec(['rebase', CC_TAG, branch])
        else:
            git_exec(['branch', '-f', CC_TAG])
        tag(CI_TAG, CC_TAG)

def getSince():
    try:
        date = git_exec(['log', '-n', '1', '--pretty=format:%ai', '%s' % CC_TAG])
        date = date[:19]
        date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        date = date + timedelta(seconds=1)
        return datetime.strftime(date, '%d-%b-%Y.%H:%M:%S')
    except:
        return cfg.get('since')

def getHistory(since):
    lsh = CC_LSH[:]
    if since:
        lsh.extend(['-since', since])
    lsh.extend(cfg.getInclude())
    return cc_exec(lsh)

def filterBranches(version, all=False):
    version = version.split(FS)
    version.pop()
    version = version[-1]
    branches = cfg.getBranches();
    if all:
        branches.extend(cfg.getExtraBranches())
    for branch in branches:
        if fnmatch(version, branch):
            return True
    return False

def parseHistory(lines):
    changesets = []
    def add(split, comment):
        if not split:
            return
        cstype = split[0]
        if cstype in TYPES:
            cs = TYPES[cstype](split, comment)
            try:
                if filterBranches(cs.version):
                    changesets.append(cs)
            except Exception as e:
                print('Bad line', split, comment)
                raise
    last = None
    comment = None
    for line in lines.splitlines():
        split = line.split(DELIM)
        if len(split) < 6 and last:
            # Cope with comments with '|' character in them
            comment += "\n" + DELIM.join(split)
        else:
            add(last, comment)
            comment = DELIM.join(split[5:])
            last = split
    add(last, comment)
    return changesets

def mergeHistory(changesets):
    last = None
    groups = []
    def same(a, b):
        return a.subject == b.subject and a.user == b.user
    for cs in changesets:
        if last and same(last, cs):
            last.append(cs)
        else:
            last = Group(cs)
            groups.append(last)
    for group in groups:
        group.fixComment()
    return groups

def commit(list):
    for cs in list:
        cs.commit()

def printGroups(groups):
    for cs in groups:
        print('%s "%s"' % (cs.user, cs.subject))
        for file in cs.files:
            print("  %s" % file.file)

class Group:
    def __init__(self, cs):
        self.user = cs.user
        self.comment = cs.comment
        self.subject = cs.subject
        self.files = []
        self.append(cs)
    def append(self, cs):
        self.date = cs.date
        self.files.append(cs)
    def fixComment(self):
        self.comment = cc.getRealComment(self.comment)
        self.subject = self.comment.split('\n')[0]
    def commit(self):
        def getCommitDate(date):
            return date[:4] + '-' + date[4:6] + '-' + date[6:8] + ' ' + \
                   date[9:11] + ':' + date[11:13] + ':' + date[13:15]
        def getUserName(user):
            return str(user).split(' <')[0]
        def getUserEmail(user):
            email = search('<.*@.*>', str(user))
            if email == None:
                return '<%s@%s>' % (user.lower().replace(' ','.').replace("'", ''), mailSuffix)
            else:
                return email.group(0)
        files = []
        for file in self.files:
            files.append(file.file)
        for file in self.files:
            file.add(files)
        cache.write()
        env = os.environ
        user = users.get(self.user, self.user)
        env['GIT_AUTHOR_DATE'] = env['GIT_COMMITTER_DATE'] = str(getCommitDate(self.date))
        env['GIT_AUTHOR_NAME'] = env['GIT_COMMITTER_NAME'] = getUserName(user)
        env['GIT_AUTHOR_EMAIL'] = env['GIT_COMMITTER_EMAIL'] = str(getUserEmail(user))
        comment = self.comment if self.comment.strip() != "" else "<empty message>"
        try:
            git_exec(['commit', '-m', comment.encode(ENCODING)], env=env)
        except Exception as e:
            if search('nothing( added)? to commit', e.args[0]) == None:
                raise

def cc_file(file, version):
    return '%s@@%s' % (file, version)

class Changeset(object):
    def __init__(self, split, comment):
        self.date = split[1]
        self.user = split[2]
        self.file = split[3]
        self.version = split[4]
        self.comment = comment
        self.subject = comment.split('\n')[0]
    def add(self, files):
        self._add(self.file, self.version)
    def _add(self, file, version):
        if not cache.update(CCFile(file, version)):
            return
        if [e for e in cfg.getExclude() if fnmatch(file, e)]:
            return
        toFile = path(join(GIT_DIR, file))
        mkdirs(toFile)
        removeFile(toFile)
        try:
            cc_exec(['get','-to', toFile, cc_file(file, version)])
        except:
            if len(file) < 200:
                raise
            debug("Ignoring %s as it may be related to https://github.com/charleso/git-cc/issues/9" % file)
        if not exists(toFile):
            git_exec(['checkout', 'HEAD', toFile])
        else:
            os.chmod(toFile, os.stat(toFile).st_mode | stat.S_IWRITE)
        git_exec(['add', '-f', file], errors=False)

class Uncataloged(Changeset):
    def add(self, files):
        dir = path(cc_file(self.file, self.version))
        diff = cc_exec(['diff', '-diff_format', '-pred', dir], errors=False)
        def getFile(line):
            return join(self.file, line[2:max(line.find('  '), line.find(FS + ' '))])
        for line in diff.split('\n'):
            sym = line.find(' -> ')
            if sym >= 0:
                continue
            if line.startswith('<'):
                git_exec(['rm', '-r', getFile(line)], errors=False)
                cache.remove(getFile(line))
            elif line.startswith('>'):
                added = getFile(line)
                cc_added = join(CC_DIR, added)
                if not exists(cc_added) or isdir(cc_added) or added in files:
                    continue
                history = cc_exec(['lshistory', '-fmt', '%o%m|%Nd|%Vn\\n', added], errors=False)
                if not history:
                    continue
                date = cc_exec(['describe', '-fmt', '%Nd', dir])
                def f(s):
                    return s[0] == 'checkinversion' and s[1] < date and filterBranches(s[2], True)
                versions = list(filter(f, list(map(lambda x: x.split('|'), history.split('\n')))))
                if not versions:
                    print("It appears that you may be missing a branch in the includes section of your gitcc config for file '%s'." % added)  
                    continue
                self._add(added, versions[0][2].strip())

TYPES = {\
    'checkinversion': Changeset,\
    'checkindirectory version': Uncataloged,\
}

########NEW FILE########
__FILENAME__ = reset
"""Reset hard to a specific changeset"""

from common import *

def main(commit):
    git_exec(['branch', '-f', CC_TAG, commit])
    tag(CI_TAG, commit)

########NEW FILE########
__FILENAME__ = status
from common import *
from os.path import join, dirname

class Status:
    def __init__(self, files):
        self.setFile(files[0])
    def setFile(self, file):
        self.file = file
    def cat(self):
        blob = git_exec(['cat-file', 'blob', getBlob(self.id, self.file)], decode=False)
        write(join(CC_DIR, self.file), blob)
    def stageDirs(self, t):
        dir = dirname(self.file)
        dirs = []
        while not exists(join(CC_DIR, dir)):
            dirs.append(dir)
            dir = dirname(dir)
        self.dirs = dirs
        t.stageDir(dir)
    def commitDirs(self, t):
        while len(self.dirs) > 0:
            dir = self.dirs.pop();
            if not exists(join(CC_DIR, dir)):
                cc_exec(['mkelem', '-nc', '-eltype', 'directory', dir])
                if t.cc_label:
                    cc_exec(['mklabel', '-nc', t.cc_label, dir])
                t.add(dir)

class Modify(Status):
    def stage(self, t):
        t.stage(self.file)
    def commit(self, t):
        self.cat()

class Add(Status):
    def stage(self, t):
        self.stageDirs(t)
    def commit(self, t):
        self.commitDirs(t)
        self.cat()
        cc_exec(['mkelem', '-nc', self.file])
        if t.cc_label:
            cc_exec(['mklabel', '-nc', t.cc_label, self.file])
        t.add(self.file)

class Delete(Status):
    def stage(self, t):
        t.stageDir(dirname(self.file))
    def commit(self, t):
        # TODO Empty dirs?!?
        cc_exec(['rm', self.file])

class Rename(Status):
    def __init__(self, files):
        self.old = files[0]
        self.new = files[1]
        self.setFile(self.new)
    def stage(self, t):
        t.stageDir(dirname(self.old))
        t.stage(self.old)
        self.stageDirs(t)
    def commit(self, t):
        self.commitDirs(t)
        cc_exec(['mv', '-nc', self.old, self.new])
        t.checkedout.remove(self.old)
        t.add(self.new)
        self.cat()

class SymLink(Status):
    def __init__(self, files):
        self.setFile(files[0])
        id = files[1]
        self.target = git_exec(['cat-file', 'blob', getBlob(id, self.file)], decode=False)
        if exists(join(CC_DIR, self.file)):
            self.rmfirst=True
        else:
            self.rmfirst=False
    def stage(self, t):
        self.stageDirs(t)
    def commit(self, t):
        if self.rmfirst:
            cc_exec(['rm', self.file])
        cc_exec(['ln', '-s', self.target, self.file])

########NEW FILE########
__FILENAME__ = sync
"""Copy files from Clearcase to Git manually"""

from common import *
from cache import *
import os, shutil, stat
from os.path import join, abspath, isdir
from fnmatch import fnmatch

ARGS = {
    'cache': 'Use the cache for faster syncing'
}

def main(cache=False):
    validateCC()
    if cache:
        return syncCache()
    glob = '*'
    base = abspath(CC_DIR)
    for i in cfg.getInclude():
        for (dirpath, dirnames, filenames) in os.walk(join(CC_DIR, i)):
            reldir = dirpath[len(base)+1:]
            if fnmatch(reldir, './lost+found'):
                continue
            for file in filenames:
                if fnmatch(file, glob):
                    copy(join(reldir, file))

def copy(file):
    newFile = join(GIT_DIR, file)
    debug('Copying %s' % newFile)
    mkdirs(newFile)
    shutil.copy(join(CC_DIR, file), newFile)
    os.chmod(newFile, stat.S_IREAD | stat.S_IWRITE)

def syncCache():
    cache1 = Cache(GIT_DIR)
    cache1.start()
    
    cache2 = Cache(GIT_DIR)
    cache2.initial()
    
    for path in cache2.list():
        if not cache1.contains(path):
            cache1.update(path)
            if not isdir(join(CC_DIR, path.file)):
                copy(path.file)
    cache1.write()

########NEW FILE########
__FILENAME__ = tag
"""Tag a particular commit as gitcc start point"""

from common import *

def main(commit):
    tag(CI_TAG, commit)

########NEW FILE########
__FILENAME__ = test-cache
import sys, shutil
sys.path.append("..")
from os.path import join
import unittest
import cache
from cache import Cache, CCFile
import tempfile

TEMP1 = """
file.py@@/main/a/b/1
"""

TEMP1_EXPECTED = """file.py@@/main/a/b/2
file2.py@@/main/c/2
"""

class CacheTest(unittest.TestCase):
    def testLoad(self):
        dir = tempfile.mkdtemp()
        f = open(join(dir, cache.FILE), 'w')
        f.write(TEMP1)
        f.close()
        try:
            c = Cache(dir)
            self.assertFalse(c.isChild(CCFile('file.py', '/main/a/1')))
            self.assertFalse(c.isChild(CCFile('file.py', r'\main\a\1')))
            self.assertTrue(c.isChild(CCFile('file.py', '/main/a/b/c/1')))
            self.assertFalse(c.isChild(CCFile('file.py', '/main/a/c/1')))
            c.update(CCFile('file.py', '/main/a/b/2'))
            c.update(CCFile('file2.py', '/main/c/2'))
            c.write()
            f = open(join(dir, cache.FILE), 'r')
            try:
                self.assertEqual(TEMP1_EXPECTED, f.read())
            finally:
                f.close()
        finally:
            shutil.rmtree(dir)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test-checkin
from __init__ import *
import checkin, common
import unittest, os
from os.path import join
from common import CC_DIR, CI_TAG

class CheckinTest(TestCaseEx):
    def setUp(self):
        TestCaseEx.setUp(self)
        self.expectedExec.append((['cleartool', 'update', '.'], ''))
        self.commits = []
    def checkin(self):
        self.expectedExec.insert(1,
            (['git', 'log', '--first-parent', '--reverse', '--pretty=format:%H%n%s%n%b', '%s..' % CI_TAG], '\n'.join(self.commits)),
        )
        checkin.main()
        self.assert_(not len(self.expectedExec))
    def commit(self, commit, message, files):
        nameStatus = []
        for type, file in files:
            nameStatus.append('%s\0%s' % (type, file))
        self.expectedExec.extend([
            (['git', 'diff', '--name-status', '-M', '-z', '%s^..%s' % (commit, commit)], '\n'.join(nameStatus)),
        ])
        types = {'M': MockModfy, 'A': MockAdd, 'D': MockDelete, 'R': MockRename}
        self.expectedExec.extend([
            (['git', 'merge-base', CI_TAG, 'HEAD'], 'abcdef'),
        ])
        for type, file in files:
            types[type](self.expectedExec, commit, message, file)
        self.expectedExec.extend([
            (['git', 'tag', '-f', CI_TAG, commit], ''),
        ])
        self.commits.extend([commit, message, ''])
    def testEmpty(self):
        self.checkin()
    def testSimple(self):
        self.commit('sha1', 'commit1', [('M', 'a.py')])
        self.commit('sha2', 'commit2', [('M', 'b.py')])
        self.commit('sha3', 'commit3', [('A', 'c.py')])
        self.checkin();
    def testFolderAdd(self):
        self.commit('sha4', 'commit4', [('A', 'a/b/c/d.py')])
        self.checkin();
    def testDelete(self):
        os.mkdir(join(CC_DIR, 'd'))
        self.commit('sha4', 'commit4', [('D', 'd/e.py')])
        self.checkin();
    def testRename(self):
        os.mkdir(join(CC_DIR, 'a'))
        self.commit('sha1', 'commit1', [('R', 'a/b.py\0c/d.py')])
        self.checkin();

class MockStatus:
    def lsTree(self, id, file, hash):
        return (['git', 'ls-tree', '-z', id, file], '100644 blob %s %s' % (hash, file))
    def catFile(self, file, hash):
        blob = "blob"
        return [
            (['git', 'cat-file', 'blob', hash], blob),
            (join(CC_DIR, file), blob),
        ]
    def hash(self, file):
        hash1 = 'hash1'
        return [
            (['git', 'hash-object', join(CC_DIR, file)], hash1 + '\n'),
            self.lsTree('abcdef', file, hash1),
        ]
    def co(self, file):
        return (['cleartool', 'co', '-reserved', '-nc', file], '')
    def ci(self, message, file):
        return (['cleartool', 'ci', '-identical', '-c', message, file], '')
    def mkelem(self, file):
        return (['cleartool', 'mkelem', '-nc', '-eltype', 'directory', file], '')
    def dir(self, file):
        return file[0:file.rfind('/')];

class MockModfy(MockStatus):
    def __init__(self, e, commit, message, file):
        hash2 = "hash2"
        e.append(self.co(file))
        e.extend(self.hash(file))
        e.append(self.lsTree(commit, file, hash2))
        e.extend(self.catFile(file, hash2))
        e.append(self.ci(message, file))

class MockAdd(MockStatus):
    def __init__(self, e, commit, message, file):
        hash = 'hash'
        files = []
        files.append(".")
        e.append(self.co("."))
        path = ""
        for f in file.split('/')[0:-1]:
            path = path + f + '/'
            f = path[0:-1]
            files.append(f)
            e.append(self.mkelem(f))
        e.append(self.lsTree(commit, file, hash))
        e.extend(self.catFile(file, hash))
        e.append((['cleartool', 'mkelem', '-nc', file], '.'))
        for f in files:
            e.append(self.ci(message, f))
        e.append(self.ci(message, file))

class MockDelete(MockStatus):
    def __init__(self, e, commit, message, file):
        dir = file[0:file.rfind('/')]
        e.extend([
            self.co(dir),
            (['cleartool', 'rm', file], ''),
            self.ci(message, dir),
        ])

class MockRename(MockStatus):
    def __init__(self, e, commit, message, file):
        a, b = file.split('\0')
        hash = 'hash'
        e.extend([
            self.co(self.dir(a)),
            self.co(a),
        ])
        e.extend(self.hash(a))
        e.extend([
            self.co("."),
            self.mkelem(self.dir(b)),
            (['cleartool', 'mv', '-nc', a, b], '.'),
            self.lsTree(commit, b, hash),
        ])
        e.extend(self.catFile(b, hash))
        e.extend([
            self.ci(message, self.dir(a)),
            self.ci(message, "."),
            self.ci(message, self.dir(b)),
            self.ci(message, b),
        ])

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = update
"""Update the git repository with Clearcase manually, ignoring history"""

from common import *
import sync, reset

def main(message):
    cc_exec(['update', '.'], errors=False)
    sync.main()
    git_exec(['add', '.'])
    git_exec(['commit', '-m', message])
    reset.main('HEAD')

########NEW FILE########
