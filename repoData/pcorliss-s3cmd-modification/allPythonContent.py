__FILENAME__ = run-tests
#!/usr/bin/env python
# -*- coding=utf-8 -*-

## Amazon S3cmd - testsuite
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2

import sys
import os
import re
from subprocess import Popen, PIPE, STDOUT
import locale

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
		if type(_list) not in [ list, tuple ]:
			_list = [_list]

		if regexps == False:
			_list = [re.escape(item.encode(encoding, "replace")) for item in _list]

		return [re.compile(item, re.MULTILINE) for item in _list]

	global test_counter
	test_counter += 1
	print ("%3d  %s " % (test_counter, label)).ljust(30, "."),
	sys.stdout.flush()

	if run_tests.count(test_counter) == 0 or exclude_tests.count(test_counter) > 0:
		return skip()

	p = Popen(cmd_args, stdout = PIPE, stderr = STDOUT, universal_newlines = True)
	stdout, stderr = p.communicate()
	if retcode != p.returncode:
		return failure("retcode: %d, expected: %d" % (p.returncode, retcode))

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
		cmd = ['mkdir']
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

def test_flushdir(label, dir_name):
	test_rmdir(label + "(rm)", dir_name)
	return test_mkdir(label + "(mk)", dir_name)

bucket_prefix = ''
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
test_s3cmd("Remove test buckets", ['rb', '-r', pbucket(1), pbucket(2), pbucket(3)],
	must_find = [ "Bucket '%s/' removed" % pbucket(1),
		      "Bucket '%s/' removed" % pbucket(2),
		      "Bucket '%s/' removed" % pbucket(3) ])


## ====== Create one bucket (EU)
test_s3cmd("Create one bucket (EU)", ['mb', '--bucket-location=EU', pbucket(1)], 
	must_find = "Bucket '%s/' created" % pbucket(1))



## ====== Create multiple buckets
test_s3cmd("Create multiple buckets", ['mb', pbucket(2), pbucket(3)], 
	must_find = [ "Bucket '%s/' created" % pbucket(2), "Bucket '%s/' created" % pbucket(3)])


## ====== Invalid bucket name
test_s3cmd("Invalid bucket name", ["mb", "--bucket-location=EU", pbucket('EU')], 
	retcode = 1,
	must_find = "ERROR: Parameter problem: Bucket name '%s' contains disallowed character" % bucket('EU'), 
	must_not_find_re = "Bucket.*created")


## ====== Buckets list
test_s3cmd("Buckets list", ["ls"], 
	must_find = [ "autotest-1", "autotest-2", "Autotest-3" ], must_not_find_re = "autotest-EU")


## ====== Sync to S3
test_s3cmd("Sync to S3", ['sync', 'testsuite/', pbucket(1) + '/xyz/', '--exclude', '.svn/*', '--exclude', '*.png', '--no-encrypt', '--exclude-from', 'testsuite/exclude.encodings' ],
	must_find = [ "WARNING: 32 non-printable characters replaced in: crappy-file-name/too-crappy ^A^B^C^D^E^F^G^H^I^J^K^L^M^N^O^P^Q^R^S^T^U^V^W^X^Y^Z^[^\^]^^^_^? +-[\]^<>%%\"'#{}`&?.end",
	              "stored as '%s/xyz/crappy-file-name/too-crappy ^A^B^C^D^E^F^G^H^I^J^K^L^M^N^O^P^Q^R^S^T^U^V^W^X^Y^Z^[^\^]^^^_^? +-[\\]^<>%%%%\"'#{}`&?.end'" % pbucket(1) ],
	must_not_find_re = [ "\.svn/", "\.png$" ])

if have_encoding:
	## ====== Sync UTF-8 / GBK / ... to S3
	test_s3cmd("Sync %s to S3" % encoding, ['sync', 'testsuite/encodings/' + encoding, '%s/xyz/encodings/' % pbucket(1), '--exclude', '.svn/*', '--no-encrypt' ],
		must_find = [ u"File 'testsuite/encodings/%(encoding)s/%(pattern)s' stored as '%(pbucket)s/xyz/encodings/%(encoding)s/%(pattern)s'" % { 'encoding' : encoding, 'pattern' : enc_pattern , 'pbucket' : pbucket(1)} ])


## ====== List bucket content
must_find_re = [ u"DIR   %s/xyz/binary/$" % pbucket(1) , u"DIR   %s/xyz/etc/$" % pbucket(1) ]
must_not_find = [ u"random-crap.md5", u".svn" ]
test_s3cmd("List bucket content", ['ls', '%s/xyz/' % pbucket(1) ],
	must_find_re = must_find_re,
	must_not_find = must_not_find)


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


## ====== Clean up local destination dir
test_flushdir("Clean testsuite-out/", "testsuite-out")


## ====== Put public, guess MIME
test_s3cmd("Put public, guess MIME", ['put', '--guess-mime-type', '--acl-public', 'testsuite/etc/logo.png', '%s/xyz/etc/logo.png' % pbucket(1)],
	must_find = [ "stored as '%s/xyz/etc/logo.png'" % pbucket(1) ])


## ====== Retrieve from URL
if have_wget:
	test("Retrieve from URL", ['wget', '-O', 'testsuite-out/logo.png', 'http://%s.s3.amazonaws.com/xyz/etc/logo.png' % bucket(1)],
		must_find_re = [ 'logo.png.*saved \[22059/22059\]' ])


## ====== Change ACL to Private
test_s3cmd("Change ACL to Private", ['setacl', '--acl-private', '%s/xyz/etc/l*.png' % pbucket(1)],
	must_find = [ "logo.png: ACL set to Private" ])


## ====== Verify Private ACL
if have_wget:
	test("Verify Private ACL", ['wget', '-O', 'testsuite-out/logo.png', 'http://%s.s3.amazonaws.com/xyz/etc/logo.png' % bucket(1)],
		retcode = 1,
		must_find_re = [ 'ERROR 403: Forbidden' ])


## ====== Change ACL to Public
test_s3cmd("Change ACL to Public", ['setacl', '--acl-public', '--recursive', '%s/xyz/etc/' % pbucket(1) , '-v'],
	must_find = [ "logo.png: ACL set to Public" ])


## ====== Verify Public ACL
if have_wget:
	test("Verify Public ACL", ['wget', '-O', 'testsuite-out/logo.png', 'http://%s.s3.amazonaws.com/xyz/etc/logo.png' % bucket(1)],
		must_find_re = [ 'logo.png.*saved \[22059/22059\]' ])


## ====== Sync more to S3
test_s3cmd("Sync more to S3", ['sync', 'testsuite/', 's3://%s/xyz/' % bucket(1), '--no-encrypt' ],
	must_find = [ "File 'testsuite/.svn/entries' stored as '%s/xyz/.svn/entries' " % pbucket(1) ],
	must_not_find = [ "File 'testsuite/etc/linked.png' stored as '%s/xyz/etc/linked.png" % pbucket(1) ])
           


## ====== Rename within S3
test_s3cmd("Rename within S3", ['mv', '%s/xyz/etc/logo.png' % pbucket(1), '%s/xyz/etc2/Logo.PNG' % pbucket(1)],
	must_find = [ 'File %s/xyz/etc/logo.png moved to %s/xyz/etc2/Logo.PNG' % (pbucket(1), pbucket(1))])


## ====== Rename (NoSuchKey)
test_s3cmd("Rename (NoSuchKey)", ['mv', '%s/xyz/etc/logo.png' % pbucket(1), '%s/xyz/etc2/Logo.PNG' % pbucket(1)],
	retcode = 1,
	must_find_re = [ 'ERROR:.*NoSuchKey' ],
	must_not_find = [ 'File %s/xyz/etc/logo.png moved to %s/xyz/etc2/Logo.PNG' % (pbucket(1), pbucket(1)) ])


## ====== Sync more from S3
test_s3cmd("Sync more from S3", ['sync', '--delete-removed', '%s/xyz' % pbucket(1), 'testsuite-out'],
	must_find = [ "deleted: testsuite-out/logo.png",
	              "File '%s/xyz/etc2/Logo.PNG' stored as 'testsuite-out/xyz/etc2/Logo.PNG' (22059 bytes" % pbucket(1), 
	              "File '%s/xyz/.svn/entries' stored as 'testsuite-out/xyz/.svn/entries' " % pbucket(1) ],
	must_not_find_re = [ "not-deleted.*etc/logo.png" ])


## ====== Make dst dir for get
test_rmdir("Remove dst dir for get", "testsuite-out")


## ====== Get multiple files
test_s3cmd("Get multiple files", ['get', '%s/xyz/etc2/Logo.PNG' % pbucket(1), '%s/xyz/etc/AtomicClockRadio.ttf' % pbucket(1), 'testsuite-out'],
	retcode = 1,
	must_find = [ 'Destination must be a directory when downloading multiple sources.' ])


## ====== Make dst dir for get
test_mkdir("Make dst dir for get", "testsuite-out")


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
test_s3cmd("Recursive copy, set ACL", ['cp', '-r', '--acl-public', '%s/xyz/' % pbucket(1), '%s/copy' % pbucket(2), '--exclude', '.svn/*', '--exclude', 'too-crappy*'],
	must_find = [ "File %s/xyz/etc2/Logo.PNG copied to %s/copy/etc2/Logo.PNG" % (pbucket(1), pbucket(2)),
	              "File %s/xyz/blahBlah/Blah.txt copied to %s/copy/blahBlah/Blah.txt" % (pbucket(1), pbucket(2)),
	              "File %s/xyz/blahBlah/blah.txt copied to %s/copy/blahBlah/blah.txt" % (pbucket(1), pbucket(2)) ],
	must_not_find = [ ".svn" ])

## ====== Don't Put symbolic link
test_s3cmd("Don't put symbolic links", ['put', 'testsuite/etc/linked1.png', 's3://%s/xyz/' % bucket(1),],
	must_not_find_re = [ "linked1.png"])

## ====== Put symbolic link
test_s3cmd("Put symbolic links", ['put', 'testsuite/etc/linked1.png', 's3://%s/xyz/' % bucket(1),'--follow-symlinks' ],
           must_find = [ "File 'testsuite/etc/linked1.png' stored as '%s/xyz/linked1.png'" % pbucket(1)])

## ====== Sync symbolic links
test_s3cmd("Sync symbolic links", ['sync', 'testsuite/', 's3://%s/xyz/' % bucket(1), '--no-encrypt', '--follow-symlinks' ],
	must_find = ["File 'testsuite/etc/linked.png' stored as '%s/xyz/etc/linked.png'" % pbucket(1)],
           # Don't want to recursively copy linked directories!
           must_not_find_re = ["etc/more/linked-dir/more/give-me-more.txt",
                               "etc/brokenlink.png"],
           )

## ====== Verify ACL and MIME type
test_s3cmd("Verify ACL and MIME type", ['info', '%s/copy/etc2/Logo.PNG' % pbucket(2) ],
	must_find_re = [ "MIME type:.*image/png", 
	                 "ACL:.*\*anon\*: READ",
					 "URL:.*http://%s.s3.amazonaws.com/copy/etc2/Logo.PNG" % bucket(2) ])

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


## ====== Recursive delete
test_s3cmd("Recursive delete", ['del', '--recursive', '--exclude', 'Atomic*', '%s/xyz/etc' % pbucket(1)],
	must_find = [ "File %s/xyz/etc/TypeRa.ttf deleted" % pbucket(1) ],
	must_find_re = [ "File .*\.svn/entries deleted" ],
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

########NEW FILE########
__FILENAME__ = AccessLog
## Amazon S3 - Access Control List representation
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2

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

########NEW FILE########
__FILENAME__ = ACL
## Amazon S3 - Access Control List representation
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2

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

		name = name.lower()
		permission = permission.upper()

		if "ALL" == permission:
			permission = "FULL_CONTROL"

		if "FULL_CONTROL" == permission:
			self.revoke(name, "ALL")

		grantee = Grantee()
		grantee.name = name
		grantee.permission = permission

		if  name.find('@') <= -1: # ultra lame attempt to differenciate emails id from canonical ids
			grantee.xsi_type = "CanonicalUser"
			grantee.tag = "ID"
		else:
			grantee.xsi_type = "AmazonCustomerByEmail"
			grantee.tag = "EmailAddress"
				
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

########NEW FILE########
__FILENAME__ = BidirMap
## Amazon S3 manager
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2

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

########NEW FILE########
__FILENAME__ = CloudFront
## Amazon CloudFront support
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2

import sys
import time
import httplib
from logging import debug, info, warning, error

try:
	import xml.etree.ElementTree as ET
except ImportError:
	import elementtree.ElementTree as ET

from Config import Config
from Exceptions import *
from Utils import getTreeFromXml, appendXmlTextNode, getDictFromTree, dateS3toPython, sign_string, getBucketFromHostname, getHostnameFromBucket
from S3Uri import S3Uri, S3UriS3

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
	##	<Id>1234567890ABC</Id>
	##	<Status>Deployed</Status>
	##	<LastModifiedTime>2009-01-16T11:49:02.189Z</LastModifiedTime>
	##	<DomainName>blahblahblah.cloudfront.net</DomainName>
	##	<Origin>example.bucket.s3.amazonaws.com</Origin>
	##	<Enabled>true</Enabled>
	## </DistributionSummary>

	def __init__(self, tree):
		if tree.tag != "DistributionSummary":
			raise ValueError("Expected <DistributionSummary /> xml, got: <%s />" % tree.tag)
		self.parse(tree)

	def parse(self, tree):
		self.info = getDictFromTree(tree)
		self.info['Enabled'] = (self.info['Enabled'].lower() == "true")

	def uri(self):
		return S3Uri("cf://%s" % self.info['Id'])

class DistributionList(object):
	## Example:
	## 
	## <DistributionList xmlns="http://cloudfront.amazonaws.com/doc/2010-06-01/">
	##	<Marker />
	##	<MaxItems>100</MaxItems>
	##	<IsTruncated>false</IsTruncated>
	##	<DistributionSummary>
	##	... handled by DistributionSummary() class ...
	##	</DistributionSummary>
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
	## <Distribution xmlns="http://cloudfront.amazonaws.com/doc/2010-06-01/">
	##	<Id>1234567890ABC</Id>
	##	<Status>InProgress</Status>
	##	<LastModifiedTime>2009-01-16T13:07:11.319Z</LastModifiedTime>
	##	<DomainName>blahblahblah.cloudfront.net</DomainName>
	##	<DistributionConfig>
	##	... handled by DistributionConfig() class ...
	##	</DistributionConfig>
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
	##	<Origin>somebucket.s3.amazonaws.com</Origin>
	##	<CallerReference>s3://somebucket/</CallerReference>
	##	<Comment>http://somebucket.s3.amazonaws.com/</Comment>
	##	<Enabled>true</Enabled>
	##  <Logging>
	##    <Bucket>bu.ck.et</Bucket>
	##    <Prefix>/cf-somebucket/</Prefix>
	##  </Logging>
	## </DistributionConfig>

	EMPTY_CONFIG = "<DistributionConfig><Origin/><CallerReference/><Enabled>true</Enabled></DistributionConfig>"
	xmlns = "http://cloudfront.amazonaws.com/doc/2010-06-01/"
	def __init__(self, xml = None, tree = None):
		if not xml:
			xml = DistributionConfig.EMPTY_CONFIG

		if not tree:
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
		appendXmlTextNode("Origin", self.info['Origin'], tree)
		appendXmlTextNode("CallerReference", self.info['CallerReference'], tree)
		for cname in self.info['CNAME']:
			appendXmlTextNode("CNAME", cname.lower(), tree)
		if self.info['Comment']:
			appendXmlTextNode("Comment", self.info['Comment'], tree)
		appendXmlTextNode("Enabled", str(self.info['Enabled']).lower(), tree)
		if self.info['Logging']:
			logging_el = ET.Element("Logging")
			appendXmlTextNode("Bucket", getHostnameFromBucket(self.info['Logging'].bucket()), logging_el)
			appendXmlTextNode("Prefix", self.info['Logging'].object(), logging_el)
			tree.append(logging_el)
		return ET.tostring(tree)

class CloudFront(object):
	operations = {
		"CreateDist" : { 'method' : "POST", 'resource' : "" },
		"DeleteDist" : { 'method' : "DELETE", 'resource' : "/%(dist_id)s" },
		"GetList" : { 'method' : "GET", 'resource' : "" },
		"GetDistInfo" : { 'method' : "GET", 'resource' : "/%(dist_id)s" },
		"GetDistConfig" : { 'method' : "GET", 'resource' : "/%(dist_id)s/config" },
		"SetDistConfig" : { 'method' : "PUT", 'resource' : "/%(dist_id)s/config" },
	}

	## Maximum attempts of re-issuing failed requests
	_max_retries = 5

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
	
	def CreateDistribution(self, uri, cnames_add = [], comment = None, logging = None):
		dist_config = DistributionConfig()
		dist_config.info['Enabled'] = True
		dist_config.info['Origin'] = uri.host_name()
		dist_config.info['CallerReference'] = str(uri)
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
	                       comment = None, enabled = None, logging = None):
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

	## --------------------------------------------------
	## Low-level methods for handling CloudFront requests
	## --------------------------------------------------

	def send_request(self, op_name, dist_id = None, body = None, headers = {}, retries = _max_retries):
		operation = self.operations[op_name]
		if body:
			headers['content-type'] = 'text/plain'
		request = self.create_request(operation, dist_id, headers)
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
				return self.send_request(op_name, dist_id, body, retries - 1)
			else:
				raise e

		if response["status"] < 200 or response["status"] > 299:
			raise CloudFrontError(response)

		return response

	def create_request(self, operation, dist_id = None, headers = None):
		resource = self.config.cloudfront_resource + (
		           operation['resource'] % { 'dist_id' : dist_id })

		if not headers:
			headers = {}

		if headers.has_key("date"):
			if not headers.has_key("x-amz-date"):
				headers["x-amz-date"] = headers["date"]
			del(headers["date"])
		
		if not headers.has_key("x-amz-date"):
			headers["x-amz-date"] = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())

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

		def option_list(self):
			return [opt for opt in dir(self) if opt.startswith("cf_")]

		def update_option(self, option, value):
			setattr(Cmd.options, option, value)

	options = Options()
	dist_list = None

	@staticmethod
	def _get_dist_name_for_bucket(uri):
		cf = CloudFront(Config())
		debug("_get_dist_name_for_bucket(%r)" % uri)
		assert(uri.type == "s3")
		if Cmd.dist_list is None:
			response = cf.GetList()
			Cmd.dist_list = {}
			for d in response['dist_list'].dist_summs:
				Cmd.dist_list[getBucketFromHostname(d.info['Origin'])[0]] = d.uri()
			debug("dist_list: %s" % Cmd.dist_list)
		return Cmd.dist_list[uri.bucket()]

	@staticmethod
	def _parse_args(args):
		cfuris = []
		for arg in args:
			uri = S3Uri(arg)
			if uri.type == 's3':
				try:
					uri = Cmd._get_dist_name_for_bucket(uri)
				except Exception, e:
					debug(e)
					raise ParameterError("Unable to translate S3 URI to CloudFront distribution name: %s" % uri)
			if uri.type != 'cf':
				raise ParameterError("CloudFront URI required instead of: %s" % arg)
			cfuris.append(uri)
		return cfuris

	@staticmethod
	def info(args):
		cf = CloudFront(Config())
		if not args:
			response = cf.GetList()
			for d in response['dist_list'].dist_summs:
				pretty_output("Origin", S3UriS3.httpurl_to_s3uri(d.info['Origin']))
				pretty_output("DistId", d.uri())
				pretty_output("DomainName", d.info['DomainName'])
				pretty_output("Status", d.info['Status'])
				pretty_output("Enabled", d.info['Enabled'])
				output("")
		else:
			cfuris = Cmd._parse_args(args)
			for cfuri in cfuris:
				response = cf.GetDistInfo(cfuri)
				d = response['distribution']
				dc = d.info['DistributionConfig']
				pretty_output("Origin", S3UriS3.httpurl_to_s3uri(dc.info['Origin']))
				pretty_output("DistId", d.uri())
				pretty_output("DomainName", d.info['DomainName'])
				pretty_output("Status", d.info['Status'])
				pretty_output("CNAMEs", ", ".join(dc.info['CNAME']))
				pretty_output("Comment", dc.info['Comment'])
				pretty_output("Enabled", dc.info['Enabled'])
				pretty_output("Logging", dc.info['Logging'] or "Disabled")
				pretty_output("Etag", response['headers']['etag'])

	@staticmethod
	def create(args):
		cf = CloudFront(Config())
		buckets = []
		for arg in args:
			uri = S3Uri(arg)
			if uri.type != "s3":
				raise ParameterError("Bucket can only be created from a s3:// URI instead of: %s" % arg)
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
			                                 logging = Cmd.options.cf_logging)
			d = response['distribution']
			dc = d.info['DistributionConfig']
			output("Distribution created:")
			pretty_output("Origin", S3UriS3.httpurl_to_s3uri(dc.info['Origin']))
			pretty_output("DistId", d.uri())
			pretty_output("DomainName", d.info['DomainName'])
			pretty_output("CNAMEs", ", ".join(dc.info['CNAME']))
			pretty_output("Comment", dc.info['Comment'])
			pretty_output("Status", d.info['Status'])
			pretty_output("Enabled", dc.info['Enabled'])
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
		                                 logging = Cmd.options.cf_logging)
		if response['status'] >= 400:
			error("Distribution %s could not be modified: %s" % (cfuri, response['reason']))
		output("Distribution modified: %s" % cfuri)
		response = cf.GetDistInfo(cfuri)
		d = response['distribution']
		dc = d.info['DistributionConfig']
		pretty_output("Origin", S3UriS3.httpurl_to_s3uri(dc.info['Origin']))
		pretty_output("DistId", d.uri())
		pretty_output("DomainName", d.info['DomainName'])
		pretty_output("Status", d.info['Status'])
		pretty_output("CNAMEs", ", ".join(dc.info['CNAME']))
		pretty_output("Comment", dc.info['Comment'])
		pretty_output("Enabled", dc.info['Enabled'])
		pretty_output("Etag", response['headers']['etag'])

########NEW FILE########
__FILENAME__ = Config
## Amazon S3 manager
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2

import logging
from logging import debug, info, warning, error
import re
import Progress
from SortedDict import SortedDict

class Config(object):
	_instance = None
	_parsed_files = []
	_doc = {}
	access_key = ""
	secret_key = ""
	host_base = "s3.amazonaws.com"
	host_bucket = "%(bucket)s.s3.amazonaws.com"
	simpledb_host = "sdb.amazonaws.com"
	cloudfront_host = "cloudfront.amazonaws.com"
	cloudfront_resource = "/2010-06-01/distribution"
	verbosity = logging.WARNING
	progress_meter = True
	progress_class = Progress.ProgressCR
	send_chunk = 4096
	recv_chunk = 4096
	list_md5 = False
	human_readable_sizes = False
	extra_headers = SortedDict(ignore_case = True)
	force = False
	enable = None
	get_continue = False
	skip_existing = False
	recursive = False
	acl_public = None
	acl_grants = []
	acl_revokes = []
	proxy_host = ""
	proxy_port = 3128
	encrypt = False
	dry_run = False
	preserve_attrs = True
	preserve_attrs_list = [ 
		'uname',	# Verbose owner Name (e.g. 'root')
		'uid',		# Numeric user ID (e.g. 0)
		'gname',	# Group name (e.g. 'users')
		'gid',		# Numeric group ID (e.g. 100)
		'atime',	# Last access timestamp
		'mtime',	# Modification timestamp
		'ctime',	# Creation timestamp
		'mode',		# File mode (e.g. rwxr-xr-x = 755)
		#'acl',		# Full ACL (not yet supported)
	]
	delete_removed = False
	_doc['delete_removed'] = "[sync] Remove remote S3 objects when local file has been deleted"
	gpg_passphrase = ""
	gpg_command = ""
	gpg_encrypt = "%(gpg_command)s -c --verbose --no-use-agent --batch --yes --passphrase-fd %(passphrase_fd)s -o %(output_file)s %(input_file)s"
	gpg_decrypt = "%(gpg_command)s -d --verbose --no-use-agent --batch --yes --passphrase-fd %(passphrase_fd)s -o %(output_file)s %(input_file)s"
	use_https = False
	bucket_location = "US"
	default_mime_type = "binary/octet-stream"
	guess_mime_type = True
	# List of checks to be performed for 'sync'
	sync_checks = ['size', 'md5']	# 'weak-timestamp'
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
	parallel = False
	workers = 10
	follow_symlinks=False

	## Creating a singleton
	def __new__(self, configfile = None):
		if self._instance is None:
			self._instance = object.__new__(self)
		return self._instance

	def __init__(self, configfile = None):
		if configfile:
			self.read_config_file(configfile)

	def option_list(self):
		retval = []
		for option in dir(self):
			## Skip attributes that start with underscore or are not string, int or bool
			option_type = type(getattr(Config, option))
			if option.startswith("_") or \
			   not (option_type in (
			   		type("string"),	# str
			        	type(42),	# int
					type(True))):	# bool
				continue
			retval.append(option)
		return retval

	def read_config_file(self, configfile):
		cp = ConfigParser(configfile)
		for option in self.option_list():
			self.update_option(option, cp.get(option))
		self._parsed_files.append(configfile)

	def dump_config(self, stream):
		ConfigDumper(stream).dump("default", self)

	def update_option(self, option, value):
		if value is None:
			return
		#### Special treatment of some options
		## verbosity must be known to "logging" module
		if option == "verbosity":
			try:
				setattr(Config, "verbosity", logging._levelNames[value])
			except KeyError:
				error("Config: verbosity level '%s' is not valid" % value)
		## allow yes/no, true/false, on/off and 1/0 for boolean options
		elif type(getattr(Config, option)) is type(True):	# bool
			if str(value).lower() in ("true", "yes", "on", "1"):
				setattr(Config, option, True)
			elif str(value).lower() in ("false", "no", "off", "0"):
				setattr(Config, option, False)
			else:
				error("Config: value of option '%s' must be Yes or No, not '%s'" % (option, value))
		elif type(getattr(Config, option)) is type(42):		# int
			try:
				setattr(Config, option, int(value))
			except ValueError, e:
				error("Config: value of option '%s' must be an integer, not '%s'" % (option, value))
		else:							# string
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
					print_value = (data["value"][:2]+"...%d_chars..."+data["value"][-1:]) % (len(data["value"]) - 3)
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
			self.stream.write("%s = %s\n" % (option, getattr(config, option)))


########NEW FILE########
__FILENAME__ = Exceptions
## Amazon S3 manager - Exceptions library
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2

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
		if response.has_key("data"):
			tree = getTreeFromXml(response["data"])
			error_node = tree
			if not error_node.tag == "Error":
				error_node = tree.find(".//Error")
			for child in error_node.getchildren():
				if child.text != "":
					debug("ErrorXML: " + child.tag + ": " + repr(child.text))
					self.info[child.tag] = child.text
		self.code = self.info["Code"]
		self.message = self.info["Message"]
		self.resource = self.info["Resource"]

	def __unicode__(self):
		retval = u"%d " % (self.status)
		retval += (u"(%s)" % (self.info.has_key("Code") and self.info["Code"] or self.reason))
		if self.info.has_key("Message"):
			retval += (u": %s" % self.info["Message"])
		return retval

class CloudFrontError(S3Error):
	pass
		
class S3UploadError(S3Exception):
	pass

class S3DownloadError(S3Exception):
	pass

class S3RequestError(S3Exception):
	pass

class InvalidFileError(S3Exception):
	pass

class ParameterError(S3Exception):
	pass

########NEW FILE########
__FILENAME__ = PkgInfo
package = "s3cmd"
version = "0.9.9.91"
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


########NEW FILE########
__FILENAME__ = Progress
## Amazon S3 manager
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2

import sys
import datetime
import Utils

class Progress(object):
	_stdout = sys.stdout

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
		#	no update, just call display()
		self.display()

	def done(self, message):
		self.display(done_message = message)

	def output_labels(self):
		self._stdout.write(u"%(source)s -> %(destination)s  %(extra)s\n" % self.labels)
		self._stdout.flush()

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

		rel_position = selfself.current_position * 100 / self.total_size
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

########NEW FILE########
__FILENAME__ = S3
## Amazon S3 manager
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2

import sys
import os, os.path
import time
import httplib
import logging
import mimetypes
import re
from logging import debug, info, warning, error
from stat import ST_SIZE

try:
	from hashlib import md5
except ImportError:
	from md5 import md5

from Utils import *
from SortedDict import SortedDict
from BidirMap import BidirMap
from Config import Config
from Exceptions import *
from ACL import ACL, GranteeLogDelivery
from AccessLog import AccessLog
from S3Uri import S3Uri

__all__ = []
class S3Request(object):
	def __init__(self, s3, method_string, resource, headers, params = {}):
		self.s3 = s3
		self.headers = SortedDict(headers or {}, ignore_case = True)
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
		resource = dict(self.resource)	## take a copy
		resource['uri'] += self.format_param_str()
		return (self.method_string, resource, self.headers)

class S3(object):
	http_methods = BidirMap(
		GET = 0x01,
		PUT = 0x02,
		HEAD = 0x04,
		DELETE = 0x08,
		MASK = 0x0F,
		)
	
	targets = BidirMap(
		SERVICE = 0x0100,
		BUCKET = 0x0200,
		OBJECT = 0x0400,
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

	def get_connection(self, bucket):
		if self.config.proxy_host != "":
			return httplib.HTTPConnection(self.config.proxy_host, self.config.proxy_port)
		else:
			if self.config.use_https:
				return httplib.HTTPSConnection(self.get_hostname(bucket))
			else:
				return httplib.HTTPConnection(self.get_hostname(bucket))

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
	
	def bucket_list(self, bucket, prefix = None, recursive = None):
		def _list_truncated(data):
			## <IsTruncated> can either be "true" or "false" or be missing completely
			is_truncated = getTextFromXml(data, ".//IsTruncated") or "false"
			return is_truncated.lower() != "false"

		def _get_contents(data):
			return getListFromXml(data, "Contents")

		def _get_common_prefixes(data):
			return getListFromXml(data, "CommonPrefixes")

		uri_params = {}
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

	def bucket_info(self, uri):
		request = self.create_request("BUCKET_LIST", bucket = uri.bucket(), extra = "?location")
		response = self.send_request(request)
		response['bucket-location'] = getTextFromXml(response['data'], "LocationConstraint") or "any"
		return response

	def object_put(self, filename, uri, extra_headers = None, extra_label = ""):
		# TODO TODO
		# Make it consistent with stream-oriented object_get()
		if uri.type != "s3":
			raise ValueError("Expected URI type 's3', got '%s'" % uri.type)

		if not os.path.isfile(filename):
			raise InvalidFileError(u"%s is not a regular file" % unicodise(filename))
		try:
			file = open(filename, "rb")
			size = os.stat(filename)[ST_SIZE]
		except IOError, e:
			raise InvalidFileError(u"%s: %s" % (unicodise(filename), e.strerror))
		headers = SortedDict(ignore_case = True)
		if extra_headers:
			headers.update(extra_headers)
		headers["content-length"] = size
		content_type = None
		if self.config.guess_mime_type:
			content_type = mimetypes.guess_type(filename)[0]
		if not content_type:
			content_type = self.config.default_mime_type
		debug("Content-Type set to '%s'" % content_type)
		headers["content-type"] = content_type
		if self.config.acl_public:
			headers["x-amz-acl"] = "public-read"
		if self.config.reduced_redundancy:
			headers["x-amz-storage-class"] = "REDUCED_REDUNDANCY"
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

	def object_delete(self, uri):
		if uri.type != "s3":
			raise ValueError("Expected URI type 's3', got '%s'" % uri.type)
		request = self.create_request("OBJECT_DELETE", uri = uri)
		response = self.send_request(request)
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
		# if extra_headers:
		# 	headers.update(extra_headers)
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
		for c in string:	# I'm not sure how to know in what encoding 
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
			elif (o == 0x20 or	# Space and below
			    o == 0x22 or	# "
			    o == 0x23 or	# #
			    o == 0x25 or	# % (escape character)
			    o == 0x26 or	# &
			    o == 0x2B or	# + (or it would become <space>)
			    o == 0x3C or	# <
			    o == 0x3E or	# >
			    o == 0x3F or	# ?
			    o == 0x60 or	# `
			    o >= 123):   	# { and above, including >= 128 for UTF-8
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
			conn = self.get_connection(resource['bucket'])
			conn.request(method_string, self.format_uri(resource), body, headers)
			response = {}
			http_response = conn.getresponse()
			response["status"] = http_response.status
			response["reason"] = http_response.reason
			response["headers"] = convertTupleListToDict(http_response.getheaders())
			response["data"] =  http_response.read()
			debug("Response: " + str(response))
			conn.close()
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

	def send_file(self, request, file, labels, throttle = 0, retries = _max_retries):
		method_string, resource, headers = request.get_triplet()
		size_left = size_total = headers.get("content-length")
		if self.config.progress_meter:
			progress = self.config.progress_class(labels, size_total)
		else:
			info("Sending file '%s', please wait..." % file.name)
		timestamp_start = time.time()
		try:
			conn = self.get_connection(resource['bucket'])
			conn.connect()
			conn.putrequest(method_string, self.format_uri(resource))
			for header in headers.keys():
				conn.putheader(header, str(headers[header]))
			conn.endheaders()
		except Exception, e:
			if self.config.progress_meter:
				progress.done("failed")
			if retries:
				warning("Retrying failed request: %s (%s)" % (resource['uri'], e))
				warning("Waiting %d sec..." % self._fail_wait(retries))
				time.sleep(self._fail_wait(retries))
				# Connection error -> same throttle value
				return self.send_file(request, file, labels, throttle, retries - 1)
			else:
				raise S3UploadError("Upload failed for: %s" % resource['uri'])
		file.seek(0)
		md5_hash = md5()
		try:
			while (size_left > 0):
				#debug("SendFile: Reading up to %d bytes from '%s'" % (self.config.send_chunk, file.name))
				data = file.read(self.config.send_chunk)
				md5_hash.update(data)
				conn.send(data)
				if self.config.progress_meter:
					progress.update(delta_position = len(data))
				size_left -= len(data)
				if throttle:
					time.sleep(throttle)
			md5_computed = md5_hash.hexdigest()
			response = {}
			http_response = conn.getresponse()
			response["status"] = http_response.status
			response["reason"] = http_response.reason
			response["headers"] = convertTupleListToDict(http_response.getheaders())
			response["data"] = http_response.read()
			response["size"] = size_total
			conn.close()
			debug(u"Response: %s" % response)
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
				return self.send_file(request, file, labels, throttle, retries - 1)
			else:
				debug("Giving up on '%s' %s" % (file.name, e))
				raise S3UploadError("Upload failed for: %s" % resource['uri'])

		timestamp_end = time.time()
		response["elapsed"] = timestamp_end - timestamp_start
		response["speed"] = response["elapsed"] and float(response["size"]) / response["elapsed"] or float(-1)

		if self.config.progress_meter:
			## The above conn.close() takes some time -> update() progress meter
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
			return self.send_file(request, file, labels)

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
					return self.send_file(request, file, labels, throttle, retries - 1)
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
				return self.send_file(request, file, labels, throttle, retries - 1)
			else:
				warning("Too many failures. Giving up on '%s'" % (file.name))
				raise S3UploadError

		return response

	def recv_file(self, request, stream, labels, start_position = 0, retries = _max_retries):
		method_string, resource, headers = request.get_triplet()
		if self.config.progress_meter:
			progress = self.config.progress_class(labels, 0)
		else:
			info("Receiving file '%s', please wait..." % stream.name)
		timestamp_start = time.time()
		try:
			conn = self.get_connection(resource['bucket'])
			conn.connect()
			conn.putrequest(method_string, self.format_uri(resource))
			for header in headers.keys():
				conn.putheader(header, str(headers[header]))
			if start_position > 0:
				debug("Requesting Range: %d .. end" % start_position)
				conn.putheader("Range", "bytes=%d-" % start_position)
			conn.endheaders()
			response = {}
			http_response = conn.getresponse()
			response["status"] = http_response.status
			response["reason"] = http_response.reason
			response["headers"] = convertTupleListToDict(http_response.getheaders())
			debug("Response: %s" % response)
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
				stream.write(data)
				if start_position == 0:
					md5_hash.update(data)
				current_position += len(data)
				## Call progress meter from here...
				if self.config.progress_meter:
					progress.update(delta_position = len(data))
			conn.close()
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

		response["md5match"] = response["headers"]["etag"].find(response["md5"]) >= 0
		response["elapsed"] = timestamp_end - timestamp_start
		response["size"] = current_position
		response["speed"] = response["elapsed"] and float(response["size"]) / response["elapsed"] or float(-1)
		if response["size"] != start_position + long(response["headers"]["content-length"]):
			warning("Reported size (%s) does not match received size (%s)" % (
				start_position + response["headers"]["content-length"], response["size"]))
		debug("ReceiveFile: Computed MD5 = %s" % response["md5"])
		if not response["md5match"]:
			warning("MD5 signatures do not match: computed=%s, received=%s" % (
				response["md5"], response["headers"]["etag"]))
		return response
__all__.append("S3")

########NEW FILE########
__FILENAME__ = S3Uri
## Amazon S3 manager
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2

import os
import re
import sys
from BidirMap import BidirMap
from logging import debug
import S3
from Utils import unicodise, check_bucket_name_dns_conformity

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
		return "/".join(["s3:/", self._bucket, self._object])
	
	def is_dns_compatible(self):
		return check_bucket_name_dns_conformity(self._bucket)

	def public_url(self):
		if self.is_dns_compatible():
			return "http://%s.s3.amazonaws.com/%s" % (self._bucket, self._object)
		else:
			return "http://s3.amazonaws.com/%s/%s" % (self._bucket, self._object)

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
	_re = re.compile("^cf://([^/]*)/?", re.IGNORECASE)
	def __init__(self, string):
		match = self._re.match(string)
		if not match:
			raise ValueError("%s: not a CloudFront URI" % string)
		groups = match.groups()
		self._dist_id = groups[0]

	def dist_id(self):
		return self._dist_id

	def uri(self):
		return "/".join(["cf:/", self.dist_id()])

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


########NEW FILE########
__FILENAME__ = SimpleDB
## Amazon SimpleDB library
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2

"""
Low-level class for working with Amazon SimpleDB
"""

import time
import urllib
import base64
import hmac
import sha
import httplib
from logging import debug, info, warning, error

from Utils import convertTupleListToDict
from SortedDict import SortedDict
from Exceptions import *

class SimpleDB(object):
	# API Version
	# See http://docs.amazonwebservices.com/AmazonSimpleDB/2007-11-07/DeveloperGuide/
	Version = "2007-11-07"
	SignatureVersion = 1

	def __init__(self, config):
		self.config = config

	## ------------------------------------------------
	## Methods implementing SimpleDB API
	## ------------------------------------------------

	def ListDomains(self, MaxNumberOfDomains = 100):
		'''
		Lists all domains associated with our Access Key. Returns 
		domain names up to the limit set by MaxNumberOfDomains.
		'''
		parameters = SortedDict()
		parameters['MaxNumberOfDomains'] = MaxNumberOfDomains
		return self.send_request("ListDomains", DomainName = None, parameters = parameters)

	def CreateDomain(self, DomainName):
		return self.send_request("CreateDomain", DomainName = DomainName)

	def DeleteDomain(self, DomainName):
		return self.send_request("DeleteDomain", DomainName = DomainName)

	def PutAttributes(self, DomainName, ItemName, Attributes):
		parameters = SortedDict()
		parameters['ItemName'] = ItemName
		seq = 0
		for attrib in Attributes:
			if type(Attributes[attrib]) == type(list()):
				for value in Attributes[attrib]:
					parameters['Attribute.%d.Name' % seq] = attrib
					parameters['Attribute.%d.Value' % seq] = unicode(value)
					seq += 1
			else:
				parameters['Attribute.%d.Name' % seq] = attrib
				parameters['Attribute.%d.Value' % seq] = unicode(Attributes[attrib])
				seq += 1
		## TODO:
		## - support for Attribute.N.Replace
		## - support for multiple values for one attribute
		return self.send_request("PutAttributes", DomainName = DomainName, parameters = parameters)

	def GetAttributes(self, DomainName, ItemName, Attributes = []):
		parameters = SortedDict()
		parameters['ItemName'] = ItemName
		seq = 0
		for attrib in Attributes:
			parameters['AttributeName.%d' % seq] = attrib
			seq += 1
		return self.send_request("GetAttributes", DomainName = DomainName, parameters = parameters)

	def DeleteAttributes(self, DomainName, ItemName, Attributes = {}):
		"""
		Remove specified Attributes from ItemName.
		Attributes parameter can be either:
		- not specified, in which case the whole Item is removed
		- list, e.g. ['Attr1', 'Attr2'] in which case these parameters are removed
		- dict, e.g. {'Attr' : 'One', 'Attr' : 'Two'} in which case the 
		  specified values are removed from multi-value attributes.
		"""
		parameters = SortedDict()
		parameters['ItemName'] = ItemName
		seq = 0
		for attrib in Attributes:
			parameters['Attribute.%d.Name' % seq] = attrib
			if type(Attributes) == type(dict()):
				parameters['Attribute.%d.Value' % seq] = unicode(Attributes[attrib])
			seq += 1
		return self.send_request("DeleteAttributes", DomainName = DomainName, parameters = parameters)

	def Query(self, DomainName, QueryExpression = None, MaxNumberOfItems = None, NextToken = None):
		parameters = SortedDict()
		if QueryExpression:
			parameters['QueryExpression'] = QueryExpression
		if MaxNumberOfItems:
			parameters['MaxNumberOfItems'] = MaxNumberOfItems
		if NextToken:
			parameters['NextToken'] = NextToken
		return self.send_request("Query", DomainName = DomainName, parameters = parameters)
		## Handle NextToken? Or maybe not - let the upper level do it

	## ------------------------------------------------
	## Low-level methods for handling SimpleDB requests
	## ------------------------------------------------

	def send_request(self, *args, **kwargs):
		request = self.create_request(*args, **kwargs)
		#debug("Request: %s" % repr(request))
		conn = self.get_connection()
		conn.request("GET", self.format_uri(request['uri_params']))
		http_response = conn.getresponse()
		response = {}
		response["status"] = http_response.status
		response["reason"] = http_response.reason
		response["headers"] = convertTupleListToDict(http_response.getheaders())
		response["data"] =  http_response.read()
		conn.close()

		if response["status"] < 200 or response["status"] > 299:
			debug("Response: " + str(response))
			raise S3Error(response)

		return response

	def create_request(self, Action, DomainName, parameters = None):
		if not parameters:
			parameters = SortedDict()
		parameters['AWSAccessKeyId'] = self.config.access_key
		parameters['Version'] = self.Version
		parameters['SignatureVersion'] = self.SignatureVersion
		parameters['Action'] = Action
		parameters['Timestamp'] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
		if DomainName:
			parameters['DomainName'] = DomainName
		parameters['Signature'] = self.sign_request(parameters)
		parameters.keys_return_lowercase = False
		uri_params = urllib.urlencode(parameters)
		request = {}
		request['uri_params'] = uri_params
		request['parameters'] = parameters
		return request

	def sign_request(self, parameters):
		h = ""
		parameters.keys_sort_lowercase = True
		parameters.keys_return_lowercase = False
		for key in parameters:
			h += "%s%s" % (key, parameters[key])
		#debug("SignRequest: %s" % h)
		return base64.encodestring(hmac.new(self.config.secret_key, h, sha).digest()).strip()

	def get_connection(self):
		if self.config.proxy_host != "":
			return httplib.HTTPConnection(self.config.proxy_host, self.config.proxy_port)
		else:
			if self.config.use_https:
				return httplib.HTTPSConnection(self.config.simpledb_host)
			else:
				return httplib.HTTPConnection(self.config.simpledb_host)

	def format_uri(self, uri_params):
		if self.config.proxy_host != "":
			uri = "http://%s/?%s" % (self.config.simpledb_host, uri_params)
		else:
			uri = "/?%s" % uri_params
		#debug('format_uri(): ' + uri)
		return uri

########NEW FILE########
__FILENAME__ = SortedDict
## Amazon S3 manager
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2

from BidirMap import BidirMap

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

########NEW FILE########
__FILENAME__ = Utils
## Amazon S3 manager
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2

import os
import time
import re
import string
import random
import rfc822
try:
	from hashlib import md5, sha1
except ImportError:
	from md5 import md5
	import sha as sha1
import hmac
import base64
import errno

from logging import debug, info, warning, error

import Config
import Exceptions

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
			## Complex-type child. We're not interested
			continue
		if ret_dict.has_key(child.tag):
			if not type(ret_dict[child.tag]) == list:
				ret_dict[child.tag] = [ret_dict[child.tag]]
			ret_dict[child.tag].append(child.text or "")
		else:
			ret_dict[child.tag] = child.text or ""
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
	date = re.compile("(\.\d*)?Z").sub(".000Z", date)
	return time.strptime(date, "%Y-%m-%dT%H:%M:%S.000Z")
__all__.append("dateS3toPython")

def dateS3toUnix(date):
	## FIXME: This should be timezone-aware.
	## Currently the argument to strptime() is GMT but mktime() 
	## treats it as "localtime". Anyway...
	return time.mktime(dateS3toPython(date))
__all__.append("dateS3toUnix")

def dateRFC822toPython(date):
	return rfc822.parsedate(date)
__all__.append("dateRFC822toPython")

def dateRFC822toUnix(date):
	return time.mktime(dateRFC822toPython(date))
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
	return time.strftime("%Y-%m-%d %H:%M", dateS3toPython(s3timestamp))
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

def mktmpdir(prefix = "/tmp/tmpdir-", randchars = 10):
	return mktmpsomething(prefix, randchars, os.mkdir)
__all__.append("mktmpdir")

def mktmpfile(prefix = "/tmp/tmpfile-", randchars = 20):
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
	#debug("string_to_sign: %s" % string_to_sign)
	signature = base64.encodestring(hmac.new(Config.Config().secret_key, string_to_sign, sha1).digest()).strip()
	#debug("signature: %s" % signature)
	return signature
__all__.append("sign_string")

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

########NEW FILE########
