__FILENAME__ = adjust-emlx-modification-dates
#!/usr/bin/env python
#
# Adjust the file modification dates of OS X Mail.app .emlx files
# to match the date in their headers.
#
# Maintained at https://github.com/liyanage/macosx-shell-scripts/
#

import os
import argparse
import logging
import email.parser
import email.utils
import time


class MailMessageFile(object):
    
    def __init__(self, path):
        self.path = path
        self._header_date = None
        self._file_date = None
    
    def header_date(self):
        if not self._header_date:
            with open(self.path) as f:
                f.readline() # emlx files have an additional leading line
                message = email.parser.Parser().parse(f, headersonly=True)
                if not message:
                    logging.warning('Unable to parse emlx file as mail message: {}'.format(self.path))
                    return None
                date = message.get('date')
                if not date:
                    logging.warning('No date header found in {}'.format(self.path))
                    return None
                self._header_date = time.mktime(email.utils.parsedate(date))
        return self._header_date
    
    def file_date(self):
        if not self._file_date:
            self._file_date = os.path.getmtime(self.path)
        return self._file_date

    def has_date_mismatch(self, threshold_seconds=60):
        header_date = self.header_date()
        file_date = self.file_date()
        if not header_date and file_date:
            return None, True
        absdelta_seconds = int(abs(header_date - file_date))
        has_mismatch = absdelta_seconds > threshold_seconds
        return has_mismatch, None
    
    def fix_date(self):
        header_date = self.header_date()
        logging.debug('Changing date to {} for {}'.format(header_date, self.path))
        os.utime(self.path, (header_date, header_date))


class Tool(object):
    
    def __init__(self, mail_root, verbose=False):
        logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)
        mail_root = os.path.expanduser(mail_root)
        assert os.path.exists(mail_root), 'Mail root directory {} does not exist.'.format(mail_root)
        self.mail_root = mail_root
        logging.debug('Mail root directory: {}'.format(mail_root))
    
    def adjust_dates(self, dry_run=False):
        for dirpath, dirnames, filenames in os.walk(self.mail_root):
            if 'Attachments' in dirnames:
                del(dirnames[dirnames.index('Attachments')])
            logging.info(dirpath)
            for filename in [f for f in filenames if f.endswith('.emlx')]:
                self.process_message_file(os.path.join(dirpath, filename), dry_run)

    def process_message_file(self, path, dry_run=False):
        message = MailMessageFile(path)
        has_mismatch, error = message.has_date_mismatch()
        if error or not has_mismatch:
            return
        logging.info('Found message with date mismatch: {}/{} {}'.format(message.header_date(), message.file_date(), path))
        if not dry_run:
            message.fix_date()
    
    @classmethod
    def run(cls):
        parser = argparse.ArgumentParser(description='Adjust the file modification dates of OS X Mail.app .emlx files to match the date in their headers.')
        parser.add_argument('mailroot', nargs='?', default='~/Library/Mail/V2/', help='Toplevel directory in which .emlx files should be changed. Defaults to ~/Library/Mail/V2')
        parser.add_argument('--dry-run', help='Dry run, list the affected files only', action='store_true')
        parser.add_argument('--verbose', help='Log debug output', action='store_true')
        args = parser.parse_args()
        Tool(args.mailroot, args.verbose).adjust_dates(dry_run=args.dry_run)

if __name__ == '__main__':
    Tool.run()

########NEW FILE########
__FILENAME__ = brace-expression
#!/usr/bin/env python
#
# Converts a set of paths (on stdin, one path per line) into a shell brace expression.
#
# Example:
#
# security
# security/audit_class
# security/audit_control
# security/audit_event
# security/audit_user
# security/audit_warn
# services
# shells
# slpsa.conf
# smb.conf.old
# snmp
# snmp/snmpd.conf
# snmp/snmpd.conf.default
#
# becomes
#
# {smb.conf.old,shells,snmp,snmp/{snmpd.conf.default,snmpd.conf},services,security,security/{audit_control,audit_class,audit_user,audit_warn,audit_event},slpsa.conf}


import re
import sys
import collections

class Node(object):

    def __init__(self, name=None):
        self.name = name
        self.include_self = False
        self.children = {}
    
    def add_path(self, path):
        if not path:
            return
        path = re.sub(r'([^a-zA-Z0-9/_.-])', r'\\\1', path)
        items = path.split('/')
        self.add_path_components(items)

    def add_path_components(self, path_components):
        if not path_components:
            return
        head = path_components[0]
        tail = path_components[1:]
        child = self.children.setdefault(head, Node(head))
        if tail:
            child.add_path_components(tail)
        else:
            child.include_self = True
    
    def shell_brace_expression(self):
        if not self.children:
            return self.name
        
        children = ','.join([child.shell_brace_expression() for child in self.children.values()])
        if len(self.children) > 1:
            children = '{' + children + '}'
        
        if self.name:
            result = ['/'.join([self.name, children])]
            if self.include_self and children:
                result.insert(0, self.name)
            return ','.join(result)
        else:
            return children

    @classmethod
    def shell_brace_expression_for_paths(cls, paths):
        root = cls()
        for path in paths:
            root.add_path(path)
        return root.shell_brace_expression()

paths = [line.rstrip() for line in sys.stdin.readlines()]
print Node.shell_brace_expression_for_paths(paths)

########NEW FILE########
__FILENAME__ = branch-svn-subtree
#!/usr/bin/env python

from Shell import Shell
import os, re, sys, argparse, urlparse


class ExternalsDefinition:

	def __init__(self, subdirectory, url):
		self.subdirectory = subdirectory
		self.url = url


class SVNDirectory:

	processed_locations = []

	def __init__(self, url, parent = None, replacements = None, workdir = None, commit_message = None):
		self.url = url
		self.parent = parent
		self._replacements = replacements
		self._subdirectories = None
		self._externals_property = None
		self._workdir = workdir
		self._commit_message = commit_message
	
	def workdir(self):
		return self.root()._workdir

	def commit_message(self):
		return self.root()._commit_message

	def commit_message_option(self):
		commit_message = self.commit_message()
		if not commit_message:
			return ''
		return "-m '{0}'".format(commit_message)
	
	def is_root(self):
		return not self.parent
		
	def root(self):
		if self.is_root():
			return self
		return self.parent.root()
	
	def subdirectories(self):
		if self._subdirectories == None:
			self._subdirectories = []
			contents_xml = Shell(verbose = False).run('svn ls --xml "{0}"'.format(self.url)).output_xml()
			for element in contents_xml.find('list').findall('entry'):
				if not element.get('kind') == 'dir':
					continue
				name = element.findtext('name')
				subdirectory_url = os.path.join(self.url, name)
				subdirectory = SVNDirectory(subdirectory_url, parent = self)
				if subdirectory.should_ignore():
					continue
				self._subdirectories.append(subdirectory)

		return self._subdirectories
	
	def should_ignore(self):
		if self.depth() > 2:
			return True
			
		name = self.name()
		for ignore in ('.lproj', '.nib', '.xcodeproj'):
			if name.find(ignore) != -1:
				return True
		return False
	
	def depth(self):
		if self.is_root():
			return 0
		return self.parent.depth() + 1
	
	def replacements(self):
		return self.root()._replacements
	
	def string_contains_replacement(self, string):
		for key in self.replacements():
			if string.find(key) != -1:
				return True
		return False

	def apply_replacements_to_string(self, string):
		replacements = self.replacements()
		for old in replacements:
			new = replacements[old]
			string = string.replace(old, new)
		return string
			
		for key in self.replacements().keys():
			if string.find(key) != -1:
				return True
		return False

	def externals_property(self):
		if self._externals_property == None:
			propget_cmd = Shell(verbose = False, fatal = True).run('svn pg --xml svn:externals "{0}"'.format(self.url))
			contents_xml = propget_cmd.output_xml()
			self._externals_property = contents_xml.findtext('target/property')
		return self._externals_property
	
	def externals_definitions(self):
		property = self.externals_property()
		externals = []
		for line in property.splitlines():
			match = re.search('("[^"]+"|\S+)\s+(.+)', line)
			if not match:
				continue
			directory = match.group(1).replace('"', '')
			url = match.group(2)
			externals.append(ExternalsDefinition(directory, url))
		return externals			
	
	def new_url(self):
		return self.apply_replacements_to_string(self.url)
	
	def new_name(self):
		return os.path.basename(self.new_url())
	
	def name(self):
		return os.path.basename(self.url)
	
	def sandbox_dir(self):
		if self.is_root():
			parsed_url = urlparse.urlparse(self.new_url())
			return os.path.join(self.workdir(), parsed_url.path[1:].replace('/', '-'))
		else:
			return os.path.join(self.parent.sandbox_dir(), self.new_name());

	def self_or_subdirectory_has_rewritten_externals(self):
		value = self.externals_property()
		if value and self.string_contains_replacement(value):
			return True

		for subdir in self.subdirectories():
			if subdir.self_or_subdirectory_has_rewritten_externals():
				return True
		
		return False
	
	def externals_urls_containing_replacements(self):
		urls = []
		for definition in self.externals_definitions():
			url = definition.url
			if self.string_contains_replacement(url):
				urls.append(url)
		return urls

	def process(self):
		
		new_url = self.new_url()

		if self.url in self.processed_locations:
#			print "### Skipping {0}, already processed".format(self.url)
			return False

		self.processed_locations.append(self.url)

 		if self.is_root():
 			print "###### processing as root dir"
			print 'svn cp {0} {1} {2}'.format(self.commit_message_option(), self.url, new_url)

		if not self.self_or_subdirectory_has_rewritten_externals():
			return False

		sandbox_dir = self.sandbox_dir()
		
		parent_dir = os.path.dirname(sandbox_dir)
		print 'cd {0}'.format(parent_dir)
		
 		if self.is_root():
			print 'svn co --depth empty {0} {1}'.format(self.new_url(), sandbox_dir)
		else:
			print 'svn up --depth empty {0}'.format(sandbox_dir)
		
		print 'cd {0}'.format(sandbox_dir)

		externals_value = self.externals_property()
		if externals_value and self.string_contains_replacement(externals_value):
			new_externals = self.apply_replacements_to_string(externals_value)
			print "svn ps svn:externals '{0}' .".format(new_externals)
			print "svn ci {0} .".format(self.commit_message_option())
			
			externals_urls_containing_replacements = [url for url in self.externals_urls_containing_replacements()]
			for url in externals_urls_containing_replacements:
				if url in self.processed_locations:
#					print "### Skipping externals URL {0}, already processed".format(url)
					continue
					
				print '### Processing external {0} in {1}'.format(url, self.url)
				externals_dir = SVNDirectory(url, replacements = self.replacements(), workdir = self.workdir(), commit_message = self.commit_message())
				externals_dir.process()
			
		for subdir in self.subdirectories():
			subdir.process()

		return True


class BranchMapper:

	def __init__(self, root_urls, replacements, commit_message = None):
		self.root_urls = root_urls
		self.replacements = replacements
		self.commit_message = commit_message
		self.prepare_workdir()
	
	def prepare_workdir(self):
		self.workdir = '-'.join((os.path.basename(sys.argv[0]), 'workdir'))
		if not os.path.exists(self.workdir):
			os.mkdir(self.workdir)
		self.workdir = os.path.abspath(self.workdir)
		os.chdir(self.workdir)
	
	def run(self):
		for root_url in self.root_urls:
 			print '### Processing toplevel URL {0}'.format(root_url)
			root_dir = SVNDirectory(root_url, replacements = self.replacements, workdir = self.workdir, commit_message = self.commit_message)
			root_dir.process()
	
	


parser = argparse.ArgumentParser(description = 'Branch subversion subtree')
parser.add_argument('--url', action = 'append', dest = 'root_urls', metavar = 'ROOT_URL', required = True, help='An SVN URL to be branched. Can be used multiple times.')
parser.add_argument('--replace', nargs = 2, action = 'append', metavar = 'REPLACEMENT', dest = 'replacements', required = True, help='a from -> to mapping of existing to new branch name. Can be used multiple times.')
parser.add_argument('-m', dest = 'commit_message', help='An optional SVN commit message')
args = parser.parse_args()
replacements = dict(args.replacements)

BranchMapper(args.root_urls, replacements, args.commit_message).run()


########NEW FILE########
__FILENAME__ = checklibs
#!/usr/bin/env python
#
# checklibs.py
#
# Check Mach-O dependencies.
#
# See http://www.entropy.ch/blog/Developer/2011/03/05/2011-Update-to-checklibs-Script-for-dynamic-library-dependencies.html
#
# Written by Marc Liyanage <http://www.entropy.ch>
#
#

import subprocess, sys, re, os.path, optparse, collections
from pprint import pprint


class MachOFile:

    def __init__(self, image_path, arch, parent = None):
        self.image_path = image_path
        self._dependencies = []
        self._cache = dict(paths = {}, order = [])
        self.arch = arch
        self.parent = parent
        self.header_info = {}
        self.load_info()
        self.add_to_cache()
        
    def load_info(self):
        if not self.image_path.exists():
            return
        self.load_header()
        self.load_rpaths()

    def load_header(self):
        # Get the mach-o header info, we're interested in the file type (executable, dylib)
        cmd = 'otool -arch {0} -h "{1}"'
        output = self.shell(cmd, [self.arch, self.image_path.resolved_path], fatal = True)
        if not output:
            print >> sys.stderr, 'Unable to load mach header for {0} ({1}), architecture mismatch? Use --arch option to pick architecture'.format(self.image_path.resolved_path, self.arch)
            exit()
        (keys, values) = output.splitlines()[2:]
        self.header_info = dict(zip(keys.split(), values.split()))

    def load_rpaths(self):
        output = self.shell('otool -arch {0} -l "{1}"', [self.arch, self.image_path.resolved_path], fatal = True)
        load_commands = re.split('Load command (\d+)', output)[1:] # skip file name on first line
        self._rpaths = []
        load_commands = collections.deque(load_commands)
        while load_commands:
            load_commands.popleft() # command index
            command = load_commands.popleft().strip().splitlines()
            if command[0].find('LC_RPATH') == -1:
                continue
            
            path = re.findall('path (.+) \(offset \d+\)$', command[2])[0]
            image_path = self.image_path_for_recorded_path(path)
            image_path.rpath_source = self
            self._rpaths.append(image_path)

    def ancestors(self):
        ancestors = []
        parent = self.parent
        while parent:
            ancestors.append(parent)
            parent = parent.parent
        
        return ancestors

    def self_and_ancestors(self):
        return [self] + self.ancestors()
    
    def rpaths(self):
        return self._rpaths
    
    def all_rpaths(self):
        rpaths = []
        for image in self.self_and_ancestors():
            rpaths.extend(image.rpaths())
        return rpaths
    
    def root(self):
        if not self.parent:
            return self
        return self.ancestors()[-1]
    
    def executable_path(self):
        root = self.root()
        if root.is_executable():
            return root.image_path
        return None

    def filetype(self):
        return long(self.header_info.get('filetype', 0))
        
    def is_dylib(self):
        return self.filetype() == MachOFile.MH_DYLIB

    def is_executable(self):
        return self.filetype() == MachOFile.MH_EXECUTE
        
    def all_dependencies(self):
        self.walk_dependencies()
        return self.cache()['order']
    
    def walk_dependencies(self, known = {}):
        if known.get(self.image_path.resolved_path):
            return
        
        known[self.image_path.resolved_path] = self
        
        for item in self.dependencies():
            item.walk_dependencies(known)
        
    def dependencies(self):
        if not self.image_path.exists():
            return []

        if self._dependencies:
            return self._dependencies

        output = self.shell('otool -arch {0} -L "{1}"', [self.arch, self.image_path.resolved_path], fatal = True)
        output = [line.strip() for line in output.splitlines()]
        del(output[0])
        if self.is_dylib():
            del(output[0]) # In the case of dylibs, the first line is the id line

        self._dependencies = []
        for line in output:
            match = re.match('^(.+)\s+(\(.+)\)$', line)
            if not match:
                continue
            recorded_path = match.group(1)
            image_path = self.image_path_for_recorded_path(recorded_path)
            image = self.lookup_or_make_item(image_path)
            self._dependencies.append(image)
            
        return self._dependencies

    # The root item holds the cache, all lower-level requests bubble up the parent chain
    def cache(self):
        if self.parent:
            return self.parent.cache()
        return self._cache
    
    def add_to_cache(self):
        cache = self.cache()
        cache['paths'][self.image_path.resolved_path] = self
        cache['order'].append(self)
        
    def cached_item_for_path(self, path):
        if not path:
            return None
        return self.cache()['paths'].get(path)
    
    def lookup_or_make_item(self, image_path):
        image = self.cached_item_for_path(image_path.resolved_path)
        if not image: # cache miss
            image = MachOFile(image_path, self.arch, parent = self)
        return image

    def image_path_for_recorded_path(self, recorded_path):
        path = ImagePath(None, recorded_path)

        # handle @executable_path       
        if recorded_path.startswith(ImagePath.EXECUTABLE_PATH_TOKEN):
            executable_image_path = self.executable_path()
            if executable_image_path:
                path.resolved_path = os.path.normpath(recorded_path.replace(ImagePath.EXECUTABLE_PATH_TOKEN, os.path.dirname(executable_image_path.resolved_path)))

        # handle @loader_path
        elif recorded_path.startswith(ImagePath.LOADER_PATH_TOKEN):
            path.resolved_path = os.path.normpath(recorded_path.replace(ImagePath.LOADER_PATH_TOKEN, os.path.dirname(self.image_path.resolved_path)))

        # handle @rpath
        elif recorded_path.startswith(ImagePath.RPATH_TOKEN):
            for rpath in self.all_rpaths():
                resolved_path = os.path.normpath(recorded_path.replace(ImagePath.RPATH_TOKEN, rpath.resolved_path))
                if os.path.exists(resolved_path):
                    path.resolved_path = resolved_path
                    path.rpath_source = rpath.rpath_source
                    break

        # handle absolute path
        elif recorded_path.startswith('/'):
            path.resolved_path = recorded_path

        return path

    def __repr__(self):
        return str(self.image_path)
    
    def dump(self):
        print self.image_path
        for dependency in self.dependencies():
            print '\t{0}'.format(dependency)
    
    @staticmethod
    def shell(cmd_format, args, fatal = False):
        cmd = cmd_format.format(*args)
        popen = subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE)
        output = popen.communicate()[0]
        if popen.returncode and fatal:
            print >> sys.stderr, 'Nonzero exit status for shell command "{0}"'.format(cmd)
            sys.exit(1)

        return output

    @classmethod
    def architectures_for_image_at_path(cls, path):
        output = cls.shell('file "{}"', [path])
        file_architectures = re.findall(r' executable (\w+)', output)
        ordering = 'x86_64 i386'.split()
        file_architectures = sorted(file_architectures, lambda a, b: cmp(ordering.index(a), ordering.index(b)))
        return file_architectures

    MH_EXECUTE = 0x2
    MH_DYLIB = 0x6
    MH_BUNDLE = 0x8
    

# ANSI terminal coloring sequences
class Color:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    
    @staticmethod
    def red(string):
        return Color.wrap(string, Color.RED)
    
    @staticmethod
    def blue(string):
        return Color.wrap(string, Color.BLUE)
    
    @staticmethod
    def wrap(string, color):
        return Color.HEADER + color + string + Color.ENDC


# This class holds path information for a mach-0 image file. It holds the path as it was recorded
# in the loading binary as well as the effective, resolved file system path.
# The former can contain @-replacement tokens.
# In the case where the recorded path contains an @rpath token that was resolved successfully, we also
# capture the path of the binary that supplied the rpath value that was used.
# That path itself can contain replacement tokens such as @loader_path.
class ImagePath:

    def __init__(self, resolved_path, recorded_path = None):
        self.recorded_path = recorded_path
        self.resolved_path = resolved_path
        self.rpath_source = None
        
    def __repr__(self):
        description = None
        
        if self.resolved_equals_recorded() or self.recorded_path == None:
            description = self.resolved_path
        else:
            description = '{0} ({1})'.format(self.resolved_path, self.recorded_path)
        
        if (not self.is_system_location()) and (not self.uses_dyld_token()):
            description = Color.blue(description)
        
        if self.rpath_source:
            description += ' (rpath source: {0})'.format(self.rpath_source.image_path.resolved_path)
        
        if not self.exists():
            description += Color.red(' (missing)')
        
        return description
    
    def exists(self):
        return self.resolved_path and os.path.exists(self.resolved_path)
    
    def resolved_equals_recorded(self):
        return self.resolved_path and self.recorded_path and self.resolved_path == self.recorded_path
    
    def uses_dyld_token(self):
        return self.recorded_path and self.recorded_path.startswith('@')
    
    def is_system_location(self):
        system_prefixes = ['/System/Library', '/usr/lib']
        for prefix in system_prefixes:
            if self.resolved_path and self.resolved_path.startswith(prefix):
                return True

    EXECUTABLE_PATH_TOKEN = '@executable_path'
    LOADER_PATH_TOKEN = '@loader_path'
    RPATH_TOKEN = '@rpath'


# Command line driver
parser = optparse.OptionParser(usage = "Usage: %prog [options] path_to_mach_o_file")
parser.add_option("--arch", dest = "arch", help = "architecture", metavar = "ARCH")
parser.add_option("--all", dest = "include_system_libraries", help = "Include system frameworks and libraries", action="store_true")
(options, args) = parser.parse_args()

if len(args) < 1:
    parser.print_help()
    sys.exit(1)

archs = MachOFile.architectures_for_image_at_path(args[0])
if archs and not options.arch:
    print >> sys.stderr, 'Analyzing architecture {}, override with --arch if needed'.format(archs[0])
    options.arch = archs[0]

toplevel_image = MachOFile(ImagePath(args[0]), options.arch)

for dependency in toplevel_image.all_dependencies():
    if dependency.image_path.exists() and (not options.include_system_libraries) and dependency.image_path.is_system_location():
        continue

    dependency.dump()
    print


########NEW FILE########
__FILENAME__ = copy-dummy-file-tree
#!/usr/bin/env python

# Copies a directory tree, but all files will be zero-length placeholder/dummy files.

import os, sys

input_dir, output_dir_parent = sys.argv[1:3]
print input_dir, output_dir_parent

input_dir_parent = os.path.dirname(input_dir)

for root, dirs, files in os.walk(input_dir):
	for dir in dirs:
		subdir = os.path.join(root, dir)
		output_subdir = os.path.normpath(subdir.replace(input_dir_parent, output_dir_parent))
 		output_subdir = os.path.normpath('/'.join((output_dir_parent, subdir.replace(input_dir_parent, ''))))
 		if not os.path.exists(output_subdir):
 			os.makedirs(output_subdir)

	for filename in files:
		if filename.startswith("."):
			continue
		filepath = os.path.join(root, filename)
		output_filepath = os.path.normpath(filepath.replace(input_dir_parent, output_dir_parent))
 		with file(output_filepath, 'a'):
 			pass

########NEW FILE########
__FILENAME__ = diff-non-whitespace-only-counter
#!/usr/bin/env python
#
# Find change lines in a unified diff that are not just leading whitespace changes
#

import collections
import sys
import re

counter = collections.Counter()

with open(sys.argv[1]) as f:
    for line in f:
        if not line:
            continue
        operation = line[0]
        if operation not in '+-':
            continue
        
        content = line[1:]
        content = re.findall(r'^\s*(\S.*)$', content)
        if not content:
            continue
        content = content[0]
        if operation == '-':
            counter[content] -= 1
        elif operation == '+':
            counter[content] += 1


for key, count in counter.iteritems():
    if not count:
        continue
    
    print key
########NEW FILE########
__FILENAME__ = dmgtool
#!/usr/bin/env python

#
# Library and tool for some OS X DMG file operation, using hdiutil
#
# Maintained at https://github.com/liyanage/macosx-shell-scripts
#

import os
import re
import sys
import glob
import shutil
import logging
import argparse
import datetime
import plistlib
import tempfile
import textwrap
import subprocess
import contextlib
import collections

class DiskImage(object):

    def __init__(self, dmg_url_or_path):
        self.dmg_url_or_path = dmg_url_or_path
        self.is_remote = bool(re.match(r'^https?://', dmg_url_or_path))
        self.converted_mount_path = None
        self.mount_data = None
        self.info_data = None
    
    def __del__(self):
        if self.converted_mount_path:
            logging.debug('Cleaning up "{}"'.format(self.converted_mount_path))
            os.unlink(self.converted_mount_path)
    
    def info(self):
        if not self.info_data:
            cmd = ['imageinfo', '-plist', self.dmg_url_or_path]
            self.info_data = self.run_hdiutil_plist_command(cmd)
        return self.info_data
    
    def has_license_agreement(self):
        return self.info()['Properties']['Software License Agreement']
    
    def mount(self):
        mount_path = self.dmg_url_or_path
        if self.has_license_agreement():
            print >> sys.stderr, 'Stripping license agreement...'
            tempfile_path = tempfile.mktemp(dir=os.environ['TMPDIR'])
            cmd = ['convert', self.dmg_url_or_path, '-plist', '-format', 'UDTO', '-o', tempfile_path]
            convert_data = self.run_hdiutil_plist_command(cmd)
            self.converted_mount_path, = convert_data
            mount_path = self.converted_mount_path

        cmd = ['mount', '-plist', mount_path]
        self.mount_data = self.run_hdiutil_plist_command(cmd)

    def basename(self):
        return os.path.basename(self.dmg_url_or_path)
    
    def basename_without_extension(self):
        name, extension = os.path.splitext(self.basename())
        return name

    def mount_point(self):
        mount_points = []
        for item in self.mount_data['system-entities']:
            if 'mount-point' not in item:
                continue
            path = item['mount-point']
            mount_points.append(path)
        return mount_points[0] if mount_points else None
    
    def unmount(self):
        cmd = ['unmount', self.mount_point()]
        status, stdout, stderr = self.run_hdiutil_command(cmd)
    
    def run_hdiutil_command(self, cmd, input=None):
        cmd = ['hdiutil'] + cmd
        stdin = subprocess.PIPE if input else None
        process = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stdin=stdin)
        stdoutdata, stderrdata = process.communicate()
        logging.debug('ran cmd "{}": returncode={}, stdout={}, stderr={}'.format(cmd, process.returncode, stdoutdata, stderrdata))
        if process.returncode:
            print >> sys.stderr, 'Nonzero status {} for "{}": {}'.format(process.returncode, cmd, stderrdata)
        return process.returncode, stdoutdata, stderrdata
        
    def run_hdiutil_plist_command(self, cmd, input=None):
        status, stdoutdata, stderrdata = self.run_hdiutil_command(cmd, input=input)
        if status:
            return None
        data = plistlib.readPlistFromString(stdoutdata)
        return data


class AbstractSubcommand(object):

    def __init__(self, arguments):
        self.args = arguments

    def run(self):
        pass

    @classmethod
    def configure_argument_parser(cls, parser):
        pass
    
    @classmethod
    def subcommand_name(cls):
        return '-'.join([i.lower() for i in re.findall(r'([A-Z][a-z]+)', re.sub(r'^Subcommand', '', cls.__name__))])

    @classmethod
    def subclass_map(cls):
        map = {c.__name__: c for c in cls.__subclasses__()}
        for subclass in map.values():
            map.update(subclass.subclass_map())
        return map


class SubcommandInfo(AbstractSubcommand):
    """
    Print information about a disk image.
    """
    
    def run(self):
        image = DiskImage(self.args.dmg_url_or_path)
        print image.info()
    
    @classmethod
    def configure_argument_parser(cls, parser):
        parser.add_argument('dmg_url_or_path', help='DMG URL or path')


class ImageMountingSubcommand(AbstractSubcommand):
    
    def run(self):
        image = DiskImage(self.args.dmg_url_or_path)
        print >> sys.stderr, 'Mounting {}...'.format(self.args.dmg_url_or_path)
        image.mount()
        print >> sys.stderr, 'Mounted at {}'.format(image.mount_point())

        try:
            self.process_image(image)
            if self.args.delete and not image.is_remote:
                self.trash_path(self.args.dmg_url_or_path)
        finally:
            print >> sys.stderr, 'Unmounting {}...'.format(image.mount_point())
            image.unmount()

    def process_image(self, image):
        raise NotImplementedError()

    def trash_path(self, path):
        basename = os.path.basename(path)
        user_trash_path = os.path.expanduser('~/.Trash')
        trash_path = os.path.join(user_trash_path, basename)
        trash_path, did_rename = self.unique_path_for_path(trash_path)
        if did_rename:
            print >> sys.stderr, 'Trashing {} to {}'.format(path, trash_path)
        else:
            print >> sys.stderr, 'Trashing {}'.format(path)
        shutil.move(path, trash_path)
    
    def unique_path_for_path(self, path):
        if not os.path.exists(os.path.expanduser(path)):
            return path, False

        head, tail = os.path.split(path)
        name, ext = os.path.splitext(tail)
        timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        new_basename = '{}-{}{}'.format(name, timestamp, ext)
        new_path = os.path.join(head, new_basename)
        return new_path, True

    def copy_path(self, source_path, destination_path):        
        cmd = ['cp', '-pR', source_path, destination_path]
        process = subprocess.Popen(cmd)
        process.communicate()
    
    @classmethod
    def configure_argument_parser(cls, parser):
        parser.add_argument('dmg_url_or_path', help='DMG URL or path')
        parser.add_argument('-d', '--delete', action='store_true', help='Delete disk image file after installation')


class SubcommandInstallApplication(ImageMountingSubcommand):
    """
    Mount a DMG and install a toplevel .app into /Applications.
    """

    def process_image(self, image):
        apps = glob.glob('{}/*.app'.format(image.mount_point()))
        if not apps:
            return
        
        for app_path in apps:
            basename = os.path.basename(app_path)
            destination_path = os.path.join('/Applications', basename)
            if os.path.exists(destination_path):
                self.trash_path(destination_path)
            print >> sys.stderr, 'Installing {} to {}'.format(app_path, destination_path)
            self.copy_path(app_path, destination_path)


class SubcommandUnpackMasPackage(ImageMountingSubcommand):
    """
    Mount a DMG and unpack a toplevel Mac App Store package to the Desktop
    """
    
    # Useful productutil tips: http://shapeof.com/archives/2011/07/stupid_productutil_tricks.html

    def process_image(self, image):
        packages = glob.glob('{}/*.pkg'.format(image.mount_point()))
        if not packages:
            return
            
        if self.args.install:
            self.install_packages(packages)
        else:
            self.unpack_packages(packages, image)

    def install_packages(self, packages):
        for package_path in packages:
            print >> sys.stderr, 'Installing {}...'.format(package_path)
            cmd = ['/usr/sbin/installer', '-store', '-pkg', package_path, '-target', '/']
            process = subprocess.Popen(cmd)
            process.communicate()
    
    def unpack_packages(self, packages, image):
        image_basename = image.basename_without_extension()
        single_package = len(packages) == 1
        for package_path in packages:
            basename = os.path.basename(package_path)
            if single_package:
                destination_path = os.path.join('~/Desktop', 'mas-payload-{}'.format(image_basename))
            else:
                package_name, extension = os.path.splitext(basename)
                destination_path = os.path.join('~/Desktop', 'mas-payload-{}-{}'.format(image_basename, package_name))
            
            destination_path, did_rename = self.unique_path_for_path(destination_path)
            destination_path = os.path.expanduser(destination_path)
            
            print >> sys.stderr, 'Extracting "{}" payload to {}...'.format(basename, destination_path)
            cmd = ['/usr/libexec/productutil', '--package', package_path, '--expand', destination_path]
            process = subprocess.Popen(cmd)
            process.communicate()
            
            if single_package and not process.returncode:
                payload = glob.glob('{}/*.pkg/Payload'.format(destination_path))
                if payload:
                    cmd = ['open', payload[0]]
                    process = subprocess.Popen(cmd)
                    process.communicate()

    @classmethod
    def configure_argument_parser(cls, parser):
        super(SubcommandUnpackMasPackage, cls).configure_argument_parser(parser)
        parser.add_argument('-i', '--install', action='store_true', help='Install package to its intended location, presumably /Applications, instead of unpacking the payload to ~/Desktop')


class ANSIColor(object):

    red = '1'
    green = '2'
    yellow = '3'
    blue = '4'

    @classmethod
    @contextlib.contextmanager
    def terminal_color(cls, stdout_color=None, stderr_color=red):

        if stdout_color:
            sys.stdout.write(cls.start_sequence(stdout_color))
        if stderr_color:
            sys.stderr.write(cls.start_sequence(stderr_color))

        try:
            yield
        except:
            cls.clear()
            raise

        cls.clear()

    @classmethod
    def clear(cls):
        for stream in [sys.stdout, sys.stderr]:
            stream.write(cls.clear_sequence())

    @classmethod
    def start_sequence(cls, color=red):
        return "\x1b[3{0}m".format(color)

    @classmethod
    def clear_sequence(cls):
        return "\x1b[m"

    @classmethod
    def wrap(cls, value, color=red):
        return u'{}{}{}'.format(cls.start_sequence(color), value, cls.clear_sequence())


class Tool(object):
    """
    This is a convenience tool for mounting a disk image, doing something with its contents, and then unmounting it again. It can currently do two things with the contents of a dmg:


    1.) Installing an .app bundle

    For .dmg files that contain an .app bundle at the top level, it will install that bundle into /Applications:

        $ dmgtool.py install-application /path/to/dmg

    2.) Unpack or Install a MAS installer package

    For .dmg files that contain a MAS style .pkg file at the top, it can either:

    - unpack the payload to the Desktop for a quick inspection
    - install the package into /Applications with the "installer" command

    This example unpacks the package to the Desktop:

        $ dmgtool.py unpack-mas-package /path/to/dmg

    This installs it into /Applications:

        $ dmgtool.py unpack-mas-package -i /path/to/dmg


    Some bonus features:

    - With the -d flag, it will optionally trash the .dmg file after unmounting it.

    - You can give it the URL of a DMG instead of a path. This mounts the image directly from a web server (if the server supports it). Example:

        $ dmgtool.py unpack-mas-package https://example.com/path/to/mas-packaged-app.dmg

    and this installs it:

        $ dmgtool.py unpack-mas-package -i https://example.com/path/to/mas-packaged-app.dmg

    This example installs an application bundle directly from a web server into /Applications:

        $ dmgtool.py install-application https://example.com/path/to/app.dmg

    """

    def subcommand_map(self):
        return {s.subcommand_name(): s for s in AbstractSubcommand.subclass_map().values() if s.__name__.startswith('Subcommand')}

    def resolve_subcommand_abbreviation(self, subcommand_map):
        non_option_arguments = [i for i in sys.argv[1:] if not i.startswith('-')]
        if not non_option_arguments:
            return True

        subcommand = non_option_arguments[0]
        if subcommand in subcommand_map.keys():
            return True

        # converts a string like 'abc' to a regex like '(a).*?(b).*?(c)'
        regex = re.compile('.*?'.join(['(' + char + ')' for char in subcommand]))
        subcommand_candidates = []
        for subcommand_name in subcommand_map.keys():
            match = regex.match(subcommand_name)
            if not match:
                continue
            subcommand_candidates.append(self.subcommand_candidate_for_abbreviation_match(subcommand_name, match))

        if not subcommand_candidates:
            return True

        if len(subcommand_candidates) == 1:
            print >> sys.stderr, subcommand_candidates[0].decorated_name
            sys.argv[sys.argv.index(subcommand)] = subcommand_candidates[0].name
            return True

        print >> sys.stderr, 'Ambiguous subcommand "{}": {}'.format(subcommand, ', '.join([i.decorated_name for i in subcommand_candidates]))
        return False

    def subcommand_candidate_for_abbreviation_match(self, subcommand_name, match):
        SubcommandCandidate = collections.namedtuple('SubcommandCandidate', ['name', 'decorated_name'])
        decorated_name = ''
        for i in range(1, match.lastindex + 1):
            span = match.span(i)
            preceding = subcommand_name[match.span(i - 1)[1]:span[0]] if span[0] else ''
            letter = subcommand_name[span[0]:span[1]]
            decorated_name += preceding + ANSIColor.wrap(letter, color=ANSIColor.green)
        trailing = subcommand_name[span[1]:]
        decorated_name += trailing
        return SubcommandCandidate(subcommand_name, decorated_name)

    def configure_argument_parser(self, parser):
        pass

    def run(self):
        subcommand_map = self.subcommand_map()
        if not self.resolve_subcommand_abbreviation(subcommand_map):
            exit(1)

        parser = argparse.ArgumentParser(description=textwrap.dedent(self.__doc__), formatter_class=argparse.RawDescriptionHelpFormatter)
        self.configure_argument_parser(parser)
        parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose debug logging')
        subparsers = parser.add_subparsers(title='Subcommands', dest='subcommand_name')
        for subcommand_name, subcommand_class in subcommand_map.items():
            subparser = subparsers.add_parser(subcommand_name, help=subcommand_class.__doc__)
            subcommand_class.configure_argument_parser(subparser)

        args = parser.parse_args()
        if args.verbose:
            logging.basicConfig(level=logging.DEBUG)

        subcommand_class = subcommand_map[args.subcommand_name]
        subcommand_class(args).run()

    @classmethod
    def ensure_superuser(cls):
        if os.getuid() != 0:
            print >> sys.stderr, 'Relaunching with sudo'
            os.execv('/usr/bin/sudo', ['/usr/bin/sudo', '-E'] + sys.argv)

    @classmethod
    def main(cls):
        cls.ensure_superuser()
        try:
            cls().run()
        except KeyboardInterrupt:
            print >> sys.stderr, 'Interrupted'



if __name__ == "__main__":
    Tool.main()

########NEW FILE########
__FILENAME__ = dropbox-conflict-helper
#!/usr/bin/env python
#
# Dropbox conflict helper. To be run from within a BBEdit shell worksheet
#
# Written by Marc Liyanage
#
# https://github.com/liyanage/macosx-shell-scripts
#

import re
import os
import sys
import hashlib
import datetime
import argparse
import subprocess


class DuplicateFile(object):

    def __init__(self, path):
        assert os.path.exists(path), 'Invalid path: {}'.format(path)
        self.path = path
        self.cached_hexdigest = None
        self.cached_last_modified_timestamp = None
    
    def hexdigest(self):
        if not self.cached_hexdigest:
            hash = hashlib.new('md5')
            with open(self.path) as f:
                hash.update(f.read())
            self.cached_hexdigest = hash.hexdigest()
        return self.cached_hexdigest
    
    def last_modified_timestamp(self):
        if not self.cached_last_modified_timestamp:
            self.cached_last_modified_timestamp = datetime.datetime.fromtimestamp(os.stat(self.path).st_mtime)
        return self.cached_last_modified_timestamp
    
    def is_symlink(self):
        return os.path.islink(self.path)


class DuplicateSet(object):

    def __init__(self, original_path):
        self.original_file = DuplicateFile(original_path)
        self.duplicate_files = []

    def add_duplicate_path(self, path):
        self.duplicate_files.append(DuplicateFile(path))
    
    def all_duplicates_are_identical(self):
        if self.duplicates_contain_symlinks():
            return False

        hashes = set()
        for file in self.all_files():
            hashes.add(file.hexdigest())
        return len(hashes) == 1

    def duplicates_contain_symlinks(self):
        for file in self.all_files():
            if file.is_symlink():
                return True
        return False
    
    def all_files(self):
        return [self.original_file] + self.duplicate_files
    
    def all_files_ordered_by_date(self):
        return sorted(self.all_files(), cmp=lambda a, b: cmp(b.last_modified_timestamp(), a.last_modified_timestamp()))

    def summary(self, keep_newest=False):
        summary = ''
        for duplicate_file in self.all_files_ordered_by_date():
            summary += '# ' + subprocess.check_output(['ls', '-l', duplicate_file.path])

        if self.all_duplicates_are_identical():
            summary += '# All duplicates identical\n'
        if self.duplicates_contain_symlinks():
            summary += '# Duplicates contain symlinks\n'
        return summary

    def delete_all_duplicates_worksheet_content(self):
        worksheet_content = ''
        for duplicate_file in self.duplicate_files:
            worksheet_content += 'rm "{}"\n'.format(duplicate_file.path, self.original_file.path)
        return worksheet_content

    def worksheet_content(self, keep_newest=False):
        if self.all_duplicates_are_identical():
            return self.delete_all_duplicates_worksheet_content()

        worksheet_content = ''
        if keep_newest:
            all_files = self.all_files_ordered_by_date()
            newest_file = all_files[0]
            if self.original_file == newest_file:
                return self.delete_all_duplicates_worksheet_content()
            
            original_path = self.original_file.path
            for file in all_files[1:]:
                worksheet_content += '# diff -u "{}" "{}"\n'.format(newest_file.path, file.path)
                if file.path != original_path:
                    worksheet_content += 'rm "{}"\n'.format(file.path)
            worksheet_content += 'mv "{}" "{}"\n'.format(newest_file.path, original_path)
            return worksheet_content

        for duplicate_file in self.duplicate_files:
            if not self.all_duplicates_are_identical():
                worksheet_content += 'diff -u "{}" "{}"\n'.format(self.original_file.path, duplicate_file.path)
                worksheet_content += 'mv "{}" "{}"\n'.format(duplicate_file.path, self.original_file.path)
            worksheet_content += 'rm "{}"\n'.format(duplicate_file.path)
        return worksheet_content
    
    def __str__(self):
        return '<Duplicate {}>'.format(self.original_file.path)


class Tool(object):

    def __init__(self, args):
        self.args = args
        self.dropbox_path = os.path.expanduser(args.dropbox_path)
        assert os.path.exists(self.dropbox_path), 'Invalid Dropbox path {}'.format(dropbox_path)
        self.duplicate_sets = []
        self.duplicate_set_map = {}
        self.running_from_worksheet = 'BBEDIT_CLIENT_INTERACTIVE' in os.environ
    
    def run(self):
        self.gather_duplicates()
        self.process_duplicates()
    
    def gather_duplicates(self):
        limit = 0
        count = 0
        for root, dirs, files in os.walk(self.dropbox_path):
            if '.dropbox.cache' in dirs:
                del(dirs[dirs.index('.dropbox.cache')])

            for file in files:
                match = re.match(r'^(.*?) \([^\(]+ conflicted copy .+\)(.*)$', file)
                if not match:
                    continue

                count += 1
                if limit and count > limit:
                    return

                original_name = match.group(1)
                extension = match.group(2)
                if extension:
                    original_name += extension

                full_path = os.path.join(root, original_name)
                duplicate_set = self.duplicate_set_for_original_path(full_path)
                duplicate_set.add_duplicate_path(os.path.join(root, file))

    def process_duplicates(self):
        if not self.duplicate_sets:
            print 'No conflicted files found'
            return
            
        if not self.running_from_worksheet:
            bbedit = subprocess.Popen(['bbedit', '-s'], stdin=subprocess.PIPE)
            
        for duplicate_set in self.duplicate_sets:
            text = '# {}\n'.format(duplicate_set)
            text += duplicate_set.summary(keep_newest=self.args.keep_newest)
            text += duplicate_set.worksheet_content(keep_newest=self.args.keep_newest)
            text += '\n'
            if self.running_from_worksheet:
                sys.stdout.write(text)
            else:
                bbedit.stdin.write(text)

    def duplicate_set_for_original_path(self, path):
        duplicate_set = self.duplicate_set_map.get(path, None)
        if not duplicate_set:
            duplicate_set = DuplicateSet(path)
            self.duplicate_sets.append(duplicate_set)
            self.duplicate_set_map[path] = duplicate_set
        return duplicate_set

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(description='Helper to process Dropbox conflict duplicates')
        parser.add_argument('dropbox_path', help='Path to Drobox folder')
        parser.add_argument('-n', '--keep-newest', action='store_true', default=True, help='Default to keeping the newest duplicate of a file')

        args = parser.parse_args()
        cls(args).run()


if __name__ == '__main__':
    Tool.main()
########NEW FILE########
__FILENAME__ = dump-launchd-bookmarks
#!/usr/bin/env python

import Foundation
import plistlib
import sys
import os
import objc

plist_path = sys.argv[1] if len(sys.argv) > 1 else None
if not plist_path:
    plist_path = os.path.join('/private/var/db/launchd.db', 'com.apple.launchd.peruser.{}'.format(os.getuid()), 'overrides.plist')

plist = plistlib.readPlist(plist_path)
for key, value in plist['_com.apple.SMLoginItemBookmarks'].items():
    print
    print key
    nsdata = Foundation.NSData.dataWithBytes_length_(value.data, len(value.data))
    url, isStale, error = Foundation.NSURL.URLByResolvingBookmarkData_options_relativeToURL_bookmarkDataIsStale_error_(nsdata, 0, None, None, None)
    if error:
        info = Foundation.NSURL.resourceValuesForKeys_fromBookmarkData_('_NSURLPathKey NSURLVolumeURLKey'.split(), nsdata)
        expected_path = info['_NSURLPathKey']
        print unicode(error).encode('utf-8')
        print 'Expected but not found at: {}'.format(expected_path)
    else:
        print 'Expected and found at: {}'.format(url.path())
    
    


########NEW FILE########
__FILENAME__ = dump-scutil
#!/usr/bin/env python
#
# dump the contents of all toplevel keys in scutil's toplevel list.
#

import subprocess
import re

def run_command_with_input(command, input):
    popen = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    (stdout, stderr) = popen.communicate(input)
    return stdout

scutil_script = 'list\n'
stdout = run_command_with_input('/usr/sbin/scutil', scutil_script)
keys = re.findall(r'subKey \[\d+\] = (.+)', stdout)

for key in keys:
    scutil_script = 'show {}\n'.format(key)
    print '\n====== {} ======'.format(key)
    print run_command_with_input('/usr/sbin/scutil', scutil_script)
    

########NEW FILE########
__FILENAME__ = grep-preferences
#!/usr/bin/env python
#
# Grep preferences plists
#
# Written by Marc Liyanage
#
# https://github.com/liyanage/macosx-shell-scripts
#

import argparse
import os
import re
import subprocess
import plistlib


class Tool(object):

    def __init__(self, search_string, exclude=None):
        self.search_string = search_string.lower()
        self.exclude = []
        if exclude:
            for item in exclude:
                self.exclude.append(item.lower())
    
    def run(self):
        for dir in ['/Library/Preferences', os.path.expanduser('~/Library/Preferences')]:
            self.process_directory(dir)
    
    def process_directory(self, directory):
        for root, dirs, files in os.walk(directory):
            for file in files:
                if not file.endswith('.plist'):
                    continue
                
                did_print_file = False
                full_path = os.path.join(root, file)
                domain = full_path[:-6]
                if os.stat(full_path).st_size == 0:
                    print 'skipping zero-byte plist {}'.format(full_path)
                    continue
                    
                try:
                    xml_plist = subprocess.check_output(['sudo', 'plutil', '-convert', 'xml1', '-o', '-', full_path])
                    plist = plistlib.readPlistFromString(xml_plist)
                except Exception as e:
                    print 'Unable to read plist "{}": {}\n'.format(full_path, e)

                if not isinstance(plist, dict):
                    print 'Skipping non-dict plist of type {} in {}\n'.format(type(plist), full_path)
                    continue
                    
                for key, value in plist.items():
                    key_lower = key.lower()
                    is_excluded = False
                    if self.search_string in key_lower:
                        for exclude_item in self.exclude:
                            if exclude_item in key_lower:
                                is_excluded = True
                        if is_excluded:
                            continue
                        if not did_print_file:
                            did_print_file = True
                            print full_path
                        print u'{}: {}'.format(key, value)
                if did_print_file:
                    print ''

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(description='Grep keys in preferences plist files for string')
        parser.add_argument('search_string', help='The search string')
        parser.add_argument('--exclude', action='append', help='Exclude matches that also match this string. Can be given multiple times')

        args = parser.parse_args()
        cls(search_string=args.search_string, exclude=args.exclude).run()


if __name__ == '__main__':
    Tool.main()
########NEW FILE########
__FILENAME__ = installer-status-parse
#!/usr/bin/env python

import sys, re

percentage = 0
while True:
	line = sys.stdin.readline()
	if not line:
		break
		
	match = re.match(r'installer:(.+)', line)
	if not match:
		sys.stdout.write(line)
		continue

	line = match.group(1).strip().replace('PHASE:', '')
	match = re.match(r'%(.+)', line)
	if match:
		percentage = int(float(match.group(1)))
	else:
		status = line
	
	sys.stdout.write('\x1b[0G\x1b[0K')
	sys.stdout.write(' {0: >3d}%  {1}'.format(percentage, status))
	sys.stdout.write('\x1b[0G')
	sys.stdout.flush()

print

########NEW FILE########
__FILENAME__ = keychain_password

import subprocess, re

class KeychainPassword:

    @classmethod
    def find_internet_password(cls, username, host=None):
        cmd = ['security', 'find-internet-password', '-g', '-a', username]
        if host:
            cmd.extend(['-s', host])
        
        credentials = cls.run_security_command(cmd)
        if not credentials:
            return None
        username, password = credentials
        return password
        
    @classmethod
    def find_generic_password(cls, username, label=None):
        credentials = cls.find_generic_username_and_password(username=username, label=label)
        if not credentials:
            return None
        username, password = credentials
        return password
        
    @classmethod
    def find_generic_username_and_password(cls, username=None, label=None):
        cmd = ['security', 'find-generic-password', '-g']
        if label:
            cmd.extend(['-l', label])
        if username:
            cmd.extend(['-a', username])
        return cls.run_security_command(cmd)

    @classmethod
    def run_security_command(cls, cmd):
        try:
            security_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except:
            return None
        
        result = re.findall('password: (?:0x([A-Z0-9]+)\s+)?"(.*?)"$.*"acct"<blob>="(.*?)"$', security_output, re.DOTALL|re.MULTILINE)
        if not result:
            return None
        (hexpassword, password, username), = result

        if hexpassword:
            password = hexpassword.decode('hex').decode('utf-8')

        return username, password

        

########NEW FILE########
__FILENAME__ = keyedarchive
#!/usr/bin/env python
#
# Decode NSKeyedArchiver blobs for debugging purposes
#
# Written by Marc Liyanage
#
# See https://github.com/liyanage/macosx-shell-scripts
#

import os
import sys
import sqlite3
import argparse
import Foundation
import re
import objc
import base64
import collections
import tempfile
import subprocess
import logging

class KeyedArchiveObjectGraphNode(object):

    def __init__(self, identifier, serialized_representation):
        self.identifier = identifier
        self.serialized_representation = serialized_representation
    
    def resolve_references(self, archive):
        pass
    
    def dump_string(self, seen=None):
        raise Exception('{} must override dump_string()'.format(self.__class__))

    def indent(self, text):
        return ''.join(['|   ' + line for line in text.splitlines(True)])

    def indent_except_first(self, text, indent_count):
        lines = text.splitlines(True)
        if len(lines) < 2:
            return text
        indent = '|' + ' ' * (indent_count - 1)
        return ''.join(lines[:1] + [indent + line for line in lines[1:]])

    def wrap_text_to_line_length(self, text, length):
        return [text[i:i + length] for i in range(0, len(text), length)]

    def b64encode_and_wrap(self, bytes):
        dump = base64.b64encode(bytes)
        return '\n'.join(self.wrap_text_to_line_length(dump, 76))
    
    def __getitem__(self, key):
        raise Exception('{} must override __getitem__()'.format(self.__class__))
        
    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return False
        
    @classmethod
    def parse_serialized_representation(cls, identifier, serialized_representation):
        return cls(identifier, serialized_representation)

    @classmethod
    def node_for_serialized_representation(cls, identifier, serialized_representation):
        for node_class in cls.__subclasses__():
            if node_class.can_parse_serialized_representation(serialized_representation):
                return node_class.parse_serialized_representation(identifier, serialized_representation)
        return None
    
    @classmethod
    def is_nsdictionary(cls, value):
        return hasattr(value, 'isNSDictionary__') and value.isNSDictionary__()
    
    @classmethod
    def is_nsdata(cls, value):
        return hasattr(value, 'isNSData__') and value.isNSData__()
    
    @classmethod
    def keyed_archiver_uid_for_value(cls, value):
        if hasattr(value, 'className') and value.className() == '__NSCFType':
            # TODO: find a non-hacky way to get at the value
            ids = re.findall(r'^<CFKeyedArchiverUID.+>\{value = (\d+)\}', unicode(value))
            if ids:
                return int(ids[0])
        return None
    

class KeyedArchiveObjectGraphNullNode(KeyedArchiveObjectGraphNode):

    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return serialized_representation == '$null'
    
    def dump_string(self, seen=None):
        return '(null)'


class KeyedArchiveObjectGraphInstanceNode(KeyedArchiveObjectGraphNode):

    def __init__(self, identifier, serialized_representation):
        self.properties = {}
        super(KeyedArchiveObjectGraphInstanceNode, self).__init__(identifier, serialized_representation)
        for key, value in serialized_representation.items():
            if key == '$class':
                self.node_class = value
                continue
            self.properties[key] = value

    def resolve_references(self, archive):
        replacements = {}
        for key, value in self.properties.items():
            value = archive.replacement_object_for_value(value)
            if value:
                replacements[key] = value
        self.properties.update(replacements)

        self.node_class = archive.replacement_object_for_value(self.node_class)

    def dump_string(self, seen=None):
        if not seen:
            seen = set()
        if self in seen:
            return '<reference to {} id {}>'.format(self.node_class.dump_string(), self.identifier)
        seen.add(self)

        keys = self.properties.keys()
        instance_header = '<{} id {}>'.format(self.node_class.dump_string(), self.identifier)
        if not keys:
            instance_header += ' (empty)'
            return instance_header

        lines = [instance_header]
        max_key_len = max(map(len, keys))
        case_insensitive_sorted_property_items = sorted(self.properties.items(), key=lambda x: x[0], cmp=lambda a, b: cmp(a.lower(), b.lower()))
        for key, value in case_insensitive_sorted_property_items:
            if isinstance(value, KeyedArchiveObjectGraphNode):
#            if callable(getattr(value, 'dump_string', None)):
                description = value.dump_string(seen=seen)
            else:
                description = unicode(value)
            longest_key_padding = ' ' * (max_key_len - len(key))
            longest_key_value_indent = max_key_len + 2
            lines.append(self.indent(u'{}:{} {}'.format(key, longest_key_padding, self.indent_except_first(description, longest_key_value_indent))))
        
        return '\n'.join(lines)
    
    def __getitem__(self, key):
        if key not in self.properties:
            raise KeyError('Unknown key {}'.format(key))
        value = self.properties[key]
        if isinstance(value, KeyedArchiveObjectGraphNode):
            value = value.dump_string()
        return value
    

    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return cls.is_nsdictionary(serialized_representation) and '$class' in serialized_representation

    @classmethod
    def parse_serialized_representation(cls, identifier, serialized_representation):
        for node_class in cls.__subclasses__():
            if node_class.can_parse_serialized_representation(serialized_representation):
                return node_class.parse_serialized_representation(identifier, serialized_representation)
        return super(KeyedArchiveObjectGraphInstanceNode, cls).parse_serialized_representation(identifier, serialized_representation)


class KeyedArchiveObjectGraphNSDateNode(KeyedArchiveObjectGraphInstanceNode):
    
    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return 'NS.time' in serialized_representation

    def dump_string(self, seen=None):
        return unicode(Foundation.NSDate.dateWithTimeIntervalSinceReferenceDate_(self.serialized_representation['NS.time']))


class KeyedArchiveObjectGraphNSMutableDataNode(KeyedArchiveObjectGraphInstanceNode):
    
    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return 'NS.data' in serialized_representation

    def dump_string(self, seen=None):
        b64dump = self.b64encode_and_wrap(self.serialized_representation['NS.data'].bytes())
        return u'<NSMutableData length {}>\n{}'.format(self.serialized_representation['NS.data'].length(), b64dump)


class KeyedArchiveObjectGraphNSDataNode(KeyedArchiveObjectGraphNode):

    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return cls.is_nsdata(serialized_representation)

    def dump_string(self, seen=None):
        b64dump = self.b64encode_and_wrap(self.serialized_representation.bytes())
        return u'<NSData length {}>\n{}'.format(self.serialized_representation.length(), b64dump)


class KeyedArchiveObjectGraphBoolNode(KeyedArchiveObjectGraphNode):

    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return isinstance(serialized_representation, bool)

    def dump_string(self, seen=None):
        return 'True' if bool(self.serialized_representation) else 'False'


class KeyedArchiveObjectGraphLongNode(KeyedArchiveObjectGraphNode):

    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return isinstance(serialized_representation, objc._pythonify.OC_PythonLong)

    def dump_string(self, seen=None):
        return str(self.serialized_representation)


class KeyedArchiveObjectGraphFloatNode(KeyedArchiveObjectGraphNode):

    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return isinstance(serialized_representation, objc._pythonify.OC_PythonFloat)

    def dump_string(self, seen=None):
        return str(self.serialized_representation)


class KeyedArchiveObjectGraphNSMutableStringNode(KeyedArchiveObjectGraphInstanceNode):
    
    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return 'NS.string' in serialized_representation

    def dump_string(self, seen=None):
        return self.serialized_representation['NS.string']


class KeyedArchiveObjectGraphNSDictionaryNode(KeyedArchiveObjectGraphInstanceNode):
    
    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return 'NS.keys' in serialized_representation and 'NS.objects' in serialized_representation

    def resolve_references(self, archive):
        super(KeyedArchiveObjectGraphNSDictionaryNode, self).resolve_references(archive)

        dictionary = {}
        for index, key in enumerate(self.serialized_representation['NS.keys']):
            replacement_key = archive.replacement_object_for_value(key)
            if replacement_key:
                key = replacement_key.dump_string()
            value = self.serialized_representation['NS.objects'][index]
            replacement_value = archive.replacement_object_for_value(value)
            if replacement_value:
                value = replacement_value
            dictionary[key] = value
        self.properties.update(dictionary)
        del(self.properties['NS.keys'])
        del(self.properties['NS.objects'])


class KeyedArchiveObjectGraphNSArrayNode(KeyedArchiveObjectGraphInstanceNode):
    
    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return 'NS.objects' in serialized_representation and 'NS.keys' not in serialized_representation

    def resolve_references(self, archive):
        super(KeyedArchiveObjectGraphNSArrayNode, self).resolve_references(archive)

        dictionary = {}
        fill = len(str(len(self.serialized_representation['NS.objects'])))
        for index, value in enumerate(self.serialized_representation['NS.objects']):
            replacement_value = archive.replacement_object_for_value(value)
            if replacement_value:
                value = replacement_value
            dictionary['{:0{fill}d}'.format(index, fill=fill)] = value
        self.properties.update(dictionary)
        del(self.properties['NS.objects'])


class KeyedArchiveObjectGraphClassNode(KeyedArchiveObjectGraphNode):

    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return cls.is_nsdictionary(serialized_representation) and '$classname' in serialized_representation

    def dump_string(self):
        return self.serialized_representation['$classname']


class KeyedArchiveObjectGraphStringNode(KeyedArchiveObjectGraphNode):

    @classmethod
    def can_parse_serialized_representation(cls, serialized_representation):
        return isinstance(serialized_representation, basestring)

    def dump_string(self, seen=None):
        return unicode(self.serialized_representation)


class KeyedArchiveInputData(object):

    def __init__(self, raw_data):
        self.raw_data = raw_data
        self.encoded_data = None
        self.decoded_data = None
        self.decode_data()
        
    def decode_data(self):
        self.encoded_data = self.raw_data
        self.decoded_data = self.raw_data
    
    def data(self):
        return self.decoded_data
    
    def encoded_data_length(self):
        if not self.encoded_data:
            return 0
        return len(self.encoded_data)
    
    def raw_data_is_ascii(self):
        try:
            self.raw_data.decode('ascii')
        except UnicodeDecodeError:
            return False
        return True
    
    @classmethod
    def priority(cls):
        return 0
    
    @classmethod
    def identifier(cls):
        return cls.__name__.replace('KeyedArchiveInputData', '').lower()
    
    @classmethod
    def guess_encoding(cls, data, encoding='auto'):
        if encoding == 'none':
            return cls(data)
        logging.debug('encoding: {}'.format(encoding))
        subclasses = cls.__subclasses__()

        if encoding == 'auto':
            items = []
            for subclass in subclasses:
                try:
                    item = subclass(data)
                    items.append(item)
                except:
                    pass
            
            def item_comparator(a, b):
                length_comparison = cmp(b.encoded_data_length(), a.encoded_data_length())
                if length_comparison != 0:
                    return length_comparison
                
                return cmp(b.priority(), a.priority())
            
            items = sorted(items, cmp=item_comparator)
            item = items[0]
            if items[0].encoded_data_length() == 0:
                # fall back to 'none'
                item = cls(data)
            logging.debug('Encoding "auto" picked encoding class {}'.format(type(item)))
            return item

        for subclass in subclasses:
            if subclass.identifier() == encoding:
                return subclass(data)
        
        raise Exception('Unable to determine input encoding')
        

class KeyedArchiveInputDataHex(KeyedArchiveInputData):
    
    def decode_data(self):
        if not self.raw_data_is_ascii():
            return

        regular_expressions = [r'<([A-Fa-f\s0-9]+)>', r'([A-Fa-f\s0-9]+)']
        for regex in regular_expressions:
            matches = re.findall(regex, self.raw_data, re.MULTILINE)
            if matches:
                matches = sorted(matches, key=len, reverse=True)
                data = matches[0]
                data = re.sub(r'\s+', '', data)
                self.encoded_data = data
                self.decoded_data = data.decode('hex')
                return

    @classmethod
    def priority(cls):
        return 1

class KeyedArchiveInputDataBase64(KeyedArchiveInputData):

    def decode_data(self):
        if not self.raw_data_is_ascii():
            return

        matches = re.findall(r'([A-Za-z\s0-9+/=]+)', self.raw_data, re.MULTILINE)
        if not matches:
            return

        if matches:
            matches = sorted(matches, key=len, reverse=True)
        
        data = matches[0]
        data = re.sub(r'\s+', '', data)
        self.encoded_data = data
        self.decoded_data = base64.b64decode(data)
        

class KeyedArchive(object):

    def __init__(self, archive_dictionary):
        self.archive_dictionary = archive_dictionary
        self.parse_archive_dictionary()
    
    def parse_archive_dictionary(self):
        self.objects = []

        for index, obj in enumerate(self.archive_dictionary['$objects']):
            node = KeyedArchiveObjectGraphNode.node_for_serialized_representation(index, obj)
            if not node:
                raise Exception('Unable to parse serialized representation: {} / {}'.format(type(obj), obj))
            assert isinstance(node, KeyedArchiveObjectGraphNode)
            self.objects.append(node)

        for object in self.objects:
            object.resolve_references(self)
        
        self.top_object = self.object_at_index(self.top_object_identifier())
    
    def top_object_identifier(self):
        top_object_reference = self.archive_dictionary['$top']['root']
        top_object_identifier = KeyedArchiveObjectGraphNode.keyed_archiver_uid_for_value(top_object_reference)
        if top_object_identifier is None:
            raise Exception('Unable to find root object')
        return top_object_identifier
    
    def object_at_index(self, index):
        return self.objects[index]
    
    def dump_string(self):
        return self.top_object.dump_string()

    def replacement_object_for_value(self, value):
        id = KeyedArchiveObjectGraphNode.keyed_archiver_uid_for_value(value)
        if id is None:
            return None
        return self.object_at_index(id)
    
    @classmethod
    def archive_from_bytes(cls, bytes):
        bytes = bytearray(bytes)
        assert bytes, 'Missing input data'
        archive_dictionary, format, error = Foundation.NSPropertyListSerialization.propertyListWithData_options_format_error_(bytes, 0, None, None)
        if not archive_dictionary:
            return None, error
        return cls(archive_dictionary), None

    @classmethod
    def archives_from_sqlite_table_column(cls, connection, table_name, column_name, extra_columns):
        columns = [column_name]
        if extra_columns:
            columns.extend(extra_columns)
        sql = 'SELECT {} FROM {}'.format(', '.join(columns), table_name)
        cursor = connection.execute(sql)

        ArchiveDataRow = collections.namedtuple('ArchiveDataRow', 'archive extra_data error'.split())

        archives = []
        for row in cursor:
            blob, extra_fields = row[0], cls.sanitize_row(row[1:])
            archive = None
            error = None
            if blob:
                archive, error = cls.archive_from_bytes(blob)
            extra_data = dict(zip(extra_columns, extra_fields)) if extra_columns else None
            archive_data_row = ArchiveDataRow(archive, extra_data, error)
            archives.append(archive_data_row)
        return archives

    @classmethod
    def dump_archives_from_sqlite_table_column(cls, connection, table_name, column_name, extra_columns):
        rows = cls.archives_from_sqlite_table_column(connection, table_name, column_name, extra_columns)
        for row in rows:
            if row.extra_data:
                print row.extra_data
            if row.archive:
                print row.archive.dump_string()
            else:
                if row.extra_data:
                    print '(null)'
    
    @classmethod
    def sanitize_row(cls, row):
        return ['(null)' if i is None else i for i in row]

    @classmethod
    def dump_archive_from_plist_file(cls, plist_path, keypath):
        with open(plist_path) as f:
            bytes = f.read()
        assert bytes, 'Input file {} is empty'.format(plist_path)
        bytes = bytearray(bytes)
        plist_dictionary, format, error = Foundation.NSPropertyListSerialization.propertyListWithData_options_format_error_(bytes, 0, None, None)
        if not plist_dictionary:
            raise Exception('Unable to read property list from {}'.format(plist_dictionary))
        value = plist_dictionary.valueForKeyPath_(keypath)
        archive, error = cls.archive_from_bytes(value.bytes())
        print archive.dump_string()
    
    @classmethod
    def dump_archive_from_file(cls, archive_file, encoding, output_file=None):
        if not output_file:
            output_file = sys.stdout
        archive = cls.archive_from_file(archive_file, encoding)
        print >> output_file, archive.dump_string().encode('utf-8')

    @classmethod
    def archive_from_file(cls, archive_file, encoding):
        data = archive_file.read()
        
        data = KeyedArchiveInputData.guess_encoding(data, encoding)
        archive, error = cls.archive_from_bytes(data.data())
        if not archive:
            if error:
                error = unicode(error).encode('utf-8')
            raise Exception('Unable to decode a keyed archive from input data: {}'.format(error))
        return archive
    

class KeyedArchiveTool(object):

    def __init__(self, args):
        self.args = args

    def run(self):
    
        if self.args.verbose:
            logging.basicConfig(level=logging.DEBUG)
    
        # If the ThisServiceMode env variable is set
        # (see http://wafflesoftware.net/thisservice/ for details),
        # switch to filter mode
        if os.environ.get('ThisServiceMode'):
            self.args.service_mode = True
        
        if self.args.service_mode:
            self.run_service()
        elif self.args.sqlite_path:
            self.run_sqlite()
        elif self.args.plist_path:
            self.run_plist()
        else:
            self.run_file()
        
    def run_sqlite(self):
        conn = sqlite3.connect(self.args.sqlite_path)
        KeyedArchive.dump_archives_from_sqlite_table_column(conn, self.args.sqlite_table, self.args.sqlite_column, self.args.extra_columns)

    def run_plist(self):
        KeyedArchive.dump_archive_from_plist_file(self.args.plist_path, self.args.plist_keypath)
    
    def run_file(self):
        if self.args.infile is None:
            self.parser().print_help()
            exit(0)
        KeyedArchive.dump_archive_from_file(self.args.infile, self.args.encoding)
    
    def run_service(self):
        temp = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
        try:
            KeyedArchive.dump_archive_from_file(sys.stdin, self.args.encoding, output_file=temp)
        except Exception as e:
            temp.write('Unable to decode NSKeyedArchive: {}'.format(e))
        temp.close()
        subprocess.call(['open', '-a', 'Safari', temp.name])

    @classmethod
    def parser(cls):
        parser = argparse.ArgumentParser(description='NSKeyedArchive tool')
        parser.add_argument('--verbose', action='store_true', help='Enable some additional debug logging output')

        file_group = parser.add_argument_group(title='Reading from Files', description='Read the serialized archive from a file or stdin. The tool tries to guess the binary-to-text encoding, if any, unless one is chosen explicitly.')
        file_group.add_argument('infile', nargs='?', type=argparse.FileType('r'), help='The path to the input file. Pass - to read from stdin')
        file_group.add_argument('--encoding', choices='auto hex base64 none'.split(), default='auto', help='The binary-to-text encoding, if any. The default is auto.')
        file_group.add_argument('--service_mode', action='store_true', help='Enable OS X service mode. Take input from stdin with auto-detected encoding and write the result to a temporary text file and open it with Safari.')
        
        sqlite_group = parser.add_argument_group(title='Reading from SQLite databases', description='Read the serialized archive from SQLite DB. You need to pass at least the sqlite_path, sqlite_table, and sqlite_column options.')
        sqlite_group.add_argument('--sqlite_path', help='The path to the SQLite database file')
        sqlite_group.add_argument('--sqlite_table', help='SQLite DB table name')
        sqlite_group.add_argument('--sqlite_column', help='SQLite DB column name')
        sqlite_group.add_argument('--sqlite_extra_column', action='append', dest='extra_columns', help='additional column name, just for printing. Can occur multiple times.')

        plist_group = parser.add_argument_group(title='Reading from Property Lists', description='Read the serialized archive from a property list file, usually a preferences file in ~/Library/Preferences. You need to pass the plist_path and plist_keypath options.')
        plist_group.add_argument('--plist_path', help='The path to the plist file')
        plist_group.add_argument('--plist_keypath', help='The key/value coding key path to the object in the plist that contains the serialized keyed archiver data.')

        return parser

    @classmethod
    def main(cls):
        cls(cls.parser().parse_args()).run()

if __name__ == '__main__':
    KeyedArchiveTool.main()

########NEW FILE########
__FILENAME__ = mitmproxywrapper
# This script has been merged into the mitmproxy distribution, upstream and in my fork:
# https://github.com/liyanage/mitmproxy/blob/master/examples/mitmproxywrapper.py

########NEW FILE########
__FILENAME__ = notificationlistener
#!/usr/bin/env python

# Listen for and dump NSDistributedNotifications
#
# Maintainted at https://github.com/liyanage/macosx-shell-scripts

import objc
import datetime
import Foundation

class DistributedNotificationListener(object):

    def __init__(self):
        self.should_terminate = False

    def run(self):
        center = Foundation.NSDistributedNotificationCenter.defaultCenter()
        selector = objc.selector(self.didReceiveNotification_, signature='v@:@')
        center.addObserver_selector_name_object_suspensionBehavior_(self, selector, None, None, Foundation.NSNotificationSuspensionBehaviorDeliverImmediately)
        runloop = Foundation.NSRunLoop.currentRunLoop()
        
        while not self.should_terminate:
            runloop.runUntilDate_(Foundation.NSDate.dateWithTimeIntervalSinceNow_(1))
    
    def didReceiveNotification_(self, notification):
        timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        print '{} name={} object={} userInfo={}'.format(timestamp, notification.name(), notification.object(), notification.userInfo())

    def terminate(self):
        print 'Stopping'
        self.should_terminate = True
    
    @classmethod
    def main(cls):
        listener = cls()
        try:
            listener.run()
        except KeyboardInterrupt:
            listener.terminate()

if __name__ == '__main__':
    DistributedNotificationListener.main()

########NEW FILE########
__FILENAME__ = shell

import subprocess, sys
import xml.etree.ElementTree

class Shell:

	def __init__(self, fatal = False, verbose = False):
		self.fatal = fatal
		self.verbose = verbose
		self.reset()
	
	def reset(self):
		self.xml = None
		self.plist = None
	
	def run(self, command, silent = False):
		self.reset()
		command_is_string = isinstance(command, basestring)
		popen = subprocess.Popen(command, stderr = subprocess.PIPE, stdout = subprocess.PIPE, shell = command_is_string)
		(self.output, self.stderr) = popen.communicate()
		self.returncode = popen.returncode

		should_log_failure = self.returncode and self.fatal

		if self.verbose or should_log_failure:
			if not command_is_string:
				command = ' '.join(command)
			
		if self.verbose and not should_log_failure:
			print "running shell command:", command
			
		if should_log_failure:
			print >> sys.stderr, 'Non-zero exit status {0} for command "{1}": {2}'.format(self.returncode, command, self.stderr)
			sys.exit(1)
		
		if self.stderr and not silent:
			print >> sys.stderr, self.stderr
		
		return self

	def output_strip(self):
		return self.output.strip()

	def output_xml(self):
		if not self.xml:
			self.xml = xml.etree.ElementTree.fromstring(self.output)
		return self.xml
	
	def output_plist(self):
		if not self.plist:
			self.plist = plistlib.readPlistFromString(self.output)
		return self.plist

########NEW FILE########
__FILENAME__ = svn-revision-info
#!/usr/bin/env python
#
# Takes a list of SVN revision numbers on stdin and an SVN base URL as argument.
# Looks up the commit message for each revision and prints a line with revision number and message.
#
# Intended usage is with the output of svn mergeinfo:
# 
#     svn mergeinfo --show-revs eligible svn_url_1 svn_url_2 | svn-revision-info.py svn_base_url
#
# or alternatively with two SVN URLs, in which case the script runs "svn mergeinfo" for you
# and figures out the base URL automatically:
# 
#     svn-revision-info.py svn_url_1 svn_url_2
#
# Written by Marc Liyanage <http://www.entropy.ch>
# 

import subprocess, sys, re, xml.etree.ElementTree
from pprint import pprint

svn_url_src = ''
svn_url_dst = ''
svn_base_url = ''

argc = len(sys.argv)
if argc == 3:
	svn_url_src, svn_url_dst = sys.argv[1:3]
elif argc == 2:
	svn_base_url = sys.argv[1]
	input_lines = [line.rstrip() for line in sys.stdin]
else:
	print >> sys.stderr, 'Usage:'
	print >> sys.stderr, '{0} svn_base_url < file_with_list_of_revisions'.format(sys.argv[0])
	print >> sys.stderr, '{0} svn_url_source svn_url_destination'.format(sys.argv[0])
	exit(1)

if svn_url_src:
	cmd = 'svn mergeinfo --show-revs eligible "{0}" "{1}"'.format(svn_url_src, svn_url_dst)
	popen = subprocess.Popen(cmd, stdout = subprocess.PIPE, shell = True)
	output = popen.communicate()[0]
	if popen.returncode:
		print >> sys.stderr, 'Nonzero exit status for "{0}"'.format(cmd)
		exit(1)
	input_lines = output.split()
	
	cmd = 'svn info --xml "{0}"'.format(svn_url_src)
	popen = subprocess.Popen(cmd, stdout = subprocess.PIPE, shell = True)
	output = popen.communicate()[0]
	if popen.returncode:
		print >> sys.stderr, 'Nonzero exit status for "{0}"'.format(cmd)
		exit(1)

	tree = xml.etree.ElementTree.fromstring(output)
	svn_base_url = tree.findtext('entry/repository/root')


for line in input_lines:
	match = re.search('(\d+)', line)
	if not match:
		if re.match('^\s*$', line):
			print line
		continue
	
	revision = match.group(0)
	cmd = 'svn log -l 1 --xml {0}@{1}'.format(svn_base_url, revision)
	popen = subprocess.Popen(cmd, stdout = subprocess.PIPE, shell = True)
	output = popen.communicate()[0]
	if popen.returncode:
		print >> sys.stderr, 'Nonzero exit status for "{0}"'.format(cmd)
		continue

	tree = xml.etree.ElementTree.fromstring(output)
	author = tree.find('logentry').findtext('author')
	msg = tree.find('logentry').findtext('msg')
	msg = ' '.join(msg.strip().splitlines())
	truncated = msg[:100]
	if len(truncated) < len(msg):
		truncated += ' [...]'
	msg = '{0} [{1:<10}]  {2}'.format(line, author[0:10], truncated.encode('utf-8'))
	print msg

########NEW FILE########
__FILENAME__ = svnstatus
#!/usr/bin/env python
#
# Cleaned up "svn status" output
#

import subprocess, time, sys

popen = subprocess.Popen(['svn', 'status'], stdout = subprocess.PIPE)
output = popen.communicate()[0]
if popen.returncode:
	sys.exit(1)

current_external = ''
for line in output.splitlines():
	
	if not len(line) or line.startswith('X'):
		continue

	if line.startswith('Performing status on external'):
		current_external = line
		print "\x1b[2K\r",
		print current_external,
		sys.stdout.flush()
		time.sleep(0.01)
		continue

	if current_external:
		current_external = ''
		print

	print line

print "\x1b[2K",

########NEW FILE########
__FILENAME__ = usernotification
#!/usr/bin/env python
#
# Send OS X NSUserNotifications from Python.
#
# Written by Marc Liyanage
#
# https://github.com/liyanage/macosx-shell-scripts
#

import AppKit
import argparse


class UserNotification(object):
    
    def __init__(self, title, subtitle=None, informative_text=None, image_path=None):
        self.title = title
        self.subtitle = subtitle
        self.informative_text = informative_text
        self.image_path = image_path
    
    def post(self):
        notification = AppKit.NSUserNotification.alloc().init()
        notification.setTitle_(self.title)
        if self.subtitle:
            notification.setSubtitle_(self.subtitle)
        if self.informative_text:
            notification.setInformativeText_(self.informative_text)
        if self.image_path:
            image = AppKit.NSImage.alloc().initByReferencingFile_(self.image_path)
        
        center = AppKit.NSUserNotificationCenter.defaultUserNotificationCenter()
        center.scheduleNotification_(notification)
    
    def __unicode__(self):
        return u'<UserNotification title={} subtitle={} informative_text={}>'.format(self.title, self.subtitle, self.informative_text)

    def __str__(self):
        return unicode(self).encode('utf-8')


class UserNotificationTool(object):
    
    def __init__(self, args):
        self.args = args
    
    def post_notification(self):
        title = unicode(self.args.title, 'utf-8')
        subtitle = unicode(self.args.subtitle, 'utf-8') if self.args.subtitle else None
        informative_text = unicode(self.args.informative_text, 'utf-8') if self.args.informative_text else None
        image_path = unicode(self.args.image_path, 'utf-8') if self.args.image_path else None
        notification = UserNotification(title, subtitle=subtitle, informative_text=informative_text, image_path=image_path)
        notification.post()
        print notification
        
    
    @classmethod
    def run(cls):
        parser = argparse.ArgumentParser(description='Post Mac OS X user notifications')
        parser.add_argument('title', help='The notification title')
        parser.add_argument('subtitle', nargs='?', help='The notification subtitle')
        parser.add_argument('informative_text', nargs='?', help='The notification informative text')
        parser.add_argument('--image', dest='image_path', help='Optional Path to an image')

        args = parser.parse_args()
        tool = cls(args)
        tool.post_notification()


if __name__ == '__main__':
    UserNotificationTool.run()
########NEW FILE########
__FILENAME__ = wordlist
#!/usr/bin/env python

import random
import sys

def find_words(node, available, parents=None):
    if parents is None:
        parents = []
    if '_leaf' in node:
        yield ''.join(parents)
    for char in (i for i in set(available) if i in node):
        remaining = available[:]
        remaining.remove(char)
        for word in find_words(node[char], remaining, parents + [char]):
            yield word

def read_words(filename):
    root = {}
    with open(filename) as f:
        for line in (line.rstrip().lower() for line in f.readlines()):
            node = root
            for char in line:
                node = node.setdefault(char, {})
            node['_leaf'] = True
    return root

available_characters = list(sys.argv[1])
length_comparator = lambda x, y: cmp(len(x), len(y))
words = sorted(find_words(read_words('/usr/share/dict/words'), available_characters), length_comparator)
print ' '.join(words)


########NEW FILE########
