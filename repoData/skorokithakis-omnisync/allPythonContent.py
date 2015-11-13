__FILENAME__ = configuration
"""omnisync configuration module."""

import logging
import re

log = logging.getLogger("omnisync")

class Configuration:
    """Hold various configuration options."""

    def __init__(self, options):
        """Retrieve the configuration from the parser options."""
        if options.verbosity == 0:
            log.setLevel(logging.ERROR)
        elif options.verbosity == 1:
            log.setLevel(logging.INFO)
        elif options.verbosity == 2:
            log.setLevel(logging.DEBUG)
            log.debug("Debug logging on")
        self.delete = options.delete
        if options.attributes:
            self.requested_attributes = set(options.attributes)
        else:
            self.requested_attributes = set()
        self.dry_run = options.dry_run
        self.update = options.update
        if self.update:
            self.requested_attributes.add("mtime")
        self.recursive = options.recursive
        if options.exclude_files:
            self.exclude_files = re.compile(options.exclude_files)
        else:
            # An unmatchable regex, to save us from checking if this is set. Hopefully it's
            # not too slow.
            self.exclude_files = re.compile("^$")
        if options.include_files:
            self.include_files = re.compile(options.include_files)
            if not self.exclude_files:
                self.exclude_files = re.compile("")
        else:
            self.include_files = re.compile("^$")
        if options.exclude_dirs:
            self.exclude_dirs = re.compile(options.exclude_dirs)
        else:
            self.exclude_dirs = re.compile("^$")
        if options.include_dirs:
            self.include_dirs = re.compile(options.include_dirs)
            if not self.exclude_dirs:
                self.exclude_dirs = re.compile("")
        else:
            self.include_dirs = re.compile("^$")
        
        # access to remaining options and any options
        # that were set by plugins.
        self.full_options = options
        
        self.exclude_attributes = set()
        
########NEW FILE########
__FILENAME__ = fileobject
"""A file object class."""

class FileObject(object):
    """A file object that caches file attributes."""
    def __init__(self, transport, url, attributes=None):
        super(FileObject, self).__setattr__("_transport", transport)
        if not attributes:
            attributes = {}
        super(FileObject, self).__setattr__("_attr_dict", attributes)
        super(FileObject, self).__setattr__("url", url)

    def __getattr__(self, name):
        """Get the requested attribute from the cache, or fetch it if it doesn't exist.."""
        try:
            return self._attr_dict[name]
        except KeyError:
            if name == "isdir":
                self._attr_dict[name] = self._transport.isdir(self.url)
                return self._attr_dict[name]
            # See if we can getattr() for the attribute.
            elif name in self._transport.getattr_attributes:
                attrs = self._transport.getattr(self.url, name)
                self._attr_dict.update(attrs)
                return self._attr_dict[name]
            else:
                # Doing a listdir() is left as an exercise for the reader.
                raise

    def __eq__(self, other):
        """Test equality of two class instances."""
        if self.url == other.url:
            return True
        else:
            return False

    def __ne__(self, other):
        """Test inequality of two class instances."""
        if self.url != other.url:
            return True
        else:
            return False

    def __setattr__(self, name, value):
        """Set the requested attribute."""
        self._attr_dict[name] = value

    def __repr__(self):
        """Return a human-readable description of the object."""
        return self.url

    def __contains__(self, name):
        """Returns True if we have cached the attribute, False otherwise."""
        if name in self._attr_dict:
            return True
        else:
            return False

    @property
    def attribute_set(self):
        """Return a set of cached attributes."""
        return set(self._attr_dict)

    @property
    def attributes(self):
        """Return the cached attribute dict."""
        return self._attr_dict

    def populate_attributes(self, attr_list):
        """Retrieve a file's requested attributes and populate the instance's attributes
           with them."""
        for attribute in attr_list:
            if attribute not in self._attr_dict:
                assert attribute in self._transport.getattr_attributes, \
                       "Attribute %s not recoverable by getattr()" % attribute
                self._attr_dict.update(self._transport.getattr(self.url, [attribute]))

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
"""The main omnisync module."""

import os
import sys
import logging
import optparse
import time
import locale

from omnisync.configuration import Configuration
from omnisync.progress import Progress

from omnisync.version import VERSION
from omnisync.transportmount import TransportInterface
from omnisync.fileobject import FileObject
from omnisync.urlfunctions import url_splice, url_split, url_join, normalise_url, append_slash

log = logging.getLogger("omnisync.main")

class OmniSync(object):
    """The main program class."""
    def __init__(self):
        """Initialise various program structures."""
        self.source = None
        self.destination = None
        self.source_transport = None
        self.destination_transport = None
        self.config = None
        self.max_attributes = None
        self.max_evaluation_attributes = None

        self.file_counter = 0
        self.bytes_total = 0

        transp_dir = "transports"
        # If we have been imported, get the path.
        if __name__ != "__main__":
            os_dir = os.path.dirname(os.path.join(os.getcwd(), __file__))
            basedir = os.path.join(os_dir, transp_dir)
            sys.path.append(os_dir)
        else:
            basedir = transp_dir

        # Import the I/O module classes.
        for module in os.listdir(basedir):
            if module.endswith(".py"):
                module_name = "omnisync." + transp_dir + "." + module[:-3]
                log.debug("Importing \"%s\"." % (module_name))
                try:
                    __import__(module_name)
                except ImportError:
                    pass

        # Instantiate a dictionary in {"protocol": module} format.
        self.transports = {}
        for transport in TransportInterface.transports:
            for protocol in transport.protocols:
                if protocol in self.transports:
                    log.warning("Protocol %s already handled, ignoring." % protocol)
                else:
                    self.transports[protocol] = transport
    
    def exit(self, return_code):
        """Ends the sync, with the return_code provided."""
        sys.exit(return_code)
        
    def add_options(self, parser):
        """Set plugin options on the command-line parser."""
        for transport in self.transports.values():
            for args, kwargs in transport().add_options():
                kwargs["help"] = kwargs["help"] + " (%s)" % ", ".join(transport.protocols)
                kwargs["dest"] = kwargs["dest"] + transport.protocols[0]
                parser.add_option(*args, **kwargs)

    def check_locations(self):
        """Check that the two locations are suitable for synchronisation."""
        if url_split(self.source).get_dict().keys == ["scheme"]:
            log.error("You need to specify something more than that for the source.")
            return False
        elif url_split(self.source).get_dict().keys == ["scheme"]:
            log.error("You need to specify more information than that for the destination.")
            return False
        elif not self.source_transport.exists(self.source):
            log.error("The source location \"%s\" does not exist, aborting." %
                          self.source)
            return False

        # Check if both locations are of the same type.
        source_isdir = self.source_transport.isdir(self.source)
        leave = False
        if self.source.startswith(self.destination) and source_isdir:
            log.error("The destination directory is a parent of the source directory.")
            leave = True
        elif not hasattr(self.source_transport, "read"):
            log.error("The source protocol is write-only.")
            leave = True
        elif not hasattr(self.destination_transport, "write"):
            log.error("The destination protocol is read-only.")
            leave = True
        elif not hasattr(self.destination_transport, "remove") and self.config.delete:
            log.error("The destination protocol does not support file deletion.")
            leave = True
        elif self.config.requested_attributes - self.source_transport.getattr_attributes:
            log.error("Requested attributes cannot be read: %s." %
                          ", ".join(x for x in self.config.requested_attributes - \
                                    self.source_transport.getattr_attributes)
                          )
            leave = True
        elif self.config.requested_attributes - self.destination_transport.setattr_attributes:
            log.error("Requested attributes cannot be set: %s." %
                          ", ".join(x for x in self.config.requested_attributes - \
                                    self.destination_transport.setattr_attributes)
                          )
            leave = True

        if leave:
            return False
        else:
            return True

    def sync(self, source, destination):
        """Synchronise two locations."""
        start_time = time.time()
        self.source = normalise_url(source)
        self.destination = normalise_url(destination)

        # Instantiate the transports.
        try:
            self.source_transport = self.transports[url_split(self.source).scheme]()
        except KeyError:
            log.error("Protocol not supported: %s." % url_split(self.source).scheme)
            return
        try:
            self.destination_transport = self.transports[url_split(self.destination).scheme]()
        except KeyError:
            log.error("Protocol not supported: %s." % url_split(self.destination).scheme)
            return

        # Give the transports a chance to connect to their servers.
        try:
            self.source_transport.connect(self.source, self.config)
        except:
            log.error("Connection to source failed, exiting...")
            self.exit(1)
        try:
            self.destination_transport.connect(self.destination, self.config)
        except:
            log.error("Connection to destination failed, exiting...")
            self.exit(1)

        # These are the most attributes we can expect from getattr calls in these two protocols.
        self.max_attributes = (self.source_transport.getattr_attributes &
                               self.destination_transport.getattr_attributes)

        self.max_evaluation_attributes = (self.source_transport.evaluation_attributes &
                                          self.destination_transport.evaluation_attributes)

        if not self.check_locations():
            self.exit(1)

        # Begin the actual synchronisation.
        self.recurse()

        self.source_transport.disconnect()
        self.destination_transport.disconnect()
        total_time = time.time() - start_time
        locale.setlocale(locale.LC_NUMERIC, '')
        try:
            bps = locale.format("%d", int(self.bytes_total / total_time), True)
        except ZeroDivisionError:
            bps = "inf"
        log.info("Copied %s files (%s bytes) in %s sec (%s Bps)." % (
                      locale.format("%d", self.file_counter, True),
                      locale.format("%d", self.bytes_total, True),
                      locale.format("%.2f", total_time, True),
                      bps))

    def set_destination_attributes(self, destination, attributes):
        """Set the destination's attributes. This is a wrapper for the transport's _setattr_."""
        # The given attributes might not have any we're able to set, so just return if that's
        # the case.
        if not self.config.dry_run and \
           set(attributes) & set(self.destination_transport.setattr_attributes):
            self.destination_transport.setattr(destination, attributes)

    def compare_directories(self, source, source_dir_list, dest_dir_url):
        """Compare the source's directory list with the destination's and perform any actions
           necessary, such as deleting files or creating directories."""
        dest_dir_list = self.destination_transport.listdir(dest_dir_url)
        if not dest_dir_list:
            if not self.config.dry_run:
                self.destination_transport.mkdir(dest_dir_url)
                # Populate the item's attributes for the remote directory so we can set them.
                attribute_set = self.max_evaluation_attributes & \
                                self.destination_transport.setattr_attributes
                attribute_set = attribute_set | self.config.requested_attributes
                attribute_set = attribute_set ^ self.config.exclude_attributes
                source.populate_attributes(attribute_set)

                self.set_destination_attributes(dest_dir_url, source.attributes)
            dest_dir_list = []
        # Construct a dictionary of {filename: FileObject} items.
        dest_paths = dict([(url_split(append_slash(x.url, False),
                                      self.destination_transport.uses_hostname,
                                      True).file, x) for x in dest_dir_list])
        create_dirs = []
        for item in source_dir_list:
            # Remove slashes so the splitter can get the filename.
            url = url_split(append_slash(item.url, False),
                            self.source_transport.uses_hostname,
                            True).file
            # If the file exists and both the source and destination are of the same type...
            if url in dest_paths and dest_paths[url].isdir == item.isdir:
                # ...if it's a directory, set its attributes as well...
                if dest_paths[url].isdir:
                    log.info("Setting attributes for %s..." % url)
                    item.populate_attributes(self.max_evaluation_attributes |
                                             self.config.requested_attributes)
                    self.set_destination_attributes(dest_paths[url].url, item.attributes)
                # ...and remove it from the list.
                del dest_paths[url]
            else:
                # If an item is in the source but not the destination tree...
                if item.isdir and self.config.recursive:
                    # ...create it if it's a directory.
                    create_dirs.append(item)

        if self.config.delete:
            for item in dest_paths.values():
                if item.isdir:
                    if self.config.recursive:
                        log.info("Deleting destination directory %s..." % item)
                        self.recursively_delete(item)
                else:
                    log.info("Deleting destination file %s..." % item)
                    self.destination_transport.remove(item.url)

        if self.config.dry_run:
            return

        # Create directories after we've deleted everything else because sometimes a directory in
        # the source might have the same name as a file, so we need to delete files first.
        for item in create_dirs:
            dest_url = url_splice(self.source, item.url, self.destination)
            self.destination_transport.mkdir(dest_url)
            item.populate_attributes(self.max_evaluation_attributes |
                                       self.config.requested_attributes)
            self.set_destination_attributes(dest_url, item.attributes)

    def include_file(self, item):
        """Check whether to include a file or not given our exclusion patterns."""
        # We have separate exclusion patterns for files and directories.
        if item.isdir:
            if self.config.exclude_dirs.search(item.url) and \
                not self.config.include_dirs.search(item.url):
                # If we are told to exclude the directory and not told to include it,
                # act as if it doesn't exist.
                return False
            else:
                # Otherwise, append the file to the directory list.
                return True
        else:
            if self.config.exclude_files.search(item.url) and \
                not self.config.include_files.search(item.url):
                # If we are told to exclude the file and not told to include it,
                # act as if it doesn't exist.
                return False
            else:
                # Otherwise, append the file to the directory list.
                return True

    def recurse(self):
        """Recursively synchronise everything."""
        source_dir_list = self.source_transport.listdir(self.source)
        dest = FileObject(self.destination_transport, self.destination)
        # If the source is a file, rather than a directory, just copy it. We know for sure that
        # it exists from the checks we did before, so the "False" return value can't be because
        # of that.
        if not source_dir_list:
            # If the destination ends in a slash or is an actual directory:
            if self.destination.endswith("/") or dest.isdir:
                if not dest.isdir:
                    self.destination_transport.mkdir(dest.url)
                # Splice the source filename onto the destination URL.
                dest_url = url_split(dest.url)
                dest_url.file = url_split(self.source,
                                          uses_hostname=self.source_transport.uses_hostname,
                                          split_filename=True).file
                dest_url = url_join(dest_url)
            else:
                dest_url = self.destination
            self.compare_and_copy(
                FileObject(self.source_transport, self.source, {"isdir": False}),
                FileObject(self.destination_transport, dest_url, {"isdir": False}),
                )
            return

        # If source is a directory...
        directory_stack = [FileObject(self.source_transport, self.source, {"isdir": True})]

        # Depth-first tree traversal.
        while directory_stack:
            # TODO: Rethink the assumption that a file cannot have the same name as a directory.
            item = directory_stack.pop()
            log.debug("URL %s is %sa directory." % \
                          (item.url, not item.isdir and "not " or ""))
            if item.isdir:
                # Don't skip the first directory.
                if not self.config.recursive and item.url != self.source:
                    log.info("Skipping directory %s..." % item)
                    continue
                # Obtain a directory list.
                new_dir_list = []
                for new_file in reversed(self.source_transport.listdir(item.url)):
                    if self.include_file(new_file):
                        new_dir_list.append(new_file)
                    else:
                        log.debug("Skipping %s..." % (new_file))
                dest = url_splice(self.source, item.url, self.destination)
                dest = FileObject(self.destination_transport, dest)
                log.debug("Comparing directories %s and %s..." % (item.url, dest.url))
                self.compare_directories(item, new_dir_list, dest.url)
                directory_stack.extend(new_dir_list)
            else:
                dest_url = url_splice(self.source, item.url, self.destination)
                log.debug("Destination URL is %s." % dest_url)
                dest = FileObject(self.destination_transport, dest_url)
                self.compare_and_copy(item, dest)

    def compare_and_copy(self, source, destination):
        """Compare the attributes of two files and copy if changed.

           source      - A FileObject instance pointing to the source file.
           destination - A FileObject instance pointing to the source file.

           Returns True if the file was copied, False otherwise.
        """
        # Try to gather as many attributes of both files as possible.
        our_src_attributes = (source.attribute_set & self.max_evaluation_attributes)
        max_src_attributes = (self.source_transport.getattr_attributes &
                              self.max_evaluation_attributes) | \
                              self.config.requested_attributes
        src_difference = max_src_attributes - our_src_attributes
        if src_difference:
            # If the set of useful attributes we have is smaller than the set of attributes the
            # user requested and the ones we can gather through getattr(), get the rest.
            log.debug("Source getattr for file %s and arguments %s deemed necessary." % \
                          (source, src_difference))
            source.populate_attributes(src_difference)
            # We should now have all the attributes we're interested in, both for evaluating if
            # the files are different and setting.

        # We aren't interested in the user's requested arguments for the destination.
        dest_difference = (self.destination_transport.getattr_attributes -
                           destination.attribute_set) & self.max_evaluation_attributes
        if dest_difference:
            # Same for the destination.
            log.debug("Destination getattr for %s deemed necessary." % destination)
            destination.populate_attributes(dest_difference)

        # Compare the evaluation keys that are common in both dictionaries. If one is different,
        # copy the file.
        evaluation_attributes = source.attribute_set & destination.attribute_set & \
                                self.max_evaluation_attributes
        log.debug("Checking evaluation attributes %s..." % evaluation_attributes)
        for key in evaluation_attributes:
            if getattr(source, key) != getattr(destination, key):
                log.debug("Source and destination %s was different (%s vs %s)." %\
                              (key, getattr(source, key), getattr(destination, key)))
                if self.config.update and destination.mtime > source.mtime:
                    log.info("Destination file is newer and --update specified, skipping...")
                    break
                log.info("Copying \"%s\"\n        to \"%s\"..." % (source, destination))
                try:
                    self.copy_file(source, destination)
                except IOError:
                    return
                else:
                    # If the file was successfully copied, set its attributes.
                    self.set_destination_attributes(destination.url, source.attributes)
                    break
        else:
            # The two files are identical, skip them...
            log.info("Files \"%s\"\n      and \"%s\" are identical, skipping..." %
                         (source, destination))
            # ...but set the attributes anyway.
            self.set_destination_attributes(destination.url, source.attributes)
        self.file_counter += 1

    def recursively_delete(self, directory):
        """Recursively delete a directory from the destination transport.

           directory - A FileObject instance of the directory to delete.
        """
        directory_stack = [directory]
        directory_names = []

        # Delete all files in the given directories and gather their names in a stack.
        while directory_stack:
            item = directory_stack.pop()
            if item.isdir:
                # If the item is a directory, append its contents to the stack (reversing them for
                # proper ordering)...
                directory_stack.extend(reversed(self.destination_transport.listdir(item.url)))
                directory_names.append(item)
            else:
                # ...otherwise, remove it.
                self.destination_transport.remove(item.url)

        while directory_names:
            item = directory_names.pop()
            self.destination_transport.rmdir(item.url)

    def copy_file(self, source, destination):
        """Copy a file.

           source      - A FileObject instance pointing to the source file.
           destination - A FileObject instance pointing to the source file.
        """
        if self.config.dry_run:
            return

        # Select the smallest buffer size of the two, to avoid congestion.
        buffer_size = min(self.source_transport.buffer_size,
                          self.destination_transport.buffer_size)
        try:
            self.source_transport.open(source.url, "rb")
        except IOError:
            log.error("Could not open %s, skipping..." % source)
            raise
        # Remove the file before copying.
        self.destination_transport.remove(destination.url)
        try:
            self.destination_transport.open(destination.url, "wb")
        except IOError:
            log.error("Could not open %s, skipping..." % destination)
            self.destination_transport.close()
            self.source_transport.close()
            raise
            
        if hasattr(source, "size"):
            prog = Progress(source.size)
        else:
            prog = None
            
        bytes_done = 0
        data = self.source_transport.read(buffer_size)
        while data:
            if not bytes_done % 5:
                self.report_file_progress(prog, bytes_done)
            bytes_done += len(data)
            self.destination_transport.write(data)
            data = self.source_transport.read(buffer_size)
        self.bytes_total += bytes_done
        self.destination_transport.close()
        self.source_transport.close()
    
    def report_file_progress(self, prog, bytes_done):
        """Displays the progress of a file copy. Displays
        the output via print.
        
            prog - Progress instance to compute the progress
            bytes_done - how much of the file has been transferred already.
        """
        # The source file might not have a size attribute.
        if prog:
            done = prog.progress(bytes_done)
            print "Copied %(item)s/%(items)s bytes (%(percentage)s%%) " \
            "%(elapsed_time)s/%(total_time)s.\r" % done,
        else:
            print "Copied %s bytes.\r" % (bytes_done),


def parse_arguments(omnisync):
    """Parse the command-line arguments."""
    parser = optparse.OptionParser(
        usage="%prog [options] <source> <destination>",
        version="%%prog %s" % VERSION
        )
    parser.set_defaults(verbosity=1)
    parser.add_option("-q", "--quiet",
                      action="store_const",
                      dest="verbosity",
                      const=0,
                      help="be vewy vewy quiet"
                      )
    parser.add_option("-d", "--debug",
                      action="store_const",
                      dest="verbosity",
                      const=2,
                      help="talk too much"
                      )
    parser.add_option("-r", "--recursive",
                      action="store_true",
                      dest="recursive",
                      help="recurse into directories",
                      )
    parser.add_option("-u", "--update",
                      action="store_true",
                      dest="update",
                      help="update only (don't overwrite newer files on destination)",
                      )
    parser.add_option("--delete",
                      action="store_true",
                      dest="delete",
                      help="delete extraneous files from destination"
                      )
    parser.add_option("-n", "--dry-run",
                      action="store_true",
                      dest="dry_run",
                      help="show what would have been transferred"
                      )
    parser.add_option("-p", "--perms",
                      action="append_const",
                      const="perms",
                      dest="attributes",
                      help="preserve permissions"
                      )
    parser.add_option("-o", "--owner",
                      action="append_const",
                      const="owner",
                      dest="attributes",
                      help="preserve owner"
                      )
    parser.add_option("-g", "--group",
                      action="append_const",
                      const="group",
                      dest="attributes",
                      help="preserve group"
                      )
    parser.add_option("--exclude-files",
                      dest="exclude_files",
                      help="exclude files matching the PATTERN regex",
                      metavar="PATTERN"
                      )
    parser.add_option("--include-files",
                      dest="include_files",
                      help="don't exclude files matching the PATTERN regex",
                      metavar="PATTERN"
                      )
    parser.add_option("--exclude-dirs",
                      dest="exclude_dirs",
                      help="exclude directories matching the PATTERN regex",
                      metavar="PATTERN"
                      )
    parser.add_option("--include-dirs",
                      dest="include_dirs",
                      help="don't exclude directories matching the PATTERN regex",
                      metavar="PATTERN"
                      )
    # Allow the plugins to set their own options.
    omnisync.add_options(parser)
    (options, args) = parser.parse_args()
    if len(args) != 2:
        parser.print_help()
        sys.exit()
    return options, args

def main():
    # Initialise the logger.
    logging.basicConfig(level=logging.INFO, format='%(message)s',
        stream=sys.stdout)

    omnisync = OmniSync()
    (options, args) = parse_arguments(omnisync)
    omnisync.config = Configuration(options)
    omnisync.sync(args[0], args[1])

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = progress
"""A progress indicator and remaining time calculator class."""
import time

def timetostr(duration):
    """Convert seconds to D:H:M:S format (whichever applicable)."""
    duration = int(duration)
    timelist = [duration / 86400, (duration / 3600) % 24]
    timestring = ""
    printall = False
    for item in timelist:
        printall |= item
        if printall:
            timestring += str(item).zfill(2) + ":"
    timestring += str((duration / 60) % 60).zfill(2) + ":" + str(duration % 60).zfill(2)
    return timestring


class Progress:
    """Track the progress of an operation and calculate the projected time to
    its completion."""
    def __init__(self, totalitems, timeasstring = True):
        """Create a Progress instance. totalitems must be the total number of
        items we intend to process, so the class knows how far we've gone."""
        self._totalitems = totalitems
        self._starttime = time.time()
        self._timeasstring = timeasstring

    def progress(self, itemnumber):
        """We have progressed itemnumber items, so return our completion
        percentage, items/total items, total time and projected total
        time."""
        elapsed = time.time() - self._starttime
        # Multiply by 1.0 to force conversion to long.
        percentcomplete = (1.0 * itemnumber) / self._totalitems
        try:
            total = int(elapsed / percentcomplete)
        except ZeroDivisionError:
            total = 0
        if self._timeasstring:
            return ({"elapsed_time": timetostr(elapsed),
                    "total_time": timetostr(total),
                    "percentage": int(percentcomplete * 100),
                    "item": itemnumber,
                    "items": self._totalitems})
        else:
            return ({"elapsed_time": int(elapsed),
                    "total_time": int(total),
                    "percentage": int(percentcomplete * 100),
                    "item": itemnumber,
                    "items": self._totalitems})

    def progressstring(self, itemnumber):
        """Return a string detailing the current progress."""
        timings = self.progress(itemnumber)
        if itemnumber == self._totalitems:
            return "Done in %s, processed %s items.        \n" % (timings[0], timings[4])
        else:
            return "Progress: %s/%s, %s%%, %s/%s items.\r" % timings

########NEW FILE########
__FILENAME__ = transportmount
"""Transport mounting module."""

class TransportMount(type):
    """The mount point class for transport modules."""
    def __init__(cls, name, bases, attrs):
        """Mount other transports modules."""
        if not hasattr(cls, "transports"):
            # If we are the main mount point, create a transport list.
            cls.transports = []
        else:
            # If we are a plugin implementation, append to the list.
            cls.transports.append(cls)

class TransportInterface:
    """Parent class for transport classes."""
    __metaclass__ = TransportMount

########NEW FILE########
__FILENAME__ = file
"""Plain file access module."""

from omnisync.transportmount import TransportInterface
from omnisync.fileobject import FileObject
from omnisync import urlfunctions

import platform
import os
import time
import errno

if platform.system() == "Windows":
    OSERROR = WindowsError
else:
    OSERROR = OSError


class FileTransport(TransportInterface):
    """Plain file access class."""
    # Transports should declare the protocols attribute to specify the protocol(s)
    # they can handle.
    protocols = ("file", )
    # Inform whether this transport's URLs use a hostname. The difference between http://something
    # and file://something is that in the former "something" is a hostname, but in the latter it's
    # a path.
    uses_hostname = False
    # listdir_attributes is a set that contains the file attributes that listdir()
    # supports.
    listdir_attributes = set()
    # Conversely, for getattr().
    getattr_attributes = set(("size", "mtime", "atime", "perms", "owner", "group"))
    # List the attributes setattr() can set.
    if platform.system() == "Windows":
        setattr_attributes = set(("mtime", "atime", "perms"))
    else:
        setattr_attributes = set(("mtime", "atime", "perms", "owner", "group"))
    # Define attributes that can be used to decide whether a file has been changed
    # or not.
    evaluation_attributes = set(("size", "mtime"))
    # The preferred buffer size for reads/writes.
    buffer_size = 2**15

    def __init__(self):
        self._file_handle = None

    def _get_filename(self, url):
        """Retrieve the local filename from a given URL."""
        split_url = urlfunctions.url_split(url, uses_hostname=self.uses_hostname)
        return split_url.path

    # Transports should also implement the following methods:
    def add_options(self):
        """Return the desired command-line plugin options.

           Returns a tuple of ((args), {kwargs}) items for optparse's add_option().
        """
        return ()

    def connect(self, url, config):
        """This method does nothing, since we don't need to connect to the
           filesystem."""

    def disconnect(self):
        """This method does nothing, since we don't need to disconnect from the
           filesystem."""

    def open(self, url, mode="rb"):
        """Open a file in _mode_ to prepare for I/O.

           Raises IOError if anything goes wrong.
        """
        if self._file_handle:
            raise IOError, "Another file is already open."
        self._file_handle = open(self._get_filename(url), mode)

    def read(self, size):
        """Read _size_ bytes from the open file."""
        return self._file_handle.read(size)

    def write(self, data):
        """Write _data_ to the open file."""
        self._file_handle.write(data)

    def remove(self, url):
        """Remove the specified file."""
        try:
            os.remove(self._get_filename(url))
        except OSERROR:
            return False
        else:
            return True

    def rmdir(self, url):
        """Remove the specified directory non-recursively."""
        try:
            os.rmdir(self._get_filename(url))
        except OSERROR:
            return False
        else:
            return True

    def close(self):
        """Close the open file."""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None

    def mkdir(self, url):
        """Recursively make the given directories at the current URL."""
        # Recursion is not needed for anything but the first directory, so we need to be able to
        # do it.
        current_path = ""
        error = False
        for component in self._get_filename(url).split("/"):
            current_path += component + "/"
            try:
                os.mkdir(current_path)
            except OSERROR, failure:
                if failure.errno != errno.EEXIST:
                    error = True
            else:
                error = False

        return error

    def listdir(self, url):
        """Retrieve a directory listing of the given location.

        Returns a list of (url, attribute_dict) tuples if the given URL is a directory,
        False otherwise. URLs should be absolute, including protocol, etc.
        attribute_dict is a dictionary of {key: value} pairs for any applicable
        attributes from ("size", "mtime", "atime", "ctime", "isdir").
        """
        if not url.endswith("/"):
            url = url + "/"
        try:
            return [FileObject(self, url + x) for x in os.listdir(self._get_filename(url))]
        except OSERROR:
            return False

    def isdir(self, url):
        """Return True if the given URL is a directory, False if it is a file or
           does not exist."""
        return os.path.isdir(self._get_filename(url))

    def getattr(self, url, attributes):
        """Retrieve as many file attributes as we can, at the very *least* the requested ones.

        Returns a dictionary of {"attribute": "value"}, or {"attribute": None} if the file does
        not exist.
        """
        if set(attributes) - self.getattr_attributes:
            raise NotImplementedError, "Some requested attributes are not implemented."
        try:
            statinfo = os.stat(self._get_filename(url))
        except OSERROR:
            return dict([(x, None) for x in self.getattr_attributes])
        # Turn times to ints because checks fail sometimes due to rounding errors.
        return {"size": statinfo.st_size,
                "mtime": int(statinfo.st_mtime),
                "atime": int(statinfo.st_atime),
                "perms": statinfo.st_mode,
                "owner": statinfo.st_uid,
                "group": statinfo.st_gid,
                }

    def setattr(self, url, attributes):
        """Set a file's attributes if possible."""
        filename = self._get_filename(url)
        if "atime" in attributes or "mtime" in attributes:
            atime = attributes.get("atime", time.time())
            mtime = attributes.get("mtime", time.time())
            try:
                os.utime(filename, (atime, mtime))
            except OSERROR:
                print "FILE: Permission denied, could not set atime/mtime on %s." % url
        if "perms" in attributes:
            try:
                os.chmod(filename, attributes["perms"])
            except OSERROR:
                print "FILE: Permission denied, could not set perms on %s." % url
        if platform.system() != "Windows" and ("owner" in attributes or "group" in attributes):
            try:
                os.chown(filename, attributes.get("owner", -1), attributes.get("group", -1))
            except OSERROR:
                print "FILE: Permission denied, could not set uid/gid on %s." % url

    def exists(self, url):
        """Return True if a given path exists, False otherwise."""
        return os.path.exists(self._get_filename(url))

########NEW FILE########
__FILENAME__ = s3
"""S3 transport module."""

from omnisync.transportmount import TransportInterface
from omnisync.fileobject import FileObject
from omnisync import urlfunctions

import getpass


class S3Transport(TransportInterface):
    """S3 transport class."""
    # Transports should declare the protocols attribute to specify the protocol(s)
    # they can handle.
    protocols = ("s3", )
    # Inform whether this transport's URLs use a hostname. The difference between http://something
    # and file://something is that in the former "something" is a hostname, but in the latter it's
    # a path.
    uses_hostname = True
    # listdir_attributes is a set that contains the file attributes that listdir()
    # supports.
    listdir_attributes = set(("size", ))
    # Conversely, for getattr().
    getattr_attributes = set()
    # List the attributes setattr() can set.
    setattr_attributes = set()
    # Define attributes that can be used to decide whether a file has been changed
    # or not.
    evaluation_attributes = set(("size", ))
    # The preferred buffer size for reads/writes.
    buffer_size = 2**15

    def __init__(self):
        self._bucket = None
        self._connection = None

    def _get_filename(self, url):
        """Retrieve the local filename from a given URL."""
        url = urlfunctions.append_slash(url, False)
        split_url = urlfunctions.url_split(url, uses_hostname=self.uses_hostname)
        return urlfunctions.prepend_slash(split_url.path, False)

    # Transports should also implement the following methods:
    def add_options(self):
        """Return the desired command-line plugin options.

           Returns a tuple of ((args), {kwargs}) items for optparse's add_option().
        """
        return ()

    def connect(self, url, config):
        """Initiate a connection to the remote host."""
        url = urlfunctions.url_split(url)
        if not url.username:
            print "S3: Please enter your AWS access key:",
            url.username = raw_input()
        if not url.password:
            url.password = getpass.getpass("S3: Please enter your AWS secret key:")
        global S3Connection, Key
        try:
            # We import boto here so the program doesn't crash if the library is not installed.
            from boto.s3.connection import S3Connection
            from boto.s3.key import Key
            import boto
        except ImportError:
            print "S3: You will need to install the boto library to have s3 support."
            raise
        self._connection = S3Connection(url.username, url.password)
        try:
            self._bucket = self._connection.get_bucket(url.hostname)
        except boto.exception.S3ResponseError, failure:
            if failure.status == 404:
                self._bucket = self._connection.create_bucket(url.hostname)
            else:
                print "S3: Unspecified failure while connecting to the S3 bucket, aborting."

    def disconnect(self):
        """Do nothing, S3 doesn't require anything."""

    def open(self, url, mode="r"):
        """Open a file in _mode_ to prepare for I/O.

           Raises IOError if anything goes wrong.
        """
        self._file_handle = Key(self._bucket, self._get_filename(url))
        self._file_handle.open(mode.replace("b", ""))

    def read(self, size):
        """Read _size_ bytes from the open file."""
        return self._file_handle.read(size)

    #def write(self, data):
    #    """No writes yet for s3 :(."""
    #    self._file_handle.write(data)

    def remove(self, url):
        """Remove the specified file."""
        self._bucket.remove(self._get_filename(url))

    def rmdir(self, url):
        """Remove the specified directory non-recursively."""
        return True

    def close(self):
        """Close the open file."""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None

    def mkdir(self, url):
        """Where we're going, we don't *need* directories."""

    def listdir(self, url):
        """Retrieve a directory listing of the given location.

        Returns a list of (url, attribute_dict) tuples if the given URL is a directory,
        False otherwise. URLs should be absolute, including protocol, etc.
        attribute_dict is a dictionary of {key: value} pairs for any applicable
        attributes from ("size", "mtime", "atime", "ctime", "isdir").
        """
        url = urlfunctions.append_slash(url, True)
        url = urlfunctions.url_split(url)
        path = urlfunctions.prepend_slash(url.path, False)
        dir_list = self._bucket.list(prefix=path, delimiter="/")
        file_list = []
        for item in dir_list:
            # Prepend a slash by convention.
            url.path = "/" + item.name
            # list() returns directories ending with a slash.
            file_obj = FileObject(self, urlfunctions.url_join(url),
                                        {"isdir": item.name.endswith("/")})
            if not file_obj.isdir:
                file_obj.size = item.size
            else:
                file_obj.size = 0
            file_list.append(file_obj)
        return file_list

    def isdir(self, url):
        """Return True if the given URL is a directory, False if it is a file or
           does not exist."""
        return self.listdir(url) != []

    def getattr(self, url, attributes):
        """Do nothing."""
        # TODO: Retrieve ACL.

    def setattr(self, url, attributes):
        """Do nothing."""
        # TODO: Set ACL.

    def exists(self, url):
        """Return True if a given path exists, False otherwise."""
        filename = self._get_filename(url)
        # If we're looking for the root, return True.
        if filename == "":
            return True
        return Key(self._bucket, filename).exists()

########NEW FILE########
__FILENAME__ = sftp
"""SFTP transport module."""

from omnisync.transportmount import TransportInterface
from omnisync.fileobject import FileObject
from omnisync import urlfunctions

import getpass
import time
import errno


class SFTPTransport(TransportInterface):
    """SFTP transport class."""
    # Transports should declare the protocols attribute to specify the protocol(s)
    # they can handle.
    protocols = ("sftp", )
    # Inform whether this transport's URLs use a hostname. The difference between http://something
    # and file://something is that in the former "something" is a hostname, but in the latter it's
    # a path.
    uses_hostname = True
    # listdir_attributes is a set that contains the file attributes that listdir()
    # supports.
    listdir_attributes = set(("size", "mtime", "atime", "perms", "owner", "group"))
    # Conversely, for getattr().
    getattr_attributes = set(("size", "mtime", "atime", "perms", "owner", "group"))
    # List the attributes setattr() can set.
    setattr_attributes = set(("mtime", "atime", "perms", "owner", "group"))
    # Define attributes that can be used to decide whether a file has been changed
    # or not.
    evaluation_attributes = set(("size", "mtime"))
    # The preferred buffer size for reads/writes.
    buffer_size = 2**15

    def __init__(self):
        self._file_handle = None
        self._connection = None
        self._transport = None

    def _get_filename(self, url):
        """Retrieve the local filename from a given URL."""
        split_url = urlfunctions.url_split(url, uses_hostname=self.uses_hostname)
        # paths are relative unless they start with two //
        path = split_url.path
        if len(path) > 1 and path.startswith("/"):
            path = path[1:]
        return path

    # Transports should also implement the following methods:
    def add_options(self):
        """Return the desired command-line plugin options.

           Returns a tuple of ((args), {kwargs}) items for optparse's add_option().
        """
        return ()

    def connect(self, url, config):
        """Initiate a connection to the remote host."""
        options = config.full_options
        
        # Make the import global.
        global paramiko
        try:
            # We import paramiko only when we need it because its import is really slow.
            import paramiko
        except ImportError:
            print "SFTP: You will need to install the paramiko library to have sftp support."
            raise
        url = urlfunctions.url_split(url)
        if not url.port:
            url.port = 22
        self._transport = paramiko.Transport((url.hostname, url.port))
        
        username = url.username
        if not url.username:
            if hasattr(options, "username"):
                username = options.username
            else:
                url.username = getpass.getuser()
        
        password = url.password
        if not url.password:
            if hasattr(options, "password"):
                password = options.password
            else:
                password = getpass.getpass(
                    "SFTP: Please enter the password for %s@%s:" % (url.username, url.hostname)
                )
        self._transport.connect(username=username, password=password)
        self._connection = paramiko.SFTPClient.from_transport(self._transport)

    def disconnect(self):
        """Disconnect from the remote server."""
        self._transport.close()

    def open(self, url, mode="rb"):
        """Open a file in _mode_ to prepare for I/O.

           Raises IOError if anything goes wrong.
        """
        if self._file_handle:
            raise IOError, "Another file is already open."
        self._file_handle = self._connection.open(self._get_filename(url), mode)

    def read(self, size):
        """Read _size_ bytes from the open file."""
        return self._file_handle.read(size)

    def write(self, data):
        """Write _data_ to the open file."""
        self._file_handle.write(data)

    def remove(self, url):
        """Remove the specified file."""
        try:
            self._connection.remove(self._get_filename(url))
        except IOError:
            return False
        else:
            return True

    def rmdir(self, url):
        """Remove the specified directory non-recursively."""
        try:
            self._connection.rmdir(self._get_filename(url))
        except IOError:
            return False
        else:
            return True

    def close(self):
        """Close the open file."""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None

    def mkdir(self, url):
        """Recursively make the given directories at the current URL."""
        # Recursion is not needed for anything but the first directory, so we need to be able to
        # do it.
        current_path = ""
        error = False
        for component in self._get_filename(url).split("/"):
            current_path += component + "/"
            try:
                self._connection.mkdir(current_path)
            except IOError, failure:
                if failure.errno != errno.EEXIST:
                    error = True
            else:
                error = False

        return error

    def listdir(self, url):
        """Retrieve a directory listing of the given location.

        Returns a list of (url, attribute_dict) tuples if the given URL is a directory,
        False otherwise. URLs should be absolute, including protocol, etc.
        attribute_dict is a dictionary of {key: value} pairs for any applicable
        attributes from ("size", "mtime", "atime", "ctime", "isdir").
        """
        url = urlfunctions.append_slash(url, True)
        try:
            dir_list = self._connection.listdir_attr(self._get_filename(url))
        except IOError:
            return False
        file_list = []
        for item in dir_list:
            file_list.append(FileObject(self, url + item.filename,
                {"size": item.st_size,
                 "mtime": item.st_mtime,
                 "atime": item.st_atime,
                 "perms": item.st_mode,
                 "owner": item.st_uid,
                 "group": item.st_gid,
                }))
        return file_list

    def isdir(self, url):
        """Return True if the given URL is a directory, False if it is a file or
           does not exist."""
        try:
            # paramiko doesn't allow you to check any other way.
            self._connection.listdir(self._get_filename(url))
        except IOError, failure:
            if failure.errno == errno.ENOENT:
                return False
            else:
                raise
        else:
            return True

    def getattr(self, url, attributes):
        """Retrieve as many file attributes as we can, at the very *least* the requested ones.

        Returns a dictionary of {"attribute": "value"}, or {"attribute": None} if the file does
        not exist.
        """
        if set(attributes) - self.getattr_attributes:
            raise NotImplementedError, "Some requested attributes are not implemented."
        try:
            statinfo = self._connection.stat(self._get_filename(url))
        except IOError:
            return dict([(x, None) for x in self.getattr_attributes])
        # Turn times to ints because checks fail sometimes due to rounding errors.
        return {"size": statinfo.st_size,
                "mtime": int(statinfo.st_mtime),
                "atime": int(statinfo.st_atime),
                "perms": statinfo.st_mode,
                "owner": statinfo.st_uid,
                "group": statinfo.st_gid,
                }

    def setattr(self, url, attributes):
        """Set a file's attributes if possible."""
        filename = self._get_filename(url)
        if "atime" in attributes or "mtime" in attributes:
            atime = attributes.get("atime", time.time())
            mtime = attributes.get("mtime", time.time())
            try:
                self._connection.utime(filename, (atime, mtime))
            except IOError:
                print "SFTP: Permission denied, could not set atime/mtime."
        if "perms" in attributes:
            try:
                self._connection.chmod(filename, attributes["perms"])
            except IOError:
                print "SFTP: Permission denied, could not set perms."
        if "owner" in attributes or "group" in attributes:
            # If we're missing one, get it.
            if not "owner" in attributes or not "group" in attributes:
                stat = self._connection.stat(filename)
                owner = attributes.get("owner", stat.st_uid)
                group = attributes.get("group", stat.st_gid)
            else:
                owner = attributes["owner"]
                group = attributes["group"]
            try:
                self._connection.chown(filename, owner, group)
            except IOError:
                print "SFTP: Permission denied, could not set uid/gid."

    def exists(self, url):
        """Return True if a given path exists, False otherwise."""
        try:
            self._connection.stat(self._get_filename(url))
        except IOError:
            return False
        else:
            return True

########NEW FILE########
__FILENAME__ = virtual
"""Virtual filesystem access module."""

from omnisync.transportmount import TransportInterface
from omnisync.fileobject import FileObject
from omnisync import urlfunctions

import pickle


class VirtualTransport(TransportInterface):
    """Virtual filesystem access class."""
    # Transports should declare the protocols attribute to specify the protocol(s)
    # they can handle.
    protocols = ("virtual", )
    # Inform whether this transport's URLs use a hostname. The difference between http://something
    # and file://something is that in the former "something" is a hostname, but in the latter it's
    # a path.
    uses_hostname = True
    # listdir_attributes is a set that contains the file attributes that listdir()
    # supports.
    listdir_attributes = set()
    # Conversely, for getattr().
    getattr_attributes = set(("size", ))
    # List the attributes setattr() can set.
    setattr_attributes = set()
    # Define attributes that can be used to decide whether a file has been changed
    # or not.
    evaluation_attributes = set(("size", ))
    # The preferred buffer size for reads/writes.
    buffer_size = 2**15

    def __init__(self):
        self._file_handle = None
        self._filesystem = {"/": None}
        self._storage = None
        self._bytes_read = None

    def _get_filename(self, url, remove_slash=True):
        """Retrieve the local filename from a given URL."""
        # Remove the trailing slash as a convention unless specified otherwise.
        if remove_slash:
            urlfunctions.append_slash(url, False)
        filename = urlfunctions.url_split(url).path
        if filename == "":
            filename = "/"
        return filename

    # Transports should also implement the following methods:
    def add_options(self):
        """Return the desired command-line plugin options.

           Returns a tuple of ((args), {kwargs}) items for optparse's add_option().
        """
        return ()

    def connect(self, url, config):
        """Unpickle the filesystem dictionary."""
        self._storage = urlfunctions.url_split(url).hostname
        # If the storage is in-memory only, don't do anything.
        if self._storage == "memory":
            return
        try:
            pickled_file = open(self._storage, "rb")
        except IOError:
            return
        self._filesystem = pickle.load(pickled_file)
        pickled_file.close()

    def disconnect(self):
        """Pickle the filesystem to a file for persistence."""
        # If the storage is in-memory only, don't do anything.
        if self._storage == "memory":
            return
        pickled_file = open(self._storage, "wb")
        pickle.dump(self._filesystem, pickled_file)
        pickled_file.close()

    def open(self, url, mode="rb"):
        """Open a file in _mode_ to prepare for I/O.

           Raises IOError if anything goes wrong.
        """
        filename = self._get_filename(url)
        if self._filesystem.get(filename, False) is None:
            raise IOError, "File is a directory."
        self._file_handle = filename
        if mode.startswith("r"):
            if filename not in self._filesystem:
                raise IOError, "File does not exist."
            self._bytes_read = 0
        else:
            self._filesystem[self._file_handle] = {"size": 0}

    def read(self, size):
        """Read _size_ bytes from the open file."""
        if self._file_handle is None:
            return IOError, "No file is open."
        if self._bytes_read + size < self._filesystem[self._file_handle]["size"]:
            self._bytes_read += size
            return " " * size
        else:
            bytes_read = self._bytes_read
            self._bytes_read = self._filesystem[self._file_handle]["size"]
            return " " * (self._filesystem[self._file_handle]["size"] - bytes_read)

    def write(self, data):
        """Write _data_ to the open file."""
        if self._file_handle is None:
            return IOError, "No file is open."
        self._filesystem[self._file_handle]["size"] += len(data)

    def close(self):
        """Close the open file."""
        self._file_handle = None

    def remove(self, url):
        """Remove the specified file."""
        filename = self._get_filename(url)
        if filename not in self._filesystem or self._filesystem[filename] is None:
            return False
        del self._filesystem[filename]
        return True

    def rmdir(self, url):
        """Remove the specified directory non-recursively."""
        filename = self._get_filename(url)
        if self._filesystem[filename] is not None:
            return False
        if self.listdir(url):
            return False
        else:
            del self._filesystem[filename]
            return True

    def mkdir(self, url):
        """Create a directory."""
        filename = self._get_filename(url)
        if filename not in self._filesystem:
            return IOError, "A directory with the specified name already exists."
        self._filesystem[filename] = None

    def listdir(self, url):
        """Retrieve a directory listing of the given location.

        Returns a list of (url, attribute_dict) tuples if the
        given URL is a directory, False otherwise.
        """
        # Add a slash so we don't have to remove it from the start of the subpaths.
        url = urlfunctions.append_slash(url)
        filename = self._get_filename(url, False)
        files = set()
        for key in self._filesystem:
            # Check the length to prevent returning the directory itself.
            if key.startswith(filename) and len(key) > len(filename):
                subpath = key[len(filename):]
                if "/" not in subpath:
                    # Add the subpath in the set as is, because there are no lower levels.
                    files.add(subpath)
                else:
                    files.add(subpath[:subpath.find("/")])
        return [FileObject(self, url + x,) for x in files]

    def isdir(self, url):
        """Return True if the given URL is a directory, False if it is a file or
           does not exist."""
        filename = self._get_filename(url)
        if filename not in self._filesystem:
            return False
        return self._filesystem[filename] is None

    def getattr(self, url, attributes):
        """Retrieve as many file attributes as we can, at the very *least* the requested ones.

        Returns a dictionary of {"attribute": "value"}, or {"attribute": None} if the file does
        not exist.
        """
        try:
            attrs = self._filesystem[self._get_filename(url)]
        except KeyError:
            return {"size": None}
        if attrs is None:
            # Directories have no attributes in our virtual FS.
            return {"size": None}
        else:
            return attrs

    def setattr(self, url, attributes):
        """Do nothing."""

    def exists(self, url):
        """Return True if a given path exists, False otherwise."""
        return self._get_filename(url) in self._filesystem

########NEW FILE########
__FILENAME__ = unit_tests
#!/usr/bin/env python
"""omnisync unit tests."""

import unittest
from omnisync import urlfunctions

class Tests(unittest.TestCase):
    """Various omnisync unit tests."""

    def test_append_slash(self):
        """Test append_slash."""
        tests = (
            (("file:///home/user/", True), "file:///home/user/"),
            (("file:///home/user/", False), "file:///home/user"),
            (("file:///home/user/", True), "file:///home/user/"),
            (("file:///home/user", False), "file:///home/user"),
        )
        for test, expected_output in tests:
            self.assertEqual(urlfunctions.append_slash(*test), expected_output)

    def test_prepend_slash(self):
        """Test append_slash."""
        tests = (
            (("/home/user/", True), "/home/user/"),
            (("/home/user/", False), "home/user/"),
            (("home/user/", True), "/home/user/"),
            (("home/user/", False), "home/user/"),
        )
        for test, expected_output in tests:
            self.assertEqual(urlfunctions.prepend_slash(*test), expected_output)

    def test_url_join(self):
        """Test url_join."""
        tests = (
            ("http://user:pass@myhost:80/some/path/file;things?myhost=hi#lala", True, True),
            ("http://user:pass@myhost:80/some/path/;things?myhost=hi#lala", True, True),
            ("http://user@myhost/file;things?myhost=hi#lala", True, True),
            ("http://myhost/;things?myhost=hi#lala", True, True),
            ("http://user:pass@myhost:80/?myhost=hi#lala", True, True),
            ("myhost/", True, True),
            ("user:pass@myhost:80/", True, True),
            ("user:pass@myhost/some#lala", True, True),
            ("http://myhost:80/;things?myhost=hi#lala", True, True),
            ("http://myhost/#lala", True, True),
            ("file://path", False, True),
            ("file://path/file", False, True),
            ("file:///path", False, True),
            ("file:///path/file", False, True),
            ("file:///path/file?something=else", False, True),
        )
        for test in tests:
            self.assertEqual(urlfunctions.url_join(urlfunctions.url_split(*test)), test[0])

    def test_url_split(self):
        """Test url_split."""
        tests = (
            (("http://user:pass@myhost:80/some/path/file;things?myhost=hi#lala", True, False),
             {"scheme": "http",
              "netloc": "user:pass@myhost:80",
              "username": "user",
              "password": "pass",
              "hostname": "myhost",
              "port": 80,
              "path": "/some/path/file",
              "file": "",
              "params": "things",
              "query": "myhost=hi",
              "anchor": "lala"}),
            (("http://myhost/some/path/file;things?myhost=hi#lala", True, False),
             {"scheme": "http",
              "netloc": "myhost",
              "username": "",
              "password": "",
              "hostname": "myhost",
              "port": 0,
              "path": "/some/path/file",
              "file": "",
              "params": "things",
              "query": "myhost=hi",
              "anchor": "lala"}),
            (("http://user@myhost/some/path/", True, False),
             {"scheme": "http",
              "netloc": "user@myhost",
              "username": "user",
              "password": "",
              "hostname": "myhost",
              "port": 0,
              "path": "/some/path/",
              "file": "",
              "params": "",
              "query": "",
              "anchor": ""}),
            (("http://myhost", True, False),
             {"scheme": "http",
              "netloc": "myhost",
              "username": "",
              "password": "",
              "hostname": "myhost",
              "port": 0,
              "path": "",
              "file": "",
              "params": "",
              "query": "",
              "anchor": ""}),
            (("file://some/directory", False, False),
             {"scheme": "file",
              "path": "some/directory",
              "file": "",
              "params": "",
              "query": "",
              "anchor": ""}),
            (("file://some/directory", True, True),
             {"scheme": "file",
              "netloc": "some",
              "username": "",
              "password": "",
              "hostname": "some",
              "port": 0,
              "path": "/",
              "file": "directory",
              "params": "",
              "query": "",
              "anchor": ""}),
            (("host", True, True),
             {"scheme": "",
              "netloc": "host",
              "username": "",
              "password": "",
              "hostname": "host",
              "port": 0,
              "path": "",
              "file": "",
              "params": "",
              "query": "",
              "anchor": ""}),
            (("http://user:pass@myhost:80/some/path/file;things?arg=hi#lala", True, True),
             {"scheme": "http",
              "netloc": "user:pass@myhost:80",
              "username": "user",
              "password": "pass",
              "hostname": "myhost",
              "port": 80,
              "path": "/some/path/",
              "file": "file",
              "params": "things",
              "query": "arg=hi",
              "anchor": "lala"}),
            (("http://myhost:80/some/path/file;things?arg=hi#lala", True, False),
             {"scheme": "http",
              "netloc": "myhost:80",
              "username": "",
              "password": "",
              "hostname": "myhost",
              "port": 80,
              "path": "/some/path/file",
              "file": "",
              "params": "things",
              "query": "arg=hi",
              "anchor": "lala"}),
            (("http://user:pass@myhost:80/some/path/file#lala", True, False),
             {"scheme": "http",
              "netloc": "user:pass@myhost:80",
              "username": "user",
              "password": "pass",
              "hostname": "myhost",
              "port": 80,
              "path": "/some/path/file",
              "file": "",
              "params": "",
              "query": "",
              "anchor": "lala"}),
            (("file://I:/some/path/file", False, True),
             {"scheme": "file",
              "path": "I:/some/path/",
              "file": "file",
              "params": "",
              "query": "",
              "anchor": ""}),
            (("file://file", False, True),
             {"scheme": "file",
              "path": "",
              "file": "file",
              "params": "",
              "query": "",
              "anchor": ""}),
        )
        for test, expected_output in tests:
            result = urlfunctions.url_split(*test)
            for key in expected_output.keys():
                self.assertEqual(getattr(result, key), expected_output[key])

    def test_url_splice(self):
        """Test url_splice."""
        tests = (
            (("file://C:/test/file",
              "file://C:/test/file/some/other/dir",
              "file://C:/test/"),
             "file://C:/test/some/other/dir",
             ),
            (("file://C:/test/file",
              "file://C:/test/file/some/other/dir",
              "ftp://C:/test/"),
             "ftp://C:/test/some/other/dir",
             ),
            (("file://C:/test/file",
              "file://C:/test/file/some/other/dir",
              "file://C:/test/"),
             "file://C:/test/some/other/dir",
             ),
            (("file://C:/test/file/",
              "file://C:/test/file/some/other/dir/",
              "file://C:/test/"),
             "file://C:/test/some/other/dir/",
             ),
            (("file://C:/test/file/",
              "file://C:/test/file/some/other/dir",
              "file://C:/test"),
             "file://C:/test/some/other/dir",
             ),
            (("ftp://C:/test/file",
              "ftp://C:/test/file/some/other/dir",
              "file://C:/test/"),
             "file://C:/test/some/other/dir",
             ),
            (("ftp://C:/test/file",
              "ftp://C:/test/file/some/other/dir",
              "file://C:/test"),
             "file://C:/test/some/other/dir",
             ),
            (("ftp://myhost:21/test/",
              "ftp://myhost:21/test/file",
              "file://otherhost:21/test;someparams"),
             "file://otherhost:21/test/file;someparams",
             ),
            (("ftp://user:pass@myhost:21/test/",
              "ftp://user:pass@myhost:21/test/file",
              "file://otherhost:21/test;someparams"),
             "file://otherhost:21/test/file;someparams",
             ),
        )
        for test, expected_output in tests:
            self.assertEqual(urlfunctions.url_splice(*test), expected_output)

    def test_urls(self):
        """Test URL normalisation."""
        urls = (
            ("C:\\test\\file", "file://C:/test/file"),
            ("C:\\test\\directory\\", "file://C:/test/directory/"),
            ("file", "file://file"),
            ("/root/file", "file:///root/file"),
            ("/root/dir/", "file:///root/dir/"),
        )
        for test, expected_output in urls:
            self.assertEqual(urlfunctions.normalise_url(test), expected_output)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = urlfunctions
"""Implement URL helper functions"""

import re

URL_RE_HOSTNAME = re.compile("""^(?:(?P<scheme>\w+)://|)
                                 (?P<netloc>(?:(?P<username>.*?)(?::(?P<password>.*?)|)@|)
                                 (?P<hostname>[^@/]*?)(?::(?P<port>\d+)|))
                                 (?:(?P<path>/(?:.*?/|))
                                 /?(?P<file>[^/]*?|)|)
                                 (?:\;(?P<params>.*?)|)
                                 (?:\?(?P<query>.*?)|)
                                 (?:\#(?P<anchor>.*?)|)$""", re.VERBOSE)

URL_RE_PLAIN    = re.compile("""^(?:(?P<scheme>\w+)://|)
                                 (?:(?P<path>(?:.*?/|))
                                 /?(?P<file>[^/]*?|)|)
                                 (?:\;(?P<params>.*?)|)
                                 (?:\?(?P<query>.*?)|)
                                 (?:\#(?P<anchor>.*?)|)$""", re.VERBOSE)


class URLSplitResult(object):
    """Implement the result of url_split."""
    def __init__(self, match):
        # Call the superclass's __setattr__ to create the dictionary.
        super(URLSplitResult, self).__setattr__("_attr_dict", match)

    def __getattr__(self, name):
        """Get the requested attribute."""
        try:
            return self._attr_dict[name]
        except KeyError:
            return ""

    def __setattr__(self, name, value):
        """Set the requested attribute."""
        self._attr_dict[name] = value

    def get_dict(self):
        """Return a dictionary of only the attributes that have values set."""
        return dict((x[0], x[1]) for x in self._attr_dict.items() if x[1])

    def __repr__(self):
        """Return the dictionary representation of the class."""
        return repr(dict((x[0], x[1]) for x in self._attr_dict.items() if x[1]))


def url_split(url, uses_hostname=True, split_filename=False):
    """Split the URL into its components.

       uses_hostname defines whether the protocol uses a hostname or just a path (for
       "file://relative/directory"-style URLs) or not. split_filename defines whether the
       filename will be split off in an attribute or whether it will be part of the path
    """
    # urlparse.urlparse() is a bit deficient for our needs.
    try:
        if uses_hostname:
            match = URL_RE_HOSTNAME.match(url).groupdict()
        else:
            match = URL_RE_PLAIN.match(url).groupdict()
    except AttributeError:
        raise AttributeError, "Invalid URL."
    for key, item in match.items():
        if item is None:
            if key == "port":
                # We should leave port as None if it's not defined.
                match[key] = "0"
            else:
                match[key] = ""
    if uses_hostname:
        match["port"] = int(match["port"])
    if not split_filename:
        match["path"] = match["path"] + match["file"]
        match["file"] = ""

    return URLSplitResult(match)

def url_join(url):
    """Join a URLSplitResult class into a full URL. url_join(url_split(url)) returns _url_, with
       (valid) trailing slashes."""
    constructed_url = []
    if url.scheme:
        constructed_url.append(url.scheme + "://")
    constructed_url.append(url.username)
    if url.password:
        constructed_url.append(":" + url.password)
    if url.username or url.password:
        constructed_url.append("@")
    constructed_url.append(url.hostname)
    if url.port:
        constructed_url.append(":%s" % url.port)
    constructed_url.append(url.path)
    # If we have a file part and there is a hostname, make sure the path ends with a slash.
    if url.file and url.hostname and not url.path.endswith("/"):
        constructed_url.append("/")
    constructed_url.append(url.file)
    if url.params:
        constructed_url.append(";" + url.params)
    if url.query:
        constructed_url.append("?" + url.query)
    if url.anchor:
        constructed_url.append("#" + url.anchor)

    return "".join(constructed_url)

def append_slash(url, append=True):
    """Append a slash to a URL, checking if it already has one."""
    if url.endswith("/"):
        if append:
            return url
        else:
            return url[:-1]
    else:
        if append:
            return url + "/"
        else:
            return url

def prepend_slash(url, prepend=True):
    """Prepend a slash to a URL fragment, checking if it already has one."""
    if url.startswith("/"):
        if prepend:
            return url
        else:
            return url[1:]
    else:
        if prepend:
            return "/" + url
        else:
            return url

def url_splice(source_base_url, source_full_url, destination_base_url):
    """Intelligently join the difference in path to a second URL. For example, if
       _source_base_url_ is "my_url/path", _source_full_url_ is "my_url/path/other/files" and
       _destination_base_url_ is "another_url/another_path" then the function should return
       "another_url/another_path/other/files". The destination's query/parameters/anchor are left
       untouched.
    """
    source_base_url = url_split(source_base_url)
    source_full_url = url_split(source_full_url)
    destination_base_url = url_split(destination_base_url)
    assert source_full_url.path.startswith(source_base_url.path), \
           "Full URL does not begin with base URL."
    url_difference = source_full_url.path[len(source_base_url.path):]
    url_difference = prepend_slash(url_difference, False)
    destination_base_url.path = append_slash(destination_base_url.path, True) + url_difference
    return url_join(destination_base_url)

def normalise_url(url):
    """Normalise a URL from its shortcut to its proper form."""
    # Replace all backslashes with forward slashes.
    url = url.replace("\\", "/")

    # Prepend file:// to the URL if it lacks a protocol.
    split_url = url_split(url)
    if split_url.scheme == "":
        url = "file://" + url
    return url

########NEW FILE########
__FILENAME__ = version
VERSION = "0.1a2"

########NEW FILE########
