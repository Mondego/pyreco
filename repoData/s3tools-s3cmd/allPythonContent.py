__FILENAME__ = run-tests
#!/usr/bin/env python
# -*- coding=utf-8 -*-

## Amazon S3cmd - testsuite
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2
## Copyright: TGRMN Software and contributors

import sys
import os
import re
from subprocess import Popen, PIPE, STDOUT
import locale
import getpass
import S3.Exceptions
import S3.Config
from S3.ExitCodes import *

count_pass = 0
count_fail = 0
count_skip = 0

test_counter = 0
run_tests = []
exclude_tests = []

verbose = False

if os.name == "posix":
    have_wget = True
elif os.name == "nt":
    have_wget = False
else:
    print "Unknown platform: %s" % os.name
    sys.exit(1)

config_file = None
if os.getenv("HOME"):
    config_file = os.path.join(os.getenv("HOME"), ".s3cfg")
elif os.name == "nt" and os.getenv("USERPROFILE"):
    config_file = os.path.join(os.getenv("USERPROFILE").decode('mbcs'), os.getenv("APPDATA").decode('mbcs') or 'Application Data', "s3cmd.ini")

cfg = S3.Config.Config(config_file)

## Unpack testsuite/ directory
if not os.path.isdir('testsuite') and os.path.isfile('testsuite.tar.gz'):
    os.system("tar -xz -f testsuite.tar.gz")
if not os.path.isdir('testsuite'):
    print "Something went wrong while unpacking testsuite.tar.gz"
    sys.exit(1)

os.system("tar -xf testsuite/checksum.tar -C testsuite")
if not os.path.isfile('testsuite/checksum/cksum33.txt'):
    print "Something went wrong while unpacking testsuite/checkum.tar"
    sys.exit(1)

## Fix up permissions for permission-denied tests
os.chmod("testsuite/permission-tests/permission-denied-dir", 0444)
os.chmod("testsuite/permission-tests/permission-denied.txt", 0000)

## Patterns for Unicode tests
patterns = {}
patterns['UTF-8'] = u"ŪņЇЌœđЗ/☺ unicode € rocks ™"
patterns['GBK'] = u"12月31日/1-特色條目"

encoding = locale.getpreferredencoding()
if not encoding:
    print "Guessing current system encoding failed. Consider setting $LANG variable."
    sys.exit(1)
else:
    print "System encoding: " + encoding

have_encoding = os.path.isdir('testsuite/encodings/' + encoding)
if not have_encoding and os.path.isfile('testsuite/encodings/%s.tar.gz' % encoding):
    os.system("tar xvz -C testsuite/encodings -f testsuite/encodings/%s.tar.gz" % encoding)
    have_encoding = os.path.isdir('testsuite/encodings/' + encoding)

if have_encoding:
    #enc_base_remote = "%s/xyz/%s/" % (pbucket(1), encoding)
    enc_pattern = patterns[encoding]
else:
    print encoding + " specific files not found."

if not os.path.isdir('testsuite/crappy-file-name'):
    os.system("tar xvz -C testsuite -f testsuite/crappy-file-name.tar.gz")
    # TODO: also unpack if the tarball is newer than the directory timestamp
    #       for instance when a new version was pulled from SVN.

def test(label, cmd_args = [], retcode = 0, must_find = [], must_not_find = [], must_find_re = [], must_not_find_re = []):
    def command_output():
        print "----"
        print " ".join([arg.find(" ")>=0 and "'%s'" % arg or arg for arg in cmd_args])
        print "----"
        print stdout
        print "----"

    def failure(message = ""):
        global count_fail
        if message:
            message = "  (%r)" % message
        print "\x1b[31;1mFAIL%s\x1b[0m" % (message)
        count_fail += 1
        command_output()
        #return 1
        sys.exit(1)
    def success(message = ""):
        global count_pass
        if message:
            message = "  (%r)" % message
        print "\x1b[32;1mOK\x1b[0m%s" % (message)
        count_pass += 1
        if verbose:
            command_output()
        return 0
    def skip(message = ""):
        global count_skip
        if message:
            message = "  (%r)" % message
        print "\x1b[33;1mSKIP\x1b[0m%s" % (message)
        count_skip += 1
        return 0
    def compile_list(_list, regexps = False):
        if regexps == False:
            _list = [re.escape(item.encode(encoding, "replace")) for item in _list]

        return [re.compile(item, re.MULTILINE) for item in _list]

    global test_counter
    test_counter += 1
    print ("%3d  %s " % (test_counter, label)).ljust(30, "."),
    sys.stdout.flush()

    if run_tests.count(test_counter) == 0 or exclude_tests.count(test_counter) > 0:
        return skip()

    if not cmd_args:
        return skip()

    p = Popen(cmd_args, stdout = PIPE, stderr = STDOUT, universal_newlines = True)
    stdout, stderr = p.communicate()
    if type(retcode) not in [list, tuple]: retcode = [retcode]
    if p.returncode not in retcode:
        return failure("retcode: %d, expected one of: %s" % (p.returncode, retcode))

    if type(must_find) not in [ list, tuple ]: must_find = [must_find]
    if type(must_find_re) not in [ list, tuple ]: must_find_re = [must_find_re]
    if type(must_not_find) not in [ list, tuple ]: must_not_find = [must_not_find]
    if type(must_not_find_re) not in [ list, tuple ]: must_not_find_re = [must_not_find_re]

    find_list = []
    find_list.extend(compile_list(must_find))
    find_list.extend(compile_list(must_find_re, regexps = True))
    find_list_patterns = []
    find_list_patterns.extend(must_find)
    find_list_patterns.extend(must_find_re)

    not_find_list = []
    not_find_list.extend(compile_list(must_not_find))
    not_find_list.extend(compile_list(must_not_find_re, regexps = True))
    not_find_list_patterns = []
    not_find_list_patterns.extend(must_not_find)
    not_find_list_patterns.extend(must_not_find_re)

    for index in range(len(find_list)):
        match = find_list[index].search(stdout)
        if not match:
            return failure("pattern not found: %s" % find_list_patterns[index])
    for index in range(len(not_find_list)):
        match = not_find_list[index].search(stdout)
        if match:
            return failure("pattern found: %s (match: %s)" % (not_find_list_patterns[index], match.group(0)))

    return success()

def test_s3cmd(label, cmd_args = [], **kwargs):
    if not cmd_args[0].endswith("s3cmd"):
        cmd_args.insert(0, "python")
        cmd_args.insert(1, "s3cmd")

    return test(label, cmd_args, **kwargs)

def test_mkdir(label, dir_name):
    if os.name in ("posix", "nt"):
        cmd = ['mkdir', '-p']
    else:
        print "Unknown platform: %s" % os.name
        sys.exit(1)
    cmd.append(dir_name)
    return test(label, cmd)

def test_rmdir(label, dir_name):
    if os.path.isdir(dir_name):
        if os.name == "posix":
            cmd = ['rm', '-rf']
        elif os.name == "nt":
            cmd = ['rmdir', '/s/q']
        else:
            print "Unknown platform: %s" % os.name
            sys.exit(1)
        cmd.append(dir_name)
        return test(label, cmd)
    else:
        return test(label, [])

def test_flushdir(label, dir_name):
    test_rmdir(label + "(rm)", dir_name)
    return test_mkdir(label + "(mk)", dir_name)

def test_copy(label, src_file, dst_file):
    if os.name == "posix":
        cmd = ['cp', '-f']
    elif os.name == "nt":
        cmd = ['copy']
    else:
        print "Unknown platform: %s" % os.name
        sys.exit(1)
    cmd.append(src_file)
    cmd.append(dst_file)
    return test(label, cmd)

bucket_prefix = u"%s-" % getpass.getuser()
print "Using bucket prefix: '%s'" % bucket_prefix

argv = sys.argv[1:]
while argv:
    arg = argv.pop(0)
    if arg.startswith('--bucket-prefix='):
        print "Usage: '--bucket-prefix PREFIX', not '--bucket-prefix=PREFIX'"
        sys.exit(0)
    if arg in ("-h", "--help"):
        print "%s A B K..O -N" % sys.argv[0]
        print "Run tests number A, B and K through to O, except for N"
        sys.exit(0)
    if arg in ("-l", "--list"):
        exclude_tests = range(0, 999)
        break
    if arg in ("-v", "--verbose"):
        verbose = True
        continue
    if arg in ("-p", "--bucket-prefix"):
        try:
            bucket_prefix = argv.pop(0)
        except IndexError:
            print "Bucket prefix option must explicitly supply a bucket name prefix"
            sys.exit(0)
        continue
    if arg.find("..") >= 0:
        range_idx = arg.find("..")
        range_start = arg[:range_idx] or 0
        range_end = arg[range_idx+2:] or 999
        run_tests.extend(range(int(range_start), int(range_end) + 1))
    elif arg.startswith("-"):
        exclude_tests.append(int(arg[1:]))
    else:
        run_tests.append(int(arg))

if not run_tests:
    run_tests = range(0, 999)

# helper functions for generating bucket names
def bucket(tail):
        '''Test bucket name'''
        label = 'autotest'
        if str(tail) == '3':
                label = 'Autotest'
        return '%ss3cmd-%s-%s' % (bucket_prefix, label, tail)

def pbucket(tail):
        '''Like bucket(), but prepends "s3://" for you'''
        return 's3://' + bucket(tail)

## ====== Remove test buckets
test_s3cmd("Remove test buckets", ['rb', '-r', '--force', pbucket(1), pbucket(2), pbucket(3)])

## ====== verify they were removed
test_s3cmd("Verify no test buckets", ['ls'],
           must_not_find = [pbucket(1), pbucket(2), pbucket(3)])


## ====== Create one bucket (EU)
test_s3cmd("Create one bucket (EU)", ['mb', '--bucket-location=EU', pbucket(1)],
    must_find = "Bucket '%s/' created" % pbucket(1))



## ====== Create multiple buckets
test_s3cmd("Create multiple buckets", ['mb', pbucket(2), pbucket(3)],
    must_find = [ "Bucket '%s/' created" % pbucket(2), "Bucket '%s/' created" % pbucket(3)])


## ====== Invalid bucket name
test_s3cmd("Invalid bucket name", ["mb", "--bucket-location=EU", pbucket('EU')],
    retcode = EX_USAGE,
    must_find = "ERROR: Parameter problem: Bucket name '%s' contains disallowed character" % bucket('EU'),
    must_not_find_re = "Bucket.*created")


## ====== Buckets list
test_s3cmd("Buckets list", ["ls"],
    must_find = [ "autotest-1", "autotest-2", "Autotest-3" ], must_not_find_re = "autotest-EU")


## ====== Sync to S3
test_s3cmd("Sync to S3", ['sync', 'testsuite/', pbucket(1) + '/xyz/', '--exclude', 'demo/*', '--exclude', '*.png', '--no-encrypt', '--exclude-from', 'testsuite/exclude.encodings' ],
    must_find = [ "WARNING: 32 non-printable characters replaced in: crappy-file-name/non-printables ^A^B^C^D^E^F^G^H^I^J^K^L^M^N^O^P^Q^R^S^T^U^V^W^X^Y^Z^[^\^]^^^_^? +-[\]^<>%%\"'#{}`&?.end",
                  "WARNING: File can not be uploaded: testsuite/permission-tests/permission-denied.txt: Permission denied",
                  "stored as '%s/xyz/crappy-file-name/non-printables ^A^B^C^D^E^F^G^H^I^J^K^L^M^N^O^P^Q^R^S^T^U^V^W^X^Y^Z^[^\^]^^^_^? +-[\\]^<>%%%%\"'#{}`&?.end'" % pbucket(1) ],
    must_not_find_re = [ "demo/", "\.png$", "permission-denied-dir" ])

if have_encoding:
    ## ====== Sync UTF-8 / GBK / ... to S3
    test_s3cmd("Sync %s to S3" % encoding, ['sync', 'testsuite/encodings/' + encoding, '%s/xyz/encodings/' % pbucket(1), '--exclude', 'demo/*', '--no-encrypt' ],
        must_find = [ u"File 'testsuite/encodings/%(encoding)s/%(pattern)s' stored as '%(pbucket)s/xyz/encodings/%(encoding)s/%(pattern)s'" % { 'encoding' : encoding, 'pattern' : enc_pattern , 'pbucket' : pbucket(1)} ])


## ====== List bucket content
test_s3cmd("List bucket content", ['ls', '%s/xyz/' % pbucket(1) ],
    must_find_re = [ u"DIR +%s/xyz/binary/$" % pbucket(1) , u"DIR +%s/xyz/etc/$" % pbucket(1) ],
    must_not_find = [ u"random-crap.md5", u"/demo" ])


## ====== List bucket recursive
must_find = [ u"%s/xyz/binary/random-crap.md5" % pbucket(1) ]
if have_encoding:
    must_find.append(u"%(pbucket)s/xyz/encodings/%(encoding)s/%(pattern)s" % { 'encoding' : encoding, 'pattern' : enc_pattern, 'pbucket' : pbucket(1) })

test_s3cmd("List bucket recursive", ['ls', '--recursive', pbucket(1)],
    must_find = must_find,
    must_not_find = [ "logo.png" ])

## ====== FIXME
# test_s3cmd("Recursive put", ['put', '--recursive', 'testsuite/etc', '%s/xyz/' % pbucket(1) ])


## ====== Clean up local destination dir
test_flushdir("Clean testsuite-out/", "testsuite-out")


## ====== Sync from S3
must_find = [ "File '%s/xyz/binary/random-crap.md5' stored as 'testsuite-out/xyz/binary/random-crap.md5'" % pbucket(1) ]
if have_encoding:
    must_find.append(u"File '%(pbucket)s/xyz/encodings/%(encoding)s/%(pattern)s' stored as 'testsuite-out/xyz/encodings/%(encoding)s/%(pattern)s' " % { 'encoding' : encoding, 'pattern' : enc_pattern, 'pbucket' : pbucket(1) })
test_s3cmd("Sync from S3", ['sync', '%s/xyz' % pbucket(1), 'testsuite-out'],
    must_find = must_find)


## ====== Remove 'demo' directory
test_rmdir("Remove 'dir-test/'", "testsuite-out/xyz/dir-test/")


## ====== Create dir with name of a file
test_mkdir("Create file-dir dir", "testsuite-out/xyz/dir-test/file-dir")


## ====== Skip dst dirs
test_s3cmd("Skip over dir", ['sync', '%s/xyz' % pbucket(1), 'testsuite-out'],
    must_find = "WARNING: testsuite-out/xyz/dir-test/file-dir is a directory - skipping over")


## ====== Clean up local destination dir
test_flushdir("Clean testsuite-out/", "testsuite-out")


## ====== Put public, guess MIME
test_s3cmd("Put public, guess MIME", ['put', '--guess-mime-type', '--acl-public', 'testsuite/etc/logo.png', '%s/xyz/etc/logo.png' % pbucket(1)],
    must_find = [ "stored as '%s/xyz/etc/logo.png'" % pbucket(1) ])


## ====== Retrieve from URL
if have_wget:
    test("Retrieve from URL", ['wget', '-O', 'testsuite-out/logo.png', 'http://%s.%s/xyz/etc/logo.png' % (bucket(1), cfg.host_base)],
        must_find_re = [ 'logo.png.*saved \[22059/22059\]' ])


## ====== Change ACL to Private
test_s3cmd("Change ACL to Private", ['setacl', '--acl-private', '%s/xyz/etc/l*.png' % pbucket(1)],
    must_find = [ "logo.png: ACL set to Private" ])


## ====== Verify Private ACL
if have_wget:
    test("Verify Private ACL", ['wget', '-O', 'testsuite-out/logo.png', 'http://%s.%s/xyz/etc/logo.png' % (bucket(1), cfg.host_base)],
         retcode = [1, 8],
         must_find_re = [ 'ERROR 403: Forbidden' ])


## ====== Change ACL to Public
test_s3cmd("Change ACL to Public", ['setacl', '--acl-public', '--recursive', '%s/xyz/etc/' % pbucket(1) , '-v'],
    must_find = [ "logo.png: ACL set to Public" ])


## ====== Verify Public ACL
if have_wget:
    test("Verify Public ACL", ['wget', '-O', 'testsuite-out/logo.png', 'http://%s.%s/xyz/etc/logo.png' % (bucket(1), cfg.host_base)],
        must_find_re = [ 'logo.png.*saved \[22059/22059\]' ])


## ====== Sync more to S3
test_s3cmd("Sync more to S3", ['sync', 'testsuite/', 's3://%s/xyz/' % bucket(1), '--no-encrypt' ],
    must_find = [ "File 'testsuite/demo/some-file.xml' stored as '%s/xyz/demo/some-file.xml' " % pbucket(1) ],
    must_not_find = [ "File 'testsuite/etc/linked.png' stored as '%s/xyz/etc/linked.png" % pbucket(1) ])


## ====== Don't check MD5 sum on Sync
test_copy("Change file cksum1.txt", "testsuite/checksum/cksum2.txt", "testsuite/checksum/cksum1.txt")
test_copy("Change file cksum33.txt", "testsuite/checksum/cksum2.txt", "testsuite/checksum/cksum33.txt")
test_s3cmd("Don't check MD5", ['sync', 'testsuite/', 's3://%s/xyz/' % bucket(1), '--no-encrypt', '--no-check-md5'],
    must_find = [ "cksum33.txt" ],
    must_not_find = [ "cksum1.txt" ])


## ====== Check MD5 sum on Sync
test_s3cmd("Check MD5", ['sync', 'testsuite/', 's3://%s/xyz/' % bucket(1), '--no-encrypt', '--check-md5'],
    must_find = [ "cksum1.txt" ])


## ====== Rename within S3
test_s3cmd("Rename within S3", ['mv', '%s/xyz/etc/logo.png' % pbucket(1), '%s/xyz/etc2/Logo.PNG' % pbucket(1)],
    must_find = [ 'File %s/xyz/etc/logo.png moved to %s/xyz/etc2/Logo.PNG' % (pbucket(1), pbucket(1))])


## ====== Rename (NoSuchKey)
test_s3cmd("Rename (NoSuchKey)", ['mv', '%s/xyz/etc/logo.png' % pbucket(1), '%s/xyz/etc2/Logo.PNG' % pbucket(1)],
    retcode = EX_SOFTWARE,
    must_find_re = [ 'ERROR:.*NoSuchKey' ],
    must_not_find = [ 'File %s/xyz/etc/logo.png moved to %s/xyz/etc2/Logo.PNG' % (pbucket(1), pbucket(1)) ])

## ====== Sync more from S3 (invalid src)
test_s3cmd("Sync more from S3 (invalid src)", ['sync', '--delete-removed', '%s/xyz/DOESNOTEXIST' % pbucket(1), 'testsuite-out'],
    must_not_find = [ "deleted: testsuite-out/logo.png" ])

## ====== Sync more from S3
test_s3cmd("Sync more from S3", ['sync', '--delete-removed', '%s/xyz' % pbucket(1), 'testsuite-out'],
    must_find = [ "deleted: testsuite-out/logo.png",
                  "File '%s/xyz/etc2/Logo.PNG' stored as 'testsuite-out/xyz/etc2/Logo.PNG' (22059 bytes" % pbucket(1),
                  "File '%s/xyz/demo/some-file.xml' stored as 'testsuite-out/xyz/demo/some-file.xml' " % pbucket(1) ],
    must_not_find_re = [ "not-deleted.*etc/logo.png" ])


## ====== Make dst dir for get
test_rmdir("Remove dst dir for get", "testsuite-out")


## ====== Get multiple files
test_s3cmd("Get multiple files", ['get', '%s/xyz/etc2/Logo.PNG' % pbucket(1), '%s/xyz/etc/AtomicClockRadio.ttf' % pbucket(1), 'testsuite-out'],
    retcode = EX_USAGE,
    must_find = [ 'Destination must be a directory or stdout when downloading multiple sources.' ])

## ====== put/get non-ASCII filenames
test_s3cmd("Put unicode filenames", ['put', u'testsuite/encodings/UTF-8/ŪņЇЌœđЗ/Žůžo',  u'%s/xyz/encodings/UTF-8/ŪņЇЌœđЗ/Žůžo' % pbucket(1)],
           retcode = 0,
           must_find = [ 'stored as' ])


## ====== Make dst dir for get
test_mkdir("Make dst dir for get", "testsuite-out")


## ====== put/get non-ASCII filenames
test_s3cmd("Get unicode filenames", ['get', u'%s/xyz/encodings/UTF-8/ŪņЇЌœđЗ/Žůžo' % pbucket(1), 'testsuite-out'],
           retcode = 0,
           must_find = [ 'saved as' ])


## ====== Get multiple files
test_s3cmd("Get multiple files", ['get', '%s/xyz/etc2/Logo.PNG' % pbucket(1), '%s/xyz/etc/AtomicClockRadio.ttf' % pbucket(1), 'testsuite-out'],
    must_find = [ u"saved as 'testsuite-out/Logo.PNG'", u"saved as 'testsuite-out/AtomicClockRadio.ttf'" ])

## ====== Upload files differing in capitalisation
test_s3cmd("blah.txt / Blah.txt", ['put', '-r', 'testsuite/blahBlah', pbucket(1)],
    must_find = [ '%s/blahBlah/Blah.txt' % pbucket(1), '%s/blahBlah/blah.txt' % pbucket(1)])

## ====== Copy between buckets
test_s3cmd("Copy between buckets", ['cp', '%s/xyz/etc2/Logo.PNG' % pbucket(1), '%s/xyz/etc2/logo.png' % pbucket(3)],
    must_find = [ "File %s/xyz/etc2/Logo.PNG copied to %s/xyz/etc2/logo.png" % (pbucket(1), pbucket(3)) ])

## ====== Recursive copy
test_s3cmd("Recursive copy, set ACL", ['cp', '-r', '--acl-public', '%s/xyz/' % pbucket(1), '%s/copy' % pbucket(2), '--exclude', 'demo/dir?/*.txt', '--exclude', 'non-printables*'],
    must_find = [ "File %s/xyz/etc2/Logo.PNG copied to %s/copy/etc2/Logo.PNG" % (pbucket(1), pbucket(2)),
                  "File %s/xyz/blahBlah/Blah.txt copied to %s/copy/blahBlah/Blah.txt" % (pbucket(1), pbucket(2)),
                  "File %s/xyz/blahBlah/blah.txt copied to %s/copy/blahBlah/blah.txt" % (pbucket(1), pbucket(2)) ],
    must_not_find = [ "demo/dir1/file1-1.txt" ])

## ====== Verify ACL and MIME type
test_s3cmd("Verify ACL and MIME type", ['info', '%s/copy/etc2/Logo.PNG' % pbucket(2) ],
    must_find_re = [ "MIME type:.*image/png",
                     "ACL:.*\*anon\*: READ",
                     "URL:.*http://%s.%s/copy/etc2/Logo.PNG" % (bucket(2), cfg.host_base) ])

## ====== Rename within S3
test_s3cmd("Rename within S3", ['mv', '%s/copy/etc2/Logo.PNG' % pbucket(2), '%s/copy/etc/logo.png' % pbucket(2)],
    must_find = [ 'File %s/copy/etc2/Logo.PNG moved to %s/copy/etc/logo.png' % (pbucket(2), pbucket(2))])

## ====== Sync between buckets
test_s3cmd("Sync remote2remote", ['sync', '%s/xyz/' % pbucket(1), '%s/copy/' % pbucket(2), '--delete-removed', '--exclude', 'non-printables*'],
    must_find = [ "File %s/xyz/demo/dir1/file1-1.txt copied to %s/copy/demo/dir1/file1-1.txt" % (pbucket(1), pbucket(2)),
                  "remote copy: etc/logo.png -> etc2/Logo.PNG",
                  "File %s/copy/etc/logo.png deleted" % pbucket(2) ],
    must_not_find = [ "blah.txt" ])

## ====== Don't Put symbolic link
test_s3cmd("Don't put symbolic links", ['put', 'testsuite/etc/linked1.png', 's3://%s/xyz/' % bucket(1),],
           retcode = EX_USAGE,
           must_not_find_re = [ "linked1.png"])

## ====== Put symbolic link
test_s3cmd("Put symbolic links", ['put', 'testsuite/etc/linked1.png', 's3://%s/xyz/' % bucket(1),'--follow-symlinks' ],
           must_find = [ "File 'testsuite/etc/linked1.png' stored as '%s/xyz/linked1.png'" % pbucket(1)])

## ====== Sync symbolic links
test_s3cmd("Sync symbolic links", ['sync', 'testsuite/', 's3://%s/xyz/' % bucket(1), '--no-encrypt', '--follow-symlinks' ],
    must_find = ["remote copy: etc2/Logo.PNG -> etc/linked.png"],
           # Don't want to recursively copy linked directories!
           must_not_find_re = ["etc/more/linked-dir/more/give-me-more.txt",
                               "etc/brokenlink.png"],
           )

## ====== Multi source move
test_s3cmd("Multi-source move", ['mv', '-r', '%s/copy/blahBlah/Blah.txt' % pbucket(2), '%s/copy/etc/' % pbucket(2), '%s/moved/' % pbucket(2)],
    must_find = [ "File %s/copy/blahBlah/Blah.txt moved to %s/moved/Blah.txt" % (pbucket(2), pbucket(2)),
                  "File %s/copy/etc/AtomicClockRadio.ttf moved to %s/moved/AtomicClockRadio.ttf" % (pbucket(2), pbucket(2)),
                  "File %s/copy/etc/TypeRa.ttf moved to %s/moved/TypeRa.ttf" % (pbucket(2), pbucket(2)) ],
    must_not_find = [ "blah.txt" ])

## ====== Verify move
test_s3cmd("Verify move", ['ls', '-r', pbucket(2)],
    must_find = [ "%s/moved/Blah.txt" % pbucket(2),
                  "%s/moved/AtomicClockRadio.ttf" % pbucket(2),
                  "%s/moved/TypeRa.ttf" % pbucket(2),
                  "%s/copy/blahBlah/blah.txt" % pbucket(2) ],
    must_not_find = [ "%s/copy/blahBlah/Blah.txt" % pbucket(2),
                      "%s/copy/etc/AtomicClockRadio.ttf" % pbucket(2),
                      "%s/copy/etc/TypeRa.ttf" % pbucket(2) ])

## ====== Simple delete
test_s3cmd("Simple delete", ['del', '%s/xyz/etc2/Logo.PNG' % pbucket(1)],
    must_find = [ "File %s/xyz/etc2/Logo.PNG deleted" % pbucket(1) ])

## ====== Simple delete with rm
test_s3cmd("Simple delete with rm", ['rm', '%s/xyz/test_rm/TypeRa.ttf' % pbucket(1)],
    must_find = [ "File %s/xyz/test_rm/TypeRa.ttf deleted" % pbucket(1) ])

## ====== Create expiration rule with days and prefix
test_s3cmd("Create expiration rule with days and prefix", ['expire', pbucket(1), '--expiry-days=365', '--expiry-prefix=log/'],
    must_find = [ "Bucket '%s/': expiration configuration is set." % pbucket(1)])

## ====== Create expiration rule with date and prefix
test_s3cmd("Create expiration rule with date and prefix", ['expire', pbucket(1), '--expiry-date=2012-12-31T00:00:00.000Z', '--expiry-prefix=log/'],
    must_find = [ "Bucket '%s/': expiration configuration is set." % pbucket(1)])

## ====== Create expiration rule with days only
test_s3cmd("Create expiration rule with days only", ['expire', pbucket(1), '--expiry-days=365'],
    must_find = [ "Bucket '%s/': expiration configuration is set." % pbucket(1)])

## ====== Create expiration rule with date only
test_s3cmd("Create expiration rule with date only", ['expire', pbucket(1), '--expiry-date=2012-12-31T00:00:00.000Z'],
    must_find = [ "Bucket '%s/': expiration configuration is set." % pbucket(1)])

## ====== Get current expiration setting
test_s3cmd("Get current expiration setting", ['info', pbucket(1)],
    must_find = [ "Expiration Rule: all objects in this bucket will expire in '2012-12-31T00:00:00.000Z'"])

## ====== Delete expiration rule
test_s3cmd("Delete expiration rule", ['expire', pbucket(1)],
    must_find = [ "Bucket '%s/': expiration configuration is deleted." % pbucket(1)])

## ====== Recursive delete maximum exceeed
test_s3cmd("Recursive delete maximum exceeded", ['del', '--recursive', '--max-delete=1', '--exclude', 'Atomic*', '%s/xyz/etc' % pbucket(1)],
    must_not_find = [ "File %s/xyz/etc/TypeRa.ttf deleted" % pbucket(1) ])

## ====== Recursive delete
test_s3cmd("Recursive delete", ['del', '--recursive', '--exclude', 'Atomic*', '%s/xyz/etc' % pbucket(1)],
    must_find = [ "File %s/xyz/etc/TypeRa.ttf deleted" % pbucket(1) ],
    must_find_re = [ "File .*/etc/logo.png deleted" ],
    must_not_find = [ "AtomicClockRadio.ttf" ])

## ====== Recursive delete with rm
test_s3cmd("Recursive delete with rm", ['rm', '--recursive', '--exclude', 'Atomic*', '%s/xyz/test_rm' % pbucket(1)],
    must_find = [ "File %s/xyz/test_rm/more/give-me-more.txt deleted" % pbucket(1) ],
    must_find_re = [ "File .*/test_rm/logo.png deleted" ],
    must_not_find = [ "AtomicClockRadio.ttf" ])

## ====== Recursive delete all
test_s3cmd("Recursive delete all", ['del', '--recursive', '--force', pbucket(1)],
    must_find_re = [ "File .*binary/random-crap deleted" ])

## ====== Remove empty bucket
test_s3cmd("Remove empty bucket", ['rb', pbucket(1)],
    must_find = [ "Bucket '%s/' removed" % pbucket(1) ])

## ====== Remove remaining buckets
test_s3cmd("Remove remaining buckets", ['rb', '--recursive', pbucket(2), pbucket(3)],
    must_find = [ "Bucket '%s/' removed" % pbucket(2),
              "Bucket '%s/' removed" % pbucket(3) ])

# vim:et:ts=4:sts=4:ai

########NEW FILE########
__FILENAME__ = AccessLog
## Amazon S3 - Access Control List representation
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2
## Copyright: TGRMN Software and contributors

import S3Uri
from Exceptions import ParameterError
from Utils import getTreeFromXml
from ACL import GranteeAnonRead

try:
    import xml.etree.ElementTree as ET
except ImportError:
    import elementtree.ElementTree as ET

__all__ = []
class AccessLog(object):
    LOG_DISABLED = "<BucketLoggingStatus></BucketLoggingStatus>"
    LOG_TEMPLATE = "<LoggingEnabled><TargetBucket></TargetBucket><TargetPrefix></TargetPrefix></LoggingEnabled>"

    def __init__(self, xml = None):
        if not xml:
            xml = self.LOG_DISABLED
        self.tree = getTreeFromXml(xml)
        self.tree.attrib['xmlns'] = "http://doc.s3.amazonaws.com/2006-03-01"

    def isLoggingEnabled(self):
        return bool(self.tree.find(".//LoggingEnabled"))

    def disableLogging(self):
        el = self.tree.find(".//LoggingEnabled")
        if el:
            self.tree.remove(el)

    def enableLogging(self, target_prefix_uri):
        el = self.tree.find(".//LoggingEnabled")
        if not el:
            el = getTreeFromXml(self.LOG_TEMPLATE)
            self.tree.append(el)
        el.find(".//TargetBucket").text = target_prefix_uri.bucket()
        el.find(".//TargetPrefix").text = target_prefix_uri.object()

    def targetPrefix(self):
        if self.isLoggingEnabled():
            el = self.tree.find(".//LoggingEnabled")
            target_prefix = "s3://%s/%s" % (
                self.tree.find(".//LoggingEnabled//TargetBucket").text,
                self.tree.find(".//LoggingEnabled//TargetPrefix").text)
            return S3Uri.S3Uri(target_prefix)
        else:
            return ""

    def setAclPublic(self, acl_public):
        le = self.tree.find(".//LoggingEnabled")
        if not le:
            raise ParameterError("Logging not enabled, can't set default ACL for logs")
        tg = le.find(".//TargetGrants")
        if not acl_public:
            if not tg:
                ## All good, it's not been there
                return
            else:
                le.remove(tg)
        else: # acl_public == True
            anon_read = GranteeAnonRead().getElement()
            if not tg:
                tg = ET.SubElement(le, "TargetGrants")
            ## What if TargetGrants already exists? We should check if
            ## AnonRead is there before appending a new one. Later...
            tg.append(anon_read)

    def isAclPublic(self):
        raise NotImplementedError()

    def __str__(self):
        return ET.tostring(self.tree)
__all__.append("AccessLog")

if __name__ == "__main__":
    from S3Uri import S3Uri
    log = AccessLog()
    print log
    log.enableLogging(S3Uri("s3://targetbucket/prefix/log-"))
    print log
    log.setAclPublic(True)
    print log
    log.setAclPublic(False)
    print log
    log.disableLogging()
    print log

# vim:et:ts=4:sts=4:ai

########NEW FILE########
__FILENAME__ = ACL
## Amazon S3 - Access Control List representation
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2
## Copyright: TGRMN Software and contributors

from Utils import getTreeFromXml

try:
    import xml.etree.ElementTree as ET
except ImportError:
    import elementtree.ElementTree as ET

class Grantee(object):
    ALL_USERS_URI = "http://acs.amazonaws.com/groups/global/AllUsers"
    LOG_DELIVERY_URI = "http://acs.amazonaws.com/groups/s3/LogDelivery"

    def __init__(self):
        self.xsi_type = None
        self.tag = None
        self.name = None
        self.display_name = None
        self.permission = None

    def __repr__(self):
        return 'Grantee("%(tag)s", "%(name)s", "%(permission)s")' % {
            "tag" : self.tag,
            "name" : self.name,
            "permission" : self.permission
        }

    def isAllUsers(self):
        return self.tag == "URI" and self.name == Grantee.ALL_USERS_URI

    def isAnonRead(self):
        return self.isAllUsers() and (self.permission == "READ" or self.permission == "FULL_CONTROL")

    def getElement(self):
        el = ET.Element("Grant")
        grantee = ET.SubElement(el, "Grantee", {
            'xmlns:xsi' : 'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:type' : self.xsi_type
        })
        name = ET.SubElement(grantee, self.tag)
        name.text = self.name
        permission = ET.SubElement(el, "Permission")
        permission.text = self.permission
        return el

class GranteeAnonRead(Grantee):
    def __init__(self):
        Grantee.__init__(self)
        self.xsi_type = "Group"
        self.tag = "URI"
        self.name = Grantee.ALL_USERS_URI
        self.permission = "READ"

class GranteeLogDelivery(Grantee):
    def __init__(self, permission):
        """
        permission must be either READ_ACP or WRITE
        """
        Grantee.__init__(self)
        self.xsi_type = "Group"
        self.tag = "URI"
        self.name = Grantee.LOG_DELIVERY_URI
        self.permission = permission

class ACL(object):
    EMPTY_ACL = "<AccessControlPolicy><Owner><ID></ID></Owner><AccessControlList></AccessControlList></AccessControlPolicy>"

    def __init__(self, xml = None):
        if not xml:
            xml = ACL.EMPTY_ACL

        self.grantees = []
        self.owner_id = ""
        self.owner_nick = ""

        tree = getTreeFromXml(xml)
        self.parseOwner(tree)
        self.parseGrants(tree)

    def parseOwner(self, tree):
        self.owner_id = tree.findtext(".//Owner//ID")
        self.owner_nick = tree.findtext(".//Owner//DisplayName")

    def parseGrants(self, tree):
        for grant in tree.findall(".//Grant"):
            grantee = Grantee()
            g = grant.find(".//Grantee")
            grantee.xsi_type = g.attrib['{http://www.w3.org/2001/XMLSchema-instance}type']
            grantee.permission = grant.find('Permission').text
            for el in g:
                if el.tag == "DisplayName":
                    grantee.display_name = el.text
                else:
                    grantee.tag = el.tag
                    grantee.name = el.text
            self.grantees.append(grantee)

    def getGrantList(self):
        acl = []
        for grantee in self.grantees:
            if grantee.display_name:
                user = grantee.display_name
            elif grantee.isAllUsers():
                user = "*anon*"
            else:
                user = grantee.name
            acl.append({'grantee': user, 'permission': grantee.permission})
        return acl

    def getOwner(self):
        return { 'id' : self.owner_id, 'nick' : self.owner_nick }

    def isAnonRead(self):
        for grantee in self.grantees:
            if grantee.isAnonRead():
                return True
        return False

    def grantAnonRead(self):
        if not self.isAnonRead():
            self.appendGrantee(GranteeAnonRead())

    def revokeAnonRead(self):
        self.grantees = [g for g in self.grantees if not g.isAnonRead()]

    def appendGrantee(self, grantee):
        self.grantees.append(grantee)

    def hasGrant(self, name, permission):
        name = name.lower()
        permission = permission.upper()

        for grantee in self.grantees:
            if grantee.name.lower() == name:
                if grantee.permission == "FULL_CONTROL":
                    return True
                elif grantee.permission.upper() == permission:
                    return True

        return False;

    def grant(self, name, permission):
        if self.hasGrant(name, permission):
            return

        permission = permission.upper()

        if "ALL" == permission:
            permission = "FULL_CONTROL"

        if "FULL_CONTROL" == permission:
            self.revoke(name, "ALL")

        grantee = Grantee()
        grantee.name = name
        grantee.permission = permission

        if  name.find('@') > -1:
            grantee.name = grantee.name.lower()
            grantee.xsi_type = "AmazonCustomerByEmail"
            grantee.tag = "EmailAddress"
        elif name.find('http://acs.amazonaws.com/groups/') > -1:
            grantee.xsi_type = "Group"
            grantee.tag = "URI"
        else:
            grantee.name = grantee.name.lower()
            grantee.xsi_type = "CanonicalUser"
            grantee.tag = "ID"

        self.appendGrantee(grantee)


    def revoke(self, name, permission):
        name = name.lower()
        permission = permission.upper()

        if "ALL" == permission:
            self.grantees = [g for g in self.grantees if not g.name.lower() == name]
        else:
            self.grantees = [g for g in self.grantees if not (g.name.lower() == name and g.permission.upper() ==  permission)]


    def __str__(self):
        tree = getTreeFromXml(ACL.EMPTY_ACL)
        tree.attrib['xmlns'] = "http://s3.amazonaws.com/doc/2006-03-01/"
        owner = tree.find(".//Owner//ID")
        owner.text = self.owner_id
        acl = tree.find(".//AccessControlList")
        for grantee in self.grantees:
            acl.append(grantee.getElement())
        return ET.tostring(tree)

if __name__ == "__main__":
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<AccessControlPolicy xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
<Owner>
    <ID>12345678901234567890</ID>
    <DisplayName>owner-nickname</DisplayName>
</Owner>
<AccessControlList>
    <Grant>
        <Grantee xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="CanonicalUser">
            <ID>12345678901234567890</ID>
            <DisplayName>owner-nickname</DisplayName>
        </Grantee>
        <Permission>FULL_CONTROL</Permission>
    </Grant>
    <Grant>
        <Grantee xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="Group">
            <URI>http://acs.amazonaws.com/groups/global/AllUsers</URI>
        </Grantee>
        <Permission>READ</Permission>
    </Grant>
</AccessControlList>
</AccessControlPolicy>
    """
    acl = ACL(xml)
    print "Grants:", acl.getGrantList()
    acl.revokeAnonRead()
    print "Grants:", acl.getGrantList()
    acl.grantAnonRead()
    print "Grants:", acl.getGrantList()
    print acl

# vim:et:ts=4:sts=4:ai

########NEW FILE########
__FILENAME__ = BidirMap
## Amazon S3 manager
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2
## Copyright: TGRMN Software and contributors

class BidirMap(object):
    def __init__(self, **map):
        self.k2v = {}
        self.v2k = {}
        for key in map:
            self.__setitem__(key, map[key])

    def __setitem__(self, key, value):
        if self.v2k.has_key(value):
            if self.v2k[value] != key:
                raise KeyError("Value '"+str(value)+"' already in use with key '"+str(self.v2k[value])+"'")
        try:
            del(self.v2k[self.k2v[key]])
        except KeyError:
            pass
        self.k2v[key] = value
        self.v2k[value] = key

    def __getitem__(self, key):
        return self.k2v[key]

    def __str__(self):
        return self.v2k.__str__()

    def getkey(self, value):
        return self.v2k[value]

    def getvalue(self, key):
        return self.k2v[key]

    def keys(self):
        return [key for key in self.k2v]

    def values(self):
        return [value for value in self.v2k]

# vim:et:ts=4:sts=4:ai

########NEW FILE########
__FILENAME__ = CloudFront
## Amazon CloudFront support
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2
## Copyright: TGRMN Software and contributors

import sys
import time
import httplib
import random
from datetime import datetime
from logging import debug, info, warning, error

try:
    import xml.etree.ElementTree as ET
except ImportError:
    import elementtree.ElementTree as ET

from S3 import S3
from Config import Config
from Exceptions import *
from Utils import getTreeFromXml, appendXmlTextNode, getDictFromTree, dateS3toPython, sign_string, getBucketFromHostname, getHostnameFromBucket
from S3Uri import S3Uri, S3UriS3
from FileLists import fetch_remote_list

cloudfront_api_version = "2010-11-01"
cloudfront_resource = "/%(api_ver)s/distribution" % { 'api_ver' : cloudfront_api_version }

def output(message):
    sys.stdout.write(message + "\n")

def pretty_output(label, message):
    #label = ("%s " % label).ljust(20, ".")
    label = ("%s:" % label).ljust(15)
    output("%s %s" % (label, message))

class DistributionSummary(object):
    ## Example:
    ##
    ## <DistributionSummary>
    ##  <Id>1234567890ABC</Id>
    ##  <Status>Deployed</Status>
    ##  <LastModifiedTime>2009-01-16T11:49:02.189Z</LastModifiedTime>
    ##  <DomainName>blahblahblah.cloudfront.net</DomainName>
    ##  <S3Origin>
    ##     <DNSName>example.bucket.s3.amazonaws.com</DNSName>
    ##  </S3Origin>
    ##  <CNAME>cdn.example.com</CNAME>
    ##  <CNAME>img.example.com</CNAME>
    ##  <Comment>What Ever</Comment>
    ##  <Enabled>true</Enabled>
    ## </DistributionSummary>

    def __init__(self, tree):
        if tree.tag != "DistributionSummary":
            raise ValueError("Expected <DistributionSummary /> xml, got: <%s />" % tree.tag)
        self.parse(tree)

    def parse(self, tree):
        self.info = getDictFromTree(tree)
        self.info['Enabled'] = (self.info['Enabled'].lower() == "true")
        if self.info.has_key("CNAME") and type(self.info['CNAME']) != list:
            self.info['CNAME'] = [self.info['CNAME']]

    def uri(self):
        return S3Uri("cf://%s" % self.info['Id'])

class DistributionList(object):
    ## Example:
    ##
    ## <DistributionList xmlns="http://cloudfront.amazonaws.com/doc/2010-07-15/">
    ##  <Marker />
    ##  <MaxItems>100</MaxItems>
    ##  <IsTruncated>false</IsTruncated>
    ##  <DistributionSummary>
    ##  ... handled by DistributionSummary() class ...
    ##  </DistributionSummary>
    ## </DistributionList>

    def __init__(self, xml):
        tree = getTreeFromXml(xml)
        if tree.tag != "DistributionList":
            raise ValueError("Expected <DistributionList /> xml, got: <%s />" % tree.tag)
        self.parse(tree)

    def parse(self, tree):
        self.info = getDictFromTree(tree)
        ## Normalise some items
        self.info['IsTruncated'] = (self.info['IsTruncated'].lower() == "true")

        self.dist_summs = []
        for dist_summ in tree.findall(".//DistributionSummary"):
            self.dist_summs.append(DistributionSummary(dist_summ))

class Distribution(object):
    ## Example:
    ##
    ## <Distribution xmlns="http://cloudfront.amazonaws.com/doc/2010-07-15/">
    ##  <Id>1234567890ABC</Id>
    ##  <Status>InProgress</Status>
    ##  <LastModifiedTime>2009-01-16T13:07:11.319Z</LastModifiedTime>
    ##  <DomainName>blahblahblah.cloudfront.net</DomainName>
    ##  <DistributionConfig>
    ##  ... handled by DistributionConfig() class ...
    ##  </DistributionConfig>
    ## </Distribution>

    def __init__(self, xml):
        tree = getTreeFromXml(xml)
        if tree.tag != "Distribution":
            raise ValueError("Expected <Distribution /> xml, got: <%s />" % tree.tag)
        self.parse(tree)

    def parse(self, tree):
        self.info = getDictFromTree(tree)
        ## Normalise some items
        self.info['LastModifiedTime'] = dateS3toPython(self.info['LastModifiedTime'])

        self.info['DistributionConfig'] = DistributionConfig(tree = tree.find(".//DistributionConfig"))

    def uri(self):
        return S3Uri("cf://%s" % self.info['Id'])

class DistributionConfig(object):
    ## Example:
    ##
    ## <DistributionConfig>
    ##  <Origin>somebucket.s3.amazonaws.com</Origin>
    ##  <CallerReference>s3://somebucket/</CallerReference>
    ##  <Comment>http://somebucket.s3.amazonaws.com/</Comment>
    ##  <Enabled>true</Enabled>
    ##  <Logging>
    ##    <Bucket>bu.ck.et</Bucket>
    ##    <Prefix>/cf-somebucket/</Prefix>
    ##  </Logging>
    ## </DistributionConfig>

    EMPTY_CONFIG = "<DistributionConfig><S3Origin><DNSName/></S3Origin><CallerReference/><Enabled>true</Enabled></DistributionConfig>"
    xmlns = "http://cloudfront.amazonaws.com/doc/%(api_ver)s/" % { 'api_ver' : cloudfront_api_version }
    def __init__(self, xml = None, tree = None):
        if xml is None:
            xml = DistributionConfig.EMPTY_CONFIG

        if tree is None:
            tree = getTreeFromXml(xml)

        if tree.tag != "DistributionConfig":
            raise ValueError("Expected <DistributionConfig /> xml, got: <%s />" % tree.tag)
        self.parse(tree)

    def parse(self, tree):
        self.info = getDictFromTree(tree)
        self.info['Enabled'] = (self.info['Enabled'].lower() == "true")
        if not self.info.has_key("CNAME"):
            self.info['CNAME'] = []
        if type(self.info['CNAME']) != list:
            self.info['CNAME'] = [self.info['CNAME']]
        self.info['CNAME'] = [cname.lower() for cname in self.info['CNAME']]
        if not self.info.has_key("Comment"):
            self.info['Comment'] = ""
        if not self.info.has_key("DefaultRootObject"):
            self.info['DefaultRootObject'] = ""
        ## Figure out logging - complex node not parsed by getDictFromTree()
        logging_nodes = tree.findall(".//Logging")
        if logging_nodes:
            logging_dict = getDictFromTree(logging_nodes[0])
            logging_dict['Bucket'], success = getBucketFromHostname(logging_dict['Bucket'])
            if not success:
                warning("Logging to unparsable bucket name: %s" % logging_dict['Bucket'])
            self.info['Logging'] = S3UriS3("s3://%(Bucket)s/%(Prefix)s" % logging_dict)
        else:
            self.info['Logging'] = None

    def __str__(self):
        tree = ET.Element("DistributionConfig")
        tree.attrib['xmlns'] = DistributionConfig.xmlns

        ## Retain the order of the following calls!
        s3org = appendXmlTextNode("S3Origin", '', tree)
        appendXmlTextNode("DNSName", self.info['S3Origin']['DNSName'], s3org)
        appendXmlTextNode("CallerReference", self.info['CallerReference'], tree)
        for cname in self.info['CNAME']:
            appendXmlTextNode("CNAME", cname.lower(), tree)
        if self.info['Comment']:
            appendXmlTextNode("Comment", self.info['Comment'], tree)
        appendXmlTextNode("Enabled", str(self.info['Enabled']).lower(), tree)
        # don't create a empty DefaultRootObject element as it would result in a MalformedXML error
        if str(self.info['DefaultRootObject']):
            appendXmlTextNode("DefaultRootObject", str(self.info['DefaultRootObject']), tree)
        if self.info['Logging']:
            logging_el = ET.Element("Logging")
            appendXmlTextNode("Bucket", getHostnameFromBucket(self.info['Logging'].bucket()), logging_el)
            appendXmlTextNode("Prefix", self.info['Logging'].object(), logging_el)
            tree.append(logging_el)
        return ET.tostring(tree)

class Invalidation(object):
    ## Example:
    ##
    ## <Invalidation xmlns="http://cloudfront.amazonaws.com/doc/2010-11-01/">
    ##   <Id>id</Id>
    ##   <Status>status</Status>
    ##   <CreateTime>date</CreateTime>
    ##   <InvalidationBatch>
    ##       <Path>/image1.jpg</Path>
    ##       <Path>/image2.jpg</Path>
    ##       <Path>/videos/movie.flv</Path>
    ##       <CallerReference>my-batch</CallerReference>
    ##   </InvalidationBatch>
    ## </Invalidation>

    def __init__(self, xml):
        tree = getTreeFromXml(xml)
        if tree.tag != "Invalidation":
            raise ValueError("Expected <Invalidation /> xml, got: <%s />" % tree.tag)
        self.parse(tree)

    def parse(self, tree):
        self.info = getDictFromTree(tree)

    def __str__(self):
        return str(self.info)

class InvalidationList(object):
    ## Example:
    ##
    ## <InvalidationList>
    ##   <Marker/>
    ##   <NextMarker>Invalidation ID</NextMarker>
    ##   <MaxItems>2</MaxItems>
    ##   <IsTruncated>true</IsTruncated>
    ##   <InvalidationSummary>
    ##     <Id>[Second Invalidation ID]</Id>
    ##     <Status>Completed</Status>
    ##   </InvalidationSummary>
    ##   <InvalidationSummary>
    ##     <Id>[First Invalidation ID]</Id>
    ##     <Status>Completed</Status>
    ##   </InvalidationSummary>
    ## </InvalidationList>

    def __init__(self, xml):
        tree = getTreeFromXml(xml)
        if tree.tag != "InvalidationList":
            raise ValueError("Expected <InvalidationList /> xml, got: <%s />" % tree.tag)
        self.parse(tree)

    def parse(self, tree):
        self.info = getDictFromTree(tree)

    def __str__(self):
        return str(self.info)

class InvalidationBatch(object):
    ## Example:
    ##
    ## <InvalidationBatch>
    ##   <Path>/image1.jpg</Path>
    ##   <Path>/image2.jpg</Path>
    ##   <Path>/videos/movie.flv</Path>
    ##   <Path>/sound%20track.mp3</Path>
    ##   <CallerReference>my-batch</CallerReference>
    ## </InvalidationBatch>

    def __init__(self, reference = None, distribution = None, paths = []):
        if reference:
            self.reference = reference
        else:
            if not distribution:
                distribution="0"
            self.reference = "%s.%s.%s" % (distribution,
                datetime.strftime(datetime.now(),"%Y%m%d%H%M%S"),
                random.randint(1000,9999))
        self.paths = []
        self.add_objects(paths)

    def add_objects(self, paths):
        self.paths.extend(paths)

    def get_reference(self):
        return self.reference

    def __str__(self):
        tree = ET.Element("InvalidationBatch")
        s3 = S3(Config())

        for path in self.paths:
            if len(path) < 1 or path[0] != "/":
                path = "/" + path
            appendXmlTextNode("Path", s3.urlencode_string(path), tree)
        appendXmlTextNode("CallerReference", self.reference, tree)
        return ET.tostring(tree)

class CloudFront(object):
    operations = {
        "CreateDist" : { 'method' : "POST", 'resource' : "" },
        "DeleteDist" : { 'method' : "DELETE", 'resource' : "/%(dist_id)s" },
        "GetList" : { 'method' : "GET", 'resource' : "" },
        "GetDistInfo" : { 'method' : "GET", 'resource' : "/%(dist_id)s" },
        "GetDistConfig" : { 'method' : "GET", 'resource' : "/%(dist_id)s/config" },
        "SetDistConfig" : { 'method' : "PUT", 'resource' : "/%(dist_id)s/config" },
        "Invalidate" : { 'method' : "POST", 'resource' : "/%(dist_id)s/invalidation" },
        "GetInvalList" : { 'method' : "GET", 'resource' : "/%(dist_id)s/invalidation" },
        "GetInvalInfo" : { 'method' : "GET", 'resource' : "/%(dist_id)s/invalidation/%(request_id)s" },
    }

    ## Maximum attempts of re-issuing failed requests
    _max_retries = 5
    dist_list = None

    def __init__(self, config):
        self.config = config

    ## --------------------------------------------------
    ## Methods implementing CloudFront API
    ## --------------------------------------------------

    def GetList(self):
        response = self.send_request("GetList")
        response['dist_list'] = DistributionList(response['data'])
        if response['dist_list'].info['IsTruncated']:
            raise NotImplementedError("List is truncated. Ask s3cmd author to add support.")
        ## TODO: handle Truncated
        return response

    def CreateDistribution(self, uri, cnames_add = [], comment = None, logging = None, default_root_object = None):
        dist_config = DistributionConfig()
        dist_config.info['Enabled'] = True
        dist_config.info['S3Origin']['DNSName'] = uri.host_name()
        dist_config.info['CallerReference'] = str(uri)
        dist_config.info['DefaultRootObject'] = default_root_object
        if comment == None:
            dist_config.info['Comment'] = uri.public_url()
        else:
            dist_config.info['Comment'] = comment
        for cname in cnames_add:
            if dist_config.info['CNAME'].count(cname) == 0:
                dist_config.info['CNAME'].append(cname)
        if logging:
            dist_config.info['Logging'] = S3UriS3(logging)
        request_body = str(dist_config)
        debug("CreateDistribution(): request_body: %s" % request_body)
        response = self.send_request("CreateDist", body = request_body)
        response['distribution'] = Distribution(response['data'])
        return response

    def ModifyDistribution(self, cfuri, cnames_add = [], cnames_remove = [],
                           comment = None, enabled = None, logging = None,
                           default_root_object = None):
        if cfuri.type != "cf":
            raise ValueError("Expected CFUri instead of: %s" % cfuri)
        # Get current dist status (enabled/disabled) and Etag
        info("Checking current status of %s" % cfuri)
        response = self.GetDistConfig(cfuri)
        dc = response['dist_config']
        if enabled != None:
            dc.info['Enabled'] = enabled
        if comment != None:
            dc.info['Comment'] = comment
        if default_root_object != None:
            dc.info['DefaultRootObject'] = default_root_object
        for cname in cnames_add:
            if dc.info['CNAME'].count(cname) == 0:
                dc.info['CNAME'].append(cname)
        for cname in cnames_remove:
            while dc.info['CNAME'].count(cname) > 0:
                dc.info['CNAME'].remove(cname)
        if logging != None:
            if logging == False:
                dc.info['Logging'] = False
            else:
                dc.info['Logging'] = S3UriS3(logging)
        response = self.SetDistConfig(cfuri, dc, response['headers']['etag'])
        return response

    def DeleteDistribution(self, cfuri):
        if cfuri.type != "cf":
            raise ValueError("Expected CFUri instead of: %s" % cfuri)
        # Get current dist status (enabled/disabled) and Etag
        info("Checking current status of %s" % cfuri)
        response = self.GetDistConfig(cfuri)
        if response['dist_config'].info['Enabled']:
            info("Distribution is ENABLED. Disabling first.")
            response['dist_config'].info['Enabled'] = False
            response = self.SetDistConfig(cfuri, response['dist_config'],
                                          response['headers']['etag'])
            warning("Waiting for Distribution to become disabled.")
            warning("This may take several minutes, please wait.")
            while True:
                response = self.GetDistInfo(cfuri)
                d = response['distribution']
                if d.info['Status'] == "Deployed" and d.info['Enabled'] == False:
                    info("Distribution is now disabled")
                    break
                warning("Still waiting...")
                time.sleep(10)
        headers = {}
        headers['if-match'] = response['headers']['etag']
        response = self.send_request("DeleteDist", dist_id = cfuri.dist_id(),
                                     headers = headers)
        return response

    def GetDistInfo(self, cfuri):
        if cfuri.type != "cf":
            raise ValueError("Expected CFUri instead of: %s" % cfuri)
        response = self.send_request("GetDistInfo", dist_id = cfuri.dist_id())
        response['distribution'] = Distribution(response['data'])
        return response

    def GetDistConfig(self, cfuri):
        if cfuri.type != "cf":
            raise ValueError("Expected CFUri instead of: %s" % cfuri)
        response = self.send_request("GetDistConfig", dist_id = cfuri.dist_id())
        response['dist_config'] = DistributionConfig(response['data'])
        return response

    def SetDistConfig(self, cfuri, dist_config, etag = None):
        if etag == None:
            debug("SetDistConfig(): Etag not set. Fetching it first.")
            etag = self.GetDistConfig(cfuri)['headers']['etag']
        debug("SetDistConfig(): Etag = %s" % etag)
        request_body = str(dist_config)
        debug("SetDistConfig(): request_body: %s" % request_body)
        headers = {}
        headers['if-match'] = etag
        response = self.send_request("SetDistConfig", dist_id = cfuri.dist_id(),
                                     body = request_body, headers = headers)
        return response

    def InvalidateObjects(self, uri, paths, default_index_file, invalidate_default_index_on_cf, invalidate_default_index_root_on_cf):
        # joseprio: if the user doesn't want to invalidate the default index
        # path, or if the user wants to invalidate the root of the default
        # index, we need to process those paths
        if default_index_file is not None and (not invalidate_default_index_on_cf or invalidate_default_index_root_on_cf):
            new_paths = []
            default_index_suffix = '/' + default_index_file
            for path in paths:
                if path.endswith(default_index_suffix) or path == default_index_file:
                    if invalidate_default_index_on_cf:
                        new_paths.append(path)
                    if invalidate_default_index_root_on_cf:
                        new_paths.append(path[:-len(default_index_file)])
                else:
                    new_paths.append(path)
            paths = new_paths

        # uri could be either cf:// or s3:// uri
        cfuri = self.get_dist_name_for_bucket(uri)
        if len(paths) > 999:
            try:
                tmp_filename = Utils.mktmpfile()
                f = open(tmp_filename, "w")
                f.write("\n".join(paths)+"\n")
                f.close()
                warning("Request to invalidate %d paths (max 999 supported)" % len(paths))
                warning("All the paths are now saved in: %s" % tmp_filename)
            except:
                pass
            raise ParameterError("Too many paths to invalidate")
        invalbatch = InvalidationBatch(distribution = cfuri.dist_id(), paths = paths)
        debug("InvalidateObjects(): request_body: %s" % invalbatch)
        response = self.send_request("Invalidate", dist_id = cfuri.dist_id(),
                                     body = str(invalbatch))
        response['dist_id'] = cfuri.dist_id()
        if response['status'] == 201:
            inval_info = Invalidation(response['data']).info
            response['request_id'] = inval_info['Id']
        debug("InvalidateObjects(): response: %s" % response)
        return response

    def GetInvalList(self, cfuri):
        if cfuri.type != "cf":
            raise ValueError("Expected CFUri instead of: %s" % cfuri)
        response = self.send_request("GetInvalList", dist_id = cfuri.dist_id())
        response['inval_list'] = InvalidationList(response['data'])
        return response

    def GetInvalInfo(self, cfuri):
        if cfuri.type != "cf":
            raise ValueError("Expected CFUri instead of: %s" % cfuri)
        if cfuri.request_id() is None:
            raise ValueError("Expected CFUri with Request ID")
        response = self.send_request("GetInvalInfo", dist_id = cfuri.dist_id(), request_id = cfuri.request_id())
        response['inval_status'] = Invalidation(response['data'])
        return response

    ## --------------------------------------------------
    ## Low-level methods for handling CloudFront requests
    ## --------------------------------------------------

    def send_request(self, op_name, dist_id = None, request_id = None, body = None, headers = {}, retries = _max_retries):
        operation = self.operations[op_name]
        if body:
            headers['content-type'] = 'text/plain'
        request = self.create_request(operation, dist_id, request_id, headers)
        conn = self.get_connection()
        debug("send_request(): %s %s" % (request['method'], request['resource']))
        conn.request(request['method'], request['resource'], body, request['headers'])
        http_response = conn.getresponse()
        response = {}
        response["status"] = http_response.status
        response["reason"] = http_response.reason
        response["headers"] = dict(http_response.getheaders())
        response["data"] =  http_response.read()
        conn.close()

        debug("CloudFront: response: %r" % response)

        if response["status"] >= 500:
            e = CloudFrontError(response)
            if retries:
                warning(u"Retrying failed request: %s" % op_name)
                warning(unicode(e))
                warning("Waiting %d sec..." % self._fail_wait(retries))
                time.sleep(self._fail_wait(retries))
                return self.send_request(op_name, dist_id, body, retries = retries - 1)
            else:
                raise e

        if response["status"] < 200 or response["status"] > 299:
            raise CloudFrontError(response)

        return response

    def create_request(self, operation, dist_id = None, request_id = None, headers = None):
        resource = cloudfront_resource + (
                   operation['resource'] % { 'dist_id' : dist_id, 'request_id' : request_id })

        if not headers:
            headers = {}

        if headers.has_key("date"):
            if not headers.has_key("x-amz-date"):
                headers["x-amz-date"] = headers["date"]
            del(headers["date"])

        if not headers.has_key("x-amz-date"):
            headers["x-amz-date"] = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())

        if len(self.config.access_token)>0:
            self.config.role_refresh()
            headers['x-amz-security-token']=self.config.access_token

        signature = self.sign_request(headers)
        headers["Authorization"] = "AWS "+self.config.access_key+":"+signature

        request = {}
        request['resource'] = resource
        request['headers'] = headers
        request['method'] = operation['method']

        return request

    def sign_request(self, headers):
        string_to_sign = headers['x-amz-date']
        signature = sign_string(string_to_sign)
        debug(u"CloudFront.sign_request('%s') = %s" % (string_to_sign, signature))
        return signature

    def get_connection(self):
        if self.config.proxy_host != "":
            raise ParameterError("CloudFront commands don't work from behind a HTTP proxy")
        return httplib.HTTPSConnection(self.config.cloudfront_host)

    def _fail_wait(self, retries):
        # Wait a few seconds. The more it fails the more we wait.
        return (self._max_retries - retries + 1) * 3

    def get_dist_name_for_bucket(self, uri):
        if (uri.type == "cf"):
            return uri
        if (uri.type != "s3"):
            raise ParameterError("CloudFront or S3 URI required instead of: %s" % uri)

        debug("_get_dist_name_for_bucket(%r)" % uri)
        if CloudFront.dist_list is None:
            response = self.GetList()
            CloudFront.dist_list = {}
            for d in response['dist_list'].dist_summs:
                if d.info.has_key("S3Origin"):
                    CloudFront.dist_list[getBucketFromHostname(d.info['S3Origin']['DNSName'])[0]] = d.uri()
                elif d.info.has_key("CustomOrigin"):
                    # Aral: This used to skip over distributions with CustomOrigin, however, we mustn't
                    #       do this since S3 buckets that are set up as websites use custom origins.
                    #       Thankfully, the custom origin URLs they use start with the URL of the
                    #       S3 bucket. Here, we make use this naming convention to support this use case.
                    distListIndex = getBucketFromHostname(d.info['CustomOrigin']['DNSName'])[0];
                    distListIndex = distListIndex[:len(uri.bucket())]
                    CloudFront.dist_list[distListIndex] = d.uri()
                else:
                    # Aral: I'm not sure when this condition will be reached, but keeping it in there.
                    continue
            debug("dist_list: %s" % CloudFront.dist_list)
        try:
            return CloudFront.dist_list[uri.bucket()]
        except Exception, e:
            debug(e)
            raise ParameterError("Unable to translate S3 URI to CloudFront distribution name: %s" % uri)

class Cmd(object):
    """
    Class that implements CloudFront commands
    """

    class Options(object):
        cf_cnames_add = []
        cf_cnames_remove = []
        cf_comment = None
        cf_enable = None
        cf_logging = None
        cf_default_root_object = None

        def option_list(self):
            return [opt for opt in dir(self) if opt.startswith("cf_")]

        def update_option(self, option, value):
            setattr(Cmd.options, option, value)

    options = Options()

    @staticmethod
    def _parse_args(args):
        cf = CloudFront(Config())
        cfuris = []
        for arg in args:
            uri = cf.get_dist_name_for_bucket(S3Uri(arg))
            cfuris.append(uri)
        return cfuris

    @staticmethod
    def info(args):
        cf = CloudFront(Config())
        if not args:
            response = cf.GetList()
            for d in response['dist_list'].dist_summs:
                if d.info.has_key("S3Origin"):
                    origin = S3UriS3.httpurl_to_s3uri(d.info['S3Origin']['DNSName'])
                elif d.info.has_key("CustomOrigin"):
                    origin = "http://%s/" % d.info['CustomOrigin']['DNSName']
                else:
                    origin = "<unknown>"
                pretty_output("Origin", origin)
                pretty_output("DistId", d.uri())
                pretty_output("DomainName", d.info['DomainName'])
                if d.info.has_key("CNAME"):
                    pretty_output("CNAMEs", ", ".join(d.info['CNAME']))
                pretty_output("Status", d.info['Status'])
                pretty_output("Enabled", d.info['Enabled'])
                output("")
        else:
            cfuris = Cmd._parse_args(args)
            for cfuri in cfuris:
                response = cf.GetDistInfo(cfuri)
                d = response['distribution']
                dc = d.info['DistributionConfig']
                if dc.info.has_key("S3Origin"):
                    origin = S3UriS3.httpurl_to_s3uri(dc.info['S3Origin']['DNSName'])
                elif dc.info.has_key("CustomOrigin"):
                    origin = "http://%s/" % dc.info['CustomOrigin']['DNSName']
                else:
                    origin = "<unknown>"
                pretty_output("Origin", origin)
                pretty_output("DistId", d.uri())
                pretty_output("DomainName", d.info['DomainName'])
                if dc.info.has_key("CNAME"):
                    pretty_output("CNAMEs", ", ".join(dc.info['CNAME']))
                pretty_output("Status", d.info['Status'])
                pretty_output("Comment", dc.info['Comment'])
                pretty_output("Enabled", dc.info['Enabled'])
                pretty_output("DfltRootObject", dc.info['DefaultRootObject'])
                pretty_output("Logging", dc.info['Logging'] or "Disabled")
                pretty_output("Etag", response['headers']['etag'])

    @staticmethod
    def create(args):
        cf = CloudFront(Config())
        buckets = []
        for arg in args:
            uri = S3Uri(arg)
            if uri.type != "s3":
                raise ParameterError("Distribution can only be created from a s3:// URI instead of: %s" % arg)
            if uri.object():
                raise ParameterError("Use s3:// URI with a bucket name only instead of: %s" % arg)
            if not uri.is_dns_compatible():
                raise ParameterError("CloudFront can only handle lowercase-named buckets.")
            buckets.append(uri)
        if not buckets:
            raise ParameterError("No valid bucket names found")
        for uri in buckets:
            info("Creating distribution from: %s" % uri)
            response = cf.CreateDistribution(uri, cnames_add = Cmd.options.cf_cnames_add,
                                             comment = Cmd.options.cf_comment,
                                             logging = Cmd.options.cf_logging,
                                             default_root_object = Cmd.options.cf_default_root_object)
            d = response['distribution']
            dc = d.info['DistributionConfig']
            output("Distribution created:")
            pretty_output("Origin", S3UriS3.httpurl_to_s3uri(dc.info['S3Origin']['DNSName']))
            pretty_output("DistId", d.uri())
            pretty_output("DomainName", d.info['DomainName'])
            pretty_output("CNAMEs", ", ".join(dc.info['CNAME']))
            pretty_output("Comment", dc.info['Comment'])
            pretty_output("Status", d.info['Status'])
            pretty_output("Enabled", dc.info['Enabled'])
            pretty_output("DefaultRootObject", dc.info['DefaultRootObject'])
            pretty_output("Etag", response['headers']['etag'])

    @staticmethod
    def delete(args):
        cf = CloudFront(Config())
        cfuris = Cmd._parse_args(args)
        for cfuri in cfuris:
            response = cf.DeleteDistribution(cfuri)
            if response['status'] >= 400:
                error("Distribution %s could not be deleted: %s" % (cfuri, response['reason']))
            output("Distribution %s deleted" % cfuri)

    @staticmethod
    def modify(args):
        cf = CloudFront(Config())
        if len(args) > 1:
            raise ParameterError("Too many parameters. Modify one Distribution at a time.")
        try:
            cfuri = Cmd._parse_args(args)[0]
        except IndexError, e:
            raise ParameterError("No valid Distribution URI found.")
        response = cf.ModifyDistribution(cfuri,
                                         cnames_add = Cmd.options.cf_cnames_add,
                                         cnames_remove = Cmd.options.cf_cnames_remove,
                                         comment = Cmd.options.cf_comment,
                                         enabled = Cmd.options.cf_enable,
                                         logging = Cmd.options.cf_logging,
                                         default_root_object = Cmd.options.cf_default_root_object)
        if response['status'] >= 400:
            error("Distribution %s could not be modified: %s" % (cfuri, response['reason']))
        output("Distribution modified: %s" % cfuri)
        response = cf.GetDistInfo(cfuri)
        d = response['distribution']
        dc = d.info['DistributionConfig']
        pretty_output("Origin", S3UriS3.httpurl_to_s3uri(dc.info['S3Origin']['DNSName']))
        pretty_output("DistId", d.uri())
        pretty_output("DomainName", d.info['DomainName'])
        pretty_output("Status", d.info['Status'])
        pretty_output("CNAMEs", ", ".join(dc.info['CNAME']))
        pretty_output("Comment", dc.info['Comment'])
        pretty_output("Enabled", dc.info['Enabled'])
        pretty_output("DefaultRootObject", dc.info['DefaultRootObject'])
        pretty_output("Etag", response['headers']['etag'])

    @staticmethod
    def invalinfo(args):
        cf = CloudFront(Config())
        cfuris = Cmd._parse_args(args)
        requests = []
        for cfuri in cfuris:
            if cfuri.request_id():
                requests.append(str(cfuri))
            else:
                inval_list = cf.GetInvalList(cfuri)
                try:
                    for i in inval_list['inval_list'].info['InvalidationSummary']:
                        requests.append("/".join(["cf:/", cfuri.dist_id(), i["Id"]]))
                except:
                    continue
        for req in requests:
            cfuri = S3Uri(req)
            inval_info = cf.GetInvalInfo(cfuri)
            st = inval_info['inval_status'].info
            pretty_output("URI", str(cfuri))
            pretty_output("Status", st['Status'])
            pretty_output("Created", st['CreateTime'])
            pretty_output("Nr of paths", len(st['InvalidationBatch']['Path']))
            pretty_output("Reference", st['InvalidationBatch']['CallerReference'])
            output("")

# vim:et:ts=4:sts=4:ai

########NEW FILE########
__FILENAME__ = Config
## Amazon S3 manager
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2
## Copyright: TGRMN Software and contributors

import logging
from logging import debug, info, warning, error
import re
import os
import sys
import Progress
from SortedDict import SortedDict
import httplib
try:
    import json
except ImportError, e:
    pass

class Config(object):
    _instance = None
    _parsed_files = []
    _doc = {}
    access_key = ""
    secret_key = ""
    access_token = ""
    host_base = "s3.amazonaws.com"
    host_bucket = "%(bucket)s.s3.amazonaws.com"
    simpledb_host = "sdb.amazonaws.com"
    cloudfront_host = "cloudfront.amazonaws.com"
    verbosity = logging.WARNING
    progress_meter = True
    progress_class = Progress.ProgressCR
    send_chunk = 4096
    recv_chunk = 4096
    list_md5 = False
    human_readable_sizes = False
    extra_headers = SortedDict(ignore_case = True)
    force = False
    server_side_encryption = False
    enable = None
    get_continue = False
    put_continue = False
    upload_id = None
    skip_existing = False
    recursive = False
    restore_days = 1
    acl_public = None
    acl_grants = []
    acl_revokes = []
    proxy_host = ""
    proxy_port = 3128
    encrypt = False
    dry_run = False
    add_encoding_exts = ""
    preserve_attrs = True
    preserve_attrs_list = [
        'uname',    # Verbose owner Name (e.g. 'root')
        'uid',      # Numeric user ID (e.g. 0)
        'gname',    # Group name (e.g. 'users')
        'gid',      # Numeric group ID (e.g. 100)
        'atime',    # Last access timestamp
        'mtime',    # Modification timestamp
        'ctime',    # Creation timestamp
        'mode',     # File mode (e.g. rwxr-xr-x = 755)
        'md5',      # File MD5 (if known)
        #'acl',     # Full ACL (not yet supported)
    ]
    delete_removed = False
    delete_after = False
    delete_after_fetch = False
    max_delete = -1
    _doc['delete_removed'] = "[sync] Remove remote S3 objects when local file has been deleted"
    delay_updates = False
    gpg_passphrase = ""
    gpg_command = ""
    gpg_encrypt = "%(gpg_command)s -c --verbose --no-use-agent --batch --yes --passphrase-fd %(passphrase_fd)s -o %(output_file)s %(input_file)s"
    gpg_decrypt = "%(gpg_command)s -d --verbose --no-use-agent --batch --yes --passphrase-fd %(passphrase_fd)s -o %(output_file)s %(input_file)s"
    use_https = False
    bucket_location = "US"
    default_mime_type = "binary/octet-stream"
    guess_mime_type = True
    use_mime_magic = True
    mime_type = ""
    enable_multipart = True
    multipart_chunk_size_mb = 15    # MB
    # List of checks to be performed for 'sync'
    sync_checks = ['size', 'md5']   # 'weak-timestamp'
    # List of compiled REGEXPs
    exclude = []
    include = []
    # Dict mapping compiled REGEXPs back to their textual form
    debug_exclude = {}
    debug_include = {}
    encoding = "utf-8"
    urlencoding_mode = "normal"
    log_target_prefix = ""
    reduced_redundancy = False
    follow_symlinks = False
    socket_timeout = 300
    invalidate_on_cf = False
    # joseprio: new flags for default index invalidation
    invalidate_default_index_on_cf = False
    invalidate_default_index_root_on_cf = True
    website_index = "index.html"
    website_error = ""
    website_endpoint = "http://%(bucket)s.s3-website-%(location)s.amazonaws.com/"
    additional_destinations = []
    files_from = []
    cache_file = ""
    add_headers = ""
    ignore_failed_copy = False
    expiry_days = ""
    expiry_date = ""
    expiry_prefix = ""

    ## Creating a singleton
    def __new__(self, configfile = None, access_key=None, secret_key=None):
        if self._instance is None:
            self._instance = object.__new__(self)
        return self._instance

    def __init__(self, configfile = None, access_key=None, secret_key=None):
        if configfile:
            try:
                self.read_config_file(configfile)
            except IOError, e:
                if 'AWS_CREDENTIAL_FILE' in os.environ:
                    self.env_config()

            # override these if passed on the command-line
            if access_key and secret_key:
                self.access_key = access_key
                self.secret_key = secret_key

            if len(self.access_key)==0:
                self.role_config()

    def role_config(self):
        if sys.version_info[0] * 10 + sys.version_info[1] < 26:
            error("IAM authentication requires Python 2.6 or newer")
            raise
        if not 'json' in sys.modules:
            error("IAM authentication not available -- missing module json")
            raise
        try:
            conn = httplib.HTTPConnection(host='169.254.169.254', timeout = 2)
            conn.request('GET', "/latest/meta-data/iam/security-credentials/")
            resp = conn.getresponse()
            files = resp.read()
            if resp.status == 200 and len(files)>1:
                conn.request('GET', "/latest/meta-data/iam/security-credentials/%s"%files)
                resp=conn.getresponse()
                if resp.status == 200:
                    creds=json.load(resp)
                    Config().update_option('access_key', creds['AccessKeyId'].encode('ascii'))
                    Config().update_option('secret_key', creds['SecretAccessKey'].encode('ascii'))
                    Config().update_option('access_token', creds['Token'].encode('ascii'))
                else:
                    raise IOError
            else:
                raise IOError
        except:
            raise

    def role_refresh(self):
        try:
            self.role_config()
        except:
            warning("Could not refresh role")

    def env_config(self):
        cred_content = ""
        try:
            cred_file = open(os.environ['AWS_CREDENTIAL_FILE'],'r')
            cred_content = cred_file.read()
        except IOError, e:
            debug("Error %d accessing credentials file %s" % (e.errno,os.environ['AWS_CREDENTIAL_FILE']))
        r_data = re.compile("^\s*(?P<orig_key>\w+)\s*=\s*(?P<value>.*)")
        r_quotes = re.compile("^\"(.*)\"\s*$")
        if len(cred_content)>0:
            for line in cred_content.splitlines():
                is_data = r_data.match(line)
                is_data = r_data.match(line)
                if is_data:
                    data = is_data.groupdict()
                    if r_quotes.match(data["value"]):
                        data["value"] = data["value"][1:-1]
                    if data["orig_key"]=="AWSAccessKeyId":
                        data["key"] = "access_key"
                    elif data["orig_key"]=="AWSSecretKey":
                        data["key"] = "secret_key"
                    else:
                        del data["key"]
                    if "key" in data:
                        Config().update_option(data["key"], data["value"])
                        if data["key"] in ("access_key", "secret_key", "gpg_passphrase"):
                            print_value = ("%s...%d_chars...%s") % (data["value"][:2], len(data["value"]) - 3, data["value"][-1:])
                        else:
                            print_value = data["value"]
                        debug("env_Config: %s->%s" % (data["key"], print_value))

    def option_list(self):
        retval = []
        for option in dir(self):
            ## Skip attributes that start with underscore or are not string, int or bool
            option_type = type(getattr(Config, option))
            if option.startswith("_") or \
               not (option_type in (
                    type("string"), # str
                        type(42),   # int
                    type(True))):   # bool
                continue
            retval.append(option)
        return retval

    def read_config_file(self, configfile):
        cp = ConfigParser(configfile)
        for option in self.option_list():
            self.update_option(option, cp.get(option))

        if cp.get('add_headers'):
            for option in cp.get('add_headers').split(","):
                (key, value) = option.split(':')
                self.extra_headers[key.replace('_', '-').strip()] = value.strip()

        self._parsed_files.append(configfile)

    def dump_config(self, stream):
        ConfigDumper(stream).dump("default", self)

    def update_option(self, option, value):
        if value is None:
            return

        #### Handle environment reference
        if str(value).startswith("$"):
            return self.update_option(option, os.getenv(str(value)[1:]))

        #### Special treatment of some options
        ## verbosity must be known to "logging" module
        if option == "verbosity":
            # support integer verboisities
            try:
                value = int(value)
            except ValueError, e:
                try:
                    # otherwise it must be a key known to the logging module
                    value = logging._levelNames[value]
                except KeyError:
                    error("Config: verbosity level '%s' is not valid" % value)
                    return

        ## allow yes/no, true/false, on/off and 1/0 for boolean options
        elif type(getattr(Config, option)) is type(True):   # bool
            if str(value).lower() in ("true", "yes", "on", "1"):
                value = True
            elif str(value).lower() in ("false", "no", "off", "0"):
                value = False
            else:
                error("Config: value of option '%s' must be Yes or No, not '%s'" % (option, value))
                return

        elif type(getattr(Config, option)) is type(42):     # int
            try:
                value = int(value)
            except ValueError, e:
                error("Config: value of option '%s' must be an integer, not '%s'" % (option, value))
                return

        setattr(Config, option, value)

class ConfigParser(object):
    def __init__(self, file, sections = []):
        self.cfg = {}
        self.parse_file(file, sections)

    def parse_file(self, file, sections = []):
        debug("ConfigParser: Reading file '%s'" % file)
        if type(sections) != type([]):
            sections = [sections]
        in_our_section = True
        f = open(file, "r")
        r_comment = re.compile("^\s*#.*")
        r_empty = re.compile("^\s*$")
        r_section = re.compile("^\[([^\]]+)\]")
        r_data = re.compile("^\s*(?P<key>\w+)\s*=\s*(?P<value>.*)")
        r_quotes = re.compile("^\"(.*)\"\s*$")
        for line in f:
            if r_comment.match(line) or r_empty.match(line):
                continue
            is_section = r_section.match(line)
            if is_section:
                section = is_section.groups()[0]
                in_our_section = (section in sections) or (len(sections) == 0)
                continue
            is_data = r_data.match(line)
            if is_data and in_our_section:
                data = is_data.groupdict()
                if r_quotes.match(data["value"]):
                    data["value"] = data["value"][1:-1]
                self.__setitem__(data["key"], data["value"])
                if data["key"] in ("access_key", "secret_key", "gpg_passphrase"):
                    print_value = ("%s...%d_chars...%s") % (data["value"][:2], len(data["value"]) - 3, data["value"][-1:])
                else:
                    print_value = data["value"]
                debug("ConfigParser: %s->%s" % (data["key"], print_value))
                continue
            warning("Ignoring invalid line in '%s': %s" % (file, line))

    def __getitem__(self, name):
        return self.cfg[name]

    def __setitem__(self, name, value):
        self.cfg[name] = value

    def get(self, name, default = None):
        if self.cfg.has_key(name):
            return self.cfg[name]
        return default

class ConfigDumper(object):
    def __init__(self, stream):
        self.stream = stream

    def dump(self, section, config):
        self.stream.write("[%s]\n" % section)
        for option in config.option_list():
            value = getattr(config, option)
            if option == "verbosity":
                # we turn level numbers back into strings if possible
                if isinstance(value,int) and value in logging._levelNames:
                    value = logging._levelNames[value]

            self.stream.write("%s = %s\n" % (option, value))

# vim:et:ts=4:sts=4:ai

########NEW FILE########
__FILENAME__ = ConnMan
## Amazon S3 manager
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2
## Copyright: TGRMN Software and contributors

import httplib
from urlparse import urlparse
from threading import Semaphore
from logging import debug, info, warning, error

from Config import Config
from Exceptions import ParameterError

__all__ = [ "ConnMan" ]

class http_connection(object):
    def __init__(self, id, hostname, ssl, cfg):
        self.hostname = hostname
        self.ssl = ssl
        self.id = id
        self.counter = 0
        if cfg.proxy_host != "":
            self.c = httplib.HTTPConnection(cfg.proxy_host, cfg.proxy_port)
        elif not ssl:
            self.c = httplib.HTTPConnection(hostname)
        else:
            self.c = httplib.HTTPSConnection(hostname)

class ConnMan(object):
    conn_pool_sem = Semaphore()
    conn_pool = {}
    conn_max_counter = 800    ## AWS closes connection after some ~90 requests

    @staticmethod
    def get(hostname, ssl = None):
        cfg = Config()
        if ssl == None:
            ssl = cfg.use_https
        conn = None
        if cfg.proxy_host != "":
            if ssl:
                raise ParameterError("use_https=True can't be used with proxy")
            conn_id = "proxy://%s:%s" % (cfg.proxy_host, cfg.proxy_port)
        else:
            conn_id = "http%s://%s" % (ssl and "s" or "", hostname)
        ConnMan.conn_pool_sem.acquire()
        if not ConnMan.conn_pool.has_key(conn_id):
            ConnMan.conn_pool[conn_id] = []
        if len(ConnMan.conn_pool[conn_id]):
            conn = ConnMan.conn_pool[conn_id].pop()
            debug("ConnMan.get(): re-using connection: %s#%d" % (conn.id, conn.counter))
        ConnMan.conn_pool_sem.release()
        if not conn:
            debug("ConnMan.get(): creating new connection: %s" % conn_id)
            conn = http_connection(conn_id, hostname, ssl, cfg)
            conn.c.connect()
        conn.counter += 1
        return conn

    @staticmethod
    def put(conn):
        if conn.id.startswith("proxy://"):
            conn.c.close()
            debug("ConnMan.put(): closing proxy connection (keep-alive not yet supported)")
            return

        if conn.counter >= ConnMan.conn_max_counter:
            conn.c.close()
            debug("ConnMan.put(): closing over-used connection")
            return

        ConnMan.conn_pool_sem.acquire()
        ConnMan.conn_pool[conn.id].append(conn)
        ConnMan.conn_pool_sem.release()
        debug("ConnMan.put(): connection put back to pool (%s#%d)" % (conn.id, conn.counter))


########NEW FILE########
__FILENAME__ = Exceptions
## Amazon S3 manager - Exceptions library
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2
## Copyright: TGRMN Software and contributors

from Utils import getTreeFromXml, unicodise, deunicodise
from logging import debug, info, warning, error

try:
    import xml.etree.ElementTree as ET
except ImportError:
    import elementtree.ElementTree as ET

class S3Exception(Exception):
    def __init__(self, message = ""):
        self.message = unicodise(message)

    def __str__(self):
        ## Call unicode(self) instead of self.message because
        ## __unicode__() method could be overriden in subclasses!
        return deunicodise(unicode(self))

    def __unicode__(self):
        return self.message

    ## (Base)Exception.message has been deprecated in Python 2.6
    def _get_message(self):
        return self._message
    def _set_message(self, message):
        self._message = message
    message = property(_get_message, _set_message)


class S3Error (S3Exception):
    def __init__(self, response):
        self.status = response["status"]
        self.reason = response["reason"]
        self.info = {
            "Code" : "",
            "Message" : "",
            "Resource" : ""
        }
        debug("S3Error: %s (%s)" % (self.status, self.reason))
        if response.has_key("headers"):
            for header in response["headers"]:
                debug("HttpHeader: %s: %s" % (header, response["headers"][header]))
        if response.has_key("data") and response["data"]:
            try:
                tree = getTreeFromXml(response["data"])
            except ET.ParseError:
                debug("Not an XML response")
            else:
                self.info.update(self.parse_error_xml(tree))

        self.code = self.info["Code"]
        self.message = self.info["Message"]
        self.resource = self.info["Resource"]

    def __unicode__(self):
        retval = u"%d " % (self.status)
        retval += (u"(%s)" % (self.info.has_key("Code") and self.info["Code"] or self.reason))
        if self.info.has_key("Message"):
            retval += (u": %s" % self.info["Message"])
        return retval

    @staticmethod
    def parse_error_xml(tree):
        info = {}
        error_node = tree
        if not error_node.tag == "Error":
            error_node = tree.find(".//Error")
        for child in error_node.getchildren():
            if child.text != "":
                debug("ErrorXML: " + child.tag + ": " + repr(child.text))
                info[child.tag] = child.text

        return info


class CloudFrontError(S3Error):
    pass

class S3UploadError(S3Exception):
    pass

class S3DownloadError(S3Exception):
    pass

class S3RequestError(S3Exception):
    pass

class S3ResponseError(S3Exception):
    pass

class InvalidFileError(S3Exception):
    pass

class ParameterError(S3Exception):
    pass

# vim:et:ts=4:sts=4:ai

########NEW FILE########
__FILENAME__ = ExitCodes
# patterned on /usr/include/sysexits.h

EX_OK         = 0
EX_GENERAL    = 1
EX_SOMEFAILED = 2    # some parts of the command succeeded, while others failed
EX_USAGE      = 64   # The command was used incorrectly (e.g. bad command line syntax)
EX_SOFTWARE   = 70   # internal software error (e.g. S3 error of unknown specificity)
EX_OSERR      = 71   # system error (e.g. out of memory)
EX_OSFILE     = 72   # OS error (e.g. invalid Python version)
EX_IOERR      = 74   # An error occurred while doing I/O on some file.
EX_TEMPFAIL   = 75   # temporary failure (S3DownloadError or similar, retry later)
EX_NOPERM     = 77   # Insufficient permissions to perform the operation on S3  
EX_CONFIG     = 78   # Configuration file error
_EX_SIGNAL    = 128
_EX_SIGINT    = 2
EX_BREAK      = _EX_SIGNAL + _EX_SIGINT # Control-C (KeyboardInterrupt raised)

########NEW FILE########
__FILENAME__ = FileDict
## Amazon S3 manager
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2
## Copyright: TGRMN Software and contributors

import logging
from SortedDict import SortedDict
import Utils
import Config

zero_length_md5 = "d41d8cd98f00b204e9800998ecf8427e"
cfg = Config.Config()

class FileDict(SortedDict):
    def __init__(self, mapping = {}, ignore_case = True, **kwargs):
        SortedDict.__init__(self, mapping = mapping, ignore_case = ignore_case, **kwargs)
        self.hardlinks = dict() # { dev: { inode : {'md5':, 'relative_files':}}}
        self.by_md5 = dict() # {md5: set(relative_files)}

    def record_md5(self, relative_file, md5):
        if md5 is None: return
        if md5 == zero_length_md5: return
        if md5 not in self.by_md5:
            self.by_md5[md5] = set()
        self.by_md5[md5].add(relative_file)

    def find_md5_one(self, md5):
        if md5 is None: return None
        try:
            return list(self.by_md5.get(md5, set()))[0]
        except:
            return None

    def get_md5(self, relative_file):
        """returns md5 if it can, or raises IOError if file is unreadable"""
        md5 = None
        if 'md5' in self[relative_file]:
            return self[relative_file]['md5']
        md5 = self.get_hardlink_md5(relative_file)
        if md5 is None and 'md5' in cfg.sync_checks:
            logging.debug(u"doing file I/O to read md5 of %s" % relative_file)
            md5 = Utils.hash_file_md5(self[relative_file]['full_name'])
        self.record_md5(relative_file, md5)
        self[relative_file]['md5'] = md5
        return md5

    def record_hardlink(self, relative_file, dev, inode, md5, size):
        if md5 is None: return
        if size == 0: return # don't record 0-length files
        if dev == 0 or inode == 0: return # Windows
        if dev not in self.hardlinks:
            self.hardlinks[dev] = dict()
        if inode not in self.hardlinks[dev]:
            self.hardlinks[dev][inode] = dict(md5=md5, relative_files=set())
        self.hardlinks[dev][inode]['relative_files'].add(relative_file)

    def get_hardlink_md5(self, relative_file):
        md5 = None
        try:
            dev = self[relative_file]['dev']
            inode = self[relative_file]['inode']
            md5 = self.hardlinks[dev][inode]['md5']
        except KeyError:
            pass
        return md5

########NEW FILE########
__FILENAME__ = FileLists
## Create and compare lists of files/objects
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2
## Copyright: TGRMN Software and contributors

from S3 import S3
from Config import Config
from S3Uri import S3Uri
from FileDict import FileDict
from Utils import *
from Exceptions import ParameterError
from HashCache import HashCache

from logging import debug, info, warning, error

import os
import sys
import glob
import copy
import re
import errno

__all__ = ["fetch_local_list", "fetch_remote_list", "compare_filelists"]

def _fswalk_follow_symlinks(path):
    '''
    Walk filesystem, following symbolic links (but without recursion), on python2.4 and later

    If a symlink directory loop is detected, emit a warning and skip.
    E.g.: dir1/dir2/sym-dir -> ../dir2
    '''
    assert os.path.isdir(path) # only designed for directory argument
    walkdirs = set([path])
    for dirpath, dirnames, filenames in os.walk(path):
        handle_exclude_include_walk(dirpath, dirnames, [])
        real_dirpath = os.path.realpath(dirpath)
        for dirname in dirnames:
            current = os.path.join(dirpath, dirname)
            real_current = os.path.realpath(current)
            if os.path.islink(current):
                if (real_dirpath == real_current or
                    real_dirpath.startswith(real_current + os.path.sep)):
                    warning("Skipping recursively symlinked directory %s" % dirname)
                else:
                    walkdirs.add(current)
    for walkdir in walkdirs:
        for dirpath, dirnames, filenames in os.walk(walkdir):
            handle_exclude_include_walk(dirpath, dirnames, [])
            yield (dirpath, dirnames, filenames)

def _fswalk_no_symlinks(path):
    '''
    Directory tree generator

    path (str) is the root of the directory tree to walk
    '''
    for dirpath, dirnames, filenames in os.walk(path):
        handle_exclude_include_walk(dirpath, dirnames, filenames)
        yield (dirpath, dirnames, filenames)

def filter_exclude_include(src_list):
    debug(u"Applying --exclude/--include")
    cfg = Config()
    exclude_list = FileDict(ignore_case = False)
    for file in src_list.keys():
        debug(u"CHECK: %s" % file)
        excluded = False
        for r in cfg.exclude:
            if r.search(file):
                excluded = True
                debug(u"EXCL-MATCH: '%s'" % (cfg.debug_exclude[r]))
                break
        if excluded:
            ## No need to check for --include if not excluded
            for r in cfg.include:
                if r.search(file):
                    excluded = False
                    debug(u"INCL-MATCH: '%s'" % (cfg.debug_include[r]))
                    break
        if excluded:
            ## Still excluded - ok, action it
            debug(u"EXCLUDE: %s" % file)
            exclude_list[file] = src_list[file]
            del(src_list[file])
            continue
        else:
            debug(u"PASS: %r" % (file))
    return src_list, exclude_list

def handle_exclude_include_walk(root, dirs, files):
    cfg = Config()
    copydirs = copy.copy(dirs)
    # exclude dir matches in the current directory
    # this prevents us from recursing down trees we know we want to ignore
    for x in copydirs:
        d = os.path.join(root, x, '')
        debug(u"CHECK: %r" % d)
        excluded = False
        for r in cfg.exclude:
            if not r.pattern.endswith(u'/'): continue # we only check for directories here
            if r.search(d):
                excluded = True
                debug(u"EXCL-MATCH: '%s'" % (cfg.debug_exclude[r]))
                break
        if excluded:
            ## No need to check for --include if not excluded
            for r in cfg.include:
                if not r.pattern.endswith(u'/'): continue # we only check for directories here
                debug(u"INCL-TEST: %s ~ %s" % (d, r.pattern))
                if r.search(d):
                    excluded = False
                    debug(u"INCL-MATCH: '%s'" % (cfg.debug_include[r]))
                    break
        if excluded:
            ## Still excluded - ok, action it
            debug(u"EXCLUDE: %r" % d)
            dirs.remove(x)
            continue
        else:
            debug(u"PASS: %r" % (d))


def _get_filelist_from_file(cfg, local_path):
    def _append(d, key, value):
        if key not in d:
            d[key] = [value]
        else:
            d[key].append(value)

    filelist = {}
    for fname in cfg.files_from:
        if fname == u'-':
            f = sys.stdin
        else:
            try:
                f = open(fname, 'r')
            except IOError, e:
                warning(u"--files-from input file %s could not be opened for reading (%s), skipping." % (fname, e.strerror))
                continue

        for line in f:
            line = line.strip()
            line = os.path.normpath(os.path.join(local_path, line))
            dirname = os.path.dirname(line)
            basename = os.path.basename(line)
            _append(filelist, dirname, basename)
        if f != sys.stdin:
            f.close()

    # reformat to match os.walk()
    result = []
    keys = filelist.keys()
    keys.sort()
    for key in keys:
        values = filelist[key]
        values.sort()
        result.append((key, [], values))
    return result

def fetch_local_list(args, is_src = False, recursive = None):

    def _fetch_local_list_info(loc_list):
        len_loc_list = len(loc_list)
        info(u"Running stat() and reading/calculating MD5 values on %d files, this may take some time..." % len_loc_list)
        counter = 0
        for relative_file in loc_list:
            counter += 1
            if counter % 1000 == 0:
                info(u"[%d/%d]" % (counter, len_loc_list))

            if relative_file == '-': continue

            full_name = loc_list[relative_file]['full_name']
            try:
                sr = os.stat_result(os.stat(full_name))
            except OSError, e:
                if e.errno == errno.ENOENT:
                    # file was removed async to us getting the list
                    continue
                else:
                    raise
            loc_list[relative_file].update({
                'size' : sr.st_size,
                'mtime' : sr.st_mtime,
                'dev'   : sr.st_dev,
                'inode' : sr.st_ino,
                'uid' : sr.st_uid,
                'gid' : sr.st_gid,
                'sr': sr # save it all, may need it in preserve_attrs_list
                ## TODO: Possibly more to save here...
            })
            if 'md5' in cfg.sync_checks:
                md5 = cache.md5(sr.st_dev, sr.st_ino, sr.st_mtime, sr.st_size)
                if md5 is None:
                        try:
                            md5 = loc_list.get_md5(relative_file) # this does the file I/O
                        except IOError:
                            continue
                        cache.add(sr.st_dev, sr.st_ino, sr.st_mtime, sr.st_size, md5)
                loc_list.record_hardlink(relative_file, sr.st_dev, sr.st_ino, md5, sr.st_size)


    def _get_filelist_local(loc_list, local_uri, cache):
        info(u"Compiling list of local files...")

        if deunicodise(local_uri.basename()) == "-":
            try:
                uid = os.geteuid()
                gid = os.getegid()
            except:
                uid = 0
                gid = 0
            loc_list["-"] = {
                'full_name_unicode' : '-',
                'full_name' : '-',
                'size' : -1,
                'mtime' : -1,
                'uid' : uid,
                'gid' : gid,
                'dev' : 0,
                'inode': 0,
            }
            return loc_list, True
        if local_uri.isdir():
            local_base = deunicodise(local_uri.basename())
            local_path = deunicodise(local_uri.path())
            if is_src and len(cfg.files_from):
                filelist = _get_filelist_from_file(cfg, local_path)
                single_file = False
            else:
                if cfg.follow_symlinks:
                    filelist = _fswalk_follow_symlinks(local_path)
                else:
                    filelist = _fswalk_no_symlinks(local_path)
                single_file = False
        else:
            local_base = ""
            local_path = deunicodise(local_uri.dirname())
            filelist = [( local_path, [], [deunicodise(local_uri.basename())] )]
            single_file = True
        for root, dirs, files in filelist:
            rel_root = root.replace(local_path, local_base, 1)
            for f in files:
                full_name = os.path.join(root, f)
                if not os.path.isfile(full_name):
                    continue
                if os.path.islink(full_name):
                                    if not cfg.follow_symlinks:
                                            continue
                relative_file = unicodise(os.path.join(rel_root, f))
                if os.path.sep != "/":
                    # Convert non-unix dir separators to '/'
                    relative_file = "/".join(relative_file.split(os.path.sep))
                if cfg.urlencoding_mode == "normal":
                    relative_file = replace_nonprintables(relative_file)
                if relative_file.startswith('./'):
                    relative_file = relative_file[2:]
                loc_list[relative_file] = {
                    'full_name_unicode' : unicodise(full_name),
                    'full_name' : full_name,
                }

        return loc_list, single_file

    def _maintain_cache(cache, local_list):
        # if getting the file list from files_from, it is going to be
        # a subset of the actual tree.  We should not purge content
        # outside of that subset as we don't know if it's valid or
        # not.  Leave it to a non-files_from run to purge.
        if cfg.cache_file and len(cfg.files_from) == 0:
            cache.mark_all_for_purge()
            for i in local_list.keys():
                cache.unmark_for_purge(local_list[i]['dev'], local_list[i]['inode'], local_list[i]['mtime'], local_list[i]['size'])
            cache.purge()
            cache.save(cfg.cache_file)

    cfg = Config()

    cache = HashCache()
    if cfg.cache_file:
        try:
            cache.load(cfg.cache_file)
        except IOError:
            info(u"No cache file found, creating it.")

    local_uris = []
    local_list = FileDict(ignore_case = False)
    single_file = False

    if type(args) not in (list, tuple):
        args = [args]

    if recursive == None:
        recursive = cfg.recursive

    for arg in args:
        uri = S3Uri(arg)
        if not uri.type == 'file':
            raise ParameterError("Expecting filename or directory instead of: %s" % arg)
        if uri.isdir() and not recursive:
            raise ParameterError("Use --recursive to upload a directory: %s" % arg)
        local_uris.append(uri)

    for uri in local_uris:
        list_for_uri, single_file = _get_filelist_local(local_list, uri, cache)

    ## Single file is True if and only if the user
    ## specified one local URI and that URI represents
    ## a FILE. Ie it is False if the URI was of a DIR
    ## and that dir contained only one FILE. That's not
    ## a case of single_file==True.
    if len(local_list) > 1:
        single_file = False

    local_list, exclude_list = filter_exclude_include(local_list)
    _fetch_local_list_info(local_list)
    _maintain_cache(cache, local_list)
    return local_list, single_file, exclude_list

def fetch_remote_list(args, require_attribs = False, recursive = None, uri_params = {}):
    def _get_remote_attribs(uri, remote_item):
        response = S3(cfg).object_info(uri)
        remote_item.update({
        'size': int(response['headers']['content-length']),
        'md5': response['headers']['etag'].strip('"\''),
        'timestamp' : dateRFC822toUnix(response['headers']['date'])
        })
        try:
            md5 = response['s3cmd-attrs']['md5']
            remote_item.update({'md5': md5})
            debug(u"retreived md5=%s from headers" % md5)
        except KeyError:
            pass

    def _get_filelist_remote(remote_uri, recursive = True):
        ## If remote_uri ends with '/' then all remote files will have
        ## the remote_uri prefix removed in the relative path.
        ## If, on the other hand, the remote_uri ends with something else
        ## (probably alphanumeric symbol) we'll use the last path part
        ## in the relative path.
        ##
        ## Complicated, eh? See an example:
        ## _get_filelist_remote("s3://bckt/abc/def") may yield:
        ## { 'def/file1.jpg' : {}, 'def/xyz/blah.txt' : {} }
        ## _get_filelist_remote("s3://bckt/abc/def/") will yield:
        ## { 'file1.jpg' : {}, 'xyz/blah.txt' : {} }
        ## Furthermore a prefix-magic can restrict the return list:
        ## _get_filelist_remote("s3://bckt/abc/def/x") yields:
        ## { 'xyz/blah.txt' : {} }

        info(u"Retrieving list of remote files for %s ..." % remote_uri)
        empty_fname_re = re.compile(r'\A\s*\Z')

        s3 = S3(Config())
        response = s3.bucket_list(remote_uri.bucket(), prefix = remote_uri.object(),
                                  recursive = recursive, uri_params = uri_params)

        rem_base_original = rem_base = remote_uri.object()
        remote_uri_original = remote_uri
        if rem_base != '' and rem_base[-1] != '/':
            rem_base = rem_base[:rem_base.rfind('/')+1]
            remote_uri = S3Uri("s3://%s/%s" % (remote_uri.bucket(), rem_base))
        rem_base_len = len(rem_base)
        rem_list = FileDict(ignore_case = False)
        break_now = False
        for object in response['list']:
            if object['Key'] == rem_base_original and object['Key'][-1] != "/":
                ## We asked for one file and we got that file :-)
                key = os.path.basename(object['Key'])
                object_uri_str = remote_uri_original.uri()
                break_now = True
                rem_list = FileDict(ignore_case = False)   ## Remove whatever has already been put to rem_list
            else:
                key = object['Key'][rem_base_len:]      ## Beware - this may be '' if object['Key']==rem_base !!
                object_uri_str = remote_uri.uri() + key
            if empty_fname_re.match(key):
                # Objects may exist on S3 with empty names (''), which don't map so well to common filesystems.
                warning(u"Empty object name on S3 found, ignoring.")
                continue
            rem_list[key] = {
                'size' : int(object['Size']),
                'timestamp' : dateS3toUnix(object['LastModified']), ## Sadly it's upload time, not our lastmod time :-(
                'md5' : object['ETag'][1:-1],
                'object_key' : object['Key'],
                'object_uri_str' : object_uri_str,
                'base_uri' : remote_uri,
                'dev' : None,
                'inode' : None,
            }
            if rem_list[key]['md5'].find("-") > 0: # always get it for multipart uploads
                _get_remote_attribs(S3Uri(object_uri_str), rem_list[key])
            md5 = rem_list[key]['md5']
            rem_list.record_md5(key, md5)
            if break_now:
                break
        return rem_list

    cfg = Config()
    remote_uris = []
    remote_list = FileDict(ignore_case = False)

    if type(args) not in (list, tuple):
        args = [args]

    if recursive == None:
        recursive = cfg.recursive

    for arg in args:
        uri = S3Uri(arg)
        if not uri.type == 's3':
            raise ParameterError("Expecting S3 URI instead of '%s'" % arg)
        remote_uris.append(uri)

    if recursive:
        for uri in remote_uris:
            objectlist = _get_filelist_remote(uri, recursive = True)
            for key in objectlist:
                remote_list[key] = objectlist[key]
                remote_list.record_md5(key, objectlist.get_md5(key))
    else:
        for uri in remote_uris:
            uri_str = unicode(uri)
            ## Wildcards used in remote URI?
            ## If yes we'll need a bucket listing...
            wildcard_split_result = re.split("\*|\?", uri_str, maxsplit=1)
            if len(wildcard_split_result) == 2: # wildcards found
                prefix, rest = wildcard_split_result
                ## Only request recursive listing if the 'rest' of the URI,
                ## i.e. the part after first wildcard, contains '/'
                need_recursion = '/' in rest
                objectlist = _get_filelist_remote(S3Uri(prefix), recursive = need_recursion)
                for key in objectlist:
                    ## Check whether the 'key' matches the requested wildcards
                    if glob.fnmatch.fnmatch(objectlist[key]['object_uri_str'], uri_str):
                        remote_list[key] = objectlist[key]
            else:
                ## No wildcards - simply append the given URI to the list
                key = os.path.basename(uri.object())
                if not key:
                    raise ParameterError(u"Expecting S3 URI with a filename or --recursive: %s" % uri.uri())
                remote_item = {
                    'base_uri': uri,
                    'object_uri_str': unicode(uri),
                    'object_key': uri.object()
                }
                if require_attribs:
                    _get_remote_attribs(uri, remote_item)

                remote_list[key] = remote_item
                md5 = remote_item.get('md5')
                if md5:
                    remote_list.record_md5(key, md5)

    remote_list, exclude_list = filter_exclude_include(remote_list)
    return remote_list, exclude_list


def compare_filelists(src_list, dst_list, src_remote, dst_remote, delay_updates = False):
    def __direction_str(is_remote):
        return is_remote and "remote" or "local"

    def _compare(src_list, dst_lst, src_remote, dst_remote, file):
        """Return True if src_list[file] matches dst_list[file], else False"""
        attribs_match = True
        if not (src_list.has_key(file) and dst_list.has_key(file)):
            info(u"%s: does not exist in one side or the other: src_list=%s, dst_list=%s" % (file, src_list.has_key(file), dst_list.has_key(file)))
            return False

        ## check size first
        if 'size' in cfg.sync_checks and dst_list[file]['size'] != src_list[file]['size']:
            debug(u"xfer: %s (size mismatch: src=%s dst=%s)" % (file, src_list[file]['size'], dst_list[file]['size']))
            attribs_match = False

        ## check md5
        compare_md5 = 'md5' in cfg.sync_checks
        # Multipart-uploaded files don't have a valid md5 sum - it ends with "...-nn"
        if compare_md5:
            if (src_remote == True and src_list[file]['md5'].find("-") >= 0) or (dst_remote == True and dst_list[file]['md5'].find("-") >= 0):
                compare_md5 = False
                info(u"disabled md5 check for %s" % file)
        if attribs_match and compare_md5:
            try:
                src_md5 = src_list.get_md5(file)
                dst_md5 = dst_list.get_md5(file)
            except (IOError,OSError), e:
                # md5 sum verification failed - ignore that file altogether
                debug(u"IGNR: %s (disappeared)" % (file))
                warning(u"%s: file disappeared, ignoring." % (file))
                raise

            if src_md5 != dst_md5:
                ## checksums are different.
                attribs_match = False
                debug(u"XFER: %s (md5 mismatch: src=%s dst=%s)" % (file, src_md5, dst_md5))

        return attribs_match

    # we don't support local->local sync, use 'rsync' or something like that instead ;-)
    assert(not(src_remote == False and dst_remote == False))

    info(u"Verifying attributes...")
    cfg = Config()
    ## Items left on src_list will be transferred
    ## Items left on update_list will be transferred after src_list
    ## Items left on copy_pairs will be copied from dst1 to dst2
    update_list = FileDict(ignore_case = False)
    ## Items left on dst_list will be deleted
    copy_pairs = []

    debug("Comparing filelists (direction: %s -> %s)" % (__direction_str(src_remote), __direction_str(dst_remote)))

    for relative_file in src_list.keys():
        debug(u"CHECK: %s" % (relative_file))

        if dst_list.has_key(relative_file):
            ## Was --skip-existing requested?
            if cfg.skip_existing:
                debug(u"IGNR: %s (used --skip-existing)" % (relative_file))
                del(src_list[relative_file])
                del(dst_list[relative_file])
                continue

            try:
                same_file = _compare(src_list, dst_list, src_remote, dst_remote, relative_file)
            except (IOError,OSError), e:
                debug(u"IGNR: %s (disappeared)" % (relative_file))
                warning(u"%s: file disappeared, ignoring." % (relative_file))
                del(src_list[relative_file])
                del(dst_list[relative_file])
                continue

            if same_file:
                debug(u"IGNR: %s (transfer not needed)" % relative_file)
                del(src_list[relative_file])
                del(dst_list[relative_file])

            else:
                # look for matching file in src
                try:
                    md5 = src_list.get_md5(relative_file)
                except IOError:
                    md5 = None
                if md5 is not None and dst_list.by_md5.has_key(md5):
                    # Found one, we want to copy
                    dst1 = list(dst_list.by_md5[md5])[0]
                    debug(u"DST COPY src: %s -> %s" % (dst1, relative_file))
                    copy_pairs.append((src_list[relative_file], dst1, relative_file))
                    del(src_list[relative_file])
                    del(dst_list[relative_file])
                else:
                    # record that we will get this file transferred to us (before all the copies), so if we come across it later again,
                    # we can copy from _this_ copy (e.g. we only upload it once, and copy thereafter).
                    dst_list.record_md5(relative_file, md5)
                    update_list[relative_file] = src_list[relative_file]
                    del src_list[relative_file]
                    del dst_list[relative_file]

        else:
            # dst doesn't have this file
            # look for matching file elsewhere in dst
            try:
                md5 = src_list.get_md5(relative_file)
            except IOError:
               md5 = None
            dst1 = dst_list.find_md5_one(md5)
            if dst1 is not None:
                # Found one, we want to copy
                debug(u"DST COPY dst: %s -> %s" % (dst1, relative_file))
                copy_pairs.append((src_list[relative_file], dst1, relative_file))
                del(src_list[relative_file])
            else:
                # we don't have this file, and we don't have a copy of this file elsewhere.  Get it.
                # record that we will get this file transferred to us (before all the copies), so if we come across it later again,
                # we can copy from _this_ copy (e.g. we only upload it once, and copy thereafter).
                dst_list.record_md5(relative_file, md5)

    for f in dst_list.keys():
        if src_list.has_key(f) or update_list.has_key(f):
            # leave only those not on src_list + update_list
            del dst_list[f]

    return src_list, dst_list, update_list, copy_pairs

# vim:et:ts=4:sts=4:ai

########NEW FILE########
__FILENAME__ = HashCache
import cPickle as pickle

class HashCache(object):
    def __init__(self):
        self.inodes = dict()

    def add(self, dev, inode, mtime, size, md5):
        if dev == 0 or inode == 0: return # Windows
        if dev not in self.inodes:
            self.inodes[dev] = dict()
        if inode not in self.inodes[dev]:
            self.inodes[dev][inode] = dict()
        self.inodes[dev][inode][mtime] = dict(md5=md5, size=size)

    def md5(self, dev, inode, mtime, size):
        try:
            d = self.inodes[dev][inode][mtime]
            if d['size'] != size:
                return None
        except:
            return None
        return d['md5']

    def mark_all_for_purge(self):
        for d in self.inodes.keys():
            for i in self.inodes[d].keys():
                for c in self.inodes[d][i].keys():
                    self.inodes[d][i][c]['purge'] = True

    def unmark_for_purge(self, dev, inode, mtime, size):
        try:
            d = self.inodes[dev][inode][mtime]
        except KeyError:
            return
        if d['size'] == size and 'purge' in d:
            del self.inodes[dev][inode][mtime]['purge']

    def purge(self):
        for d in self.inodes.keys():
            for i in self.inodes[d].keys():
                for m in self.inodes[d][i].keys():
                    if 'purge' in self.inodes[d][i][m]:
                        del self.inodes[d][i]
                        break

    def save(self, f):
        d = dict(inodes=self.inodes, version=1)
        f = open(f, 'w')
        p = pickle.dump(d, f)
        f.close()

    def load(self, f):
        f = open(f, 'r')
        d = pickle.load(f)
        f.close()
        if d.get('version') == 1 and 'inodes' in d:
            self.inodes = d['inodes']

########NEW FILE########
__FILENAME__ = MultiPart
## Amazon S3 Multipart upload support
## Author: Jerome Leclanche <jerome.leclanche@gmail.com>
## License: GPL Version 2

import os
import sys
from stat import ST_SIZE
from logging import debug, info, warning, error
from Utils import getTextFromXml, getTreeFromXml, formatSize, unicodise, calculateChecksum, parseNodes
from Exceptions import S3UploadError

class MultiPartUpload(object):

    MIN_CHUNK_SIZE_MB = 5       # 5MB
    MAX_CHUNK_SIZE_MB = 5120    # 5GB
    MAX_FILE_SIZE = 42949672960 # 5TB

    def __init__(self, s3, file, uri, headers_baseline = {}):
        self.s3 = s3
        self.file = file
        self.uri = uri
        self.parts = {}
        self.headers_baseline = headers_baseline
        self.upload_id = self.initiate_multipart_upload()

    def get_parts_information(self, uri, upload_id):
        multipart_response = self.s3.list_multipart(uri, upload_id)
        tree = getTreeFromXml(multipart_response['data'])

        parts = dict()
        for elem in parseNodes(tree):
            try:
                parts[int(elem['PartNumber'])] = {'checksum': elem['ETag'], 'size': elem['Size']}
            except KeyError:
                pass

        return parts

    def get_unique_upload_id(self, uri):
        upload_id = None
        multipart_response = self.s3.get_multipart(uri)
        tree = getTreeFromXml(multipart_response['data'])
        for mpupload in parseNodes(tree):
            try:
                mp_upload_id = mpupload['UploadId']
                mp_path = mpupload['Key']
                info("mp_path: %s, object: %s" % (mp_path, uri.object()))
                if mp_path == uri.object():
                    if upload_id is not None:
                        raise ValueError("More than one UploadId for URI %s.  Disable multipart upload, or use\n %s multipart %s\nto list the Ids, then pass a unique --upload-id into the put command." % (uri, sys.argv[0], uri))
                    upload_id = mp_upload_id
            except KeyError:
                pass

        return upload_id

    def initiate_multipart_upload(self):
        """
        Begin a multipart upload
        http://docs.amazonwebservices.com/AmazonS3/latest/API/index.html?mpUploadInitiate.html
        """
        if self.s3.config.upload_id is not None:
            self.upload_id = self.s3.config.upload_id
        elif self.s3.config.put_continue:
            self.upload_id = self.get_unique_upload_id(self.uri)
        else:
            self.upload_id = None

        if self.upload_id is None:
            request = self.s3.create_request("OBJECT_POST", uri = self.uri, headers = self.headers_baseline, extra = "?uploads")
            response = self.s3.send_request(request)
            data = response["data"]
            self.upload_id = getTextFromXml(data, "UploadId")

        return self.upload_id

    def upload_all_parts(self):
        """
        Execute a full multipart upload on a file
        Returns the seq/etag dict
        TODO use num_processes to thread it
        """
        if not self.upload_id:
            raise RuntimeError("Attempting to use a multipart upload that has not been initiated.")

        self.chunk_size = self.s3.config.multipart_chunk_size_mb * 1024 * 1024

        if self.file.name != "<stdin>":
                size_left = file_size = os.stat(self.file.name)[ST_SIZE]
                nr_parts = file_size / self.chunk_size + (file_size % self.chunk_size and 1)
                debug("MultiPart: Uploading %s in %d parts" % (self.file.name, nr_parts))
        else:
            debug("MultiPart: Uploading from %s" % (self.file.name))

        remote_statuses = dict()
        if self.s3.config.put_continue:
            remote_statuses = self.get_parts_information(self.uri, self.upload_id)

        seq = 1
        if self.file.name != "<stdin>":
            while size_left > 0:
                offset = self.chunk_size * (seq - 1)
                current_chunk_size = min(file_size - offset, self.chunk_size)
                size_left -= current_chunk_size
                labels = {
                    'source' : unicodise(self.file.name),
                    'destination' : unicodise(self.uri.uri()),
                    'extra' : "[part %d of %d, %s]" % (seq, nr_parts, "%d%sB" % formatSize(current_chunk_size, human_readable = True))
                }
                try:
                    self.upload_part(seq, offset, current_chunk_size, labels, remote_status = remote_statuses.get(seq))
                except:
                    error(u"\nUpload of '%s' part %d failed. Use\n  %s abortmp %s %s\nto abort the upload, or\n  %s --upload-id %s put ...\nto continue the upload."
                          % (self.file.name, seq, sys.argv[0], self.uri, self.upload_id, sys.argv[0], self.upload_id))
                    raise
                seq += 1
        else:
            while True:
                buffer = self.file.read(self.chunk_size)
                offset = self.chunk_size * (seq - 1)
                current_chunk_size = len(buffer)
                labels = {
                    'source' : unicodise(self.file.name),
                    'destination' : unicodise(self.uri.uri()),
                    'extra' : "[part %d, %s]" % (seq, "%d%sB" % formatSize(current_chunk_size, human_readable = True))
                }
                if len(buffer) == 0: # EOF
                    break
                try:
                    self.upload_part(seq, offset, current_chunk_size, labels, buffer, remote_status = remote_statuses.get(seq))
                except:
                    error(u"\nUpload of '%s' part %d failed. Use\n  %s abortmp %s %s\nto abort, or\n  %s --upload-id %s put ...\nto continue the upload."
                          % (self.file.name, seq, self.uri, sys.argv[0], self.upload_id, sys.argv[0], self.upload_id))
                    raise
                seq += 1

        debug("MultiPart: Upload finished: %d parts", seq - 1)

    def upload_part(self, seq, offset, chunk_size, labels, buffer = '', remote_status = None):
        """
        Upload a file chunk
        http://docs.amazonwebservices.com/AmazonS3/latest/API/index.html?mpUploadUploadPart.html
        """
        # TODO implement Content-MD5
        debug("Uploading part %i of %r (%s bytes)" % (seq, self.upload_id, chunk_size))

        if remote_status is not None:
            if int(remote_status['size']) == chunk_size:
                checksum = calculateChecksum(buffer, self.file, offset, chunk_size, self.s3.config.send_chunk)
                remote_checksum = remote_status['checksum'].strip('"')
                if remote_checksum == checksum:
                    warning("MultiPart: size and md5sum match for %s part %d, skipping." % (self.uri, seq))
                    self.parts[seq] = remote_status['checksum']
                    return
                else:
                    warning("MultiPart: checksum (%s vs %s) does not match for %s part %d, reuploading."
                            % (remote_checksum, checksum, self.uri, seq))
            else:
                warning("MultiPart: size (%d vs %d) does not match for %s part %d, reuploading."
                        % (int(remote_status['size']), chunk_size, self.uri, seq))

        headers = { "content-length": chunk_size }
        query_string = "?partNumber=%i&uploadId=%s" % (seq, self.upload_id)
        request = self.s3.create_request("OBJECT_PUT", uri = self.uri, headers = headers, extra = query_string)
        response = self.s3.send_file(request, self.file, labels, buffer, offset = offset, chunk_size = chunk_size)
        self.parts[seq] = response["headers"]["etag"]
        return response

    def complete_multipart_upload(self):
        """
        Finish a multipart upload
        http://docs.amazonwebservices.com/AmazonS3/latest/API/index.html?mpUploadComplete.html
        """
        debug("MultiPart: Completing upload: %s" % self.upload_id)

        parts_xml = []
        part_xml = "<Part><PartNumber>%i</PartNumber><ETag>%s</ETag></Part>"
        for seq, etag in self.parts.items():
            parts_xml.append(part_xml % (seq, etag))
        body = "<CompleteMultipartUpload>%s</CompleteMultipartUpload>" % ("".join(parts_xml))

        headers = { "content-length": len(body) }
        request = self.s3.create_request("OBJECT_POST", uri = self.uri, headers = headers, extra = "?uploadId=%s" % (self.upload_id))
        response = self.s3.send_request(request, body = body)

        return response

    def abort_upload(self):
        """
        Abort multipart upload
        http://docs.amazonwebservices.com/AmazonS3/latest/API/index.html?mpUploadAbort.html
        """
        debug("MultiPart: Aborting upload: %s" % self.upload_id)
        #request = self.s3.create_request("OBJECT_DELETE", uri = self.uri, extra = "?uploadId=%s" % (self.upload_id))
        #response = self.s3.send_request(request)
        response = None
        return response

# vim:et:ts=4:sts=4:ai

########NEW FILE########
__FILENAME__ = PkgInfo
## Amazon S3 manager
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2
## Copyright: TGRMN Software and contributors

package = "s3cmd"
version = "1.5.0-beta1"
url = "http://s3tools.org"
license = "GPL version 2"
short_description = "Command line tool for managing Amazon S3 and CloudFront services"
long_description = """
S3cmd lets you copy files from/to Amazon S3
(Simple Storage Service) using a simple to use
command line client. Supports rsync-like backup,
GPG encryption, and more. Also supports management
of Amazon's CloudFront content delivery network.
"""

# vim:et:ts=4:sts=4:ai

########NEW FILE########
__FILENAME__ = Progress
## Amazon S3 manager
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2
## Copyright: TGRMN Software and contributors

import sys
import datetime
import time
import Utils

class Progress(object):
    _stdout = sys.stdout
    _last_display = 0

    def __init__(self, labels, total_size):
        self._stdout = sys.stdout
        self.new_file(labels, total_size)

    def new_file(self, labels, total_size):
        self.labels = labels
        self.total_size = total_size
        # Set initial_position to something in the
        # case we're not counting from 0. For instance
        # when appending to a partially downloaded file.
        # Setting initial_position will let the speed
        # be computed right.
        self.initial_position = 0
        self.current_position = self.initial_position
        self.time_start = datetime.datetime.now()
        self.time_last = self.time_start
        self.time_current = self.time_start

        self.display(new_file = True)

    def update(self, current_position = -1, delta_position = -1):
        self.time_last = self.time_current
        self.time_current = datetime.datetime.now()
        if current_position > -1:
            self.current_position = current_position
        elif delta_position > -1:
            self.current_position += delta_position
        #else:
        #   no update, just call display()
        self.display()

    def done(self, message):
        self.display(done_message = message)

    def output_labels(self):
        self._stdout.write(u"%(source)s -> %(destination)s  %(extra)s\n" % self.labels)
        self._stdout.flush()

    def _display_needed(self):
        # We only need to update the display every so often.
        if time.time() - self._last_display > 1:
            self._last_display = time.time()
            return True
        return False

    def display(self, new_file = False, done_message = None):
        """
        display(new_file = False[/True], done = False[/True])

        Override this method to provide a nicer output.
        """
        if new_file:
            self.output_labels()
            self.last_milestone = 0
            return

        if self.current_position == self.total_size:
            print_size = Utils.formatSize(self.current_position, True)
            if print_size[1] != "": print_size[1] += "B"
            timedelta = self.time_current - self.time_start
            sec_elapsed = timedelta.days * 86400 + timedelta.seconds + float(timedelta.microseconds)/1000000.0
            print_speed = Utils.formatSize((self.current_position - self.initial_position) / sec_elapsed, True, True)
            self._stdout.write("100%%  %s%s in %.2fs (%.2f %sB/s)\n" %
                (print_size[0], print_size[1], sec_elapsed, print_speed[0], print_speed[1]))
            self._stdout.flush()
            return

        rel_position = self.current_position * 100 / self.total_size
        if rel_position >= self.last_milestone:
            self.last_milestone = (int(rel_position) / 5) * 5
            self._stdout.write("%d%% ", self.last_milestone)
            self._stdout.flush()
            return

class ProgressANSI(Progress):
    ## http://en.wikipedia.org/wiki/ANSI_escape_code
    SCI = '\x1b['
    ANSI_hide_cursor = SCI + "?25l"
    ANSI_show_cursor = SCI + "?25h"
    ANSI_save_cursor_pos = SCI + "s"
    ANSI_restore_cursor_pos = SCI + "u"
    ANSI_move_cursor_to_column = SCI + "%uG"
    ANSI_erase_to_eol = SCI + "0K"
    ANSI_erase_current_line = SCI + "2K"

    def display(self, new_file = False, done_message = None):
        """
        display(new_file = False[/True], done_message = None)
        """
        if new_file:
            self.output_labels()
            self._stdout.write(self.ANSI_save_cursor_pos)
            self._stdout.flush()
            return

        # Only display progress every so often
        if not (new_file or done_message) and not self._display_needed():
            return

        timedelta = self.time_current - self.time_start
        sec_elapsed = timedelta.days * 86400 + timedelta.seconds + float(timedelta.microseconds)/1000000.0
        if (sec_elapsed > 0):
            print_speed = Utils.formatSize((self.current_position - self.initial_position) / sec_elapsed, True, True)
        else:
            print_speed = (0, "")
        self._stdout.write(self.ANSI_restore_cursor_pos)
        self._stdout.write(self.ANSI_erase_to_eol)
        self._stdout.write("%(current)s of %(total)s   %(percent)3d%% in %(elapsed)ds  %(speed).2f %(speed_coeff)sB/s" % {
            "current" : str(self.current_position).rjust(len(str(self.total_size))),
            "total" : self.total_size,
            "percent" : self.total_size and (self.current_position * 100 / self.total_size) or 0,
            "elapsed" : sec_elapsed,
            "speed" : print_speed[0],
            "speed_coeff" : print_speed[1]
        })

        if done_message:
            self._stdout.write("  %s\n" % done_message)

        self._stdout.flush()

class ProgressCR(Progress):
    ## Uses CR char (Carriage Return) just like other progress bars do.
    CR_char = chr(13)

    def display(self, new_file = False, done_message = None):
        """
        display(new_file = False[/True], done_message = None)
        """
        if new_file:
            self.output_labels()
            return

        # Only display progress every so often
        if not (new_file or done_message) and not self._display_needed():
            return

        timedelta = self.time_current - self.time_start
        sec_elapsed = timedelta.days * 86400 + timedelta.seconds + float(timedelta.microseconds)/1000000.0
        if (sec_elapsed > 0):
            print_speed = Utils.formatSize((self.current_position - self.initial_position) / sec_elapsed, True, True)
        else:
            print_speed = (0, "")
        self._stdout.write(self.CR_char)
        output = " %(current)s of %(total)s   %(percent)3d%% in %(elapsed)4ds  %(speed)7.2f %(speed_coeff)sB/s" % {
            "current" : str(self.current_position).rjust(len(str(self.total_size))),
            "total" : self.total_size,
            "percent" : self.total_size and (self.current_position * 100 / self.total_size) or 0,
            "elapsed" : sec_elapsed,
            "speed" : print_speed[0],
            "speed_coeff" : print_speed[1]
        }
        self._stdout.write(output)
        if done_message:
            self._stdout.write("  %s\n" % done_message)

        self._stdout.flush()

# vim:et:ts=4:sts=4:ai

########NEW FILE########
__FILENAME__ = S3
## Amazon S3 manager
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2
## Copyright: TGRMN Software and contributors

import sys
import os, os.path
import time
import errno
import base64
import httplib
import logging
import mimetypes
import re
from xml.sax import saxutils
import base64
from logging import debug, info, warning, error
from stat import ST_SIZE

try:
    from hashlib import md5
except ImportError:
    from md5 import md5

from Utils import *
from SortedDict import SortedDict
from AccessLog import AccessLog
from ACL import ACL, GranteeLogDelivery
from BidirMap import BidirMap
from Config import Config
from Exceptions import *
from MultiPart import MultiPartUpload
from S3Uri import S3Uri
from ConnMan import ConnMan

try:
    import magic
    try:
        ## https://github.com/ahupp/python-magic
        magic_ = magic.Magic(mime=True)
        def mime_magic_file(file):
            return magic_.from_file(file)
    except TypeError:
        ## http://pypi.python.org/pypi/filemagic
        try:
            magic_ = magic.Magic(flags=magic.MAGIC_MIME)
            def mime_magic_file(file):
                return magic_.id_filename(file)
        except TypeError:
            ## file-5.11 built-in python bindings
            magic_ = magic.open(magic.MAGIC_MIME)
            magic_.load()
            def mime_magic_file(file):
                return magic_.file(file)
    except AttributeError:
        ## Older python-magic versions
        magic_ = magic.open(magic.MAGIC_MIME)
        magic_.load()
        def mime_magic_file(file):
            return magic_.file(file)

except ImportError, e:
    if str(e).find("magic") >= 0:
        magic_message = "Module python-magic is not available."
    else:
        magic_message = "Module python-magic can't be used (%s)." % e.message
    magic_message += " Guessing MIME types based on file extensions."
    magic_warned = False
    def mime_magic_file(file):
        global magic_warned
        if (not magic_warned):
            warning(magic_message)
            magic_warned = True
        return mimetypes.guess_type(file)[0]

def mime_magic(file):
    # we can't tell if a given copy of the magic library will take a
    # filesystem-encoded string or a unicode value, so try first
    # with the encoded string, then unicode.
    def _mime_magic(file):
        magictype = None
        try:
            magictype = mime_magic_file(file)
        except UnicodeDecodeError:
            magictype = mime_magic_file(unicodise(file))
        return magictype

    result = _mime_magic(file)
    if result is not None:
        if isinstance(result, str):
            if ';' in result:
                mimetype, charset = result.split(';')
                charset = charset[len('charset'):]
                result = (mimetype, charset)
            else:
                result = (result, None)
    if result is None:
        result = (None, None)
    return result

__all__ = []
class S3Request(object):
    def __init__(self, s3, method_string, resource, headers, params = {}):
        self.s3 = s3
        self.headers = SortedDict(headers or {}, ignore_case = True)
        # Add in any extra headers from s3 config object
        if self.s3.config.extra_headers:
            self.headers.update(self.s3.config.extra_headers)
        if len(self.s3.config.access_token)>0:
            self.s3.config.role_refresh()
            self.headers['x-amz-security-token']=self.s3.config.access_token
        self.resource = resource
        self.method_string = method_string
        self.params = params

        self.update_timestamp()
        self.sign()

    def update_timestamp(self):
        if self.headers.has_key("date"):
            del(self.headers["date"])
        self.headers["x-amz-date"] = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())

    def format_param_str(self):
        """
        Format URL parameters from self.params and returns
        ?parm1=val1&parm2=val2 or an empty string if there
        are no parameters.  Output of this function should
        be appended directly to self.resource['uri']
        """
        param_str = ""
        for param in self.params:
            if self.params[param] not in (None, ""):
                param_str += "&%s=%s" % (param, self.params[param])
            else:
                param_str += "&%s" % param
        return param_str and "?" + param_str[1:]

    def sign(self):
        h  = self.method_string + "\n"
        h += self.headers.get("content-md5", "")+"\n"
        h += self.headers.get("content-type", "")+"\n"
        h += self.headers.get("date", "")+"\n"
        for header in self.headers.keys():
            if header.startswith("x-amz-"):
                h += header+":"+str(self.headers[header])+"\n"
        if self.resource['bucket']:
            h += "/" + self.resource['bucket']
        h += self.resource['uri']
        debug("SignHeaders: " + repr(h))
        signature = sign_string(h)

        self.headers["Authorization"] = "AWS "+self.s3.config.access_key+":"+signature

    def get_triplet(self):
        self.update_timestamp()
        self.sign()
        resource = dict(self.resource)  ## take a copy
        resource['uri'] += self.format_param_str()
        return (self.method_string, resource, self.headers)

class S3(object):
    http_methods = BidirMap(
        GET = 0x01,
        PUT = 0x02,
        HEAD = 0x04,
        DELETE = 0x08,
        POST = 0x10,
        MASK = 0x1F,
    )

    targets = BidirMap(
        SERVICE = 0x0100,
        BUCKET = 0x0200,
        OBJECT = 0x0400,
        BATCH = 0x0800,
        MASK = 0x0700,
    )

    operations = BidirMap(
        UNDFINED = 0x0000,
        LIST_ALL_BUCKETS = targets["SERVICE"] | http_methods["GET"],
        BUCKET_CREATE = targets["BUCKET"] | http_methods["PUT"],
        BUCKET_LIST = targets["BUCKET"] | http_methods["GET"],
        BUCKET_DELETE = targets["BUCKET"] | http_methods["DELETE"],
        OBJECT_PUT = targets["OBJECT"] | http_methods["PUT"],
        OBJECT_GET = targets["OBJECT"] | http_methods["GET"],
        OBJECT_HEAD = targets["OBJECT"] | http_methods["HEAD"],
        OBJECT_DELETE = targets["OBJECT"] | http_methods["DELETE"],
        OBJECT_POST = targets["OBJECT"] | http_methods["POST"],
        BATCH_DELETE = targets["BATCH"] | http_methods["POST"],
    )

    codes = {
        "NoSuchBucket" : "Bucket '%s' does not exist",
        "AccessDenied" : "Access to bucket '%s' was denied",
        "BucketAlreadyExists" : "Bucket '%s' already exists",
    }

    ## S3 sometimes sends HTTP-307 response
    redir_map = {}

    ## Maximum attempts of re-issuing failed requests
    _max_retries = 5

    def __init__(self, config):
        self.config = config

    def get_hostname(self, bucket):
        if bucket and check_bucket_name_dns_conformity(bucket):
            if self.redir_map.has_key(bucket):
                host = self.redir_map[bucket]
            else:
                host = getHostnameFromBucket(bucket)
        else:
            host = self.config.host_base
        debug('get_hostname(%s): %s' % (bucket, host))
        return host

    def set_hostname(self, bucket, redir_hostname):
        self.redir_map[bucket] = redir_hostname

    def format_uri(self, resource):
        if resource['bucket'] and not check_bucket_name_dns_conformity(resource['bucket']):
            uri = "/%s%s" % (resource['bucket'], resource['uri'])
        else:
            uri = resource['uri']
        if self.config.proxy_host != "":
            uri = "http://%s%s" % (self.get_hostname(resource['bucket']), uri)
        debug('format_uri(): ' + uri)
        return uri

    ## Commands / Actions
    def list_all_buckets(self):
        request = self.create_request("LIST_ALL_BUCKETS")
        response = self.send_request(request)
        response["list"] = getListFromXml(response["data"], "Bucket")
        return response

    def bucket_list(self, bucket, prefix = None, recursive = None, uri_params = {}):
        def _list_truncated(data):
            ## <IsTruncated> can either be "true" or "false" or be missing completely
            is_truncated = getTextFromXml(data, ".//IsTruncated") or "false"
            return is_truncated.lower() != "false"

        def _get_contents(data):
            return getListFromXml(data, "Contents")

        def _get_common_prefixes(data):
            return getListFromXml(data, "CommonPrefixes")

        uri_params = uri_params.copy()
        truncated = True
        list = []
        prefixes = []

        while truncated:
            response = self.bucket_list_noparse(bucket, prefix, recursive, uri_params)
            current_list = _get_contents(response["data"])
            current_prefixes = _get_common_prefixes(response["data"])
            truncated = _list_truncated(response["data"])
            if truncated:
                if current_list:
                    uri_params['marker'] = self.urlencode_string(current_list[-1]["Key"])
                else:
                    uri_params['marker'] = self.urlencode_string(current_prefixes[-1]["Prefix"])
                debug("Listing continues after '%s'" % uri_params['marker'])

            list += current_list
            prefixes += current_prefixes

        response['list'] = list
        response['common_prefixes'] = prefixes
        return response

    def bucket_list_noparse(self, bucket, prefix = None, recursive = None, uri_params = {}):
        if prefix:
            uri_params['prefix'] = self.urlencode_string(prefix)
        if not self.config.recursive and not recursive:
            uri_params['delimiter'] = "/"
        request = self.create_request("BUCKET_LIST", bucket = bucket, **uri_params)
        response = self.send_request(request)
        #debug(response)
        return response

    def bucket_create(self, bucket, bucket_location = None):
        headers = SortedDict(ignore_case = True)
        body = ""
        if bucket_location and bucket_location.strip().upper() != "US":
            bucket_location = bucket_location.strip()
            if bucket_location.upper() == "EU":
                bucket_location = bucket_location.upper()
            else:
                bucket_location = bucket_location.lower()
            body  = "<CreateBucketConfiguration><LocationConstraint>"
            body += bucket_location
            body += "</LocationConstraint></CreateBucketConfiguration>"
            debug("bucket_location: " + body)
            check_bucket_name(bucket, dns_strict = True)
        else:
            check_bucket_name(bucket, dns_strict = False)
        if self.config.acl_public:
            headers["x-amz-acl"] = "public-read"
        request = self.create_request("BUCKET_CREATE", bucket = bucket, headers = headers)
        response = self.send_request(request, body)
        return response

    def bucket_delete(self, bucket):
        request = self.create_request("BUCKET_DELETE", bucket = bucket)
        response = self.send_request(request)
        return response

    def get_bucket_location(self, uri):
        request = self.create_request("BUCKET_LIST", bucket = uri.bucket(), extra = "?location")
        response = self.send_request(request)
        location = getTextFromXml(response['data'], "LocationConstraint")
        if not location or location in [ "", "US" ]:
            location = "us-east-1"
        elif location == "EU":
            location = "eu-west-1"
        return location

    def bucket_info(self, uri):
        # For now reports only "Location". One day perhaps more.
        response = {}
        response['bucket-location'] = self.get_bucket_location(uri)
        return response

    def website_info(self, uri, bucket_location = None):
        headers = SortedDict(ignore_case = True)
        bucket = uri.bucket()
        body = ""

        request = self.create_request("BUCKET_LIST", bucket = bucket, extra="?website")
        try:
            response = self.send_request(request, body)
            response['index_document'] = getTextFromXml(response['data'], ".//IndexDocument//Suffix")
            response['error_document'] = getTextFromXml(response['data'], ".//ErrorDocument//Key")
            response['website_endpoint'] = self.config.website_endpoint % {
                "bucket" : uri.bucket(),
                "location" : self.get_bucket_location(uri)}
            return response
        except S3Error, e:
            if e.status == 404:
                debug("Could not get /?website - website probably not configured for this bucket")
                return None
            raise

    def website_create(self, uri, bucket_location = None):
        headers = SortedDict(ignore_case = True)
        bucket = uri.bucket()
        body = '<WebsiteConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        body += '  <IndexDocument>'
        body += ('    <Suffix>%s</Suffix>' % self.config.website_index)
        body += '  </IndexDocument>'
        if self.config.website_error:
            body += '  <ErrorDocument>'
            body += ('    <Key>%s</Key>' % self.config.website_error)
            body += '  </ErrorDocument>'
        body += '</WebsiteConfiguration>'

        request = self.create_request("BUCKET_CREATE", bucket = bucket, extra="?website")
        debug("About to send request '%s' with body '%s'" % (request, body))
        response = self.send_request(request, body)
        debug("Received response '%s'" % (response))

        return response

    def website_delete(self, uri, bucket_location = None):
        headers = SortedDict(ignore_case = True)
        bucket = uri.bucket()
        body = ""

        request = self.create_request("BUCKET_DELETE", bucket = bucket, extra="?website")
        debug("About to send request '%s' with body '%s'" % (request, body))
        response = self.send_request(request, body)
        debug("Received response '%s'" % (response))

        if response['status'] != 204:
            raise S3ResponseError("Expected status 204: %s" % response)

        return response

    def expiration_info(self, uri, bucket_location = None):
        headers = SortedDict(ignore_case = True)
        bucket = uri.bucket()
        body = ""

        request = self.create_request("BUCKET_LIST", bucket = bucket, extra="?lifecycle")
        try:
            response = self.send_request(request, body)
            response['prefix'] = getTextFromXml(response['data'], ".//Rule//Prefix")
            response['date'] = getTextFromXml(response['data'], ".//Rule//Expiration//Date")
            response['days'] = getTextFromXml(response['data'], ".//Rule//Expiration//Days")
            return response
        except S3Error, e:
            if e.status == 404:
                debug("Could not get /?lifecycle - lifecycle probably not configured for this bucket")
                return None
            raise

    def expiration_set(self, uri, bucket_location = None):
        if self.config.expiry_date and self.config.expiry_days:
             raise ParameterError("Expect either --expiry-day or --expiry-date")
        if not (self.config.expiry_date or self.config.expiry_days):
             if self.config.expiry_prefix:
                 raise ParameterError("Expect either --expiry-day or --expiry-date")
             debug("del bucket lifecycle")
             bucket = uri.bucket()
             body = ""
             request = self.create_request("BUCKET_DELETE", bucket = bucket, extra="?lifecycle")
        else:
             request, body = self._expiration_set(uri)
        debug("About to send request '%s' with body '%s'" % (request, body))
        response = self.send_request(request, body)
        debug("Received response '%s'" % (response))
        return response

    def _expiration_set(self, uri):
        debug("put bucket lifecycle")
        body = '<LifecycleConfiguration>'
        body += '  <Rule>'
        body += ('    <Prefix>%s</Prefix>' % self.config.expiry_prefix)
        body += ('    <Status>Enabled</Status>')
        body += ('    <Expiration>')
        if self.config.expiry_date:
            body += ('    <Date>%s</Date>' % self.config.expiry_date)
        elif self.config.expiry_days:
            body += ('    <Days>%s</Days>' % self.config.expiry_days)
        body += ('    </Expiration>')
        body += '  </Rule>'
        body += '</LifecycleConfiguration>'

        headers = SortedDict(ignore_case = True)
        headers['content-md5'] = compute_content_md5(body)
        bucket = uri.bucket()
        request =  self.create_request("BUCKET_CREATE", bucket = bucket, headers = headers, extra="?lifecycle")
        return (request, body)

    def add_encoding(self, filename, content_type):
        if content_type.find("charset=") != -1:
           return False
        exts = self.config.add_encoding_exts.split(',')
        if exts[0]=='':
            return False
        parts = filename.rsplit('.',2)
        if len(parts) < 2:
            return False
        ext = parts[1]
        if ext in exts:
            return True
        else:
            return False

    def object_put(self, filename, uri, extra_headers = None, extra_label = ""):
        # TODO TODO
        # Make it consistent with stream-oriented object_get()
        if uri.type != "s3":
            raise ValueError("Expected URI type 's3', got '%s'" % uri.type)

        if filename != "-" and not os.path.isfile(filename):
            raise InvalidFileError(u"%s is not a regular file" % unicodise(filename))
        try:
            if filename == "-":
                file = sys.stdin
                size = 0
            else:
                file = open(filename, "rb")
                size = os.stat(filename)[ST_SIZE]
        except (IOError, OSError), e:
            raise InvalidFileError(u"%s: %s" % (unicodise(filename), e.strerror))

        headers = SortedDict(ignore_case = True)
        if extra_headers:
            headers.update(extra_headers)

        ## Set server side encryption
        if self.config.server_side_encryption:
            headers["x-amz-server-side-encryption"] = "AES256"

        ## MIME-type handling
        content_type = self.config.mime_type
        content_charset = None
        if filename != "-" and not content_type and self.config.guess_mime_type:
            if self.config.use_mime_magic:
                (content_type, content_charset) = mime_magic(filename)
            else:
                (content_type, content_charset) = mimetypes.guess_type(filename)
        if not content_type:
            content_type = self.config.default_mime_type
        if not content_charset:
            content_charset = self.config.encoding.upper()

        ## add charset to content type
        if self.add_encoding(filename, content_type) and content_charset is not None:
            content_type = content_type + "; charset=" + content_charset

        headers["content-type"] = content_type

        ## Other Amazon S3 attributes
        if self.config.acl_public:
            headers["x-amz-acl"] = "public-read"
        if self.config.reduced_redundancy:
            headers["x-amz-storage-class"] = "REDUCED_REDUNDANCY"

        ## Multipart decision
        multipart = False
        if not self.config.enable_multipart and filename == "-":
            raise ParameterError("Multi-part upload is required to upload from stdin")
        if self.config.enable_multipart:
            if size > self.config.multipart_chunk_size_mb * 1024 * 1024 or filename == "-":
                multipart = True
        if multipart:
            # Multipart requests are quite different... drop here
            return self.send_file_multipart(file, headers, uri, size)

        ## Not multipart...
        if self.config.put_continue:
            # Note, if input was stdin, we would be performing multipart upload.
            # So this will always work as long as the file already uploaded was
            # not uploaded via MultiUpload, in which case its ETag will not be
            # an md5.
            try:
                info = self.object_info(uri)
            except:
                info = None

            if info is not None:
                remote_size = int(info['headers']['content-length'])
                remote_checksum = info['headers']['etag'].strip('"')
                if size == remote_size:
                    checksum = calculateChecksum('', file, 0, size, self.config.send_chunk)
                    if remote_checksum == checksum:
                        warning("Put: size and md5sum match for %s, skipping." % uri)
                        return
                    else:
                        warning("MultiPart: checksum (%s vs %s) does not match for %s, reuploading."
                                % (remote_checksum, checksum, uri))
                else:
                    warning("MultiPart: size (%d vs %d) does not match for %s, reuploading."
                            % (remote_size, size, uri))

        headers["content-length"] = size
        request = self.create_request("OBJECT_PUT", uri = uri, headers = headers)
        labels = { 'source' : unicodise(filename), 'destination' : unicodise(uri.uri()), 'extra' : extra_label }
        response = self.send_file(request, file, labels)
        return response

    def object_get(self, uri, stream, start_position = 0, extra_label = ""):
        if uri.type != "s3":
            raise ValueError("Expected URI type 's3', got '%s'" % uri.type)
        request = self.create_request("OBJECT_GET", uri = uri)
        labels = { 'source' : unicodise(uri.uri()), 'destination' : unicodise(stream.name), 'extra' : extra_label }
        response = self.recv_file(request, stream, labels, start_position)
        return response

    def object_batch_delete(self, remote_list):
        def compose_batch_del_xml(bucket, key_list):
            body = u"<?xml version=\"1.0\" encoding=\"UTF-8\"?><Delete>"
            for key in key_list:
                uri = S3Uri(key)
                if uri.type != "s3":
                    raise ValueError("Excpected URI type 's3', got '%s'" % uri.type)
                if not uri.has_object():
                    raise ValueError("URI '%s' has no object" % key)
                if uri.bucket() != bucket:
                    raise ValueError("The batch should contain keys from the same bucket")
                object = saxutils.escape(uri.object())
                body += u"<Object><Key>%s</Key></Object>" % object
            body += u"</Delete>"
            body = body.encode('utf-8')
            return body

        batch = [remote_list[item]['object_uri_str'] for item in remote_list]
        if len(batch) == 0:
            raise ValueError("Key list is empty")
        bucket = S3Uri(batch[0]).bucket()
        request_body = compose_batch_del_xml(bucket, batch)
        md5_hash = md5()
        md5_hash.update(request_body)
        headers = {'content-md5': base64.b64encode(md5_hash.digest())}
        request = self.create_request("BATCH_DELETE", bucket = bucket, extra = '?delete', headers = headers)
        response = self.send_request(request, request_body)
        return response

    def object_delete(self, uri):
        if uri.type != "s3":
            raise ValueError("Expected URI type 's3', got '%s'" % uri.type)
        request = self.create_request("OBJECT_DELETE", uri = uri)
        response = self.send_request(request)
        return response

    def object_restore(self, uri):
        if uri.type != "s3":
            raise ValueError("Expected URI type 's3', got '%s'" % uri.type)
        body = '<RestoreRequest xmlns="http://s3.amazonaws.com/doc/2006-3-01">'
        body += ('  <Days>%s</Days>' % self.config.restore_days)
        body += '</RestoreRequest>'
        request = self.create_request("OBJECT_POST", uri = uri, extra = "?restore")
        debug("About to send request '%s' with body '%s'" % (request, body))
        response = self.send_request(request, body)
        debug("Received response '%s'" % (response))
        return response

    def object_copy(self, src_uri, dst_uri, extra_headers = None):
        if src_uri.type != "s3":
            raise ValueError("Expected URI type 's3', got '%s'" % src_uri.type)
        if dst_uri.type != "s3":
            raise ValueError("Expected URI type 's3', got '%s'" % dst_uri.type)
        headers = SortedDict(ignore_case = True)
        headers['x-amz-copy-source'] = "/%s/%s" % (src_uri.bucket(), self.urlencode_string(src_uri.object()))
        ## TODO: For now COPY, later maybe add a switch?
        headers['x-amz-metadata-directive'] = "COPY"
        if self.config.acl_public:
            headers["x-amz-acl"] = "public-read"
        if self.config.reduced_redundancy:
            headers["x-amz-storage-class"] = "REDUCED_REDUNDANCY"

        ## Set server side encryption
        if self.config.server_side_encryption:
            headers["x-amz-server-side-encryption"] = "AES256"

        if extra_headers:
            headers['x-amz-metadata-directive'] = "REPLACE"
            headers.update(extra_headers)
        request = self.create_request("OBJECT_PUT", uri = dst_uri, headers = headers)
        response = self.send_request(request)
        return response

    def object_move(self, src_uri, dst_uri, extra_headers = None):
        response_copy = self.object_copy(src_uri, dst_uri, extra_headers)
        debug("Object %s copied to %s" % (src_uri, dst_uri))
        if getRootTagName(response_copy["data"]) == "CopyObjectResult":
            response_delete = self.object_delete(src_uri)
            debug("Object %s deleted" % src_uri)
        return response_copy

    def object_info(self, uri):
        request = self.create_request("OBJECT_HEAD", uri = uri)
        response = self.send_request(request)
        return response

    def get_acl(self, uri):
        if uri.has_object():
            request = self.create_request("OBJECT_GET", uri = uri, extra = "?acl")
        else:
            request = self.create_request("BUCKET_LIST", bucket = uri.bucket(), extra = "?acl")

        response = self.send_request(request)
        acl = ACL(response['data'])
        return acl

    def set_acl(self, uri, acl):
        if uri.has_object():
            request = self.create_request("OBJECT_PUT", uri = uri, extra = "?acl")
        else:
            request = self.create_request("BUCKET_CREATE", bucket = uri.bucket(), extra = "?acl")

        body = str(acl)
        debug(u"set_acl(%s): acl-xml: %s" % (uri, body))
        response = self.send_request(request, body)
        return response

    def get_policy(self, uri):
        request = self.create_request("BUCKET_LIST", bucket = uri.bucket(), extra = "?policy")
        response = self.send_request(request)
        return response['data']

    def set_policy(self, uri, policy):
        headers = {}
        # TODO check policy is proper json string
        headers['content-type'] = 'application/json'
        request = self.create_request("BUCKET_CREATE", uri = uri,
                                      extra = "?policy", headers=headers)
        body = policy
        debug(u"set_policy(%s): policy-json: %s" % (uri, body))
        request.sign()
        response = self.send_request(request, body=body)
        return response

    def delete_policy(self, uri):
        request = self.create_request("BUCKET_DELETE", uri = uri, extra = "?policy")
        debug(u"delete_policy(%s)" % uri)
        response = self.send_request(request)
        return response

    def get_multipart(self, uri):
        request = self.create_request("BUCKET_LIST", bucket = uri.bucket(), extra = "?uploads")
        response = self.send_request(request)
        return response

    def abort_multipart(self, uri, id):
        request = self.create_request("OBJECT_DELETE", uri=uri,
                                      extra = ("?uploadId=%s" % id))
        response = self.send_request(request)
        return response

    def list_multipart(self, uri, id):
        request = self.create_request("OBJECT_GET", uri=uri,
                                      extra = ("?uploadId=%s" % id))
        response = self.send_request(request)
        return response

    def get_accesslog(self, uri):
        request = self.create_request("BUCKET_LIST", bucket = uri.bucket(), extra = "?logging")
        response = self.send_request(request)
        accesslog = AccessLog(response['data'])
        return accesslog

    def set_accesslog_acl(self, uri):
        acl = self.get_acl(uri)
        debug("Current ACL(%s): %s" % (uri.uri(), str(acl)))
        acl.appendGrantee(GranteeLogDelivery("READ_ACP"))
        acl.appendGrantee(GranteeLogDelivery("WRITE"))
        debug("Updated ACL(%s): %s" % (uri.uri(), str(acl)))
        self.set_acl(uri, acl)

    def set_accesslog(self, uri, enable, log_target_prefix_uri = None, acl_public = False):
        request = self.create_request("BUCKET_CREATE", bucket = uri.bucket(), extra = "?logging")
        accesslog = AccessLog()
        if enable:
            accesslog.enableLogging(log_target_prefix_uri)
            accesslog.setAclPublic(acl_public)
        else:
            accesslog.disableLogging()
        body = str(accesslog)
        debug(u"set_accesslog(%s): accesslog-xml: %s" % (uri, body))
        try:
            response = self.send_request(request, body)
        except S3Error, e:
            if e.info['Code'] == "InvalidTargetBucketForLogging":
                info("Setting up log-delivery ACL for target bucket.")
                self.set_accesslog_acl(S3Uri("s3://%s" % log_target_prefix_uri.bucket()))
                response = self.send_request(request, body)
            else:
                raise
        return accesslog, response

    ## Low level methods
    def urlencode_string(self, string, urlencoding_mode = None):
        if type(string) == unicode:
            string = string.encode("utf-8")

        if urlencoding_mode is None:
            urlencoding_mode = self.config.urlencoding_mode

        if urlencoding_mode == "verbatim":
            ## Don't do any pre-processing
            return string

        encoded = ""
        ## List of characters that must be escaped for S3
        ## Haven't found this in any official docs
        ## but my tests show it's more less correct.
        ## If you start getting InvalidSignature errors
        ## from S3 check the error headers returned
        ## from S3 to see whether the list hasn't
        ## changed.
        for c in string:    # I'm not sure how to know in what encoding
                    # 'object' is. Apparently "type(object)==str"
                    # but the contents is a string of unicode
                    # bytes, e.g. '\xc4\x8d\xc5\xafr\xc3\xa1k'
                    # Don't know what it will do on non-utf8
                    # systems.
                    #           [hope that sounds reassuring ;-)]
            o = ord(c)
            if (o < 0x20 or o == 0x7f):
                if urlencoding_mode == "fixbucket":
                    encoded += "%%%02X" % o
                else:
                    error(u"Non-printable character 0x%02x in: %s" % (o, string))
                    error(u"Please report it to s3tools-bugs@lists.sourceforge.net")
                    encoded += replace_nonprintables(c)
            elif (o == 0x20 or  # Space and below
                o == 0x22 or    # "
                o == 0x23 or    # #
                o == 0x25 or    # % (escape character)
                o == 0x26 or    # &
                o == 0x2B or    # + (or it would become <space>)
                o == 0x3C or    # <
                o == 0x3E or    # >
                o == 0x3F or    # ?
                o == 0x60 or    # `
                o >= 123):      # { and above, including >= 128 for UTF-8
                encoded += "%%%02X" % o
            else:
                encoded += c
        debug("String '%s' encoded to '%s'" % (string, encoded))
        return encoded

    def create_request(self, operation, uri = None, bucket = None, object = None, headers = None, extra = None, **params):
        resource = { 'bucket' : None, 'uri' : "/" }

        if uri and (bucket or object):
            raise ValueError("Both 'uri' and either 'bucket' or 'object' parameters supplied")
        ## If URI is given use that instead of bucket/object parameters
        if uri:
            bucket = uri.bucket()
            object = uri.has_object() and uri.object() or None

        if bucket:
            resource['bucket'] = str(bucket)
            if object:
                resource['uri'] = "/" + self.urlencode_string(object)
        if extra:
            resource['uri'] += extra

        method_string = S3.http_methods.getkey(S3.operations[operation] & S3.http_methods["MASK"])

        request = S3Request(self, method_string, resource, headers, params)

        debug("CreateRequest: resource[uri]=" + resource['uri'])
        return request

    def _fail_wait(self, retries):
        # Wait a few seconds. The more it fails the more we wait.
        return (self._max_retries - retries + 1) * 3

    def send_request(self, request, body = None, retries = _max_retries):
        method_string, resource, headers = request.get_triplet()
        debug("Processing request, please wait...")
        if not headers.has_key('content-length'):
            headers['content-length'] = body and len(body) or 0
        try:
            # "Stringify" all headers
            for header in headers.keys():
                headers[header] = str(headers[header])
            conn = ConnMan.get(self.get_hostname(resource['bucket']))
            uri = self.format_uri(resource)
            debug("Sending request method_string=%r, uri=%r, headers=%r, body=(%i bytes)" % (method_string, uri, headers, len(body or "")))
            conn.c.request(method_string, uri, body, headers)
            response = {}
            http_response = conn.c.getresponse()
            response["status"] = http_response.status
            response["reason"] = http_response.reason
            response["headers"] = convertTupleListToDict(http_response.getheaders())
            response["data"] =  http_response.read()
            if response["headers"].has_key("x-amz-meta-s3cmd-attrs"):
                attrs = parse_attrs_header(response["headers"]["x-amz-meta-s3cmd-attrs"])
                response["s3cmd-attrs"] = attrs
            debug("Response: " + str(response))
            ConnMan.put(conn)
        except ParameterError, e:
            raise
        except (IOError, OSError), e:
            raise
        except Exception, e:
            if retries:
                warning("Retrying failed request: %s (%s)" % (resource['uri'], e))
                warning("Waiting %d sec..." % self._fail_wait(retries))
                time.sleep(self._fail_wait(retries))
                return self.send_request(request, body, retries - 1)
            else:
                raise S3RequestError("Request failed for: %s" % resource['uri'])

        if response["status"] == 307:
            ## RedirectPermanent
            redir_bucket = getTextFromXml(response['data'], ".//Bucket")
            redir_hostname = getTextFromXml(response['data'], ".//Endpoint")
            self.set_hostname(redir_bucket, redir_hostname)
            warning("Redirected to: %s" % (redir_hostname))
            return self.send_request(request, body)

        if response["status"] >= 500:
            e = S3Error(response)
            if retries:
                warning(u"Retrying failed request: %s" % resource['uri'])
                warning(unicode(e))
                warning("Waiting %d sec..." % self._fail_wait(retries))
                time.sleep(self._fail_wait(retries))
                return self.send_request(request, body, retries - 1)
            else:
                raise e

        if response["status"] < 200 or response["status"] > 299:
            raise S3Error(response)

        return response

    def send_file(self, request, file, labels, buffer = '', throttle = 0, retries = _max_retries, offset = 0, chunk_size = -1):
        method_string, resource, headers = request.get_triplet()
        size_left = size_total = headers.get("content-length")
        if self.config.progress_meter:
            progress = self.config.progress_class(labels, size_total)
        else:
            info("Sending file '%s', please wait..." % file.name)
        timestamp_start = time.time()
        try:
            conn = ConnMan.get(self.get_hostname(resource['bucket']))
            conn.c.putrequest(method_string, self.format_uri(resource))
            for header in headers.keys():
                conn.c.putheader(header, str(headers[header]))
            conn.c.endheaders()
        except ParameterError, e:
            raise
        except Exception, e:
            if self.config.progress_meter:
                progress.done("failed")
            if retries:
                warning("Retrying failed request: %s (%s)" % (resource['uri'], e))
                warning("Waiting %d sec..." % self._fail_wait(retries))
                time.sleep(self._fail_wait(retries))
                # Connection error -> same throttle value
                return self.send_file(request, file, labels, buffer, throttle, retries - 1, offset, chunk_size)
            else:
                raise S3UploadError("Upload failed for: %s" % resource['uri'])
        if buffer == '':
            file.seek(offset)
        md5_hash = md5()

        try:
            while (size_left > 0):
                #debug("SendFile: Reading up to %d bytes from '%s' - remaining bytes: %s" % (self.config.send_chunk, file.name, size_left))
                if buffer == '':
                    data = file.read(min(self.config.send_chunk, size_left))
                else:
                    data = buffer

                md5_hash.update(data)
                conn.c.send(data)
                if self.config.progress_meter:
                    progress.update(delta_position = len(data))
                size_left -= len(data)
                if throttle:
                    time.sleep(throttle)
            md5_computed = md5_hash.hexdigest()

            response = {}
            http_response = conn.c.getresponse()
            response["status"] = http_response.status
            response["reason"] = http_response.reason
            response["headers"] = convertTupleListToDict(http_response.getheaders())
            response["data"] = http_response.read()
            response["size"] = size_total
            ConnMan.put(conn)
            debug(u"Response: %s" % response)
        except ParameterError, e:
            raise
        except Exception, e:
            if self.config.progress_meter:
                progress.done("failed")
            if retries:
                if retries < self._max_retries:
                    throttle = throttle and throttle * 5 or 0.01
                warning("Upload failed: %s (%s)" % (resource['uri'], e))
                warning("Retrying on lower speed (throttle=%0.2f)" % throttle)
                warning("Waiting %d sec..." % self._fail_wait(retries))
                time.sleep(self._fail_wait(retries))
                # Connection error -> same throttle value
                return self.send_file(request, file, labels, buffer, throttle, retries - 1, offset, chunk_size)
            else:
                debug("Giving up on '%s' %s" % (file.name, e))
                raise S3UploadError("Upload failed for: %s" % resource['uri'])

        timestamp_end = time.time()
        response["elapsed"] = timestamp_end - timestamp_start
        response["speed"] = response["elapsed"] and float(response["size"]) / response["elapsed"] or float(-1)

        if self.config.progress_meter:
            ## Finalising the upload takes some time -> update() progress meter
            ## to correct the average speed. Otherwise people will complain that
            ## 'progress' and response["speed"] are inconsistent ;-)
            progress.update()
            progress.done("done")

        if response["status"] == 307:
            ## RedirectPermanent
            redir_bucket = getTextFromXml(response['data'], ".//Bucket")
            redir_hostname = getTextFromXml(response['data'], ".//Endpoint")
            self.set_hostname(redir_bucket, redir_hostname)
            warning("Redirected to: %s" % (redir_hostname))
            return self.send_file(request, file, labels, buffer, offset = offset, chunk_size = chunk_size)

        # S3 from time to time doesn't send ETag back in a response :-(
        # Force re-upload here.
        if not response['headers'].has_key('etag'):
            response['headers']['etag'] = ''

        if response["status"] < 200 or response["status"] > 299:
            try_retry = False
            if response["status"] >= 500:
                ## AWS internal error - retry
                try_retry = True
            elif response["status"] >= 400:
                err = S3Error(response)
                ## Retriable client error?
                if err.code in [ 'BadDigest', 'OperationAborted', 'TokenRefreshRequired', 'RequestTimeout' ]:
                    try_retry = True

            if try_retry:
                if retries:
                    warning("Upload failed: %s (%s)" % (resource['uri'], S3Error(response)))
                    warning("Waiting %d sec..." % self._fail_wait(retries))
                    time.sleep(self._fail_wait(retries))
                    return self.send_file(request, file, labels, buffer, throttle, retries - 1, offset, chunk_size)
                else:
                    warning("Too many failures. Giving up on '%s'" % (file.name))
                    raise S3UploadError

            ## Non-recoverable error
            raise S3Error(response)

        debug("MD5 sums: computed=%s, received=%s" % (md5_computed, response["headers"]["etag"]))
        if response["headers"]["etag"].strip('"\'') != md5_hash.hexdigest():
            warning("MD5 Sums don't match!")
            if retries:
                warning("Retrying upload of %s" % (file.name))
                return self.send_file(request, file, labels, buffer, throttle, retries - 1, offset, chunk_size)
            else:
                warning("Too many failures. Giving up on '%s'" % (file.name))
                raise S3UploadError

        return response

    def send_file_multipart(self, file, headers, uri, size):
        chunk_size = self.config.multipart_chunk_size_mb * 1024 * 1024
        timestamp_start = time.time()
        upload = MultiPartUpload(self, file, uri, headers)
        upload.upload_all_parts()
        response = upload.complete_multipart_upload()
        timestamp_end = time.time()
        response["elapsed"] = timestamp_end - timestamp_start
        response["size"] = size
        response["speed"] = response["elapsed"] and float(response["size"]) / response["elapsed"] or float(-1)
        return response

    def recv_file(self, request, stream, labels, start_position = 0, retries = _max_retries):
        method_string, resource, headers = request.get_triplet()
        if self.config.progress_meter:
            progress = self.config.progress_class(labels, 0)
        else:
            info("Receiving file '%s', please wait..." % stream.name)
        timestamp_start = time.time()
        try:
            conn = ConnMan.get(self.get_hostname(resource['bucket']))
            conn.c.putrequest(method_string, self.format_uri(resource))
            for header in headers.keys():
                conn.c.putheader(header, str(headers[header]))
            if start_position > 0:
                debug("Requesting Range: %d .. end" % start_position)
                conn.c.putheader("Range", "bytes=%d-" % start_position)
            conn.c.endheaders()
            response = {}
            http_response = conn.c.getresponse()
            response["status"] = http_response.status
            response["reason"] = http_response.reason
            response["headers"] = convertTupleListToDict(http_response.getheaders())
            if response["headers"].has_key("x-amz-meta-s3cmd-attrs"):
                attrs = parse_attrs_header(response["headers"]["x-amz-meta-s3cmd-attrs"])
                response["s3cmd-attrs"] = attrs
            debug("Response: %s" % response)
        except ParameterError, e:
            raise
        except (IOError, OSError), e:
            raise
        except Exception, e:
            if self.config.progress_meter:
                progress.done("failed")
            if retries:
                warning("Retrying failed request: %s (%s)" % (resource['uri'], e))
                warning("Waiting %d sec..." % self._fail_wait(retries))
                time.sleep(self._fail_wait(retries))
                # Connection error -> same throttle value
                return self.recv_file(request, stream, labels, start_position, retries - 1)
            else:
                raise S3DownloadError("Download failed for: %s" % resource['uri'])

        if response["status"] == 307:
            ## RedirectPermanent
            response['data'] = http_response.read()
            redir_bucket = getTextFromXml(response['data'], ".//Bucket")
            redir_hostname = getTextFromXml(response['data'], ".//Endpoint")
            self.set_hostname(redir_bucket, redir_hostname)
            warning("Redirected to: %s" % (redir_hostname))
            return self.recv_file(request, stream, labels)

        if response["status"] < 200 or response["status"] > 299:
            raise S3Error(response)

        if start_position == 0:
            # Only compute MD5 on the fly if we're downloading from beginning
            # Otherwise we'd get a nonsense.
            md5_hash = md5()
        size_left = int(response["headers"]["content-length"])
        size_total = start_position + size_left
        current_position = start_position

        if self.config.progress_meter:
            progress.total_size = size_total
            progress.initial_position = current_position
            progress.current_position = current_position

        try:
            while (current_position < size_total):
                this_chunk = size_left > self.config.recv_chunk and self.config.recv_chunk or size_left
                data = http_response.read(this_chunk)
                if len(data) == 0:
                    raise S3Error("EOF from S3!")

                stream.write(data)
                if start_position == 0:
                    md5_hash.update(data)
                current_position += len(data)
                ## Call progress meter from here...
                if self.config.progress_meter:
                    progress.update(delta_position = len(data))
            ConnMan.put(conn)
        except (IOError, OSError), e:
            raise
        except Exception, e:
            if self.config.progress_meter:
                progress.done("failed")
            if retries:
                warning("Retrying failed request: %s (%s)" % (resource['uri'], e))
                warning("Waiting %d sec..." % self._fail_wait(retries))
                time.sleep(self._fail_wait(retries))
                # Connection error -> same throttle value
                return self.recv_file(request, stream, labels, current_position, retries - 1)
            else:
                raise S3DownloadError("Download failed for: %s" % resource['uri'])

        stream.flush()
        timestamp_end = time.time()

        if self.config.progress_meter:
            ## The above stream.flush() may take some time -> update() progress meter
            ## to correct the average speed. Otherwise people will complain that
            ## 'progress' and response["speed"] are inconsistent ;-)
            progress.update()
            progress.done("done")

        if start_position == 0:
            # Only compute MD5 on the fly if we were downloading from the beginning
            response["md5"] = md5_hash.hexdigest()
        else:
            # Otherwise try to compute MD5 of the output file
            try:
                response["md5"] = hash_file_md5(stream.name)
            except IOError, e:
                if e.errno != errno.ENOENT:
                    warning("Unable to open file: %s: %s" % (stream.name, e))
                warning("Unable to verify MD5. Assume it matches.")
                response["md5"] = response["headers"]["etag"]

        md5_hash = response["headers"]["etag"]
        if not 'x-amz-meta-s3tools-gpgenc' in response["headers"]:
            # we can't trust our stored md5 because we
            # encrypted the file after calculating it but before
            # uploading it.
            try:
                md5_hash = response["s3cmd-attrs"]["md5"]
            except KeyError:
                pass

        response["md5match"] = md5_hash.find(response["md5"]) >= 0
        response["elapsed"] = timestamp_end - timestamp_start
        response["size"] = current_position
        response["speed"] = response["elapsed"] and float(response["size"]) / response["elapsed"] or float(-1)
        if response["size"] != start_position + long(response["headers"]["content-length"]):
            warning("Reported size (%s) does not match received size (%s)" % (
                start_position + response["headers"]["content-length"], response["size"]))
        debug("ReceiveFile: Computed MD5 = %s" % response["md5"])
        if not response["md5match"]:
            warning("MD5 signatures do not match: computed=%s, received=%s" % (
                response["md5"], md5_hash))
        return response
__all__.append("S3")

def parse_attrs_header(attrs_header):
    attrs = {}
    for attr in attrs_header.split("/"):
        key, val = attr.split(":")
        attrs[key] = val
    return attrs

def compute_content_md5(body):
    m = md5(body)
    base64md5 = base64.encodestring(m.digest())
    if base64md5[-1] == '\n':
        base64md5 = base64md5[0:-1]
    return base64md5
# vim:et:ts=4:sts=4:ai

########NEW FILE########
__FILENAME__ = S3Uri
## Amazon S3 manager
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2
## Copyright: TGRMN Software and contributors

import os
import re
import sys
from BidirMap import BidirMap
from logging import debug
import S3
from Utils import unicodise, check_bucket_name_dns_conformity
import Config

class S3Uri(object):
    type = None
    _subclasses = None

    def __new__(self, string):
        if not self._subclasses:
            ## Generate a list of all subclasses of S3Uri
            self._subclasses = []
            dict = sys.modules[__name__].__dict__
            for something in dict:
                if type(dict[something]) is not type(self):
                    continue
                if issubclass(dict[something], self) and dict[something] != self:
                    self._subclasses.append(dict[something])
        for subclass in self._subclasses:
            try:
                instance = object.__new__(subclass)
                instance.__init__(string)
                return instance
            except ValueError, e:
                continue
        raise ValueError("%s: not a recognized URI" % string)

    def __str__(self):
        return self.uri()

    def __unicode__(self):
        return self.uri()

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.__unicode__())

    def public_url(self):
        raise ValueError("This S3 URI does not have Anonymous URL representation")

    def basename(self):
        return self.__unicode__().split("/")[-1]

class S3UriS3(S3Uri):
    type = "s3"
    _re = re.compile("^s3://([^/]+)/?(.*)", re.IGNORECASE)
    def __init__(self, string):
        match = self._re.match(string)
        if not match:
            raise ValueError("%s: not a S3 URI" % string)
        groups = match.groups()
        self._bucket = groups[0]
        self._object = unicodise(groups[1])

    def bucket(self):
        return self._bucket

    def object(self):
        return self._object

    def has_bucket(self):
        return bool(self._bucket)

    def has_object(self):
        return bool(self._object)

    def uri(self):
        return u"/".join([u"s3:/", self._bucket, self._object])

    def is_dns_compatible(self):
        return check_bucket_name_dns_conformity(self._bucket)

    def public_url(self):
        if self.is_dns_compatible():
            return "http://%s.%s/%s" % (self._bucket, Config.Config().host_base, self._object)
        else:
            return "http://%s/%s/%s" % (Config.Config().host_base, self._bucket, self._object)

    def host_name(self):
        if self.is_dns_compatible():
            return "%s.s3.amazonaws.com" % (self._bucket)
        else:
            return "s3.amazonaws.com"

    @staticmethod
    def compose_uri(bucket, object = ""):
        return "s3://%s/%s" % (bucket, object)

    @staticmethod
    def httpurl_to_s3uri(http_url):
        m=re.match("(https?://)?([^/]+)/?(.*)", http_url, re.IGNORECASE)
        hostname, object = m.groups()[1:]
        hostname = hostname.lower()
        if hostname == "s3.amazonaws.com":
            ## old-style url: http://s3.amazonaws.com/bucket/object
            if object.count("/") == 0:
                ## no object given
                bucket = object
                object = ""
            else:
                ## bucket/object
                bucket, object = object.split("/", 1)
        elif hostname.endswith(".s3.amazonaws.com"):
            ## new-style url: http://bucket.s3.amazonaws.com/object
            bucket = hostname[:-(len(".s3.amazonaws.com"))]
        else:
            raise ValueError("Unable to parse URL: %s" % http_url)
        return S3Uri("s3://%(bucket)s/%(object)s" % {
            'bucket' : bucket,
            'object' : object })

class S3UriS3FS(S3Uri):
    type = "s3fs"
    _re = re.compile("^s3fs://([^/]*)/?(.*)", re.IGNORECASE)
    def __init__(self, string):
        match = self._re.match(string)
        if not match:
            raise ValueError("%s: not a S3fs URI" % string)
        groups = match.groups()
        self._fsname = groups[0]
        self._path = unicodise(groups[1]).split("/")

    def fsname(self):
        return self._fsname

    def path(self):
        return "/".join(self._path)

    def uri(self):
        return "/".join(["s3fs:/", self._fsname, self.path()])

class S3UriFile(S3Uri):
    type = "file"
    _re = re.compile("^(\w+://)?(.*)")
    def __init__(self, string):
        match = self._re.match(string)
        groups = match.groups()
        if groups[0] not in (None, "file://"):
            raise ValueError("%s: not a file:// URI" % string)
        self._path = unicodise(groups[1]).split("/")

    def path(self):
        return "/".join(self._path)

    def uri(self):
        return "/".join(["file:/", self.path()])

    def isdir(self):
        return os.path.isdir(self.path())

    def dirname(self):
        return os.path.dirname(self.path())

class S3UriCloudFront(S3Uri):
    type = "cf"
    _re = re.compile("^cf://([^/]*)/*(.*)", re.IGNORECASE)
    def __init__(self, string):
        match = self._re.match(string)
        if not match:
            raise ValueError("%s: not a CloudFront URI" % string)
        groups = match.groups()
        self._dist_id = groups[0]
        self._request_id = groups[1] != "/" and groups[1] or None

    def dist_id(self):
        return self._dist_id

    def request_id(self):
        return self._request_id

    def uri(self):
        uri = "cf://" + self.dist_id()
        if self.request_id():
            uri += "/" + self.request_id()
        return uri

if __name__ == "__main__":
    uri = S3Uri("s3://bucket/object")
    print "type()  =", type(uri)
    print "uri     =", uri
    print "uri.type=", uri.type
    print "bucket  =", uri.bucket()
    print "object  =", uri.object()
    print

    uri = S3Uri("s3://bucket")
    print "type()  =", type(uri)
    print "uri     =", uri
    print "uri.type=", uri.type
    print "bucket  =", uri.bucket()
    print

    uri = S3Uri("s3fs://filesystem1/path/to/remote/file.txt")
    print "type()  =", type(uri)
    print "uri     =", uri
    print "uri.type=", uri.type
    print "path    =", uri.path()
    print

    uri = S3Uri("/path/to/local/file.txt")
    print "type()  =", type(uri)
    print "uri     =", uri
    print "uri.type=", uri.type
    print "path    =", uri.path()
    print

    uri = S3Uri("cf://1234567890ABCD/")
    print "type()  =", type(uri)
    print "uri     =", uri
    print "uri.type=", uri.type
    print "dist_id =", uri.dist_id()
    print

# vim:et:ts=4:sts=4:ai

########NEW FILE########
__FILENAME__ = SortedDict
## Amazon S3 manager
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2
## Copyright: TGRMN Software and contributors

from BidirMap import BidirMap
import Utils

class SortedDictIterator(object):
    def __init__(self, sorted_dict, keys):
        self.sorted_dict = sorted_dict
        self.keys = keys

    def next(self):
        try:
            return self.keys.pop(0)
        except IndexError:
            raise StopIteration

class SortedDict(dict):
    def __init__(self, mapping = {}, ignore_case = True, **kwargs):
        """
        WARNING: SortedDict() with ignore_case==True will
                 drop entries differing only in capitalisation!
                 Eg: SortedDict({'auckland':1, 'Auckland':2}).keys() => ['Auckland']
                 With ignore_case==False it's all right
        """
        dict.__init__(self, mapping, **kwargs)
        self.ignore_case = ignore_case

    def keys(self):
        keys = dict.keys(self)
        if self.ignore_case:
            # Translation map
            xlat_map = BidirMap()
            for key in keys:
                xlat_map[key.lower()] = key
            # Lowercase keys
            lc_keys = xlat_map.keys()
            lc_keys.sort()
            return [xlat_map[k] for k in lc_keys]
        else:
            keys.sort()
            return keys

    def __iter__(self):
        return SortedDictIterator(self, self.keys())

    def __getslice__(self, i=0, j=-1):
        keys = self.keys()[i:j]
        r = SortedDict(ignore_case = self.ignore_case)
        for k in keys:
            r[k] = self[k]
        return r


if __name__ == "__main__":
    d = { 'AWS' : 1, 'Action' : 2, 'america' : 3, 'Auckland' : 4, 'America' : 5 }
    sd = SortedDict(d)
    print "Wanted: Action, america, Auckland, AWS,    [ignore case]"
    print "Got:   ",
    for key in sd:
        print "%s," % key,
    print "   [used: __iter__()]"
    d = SortedDict(d, ignore_case = False)
    print "Wanted: AWS, Action, Auckland, america,    [case sensitive]"
    print "Got:   ",
    for key in d.keys():
        print "%s," % key,
    print "   [used: keys()]"

# vim:et:ts=4:sts=4:ai

########NEW FILE########
__FILENAME__ = Utils
## Amazon S3 manager
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2
## Copyright: TGRMN Software and contributors

import datetime
import os
import sys
import time
import re
import string
import random
import rfc822
import hmac
import base64
import errno
import urllib
from calendar import timegm
from logging import debug, info, warning, error
from ExitCodes import EX_OSFILE
try:
    import dateutil.parser
except ImportError:
    sys.stderr.write(u"""
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
ImportError trying to import dateutil.parser.
Please install the python dateutil module:
$ sudo apt-get install python-dateutil
  or
$ sudo yum install python-dateutil
  or
$ pip install python-dateutil
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
""")
    sys.stderr.flush()
    sys.exit(EX_OSFILE)

import Config
import Exceptions

# hashlib backported to python 2.4 / 2.5 is not compatible with hmac!
if sys.version_info[0] == 2 and sys.version_info[1] < 6:
    from md5 import md5
    import sha as sha1
else:
    from hashlib import md5, sha1

try:
    import xml.etree.ElementTree as ET
except ImportError:
    import elementtree.ElementTree as ET
from xml.parsers.expat import ExpatError

__all__ = []
def parseNodes(nodes):
    ## WARNING: Ignores text nodes from mixed xml/text.
    ## For instance <tag1>some text<tag2>other text</tag2></tag1>
    ## will be ignore "some text" node
    retval = []
    for node in nodes:
        retval_item = {}
        for child in node.getchildren():
            name = child.tag
            if child.getchildren():
                retval_item[name] = parseNodes([child])
            else:
                retval_item[name] = node.findtext(".//%s" % child.tag)
        retval.append(retval_item)
    return retval
__all__.append("parseNodes")

def stripNameSpace(xml):
    """
    removeNameSpace(xml) -- remove top-level AWS namespace
    """
    r = re.compile('^(<?[^>]+?>\s?)(<\w+) xmlns=[\'"](http://[^\'"]+)[\'"](.*)', re.MULTILINE)
    if r.match(xml):
        xmlns = r.match(xml).groups()[2]
        xml = r.sub("\\1\\2\\4", xml)
    else:
        xmlns = None
    return xml, xmlns
__all__.append("stripNameSpace")

def getTreeFromXml(xml):
    xml, xmlns = stripNameSpace(xml)
    try:
        tree = ET.fromstring(xml)
        if xmlns:
            tree.attrib['xmlns'] = xmlns
        return tree
    except ExpatError, e:
        error(e)
        raise Exceptions.ParameterError("Bucket contains invalid filenames. Please run: s3cmd fixbucket s3://your-bucket/")
    except Exception, e:
        error(e)
        error(xml)
        raise

__all__.append("getTreeFromXml")

def getListFromXml(xml, node):
    tree = getTreeFromXml(xml)
    nodes = tree.findall('.//%s' % (node))
    return parseNodes(nodes)
__all__.append("getListFromXml")

def getDictFromTree(tree):
    ret_dict = {}
    for child in tree.getchildren():
        if child.getchildren():
            ## Complex-type child. Recurse
            content = getDictFromTree(child)
        else:
            content = child.text
        if ret_dict.has_key(child.tag):
            if not type(ret_dict[child.tag]) == list:
                ret_dict[child.tag] = [ret_dict[child.tag]]
            ret_dict[child.tag].append(content or "")
        else:
            ret_dict[child.tag] = content or ""
    return ret_dict
__all__.append("getDictFromTree")

def getTextFromXml(xml, xpath):
    tree = getTreeFromXml(xml)
    if tree.tag.endswith(xpath):
        return tree.text
    else:
        return tree.findtext(xpath)
__all__.append("getTextFromXml")

def getRootTagName(xml):
    tree = getTreeFromXml(xml)
    return tree.tag
__all__.append("getRootTagName")

def xmlTextNode(tag_name, text):
    el = ET.Element(tag_name)
    el.text = unicode(text)
    return el
__all__.append("xmlTextNode")

def appendXmlTextNode(tag_name, text, parent):
    """
    Creates a new <tag_name> Node and sets
    its content to 'text'. Then appends the
    created Node to 'parent' element if given.
    Returns the newly created Node.
    """
    el = xmlTextNode(tag_name, text)
    parent.append(el)
    return el
__all__.append("appendXmlTextNode")

def dateS3toPython(date):
    # Reset milliseconds to 000
    date = re.compile('\.[0-9]*(?:[Z\\-\\+]*?)').sub(".000", date)
    return dateutil.parser.parse(date, fuzzy=True)
__all__.append("dateS3toPython")

def dateS3toUnix(date):
    ## NOTE: This is timezone-aware and return the timestamp regarding GMT
    return timegm(dateS3toPython(date).utctimetuple())
__all__.append("dateS3toUnix")

def dateRFC822toPython(date):
    return dateutil.parser.parse(date, fuzzy=True)
__all__.append("dateRFC822toPython")

def dateRFC822toUnix(date):
    return timegm(dateRFC822toPython(date).utctimetuple())
__all__.append("dateRFC822toUnix")

def formatSize(size, human_readable = False, floating_point = False):
    size = floating_point and float(size) or int(size)
    if human_readable:
        coeffs = ['k', 'M', 'G', 'T']
        coeff = ""
        while size > 2048:
            size /= 1024
            coeff = coeffs.pop(0)
        return (size, coeff)
    else:
        return (size, "")
__all__.append("formatSize")

def formatDateTime(s3timestamp):
    date_obj = dateutil.parser.parse(s3timestamp, fuzzy=True)
    return date_obj.strftime("%Y-%m-%d %H:%M")
__all__.append("formatDateTime")

def convertTupleListToDict(list):
    retval = {}
    for tuple in list:
        retval[tuple[0]] = tuple[1]
    return retval
__all__.append("convertTupleListToDict")

_rnd_chars = string.ascii_letters+string.digits
_rnd_chars_len = len(_rnd_chars)
def rndstr(len):
    retval = ""
    while len > 0:
        retval += _rnd_chars[random.randint(0, _rnd_chars_len-1)]
        len -= 1
    return retval
__all__.append("rndstr")

def mktmpsomething(prefix, randchars, createfunc):
    old_umask = os.umask(0077)
    tries = 5
    while tries > 0:
        dirname = prefix + rndstr(randchars)
        try:
            createfunc(dirname)
            break
        except OSError, e:
            if e.errno != errno.EEXIST:
                os.umask(old_umask)
                raise
        tries -= 1

    os.umask(old_umask)
    return dirname
__all__.append("mktmpsomething")

def mktmpdir(prefix = os.getenv('TMP','/tmp') + "/tmpdir-", randchars = 10):
    return mktmpsomething(prefix, randchars, os.mkdir)
__all__.append("mktmpdir")

def mktmpfile(prefix = os.getenv('TMP','/tmp') + "/tmpfile-", randchars = 20):
    createfunc = lambda filename : os.close(os.open(filename, os.O_CREAT | os.O_EXCL))
    return mktmpsomething(prefix, randchars, createfunc)
__all__.append("mktmpfile")

def hash_file_md5(filename):
    h = md5()
    f = open(filename, "rb")
    while True:
        # Hash 32kB chunks
        data = f.read(32*1024)
        if not data:
            break
        h.update(data)
    f.close()
    return h.hexdigest()
__all__.append("hash_file_md5")

def mkdir_with_parents(dir_name):
    """
    mkdir_with_parents(dst_dir)

    Create directory 'dir_name' with all parent directories

    Returns True on success, False otherwise.
    """
    pathmembers = dir_name.split(os.sep)
    tmp_stack = []
    while pathmembers and not os.path.isdir(os.sep.join(pathmembers)):
        tmp_stack.append(pathmembers.pop())
    while tmp_stack:
        pathmembers.append(tmp_stack.pop())
        cur_dir = os.sep.join(pathmembers)
        try:
            debug("mkdir(%s)" % cur_dir)
            os.mkdir(cur_dir)
        except (OSError, IOError), e:
            warning("%s: can not make directory: %s" % (cur_dir, e.strerror))
            return False
        except Exception, e:
            warning("%s: %s" % (cur_dir, e))
            return False
    return True
__all__.append("mkdir_with_parents")

def unicodise(string, encoding = None, errors = "replace"):
    """
    Convert 'string' to Unicode or raise an exception.
    """

    if not encoding:
        encoding = Config.Config().encoding

    if type(string) == unicode:
        return string
    debug("Unicodising %r using %s" % (string, encoding))
    try:
        return string.decode(encoding, errors)
    except UnicodeDecodeError:
        raise UnicodeDecodeError("Conversion to unicode failed: %r" % string)
__all__.append("unicodise")

def deunicodise(string, encoding = None, errors = "replace"):
    """
    Convert unicode 'string' to <type str>, by default replacing
    all invalid characters with '?' or raise an exception.
    """

    if not encoding:
        encoding = Config.Config().encoding

    if type(string) != unicode:
        return str(string)
    debug("DeUnicodising %r using %s" % (string, encoding))
    try:
        return string.encode(encoding, errors)
    except UnicodeEncodeError:
        raise UnicodeEncodeError("Conversion from unicode failed: %r" % string)
__all__.append("deunicodise")

def unicodise_safe(string, encoding = None):
    """
    Convert 'string' to Unicode according to current encoding
    and replace all invalid characters with '?'
    """

    return unicodise(deunicodise(string, encoding), encoding).replace(u'\ufffd', '?')
__all__.append("unicodise_safe")

def replace_nonprintables(string):
    """
    replace_nonprintables(string)

    Replaces all non-printable characters 'ch' in 'string'
    where ord(ch) <= 26 with ^@, ^A, ... ^Z
    """
    new_string = ""
    modified = 0
    for c in string:
        o = ord(c)
        if (o <= 31):
            new_string += "^" + chr(ord('@') + o)
            modified += 1
        elif (o == 127):
            new_string += "^?"
            modified += 1
        else:
            new_string += c
    if modified and Config.Config().urlencoding_mode != "fixbucket":
        warning("%d non-printable characters replaced in: %s" % (modified, new_string))
    return new_string
__all__.append("replace_nonprintables")

def sign_string(string_to_sign):
    """Sign a string with the secret key, returning base64 encoded results.
    By default the configured secret key is used, but may be overridden as
    an argument.

    Useful for REST authentication. See http://s3.amazonaws.com/doc/s3-developer-guide/RESTAuthentication.html
    """
    signature = base64.encodestring(hmac.new(Config.Config().secret_key, string_to_sign, sha1).digest()).strip()
    return signature
__all__.append("sign_string")

def sign_url(url_to_sign, expiry):
    """Sign a URL in s3://bucket/object form with the given expiry
    time. The object will be accessible via the signed URL until the
    AWS key and secret are revoked or the expiry time is reached, even
    if the object is otherwise private.

    See: http://s3.amazonaws.com/doc/s3-developer-guide/RESTAuthentication.html
    """
    return sign_url_base(
        bucket = url_to_sign.bucket(),
        object = url_to_sign.object(),
        expiry = expiry
    )
__all__.append("sign_url")

def sign_url_base(**parms):
    """Shared implementation of sign_url methods. Takes a hash of 'bucket', 'object' and 'expiry' as args."""
    parms['expiry']=time_to_epoch(parms['expiry'])
    parms['access_key']=Config.Config().access_key
    parms['host_base']=Config.Config().host_base
    debug("Expiry interpreted as epoch time %s", parms['expiry'])
    signtext = 'GET\n\n\n%(expiry)d\n/%(bucket)s/%(object)s' % parms
    debug("Signing plaintext: %r", signtext)
    parms['sig'] = urllib.quote_plus(sign_string(signtext))
    debug("Urlencoded signature: %s", parms['sig'])
    return "http://%(bucket)s.%(host_base)s/%(object)s?AWSAccessKeyId=%(access_key)s&Expires=%(expiry)d&Signature=%(sig)s" % parms

def time_to_epoch(t):
    """Convert time specified in a variety of forms into UNIX epoch time.
    Accepts datetime.datetime, int, anything that has a strftime() method, and standard time 9-tuples
    """
    if isinstance(t, int):
        # Already an int
        return t
    elif isinstance(t, tuple) or isinstance(t, time.struct_time):
        # Assume it's a time 9-tuple
        return int(time.mktime(t))
    elif hasattr(t, 'timetuple'):
        # Looks like a datetime object or compatible
        return int(time.mktime(t.timetuple()))
    elif hasattr(t, 'strftime'):
        # Looks like the object supports standard srftime()
        return int(t.strftime('%s'))
    elif isinstance(t, str) or isinstance(t, unicode):
        # See if it's a string representation of an epoch
        try:
            return int(t)
        except ValueError:
            # Try to parse it as a timestamp string
            try:
                return time.strptime(t)
            except ValueError, ex:
                # Will fall through
                debug("Failed to parse date with strptime: %s", ex)
                pass
    raise Exceptions.ParameterError('Unable to convert %r to an epoch time. Pass an epoch time. Try `date -d \'now + 1 year\' +%%s` (shell) or time.mktime (Python).' % t)


def check_bucket_name(bucket, dns_strict = True):
    if dns_strict:
        invalid = re.search("([^a-z0-9\.-])", bucket)
        if invalid:
            raise Exceptions.ParameterError("Bucket name '%s' contains disallowed character '%s'. The only supported ones are: lowercase us-ascii letters (a-z), digits (0-9), dot (.) and hyphen (-)." % (bucket, invalid.groups()[0]))
    else:
        invalid = re.search("([^A-Za-z0-9\._-])", bucket)
        if invalid:
            raise Exceptions.ParameterError("Bucket name '%s' contains disallowed character '%s'. The only supported ones are: us-ascii letters (a-z, A-Z), digits (0-9), dot (.), hyphen (-) and underscore (_)." % (bucket, invalid.groups()[0]))

    if len(bucket) < 3:
        raise Exceptions.ParameterError("Bucket name '%s' is too short (min 3 characters)" % bucket)
    if len(bucket) > 255:
        raise Exceptions.ParameterError("Bucket name '%s' is too long (max 255 characters)" % bucket)
    if dns_strict:
        if len(bucket) > 63:
            raise Exceptions.ParameterError("Bucket name '%s' is too long (max 63 characters)" % bucket)
        if re.search("-\.", bucket):
            raise Exceptions.ParameterError("Bucket name '%s' must not contain sequence '-.' for DNS compatibility" % bucket)
        if re.search("\.\.", bucket):
            raise Exceptions.ParameterError("Bucket name '%s' must not contain sequence '..' for DNS compatibility" % bucket)
        if not re.search("^[0-9a-z]", bucket):
            raise Exceptions.ParameterError("Bucket name '%s' must start with a letter or a digit" % bucket)
        if not re.search("[0-9a-z]$", bucket):
            raise Exceptions.ParameterError("Bucket name '%s' must end with a letter or a digit" % bucket)
    return True
__all__.append("check_bucket_name")

def check_bucket_name_dns_conformity(bucket):
    try:
        return check_bucket_name(bucket, dns_strict = True)
    except Exceptions.ParameterError:
        return False
__all__.append("check_bucket_name_dns_conformity")

def getBucketFromHostname(hostname):
    """
    bucket, success = getBucketFromHostname(hostname)

    Only works for hostnames derived from bucket names
    using Config.host_bucket pattern.

    Returns bucket name and a boolean success flag.
    """

    # Create RE pattern from Config.host_bucket
    pattern = Config.Config().host_bucket % { 'bucket' : '(?P<bucket>.*)' }
    m = re.match(pattern, hostname)
    if not m:
        return (hostname, False)
    return m.groups()[0], True
__all__.append("getBucketFromHostname")

def getHostnameFromBucket(bucket):
    return Config.Config().host_bucket % { 'bucket' : bucket }
__all__.append("getHostnameFromBucket")


def calculateChecksum(buffer, mfile, offset, chunk_size, send_chunk):
    md5_hash = md5()
    size_left = chunk_size
    if buffer == '':
        mfile.seek(offset)
        while size_left > 0:
            data = mfile.read(min(send_chunk, size_left))
            md5_hash.update(data)
            size_left -= len(data)
    else:
        md5_hash.update(buffer)

    return md5_hash.hexdigest()


__all__.append("calculateChecksum")


# Deal with the fact that pwd and grp modules don't exist for Windows
try:
    import pwd
    def getpwuid_username(uid):
        """returns a username from the password databse for the given uid"""
        return pwd.getpwuid(uid).pw_name
except ImportError:
    import getpass
    def getpwuid_username(uid):
        return getpass.getuser()
__all__.append("getpwuid_username")

try:
    import grp
    def getgrgid_grpname(gid):
        """returns a groupname from the group databse for the given gid"""
        return  grp.getgrgid(gid).gr_name
except ImportError:
    def getgrgid_grpname(gid):
        return "nobody"

__all__.append("getgrgid_grpname")



# vim:et:ts=4:sts=4:ai


########NEW FILE########
