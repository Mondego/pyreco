__FILENAME__ = bloom-cmd
#!/usr/bin/env python
import sys, glob, tempfile
from bup import options, git, bloom
from bup.helpers import *

optspec = """
bup bloom [options...]
--
ruin       ruin the specified bloom file (clearing the bitfield)
f,force    ignore existing bloom file and regenerate it from scratch
o,output=  output bloom filename (default: auto)
d,dir=     input directory to look for idx files (default: auto)
k,hashes=  number of hash functions to use (4 or 5) (default: auto)
c,check=   check the given .idx file against the bloom filter
"""


def ruin_bloom(bloomfilename):
    rbloomfilename = git.repo_rel(bloomfilename)
    if not os.path.exists(bloomfilename):
        log("%s\n" % bloomfilename)
        add_error("bloom: %s not found to ruin\n" % rbloomfilename)
        return
    b = bloom.ShaBloom(bloomfilename, readwrite=True, expected=1)
    b.map[16:16+2**b.bits] = '\0' * 2**b.bits


def check_bloom(path, bloomfilename, idx):
    rbloomfilename = git.repo_rel(bloomfilename)
    ridx = git.repo_rel(idx)
    if not os.path.exists(bloomfilename):
        log("bloom: %s: does not exist.\n" % rbloomfilename)
        return
    b = bloom.ShaBloom(bloomfilename)
    if not b.valid():
        add_error("bloom: %r is invalid.\n" % rbloomfilename)
        return
    base = os.path.basename(idx)
    if base not in b.idxnames:
        log("bloom: %s does not contain the idx.\n" % rbloomfilename)
        return
    if base == idx:
        idx = os.path.join(path, idx)
    log("bloom: bloom file: %s\n" % rbloomfilename)
    log("bloom:   checking %s\n" % ridx)
    for objsha in git.open_idx(idx):
        if not b.exists(objsha):
            add_error("bloom: ERROR: object %s missing" 
                      % str(objsha).encode('hex'))


_first = None
def do_bloom(path, outfilename):
    global _first
    b = None
    if os.path.exists(outfilename) and not opt.force:
        b = bloom.ShaBloom(outfilename)
        if not b.valid():
            debug1("bloom: Existing invalid bloom found, regenerating.\n")
            b = None

    add = []
    rest = []
    add_count = 0
    rest_count = 0
    for i,name in enumerate(glob.glob('%s/*.idx' % path)):
        progress('bloom: counting: %d\r' % i)
        ix = git.open_idx(name)
        ixbase = os.path.basename(name)
        if b and (ixbase in b.idxnames):
            rest.append(name)
            rest_count += len(ix)
        else:
            add.append(name)
            add_count += len(ix)
    total = add_count + rest_count

    if not add:
        debug1("bloom: nothing to do.\n")
        return

    if b:
        if len(b) != rest_count:
            debug1("bloom: size %d != idx total %d, regenerating\n"
                   % (len(b), rest_count))
            b = None
        elif (b.bits < bloom.MAX_BLOOM_BITS and
              b.pfalse_positive(add_count) > bloom.MAX_PFALSE_POSITIVE):
            debug1("bloom: regenerating: adding %d entries gives "
                   "%.2f%% false positives.\n"
                   % (add_count, b.pfalse_positive(add_count)))
            b = None
        else:
            b = bloom.ShaBloom(outfilename, readwrite=True, expected=add_count)
    if not b: # Need all idxs to build from scratch
        add += rest
        add_count += rest_count
    del rest
    del rest_count

    msg = b is None and 'creating from' or 'adding'
    if not _first: _first = path
    dirprefix = (_first != path) and git.repo_rel(path)+': ' or ''
    progress('bloom: %s%s %d file%s (%d object%s).\n'
        % (dirprefix, msg,
           len(add), len(add)!=1 and 's' or '',
           add_count, add_count!=1 and 's' or ''))

    tfname = None
    if b is None:
        tfname = os.path.join(path, 'bup.tmp.bloom')
        b = bloom.create(tfname, expected=add_count, k=opt.k)
    count = 0
    icount = 0
    for name in add:
        ix = git.open_idx(name)
        qprogress('bloom: writing %.2f%% (%d/%d objects)\r' 
                  % (icount*100.0/add_count, icount, add_count))
        b.add_idx(ix)
        count += 1
        icount += len(ix)

    # Currently, there's an open file object for tfname inside b.
    # Make sure it's closed before rename.
    b.close()

    if tfname:
        os.rename(tfname, outfilename)


handle_ctrl_c()

o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

if extra:
    o.fatal('no positional parameters expected')

git.check_repo_or_die()

if not opt.check and opt.k and opt.k not in (4,5):
    o.fatal('only k values of 4 and 5 are supported')

paths = opt.dir and [opt.dir] or git.all_packdirs()
for path in paths:
    debug1('bloom: scanning %s\n' % path)
    outfilename = opt.output or os.path.join(path, 'bup.bloom')
    if opt.check:
        check_bloom(path, outfilename, opt.check)
    elif opt.ruin:
        ruin_bloom(outfilename)
    else:
        do_bloom(path, outfilename)

if saved_errors:
    log('WARNING: %d errors encountered during bloom.\n' % len(saved_errors))
    sys.exit(1)
elif opt.check:
    log('All tests passed.\n')

########NEW FILE########
__FILENAME__ = cat-file-cmd
#!/usr/bin/env python
import sys, stat
from bup import options, git, vfs
from bup.helpers import *

optspec = """
bup cat-file [--meta|--bupm] /branch/revision/[path]
--
meta        print the target's metadata entry (decoded then reencoded) to stdout
bupm        print the target directory's .bupm file directly to stdout
"""

handle_ctrl_c()

o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

git.check_repo_or_die()
top = vfs.RefList(None)

if not extra:
    o.fatal('must specify a target')
if len(extra) > 1:
    o.fatal('only one target file allowed')
if opt.bupm and opt.meta:
    o.fatal('--meta and --bupm are incompatible')
    
target = extra[0]

if not re.match(r'/*[^/]+/[^/]+', target):
    o.fatal("path %r doesn't include a branch and revision" % target)

try:
    n = top.lresolve(target)
except vfs.NodeError, e:
    o.fatal(e)

if isinstance(n, vfs.FakeSymlink):
    # Source is actually /foo/what, i.e. a top-level commit
    # like /foo/latest, which is a symlink to ../.commit/SHA.
    # So dereference it.
    target = n.dereference()

if opt.bupm:
    if not stat.S_ISDIR(n.mode):
        o.fatal('%r is not a directory' % target)
    mfile = n.metadata_file() # VFS file -- cannot close().
    if mfile:
        meta_stream = mfile.open()
        sys.stdout.write(meta_stream.read())
elif opt.meta:
    sys.stdout.write(n.metadata().encode())
else:
    if stat.S_ISREG(n.mode):
        for b in chunkyreader(n.open()):
            sys.stdout.write(b)
    else:
        o.fatal('%r is not a plain file' % target)

if saved_errors:
    log('warning: %d errors encountered\n' % len(saved_errors))
    sys.exit(1)

########NEW FILE########
__FILENAME__ = daemon-cmd
#!/usr/bin/env python
import sys, getopt, socket, subprocess, fcntl
from bup import options, path
from bup.helpers import *

optspec = """
bup daemon [options...] -- [bup-server options...]
--
l,listen  ip address to listen on, defaults to *
p,port    port to listen on, defaults to 1982
"""
o = options.Options(optspec, optfunc=getopt.getopt)
(opt, flags, extra) = o.parse(sys.argv[1:])

host = opt.listen
port = opt.port and int(opt.port) or 1982

import socket
import sys

socks = []
e = None
for res in socket.getaddrinfo(host, port, socket.AF_UNSPEC,
                              socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
    af, socktype, proto, canonname, sa = res
    try:
        s = socket.socket(af, socktype, proto)
    except socket.error, e:
        continue
    try:
        if af == socket.AF_INET6:
            log("bup daemon: listening on [%s]:%s\n" % sa[:2])
        else:
            log("bup daemon: listening on %s:%s\n" % sa[:2])
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(sa)
        s.listen(1)
        fcntl.fcntl(s.fileno(), fcntl.F_SETFD, fcntl.FD_CLOEXEC)
    except socket.error, e:
        s.close()
        continue
    socks.append(s)

if not socks:
    log('bup daemon: listen socket: %s\n' % e.args[1])
    sys.exit(1)

try:
    while True:
        [rl,wl,xl] = select.select(socks, [], [], 60)
        for l in rl:
            s, src = l.accept()
            try:
                log("Socket accepted connection from %s\n" % (src,))
                fd1 = os.dup(s.fileno())
                fd2 = os.dup(s.fileno())
                s.close()
                sp = subprocess.Popen([path.exe(), 'mux', '--', 'server']
                                      + extra, stdin=fd1, stdout=fd2)
            finally:
                os.close(fd1)
                os.close(fd2)
finally:
    for l in socks:
        l.shutdown(socket.SHUT_RDWR)
        l.close()

debug1("bup daemon: done")

########NEW FILE########
__FILENAME__ = damage-cmd
#!/usr/bin/env python
import sys, os, random
from bup import options
from bup.helpers import *


def randblock(n):
    l = []
    for i in xrange(n):
        l.append(chr(random.randrange(0,256)))
    return ''.join(l)


optspec = """
bup damage [-n count] [-s maxsize] [-S seed] <filenames...>
--
   WARNING: THIS COMMAND IS EXTREMELY DANGEROUS
n,num=   number of blocks to damage
s,size=  maximum size of each damaged block
percent= maximum size of each damaged block (as a percent of entire file)
equal    spread damage evenly throughout the file
S,seed=  random number seed (for repeatable tests)
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

if not extra:
    o.fatal('filenames expected')

if opt.seed != None:
    random.seed(opt.seed)

for name in extra:
    log('Damaging "%s"...\n' % name)
    f = open(name, 'r+b')
    st = os.fstat(f.fileno())
    size = st.st_size
    if opt.percent or opt.size:
        ms1 = int(float(opt.percent or 0)/100.0*size) or size
        ms2 = opt.size or size
        maxsize = min(ms1, ms2)
    else:
        maxsize = 1
    chunks = opt.num or 10
    chunksize = size/chunks
    for r in range(chunks):
        sz = random.randrange(1, maxsize+1)
        if sz > size:
            sz = size
        if opt.equal:
            ofs = r*chunksize
        else:
            ofs = random.randrange(0, size - sz + 1)
        log('  %6d bytes at %d\n' % (sz, ofs))
        f.seek(ofs)
        f.write(randblock(sz))
    f.close()

########NEW FILE########
__FILENAME__ = drecurse-cmd
#!/usr/bin/env python

from os.path import relpath
from bup import options, drecurse
from bup.helpers import *

optspec = """
bup drecurse <path>
--
x,xdev,one-file-system   don't cross filesystem boundaries
exclude= a path to exclude from the backup (can be used more than once)
exclude-from= a file that contains exclude paths (can be used more than once)
exclude-rx= skip paths matching the unanchored regex (may be repeated)
exclude-rx-from= skip --exclude-rx patterns in file (may be repeated)
q,quiet  don't actually print filenames
profile  run under the python profiler
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

if len(extra) != 1:
    o.fatal("exactly one filename expected")

drecurse_top = extra[0]
excluded_paths = parse_excludes(flags, o.fatal)
if not drecurse_top.startswith('/'):
    excluded_paths = [relpath(x) for x in excluded_paths]
exclude_rxs = parse_rx_excludes(flags, o.fatal)
it = drecurse.recursive_dirlist([drecurse_top], opt.xdev,
                                excluded_paths=excluded_paths,
                                exclude_rxs=exclude_rxs)
if opt.profile:
    import cProfile
    def do_it():
        for i in it:
            pass
    cProfile.run('do_it()')
else:
    if opt.quiet:
        for i in it:
            pass
    else:
        for (name,st) in it:
            print name

if saved_errors:
    log('WARNING: %d errors encountered.\n' % len(saved_errors))
    sys.exit(1)

########NEW FILE########
__FILENAME__ = fsck-cmd
#!/usr/bin/env python
import sys, os, glob, subprocess
from bup import options, git
from bup.helpers import *

par2_ok = 0
nullf = open('/dev/null')

def debug(s):
    if opt.verbose > 1:
        log(s)

def run(argv):
    # at least in python 2.5, using "stdout=2" or "stdout=sys.stderr" below
    # doesn't actually work, because subprocess closes fd #2 right before
    # execing for some reason.  So we work around it by duplicating the fd
    # first.
    fd = os.dup(2)  # copy stderr
    try:
        p = subprocess.Popen(argv, stdout=fd, close_fds=False)
        return p.wait()
    finally:
        os.close(fd)

def par2_setup():
    global par2_ok
    rv = 1
    try:
        p = subprocess.Popen(['par2', '--help'],
                             stdout=nullf, stderr=nullf, stdin=nullf)
        rv = p.wait()
    except OSError:
        log('fsck: warning: par2 not found; disabling recovery features.\n')
    else:
        par2_ok = 1

def parv(lvl):
    if opt.verbose >= lvl:
        if istty2:
            return []
        else:
            return ['-q']
    else:
        return ['-qq']

def par2_generate(base):
    return run(['par2', 'create', '-n1', '-c200'] + parv(2)
               + ['--', base, base+'.pack', base+'.idx'])

def par2_verify(base):
    return run(['par2', 'verify'] + parv(3) + ['--', base])

def par2_repair(base):
    return run(['par2', 'repair'] + parv(2) + ['--', base])

def quick_verify(base):
    f = open(base + '.pack', 'rb')
    f.seek(-20, 2)
    wantsum = f.read(20)
    assert(len(wantsum) == 20)
    f.seek(0)
    sum = Sha1()
    for b in chunkyreader(f, os.fstat(f.fileno()).st_size - 20):
        sum.update(b)
    if sum.digest() != wantsum:
        raise ValueError('expected %r, got %r' % (wantsum.encode('hex'),
                                                  sum.hexdigest()))
        

def git_verify(base):
    if opt.quick:
        try:
            quick_verify(base)
        except Exception, e:
            debug('error: %s\n' % e)
            return 1
        return 0
    else:
        return run(['git', 'verify-pack', '--', base])
    
    
def do_pack(base, last, par2_exists):
    code = 0
    if par2_ok and par2_exists and (opt.repair or not opt.generate):
        vresult = par2_verify(base)
        if vresult != 0:
            if opt.repair:
                rresult = par2_repair(base)
                if rresult != 0:
                    action_result = 'failed'
                    log('%s par2 repair: failed (%d)\n' % (last, rresult))
                    code = rresult
                else:
                    action_result = 'repaired'
                    log('%s par2 repair: succeeded (0)\n' % last)
                    code = 100
            else:
                action_result = 'failed'
                log('%s par2 verify: failed (%d)\n' % (last, vresult))
                code = vresult
        else:
            action_result = 'ok'
    elif not opt.generate or (par2_ok and not par2_exists):
        gresult = git_verify(base)
        if gresult != 0:
            action_result = 'failed'
            log('%s git verify: failed (%d)\n' % (last, gresult))
            code = gresult
        else:
            if par2_ok and opt.generate:
                presult = par2_generate(base)
                if presult != 0:
                    action_result = 'failed'
                    log('%s par2 create: failed (%d)\n' % (last, presult))
                    code = presult
                else:
                    action_result = 'generated'
            else:
                action_result = 'ok'
    else:
        assert(opt.generate and (not par2_ok or par2_exists))
        action_result = 'exists' if par2_exists else 'skipped'
    if opt.verbose:
        print last, action_result
    return code


optspec = """
bup fsck [options...] [filenames...]
--
r,repair    attempt to repair errors using par2 (dangerous!)
g,generate  generate auto-repair information using par2
v,verbose   increase verbosity (can be used more than once)
quick       just check pack sha1sum, don't use git verify-pack
j,jobs=     run 'n' jobs in parallel
par2-ok     immediately return 0 if par2 is ok, 1 if not
disable-par2  ignore par2 even if it is available
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

par2_setup()
if opt.par2_ok:
    if par2_ok:
        sys.exit(0)  # 'true' in sh
    else:
        sys.exit(1)
if opt.disable_par2:
    par2_ok = 0

git.check_repo_or_die()

if not extra:
    debug('fsck: No filenames given: checking all packs.\n')
    extra = glob.glob(git.repo('objects/pack/*.pack'))

code = 0
count = 0
outstanding = {}
for name in extra:
    if name.endswith('.pack'):
        base = name[:-5]
    elif name.endswith('.idx'):
        base = name[:-4]
    elif name.endswith('.par2'):
        base = name[:-5]
    elif os.path.exists(name + '.pack'):
        base = name
    else:
        raise Exception('%s is not a pack file!' % name)
    (dir,last) = os.path.split(base)
    par2_exists = os.path.exists(base + '.par2')
    if par2_exists and os.stat(base + '.par2').st_size == 0:
        par2_exists = 0
    sys.stdout.flush()
    debug('fsck: checking %s (%s)\n' 
          % (last, par2_ok and par2_exists and 'par2' or 'git'))
    if not opt.verbose:
        progress('fsck (%d/%d)\r' % (count, len(extra)))
    
    if not opt.jobs:
        nc = do_pack(base, last, par2_exists)
        code = code or nc
        count += 1
    else:
        while len(outstanding) >= opt.jobs:
            (pid,nc) = os.wait()
            nc >>= 8
            if pid in outstanding:
                del outstanding[pid]
                code = code or nc
                count += 1
        pid = os.fork()
        if pid:  # parent
            outstanding[pid] = 1
        else: # child
            try:
                sys.exit(do_pack(base, last, par2_exists))
            except Exception, e:
                log('exception: %r\n' % e)
                sys.exit(99)
                
while len(outstanding):
    (pid,nc) = os.wait()
    nc >>= 8
    if pid in outstanding:
        del outstanding[pid]
        code = code or nc
        count += 1
    if not opt.verbose:
        progress('fsck (%d/%d)\r' % (count, len(extra)))

if istty2:
    debug('fsck done.           \n')
sys.exit(code)

########NEW FILE########
__FILENAME__ = ftp-cmd
#!/usr/bin/env python
import sys, os, stat, fnmatch
from bup import options, git, shquote, vfs, ls
from bup.helpers import *

handle_ctrl_c()


class OptionError(Exception):
    pass


# Check out lib/bup/ls.py for the opt spec
def do_ls(cmd_args):
    try:
        ls.do_ls(cmd_args, pwd, onabort=OptionError)
    except OptionError, e:
        return


def write_to_file(inf, outf):
    for blob in chunkyreader(inf):
        outf.write(blob)


def inputiter():
    if os.isatty(sys.stdin.fileno()):
        while 1:
            try:
                yield raw_input('bup> ')
            except EOFError:
                print ''  # Clear the line for the terminal's next prompt
                break
    else:
        for line in sys.stdin:
            yield line


def _completer_get_subs(line):
    (qtype, lastword) = shquote.unfinished_word(line)
    (dir,name) = os.path.split(lastword)
    #log('\ncompleter: %r %r %r\n' % (qtype, lastword, text))
    try:
        n = pwd.resolve(dir)
        subs = list(filter(lambda x: x.name.startswith(name),
                           n.subs()))
    except vfs.NoSuchFile, e:
        subs = []
    return (dir, name, qtype, lastword, subs)


def find_readline_lib():
    """Return the name (and possibly the full path) of the readline library
    linked to the given readline module.
    """
    import readline
    f = open(readline.__file__, "rb")
    try:
        data = f.read()
    finally:
        f.close()
    import re
    m = re.search('\0([^\0]*libreadline[^\0]*)\0', data)
    if m:
        return m.group(1)
    return None


def init_readline_vars():
    """Work around trailing space automatically inserted by readline.
    See http://bugs.python.org/issue5833"""
    try:
        import ctypes
    except ImportError:
        # python before 2.5 didn't have the ctypes module; but those
        # old systems probably also didn't have this readline bug, so
        # just ignore it.
        return
    lib_name = find_readline_lib()
    if lib_name is not None:
        lib = ctypes.cdll.LoadLibrary(lib_name)
        global rl_completion_suppress_append
        rl_completion_suppress_append = ctypes.c_int.in_dll(lib,
                                    "rl_completion_suppress_append")


rl_completion_suppress_append = None
_last_line = None
_last_res = None
def completer(text, state):
    global _last_line
    global _last_res
    global rl_completion_suppress_append
    if rl_completion_suppress_append is not None:
        rl_completion_suppress_append.value = 1
    try:
        line = readline.get_line_buffer()[:readline.get_endidx()]
        if _last_line != line:
            _last_res = _completer_get_subs(line)
            _last_line = line
        (dir, name, qtype, lastword, subs) = _last_res
        if state < len(subs):
            sn = subs[state]
            sn1 = sn.try_resolve()  # find the type of any symlink target
            fullname = os.path.join(dir, sn.name)
            if stat.S_ISDIR(sn1.mode):
                ret = shquote.what_to_add(qtype, lastword, fullname+'/',
                                          terminate=False)
            else:
                ret = shquote.what_to_add(qtype, lastword, fullname,
                                          terminate=True) + ' '
            return text + ret
    except Exception, e:
        log('\n')
        try:
            import traceback
            traceback.print_tb(sys.exc_traceback)
        except Exception, e2:
            log('Error printing traceback: %s\n' % e2)
        log('\nError in completion: %s\n' % e)


optspec = """
bup ftp [commands...]
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

git.check_repo_or_die()

top = vfs.RefList(None)
pwd = top
rv = 0

if extra:
    lines = extra
else:
    try:
        import readline
    except ImportError:
        log('* readline module not available: line editing disabled.\n')
        readline = None

    if readline:
        readline.set_completer_delims(' \t\n\r/')
        readline.set_completer(completer)
        if sys.platform.startswith('darwin'):
            # MacOS uses a slighly incompatible clone of libreadline
            readline.parse_and_bind('bind ^I rl_complete')
        readline.parse_and_bind('tab: complete')
        init_readline_vars()
    lines = inputiter()

for line in lines:
    if not line.strip():
        continue
    words = [word for (wordstart,word) in shquote.quotesplit(line)]
    cmd = words[0].lower()
    #log('execute: %r %r\n' % (cmd, parm))
    try:
        if cmd == 'ls':
            do_ls(words[1:])
        elif cmd == 'cd':
            np = pwd
            for parm in words[1:]:
                np = np.resolve(parm)
                if not stat.S_ISDIR(np.mode):
                    raise vfs.NotDir('%s is not a directory' % parm)
            pwd = np
        elif cmd == 'pwd':
            print pwd.fullname()
        elif cmd == 'cat':
            for parm in words[1:]:
                write_to_file(pwd.resolve(parm).open(), sys.stdout)
        elif cmd == 'get':
            if len(words) not in [2,3]:
                rv = 1
                raise Exception('Usage: get <filename> [localname]')
            rname = words[1]
            (dir,base) = os.path.split(rname)
            lname = len(words)>2 and words[2] or base
            inf = pwd.resolve(rname).open()
            log('Saving %r\n' % lname)
            write_to_file(inf, open(lname, 'wb'))
        elif cmd == 'mget':
            for parm in words[1:]:
                (dir,base) = os.path.split(parm)
                for n in pwd.resolve(dir).subs():
                    if fnmatch.fnmatch(n.name, base):
                        try:
                            log('Saving %r\n' % n.name)
                            inf = n.open()
                            outf = open(n.name, 'wb')
                            write_to_file(inf, outf)
                            outf.close()
                        except Exception, e:
                            rv = 1
                            log('  error: %s\n' % e)
        elif cmd == 'help' or cmd == '?':
            log('Commands: ls cd pwd cat get mget help quit\n')
        elif cmd == 'quit' or cmd == 'exit' or cmd == 'bye':
            break
        else:
            rv = 1
            raise Exception('no such command %r' % cmd)
    except Exception, e:
        rv = 1
        log('error: %s\n' % e)
        #raise

sys.exit(rv)

########NEW FILE########
__FILENAME__ = fuse-cmd
#!/usr/bin/env python
import sys, os, errno
from bup import options, git, vfs
from bup.helpers import *
try:
    import fuse
except ImportError:
    log('error: cannot find the python "fuse" module; please install it\n')
    sys.exit(1)


class Stat(fuse.Stat):
    def __init__(self):
        self.st_mode = 0
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = 0
        self.st_gid = 0
        self.st_size = 0
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0
        self.st_blocks = 0
        self.st_blksize = 0
        self.st_rdev = 0


cache = {}
def cache_get(top, path):
    parts = path.split('/')
    cache[('',)] = top
    c = None
    max = len(parts)
    #log('cache: %r\n' % cache.keys())
    for i in range(max):
        pre = parts[:max-i]
        #log('cache trying: %r\n' % pre)
        c = cache.get(tuple(pre))
        if c:
            rest = parts[max-i:]
            for r in rest:
                #log('resolving %r from %r\n' % (r, c.fullname()))
                c = c.lresolve(r)
                key = tuple(pre + [r])
                #log('saving: %r\n' % (key,))
                cache[key] = c
            break
    assert(c)
    return c
        
    

class BupFs(fuse.Fuse):
    def __init__(self, top):
        fuse.Fuse.__init__(self)
        self.top = top
    
    def getattr(self, path):
        log('--getattr(%r)\n' % path)
        try:
            node = cache_get(self.top, path)
            st = Stat()
            st.st_mode = node.mode
            st.st_nlink = node.nlinks()
            st.st_size = node.size()
            st.st_mtime = node.mtime
            st.st_ctime = node.ctime
            st.st_atime = node.atime
            return st
        except vfs.NoSuchFile:
            return -errno.ENOENT

    def readdir(self, path, offset):
        log('--readdir(%r)\n' % path)
        node = cache_get(self.top, path)
        yield fuse.Direntry('.')
        yield fuse.Direntry('..')
        for sub in node.subs():
            yield fuse.Direntry(sub.name)

    def readlink(self, path):
        log('--readlink(%r)\n' % path)
        node = cache_get(self.top, path)
        return node.readlink()

    def open(self, path, flags):
        log('--open(%r)\n' % path)
        node = cache_get(self.top, path)
        accmode = os.O_RDONLY | os.O_WRONLY | os.O_RDWR
        if (flags & accmode) != os.O_RDONLY:
            return -errno.EACCES
        node.open()

    def release(self, path, flags):
        log('--release(%r)\n' % path)

    def read(self, path, size, offset):
        log('--read(%r)\n' % path)
        n = cache_get(self.top, path)
        o = n.open()
        o.seek(offset)
        return o.read(size)


if not hasattr(fuse, '__version__'):
    raise RuntimeError, "your fuse module is too old for fuse.__version__"
fuse.fuse_python_api = (0, 2)


optspec = """
bup fuse [-d] [-f] <mountpoint>
--
d,debug   increase debug level
f,foreground  run in foreground
o,allow-other allow other users to access the filesystem
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

if len(extra) != 1:
    o.fatal("exactly one argument expected")

git.check_repo_or_die()
top = vfs.RefList(None)
f = BupFs(top)
f.fuse_args.mountpoint = extra[0]
if opt.debug:
    f.fuse_args.add('debug')
if opt.foreground:
    f.fuse_args.setmod('foreground')
print f.multithreaded
f.multithreaded = False
if opt.allow_other:
    f.fuse_args.add('allow_other')

f.main()

########NEW FILE########
__FILENAME__ = help-cmd
#!/usr/bin/env python
import sys, os, glob
from bup import options, path

optspec = """
bup help <command>
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

if len(extra) == 0:
    # the wrapper program provides the default usage string
    os.execvp(os.environ['BUP_MAIN_EXE'], ['bup'])
elif len(extra) == 1:
    docname = (extra[0]=='bup' and 'bup' or ('bup-%s' % extra[0]))
    manpath = os.path.join(path.exedir(),
                           'Documentation/' + docname + '.[1-9]')
    g = glob.glob(manpath)
    try:
        if g:
            os.execvp('man', ['man', '-l', g[0]])
        else:
            os.execvp('man', ['man', docname])
    except OSError, e:
        sys.stderr.write('Unable to run man command: %s\n' % e)
        sys.exit(1)
else:
    o.fatal("exactly one command name expected")

########NEW FILE########
__FILENAME__ = index-cmd
#!/usr/bin/env python

import sys, stat, time, os, errno, re
from bup import metadata, options, git, index, drecurse, hlinkdb
from bup.helpers import *
from bup.hashsplit import GIT_MODE_TREE, GIT_MODE_FILE

class IterHelper:
    def __init__(self, l):
        self.i = iter(l)
        self.cur = None
        self.next()

    def next(self):
        try:
            self.cur = self.i.next()
        except StopIteration:
            self.cur = None
        return self.cur


def check_index(reader):
    try:
        log('check: checking forward iteration...\n')
        e = None
        d = {}
        for e in reader.forward_iter():
            if e.children_n:
                if opt.verbose:
                    log('%08x+%-4d %r\n' % (e.children_ofs, e.children_n,
                                            e.name))
                assert(e.children_ofs)
                assert(e.name.endswith('/'))
                assert(not d.get(e.children_ofs))
                d[e.children_ofs] = 1
            if e.flags & index.IX_HASHVALID:
                assert(e.sha != index.EMPTY_SHA)
                assert(e.gitmode)
        assert(not e or e.name == '/')  # last entry is *always* /
        log('check: checking normal iteration...\n')
        last = None
        for e in reader:
            if last:
                assert(last > e.name)
            last = e.name
    except:
        log('index error! at %r\n' % e)
        raise
    log('check: passed.\n')


def clear_index(indexfile):
    indexfiles = [indexfile, indexfile + '.meta', indexfile + '.hlink']
    for indexfile in indexfiles:
        path = git.repo(indexfile)
        try:
            os.remove(path)
            if opt.verbose:
                log('clear: removed %s\n' % path)
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise


def update_index(top, excluded_paths, exclude_rxs):
    # tmax and start must be epoch nanoseconds.
    tmax = (time.time() - 1) * 10**9
    ri = index.Reader(indexfile)
    msw = index.MetaStoreWriter(indexfile + '.meta')
    wi = index.Writer(indexfile, msw, tmax)
    rig = IterHelper(ri.iter(name=top))
    tstart = int(time.time()) * 10**9

    hlinks = hlinkdb.HLinkDB(indexfile + '.hlink')

    hashgen = None
    if opt.fake_valid:
        def hashgen(name):
            return (GIT_MODE_FILE, index.FAKE_SHA)

    total = 0
    bup_dir = os.path.abspath(git.repo())
    index_start = time.time()
    for (path,pst) in drecurse.recursive_dirlist([top], xdev=opt.xdev,
                                                 bup_dir=bup_dir,
                                                 excluded_paths=excluded_paths,
                                                 exclude_rxs=exclude_rxs):
        if opt.verbose>=2 or (opt.verbose==1 and stat.S_ISDIR(pst.st_mode)):
            sys.stdout.write('%s\n' % path)
            sys.stdout.flush()
            elapsed = time.time() - index_start
            paths_per_sec = total / elapsed if elapsed else 0
            qprogress('Indexing: %d (%d paths/s)\r' % (total, paths_per_sec))
        elif not (total % 128):
            elapsed = time.time() - index_start
            paths_per_sec = total / elapsed if elapsed else 0
            qprogress('Indexing: %d (%d paths/s)\r' % (total, paths_per_sec))
        total += 1
        while rig.cur and rig.cur.name > path:  # deleted paths
            if rig.cur.exists():
                rig.cur.set_deleted()
                rig.cur.repack()
                if rig.cur.nlink > 1 and not stat.S_ISDIR(rig.cur.mode):
                    hlinks.del_path(rig.cur.name)
            rig.next()
        if rig.cur and rig.cur.name == path:    # paths that already existed
            try:
                meta = metadata.from_path(path, statinfo=pst)
            except (OSError, IOError), e:
                add_error(e)
                rig.next()
                continue
            if not stat.S_ISDIR(rig.cur.mode) and rig.cur.nlink > 1:
                hlinks.del_path(rig.cur.name)
            if not stat.S_ISDIR(pst.st_mode) and pst.st_nlink > 1:
                hlinks.add_path(path, pst.st_dev, pst.st_ino)
            # Clear these so they don't bloat the store -- they're
            # already in the index (since they vary a lot and they're
            # fixed length).  If you've noticed "tmax", you might
            # wonder why it's OK to do this, since that code may
            # adjust (mangle) the index mtime and ctime -- producing
            # fake values which must not end up in a .bupm.  However,
            # it looks like that shouldn't be possible:  (1) When
            # "save" validates the index entry, it always reads the
            # metadata from the filesytem. (2) Metadata is only
            # read/used from the index if hashvalid is true. (3) index
            # always invalidates "faked" entries, because "old != new"
            # in from_stat().
            meta.ctime = meta.mtime = meta.atime = 0
            meta_ofs = msw.store(meta)
            rig.cur.from_stat(pst, meta_ofs, tstart,
                              check_device=opt.check_device)
            if not (rig.cur.flags & index.IX_HASHVALID):
                if hashgen:
                    (rig.cur.gitmode, rig.cur.sha) = hashgen(path)
                    rig.cur.flags |= index.IX_HASHVALID
            if opt.fake_invalid:
                rig.cur.invalidate()
            rig.cur.repack()
            rig.next()
        else:  # new paths
            try:
                meta = metadata.from_path(path, statinfo=pst)
            except (OSError, IOError), e:
                add_error(e)
                continue
            # See same assignment to 0, above, for rationale.
            meta.atime = meta.mtime = meta.ctime = 0
            meta_ofs = msw.store(meta)
            wi.add(path, pst, meta_ofs, hashgen = hashgen)
            if not stat.S_ISDIR(pst.st_mode) and pst.st_nlink > 1:
                hlinks.add_path(path, pst.st_dev, pst.st_ino)

    elapsed = time.time() - index_start
    paths_per_sec = total / elapsed if elapsed else 0
    progress('Indexing: %d, done (%d paths/s).\n' % (total, paths_per_sec))

    hlinks.prepare_save()

    if ri.exists():
        ri.save()
        wi.flush()
        if wi.count:
            wr = wi.new_reader()
            if opt.check:
                log('check: before merging: oldfile\n')
                check_index(ri)
                log('check: before merging: newfile\n')
                check_index(wr)
            mi = index.Writer(indexfile, msw, tmax)

            for e in index.merge(ri, wr):
                # FIXME: shouldn't we remove deleted entries eventually?  When?
                mi.add_ixentry(e)

            ri.close()
            mi.close()
            wr.close()
        wi.abort()
    else:
        wi.close()

    msw.close()
    hlinks.commit_save()


optspec = """
bup index <-p|m|s|u> [options...] <filenames...>
--
 Modes:
p,print    print the index entries for the given names (also works with -u)
m,modified print only added/deleted/modified files (implies -p)
s,status   print each filename with a status char (A/M/D) (implies -p)
u,update   recursively update the index entries for the given file/dir names (default if no mode is specified)
check      carefully check index file integrity
clear      clear the default index
 Options:
H,hash     print the hash for each object next to its name
l,long     print more information about each file
no-check-device don't invalidate an entry if the containing device changes
fake-valid mark all index entries as up-to-date even if they aren't
fake-invalid mark all index entries as invalid
f,indexfile=  the name of the index file (normally BUP_DIR/bupindex)
exclude= a path to exclude from the backup (may be repeated)
exclude-from= skip --exclude paths in file (may be repeated)
exclude-rx= skip paths matching the unanchored regex (may be repeated)
exclude-rx-from= skip --exclude-rx patterns in file (may be repeated)
v,verbose  increase log output (can be used more than once)
x,xdev,one-file-system  don't cross filesystem boundaries
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

if not (opt.modified or \
        opt['print'] or \
        opt.status or \
        opt.update or \
        opt.check or \
        opt.clear):
    opt.update = 1
if (opt.fake_valid or opt.fake_invalid) and not opt.update:
    o.fatal('--fake-{in,}valid are meaningless without -u')
if opt.fake_valid and opt.fake_invalid:
    o.fatal('--fake-valid is incompatible with --fake-invalid')
if opt.clear and opt.indexfile:
    o.fatal('cannot clear an external index (via -f)')

# FIXME: remove this once we account for timestamp races, i.e. index;
# touch new-file; index.  It's possible for this to happen quickly
# enough that new-file ends up with the same timestamp as the first
# index, and then bup will ignore it.
tick_start = time.time()
time.sleep(1 - (tick_start - int(tick_start)))

git.check_repo_or_die()
indexfile = opt.indexfile or git.repo('bupindex')

handle_ctrl_c()

if opt.check:
    log('check: starting initial check.\n')
    check_index(index.Reader(indexfile))

if opt.clear:
    log('clear: clearing index.\n')
    clear_index(indexfile)

excluded_paths = parse_excludes(flags, o.fatal)
exclude_rxs = parse_rx_excludes(flags, o.fatal)
paths = index.reduce_paths(extra)

if opt.update:
    if not extra:
        o.fatal('update mode (-u) requested but no paths given')
    for (rp,path) in paths:
        update_index(rp, excluded_paths, exclude_rxs)

if opt['print'] or opt.status or opt.modified:
    for (name, ent) in index.Reader(indexfile).filter(extra or ['']):
        if (opt.modified 
            and (ent.is_valid() or ent.is_deleted() or not ent.mode)):
            continue
        line = ''
        if opt.status:
            if ent.is_deleted():
                line += 'D '
            elif not ent.is_valid():
                if ent.sha == index.EMPTY_SHA:
                    line += 'A '
                else:
                    line += 'M '
            else:
                line += '  '
        if opt.hash:
            line += ent.sha.encode('hex') + ' '
        if opt.long:
            line += "%7s %7s " % (oct(ent.mode), oct(ent.gitmode))
        print line + (name or './')

if opt.check and (opt['print'] or opt.status or opt.modified or opt.update):
    log('check: starting final check.\n')
    check_index(index.Reader(indexfile))

if saved_errors:
    log('WARNING: %d errors encountered.\n' % len(saved_errors))
    sys.exit(1)

########NEW FILE########
__FILENAME__ = init-cmd
#!/usr/bin/env python
import sys

from bup import git, options, client
from bup.helpers import *


optspec = """
[BUP_DIR=...] bup init [-r host:path]
--
r,remote=  remote repository path
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

if extra:
    o.fatal("no arguments expected")


try:
    git.init_repo()  # local repo
except git.GitError, e:
    log("bup: error: could not init repository: %s" % e)
    sys.exit(1)

if opt.remote:
    git.check_repo_or_die()
    cli = client.Client(opt.remote, create=True)
    cli.close()

########NEW FILE########
__FILENAME__ = join-cmd
#!/usr/bin/env python
import sys
from bup import git, options, client
from bup.helpers import *


optspec = """
bup join [-r host:path] [refs or hashes...]
--
r,remote=  remote repository path
o=         output filename
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

git.check_repo_or_die()

if not extra:
    extra = linereader(sys.stdin)

ret = 0

if opt.remote:
    cli = client.Client(opt.remote)
    cat = cli.cat
else:
    cp = git.CatPipe()
    cat = cp.join

if opt.o:
    outfile = open(opt.o, 'wb')
else:
    outfile = sys.stdout

for id in extra:
    try:
        for blob in cat(id):
            outfile.write(blob)
    except KeyError, e:
        outfile.flush()
        log('error: %s\n' % e)
        ret = 1

sys.exit(ret)

########NEW FILE########
__FILENAME__ = list-idx-cmd
#!/usr/bin/env python
import sys, os
from bup import git, options
from bup.helpers import *

optspec = """
bup list-idx [--find=<prefix>] <idxfilenames...>
--
find=   display only objects that start with <prefix>
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

handle_ctrl_c()
opt.find = opt.find or ''

if not extra:
    o.fatal('you must provide at least one filename')

if len(opt.find) > 40:
    o.fatal('--find parameter must be <= 40 chars long')
else:
    if len(opt.find) % 2:
        s = opt.find + '0'
    else:
        s = opt.find
    try:
        bin = s.decode('hex')
    except TypeError:
        o.fatal('--find parameter is not a valid hex string')

find = opt.find.lower()

count = 0
for name in extra:
    try:
        ix = git.open_idx(name)
    except git.GitError, e:
        add_error('%s: %s' % (name, e))
        continue
    if len(opt.find) == 40:
        if ix.exists(bin):
            print name, find
    else:
        # slow, exhaustive search
        for _i in ix:
            i = str(_i).encode('hex')
            if i.startswith(find):
                print name, i
            qprogress('Searching: %d\r' % count)
            count += 1

if saved_errors:
    log('WARNING: %d errors encountered while saving.\n' % len(saved_errors))
    sys.exit(1)

########NEW FILE########
__FILENAME__ = ls-cmd
#!/usr/bin/env python
import sys
from bup import git, vfs, ls
from bup.helpers import *


git.check_repo_or_die()
top = vfs.RefList(None)

# Check out lib/bup/ls.py for the opt spec
ret = ls.do_ls(sys.argv[1:], top, default='/', spec_prefix='bup ')
sys.exit(ret)

########NEW FILE########
__FILENAME__ = margin-cmd
#!/usr/bin/env python
import sys, struct, math
from bup import options, git, _helpers
from bup.helpers import *

POPULATION_OF_EARTH=6.7e9  # as of September, 2010

optspec = """
bup margin
--
predict    Guess object offsets and report the maximum deviation
ignore-midx  Don't use midx files; use only plain pack idx files.
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

if extra:
    o.fatal("no arguments expected")

git.check_repo_or_die()
git.ignore_midx = opt.ignore_midx

mi = git.PackIdxList(git.repo('objects/pack'))

def do_predict(ix):
    total = len(ix)
    maxdiff = 0
    for count,i in enumerate(ix):
        prefix = struct.unpack('!Q', i[:8])[0]
        expected = prefix * total / (1<<64)
        diff = count - expected
        maxdiff = max(maxdiff, abs(diff))
    print '%d of %d (%.3f%%) ' % (maxdiff, len(ix), maxdiff*100.0/len(ix))
    sys.stdout.flush()
    assert(count+1 == len(ix))

if opt.predict:
    if opt.ignore_midx:
        for pack in mi.packs:
            do_predict(pack)
    else:
        do_predict(mi)
else:
    # default mode: find longest matching prefix
    last = '\0'*20
    longmatch = 0
    for i in mi:
        if i == last:
            continue
        #assert(str(i) >= last)
        pm = _helpers.bitmatch(last, i)
        longmatch = max(longmatch, pm)
        last = i
    print longmatch
    log('%d matching prefix bits\n' % longmatch)
    doublings = math.log(len(mi), 2)
    bpd = longmatch / doublings
    log('%.2f bits per doubling\n' % bpd)
    remain = 160 - longmatch
    rdoublings = remain / bpd
    log('%d bits (%.2f doublings) remaining\n' % (remain, rdoublings))
    larger = 2**rdoublings
    log('%g times larger is possible\n' % larger)
    perperson = larger/POPULATION_OF_EARTH
    log('\nEveryone on earth could have %d data sets like yours, all in one\n'
        'repository, and we would expect 1 object collision.\n'
        % int(perperson))

########NEW FILE########
__FILENAME__ = memtest-cmd
#!/usr/bin/env python
import sys, re, struct, time, resource
from bup import git, bloom, midx, options, _helpers
from bup.helpers import *

handle_ctrl_c()

_linux_warned = 0
def linux_memstat():
    global _linux_warned
    #fields = ['VmSize', 'VmRSS', 'VmData', 'VmStk', 'ms']
    d = {}
    try:
        f = open('/proc/self/status')
    except IOError, e:
        if not _linux_warned:
            log('Warning: %s\n' % e)
            _linux_warned = 1
        return {}
    for line in f:
        # Note that on Solaris, this file exists but is binary.  If that
        # happens, this split() might not return two elements.  We don't
        # really need to care about the binary format since this output
        # isn't used for much and report() can deal with missing entries.
        t = re.split(r':\s*', line.strip(), 1)
        if len(t) == 2:
            k,v = t
            d[k] = v
    return d


last = last_u = last_s = start = 0
def report(count):
    global last, last_u, last_s, start
    headers = ['RSS', 'MajFlt', 'user', 'sys', 'ms']
    ru = resource.getrusage(resource.RUSAGE_SELF)
    now = time.time()
    rss = int(ru.ru_maxrss/1024)
    if not rss:
        rss = linux_memstat().get('VmRSS', '??')
    fields = [rss,
              ru.ru_majflt,
              int((ru.ru_utime - last_u) * 1000),
              int((ru.ru_stime - last_s) * 1000),
              int((now - last) * 1000)]
    fmt = '%9s  ' + ('%10s ' * len(fields))
    if count >= 0:
        print fmt % tuple([count] + fields)
    else:
        start = now
        print fmt % tuple([''] + headers)
    sys.stdout.flush()
    
    # don't include time to run report() in usage counts
    ru = resource.getrusage(resource.RUSAGE_SELF)
    last_u = ru.ru_utime
    last_s = ru.ru_stime
    last = time.time()


optspec = """
bup memtest [-n elements] [-c cycles]
--
n,number=  number of objects per cycle [10000]
c,cycles=  number of cycles to run [100]
ignore-midx  ignore .midx files, use only .idx files
existing   test with existing objects instead of fake ones
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

if extra:
    o.fatal('no arguments expected')

git.ignore_midx = opt.ignore_midx

git.check_repo_or_die()
m = git.PackIdxList(git.repo('objects/pack'))

report(-1)
_helpers.random_sha()
report(0)

if opt.existing:
    def foreverit(mi):
        while 1:
            for e in mi:
                yield e
    objit = iter(foreverit(m))
    
for c in xrange(opt.cycles):
    for n in xrange(opt.number):
        if opt.existing:
            bin = objit.next()
            assert(m.exists(bin))
        else:
            bin = _helpers.random_sha()

            # technically, a randomly generated object id might exist.
            # but the likelihood of that is the likelihood of finding
            # a collision in sha-1 by accident, which is so unlikely that
            # we don't care.
            assert(not m.exists(bin))
    report((c+1)*opt.number)

if bloom._total_searches:
    print ('bloom: %d objects searched in %d steps: avg %.3f steps/object' 
           % (bloom._total_searches, bloom._total_steps,
              bloom._total_steps*1.0/bloom._total_searches))
if midx._total_searches:
    print ('midx: %d objects searched in %d steps: avg %.3f steps/object' 
           % (midx._total_searches, midx._total_steps,
              midx._total_steps*1.0/midx._total_searches))
if git._total_searches:
    print ('idx: %d objects searched in %d steps: avg %.3f steps/object' 
           % (git._total_searches, git._total_steps,
              git._total_steps*1.0/git._total_searches))
print 'Total time: %.3fs' % (time.time() - start)

########NEW FILE########
__FILENAME__ = meta-cmd
#!/usr/bin/env python

# Copyright (C) 2010 Rob Browning
#
# This code is covered under the terms of the GNU Library General
# Public License as described in the bup LICENSE file.

# TODO: Add tar-like -C option.

import sys
from bup import metadata
from bup import options
from bup.helpers import handle_ctrl_c, log, saved_errors


def open_input(name):
    if not name or name == '-':
        return sys.stdin
    return open(name, 'r')


def open_output(name):
    if not name or name == '-':
        return sys.stdout
    return open(name, 'w')


optspec = """
bup meta --create [OPTION ...] <PATH ...>
bup meta --list [OPTION ...]
bup meta --extract [OPTION ...]
bup meta --start-extract [OPTION ...]
bup meta --finish-extract [OPTION ...]
bup meta --edit [OPTION ...] <PATH ...>
--
c,create       write metadata for PATHs to stdout (or --file)
t,list         display metadata
x,extract      perform --start-extract followed by --finish-extract
start-extract  build tree matching metadata provided on standard input (or --file)
finish-extract finish applying standard input (or --file) metadata to filesystem
edit           alter metadata; write to stdout (or --file)
f,file=        specify source or destination file
R,recurse      recurse into subdirectories
xdev,one-file-system  don't cross filesystem boundaries
numeric-ids    apply numeric IDs (user, group, etc.) rather than names
symlinks       handle symbolic links (default is true)
paths          include paths in metadata (default is true)
set-uid=       set metadata uid (via --edit)
set-gid=       set metadata gid (via --edit)
set-user=      set metadata user (via --edit)
unset-user     remove metadata user (via --edit)
set-group=     set metadata group (via --edit)
unset-group    remove metadata group (via --edit)
v,verbose      increase log output (can be used more than once)
q,quiet        don't show progress meter
"""

handle_ctrl_c()

o = options.Options(optspec)
(opt, flags, remainder) = o.parse(['--paths', '--symlinks', '--recurse']
                                  + sys.argv[1:])

opt.verbose = opt.verbose or 0
opt.quiet = opt.quiet or 0
metadata.verbose = opt.verbose - opt.quiet

action_count = sum([bool(x) for x in [opt.create, opt.list, opt.extract,
                                      opt.start_extract, opt.finish_extract,
                                      opt.edit]])
if action_count > 1:
    o.fatal("bup: only one action permitted: --create --list --extract --edit")
if action_count == 0:
    o.fatal("bup: no action specified")

if opt.create:
    if len(remainder) < 1:
        o.fatal("no paths specified for create")
    output_file = open_output(opt.file)
    metadata.save_tree(output_file,
                       remainder,
                       recurse=opt.recurse,
                       write_paths=opt.paths,
                       save_symlinks=opt.symlinks,
                       xdev=opt.xdev)
elif opt.list:
    if len(remainder) > 0:
        o.fatal("cannot specify paths for --list")
    src = open_input(opt.file)
    metadata.display_archive(src)
elif opt.start_extract:
    if len(remainder) > 0:
        o.fatal("cannot specify paths for --start-extract")
    src = open_input(opt.file)
    metadata.start_extract(src, create_symlinks=opt.symlinks)
elif opt.finish_extract:
    if len(remainder) > 0:
        o.fatal("cannot specify paths for --finish-extract")
    src = open_input(opt.file)
    metadata.finish_extract(src, restore_numeric_ids=opt.numeric_ids)
elif opt.extract:
    if len(remainder) > 0:
        o.fatal("cannot specify paths for --extract")
    src = open_input(opt.file)
    metadata.extract(src,
                     restore_numeric_ids=opt.numeric_ids,
                     create_symlinks=opt.symlinks)
elif opt.edit:
    if len(remainder) < 1:
        o.fatal("no paths specified for edit")
    output_file = open_output(opt.file)

    unset_user = False # True if --unset-user was the last relevant option.
    unset_group = False # True if --unset-group was the last relevant option.
    for flag in flags:
        if flag[0] == '--set-user':
            unset_user = False
        elif flag[0] == '--unset-user':
            unset_user = True
        elif flag[0] == '--set-group':
            unset_group = False
        elif flag[0] == '--unset-group':
            unset_group = True

    for path in remainder:
        f = open(path, 'r')
        try:
            for m in metadata._ArchiveIterator(f):
                if opt.set_uid is not None:
                    try:
                        m.uid = int(opt.set_uid)
                    except ValueError:
                        o.fatal("uid must be an integer")

                if opt.set_gid is not None:
                    try:
                        m.gid = int(opt.set_gid)
                    except ValueError:
                        o.fatal("gid must be an integer")

                if unset_user:
                    m.user = ''
                elif opt.set_user is not None:
                    m.user = opt.set_user

                if unset_group:
                    m.group = ''
                elif opt.set_group is not None:
                    m.group = opt.set_group

                m.write(output_file)
        finally:
            f.close()


if saved_errors:
    log('WARNING: %d errors encountered.\n' % len(saved_errors))
    sys.exit(1)
else:
    sys.exit(0)

########NEW FILE########
__FILENAME__ = midx-cmd
#!/usr/bin/env python
import sys, math, struct, glob, resource
import tempfile
from bup import options, git, midx, _helpers, xstat
from bup.helpers import *

PAGE_SIZE=4096
SHA_PER_PAGE=PAGE_SIZE/20.

optspec = """
bup midx [options...] <idxnames...>
--
o,output=  output midx filename (default: auto-generated)
a,auto     automatically use all existing .midx/.idx files as input
f,force    merge produce exactly one .midx containing all objects
p,print    print names of generated midx files
check      validate contents of the given midx files (with -a, all midx files)
max-files= maximum number of idx files to open at once [-1]
d,dir=     directory containing idx/midx files
"""

merge_into = _helpers.merge_into


def _group(l, count):
    for i in xrange(0, len(l), count):
        yield l[i:i+count]
        
        
def max_files():
    mf = min(resource.getrlimit(resource.RLIMIT_NOFILE))
    if mf > 32:
        mf -= 20  # just a safety margin
    else:
        mf -= 6   # minimum safety margin
    return mf


def check_midx(name):
    nicename = git.repo_rel(name)
    log('Checking %s.\n' % nicename)
    try:
        ix = git.open_idx(name)
    except git.GitError, e:
        add_error('%s: %s' % (name, e))
        return
    for count,subname in enumerate(ix.idxnames):
        sub = git.open_idx(os.path.join(os.path.dirname(name), subname))
        for ecount,e in enumerate(sub):
            if not (ecount % 1234):
                qprogress('  %d/%d: %s %d/%d\r' 
                          % (count, len(ix.idxnames),
                             git.shorten_hash(subname), ecount, len(sub)))
            if not sub.exists(e):
                add_error("%s: %s: %s missing from idx"
                          % (nicename, git.shorten_hash(subname),
                             str(e).encode('hex')))
            if not ix.exists(e):
                add_error("%s: %s: %s missing from midx"
                          % (nicename, git.shorten_hash(subname),
                             str(e).encode('hex')))
    prev = None
    for ecount,e in enumerate(ix):
        if not (ecount % 1234):
            qprogress('  Ordering: %d/%d\r' % (ecount, len(ix)))
        if not e >= prev:
            add_error('%s: ordering error: %s < %s'
                      % (nicename,
                         str(e).encode('hex'), str(prev).encode('hex')))
        prev = e


_first = None
def _do_midx(outdir, outfilename, infilenames, prefixstr):
    global _first
    if not outfilename:
        assert(outdir)
        sum = Sha1('\0'.join(infilenames)).hexdigest()
        outfilename = '%s/midx-%s.midx' % (outdir, sum)
    
    inp = []
    total = 0
    allfilenames = []
    midxs = []
    try:
        for name in infilenames:
            ix = git.open_idx(name)
            midxs.append(ix)
            inp.append((
                ix.map,
                len(ix),
                ix.sha_ofs,
                isinstance(ix, midx.PackMidx) and ix.which_ofs or 0,
                len(allfilenames),
            ))
            for n in ix.idxnames:
                allfilenames.append(os.path.basename(n))
            total += len(ix)
        inp.sort(lambda x,y: cmp(str(y[0][y[2]:y[2]+20]),str(x[0][x[2]:x[2]+20])))

        if not _first: _first = outdir
        dirprefix = (_first != outdir) and git.repo_rel(outdir)+': ' or ''
        debug1('midx: %s%screating from %d files (%d objects).\n'
               % (dirprefix, prefixstr, len(infilenames), total))
        if (opt.auto and (total < 1024 and len(infilenames) < 3)) \
           or ((opt.auto or opt.force) and len(infilenames) < 2) \
           or (opt.force and not total):
            debug1('midx: nothing to do.\n')
            return

        pages = int(total/SHA_PER_PAGE) or 1
        bits = int(math.ceil(math.log(pages, 2)))
        entries = 2**bits
        debug1('midx: table size: %d (%d bits)\n' % (entries*4, bits))

        unlink(outfilename)
        f = open(outfilename + '.tmp', 'w+b')
        f.write('MIDX')
        f.write(struct.pack('!II', midx.MIDX_VERSION, bits))
        assert(f.tell() == 12)

        f.truncate(12 + 4*entries + 20*total + 4*total)
        f.flush()
        fdatasync(f.fileno())

        fmap = mmap_readwrite(f, close=False)

        count = merge_into(fmap, bits, total, inp)
        del fmap # Assume this calls msync() now.
    finally:
        for ix in midxs:
            if isinstance(ix, midx.PackMidx):
                ix.close()
        midxs = None
        inp = None

    f.seek(0, os.SEEK_END)
    f.write('\0'.join(allfilenames))
    f.close()
    os.rename(outfilename + '.tmp', outfilename)

    # This is just for testing (if you enable this, don't clear inp above)
    if 0:
        p = midx.PackMidx(outfilename)
        assert(len(p.idxnames) == len(infilenames))
        print p.idxnames
        assert(len(p) == total)
        for pe, e in p, git.idxmerge(inp, final_progress=False):
            pin = pi.next()
            assert(i == pin)
            assert(p.exists(i))

    return total, outfilename


def do_midx(outdir, outfilename, infilenames, prefixstr):
    rv = _do_midx(outdir, outfilename, infilenames, prefixstr)
    if rv and opt['print']:
        print rv[1]


def do_midx_dir(path):
    already = {}
    sizes = {}
    if opt.force and not opt.auto:
        midxs = []   # don't use existing midx files
    else:
        midxs = glob.glob('%s/*.midx' % path)
        contents = {}
        for mname in midxs:
            m = git.open_idx(mname)
            contents[mname] = [('%s/%s' % (path,i)) for i in m.idxnames]
            sizes[mname] = len(m)
                    
        # sort the biggest+newest midxes first, so that we can eliminate
        # smaller (or older) redundant ones that come later in the list
        midxs.sort(key=lambda ix: (-sizes[ix], -xstat.stat(ix).st_mtime))
        
        for mname in midxs:
            any = 0
            for iname in contents[mname]:
                if not already.get(iname):
                    already[iname] = 1
                    any = 1
            if not any:
                debug1('%r is redundant\n' % mname)
                unlink(mname)
                already[mname] = 1

    midxs = [k for k in midxs if not already.get(k)]
    idxs = [k for k in glob.glob('%s/*.idx' % path) if not already.get(k)]

    for iname in idxs:
        i = git.open_idx(iname)
        sizes[iname] = len(i)

    all = [(sizes[n],n) for n in (midxs + idxs)]
    
    # FIXME: what are the optimal values?  Does this make sense?
    DESIRED_HWM = opt.force and 1 or 5
    DESIRED_LWM = opt.force and 1 or 2
    existed = dict((name,1) for sz,name in all)
    debug1('midx: %d indexes; want no more than %d.\n' 
           % (len(all), DESIRED_HWM))
    if len(all) <= DESIRED_HWM:
        debug1('midx: nothing to do.\n')
    while len(all) > DESIRED_HWM:
        all.sort()
        part1 = [name for sz,name in all[:len(all)-DESIRED_LWM+1]]
        part2 = all[len(all)-DESIRED_LWM+1:]
        all = list(do_midx_group(path, part1)) + part2
        if len(all) > DESIRED_HWM:
            debug1('\nStill too many indexes (%d > %d).  Merging again.\n'
                   % (len(all), DESIRED_HWM))

    if opt['print']:
        for sz,name in all:
            if not existed.get(name):
                print name


def do_midx_group(outdir, infiles):
    groups = list(_group(infiles, opt.max_files))
    gprefix = ''
    for n,sublist in enumerate(groups):
        if len(groups) != 1:
            gprefix = 'Group %d: ' % (n+1)
        rv = _do_midx(path, None, sublist, gprefix)
        if rv:
            yield rv


handle_ctrl_c()

o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

if extra and (opt.auto or opt.force):
    o.fatal("you can't use -f/-a and also provide filenames")
if opt.check and (not extra and not opt.auto):
    o.fatal("if using --check, you must provide filenames or -a")

git.check_repo_or_die()

if opt.max_files < 0:
    opt.max_files = max_files()
assert(opt.max_files >= 5)

if opt.check:
    # check existing midx files
    if extra:
        midxes = extra
    else:
        midxes = []
        paths = opt.dir and [opt.dir] or git.all_packdirs()
        for path in paths:
            debug1('midx: scanning %s\n' % path)
            midxes += glob.glob(os.path.join(path, '*.midx'))
    for name in midxes:
        check_midx(name)
    if not saved_errors:
        log('All tests passed.\n')
else:
    if extra:
        do_midx(git.repo('objects/pack'), opt.output, extra, '')
    elif opt.auto or opt.force:
        paths = opt.dir and [opt.dir] or git.all_packdirs()
        for path in paths:
            debug1('midx: scanning %s\n' % path)
            do_midx_dir(path)
    else:
        o.fatal("you must use -f or -a or provide input filenames")

if saved_errors:
    log('WARNING: %d errors encountered.\n' % len(saved_errors))
    sys.exit(1)

########NEW FILE########
__FILENAME__ = mux-cmd
#!/usr/bin/env python
import os, sys, subprocess, struct
from bup import options
from bup.helpers import *

optspec = """
bup mux command [command arguments...]
--
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])
if len(extra) < 1:
    o.fatal('command is required')

cmdpath, cmdfn = os.path.split(__file__)
subcmd = extra
subcmd[0] = os.path.join(cmdpath, 'bup-' + subcmd[0])

debug2('bup mux: starting %r\n' % (extra,))

outr, outw = os.pipe()
errr, errw = os.pipe()
def close_fds():
    os.close(outr)
    os.close(errr)
p = subprocess.Popen(subcmd, stdout=outw, stderr=errw, preexec_fn=close_fds)
os.close(outw)
os.close(errw)
sys.stdout.write('BUPMUX')
sys.stdout.flush()
mux(p, sys.stdout.fileno(), outr, errr)
os.close(outr)
os.close(errr)
prv = p.wait()

if prv:
    debug1('%s exited with code %d\n' % (extra[0], prv))

debug1('bup mux: done\n')

sys.exit(prv)

########NEW FILE########
__FILENAME__ = newliner-cmd
#!/usr/bin/env python
import sys, os, re
from bup import options
from bup import _helpers   # fixes up sys.argv on import

optspec = """
bup newliner
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

if extra:
    o.fatal("no arguments expected")

r = re.compile(r'([\r\n])')
lastlen = 0
all = ''
width = options._tty_width() or 78
while 1:
    l = r.split(all, 1)
    if len(l) <= 1:
        if len(all) >= 160:
            sys.stdout.write('%s\n' % all[:78])
            sys.stdout.flush()
            all = all[78:]
        try:
            b = os.read(sys.stdin.fileno(), 4096)
        except KeyboardInterrupt:
            break
        if not b:
            break
        all += b
    else:
        assert(len(l) == 3)
        (line, splitchar, all) = l
        if splitchar == '\r':
            line = line[:width]
        sys.stdout.write('%-*s%s' % (lastlen, line, splitchar))
        if splitchar == '\r':
            lastlen = len(line)
        else:
            lastlen = 0
        sys.stdout.flush()

if lastlen:
    sys.stdout.write('%-*s\r' % (lastlen, ''))
if all:
    sys.stdout.write('%s\n' % all)

########NEW FILE########
__FILENAME__ = on--server-cmd
#!/usr/bin/env python
import sys, os, struct
from bup import options, helpers

optspec = """
bup on--server
--
    This command is run automatically by 'bup on'
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])
if extra:
    o.fatal('no arguments expected')

# get the subcommand's argv.
# Normally we could just pass this on the command line, but since we'll often
# be getting called on the other end of an ssh pipe, which tends to mangle
# argv (by sending it via the shell), this way is much safer.
buf = sys.stdin.read(4)
sz = struct.unpack('!I', buf)[0]
assert(sz > 0)
assert(sz < 1000000)
buf = sys.stdin.read(sz)
assert(len(buf) == sz)
argv = buf.split('\0')

# stdin/stdout are supposedly connected to 'bup server' that the caller
# started for us (often on the other end of an ssh tunnel), so we don't want
# to misuse them.  Move them out of the way, then replace stdout with
# a pointer to stderr in case our subcommand wants to do something with it.
#
# It might be nice to do the same with stdin, but my experiments showed that
# ssh seems to make its child's stderr a readable-but-never-reads-anything
# socket.  They really should have used shutdown(SHUT_WR) on the other end
# of it, but probably didn't.  Anyway, it's too messy, so let's just make sure
# anyone reading from stdin is disappointed.
#
# (You can't just leave stdin/stdout "not open" by closing the file
# descriptors.  Then the next file that opens is automatically assigned 0 or 1,
# and people *trying* to read/write stdin/stdout get screwed.)
os.dup2(0, 3)
os.dup2(1, 4)
os.dup2(2, 1)
fd = os.open('/dev/null', os.O_RDONLY)
os.dup2(fd, 0)
os.close(fd)

os.environ['BUP_SERVER_REVERSE'] = helpers.hostname()
os.execvp(argv[0], argv)
sys.exit(99)

########NEW FILE########
__FILENAME__ = on-cmd
#!/usr/bin/env python
import sys, os, struct, getopt, subprocess, signal
from bup import options, ssh, path
from bup.helpers import *

optspec = """
bup on <hostname> index ...
bup on <hostname> save ...
bup on <hostname> split ...
"""
o = options.Options(optspec, optfunc=getopt.getopt)
(opt, flags, extra) = o.parse(sys.argv[1:])
if len(extra) < 2:
    o.fatal('arguments expected')

class SigException(Exception):
    def __init__(self, signum):
        self.signum = signum
        Exception.__init__(self, 'signal %d received' % signum)
def handler(signum, frame):
    raise SigException(signum)

signal.signal(signal.SIGTERM, handler)
signal.signal(signal.SIGINT, handler)

sp = None
p = None
ret = 99

try:
    hp = extra[0].split(':')
    if len(hp) == 1:
        (hostname, port) = (hp[0], None)
    else:
        (hostname, port) = hp

    argv = extra[1:]
    p = ssh.connect(hostname, port, 'on--server')

    argvs = '\0'.join(['bup'] + argv)
    p.stdin.write(struct.pack('!I', len(argvs)) + argvs)
    p.stdin.flush()

    sp = subprocess.Popen([path.exe(), 'server'],
                          stdin=p.stdout, stdout=p.stdin)
    p.stdin.close()
    p.stdout.close()

finally:
    while 1:
        # if we get a signal while waiting, we have to keep waiting, just
        # in case our child doesn't die.
        try:
            ret = p.wait()
            sp.wait()
            break
        except SigException, e:
            log('\nbup on: %s\n' % e)
            os.kill(p.pid, e.signum)
            ret = 84
sys.exit(ret)

########NEW FILE########
__FILENAME__ = random-cmd
#!/usr/bin/env python
import sys
from bup import options, _helpers
from bup.helpers import *

optspec = """
bup random [-S seed] <numbytes>
--
S,seed=   optional random number seed [1]
f,force   print random data to stdout even if it's a tty
v,verbose print byte counter to stderr
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

if len(extra) != 1:
    o.fatal("exactly one argument expected")

total = parse_num(extra[0])

handle_ctrl_c()

if opt.force or (not os.isatty(1) and
                 not atoi(os.environ.get('BUP_FORCE_TTY')) & 1):
    _helpers.write_random(sys.stdout.fileno(), total, opt.seed,
                          opt.verbose and 1 or 0)
else:
    log('error: not writing binary data to a terminal. Use -f to force.\n')
    sys.exit(1)

########NEW FILE########
__FILENAME__ = restore-cmd
#!/usr/bin/env python
import copy, errno, sys, stat, re
from bup import options, git, metadata, vfs
from bup.helpers import *

optspec = """
bup restore [-C outdir] </branch/revision/path/to/dir ...>
--
C,outdir=   change to given outdir before extracting files
numeric-ids restore numeric IDs (user, group, etc.) rather than names
exclude-rx= skip paths matching the unanchored regex (may be repeated)
exclude-rx-from= skip --exclude-rx patterns in file (may be repeated)
v,verbose   increase log output (can be used more than once)
map-user=   given OLD=NEW, restore OLD user as NEW user
map-group=  given OLD=NEW, restore OLD group as NEW group
map-uid=    given OLD=NEW, restore OLD uid as NEW uid
map-gid=    given OLD=NEW, restore OLD gid as NEW gid
q,quiet     don't show progress meter
"""

total_restored = 0

# stdout should be flushed after each line, even when not connected to a tty
sys.stdout.flush()
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)

def verbose1(s):
    if opt.verbose >= 1:
        print s


def verbose2(s):
    if opt.verbose >= 2:
        print s


def plog(s):
    if opt.quiet:
        return
    qprogress(s)


def valid_restore_path(path):
    path = os.path.normpath(path)
    if path.startswith('/'):
        path = path[1:]
    if '/' in path:
        return True


def print_info(n, fullname):
    if stat.S_ISDIR(n.mode):
        verbose1('%s/' % fullname)
    elif stat.S_ISLNK(n.mode):
        verbose2('%s@ -> %s' % (fullname, n.readlink()))
    else:
        verbose2(fullname)


def create_path(n, fullname, meta):
    if meta:
        meta.create_path(fullname)
    else:
        # These fallbacks are important -- meta could be null if, for
        # example, save created a "fake" item, i.e. a new strip/graft
        # path element, etc.  You can find cases like that by
        # searching for "Metadata()".
        unlink(fullname)
        if stat.S_ISDIR(n.mode):
            mkdirp(fullname)
        elif stat.S_ISLNK(n.mode):
            os.symlink(n.readlink(), fullname)


def parse_owner_mappings(type, options, fatal):
    """Traverse the options and parse all --map-TYPEs, or call Option.fatal()."""
    opt_name = '--map-' + type
    value_rx = r'^([^=]+)=([^=]*)$'
    if type in ('uid', 'gid'):
        value_rx = r'^(-?[0-9]+)=(-?[0-9]+)$'
    owner_map = {}
    for flag in options:
        (option, parameter) = flag
        if option != opt_name:
            continue
        match = re.match(value_rx, parameter)
        if not match:
            raise fatal("couldn't parse %s as %s mapping" % (parameter, type))
        old_id, new_id = match.groups()
        if type in ('uid', 'gid'):
            old_id = int(old_id)
            new_id = int(new_id)
        owner_map[old_id] = new_id
    return owner_map


def apply_metadata(meta, name, restore_numeric_ids, owner_map):
    m = copy.deepcopy(meta)
    m.user = owner_map['user'].get(m.user, m.user)
    m.group = owner_map['group'].get(m.group, m.group)
    m.uid = owner_map['uid'].get(m.uid, m.uid)
    m.gid = owner_map['gid'].get(m.gid, m.gid)
    m.apply_to_path(name, restore_numeric_ids = restore_numeric_ids)


# Track a list of (restore_path, vfs_path, meta) triples for each path
# we've written for a given hardlink_target.  This allows us to handle
# the case where we restore a set of hardlinks out of order (with
# respect to the original save call(s)) -- i.e. when we don't restore
# the hardlink_target path first.  This data also allows us to attempt
# to handle other situations like hardlink sets that change on disk
# during a save, or between index and save.
targets_written = {}

def hardlink_compatible(target_path, target_vfs_path, target_meta,
                        src_node, src_meta):
    global top
    if not os.path.exists(target_path):
        return False
    target_node = top.lresolve(target_vfs_path)
    if src_node.mode != target_node.mode \
            or src_node.mtime != target_node.mtime \
            or src_node.ctime != target_node.ctime \
            or src_node.hash != target_node.hash:
        return False
    if not src_meta.same_file(target_meta):
        return False
    return True


def hardlink_if_possible(fullname, node, meta):
    """Find a suitable hardlink target, link to it, and return true,
    otherwise return false."""
    # Expect the caller to handle restoring the metadata if
    # hardlinking isn't possible.
    global targets_written
    target = meta.hardlink_target
    target_versions = targets_written.get(target)
    if target_versions:
        # Check every path in the set that we've written so far for a match.
        for (target_path, target_vfs_path, target_meta) in target_versions:
            if hardlink_compatible(target_path, target_vfs_path, target_meta,
                                   node, meta):
                try:
                    os.link(target_path, fullname)
                    return True
                except OSError, e:
                    if e.errno != errno.EXDEV:
                        raise
    else:
        target_versions = []
        targets_written[target] = target_versions
    full_vfs_path = node.fullname()
    target_versions.append((fullname, full_vfs_path, meta))
    return False


def write_file_content(fullname, n):
    outf = open(fullname, 'wb')
    try:
        for b in chunkyreader(n.open()):
            outf.write(b)
    finally:
        outf.close()


def find_dir_item_metadata_by_name(dir, name):
    """Find metadata in dir (a node) for an item with the given name,
    or for the directory itself if the name is ''."""
    meta_stream = None
    try:
        mfile = dir.metadata_file() # VFS file -- cannot close().
        if mfile:
            meta_stream = mfile.open()
            # First entry is for the dir itself.
            meta = metadata.Metadata.read(meta_stream)
            if name == '':
                return meta
            for sub in dir:
                if stat.S_ISDIR(sub.mode):
                    meta = find_dir_item_metadata_by_name(sub, '')
                else:
                    meta = metadata.Metadata.read(meta_stream)
                if sub.name == name:
                    return meta
    finally:
        if meta_stream:
            meta_stream.close()


def do_root(n, owner_map, restore_root_meta = True):
    # Very similar to do_node(), except that this function doesn't
    # create a path for n's destination directory (and so ignores
    # n.fullname).  It assumes the destination is '.', and restores
    # n's metadata and content there.
    global total_restored, opt
    meta_stream = None
    try:
        # Directory metadata is the first entry in any .bupm file in
        # the directory.  Get it.
        mfile = n.metadata_file() # VFS file -- cannot close().
        root_meta = None
        if mfile:
            meta_stream = mfile.open()
            root_meta = metadata.Metadata.read(meta_stream)
        print_info(n, '.')
        total_restored += 1
        plog('Restoring: %d\r' % total_restored)
        for sub in n:
            m = None
            # Don't get metadata if this is a dir -- handled in sub do_node().
            if meta_stream and not stat.S_ISDIR(sub.mode):
                m = metadata.Metadata.read(meta_stream)
            do_node(n, sub, owner_map, meta = m)
        if root_meta and restore_root_meta:
            apply_metadata(root_meta, '.', opt.numeric_ids, owner_map)
    finally:
        if meta_stream:
            meta_stream.close()


def do_node(top, n, owner_map, meta = None):
    # Create n.fullname(), relative to the current directory, and
    # restore all of its metadata, when available.  The meta argument
    # will be None for dirs, or when there is no .bupm (i.e. no
    # metadata).
    global total_restored, opt
    meta_stream = None
    try:
        fullname = n.fullname(stop_at=top)
        # Match behavior of index --exclude-rx with respect to paths.
        exclude_candidate = '/' + fullname
        if(stat.S_ISDIR(n.mode)):
            exclude_candidate += '/'
        if should_rx_exclude_path(exclude_candidate, exclude_rxs):
            return
        # If this is a directory, its metadata is the first entry in
        # any .bupm file inside the directory.  Get it.
        if(stat.S_ISDIR(n.mode)):
            mfile = n.metadata_file() # VFS file -- cannot close().
            if mfile:
                meta_stream = mfile.open()
                meta = metadata.Metadata.read(meta_stream)
        print_info(n, fullname)

        created_hardlink = False
        if meta and meta.hardlink_target:
            created_hardlink = hardlink_if_possible(fullname, n, meta)

        if not created_hardlink:
            create_path(n, fullname, meta)
            if meta:
                if stat.S_ISREG(meta.mode):
                    write_file_content(fullname, n)
            elif stat.S_ISREG(n.mode):
                write_file_content(fullname, n)

        total_restored += 1
        plog('Restoring: %d\r' % total_restored)
        for sub in n:
            m = None
            # Don't get metadata if this is a dir -- handled in sub do_node().
            if meta_stream and not stat.S_ISDIR(sub.mode):
                m = metadata.Metadata.read(meta_stream)
            do_node(top, sub, owner_map, meta = m)
        if meta and not created_hardlink:
            apply_metadata(meta, fullname, opt.numeric_ids, owner_map)
    finally:
        if meta_stream:
            meta_stream.close()
        n.release()


handle_ctrl_c()

o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

git.check_repo_or_die()
top = vfs.RefList(None)

if not extra:
    o.fatal('must specify at least one filename to restore')
    
exclude_rxs = parse_rx_excludes(flags, o.fatal)

owner_map = {}
for map_type in ('user', 'group', 'uid', 'gid'):
    owner_map[map_type] = parse_owner_mappings(map_type, flags, o.fatal)

if opt.outdir:
    mkdirp(opt.outdir)
    os.chdir(opt.outdir)

ret = 0
for d in extra:
    if not valid_restore_path(d):
        add_error("ERROR: path %r doesn't include a branch and revision" % d)
        continue
    path,name = os.path.split(d)
    try:
        n = top.lresolve(d)
    except vfs.NodeError, e:
        add_error(e)
        continue
    isdir = stat.S_ISDIR(n.mode)
    if not name or name == '.':
        # Source is /foo/what/ever/ or /foo/what/ever/. -- extract
        # what/ever/* to the current directory, and if name == '.'
        # (i.e. /foo/what/ever/.), then also restore what/ever's
        # metadata to the current directory.
        if not isdir:
            add_error('%r: not a directory' % d)
        else:
            do_root(n, owner_map, restore_root_meta = (name == '.'))
    else:
        # Source is /foo/what/ever -- extract ./ever to cwd.
        if isinstance(n, vfs.FakeSymlink):
            # Source is actually /foo/what, i.e. a top-level commit
            # like /foo/latest, which is a symlink to ../.commit/SHA.
            # So dereference it, and restore ../.commit/SHA/. to
            # "./what/.".
            target = n.dereference()
            mkdirp(n.name)
            os.chdir(n.name)
            do_root(target, owner_map)
        else: # Not a directory or fake symlink.
            meta = find_dir_item_metadata_by_name(n.parent, n.name)
            do_node(n.parent, n, owner_map, meta = meta)

if not opt.quiet:
    progress('Restoring: %d, done.\n' % total_restored)

if saved_errors:
    log('WARNING: %d errors encountered while restoring.\n' % len(saved_errors))
    sys.exit(1)

########NEW FILE########
__FILENAME__ = save-cmd
#!/usr/bin/env python
import sys, stat, time, math
from cStringIO import StringIO
from bup import hashsplit, git, options, index, client, metadata, hlinkdb
from bup.helpers import *
from bup.hashsplit import GIT_MODE_TREE, GIT_MODE_FILE, GIT_MODE_SYMLINK


optspec = """
bup save [-tc] [-n name] <filenames...>
--
r,remote=  hostname:/path/to/repo of remote repository
t,tree     output a tree id
c,commit   output a commit id
n,name=    name of backup set to update (if any)
d,date=    date for the commit (seconds since the epoch)
v,verbose  increase log output (can be used more than once)
q,quiet    don't show progress meter
smaller=   only back up files smaller than n bytes
bwlimit=   maximum bytes/sec to transmit to server
f,indexfile=  the name of the index file (normally BUP_DIR/bupindex)
strip      strips the path to every filename given
strip-path= path-prefix to be stripped when saving
graft=     a graft point *old_path*=*new_path* (can be used more than once)
#,compress=  set compression level to # (0-9, 9 is highest) [1]
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

git.check_repo_or_die()
if not (opt.tree or opt.commit or opt.name):
    o.fatal("use one or more of -t, -c, -n")
if not extra:
    o.fatal("no filenames given")

opt.progress = (istty2 and not opt.quiet)
opt.smaller = parse_num(opt.smaller or 0)
if opt.bwlimit:
    client.bwlimit = parse_num(opt.bwlimit)

if opt.date:
    date = parse_date_or_fatal(opt.date, o.fatal)
else:
    date = time.time()

if opt.strip and opt.strip_path:
    o.fatal("--strip is incompatible with --strip-path")

graft_points = []
if opt.graft:
    if opt.strip:
        o.fatal("--strip is incompatible with --graft")

    if opt.strip_path:
        o.fatal("--strip-path is incompatible with --graft")

    for (option, parameter) in flags:
        if option == "--graft":
            splitted_parameter = parameter.split('=')
            if len(splitted_parameter) != 2:
                o.fatal("a graft point must be of the form old_path=new_path")
            old_path, new_path = splitted_parameter
            if not (old_path and new_path):
                o.fatal("a graft point cannot be empty")
            graft_points.append((realpath(old_path), realpath(new_path)))

is_reverse = os.environ.get('BUP_SERVER_REVERSE')
if is_reverse and opt.remote:
    o.fatal("don't use -r in reverse mode; it's automatic")

if opt.name and opt.name.startswith('.'):
    o.fatal("'%s' is not a valid branch name" % opt.name)
refname = opt.name and 'refs/heads/%s' % opt.name or None
if opt.remote or is_reverse:
    cli = client.Client(opt.remote)
    oldref = refname and cli.read_ref(refname) or None
    w = cli.new_packwriter(compression_level=opt.compress)
else:
    cli = None
    oldref = refname and git.read_ref(refname) or None
    w = git.PackWriter(compression_level=opt.compress)

handle_ctrl_c()


def eatslash(dir):
    if dir.endswith('/'):
        return dir[:-1]
    else:
        return dir


# Metadata is stored in a file named .bupm in each directory.  The
# first metadata entry will be the metadata for the current directory.
# The remaining entries will be for each of the other directory
# elements, in the order they're listed in the index.
#
# Since the git tree elements are sorted according to
# git.shalist_item_sort_key, the metalist items are accumulated as
# (sort_key, metadata) tuples, and then sorted when the .bupm file is
# created.  The sort_key must be computed using the element's real
# name and mode rather than the git mode and (possibly mangled) name.

# Maintain a stack of information representing the current location in
# the archive being constructed.  The current path is recorded in
# parts, which will be something like ['', 'home', 'someuser'], and
# the accumulated content and metadata for of the dirs in parts is
# stored in parallel stacks in shalists and metalists.

parts = [] # Current archive position (stack of dir names).
shalists = [] # Hashes for each dir in paths.
metalists = [] # Metadata for each dir in paths.


def _push(part, metadata):
    # Enter a new archive directory -- make it the current directory.
    parts.append(part)
    shalists.append([])
    metalists.append([('', metadata)]) # This dir's metadata (no name).


def _pop(force_tree, dir_metadata=None):
    # Leave the current archive directory and add its tree to its parent.
    assert(len(parts) >= 1)
    part = parts.pop()
    shalist = shalists.pop()
    metalist = metalists.pop()
    if metalist and not force_tree:
        if dir_metadata: # Override the original metadata pushed for this dir.
            metalist = [('', dir_metadata)] + metalist[1:]
        sorted_metalist = sorted(metalist, key = lambda x : x[0])
        metadata = ''.join([m[1].encode() for m in sorted_metalist])
        metadata_f = StringIO(metadata)
        mode, id = hashsplit.split_to_blob_or_tree(w.new_blob, w.new_tree,
                                                   [metadata_f],
                                                   keep_boundaries=False)
        shalist.append((mode, '.bupm', id))
    tree = force_tree or w.new_tree(shalist)
    if shalists:
        shalists[-1].append((GIT_MODE_TREE,
                             git.mangle_name(part,
                                             GIT_MODE_TREE, GIT_MODE_TREE),
                             tree))
    return tree


lastremain = None
def progress_report(n):
    global count, subcount, lastremain
    subcount += n
    cc = count + subcount
    pct = total and (cc*100.0/total) or 0
    now = time.time()
    elapsed = now - tstart
    kps = elapsed and int(cc/1024./elapsed)
    kps_frac = 10 ** int(math.log(kps+1, 10) - 1)
    kps = int(kps/kps_frac)*kps_frac
    if cc:
        remain = elapsed*1.0/cc * (total-cc)
    else:
        remain = 0.0
    if (lastremain and (remain > lastremain)
          and ((remain - lastremain)/lastremain < 0.05)):
        remain = lastremain
    else:
        lastremain = remain
    hours = int(remain/60/60)
    mins = int(remain/60 - hours*60)
    secs = int(remain - hours*60*60 - mins*60)
    if elapsed < 30:
        remainstr = ''
        kpsstr = ''
    else:
        kpsstr = '%dk/s' % kps
        if hours:
            remainstr = '%dh%dm' % (hours, mins)
        elif mins:
            remainstr = '%dm%d' % (mins, secs)
        else:
            remainstr = '%ds' % secs
    qprogress('Saving: %.2f%% (%d/%dk, %d/%d files) %s %s\r'
              % (pct, cc/1024, total/1024, fcount, ftotal,
                 remainstr, kpsstr))


indexfile = opt.indexfile or git.repo('bupindex')
r = index.Reader(indexfile)
if not os.access(indexfile + '.meta', os.W_OK|os.R_OK):
    log('error: cannot access "%s"; have you run bup index?' % indexfile)
    sys.exit(1)
msr = index.MetaStoreReader(indexfile + '.meta')
hlink_db = hlinkdb.HLinkDB(indexfile + '.hlink')

def already_saved(ent):
    return ent.is_valid() and w.exists(ent.sha) and ent.sha

def wantrecurse_pre(ent):
    return not already_saved(ent)

def wantrecurse_during(ent):
    return not already_saved(ent) or ent.sha_missing()

def find_hardlink_target(hlink_db, ent):
    if hlink_db and not stat.S_ISDIR(ent.mode) and ent.nlink > 1:
        link_paths = hlink_db.node_paths(ent.dev, ent.ino)
        if link_paths:
            return link_paths[0]

total = ftotal = 0
if opt.progress:
    for (transname,ent) in r.filter(extra, wantrecurse=wantrecurse_pre):
        if not (ftotal % 10024):
            qprogress('Reading index: %d\r' % ftotal)
        exists = ent.exists()
        hashvalid = already_saved(ent)
        ent.set_sha_missing(not hashvalid)
        if not opt.smaller or ent.size < opt.smaller:
            if exists and not hashvalid:
                total += ent.size
        ftotal += 1
    progress('Reading index: %d, done.\n' % ftotal)
    hashsplit.progress_callback = progress_report

# Root collisions occur when strip or graft options map more than one
# path to the same directory (paths which originally had separate
# parents).  When that situation is detected, use empty metadata for
# the parent.  Otherwise, use the metadata for the common parent.
# Collision example: "bup save ... --strip /foo /foo/bar /bar".

# FIXME: Add collision tests, or handle collisions some other way.

# FIXME: Detect/handle strip/graft name collisions (other than root),
# i.e. if '/foo/bar' and '/bar' both map to '/'.

first_root = None
root_collision = None
tstart = time.time()
count = subcount = fcount = 0
lastskip_name = None
lastdir = ''
for (transname,ent) in r.filter(extra, wantrecurse=wantrecurse_during):
    (dir, file) = os.path.split(ent.name)
    exists = (ent.flags & index.IX_EXISTS)
    hashvalid = already_saved(ent)
    wasmissing = ent.sha_missing()
    oldsize = ent.size
    if opt.verbose:
        if not exists:
            status = 'D'
        elif not hashvalid:
            if ent.sha == index.EMPTY_SHA:
                status = 'A'
            else:
                status = 'M'
        else:
            status = ' '
        if opt.verbose >= 2:
            log('%s %-70s\n' % (status, ent.name))
        elif not stat.S_ISDIR(ent.mode) and lastdir != dir:
            if not lastdir.startswith(dir):
                log('%s %-70s\n' % (status, os.path.join(dir, '')))
            lastdir = dir

    if opt.progress:
        progress_report(0)
    fcount += 1
    
    if not exists:
        continue
    if opt.smaller and ent.size >= opt.smaller:
        if exists and not hashvalid:
            add_error('skipping large file "%s"' % ent.name)
            lastskip_name = ent.name
        continue

    assert(dir.startswith('/'))
    if opt.strip:
        dirp = stripped_path_components(dir, extra)
    elif opt.strip_path:
        dirp = stripped_path_components(dir, [opt.strip_path])
    elif graft_points:
        dirp = grafted_path_components(graft_points, dir)
    else:
        dirp = path_components(dir)

    # At this point, dirp contains a representation of the archive
    # path that looks like [(archive_dir_name, real_fs_path), ...].
    # So given "bup save ... --strip /foo/bar /foo/bar/baz", dirp
    # might look like this at some point:
    #   [('', '/foo/bar'), ('baz', '/foo/bar/baz'), ...].

    # This dual representation supports stripping/grafting, where the
    # archive path may not have a direct correspondence with the
    # filesystem.  The root directory is represented by an initial
    # component named '', and any component that doesn't have a
    # corresponding filesystem directory (due to grafting, for
    # example) will have a real_fs_path of None, i.e. [('', None),
    # ...].

    if first_root == None:
        dir_name, fs_path = dirp[0]
        first_root = dirp[0]
        # Not indexed, so just grab the FS metadata or use empty metadata.
        try:
           meta = metadata.from_path(fs_path) if fs_path else metadata.Metadata()
        except (OSError, IOError), e:
            add_error(e)
            lastskip_name = dir_name
        else:
           _push(dir_name, meta)
    elif first_root != dirp[0]:
        root_collision = True

    # If switching to a new sub-tree, finish the current sub-tree.
    while parts > [x[0] for x in dirp]:
        _pop(force_tree = None)

    # If switching to a new sub-tree, start a new sub-tree.
    for path_component in dirp[len(parts):]:
        dir_name, fs_path = path_component
        # Not indexed, so just grab the FS metadata or use empty metadata.
        try:
           meta = metadata.from_path(fs_path) if fs_path else metadata.Metadata()
        except (OSError, IOError), e:
            add_error(e)
            lastskip_name = dir_name
        else:
           _push(dir_name, meta)

    if not file:
        if len(parts) == 1:
            continue # We're at the top level -- keep the current root dir
        # Since there's no filename, this is a subdir -- finish it.
        oldtree = already_saved(ent) # may be None
        newtree = _pop(force_tree = oldtree)
        if not oldtree:
            if lastskip_name and lastskip_name.startswith(ent.name):
                ent.invalidate()
            else:
                ent.validate(GIT_MODE_TREE, newtree)
            ent.repack()
        if exists and wasmissing:
            count += oldsize
        continue

    # it's not a directory
    id = None
    if hashvalid:
        id = ent.sha
        git_name = git.mangle_name(file, ent.mode, ent.gitmode)
        git_info = (ent.gitmode, git_name, id)
        shalists[-1].append(git_info)
        sort_key = git.shalist_item_sort_key((ent.mode, file, id))
        meta = msr.metadata_at(ent.meta_ofs)
        meta.hardlink_target = find_hardlink_target(hlink_db, ent)
        # Restore the times that were cleared to 0 in the metastore.
        (meta.atime, meta.mtime, meta.ctime) = (ent.atime, ent.mtime, ent.ctime)
        metalists[-1].append((sort_key, meta))
    else:
        if stat.S_ISREG(ent.mode):
            try:
                f = hashsplit.open_noatime(ent.name)
            except (IOError, OSError), e:
                add_error(e)
                lastskip_name = ent.name
            else:
                try:
                    (mode, id) = hashsplit.split_to_blob_or_tree(
                                            w.new_blob, w.new_tree, [f],
                                            keep_boundaries=False)
                except (IOError, OSError), e:
                    add_error('%s: %s' % (ent.name, e))
                    lastskip_name = ent.name
        else:
            if stat.S_ISDIR(ent.mode):
                assert(0)  # handled above
            elif stat.S_ISLNK(ent.mode):
                try:
                    rl = os.readlink(ent.name)
                except (OSError, IOError), e:
                    add_error(e)
                    lastskip_name = ent.name
                else:
                    (mode, id) = (GIT_MODE_SYMLINK, w.new_blob(rl))
            else:
                # Everything else should be fully described by its
                # metadata, so just record an empty blob, so the paths
                # in the tree and .bupm will match up.
                (mode, id) = (GIT_MODE_FILE, w.new_blob(""))

        if id:
            ent.validate(mode, id)
            ent.repack()
            git_name = git.mangle_name(file, ent.mode, ent.gitmode)
            git_info = (mode, git_name, id)
            shalists[-1].append(git_info)
            sort_key = git.shalist_item_sort_key((ent.mode, file, id))
            hlink = find_hardlink_target(hlink_db, ent)
            try:
                meta = metadata.from_path(ent.name, hardlink_target=hlink)
            except (OSError, IOError), e:
                add_error(e)
                lastskip_name = ent.name
            else:
                metalists[-1].append((sort_key, meta))

    if exists and wasmissing:
        count += oldsize
        subcount = 0


if opt.progress:
    pct = total and count*100.0/total or 100
    progress('Saving: %.2f%% (%d/%dk, %d/%d files), done.    \n'
             % (pct, count/1024, total/1024, fcount, ftotal))

while len(parts) > 1: # _pop() all the parts above the root
    _pop(force_tree = None)
assert(len(shalists) == 1)
assert(len(metalists) == 1)

# Finish the root directory.
tree = _pop(force_tree = None,
            # When there's a collision, use empty metadata for the root.
            dir_metadata = metadata.Metadata() if root_collision else None)

if opt.tree:
    print tree.encode('hex')
if opt.commit or opt.name:
    msg = 'bup save\n\nGenerated by command:\n%r\n' % sys.argv
    commit = w.new_commit(oldref, tree, date, msg)
    if opt.commit:
        print commit.encode('hex')

msr.close()
w.close()  # must close before we can update the ref
        
if opt.name:
    if cli:
        cli.update_ref(refname, commit, oldref)
    else:
        git.update_ref(refname, commit, oldref)

if cli:
    cli.close()

if saved_errors:
    log('WARNING: %d errors encountered while saving.\n' % len(saved_errors))
    sys.exit(1)

########NEW FILE########
__FILENAME__ = server-cmd
#!/usr/bin/env python
import os, sys, struct
from bup import options, git
from bup.helpers import *

suspended_w = None
dumb_server_mode = False


def do_help(conn, junk):
    conn.write('Commands:\n    %s\n' % '\n    '.join(sorted(commands)))
    conn.ok()


def _set_mode():
    global dumb_server_mode
    dumb_server_mode = os.path.exists(git.repo('bup-dumb-server'))
    debug1('bup server: serving in %s mode\n' 
           % (dumb_server_mode and 'dumb' or 'smart'))


def _init_session(reinit_with_new_repopath=None):
    if reinit_with_new_repopath is None and git.repodir:
        return
    git.check_repo_or_die(reinit_with_new_repopath)
    # OK. we now know the path is a proper repository. Record this path in the
    # environment so that subprocesses inherit it and know where to operate.
    os.environ['BUP_DIR'] = git.repodir
    debug1('bup server: bupdir is %r\n' % git.repodir)
    _set_mode()


def init_dir(conn, arg):
    git.init_repo(arg)
    debug1('bup server: bupdir initialized: %r\n' % git.repodir)
    _init_session(arg)
    conn.ok()


def set_dir(conn, arg):
    _init_session(arg)
    conn.ok()

    
def list_indexes(conn, junk):
    _init_session()
    suffix = ''
    if dumb_server_mode:
        suffix = ' load'
    for f in os.listdir(git.repo('objects/pack')):
        if f.endswith('.idx'):
            conn.write('%s%s\n' % (f, suffix))
    conn.ok()


def send_index(conn, name):
    _init_session()
    assert(name.find('/') < 0)
    assert(name.endswith('.idx'))
    idx = git.open_idx(git.repo('objects/pack/%s' % name))
    conn.write(struct.pack('!I', len(idx.map)))
    conn.write(idx.map)
    conn.ok()


def receive_objects_v2(conn, junk):
    global suspended_w
    _init_session()
    suggested = set()
    if suspended_w:
        w = suspended_w
        suspended_w = None
    else:
        if dumb_server_mode:
            w = git.PackWriter(objcache_maker=None)
        else:
            w = git.PackWriter()
    while 1:
        ns = conn.read(4)
        if not ns:
            w.abort()
            raise Exception('object read: expected length header, got EOF\n')
        n = struct.unpack('!I', ns)[0]
        #debug2('expecting %d bytes\n' % n)
        if not n:
            debug1('bup server: received %d object%s.\n' 
                % (w.count, w.count!=1 and "s" or ''))
            fullpath = w.close(run_midx=not dumb_server_mode)
            if fullpath:
                (dir, name) = os.path.split(fullpath)
                conn.write('%s.idx\n' % name)
            conn.ok()
            return
        elif n == 0xffffffff:
            debug2('bup server: receive-objects suspended.\n')
            suspended_w = w
            conn.ok()
            return
            
        shar = conn.read(20)
        crcr = struct.unpack('!I', conn.read(4))[0]
        n -= 20 + 4
        buf = conn.read(n)  # object sizes in bup are reasonably small
        #debug2('read %d bytes\n' % n)
        _check(w, n, len(buf), 'object read: expected %d bytes, got %d\n')
        if not dumb_server_mode:
            oldpack = w.exists(shar, want_source=True)
            if oldpack:
                assert(not oldpack == True)
                assert(oldpack.endswith('.idx'))
                (dir,name) = os.path.split(oldpack)
                if not (name in suggested):
                    debug1("bup server: suggesting index %s\n"
                           % git.shorten_hash(name))
                    debug1("bup server:   because of object %s\n"
                           % shar.encode('hex'))
                    conn.write('index %s\n' % name)
                    suggested.add(name)
                continue
        nw, crc = w._raw_write((buf,), sha=shar)
        _check(w, crcr, crc, 'object read: expected crc %d, got %d\n')
    # NOTREACHED
    

def _check(w, expected, actual, msg):
    if expected != actual:
        w.abort()
        raise Exception(msg % (expected, actual))


def read_ref(conn, refname):
    _init_session()
    r = git.read_ref(refname)
    conn.write('%s\n' % (r or '').encode('hex'))
    conn.ok()


def update_ref(conn, refname):
    _init_session()
    newval = conn.readline().strip()
    oldval = conn.readline().strip()
    git.update_ref(refname, newval.decode('hex'), oldval.decode('hex'))
    conn.ok()


cat_pipe = None
def cat(conn, id):
    global cat_pipe
    _init_session()
    if not cat_pipe:
        cat_pipe = git.CatPipe()
    try:
        for blob in cat_pipe.join(id):
            conn.write(struct.pack('!I', len(blob)))
            conn.write(blob)
    except KeyError, e:
        log('server: error: %s\n' % e)
        conn.write('\0\0\0\0')
        conn.error(e)
    else:
        conn.write('\0\0\0\0')
        conn.ok()


optspec = """
bup server
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

if extra:
    o.fatal('no arguments expected')

debug2('bup server: reading from stdin.\n')

commands = {
    'quit': None,
    'help': do_help,
    'init-dir': init_dir,
    'set-dir': set_dir,
    'list-indexes': list_indexes,
    'send-index': send_index,
    'receive-objects-v2': receive_objects_v2,
    'read-ref': read_ref,
    'update-ref': update_ref,
    'cat': cat,
}

# FIXME: this protocol is totally lame and not at all future-proof.
# (Especially since we abort completely as soon as *anything* bad happens)
conn = Conn(sys.stdin, sys.stdout)
lr = linereader(conn)
for _line in lr:
    line = _line.strip()
    if not line:
        continue
    debug1('bup server: command: %r\n' % line)
    words = line.split(' ', 1)
    cmd = words[0]
    rest = len(words)>1 and words[1] or ''
    if cmd == 'quit':
        break
    else:
        cmd = commands.get(cmd)
        if cmd:
            cmd(conn, rest)
        else:
            raise Exception('unknown server command: %r\n' % line)

debug1('bup server: done\n')

########NEW FILE########
__FILENAME__ = split-cmd
#!/usr/bin/env python
import os, sys, time
from bup import hashsplit, git, options, client
from bup.helpers import *


optspec = """
bup split [-t] [-c] [-n name] OPTIONS [--git-ids | filenames...]
bup split -b OPTIONS [--git-ids | filenames...]
bup split <--noop [--copy]|--copy>  OPTIONS [--git-ids | filenames...]
--
 Modes:
b,blobs    output a series of blob ids.  Implies --fanout=0.
t,tree     output a tree id
c,commit   output a commit id
n,name=    save the result under the given name
noop       split the input, but throw away the result
copy       split the input, copy it to stdout, don't save to repo
 Options:
r,remote=  remote repository path
d,date=    date for the commit (seconds since the epoch)
q,quiet    don't print progress messages
v,verbose  increase log output (can be used more than once)
git-ids    read a list of git object ids from stdin and split their contents
keep-boundaries  don't let one chunk span two input files
bench      print benchmark timings to stderr
max-pack-size=  maximum bytes in a single pack
max-pack-objects=  maximum number of objects in a single pack
fanout=    average number of blobs in a single tree
bwlimit=   maximum bytes/sec to transmit to server
#,compress=  set compression level to # (0-9, 9 is highest) [1]
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

handle_ctrl_c()
git.check_repo_or_die()
if not (opt.blobs or opt.tree or opt.commit or opt.name or
        opt.noop or opt.copy):
    o.fatal("use one or more of -b, -t, -c, -n, --noop, --copy")
if (opt.noop or opt.copy) and (opt.blobs or opt.tree or
                               opt.commit or opt.name):
    o.fatal('--noop and --copy are incompatible with -b, -t, -c, -n')
if opt.blobs and (opt.tree or opt.commit or opt.name):
    o.fatal('-b is incompatible with -t, -c, -n')
if extra and opt.git_ids:
    o.fatal("don't provide filenames when using --git-ids")

if opt.verbose >= 2:
    git.verbose = opt.verbose - 1
    opt.bench = 1
if opt.max_pack_size:
    git.max_pack_size = parse_num(opt.max_pack_size)
if opt.max_pack_objects:
    git.max_pack_objects = parse_num(opt.max_pack_objects)
if opt.fanout:
    hashsplit.fanout = parse_num(opt.fanout)
if opt.blobs:
    hashsplit.fanout = 0
if opt.bwlimit:
    client.bwlimit = parse_num(opt.bwlimit)
if opt.date:
    date = parse_date_or_fatal(opt.date, o.fatal)
else:
    date = time.time()

total_bytes = 0
def prog(filenum, nbytes):
    global total_bytes
    total_bytes += nbytes
    if filenum > 0:
        qprogress('Splitting: file #%d, %d kbytes\r'
                  % (filenum+1, total_bytes/1024))
    else:
        qprogress('Splitting: %d kbytes\r' % (total_bytes/1024))


is_reverse = os.environ.get('BUP_SERVER_REVERSE')
if is_reverse and opt.remote:
    o.fatal("don't use -r in reverse mode; it's automatic")
start_time = time.time()

if opt.name and opt.name.startswith('.'):
    o.fatal("'%s' is not a valid branch name." % opt.name)
refname = opt.name and 'refs/heads/%s' % opt.name or None
if opt.noop or opt.copy:
    cli = pack_writer = oldref = None
elif opt.remote or is_reverse:
    cli = client.Client(opt.remote)
    oldref = refname and cli.read_ref(refname) or None
    pack_writer = cli.new_packwriter(compression_level=opt.compress)
else:
    cli = None
    oldref = refname and git.read_ref(refname) or None
    pack_writer = git.PackWriter(compression_level=opt.compress)

if opt.git_ids:
    # the input is actually a series of git object ids that we should retrieve
    # and split.
    #
    # This is a bit messy, but basically it converts from a series of
    # CatPipe.get() iterators into a series of file-type objects.
    # It would be less ugly if either CatPipe.get() returned a file-like object
    # (not very efficient), or split_to_shalist() expected an iterator instead
    # of a file.
    cp = git.CatPipe()
    class IterToFile:
        def __init__(self, it):
            self.it = iter(it)
        def read(self, size):
            v = next(self.it, None)
            return v or ''
    def read_ids():
        while 1:
            line = sys.stdin.readline()
            if not line:
                break
            if line:
                line = line.strip()
            try:
                it = cp.get(line.strip())
                next(it, None)  # skip the file type
            except KeyError, e:
                add_error('error: %s' % e)
                continue
            yield IterToFile(it)
    files = read_ids()
else:
    # the input either comes from a series of files or from stdin.
    files = extra and (open(fn) for fn in extra) or [sys.stdin]

if pack_writer and opt.blobs:
    shalist = hashsplit.split_to_blobs(pack_writer.new_blob, files,
                                       keep_boundaries=opt.keep_boundaries,
                                       progress=prog)
    for (sha, size, level) in shalist:
        print sha.encode('hex')
        reprogress()
elif pack_writer:  # tree or commit or name
    if opt.name: # insert dummy_name which may be used as a restore target
        mode, sha = \
            hashsplit.split_to_blob_or_tree(pack_writer.new_blob,
                                            pack_writer.new_tree,
                                            files,
                                            keep_boundaries=opt.keep_boundaries,
                                            progress=prog)
        splitfile_name = git.mangle_name('data', hashsplit.GIT_MODE_FILE, mode)
        shalist = [(mode, splitfile_name, sha)]
    else:
        shalist = hashsplit.split_to_shalist(
                      pack_writer.new_blob, pack_writer.new_tree, files,
                      keep_boundaries=opt.keep_boundaries, progress=prog)
    tree = pack_writer.new_tree(shalist)
else:
    last = 0
    it = hashsplit.hashsplit_iter(files,
                                  keep_boundaries=opt.keep_boundaries,
                                  progress=prog)
    for (blob, level) in it:
        hashsplit.total_split += len(blob)
        if opt.copy:
            sys.stdout.write(str(blob))
        megs = hashsplit.total_split/1024/1024
        if not opt.quiet and last != megs:
            last = megs

if opt.verbose:
    log('\n')
if opt.tree:
    print tree.encode('hex')
if opt.commit or opt.name:
    msg = 'bup split\n\nGenerated by command:\n%r\n' % sys.argv
    ref = opt.name and ('refs/heads/%s' % opt.name) or None
    commit = pack_writer.new_commit(oldref, tree, date, msg)
    if opt.commit:
        print commit.encode('hex')

if pack_writer:
    pack_writer.close()  # must close before we can update the ref

if opt.name:
    if cli:
        cli.update_ref(refname, commit, oldref)
    else:
        git.update_ref(refname, commit, oldref)

if cli:
    cli.close()

secs = time.time() - start_time
size = hashsplit.total_split
if opt.bench:
    log('bup: %.2fkbytes in %.2f secs = %.2f kbytes/sec\n'
        % (size/1024., secs, size/1024./secs))

if saved_errors:
    log('WARNING: %d errors encountered while saving.\n' % len(saved_errors))
    sys.exit(1)

########NEW FILE########
__FILENAME__ = tag-cmd
#!/usr/bin/env python
"""Tag a commit in the bup repository.
Creating a tag on a commit can be used for avoiding automatic cleanup from
removing this commit due to old age.
"""
import sys
import os

from bup import git, options
from bup.helpers import *

# FIXME: review for safe writes.

handle_ctrl_c()

optspec = """
bup tag
bup tag [-f] <tag name> <commit>
bup tag -d [-f] <tag name>
--
d,delete=   Delete a tag
f,force     Overwrite existing tag, or 'delete' a tag that doesn't exist
"""

o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

git.check_repo_or_die()

if opt.delete:
    tag_file = git.repo('refs/tags/%s' % opt.delete)
    debug1("tag file: %s\n" % tag_file)
    if not os.path.exists(tag_file):
        if opt.force:
            sys.exit(0)
        log("bup: error: tag '%s' not found.\n" % opt.delete)
        sys.exit(1)

    try:
        os.unlink(tag_file)
    except OSError, e:
        log("bup: error: unable to delete tag '%s': %s" % (opt.delete, e))
        sys.exit(1)

    sys.exit(0)

tags = [t for sublist in git.tags().values() for t in sublist]

if not extra:
    for t in tags:
        print t
    sys.exit(0)
elif len(extra) < 2:
    o.fatal('no commit ref or hash given.')

(tag_name, commit) = extra[:2]
if not tag_name:
    o.fatal("tag name must not be empty.")
debug1("args: tag name = %s; commit = %s\n" % (tag_name, commit))

if tag_name in tags and not opt.force:
    log("bup: error: tag '%s' already exists\n" % tag_name)
    sys.exit(1)

if tag_name.startswith('.'):
    o.fatal("'%s' is not a valid tag name." % tag_name)

try:
    hash = git.rev_parse(commit)
except git.GitError, e:
    log("bup: error: %s" % e)
    sys.exit(2)

if not hash:
    log("bup: error: commit %s not found.\n" % commit)
    sys.exit(2)

pL = git.PackIdxList(git.repo('objects/pack'))
if not pL.exists(hash):
    log("bup: error: commit %s not found.\n" % commit)
    sys.exit(2)

tag_file = git.repo('refs/tags/%s' % tag_name)
try:
    tag = file(tag_file, 'w')
except OSError, e:
    log("bup: error: could not create tag '%s': %s" % (tag_name, e))
    sys.exit(3)

tag.write(hash.encode('hex'))
tag.close()

########NEW FILE########
__FILENAME__ = tick-cmd
#!/usr/bin/env python
import sys, time
from bup import options

optspec = """
bup tick
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

if extra:
    o.fatal("no arguments expected")

t = time.time()
tleft = 1 - (t - int(t))
time.sleep(tleft)

########NEW FILE########
__FILENAME__ = version-cmd
#!/usr/bin/env python
import sys
from bup import options
from bup import _version

optspec = """
bup version [--date|--commit|--tag]
--
date    display the date this version of bup was created
commit  display the git commit id of this version of bup
tag     display the tag name of this version.  If no tag is available, display the commit id
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])


total = (opt.date or 0) + (opt.commit or 0) + (opt.tag or 0)
if total > 1:
    o.fatal('at most one option expected')


def version_date():
    """Format bup's version date string for output."""
    return _version.DATE.split(' ')[0]


def version_commit():
    """Get the commit hash of bup's current version."""
    return _version.COMMIT


def version_tag():
    """Format bup's version tag (the official version number).

    When generated from a commit other than one pointed to with a tag, the
    returned string will be "unknown-" followed by the first seven positions of
    the commit hash.
    """
    names = _version.NAMES.strip()
    assert(names[0] == '(')
    assert(names[-1] == ')')
    names = names[1:-1]
    l = [n.strip() for n in names.split(',')]
    for n in l:
        if n.startswith('tag: bup-'):
            return n[9:]
    return 'unknown-%s' % _version.COMMIT[:7]


if opt.date:
    print version_date()
elif opt.commit:
    print version_commit()
else:
    print version_tag()

########NEW FILE########
__FILENAME__ = web-cmd
#!/usr/bin/env python
import sys, stat, urllib, mimetypes, posixpath, time
from bup import options, git, vfs
from bup.helpers import *
try:
    import tornado.httpserver
    import tornado.ioloop
    import tornado.web
except ImportError:
    log('error: cannot find the python "tornado" module; please install it\n')
    sys.exit(1)

handle_ctrl_c()


def _compute_breadcrumbs(path, show_hidden=False):
    """Returns a list of breadcrumb objects for a path."""
    breadcrumbs = []
    breadcrumbs.append(('[root]', '/'))
    path_parts = path.split('/')[1:-1]
    full_path = '/'
    for part in path_parts:
        full_path += part + "/"
        url_append = ""
        if show_hidden:
            url_append = '?hidden=1'
        breadcrumbs.append((part, full_path+url_append))
    return breadcrumbs


def _contains_hidden_files(n):
    """Return True if n contains files starting with a '.', False otherwise."""
    for sub in n:
        name = sub.name
        if len(name)>1 and name.startswith('.'):
            return True

    return False


def _compute_dir_contents(n, path, show_hidden=False):
    """Given a vfs node, returns an iterator for display info of all subs."""
    url_append = ""
    if show_hidden:
        url_append = "?hidden=1"

    if path != "/":
        yield('..', '../' + url_append, '')
    for sub in n:
        display = link = sub.name

        # link should be based on fully resolved type to avoid extra
        # HTTP redirect.
        if stat.S_ISDIR(sub.try_resolve().mode):
            link = sub.name + "/"

        if not show_hidden and len(display)>1 and display.startswith('.'):
            continue

        size = None
        if stat.S_ISDIR(sub.mode):
            display = sub.name + '/'
        elif stat.S_ISLNK(sub.mode):
            display = sub.name + '@'
        else:
            size = sub.size()
            size = (opt.human_readable and format_filesize(size)) or size

        yield (display, link + url_append, size)


class BupRequestHandler(tornado.web.RequestHandler):
    def get(self, path):
        return self._process_request(path)

    def head(self, path):
        return self._process_request(path)
    
    @tornado.web.asynchronous
    def _process_request(self, path):
        path = urllib.unquote(path)
        print 'Handling request for %s' % path
        try:
            n = top.resolve(path)
        except vfs.NoSuchFile:
            self.send_error(404)
            return
        f = None
        if stat.S_ISDIR(n.mode):
            self._list_directory(path, n)
        else:
            self._get_file(path, n)

    def _list_directory(self, path, n):
        """Helper to produce a directory listing.

        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent.
        """
        if not path.endswith('/') and len(path) > 0:
            print 'Redirecting from %s to %s' % (path, path + '/')
            return self.redirect(path + '/', permanent=True)

        try:
            show_hidden = int(self.request.arguments.get('hidden', [0])[-1])
        except ValueError, e:
            show_hidden = False

        self.render(
            'list-directory.html',
            path=path,
            breadcrumbs=_compute_breadcrumbs(path, show_hidden),
            files_hidden=_contains_hidden_files(n),
            hidden_shown=show_hidden,
            dir_contents=_compute_dir_contents(n, path, show_hidden))

    def _get_file(self, path, n):
        """Process a request on a file.

        Return value is either a file object, or None (indicating an error).
        In either case, the headers are sent.
        """
        ctype = self._guess_type(path)

        self.set_header("Last-Modified", self.date_time_string(n.mtime))
        self.set_header("Content-Type", ctype)
        size = n.size()
        self.set_header("Content-Length", str(size))
        assert(len(n.hash) == 20)
        self.set_header("Etag", n.hash.encode('hex'))

        if self.request.method != 'HEAD':
            self.flush()
            f = n.open()
            it = chunkyreader(f)
            def write_more(me):
                try:
                    blob = it.next()
                except StopIteration:
                    f.close()
                    self.finish()
                    return
                self.request.connection.stream.write(blob,
                                                     callback=lambda: me(me))
            write_more(write_more)

    def _guess_type(self, path):
        """Guess the type of a file.

        Argument is a PATH (a filename).

        Return value is a string of the form type/subtype,
        usable for a MIME Content-type header.

        The default implementation looks the file's extension
        up in the table self.extensions_map, using application/octet-stream
        as a default; however it would be permissible (if
        slow) to look inside the data to make a better guess.
        """
        base, ext = posixpath.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        else:
            return self.extensions_map['']

    if not mimetypes.inited:
        mimetypes.init() # try to read system mime.types
    extensions_map = mimetypes.types_map.copy()
    extensions_map.update({
        '': 'text/plain', # Default
        '.py': 'text/plain',
        '.c': 'text/plain',
        '.h': 'text/plain',
        })

    def date_time_string(self, t):
        return time.strftime('%a, %d %b %Y %H:%M:%S', time.gmtime(t))


optspec = """
bup web [[hostname]:port]
--
human-readable    display human readable file sizes (i.e. 3.9K, 4.7M)
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])

if len(extra) > 1:
    o.fatal("at most one argument expected")

address = ('127.0.0.1', 8080)
if len(extra) > 0:
    addressl = extra[0].split(':', 1)
    addressl[1] = int(addressl[1])
    address = tuple(addressl)

git.check_repo_or_die()
top = vfs.RefList(None)

settings = dict(
    debug = 1,
    template_path = resource_path('web'),
    static_path = resource_path('web/static')
)

# Disable buffering on stdout, for debug messages
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

application = tornado.web.Application([
    (r"(/.*)", BupRequestHandler),
], **settings)

if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(address[1], address=address[0])

    try:
        sock = http_server._socket # tornado < 2.0
    except AttributeError, e:
        sock = http_server._sockets.values()[0]

    print "Serving HTTP on %s:%d..." % sock.getsockname()
    loop = tornado.ioloop.IOLoop.instance()
    loop.start()


########NEW FILE########
__FILENAME__ = xstat-cmd
#!/usr/bin/env python
# Copyright (C) 2010 Rob Browning
#
# This code is covered under the terms of the GNU Library General
# Public License as described in the bup LICENSE file.
import sys, stat, errno
from bup import metadata, options, xstat
from bup.helpers import handle_ctrl_c, parse_timestamp, saved_errors, \
    add_error, log


def parse_timestamp_arg(field, value):
    res = str(value) # Undo autoconversion.
    try:
        res = parse_timestamp(res)
    except ValueError, ex:
        if ex.args:
            o.fatal('unable to parse %s resolution "%s" (%s)'
                    % (field, value, ex))
        else:
            o.fatal('unable to parse %s resolution "%s"' % (field, value))

    if res != 1 and res % 10:
        o.fatal('%s resolution "%s" must be a power of 10' % (field, value))
    return res


optspec = """
bup xstat pathinfo [OPTION ...] <PATH ...>
--
v,verbose       increase log output (can be used more than once)
q,quiet         don't show progress meter
exclude-fields= exclude comma-separated fields
include-fields= include comma-separated fields (definitive if first)
atime-resolution=  limit s, ms, us, ns, 10ns (value must be a power of 10) [ns]
mtime-resolution=  limit s, ms, us, ns, 10ns (value must be a power of 10) [ns]
ctime-resolution=  limit s, ms, us, ns, 10ns (value must be a power of 10) [ns]
"""

target_filename = ''
active_fields = metadata.all_fields

handle_ctrl_c()

o = options.Options(optspec)
(opt, flags, remainder) = o.parse(sys.argv[1:])

atime_resolution = parse_timestamp_arg('atime', opt.atime_resolution)
mtime_resolution = parse_timestamp_arg('mtime', opt.mtime_resolution)
ctime_resolution = parse_timestamp_arg('ctime', opt.ctime_resolution)

treat_include_fields_as_definitive = True
for flag, value in flags:
    if flag == '--exclude-fields':
        exclude_fields = frozenset(value.split(','))
        for f in exclude_fields:
            if not f in metadata.all_fields:
                o.fatal(f + ' is not a valid field name')
        active_fields = active_fields - exclude_fields
        treat_include_fields_as_definitive = False
    elif flag == '--include-fields':
        include_fields = frozenset(value.split(','))
        for f in include_fields:
            if not f in metadata.all_fields:
                o.fatal(f + ' is not a valid field name')
        if treat_include_fields_as_definitive:
            active_fields = include_fields
            treat_include_fields_as_definitive = False
        else:
            active_fields = active_fields | include_fields

opt.verbose = opt.verbose or 0
opt.quiet = opt.quiet or 0
metadata.verbose = opt.verbose - opt.quiet

first_path = True
for path in remainder:
    try:
        m = metadata.from_path(path, archive_path = path)
    except (OSError,IOError), e:
        if e.errno == errno.ENOENT:
            add_error(e)
            continue
        else:
            raise
    if metadata.verbose >= 0:
        if not first_path:
            print
        if atime_resolution != 1:
            m.atime = (m.atime / atime_resolution) * atime_resolution
        if mtime_resolution != 1:
            m.mtime = (m.mtime / mtime_resolution) * mtime_resolution
        if ctime_resolution != 1:
            m.ctime = (m.ctime / ctime_resolution) * ctime_resolution
        print metadata.detailed_str(m, active_fields)
        first_path = False

if saved_errors:
    log('WARNING: %d errors encountered.\n' % len(saved_errors))
    sys.exit(1)
else:
    sys.exit(0)

########NEW FILE########
__FILENAME__ = bloom
"""Discussion of bloom constants for bup:

There are four basic things to consider when building a bloom filter:
The size, in bits, of the filter
The capacity, in entries, of the filter
The probability of a false positive that is tolerable
The number of bits readily available to use for addressing filter bits

There is one major tunable that is not directly related to the above:
k: the number of bits set in the filter per entry

Here's a wall of numbers showing the relationship between k; the ratio between
the filter size in bits and the entries in the filter; and pfalse_positive:

mn|k=3    |k=4    |k=5    |k=6    |k=7    |k=8    |k=9    |k=10   |k=11
 8|3.05794|2.39687|2.16792|2.15771|2.29297|2.54917|2.92244|3.41909|4.05091
 9|2.27780|1.65770|1.40703|1.32721|1.34892|1.44631|1.61138|1.84491|2.15259
10|1.74106|1.18133|0.94309|0.84362|0.81937|0.84555|0.91270|1.01859|1.16495
11|1.36005|0.86373|0.65018|0.55222|0.51259|0.50864|0.53098|0.57616|0.64387
12|1.08231|0.64568|0.45945|0.37108|0.32939|0.31424|0.31695|0.33387|0.36380
13|0.87517|0.49210|0.33183|0.25527|0.21689|0.19897|0.19384|0.19804|0.21013
14|0.71759|0.38147|0.24433|0.17934|0.14601|0.12887|0.12127|0.12012|0.12399
15|0.59562|0.30019|0.18303|0.12840|0.10028|0.08523|0.07749|0.07440|0.07468
16|0.49977|0.23941|0.13925|0.09351|0.07015|0.05745|0.05049|0.04700|0.04587
17|0.42340|0.19323|0.10742|0.06916|0.04990|0.03941|0.03350|0.03024|0.02870
18|0.36181|0.15765|0.08392|0.05188|0.03604|0.02748|0.02260|0.01980|0.01827
19|0.31160|0.12989|0.06632|0.03942|0.02640|0.01945|0.01549|0.01317|0.01182
20|0.27026|0.10797|0.05296|0.03031|0.01959|0.01396|0.01077|0.00889|0.00777
21|0.23591|0.09048|0.04269|0.02356|0.01471|0.01014|0.00759|0.00609|0.00518
22|0.20714|0.07639|0.03473|0.01850|0.01117|0.00746|0.00542|0.00423|0.00350
23|0.18287|0.06493|0.02847|0.01466|0.00856|0.00555|0.00392|0.00297|0.00240
24|0.16224|0.05554|0.02352|0.01171|0.00663|0.00417|0.00286|0.00211|0.00166
25|0.14459|0.04779|0.01957|0.00944|0.00518|0.00316|0.00211|0.00152|0.00116
26|0.12942|0.04135|0.01639|0.00766|0.00408|0.00242|0.00157|0.00110|0.00082
27|0.11629|0.03595|0.01381|0.00626|0.00324|0.00187|0.00118|0.00081|0.00059
28|0.10489|0.03141|0.01170|0.00515|0.00259|0.00146|0.00090|0.00060|0.00043
29|0.09492|0.02756|0.00996|0.00426|0.00209|0.00114|0.00069|0.00045|0.00031
30|0.08618|0.02428|0.00853|0.00355|0.00169|0.00090|0.00053|0.00034|0.00023
31|0.07848|0.02147|0.00733|0.00297|0.00138|0.00072|0.00041|0.00025|0.00017
32|0.07167|0.01906|0.00633|0.00250|0.00113|0.00057|0.00032|0.00019|0.00013

Here's a table showing available repository size for a given pfalse_positive
and three values of k (assuming we only use the 160 bit SHA1 for addressing the
filter and 8192bytes per object):

pfalse|obj k=4     |cap k=4    |obj k=5  |cap k=5    |obj k=6 |cap k=6
2.500%|139333497228|1038.11 TiB|558711157|4262.63 GiB|13815755|105.41 GiB
1.000%|104489450934| 778.50 TiB|436090254|3327.10 GiB|11077519| 84.51 GiB
0.125%| 57254889824| 426.58 TiB|261732190|1996.86 GiB| 7063017| 55.89 GiB

This eliminates pretty neatly any k>6 as long as we use the raw SHA for
addressing.

filter size scales linearly with repository size for a given k and pfalse.

Here's a table of filter sizes for a 1 TiB repository:

pfalse| k=3        | k=4        | k=5        | k=6
2.500%| 138.78 MiB | 126.26 MiB | 123.00 MiB | 123.37 MiB
1.000%| 197.83 MiB | 168.36 MiB | 157.58 MiB | 153.87 MiB
0.125%| 421.14 MiB | 307.26 MiB | 262.56 MiB | 241.32 MiB

For bup:
* We want the bloom filter to fit in memory; if it doesn't, the k pagefaults
per lookup will be worse than the two required for midx.
* We want the pfalse_positive to be low enough that the cost of sometimes
faulting on the midx doesn't overcome the benefit of the bloom filter.
* We have readily available 160 bits for addressing the filter.
* We want to be able to have a single bloom address entire repositories of
reasonable size.

Based on these parameters, a combination of k=4 and k=5 provides the behavior
that bup needs.  As such, I've implemented bloom addressing, adding and
checking functions in C for these two values.  Because k=5 requires less space
and gives better overall pfalse_positive performance, it is preferred if a
table with k=5 can represent the repository.

None of this tells us what max_pfalse_positive to choose.

Brandon Low <lostlogic@lostlogicx.com> 2011-02-04
"""
import sys, os, math, mmap
from bup import _helpers
from bup.helpers import *

BLOOM_VERSION = 2
MAX_BITS_EACH = 32 # Kinda arbitrary, but 4 bytes per entry is pretty big
MAX_BLOOM_BITS = {4: 37, 5: 29} # 160/k-log2(8)
MAX_PFALSE_POSITIVE = 1. # Totally arbitrary, needs benchmarking

_total_searches = 0
_total_steps = 0

bloom_contains = _helpers.bloom_contains
bloom_add = _helpers.bloom_add

# FIXME: check bloom create() and ShaBloom handling/ownership of "f".
# The ownership semantics should be clarified since the caller needs
# to know who is responsible for closing it.

class ShaBloom:
    """Wrapper which contains data from multiple index files. """
    def __init__(self, filename, f=None, readwrite=False, expected=-1):
        self.name = filename
        self.rwfile = None
        self.map = None
        assert(filename.endswith('.bloom'))
        if readwrite:
            assert(expected > 0)
            self.rwfile = f = f or open(filename, 'r+b')
            f.seek(0)

            # Decide if we want to mmap() the pages as writable ('immediate'
            # write) or else map them privately for later writing back to
            # the file ('delayed' write).  A bloom table's write access
            # pattern is such that we dirty almost all the pages after adding
            # very few entries.  But the table is so big that dirtying
            # *all* the pages often exceeds Linux's default
            # /proc/sys/vm/dirty_ratio or /proc/sys/vm/dirty_background_ratio,
            # thus causing it to start flushing the table before we're
            # finished... even though there's more than enough space to
            # store the bloom table in RAM.
            #
            # To work around that behaviour, if we calculate that we'll
            # probably end up touching the whole table anyway (at least
            # one bit flipped per memory page), let's use a "private" mmap,
            # which defeats Linux's ability to flush it to disk.  Then we'll
            # flush it as one big lump during close().
            pages = os.fstat(f.fileno()).st_size / 4096 * 5 # assume k=5
            self.delaywrite = expected > pages
            debug1('bloom: delaywrite=%r\n' % self.delaywrite)
            if self.delaywrite:
                self.map = mmap_readwrite_private(self.rwfile, close=False)
            else:
                self.map = mmap_readwrite(self.rwfile, close=False)
        else:
            self.rwfile = None
            f = f or open(filename, 'rb')
            self.map = mmap_read(f)
        got = str(self.map[0:4])
        if got != 'BLOM':
            log('Warning: invalid BLOM header (%r) in %r\n' % (got, filename))
            return self._init_failed()
        ver = struct.unpack('!I', self.map[4:8])[0]
        if ver < BLOOM_VERSION:
            log('Warning: ignoring old-style (v%d) bloom %r\n' 
                % (ver, filename))
            return self._init_failed()
        if ver > BLOOM_VERSION:
            log('Warning: ignoring too-new (v%d) bloom %r\n'
                % (ver, filename))
            return self._init_failed()

        self.bits, self.k, self.entries = struct.unpack('!HHI', self.map[8:16])
        idxnamestr = str(self.map[16 + 2**self.bits:])
        if idxnamestr:
            self.idxnames = idxnamestr.split('\0')
        else:
            self.idxnames = []

    def _init_failed(self):
        if self.map:
            self.map = None
        if self.rwfile:
            self.rwfile.close()
            self.rwfile = None
        self.idxnames = []
        self.bits = self.entries = 0

    def valid(self):
        return self.map and self.bits

    def __del__(self):
        self.close()

    def close(self):
        if self.map and self.rwfile:
            debug2("bloom: closing with %d entries\n" % self.entries)
            self.map[12:16] = struct.pack('!I', self.entries)
            if self.delaywrite:
                self.rwfile.seek(0)
                self.rwfile.write(self.map)
            else:
                self.map.flush()
            self.rwfile.seek(16 + 2**self.bits)
            if self.idxnames:
                self.rwfile.write('\0'.join(self.idxnames))
        self._init_failed()

    def pfalse_positive(self, additional=0):
        n = self.entries + additional
        m = 8*2**self.bits
        k = self.k
        return 100*(1-math.exp(-k*float(n)/m))**k

    def add_idx(self, ix):
        """Add the object to the filter, return current pfalse_positive."""
        if not self.map:
            raise Exception("Cannot add to closed bloom")
        self.entries += bloom_add(self.map, ix.shatable, self.bits, self.k)
        self.idxnames.append(os.path.basename(ix.name))

    def exists(self, sha):
        """Return nonempty if the object probably exists in the bloom filter.

        If this function returns false, the object definitely does not exist.
        If it returns true, there is a small probability that it exists
        anyway, so you'll have to check it some other way.
        """
        global _total_searches, _total_steps
        _total_searches += 1
        if not self.map:
            return None
        found, steps = bloom_contains(self.map, str(sha), self.bits, self.k)
        _total_steps += steps
        return found

    def __len__(self):
        return int(self.entries)


def create(name, expected, delaywrite=None, f=None, k=None):
    """Create and return a bloom filter for `expected` entries."""
    bits = int(math.floor(math.log(expected*MAX_BITS_EACH/8,2)))
    k = k or ((bits <= MAX_BLOOM_BITS[5]) and 5 or 4)
    if bits > MAX_BLOOM_BITS[k]:
        log('bloom: warning, max bits exceeded, non-optimal\n')
        bits = MAX_BLOOM_BITS[k]
    debug1('bloom: using 2^%d bytes and %d hash functions\n' % (bits, k))
    f = f or open(name, 'w+b')
    f.write('BLOM')
    f.write(struct.pack('!IHHI', BLOOM_VERSION, bits, k, 0))
    assert(f.tell() == 16)
    # NOTE: On some systems this will not extend+zerofill, but it does on
    # darwin, linux, bsd and solaris.
    f.truncate(16+2**bits)
    f.seek(0)
    if delaywrite != None and not delaywrite:
        # tell it to expect very few objects, forcing a direct mmap
        expected = 1
    return ShaBloom(name, f=f, readwrite=True, expected=expected)


########NEW FILE########
__FILENAME__ = client
import re, struct, errno, time, zlib
from bup import git, ssh
from bup.helpers import *

bwlimit = None


class ClientError(Exception):
    pass


def _raw_write_bwlimit(f, buf, bwcount, bwtime):
    if not bwlimit:
        f.write(buf)
        return (len(buf), time.time())
    else:
        # We want to write in reasonably large blocks, but not so large that
        # they're likely to overflow a router's queue.  So our bwlimit timing
        # has to be pretty granular.  Also, if it takes too long from one
        # transmit to the next, we can't just make up for lost time to bring
        # the average back up to bwlimit - that will risk overflowing the
        # outbound queue, which defeats the purpose.  So if we fall behind
        # by more than one block delay, we shouldn't ever try to catch up.
        for i in xrange(0,len(buf),4096):
            now = time.time()
            next = max(now, bwtime + 1.0*bwcount/bwlimit)
            time.sleep(next-now)
            sub = buf[i:i+4096]
            f.write(sub)
            bwcount = len(sub)  # might be less than 4096
            bwtime = next
        return (bwcount, bwtime)


def parse_remote(remote):
    protocol = r'([a-z]+)://'
    host = r'(?P<sb>\[)?((?(sb)[0-9a-f:]+|[^:/]+))(?(sb)\])'
    port = r'(?::(\d+))?'
    path = r'(/.*)?'
    url_match = re.match(
            '%s(?:%s%s)?%s' % (protocol, host, port, path), remote, re.I)
    if url_match:
        if not url_match.group(1) in ('ssh', 'bup', 'file'):
            raise ClientError, 'unexpected protocol: %s' % url_match.group(1)
        return url_match.group(1,3,4,5)
    else:
        rs = remote.split(':', 1)
        if len(rs) == 1 or rs[0] in ('', '-'):
            return 'file', None, None, rs[-1]
        else:
            return 'ssh', rs[0], None, rs[1]


class Client:
    def __init__(self, remote, create=False):
        self._busy = self.conn = None
        self.sock = self.p = self.pout = self.pin = None
        is_reverse = os.environ.get('BUP_SERVER_REVERSE')
        if is_reverse:
            assert(not remote)
            remote = '%s:' % is_reverse
        (self.protocol, self.host, self.port, self.dir) = parse_remote(remote)
        self.cachedir = git.repo('index-cache/%s'
                                 % re.sub(r'[^@\w]', '_', 
                                          "%s:%s" % (self.host, self.dir)))
        if is_reverse:
            self.pout = os.fdopen(3, 'rb')
            self.pin = os.fdopen(4, 'wb')
            self.conn = Conn(self.pout, self.pin)
        else:
            if self.protocol in ('ssh', 'file'):
                try:
                    # FIXME: ssh and file shouldn't use the same module
                    self.p = ssh.connect(self.host, self.port, 'server')
                    self.pout = self.p.stdout
                    self.pin = self.p.stdin
                    self.conn = Conn(self.pout, self.pin)
                except OSError, e:
                    raise ClientError, 'connect: %s' % e, sys.exc_info()[2]
            elif self.protocol == 'bup':
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.host, atoi(self.port) or 1982))
                self.sockw = self.sock.makefile('wb')
                self.conn = DemuxConn(self.sock.fileno(), self.sockw)
        if self.dir:
            self.dir = re.sub(r'[\r\n]', ' ', self.dir)
            if create:
                self.conn.write('init-dir %s\n' % self.dir)
            else:
                self.conn.write('set-dir %s\n' % self.dir)
            self.check_ok()
        self.sync_indexes()

    def __del__(self):
        try:
            self.close()
        except IOError, e:
            if e.errno == errno.EPIPE:
                pass
            else:
                raise

    def close(self):
        if self.conn and not self._busy:
            self.conn.write('quit\n')
        if self.pin:
            self.pin.close()
        if self.sock and self.sockw:
            self.sockw.close()
            self.sock.shutdown(socket.SHUT_WR)
        if self.conn:
            self.conn.close()
        if self.pout:
            self.pout.close()
        if self.sock:
            self.sock.close()
        if self.p:
            self.p.wait()
            rv = self.p.wait()
            if rv:
                raise ClientError('server tunnel returned exit code %d' % rv)
        self.conn = None
        self.sock = self.p = self.pin = self.pout = None

    def check_ok(self):
        if self.p:
            rv = self.p.poll()
            if rv != None:
                raise ClientError('server exited unexpectedly with code %r'
                                  % rv)
        try:
            return self.conn.check_ok()
        except Exception, e:
            raise ClientError, e, sys.exc_info()[2]

    def check_busy(self):
        if self._busy:
            raise ClientError('already busy with command %r' % self._busy)
        
    def ensure_busy(self):
        if not self._busy:
            raise ClientError('expected to be busy, but not busy?!')
        
    def _not_busy(self):
        self._busy = None

    def sync_indexes(self):
        self.check_busy()
        conn = self.conn
        mkdirp(self.cachedir)
        # All cached idxs are extra until proven otherwise
        extra = set()
        for f in os.listdir(self.cachedir):
            debug1('%s\n' % f)
            if f.endswith('.idx'):
                extra.add(f)
        needed = set()
        conn.write('list-indexes\n')
        for line in linereader(conn):
            if not line:
                break
            assert(line.find('/') < 0)
            parts = line.split(' ')
            idx = parts[0]
            if len(parts) == 2 and parts[1] == 'load' and idx not in extra:
                # If the server requests that we load an idx and we don't
                # already have a copy of it, it is needed
                needed.add(idx)
            # Any idx that the server has heard of is proven not extra
            extra.discard(idx)

        self.check_ok()
        debug1('client: removing extra indexes: %s\n' % extra)
        for idx in extra:
            os.unlink(os.path.join(self.cachedir, idx))
        debug1('client: server requested load of: %s\n' % needed)
        for idx in needed:
            self.sync_index(idx)
        git.auto_midx(self.cachedir)

    def sync_index(self, name):
        #debug1('requesting %r\n' % name)
        self.check_busy()
        mkdirp(self.cachedir)
        fn = os.path.join(self.cachedir, name)
        if os.path.exists(fn):
            msg = "won't request existing .idx, try `bup bloom --check %s`" % fn
            raise ClientError(msg)
        self.conn.write('send-index %s\n' % name)
        n = struct.unpack('!I', self.conn.read(4))[0]
        assert(n)
        f = open(fn + '.tmp', 'w')
        count = 0
        progress('Receiving index from server: %d/%d\r' % (count, n))
        for b in chunkyreader(self.conn, n):
            f.write(b)
            count += len(b)
            qprogress('Receiving index from server: %d/%d\r' % (count, n))
        progress('Receiving index from server: %d/%d, done.\n' % (count, n))
        self.check_ok()
        f.close()
        os.rename(fn + '.tmp', fn)

    def _make_objcache(self):
        return git.PackIdxList(self.cachedir)

    def _suggest_packs(self):
        ob = self._busy
        if ob:
            assert(ob == 'receive-objects-v2')
            self.conn.write('\xff\xff\xff\xff')  # suspend receive-objects-v2
        suggested = []
        for line in linereader(self.conn):
            if not line:
                break
            debug2('%s\n' % line)
            if line.startswith('index '):
                idx = line[6:]
                debug1('client: received index suggestion: %s\n'
                       % git.shorten_hash(idx))
                suggested.append(idx)
            else:
                assert(line.endswith('.idx'))
                debug1('client: completed writing pack, idx: %s\n'
                       % git.shorten_hash(line))
                suggested.append(line)
        self.check_ok()
        if ob:
            self._busy = None
        idx = None
        for idx in suggested:
            self.sync_index(idx)
        git.auto_midx(self.cachedir)
        if ob:
            self._busy = ob
            self.conn.write('%s\n' % ob)
        return idx

    def new_packwriter(self, compression_level = 1):
        self.check_busy()
        def _set_busy():
            self._busy = 'receive-objects-v2'
            self.conn.write('receive-objects-v2\n')
        return PackWriter_Remote(self.conn,
                                 objcache_maker = self._make_objcache,
                                 suggest_packs = self._suggest_packs,
                                 onopen = _set_busy,
                                 onclose = self._not_busy,
                                 ensure_busy = self.ensure_busy,
                                 compression_level = compression_level)

    def read_ref(self, refname):
        self.check_busy()
        self.conn.write('read-ref %s\n' % refname)
        r = self.conn.readline().strip()
        self.check_ok()
        if r:
            assert(len(r) == 40)   # hexified sha
            return r.decode('hex')
        else:
            return None   # nonexistent ref

    def update_ref(self, refname, newval, oldval):
        self.check_busy()
        self.conn.write('update-ref %s\n%s\n%s\n' 
                        % (refname, newval.encode('hex'),
                           (oldval or '').encode('hex')))
        self.check_ok()

    def cat(self, id):
        self.check_busy()
        self._busy = 'cat'
        self.conn.write('cat %s\n' % re.sub(r'[\n\r]', '_', id))
        while 1:
            sz = struct.unpack('!I', self.conn.read(4))[0]
            if not sz: break
            yield self.conn.read(sz)
        e = self.check_ok()
        self._not_busy()
        if e:
            raise KeyError(str(e))


class PackWriter_Remote(git.PackWriter):
    def __init__(self, conn, objcache_maker, suggest_packs,
                 onopen, onclose,
                 ensure_busy,
                 compression_level=1):
        git.PackWriter.__init__(self, objcache_maker)
        self.file = conn
        self.filename = 'remote socket'
        self.suggest_packs = suggest_packs
        self.onopen = onopen
        self.onclose = onclose
        self.ensure_busy = ensure_busy
        self._packopen = False
        self._bwcount = 0
        self._bwtime = time.time()

    def _open(self):
        if not self._packopen:
            self.onopen()
            self._packopen = True

    def _end(self):
        if self._packopen and self.file:
            self.file.write('\0\0\0\0')
            self._packopen = False
            self.onclose() # Unbusy
            self.objcache = None
            return self.suggest_packs() # Returns last idx received

    def close(self):
        id = self._end()
        self.file = None
        return id

    def abort(self):
        raise ClientError("don't know how to abort remote pack writing")

    def _raw_write(self, datalist, sha):
        assert(self.file)
        if not self._packopen:
            self._open()
        self.ensure_busy()
        data = ''.join(datalist)
        assert(data)
        assert(sha)
        crc = zlib.crc32(data) & 0xffffffff
        outbuf = ''.join((struct.pack('!I', len(data) + 20 + 4),
                          sha,
                          struct.pack('!I', crc),
                          data))
        try:
            (self._bwcount, self._bwtime) = _raw_write_bwlimit(
                    self.file, outbuf, self._bwcount, self._bwtime)
        except IOError, e:
            raise ClientError, e, sys.exc_info()[2]
        self.outbytes += len(data)
        self.count += 1

        if self.file.has_input():
            self.suggest_packs()
            self.objcache.refresh()

        return sha, crc

########NEW FILE########
__FILENAME__ = drecurse
import stat, os
from bup.helpers import *
import bup.xstat as xstat

try:
    O_LARGEFILE = os.O_LARGEFILE
except AttributeError:
    O_LARGEFILE = 0
try:
    O_NOFOLLOW = os.O_NOFOLLOW
except AttributeError:
    O_NOFOLLOW = 0


# the use of fchdir() and lstat() is for two reasons:
#  - help out the kernel by not making it repeatedly look up the absolute path
#  - avoid race conditions caused by doing listdir() on a changing symlink
class OsFile:
    def __init__(self, path):
        self.fd = None
        self.fd = os.open(path, os.O_RDONLY|O_LARGEFILE|O_NOFOLLOW|os.O_NDELAY)
        
    def __del__(self):
        if self.fd:
            fd = self.fd
            self.fd = None
            os.close(fd)

    def fchdir(self):
        os.fchdir(self.fd)

    def stat(self):
        return xstat.fstat(self.fd)


_IFMT = stat.S_IFMT(0xffffffff)  # avoid function call in inner loop
def _dirlist():
    l = []
    for n in os.listdir('.'):
        try:
            st = xstat.lstat(n)
        except OSError, e:
            add_error(Exception('%s: %s' % (realpath(n), str(e))))
            continue
        if (st.st_mode & _IFMT) == stat.S_IFDIR:
            n += '/'
        l.append((n,st))
    l.sort(reverse=True)
    return l


def _recursive_dirlist(prepend, xdev, bup_dir=None,
                       excluded_paths=None,
                       exclude_rxs=None):
    for (name,pst) in _dirlist():
        path = prepend + name
        if excluded_paths:
            if os.path.normpath(path) in excluded_paths:
                debug1('Skipping %r: excluded.\n' % path)
                continue
        if exclude_rxs and should_rx_exclude_path(path, exclude_rxs):
            continue
        if name.endswith('/'):
            if bup_dir != None:
                if os.path.normpath(path) == bup_dir:
                    debug1('Skipping BUP_DIR.\n')
                    continue
            if xdev != None and pst.st_dev != xdev:
                debug1('Skipping contents of %r: different filesystem.\n' % path)
            else:
                try:
                    OsFile(name).fchdir()
                except OSError, e:
                    add_error('%s: %s' % (prepend, e))
                else:
                    for i in _recursive_dirlist(prepend=prepend+name, xdev=xdev,
                                                bup_dir=bup_dir,
                                                excluded_paths=excluded_paths,
                                                exclude_rxs=exclude_rxs):
                        yield i
                    os.chdir('..')
        yield (path, pst)


def recursive_dirlist(paths, xdev, bup_dir=None, excluded_paths=None,
                      exclude_rxs=None):
    startdir = OsFile('.')
    try:
        assert(type(paths) != type(''))
        for path in paths:
            try:
                pst = xstat.lstat(path)
                if stat.S_ISLNK(pst.st_mode):
                    yield (path, pst)
                    continue
            except OSError, e:
                add_error('recursive_dirlist: %s' % e)
                continue
            try:
                pfile = OsFile(path)
            except OSError, e:
                add_error(e)
                continue
            pst = pfile.stat()
            if xdev:
                xdev = pst.st_dev
            else:
                xdev = None
            if stat.S_ISDIR(pst.st_mode):
                pfile.fchdir()
                prepend = os.path.join(path, '')
                for i in _recursive_dirlist(prepend=prepend, xdev=xdev,
                                            bup_dir=bup_dir,
                                            excluded_paths=excluded_paths,
                                            exclude_rxs=exclude_rxs):
                    yield i
                startdir.fchdir()
            else:
                prepend = path
            yield (prepend,pst)
    except:
        try:
            startdir.fchdir()
        except:
            pass
        raise

########NEW FILE########
__FILENAME__ = git
"""Git interaction library.
bup repositories are in Git format. This library allows us to
interact with the Git data structures.
"""
import os, sys, zlib, time, subprocess, struct, stat, re, tempfile, glob
from collections import namedtuple

from bup.helpers import *
from bup import _helpers, path, midx, bloom, xstat

max_pack_size = 1000*1000*1000  # larger packs will slow down pruning
max_pack_objects = 200*1000  # cache memory usage is about 83 bytes per object

verbose = 0
ignore_midx = 0
repodir = None

_typemap =  { 'blob':3, 'tree':2, 'commit':1, 'tag':4 }
_typermap = { 3:'blob', 2:'tree', 1:'commit', 4:'tag' }

_total_searches = 0
_total_steps = 0


class GitError(Exception):
    pass


def parse_tz_offset(s):
    """UTC offset in seconds."""
    tz_off = (int(s[1:3]) * 60 * 60) + (int(s[3:5]) * 60)
    if s[0] == '-':
        return - tz_off
    return tz_off


# FIXME: derived from http://git.rsbx.net/Documents/Git_Data_Formats.txt
# Make sure that's authoritative.
_start_end_char = r'[^ .,:;<>"\'\0\n]'
_content_char = r'[^\0\n<>]'
_safe_str_rx = '(?:%s{1,2}|(?:%s%s*%s))' \
    % (_start_end_char,
       _start_end_char, _content_char, _start_end_char)
_tz_rx = r'[-+]\d\d[0-5]\d'
_parent_rx = r'(?:parent [abcdefABCDEF0123456789]{40}\n)'
_commit_rx = re.compile(r'''tree (?P<tree>[abcdefABCDEF0123456789]{40})
(?P<parents>%s*)author (?P<author_name>%s) <(?P<author_mail>%s)> (?P<asec>\d+) (?P<atz>%s)
committer (?P<committer_name>%s) <(?P<committer_mail>%s)> (?P<csec>\d+) (?P<ctz>%s)

(?P<message>(?:.|\n)*)''' % (_parent_rx,
                             _safe_str_rx, _safe_str_rx, _tz_rx,
                             _safe_str_rx, _safe_str_rx, _tz_rx))
_parent_hash_rx = re.compile(r'\s*parent ([abcdefABCDEF0123456789]{40})\s*')


# Note that the author_sec and committer_sec values are (UTC) epoch seconds.
CommitInfo = namedtuple('CommitInfo', ['tree', 'parents',
                                       'author_name', 'author_mail',
                                       'author_sec', 'author_offset',
                                       'committer_name', 'committer_mail',
                                       'committer_sec', 'committer_offset',
                                       'message'])

def parse_commit(content):
    commit_match = re.match(_commit_rx, content)
    if not commit_match:
        raise Exception('cannot parse commit %r' % content)
    matches = commit_match.groupdict()
    return CommitInfo(tree=matches['tree'],
                      parents=re.findall(_parent_hash_rx, matches['parents']),
                      author_name=matches['author_name'],
                      author_mail=matches['author_mail'],
                      author_sec=int(matches['asec']),
                      author_offset=parse_tz_offset(matches['atz']),
                      committer_name=matches['committer_name'],
                      committer_mail=matches['committer_mail'],
                      committer_sec=int(matches['csec']),
                      committer_offset=parse_tz_offset(matches['ctz']),
                      message=matches['message'])


def get_commit_items(id, cp):
    commit_it = cp.get(id)
    assert(commit_it.next() == 'commit')
    commit_content = ''.join(commit_it)
    return parse_commit(commit_content)


def repo(sub = ''):
    """Get the path to the git repository or one of its subdirectories."""
    global repodir
    if not repodir:
        raise GitError('You should call check_repo_or_die()')

    # If there's a .git subdirectory, then the actual repo is in there.
    gd = os.path.join(repodir, '.git')
    if os.path.exists(gd):
        repodir = gd

    return os.path.join(repodir, sub)


def shorten_hash(s):
    return re.sub(r'([^0-9a-z]|\b)([0-9a-z]{7})[0-9a-z]{33}([^0-9a-z]|\b)',
                  r'\1\2*\3', s)


def repo_rel(path):
    full = os.path.abspath(path)
    fullrepo = os.path.abspath(repo(''))
    if not fullrepo.endswith('/'):
        fullrepo += '/'
    if full.startswith(fullrepo):
        path = full[len(fullrepo):]
    if path.startswith('index-cache/'):
        path = path[len('index-cache/'):]
    return shorten_hash(path)


def all_packdirs():
    paths = [repo('objects/pack')]
    paths += glob.glob(repo('index-cache/*/.'))
    return paths


def auto_midx(objdir):
    args = [path.exe(), 'midx', '--auto', '--dir', objdir]
    try:
        rv = subprocess.call(args, stdout=open('/dev/null', 'w'))
    except OSError, e:
        # make sure 'args' gets printed to help with debugging
        add_error('%r: exception: %s' % (args, e))
        raise
    if rv:
        add_error('%r: returned %d' % (args, rv))

    args = [path.exe(), 'bloom', '--dir', objdir]
    try:
        rv = subprocess.call(args, stdout=open('/dev/null', 'w'))
    except OSError, e:
        # make sure 'args' gets printed to help with debugging
        add_error('%r: exception: %s' % (args, e))
        raise
    if rv:
        add_error('%r: returned %d' % (args, rv))


def mangle_name(name, mode, gitmode):
    """Mangle a file name to present an abstract name for segmented files.
    Mangled file names will have the ".bup" extension added to them. If a
    file's name already ends with ".bup", a ".bupl" extension is added to
    disambiguate normal files from semgmented ones.
    """
    if stat.S_ISREG(mode) and not stat.S_ISREG(gitmode):
        return name + '.bup'
    elif name.endswith('.bup') or name[:-1].endswith('.bup'):
        return name + '.bupl'
    else:
        return name


(BUP_NORMAL, BUP_CHUNKED) = (0,1)
def demangle_name(name):
    """Remove name mangling from a file name, if necessary.

    The return value is a tuple (demangled_filename,mode), where mode is one of
    the following:

    * BUP_NORMAL  : files that should be read as-is from the repository
    * BUP_CHUNKED : files that were chunked and need to be assembled

    For more information on the name mangling algorythm, see mangle_name()
    """
    if name.endswith('.bupl'):
        return (name[:-5], BUP_NORMAL)
    elif name.endswith('.bup'):
        return (name[:-4], BUP_CHUNKED)
    else:
        return (name, BUP_NORMAL)


def calc_hash(type, content):
    """Calculate some content's hash in the Git fashion."""
    header = '%s %d\0' % (type, len(content))
    sum = Sha1(header)
    sum.update(content)
    return sum.digest()


def shalist_item_sort_key(ent):
    (mode, name, id) = ent
    assert(mode+0 == mode)
    if stat.S_ISDIR(mode):
        return name + '/'
    else:
        return name


def tree_encode(shalist):
    """Generate a git tree object from (mode,name,hash) tuples."""
    shalist = sorted(shalist, key = shalist_item_sort_key)
    l = []
    for (mode,name,bin) in shalist:
        assert(mode)
        assert(mode+0 == mode)
        assert(name)
        assert(len(bin) == 20)
        s = '%o %s\0%s' % (mode,name,bin)
        assert(s[0] != '0')  # 0-padded octal is not acceptable in a git tree
        l.append(s)
    return ''.join(l)


def tree_decode(buf):
    """Generate a list of (mode,name,hash) from the git tree object in buf."""
    ofs = 0
    while ofs < len(buf):
        z = buf.find('\0', ofs)
        assert(z > ofs)
        spl = buf[ofs:z].split(' ', 1)
        assert(len(spl) == 2)
        mode,name = spl
        sha = buf[z+1:z+1+20]
        ofs = z+1+20
        yield (int(mode, 8), name, sha)


def _encode_packobj(type, content, compression_level=1):
    szout = ''
    sz = len(content)
    szbits = (sz & 0x0f) | (_typemap[type]<<4)
    sz >>= 4
    while 1:
        if sz: szbits |= 0x80
        szout += chr(szbits)
        if not sz:
            break
        szbits = sz & 0x7f
        sz >>= 7
    if compression_level > 9:
        compression_level = 9
    elif compression_level < 0:
        compression_level = 0
    z = zlib.compressobj(compression_level)
    yield szout
    yield z.compress(content)
    yield z.flush()


def _encode_looseobj(type, content, compression_level=1):
    z = zlib.compressobj(compression_level)
    yield z.compress('%s %d\0' % (type, len(content)))
    yield z.compress(content)
    yield z.flush()


def _decode_looseobj(buf):
    assert(buf);
    s = zlib.decompress(buf)
    i = s.find('\0')
    assert(i > 0)
    l = s[:i].split(' ')
    type = l[0]
    sz = int(l[1])
    content = s[i+1:]
    assert(type in _typemap)
    assert(sz == len(content))
    return (type, content)


def _decode_packobj(buf):
    assert(buf)
    c = ord(buf[0])
    type = _typermap[(c & 0x70) >> 4]
    sz = c & 0x0f
    shift = 4
    i = 0
    while c & 0x80:
        i += 1
        c = ord(buf[i])
        sz |= (c & 0x7f) << shift
        shift += 7
        if not (c & 0x80):
            break
    return (type, zlib.decompress(buf[i+1:]))


class PackIdx:
    def __init__(self):
        assert(0)

    def find_offset(self, hash):
        """Get the offset of an object inside the index file."""
        idx = self._idx_from_hash(hash)
        if idx != None:
            return self._ofs_from_idx(idx)
        return None

    def exists(self, hash, want_source=False):
        """Return nonempty if the object exists in this index."""
        if hash and (self._idx_from_hash(hash) != None):
            return want_source and os.path.basename(self.name) or True
        return None

    def __len__(self):
        return int(self.fanout[255])

    def _idx_from_hash(self, hash):
        global _total_searches, _total_steps
        _total_searches += 1
        assert(len(hash) == 20)
        b1 = ord(hash[0])
        start = self.fanout[b1-1] # range -1..254
        end = self.fanout[b1] # range 0..255
        want = str(hash)
        _total_steps += 1  # lookup table is a step
        while start < end:
            _total_steps += 1
            mid = start + (end-start)/2
            v = self._idx_to_hash(mid)
            if v < want:
                start = mid+1
            elif v > want:
                end = mid
            else: # got it!
                return mid
        return None


class PackIdxV1(PackIdx):
    """Object representation of a Git pack index (version 1) file."""
    def __init__(self, filename, f):
        self.name = filename
        self.idxnames = [self.name]
        self.map = mmap_read(f)
        self.fanout = list(struct.unpack('!256I',
                                         str(buffer(self.map, 0, 256*4))))
        self.fanout.append(0)  # entry "-1"
        nsha = self.fanout[255]
        self.sha_ofs = 256*4
        self.shatable = buffer(self.map, self.sha_ofs, nsha*24)

    def _ofs_from_idx(self, idx):
        return struct.unpack('!I', str(self.shatable[idx*24 : idx*24+4]))[0]

    def _idx_to_hash(self, idx):
        return str(self.shatable[idx*24+4 : idx*24+24])

    def __iter__(self):
        for i in xrange(self.fanout[255]):
            yield buffer(self.map, 256*4 + 24*i + 4, 20)


class PackIdxV2(PackIdx):
    """Object representation of a Git pack index (version 2) file."""
    def __init__(self, filename, f):
        self.name = filename
        self.idxnames = [self.name]
        self.map = mmap_read(f)
        assert(str(self.map[0:8]) == '\377tOc\0\0\0\2')
        self.fanout = list(struct.unpack('!256I',
                                         str(buffer(self.map, 8, 256*4))))
        self.fanout.append(0)  # entry "-1"
        nsha = self.fanout[255]
        self.sha_ofs = 8 + 256*4
        self.shatable = buffer(self.map, self.sha_ofs, nsha*20)
        self.ofstable = buffer(self.map,
                               self.sha_ofs + nsha*20 + nsha*4,
                               nsha*4)
        self.ofs64table = buffer(self.map,
                                 8 + 256*4 + nsha*20 + nsha*4 + nsha*4)

    def _ofs_from_idx(self, idx):
        ofs = struct.unpack('!I', str(buffer(self.ofstable, idx*4, 4)))[0]
        if ofs & 0x80000000:
            idx64 = ofs & 0x7fffffff
            ofs = struct.unpack('!Q',
                                str(buffer(self.ofs64table, idx64*8, 8)))[0]
        return ofs

    def _idx_to_hash(self, idx):
        return str(self.shatable[idx*20:(idx+1)*20])

    def __iter__(self):
        for i in xrange(self.fanout[255]):
            yield buffer(self.map, 8 + 256*4 + 20*i, 20)


_mpi_count = 0
class PackIdxList:
    def __init__(self, dir):
        global _mpi_count
        assert(_mpi_count == 0) # these things suck tons of VM; don't waste it
        _mpi_count += 1
        self.dir = dir
        self.also = set()
        self.packs = []
        self.do_bloom = False
        self.bloom = None
        self.refresh()

    def __del__(self):
        global _mpi_count
        _mpi_count -= 1
        assert(_mpi_count == 0)

    def __iter__(self):
        return iter(idxmerge(self.packs))

    def __len__(self):
        return sum(len(pack) for pack in self.packs)

    def exists(self, hash, want_source=False):
        """Return nonempty if the object exists in the index files."""
        global _total_searches
        _total_searches += 1
        if hash in self.also:
            return True
        if self.do_bloom and self.bloom:
            if self.bloom.exists(hash):
                self.do_bloom = False
            else:
                _total_searches -= 1  # was counted by bloom
                return None
        for i in xrange(len(self.packs)):
            p = self.packs[i]
            _total_searches -= 1  # will be incremented by sub-pack
            ix = p.exists(hash, want_source=want_source)
            if ix:
                # reorder so most recently used packs are searched first
                self.packs = [p] + self.packs[:i] + self.packs[i+1:]
                return ix
        self.do_bloom = True
        return None

    def refresh(self, skip_midx = False):
        """Refresh the index list.
        This method verifies if .midx files were superseded (e.g. all of its
        contents are in another, bigger .midx file) and removes the superseded
        files.

        If skip_midx is True, all work on .midx files will be skipped and .midx
        files will be removed from the list.

        The module-global variable 'ignore_midx' can force this function to
        always act as if skip_midx was True.
        """
        self.bloom = None # Always reopen the bloom as it may have been relaced
        self.do_bloom = False
        skip_midx = skip_midx or ignore_midx
        d = dict((p.name, p) for p in self.packs
                 if not skip_midx or not isinstance(p, midx.PackMidx))
        if os.path.exists(self.dir):
            if not skip_midx:
                midxl = []
                for ix in self.packs:
                    if isinstance(ix, midx.PackMidx):
                        for name in ix.idxnames:
                            d[os.path.join(self.dir, name)] = ix
                for full in glob.glob(os.path.join(self.dir,'*.midx')):
                    if not d.get(full):
                        mx = midx.PackMidx(full)
                        (mxd, mxf) = os.path.split(mx.name)
                        broken = False
                        for n in mx.idxnames:
                            if not os.path.exists(os.path.join(mxd, n)):
                                log(('warning: index %s missing\n' +
                                    '  used by %s\n') % (n, mxf))
                                broken = True
                        if broken:
                            mx.close()
                            del mx
                            unlink(full)
                        else:
                            midxl.append(mx)
                midxl.sort(key=lambda ix:
                           (-len(ix), -xstat.stat(ix.name).st_mtime))
                for ix in midxl:
                    any_needed = False
                    for sub in ix.idxnames:
                        found = d.get(os.path.join(self.dir, sub))
                        if not found or isinstance(found, PackIdx):
                            # doesn't exist, or exists but not in a midx
                            any_needed = True
                            break
                    if any_needed:
                        d[ix.name] = ix
                        for name in ix.idxnames:
                            d[os.path.join(self.dir, name)] = ix
                    elif not ix.force_keep:
                        debug1('midx: removing redundant: %s\n'
                               % os.path.basename(ix.name))
                        ix.close()
                        unlink(ix.name)
            for full in glob.glob(os.path.join(self.dir,'*.idx')):
                if not d.get(full):
                    try:
                        ix = open_idx(full)
                    except GitError, e:
                        add_error(e)
                        continue
                    d[full] = ix
            bfull = os.path.join(self.dir, 'bup.bloom')
            if self.bloom is None and os.path.exists(bfull):
                self.bloom = bloom.ShaBloom(bfull)
            self.packs = list(set(d.values()))
            self.packs.sort(lambda x,y: -cmp(len(x),len(y)))
            if self.bloom and self.bloom.valid() and len(self.bloom) >= len(self):
                self.do_bloom = True
            else:
                self.bloom = None
        debug1('PackIdxList: using %d index%s.\n'
            % (len(self.packs), len(self.packs)!=1 and 'es' or ''))

    def add(self, hash):
        """Insert an additional object in the list."""
        self.also.add(hash)


def open_idx(filename):
    if filename.endswith('.idx'):
        f = open(filename, 'rb')
        header = f.read(8)
        if header[0:4] == '\377tOc':
            version = struct.unpack('!I', header[4:8])[0]
            if version == 2:
                return PackIdxV2(filename, f)
            else:
                raise GitError('%s: expected idx file version 2, got %d'
                               % (filename, version))
        elif len(header) == 8 and header[0:4] < '\377tOc':
            return PackIdxV1(filename, f)
        else:
            raise GitError('%s: unrecognized idx file header' % filename)
    elif filename.endswith('.midx'):
        return midx.PackMidx(filename)
    else:
        raise GitError('idx filenames must end with .idx or .midx')


def idxmerge(idxlist, final_progress=True):
    """Generate a list of all the objects reachable in a PackIdxList."""
    def pfunc(count, total):
        qprogress('Reading indexes: %.2f%% (%d/%d)\r'
                  % (count*100.0/total, count, total))
    def pfinal(count, total):
        if final_progress:
            progress('Reading indexes: %.2f%% (%d/%d), done.\n'
                     % (100, total, total))
    return merge_iter(idxlist, 10024, pfunc, pfinal)


def _make_objcache():
    return PackIdxList(repo('objects/pack'))

class PackWriter:
    """Writes Git objects inside a pack file."""
    def __init__(self, objcache_maker=_make_objcache, compression_level=1):
        self.count = 0
        self.outbytes = 0
        self.filename = None
        self.file = None
        self.idx = None
        self.objcache_maker = objcache_maker
        self.objcache = None
        self.compression_level = compression_level

    def __del__(self):
        self.close()

    def _open(self):
        if not self.file:
            (fd,name) = tempfile.mkstemp(suffix='.pack', dir=repo('objects'))
            self.file = os.fdopen(fd, 'w+b')
            assert(name.endswith('.pack'))
            self.filename = name[:-5]
            self.file.write('PACK\0\0\0\2\0\0\0\0')
            self.idx = list(list() for i in xrange(256))

    def _raw_write(self, datalist, sha):
        self._open()
        f = self.file
        # in case we get interrupted (eg. KeyboardInterrupt), it's best if
        # the file never has a *partial* blob.  So let's make sure it's
        # all-or-nothing.  (The blob shouldn't be very big anyway, thanks
        # to our hashsplit algorithm.)  f.write() does its own buffering,
        # but that's okay because we'll flush it in _end().
        oneblob = ''.join(datalist)
        try:
            f.write(oneblob)
        except IOError, e:
            raise GitError, e, sys.exc_info()[2]
        nw = len(oneblob)
        crc = zlib.crc32(oneblob) & 0xffffffff
        self._update_idx(sha, crc, nw)
        self.outbytes += nw
        self.count += 1
        return nw, crc

    def _update_idx(self, sha, crc, size):
        assert(sha)
        if self.idx:
            self.idx[ord(sha[0])].append((sha, crc, self.file.tell() - size))

    def _write(self, sha, type, content):
        if verbose:
            log('>')
        if not sha:
            sha = calc_hash(type, content)
        size, crc = self._raw_write(_encode_packobj(type, content,
                                                    self.compression_level),
                                    sha=sha)
        if self.outbytes >= max_pack_size or self.count >= max_pack_objects:
            self.breakpoint()
        return sha

    def breakpoint(self):
        """Clear byte and object counts and return the last processed id."""
        id = self._end()
        self.outbytes = self.count = 0
        return id

    def _require_objcache(self):
        if self.objcache is None and self.objcache_maker:
            self.objcache = self.objcache_maker()
        if self.objcache is None:
            raise GitError(
                    "PackWriter not opened or can't check exists w/o objcache")

    def exists(self, id, want_source=False):
        """Return non-empty if an object is found in the object cache."""
        self._require_objcache()
        return self.objcache.exists(id, want_source=want_source)

    def maybe_write(self, type, content):
        """Write an object to the pack file if not present and return its id."""
        sha = calc_hash(type, content)
        if not self.exists(sha):
            self._write(sha, type, content)
            self._require_objcache()
            self.objcache.add(sha)
        return sha

    def new_blob(self, blob):
        """Create a blob object in the pack with the supplied content."""
        return self.maybe_write('blob', blob)

    def new_tree(self, shalist):
        """Create a tree object in the pack."""
        content = tree_encode(shalist)
        return self.maybe_write('tree', content)

    def _new_commit(self, tree, parent, author, adate, committer, cdate, msg):
        l = []
        if tree: l.append('tree %s' % tree.encode('hex'))
        if parent: l.append('parent %s' % parent.encode('hex'))
        if author: l.append('author %s %s' % (author, _git_date(adate)))
        if committer: l.append('committer %s %s' % (committer, _git_date(cdate)))
        l.append('')
        l.append(msg)
        return self.maybe_write('commit', '\n'.join(l))

    def new_commit(self, parent, tree, date, msg):
        """Create a commit object in the pack."""
        userline = '%s <%s@%s>' % (userfullname(), username(), hostname())
        commit = self._new_commit(tree, parent,
                                  userline, date, userline, date,
                                  msg)
        return commit

    def abort(self):
        """Remove the pack file from disk."""
        f = self.file
        if f:
            self.idx = None
            self.file = None
            f.close()
            os.unlink(self.filename + '.pack')

    def _end(self, run_midx=True):
        f = self.file
        if not f: return None
        self.file = None
        self.objcache = None
        idx = self.idx
        self.idx = None

        # update object count
        f.seek(8)
        cp = struct.pack('!i', self.count)
        assert(len(cp) == 4)
        f.write(cp)

        # calculate the pack sha1sum
        f.seek(0)
        sum = Sha1()
        for b in chunkyreader(f):
            sum.update(b)
        packbin = sum.digest()
        f.write(packbin)
        f.close()

        obj_list_sha = self._write_pack_idx_v2(self.filename + '.idx', idx, packbin)

        nameprefix = repo('objects/pack/pack-%s' % obj_list_sha)
        if os.path.exists(self.filename + '.map'):
            os.unlink(self.filename + '.map')
        os.rename(self.filename + '.pack', nameprefix + '.pack')
        os.rename(self.filename + '.idx', nameprefix + '.idx')

        if run_midx:
            auto_midx(repo('objects/pack'))
        return nameprefix

    def close(self, run_midx=True):
        """Close the pack file and move it to its definitive path."""
        return self._end(run_midx=run_midx)

    def _write_pack_idx_v2(self, filename, idx, packbin):
        ofs64_count = 0
        for section in idx:
            for entry in section:
                if entry[2] >= 2**31:
                    ofs64_count += 1

        # Length: header + fan-out + shas-and-crcs + overflow-offsets
        index_len = 8 + (4 * 256) + (28 * self.count) + (8 * ofs64_count)
        idx_map = None
        idx_f = open(filename, 'w+b')
        try:
            idx_f.truncate(index_len)
            idx_map = mmap_readwrite(idx_f, close=False)
            count = _helpers.write_idx(filename, idx_map, idx, self.count)
            assert(count == self.count)
        finally:
            if idx_map: idx_map.close()
            idx_f.close()

        idx_f = open(filename, 'a+b')
        try:
            idx_f.write(packbin)
            idx_f.seek(0)
            idx_sum = Sha1()
            b = idx_f.read(8 + 4*256)
            idx_sum.update(b)

            obj_list_sum = Sha1()
            for b in chunkyreader(idx_f, 20*self.count):
                idx_sum.update(b)
                obj_list_sum.update(b)
            namebase = obj_list_sum.hexdigest()

            for b in chunkyreader(idx_f):
                idx_sum.update(b)
            idx_f.write(idx_sum.digest())
            return namebase
        finally:
            idx_f.close()


def _git_date(date):
    return '%d %s' % (date, time.strftime('%z', time.localtime(date)))


def _gitenv():
    os.environ['GIT_DIR'] = os.path.abspath(repo())


def list_refs(refname = None):
    """Generate a list of tuples in the form (refname,hash).
    If a ref name is specified, list only this particular ref.
    """
    argv = ['git', 'show-ref', '--']
    if refname:
        argv += [refname]
    p = subprocess.Popen(argv, preexec_fn = _gitenv, stdout = subprocess.PIPE)
    out = p.stdout.read().strip()
    rv = p.wait()  # not fatal
    if rv:
        assert(not out)
    if out:
        for d in out.split('\n'):
            (sha, name) = d.split(' ', 1)
            yield (name, sha.decode('hex'))


def read_ref(refname):
    """Get the commit id of the most recent commit made on a given ref."""
    l = list(list_refs(refname))
    if l:
        assert(len(l) == 1)
        return l[0][1]
    else:
        return None


def rev_list(ref, count=None):
    """Generate a list of reachable commits in reverse chronological order.

    This generator walks through commits, from child to parent, that are
    reachable via the specified ref and yields a series of tuples of the form
    (date,hash).

    If count is a non-zero integer, limit the number of commits to "count"
    objects.
    """
    assert(not ref.startswith('-'))
    opts = []
    if count:
        opts += ['-n', str(atoi(count))]
    argv = ['git', 'rev-list', '--pretty=format:%at'] + opts + [ref, '--']
    p = subprocess.Popen(argv, preexec_fn = _gitenv, stdout = subprocess.PIPE)
    commit = None
    for row in p.stdout:
        s = row.strip()
        if s.startswith('commit '):
            commit = s[7:].decode('hex')
        else:
            date = int(s)
            yield (date, commit)
    rv = p.wait()  # not fatal
    if rv:
        raise GitError, 'git rev-list returned error %d' % rv


def get_commit_dates(refs):
    """Get the dates for the specified commit refs.  For now, every unique
       string in refs must resolve to a different commit or this
       function will fail."""
    result = []
    for ref in refs:
        commit = get_commit_items(ref, cp())
        result.append(commit.author_sec)
    return result


def rev_parse(committish):
    """Resolve the full hash for 'committish', if it exists.

    Should be roughly equivalent to 'git rev-parse'.

    Returns the hex value of the hash if it is found, None if 'committish' does
    not correspond to anything.
    """
    head = read_ref(committish)
    if head:
        debug2("resolved from ref: commit = %s\n" % head.encode('hex'))
        return head

    pL = PackIdxList(repo('objects/pack'))

    if len(committish) == 40:
        try:
            hash = committish.decode('hex')
        except TypeError:
            return None

        if pL.exists(hash):
            return hash

    return None


def update_ref(refname, newval, oldval):
    """Change the commit pointed to by a branch."""
    if not oldval:
        oldval = ''
    assert(refname.startswith('refs/heads/'))
    p = subprocess.Popen(['git', 'update-ref', refname,
                          newval.encode('hex'), oldval.encode('hex')],
                         preexec_fn = _gitenv)
    _git_wait('git update-ref', p)


def guess_repo(path=None):
    """Set the path value in the global variable "repodir".
    This makes bup look for an existing bup repository, but not fail if a
    repository doesn't exist. Usually, if you are interacting with a bup
    repository, you would not be calling this function but using
    check_repo_or_die().
    """
    global repodir
    if path:
        repodir = path
    if not repodir:
        repodir = os.environ.get('BUP_DIR')
        if not repodir:
            repodir = os.path.expanduser('~/.bup')


def init_repo(path=None):
    """Create the Git bare repository for bup in a given path."""
    guess_repo(path)
    d = repo()  # appends a / to the path
    parent = os.path.dirname(os.path.dirname(d))
    if parent and not os.path.exists(parent):
        raise GitError('parent directory "%s" does not exist\n' % parent)
    if os.path.exists(d) and not os.path.isdir(os.path.join(d, '.')):
        raise GitError('"%s" exists but is not a directory\n' % d)
    p = subprocess.Popen(['git', '--bare', 'init'], stdout=sys.stderr,
                         preexec_fn = _gitenv)
    _git_wait('git init', p)
    # Force the index version configuration in order to ensure bup works
    # regardless of the version of the installed Git binary.
    p = subprocess.Popen(['git', 'config', 'pack.indexVersion', '2'],
                         stdout=sys.stderr, preexec_fn = _gitenv)
    _git_wait('git config', p)
    # Enable the reflog
    p = subprocess.Popen(['git', 'config', 'core.logAllRefUpdates', 'true'],
                         stdout=sys.stderr, preexec_fn = _gitenv)
    _git_wait('git config', p)


def check_repo_or_die(path=None):
    """Make sure a bup repository exists, and abort if not.
    If the path to a particular repository was not specified, this function
    initializes the default repository automatically.
    """
    guess_repo(path)
    try:
        os.stat(repo('objects/pack/.'))
    except OSError, e:
        if e.errno == errno.ENOENT:
            log('error: %r is not a bup repository; run "bup init"\n'
                % repo())
            sys.exit(15)
        else:
            log('error: %s\n' % e)
            sys.exit(14)


_ver = None
def ver():
    """Get Git's version and ensure a usable version is installed.

    The returned version is formatted as an ordered tuple with each position
    representing a digit in the version tag. For example, the following tuple
    would represent version 1.6.6.9:

        ('1', '6', '6', '9')
    """
    global _ver
    if not _ver:
        p = subprocess.Popen(['git', '--version'],
                             stdout=subprocess.PIPE)
        gvs = p.stdout.read()
        _git_wait('git --version', p)
        m = re.match(r'git version (\S+.\S+)', gvs)
        if not m:
            raise GitError('git --version weird output: %r' % gvs)
        _ver = tuple(m.group(1).split('.'))
    needed = ('1','5', '3', '1')
    if _ver < needed:
        raise GitError('git version %s or higher is required; you have %s'
                       % ('.'.join(needed), '.'.join(_ver)))
    return _ver


def _git_wait(cmd, p):
    rv = p.wait()
    if rv != 0:
        raise GitError('%s returned %d' % (cmd, rv))


def _git_capture(argv):
    p = subprocess.Popen(argv, stdout=subprocess.PIPE, preexec_fn = _gitenv)
    r = p.stdout.read()
    _git_wait(repr(argv), p)
    return r


class _AbortableIter:
    def __init__(self, it, onabort = None):
        self.it = it
        self.onabort = onabort
        self.done = None

    def __iter__(self):
        return self

    def next(self):
        try:
            return self.it.next()
        except StopIteration, e:
            self.done = True
            raise
        except:
            self.abort()
            raise

    def abort(self):
        """Abort iteration and call the abortion callback, if needed."""
        if not self.done:
            self.done = True
            if self.onabort:
                self.onabort()

    def __del__(self):
        self.abort()


_ver_warned = 0
class CatPipe:
    """Link to 'git cat-file' that is used to retrieve blob data."""
    def __init__(self):
        global _ver_warned
        wanted = ('1','5','6')
        if ver() < wanted:
            if not _ver_warned:
                log('warning: git version < %s; bup will be slow.\n'
                    % '.'.join(wanted))
                _ver_warned = 1
            self.get = self._slow_get
        else:
            self.p = self.inprogress = None
            self.get = self._fast_get

    def _abort(self):
        if self.p:
            self.p.stdout.close()
            self.p.stdin.close()
        self.p = None
        self.inprogress = None

    def _restart(self):
        self._abort()
        self.p = subprocess.Popen(['git', 'cat-file', '--batch'],
                                  stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  close_fds = True,
                                  bufsize = 4096,
                                  preexec_fn = _gitenv)

    def _fast_get(self, id):
        if not self.p or self.p.poll() != None:
            self._restart()
        assert(self.p)
        poll_result = self.p.poll()
        assert(poll_result == None)
        if self.inprogress:
            log('_fast_get: opening %r while %r is open\n'
                % (id, self.inprogress))
        assert(not self.inprogress)
        assert(id.find('\n') < 0)
        assert(id.find('\r') < 0)
        assert(not id.startswith('-'))
        self.inprogress = id
        self.p.stdin.write('%s\n' % id)
        self.p.stdin.flush()
        hdr = self.p.stdout.readline()
        if hdr.endswith(' missing\n'):
            self.inprogress = None
            raise KeyError('blob %r is missing' % id)
        spl = hdr.split(' ')
        if len(spl) != 3 or len(spl[0]) != 40:
            raise GitError('expected blob, got %r' % spl)
        (hex, type, size) = spl

        it = _AbortableIter(chunkyreader(self.p.stdout, int(spl[2])),
                           onabort = self._abort)
        try:
            yield type
            for blob in it:
                yield blob
            readline_result = self.p.stdout.readline()
            assert(readline_result == '\n')
            self.inprogress = None
        except Exception, e:
            it.abort()
            raise

    def _slow_get(self, id):
        assert(id.find('\n') < 0)
        assert(id.find('\r') < 0)
        assert(id[0] != '-')
        type = _git_capture(['git', 'cat-file', '-t', id]).strip()
        yield type

        p = subprocess.Popen(['git', 'cat-file', type, id],
                             stdout=subprocess.PIPE,
                             preexec_fn = _gitenv)
        for blob in chunkyreader(p.stdout):
            yield blob
        _git_wait('git cat-file', p)

    def _join(self, it):
        type = it.next()
        if type == 'blob':
            for blob in it:
                yield blob
        elif type == 'tree':
            treefile = ''.join(it)
            for (mode, name, sha) in tree_decode(treefile):
                for blob in self.join(sha.encode('hex')):
                    yield blob
        elif type == 'commit':
            treeline = ''.join(it).split('\n')[0]
            assert(treeline.startswith('tree '))
            for blob in self.join(treeline[5:]):
                yield blob
        else:
            raise GitError('invalid object type %r: expected blob/tree/commit'
                           % type)

    def join(self, id):
        """Generate a list of the content of all blobs that can be reached
        from an object.  The hash given in 'id' must point to a blob, a tree
        or a commit. The content of all blobs that can be seen from trees or
        commits will be added to the list.
        """
        try:
            for d in self._join(self.get(id)):
                yield d
        except StopIteration:
            log('booger!\n')


_cp = (None, None)

def cp():
    """Create a CatPipe object or reuse an already existing one."""
    global _cp
    cp_dir, cp = _cp
    cur_dir = os.path.realpath(repo())
    if cur_dir != cp_dir:
        cp = CatPipe()
        _cp = (cur_dir, cp)
    return cp


def tags():
    """Return a dictionary of all tags in the form {hash: [tag_names, ...]}."""
    tags = {}
    for (n,c) in list_refs():
        if n.startswith('refs/tags/'):
            name = n[10:]
            if not c in tags:
                tags[c] = []

            tags[c].append(name)  # more than one tag can point at 'c'

    return tags

########NEW FILE########
__FILENAME__ = hashsplit
import math
from bup import _helpers
from bup.helpers import *

BLOB_MAX = 8192*4   # 8192 is the "typical" blob size for bupsplit
BLOB_READ_SIZE = 1024*1024
MAX_PER_TREE = 256
progress_callback = None
fanout = 16

GIT_MODE_FILE = 0100644
GIT_MODE_TREE = 040000
GIT_MODE_SYMLINK = 0120000
assert(GIT_MODE_TREE != 40000)  # 0xxx should be treated as octal

# The purpose of this type of buffer is to avoid copying on peek(), get(),
# and eat().  We do copy the buffer contents on put(), but that should
# be ok if we always only put() large amounts of data at a time.
class Buf:
    def __init__(self):
        self.data = ''
        self.start = 0

    def put(self, s):
        if s:
            self.data = buffer(self.data, self.start) + s
            self.start = 0
            
    def peek(self, count):
        return buffer(self.data, self.start, count)
    
    def eat(self, count):
        self.start += count

    def get(self, count):
        v = buffer(self.data, self.start, count)
        self.start += count
        return v

    def used(self):
        return len(self.data) - self.start


def readfile_iter(files, progress=None):
    for filenum,f in enumerate(files):
        ofs = 0
        b = ''
        while 1:
            if progress:
                progress(filenum, len(b))
            fadvise_done(f, max(0, ofs - 1024*1024))
            b = f.read(BLOB_READ_SIZE)
            ofs += len(b)
            if not b:
                fadvise_done(f, ofs)
                break
            yield b


def _splitbuf(buf, basebits, fanbits):
    while 1:
        b = buf.peek(buf.used())
        (ofs, bits) = _helpers.splitbuf(b)
        if ofs:
            if ofs > BLOB_MAX:
                ofs = BLOB_MAX
                level = 0
            else:
                level = (bits-basebits)//fanbits  # integer division
            buf.eat(ofs)
            yield buffer(b, 0, ofs), level
        else:
            break
    while buf.used() >= BLOB_MAX:
        # limit max blob size
        yield buf.get(BLOB_MAX), 0


def _hashsplit_iter(files, progress):
    assert(BLOB_READ_SIZE > BLOB_MAX)
    basebits = _helpers.blobbits()
    fanbits = int(math.log(fanout or 128, 2))
    buf = Buf()
    for inblock in readfile_iter(files, progress):
        buf.put(inblock)
        for buf_and_level in _splitbuf(buf, basebits, fanbits):
            yield buf_and_level
    if buf.used():
        yield buf.get(buf.used()), 0


def _hashsplit_iter_keep_boundaries(files, progress):
    for real_filenum,f in enumerate(files):
        if progress:
            def prog(filenum, nbytes):
                # the inner _hashsplit_iter doesn't know the real file count,
                # so we'll replace it here.
                return progress(real_filenum, nbytes)
        else:
            prog = None
        for buf_and_level in _hashsplit_iter([f], progress=prog):
            yield buf_and_level


def hashsplit_iter(files, keep_boundaries, progress):
    if keep_boundaries:
        return _hashsplit_iter_keep_boundaries(files, progress)
    else:
        return _hashsplit_iter(files, progress)


total_split = 0
def split_to_blobs(makeblob, files, keep_boundaries, progress):
    global total_split
    for (blob, level) in hashsplit_iter(files, keep_boundaries, progress):
        sha = makeblob(blob)
        total_split += len(blob)
        if progress_callback:
            progress_callback(len(blob))
        yield (sha, len(blob), level)


def _make_shalist(l):
    ofs = 0
    l = list(l)
    total = sum(size for mode,sha,size, in l)
    vlen = len('%x' % total)
    shalist = []
    for (mode, sha, size) in l:
        shalist.append((mode, '%0*x' % (vlen,ofs), sha))
        ofs += size
    assert(ofs == total)
    return (shalist, total)


def _squish(maketree, stacks, n):
    i = 0
    while i < n or len(stacks[i]) >= MAX_PER_TREE:
        while len(stacks) <= i+1:
            stacks.append([])
        if len(stacks[i]) == 1:
            stacks[i+1] += stacks[i]
        elif stacks[i]:
            (shalist, size) = _make_shalist(stacks[i])
            tree = maketree(shalist)
            stacks[i+1].append((GIT_MODE_TREE, tree, size))
        stacks[i] = []
        i += 1


def split_to_shalist(makeblob, maketree, files,
                     keep_boundaries, progress=None):
    sl = split_to_blobs(makeblob, files, keep_boundaries, progress)
    assert(fanout != 0)
    if not fanout:
        shal = []
        for (sha,size,level) in sl:
            shal.append((GIT_MODE_FILE, sha, size))
        return _make_shalist(shal)[0]
    else:
        stacks = [[]]
        for (sha,size,level) in sl:
            stacks[0].append((GIT_MODE_FILE, sha, size))
            _squish(maketree, stacks, level)
        #log('stacks: %r\n' % [len(i) for i in stacks])
        _squish(maketree, stacks, len(stacks)-1)
        #log('stacks: %r\n' % [len(i) for i in stacks])
        return _make_shalist(stacks[-1])[0]


def split_to_blob_or_tree(makeblob, maketree, files,
                          keep_boundaries, progress=None):
    shalist = list(split_to_shalist(makeblob, maketree,
                                    files, keep_boundaries, progress))
    if len(shalist) == 1:
        return (shalist[0][0], shalist[0][2])
    elif len(shalist) == 0:
        return (GIT_MODE_FILE, makeblob(''))
    else:
        return (GIT_MODE_TREE, maketree(shalist))


def open_noatime(name):
    fd = _helpers.open_noatime(name)
    try:
        return os.fdopen(fd, 'rb', 1024*1024)
    except:
        try:
            os.close(fd)
        except:
            pass
        raise


def fadvise_done(f, ofs):
    assert(ofs >= 0)
    if ofs > 0 and hasattr(f, 'fileno'):
        _helpers.fadvise_done(f.fileno(), ofs)

########NEW FILE########
__FILENAME__ = helpers
"""Helper functions and classes for bup."""

from ctypes import sizeof, c_void_p
from os import environ
import sys, os, pwd, subprocess, errno, socket, select, mmap, stat, re, struct
import hashlib, heapq, operator, time, grp

from bup import _helpers
import bup._helpers as _helpers
import math

# This function should really be in helpers, not in bup.options.  But we
# want options.py to be standalone so people can include it in other projects.
from bup.options import _tty_width
tty_width = _tty_width


def atoi(s):
    """Convert the string 's' to an integer. Return 0 if s is not a number."""
    try:
        return int(s or '0')
    except ValueError:
        return 0


def atof(s):
    """Convert the string 's' to a float. Return 0 if s is not a number."""
    try:
        return float(s or '0')
    except ValueError:
        return 0


buglvl = atoi(os.environ.get('BUP_DEBUG', 0))


# If the platform doesn't have fdatasync (OS X), fall back to fsync.
try:
    fdatasync = os.fdatasync
except AttributeError:
    fdatasync = os.fsync


# Write (blockingly) to sockets that may or may not be in blocking mode.
# We need this because our stderr is sometimes eaten by subprocesses
# (probably ssh) that sometimes make it nonblocking, if only temporarily,
# leading to race conditions.  Ick.  We'll do it the hard way.
def _hard_write(fd, buf):
    while buf:
        (r,w,x) = select.select([], [fd], [], None)
        if not w:
            raise IOError('select(fd) returned without being writable')
        try:
            sz = os.write(fd, buf)
        except OSError, e:
            if e.errno != errno.EAGAIN:
                raise
        assert(sz >= 0)
        buf = buf[sz:]


_last_prog = 0
def log(s):
    """Print a log message to stderr."""
    global _last_prog
    sys.stdout.flush()
    _hard_write(sys.stderr.fileno(), s)
    _last_prog = 0


def debug1(s):
    if buglvl >= 1:
        log(s)


def debug2(s):
    if buglvl >= 2:
        log(s)


istty1 = os.isatty(1) or (atoi(os.environ.get('BUP_FORCE_TTY')) & 1)
istty2 = os.isatty(2) or (atoi(os.environ.get('BUP_FORCE_TTY')) & 2)
_last_progress = ''
def progress(s):
    """Calls log() if stderr is a TTY.  Does nothing otherwise."""
    global _last_progress
    if istty2:
        log(s)
        _last_progress = s


def qprogress(s):
    """Calls progress() only if we haven't printed progress in a while.
    
    This avoids overloading the stderr buffer with excess junk.
    """
    global _last_prog
    now = time.time()
    if now - _last_prog > 0.1:
        progress(s)
        _last_prog = now


def reprogress():
    """Calls progress() to redisplay the most recent progress message.

    Useful after you've printed some other message that wipes out the
    progress line.
    """
    if _last_progress and _last_progress.endswith('\r'):
        progress(_last_progress)


def mkdirp(d, mode=None):
    """Recursively create directories on path 'd'.

    Unlike os.makedirs(), it doesn't raise an exception if the last element of
    the path already exists.
    """
    try:
        if mode:
            os.makedirs(d, mode)
        else:
            os.makedirs(d)
    except OSError, e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise


_unspecified_next_default = object()

def _fallback_next(it, default=_unspecified_next_default):
    """Retrieve the next item from the iterator by calling its
    next() method. If default is given, it is returned if the
    iterator is exhausted, otherwise StopIteration is raised."""

    if default is _unspecified_next_default:
        return it.next()
    else:
        try:
            return it.next()
        except StopIteration:
            return default

if sys.version_info < (2, 6):
    next =  _fallback_next


def merge_iter(iters, pfreq, pfunc, pfinal, key=None):
    if key:
        samekey = lambda e, pe: getattr(e, key) == getattr(pe, key, None)
    else:
        samekey = operator.eq
    count = 0
    total = sum(len(it) for it in iters)
    iters = (iter(it) for it in iters)
    heap = ((next(it, None),it) for it in iters)
    heap = [(e,it) for e,it in heap if e]

    heapq.heapify(heap)
    pe = None
    while heap:
        if not count % pfreq:
            pfunc(count, total)
        e, it = heap[0]
        if not samekey(e, pe):
            pe = e
            yield e
        count += 1
        try:
            e = it.next() # Don't use next() function, it's too expensive
        except StopIteration:
            heapq.heappop(heap) # remove current
        else:
            heapq.heapreplace(heap, (e, it)) # shift current to new location
    pfinal(count, total)


def unlink(f):
    """Delete a file at path 'f' if it currently exists.

    Unlike os.unlink(), does not throw an exception if the file didn't already
    exist.
    """
    try:
        os.unlink(f)
    except OSError, e:
        if e.errno == errno.ENOENT:
            pass  # it doesn't exist, that's what you asked for


def readpipe(argv, preexec_fn=None):
    """Run a subprocess and return its output."""
    p = subprocess.Popen(argv, stdout=subprocess.PIPE, preexec_fn=preexec_fn)
    out, err = p.communicate()
    if p.returncode != 0:
        raise Exception('subprocess %r failed with status %d'
                        % (' '.join(argv), p.returncode))
    return out


def _argmax_base(command):
    base_size = 2048
    for c in command:
        base_size += len(command) + 1
    for k, v in environ.iteritems():
        base_size += len(k) + len(v) + 2 + sizeof(c_void_p)
    return base_size


def _argmax_args_size(args):
    return sum(len(x) + 1 + sizeof(c_void_p) for x in args)


def batchpipe(command, args, preexec_fn=None, arg_max=_helpers.SC_ARG_MAX):
    """If args is not empty, yield the output produced by calling the
command list with args as a sequence of strings (It may be necessary
to return multiple strings in order to respect ARG_MAX)."""
    # The optional arg_max arg is a workaround for an issue with the
    # current wvtest behavior.
    base_size = _argmax_base(command)
    while args:
        room = arg_max - base_size
        i = 0
        while i < len(args):
            next_size = _argmax_args_size(args[i:i+1])
            if room - next_size < 0:
                break
            room -= next_size
            i += 1
        sub_args = args[:i]
        args = args[i:]
        assert(len(sub_args))
        yield readpipe(command + sub_args, preexec_fn=preexec_fn)


def realpath(p):
    """Get the absolute path of a file.

    Behaves like os.path.realpath, but doesn't follow a symlink for the last
    element. (ie. if 'p' itself is a symlink, this one won't follow it, but it
    will follow symlinks in p's directory)
    """
    try:
        st = os.lstat(p)
    except OSError:
        st = None
    if st and stat.S_ISLNK(st.st_mode):
        (dir, name) = os.path.split(p)
        dir = os.path.realpath(dir)
        out = os.path.join(dir, name)
    else:
        out = os.path.realpath(p)
    #log('realpathing:%r,%r\n' % (p, out))
    return out


def detect_fakeroot():
    "Return True if we appear to be running under fakeroot."
    return os.getenv("FAKEROOTKEY") != None


def is_superuser():
    if sys.platform.startswith('cygwin'):
        import ctypes
        return ctypes.cdll.shell32.IsUserAnAdmin()
    else:
        return os.geteuid() == 0


def _cache_key_value(get_value, key, cache):
    """Return (value, was_cached).  If there is a value in the cache
    for key, use that, otherwise, call get_value(key) which should
    throw a KeyError if there is no value -- in which case the cached
    and returned value will be None.
    """
    try: # Do we already have it (or know there wasn't one)?
        value = cache[key]
        return value, True
    except KeyError:
        pass
    value = None
    try:
        cache[key] = value = get_value(key)
    except KeyError:
        cache[key] = None
    return value, False


_uid_to_pwd_cache = {}
_name_to_pwd_cache = {}

def pwd_from_uid(uid):
    """Return password database entry for uid (may be a cached value).
    Return None if no entry is found.
    """
    global _uid_to_pwd_cache, _name_to_pwd_cache
    entry, cached = _cache_key_value(pwd.getpwuid, uid, _uid_to_pwd_cache)
    if entry and not cached:
        _name_to_pwd_cache[entry.pw_name] = entry
    return entry


def pwd_from_name(name):
    """Return password database entry for name (may be a cached value).
    Return None if no entry is found.
    """
    global _uid_to_pwd_cache, _name_to_pwd_cache
    entry, cached = _cache_key_value(pwd.getpwnam, name, _name_to_pwd_cache)
    if entry and not cached:
        _uid_to_pwd_cache[entry.pw_uid] = entry
    return entry


_gid_to_grp_cache = {}
_name_to_grp_cache = {}

def grp_from_gid(gid):
    """Return password database entry for gid (may be a cached value).
    Return None if no entry is found.
    """
    global _gid_to_grp_cache, _name_to_grp_cache
    entry, cached = _cache_key_value(grp.getgrgid, gid, _gid_to_grp_cache)
    if entry and not cached:
        _name_to_grp_cache[entry.gr_name] = entry
    return entry


def grp_from_name(name):
    """Return password database entry for name (may be a cached value).
    Return None if no entry is found.
    """
    global _gid_to_grp_cache, _name_to_grp_cache
    entry, cached = _cache_key_value(grp.getgrnam, name, _name_to_grp_cache)
    if entry and not cached:
        _gid_to_grp_cache[entry.gr_gid] = entry
    return entry


_username = None
def username():
    """Get the user's login name."""
    global _username
    if not _username:
        uid = os.getuid()
        _username = pwd_from_uid(uid)[0] or 'user%d' % uid
    return _username


_userfullname = None
def userfullname():
    """Get the user's full name."""
    global _userfullname
    if not _userfullname:
        uid = os.getuid()
        entry = pwd_from_uid(uid)
        if entry:
            _userfullname = entry[4].split(',')[0] or entry[0]
        if not _userfullname:
            _userfullname = 'user%d' % uid
    return _userfullname


_hostname = None
def hostname():
    """Get the FQDN of this machine."""
    global _hostname
    if not _hostname:
        _hostname = socket.getfqdn()
    return _hostname


_resource_path = None
def resource_path(subdir=''):
    global _resource_path
    if not _resource_path:
        _resource_path = os.environ.get('BUP_RESOURCE_PATH') or '.'
    return os.path.join(_resource_path, subdir)

def format_filesize(size):
    unit = 1024.0
    size = float(size)
    if size < unit:
        return "%d" % (size)
    exponent = int(math.log(size) / math.log(unit))
    size_prefix = "KMGTPE"[exponent - 1]
    return "%.1f%s" % (size / math.pow(unit, exponent), size_prefix)


class NotOk(Exception):
    pass


class BaseConn:
    def __init__(self, outp):
        self.outp = outp

    def close(self):
        while self._read(65536): pass

    def read(self, size):
        """Read 'size' bytes from input stream."""
        self.outp.flush()
        return self._read(size)

    def readline(self):
        """Read from input stream until a newline is found."""
        self.outp.flush()
        return self._readline()

    def write(self, data):
        """Write 'data' to output stream."""
        #log('%d writing: %d bytes\n' % (os.getpid(), len(data)))
        self.outp.write(data)

    def has_input(self):
        """Return true if input stream is readable."""
        raise NotImplemented("Subclasses must implement has_input")

    def ok(self):
        """Indicate end of output from last sent command."""
        self.write('\nok\n')

    def error(self, s):
        """Indicate server error to the client."""
        s = re.sub(r'\s+', ' ', str(s))
        self.write('\nerror %s\n' % s)

    def _check_ok(self, onempty):
        self.outp.flush()
        rl = ''
        for rl in linereader(self):
            #log('%d got line: %r\n' % (os.getpid(), rl))
            if not rl:  # empty line
                continue
            elif rl == 'ok':
                return None
            elif rl.startswith('error '):
                #log('client: error: %s\n' % rl[6:])
                return NotOk(rl[6:])
            else:
                onempty(rl)
        raise Exception('server exited unexpectedly; see errors above')

    def drain_and_check_ok(self):
        """Remove all data for the current command from input stream."""
        def onempty(rl):
            pass
        return self._check_ok(onempty)

    def check_ok(self):
        """Verify that server action completed successfully."""
        def onempty(rl):
            raise Exception('expected "ok", got %r' % rl)
        return self._check_ok(onempty)


class Conn(BaseConn):
    def __init__(self, inp, outp):
        BaseConn.__init__(self, outp)
        self.inp = inp

    def _read(self, size):
        return self.inp.read(size)

    def _readline(self):
        return self.inp.readline()

    def has_input(self):
        [rl, wl, xl] = select.select([self.inp.fileno()], [], [], 0)
        if rl:
            assert(rl[0] == self.inp.fileno())
            return True
        else:
            return None


def checked_reader(fd, n):
    while n > 0:
        rl, _, _ = select.select([fd], [], [])
        assert(rl[0] == fd)
        buf = os.read(fd, n)
        if not buf: raise Exception("Unexpected EOF reading %d more bytes" % n)
        yield buf
        n -= len(buf)


MAX_PACKET = 128 * 1024
def mux(p, outfd, outr, errr):
    try:
        fds = [outr, errr]
        while p.poll() is None:
            rl, _, _ = select.select(fds, [], [])
            for fd in rl:
                if fd == outr:
                    buf = os.read(outr, MAX_PACKET)
                    if not buf: break
                    os.write(outfd, struct.pack('!IB', len(buf), 1) + buf)
                elif fd == errr:
                    buf = os.read(errr, 1024)
                    if not buf: break
                    os.write(outfd, struct.pack('!IB', len(buf), 2) + buf)
    finally:
        os.write(outfd, struct.pack('!IB', 0, 3))


class DemuxConn(BaseConn):
    """A helper class for bup's client-server protocol."""
    def __init__(self, infd, outp):
        BaseConn.__init__(self, outp)
        # Anything that comes through before the sync string was not
        # multiplexed and can be assumed to be debug/log before mux init.
        tail = ''
        while tail != 'BUPMUX':
            b = os.read(infd, (len(tail) < 6) and (6-len(tail)) or 1)
            if not b:
                raise IOError('demux: unexpected EOF during initialization')
            tail += b
            sys.stderr.write(tail[:-6])  # pre-mux log messages
            tail = tail[-6:]
        self.infd = infd
        self.reader = None
        self.buf = None
        self.closed = False

    def write(self, data):
        self._load_buf(0)
        BaseConn.write(self, data)

    def _next_packet(self, timeout):
        if self.closed: return False
        rl, wl, xl = select.select([self.infd], [], [], timeout)
        if not rl: return False
        assert(rl[0] == self.infd)
        ns = ''.join(checked_reader(self.infd, 5))
        n, fdw = struct.unpack('!IB', ns)
        assert(n <= MAX_PACKET)
        if fdw == 1:
            self.reader = checked_reader(self.infd, n)
        elif fdw == 2:
            for buf in checked_reader(self.infd, n):
                sys.stderr.write(buf)
        elif fdw == 3:
            self.closed = True
            debug2("DemuxConn: marked closed\n")
        return True

    def _load_buf(self, timeout):
        if self.buf is not None:
            return True
        while not self.closed:
            while not self.reader:
                if not self._next_packet(timeout):
                    return False
            try:
                self.buf = self.reader.next()
                return True
            except StopIteration:
                self.reader = None
        return False

    def _read_parts(self, ix_fn):
        while self._load_buf(None):
            assert(self.buf is not None)
            i = ix_fn(self.buf)
            if i is None or i == len(self.buf):
                yv = self.buf
                self.buf = None
            else:
                yv = self.buf[:i]
                self.buf = self.buf[i:]
            yield yv
            if i is not None:
                break

    def _readline(self):
        def find_eol(buf):
            try:
                return buf.index('\n')+1
            except ValueError:
                return None
        return ''.join(self._read_parts(find_eol))

    def _read(self, size):
        csize = [size]
        def until_size(buf): # Closes on csize
            if len(buf) < csize[0]:
                csize[0] -= len(buf)
                return None
            else:
                return csize[0]
        return ''.join(self._read_parts(until_size))

    def has_input(self):
        return self._load_buf(0)


def linereader(f):
    """Generate a list of input lines from 'f' without terminating newlines."""
    while 1:
        line = f.readline()
        if not line:
            break
        yield line[:-1]


def chunkyreader(f, count = None):
    """Generate a list of chunks of data read from 'f'.

    If count is None, read until EOF is reached.

    If count is a positive integer, read 'count' bytes from 'f'. If EOF is
    reached while reading, raise IOError.
    """
    if count != None:
        while count > 0:
            b = f.read(min(count, 65536))
            if not b:
                raise IOError('EOF with %d bytes remaining' % count)
            yield b
            count -= len(b)
    else:
        while 1:
            b = f.read(65536)
            if not b: break
            yield b


def slashappend(s):
    """Append "/" to 's' if it doesn't aleady end in "/"."""
    if s and not s.endswith('/'):
        return s + '/'
    else:
        return s


def _mmap_do(f, sz, flags, prot, close):
    if not sz:
        st = os.fstat(f.fileno())
        sz = st.st_size
    if not sz:
        # trying to open a zero-length map gives an error, but an empty
        # string has all the same behaviour of a zero-length map, ie. it has
        # no elements :)
        return ''
    map = mmap.mmap(f.fileno(), sz, flags, prot)
    if close:
        f.close()  # map will persist beyond file close
    return map


def mmap_read(f, sz = 0, close=True):
    """Create a read-only memory mapped region on file 'f'.
    If sz is 0, the region will cover the entire file.
    """
    return _mmap_do(f, sz, mmap.MAP_PRIVATE, mmap.PROT_READ, close)


def mmap_readwrite(f, sz = 0, close=True):
    """Create a read-write memory mapped region on file 'f'.
    If sz is 0, the region will cover the entire file.
    """
    return _mmap_do(f, sz, mmap.MAP_SHARED, mmap.PROT_READ|mmap.PROT_WRITE,
                    close)


def mmap_readwrite_private(f, sz = 0, close=True):
    """Create a read-write memory mapped region on file 'f'.
    If sz is 0, the region will cover the entire file.
    The map is private, which means the changes are never flushed back to the
    file.
    """
    return _mmap_do(f, sz, mmap.MAP_PRIVATE, mmap.PROT_READ|mmap.PROT_WRITE,
                    close)


def parse_timestamp(epoch_str):
    """Return the number of nanoseconds since the epoch that are described
by epoch_str (100ms, 100ns, ...); when epoch_str cannot be parsed,
throw a ValueError that may contain additional information."""
    ns_per = {'s' :  1000000000,
              'ms' : 1000000,
              'us' : 1000,
              'ns' : 1}
    match = re.match(r'^((?:[-+]?[0-9]+)?)(s|ms|us|ns)$', epoch_str)
    if not match:
        if re.match(r'^([-+]?[0-9]+)$', epoch_str):
            raise ValueError('must include units, i.e. 100ns, 100ms, ...')
        raise ValueError()
    (n, units) = match.group(1, 2)
    if not n:
        n = 1
    n = int(n)
    return n * ns_per[units]


def parse_num(s):
    """Parse data size information into a float number.

    Here are some examples of conversions:
        199.2k means 203981 bytes
        1GB means 1073741824 bytes
        2.1 tb means 2199023255552 bytes
    """
    g = re.match(r'([-+\d.e]+)\s*(\w*)', str(s))
    if not g:
        raise ValueError("can't parse %r as a number" % s)
    (val, unit) = g.groups()
    num = float(val)
    unit = unit.lower()
    if unit in ['t', 'tb']:
        mult = 1024*1024*1024*1024
    elif unit in ['g', 'gb']:
        mult = 1024*1024*1024
    elif unit in ['m', 'mb']:
        mult = 1024*1024
    elif unit in ['k', 'kb']:
        mult = 1024
    elif unit in ['', 'b']:
        mult = 1
    else:
        raise ValueError("invalid unit %r in number %r" % (unit, s))
    return int(num*mult)


def count(l):
    """Count the number of elements in an iterator. (consumes the iterator)"""
    return reduce(lambda x,y: x+1, l)


saved_errors = []
def add_error(e):
    """Append an error message to the list of saved errors.

    Once processing is able to stop and output the errors, the saved errors are
    accessible in the module variable helpers.saved_errors.
    """
    saved_errors.append(e)
    log('%-70s\n' % e)


def clear_errors():
    global saved_errors
    saved_errors = []


def handle_ctrl_c():
    """Replace the default exception handler for KeyboardInterrupt (Ctrl-C).

    The new exception handler will make sure that bup will exit without an ugly
    stacktrace when Ctrl-C is hit.
    """
    oldhook = sys.excepthook
    def newhook(exctype, value, traceback):
        if exctype == KeyboardInterrupt:
            log('\nInterrupted.\n')
        else:
            return oldhook(exctype, value, traceback)
    sys.excepthook = newhook


def columnate(l, prefix):
    """Format elements of 'l' in columns with 'prefix' leading each line.

    The number of columns is determined automatically based on the string
    lengths.
    """
    if not l:
        return ""
    l = l[:]
    clen = max(len(s) for s in l)
    ncols = (tty_width() - len(prefix)) / (clen + 2)
    if ncols <= 1:
        ncols = 1
        clen = 0
    cols = []
    while len(l) % ncols:
        l.append('')
    rows = len(l)/ncols
    for s in range(0, len(l), rows):
        cols.append(l[s:s+rows])
    out = ''
    for row in zip(*cols):
        out += prefix + ''.join(('%-*s' % (clen+2, s)) for s in row) + '\n'
    return out


def parse_date_or_fatal(str, fatal):
    """Parses the given date or calls Option.fatal().
    For now we expect a string that contains a float."""
    try:
        date = atof(str)
    except ValueError, e:
        raise fatal('invalid date format (should be a float): %r' % e)
    else:
        return date


def parse_excludes(options, fatal):
    """Traverse the options and extract all excludes, or call Option.fatal()."""
    excluded_paths = []

    for flag in options:
        (option, parameter) = flag
        if option == '--exclude':
            excluded_paths.append(realpath(parameter))
        elif option == '--exclude-from':
            try:
                f = open(realpath(parameter))
            except IOError, e:
                raise fatal("couldn't read %s" % parameter)
            for exclude_path in f.readlines():
                excluded_paths.append(realpath(exclude_path.strip()))
    return sorted(frozenset(excluded_paths))


def parse_rx_excludes(options, fatal):
    """Traverse the options and extract all rx excludes, or call
    Option.fatal()."""
    excluded_patterns = []

    for flag in options:
        (option, parameter) = flag
        if option == '--exclude-rx':
            try:
                excluded_patterns.append(re.compile(parameter))
            except re.error, ex:
                fatal('invalid --exclude-rx pattern (%s): %s' % (parameter, ex))
        elif option == '--exclude-rx-from':
            try:
                f = open(realpath(parameter))
            except IOError, e:
                raise fatal("couldn't read %s" % parameter)
            for pattern in f.readlines():
                spattern = pattern.rstrip('\n')
                try:
                    excluded_patterns.append(re.compile(spattern))
                except re.error, ex:
                    fatal('invalid --exclude-rx pattern (%s): %s' % (spattern, ex))
    return excluded_patterns


def should_rx_exclude_path(path, exclude_rxs):
    """Return True if path matches a regular expression in exclude_rxs."""
    for rx in exclude_rxs:
        if rx.search(path):
            debug1('Skipping %r: excluded by rx pattern %r.\n'
                   % (path, rx.pattern))
            return True
    return False


# FIXME: Carefully consider the use of functions (os.path.*, etc.)
# that resolve against the current filesystem in the strip/graft
# functions for example, but elsewhere as well.  I suspect bup's not
# always being careful about that.  For some cases, the contents of
# the current filesystem should be irrelevant, and consulting it might
# produce the wrong result, perhaps via unintended symlink resolution,
# for example.

def path_components(path):
    """Break path into a list of pairs of the form (name,
    full_path_to_name).  Path must start with '/'.
    Example:
      '/home/foo' -> [('', '/'), ('home', '/home'), ('foo', '/home/foo')]"""
    if not path.startswith('/'):
        raise Exception, 'path must start with "/": %s' % path
    # Since we assume path startswith('/'), we can skip the first element.
    result = [('', '/')]
    norm_path = os.path.abspath(path)
    if norm_path == '/':
        return result
    full_path = ''
    for p in norm_path.split('/')[1:]:
        full_path += '/' + p
        result.append((p, full_path))
    return result


def stripped_path_components(path, strip_prefixes):
    """Strip any prefix in strip_prefixes from path and return a list
    of path components where each component is (name,
    none_or_full_fs_path_to_name).  Assume path startswith('/').
    See thelpers.py for examples."""
    normalized_path = os.path.abspath(path)
    sorted_strip_prefixes = sorted(strip_prefixes, key=len, reverse=True)
    for bp in sorted_strip_prefixes:
        normalized_bp = os.path.abspath(bp)
        if normalized_path.startswith(normalized_bp):
            prefix = normalized_path[:len(normalized_bp)]
            result = []
            for p in normalized_path[len(normalized_bp):].split('/'):
                if p: # not root
                    prefix += '/'
                prefix += p
                result.append((p, prefix))
            return result
    # Nothing to strip.
    return path_components(path)


def grafted_path_components(graft_points, path):
    # Create a result that consists of some number of faked graft
    # directories before the graft point, followed by all of the real
    # directories from path that are after the graft point.  Arrange
    # for the directory at the graft point in the result to correspond
    # to the "orig" directory in --graft orig=new.  See t/thelpers.py
    # for some examples.

    # Note that given --graft orig=new, orig and new have *nothing* to
    # do with each other, even if some of their component names
    # match. i.e. --graft /foo/bar/baz=/foo/bar/bax is semantically
    # equivalent to --graft /foo/bar/baz=/x/y/z, or even
    # /foo/bar/baz=/x.

    # FIXME: This can't be the best solution...
    clean_path = os.path.abspath(path)
    for graft_point in graft_points:
        old_prefix, new_prefix = graft_point
        # Expand prefixes iff not absolute paths.
        old_prefix = os.path.normpath(old_prefix)
        new_prefix = os.path.normpath(new_prefix)
        if clean_path.startswith(old_prefix):
            escaped_prefix = re.escape(old_prefix)
            grafted_path = re.sub(r'^' + escaped_prefix, new_prefix, clean_path)
            # Handle /foo=/ (at least) -- which produces //whatever.
            grafted_path = '/' + grafted_path.lstrip('/')
            clean_path_components = path_components(clean_path)
            # Count the components that were stripped.
            strip_count = 0 if old_prefix == '/' else old_prefix.count('/')
            new_prefix_parts = new_prefix.split('/')
            result_prefix = grafted_path.split('/')[:new_prefix.count('/')]
            result = [(p, None) for p in result_prefix] \
                + clean_path_components[strip_count:]
            # Now set the graft point name to match the end of new_prefix.
            graft_point = len(result_prefix)
            result[graft_point] = \
                (new_prefix_parts[-1], clean_path_components[strip_count][1])
            if new_prefix == '/': # --graft ...=/ is a special case.
                return result[1:]
            return result
    return path_components(clean_path)

Sha1 = hashlib.sha1

########NEW FILE########
__FILENAME__ = hlinkdb
import cPickle, errno, os, tempfile

class Error(Exception):
    pass

class HLinkDB:
    def __init__(self, filename):
        # Map a "dev:ino" node to a list of paths associated with that node.
        self._node_paths = {}
        # Map a path to a "dev:ino" node.
        self._path_node = {}
        self._filename = filename
        self._save_prepared = None
        self._tmpname = None
        f = None
        try:
            f = open(filename, 'r')
        except IOError, e:
            if e.errno == errno.ENOENT:
                pass
            else:
                raise
        if f:
            try:
                self._node_paths = cPickle.load(f)
            finally:
                f.close()
                f = None
        # Set up the reverse hard link index.
        for node, paths in self._node_paths.iteritems():
            for path in paths:
                self._path_node[path] = node

    def prepare_save(self):
        """ Commit all of the relevant data to disk.  Do as much work
        as possible without actually making the changes visible."""
        if self._save_prepared:
            raise Error('save of %r already in progress' % self._filename)
        if self._node_paths:
            (dir, name) = os.path.split(self._filename)
            (ffd, self._tmpname) = tempfile.mkstemp('.tmp', name, dir)
            try:
                f = os.fdopen(ffd, 'wb', 65536)
            except:
                os.close(ffd)
                raise
            try:
                cPickle.dump(self._node_paths, f, 2)
            except:
                f.close()
                os.unlink(self._tmpname)
                self._tmpname = None
                raise
            else:
                f.close()
                f = None
        self._save_prepared = True

    def commit_save(self):
        if not self._save_prepared:
            raise Error('cannot commit save of %r; no save prepared'
                        % self._filename)
        if self._tmpname:
            os.rename(self._tmpname, self._filename)
            self._tmpname = None
        else: # No data -- delete _filename if it exists.
            try:
                os.unlink(self._filename)
            except OSError, e:
                if e.errno == errno.ENOENT:
                    pass
                else:
                    raise
        self._save_prepared = None

    def abort_save(self):
        if self._tmpname:
            os.unlink(self._tmpname)
            self._tmpname = None

    def __del__(self):
        self.abort_save()

    def add_path(self, path, dev, ino):
        # Assume path is new.
        node = '%s:%s' % (dev, ino)
        self._path_node[path] = node
        link_paths = self._node_paths.get(node)
        if link_paths and path not in link_paths:
            link_paths.append(path)
        else:
            self._node_paths[node] = [path]

    def _del_node_path(self, node, path):
        link_paths = self._node_paths[node]
        link_paths.remove(path)
        if not link_paths:
            del self._node_paths[node]

    def change_path(self, path, new_dev, new_ino):
        prev_node = self._path_node.get(path)
        if prev_node:
            self._del_node_path(prev_node, path)
        self.add_path(new_dev, new_ino, path)

    def del_path(self, path):
        # Path may not be in db (if updating a pre-hardlink support index).
        node = self._path_node.get(path)
        if node:
            self._del_node_path(node, path)
            del self._path_node[path]

    def node_paths(self, dev, ino):
        node = '%s:%s' % (dev, ino)
        return self._node_paths[node]

########NEW FILE########
__FILENAME__ = index
import metadata, os, stat, struct, tempfile
from bup import xstat
from bup.helpers import *

EMPTY_SHA = '\0'*20
FAKE_SHA = '\x01'*20

INDEX_HDR = 'BUPI\0\0\0\5'

# Time values are handled as integer nanoseconds since the epoch in
# memory, but are written as xstat/metadata timespecs.  This behavior
# matches the existing metadata/xstat/.bupm code.

# Record times (mtime, ctime, atime) as xstat/metadata timespecs, and
# store all of the times in the index so they won't interfere with the
# forthcoming metadata cache.
INDEX_SIG =  '!QQQqQqQqQIIQII20sHIIQ'

ENTLEN = struct.calcsize(INDEX_SIG)
FOOTER_SIG = '!Q'
FOOTLEN = struct.calcsize(FOOTER_SIG)

IX_EXISTS = 0x8000        # file exists on filesystem
IX_HASHVALID = 0x4000     # the stored sha1 matches the filesystem
IX_SHAMISSING = 0x2000    # the stored sha1 object doesn't seem to exist

class Error(Exception):
    pass


class MetaStoreReader:
    def __init__(self, filename):
        self._file = open(filename, 'rb')

    def close(self):
        if self._file:
            self._file.close()
            self._file = None

    def __del__(self):
        self.close()

    def metadata_at(self, ofs):
        self._file.seek(ofs)
        return metadata.Metadata.read(self._file)


class MetaStoreWriter:
    # For now, we just append to the file, and try to handle any
    # truncation or corruption somewhat sensibly.

    def __init__(self, filename):
        # Map metadata hashes to bupindex.meta offsets.
        self._offsets = {}
        self._filename = filename
        self._file = None
        # FIXME: see how slow this is; does it matter?
        m_file = open(filename, 'ab+')
        try:
            m_file.seek(0)
            try:
                m_off = m_file.tell()
                m = metadata.Metadata.read(m_file)
                while m:
                    m_encoded = m.encode()
                    self._offsets[m_encoded] = m_off
                    m_off = m_file.tell()
                    m = metadata.Metadata.read(m_file)
            except EOFError:
                pass
            except:
                log('index metadata in %r appears to be corrupt' % filename)
                raise
        finally:
            m_file.close()
        self._file = open(filename, 'ab')

    def close(self):
        if self._file:
            self._file.close()
            self._file = None

    def __del__(self):
        # Be optimistic.
        self.close()

    def store(self, metadata):
        meta_encoded = metadata.encode(include_path=False)
        ofs = self._offsets.get(meta_encoded)
        if ofs:
            return ofs
        ofs = self._file.tell()
        self._file.write(meta_encoded)
        self._offsets[meta_encoded] = ofs
        return ofs


class Level:
    def __init__(self, ename, parent):
        self.parent = parent
        self.ename = ename
        self.list = []
        self.count = 0

    def write(self, f):
        (ofs,n) = (f.tell(), len(self.list))
        if self.list:
            count = len(self.list)
            #log('popping %r with %d entries\n' 
            #    % (''.join(self.ename), count))
            for e in self.list:
                e.write(f)
            if self.parent:
                self.parent.count += count + self.count
        return (ofs,n)


def _golevel(level, f, ename, newentry, metastore, tmax):
    # close nodes back up the tree
    assert(level)
    default_meta_ofs = metastore.store(metadata.Metadata())
    while ename[:len(level.ename)] != level.ename:
        n = BlankNewEntry(level.ename[-1], default_meta_ofs, tmax)
        n.flags |= IX_EXISTS
        (n.children_ofs,n.children_n) = level.write(f)
        level.parent.list.append(n)
        level = level.parent

    # create nodes down the tree
    while len(level.ename) < len(ename):
        level = Level(ename[:len(level.ename)+1], level)

    # are we in precisely the right place?
    assert(ename == level.ename)
    n = newentry or \
        BlankNewEntry(ename and level.ename[-1] or None, default_meta_ofs, tmax)
    (n.children_ofs,n.children_n) = level.write(f)
    if level.parent:
        level.parent.list.append(n)
    level = level.parent

    return level


class Entry:
    def __init__(self, basename, name, meta_ofs, tmax):
        self.basename = str(basename)
        self.name = str(name)
        self.meta_ofs = meta_ofs
        self.tmax = tmax
        self.children_ofs = 0
        self.children_n = 0

    def __repr__(self):
        return ("(%s,0x%04x,%d,%d,%d,%d,%d,%d,%d,%d,%s/%s,0x%04x,%d,0x%08x/%d)"
                % (self.name, self.dev, self.ino, self.nlink,
                   self.ctime, self.mtime, self.atime, self.uid, self.gid,
                   self.size, self.mode, self.gitmode,
                   self.flags, self.meta_ofs,
                   self.children_ofs, self.children_n))

    def packed(self):
        try:
            ctime = xstat.nsecs_to_timespec(self.ctime)
            mtime = xstat.nsecs_to_timespec(self.mtime)
            atime = xstat.nsecs_to_timespec(self.atime)
            return struct.pack(INDEX_SIG,
                               self.dev, self.ino, self.nlink,
                               ctime[0], ctime[1],
                               mtime[0], mtime[1],
                               atime[0], atime[1],
                               self.uid, self.gid, self.size, self.mode,
                               self.gitmode, self.sha, self.flags,
                               self.children_ofs, self.children_n,
                               self.meta_ofs)
        except (DeprecationWarning, struct.error), e:
            log('pack error: %s (%r)\n' % (e, self))
            raise

    def from_stat(self, st, meta_ofs, tstart, check_device=True):
        old = (self.dev if check_device else 0,
               self.ino, self.nlink, self.ctime, self.mtime,
               self.uid, self.gid, self.size, self.flags & IX_EXISTS)
        new = (st.st_dev if check_device else 0,
               st.st_ino, st.st_nlink, st.st_ctime, st.st_mtime,
               st.st_uid, st.st_gid, st.st_size, IX_EXISTS)
        self.dev = st.st_dev
        self.ino = st.st_ino
        self.nlink = st.st_nlink
        self.ctime = st.st_ctime
        self.mtime = st.st_mtime
        self.atime = st.st_atime
        self.uid = st.st_uid
        self.gid = st.st_gid
        self.size = st.st_size
        self.mode = st.st_mode
        self.flags |= IX_EXISTS
        self.meta_ofs = meta_ofs
        # Check that the ctime's "second" is at or after tstart's.
        ctime_sec_in_ns = xstat.fstime_floor_secs(st.st_ctime) * 10**9
        if ctime_sec_in_ns >= tstart or old != new \
              or self.sha == EMPTY_SHA or not self.gitmode:
            self.invalidate()
        self._fixup()
        
    def _fixup(self):
        if self.uid < 0:
            self.uid += 0x100000000
        if self.gid < 0:
            self.gid += 0x100000000
        assert(self.uid >= 0)
        assert(self.gid >= 0)
        self.mtime = self._fixup_time(self.mtime)
        self.ctime = self._fixup_time(self.ctime)

    def _fixup_time(self, t):
        if self.tmax != None and t > self.tmax:
            return self.tmax
        else:
            return t

    def is_valid(self):
        f = IX_HASHVALID|IX_EXISTS
        return (self.flags & f) == f

    def invalidate(self):
        self.flags &= ~IX_HASHVALID

    def validate(self, gitmode, sha):
        assert(sha)
        assert(gitmode)
        assert(gitmode+0 == gitmode)
        self.gitmode = gitmode
        self.sha = sha
        self.flags |= IX_HASHVALID|IX_EXISTS

    def exists(self):
        return not self.is_deleted()

    def sha_missing(self):
        return (self.flags & IX_SHAMISSING) or not (self.flags & IX_HASHVALID)

    def is_deleted(self):
        return (self.flags & IX_EXISTS) == 0

    def set_deleted(self):
        if self.flags & IX_EXISTS:
            self.flags &= ~(IX_EXISTS | IX_HASHVALID)

    def is_real(self):
        return not self.is_fake()

    def is_fake(self):
        return not self.ctime

    def __cmp__(a, b):
        return (cmp(b.name, a.name)
                or cmp(a.is_valid(), b.is_valid())
                or cmp(a.is_fake(), b.is_fake()))

    def write(self, f):
        f.write(self.basename + '\0' + self.packed())


class NewEntry(Entry):
    def __init__(self, basename, name, tmax, dev, ino, nlink,
                 ctime, mtime, atime,
                 uid, gid, size, mode, gitmode, sha, flags, meta_ofs,
                 children_ofs, children_n):
        Entry.__init__(self, basename, name, meta_ofs, tmax)
        (self.dev, self.ino, self.nlink, self.ctime, self.mtime, self.atime,
         self.uid, self.gid, self.size, self.mode, self.gitmode, self.sha,
         self.flags, self.children_ofs, self.children_n
         ) = (dev, ino, nlink, ctime, mtime, atime, uid, gid,
              size, mode, gitmode, sha, flags, children_ofs, children_n)
        self._fixup()


class BlankNewEntry(NewEntry):
    def __init__(self, basename, meta_ofs, tmax):
        NewEntry.__init__(self, basename, basename, tmax,
                          0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                          0, EMPTY_SHA, 0, meta_ofs, 0, 0)


class ExistingEntry(Entry):
    def __init__(self, parent, basename, name, m, ofs):
        Entry.__init__(self, basename, name, None, None)
        self.parent = parent
        self._m = m
        self._ofs = ofs
        (self.dev, self.ino, self.nlink,
         self.ctime, ctime_ns, self.mtime, mtime_ns, self.atime, atime_ns,
         self.uid, self.gid, self.size, self.mode, self.gitmode, self.sha,
         self.flags, self.children_ofs, self.children_n, self.meta_ofs
         ) = struct.unpack(INDEX_SIG, str(buffer(m, ofs, ENTLEN)))
        self.atime = xstat.timespec_to_nsecs((self.atime, atime_ns))
        self.mtime = xstat.timespec_to_nsecs((self.mtime, mtime_ns))
        self.ctime = xstat.timespec_to_nsecs((self.ctime, ctime_ns))

    # effectively, we don't bother messing with IX_SHAMISSING if
    # not IX_HASHVALID, since it's redundant, and repacking is more
    # expensive than not repacking.
    # This is implemented by having sha_missing() check IX_HASHVALID too.
    def set_sha_missing(self, val):
        val = val and 1 or 0
        oldval = self.sha_missing() and 1 or 0
        if val != oldval:
            flag = val and IX_SHAMISSING or 0
            newflags = (self.flags & (~IX_SHAMISSING)) | flag
            self.flags = newflags
            self.repack()

    def unset_sha_missing(self, flag):
        if self.flags & IX_SHAMISSING:
            self.flags &= ~IX_SHAMISSING
            self.repack()

    def repack(self):
        self._m[self._ofs:self._ofs+ENTLEN] = self.packed()
        if self.parent and not self.is_valid():
            self.parent.invalidate()
            self.parent.repack()

    def iter(self, name=None, wantrecurse=None):
        dname = name
        if dname and not dname.endswith('/'):
            dname += '/'
        ofs = self.children_ofs
        assert(ofs <= len(self._m))
        assert(self.children_n < 1000000)
        for i in xrange(self.children_n):
            eon = self._m.find('\0', ofs)
            assert(eon >= 0)
            assert(eon >= ofs)
            assert(eon > ofs)
            basename = str(buffer(self._m, ofs, eon-ofs))
            child = ExistingEntry(self, basename, self.name + basename,
                                  self._m, eon+1)
            if (not dname
                 or child.name.startswith(dname)
                 or child.name.endswith('/') and dname.startswith(child.name)):
                if not wantrecurse or wantrecurse(child):
                    for e in child.iter(name=name, wantrecurse=wantrecurse):
                        yield e
            if not name or child.name == name or child.name.startswith(dname):
                yield child
            ofs = eon + 1 + ENTLEN

    def __iter__(self):
        return self.iter()
            

class Reader:
    def __init__(self, filename):
        self.filename = filename
        self.m = ''
        self.writable = False
        self.count = 0
        f = None
        try:
            f = open(filename, 'r+')
        except IOError, e:
            if e.errno == errno.ENOENT:
                pass
            else:
                raise
        if f:
            b = f.read(len(INDEX_HDR))
            if b != INDEX_HDR:
                log('warning: %s: header: expected %r, got %r\n'
                                 % (filename, INDEX_HDR, b))
            else:
                st = os.fstat(f.fileno())
                if st.st_size:
                    self.m = mmap_readwrite(f)
                    self.writable = True
                    self.count = struct.unpack(FOOTER_SIG,
                          str(buffer(self.m, st.st_size-FOOTLEN, FOOTLEN)))[0]

    def __del__(self):
        self.close()

    def __len__(self):
        return int(self.count)

    def forward_iter(self):
        ofs = len(INDEX_HDR)
        while ofs+ENTLEN <= len(self.m)-FOOTLEN:
            eon = self.m.find('\0', ofs)
            assert(eon >= 0)
            assert(eon >= ofs)
            assert(eon > ofs)
            basename = str(buffer(self.m, ofs, eon-ofs))
            yield ExistingEntry(None, basename, basename, self.m, eon+1)
            ofs = eon + 1 + ENTLEN

    def iter(self, name=None, wantrecurse=None):
        if len(self.m) > len(INDEX_HDR)+ENTLEN:
            dname = name
            if dname and not dname.endswith('/'):
                dname += '/'
            root = ExistingEntry(None, '/', '/',
                                 self.m, len(self.m)-FOOTLEN-ENTLEN)
            for sub in root.iter(name=name, wantrecurse=wantrecurse):
                yield sub
            if not dname or dname == root.name:
                yield root

    def __iter__(self):
        return self.iter()

    def exists(self):
        return self.m

    def save(self):
        if self.writable and self.m:
            self.m.flush()

    def close(self):
        self.save()
        if self.writable and self.m:
            self.m.close()
            self.m = None
            self.writable = False

    def filter(self, prefixes, wantrecurse=None):
        for (rp, path) in reduce_paths(prefixes):
            for e in self.iter(rp, wantrecurse=wantrecurse):
                assert(e.name.startswith(rp))
                name = path + e.name[len(rp):]
                yield (name, e)


# FIXME: this function isn't very generic, because it splits the filename
# in an odd way and depends on a terminating '/' to indicate directories.
def pathsplit(p):
    """Split a path into a list of elements of the file system hierarchy."""
    l = p.split('/')
    l = [i+'/' for i in l[:-1]] + l[-1:]
    if l[-1] == '':
        l.pop()  # extra blank caused by terminating '/'
    return l


class Writer:
    def __init__(self, filename, metastore, tmax):
        self.rootlevel = self.level = Level([], None)
        self.f = None
        self.count = 0
        self.lastfile = None
        self.filename = None
        self.filename = filename = realpath(filename)
        self.metastore = metastore
        self.tmax = tmax
        (dir,name) = os.path.split(filename)
        (ffd,self.tmpname) = tempfile.mkstemp('.tmp', filename, dir)
        self.f = os.fdopen(ffd, 'wb', 65536)
        self.f.write(INDEX_HDR)

    def __del__(self):
        self.abort()

    def abort(self):
        f = self.f
        self.f = None
        if f:
            f.close()
            os.unlink(self.tmpname)

    def flush(self):
        if self.level:
            self.level = _golevel(self.level, self.f, [], None,
                                  self.metastore, self.tmax)
            self.count = self.rootlevel.count
            if self.count:
                self.count += 1
            self.f.write(struct.pack(FOOTER_SIG, self.count))
            self.f.flush()
        assert(self.level == None)

    def close(self):
        self.flush()
        f = self.f
        self.f = None
        if f:
            f.close()
            os.rename(self.tmpname, self.filename)

    def _add(self, ename, entry):
        if self.lastfile and self.lastfile <= ename:
            raise Error('%r must come before %r' 
                             % (''.join(ename), ''.join(self.lastfile)))
        self.lastfile = ename
        self.level = _golevel(self.level, self.f, ename, entry,
                              self.metastore, self.tmax)

    def add(self, name, st, meta_ofs, hashgen = None):
        endswith = name.endswith('/')
        ename = pathsplit(name)
        basename = ename[-1]
        #log('add: %r %r\n' % (basename, name))
        flags = IX_EXISTS
        sha = None
        if hashgen:
            (gitmode, sha) = hashgen(name)
            flags |= IX_HASHVALID
        else:
            (gitmode, sha) = (0, EMPTY_SHA)
        if st:
            isdir = stat.S_ISDIR(st.st_mode)
            assert(isdir == endswith)
            e = NewEntry(basename, name, self.tmax,
                         st.st_dev, st.st_ino, st.st_nlink,
                         st.st_ctime, st.st_mtime, st.st_atime,
                         st.st_uid, st.st_gid,
                         st.st_size, st.st_mode, gitmode, sha, flags,
                         meta_ofs, 0, 0)
        else:
            assert(endswith)
            meta_ofs = self.metastore.store(metadata.Metadata())
            e = BlankNewEntry(basename, meta_ofs, self.tmax)
            e.gitmode = gitmode
            e.sha = sha
            e.flags = flags
        self._add(ename, e)

    def add_ixentry(self, e):
        e.children_ofs = e.children_n = 0
        self._add(pathsplit(e.name), e)

    def new_reader(self):
        self.flush()
        return Reader(self.tmpname)


def reduce_paths(paths):
    xpaths = []
    for p in paths:
        rp = realpath(p)
        try:
            st = os.lstat(rp)
            if stat.S_ISDIR(st.st_mode):
                rp = slashappend(rp)
                p = slashappend(p)
            xpaths.append((rp, p))
        except OSError, e:
            add_error('reduce_paths: %s' % e)
    xpaths.sort()

    paths = []
    prev = None
    for (rp, p) in xpaths:
        if prev and (prev == rp 
                     or (prev.endswith('/') and rp.startswith(prev))):
            continue # already superceded by previous path
        paths.append((rp, p))
        prev = rp
    paths.sort(reverse=True)
    return paths

def merge(*iters):
    def pfunc(count, total):
        qprogress('bup: merging indexes (%d/%d)\r' % (count, total))
    def pfinal(count, total):
        progress('bup: merging indexes (%d/%d), done.\n' % (count, total))
    return merge_iter(iters, 1024, pfunc, pfinal, key='name')

########NEW FILE########
__FILENAME__ = ls
"""Common code for listing files from a bup repository."""
import copy, os.path, stat, xstat
from bup import metadata, options, vfs
from helpers import *


def node_info(n, name,
              show_hash = False,
              long_fmt = False,
              classification = None,
              numeric_ids = False,
              human_readable = False):
    """Return a string containing the information to display for the node
    n.  Classification may be "all", "type", or None."""
    result = ''
    if show_hash:
        result += "%s " % n.hash.encode('hex')
    if long_fmt:
        meta = copy.copy(n.metadata())
        if meta:
            meta.path = name
            meta.size = n.size()
        else:
            # Fake it -- summary_str() is designed to handle a fake.
            meta = metadata.Metadata()
            meta.size = n.size()
            meta.mode = n.mode
            meta.path = name
            meta.atime, meta.mtime, meta.ctime = n.atime, n.mtime, n.ctime
            if stat.S_ISLNK(meta.mode):
                meta.symlink_target = n.readlink()
        result += metadata.summary_str(meta,
                                       numeric_ids = numeric_ids,
                                       classification = classification,
                                       human_readable = human_readable)
    else:
        result += name
        if classification:
            mode = n.metadata() and n.metadata().mode or n.mode
            result += xstat.classification_str(mode, classification == 'all')
    return result


optspec = """
%sls [-a] [path...]
--
s,hash   show hash for each file
a,all    show hidden files
A,almost-all    show hidden files except . and ..
l        use a detailed, long listing format
d,directory show directories, not contents; don't follow symlinks
F,classify append type indicator: dir/ sym@ fifo| sock= exec*
file-type append type indicator: dir/ sym@ fifo| sock=
human-readable    print human readable file sizes (i.e. 3.9K, 4.7M)
n,numeric-ids list numeric IDs (user, group, etc.) rather than names
"""

def do_ls(args, pwd, default='.', onabort=None, spec_prefix=''):
    """Output a listing of a file or directory in the bup repository.

    When a long listing is not requested and stdout is attached to a
    tty, the output is formatted in columns. When not attached to tty
    (for example when the output is piped to another command), one
    file is listed per line.

    """
    if onabort:
        o = options.Options(optspec % spec_prefix, onabort=onabort)
    else:
        o = options.Options(optspec % spec_prefix)
    (opt, flags, extra) = o.parse(args)

    # Handle order-sensitive options.
    classification = None
    show_hidden = None
    for flag in flags:
        (option, parameter) = flag
        if option in ('-F', '--classify'):
            classification = 'all'
        elif option == '--file-type':
            classification = 'type'
        elif option in ('-a', '--all'):
            show_hidden = 'all'
        elif option in ('-A', '--almost-all'):
            show_hidden = 'almost'

    L = []
    def output_node_info(node, name):
        info = node_info(node, name,
                         show_hash = opt.hash,
                         long_fmt = opt.l,
                         classification = classification,
                         numeric_ids = opt.numeric_ids,
                         human_readable = opt.human_readable)
        if not opt.l and istty1:
            L.append(info)
        else:
            print info

    ret = 0
    for path in (extra or [default]):
        try:
            if opt.directory:
                n = pwd.lresolve(path)
            else:
                n = pwd.try_resolve(path)

            if not opt.directory and stat.S_ISDIR(n.mode):
                if show_hidden == 'all':
                    output_node_info(n, '.')
                    # Match non-bup "ls -a ... /".
                    if n.parent:
                        output_node_info(n.parent, '..')
                    else:
                        output_node_info(n, '..')
                for sub in n:
                    name = sub.name
                    if show_hidden in ('almost', 'all') \
                       or not len(name)>1 or not name.startswith('.'):
                        output_node_info(sub, name)
            else:
                output_node_info(n, os.path.normpath(path))
        except vfs.NodeError, e:
            log('error: %s\n' % e)
            ret = 1

    if L:
        sys.stdout.write(columnate(L, ''))

    return ret

########NEW FILE########
__FILENAME__ = metadata
"""Metadata read/write support for bup."""

# Copyright (C) 2010 Rob Browning
#
# This code is covered under the terms of the GNU Library General
# Public License as described in the bup LICENSE file.
import errno, os, sys, stat, time, pwd, grp, socket
from cStringIO import StringIO
from bup import vint, xstat
from bup.drecurse import recursive_dirlist
from bup.helpers import add_error, mkdirp, log, is_superuser, format_filesize
from bup.helpers import pwd_from_uid, pwd_from_name, grp_from_gid, grp_from_name
from bup.xstat import utime, lutime

xattr = None
if sys.platform.startswith('linux'):
    try:
        import xattr
    except ImportError:
        log('Warning: Linux xattr support missing; install python-pyxattr.\n')
    if xattr:
        try:
            xattr.get_all
        except AttributeError:
            log('Warning: python-xattr module is too old; '
                'install python-pyxattr instead.\n')
            xattr = None

posix1e = None
if not (sys.platform.startswith('cygwin') \
        or sys.platform.startswith('darwin') \
        or sys.platform.startswith('netbsd')):
    try:
        import posix1e
    except ImportError:
        log('Warning: POSIX ACL support missing; install python-pylibacl.\n')

try:
    from bup._helpers import get_linux_file_attr, set_linux_file_attr
except ImportError:
    # No need for a warning here; the only reason they won't exist is that we're
    # not on Linux, in which case files don't have any linux attrs anyway, so
    # lacking the functions isn't a problem.
    get_linux_file_attr = set_linux_file_attr = None
    

# WARNING: the metadata encoding is *not* stable yet.  Caveat emptor!

# Q: Consider hardlink support?
# Q: Is it OK to store raw linux attr (chattr) flags?
# Q: Can anything other than S_ISREG(x) or S_ISDIR(x) support posix1e ACLs?
# Q: Is the application of posix1e has_extended() correct?
# Q: Is one global --numeric-ids argument sufficient?
# Q: Do nfsv4 acls trump posix1e acls? (seems likely)
# Q: Add support for crtime -- ntfs, and (only internally?) ext*?

# FIXME: Fix relative/abs path detection/stripping wrt other platforms.
# FIXME: Add nfsv4 acl handling - see nfs4-acl-tools.
# FIXME: Consider other entries mentioned in stat(2) (S_IFDOOR, etc.).
# FIXME: Consider pack('vvvvsss', ...) optimization.

## FS notes:
#
# osx (varies between hfs and hfs+):
#   type - regular dir char block fifo socket ...
#   perms - rwxrwxrwxsgt
#   times - ctime atime mtime
#   uid
#   gid
#   hard-link-info (hfs+ only)
#   link-target
#   device-major/minor
#   attributes-osx see chflags
#   content-type
#   content-creator
#   forks
#
# ntfs
#   type - regular dir ...
#   times - creation, modification, posix change, access
#   hard-link-info
#   link-target
#   attributes - see attrib
#   ACLs
#   forks (alternate data streams)
#   crtime?
#
# fat
#   type - regular dir ...
#   perms - rwxrwxrwx (maybe - see wikipedia)
#   times - creation, modification, access
#   attributes - see attrib

verbose = 0

_have_lchmod = hasattr(os, 'lchmod')


def _clean_up_path_for_archive(p):
    # Not the most efficient approach.
    result = p

    # Take everything after any '/../'.
    pos = result.rfind('/../')
    if pos != -1:
        result = result[result.rfind('/../') + 4:]

    # Take everything after any remaining '../'.
    if result.startswith("../"):
        result = result[3:]

    # Remove any '/./' sequences.
    pos = result.find('/./')
    while pos != -1:
        result = result[0:pos] + '/' + result[pos + 3:]
        pos = result.find('/./')

    # Remove any leading '/'s.
    result = result.lstrip('/')

    # Replace '//' with '/' everywhere.
    pos = result.find('//')
    while pos != -1:
        result = result[0:pos] + '/' + result[pos + 2:]
        pos = result.find('//')

    # Take everything after any remaining './'.
    if result.startswith('./'):
        result = result[2:]

    # Take everything before any remaining '/.'.
    if result.endswith('/.'):
        result = result[:-2]

    if result == '' or result.endswith('/..'):
        result = '.'

    return result


def _risky_path(p):
    if p.startswith('/'):
        return True
    if p.find('/../') != -1:
        return True
    if p.startswith('../'):
        return True
    if p.endswith('/..'):
        return True
    return False


def _clean_up_extract_path(p):
    result = p.lstrip('/')
    if result == '':
        return '.'
    elif _risky_path(result):
        return None
    else:
        return result


# These tags are currently conceptually private to Metadata, and they
# must be unique, and must *never* be changed.
_rec_tag_end = 0
_rec_tag_path = 1
_rec_tag_common = 2 # times, user, group, type, perms, etc. (legacy/broken)
_rec_tag_symlink_target = 3
_rec_tag_posix1e_acl = 4      # getfacl(1), setfacl(1), etc.
_rec_tag_nfsv4_acl = 5        # intended to supplant posix1e? (unimplemented)
_rec_tag_linux_attr = 6       # lsattr(1) chattr(1)
_rec_tag_linux_xattr = 7      # getfattr(1) setfattr(1)
_rec_tag_hardlink_target = 8 # hard link target path
_rec_tag_common_v2 = 9 # times, user, group, type, perms, etc. (current)


class ApplyError(Exception):
    # Thrown when unable to apply any given bit of metadata to a path.
    pass


class Metadata:
    # Metadata is stored as a sequence of tagged binary records.  Each
    # record will have some subset of add, encode, load, create, and
    # apply methods, i.e. _add_foo...

    # We do allow an "empty" object as a special case, i.e. no
    # records.  One can be created by trying to write Metadata(), and
    # for such an object, read() will return None.  This is used by
    # "bup save", for example, as a placeholder in cases where
    # from_path() fails.

    # NOTE: if any relevant fields are added or removed, be sure to
    # update same_file() below.

    ## Common records

    # Timestamps are (sec, ns), relative to 1970-01-01 00:00:00, ns
    # must be non-negative and < 10**9.

    def _add_common(self, path, st):
        self.uid = st.st_uid
        self.gid = st.st_gid
        self.atime = st.st_atime
        self.mtime = st.st_mtime
        self.ctime = st.st_ctime
        self.user = self.group = ''
        entry = pwd_from_uid(st.st_uid)
        if entry:
            self.user = entry.pw_name
        entry = grp_from_gid(st.st_gid)
        if entry:
            self.group = entry.gr_name
        self.mode = st.st_mode
        # Only collect st_rdev if we might need it for a mknod()
        # during restore.  On some platforms (i.e. kFreeBSD), it isn't
        # stable for other file types.  For example "cp -a" will
        # change it for a plain file.
        if stat.S_ISCHR(st.st_mode) or stat.S_ISBLK(st.st_mode):
            self.rdev = st.st_rdev
        else:
            self.rdev = 0

    def _same_common(self, other):
        """Return true or false to indicate similarity in the hardlink sense."""
        return self.uid == other.uid \
            and self.gid == other.gid \
            and self.rdev == other.rdev \
            and self.mtime == other.mtime \
            and self.ctime == other.ctime \
            and self.user == other.user \
            and self.group == other.group

    def _encode_common(self):
        if not self.mode:
            return None
        atime = xstat.nsecs_to_timespec(self.atime)
        mtime = xstat.nsecs_to_timespec(self.mtime)
        ctime = xstat.nsecs_to_timespec(self.ctime)
        result = vint.pack('vvsvsvvVvVvV',
                           self.mode,
                           self.uid,
                           self.user,
                           self.gid,
                           self.group,
                           self.rdev,
                           atime[0],
                           atime[1],
                           mtime[0],
                           mtime[1],
                           ctime[0],
                           ctime[1])
        return result

    def _load_common_rec(self, port, legacy_format=False):
        unpack_fmt = 'vvsvsvvVvVvV'
        if legacy_format:
            unpack_fmt = 'VVsVsVvVvVvV'
        data = vint.read_bvec(port)
        (self.mode,
         self.uid,
         self.user,
         self.gid,
         self.group,
         self.rdev,
         self.atime,
         atime_ns,
         self.mtime,
         mtime_ns,
         self.ctime,
         ctime_ns) = vint.unpack(unpack_fmt, data)
        self.atime = xstat.timespec_to_nsecs((self.atime, atime_ns))
        self.mtime = xstat.timespec_to_nsecs((self.mtime, mtime_ns))
        self.ctime = xstat.timespec_to_nsecs((self.ctime, ctime_ns))

    def _recognized_file_type(self):
        return stat.S_ISREG(self.mode) \
            or stat.S_ISDIR(self.mode) \
            or stat.S_ISCHR(self.mode) \
            or stat.S_ISBLK(self.mode) \
            or stat.S_ISFIFO(self.mode) \
            or stat.S_ISSOCK(self.mode) \
            or stat.S_ISLNK(self.mode)

    def _create_via_common_rec(self, path, create_symlinks=True):
        if not self.mode:
            raise ApplyError('no metadata - cannot create path ' + path)

        # If the path already exists and is a dir, try rmdir.
        # If the path already exists and is anything else, try unlink.
        st = None
        try:
            st = xstat.lstat(path)
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise
        if st:
            if stat.S_ISDIR(st.st_mode):
                try:
                    os.rmdir(path)
                except OSError, e:
                    if e.errno in (errno.ENOTEMPTY, errno.EEXIST):
                        msg = 'refusing to overwrite non-empty dir ' + path
                        raise Exception(msg)
                    raise
            else:
                os.unlink(path)

        if stat.S_ISREG(self.mode):
            assert(self._recognized_file_type())
            fd = os.open(path, os.O_CREAT|os.O_WRONLY|os.O_EXCL, 0600)
            os.close(fd)
        elif stat.S_ISDIR(self.mode):
            assert(self._recognized_file_type())
            os.mkdir(path, 0700)
        elif stat.S_ISCHR(self.mode):
            assert(self._recognized_file_type())
            os.mknod(path, 0600 | stat.S_IFCHR, self.rdev)
        elif stat.S_ISBLK(self.mode):
            assert(self._recognized_file_type())
            os.mknod(path, 0600 | stat.S_IFBLK, self.rdev)
        elif stat.S_ISFIFO(self.mode):
            assert(self._recognized_file_type())
            os.mknod(path, 0600 | stat.S_IFIFO)
        elif stat.S_ISSOCK(self.mode):
            try:
                os.mknod(path, 0600 | stat.S_IFSOCK)
            except OSError, e:
                if e.errno in (errno.EINVAL, errno.EPERM):
                    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    s.bind(path)
                else:
                    raise
        elif stat.S_ISLNK(self.mode):
            assert(self._recognized_file_type())
            if self.symlink_target and create_symlinks:
                # on MacOS, symlink() permissions depend on umask, and there's
                # no way to chown a symlink after creating it, so we have to
                # be careful here!
                oldumask = os.umask((self.mode & 0777) ^ 0777)
                try:
                    os.symlink(self.symlink_target, path)
                finally:
                    os.umask(oldumask)
        # FIXME: S_ISDOOR, S_IFMPB, S_IFCMP, S_IFNWK, ... see stat(2).
        else:
            assert(not self._recognized_file_type())
            add_error('not creating "%s" with unrecognized mode "0x%x"\n'
                      % (path, self.mode))

    def _apply_common_rec(self, path, restore_numeric_ids=False):
        if not self.mode:
            raise ApplyError('no metadata - cannot apply to ' + path)

        # FIXME: S_ISDOOR, S_IFMPB, S_IFCMP, S_IFNWK, ... see stat(2).
        # EACCES errors at this stage are fatal for the current path.
        if lutime and stat.S_ISLNK(self.mode):
            try:
                lutime(path, (self.atime, self.mtime))
            except OSError, e:
                if e.errno == errno.EACCES:
                    raise ApplyError('lutime: %s' % e)
                else:
                    raise
        else:
            try:
                utime(path, (self.atime, self.mtime))
            except OSError, e:
                if e.errno == errno.EACCES:
                    raise ApplyError('utime: %s' % e)
                else:
                    raise

        uid = gid = -1 # By default, do nothing.
        if is_superuser():
            uid = self.uid
            gid = self.gid
            if not restore_numeric_ids:
                if self.uid != 0 and self.user:
                    entry = pwd_from_name(self.user)
                    if entry:
                        uid = entry.pw_uid
                if self.gid != 0 and self.group:
                    entry = grp_from_name(self.group)
                    if entry:
                        gid = entry.gr_gid
        else: # not superuser - only consider changing the group/gid
            user_gids = os.getgroups()
            if self.gid in user_gids:
                gid = self.gid
            if not restore_numeric_ids and self.gid != 0:
                # The grp might not exist on the local system.
                grps = filter(None, [grp_from_gid(x) for x in user_gids])
                if self.group in [x.gr_name for x in grps]:
                    g = grp_from_name(self.group)
                    if g:
                        gid = g.gr_gid

        if uid != -1 or gid != -1:
            try:
                os.lchown(path, uid, gid)
            except OSError, e:
                if e.errno == errno.EPERM:
                    add_error('lchown: %s' %  e)
                elif sys.platform.startswith('cygwin') \
                   and e.errno == errno.EINVAL:
                    add_error('lchown: unknown uid/gid (%d/%d) for %s'
                              %  (uid, gid, path))
                else:
                    raise

        if _have_lchmod:
            os.lchmod(path, stat.S_IMODE(self.mode))
        elif not stat.S_ISLNK(self.mode):
            os.chmod(path, stat.S_IMODE(self.mode))


    ## Path records

    def _encode_path(self):
        if self.path:
            return vint.pack('s', self.path)
        else:
            return None

    def _load_path_rec(self, port):
        self.path = vint.unpack('s', vint.read_bvec(port))[0]


    ## Symlink targets

    def _add_symlink_target(self, path, st):
        try:
            if stat.S_ISLNK(st.st_mode):
                self.symlink_target = os.readlink(path)
        except OSError, e:
            add_error('readlink: %s', e)

    def _encode_symlink_target(self):
        return self.symlink_target

    def _load_symlink_target_rec(self, port):
        self.symlink_target = vint.read_bvec(port)


    ## Hardlink targets

    def _add_hardlink_target(self, target):
        self.hardlink_target = target

    def _same_hardlink_target(self, other):
        """Return true or false to indicate similarity in the hardlink sense."""
        return self.hardlink_target == other.hardlink_target

    def _encode_hardlink_target(self):
        return self.hardlink_target

    def _load_hardlink_target_rec(self, port):
        self.hardlink_target = vint.read_bvec(port)


    ## POSIX1e ACL records

    # Recorded as a list:
    #   [txt_id_acl, num_id_acl]
    # or, if a directory:
    #   [txt_id_acl, num_id_acl, txt_id_default_acl, num_id_default_acl]
    # The numeric/text distinction only matters when reading/restoring
    # a stored record.
    def _add_posix1e_acl(self, path, st):
        if not posix1e: return
        if not stat.S_ISLNK(st.st_mode):
            acls = None
            def_acls = None
            try:
                if posix1e.has_extended(path):
                    acl = posix1e.ACL(file=path)
                    acls = [acl, acl] # txt and num are the same
                    if stat.S_ISDIR(st.st_mode):
                        def_acl = posix1e.ACL(filedef=path)
                        def_acls = [def_acl, def_acl]
            except EnvironmentError, e:
                if e.errno not in (errno.EOPNOTSUPP, errno.ENOSYS):
                    raise
            if acls:
                txt_flags = posix1e.TEXT_ABBREVIATE
                num_flags = posix1e.TEXT_ABBREVIATE | posix1e.TEXT_NUMERIC_IDS
                acl_rep = [acls[0].to_any_text('', '\n', txt_flags),
                           acls[1].to_any_text('', '\n', num_flags)]
                if def_acls:
                    acl_rep.append(def_acls[0].to_any_text('', '\n', txt_flags))
                    acl_rep.append(def_acls[1].to_any_text('', '\n', num_flags))
                self.posix1e_acl = acl_rep

    def _same_posix1e_acl(self, other):
        """Return true or false to indicate similarity in the hardlink sense."""
        return self.posix1e_acl == other.posix1e_acl

    def _encode_posix1e_acl(self):
        # Encode as two strings (w/default ACL string possibly empty).
        if self.posix1e_acl:
            acls = self.posix1e_acl
            if len(acls) == 2:
                acls.extend(['', ''])
            return vint.pack('ssss', acls[0], acls[1], acls[2], acls[3])
        else:
            return None

    def _load_posix1e_acl_rec(self, port):
        acl_rep = vint.unpack('ssss', vint.read_bvec(port))
        if acl_rep[2] == '':
            acl_rep = acl_rep[:2]
        self.posix1e_acl = acl_rep

    def _apply_posix1e_acl_rec(self, path, restore_numeric_ids=False):
        def apply_acl(acl_rep, kind):
            try:
                acl = posix1e.ACL(text = acl_rep)
            except IOError, e:
                if e.errno == 0:
                    # pylibacl appears to return an IOError with errno
                    # set to 0 if a group referred to by the ACL rep
                    # doesn't exist on the current system.
                    raise ApplyError("POSIX1e ACL: can't create %r for %r"
                                     % (acl_rep, path))
                else:
                    raise
            try:
                acl.applyto(path, kind)
            except IOError, e:
                if e.errno == errno.EPERM or e.errno == errno.EOPNOTSUPP:
                    raise ApplyError('POSIX1e ACL applyto: %s' % e)
                else:
                    raise

        if not posix1e:
            if self.posix1e_acl:
                add_error("%s: can't restore ACLs; posix1e support missing.\n"
                          % path)
            return
        if self.posix1e_acl:
            acls = self.posix1e_acl
            if len(acls) > 2:
                if restore_numeric_ids:
                    apply_acl(acls[3], posix1e.ACL_TYPE_DEFAULT)
                else:
                    apply_acl(acls[2], posix1e.ACL_TYPE_DEFAULT)
            if restore_numeric_ids:
                apply_acl(acls[1], posix1e.ACL_TYPE_ACCESS)
            else:
                apply_acl(acls[0], posix1e.ACL_TYPE_ACCESS)


    ## Linux attributes (lsattr(1), chattr(1))

    def _add_linux_attr(self, path, st):
        if not get_linux_file_attr: return
        if stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode):
            try:
                attr = get_linux_file_attr(path)
                if attr != 0:
                    self.linux_attr = attr
            except OSError, e:
                if e.errno == errno.EACCES:
                    add_error('read Linux attr: %s' % e)
                elif e.errno in (errno.ENOTTY, errno.ENOSYS, errno.EOPNOTSUPP):
                    # Assume filesystem doesn't support attrs.
                    return
                else:
                    raise

    def _same_linux_attr(self, other):
        """Return true or false to indicate similarity in the hardlink sense."""
        return self.linux_attr == other.linux_attr

    def _encode_linux_attr(self):
        if self.linux_attr:
            return vint.pack('V', self.linux_attr)
        else:
            return None

    def _load_linux_attr_rec(self, port):
        data = vint.read_bvec(port)
        self.linux_attr = vint.unpack('V', data)[0]

    def _apply_linux_attr_rec(self, path, restore_numeric_ids=False):
        if self.linux_attr:
            if not set_linux_file_attr:
                add_error("%s: can't restore linuxattrs: "
                          "linuxattr support missing.\n" % path)
                return
            try:
                set_linux_file_attr(path, self.linux_attr)
            except OSError, e:
                if e.errno in (errno.ENOTTY, errno.EOPNOTSUPP, errno.ENOSYS,
                               errno.EACCES):
                    raise ApplyError('Linux chattr: %s (0x%s)'
                                     % (e, hex(self.linux_attr)))
                else:
                    raise


    ## Linux extended attributes (getfattr(1), setfattr(1))

    def _add_linux_xattr(self, path, st):
        if not xattr: return
        try:
            self.linux_xattr = xattr.get_all(path, nofollow=True)
        except EnvironmentError, e:
            if e.errno != errno.EOPNOTSUPP:
                raise

    def _same_linux_xattr(self, other):
        """Return true or false to indicate similarity in the hardlink sense."""
        return self.linux_xattr == other.linux_xattr

    def _encode_linux_xattr(self):
        if self.linux_xattr:
            result = vint.pack('V', len(self.linux_xattr))
            for name, value in self.linux_xattr:
                result += vint.pack('ss', name, value)
            return result
        else:
            return None

    def _load_linux_xattr_rec(self, file):
        data = vint.read_bvec(file)
        memfile = StringIO(data)
        result = []
        for i in range(vint.read_vuint(memfile)):
            key = vint.read_bvec(memfile)
            value = vint.read_bvec(memfile)
            result.append((key, value))
        self.linux_xattr = result

    def _apply_linux_xattr_rec(self, path, restore_numeric_ids=False):
        if not xattr:
            if self.linux_xattr:
                add_error("%s: can't restore xattr; xattr support missing.\n"
                          % path)
            return
        if not self.linux_xattr:
            return
        try:
            existing_xattrs = set(xattr.list(path, nofollow=True))
        except IOError, e:
            if e.errno == errno.EACCES:
                raise ApplyError('xattr.set %r: %s' % (path, e))
            else:
                raise
        for k, v in self.linux_xattr:
            if k not in existing_xattrs \
                    or v != xattr.get(path, k, nofollow=True):
                try:
                    xattr.set(path, k, v, nofollow=True)
                except IOError, e:
                    if e.errno == errno.EPERM \
                            or e.errno == errno.EOPNOTSUPP:
                        raise ApplyError('xattr.set %r: %s' % (path, e))
                    else:
                        raise
            existing_xattrs -= frozenset([k])
        for k in existing_xattrs:
            try:
                xattr.remove(path, k, nofollow=True)
            except IOError, e:
                if e.errno == errno.EPERM:
                    raise ApplyError('xattr.remove %r: %s' % (path, e))
                else:
                    raise

    def __init__(self):
        self.mode = self.uid = self.gid = self.user = self.group = None
        self.atime = self.mtime = self.ctime = None
        # optional members
        self.path = None
        self.size = None
        self.symlink_target = None
        self.hardlink_target = None
        self.linux_attr = None
        self.linux_xattr = None
        self.posix1e_acl = None

    def __repr__(self):
        result = ['<%s instance at %s' % (self.__class__, hex(id(self)))]
        if self.path:
            result += ' path:' + repr(self.path)
        if self.mode:
            result += ' mode:' + repr(xstat.mode_str(self.mode)
                                      + '(%s)' % hex(self.mode))
        if self.uid:
            result += ' uid:' + str(self.uid)
        if self.gid:
            result += ' gid:' + str(self.gid)
        if self.user:
            result += ' user:' + repr(self.user)
        if self.group:
            result += ' group:' + repr(self.group)
        if self.size:
            result += ' size:' + repr(self.size)
        for name, val in (('atime', self.atime),
                          ('mtime', self.mtime),
                          ('ctime', self.ctime)):
            result += ' %s:%r' \
                % (name,
                   time.strftime('%Y-%m-%d %H:%M %z',
                                 time.gmtime(xstat.fstime_floor_secs(val))))
        result += '>'
        return ''.join(result)

    def write(self, port, include_path=True):
        records = include_path and [(_rec_tag_path, self._encode_path())] or []
        records.extend([(_rec_tag_common_v2, self._encode_common()),
                        (_rec_tag_symlink_target,
                         self._encode_symlink_target()),
                        (_rec_tag_hardlink_target,
                         self._encode_hardlink_target()),
                        (_rec_tag_posix1e_acl, self._encode_posix1e_acl()),
                        (_rec_tag_linux_attr, self._encode_linux_attr()),
                        (_rec_tag_linux_xattr, self._encode_linux_xattr())])
        for tag, data in records:
            if data:
                vint.write_vuint(port, tag)
                vint.write_bvec(port, data)
        vint.write_vuint(port, _rec_tag_end)

    def encode(self, include_path=True):
        port = StringIO()
        self.write(port, include_path)
        return port.getvalue()

    @staticmethod
    def read(port):
        # This method should either return a valid Metadata object,
        # return None if there was no information at all (just a
        # _rec_tag_end), throw EOFError if there was nothing at all to
        # read, or throw an Exception if a valid object could not be
        # read completely.
        tag = vint.read_vuint(port)
        if tag == _rec_tag_end:
            return None
        try: # From here on, EOF is an error.
            result = Metadata()
            while True: # only exit is error (exception) or _rec_tag_end
                if tag == _rec_tag_path:
                    result._load_path_rec(port)
                elif tag == _rec_tag_common_v2:
                    result._load_common_rec(port)
                elif tag == _rec_tag_symlink_target:
                    result._load_symlink_target_rec(port)
                elif tag == _rec_tag_hardlink_target:
                    result._load_hardlink_target_rec(port)
                elif tag == _rec_tag_posix1e_acl:
                    result._load_posix1e_acl_rec(port)
                elif tag == _rec_tag_linux_attr:
                    result._load_linux_attr_rec(port)
                elif tag == _rec_tag_linux_xattr:
                    result._load_linux_xattr_rec(port)
                elif tag == _rec_tag_end:
                    return result
                elif tag == _rec_tag_common: # Should be very rare.
                    result._load_common_rec(port, legacy_format = True)
                else: # unknown record
                    vint.skip_bvec(port)
                tag = vint.read_vuint(port)
        except EOFError:
            raise Exception("EOF while reading Metadata")

    def isdir(self):
        return stat.S_ISDIR(self.mode)

    def create_path(self, path, create_symlinks=True):
        self._create_via_common_rec(path, create_symlinks=create_symlinks)

    def apply_to_path(self, path=None, restore_numeric_ids=False):
        # apply metadata to path -- file must exist
        if not path:
            path = self.path
        if not path:
            raise Exception('Metadata.apply_to_path() called with no path')
        if not self._recognized_file_type():
            add_error('not applying metadata to "%s"' % path
                      + ' with unrecognized mode "0x%x"\n' % self.mode)
            return
        num_ids = restore_numeric_ids
        for apply_metadata in (self._apply_common_rec,
                               self._apply_posix1e_acl_rec,
                               self._apply_linux_attr_rec,
                               self._apply_linux_xattr_rec):
            try:
                apply_metadata(path, restore_numeric_ids=num_ids)
            except ApplyError, e:
                add_error(e)

    def same_file(self, other):
        """Compare this to other for equivalency.  Return true if
        their information implies they could represent the same file
        on disk, in the hardlink sense.  Assume they're both regular
        files."""
        return self._same_common(other) \
            and self._same_hardlink_target(other) \
            and self._same_posix1e_acl(other) \
            and self._same_linux_attr(other) \
            and self._same_linux_xattr(other)


def from_path(path, statinfo=None, archive_path=None,
              save_symlinks=True, hardlink_target=None):
    result = Metadata()
    result.path = archive_path
    st = statinfo or xstat.lstat(path)
    result.size = st.st_size
    result._add_common(path, st)
    if save_symlinks:
        result._add_symlink_target(path, st)
    result._add_hardlink_target(hardlink_target)
    result._add_posix1e_acl(path, st)
    result._add_linux_attr(path, st)
    result._add_linux_xattr(path, st)
    return result


def save_tree(output_file, paths,
              recurse=False,
              write_paths=True,
              save_symlinks=True,
              xdev=False):

    # Issue top-level rewrite warnings.
    for path in paths:
        safe_path = _clean_up_path_for_archive(path)
        if safe_path != path:
            log('archiving "%s" as "%s"\n' % (path, safe_path))

    if not recurse:
        for p in paths:
            safe_path = _clean_up_path_for_archive(p)
            st = xstat.lstat(p)
            if stat.S_ISDIR(st.st_mode):
                safe_path += '/'
            m = from_path(p, statinfo=st, archive_path=safe_path,
                          save_symlinks=save_symlinks)
            if verbose:
                print >> sys.stderr, m.path
            m.write(output_file, include_path=write_paths)
    else:
        start_dir = os.getcwd()
        try:
            for (p, st) in recursive_dirlist(paths, xdev=xdev):
                dirlist_dir = os.getcwd()
                os.chdir(start_dir)
                safe_path = _clean_up_path_for_archive(p)
                m = from_path(p, statinfo=st, archive_path=safe_path,
                              save_symlinks=save_symlinks)
                if verbose:
                    print >> sys.stderr, m.path
                m.write(output_file, include_path=write_paths)
                os.chdir(dirlist_dir)
        finally:
            os.chdir(start_dir)


def _set_up_path(meta, create_symlinks=True):
    # Allow directories to exist as a special case -- might have
    # been created by an earlier longer path.
    if meta.isdir():
        mkdirp(meta.path)
    else:
        parent = os.path.dirname(meta.path)
        if parent:
            mkdirp(parent)
        meta.create_path(meta.path, create_symlinks=create_symlinks)


all_fields = frozenset(['path',
                        'mode',
                        'link-target',
                        'rdev',
                        'size',
                        'uid',
                        'gid',
                        'user',
                        'group',
                        'atime',
                        'mtime',
                        'ctime',
                        'linux-attr',
                        'linux-xattr',
                        'posix1e-acl'])


def summary_str(meta, numeric_ids = False, classification = None,
                human_readable = False):

    """Return a string containing the "ls -l" style listing for meta.
    Classification may be "all", "type", or None."""
    user_str = group_str = size_or_dev_str = '?'
    symlink_target = None
    if meta:
        name = meta.path
        mode_str = xstat.mode_str(meta.mode)
        symlink_target = meta.symlink_target
        mtime_secs = xstat.fstime_floor_secs(meta.mtime)
        mtime_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(mtime_secs))
        if meta.user and not numeric_ids:
            user_str = meta.user
        elif meta.uid != None:
            user_str = str(meta.uid)
        if meta.group and not numeric_ids:
            group_str = meta.group
        elif meta.gid != None:
            group_str = str(meta.gid)
        if stat.S_ISCHR(meta.mode) or stat.S_ISBLK(meta.mode):
            if meta.rdev:
                size_or_dev_str = '%d,%d' % (os.major(meta.rdev),
                                             os.minor(meta.rdev))
        elif meta.size != None:
            if human_readable:
                size_or_dev_str = format_filesize(meta.size)
            else:
                size_or_dev_str = str(meta.size)
        else:
            size_or_dev_str = '-'
        if classification:
            classification_str = \
                xstat.classification_str(meta.mode, classification == 'all')
    else:
        mode_str = '?' * 10
        mtime_str = '????-??-?? ??:??'
        classification_str = '?'

    name = name or ''
    if classification:
        name += classification_str
    if symlink_target:
        name += ' -> ' + meta.symlink_target

    return '%-10s %-11s %11s %16s %s' % (mode_str,
                                         user_str + "/" + group_str,
                                         size_or_dev_str,
                                         mtime_str,
                                         name)


def detailed_str(meta, fields = None):
    # FIXME: should optional fields be omitted, or empty i.e. "rdev:
    # 0", "link-target:", etc.
    if not fields:
        fields = all_fields

    result = []
    if 'path' in fields:
        path = meta.path or ''
        result.append('path: ' + path)
    if 'mode' in fields:
        result.append('mode: %s (%s)' % (oct(meta.mode),
                                         xstat.mode_str(meta.mode)))
    if 'link-target' in fields and stat.S_ISLNK(meta.mode):
        result.append('link-target: ' + meta.symlink_target)
    if 'rdev' in fields:
        if meta.rdev:
            result.append('rdev: %d,%d' % (os.major(meta.rdev),
                                           os.minor(meta.rdev)))
        else:
            result.append('rdev: 0')
    if 'size' in fields and meta.size:
        result.append('size: ' + str(meta.size))
    if 'uid' in fields:
        result.append('uid: ' + str(meta.uid))
    if 'gid' in fields:
        result.append('gid: ' + str(meta.gid))
    if 'user' in fields:
        result.append('user: ' + meta.user)
    if 'group' in fields:
        result.append('group: ' + meta.group)
    if 'atime' in fields:
        # If we don't have xstat.lutime, that means we have to use
        # utime(), and utime() has no way to set the mtime/atime of a
        # symlink.  Thus, the mtime/atime of a symlink is meaningless,
        # so let's not report it.  (That way scripts comparing
        # before/after won't trigger.)
        if xstat.lutime or not stat.S_ISLNK(meta.mode):
            result.append('atime: ' + xstat.fstime_to_sec_str(meta.atime))
        else:
            result.append('atime: 0')
    if 'mtime' in fields:
        if xstat.lutime or not stat.S_ISLNK(meta.mode):
            result.append('mtime: ' + xstat.fstime_to_sec_str(meta.mtime))
        else:
            result.append('mtime: 0')
    if 'ctime' in fields:
        result.append('ctime: ' + xstat.fstime_to_sec_str(meta.ctime))
    if 'linux-attr' in fields and meta.linux_attr:
        result.append('linux-attr: ' + hex(meta.linux_attr))
    if 'linux-xattr' in fields and meta.linux_xattr:
        for name, value in meta.linux_xattr:
            result.append('linux-xattr: %s -> %s' % (name, repr(value)))
    if 'posix1e-acl' in fields and meta.posix1e_acl:
        acl = meta.posix1e_acl[0]
        result.append('posix1e-acl: ' + acl + '\n')
        if stat.S_ISDIR(meta.mode):
            def_acl = meta.posix1e_acl[2]
            result.append('posix1e-acl-default: ' + def_acl + '\n')
    return '\n'.join(result)


class _ArchiveIterator:
    def next(self):
        try:
            return Metadata.read(self._file)
        except EOFError:
            raise StopIteration()

    def __iter__(self):
        return self

    def __init__(self, file):
        self._file = file


def display_archive(file):
    if verbose > 1:
        first_item = True
        for meta in _ArchiveIterator(file):
            if not first_item:
                print
            print detailed_str(meta)
            first_item = False
    elif verbose > 0:
        for meta in _ArchiveIterator(file):
            print summary_str(meta)
    elif verbose == 0:
        for meta in _ArchiveIterator(file):
            if not meta.path:
                print >> sys.stderr, \
                    'bup: no metadata path, but asked to only display path', \
                    '(increase verbosity?)'
                sys.exit(1)
            print meta.path


def start_extract(file, create_symlinks=True):
    for meta in _ArchiveIterator(file):
        if not meta: # Hit end record.
            break
        if verbose:
            print >> sys.stderr, meta.path
        xpath = _clean_up_extract_path(meta.path)
        if not xpath:
            add_error(Exception('skipping risky path "%s"' % meta.path))
        else:
            meta.path = xpath
            _set_up_path(meta, create_symlinks=create_symlinks)


def finish_extract(file, restore_numeric_ids=False):
    all_dirs = []
    for meta in _ArchiveIterator(file):
        if not meta: # Hit end record.
            break
        xpath = _clean_up_extract_path(meta.path)
        if not xpath:
            add_error(Exception('skipping risky path "%s"' % dir.path))
        else:
            if os.path.isdir(meta.path):
                all_dirs.append(meta)
            else:
                if verbose:
                    print >> sys.stderr, meta.path
                meta.apply_to_path(path=xpath,
                                   restore_numeric_ids=restore_numeric_ids)
    all_dirs.sort(key = lambda x : len(x.path), reverse=True)
    for dir in all_dirs:
        # Don't need to check xpath -- won't be in all_dirs if not OK.
        xpath = _clean_up_extract_path(dir.path)
        if verbose:
            print >> sys.stderr, dir.path
        dir.apply_to_path(path=xpath, restore_numeric_ids=restore_numeric_ids)


def extract(file, restore_numeric_ids=False, create_symlinks=True):
    # For now, just store all the directories and handle them last,
    # longest first.
    all_dirs = []
    for meta in _ArchiveIterator(file):
        if not meta: # Hit end record.
            break
        xpath = _clean_up_extract_path(meta.path)
        if not xpath:
            add_error(Exception('skipping risky path "%s"' % meta.path))
        else:
            meta.path = xpath
            if verbose:
                print >> sys.stderr, '+', meta.path
            _set_up_path(meta, create_symlinks=create_symlinks)
            if os.path.isdir(meta.path):
                all_dirs.append(meta)
            else:
                if verbose:
                    print >> sys.stderr, '=', meta.path
                meta.apply_to_path(restore_numeric_ids=restore_numeric_ids)
    all_dirs.sort(key = lambda x : len(x.path), reverse=True)
    for dir in all_dirs:
        # Don't need to check xpath -- won't be in all_dirs if not OK.
        xpath = _clean_up_extract_path(dir.path)
        if verbose:
            print >> sys.stderr, '=', xpath
        # Shouldn't have to check for risky paths here (omitted above).
        dir.apply_to_path(path=dir.path,
                          restore_numeric_ids=restore_numeric_ids)

########NEW FILE########
__FILENAME__ = midx
import mmap
from bup import _helpers
from bup.helpers import *

MIDX_VERSION = 4

extract_bits = _helpers.extract_bits
_total_searches = 0
_total_steps = 0


class PackMidx:
    """Wrapper which contains data from multiple index files.
    Multiple index (.midx) files constitute a wrapper around index (.idx) files
    and make it possible for bup to expand Git's indexing capabilities to vast
    amounts of files.
    """
    def __init__(self, filename):
        self.name = filename
        self.force_keep = False
        self.map = None
        assert(filename.endswith('.midx'))
        self.map = mmap_read(open(filename))
        if str(self.map[0:4]) != 'MIDX':
            log('Warning: skipping: invalid MIDX header in %r\n' % filename)
            self.force_keep = True
            return self._init_failed()
        ver = struct.unpack('!I', self.map[4:8])[0]
        if ver < MIDX_VERSION:
            log('Warning: ignoring old-style (v%d) midx %r\n' 
                % (ver, filename))
            self.force_keep = False  # old stuff is boring  
            return self._init_failed()
        if ver > MIDX_VERSION:
            log('Warning: ignoring too-new (v%d) midx %r\n'
                % (ver, filename))
            self.force_keep = True  # new stuff is exciting
            return self._init_failed()

        self.bits = _helpers.firstword(self.map[8:12])
        self.entries = 2**self.bits
        self.fanout = buffer(self.map, 12, self.entries*4)
        self.sha_ofs = 12 + self.entries*4
        self.nsha = nsha = self._fanget(self.entries-1)
        self.shatable = buffer(self.map, self.sha_ofs, nsha*20)
        self.which_ofs = self.sha_ofs + 20*nsha
        self.whichlist = buffer(self.map, self.which_ofs, nsha*4)
        self.idxnames = str(self.map[self.which_ofs + 4*nsha:]).split('\0')

    def __del__(self):
        self.close()

    def _init_failed(self):
        self.bits = 0
        self.entries = 1
        self.fanout = buffer('\0\0\0\0')
        self.shatable = buffer('\0'*20)
        self.idxnames = []

    def _fanget(self, i):
        start = i*4
        s = self.fanout[start:start+4]
        return _helpers.firstword(s)

    def _get(self, i):
        return str(self.shatable[i*20:(i+1)*20])

    def _get_idx_i(self, i):
        return struct.unpack('!I', self.whichlist[i*4:(i+1)*4])[0]

    def _get_idxname(self, i):
        return self.idxnames[self._get_idx_i(i)]

    def close(self):
        if self.map is not None:
            self.map.close()
            self.map = None

    def exists(self, hash, want_source=False):
        """Return nonempty if the object exists in the index files."""
        global _total_searches, _total_steps
        _total_searches += 1
        want = str(hash)
        el = extract_bits(want, self.bits)
        if el:
            start = self._fanget(el-1)
            startv = el << (32-self.bits)
        else:
            start = 0
            startv = 0
        end = self._fanget(el)
        endv = (el+1) << (32-self.bits)
        _total_steps += 1   # lookup table is a step
        hashv = _helpers.firstword(hash)
        #print '(%08x) %08x %08x %08x' % (extract_bits(want, 32), startv, hashv, endv)
        while start < end:
            _total_steps += 1
            #print '! %08x %08x %08x   %d - %d' % (startv, hashv, endv, start, end)
            mid = start + (hashv-startv)*(end-start-1)/(endv-startv)
            #print '  %08x %08x %08x   %d %d %d' % (startv, hashv, endv, start, mid, end)
            v = self._get(mid)
            #print '    %08x' % self._num(v)
            if v < want:
                start = mid+1
                startv = _helpers.firstword(v)
            elif v > want:
                end = mid
                endv = _helpers.firstword(v)
            else: # got it!
                return want_source and self._get_idxname(mid) or True
        return None

    def __iter__(self):
        for i in xrange(self._fanget(self.entries-1)):
            yield buffer(self.shatable, i*20, 20)

    def __len__(self):
        return int(self._fanget(self.entries-1))



########NEW FILE########
__FILENAME__ = options
# Copyright 2010-2012 Avery Pennarun and options.py contributors.
# All rights reserved.
#
# (This license applies to this file but not necessarily the other files in
# this package.)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#    1. Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#    2. Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in
#       the documentation and/or other materials provided with the
#       distribution.
#
# THIS SOFTWARE IS PROVIDED BY AVERY PENNARUN ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
"""Command-line options parser.
With the help of an options spec string, easily parse command-line options.

An options spec is made up of two parts, separated by a line with two dashes.
The first part is the synopsis of the command and the second one specifies
options, one per line.

Each non-empty line in the synopsis gives a set of options that can be used
together.

Option flags must be at the begining of the line and multiple flags are
separated by commas. Usually, options have a short, one character flag, and a
longer one, but the short one can be omitted.

Long option flags are used as the option's key for the OptDict produced when
parsing options.

When the flag definition is ended with an equal sign, the option takes
one string as an argument, and that string will be converted to an
integer when possible. Otherwise, the option does not take an argument
and corresponds to a boolean flag that is true when the option is
given on the command line.

The option's description is found at the right of its flags definition, after
one or more spaces. The description ends at the end of the line. If the
description contains text enclosed in square brackets, the enclosed text will
be used as the option's default value.

Options can be put in different groups. Options in the same group must be on
consecutive lines. Groups are formed by inserting a line that begins with a
space. The text on that line will be output after an empty line.
"""
import sys, os, textwrap, getopt, re, struct


def _invert(v, invert):
    if invert:
        return not v
    return v


def _remove_negative_kv(k, v):
    if k.startswith('no-') or k.startswith('no_'):
        return k[3:], not v
    return k,v


class OptDict(object):
    """Dictionary that exposes keys as attributes.

    Keys can be set or accessed with a "no-" or "no_" prefix to negate the
    value.
    """
    def __init__(self, aliases):
        self._opts = {}
        self._aliases = aliases

    def _unalias(self, k):
        k, reinvert = _remove_negative_kv(k, False)
        k, invert = self._aliases[k]
        return k, invert ^ reinvert

    def __setitem__(self, k, v):
        k, invert = self._unalias(k)
        self._opts[k] = _invert(v, invert)

    def __getitem__(self, k):
        k, invert = self._unalias(k)
        return _invert(self._opts[k], invert)

    def __getattr__(self, k):
        return self[k]


def _default_onabort(msg):
    sys.exit(97)


def _intify(v):
    try:
        vv = int(v or '')
        if str(vv) == v:
            return vv
    except ValueError:
        pass
    return v


def _atoi(v):
    try:
        return int(v or 0)
    except ValueError:
        return 0


def _tty_width():
    s = struct.pack("HHHH", 0, 0, 0, 0)
    try:
        import fcntl, termios
        s = fcntl.ioctl(sys.stderr.fileno(), termios.TIOCGWINSZ, s)
    except (IOError, ImportError):
        return _atoi(os.environ.get('WIDTH')) or 70
    (ysize,xsize,ypix,xpix) = struct.unpack('HHHH', s)
    return xsize or 70


class Options:
    """Option parser.
    When constructed, a string called an option spec must be given. It
    specifies the synopsis and option flags and their description.  For more
    information about option specs, see the docstring at the top of this file.

    Two optional arguments specify an alternative parsing function and an
    alternative behaviour on abort (after having output the usage string).

    By default, the parser function is getopt.gnu_getopt, and the abort
    behaviour is to exit the program.
    """
    def __init__(self, optspec, optfunc=getopt.gnu_getopt,
                 onabort=_default_onabort):
        self.optspec = optspec
        self._onabort = onabort
        self.optfunc = optfunc
        self._aliases = {}
        self._shortopts = 'h?'
        self._longopts = ['help', 'usage']
        self._hasparms = {}
        self._defaults = {}
        self._usagestr = self._gen_usage()  # this also parses the optspec

    def _gen_usage(self):
        out = []
        lines = self.optspec.strip().split('\n')
        lines.reverse()
        first_syn = True
        while lines:
            l = lines.pop()
            if l == '--': break
            out.append('%s: %s\n' % (first_syn and 'usage' or '   or', l))
            first_syn = False
        out.append('\n')
        last_was_option = False
        while lines:
            l = lines.pop()
            if l.startswith(' '):
                out.append('%s%s\n' % (last_was_option and '\n' or '',
                                       l.lstrip()))
                last_was_option = False
            elif l:
                (flags,extra) = (l + ' ').split(' ', 1)
                extra = extra.strip()
                if flags.endswith('='):
                    flags = flags[:-1]
                    has_parm = 1
                else:
                    has_parm = 0
                g = re.search(r'\[([^\]]*)\]$', extra)
                if g:
                    defval = _intify(g.group(1))
                else:
                    defval = None
                flagl = flags.split(',')
                flagl_nice = []
                flag_main, invert_main = _remove_negative_kv(flagl[0], False)
                self._defaults[flag_main] = _invert(defval, invert_main)
                for _f in flagl:
                    f,invert = _remove_negative_kv(_f, 0)
                    self._aliases[f] = (flag_main, invert_main ^ invert)
                    self._hasparms[f] = has_parm
                    if f == '#':
                        self._shortopts += '0123456789'
                        flagl_nice.append('-#')
                    elif len(f) == 1:
                        self._shortopts += f + (has_parm and ':' or '')
                        flagl_nice.append('-' + f)
                    else:
                        f_nice = re.sub(r'\W', '_', f)
                        self._aliases[f_nice] = (flag_main,
                                                 invert_main ^ invert)
                        self._longopts.append(f + (has_parm and '=' or ''))
                        self._longopts.append('no-' + f)
                        flagl_nice.append('--' + _f)
                flags_nice = ', '.join(flagl_nice)
                if has_parm:
                    flags_nice += ' ...'
                prefix = '    %-20s  ' % flags_nice
                argtext = '\n'.join(textwrap.wrap(extra, width=_tty_width(),
                                                initial_indent=prefix,
                                                subsequent_indent=' '*28))
                out.append(argtext + '\n')
                last_was_option = True
            else:
                out.append('\n')
                last_was_option = False
        return ''.join(out).rstrip() + '\n'

    def usage(self, msg=""):
        """Print usage string to stderr and abort."""
        sys.stderr.write(self._usagestr)
        if msg:
            sys.stderr.write(msg)
        e = self._onabort and self._onabort(msg) or None
        if e:
            raise e

    def fatal(self, msg):
        """Print an error message to stderr and abort with usage string."""
        msg = '\nerror: %s\n' % msg
        return self.usage(msg)

    def parse(self, args):
        """Parse a list of arguments and return (options, flags, extra).

        In the returned tuple, "options" is an OptDict with known options,
        "flags" is a list of option flags that were used on the command-line,
        and "extra" is a list of positional arguments.
        """
        try:
            (flags,extra) = self.optfunc(args, self._shortopts, self._longopts)
        except getopt.GetoptError, e:
            self.fatal(e)

        opt = OptDict(aliases=self._aliases)

        for k,v in self._defaults.iteritems():
            opt[k] = v

        for (k,v) in flags:
            k = k.lstrip('-')
            if k in ('h', '?', 'help', 'usage'):
                self.usage()
            if (self._aliases.get('#') and
                  k in ('0','1','2','3','4','5','6','7','8','9')):
                v = int(k)  # guaranteed to be exactly one digit
                k, invert = self._aliases['#']
                opt['#'] = v
            else:
                k, invert = opt._unalias(k)
                if not self._hasparms[k]:
                    assert(v == '')
                    v = (opt._opts.get(k) or 0) + 1
                else:
                    v = _intify(v)
            opt[k] = _invert(v, invert)
        return (opt,flags,extra)

########NEW FILE########
__FILENAME__ = path
"""This is a separate module so we can cleanly getcwd() before anyone
   does chdir().
"""
import sys, os

startdir = os.getcwd()

def exe():
    return (os.environ.get('BUP_MAIN_EXE') or
            os.path.join(startdir, sys.argv[0]))

def exedir():
    return os.path.split(exe())[0]

def exefile():
    return os.path.split(exe())[1]

########NEW FILE########
__FILENAME__ = shquote
import re

q = "'"
qq = '"'


class QuoteError(Exception):
    pass


def _quotesplit(line):
    inquote = None
    inescape = None
    wordstart = 0
    word = ''
    for i in range(len(line)):
        c = line[i]
        if inescape:
            if inquote == q and c != q:
                word += '\\'  # single-q backslashes can only quote single-q
            word += c
            inescape = False
        elif c == '\\':
            inescape = True
        elif c == inquote:
            inquote = None
            # this is un-sh-like, but do it for sanity when autocompleting
            yield (wordstart, word)
            word = ''
            wordstart = i+1
        elif not inquote and not word and (c == q or c == qq):
            # the 'not word' constraint on this is un-sh-like, but do it
            # for sanity when autocompleting
            inquote = c
            wordstart = i
        elif not inquote and c in [' ', '\n', '\r', '\t']:
            if word:
                yield (wordstart, word)
            word = ''
            wordstart = i+1
        else:
            word += c
    if word:
        yield (wordstart, word)
    if inquote or inescape or word:
        raise QuoteError()


def quotesplit(line):
    """Split 'line' into a list of offset,word tuples.

    The words are produced after removing doublequotes, singlequotes, and
    backslash escapes.

    Note that this implementation isn't entirely sh-compatible.  It only
    dequotes words that *start* with a quote character, that is, a string like
       hello"world"
    will not have its quotes removed, while a string like
       hello "world"
    will be turned into [(0, 'hello'), (6, 'world')] (ie. quotes removed).
    """
    l = []
    try:
        for i in _quotesplit(line):
            l.append(i)
    except QuoteError:
        pass
    return l


def unfinished_word(line):
    """Returns the quotechar,word of any unfinished word at the end of 'line'.

    You can use this to determine if 'line' is a completely parseable line
    (ie. one that quotesplit() will finish successfully) or if you need
    to read more bytes first.

    Args:
      line: an input string
    Returns:
      quotechar,word: the initial quote char (or None), and the partial word.
    """
    try:
        for (wordstart,word) in _quotesplit(line):
            pass
    except QuoteError:
        firstchar = line[wordstart]
        if firstchar in [q, qq]:
            return (firstchar, word)
        else:
            return (None, word)
    else:
        return (None, '')


def quotify(qtype, word, terminate):
    """Return a string corresponding to given word, quoted using qtype.

    The resulting string is dequotable using quotesplit() and can be
    joined with other quoted strings by adding arbitrary whitespace
    separators.

    Args:
      qtype: one of '', shquote.qq, or shquote.q
      word: the string to quote.  May contain arbitrary characters.
      terminate: include the trailing quote character, if any.
    Returns:
      The quoted string.
    """
    if qtype == qq:
        return qq + word.replace(qq, '\\"') + (terminate and qq or '')
    elif qtype == q:
        return q + word.replace(q, "\\'") + (terminate and q or '')
    else:
        return re.sub(r'([\"\' \t\n\r])', r'\\\1', word)


def quotify_list(words):
  """Return a minimally-quoted string produced by quoting each word.

  This calculates the qtype for each word depending on whether the word
  already includes singlequote characters, doublequote characters, both,
  or neither.

  Args:
    words: the list of words to quote.
  Returns:
    The resulting string, with quoted words separated by ' '.
  """
  wordout = []
  for word in words:
    qtype = q
    if word and not re.search(r'[\s\"\']', word):
      qtype = ''
    elif q in word and qq not in word:
      qtype = qq
    wordout.append(quotify(qtype, word, True))
  return ' '.join(wordout)


def what_to_add(qtype, origword, newword, terminate):
    """Return a qtype that is needed to finish a partial word.

    For example, given an origword of '\"frog' and a newword of '\"frogston',
    returns either:
       terminate=False: 'ston'
       terminate=True:  'ston\"'

    This is useful when calculating tab completion strings for readline.

    Args:
      qtype: the type of quoting to use (ie. the first character of origword)
      origword: the original word that needs completion.
      newword: the word we want it to be after completion.  Must start with
        origword.
      terminate: true if we should add the actual quote character at the end.
    Returns:
      The string to append to origword to produce (quoted) newword.
    """
    if not newword.startswith(origword):
        return ''
    else:
        qold = quotify(qtype, origword, terminate=False)
        return quotify(qtype, newword, terminate=terminate)[len(qold):]

########NEW FILE########
__FILENAME__ = ssh
"""SSH connection.
Connect to a remote host via SSH and execute a command on the host.
"""
import sys, os, re, subprocess
from bup import helpers, path


def connect(rhost, port, subcmd):
    """Connect to 'rhost' and execute the bup subcommand 'subcmd' on it."""
    assert(not re.search(r'[^\w-]', subcmd))
    nicedir = re.sub(r':', "_", path.exedir())
    if rhost == '-':
        rhost = None
    if not rhost:
        argv = ['bup', subcmd]
    else:
        # WARNING: shell quoting security holes are possible here, so we
        # have to be super careful.  We have to use 'sh -c' because
        # csh-derived shells can't handle PATH= notation.  We can't
        # set PATH in advance, because ssh probably replaces it.  We
        # can't exec *safely* using argv, because *both* ssh and 'sh -c'
        # allow shellquoting.  So we end up having to double-shellquote
        # stuff here.
        escapedir = re.sub(r'([^\w/])', r'\\\\\\\1', nicedir)
        buglvl = helpers.atoi(os.environ.get('BUP_DEBUG'))
        force_tty = helpers.atoi(os.environ.get('BUP_FORCE_TTY'))
        cmd = r"""
                   sh -c PATH=%s:'$PATH BUP_DEBUG=%s BUP_FORCE_TTY=%s bup %s'
               """ % (escapedir, buglvl, force_tty, subcmd)
        argv = ['ssh']
        if port:
            argv.extend(('-p', port))
        argv.extend((rhost, '--', cmd.strip()))
        #helpers.log('argv is: %r\n' % argv)
    def setup():
        # runs in the child process
        if not rhost:
            os.environ['PATH'] = ':'.join([nicedir,
                                           os.environ.get('PATH', '')])
        os.setsid()
    return subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            preexec_fn=setup)

########NEW FILE########
__FILENAME__ = tbloom
import errno, platform, tempfile
from bup import bloom
from bup.helpers import *
from wvtest import *

bup_tmp = os.path.realpath('../../../t/tmp')
mkdirp(bup_tmp)

@wvtest
def test_bloom():
    initial_failures = wvfailure_count()
    tmpdir = tempfile.mkdtemp(dir=bup_tmp, prefix='bup-tbloom-')
    hashes = [os.urandom(20) for i in range(100)]
    class Idx:
        pass
    ix = Idx()
    ix.name='dummy.idx'
    ix.shatable = ''.join(hashes)
    for k in (4, 5):
        b = bloom.create(tmpdir + '/pybuptest.bloom', expected=100, k=k)
        b.add_idx(ix)
        WVPASSLT(b.pfalse_positive(), .1)
        b.close()
        b = bloom.ShaBloom(tmpdir + '/pybuptest.bloom')
        all_present = True
        for h in hashes:
            all_present &= b.exists(h)
        WVPASS(all_present)
        false_positives = 0
        for h in [os.urandom(20) for i in range(1000)]:
            if b.exists(h):
                false_positives += 1
        WVPASSLT(false_positives, 5)
        os.unlink(tmpdir + '/pybuptest.bloom')

    tf = tempfile.TemporaryFile()
    b = bloom.create('bup.bloom', f=tf, expected=100)
    WVPASSEQ(b.rwfile, tf)
    WVPASSEQ(b.k, 5)

    # Test large (~1GiB) filter.  This may fail on s390 (31-bit
    # architecture), and anywhere else where the address space is
    # sufficiently limited.
    tf = tempfile.TemporaryFile()
    skip_test = False
    try:
        b = bloom.create('bup.bloom', f=tf, expected=2**28, delaywrite=False)
    except EnvironmentError, ex:
        (ptr_width, linkage) = platform.architecture()
        if ptr_width == '32bit' and ex.errno == errno.ENOMEM:
            WVMSG('skipping large bloom filter test (mmap probably failed) '
                  + str(ex))
            skip_test = True
        else:
            raise
    if not skip_test:
        WVPASSEQ(b.k, 4)
    if wvfailure_count() == initial_failures:
        subprocess.call(['rm', '-rf', tmpdir])

########NEW FILE########
__FILENAME__ = tclient
import sys, os, stat, time, random, subprocess, glob, tempfile
from bup import client, git
from bup.helpers import mkdirp
from wvtest import *

bup_tmp = os.path.realpath('../../../t/tmp')
mkdirp(bup_tmp)

def randbytes(sz):
    s = ''
    for i in xrange(sz):
        s += chr(random.randrange(0,256))
    return s

s1 = randbytes(10000)
s2 = randbytes(10000)
s3 = randbytes(10000)

IDX_PAT = '/*.idx'
    
@wvtest
def test_server_split_with_indexes():
    initial_failures = wvfailure_count()
    tmpdir = tempfile.mkdtemp(dir=bup_tmp, prefix='bup-tclient-')
    os.environ['BUP_MAIN_EXE'] = '../../../bup'
    os.environ['BUP_DIR'] = bupdir = tmpdir
    git.init_repo(bupdir)
    lw = git.PackWriter()
    c = client.Client(bupdir, create=True)
    rw = c.new_packwriter()

    lw.new_blob(s1)
    lw.close()

    rw.new_blob(s2)
    rw.breakpoint()
    rw.new_blob(s1)
    if wvfailure_count() == initial_failures:
        subprocess.call(['rm', '-rf', tmpdir])
    

@wvtest
def test_multiple_suggestions():
    initial_failures = wvfailure_count()
    tmpdir = tempfile.mkdtemp(dir=bup_tmp, prefix='bup-tclient-')
    os.environ['BUP_MAIN_EXE'] = '../../../bup'
    os.environ['BUP_DIR'] = bupdir = tmpdir
    git.init_repo(bupdir)

    lw = git.PackWriter()
    lw.new_blob(s1)
    lw.close()
    lw = git.PackWriter()
    lw.new_blob(s2)
    lw.close()
    WVPASSEQ(len(glob.glob(git.repo('objects/pack'+IDX_PAT))), 2)

    c = client.Client(bupdir, create=True)
    WVPASSEQ(len(glob.glob(c.cachedir+IDX_PAT)), 0)
    rw = c.new_packwriter()
    s1sha = rw.new_blob(s1)
    WVPASS(rw.exists(s1sha))
    s2sha = rw.new_blob(s2)
    # This is a little hacky, but ensures that we test the code under test
    while (len(glob.glob(c.cachedir+IDX_PAT)) < 2 and
           not c.conn.has_input()):
        pass
    rw.new_blob(s2)
    WVPASS(rw.objcache.exists(s1sha))
    WVPASS(rw.objcache.exists(s2sha))
    rw.new_blob(s3)
    WVPASSEQ(len(glob.glob(c.cachedir+IDX_PAT)), 2)
    rw.close()
    WVPASSEQ(len(glob.glob(c.cachedir+IDX_PAT)), 3)
    if wvfailure_count() == initial_failures:
        subprocess.call(['rm', '-rf', tmpdir])


@wvtest
def test_dumb_client_server():
    initial_failures = wvfailure_count()
    tmpdir = tempfile.mkdtemp(dir=bup_tmp, prefix='bup-tclient-')
    os.environ['BUP_MAIN_EXE'] = '../../../bup'
    os.environ['BUP_DIR'] = bupdir = tmpdir
    git.init_repo(bupdir)
    open(git.repo('bup-dumb-server'), 'w').close()

    lw = git.PackWriter()
    lw.new_blob(s1)
    lw.close()

    c = client.Client(bupdir, create=True)
    rw = c.new_packwriter()
    WVPASSEQ(len(glob.glob(c.cachedir+IDX_PAT)), 1)
    rw.new_blob(s1)
    WVPASSEQ(len(glob.glob(c.cachedir+IDX_PAT)), 1)
    rw.new_blob(s2)
    rw.close()
    WVPASSEQ(len(glob.glob(c.cachedir+IDX_PAT)), 2)
    if wvfailure_count() == initial_failures:
        subprocess.call(['rm', '-rf', tmpdir])


@wvtest
def test_midx_refreshing():
    initial_failures = wvfailure_count()
    tmpdir = tempfile.mkdtemp(dir=bup_tmp, prefix='bup-tclient-')
    os.environ['BUP_MAIN_EXE'] = bupmain = '../../../bup'
    os.environ['BUP_DIR'] = bupdir = tmpdir
    git.init_repo(bupdir)
    c = client.Client(bupdir, create=True)
    rw = c.new_packwriter()
    rw.new_blob(s1)
    p1base = rw.breakpoint()
    p1name = os.path.join(c.cachedir, p1base)
    s1sha = rw.new_blob(s1)  # should not be written; it's already in p1
    s2sha = rw.new_blob(s2)
    p2base = rw.close()
    p2name = os.path.join(c.cachedir, p2base)
    del rw

    pi = git.PackIdxList(bupdir + '/objects/pack')
    WVPASSEQ(len(pi.packs), 2)
    pi.refresh()
    WVPASSEQ(len(pi.packs), 2)
    WVPASSEQ(sorted([os.path.basename(i.name) for i in pi.packs]),
             sorted([p1base, p2base]))

    p1 = git.open_idx(p1name)
    WVPASS(p1.exists(s1sha))
    p2 = git.open_idx(p2name)
    WVFAIL(p2.exists(s1sha))
    WVPASS(p2.exists(s2sha))

    subprocess.call([bupmain, 'midx', '-f'])
    pi.refresh()
    WVPASSEQ(len(pi.packs), 1)
    pi.refresh(skip_midx=True)
    WVPASSEQ(len(pi.packs), 2)
    pi.refresh(skip_midx=False)
    WVPASSEQ(len(pi.packs), 1)
    if wvfailure_count() == initial_failures:
        subprocess.call(['rm', '-rf', tmpdir])


@wvtest
def test_remote_parsing():
    tests = (
        (':/bup', ('file', None, None, '/bup')),
        ('file:///bup', ('file', None, None, '/bup')),
        ('192.168.1.1:/bup', ('ssh', '192.168.1.1', None, '/bup')),
        ('ssh://192.168.1.1:2222/bup', ('ssh', '192.168.1.1', '2222', '/bup')),
        ('ssh://[ff:fe::1]:2222/bup', ('ssh', 'ff:fe::1', '2222', '/bup')),
        ('bup://foo.com:1950', ('bup', 'foo.com', '1950', None)),
        ('bup://foo.com:1950/bup', ('bup', 'foo.com', '1950', '/bup')),
        ('bup://[ff:fe::1]/bup', ('bup', 'ff:fe::1', None, '/bup')),
    )
    for remote, values in tests:
        WVPASSEQ(client.parse_remote(remote), values)
    try:
        client.parse_remote('http://asdf.com/bup')
        WVFAIL()
    except client.ClientError:
        WVPASS()

########NEW FILE########
__FILENAME__ = tgit
import struct, os, tempfile, time
from bup import git
from bup.helpers import *
from wvtest import *

bup_tmp = os.path.realpath('../../../t/tmp')
mkdirp(bup_tmp)

@wvtest
def testmangle():
    afile  = 0100644
    afile2 = 0100770
    alink  = 0120000
    adir   = 0040000
    adir2  = 0040777
    WVPASSEQ(git.mangle_name("a", adir2, adir), "a")
    WVPASSEQ(git.mangle_name(".bup", adir2, adir), ".bup.bupl")
    WVPASSEQ(git.mangle_name("a.bupa", adir2, adir), "a.bupa.bupl")
    WVPASSEQ(git.mangle_name("b.bup", alink, alink), "b.bup.bupl")
    WVPASSEQ(git.mangle_name("b.bu", alink, alink), "b.bu")
    WVPASSEQ(git.mangle_name("f", afile, afile2), "f")
    WVPASSEQ(git.mangle_name("f.bup", afile, afile2), "f.bup.bupl")
    WVPASSEQ(git.mangle_name("f.bup", afile, adir), "f.bup.bup")
    WVPASSEQ(git.mangle_name("f", afile, adir), "f.bup")

    WVPASSEQ(git.demangle_name("f.bup"), ("f", git.BUP_CHUNKED))
    WVPASSEQ(git.demangle_name("f.bupl"), ("f", git.BUP_NORMAL))
    WVPASSEQ(git.demangle_name("f.bup.bupl"), ("f.bup", git.BUP_NORMAL))

    # for safety, we ignore .bup? suffixes we don't recognize.  Future
    # versions might implement a .bup[a-z] extension as something other
    # than BUP_NORMAL.
    WVPASSEQ(git.demangle_name("f.bupa"), ("f.bupa", git.BUP_NORMAL))


@wvtest
def testencode():
    s = 'hello world'
    looseb = ''.join(git._encode_looseobj('blob', s))
    looset = ''.join(git._encode_looseobj('tree', s))
    loosec = ''.join(git._encode_looseobj('commit', s))
    packb = ''.join(git._encode_packobj('blob', s))
    packt = ''.join(git._encode_packobj('tree', s))
    packc = ''.join(git._encode_packobj('commit', s))
    WVPASSEQ(git._decode_looseobj(looseb), ('blob', s))
    WVPASSEQ(git._decode_looseobj(looset), ('tree', s))
    WVPASSEQ(git._decode_looseobj(loosec), ('commit', s))
    WVPASSEQ(git._decode_packobj(packb), ('blob', s))
    WVPASSEQ(git._decode_packobj(packt), ('tree', s))
    WVPASSEQ(git._decode_packobj(packc), ('commit', s))


@wvtest
def testpacks():
    initial_failures = wvfailure_count()
    tmpdir = tempfile.mkdtemp(dir=bup_tmp, prefix='bup-tgit-')
    os.environ['BUP_MAIN_EXE'] = bupmain = '../../../bup'
    os.environ['BUP_DIR'] = bupdir = tmpdir + "/bup"
    git.init_repo(bupdir)
    git.verbose = 1

    w = git.PackWriter()
    w.new_blob(os.urandom(100))
    w.new_blob(os.urandom(100))
    w.abort()

    w = git.PackWriter()
    hashes = []
    nobj = 1000
    for i in range(nobj):
        hashes.append(w.new_blob(str(i)))
    log('\n')
    nameprefix = w.close()
    print repr(nameprefix)
    WVPASS(os.path.exists(nameprefix + '.pack'))
    WVPASS(os.path.exists(nameprefix + '.idx'))

    r = git.open_idx(nameprefix + '.idx')
    print repr(r.fanout)

    for i in range(nobj):
        WVPASS(r.find_offset(hashes[i]) > 0)
    WVPASS(r.exists(hashes[99]))
    WVFAIL(r.exists('\0'*20))

    pi = iter(r)
    for h in sorted(hashes):
        WVPASSEQ(str(pi.next()).encode('hex'), h.encode('hex'))

    WVFAIL(r.find_offset('\0'*20))

    r = git.PackIdxList(bupdir + '/objects/pack')
    WVPASS(r.exists(hashes[5]))
    WVPASS(r.exists(hashes[6]))
    WVFAIL(r.exists('\0'*20))
    if wvfailure_count() == initial_failures:
        subprocess.call(['rm', '-rf', tmpdir])

@wvtest
def test_pack_name_lookup():
    initial_failures = wvfailure_count()
    tmpdir = tempfile.mkdtemp(dir=bup_tmp, prefix='bup-tgit-')
    os.environ['BUP_MAIN_EXE'] = bupmain = '../../../bup'
    os.environ['BUP_DIR'] = bupdir = tmpdir + "/bup"
    git.init_repo(bupdir)
    git.verbose = 1
    packdir = git.repo('objects/pack')

    idxnames = []
    hashes = []

    for start in range(0,28,2):
        w = git.PackWriter()
        for i in range(start, start+2):
            hashes.append(w.new_blob(str(i)))
        log('\n')
        idxnames.append(os.path.basename(w.close() + '.idx'))

    r = git.PackIdxList(packdir)
    WVPASSEQ(len(r.packs), 2)
    for e,idxname in enumerate(idxnames):
        for i in range(e*2, (e+1)*2):
            WVPASSEQ(r.exists(hashes[i], want_source=True), idxname)
    if wvfailure_count() == initial_failures:
        subprocess.call(['rm', '-rf', tmpdir])


@wvtest
def test_long_index():
    initial_failures = wvfailure_count()
    tmpdir = tempfile.mkdtemp(dir=bup_tmp, prefix='bup-tgit-')
    os.environ['BUP_MAIN_EXE'] = bupmain = '../../../bup'
    os.environ['BUP_DIR'] = bupdir = tmpdir + "/bup"
    git.init_repo(bupdir)
    w = git.PackWriter()
    obj_bin = struct.pack('!IIIII',
            0x00112233, 0x44556677, 0x88990011, 0x22334455, 0x66778899)
    obj2_bin = struct.pack('!IIIII',
            0x11223344, 0x55667788, 0x99001122, 0x33445566, 0x77889900)
    obj3_bin = struct.pack('!IIIII',
            0x22334455, 0x66778899, 0x00112233, 0x44556677, 0x88990011)
    pack_bin = struct.pack('!IIIII',
            0x99887766, 0x55443322, 0x11009988, 0x77665544, 0x33221100)
    idx = list(list() for i in xrange(256))
    idx[0].append((obj_bin, 1, 0xfffffffff))
    idx[0x11].append((obj2_bin, 2, 0xffffffffff))
    idx[0x22].append((obj3_bin, 3, 0xff))
    (fd,name) = tempfile.mkstemp(suffix='.idx', dir=git.repo('objects'))
    os.close(fd)
    w.count = 3
    r = w._write_pack_idx_v2(name, idx, pack_bin)
    i = git.PackIdxV2(name, open(name, 'rb'))
    WVPASSEQ(i.find_offset(obj_bin), 0xfffffffff)
    WVPASSEQ(i.find_offset(obj2_bin), 0xffffffffff)
    WVPASSEQ(i.find_offset(obj3_bin), 0xff)
    if wvfailure_count() == initial_failures:
        os.remove(name)
        subprocess.call(['rm', '-rf', tmpdir])


@wvtest
def test_check_repo_or_die():
    initial_failures = wvfailure_count()
    orig_cwd = os.getcwd()
    tmpdir = tempfile.mkdtemp(dir=bup_tmp, prefix='bup-tgit-')
    os.environ['BUP_DIR'] = bupdir = tmpdir + "/bup"
    try:
        os.chdir(tmpdir)
        git.init_repo(bupdir)
        git.check_repo_or_die()
        WVPASS('check_repo_or_die')  # if we reach this point the call above passed

        os.rename(bupdir + '/objects/pack', bupdir + '/objects/pack.tmp')
        open(bupdir + '/objects/pack', 'w').close()
        try:
            git.check_repo_or_die()
        except SystemExit, e:
            WVPASSEQ(e.code, 14)
        else:
            WVFAIL()
        os.unlink(bupdir + '/objects/pack')
        os.rename(bupdir + '/objects/pack.tmp', bupdir + '/objects/pack')

        try:
            git.check_repo_or_die('nonexistantbup.tmp')
        except SystemExit, e:
            WVPASSEQ(e.code, 15)
        else:
            WVFAIL()
    finally:
        os.chdir(orig_cwd)
    if wvfailure_count() == initial_failures:
        subprocess.call(['rm', '-rf', tmpdir])


@wvtest
def test_commit_parsing():
    def showval(commit, val):
        return readpipe(['git', 'show', '-s',
                         '--pretty=format:%s' % val, commit]).strip()
    initial_failures = wvfailure_count()
    orig_cwd = os.getcwd()
    tmpdir = tempfile.mkdtemp(dir=bup_tmp, prefix='bup-tgit-')
    workdir = tmpdir + "/work"
    repodir = workdir + '/.git'
    try:
        readpipe(['git', 'init', workdir])
        os.environ['GIT_DIR'] = os.environ['BUP_DIR'] = repodir
        git.check_repo_or_die(repodir)
        os.chdir(workdir)
        with open('foo', 'w') as f:
            print >> f, 'bar'
        readpipe(['git', 'add', '.'])
        readpipe(['git', 'commit', '-am', 'Do something',
                  '--author', 'Someone <someone@somewhere>',
                  '--date', 'Sat Oct 3 19:48:49 2009 -0400'])
        commit = readpipe(['git', 'show-ref', '-s', 'master']).strip()
        parents = showval(commit, '%P')
        tree = showval(commit, '%T')
        cname = showval(commit, '%cn')
        cmail = showval(commit, '%ce')
        cdate = showval(commit, '%ct')
        coffs = showval(commit, '%ci')
        coffs = coffs[-5:]
        coff = (int(coffs[-4:-2]) * 60 * 60) + (int(coffs[-2:]) * 60)
        if coffs[-5] == '-':
            coff = - coff
        commit_items = git.get_commit_items(commit, git.cp())
        WVPASSEQ(commit_items.parents, [])
        WVPASSEQ(commit_items.tree, tree)
        WVPASSEQ(commit_items.author_name, 'Someone')
        WVPASSEQ(commit_items.author_mail, 'someone@somewhere')
        WVPASSEQ(commit_items.author_sec, 1254613729)
        WVPASSEQ(commit_items.author_offset, -(4 * 60 * 60))
        WVPASSEQ(commit_items.committer_name, cname)
        WVPASSEQ(commit_items.committer_mail, cmail)
        WVPASSEQ(commit_items.committer_sec, int(cdate))
        WVPASSEQ(commit_items.committer_offset, coff)
        WVPASSEQ(commit_items.message, 'Do something\n')
        with open('bar', 'w') as f:
            print >> f, 'baz'
        readpipe(['git', 'add', '.'])
        readpipe(['git', 'commit', '-am', 'Do something else'])
        child = readpipe(['git', 'show-ref', '-s', 'master']).strip()
        parents = showval(child, '%P')
        commit_items = git.get_commit_items(child, git.cp())
        WVPASSEQ(commit_items.parents, [commit])
    finally:
        os.chdir(orig_cwd)
    if wvfailure_count() == initial_failures:
        subprocess.call(['rm', '-rf', tmpdir])

########NEW FILE########
__FILENAME__ = thashsplit
from bup import hashsplit, _helpers
from wvtest import *
from cStringIO import StringIO

@wvtest
def test_rolling_sums():
    WVPASS(_helpers.selftest())

@wvtest
def test_fanout_behaviour():

    # Drop in replacement for bupsplit, but splitting if the int value of a
    # byte >= BUP_BLOBBITS
    basebits = _helpers.blobbits()
    def splitbuf(buf):
        ofs = 0
        for c in buf:
            ofs += 1
            if ord(c) >= basebits:
                return ofs, ord(c)
        return 0, 0

    old_splitbuf = _helpers.splitbuf
    _helpers.splitbuf = splitbuf
    old_BLOB_MAX = hashsplit.BLOB_MAX
    hashsplit.BLOB_MAX = 4
    old_BLOB_READ_SIZE = hashsplit.BLOB_READ_SIZE
    hashsplit.BLOB_READ_SIZE = 10
    old_fanout = hashsplit.fanout
    hashsplit.fanout = 2

    levels = lambda f: [(len(b), l) for b, l in
        hashsplit.hashsplit_iter([f], True, None)]
    # Return a string of n null bytes
    z = lambda n: '\x00' * n
    # Return a byte which will be split with a level of n
    sb = lambda n: chr(basebits + n)

    split_never = StringIO(z(16))
    split_first = StringIO(z(1) + sb(3) + z(14))
    split_end   = StringIO(z(13) + sb(1) + z(2))
    split_many  = StringIO(sb(1) + z(3) + sb(2) + z(4) +
                            sb(0) + z(4) + sb(5) + z(1))
    WVPASSEQ(levels(split_never), [(4, 0), (4, 0), (4, 0), (4, 0)])
    WVPASSEQ(levels(split_first), [(2, 3), (4, 0), (4, 0), (4, 0), (2, 0)])
    WVPASSEQ(levels(split_end), [(4, 0), (4, 0), (4, 0), (2, 1), (2, 0)])
    WVPASSEQ(levels(split_many),
        [(1, 1), (4, 2), (4, 0), (1, 0), (4, 0), (1, 5), (1, 0)])

    _helpers.splitbuf = old_splitbuf
    hashsplit.BLOB_MAX = old_BLOB_MAX
    hashsplit.BLOB_READ_SIZE = old_BLOB_READ_SIZE
    hashsplit.fanout = old_fanout

########NEW FILE########
__FILENAME__ = thelpers
import helpers
import math
import os
import bup._helpers as _helpers
from bup.helpers import *
from wvtest import *


@wvtest
def test_next():
    # Test whatever you end up with for next() after import '*'.
    WVPASSEQ(next(iter([]), None), None)
    x = iter([1])
    WVPASSEQ(next(x, None), 1)
    WVPASSEQ(next(x, None), None)
    x = iter([1])
    WVPASSEQ(next(x, 'x'), 1)
    WVPASSEQ(next(x, 'x'), 'x')
    WVEXCEPT(StopIteration, next, iter([]))
    x = iter([1])
    WVPASSEQ(next(x), 1)
    WVEXCEPT(StopIteration, next, x)


@wvtest
def test_fallback_next():
    global next
    orig = next
    next = helpers._fallback_next
    try:
        test_next()
    finally:
        next = orig


@wvtest
def test_parse_num():
    pn = parse_num
    WVPASSEQ(pn('1'), 1)
    WVPASSEQ(pn('0'), 0)
    WVPASSEQ(pn('1.5k'), 1536)
    WVPASSEQ(pn('2 gb'), 2*1024*1024*1024)
    WVPASSEQ(pn('1e+9 k'), 1000000000 * 1024)
    WVPASSEQ(pn('-3e-3mb'), int(-0.003 * 1024 * 1024))

@wvtest
def test_detect_fakeroot():
    if os.getenv('FAKEROOTKEY'):
        WVPASS(detect_fakeroot())
    else:
        WVPASS(not detect_fakeroot())

@wvtest
def test_path_components():
    WVPASSEQ(path_components('/'), [('', '/')])
    WVPASSEQ(path_components('/foo'), [('', '/'), ('foo', '/foo')])
    WVPASSEQ(path_components('/foo/'), [('', '/'), ('foo', '/foo')])
    WVPASSEQ(path_components('/foo/bar'),
             [('', '/'), ('foo', '/foo'), ('bar', '/foo/bar')])
    WVEXCEPT(Exception, path_components, 'foo')


@wvtest
def test_stripped_path_components():
    WVPASSEQ(stripped_path_components('/', []), [('', '/')])
    WVPASSEQ(stripped_path_components('/', ['']), [('', '/')])
    WVPASSEQ(stripped_path_components('/', ['/']), [('', '/')])
    WVPASSEQ(stripped_path_components('/', ['/foo']), [('', '/')])
    WVPASSEQ(stripped_path_components('/foo', ['/bar']),
             [('', '/'), ('foo', '/foo')])
    WVPASSEQ(stripped_path_components('/foo', ['/foo']), [('', '/foo')])
    WVPASSEQ(stripped_path_components('/foo/bar', ['/foo']),
             [('', '/foo'), ('bar', '/foo/bar')])
    WVPASSEQ(stripped_path_components('/foo/bar', ['/bar', '/foo', '/baz']),
             [('', '/foo'), ('bar', '/foo/bar')])
    WVPASSEQ(stripped_path_components('/foo/bar/baz', ['/foo/bar/baz']),
             [('', '/foo/bar/baz')])
    WVEXCEPT(Exception, stripped_path_components, 'foo', [])


@wvtest
def test_grafted_path_components():
    WVPASSEQ(grafted_path_components([('/chroot', '/')], '/foo'),
             [('', '/'), ('foo', '/foo')])
    WVPASSEQ(grafted_path_components([('/foo/bar', '/')], '/foo/bar/baz/bax'),
             [('', '/foo/bar'),
              ('baz', '/foo/bar/baz'),
              ('bax', '/foo/bar/baz/bax')])
    WVPASSEQ(grafted_path_components([('/foo/bar/baz', '/bax')],
                                     '/foo/bar/baz/1/2'),
             [('', None),
              ('bax', '/foo/bar/baz'),
              ('1', '/foo/bar/baz/1'),
              ('2', '/foo/bar/baz/1/2')])
    WVPASSEQ(grafted_path_components([('/foo', '/bar/baz/bax')],
                                     '/foo/bar'),
             [('', None),
              ('bar', None),
              ('baz', None),
              ('bax', '/foo'),
              ('bar', '/foo/bar')])
    WVPASSEQ(grafted_path_components([('/foo/bar/baz', '/a/b/c')],
                                     '/foo/bar/baz'),
             [('', None), ('a', None), ('b', None), ('c', '/foo/bar/baz')])
    WVPASSEQ(grafted_path_components([('/', '/a/b/c/')], '/foo/bar'),
             [('', None), ('a', None), ('b', None), ('c', '/'),
              ('foo', '/foo'), ('bar', '/foo/bar')])
    WVEXCEPT(Exception, grafted_path_components, 'foo', [])


@wvtest
def test_readpipe():
    x = readpipe(['echo', '42'])
    WVPASSEQ(x, '42\n')
    try:
        readpipe(['bash', '-c', 'exit 42'])
    except Exception, ex:
        WVPASSEQ(str(ex), "subprocess 'bash -c exit 42' failed with status 42")


@wvtest
def test_batchpipe():
    for chunk in batchpipe(['echo'], []):
        WVPASS(False)
    out = ''
    for chunk in batchpipe(['echo'], ['42']):
        out += chunk
    WVPASSEQ(out, '42\n')
    try:
        batchpipe(['bash', '-c'], ['exit 42'])
    except Exception, ex:
        WVPASSEQ(str(ex), "subprocess 'bash -c exit 42' failed with status 42")
    args = [str(x) for x in range(6)]
    # Force batchpipe to break the args into batches of 3.  This
    # approach assumes all args are the same length.
    arg_max = \
        helpers._argmax_base(['echo']) + helpers._argmax_args_size(args[:3])
    batches = batchpipe(['echo'], args, arg_max=arg_max)
    WVPASSEQ(next(batches), '0 1 2\n')
    WVPASSEQ(next(batches), '3 4 5\n')
    WVPASSEQ(next(batches, None), None)
    batches = batchpipe(['echo'], [str(x) for x in range(5)], arg_max=arg_max)
    WVPASSEQ(next(batches), '0 1 2\n')
    WVPASSEQ(next(batches), '3 4\n')
    WVPASSEQ(next(batches, None), None)

########NEW FILE########
__FILENAME__ = tindex
import os
import time, tempfile
from bup import index, metadata
from bup.helpers import *
import bup.xstat as xstat
from wvtest import *

lib_t_dir = os.getcwd()
bup_tmp = os.path.realpath('../../../t/tmp')
mkdirp(bup_tmp)

@wvtest
def index_basic():
    cd = os.path.realpath('../../../t')
    WVPASS(cd)
    sd = os.path.realpath(cd + '/sampledata')
    WVPASSEQ(index.realpath(cd + '/sampledata'), cd + '/sampledata')
    WVPASSEQ(os.path.realpath(cd + '/sampledata/x'), sd + '/x')
    WVPASSEQ(os.path.realpath(cd + '/sampledata/etc'), os.path.realpath('/etc'))
    WVPASSEQ(index.realpath(cd + '/sampledata/etc'), sd + '/etc')


@wvtest
def index_writer():
    initial_failures = wvfailure_count()
    tmpdir = tempfile.mkdtemp(dir=bup_tmp, prefix='bup-tindex-')
    orig_cwd = os.getcwd()
    try:
        os.chdir(tmpdir)
        ds = xstat.stat('.')
        fs = xstat.stat(lib_t_dir + '/tindex.py')
        ms = index.MetaStoreWriter('index.meta.tmp');
        tmax = (time.time() - 1) * 10**9
        w = index.Writer('index.tmp', ms, tmax)
        w.add('/var/tmp/sporky', fs, 0)
        w.add('/etc/passwd', fs, 0)
        w.add('/etc/', ds, 0)
        w.add('/', ds, 0)
        ms.close()
        w.close()
    finally:
        os.chdir(orig_cwd)
    if wvfailure_count() == initial_failures:
        subprocess.call(['rm', '-rf', tmpdir])


def dump(m):
    for e in list(m):
        print '%s%s %s' % (e.is_valid() and ' ' or 'M',
                           e.is_fake() and 'F' or ' ',
                           e.name)

def fake_validate(*l):
    for i in l:
        for e in i:
            e.validate(0100644, index.FAKE_SHA)
            e.repack()

def eget(l, ename):
    for e in l:
        if e.name == ename:
            return e

@wvtest
def index_negative_timestamps():
    initial_failures = wvfailure_count()
    tmpdir = tempfile.mkdtemp(dir=bup_tmp, prefix='bup-tindex-')
    # Makes 'foo' exist
    f = file('foo', 'wb')
    f.close()

    # Dec 31, 1969
    os.utime("foo", (-86400, -86400))
    ns_per_sec = 10**9
    tstart = time.time() * ns_per_sec
    tmax = tstart - ns_per_sec
    e = index.BlankNewEntry("foo", 0, tmax)
    e.from_stat(xstat.stat("foo"), 0, tstart)
    assert len(e.packed())
    WVPASS()

    # Jun 10, 1893
    os.utime("foo", (-0x80000000, -0x80000000))
    e = index.BlankNewEntry("foo", 0, tmax)
    e.from_stat(xstat.stat("foo"), 0, tstart)
    assert len(e.packed())
    WVPASS()
    if wvfailure_count() == initial_failures:
        subprocess.call(['rm', '-rf', tmpdir])


@wvtest
def index_dirty():
    initial_failures = wvfailure_count()
    orig_cwd = os.getcwd()
    tmpdir = tempfile.mkdtemp(dir=bup_tmp, prefix='bup-tindex-')
    try:
        os.chdir(tmpdir)
        default_meta = metadata.Metadata()
        ms1 = index.MetaStoreWriter('index.meta.tmp')
        ms2 = index.MetaStoreWriter('index2.meta.tmp')
        ms3 = index.MetaStoreWriter('index3.meta.tmp')
        meta_ofs1 = ms1.store(default_meta)
        meta_ofs2 = ms2.store(default_meta)
        meta_ofs3 = ms3.store(default_meta)

        ds = xstat.stat(lib_t_dir)
        fs = xstat.stat(lib_t_dir + '/tindex.py')
        tmax = (time.time() - 1) * 10**9

        w1 = index.Writer('index.tmp', ms1, tmax)
        w1.add('/a/b/x', fs, meta_ofs1)
        w1.add('/a/b/c', fs, meta_ofs1)
        w1.add('/a/b/', ds, meta_ofs1)
        w1.add('/a/', ds, meta_ofs1)
        #w1.close()
        WVPASS()

        w2 = index.Writer('index2.tmp', ms2, tmax)
        w2.add('/a/b/n/2', fs, meta_ofs2)
        #w2.close()
        WVPASS()

        w3 = index.Writer('index3.tmp', ms3, tmax)
        w3.add('/a/c/n/3', fs, meta_ofs3)
        #w3.close()
        WVPASS()

        r1 = w1.new_reader()
        r2 = w2.new_reader()
        r3 = w3.new_reader()
        WVPASS()

        r1all = [e.name for e in r1]
        WVPASSEQ(r1all,
                 ['/a/b/x', '/a/b/c', '/a/b/', '/a/', '/'])
        r2all = [e.name for e in r2]
        WVPASSEQ(r2all,
                 ['/a/b/n/2', '/a/b/n/', '/a/b/', '/a/', '/'])
        r3all = [e.name for e in r3]
        WVPASSEQ(r3all,
                 ['/a/c/n/3', '/a/c/n/', '/a/c/', '/a/', '/'])
        all = [e.name for e in index.merge(r2, r1, r3)]
        WVPASSEQ(all,
                 ['/a/c/n/3', '/a/c/n/', '/a/c/',
                  '/a/b/x', '/a/b/n/2', '/a/b/n/', '/a/b/c',
                  '/a/b/', '/a/', '/'])
        fake_validate(r1)
        dump(r1)

        print [hex(e.flags) for e in r1]
        WVPASSEQ([e.name for e in r1 if e.is_valid()], r1all)
        WVPASSEQ([e.name for e in r1 if not e.is_valid()], [])
        WVPASSEQ([e.name for e in index.merge(r2, r1, r3) if not e.is_valid()],
                 ['/a/c/n/3', '/a/c/n/', '/a/c/',
                  '/a/b/n/2', '/a/b/n/', '/a/b/', '/a/', '/'])

        expect_invalid = ['/'] + r2all + r3all
        expect_real = (set(r1all) - set(r2all) - set(r3all)) \
                        | set(['/a/b/n/2', '/a/c/n/3'])
        dump(index.merge(r2, r1, r3))
        for e in index.merge(r2, r1, r3):
            print e.name, hex(e.flags), e.ctime
            eiv = e.name in expect_invalid
            er  = e.name in expect_real
            WVPASSEQ(eiv, not e.is_valid())
            WVPASSEQ(er, e.is_real())
        fake_validate(r2, r3)
        dump(index.merge(r2, r1, r3))
        WVPASSEQ([e.name for e in index.merge(r2, r1, r3) if not e.is_valid()], [])

        e = eget(index.merge(r2, r1, r3), '/a/b/c')
        e.invalidate()
        e.repack()
        dump(index.merge(r2, r1, r3))
        WVPASSEQ([e.name for e in index.merge(r2, r1, r3) if not e.is_valid()],
                 ['/a/b/c', '/a/b/', '/a/', '/'])        
        w1.close()
        w2.close()
        w3.close()
    finally:
        os.chdir(orig_cwd)
    if wvfailure_count() == initial_failures:
        subprocess.call(['rm', '-rf', tmpdir])

########NEW FILE########
__FILENAME__ = tmetadata
import errno, glob, grp, pwd, stat, tempfile, subprocess
import bup.helpers as helpers
from bup import git, metadata, vfs
from bup.helpers import clear_errors, detect_fakeroot, is_superuser, realpath
from wvtest import *
from bup.xstat import utime, lutime


top_dir = '../../..'
bup_tmp = os.path.realpath('../../../t/tmp')
bup_path = top_dir + '/bup'
start_dir = os.getcwd()


def ex(*cmd):
    try:
        cmd_str = ' '.join(cmd)
        print >> sys.stderr, cmd_str
        rc = subprocess.call(cmd)
        if rc < 0:
            print >> sys.stderr, 'terminated by signal', - rc
            sys.exit(1)
        elif rc > 0:
            print >> sys.stderr, 'returned exit status', rc
            sys.exit(1)
    except OSError, e:
        print >> sys.stderr, 'subprocess call failed:', e
        sys.exit(1)


def setup_testfs():
    assert(sys.platform.startswith('linux'))
    # Set up testfs with user_xattr, etc.
    subprocess.call(['umount', 'testfs'])
    ex('dd', 'if=/dev/zero', 'of=testfs.img', 'bs=1M', 'count=32')
    ex('mke2fs', '-F', '-j', '-m', '0', 'testfs.img')
    ex('rm', '-rf', 'testfs')
    os.mkdir('testfs')
    ex('mount', '-o', 'loop,acl,user_xattr', 'testfs.img', 'testfs')
    # Hide, so that tests can't create risks.
    os.chown('testfs', 0, 0)
    os.chmod('testfs', 0700)


def cleanup_testfs():
    subprocess.call(['umount', 'testfs'])
    helpers.unlink('testfs.img')


@wvtest
def test_clean_up_archive_path():
    cleanup = metadata._clean_up_path_for_archive
    WVPASSEQ(cleanup('foo'), 'foo')
    WVPASSEQ(cleanup('/foo'), 'foo')
    WVPASSEQ(cleanup('///foo'), 'foo')
    WVPASSEQ(cleanup('/foo/bar'), 'foo/bar')
    WVPASSEQ(cleanup('foo/./bar'), 'foo/bar')
    WVPASSEQ(cleanup('/foo/./bar'), 'foo/bar')
    WVPASSEQ(cleanup('/foo/./bar/././baz'), 'foo/bar/baz')
    WVPASSEQ(cleanup('/foo/./bar///././baz'), 'foo/bar/baz')
    WVPASSEQ(cleanup('//./foo/./bar///././baz/.///'), 'foo/bar/baz/')
    WVPASSEQ(cleanup('./foo/./.bar'), 'foo/.bar')
    WVPASSEQ(cleanup('./foo/.'), 'foo')
    WVPASSEQ(cleanup('./foo/..'), '.')
    WVPASSEQ(cleanup('//./..//.../..//.'), '.')
    WVPASSEQ(cleanup('//./..//..././/.'), '...')
    WVPASSEQ(cleanup('/////.'), '.')
    WVPASSEQ(cleanup('/../'), '.')
    WVPASSEQ(cleanup(''), '.')


@wvtest
def test_risky_path():
    risky = metadata._risky_path
    WVPASS(risky('/foo'))
    WVPASS(risky('///foo'))
    WVPASS(risky('/../foo'))
    WVPASS(risky('../foo'))
    WVPASS(risky('foo/..'))
    WVPASS(risky('foo/../'))
    WVPASS(risky('foo/../bar'))
    WVFAIL(risky('foo'))
    WVFAIL(risky('foo/'))
    WVFAIL(risky('foo///'))
    WVFAIL(risky('./foo'))
    WVFAIL(risky('foo/.'))
    WVFAIL(risky('./foo/.'))
    WVFAIL(risky('foo/bar'))
    WVFAIL(risky('foo/./bar'))


@wvtest
def test_clean_up_extract_path():
    cleanup = metadata._clean_up_extract_path
    WVPASSEQ(cleanup('/foo'), 'foo')
    WVPASSEQ(cleanup('///foo'), 'foo')
    WVFAIL(cleanup('/../foo'))
    WVFAIL(cleanup('../foo'))
    WVFAIL(cleanup('foo/..'))
    WVFAIL(cleanup('foo/../'))
    WVFAIL(cleanup('foo/../bar'))
    WVPASSEQ(cleanup('foo'), 'foo')
    WVPASSEQ(cleanup('foo/'), 'foo/')
    WVPASSEQ(cleanup('foo///'), 'foo///')
    WVPASSEQ(cleanup('./foo'), './foo')
    WVPASSEQ(cleanup('foo/.'), 'foo/.')
    WVPASSEQ(cleanup('./foo/.'), './foo/.')
    WVPASSEQ(cleanup('foo/bar'), 'foo/bar')
    WVPASSEQ(cleanup('foo/./bar'), 'foo/./bar')
    WVPASSEQ(cleanup('/'), '.')
    WVPASSEQ(cleanup('./'), './')
    WVPASSEQ(cleanup('///foo/bar'), 'foo/bar')
    WVPASSEQ(cleanup('///foo/bar'), 'foo/bar')


@wvtest
def test_metadata_method():
    initial_failures = wvfailure_count()
    tmpdir = tempfile.mkdtemp(dir=bup_tmp, prefix='bup-tmetadata-')
    bup_dir = tmpdir + '/bup'
    data_path = tmpdir + '/foo'
    os.mkdir(data_path)
    ex('touch', data_path + '/file')
    ex('ln', '-s', 'file', data_path + '/symlink')
    test_time1 = 13 * 1000000000
    test_time2 = 42 * 1000000000
    utime(data_path + '/file', (0, test_time1))
    lutime(data_path + '/symlink', (0, 0))
    utime(data_path, (0, test_time2))
    ex(bup_path, '-d', bup_dir, 'init')
    ex(bup_path, '-d', bup_dir, 'index', '-v', data_path)
    ex(bup_path, '-d', bup_dir, 'save', '-tvvn', 'test', data_path)
    git.check_repo_or_die(bup_dir)
    top = vfs.RefList(None)
    n = top.lresolve('/test/latest' + realpath(data_path))
    m = n.metadata()
    WVPASS(m.mtime == test_time2)
    WVPASS(len(n.subs()) == 2)
    WVPASS(n.name == 'foo')
    WVPASS(set([x.name for x in n.subs()]) == set(['file', 'symlink']))
    for sub in n:
        if sub.name == 'file':
            m = sub.metadata()
            WVPASS(m.mtime == test_time1)
        elif sub.name == 'symlink':
            m = sub.metadata()
            WVPASS(m.mtime == 0)
    if wvfailure_count() == initial_failures:
        subprocess.call(['rm', '-rf', tmpdir])


def _first_err():
    if helpers.saved_errors:
        return str(helpers.saved_errors[0])
    return ''


@wvtest
def test_from_path_error():
    initial_failures = wvfailure_count()
    if is_superuser() or detect_fakeroot():
        return
    tmpdir = tempfile.mkdtemp(dir=bup_tmp, prefix='bup-tmetadata-')
    path = tmpdir + '/foo'
    os.mkdir(path)
    m = metadata.from_path(path, archive_path=path, save_symlinks=True)
    WVPASSEQ(m.path, path)
    os.chmod(path, 000)
    metadata.from_path(path, archive_path=path, save_symlinks=True)
    if metadata.get_linux_file_attr:
        WVPASS(len(helpers.saved_errors) == 1)
        errmsg = _first_err()
        WVPASS(errmsg.startswith('read Linux attr'))
        clear_errors()
    if wvfailure_count() == initial_failures:
        subprocess.call(['chmod', '-R', 'u+rwX', tmpdir])
        subprocess.call(['rm', '-rf', tmpdir])


def _linux_attr_supported(path):
    # Expects path to denote a regular file or a directory.
    if not metadata.get_linux_file_attr:
        return False
    try:
        metadata.get_linux_file_attr(path)
    except OSError, e:
        if e.errno in (errno.ENOTTY, errno.ENOSYS, errno.EOPNOTSUPP):
            return False
        else:
            raise
    return True


@wvtest
def test_apply_to_path_restricted_access():
    initial_failures = wvfailure_count()
    if is_superuser() or detect_fakeroot():
        return
    if sys.platform.startswith('cygwin'):
        return # chmod 000 isn't effective.
    tmpdir = tempfile.mkdtemp(dir=bup_tmp, prefix='bup-tmetadata-')
    parent = tmpdir + '/foo'
    path = parent + '/bar'
    os.mkdir(parent)
    os.mkdir(path)
    clear_errors()
    m = metadata.from_path(path, archive_path=path, save_symlinks=True)
    WVPASSEQ(m.path, path)
    os.chmod(parent, 000)
    m.apply_to_path(path)
    print >> sys.stderr, helpers.saved_errors
    expected_errors = ['utime: ']
    if m.linux_attr and _linux_attr_supported(tmpdir):
        expected_errors.append('Linux chattr: ')
    if metadata.xattr and m.linux_xattr:
        expected_errors.append("xattr.set '")
    WVPASS(len(helpers.saved_errors) == len(expected_errors))
    for i in xrange(len(expected_errors)):
        WVPASS(str(helpers.saved_errors[i]).startswith(expected_errors[i]))
    clear_errors()
    if wvfailure_count() == initial_failures:
        subprocess.call(['chmod', '-R', 'u+rwX', tmpdir])
        subprocess.call(['rm', '-rf', tmpdir])


@wvtest
def test_restore_over_existing_target():
    initial_failures = wvfailure_count()
    tmpdir = tempfile.mkdtemp(dir=bup_tmp, prefix='bup-tmetadata-')
    path = tmpdir + '/foo'
    os.mkdir(path)
    dir_m = metadata.from_path(path, archive_path=path, save_symlinks=True)
    os.rmdir(path)
    open(path, 'w').close()
    file_m = metadata.from_path(path, archive_path=path, save_symlinks=True)
    # Restore dir over file.
    WVPASSEQ(dir_m.create_path(path, create_symlinks=True), None)
    WVPASS(stat.S_ISDIR(os.stat(path).st_mode))
    # Restore dir over dir.
    WVPASSEQ(dir_m.create_path(path, create_symlinks=True), None)
    WVPASS(stat.S_ISDIR(os.stat(path).st_mode))
    # Restore file over dir.
    WVPASSEQ(file_m.create_path(path, create_symlinks=True), None)
    WVPASS(stat.S_ISREG(os.stat(path).st_mode))
    # Restore file over file.
    WVPASSEQ(file_m.create_path(path, create_symlinks=True), None)
    WVPASS(stat.S_ISREG(os.stat(path).st_mode))
    # Restore file over non-empty dir.
    os.remove(path)
    os.mkdir(path)
    open(path + '/bar', 'w').close()
    WVEXCEPT(Exception, file_m.create_path, path, create_symlinks=True)
    # Restore dir over non-empty dir.
    os.remove(path + '/bar')
    os.mkdir(path + '/bar')
    WVEXCEPT(Exception, dir_m.create_path, path, create_symlinks=True)
    if wvfailure_count() == initial_failures:
        subprocess.call(['rm', '-rf', tmpdir])


from bup.metadata import posix1e
if not posix1e:
    @wvtest
    def POSIX1E_ACL_SUPPORT_IS_MISSING():
        pass


from bup.metadata import xattr
if xattr:
    @wvtest
    def test_handling_of_incorrect_existing_linux_xattrs():
        if not is_superuser() or detect_fakeroot():
            WVMSG('skipping test -- not superuser')
            return
        setup_testfs()
        for f in glob.glob('testfs/*'):
            ex('rm', '-rf', f)
        path = 'testfs/foo'
        open(path, 'w').close()
        xattr.set(path, 'foo', 'bar', namespace=xattr.NS_USER)
        m = metadata.from_path(path, archive_path=path, save_symlinks=True)
        xattr.set(path, 'baz', 'bax', namespace=xattr.NS_USER)
        m.apply_to_path(path, restore_numeric_ids=False)
        WVPASSEQ(xattr.list(path), ['user.foo'])
        WVPASSEQ(xattr.get(path, 'user.foo'), 'bar')
        xattr.set(path, 'foo', 'baz', namespace=xattr.NS_USER)
        m.apply_to_path(path, restore_numeric_ids=False)
        WVPASSEQ(xattr.list(path), ['user.foo'])
        WVPASSEQ(xattr.get(path, 'user.foo'), 'bar')
        xattr.remove(path, 'foo', namespace=xattr.NS_USER)
        m.apply_to_path(path, restore_numeric_ids=False)
        WVPASSEQ(xattr.list(path), ['user.foo'])
        WVPASSEQ(xattr.get(path, 'user.foo'), 'bar')
        os.chdir(start_dir)
        cleanup_testfs()

########NEW FILE########
__FILENAME__ = toptions
from bup import options
from wvtest import *


@wvtest
def test_optdict():
    d = options.OptDict({
        'x': ('x', False),
        'y': ('y', False),
        'z': ('z', False),
        'other_thing': ('other_thing', False),
        'no_other_thing': ('other_thing', True),
        'no_z': ('z', True),
        'no_smart': ('smart', True),
        'smart': ('smart', False),
        'stupid': ('smart', True),
        'no_smart': ('smart', False),
    })
    WVPASS('foo')
    d['x'] = 5
    d['y'] = 4
    d['z'] = 99
    d['no_other_thing'] = 5
    WVPASSEQ(d.x, 5)
    WVPASSEQ(d.y, 4)
    WVPASSEQ(d.z, 99)
    WVPASSEQ(d.no_z, False)
    WVPASSEQ(d.no_other_thing, True)
    WVEXCEPT(KeyError, lambda: d.p)


invalid_optspec0 = """
"""


invalid_optspec1 = """
prog <whatever>
"""


invalid_optspec2 = """
--
x,y
"""


@wvtest
def test_invalid_optspec():
    WVPASS(options.Options(invalid_optspec0).parse([]))
    WVPASS(options.Options(invalid_optspec1).parse([]))
    WVPASS(options.Options(invalid_optspec2).parse([]))


optspec = """
prog <optionset> [stuff...]
prog [-t] <boggle>
--
t       test
q,quiet   quiet
l,longoption=   long option with parameters and a really really long description that will require wrapping
p= short option with parameters
onlylong  long option with no short
neveropt never called options
deftest1=  a default option with default [1]
deftest2=  a default option with [1] default [2]
deftest3=  a default option with [3] no actual default
deftest4=  a default option with [[square]]
deftest5=  a default option with "correct" [[square]
s,smart,no-stupid  disable stupidity
x,extended,no-simple   extended mode [2]
#,compress=  set compression level [5]
"""

@wvtest
def test_options():
    o = options.Options(optspec)
    (opt,flags,extra) = o.parse(['-tttqp', 7, '--longoption', '19',
                                 'hanky', '--onlylong', '-7'])
    WVPASSEQ(flags[0], ('-t', ''))
    WVPASSEQ(flags[1], ('-t', ''))
    WVPASSEQ(flags[2], ('-t', ''))
    WVPASSEQ(flags[3], ('-q', ''))
    WVPASSEQ(flags[4], ('-p', 7))
    WVPASSEQ(flags[5], ('--longoption', '19'))
    WVPASSEQ(extra, ['hanky'])
    WVPASSEQ((opt.t, opt.q, opt.p, opt.l, opt.onlylong,
              opt.neveropt), (3,1,7,19,1,None))
    WVPASSEQ((opt.deftest1, opt.deftest2, opt.deftest3, opt.deftest4,
              opt.deftest5), (1,2,None,None,'[square'))
    WVPASSEQ((opt.stupid, opt.no_stupid), (True, None))
    WVPASSEQ((opt.smart, opt.no_smart), (None, True))
    WVPASSEQ((opt.x, opt.extended, opt.no_simple), (2,2,2))
    WVPASSEQ((opt.no_x, opt.no_extended, opt.simple), (False,False,False))
    WVPASSEQ(opt['#'], 7)
    WVPASSEQ(opt.compress, 7)

    (opt,flags,extra) = o.parse(['--onlylong', '-t', '--no-onlylong',
                                 '--smart', '--simple'])
    WVPASSEQ((opt.t, opt.q, opt.onlylong), (1, None, 0))
    WVPASSEQ((opt.stupid, opt.no_stupid), (False, True))
    WVPASSEQ((opt.smart, opt.no_smart), (True, False))
    WVPASSEQ((opt.x, opt.extended, opt.no_simple), (0,0,0))
    WVPASSEQ((opt.no_x, opt.no_extended, opt.simple), (True,True,True))

########NEW FILE########
__FILENAME__ = tshquote
from bup import shquote
from wvtest import *

def qst(line):
    return [word for offset,word in shquote.quotesplit(line)]

@wvtest
def test_shquote():
    WVPASSEQ(qst("""  this is    basic \t\n\r text  """),
             ['this', 'is', 'basic', 'text'])
    WVPASSEQ(qst(r""" \"x\" "help" 'yelp' """), ['"x"', 'help', 'yelp'])
    WVPASSEQ(qst(r""" "'\"\"'" '\"\'' """), ["'\"\"'", '\\"\''])

    WVPASSEQ(shquote.quotesplit('  this is "unfinished'),
             [(2,'this'), (7,'is'), (10,'unfinished')])

    WVPASSEQ(shquote.quotesplit('"silly"\'will'),
             [(0,'silly'), (7,'will')])

    WVPASSEQ(shquote.unfinished_word('this is a "billy" "goat'),
             ('"', 'goat'))
    WVPASSEQ(shquote.unfinished_word("'x"),
             ("'", 'x'))
    WVPASSEQ(shquote.unfinished_word("abra cadabra "),
             (None, ''))
    WVPASSEQ(shquote.unfinished_word("abra cadabra"),
             (None, 'cadabra'))

    (qtype, word) = shquote.unfinished_word("this is /usr/loc")
    WVPASSEQ(shquote.what_to_add(qtype, word, "/usr/local", True),
             "al")
    (qtype, word) = shquote.unfinished_word("this is '/usr/loc")
    WVPASSEQ(shquote.what_to_add(qtype, word, "/usr/local", True),
             "al'")
    (qtype, word) = shquote.unfinished_word("this is \"/usr/loc")
    WVPASSEQ(shquote.what_to_add(qtype, word, "/usr/local", True),
             "al\"")
    (qtype, word) = shquote.unfinished_word("this is \"/usr/loc")
    WVPASSEQ(shquote.what_to_add(qtype, word, "/usr/local", False),
             "al")
    (qtype, word) = shquote.unfinished_word("this is \\ hammer\\ \"")
    WVPASSEQ(word, ' hammer "')
    WVPASSEQ(shquote.what_to_add(qtype, word, " hammer \"time\"", True),
             "time\\\"")

    WVPASSEQ(shquote.quotify_list(['a', '', '"word"', "'third'", "'", "x y"]),
             "a '' '\"word\"' \"'third'\" \"'\" 'x y'")

########NEW FILE########
__FILENAME__ = tvint
from bup import vint
from wvtest import *
from cStringIO import StringIO


def encode_and_decode_vuint(x):
    f = StringIO()
    vint.write_vuint(f, x)
    return vint.read_vuint(StringIO(f.getvalue()))


@wvtest
def test_vuint():
    for x in (0, 1, 42, 128, 10**16):
        WVPASSEQ(encode_and_decode_vuint(x), x)
    WVEXCEPT(Exception, vint.write_vuint, StringIO(), -1)
    WVEXCEPT(EOFError, vint.read_vuint, StringIO())


def encode_and_decode_vint(x):
    f = StringIO()
    vint.write_vint(f, x)
    return vint.read_vint(StringIO(f.getvalue()))


@wvtest
def test_vint():
    values = (0, 1, 42, 64, 10**16)
    for x in values:
        WVPASSEQ(encode_and_decode_vint(x), x)
    for x in [-x for x in values]:
        WVPASSEQ(encode_and_decode_vint(x), x)
    WVEXCEPT(EOFError, vint.read_vint, StringIO())


def encode_and_decode_bvec(x):
    f = StringIO()
    vint.write_bvec(f, x)
    return vint.read_bvec(StringIO(f.getvalue()))


@wvtest
def test_bvec():
    values = ('', 'x', 'foo', '\0', '\0foo', 'foo\0bar\0')
    for x in values:
        WVPASSEQ(encode_and_decode_bvec(x), x)
    WVEXCEPT(EOFError, vint.read_bvec, StringIO())
    outf = StringIO()
    for x in ('foo', 'bar', 'baz', 'bax'):
        vint.write_bvec(outf, x)
    inf = StringIO(outf.getvalue())
    WVPASSEQ(vint.read_bvec(inf), 'foo')
    WVPASSEQ(vint.read_bvec(inf), 'bar')
    vint.skip_bvec(inf)
    WVPASSEQ(vint.read_bvec(inf), 'bax')


def pack_and_unpack(types, *values):
    data = vint.pack(types, *values)
    return vint.unpack(types, data)


@wvtest
def test_pack_and_unpack():
    tests = [('', []),
             ('s', ['foo']),
             ('ss', ['foo', 'bar']),
             ('sV', ['foo', 0]),
             ('sv', ['foo', -1]),
             ('V', [0]),
             ('Vs', [0, 'foo']),
             ('VV', [0, 1]),
             ('Vv', [0, -1]),
             ('v', [0]),
             ('vs', [0, 'foo']),
             ('vV', [0, 1]),
             ('vv', [0, -1])]
    for test in tests:
        (types, values) = test
        WVPASSEQ(pack_and_unpack(types, *values), values)
    WVEXCEPT(Exception, vint.pack, 's')
    WVEXCEPT(Exception, vint.pack, 's', 'foo', 'bar')
    WVEXCEPT(Exception, vint.pack, 'x', 1)
    WVEXCEPT(Exception, vint.unpack, 's', '')
    WVEXCEPT(Exception, vint.unpack, 'x', '')

########NEW FILE########
__FILENAME__ = txstat
import math, tempfile, subprocess
from wvtest import *
import bup._helpers as _helpers
from bup import xstat

bup_tmp = os.path.realpath('../../../t/tmp')

@wvtest
def test_fstime():
    WVPASSEQ(xstat.timespec_to_nsecs((0, 0)), 0)
    WVPASSEQ(xstat.timespec_to_nsecs((1, 0)), 10**9)
    WVPASSEQ(xstat.timespec_to_nsecs((0, 10**9 / 2)), 500000000)
    WVPASSEQ(xstat.timespec_to_nsecs((1, 10**9 / 2)), 1500000000)
    WVPASSEQ(xstat.timespec_to_nsecs((-1, 0)), -10**9)
    WVPASSEQ(xstat.timespec_to_nsecs((-1, 10**9 / 2)), -500000000)
    WVPASSEQ(xstat.timespec_to_nsecs((-2, 10**9 / 2)), -1500000000)
    WVPASSEQ(xstat.timespec_to_nsecs((0, -1)), -1)
    WVPASSEQ(type(xstat.timespec_to_nsecs((2, 22222222))), type(0))
    WVPASSEQ(type(xstat.timespec_to_nsecs((-2, 22222222))), type(0))

    WVPASSEQ(xstat.nsecs_to_timespec(0), (0, 0))
    WVPASSEQ(xstat.nsecs_to_timespec(10**9), (1, 0))
    WVPASSEQ(xstat.nsecs_to_timespec(500000000), (0, 10**9 / 2))
    WVPASSEQ(xstat.nsecs_to_timespec(1500000000), (1, 10**9 / 2))
    WVPASSEQ(xstat.nsecs_to_timespec(-10**9), (-1, 0))
    WVPASSEQ(xstat.nsecs_to_timespec(-500000000), (-1, 10**9 / 2))
    WVPASSEQ(xstat.nsecs_to_timespec(-1500000000), (-2, 10**9 / 2))
    x = xstat.nsecs_to_timespec(1977777778)
    WVPASSEQ(type(x[0]), type(0))
    WVPASSEQ(type(x[1]), type(0))
    x = xstat.nsecs_to_timespec(-1977777778)
    WVPASSEQ(type(x[0]), type(0))
    WVPASSEQ(type(x[1]), type(0))

    WVPASSEQ(xstat.nsecs_to_timeval(0), (0, 0))
    WVPASSEQ(xstat.nsecs_to_timeval(10**9), (1, 0))
    WVPASSEQ(xstat.nsecs_to_timeval(500000000), (0, (10**9 / 2) / 1000))
    WVPASSEQ(xstat.nsecs_to_timeval(1500000000), (1, (10**9 / 2) / 1000))
    WVPASSEQ(xstat.nsecs_to_timeval(-10**9), (-1, 0))
    WVPASSEQ(xstat.nsecs_to_timeval(-500000000), (-1, (10**9 / 2) / 1000))
    WVPASSEQ(xstat.nsecs_to_timeval(-1500000000), (-2, (10**9 / 2) / 1000))
    x = xstat.nsecs_to_timeval(1977777778)
    WVPASSEQ(type(x[0]), type(0))
    WVPASSEQ(type(x[1]), type(0))
    x = xstat.nsecs_to_timeval(-1977777778)
    WVPASSEQ(type(x[0]), type(0))
    WVPASSEQ(type(x[1]), type(0))

    WVPASSEQ(xstat.fstime_floor_secs(0), 0)
    WVPASSEQ(xstat.fstime_floor_secs(10**9 / 2), 0)
    WVPASSEQ(xstat.fstime_floor_secs(10**9), 1)
    WVPASSEQ(xstat.fstime_floor_secs(-10**9 / 2), -1)
    WVPASSEQ(xstat.fstime_floor_secs(-10**9), -1)
    WVPASSEQ(type(xstat.fstime_floor_secs(10**9 / 2)), type(0))
    WVPASSEQ(type(xstat.fstime_floor_secs(-10**9 / 2)), type(0))


@wvtest
def test_bup_utimensat():
    initial_failures = wvfailure_count()
    if not xstat._bup_utimensat:
        return
    tmpdir = tempfile.mkdtemp(dir=bup_tmp, prefix='bup-txstat-')
    path = tmpdir + '/foo'
    open(path, 'w').close()
    frac_ts = (0, 10**9 / 2)
    xstat._bup_utimensat(_helpers.AT_FDCWD, path, (frac_ts, frac_ts), 0)
    st = _helpers.stat(path)
    atime_ts = st[8]
    mtime_ts = st[9]
    WVPASSEQ(atime_ts[0], 0)
    WVPASS(atime_ts[1] == 0 or atime_ts[1] == frac_ts[1])
    WVPASSEQ(mtime_ts[0], 0)
    WVPASS(mtime_ts[1] == 0 or mtime_ts[1] == frac_ts[1])
    if wvfailure_count() == initial_failures:
        subprocess.call(['rm', '-rf', tmpdir])


@wvtest
def test_bup_utimes():
    initial_failures = wvfailure_count()
    if not xstat._bup_utimes:
        return
    tmpdir = tempfile.mkdtemp(dir=bup_tmp, prefix='bup-txstat-')
    path = tmpdir + '/foo'
    open(path, 'w').close()
    frac_ts = (0, 10**6 / 2)
    xstat._bup_utimes(path, (frac_ts, frac_ts))
    st = _helpers.stat(path)
    atime_ts = st[8]
    mtime_ts = st[9]
    WVPASSEQ(atime_ts[0], 0)
    WVPASS(atime_ts[1] == 0 or atime_ts[1] == frac_ts[1] * 1000)
    WVPASSEQ(mtime_ts[0], 0)
    WVPASS(mtime_ts[1] == 0 or mtime_ts[1] == frac_ts[1] * 1000)
    if wvfailure_count() == initial_failures:
        subprocess.call(['rm', '-rf', tmpdir])


@wvtest
def test_bup_lutimes():
    initial_failures = wvfailure_count()
    if not xstat._bup_lutimes:
        return
    tmpdir = tempfile.mkdtemp(dir=bup_tmp, prefix='bup-txstat-')
    path = tmpdir + '/foo'
    open(path, 'w').close()
    frac_ts = (0, 10**6 / 2)
    xstat._bup_lutimes(path, (frac_ts, frac_ts))
    st = _helpers.stat(path)
    atime_ts = st[8]
    mtime_ts = st[9]
    WVPASSEQ(atime_ts[0], 0)
    WVPASS(atime_ts[1] == 0 or atime_ts[1] == frac_ts[1] * 1000)
    WVPASSEQ(mtime_ts[0], 0)
    WVPASS(mtime_ts[1] == 0 or mtime_ts[1] == frac_ts[1] * 1000)
    if wvfailure_count() == initial_failures:
        subprocess.call(['rm', '-rf', tmpdir])

########NEW FILE########
__FILENAME__ = vfs
"""Virtual File System representing bup's repository contents.

The vfs.py library makes it possible to expose contents from bup's repository
and abstracts internal name mangling and storage from the exposition layer.
"""
import os, re, stat, time
from bup import git, metadata
from helpers import *
from bup.git import BUP_NORMAL, BUP_CHUNKED, cp
from bup.hashsplit import GIT_MODE_TREE, GIT_MODE_FILE

EMPTY_SHA='\0'*20


class NodeError(Exception):
    """VFS base exception."""
    pass

class NoSuchFile(NodeError):
    """Request of a file that does not exist."""
    pass

class NotDir(NodeError):
    """Attempt to do a directory action on a file that is not one."""
    pass

class NotFile(NodeError):
    """Access to a node that does not represent a file."""
    pass

class TooManySymlinks(NodeError):
    """Symlink dereferencing level is too deep."""
    pass


def _treeget(hash):
    it = cp().get(hash.encode('hex'))
    type = it.next()
    assert(type == 'tree')
    return git.tree_decode(''.join(it))


def _tree_decode(hash):
    tree = [(int(name,16),stat.S_ISDIR(mode),sha)
            for (mode,name,sha)
            in _treeget(hash)]
    assert(tree == list(sorted(tree)))
    return tree


def _chunk_len(hash):
    return sum(len(b) for b in cp().join(hash.encode('hex')))


def _last_chunk_info(hash):
    tree = _tree_decode(hash)
    assert(tree)
    (ofs,isdir,sha) = tree[-1]
    if isdir:
        (subofs, sublen) = _last_chunk_info(sha)
        return (ofs+subofs, sublen)
    else:
        return (ofs, _chunk_len(sha))


def _total_size(hash):
    (lastofs, lastsize) = _last_chunk_info(hash)
    return lastofs + lastsize


def _chunkiter(hash, startofs):
    assert(startofs >= 0)
    tree = _tree_decode(hash)

    # skip elements before startofs
    for i in xrange(len(tree)):
        if i+1 >= len(tree) or tree[i+1][0] > startofs:
            break
    first = i

    # iterate through what's left
    for i in xrange(first, len(tree)):
        (ofs,isdir,sha) = tree[i]
        skipmore = startofs-ofs
        if skipmore < 0:
            skipmore = 0
        if isdir:
            for b in _chunkiter(sha, skipmore):
                yield b
        else:
            yield ''.join(cp().join(sha.encode('hex')))[skipmore:]


class _ChunkReader:
    def __init__(self, hash, isdir, startofs):
        if isdir:
            self.it = _chunkiter(hash, startofs)
            self.blob = None
        else:
            self.it = None
            self.blob = ''.join(cp().join(hash.encode('hex')))[startofs:]
        self.ofs = startofs

    def next(self, size):
        out = ''
        while len(out) < size:
            if self.it and not self.blob:
                try:
                    self.blob = self.it.next()
                except StopIteration:
                    self.it = None
            if self.blob:
                want = size - len(out)
                out += self.blob[:want]
                self.blob = self.blob[want:]
            if not self.it:
                break
        debug2('next(%d) returned %d\n' % (size, len(out)))
        self.ofs += len(out)
        return out


class _FileReader(object):
    def __init__(self, hash, size, isdir):
        self.hash = hash
        self.ofs = 0
        self.size = size
        self.isdir = isdir
        self.reader = None

    def seek(self, ofs):
        if ofs > self.size:
            self.ofs = self.size
        elif ofs < 0:
            self.ofs = 0
        else:
            self.ofs = ofs

    def tell(self):
        return self.ofs

    def read(self, count = -1):
        if count < 0:
            count = self.size - self.ofs
        if not self.reader or self.reader.ofs != self.ofs:
            self.reader = _ChunkReader(self.hash, self.isdir, self.ofs)
        try:
            buf = self.reader.next(count)
        except:
            self.reader = None
            raise  # our offsets will be all screwed up otherwise
        self.ofs += len(buf)
        return buf

    def close(self):
        pass


class Node(object):
    """Base class for file representation."""
    def __init__(self, parent, name, mode, hash):
        self.parent = parent
        self.name = name
        self.mode = mode
        self.hash = hash
        self.ctime = self.mtime = self.atime = 0
        self._subs = None
        self._metadata = None

    def __repr__(self):
        return "<%s object at %s - name:%r hash:%s parent:%r>" \
            % (self.__class__, hex(id(self)),
               self.name, self.hash.encode('hex'),
               self.parent.name if self.parent else None)

    def __cmp__(a, b):
        if a is b:
            return 0
        return (cmp(a and a.parent, b and b.parent) or
                cmp(a and a.name, b and b.name))

    def __iter__(self):
        return iter(self.subs())

    def fullname(self, stop_at=None):
        """Get this file's full path."""
        assert(self != stop_at)  # would be the empty string; too weird
        if self.parent and self.parent != stop_at:
            return os.path.join(self.parent.fullname(stop_at=stop_at),
                                self.name)
        else:
            return self.name

    def _mksubs(self):
        self._subs = {}

    def subs(self):
        """Get a list of nodes that are contained in this node."""
        if self._subs == None:
            self._mksubs()
        return sorted(self._subs.values())

    def sub(self, name):
        """Get node named 'name' that is contained in this node."""
        if self._subs == None:
            self._mksubs()
        ret = self._subs.get(name)
        if not ret:
            raise NoSuchFile("no file %r in %r" % (name, self.name))
        return ret

    def top(self):
        """Return the very top node of the tree."""
        if self.parent:
            return self.parent.top()
        else:
            return self

    def fs_top(self):
        """Return the top node of the particular backup set.

        If this node isn't inside a backup set, return the root level.
        """
        if self.parent and not isinstance(self.parent, CommitList):
            return self.parent.fs_top()
        else:
            return self

    def _lresolve(self, parts):
        #debug2('_lresolve %r in %r\n' % (parts, self.name))
        if not parts:
            return self
        (first, rest) = (parts[0], parts[1:])
        if first == '.':
            return self._lresolve(rest)
        elif first == '..':
            if not self.parent:
                raise NoSuchFile("no parent dir for %r" % self.name)
            return self.parent._lresolve(rest)
        elif rest:
            return self.sub(first)._lresolve(rest)
        else:
            return self.sub(first)

    def lresolve(self, path, stay_inside_fs=False):
        """Walk into a given sub-path of this node.

        If the last element is a symlink, leave it as a symlink, don't resolve
        it.  (like lstat())
        """
        start = self
        if not path:
            return start
        if path.startswith('/'):
            if stay_inside_fs:
                start = self.fs_top()
            else:
                start = self.top()
            path = path[1:]
        parts = re.split(r'/+', path or '.')
        if not parts[-1]:
            parts[-1] = '.'
        #debug2('parts: %r %r\n' % (path, parts))
        return start._lresolve(parts)

    def resolve(self, path = ''):
        """Like lresolve(), and dereference it if it was a symlink."""
        return self.lresolve(path).lresolve('.')

    def try_resolve(self, path = ''):
        """Like resolve(), but don't worry if a symlink uses an invalid path.

        Returns an error if any intermediate nodes were invalid.
        """
        n = self.lresolve(path)
        try:
            n = n.lresolve('.')
        except NoSuchFile:
            pass
        return n

    def nlinks(self):
        """Get the number of hard links to the current node."""
        return 1

    def size(self):
        """Get the size of the current node."""
        return 0

    def open(self):
        """Open the current node. It is an error to open a non-file node."""
        raise NotFile('%s is not a regular file' % self.name)

    def _populate_metadata(self, force=False):
        # Only Dirs contain .bupm files, so by default, do nothing.
        pass

    def metadata(self):
        """Return this Node's Metadata() object, if any."""
        if not self._metadata and self.parent:
            self.parent._populate_metadata(force=True)
        return self._metadata

    def release(self):
        """Release resources that can be automatically restored (at a cost)."""
        self._metadata = None
        self._subs = None


class File(Node):
    """A normal file from bup's repository."""
    def __init__(self, parent, name, mode, hash, bupmode):
        Node.__init__(self, parent, name, mode, hash)
        self.bupmode = bupmode
        self._cached_size = None
        self._filereader = None

    def open(self):
        """Open the file."""
        # You'd think FUSE might call this only once each time a file is
        # opened, but no; it's really more of a refcount, and it's called
        # once per read().  Thus, it's important to cache the filereader
        # object here so we're not constantly re-seeking.
        if not self._filereader:
            self._filereader = _FileReader(self.hash, self.size(),
                                           self.bupmode == git.BUP_CHUNKED)
        self._filereader.seek(0)
        return self._filereader

    def size(self):
        """Get this file's size."""
        if self._cached_size == None:
            debug1('<<<<File.size() is calculating (for %r)...\n' % self.name)
            if self.bupmode == git.BUP_CHUNKED:
                self._cached_size = _total_size(self.hash)
            else:
                self._cached_size = _chunk_len(self.hash)
            debug1('<<<<File.size() done.\n')
        return self._cached_size


_symrefs = 0
class Symlink(File):
    """A symbolic link from bup's repository."""
    def __init__(self, parent, name, hash, bupmode):
        File.__init__(self, parent, name, 0120000, hash, bupmode)

    def size(self):
        """Get the file size of the file at which this link points."""
        return len(self.readlink())

    def readlink(self):
        """Get the path that this link points at."""
        return ''.join(cp().join(self.hash.encode('hex')))

    def dereference(self):
        """Get the node that this link points at.

        If the path is invalid, raise a NoSuchFile exception. If the level of
        indirection of symlinks is 100 levels deep, raise a TooManySymlinks
        exception.
        """
        global _symrefs
        if _symrefs > 100:
            raise TooManySymlinks('too many levels of symlinks: %r'
                                  % self.fullname())
        _symrefs += 1
        try:
            try:
                return self.parent.lresolve(self.readlink(),
                                            stay_inside_fs=True)
            except NoSuchFile:
                raise NoSuchFile("%s: broken symlink to %r"
                                 % (self.fullname(), self.readlink()))
        finally:
            _symrefs -= 1

    def _lresolve(self, parts):
        return self.dereference()._lresolve(parts)


class FakeSymlink(Symlink):
    """A symlink that is not stored in the bup repository."""
    def __init__(self, parent, name, toname):
        Symlink.__init__(self, parent, name, EMPTY_SHA, git.BUP_NORMAL)
        self.toname = toname

    def readlink(self):
        """Get the path that this link points at."""
        return self.toname


class Dir(Node):
    """A directory stored inside of bup's repository."""

    def __init__(self, *args, **kwargs):
        Node.__init__(self, *args, **kwargs)
        self._bupm = None

    def _populate_metadata(self, force=False):
        if self._metadata and not force:
            return
        if not self._subs:
            self._mksubs()
        if not self._bupm:
            return
        meta_stream = self._bupm.open()
        dir_meta = metadata.Metadata.read(meta_stream)
        for sub in self:
            if not stat.S_ISDIR(sub.mode):
                sub._metadata = metadata.Metadata.read(meta_stream)
        self._metadata = dir_meta

    def _mksubs(self):
        self._subs = {}
        it = cp().get(self.hash.encode('hex'))
        type = it.next()
        if type == 'commit':
            del it
            it = cp().get(self.hash.encode('hex') + ':')
            type = it.next()
        assert(type == 'tree')
        for (mode,mangled_name,sha) in git.tree_decode(''.join(it)):
            if mangled_name == '.bupm':
                bupmode = stat.S_ISDIR(mode) and BUP_CHUNKED or BUP_NORMAL
                self._bupm = File(self, mangled_name, GIT_MODE_FILE, sha,
                                  bupmode)
                continue
            name = mangled_name
            (name,bupmode) = git.demangle_name(mangled_name)
            if bupmode == git.BUP_CHUNKED:
                mode = GIT_MODE_FILE
            if stat.S_ISDIR(mode):
                self._subs[name] = Dir(self, name, mode, sha)
            elif stat.S_ISLNK(mode):
                self._subs[name] = Symlink(self, name, sha, bupmode)
            else:
                self._subs[name] = File(self, name, mode, sha, bupmode)

    def metadata(self):
        """Return this Dir's Metadata() object, if any."""
        self._populate_metadata()
        return self._metadata

    def metadata_file(self):
        """Return this Dir's .bupm File, if any."""
        if not self._subs:
            self._mksubs()
        return self._bupm

    def release(self):
        """Release restorable resources held by this node."""
        self._bupm = None
        super(Dir, self).release()


class CommitDir(Node):
    """A directory that contains all commits that are reachable by a ref.

    Contains a set of subdirectories named after the commits' first byte in
    hexadecimal. Each of those directories contain all commits with hashes that
    start the same as the directory name. The name used for those
    subdirectories is the hash of the commit without the first byte. This
    separation helps us avoid having too much directories on the same level as
    the number of commits grows big.
    """
    def __init__(self, parent, name):
        Node.__init__(self, parent, name, GIT_MODE_TREE, EMPTY_SHA)

    def _mksubs(self):
        self._subs = {}
        refs = git.list_refs()
        for ref in refs:
            #debug2('ref name: %s\n' % ref[0])
            revs = git.rev_list(ref[1].encode('hex'))
            for (date, commit) in revs:
                #debug2('commit: %s  date: %s\n' % (commit.encode('hex'), date))
                commithex = commit.encode('hex')
                containername = commithex[:2]
                dirname = commithex[2:]
                n1 = self._subs.get(containername)
                if not n1:
                    n1 = CommitList(self, containername)
                    self._subs[containername] = n1

                if n1.commits.get(dirname):
                    # Stop work for this ref, the rest should already be present
                    break

                n1.commits[dirname] = (commit, date)


class CommitList(Node):
    """A list of commits with hashes that start with the current node's name."""
    def __init__(self, parent, name):
        Node.__init__(self, parent, name, GIT_MODE_TREE, EMPTY_SHA)
        self.commits = {}

    def _mksubs(self):
        self._subs = {}
        for (name, (hash, date)) in self.commits.items():
            n1 = Dir(self, name, GIT_MODE_TREE, hash)
            n1.ctime = n1.mtime = date
            self._subs[name] = n1


class TagDir(Node):
    """A directory that contains all tags in the repository."""
    def __init__(self, parent, name):
        Node.__init__(self, parent, name, GIT_MODE_TREE, EMPTY_SHA)

    def _mksubs(self):
        self._subs = {}
        for (name, sha) in git.list_refs():
            if name.startswith('refs/tags/'):
                name = name[10:]
                date = git.get_commit_dates([sha.encode('hex')])[0]
                commithex = sha.encode('hex')
                target = '../.commit/%s/%s' % (commithex[:2], commithex[2:])
                tag1 = FakeSymlink(self, name, target)
                tag1.ctime = tag1.mtime = date
                self._subs[name] = tag1


class BranchList(Node):
    """A list of links to commits reachable by a branch in bup's repository.

    Represents each commit as a symlink that points to the commit directory in
    /.commit/??/ . The symlink is named after the commit date.
    """
    def __init__(self, parent, name, hash):
        Node.__init__(self, parent, name, GIT_MODE_TREE, hash)

    def _mksubs(self):
        self._subs = {}

        tags = git.tags()

        revs = list(git.rev_list(self.hash.encode('hex')))
        latest = revs[0]
        for (date, commit) in revs:
            l = time.localtime(date)
            ls = time.strftime('%Y-%m-%d-%H%M%S', l)
            commithex = commit.encode('hex')
            target = '../.commit/%s/%s' % (commithex[:2], commithex[2:])
            n1 = FakeSymlink(self, ls, target)
            n1.ctime = n1.mtime = date
            self._subs[ls] = n1

            for tag in tags.get(commit, []):
                t1 = FakeSymlink(self, tag, target)
                t1.ctime = t1.mtime = date
                self._subs[tag] = t1

        (date, commit) = latest
        commithex = commit.encode('hex')
        target = '../.commit/%s/%s' % (commithex[:2], commithex[2:])
        n1 = FakeSymlink(self, 'latest', target)
        n1.ctime = n1.mtime = date
        self._subs['latest'] = n1


class RefList(Node):
    """A list of branches in bup's repository.

    The sub-nodes of the ref list are a series of CommitList for each commit
    hash pointed to by a branch.

    Also, a special sub-node named '.commit' contains all commit directories
    that are reachable via a ref (e.g. a branch).  See CommitDir for details.
    """
    def __init__(self, parent):
        Node.__init__(self, parent, '/', GIT_MODE_TREE, EMPTY_SHA)

    def _mksubs(self):
        self._subs = {}

        commit_dir = CommitDir(self, '.commit')
        self._subs['.commit'] = commit_dir

        tag_dir = TagDir(self, '.tag')
        self._subs['.tag'] = tag_dir

        refs_info = [(name[11:], sha) for (name,sha) in git.list_refs() \
                     if name.startswith('refs/heads/')]

        dates = git.get_commit_dates([sha.encode('hex')
                                      for (name, sha) in refs_info])

        for (name, sha), date in zip(refs_info, dates):
            n1 = BranchList(self, name, sha)
            n1.ctime = n1.mtime = date
            self._subs[name] = n1

########NEW FILE########
__FILENAME__ = vint
"""Binary encodings for bup."""

# Copyright (C) 2010 Rob Browning
#
# This code is covered under the terms of the GNU Library General
# Public License as described in the bup LICENSE file.

from cStringIO import StringIO

# Variable length integers are encoded as vints -- see jakarta lucene.

def write_vuint(port, x):
    if x < 0:
        raise Exception("vuints must not be negative")
    elif x == 0:
        port.write('\0')
    else:
        while x:
            seven_bits = x & 0x7f
            x >>= 7
            if x:
                port.write(chr(0x80 | seven_bits))
            else:
                port.write(chr(seven_bits))


def read_vuint(port):
    c = port.read(1)
    if c == '':
        raise EOFError('encountered EOF while reading vuint');
    result = 0
    offset = 0
    while c:
        b = ord(c)
        if b & 0x80:
            result |= ((b & 0x7f) << offset)
            offset += 7
            c = port.read(1)
        else:
            result |= (b << offset)
            break
    return result


def write_vint(port, x):
    # Sign is handled with the second bit of the first byte.  All else
    # matches vuint.
    if x == 0:
        port.write('\0')
    else:
        if x < 0:
            x = -x
            sign_and_six_bits = (x & 0x3f) | 0x40
        else:
            sign_and_six_bits = x & 0x3f
        x >>= 6
        if x:
            port.write(chr(0x80 | sign_and_six_bits))
            write_vuint(port, x)
        else:
            port.write(chr(sign_and_six_bits))


def read_vint(port):
    c = port.read(1)
    if c == '':
        raise EOFError('encountered EOF while reading vint');
    negative = False
    result = 0
    offset = 0
    # Handle first byte with sign bit specially.
    if c:
        b = ord(c)
        if b & 0x40:
            negative = True
        result |= (b & 0x3f)
        if b & 0x80:
            offset += 6
            c = port.read(1)
        elif negative:
            return -result
        else:
            return result
    while c:
        b = ord(c)
        if b & 0x80:
            result |= ((b & 0x7f) << offset)
            offset += 7
            c = port.read(1)
        else:
            result |= (b << offset)
            break
    if negative:
        return -result
    else:
        return result


def write_bvec(port, x):
    write_vuint(port, len(x))
    port.write(x)


def read_bvec(port):
    n = read_vuint(port)
    return port.read(n)


def skip_bvec(port):
    port.read(read_vuint(port))


def pack(types, *args):
    if len(types) != len(args):
        raise Exception('number of arguments does not match format string')
    port = StringIO()
    for (type, value) in zip(types, args):
        if type == 'V':
            write_vuint(port, value)
        elif type == 'v':
            write_vint(port, value)
        elif type == 's':
            write_bvec(port, value)
        else:
            raise Exception('unknown xpack format string item "' + type + '"')
    return port.getvalue()


def unpack(types, data):
    result = []
    port = StringIO(data)
    for type in types:
        if type == 'V':
            result.append(read_vuint(port))
        elif type == 'v':
            result.append(read_vint(port))
        elif type == 's':
            result.append(read_bvec(port))
        else:
            raise Exception('unknown xunpack format string item "' + type + '"')
    return result

########NEW FILE########
__FILENAME__ = xstat
"""Enhanced stat operations for bup."""
import os
import stat as pystat
from bup import _helpers

try:
    _bup_utimensat = _helpers.bup_utimensat
except AttributeError, e:
    _bup_utimensat = False

try:
    _bup_utimes = _helpers.bup_utimes
except AttributeError, e:
    _bup_utimes = False

try:
    _bup_lutimes = _helpers.bup_lutimes
except AttributeError, e:
    _bup_lutimes = False


def timespec_to_nsecs((ts_s, ts_ns)):
    return ts_s * 10**9 + ts_ns


def nsecs_to_timespec(ns):
    """Return (s, ns) where ns is always non-negative
    and t = s + ns / 10e8""" # metadata record rep
    ns = int(ns)
    return (ns / 10**9, ns % 10**9)


def nsecs_to_timeval(ns):
    """Return (s, us) where ns is always non-negative
    and t = s + us / 10e5"""
    ns = int(ns)
    return (ns / 10**9, (ns % 10**9) / 1000)


def fstime_floor_secs(ns):
    """Return largest integer not greater than ns / 10e8."""
    return int(ns) / 10**9;


def fstime_to_timespec(ns):
    return nsecs_to_timespec(ns)


def fstime_to_sec_str(fstime):
    (s, ns) = fstime_to_timespec(fstime)
    if(s < 0):
        s += 1
    if ns == 0:
        return '%d' % s
    else:
        return '%d.%09d' % (s, ns)


if _bup_utimensat:
    def utime(path, times):
        """Times must be provided as (atime_ns, mtime_ns)."""
        atime = nsecs_to_timespec(times[0])
        mtime = nsecs_to_timespec(times[1])
        _bup_utimensat(_helpers.AT_FDCWD, path, (atime, mtime), 0)
    def lutime(path, times):
        """Times must be provided as (atime_ns, mtime_ns)."""
        atime = nsecs_to_timespec(times[0])
        mtime = nsecs_to_timespec(times[1])
        _bup_utimensat(_helpers.AT_FDCWD, path, (atime, mtime),
                       _helpers.AT_SYMLINK_NOFOLLOW)
else: # Must have these if utimensat isn't available.
    def utime(path, times):
        """Times must be provided as (atime_ns, mtime_ns)."""
        atime = nsecs_to_timeval(times[0])
        mtime = nsecs_to_timeval(times[1])
        _bup_utimes(path, (atime, mtime))
    def lutime(path, times):
        """Times must be provided as (atime_ns, mtime_ns)."""
        atime = nsecs_to_timeval(times[0])
        mtime = nsecs_to_timeval(times[1])
        _bup_lutimes(path, (atime, mtime))


class stat_result:
    @staticmethod
    def from_xstat_rep(st):
        result = stat_result()
        (result.st_mode,
         result.st_ino,
         result.st_dev,
         result.st_nlink,
         result.st_uid,
         result.st_gid,
         result.st_rdev,
         result.st_size,
         result.st_atime,
         result.st_mtime,
         result.st_ctime) = st
        result.st_atime = timespec_to_nsecs(result.st_atime)
        result.st_mtime = timespec_to_nsecs(result.st_mtime)
        result.st_ctime = timespec_to_nsecs(result.st_ctime)
        return result


def stat(path):
    return stat_result.from_xstat_rep(_helpers.stat(path))


def fstat(path):
    return stat_result.from_xstat_rep(_helpers.fstat(path))


def lstat(path):
    return stat_result.from_xstat_rep(_helpers.lstat(path))


def mode_str(mode):
    result = ''
    # FIXME: Other types?
    if pystat.S_ISREG(mode):
        result += '-'
    elif pystat.S_ISDIR(mode):
        result += 'd'
    elif pystat.S_ISCHR(mode):
        result += 'c'
    elif pystat.S_ISBLK(mode):
        result += 'b'
    elif pystat.S_ISFIFO(mode):
        result += 'p'
    elif pystat.S_ISLNK(mode):
        result += 'l'
    elif pystat.S_ISSOCK(mode):
        result += 's'
    else:
        result += '?'

    result += 'r' if (mode & pystat.S_IRUSR) else '-'
    result += 'w' if (mode & pystat.S_IWUSR) else '-'
    result += 'x' if (mode & pystat.S_IXUSR) else '-'
    result += 'r' if (mode & pystat.S_IRGRP) else '-'
    result += 'w' if (mode & pystat.S_IWGRP) else '-'
    result += 'x' if (mode & pystat.S_IXGRP) else '-'
    result += 'r' if (mode & pystat.S_IROTH) else '-'
    result += 'w' if (mode & pystat.S_IWOTH) else '-'
    result += 'x' if (mode & pystat.S_IXOTH) else '-'
    return result


def classification_str(mode, include_exec):
    if pystat.S_ISREG(mode):
        if include_exec \
           and (pystat.S_IMODE(mode) \
                & (pystat.S_IXUSR | pystat.S_IXGRP | pystat.S_IXOTH)):
            return '*'
        else:
            return ''
    elif pystat.S_ISDIR(mode):
        return '/'
    elif pystat.S_ISLNK(mode):
        return '@'
    elif pystat.S_ISFIFO(mode):
        return '|'
    elif pystat.S_ISSOCK(mode):
        return '='
    else:
        return ''

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
import sys, os, subprocess, signal, getopt

argv = sys.argv
exe = os.path.realpath(argv[0])
exepath = os.path.split(exe)[0] or '.'
exeprefix = os.path.split(os.path.abspath(exepath))[0]

# fix the PYTHONPATH to include our lib dir
if os.path.exists("%s/lib/bup/cmd/." % exeprefix):
    # installed binary in /.../bin.
    # eg. /usr/bin/bup means /usr/lib/bup/... is where our libraries are.
    cmdpath = "%s/lib/bup/cmd" % exeprefix
    libpath = "%s/lib/bup" % exeprefix
    resourcepath = libpath
else:
    # running from the src directory without being installed first
    cmdpath = os.path.join(exepath, 'cmd')
    libpath = os.path.join(exepath, 'lib')
    resourcepath = libpath
sys.path[:0] = [libpath]
os.environ['PYTHONPATH'] = libpath + ':' + os.environ.get('PYTHONPATH', '')
os.environ['BUP_MAIN_EXE'] = os.path.abspath(exe)
os.environ['BUP_RESOURCE_PATH'] = resourcepath

from bup import helpers
from bup.helpers import *

# after running 'bup newliner', the tty_width() ioctl won't work anymore
os.environ['WIDTH'] = str(tty_width())

def usage(msg=""):
    log('Usage: bup [-?|--help] [-d BUP_DIR] [--debug] [--profile] '
        '<command> [options...]\n\n')
    common = dict(
        ftp = 'Browse backup sets using an ftp-like client',
        fsck = 'Check backup sets for damage and add redundancy information',
        fuse = 'Mount your backup sets as a filesystem',
        help = 'Print detailed help for the given command',
        index = 'Create or display the index of files to back up',
        on = 'Backup a remote machine to the local one',
        restore = 'Extract files from a backup set',
        save = 'Save files into a backup set (note: run "bup index" first)',
        tag = 'Tag commits for easier access',
        web = 'Launch a web server to examine backup sets',
    )

    log('Common commands:\n')
    for cmd,synopsis in sorted(common.items()):
        log('    %-10s %s\n' % (cmd, synopsis))
    log('\n')
    
    log('Other available commands:\n')
    cmds = []
    for c in sorted(os.listdir(cmdpath) + os.listdir(exepath)):
        if c.startswith('bup-') and c.find('.') < 0:
            cname = c[4:]
            if cname not in common:
                cmds.append(c[4:])
    log(columnate(cmds, '    '))
    log('\n')
    
    log("See 'bup help COMMAND' for more information on " +
        "a specific command.\n")
    if msg:
        log("\n%s\n" % msg)
    sys.exit(99)


if len(argv) < 2:
    usage()

# Handle global options.
try:
    optspec = ['help', 'version', 'debug', 'profile', 'bup-dir=']
    global_args, subcmd = getopt.getopt(argv[1:], '?VDd:', optspec)
except getopt.GetoptError, ex:
    usage('error: %s' % ex.msg)

help_requested = None
do_profile = False

for opt in global_args:
    if opt[0] in ['-?', '--help']:
        help_requested = True
    elif opt[0] in ['-V', '--version']:
        subcmd = ['version']
    elif opt[0] in ['-D', '--debug']:
        helpers.buglvl += 1
        os.environ['BUP_DEBUG'] = str(helpers.buglvl)
    elif opt[0] in ['--profile']:
        do_profile = True
    elif opt[0] in ['-d', '--bup-dir']:
        os.environ['BUP_DIR'] = opt[1]
    else:
        usage('error: unexpected option "%s"' % opt[0])

# Make BUP_DIR absolute, so we aren't affected by chdir (i.e. save -C, etc.).
if 'BUP_DIR' in os.environ:
    os.environ['BUP_DIR'] = os.path.abspath(os.environ['BUP_DIR'])

if len(subcmd) == 0:
    if help_requested:
        subcmd = ['help']
    else:
        usage()

if help_requested and subcmd[0] != 'help':
    subcmd = ['help'] + subcmd

if len(subcmd) > 1 and subcmd[1] == '--help' and subcmd[0] != 'help':
    subcmd = ['help', subcmd[0]] + subcmd[2:]

subcmd_name = subcmd[0]
if not subcmd_name:
    usage()

def subpath(s):
    sp = os.path.join(exepath, 'bup-%s' % s)
    if not os.path.exists(sp):
        sp = os.path.join(cmdpath, 'bup-%s' % s)
    return sp

subcmd[0] = subpath(subcmd_name)
if not os.path.exists(subcmd[0]):
    usage('error: unknown command "%s"' % subcmd_name)

already_fixed = atoi(os.environ.get('BUP_FORCE_TTY'))
if subcmd_name in ['mux', 'ftp', 'help']:
    already_fixed = True
fix_stdout = not already_fixed and os.isatty(1)
fix_stderr = not already_fixed and os.isatty(2)

def force_tty():
    if fix_stdout or fix_stderr:
        amt = (fix_stdout and 1 or 0) + (fix_stderr and 2 or 0)
        os.environ['BUP_FORCE_TTY'] = str(amt)
    os.setsid()  # make sure ctrl-c is sent just to us, not to child too

if fix_stdout or fix_stderr:
    realf = fix_stderr and 2 or 1
    drealf = os.dup(realf)  # Popen goes crazy with stdout=2
    n = subprocess.Popen([subpath('newliner')],
                         stdin=subprocess.PIPE, stdout=drealf,
                         close_fds=True, preexec_fn=force_tty)
    os.close(drealf)
    outf = fix_stdout and n.stdin.fileno() or None
    errf = fix_stderr and n.stdin.fileno() or None
else:
    n = None
    outf = None
    errf = None

ret = 95
p = None
forward_signals = True

def handler(signum, frame):
    debug1('\nbup: signal %d received\n' % signum)
    if not p or not forward_signals:
        return
    if signum != signal.SIGTSTP:
        os.kill(p.pid, signum)
    else: # SIGTSTP: stop the child, then ourselves.
        os.kill(p.pid, signal.SIGSTOP)
        signal.signal(signal.SIGTSTP, signal.SIG_DFL)
        os.kill(os.getpid(), signal.SIGTSTP)
        # Back from suspend -- reestablish the handler.
        signal.signal(signal.SIGTSTP, handler)
    ret = 94

signal.signal(signal.SIGTERM, handler)
signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTSTP, handler)
signal.signal(signal.SIGCONT, handler)

try:
    try:
        c = (do_profile and [sys.executable, '-m', 'cProfile'] or []) + subcmd
        if not n and not outf and not errf:
            # shortcut when no bup-newliner stuff is needed
            os.execvp(c[0], c)
        else:
            p = subprocess.Popen(c, stdout=outf, stderr=errf,
                                 preexec_fn=force_tty)
        while 1:
            # if we get a signal while waiting, we have to keep waiting, just
            # in case our child doesn't die.
            ret = p.wait()
            forward_signals = False
            break
    except OSError, e:
        log('%s: %s\n' % (subcmd[0], e))
        ret = 98
finally:
    if p and p.poll() == None:
        os.kill(p.pid, signal.SIGTERM)
        p.wait()
    if n:
        n.stdin.close()
        try:
            n.wait()
        except:
            pass
sys.exit(ret)

########NEW FILE########
__FILENAME__ = wvtest
#!/usr/bin/env python
#
# WvTest:
#   Copyright (C)2007-2012 Versabanq Innovations Inc. and contributors.
#       Licensed under the GNU Library General Public License, version 2.
#       See the included file named LICENSE for license information.
#       You can get wvtest from: http://github.com/apenwarr/wvtest
#
import atexit
import inspect
import os
import re
import sys
import traceback

# NOTE
# Why do we do we need the "!= main" check?  Because if you run
# wvtest.py as a main program and it imports your test files, then
# those test files will try to import the wvtest module recursively.
# That actually *works* fine, because we don't run this main program
# when we're imported as a module.  But you end up with two separate
# wvtest modules, the one that gets imported, and the one that's the
# main program.  Each of them would have duplicated global variables
# (most importantly, wvtest._registered), and so screwy things could
# happen.  Thus, we make the main program module *totally* different
# from the imported module.  Then we import wvtest (the module) into
# wvtest (the main program) here and make sure to refer to the right
# versions of global variables.
#
# All this is done just so that wvtest.py can be a single file that's
# easy to import into your own applications.
if __name__ != '__main__':   # we're imported as a module
    _registered = []
    _tests = 0
    _fails = 0

    def wvtest(func):
        """ Use this decorator (@wvtest) in front of any function you want to
            run as part of the unit test suite.  Then run:
                python wvtest.py path/to/yourtest.py [other test.py files...]
            to run all the @wvtest functions in the given file(s).
        """
        _registered.append(func)
        return func


    def _result(msg, tb, code):
        global _tests, _fails
        _tests += 1
        if code != 'ok':
            _fails += 1
        (filename, line, func, text) = tb
        filename = os.path.basename(filename)
        msg = re.sub(r'\s+', ' ', str(msg))
        sys.stderr.flush()
        print '! %-70s %s' % ('%s:%-4d %s' % (filename, line, msg),
                              code)
        sys.stdout.flush()


    def _check(cond, msg = 'unknown', tb = None):
        if tb == None: tb = traceback.extract_stack()[-3]
        if cond:
            _result(msg, tb, 'ok')
        else:
            _result(msg, tb, 'FAILED')
        return cond


    def _code():
        (filename, line, func, text) = traceback.extract_stack()[-3]
        text = re.sub(r'^\w+\((.*)\)(\s*#.*)?$', r'\1', text);
        return text


    def WVMSG(message):
        ''' Issues a notification. '''
        return _result(message, traceback.extract_stack()[-3], 'ok')

    def WVPASS(cond = True):
        ''' Counts a test failure unless cond is true. '''
        return _check(cond, _code())

    def WVFAIL(cond = True):
        ''' Counts a test failure  unless cond is false. '''
        return _check(not cond, 'NOT(%s)' % _code())

    def WVPASSEQ(a, b):
        ''' Counts a test failure unless a == b. '''
        return _check(a == b, '%s == %s' % (repr(a), repr(b)))

    def WVPASSNE(a, b):
        ''' Counts a test failure unless a != b. '''
        return _check(a != b, '%s != %s' % (repr(a), repr(b)))

    def WVPASSLT(a, b):
        ''' Counts a test failure unless a < b. '''
        return _check(a < b, '%s < %s' % (repr(a), repr(b)))

    def WVPASSLE(a, b):
        ''' Counts a test failure unless a <= b. '''
        return _check(a <= b, '%s <= %s' % (repr(a), repr(b)))

    def WVPASSGT(a, b):
        ''' Counts a test failure unless a > b. '''
        return _check(a > b, '%s > %s' % (repr(a), repr(b)))

    def WVPASSGE(a, b):
        ''' Counts a test failure unless a >= b. '''
        return _check(a >= b, '%s >= %s' % (repr(a), repr(b)))

    def WVEXCEPT(etype, func, *args, **kwargs):
        ''' Counts a test failure unless func throws an 'etype' exception.
            You have to spell out the function name and arguments, rather than
            calling the function yourself, so that WVEXCEPT can run before
            your test code throws an exception.
        '''
        try:
            func(*args, **kwargs)
        except etype, e:
            return _check(True, 'EXCEPT(%s)' % _code())
        except:
            _check(False, 'EXCEPT(%s)' % _code())
            raise
        else:
            return _check(False, 'EXCEPT(%s)' % _code())

    def wvfailure_count():
        return _fails

    def _check_unfinished():
        if _registered:
            for func in _registered:
                print 'WARNING: not run: %r' % (func,)
            WVFAIL('wvtest_main() not called')
        if _fails:
            sys.exit(1)

    atexit.register(_check_unfinished)


def _run_in_chdir(path, func, *args, **kwargs):
    oldwd = os.getcwd()
    oldpath = sys.path
    try:
        os.chdir(path)
        sys.path += [path, os.path.split(path)[0]]
        return func(*args, **kwargs)
    finally:
        os.chdir(oldwd)
        sys.path = oldpath


if sys.version_info >= (2,6,0):
    _relpath = os.path.relpath;
else:
    # Implementation for Python 2.5, taken from CPython (tag v2.6,
    # file Lib/posixpath.py, hg-commit 95fff5a6a276).  Update
    # ./LICENSE When this code is eventually removed.
    def _relpath(path, start=os.path.curdir):
        if not path:
            raise ValueError("no path specified")

        start_list = os.path.abspath(start).split(os.path.sep)
        path_list = os.path.abspath(path).split(os.path.sep)

        # Work out how much of the filepath is shared by start and path.
        i = len(os.path.commonprefix([start_list, path_list]))

        rel_list = [os.path.pardir] * (len(start_list)-i) + path_list[i:]
        if not rel_list:
            return curdir
        return os.path.join(*rel_list)


def _runtest(fname, f):
    mod = inspect.getmodule(f)
    relpath = _relpath(mod.__file__, os.getcwd()).replace('.pyc', '.py')
    print
    print 'Testing "%s" in %s:' % (fname, relpath)
    sys.stdout.flush()
    try:
        _run_in_chdir(os.path.split(mod.__file__)[0], f)
    except Exception, e:
        print
        print traceback.format_exc()
        tb = sys.exc_info()[2]
        wvtest._result(e, traceback.extract_tb(tb)[1], 'EXCEPTION')


def _run_registered_tests():
    import wvtest as _wvtestmod
    while _wvtestmod._registered:
        t = _wvtestmod._registered.pop(0)
        _runtest(t.func_name, t)
        print


def wvtest_main(extra_testfiles=[]):
    import wvtest as _wvtestmod
    _run_registered_tests()
    for modname in extra_testfiles:
        if not os.path.exists(modname):
            print 'Skipping: %s' % modname
            continue
        if modname.endswith('.py'):
            modname = modname[:-3]
        print 'Importing: %s' % modname
        path, mod = os.path.split(os.path.abspath(modname))
        nicename = modname.replace(os.path.sep, '.')
        while nicename.startswith('.'):
            nicename = modname[1:]
        _run_in_chdir(path, __import__, nicename, None, None, [])
        _run_registered_tests()
    print
    print 'WvTest: %d tests, %d failures.' % (_wvtestmod._tests,
                                              _wvtestmod._fails)


if __name__ == '__main__':
    import wvtest as _wvtestmod
    sys.modules['wvtest'] = _wvtestmod
    sys.modules['wvtest.wvtest'] = _wvtestmod
    wvtest_main(sys.argv[1:])

########NEW FILE########
