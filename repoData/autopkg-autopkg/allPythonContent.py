__FILENAME__ = AppDmgVersioner
#!/usr/bin/env python
#
# Copyright 2010 Per Olofsson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os.path
import glob
from Foundation import NSData, NSPropertyListSerialization, NSPropertyListMutableContainers

from DmgMounter import DmgMounter
from autopkglib import Processor, ProcessorError


__all__ = ["AppDmgVersioner"]


class AppDmgVersioner(DmgMounter):
    description = "Extracts bundle ID and version of app inside dmg."
    input_variables = {
        "dmg_path": {
            "required": True,
            "description": "Path to a dmg containing an app.",
        },
    }
    output_variables = {
        "app_name": {
            "description": "Name of app found on the disk image."
        },
        "bundleid": {
            "description": "Bundle identifier of the app.",
        },
        "version": {
            "description": "Version of the app.",
        },
    }
    
    __doc__ = description
    
    def find_app(self, path):
        """Find app bundle at path."""
        
        apps = glob.glob(os.path.join(path, "*.app"))
        if len(apps) == 0:
            raise ProcessorError("No app found in dmg")
        return apps[0]
    
    def read_bundle_info(self, path):
        """Read Contents/Info.plist inside a bundle."""
        
        plistpath = os.path.join(path, "Contents", "Info.plist")
        info, format, error = \
            NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(
                NSData.dataWithContentsOfFile_(plistpath),
                NSPropertyListMutableContainers,
                None,
                None
            )
        if error:
            raise ProcessorError("Can't read %s: %s" % (plistpath, error))
        
        return info
    
    def main(self):
        # Mount the image.
        mount_point = self.mount(self.env["dmg_path"])
        # Wrap all other actions in a try/finally so the image is always
        # unmounted.
        try:
            app_path = self.find_app(mount_point)
            info = self.read_bundle_info(app_path)
            self.env["app_name"] = os.path.basename(app_path)
            try:
                self.env["bundleid"] = info["CFBundleIdentifier"]
                self.env["version"] = info["CFBundleShortVersionString"]
                self.output("BundleID: %s" % self.env["bundleid"])
                self.output("Version: %s" % self.env["version"])
            except BaseException as e:
                raise ProcessorError(e)
        finally:
            self.unmount(self.env["dmg_path"])
    

if __name__ == '__main__':
    processor = AppDmgVersioner()
    processor.execute_shell()
    

########NEW FILE########
__FILENAME__ = BrewCaskInfoProvider
#!/usr/bin/env python
#
# Copyright 2013 Timothy Sutton
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import re
import urllib2

from autopkglib import Processor, ProcessorError

__all__ = ["BrewCaskInfoProvider"]


class BrewCaskInfoProvider(Processor):
    description = ("Provides crowd-sourced URL and version info from brew-cask: "
                    "https://github.com/phinze/homebrew-cask. See available apps: "
                    "https://github.com/phinze/homebrew-cask/tree/master/Casks")
    input_variables = {
        "cask_name": {
            "required": True,
            "description": ("Name of cask to fetch, as would be given to the 'brew' command. "
                            "Example: 'audacity'")
        }
    }
    output_variables = {
        "url": {
            "description": "URL for the Cask's download.",
        },
        "version": {
            "description": ("Version info from formula. Depending on the nature of the formula "
                            "and stability of the URL, this might be simply 'latest'. It's "
                            "provided here for convenience in the recipe.")
        }
    }

    __doc__ = description


    def parse_formula(self, formula):
        """Return a dict containing attributes of the formula, ie. 'url', 'version', etc.
        parsed from the formula .rb file."""
        attrs = {}
        regex = r"  (?P<attr>.+) '(?P<value>.+)'"
        for line in formula.splitlines():
            match = re.match(regex, line)
            if match:
                attrs[match.group("attr")] = match.group("value")
        if not attrs:
            raise ProcessorError("Could not parse formula!")
        return attrs


    def main(self):
        github_raw_baseurl = "https://raw.github.com/phinze/homebrew-cask/master/Casks"
        cask_url = "%s/%s.rb" % (github_raw_baseurl, self.env["cask_name"])
        try:
            urlobj = urllib2.urlopen(cask_url)
        except urllib2.HTTPError as e:
            raise ProcessorError("Error opening URL %s: %s"
                % (cask_url, e))

        formula_data = urlobj.read()
        parsed = self.parse_formula(formula_data)

        if not "url" in parsed.keys():
            raise ProcessorError("No 'url' parsed from Formula!")
        self.env["url"] = parsed["url"]

        if "version" in parsed.keys():
            self.env["version"] = parsed["version"]
        else:
            self.env["version"] = ""

        self.output("Got URL %s from for cask '%s':"
            % (self.env["url"], self.env["cask_name"]))


if __name__ == "__main__":
    processor = BrewCaskInfoProvider()
    processor.execute_shell()

########NEW FILE########
__FILENAME__ = Copier
#!/usr/bin/env python
#
# Copyright 2010 Per Olofsson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os.path
import shutil

from glob import glob
from autopkglib import Processor, ProcessorError
from DmgMounter import DmgMounter


__all__ = ["Copier"]


class Copier(DmgMounter):
    description = "Copies source_path to destination_path."
    input_variables = {
        "source_path": {
            "required": True,
            "description": ("Path to a file or directory to copy. "
                "Can point to a path inside a .dmg which will be mounted. "
                "This path may also contain basic globbing characters such as "
                "the wildcard '*', but only the first result will be returned."),
        },
        "destination_path": {
            "required": True,
            "description": "Path to destination.",
        },
        "overwrite": {
            "required": False,
            "description": "Whether the destination will be overwritten if necessary.",
        },
    }
    output_variables = {
    }
    
    __doc__ = description
    
    def copy(self, source_item, dest_item, overwrite=False):
        '''Copies source_item to dest_item, overwriting if allowed'''
        # Remove destination if needed.
        if os.path.exists(dest_item) and overwrite:
            try:
                if os.path.isdir(dest_item) and not os.path.islink(dest_item):
                    shutil.rmtree(dest_item)
                else:
                    os.unlink(dest_item)
            except OSError, err:
                raise ProcessorError(
                    "Can't remove %s: %s" % (dest_item, err.strerror))
                    
        # Copy file or directory.
        try:
            if os.path.isdir(source_item):
                shutil.copytree(source_item, dest_item, symlinks=True)
            elif not os.path.isdir(dest_item):
                shutil.copyfile(source_item, dest_item)
            else:
                shutil.copy(source_item, dest_item)
            self.output("Copied %s to %s" % (source_item, dest_item))
        except BaseException, err:
            raise ProcessorError(
                "Can't copy %s to %s: %s" % (source_item, dest_item, err))
    
    def main(self):
        source_path = self.env['source_path']
        # Check if we're trying to copy something inside a dmg.
        (dmg_path, dmg,
         dmg_source_path) = source_path.partition(".dmg/")
        dmg_path += ".dmg"
        try:
            if dmg:
                # Mount dmg and copy path inside.
                mount_point = self.mount(dmg_path)
                source_path = os.path.join(mount_point, dmg_source_path)
            # process path with glob.glob
            matches = glob(source_path)
            if len(matches) == 0:
                raise ProcessorError("Error processing path '%s' with glob. " % source_path)
            matched_source_path = matches[0]
            if len(matches) > 1:
                self.output("WARNING: Multiple paths match 'source_path' glob '%s':"
                    % source_path)
                for match in matches:
                    self.output("  - %s" % match)

            if [c for c in '*?[]!' if c in source_path]:
                self.output("Using path '%s' matched from globbed '%s'."
                    % (matched_source_path, source_path))

            # do the copy
            self.copy(matched_source_path, self.env['destination_path'],
                      overwrite=self.env.get("overwrite"))
        finally:
            if dmg:
                self.unmount(dmg_path)
    

if __name__ == '__main__':
    processor = Copier()
    processor.execute_shell()
    

########NEW FILE########
__FILENAME__ = DmgCreator
#!/usr/bin/env python
#
# Copyright 2010 Per Olofsson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import subprocess
import shutil
import tempfile

from autopkglib import Processor, ProcessorError


__all__ = ["DmgCreator"]

DEFAULT_DMG_FORMAT = "UDZO"
DEFAULT_ZLIB_LEVEL = 5

class DmgCreator(Processor):
    description = "Creates a disk image from a directory."
    input_variables = {
        "dmg_root": {
            "required": True,
            "description": "Directory that will be copied to a disk image.",
        },
        "dmg_path": {
            "required": True,
            "description": "The dmg to be created.",
        },
        "dmg_format": {
            "required": False,
            "description": "The dmg format. Defaults to %s."
                            % DEFAULT_DMG_FORMAT,
        },
        "dmg_zlib_level": {
            "required": False,
            "description": ("Compression level between '1' and '9' to use "
                            "when using UDZO. Defaults to '%s', a point "
                            "beyond which very little space savings is "
                            "gained." % DEFAULT_ZLIB_LEVEL)
        },
        "dmg_megabytes": {
            "required": False,
            "description": ("Value to set for the '-megabytes' option, useful as a "
                            "workaround when hdiutil cannot accurately estimate "
                            "the required size for the dmg before compression. Not "
                            "normally required, and the option will not be used "
                            "if this variable is not defined.")
        }
    }
    output_variables = {
    }
    
    __doc__ = description
    
    def main(self):
        # Remove existing dmg if it exists.
        if os.path.exists(self.env['dmg_path']):
            os.unlink(self.env['dmg_path'])

        # Determine the format.
        # allow a subset of the formats supported by hdiutil, those
        # which aren't obsolete or deprecated
        valid_formats = [
                        "UDRW",
                        "UDRO",
                        "UDCO",
                        "UDZO",
                        "UDBZ",
                        "UFBI",
                        "UDTO",
                        "UDxx",
                        "UDSP",
                        "UDSB",
                        ]

        dmg_format = self.env.get("dmg_format", DEFAULT_DMG_FORMAT)
        if dmg_format not in valid_formats:
            raise ProcessorError(
                "dmg format '%s' is invalid. Must be one of: %s."
                % (dmg_format, ", ".join(valid_formats)))

        zlib_level = int(self.env.get("dmg_zlib_level", DEFAULT_ZLIB_LEVEL))
        if zlib_level < 1 or zlib_level > 9:
            raise ProcessorError(
                "dmg_zlib_level must be a value between 1 and 9.")

        # Build a command for hdiutil.
        cmd = [
              "/usr/bin/hdiutil",
              "create",
              "-plist",
              "-format",
              dmg_format
              ]
        if dmg_format == "UDZO":
            cmd.extend(["-imagekey", "zlib-level=%s" % str(zlib_level)])
        if self.env.get("dmg_megabytes"):
            cmd.extend(["-megabytes", str(self.env["dmg_megabytes"])])
        cmd.extend([
            "-srcfolder", self.env['dmg_root'],
            self.env['dmg_path']])

        # Call hdiutil.
        try:
            p = subprocess.Popen(cmd,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            (out, err) = p.communicate()
        except OSError as e:
            raise ProcessorError("hdiutil execution failed with error code %d: %s" % (
                                  e.errno, e.strerror))
        if p.returncode != 0:
            raise ProcessorError("creation of %s failed: %s" % (self.env['dmg_path'], err))
        
        # Read output plist.
        #output = FoundationPlist.readPlistFromString(out)
        self.output("Created dmg from %s at %s" 
            % (self.env['dmg_root'], self.env['dmg_path']))

if __name__ == '__main__':
    processor = DmgCreator()
    processor.execute_shell()
    

########NEW FILE########
__FILENAME__ = DmgMounter
#!/usr/bin/env python
#
# Copyright 2010 Per Olofsson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import subprocess
import FoundationPlist

from autopkglib import Processor, ProcessorError


__all__ = ["DmgMounter"]


class DmgMounter(Processor):
    """Base class for Processors that need to mount disk images."""
    
    def __init__(self, data=None, infile=None, outfile=None):
        super(DmgMounter, self).__init__(data, infile, outfile)
        self.mounts = dict()
        
    def getFirstPlist(self, textString):
        """Gets the first plist from a text string that may contain one or
        more text-style plists.
        Returns a tuple - the first plist (if any) and the remaining
        string after the plist"""
        plist_header = '<?xml version'
        plist_footer = '</plist>'
        plist_start_index = textString.find(plist_header)
        if plist_start_index == -1:
            # not found
            return ("", textString)
        plist_end_index = textString.find(
            plist_footer, plist_start_index + len(plist_header))
        if plist_end_index == -1:
            # not found
            return ("", textString)
        # adjust end value
        plist_end_index = plist_end_index + len(plist_footer)
        return (textString[plist_start_index:plist_end_index],
                textString[plist_end_index:])
    
    def DMGhasSLA(self, dmgpath):
        '''Returns true if dmg has a Software License Agreement.
        These dmgs normally cannot be attached without user intervention'''
        hasSLA = False
        proc = subprocess.Popen(
                    ['/usr/bin/hdiutil', 'imageinfo', dmgpath, '-plist'],
                    bufsize=-1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = proc.communicate()
        if err:
            print >> sys.stderr, (
                'hdiutil error %s with image %s.' % (err, dmgpath))
        (pliststr, out) = self.getFirstPlist(out)
        if pliststr:
            try:
                plist = FoundationPlist.readPlistFromString(pliststr)
                properties = plist.get('Properties')
                if properties:
                    hasSLA = properties.get('Software License Agreement', False)
            except FoundationPlist.NSPropertyListSerializationException:
                pass

        return hasSLA
    
    def mount(self, pathname):
        """Mount image with hdiutil."""
        # Make sure we don't try to mount something twice.
        if pathname in self.mounts:
            raise ProcessorError("%s is already mounted" % pathname)
        
        stdin = ''
        if self.DMGhasSLA(pathname):
            stdin = 'Y\n'
        
        # Call hdiutil.
        try:
            p = subprocess.Popen(("/usr/bin/hdiutil",
                                  "attach",
                                  "-plist",
                                  "-mountrandom", "/private/tmp",
                                  "-nobrowse",
                                  pathname),
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 stdin=subprocess.PIPE)
            (out, err) = p.communicate(stdin)
        except OSError as e:
            raise ProcessorError(
                "hdiutil execution failed with error code %d: %s" 
                % (e.errno, e.strerror))
        if p.returncode != 0:
            raise ProcessorError("mounting %s failed: %s" % (pathname, err))
        
        # Read output plist.
        (pliststr, out) = self.getFirstPlist(out)
        try:
            output = FoundationPlist.readPlistFromString(pliststr)
        except FoundationPlist.NSPropertyListSerializationException:
            raise ProcessorError(
                "mounting %s failed: unexpected output from hdiutil" % pathname)
        
        # Find mount point.
        for part in output.get("system-entities", []):
            if "mount-point" in part:
                # Add to mount list.
                self.mounts[pathname] = part["mount-point"]
                self.output("Mounted disk image %s" % pathname)
                return self.mounts[pathname]
        raise ProcessorError(
            "mounting %s failed: unexpected output from hdiutil" % pathname)

    def unmount(self, pathname):
        """Unmount previously mounted image."""
        
        # Don't try to unmount something we didn't mount.
        if not pathname in self.mounts:
            raise ProcessorError("%s is not mounted" % pathname)
        
        # Call hdiutil.
        try:
            p = subprocess.Popen(("/usr/bin/hdiutil",
                                  "detach",
                                  self.mounts[pathname]),
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (out, err) = p.communicate()
        except OSError as e:
            raise ProcessorError(
                "ditto execution failed with error code %d: %s" 
                % (e.errno, e.strerror))
        if p.returncode != 0:
            raise ProcessorError("unmounting %s failed: %s" % (pathname, err))
        
        # Delete mount from mount list.
        del self.mounts[pathname]
    

if __name__ == '__main__':
    try:
        import sys
        dmgmounter = DmgMounter()
        mountpoint = dmgmounter.mount("Download/Firefox-sv-SE.dmg")
        print "Mounted at %s" % mountpoint
        dmgmounter.unmount("Download/Firefox-sv-SE.dmg")
    except ProcessorError as e:
        print >>sys.stderr, "ProcessorError: %s" % e
        sys.exit(10)
    else:
        sys.exit(0)
    

########NEW FILE########
__FILENAME__ = EndOfCheckPhase
#!/usr/bin/env python
#
# Copyright 2013 Greg Neagle
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from autopkglib import Processor


__all__ = ["EndOfCheckPhase"]


class EndOfCheckPhase(Processor):
    """This processor does nothing at all."""
    input_variables = {
    }
    output_variables = {
    }
    description = __doc__
    
    
    def main(self):
        return
    
    
if __name__ == '__main__':
    processor = EndOfCheckPhase()
    processor.execute_shell()

########NEW FILE########
__FILENAME__ = FileCreator
#!/usr/bin/env python
#
# Copyright 2011 Per Olofsson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os.path
import shutil

from autopkglib import Processor, ProcessorError


__all__ = ["FileCreator"]


class FileCreator(Processor):
    description = "Create a file."
    # FIXME: add mode, owner
    input_variables = {
        "file_path": {
            "required": True,
            "description": "Path to a file to create.",
        },
        "file_content": {
            "required": True,
            "description": "Contents to put in file.",
        },
    }
    output_variables = {
    }
    
    __doc__ = description
    
    def main(self):
        try:
            with open(self.env['file_path'], "w") as f:
                f.write(self.env['file_content'])
            self.output("Created file at %s" % self.env['file_path'])
        except BaseException as e:
            raise ProcessorError("Can't create file at %s: %s" % (
                                  self.env['file_path'],
                                  e))
    

if __name__ == '__main__':
    processor = FileCreator()
    processor.execute_shell()
    

########NEW FILE########
__FILENAME__ = FileFinder
#!/usr/bin/env python
#
# Copyright 2013 Jesse Peterson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.



from glob import glob
from autopkglib import Processor, ProcessorError

__all__ = ["FileFinder"]

class FileFinder(Processor):
    '''Finds a filename for use in other Processors.

Currently only supports glob filename patterns.
'''

    input_variables = {
        'pattern': {
            'description': 'Shell glob pattern to match files by',
            'required': True,
        },
        'find_method': {
            'description': 'Type of pattern to match. Currently only supported type is "glob" (also the default)',
            'required': False,
        },
    }
    output_variables = {
        'found_filename': {
            'description': 'Found filename',
        }
    }

    description = __doc__

    def globfind(self, pattern):
        '''If multiple files are found the last alphanumerically sorted found file is returned'''

        glob_matches = glob(pattern)

        if len(glob_matches) < 1:
            raise ProcessorError('No matching filename found')

        glob_matches.sort()

        return glob_matches[-1]

    def main(self):
        pattern = self.env.get('pattern')

        method = self.env.get('find_method', 'glob')

        if method == 'glob':
            self.env['found_filename'] = self.globfind(pattern)
        else:
            raise ProcessorError('Unsupported find_method: %s' % method)

        self.output('Found file match: %s' % self.env['found_filename'])

if __name__ == '__main__':
    processor = FileFinder()
    processor.execute_shell()

########NEW FILE########
__FILENAME__ = FileMover
#!/usr/bin/env python

from os import rename
from autopkglib import Processor, ProcessorError

__all__ = ["FileMover"]

class FileMover(Processor):
    '''Moves/renames a file'''

    input_variables = {
        'source': {
            'description': 'Source file',
            'required': True,
        },
        'target': {
            'description': 'Target file',
            'required': True,
        },
    }
    output_variables = {
    }

    description = __doc__

    def main(self):
        rename(self.env['source'], self.env['target'])
        self.output('File %s moved to %s' % (self.env['source'], self.env['target']))

if __name__ == '__main__':
    processor = FileMover()
    processor.execute_shell()

########NEW FILE########
__FILENAME__ = FlatPkgPacker
#!/usr/bin/env python
#
# Copyright 2013 Jesse Peterson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import shutil
import subprocess

from autopkglib import Processor, ProcessorError

__all__ = ["FlatPkgPacker"]


class FlatPkgPacker(Processor):
    '''Flatten an expanded package using pkgutil'''

    description = __doc__

    input_variables = {
        'source_flatpkg_dir': {
            'description': 'Path to an extracted flat package',
            'required': True,
        },
        'destination_pkg': {
            'description': 'Name of destination pkg to be flattened',
            'required': True,
        },
    }

    output_variables = {}

    def flatten(self, source_dir, dest_pkg):
        try:
            subprocess.check_call(['/usr/sbin/pkgutil', '--flatten', source_dir, dest_pkg])
        except subprocess.CalledProcessError, err:
            raise ProcessorError("%s flattening %s" % (err, source_dir))

    def main(self):
        source_dir = self.env.get('source_flatpkg_dir')
        dest_pkg = self.env.get('destination_pkg')

        self.flatten(source_dir, dest_pkg)

        self.output("Flattened %s to %s" 
            % (source_dir, dest_pkg))

if __name__ == '__main__':
    processor = FlatPkgPacker()
    processor.execute_shell()

########NEW FILE########
__FILENAME__ = FlatPkgUnpacker
#!/usr/bin/env python
#
# Copyright 2013 Timothy Sutton
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Borrowed code and concepts from Unzipper and Copier processors.

import os.path
import subprocess
import shutil

from glob import glob
from autopkglib import ProcessorError
from DmgMounter import DmgMounter


__all__ = ["FlatPkgUnpacker"]


class FlatPkgUnpacker(DmgMounter):
    description = ("Expands a flat package using pkgutil or xar. "
        "For xar it also optionally skips extracting the payload.")
    input_variables = {
        "flat_pkg_path": {
            "required": True,
            "description": ("Path to a flat package. "
                "Can point to a globbed path inside a .dmg which will "
                "be mounted."),
        },
        "skip_payload": {
            "required": False,
            "description": ("If true, 'Payload' files will be skipped. "
                "Defaults to False. Note if this option is used then the "
                "files are extracted using xar(1) instead of pkgutil(1). "
                "This means components of the package will not be "
                "extracted such as scripts."),
        },
        "destination_path": {
            "required": True,
            "description": ("Directory where archive will be unpacked, created "
                "if necessary."),
        },
        "purge_destination": {
            "required": False,
            "description": ("Whether the contents of the destination directory "
                "will be removed before unpacking. Note that unless "
                "skip_payload argument is used the destination directory "
                "will be removed as pkgutil requires an empty destination."),
        },
    }
    output_variables = {
    }

    __doc__ = description
    source_path = None

    def unpackFlatPkg(self):
        # Create the directory if needed.
        if not os.path.exists(self.env['destination_path']):
            try:
                os.mkdir(self.env['destination_path'])
            except OSError as e:
                raise ProcessorError("Can't create %s: %s" 
                    % (self.env['destination_path'], e.strerror))
        elif self.env.get('purge_destination'):
            for entry in os.listdir(self.env['destination_path']):
                path = os.path.join(self.env['destination_path'], entry)
                try:
                    if os.path.isdir(path) and not os.path.islink(path):
                        shutil.rmtree(path)
                    else:
                        os.unlink(path)
                except OSError as e:
                    raise ProcessorError(
                        "Can't remove %s: %s" % (path, e.strerror))

        if self.env.get('skip_payload'):
            self.xarExpand()
        else:
            self.pkgutilExpand()

    def xarExpand(self):
        try:
            xarcmd = ["/usr/bin/xar",
                      "-x",
                      "-C", self.env['destination_path'],
                      "-f", self.source_path]
            if self.env.get('skip_payload'):
                xarcmd.extend(["--exclude", "Payload"])
            p = subprocess.Popen(xarcmd,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            (out, err) = p.communicate()
        except OSError as e:
            raise ProcessorError("xar execution failed with error code %d: %s" 
                % (e.errno, e.strerror))
        if p.returncode != 0:
            raise ProcessorError("extraction of %s with xar failed: %s" 
                % (self.env['flat_pkg_path'], err))

    def pkgutilExpand(self):
        # pkgutil requires the dest. folder to be non-existant
        if os.path.exists(self.env['destination_path']):
            try:
                shutil.rmtree(self.env['destination_path'])
            except OSError as e:
                raise ProcessorError(
                    "Can't remove %s: %s" % (self.env['destination_path'], e.strerror))

        try:
            pkgutilcmd = ["/usr/sbin/pkgutil",
                      "--expand",
                      self.source_path,
                      self.env['destination_path']]
            p = subprocess.Popen(pkgutilcmd,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            (out, err) = p.communicate()
        except OSError as e:
            raise ProcessorError("pkgutil execution failed with error code %d: %s" 
                % (e.errno, e.strerror))
        if p.returncode != 0:
            raise ProcessorError("extraction of %s with pkgutil failed: %s" 
                % (self.env['flat_pkg_path'], err))

    def main(self):
        # Check if we're trying to copy something inside a dmg.
        (dmg_path, dmg, dmg_source_path) = self.env[
            'flat_pkg_path'].partition(".dmg/")
        dmg_path += ".dmg"
        try:
            if dmg:
                # Mount dmg and copy path inside.
                mount_point = self.mount(dmg_path)
                self.source_path = glob(
                    os.path.join(mount_point, dmg_source_path))[0]
            else:
                # Straight copy from file system.
                self.source_path = self.env['flat_pkg_path']
            self.unpackFlatPkg()
            self.output("Unpacked %s to %s" 
                % (self.source_path, self.env['destination_path']))
        finally:
            if dmg:
                self.unmount(dmg_path)


if __name__ == '__main__':
    processor = FlatPkgUnpacker()
    processor.execute_shell()
    

########NEW FILE########
__FILENAME__ = MunkiCatalogBuilder
#!/usr/bin/env python
#
# Copyright 2013 Greg Neagle
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import subprocess

from autopkglib import Processor, ProcessorError


__all__ = ["MunkiCatalogBuilder"]


class MunkiCatalogBuilder(Processor):
    """Rebuilds Munki catalogs."""
    input_variables = {
        "MUNKI_REPO": {
            "required": True,
            "description": "Path to the Munki repo.",
        },
        "munki_repo_changed": {
            "required": False,
            "description": ("If not defined or False, causes running "
                "makecatalogs to be skipped."),
        },
    }
    output_variables = {
    }
    description = __doc__
    
    def main(self):
        # MunkiImporter or other processor must set
        # env["munki_repo_changed"] = True in order for makecatalogs
        # to run
        if not self.env.get("munki_repo_changed"):
            self.output("Skipping makecatalogs because repo is unchanged.")
            return
        
        # Generate arguments for makecatalogs.
        args = ["/usr/local/munki/makecatalogs", self.env["MUNKI_REPO"]]
        
        # Call makecatalogs.
        try:
            proc = subprocess.Popen(
                args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (out, err_out) = proc.communicate()
        except OSError as err:
            raise ProcessorError(
                "makecatalog execution failed with error code %d: %s" 
                % (err.errno, err.strerror))
        if proc.returncode != 0:
            raise ProcessorError(
                "makecatalogs failed: %s" % err_out)
        self.output("Munki catalogs rebuilt!")


if __name__ == "__main__":
    processor = MunkiCatalogBuilder()
    processor.execute_shell()
########NEW FILE########
__FILENAME__ = MunkiImporter
#!/usr/bin/env python
#
# Copyright 2013 Greg Neagle
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import subprocess
import FoundationPlist
import shutil

from distutils import version

from autopkglib import Processor, ProcessorError


__all__ = ["MunkiImporter"]


class MunkiImporter(Processor):
    """Imports a pkg or dmg to the Munki repo."""
    input_variables = {
        "MUNKI_REPO": {
            "description": "Path to a mounted Munki repo.",
            "required": True
        },
        "pkg_path": {
            "required": True,
            "description": "Path to a pkg or dmg to import.",
        },
        "munkiimport_pkgname": {
            "required": False,
            "description": "Corresponds to --pkgname option to munkiimport.",
        },
        "munkiimport_appname": {
            "required": False,
            "description": "Corresponds to --appname option to munkiimport.",
        },
        "repo_subdirectory": {
            "required": False,
            "description": ("The subdirectory under pkgs to which the item "
                "will be copied, and under pkgsinfo where the pkginfo will "
                "be created."),
        },
        "pkginfo": {
            "required": False,
            "description": ("Dictionary of pkginfo keys to copy to "
                "generated pkginfo."),
        },
        "force_munkiimport": {
            "required": False,
            "description": ("If not False or Null, causes the pkg/dmg to be "
                "imported even if there is a matching pkg already in the "
                "repo."),        
        },
        "additional_makepkginfo_options": {
            "required": False,
            "description": ("Array of additional command-line options that will "
                "be inserted when calling 'makepkginfo'.")
        },
        "version_comparison_key": {
            "required": False,
            "description": ("String to set 'version_comparison_key' for "
                            "any generated installs items."),
        },
        "MUNKI_PKGINFO_FILE_EXTENSION": {
            "description": "Extension for output pkginfo files. Default is 'plist'.",
            "required": False
        },
    }
    output_variables = {
        "pkginfo_repo_path": {
            "description": ("The repo path where the pkginfo was written. "
                "Empty if item not imported."),
        },
        "pkg_repo_path": {
            "description": ("The repo path where the pkg was written. "
                "Empty if item not imported."),
        },
        "munki_info": {
            "description": 
                "The pkginfo property list. Empty if item not imported.",
        },
        "munki_repo_changed": {
            "description": "True if item was imported."
        },
    }
    description = __doc__
    
    def makeCatalogDB(self):
        """Reads the 'all' catalog and returns a dict we can use like a
         database"""
        
        repo_path = self.env["MUNKI_REPO"]
        all_items_path = os.path.join(repo_path, 'catalogs', 'all')
        if not os.path.exists(all_items_path):
            # might be an error, or might be a brand-new empty repo
            catalogitems = []
        else:
            try:
                catalogitems = FoundationPlist.readPlist(all_items_path)
            except OSError, err:
                raise ProcessorError(
                    "Error reading 'all' catalog from Munki repo: %s" % err)

        pkgid_table = {}
        app_table = {}
        installer_item_table = {}
        hash_table = {}
        checksum_table = {}

        itemindex = -1
        for item in catalogitems:
            itemindex = itemindex + 1
            name = item.get('name', 'NO NAME')
            vers = item.get('version', 'NO VERSION')

            if name == 'NO NAME' or vers == 'NO VERSION':
                # skip this item
                continue

            # add to hash table
            if 'installer_item_hash' in item:
                if not item['installer_item_hash'] in hash_table:
                    hash_table[item['installer_item_hash']] = []
                hash_table[item['installer_item_hash']].append(itemindex)

            # add to installer item table
            if 'installer_item_location' in item:
                installer_item_name = os.path.basename(
                    item['installer_item_location'])
                if not installer_item_name in installer_item_table:
                    installer_item_table[installer_item_name] = {}
                if not vers in installer_item_table[installer_item_name]:
                    installer_item_table[installer_item_name][vers] = []
                installer_item_table[
                                installer_item_name][vers].append(itemindex)

            # add to table of receipts
            for receipt in item.get('receipts', []):
                try:
                    if 'packageid' in receipt and 'version' in receipt:
                        if not receipt['packageid'] in pkgid_table:
                            pkgid_table[receipt['packageid']] = {}
                        if not vers in pkgid_table[receipt['packageid']]:
                            pkgid_table[receipt['packageid']][vers] = []
                        pkgid_table[receipt['packageid']][
                                                    vers].append(itemindex)
                except TypeError:
                    # skip this receipt
                    continue
                
            # add to table of installed applications
            for install in item.get('installs', []):
                try:
                    if install.get('type') == 'application':
                        if 'path' in install:
                            if 'version_comparison_key' in install:
                                app_version = install[
                                            install['version_comparison_key']]
                            else:
                                 app_version = install[
                                                'CFBundleShortVersionString']
                            if not install['path'] in app_table:
                                app_table[install['path']] = {}
                            if not vers in app_table[install['path']]:
                                app_table[install['path']][app_version] = []
                            app_table[install['path']][app_version].append(
                                                                    itemindex)
                    if install.get('type') == 'file':
                        if 'path' in install and 'md5checksum' in install:
                            cksum = install['md5checksum']

                            if cksum not in checksum_table.keys():
                                checksum_table[cksum] = []

                            checksum_table[cksum].append({'path': install['path'], 'index': itemindex})
                except (TypeError, KeyError):
                    # skip this item
                    continue

        pkgdb = {}
        pkgdb['hashes'] = hash_table
        pkgdb['receipts'] = pkgid_table
        pkgdb['applications'] = app_table
        pkgdb['installer_items'] = installer_item_table
        pkgdb['checksums'] = checksum_table
        pkgdb['items'] = catalogitems

        return pkgdb
    
    def findMatchingItemInRepo(self, pkginfo):
        """Looks through all catalog for items matching the one
        described by pkginfo. Returns a matching item if found."""
        
        def compare_version_keys(value_a, value_b):
            """Internal comparison function for use in sorting"""
            return cmp(version.LooseVersion(value_b),
                       version.LooseVersion(value_a))
        
        if not pkginfo.get('installer_item_hash'):
            return None
            
        if self.env.get("force_munkiimport"):
            # we need to import even if there's a match, so skip
            # the check
            return None
            
        pkgdb = self.makeCatalogDB()

        # match hashes for the pkg or dmg
        if 'installer_item_hash' in pkginfo:
            pkgdb = self.makeCatalogDB()
            matchingindexes = pkgdb['hashes'].get(
                                        pkginfo['installer_item_hash'])
            if matchingindexes:
                # we have an item with the exact same checksum hash in the repo
                return pkgdb['items'][matchingindexes[0]]

        # try to match against installed applications
        applist = [item for item in pkginfo.get('installs', [])
                   if item['type'] == 'application' and 'path' in item]
        if applist:
            matching_indexes = []
            for app in applist:
                app_path = app['path']
                if 'version_comparison_key' in app:
                    app_version = app[app['version_comparison_key']]
                else:
                     app_version = app['CFBundleShortVersionString']
                match = pkgdb['applications'].get(app_path, {}).get(app_version)
                if not match:
                    # no entry for app['path'] and app['version']
                    # no point in continuing
                    return None
                else:
                    if not matching_indexes:
                        # store the array of matching item indexes
                        matching_indexes = set(match)
                    else:
                        # we're only interested in items that match
                        # all applications
                        matching_indexes = matching_indexes.intersection(
                                                                set(match))
            
            # if we get here, we may have found matches
            if matching_indexes:
                return pkgdb['items'][list(matching_indexes)[0]]
            else:
                return None
        
        # fall back to matching against receipts
        matching_indexes = []
        for item in pkginfo.get('receipts', []):
            pkgid = item.get('packageid')
            vers = item.get('version')
            if pkgid and vers:
                match = pkgdb['receipts'].get(pkgid, {}).get(vers)
                if not match:
                    # no entry for pkgid and vers
                    # no point in continuing
                    return None
                else:
                    if not matching_indexes:
                        # store the array of matching item indexes
                        matching_indexes = set(match)
                    else:
                        # we're only interested in items that match
                        # all receipts
                        matching_indexes = matching_indexes.intersection(
                                                                set(match))
        
            # if we get here, we may have found matches
            if matching_indexes:
                return pkgdb['items'][list(matching_indexes)[0]]
            else:
                return None
 
        # try to match against install md5checksums
        filelist = [item for item in pkginfo.get('installs', [])
                   if item['type'] == 'file' and
                      'path' in item and
                      'md5checksum' in item]
        if filelist:
            for f in filelist:
                cksum = f['md5checksum']
                if cksum in pkgdb['checksums']:
                    cksum_matches = pkgdb['checksums'][cksum]
                    for cksum_match in cksum_matches:
                        if cksum_match['path'] == f['path']:
                            matching_pkg = pkgdb['items'][cksum_match['index']]

                            # TODO: maybe match pkg name, too?
                            # if matching_pkg.get('name') == pkginfo.get('name'):

                            return matching_pkg

        # if we get here, we found no matches
        return None
    
    
    def copyItemToRepo(self, pkginfo):
        """Copies an item to the appropriate place in the repo.
        If itempath is a path within the repo/pkgs directory, copies nothing.
        Renames the item if an item already exists with that name.
        Returns the relative path to the item."""
        
        itempath = self.env["pkg_path"]
        repo_path = self.env["MUNKI_REPO"]
        subdirectory = self.env.get("repo_subdirectory", "")
        item_version = pkginfo.get("version")
        
        if not os.path.exists(repo_path):
            raise ProcessorError("Munki repo not available at %s." % repo_path)

        destination_path = os.path.join(repo_path, "pkgs", subdirectory)
        if not os.path.exists(destination_path):
            try:
                os.makedirs(destination_path)
            except OSError, err:
                raise ProcessorError("Could not create %s: %s" %
                                        (destination_path, err.strerror))

        item_name = os.path.basename(itempath)
        destination_pathname = os.path.join(destination_path, item_name)

        if itempath == destination_pathname:
            # we've been asked to 'import' an item already in the repo.
            # just return the relative path
            return os.path.join(subdirectory, item_name)

        if item_version:
            name, ext = os.path.splitext(item_name)
            if not name.endswith(item_version):
                # add the version number to the end of
                # the item name
                item_name = "%s-%s%s" % (name, item_version, ext)
                destination_pathname = os.path.join(
                    destination_path, item_name)

        index = 0
        name, ext = os.path.splitext(item_name)
        while os.path.exists(destination_pathname):
            # try appending numbers until we have a unique name
            index += 1
            item_name = "%s__%s%s" % (name, index, ext)
            destination_pathname = os.path.join(destination_path, item_name)

        try:
            shutil.copy(itempath, destination_pathname)
        except OSError, err:
            raise ProcessorError(
                "Can't copy %s to %s: %s" 
                % (self.env["pkg_path"], destination_pathname, err.strerror))

        return os.path.join(subdirectory, item_name)

    def copyPkginfoToRepo(self, pkginfo):
        """Saves pkginfo to munki_repo_path/pkgsinfo/subdirectory.
        Returns full path to the pkginfo in the repo."""
        # less error checking because we copy the installer_item
        # first and bail if it fails...
        repo_path = self.env["MUNKI_REPO"]
        subdirectory = self.env.get("repo_subdirectory", "")
        destination_path = os.path.join(repo_path, "pkgsinfo", subdirectory)
        if not os.path.exists(destination_path):
            try:
                os.makedirs(destination_path)
            except OSError, err:
                raise ProcessorError("Could not create %s: %s"
                                      % (destination_path, err.strerror))

        extension = "plist"
        if self.env.get("MUNKI_PKGINFO_FILE_EXTENSION"):
            extension = self.env["MUNKI_PKGINFO_FILE_EXTENSION"].strip(".")
        pkginfo_name = "%s-%s.%s" % (pkginfo["name"],
                                     pkginfo["version"].strip(),
                                     extension)
        pkginfo_path = os.path.join(destination_path, pkginfo_name)
        index = 0
        while os.path.exists(pkginfo_path):
            index += 1
            pkginfo_name = "%s-%s__%s.%s" % (
                pkginfo["name"], pkginfo["version"], index, extension)
            pkginfo_path = os.path.join(destination_path, pkginfo_name)

        try:
            FoundationPlist.writePlist(pkginfo, pkginfo_path)
        except OSError, err:
            raise ProcessorError("Could not write pkginfo %s: %s"
                                 % (pkginfo_path, err.strerror))
        return pkginfo_path
    
    def main(self):
        
        # Generate arguments for makepkginfo.
        args = ["/usr/local/munki/makepkginfo", self.env["pkg_path"]]
        if self.env.get("munkiimport_pkgname"):
            args.extend(["--pkgname", self.env["munkiimport_pkgname"]])
        if self.env.get("munkiimport_appname"):
            args.extend(["--appname", self.env["munkiimport_appname"]])
        if self.env.get("additional_makepkginfo_options"):
            args.extend(self.env["additional_makepkginfo_options"])
        
        # Call makepkginfo.
        try:
            proc = subprocess.Popen(
                args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (out, err_out) = proc.communicate()
        except OSError as err:
            raise ProcessorError(
                "makepkginfo execution failed with error code %d: %s" 
                % (err.errno, err.strerror))
        if proc.returncode != 0:
            raise ProcessorError(
                "creating pkginfo for %s failed: %s" 
                % (self.env["pkg_path"], err_out))
        
        # Get pkginfo from output plist.
        pkginfo = FoundationPlist.readPlistFromString(out)
        
        # copy any keys from pkginfo in self.env
        if "pkginfo" in self.env:
            for key in self.env["pkginfo"]:
                pkginfo[key] = self.env["pkginfo"][key]

        # set an alternate version_comparison_key if pkginfo has an installs item
        if "installs" in pkginfo and self.env.get("version_comparison_key"):
            for item in pkginfo["installs"]:
                if not self.env["version_comparison_key"] in item:
                    raise ProcessorError(
                        ("version_comparison_key '%s' could not be found in the "
                        "installs item for path '%s'" % (
                            self.env["version_comparison_key"],
                            item["path"])))
                item["version_comparison_key"] = self.env["version_comparison_key"]
        
        # check to see if this item is already in the repo
        matchingitem = self.findMatchingItemInRepo(pkginfo)
        if matchingitem:
            self.env["pkginfo_repo_path"] = ""
            # set env["pkg_repo_path"] to the path of the matching item
            self.env["pkg_repo_path"] = os.path.join(
                self.env["MUNKI_REPO"], "pkgs",
                matchingitem['installer_item_location'])
            self.env["munki_info"] = {}
            if not "munki_repo_changed" in self.env:
                self.env["munki_repo_changed"] = False
            
            self.output("Item %s already exists in the munki repo as %s."
                % (os.path.basename(self.env["pkg_path"]),
                   "pkgs/" + matchingitem['installer_item_location']))
            return
            
        # copy pkg/dmg to repo
        relative_path = self.copyItemToRepo(pkginfo)
        # adjust the installer_item_location to match the actual location
        # and name
        pkginfo["installer_item_location"] = relative_path
        
        # set output variables
        self.env["pkginfo_repo_path"] = self.copyPkginfoToRepo(pkginfo)
        self.env["pkg_repo_path"] = os.path.join(
            self.env["MUNKI_REPO"], "pkgs", relative_path)
        # update env["pkg_path"] to match env["pkg_repo_path"]
        # this allows subsequent recipe steps to reuse the uploaded
        # pkg/dmg instead of re-uploading
        # This won't affect most recipes, since most have a single
        # MunkiImporter step (and it's usually the last step)
        self.env["pkg_path"] = self.env["pkg_repo_path"]
        self.env["munki_info"] = pkginfo
        self.env["munki_repo_changed"] = True
        
        self.output("Copied pkginfo to %s" % self.env["pkginfo_repo_path"])
        self.output("Copied pkg to %s" % self.env["pkg_repo_path"])

if __name__ == "__main__":
    processor = MunkiImporter()
    processor.execute_shell()

########NEW FILE########
__FILENAME__ = MunkiInfoCreator
#!/usr/bin/env python
#
# Copyright 2010 Per Olofsson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os.path
import subprocess
import FoundationPlist
import shutil
import tempfile

from autopkglib import Processor, ProcessorError


__all__ = ["MunkiInfoCreator"]


class MunkiInfoCreator(Processor):
    description = "Creates a pkginfo file for a munki package."
    input_variables = {
        "pkg_path": {
            "required": True,
            "description": "Path to a pkg or dmg in the munki repository.",
        },
        "version": {
            "required": False,
            "description": "Version to override makepkginfo.",
        },
        "name": {
            "required": False,
            "description": "Name to override makepkginfo.",
        },
        "info_path": {
            "required": False,
            "description": "Path to the pkgsinfo file.",
        },
    }
    output_variables = {
        "munki_info": {
            "description": "The pkginfo property list.",
        },
    }
    
    __doc__ = description
    
    def main(self):
        # Wrap in a try/finally so the temp_path is always removed.
        temp_path = None
        try:
            # Check munki version.
            if os.path.exists("/usr/local/munki/munkilib/version.plist"):
                # Assume 0.7.0 or higher.
                munkiopts = ("displayname", "description", "catalog")
            else:
                # Assume 0.6.0
                munkiopts = ("catalog",)
            
            # Copy pkg to a temporary local directory, as installer -query
            # (which is called by makepkginfo) doesn't work on network drives.
            if self.env["pkg_path"].endswith("pkg"):
                # Create temporary directory.
                temp_path = tempfile.mkdtemp(prefix="autopkg", dir="/private/tmp")
                
                # Copy the pkg there
                pkg_for_makepkginfo = os.path.join(temp_path, os.path.basename(self.env["pkg_path"]))
                shutil.copyfile(self.env["pkg_path"], pkg_for_makepkginfo)
            else:
                pkg_for_makepkginfo = self.env["pkg_path"]
            
            # Generate arguments for makepkginfo.
            args = ["/usr/local/munki/makepkginfo"]
            for option in munkiopts:
                if option in self.env:
                    args.append("--%s=%s" % (option, self.env[option]))
            args.append(pkg_for_makepkginfo)
            
            # Call makepkginfo.
            try:
                p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                (out, err) = p.communicate()
            except OSError as e:
                raise ProcessorError("makepkginfo execution failed with error code %d: %s" % (
                                      e.errno, e.strerror))
            if p.returncode != 0:
                raise ProcessorError("creating pkginfo for %s failed: %s" % (self.env['pkg_path'], err))
            
        # makepkginfo cleanup.
        finally:
            if temp_path is not None:
                shutil.rmtree(temp_path)
        
        # Read output plist.
        output = FoundationPlist.readPlistFromString(out)
        
        # Set version and name.
        if "version" in self.env:
            output["version"] = self.env["version"]
        if "name" in self.env:
            output["name"] = self.env["name"]
        
        # Save info.
        self.env["munki_info"] = output
        if "info_path" in self.env:
            FoundationPlist.writePlist(output, self.env["info_path"])
    

if __name__ == '__main__':
    processor = MunkiInfoCreator()
    processor.execute_shell()
    

########NEW FILE########
__FILENAME__ = MunkiInstallsItemsCreator
#!/usr/bin/env python
#
# Copyright 2013 Greg Neagle
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import FoundationPlist
import subprocess

from autopkglib import Processor, ProcessorError
from Foundation import NSDictionary

__all__ = ["MunkiInstallsItemsCreator"]


class MunkiInstallsItemsCreator(Processor):
    """Generates an installs array for a pkginfo file."""
    input_variables = {
        "installs_item_paths": {
            "required": True,
            "description": 
                "Array of paths to create installs items for.",
        },
        "faux_root": {
            "required": False,
            "description": "The root of an expanded package or filesystem.",
        },
        "version_comparison_key": {
            "required": False,
            "description": ("Set 'version_comparison_key' for installs items. "
                            "If this is a string, it is set to this value for "
                            "all items given to 'installs_item_paths'. If this "
                            "is a dictionary, takes a mapping of a path as "
                            "given to 'installs_item_paths' to the desired "
                            "version_comparison_key.\n"
                            "Example:\n"
                            "{'/Applications/Foo.app': 'CFBundleVersion',\n"
                            "'/Library/Bar.plugin': 'CFBundleShortVersionString'}"),
        },
        
    }
    output_variables = {
        "additional_pkginfo": {
            "description": "Pkginfo dictionary containing installs array.",
        },
    }
    description = __doc__
    
    def createInstallsItems(self):
        """Calls makepkginfo to create an installs array."""
        faux_root = ""
        if self.env.get("faux_root"):
            faux_root = self.env["faux_root"].rstrip("/")
        
        args = ["/usr/local/munki/makepkginfo"]
        for item in self.env["installs_item_paths"]:
            args.extend(["-f", faux_root + item])
        
        # Call makepkginfo.
        try:
            proc = subprocess.Popen(
                args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (out, err) = proc.communicate()
        except OSError as err:
            raise ProcessorError(
                "makepkginfo execution failed with error code %d: %s" 
                % (err.errno, err.strerror))
        if proc.returncode != 0:
            raise ProcessorError(
                "creating pkginfo failed: %s" % err)

        # Get pkginfo from output plist.
        pkginfo = FoundationPlist.readPlistFromString(out)
        installs_array = pkginfo.get("installs", [])
        
        if faux_root:
            for item in installs_array:
                if item["path"].startswith(faux_root):
                    item["path"] = item["path"][len(faux_root):]
                self.output("Created installs item for %s" % item["path"])

        if "version_comparison_key" in self.env:
            for item in installs_array:
                cmp_key = None
                # If it's a string, set it for all installs items
                if isinstance(self.env["version_comparison_key"], basestring):
                    cmp_key = self.env["version_comparison_key"]
                # It it's a dict, find if there's a key that matches a path
                elif isinstance(self.env["version_comparison_key"], NSDictionary):
                    for path, key in self.env["version_comparison_key"].items():
                        if path == item["path"]:
                            cmp_key = key

                if cmp_key:
                    # Check that we really have this key available for comparison
                    if cmp_key in item:
                        item["version_comparison_key"] = cmp_key
                    else:
                        raise ProcessorError(
                        "version_comparison_key '%s' could not be found in the "
                        "installs item for path '%s'" % (
                            cmp_key,
                            item["path"]))

        if not "additional_pkginfo" in self.env:
            self.env["additional_pkginfo"] = {}
        self.env["additional_pkginfo"]["installs"] = installs_array


    def main(self):
        self.createInstallsItems()


if __name__ == "__main__":
    processor = MunkiInstallsItemsCreator()
    processor.execute_shell()

########NEW FILE########
__FILENAME__ = MunkiPkginfoMerger
#!/usr/bin/env python
#
# Copyright 2013 Greg Neagle
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from autopkglib import Processor, ProcessorError


__all__ = ["MunkiPkginfoMerger"]


class MunkiPkginfoMerger(Processor):
    """Merges two pkginfo dictionaries."""
    input_variables = {
        "pkginfo": {
            "required": False,
            "description": "Dictionary of Munki pkginfo.",
        },
        "additional_pkginfo": {
            "required": True,
            "description": ("Dictionary containing additional Munki pkginfo. "
                "This will be added to or replace keys in the pkginfo."),
        },
        
    }
    output_variables = {
        "pkginfo": {
            "description": "Merged pkginfo.",
        },
    }
    description = __doc__
    
    def main(self):
        if "pkginfo" not in self.env:
            self.env["pkginfo"] = {}
            
        for key in self.env["additional_pkginfo"].keys():
            self.env["pkginfo"][key] = self.env["additional_pkginfo"][key]
        self.output("Merged %s into pkginfo" % self.env["additional_pkginfo"])

if __name__ == "__main__":
    processor = MunkiPkginfoMerger()
    processor.execute_shell()

########NEW FILE########
__FILENAME__ = PathDeleter
#!/usr/bin/env python
#
# Copyright 2013 Greg Neagle
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from autopkglib import Processor, ProcessorError
import shutil
import os


__all__ = ["PathDeleter"]


class PathDeleter(Processor):
    """Deletes file paths."""
    input_variables = {
        "path_list": {
            "required": True,
            "description": 
                "List of pathnames to be deleted",
        },
    }
    output_variables = {
    }
    description = __doc__
    
    def main(self):
        for path in self.env["path_list"]:
            try:
                if os.path.isfile(path) or os.path.islink(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                elif not os.path.exists(path):
                    raise ProcessorError(
                        "Could not remove %s - it does not exist!" % path)
                else:
                    raise ProcessorError(
                        "Could not remove %s - it is not a file, link, "
                        "or directory" % path)
                self.output("Deleted %s" % path)
            except OSError, err:
                raise ProcessorError(
                    "Could not remove %s: %s" % (path, err))


if __name__ == "__main__":
    processor = PathDeleter()
    processor.execute_shell()

########NEW FILE########
__FILENAME__ = PkgCopier
#!/usr/bin/env python
#
# Copyright 2013 Greg Neagle
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os.path
import shutil
import glob

from autopkglib import Processor, ProcessorError
from Copier import Copier


__all__ = ["PkgCopier"]


class PkgCopier(Copier):
    description = "Copies source_pkg to pkg_path."
    input_variables = {
        "source_pkg": {
            "required": True,
            "description": ("Path to a pkg to copy. Can point to a path inside "
            "a .dmg which will be mounted. This path may also contain basic "
            "globbing characters such as the wildcard '*', but only the first "
            "result will be returned."),
        },
        "pkg_path": {
            "required": False,
            "description": 
                ("Path to destination. Defaults to "
                "RECIPE_CACHE_DIR/os.path.basename(source_pkg)"),
        },
    }
    output_variables = {
        "pkg_path": {
            "description": "Path to copied pkg.",
        },
    }

    __doc__ = description
    
    def main(self):
        # Check if we're trying to copy something inside a dmg.
        (dmg_path, dmg,
         dmg_source_path) = self.env['source_pkg'].partition(".dmg/")
        dmg_path += ".dmg"
        try:
            if dmg:
                # Mount dmg and copy path inside.
                mount_point = self.mount(dmg_path)
                source_pkg = os.path.join(mount_point, dmg_source_path)
            else:
                # Straight copy from file system.
                source_pkg = self.env["source_pkg"]


            # Prcess the path for globs
            matches = glob.glob(source_pkg)
            matched_source_path = matches[0]
            if len(matches) > 1:
                self.output("WARNING: Multiple paths match 'source_pkg' glob '%s':"
                    % source_pkg)
                for match in matches:
                    self.output("  - %s" % match)

            if [c for c in '*?[]!' if c in source_pkg]:
                self.output("Using path '%s' matched from globbed '%s'."
                    % (matched_source_path, source_pkg))

            # do the copy
            pkg_path = (self.env.get("pkg_path") or 
                os.path.join(self.env['RECIPE_CACHE_DIR'],
                             os.path.basename(source_pkg)))
            self.copy(matched_source_path, pkg_path, overwrite=True)
            self.env["pkg_path"] = pkg_path
            
        finally:
            if dmg:
                self.unmount(dmg_path)
    

if __name__ == '__main__':
    processor = Copier()
    processor.execute_shell()

########NEW FILE########
__FILENAME__ = PkgCreator
#!/usr/bin/env python
#
# Copyright 2010 Per Olofsson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os.path
import socket
import FoundationPlist
import subprocess
import xml.etree.ElementTree as ET

from autopkglib import Processor, ProcessorError


AUTO_PKG_SOCKET = "/var/run/autopkgserver"


__all__ = ["PkgCreator"]


class PkgCreator(Processor):
    description = "Calls autopkgserver to create a package."
    input_variables = {
        "pkg_request": {
            "required": True,
            "description": ("A package request dictionary. See "
                            "Code/autopkgserver/autopkgserver for more details.")
        },
        "force_pkg_build": {
            "required": False,
            "description": ("When set, this forces building a new package even if "
                            "a package already exists in the output directory with "
                            "the same identifier and version number. Defaults to "
                            "False."),
        },
    }
    output_variables = {
        "pkg_path": {
            "description": "The created package.",
        },
        "new_package_request": {
            "description": ("True if a new package was actually requested to be built. "
                            "False if a package with the same filename, identifier and "
                            "version already exists and thus no package was built (see "
                            "'force_pkg_build' input variable.")
        },
    }
    
    __doc__ = description
    
    def find_path_for_relpath(self, relpath):
        '''Searches for the relative path.
        Search order is:
            RECIPE_CACHE_DIR
            RECIPE_DIR
            PARENT_RECIPE directories'''
        cache_dir = self.env.get('RECIPE_CACHE_DIR')
        recipe_dir = self.env.get('RECIPE_DIR')
        search_dirs = [cache_dir, recipe_dir]
        if self.env.get("PARENT_RECIPES"):
            # also look in the directories containing the parent recipes
            parent_recipe_dirs = list(set([
                os.path.dirname(item)
                for item in self.env["PARENT_RECIPES"]]))
            search_dirs.extend(parent_recipe_dirs)
        for directory in search_dirs:
            test_item = os.path.join(directory, relpath)
            if os.path.exists(test_item):
                return os.path.normpath(test_item)

        raise ProcessorError("Can't find %s" % relpath)
    
    def xarExpand(self, source_path):
        try:
            xarcmd = ["/usr/bin/xar",
                      "-x",
                      "-C", self.env.get('RECIPE_CACHE_DIR'),
                      "-f", source_path,
                      "PackageInfo"]
            p = subprocess.Popen(xarcmd,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            (out, err) = p.communicate()
        except OSError as e:
            raise ProcessorError("xar execution failed with error code %d: %s" 
                % (e.errno, e.strerror))
        if p.returncode != 0:
            raise ProcessorError("extraction of %s with xar failed: %s" 
                % (source_path, err))

    
    def package(self):
        request = self.env["pkg_request"]
        if not 'pkgdir' in request:
            request['pkgdir'] = self.env['RECIPE_CACHE_DIR']
        
        # Set variables, and check that all keys are in request.
        for key in ("pkgroot",
                    "pkgname",
                    "pkgtype",
                    "id",
                    "version",
                    "infofile",
                    "resources",
                    "options",
                    "scripts"):
            if not key in request:
                if key in self.env:
                    request[key] = self.env[key]
                elif key in ["infofile", "resources", "options", "scripts"]:
                    # these keys are optional, so empty string value is OK
                    request[key] = ""
                elif key == "pkgtype":
                    # we only support flat packages now
                    request[key] = "flat"
                else:
                    raise ProcessorError("Request key %s missing" % key)
        
        # Make sure chown dict is present.
        if not "chown" in request:
            request["chown"] = dict()
        
        # Convert relative paths to absolute.
        for key, value in request.items():
            if key in ("pkgroot", "pkgdir", "infofile", "resources", "scripts"):
                if value and not value.startswith("/"):
                    # search for it
                    request[key] = self.find_path_for_relpath(value)
        
        # Check for an existing flat package in the output dir and compare its
        # identifier and version to the one we're going to build.
        pkg_path = os.path.join(request['pkgdir'], request['pkgname'] + '.pkg')
        if os.path.exists(pkg_path) and not self.env.get("force_pkg_build"):
            self.output("Package already exists at path %s." % pkg_path)
            self.xarExpand(pkg_path)
            packageinfo_file = os.path.join(self.env['RECIPE_CACHE_DIR'], 'PackageInfo')
            if not os.path.exists(packageinfo_file):
                raise ProcessorError(
                    "Failed to parse existing package, as no PackageInfo "
                    "file count be found in the extracted archive.")
                
            tree = ET.parse(packageinfo_file)
            root = tree.getroot()
            local_version = root.attrib['version']
            local_id = root.attrib['identifier']

            if (local_version == request['version']) and (local_id == request['id']):
                    self.output("Existing package matches version and identifier, not building.")
                    self.env["pkg_path"] = pkg_path
                    self.env["new_package_request"] = False
                    return
        
        # Send packaging request.
        try:
            self.output("Connecting")
            self.connect()
            self.output("Sending packaging request")
            self.env["new_package_request"] = True
            pkg_path = self.send_request(request)
        finally:
            self.output("Disconnecting")
            self.disconnect()
        
        # Return path to pkg.
        self.env["pkg_path"] = pkg_path
    
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket.connect(AUTO_PKG_SOCKET)
        except socket.error as e:
            raise ProcessorError("Couldn't connect to autopkgserver: %s" % e.strerror)
    
    def send_request(self, request):
        self.socket.send(FoundationPlist.writePlistToString(request))
        with os.fdopen(self.socket.fileno()) as f:
            reply = f.read()
        
        if reply.startswith("OK:"):
            return reply.replace("OK:", "").rstrip()
        
        errors = reply.rstrip().split("\n")
        if not errors:
            errors = ["ERROR:No reply from server (crash?), check system logs"]
        raise ProcessorError(", ".join([s.replace("ERROR:", "") for s in errors]))
    
    def disconnect(self):
        self.socket.close()
        
    def main(self):
        self.package()
    

if __name__ == '__main__':
    processor = PkgCreator()
    processor.execute_shell()
    

########NEW FILE########
__FILENAME__ = PkgExtractor
#!/usr/bin/env python
#
# Copyright 2013 Greg Neagle
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import FoundationPlist
import tempfile
import shutil
import subprocess

from autopkglib.DmgMounter import DmgMounter
from autopkglib import Processor, ProcessorError


__all__ = ["PkgExtractor"]


class PkgExtractor(DmgMounter):
    description = ("Extracts the contents of a bundle-style pkg (possibly on a disk image) to pkgroot.")
    input_variables = {
        "pkg_path": {
            "required": True,
            "description": 
                "Path to a package.",
        },
        "extract_root": {
            "required": True,
            "description": 
                "Path to where the new package root will be created.",
        },
    }
    output_variables = {
    }
    __doc__ = description

    def extract_payload(self, pkg_path, extract_root):
        '''Extract package contents to extract_root, preserving intended
         directory structure'''
        info_plist = os.path.join(pkg_path, "Contents/Info.plist")
        archive_path = os.path.join(pkg_path, "Contents/Archive.pax.gz")
        if not os.path.exists(info_plist):
            raise ProcessorError("Info.plist not found in pkg")
        if not os.path.exists(archive_path):
            raise ProcessorError("Archive.pax.gz not found in pkg")
            
        if os.path.exists(extract_root):
            try:
                shutil.rmtree(extract_root)
            except (OSError, IOError), err:
                raise ProcessorError("Failed to remove extract_root: %s" % err)

        try:
            info = FoundationPlist.readPlist(info_plist)
        except FoundationPlist.FoundationPlistException, err:
            raise ProcessorError("Failed to read Info.plist: %s" % err)
            
        install_target = info.get("IFPkgFlagDefaultLocation", "/").lstrip("/")
        extract_path = os.path.join(extract_root, install_target)
        try:
            os.makedirs(extract_path, 0755)
        except (OSError, IOError), err:
            raise ProcessorError("Failed to create extract_path: %s" % err)
        
        # Unpack payload.
        try:
            p = subprocess.Popen(("/usr/bin/ditto",
                                  "-x",
                                  "-z",
                                  archive_path,
                                  extract_path),
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
            (out, err) = p.communicate()
        except OSError as err:
            raise ProcessorError(
                "ditto execution failed with error code %d: %s" 
                % (err.errno, err.strerror))
        if p.returncode != 0:
            raise ProcessorError("Unpacking payload failed: %s" % err)

    def main(self):
        # Check if we're trying to read something inside a dmg.
        (dmg_path, dmg, dmg_source_path) = self.env[
            'pkg_path'].partition(".dmg/")
        dmg_path += ".dmg"
        try:
            if dmg:
                # Mount dmg and copy path inside.
                mount_point = self.mount(dmg_path)
                pkg_path = os.path.join(mount_point, dmg_source_path)
            else:
                # just use the given path
                pkg_path = self.env['pkg_path']
            self.extract_payload(pkg_path, self.env["extract_root"])
            
        finally:
            if dmg:
                self.unmount(dmg_path)

if __name__ == '__main__':
    processor = PkgExtractor()
    processor.execute_shell()
########NEW FILE########
__FILENAME__ = PkgInfoCreator
#!/usr/bin/env python
#
# Copyright 2010 Per Olofsson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os.path
import subprocess
import FoundationPlist
import math
from xml.etree import ElementTree

from autopkglib import Processor, ProcessorError


__all__ = ["PkgInfoCreator"]


class PkgInfoCreator(Processor):
    description = "Creates an Info.plist file for a package."
    input_variables = {
        "template_path": {
            "required": True,
            "description": "An Info.plist template.",
        },
        "version": {
            "required": True,
            "description": "Version of the package.",
        },
        "pkgroot": {
            "required": True,
            "description": "Virtual root of the package.",
        },
        "infofile": {
            "required": True,
            "description": "Path to the info file to create.",
        },
        "pkgtype": {
            "required": True,
            "description": "'flat' or 'bundle'."
        }
    }
    output_variables = {
    }
    
    __doc__ = description
    
    
    def find_template(self):
        '''Searches for the template, looking in the recipe directory
        and parent recipe directories if needed.'''
        template_path = self.env['template_path']
        if os.path.exists(template_path):
            return template_path
        elif not template_path.startswith("/"):
            recipe_dir = self.env.get('RECIPE_DIR')
            search_dirs = [recipe_dir]
            if self.env.get("PARENT_RECIPES"):
                # also look in the directories containing the parent recipes
                parent_recipe_dirs = list(set([
                    os.path.dirname(item) 
                    for item in self.env["PARENT_RECIPES"]]))
                search_dirs.extend(parent_recipe_dirs)
            for directory in search_dirs:
                test_item = os.path.join(directory, template_path)
                if os.path.exists(test_item):
                    return test_item
        raise ProcessorError("Can't find %s" % template_path)
    
    def main(self):
        if self.env['pkgtype'] not in ("bundle", "flat"):
            raise ProcessorError("Unknown pkgtype %s" % self.env['pkgtype'])
        template = self.load_template(self.find_template(), self.env['pkgtype'])
        if self.env['pkgtype'] == "bundle":
            self.create_bundle_info(template)
        else:
            self.create_flat_info(template)
    
    restartaction_to_postinstallaction = {
        "None": "none",
        "RecommendRestart": "restart",
        "RequireLogout": "logout",
        "RequireRestart": "restart",
        "RequireShutdown": "shutdown",
    }
    def convert_bundle_info_to_flat(self, info):
        pkg_info = ElementTree.Element("pkg-info")
        pkg_info.set("format-version", "2")
        for bundle, flat in (("IFPkgFlagDefaultLocation", "install-location"),
                             ("CFBundleShortVersionString", "version"),
                             ("CFBundleIdentifier", "identifier")):
            if bundle in info:
                pkg_info.set(flat, info[bundle])
        if "IFPkgFlagAuthorizationAction" in info:
            if info["IFPkgFlagAuthorizationAction"] == "RootAuthorization":
                pkg_info.set("auth", "root")
            else:
                pkg_info.set("auth", "none")
        if "IFPkgFlagRestartAction" in info:
            pkg_info.set("postinstall-action",
                self.restartaction_to_postinstallaction[info["IFPkgFlagRestartAction"]])
        
        payload = ElementTree.SubElement(pkg_info, "payload")
        if "IFPkgFlagInstalledSize" in info:
            payload.set("installKBytes", str(info["IFPkgFlagInstalledSize"]))
        
        return ElementTree.ElementTree(pkg_info)
    
    postinstallaction_to_restartaction = {
        "none": "None",
        "logout": "RequireLogout",
        "restart": "RequireRestart",
        "shutdown": "RequireShutdown",
    }
    def convert_flat_info_to_bundle(self, info):
        info = {
            #"CFBundleIdentifier": "com.adobe.pkg.FlashPlayer",
            "IFPkgFlagAllowBackRev": False,
            #"IFPkgFlagAuthorizationAction": "RootAuthorization",
            #"IFPkgFlagDefaultLocation": "/",
            "IFPkgFlagFollowLinks": True,
            "IFPkgFlagInstallFat": False,
            "IFPkgFlagIsRequired": False,
            "IFPkgFlagOverwritePermissions": False,
            "IFPkgFlagRelocatable": False,
            #"IFPkgFlagRestartAction": "None",
            "IFPkgFlagRootVolumeOnly": False,
            "IFPkgFlagUpdateInstalledLanguages": False,
            "IFPkgFormatVersion": 0.1,
        }
        
        pkg_info = info.getroot()
        if pkg_info.tag != "pkg-info":
            raise ProcessorError("PackageInfo template root isn't pkg-info")
        
        info["CFBundleShortVersionString"] = pkg_info.get("version", "")
        info["CFBundleIdentifier"] = pkg_info.get("identifier", "")
        info["IFPkgFlagDefaultLocation"] = pkg_info.get("install-location", "")
        if pkg_info.get("auth") == "root":
            info["IFPkgFlagAuthorizationAction"] = "RootAuthorization"
        else:
            raise ProcessorError("Don't know how to convert auth=%s to Info.plist format" % pkg_info.get("auth"))
        info["IFPkgFlagRestartAction"] = \
            self.postinstallaction_to_restartaction[pkg_info.get("postinstall-action", "none")]
        
        payload = ElementTree.SubElement(pkg_info, "payload")
        info["IFPkgFlagInstalledSize"] = payload.get("installKBytes", 0)
        
        return info
    
    def load_template(self, template_path, template_type):
        """Load a package info template in Info.plist or PackageInfo format."""
        
        if template_path.endswith(".plist"):
            # Try to load Info.plist in bundle format.
            try:
                info = FoundationPlist.readPlist(self.env['template_path'])
            except BaseException as e:
                raise ProcessorError("Malformed Info.plist template %s" % self.env['template_path'])
            if template_type == "bundle":
                return info
            else:
                return self.convert_bundle_info_to_flat(info)
        else:
            # Try to load PackageInfo in flat format.
            try:
                info = ElementTree.parse(template_path)
            except BaseException as e:
                raise ProcessorError("Malformed PackageInfo template %s" % self.env['template_path'])
            if template_type == "flat":
                return info
            else:
                return self.convert_flat_info_to_bundle(info)
    
    def get_pkgroot_size(self, pkgroot):
        """Return the size of pkgroot (in kilobytes) and the number of files."""
        
        size = 0
        nfiles = 0
        for (dirpath, dirnames, filenames) in os.walk(pkgroot):
            # Count the current directory and the number of files in it.
            nfiles += 1 + len(filenames)
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                # Add up file size rounded up to the nearest 4 kB, which
                # appears to match what du -sk returns, and what PackageMaker
                # uses.
                size += int(math.ceil(float(os.lstat(path).st_size) / 4096.0))
        
        return (size, nfiles)
    
    def create_flat_info(self, template):
        info = template
        
        pkg_info = info.getroot()
        if pkg_info.tag != "pkg-info":
            raise ProcessorError("PackageInfo root should be pkg-info")
        
        pkg_info.set("version", self.env['version'])
        
        payload = pkg_info.find("payload")
        if payload is None:
            payload = ElementTree.SubElement(pkg_info, "payload")
        size, nfiles = self.get_pkgroot_size(self.env['pkgroot'])
        payload.set("installKBytes", str(size))
        payload.set("numberOfFiles", str(nfiles))
        
        info.write(self.env['infofile'])

    
    def create_bundle_info(self, template):
        info = template
        
        info["CFBundleShortVersionString"] = self.env['version']
        ver = self.env['version'].split(".")
        info["IFMajorVersion"] = ver[0]
        info["IFMinorVersion"] = ver[1]
        
        size, nfiles = self.get_pkgroot_size(self.env['pkgroot'])
        info["IFPkgFlagInstalledSize"] = size
        
        try:
            FoundationPlist.writePlist(info, self.env['infofile'])
        except BaseException as e:
            raise ProcessorError("Couldn't write %s: %s" % (self.env['infofile'], e))
    

if __name__ == '__main__':
    processor = PkgInfoCreator()
    processor.execute_shell()
    

########NEW FILE########
__FILENAME__ = PkgPayloadUnpacker
#!/usr/bin/env python
#
# Copyright 2013 Greg Neagle
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import shutil
import subprocess

from autopkglib import Processor, ProcessorError


__all__ = ["PkgPayloadUnpacker"]


class PkgPayloadUnpacker(Processor):
    """Unpacks a package payload."""
    input_variables = {
        "pkg_payload_path": {
            "required": True,
            "description": 
                ("Path to a payload from an expanded flat package or "
                 "Archive.pax.gz in a bundle package."),
        },
        "destination_path": {
            "required": True,
            "description": "Destination directory.",
        },
        "purge_destination": {
            "required": False,
            "description": 
                ("Whether the contents of the destination directory will "
                "be removed before unpacking."),
        },
    }
    output_variables = {
    }
    description = __doc__
    
    def unpackPkgPayload(self):
        """Uses ditto to unpack a package payload into destination_path"""
        # Create the destination directory if needed.
        if not os.path.exists(self.env['destination_path']):
            try:
                os.mkdir(self.env['destination_path'])
            except OSError as err:
                raise ProcessorError(
                    "Can't create %s: %s" 
                    % (self.env['destination_path'], err.strerror))
        elif self.env.get('purge_destination'):
            for entry in os.listdir(self.env['destination_path']):
                path = os.path.join(self.env['destination_path'], entry)
                try:
                    if os.path.isdir(path) and not os.path.islink(path):
                        shutil.rmtree(path)
                    else:
                        os.unlink(path)
                except OSError as err:
                    raise ProcessorError(
                        "Can't remove %s: %s" % (path, err.strerror))

        try:
            dittocmd = ["/usr/bin/ditto",
                        "-x",
                        "-z",
                        self.env["pkg_payload_path"],
                        self.env["destination_path"]]
            proc = subprocess.Popen(dittocmd,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            (unused_out, err_out) = proc.communicate()
        except OSError as err:
            raise ProcessorError(
                "ditto execution failed with error code %d: %s" 
                % (err.errno, err.strerror))
        if proc.returncode != 0:
            raise ProcessorError(
                "extraction of %s with ditto failed: %s" 
                % (self.env['pkg_payload_path'], err_out))
        self.output("Unpacked %s to %s" 
            % (self.env["pkg_payload_path"], self.env["destination_path"]))
    
    def main(self):
        self.unpackPkgPayload()


if __name__ == "__main__":
    processor = PkgPayloadUnpacker()
    processor.execute_shell()

########NEW FILE########
__FILENAME__ = PkgRootCreator
#!/usr/bin/env python
#
# Copyright 2010 Per Olofsson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os.path
import shutil

from autopkglib import Processor, ProcessorError


__all__ = ["PkgRootCreator"]


# Download URLs in chunks of 256 kB.
CHUNK_SIZE = 256 * 1024


class PkgRootCreator(Processor):
    description = "Creates a package root and a directory structure."
    input_variables = {
        "pkgroot": {
            "required": True,
            "description": "Path to where the package root will be created.",
        },
        "pkgdirs": {
            "required": True,
            "description": ("A dictionary of directories to be created "
                "inside the pkgroot, with their modes in octal form."),
        }
    }
    output_variables = {
    }
    
    __doc__ = description
    
    def main(self):
        # Delete pkgroot if it exists.
        try:
            if (os.path.islink(self.env['pkgroot']) or 
                os.path.isfile(self.env['pkgroot'])):
                os.unlink(self.env['pkgroot'])
            elif os.path.isdir(self.env['pkgroot']):
                shutil.rmtree(self.env['pkgroot'])
        except OSError as e:
            raise ProcessorError("Can't remove %s: %s" % (self.env['pkgroot'],
                                                          e.strerror))
        
        # Create pkgroot. autopkghelper sets it to root:admin 01775.
        try:
            os.makedirs(self.env['pkgroot'])
            self.output("Created %s" % self.env['pkgroot'])
        except OSError as e:
            raise ProcessorError("Can't create %s: %s" % (self.env['pkgroot'],
                                                          e.strerror))
        
        # Create directories.
        absroot = os.path.abspath(self.env['pkgroot'])
        for directory, mode in sorted(self.env['pkgdirs'].items()):
            self.output("Creating %s" % directory, verbose_level=2)
            # Make sure we don't get an absolute path.
            if directory.startswith("/"):
                raise ProcessorError("%s in pkgroot is absolute." % directory)
            dirpath = os.path.join(absroot, directory)
            
            # Make sure we're not trying to make a directory outside the 
            # pkgroot.
            abspath = os.path.abspath(dirpath)
            if os.path.commonprefix((absroot, abspath)) != absroot:
                raise ProcessorError("%s is outside pkgroot" % directory)
            
            try:
                os.mkdir(dirpath)
                os.chmod(dirpath, int(mode, 8))
                self.output("Created %s" % dirpath)
            except OSError as e:
                raise ProcessorError("Can't create %s with mode %s: %s" % (
                                      dirpath, mode, e.strerror))
    

if __name__ == '__main__':
    processor = PkgRootCreator()
    processor.execute_shell()
    

########NEW FILE########
__FILENAME__ = PlistEditor
#!/usr/bin/env python
#
# Copyright 2013 Greg Neagle
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from autopkglib import Processor, ProcessorError
import FoundationPlist


__all__ = ["PlistEditor"]


class PlistEditor(Processor):
    description = ("Merges data with an input plist (which can be empty) "
                   "and writes a new plist.")
    input_variables = {
        "input_plist_path": {
            "required": False,
            "description": 
                ("File path to a plist; empty or undefined to start with "
                 "an empty plist."),
        },
        "output_plist_path": {
            "required": True,
            "description": 
                "File path to a plist. Can be the same path as input_plist.",
        },
        "plist_data": {
            "required": True,
            "description":
                ("A dictionary of data to be merged with the data from the "
                 "input plist."),
        }, 
    }
    output_variables = {
    }
    
    __doc__ = description
    
    def readPlist(self, pathname):
        if not pathname:
            return {}
        try:
            return FoundationPlist.readPlist(pathname)
        except Exception, err:
            raise ProcessorError(
                'Could not read %s: %s' % (pathname, err))
        
    def writePlist(self, data, pathname):
        try:
            FoundationPlist.writePlist(data, pathname)
        except Exception, err:
            raise ProcessorError(
                'Could not write %s: %s' % (pathname, err))
        
    def main(self):
        # read original plist (or empty plist)
        working_plist = self.readPlist(self.env.get("input_plist_path"))
        
        # insert new data
        plist_data = self.env["plist_data"]
        for key in plist_data.keys():
            working_plist[key] = plist_data[key]
            
        # write changed plist
        self.writePlist(working_plist, self.env["output_plist_path"])
        self.output("Updated plist at %s" % self.env["output_plist_path"])

if __name__ == '__main__':
    processor = PlistEditor()
    processor.execute_shell()

########NEW FILE########
__FILENAME__ = PlistReader
#!/usr/bin/env python
#
# Copyright 2013 Shea Craig
# Mostly just reworked code from Per Olofsson/AppDmgVersioner.py and
# Greg Neagle/Versioner.py
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os.path
import glob
import FoundationPlist

from DmgMounter import DmgMounter
from autopkglib import Processor, ProcessorError


__all__ = ["PlistReader"]


class PlistReader(DmgMounter):
    description = ("Extracts values from top-level keys in a plist file, and "
                   "assigns to arbitrary output variables. This behavior is "
                   "different from other processors that pre-define all their "
                   "possible output variables. As it is often used for versioning, "
                   "it defaults to extracting 'CFBundleShortVersionString' to "
                   "'version'. This can be used as a replacement for both the "
                   "AppDmgVersioner and Versioner processors.")
    input_variables = {
        "info_path": {
            "required": True,
            "description": ("Path to a plist to be read. If a path to a bundle "
                "(ie. a .app) is given, its Info.plist will be found and used. "
                "If the path is a folder, it will be searched and the first "
                "found bundle will be used. The path can also be a .dmg, "
                "or contain a .dmg file and the file will be mounted."),
        },
        "plist_keys": {
            "required": False,
            "description": ("Dictionary of plist values to query. Key names "
                            "should match a top-level key to read. Values "
                            "should be the desired output variable name. "
                            "Defaults to: ",
                            "{'CFBundleShortVersionString': 'version'}")
        },
    }
    output_variables = {
        "plist_reader_output_variables": {
            "description": ("Output variables per 'plist_keys' supplied as "
             "input. Note that this output variable is used as both a "
             "placeholder for documentation and for auditing purposes. "
             "One should use the actual named output variables as given "
             "as values to 'plist_keys' to refer to the output of this "
             "processor.")
        },
    }

    __doc__ = description

    def find_bundle(self, path):
        """Returns the first bundle that is found within the top level
        of 'path', or None."""
        files = glob.glob(os.path.join(path, "*"))
        if len(files) == 0:
            raise ProcessorError("No bundle found in dmg")

        # filter out any symlinks that don't have extensions
        # - common case is a symlink to 'Applications', which
        #   we don't want to exhaustively search
        filtered = [f for f in files if \
                    not os.path.islink(f) and \
                    not os.path.splitext(os.path.basename(f))[1]]

        for test_bundle in files:
            return self.get_bundle_info_path(test_bundle)
        return None


    def get_bundle_info_path(self, path):
        """Return full path to an Info.plist if 'path' is actually a bundle,
        otherwise None."""
        bundle_info_path = None
        if os.path.isdir(path):
            test_info_path = os.path.join(path, 'Contents/Info.plist')
            if os.path.exists(test_info_path):
                try:
                    plist = FoundationPlist.readPlist(test_info_path)
                except (FoundationPlist.NSPropertyListSerializationException,
                        UnicodeEncodeError), err:
                    raise ProcessorError(
                        "File %s looks like a bundle, but its 'Contents/Info.plist' ",
                        "file cannot be parsed." % path)
                bundle_info_path = test_info_path
        return bundle_info_path


    def main(self):
        keys = self.env.get('plist_keys', {"CFBundleShortVersionString": "version"})

        # Many types of paths are accepted. Figure out which kind we have.
        path = os.path.normpath(self.env['info_path'])

        try:
            # Wrap all other actions in a try/finally so if we mount an image,
            # it will always be unmounted.

            # Check if we're trying to read something inside a dmg.
            if '.dmg' in path:
                (dmg_path, dmg, dmg_source_path) = path.partition(".dmg")
                dmg_path += ".dmg"

                mount_point = self.mount(dmg_path)
                path = os.path.join(mount_point, dmg_source_path.lstrip('/'))
            else:
                dmg = False

            # Finally check whether this is at least a valid path
            if not os.path.exists(path):
                raise ProcessorError("Path '%s' doesn't exist!" % path)

            # Is the path a bundle?
            info_plist_path = self.get_bundle_info_path(path)
            if info_plist_path:
                path = info_plist_path

            # Does it have a 'plist' extension (naively assuming 'plist' only names, for now)
            elif path.endswith('.plist'):
                # Full path to a plist was supplied, move on.
                pass

            # Might the path contain a bundle at its root?
            else:
                path = self.find_bundle(path)

            # Try to read the plist
            self.output("Reading: %s" % path)
            try:
                info = FoundationPlist.readPlist(path)
            except (FoundationPlist.NSPropertyListSerializationException,
                    UnicodeEncodeError) as err:
                raise ProcessorError(err)

            # Copy each plist_keys' values and assign to new env variables
            self.env["plist_reader_output_variables"] = {}
            for key, val in keys.items():
                try:
                    self.env[val] = info[key]
                    self.output("Assigning value of '%s' to output variable '%s'" % (self.env[val], val))
                    # This one is for documentation/recordkeeping
                    self.env["plist_reader_output_variables"][val] = self.env[val]
                except KeyError:
                    raise ProcessorError(
                        "Key '%s' could not be found in the plist %s!" % (key, path))

        finally:
            if dmg:
                self.unmount(dmg_path)


if __name__ == '__main__':
    processor = PlistReader()
    processor.execute_shell()

########NEW FILE########
__FILENAME__ = SparkleUpdateInfoProvider
#!/usr/bin/env python
#
# Copyright 2013 Timothy Sutton
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import urllib
import urllib2
import urlparse
import os
from xml.etree import ElementTree

from autopkglib import Processor, ProcessorError
from distutils.version import LooseVersion
from operator import itemgetter

__all__ = ["SparkleUpdateInfoProvider"]

DEFAULT_XMLNS = "http://www.andymatuschak.org/xml-namespaces/sparkle"
SUPPORTED_ADDITIONAL_PKGINFO_KEYS = ["description",
                                     "minimum_os_version"
                                     ]


class SparkleUpdateInfoProvider(Processor):
    description = "Provides URL to the highest version number or latest update."
    input_variables = {
        "appcast_url": {
            "required": True,
            "description": "URL for a Sparkle Appcast feed xml.",
        },
        "appcast_request_headers": {
            "required": False,
            "description": "Dictionary of additional HTTP headers to include in request.",
        },
        "appcast_query_pairs": {
            "required": False,
            "description": ("Dictionary of additional query pairs to include in request. "
                            "Manual url-encoding isn't necessary."),
        },
        "alternate_xmlns_url": {
            "required": False,
            "description": ("Alternate URL for the XML namespace, if the appcast is using "
                            "an alternate one. Defaults to that used for 'vanilla' Sparkle "
                            "appcasts."),
        },
        "pkginfo_keys_to_copy_from_sparkle_feed": {
            "required": False,
            "description": ("Array of pkginfo keys that will be derived from any available "
                            "metadata from the Sparkle feed and copied to 'additional_pkginfo'. "
                            "The usefulness of these keys will depend on the admin's environment "
                            "and the nature of the metadata provided by the application vendor. "
                            "Note that the 'description' is usually equivalent to 'release notes' "
                            "for that specific version. Defaults to ['minimum_os_version']. "
                            "Currently supported keys: %s." %
                            ", ".join(SUPPORTED_ADDITIONAL_PKGINFO_KEYS))
        }
    }
    output_variables = {
        "url": {
            "description": "URL for a download.",
        },
        "additional_pkginfo": {
            "description": ("A pkginfo containing additional keys extracted from the "
                            "appcast feed. Currently this is 'description' and "
                            "'minimum_os_version' if it was defined in the feed.")
        }
    }

    __doc__ = description

    def get_feed_data(self, url):
        """Returns an array of dicts, one per update item, structured like:
        version: 1234
        human_version: 1.2.3.4 (optional)
        url: http://download/url.dmg
        minimum_os_version: 10.7 (optional)
        description_data: HTML description for update (optional)
        description_url: URL given by the sparkle:releaseNotesLink element (optional)

        Note: Descriptions may be either given as a URL (usually the case) or as raw HTML.
        We store one or the other rather than doing many GETs for metadata we're never going to use.
        If it's a URL, this must be handled by whoever calls this function.
        """

        # handle custom xmlns and version attributes
        if "alternate_xmlns_url" in self.env:
            xmlns = self.env["alternate_xmlns_url"]
        else:
            xmlns = DEFAULT_XMLNS

        # query string
        if "appcast_query_pairs" in self.env:
            queries = self.env["appcast_query_pairs"]
            new_query = urllib.urlencode([(k, v) for (k, v) in queries.items()])
            scheme, netloc, path, old_query, frag = urlparse.urlsplit(url)
            url = urlparse.urlunsplit((scheme, netloc, path, new_query, frag))

        request = urllib2.Request(url=url)

        # request header code borrowed from URLDownloader
        if "appcast_request_headers" in self.env:
            headers = self.env["appcast_request_headers"]
            for header, value in headers.items():
                request.add_header(header, value)

        try:
            url_handle = urllib2.urlopen(request)
        except:
            raise ProcessorError("Can't open URL %s" % request.get_full_url())

        data = url_handle.read()
        try:
            xmldata = ElementTree.fromstring(data)
        except:
            raise ProcessorError("Error parsing XML from appcast feed.")

        items = xmldata.findall("channel/item")

        versions = []
        for item_elem in items:
            enclosure = item_elem.find("enclosure")
            if enclosure is not None:
                item = {}
                # URL-quote the path component to handle spaces, etc. (Panic apps do this)
                url_bits = urlparse.urlsplit(enclosure.get("url"))
                encoded_path = urllib.quote(url_bits.path)
                built_url = url_bits.scheme + "://" + url_bits.netloc + encoded_path
                if url_bits.query:
                    built_url += "?" + url_bits.query
                item["url"] = built_url

                item["version"] = enclosure.get("{%s}version" % xmlns)
                if item["version"] is None:
                    # Sparkle tries to guess a version from the download URL for rare cases
                    # where there is no sparkle:version enclosure attribute, for the format:
                    # AppnameOrAnythingReally_1.2.3.zip
                    # https://github.com/andymatuschak/Sparkle/blob/master/SUAppcastItem.m#L153-L167
                    #
                    # We can even support OmniGroup's alternate appcast format by cheating
                    # and using the '-' as a delimiter to derive version info
                    filename = os.path.basename(os.path.splitext(item["url"])[0])
                    for delimiter in ['_', '-']:
                        if delimiter in filename:
                            item["version"] = filename.split(delimiter)[-1]
                            break
                # if we still found nothing, fail
                if item["version"] is None:
                    raise ProcessorError("Can't extract version info from item in feed!")

                human_version = item_elem.find("{%s}shortVersionString")
                if human_version is not None:
                    item["human_version"] = human_version
                min_version = item_elem.find("{%s}minimumSystemVersion" % xmlns)
                if min_version is not None:
                    item["minimum_os_version"] = min_version.text
                description_elem = item_elem.find("{%s}releaseNotesLink" % xmlns)
                if description_elem is not None:
                    item["description_url"] = description_elem.text
                if item_elem.find("description") is not None:
                    item["description_data"] = item_elem.find("description").text
                versions.append(item)

        return versions

    def main(self):
        def compare_version(a, b):
            return cmp(LooseVersion(a), LooseVersion(b))

        items = self.get_feed_data(self.env.get("appcast_url"))
        sorted_items = sorted(items,
                              key=itemgetter("version"),
                              cmp=compare_version)
        latest = sorted_items[-1]
        self.output("Version retrieved from appcast: %s" % latest["version"])
        if latest.get("human_version"):
            self.output("User-facing version retrieved from appcast: %s" % latest["human_version"])

        pkginfo = {}
        # Handle any keys we may have defined
        sparkle_pkginfo_keys = self.env.get("pkginfo_keys_to_copy_from_sparkle_feed")
        if sparkle_pkginfo_keys:
            for k in sparkle_pkginfo_keys:
                if k not in SUPPORTED_ADDITIONAL_PKGINFO_KEYS:
                    self.output("Key %s isn't a supported key to copy from the "
                                "Sparkle feed, ignoring it." % k)
            # Format description
            if "description" in sparkle_pkginfo_keys:
                if "description_url" in latest.keys():
                    description = urllib2.urlopen(latest["description_url"]).read()
                elif "description_data" in latest.keys():
                    description = "<html><body>" + latest["description_data"] + "</html></body>"
                else:
                    description = ""
                pkginfo["description"] = description = description.decode("UTF-8")

            if "minimum_os_version" in sparkle_pkginfo_keys:
                if latest.get("minimum_os_version") is not None:
                    pkginfo["minimum_os_version"] = latest.get("minimum_os_version")
            for copied_key in pkginfo.keys():
                self.output("Copied key %s from Sparkle feed to additional pkginfo." %
                            copied_key)

        self.env["url"] = latest["url"]
        self.output("Found URL %s" % self.env["url"])
        self.env["additional_pkginfo"] = pkginfo

if __name__ == "__main__":
    processor = SparkleUpdateInfoProvider()
    processor.execute_shell()

########NEW FILE########
__FILENAME__ = StopProcessingIf
#!/usr/bin/env python
#
# Copyright 2013 Greg Neagle
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from autopkglib import Processor, ProcessorError

from Foundation import NSPredicate

__all__ = ["StopProcessingIf"]


class StopProcessingIf(Processor):
    """Sets a variable to tell AutoPackager to stop processing a recipe if a
       predicate comparison evaluates to true."""
    input_variables = {
        "predicate": {
            "required": True,
            "description": 
                ("NSPredicate-style comparison against an environment key. See "
                 "http://developer.apple.com/library/mac/#documentation/"
                 "Cocoa/Conceptual/Predicates/Articles/pSyntax.html"),
        },
    }
    output_variables = {
        "stop_processing_recipe": {
            "description": "Boolean. Should we stop processing the recipe?",
        },
    }
    description = __doc__
    
    def predicateEvaluatesAsTrue(self, predicate_string):
        '''Evaluates predicate against our environment dictionary'''
        try:
            predicate = NSPredicate.predicateWithFormat_(predicate_string)
        except Exception, err:
            raise ProcessorError(
                "Predicate error for '%s': %s" 
                % (predicate_string, err))

        result = predicate.evaluateWithObject_(self.env)
        self.output("(%s) is %s" % (predicate_string, result))
        return result
        
    def main(self):
        self.env["stop_processing_recipe"] = self.predicateEvaluatesAsTrue(
            self.env["predicate"])


if __name__ == '__main__':
    processor = StopProcessingIf()
    processor.execute_shell()
########NEW FILE########
__FILENAME__ = Symlinker
#!/usr/bin/env python
#
# Copyright 2013 Greg Neagle
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os

from autopkglib import Processor, ProcessorError


__all__ = ["Symlinker"]


class Symlinker(Processor):
    description = "Copies source_path to destination_path."
    input_variables = {
        "source_path": {
            "required": True,
            "description": "Path to a file or directory to symlink.",
        },
        "destination_path": {
            "required": True,
            "description": "Path to destination.",
        },
        "overwrite": {
            "required": False,
            "description": 
                "Whether the destination will be overwritten if necessary.",
        },
    }
    output_variables = {
    }
    
    __doc__ = description
    
    def main(self):
        source_path = self.env['source_path']
        destination_path  = self.env['destination_path']
        
        # Remove destination if needed.
        if os.path.exists(destination_path):
            if "overwrite" in self.env and self.env['overwrite']:
                try:
                    os.unlink(destination_path)
                except OSError as e:
                    raise ProcessorError(
                        "Can't remove %s: %s" % (destination_path, e.strerror))
            
        # Make symlink.
        try:
            os.symlink(source_path, destination_path)
            self.output("Symlinked %s to %s" 
                        % (source_path, destination_path))
        except BaseException as e:
            raise ProcessorError("Can't symlink %s to %s: %s" 
                                 % (source_path, destination_path, e))
                                     

if __name__ == '__main__':
    processor = Symlinker()
    processor.execute_shell()
    

########NEW FILE########
__FILENAME__ = Unarchiver
#!/usr/bin/env python
#
# Copyright 2010 Per Olofsson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import subprocess
import shutil

from autopkglib import Processor, ProcessorError


__all__ = ["Unarchiver"]

EXTNS = {
    'zip': ['zip'],
    'tar_gzip': ['tar.gz', 'tgz'],
    'tar_bzip2': ['tar.bz2', 'tbz'],
    'tar': ['tar']
}

class Unarchiver(Processor):
    description = "Archive decompressor for zip and common tar-compressed formats."
    input_variables = {
        "archive_path": {
            "required": False,
            "description": "Path to an archive. Defaults to contents of the 'pathname' "
                           "variable, for example as is set by URLDownloader.",
        },
        "destination_path": {
            "required": False,
            "description": ("Directory where archive will be unpacked, created if necessary. "
                           "Defaults to RECIPE_CACHE_DIR/NAME.")
        },
        "purge_destination": {
            "required": False,
            "description": "Whether the contents of the destination directory will be removed before unpacking.",
        },
        "archive_format": {
            "required": False,
            "description": ("The archive format. Currently supported: 'zip', 'tar_gzip', 'tar_bzip2'. "
                           "If omitted, the format will try to be guessed by the file extension.")
        }
    }
    output_variables = {
    }
    
    __doc__ = description
    
    def get_archive_format(self, archive_path):
        for format, extns in EXTNS.items():
            for extn in extns:
                if archive_path.endswith(extn):
                    return format
        # We found no known archive file extension if we got this far
        return None

    def main(self):
        # handle some defaults for archive_path and destination_path
        archive_path = self.env.get("archive_path", self.env.get("pathname"))
        if not archive_path:
            raise ProcessorError("Expected an 'archive_path' input variable but none is set!")
        destination_path = self.env.get("destination_path",
                    os.path.join(self.env["RECIPE_CACHE_DIR"], self.env["NAME"]))

        # Create the directory if needed.
        if not os.path.exists(destination_path):
            try:
                os.mkdir(destination_path)
            except OSError as e:
                raise ProcessorError("Can't create %s: %s" % (path, e.strerror))
        elif self.env.get('purge_destination'):
            for entry in os.listdir(destination_path):
                path = os.path.join(destination_path, entry)
                try:
                    if os.path.isdir(path) and not os.path.islink(path):
                        shutil.rmtree(path)
                    else:
                        os.unlink(path)
                except OSError as e:
                    raise ProcessorError("Can't remove %s: %s" % (path, e.strerror))
        
        fmt = self.env.get("archive_format")
        if fmt is None:
            fmt = self.get_archive_format(archive_path)
            if not fmt:
                raise ProcessorError("Can't guess archive format for filename %s" %
                        os.path.basename(archive_path))
            self.output("Guessed archive format '%s' from filename %s" %
                        (fmt, os.path.basename(archive_path)))
        elif fmt not in EXTNS.keys():
            raise ProcessorError("'%s' is not valid for the 'archive_format' variable. Must be one of %s." %
                                (fmt, ", ".join(EXTNS.keys())))

        if fmt == "zip":
            cmd = ["/usr/bin/ditto",
                   "--noqtn",
                   "-x",
                   "-k",
                   archive_path,
                   destination_path]
        elif fmt.startswith("tar"):
            cmd = ["/usr/bin/tar",
                   "-x",
                   "-f",
                   archive_path,
                   "-C",
                   destination_path]
            if fmt.endswith("gzip"):
                cmd.append("-z")
            elif fmt.endswith("bzip2"):
                cmd.append("-j")

        # Call command.
        try:
            p = subprocess.Popen(cmd,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            (out, err) = p.communicate()
        except OSError as e:
            raise ProcessorError("%s execution failed with error code %d: %s" % (
                                  os.path.basename(cmd[0]), e.errno, e.strerror))
        if p.returncode != 0:
            raise ProcessorError("Unarchiving %s with %s failed: %s" % (
                                  archive_path, os.path.basename(cmd[0]), err))
        
        self.output("Unarchived %s to %s" 
                    % (archive_path, destination_path))

if __name__ == '__main__':
    processor = Unarchiver()
    processor.execute_shell()
    

########NEW FILE########
__FILENAME__ = URLDownloader
#!/usr/bin/env python
#
# Copyright 2010 Per Olofsson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os.path
import urllib2
import xattr

from autopkglib import Processor, ProcessorError
try:
    from autopkglib import BUNDLE_ID
except ImportError:
    BUNDLE_ID = "com.github.autopkg"


__all__ = ["URLDownloader"]

# XATTR names for Etag and Last-Modified headers
XATTR_ETAG = "%s.etag" % BUNDLE_ID
XATTR_LAST_MODIFIED = "%s.last-modified" % BUNDLE_ID

# Download URLs in chunks of 256 kB.
CHUNK_SIZE = 256 * 1024

def getxattr(pathname, attr):
    """Get a named xattr from a file. Return None if not present"""
    if attr in xattr.listxattr(pathname):
        return xattr.getxattr(pathname, attr)
    else:
        return None


class URLDownloader(Processor):
    description = "Downloads a URL to the specified download_dir."
    input_variables = {
        "url": {
            "required": True,
            "description": "The URL to download.",
        },
        "request_headers": {
            "required": False,
            "description": 
                ("Optional dictionary of headers to include with the download "
                "request.")
        },
        "download_dir": {
            "required": False,
            "description": 
                ("The directory where the file will be downloaded to. Defaults "
                 "to RECIPE_CACHE_DIR/downloads."),
        },
        "filename": {
            "required": False,
            "description": "Filename to override the URL's tail.",
        },
        "PKG": {
            "required": False,
            "description": 
                ("Local path to the pkg/dmg we'd otherwise download. "
                 "If provided, the download is skipped and we just use "
                 "this package or disk image."),
        },
    }
    output_variables = {
        "pathname": {
            "description": "Path to the downloaded file.",
        },
        "last_modified": {
            "description": "last-modified header for the downloaded item.",
        },
        "etag": {
            "description": "etag header for the downloaded item.",
        },
        "download_changed": {
            "description": 
                ("Boolean indicating if the download has changed since the "
                 "last time it was downloaded."),
        },
    }
    
    __doc__ = description
    
    
    def main(self):
        self.env["last_modified"] = ""
        self.env["etag"] = ""
        existing_file_length = None
        
        if "PKG" in self.env:
            self.env["pathname"] = os.path.expanduser(self.env["PKG"])
            self.env["download_changed"] = True
            self.output("Given %s, no download needed." % self.env["pathname"])
            return
            
        if not "filename" in self.env:
            # Generate filename.
            filename = self.env["url"].rpartition("/")[2]
        else:
            filename = self.env["filename"]
        download_dir = (self.env.get("download_dir") or
                        os.path.join(self.env["RECIPE_CACHE_DIR"], "downloads"))
        pathname = os.path.join(download_dir, filename)
        # Save pathname to environment
        self.env["pathname"] = pathname
        
        # create download_dir if needed
        if not os.path.exists(download_dir):
            try:
                os.makedirs(download_dir)
            except OSError, e:
                raise ProcessorError(
                    "Can't create %s: %s" 
                    % (download_dir, e.strerror))
        
        # Download URL.
        url_handle = None
        try:
            request = urllib2.Request(url=self.env["url"])
            
            if "request_headers" in self.env:
                headers = self.env["request_headers"]
                for header, value in headers.items():
                    request.add_header(header, value)
                    
            # if file already exists, add some headers to the request
            # so we don't retrieve the content if it hasn't changed
            if os.path.exists(pathname):
                etag = getxattr(pathname, XATTR_ETAG)
                last_modified = getxattr(pathname, XATTR_LAST_MODIFIED)
                if etag:
                    request.add_header("If-None-Match", etag)
                if last_modified:
                    request.add_header("If-Modified-Since", last_modified)
                existing_file_length = os.path.getsize(pathname)
                    
            # Open URL.
            try:
                url_handle = urllib2.urlopen(request)
            except urllib2.HTTPError, http_err:
                if http_err.code == 304:
                    # resource not modified
                    self.env["download_changed"] = False
                    self.output("Item at URL is unchanged.")
                    self.output("Using existing %s" % pathname)
                    return
                else:
                    raise
            
            # If Content-Length header is present and we had a cached
            # file, see if it matches the size of the cached file.
            # Useful for webservers that don't provide Last-Modified
            # and ETag headers.
            size_header = url_handle.info().get("Content-Length")
            if url_handle.info().get("Content-Length"):
                if int(size_header) == existing_file_length:
                    self.env["download_changed"] = False
                    self.output("File size returned by webserver matches that "
                                "of the cached file: %s bytes" % size_header)
                    self.output("WARNING: Matching a download by filesize is a "
                                "fallback mechanism that does not guarantee "
                                "that a build is unchanged.")
                    self.output("Using existing %s" % pathname)
                    return

            # Download file.
            self.env["download_changed"] = True
            with open(pathname, "wb") as file_handle:
                while True:
                    data = url_handle.read(CHUNK_SIZE)
                    if len(data) == 0:
                        break
                    file_handle.write(data)
                    
            # save last-modified header if it exists
            if url_handle.info().get("last-modified"):
                self.env["last_modified"] = url_handle.info().get(
                                                "last-modified")
                xattr.setxattr(
                    pathname, XATTR_LAST_MODIFIED,
                    url_handle.info().get("last-modified"))
                self.output("Storing new Last-Modified header: %s" %
                    url_handle.info().get("last-modified"))
                            
            # save etag if it exists
            self.env["etag"] = ""
            if url_handle.info().get("etag"):
                self.env["etag"] = url_handle.info().get("etag")
                xattr.setxattr(
                    pathname, XATTR_ETAG, url_handle.info().get("etag"))
                self.output("Storing new ETag header: %s" %
                    url_handle.info().get("etag"))
                    
            self.output("Downloaded %s" % pathname)
        
        except BaseException as e:
            raise ProcessorError(
                "Couldn't download %s: %s" % (self.env["url"], e))
        finally:
            if url_handle is not None:
                url_handle.close()


if __name__ == "__main__":
    processor = URLDownloader()
    processor.execute_shell()
    

########NEW FILE########
__FILENAME__ = URLTextSearcher
#!/usr/bin/env python

import datetime
import re
import urllib2

from autopkglib import Processor, ProcessorError

__all__ = ["URLTextSearcher"]

class URLTextSearcher(Processor):
    '''Downloads a URL and performs a regular expression match on the text.'''

    input_variables = {
        're_pattern': {
            'description': 'Regular expression (Python) to match against page.',
            'required': True,
        },
        'url': {
            'description': 'URL to download',
            'required': True,
        },
        'result_output_var_name': {
            'description': 'The name of the output variable that is returned by the match. If not specified then a default of "match" will be used.',
            'required': False,
        },
        'request_headers': {
            'description': 'Optional dictionary of headers to include with the download request.',
            'required': False,
        },
        're_flags': {
            'description': 'Optional array of strings of Python regular expression flags. E.g. IGNORECASE.',
            'required': False,
        },
    }
    output_variables = {
        'result_output_var_name': {
            'description': 'First matched sub-pattern from input found on the fetched URL. Note the actual name of variable depends on the input variable "result_output_var_name" or is assigned a default of "match."'
        }
    }

    description = __doc__

    def get_url_and_search(self, url, re_pattern, headers={}, flags={}):
        flag_accumulator = 0
        for f in flags:
            if f in re.__dict__:
                flag_accumulator += re.__dict__[f]

        re_pattern = re.compile(re_pattern, flags=flag_accumulator)

        try:
            r = urllib2.Request(url, headers=headers)
            f = urllib2.urlopen(r)
            content = f.read()
            f.close()
        except BaseException as e:
            raise ProcessorError('Could not retrieve URL: %s' % url)

        m = re_pattern.search(content)

        if not m:
            raise ProcessorError('No match found on URL: %s' % url)

        # return the last matched group with the dict of named groups
        return (m.group(m.lastindex or 0), m.groupdict(), )

    def main(self):
        output_var_name = None

        if 'result_output_var_name' in self.env and self.env['result_output_var_name']:
            output_var_name = self.env['result_output_var_name']
        else:
            output_var_name = 'match'

        headers = self.env.get('request_headers', {})

        flags = self.env.get('re_flags', {})

        groupmatch, groupdict = self.get_url_and_search(self.env['url'], self.env['re_pattern'], headers, flags)

        # favor a named group over a normal group match
        if output_var_name not in groupdict.keys():
            groupdict[output_var_name] = groupmatch

        self.output_variables = {}
        for k in groupdict.keys():
            self.env[k] = groupdict[k]
            self.output('Found matching text (%s): %s' % (k, self.env[k], ))
            self.output_variables[k] = {'description': 'Matched regular expression group'}

if __name__ == '__main__':
    processor = URLTextSearcher()
    processor.execute_shell()

########NEW FILE########
__FILENAME__ = Versioner
#!/usr/bin/env python
#
# Copyright 2013 Greg Neagle
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os.path

from autopkglib import Processor, ProcessorError
from DmgMounter import DmgMounter
import FoundationPlist

__all__ = ["Versioner"]


class Versioner(DmgMounter):
    """Returns version information from a plist"""
    input_variables = {
        "input_plist_path": {
            "required": True,
            "description": 
                ("File path to a plist. Can point to a path inside a .dmg "
                 "which will be mounted."),
        },
        "plist_version_key": {
            "required": False,
            "description": 
                ("Which plist key to use; defaults to "
                "CFBundleShortVersionString"),
        },
    }
    output_variables = {
        "version": {
            "description": "Version of the item.",
        },
    }
    description = __doc__


    def main(self):
        # Check if we're trying to read something inside a dmg.
        (dmg_path, dmg, dmg_source_path) = self.env[
            'input_plist_path'].partition(".dmg/")
        dmg_path += ".dmg"
        try:
            if dmg:
                # Mount dmg and copy path inside.
                mount_point = self.mount(dmg_path)
                input_plist_path = os.path.join(mount_point, dmg_source_path)
            else:
                # just use the given path
                input_plist_path = self.env['input_plist_path']
            try:
                plist = FoundationPlist.readPlist(input_plist_path)
                version_key = self.env.get(
                    "plist_version_key", "CFBundleShortVersionString")
                self.env['version'] = plist.get(version_key, "UNKNOWN_VERSION")
                self.output("Found version %s in file %s" 
                            % (self.env['version'], input_plist_path))
            except FoundationPlist.FoundationPlistException, err:
                raise ProcessorError(err)

        finally:
            if dmg:
                self.unmount(dmg_path)


if __name__ == '__main__':
    processor = Versioner()
    processor.execute_shell()

    
########NEW FILE########
__FILENAME__ = launch
#
# Copyright 2010 Per Olofsson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from ctypes import *
libc = CDLL("libc.dylib")


c_launch_data_t = c_void_p

# size_t launch_data_array_get_count(const launch_data_t)
launch_data_array_get_count = libc.launch_data_array_get_count
launch_data_array_get_count.restype = c_size_t
launch_data_array_get_count.argtypes = [c_launch_data_t]

#launch_data_t launch_data_array_get_index(const launch_data_t, size_t) __ld_getter;
launch_data_array_get_index = libc.launch_data_array_get_index
launch_data_array_get_index.restype = c_launch_data_t
launch_data_array_get_index.argtypes = [c_launch_data_t, c_size_t]

# size_t launch_data_dict_get_count(const launch_data_t)
launch_data_dict_get_count = libc.launch_data_dict_get_count
launch_data_dict_get_count.restype = c_size_t
launch_data_dict_get_count.argtypes = [c_launch_data_t]

# launch_data_t launch_data_dict_lookup(const launch_data_t, const char *)
launch_data_dict_lookup = libc.launch_data_dict_lookup
launch_data_dict_lookup.restype = c_launch_data_t
launch_data_dict_lookup.argtypes = [c_launch_data_t, c_char_p]

#void launch_data_dict_iterate(const launch_data_t, void (*)(const launch_data_t, const char *, void *), void *) __ld_iterator(1, 2)
DICTITCALLBACK = CFUNCTYPE(c_void_p, c_launch_data_t, c_char_p, c_void_p)
launch_data_dict_iterate = libc.launch_data_dict_iterate
launch_data_dict_iterate.restype = None
launch_data_dict_iterate.argtypes = [c_launch_data_t, DICTITCALLBACK, c_void_p]

# void launch_data_free(launch_data_t)
launch_data_free = libc.launch_data_free
launch_data_free.restype = None
launch_data_free.argtypes = [c_launch_data_t]

# int launch_data_get_errno(const launch_data_t)
launch_data_get_errno = libc.launch_data_get_errno
launch_data_get_errno.restype = c_int
launch_data_get_errno.argtypes = [c_launch_data_t]

# int launch_data_get_fd(const launch_data_t)
launch_data_get_fd = libc.launch_data_get_fd
launch_data_get_fd.restype = c_int
launch_data_get_fd.argtypes = [c_launch_data_t]

# launch_data_type_t launch_data_get_type(const launch_data_t)
launch_data_get_type = libc.launch_data_get_type
launch_data_get_type.restype = c_launch_data_t
launch_data_get_type.argtypes = [c_launch_data_t]

# launch_data_t launch_data_new_string(const char *)
launch_data_new_string = libc.launch_data_new_string
launch_data_new_string.restype = c_launch_data_t
launch_data_new_string.argtypes = [c_char_p]

# launch_data_t launch_msg(const launch_data_t)
launch_msg = libc.launch_msg
launch_msg.restype = c_launch_data_t
launch_msg.argtypes = [c_launch_data_t]


LAUNCH_KEY_SUBMITJOB						= c_char_p("SubmitJob")
LAUNCH_KEY_REMOVEJOB						= c_char_p("RemoveJob")
LAUNCH_KEY_STARTJOB							= c_char_p("StartJob")
LAUNCH_KEY_STOPJOB							= c_char_p("StopJob")
LAUNCH_KEY_GETJOB							= c_char_p("GetJob")
LAUNCH_KEY_GETJOBS							= c_char_p("GetJobs")
LAUNCH_KEY_CHECKIN							= c_char_p("CheckIn")

LAUNCH_JOBKEY_LABEL							= c_char_p("Label")
LAUNCH_JOBKEY_DISABLED						= c_char_p("Disabled")
LAUNCH_JOBKEY_USERNAME						= c_char_p("UserName")
LAUNCH_JOBKEY_GROUPNAME						= c_char_p("GroupName")
LAUNCH_JOBKEY_TIMEOUT						= c_char_p("TimeOut")
LAUNCH_JOBKEY_EXITTIMEOUT					= c_char_p("ExitTimeOut")
LAUNCH_JOBKEY_INITGROUPS					= c_char_p("InitGroups")
LAUNCH_JOBKEY_SOCKETS						= c_char_p("Sockets")
LAUNCH_JOBKEY_MACHSERVICES					= c_char_p("MachServices")
LAUNCH_JOBKEY_MACHSERVICELOOKUPPOLICIES		= c_char_p("MachServiceLookupPolicies")
LAUNCH_JOBKEY_INETDCOMPATIBILITY			= c_char_p("inetdCompatibility")
LAUNCH_JOBKEY_ENABLEGLOBBING				= c_char_p("EnableGlobbing")
LAUNCH_JOBKEY_PROGRAMARGUMENTS				= c_char_p("ProgramArguments")
LAUNCH_JOBKEY_PROGRAM						= c_char_p("Program")
LAUNCH_JOBKEY_ONDEMAND						= c_char_p("OnDemand")
LAUNCH_JOBKEY_KEEPALIVE						= c_char_p("KeepAlive")
LAUNCH_JOBKEY_LIMITLOADTOHOSTS				= c_char_p("LimitLoadToHosts")
LAUNCH_JOBKEY_LIMITLOADFROMHOSTS			= c_char_p("LimitLoadFromHosts")
LAUNCH_JOBKEY_LIMITLOADTOSESSIONTYPE		= c_char_p("LimitLoadToSessionType")
LAUNCH_JOBKEY_RUNATLOAD						= c_char_p("RunAtLoad")
LAUNCH_JOBKEY_ROOTDIRECTORY					= c_char_p("RootDirectory")
LAUNCH_JOBKEY_WORKINGDIRECTORY				= c_char_p("WorkingDirectory")
LAUNCH_JOBKEY_ENVIRONMENTVARIABLES			= c_char_p("EnvironmentVariables")
LAUNCH_JOBKEY_USERENVIRONMENTVARIABLES		= c_char_p("UserEnvironmentVariables")
LAUNCH_JOBKEY_UMASK							= c_char_p("Umask")
LAUNCH_JOBKEY_NICE							= c_char_p("Nice")
LAUNCH_JOBKEY_HOPEFULLYEXITSFIRST	  		= c_char_p("HopefullyExitsFirst")
LAUNCH_JOBKEY_HOPEFULLYEXITSLAST   			= c_char_p("HopefullyExitsLast")
LAUNCH_JOBKEY_LOWPRIORITYIO					= c_char_p("LowPriorityIO")
LAUNCH_JOBKEY_SESSIONCREATE					= c_char_p("SessionCreate")
LAUNCH_JOBKEY_STARTONMOUNT					= c_char_p("StartOnMount")
LAUNCH_JOBKEY_SOFTRESOURCELIMITS			= c_char_p("SoftResourceLimits")
LAUNCH_JOBKEY_HARDRESOURCELIMITS			= c_char_p("HardResourceLimits")
LAUNCH_JOBKEY_STANDARDINPATH				= c_char_p("StandardInPath")
LAUNCH_JOBKEY_STANDARDOUTPATH				= c_char_p("StandardOutPath")
LAUNCH_JOBKEY_STANDARDERRORPATH				= c_char_p("StandardErrorPath")
LAUNCH_JOBKEY_DEBUG							= c_char_p("Debug")
LAUNCH_JOBKEY_WAITFORDEBUGGER				= c_char_p("WaitForDebugger")
LAUNCH_JOBKEY_QUEUEDIRECTORIES				= c_char_p("QueueDirectories")
LAUNCH_JOBKEY_WATCHPATHS					= c_char_p("WatchPaths")
LAUNCH_JOBKEY_STARTINTERVAL					= c_char_p("StartInterval")
LAUNCH_JOBKEY_STARTCALENDARINTERVAL			= c_char_p("StartCalendarInterval")
LAUNCH_JOBKEY_BONJOURFDS					= c_char_p("BonjourFDs")
LAUNCH_JOBKEY_LASTEXITSTATUS				= c_char_p("LastExitStatus")
LAUNCH_JOBKEY_PID							= c_char_p("PID")
LAUNCH_JOBKEY_THROTTLEINTERVAL				= c_char_p("ThrottleInterval")
LAUNCH_JOBKEY_LAUNCHONLYONCE				= c_char_p("LaunchOnlyOnce")
LAUNCH_JOBKEY_ABANDONPROCESSGROUP			= c_char_p("AbandonProcessGroup")
LAUNCH_JOBKEY_IGNOREPROCESSGROUPATSHUTDOWN	= c_char_p("IgnoreProcessGroupAtShutdown")
LAUNCH_JOBKEY_POLICIES						= c_char_p("Policies")
LAUNCH_JOBKEY_ENABLETRANSACTIONS			= c_char_p("EnableTransactions")

LAUNCH_JOBPOLICY_DENYCREATINGOTHERJOBS		= c_char_p("DenyCreatingOtherJobs")

LAUNCH_JOBINETDCOMPATIBILITY_WAIT			= c_char_p("Wait")

LAUNCH_JOBKEY_MACH_RESETATCLOSE				= c_char_p("ResetAtClose")
LAUNCH_JOBKEY_MACH_HIDEUNTILCHECKIN			= c_char_p("HideUntilCheckIn")
LAUNCH_JOBKEY_MACH_DRAINMESSAGESONCRASH		= c_char_p("DrainMessagesOnCrash")

LAUNCH_JOBKEY_KEEPALIVE_SUCCESSFULEXIT		= c_char_p("SuccessfulExit")
LAUNCH_JOBKEY_KEEPALIVE_NETWORKSTATE		= c_char_p("NetworkState")
LAUNCH_JOBKEY_KEEPALIVE_PATHSTATE			= c_char_p("PathState")
LAUNCH_JOBKEY_KEEPALIVE_OTHERJOBACTIVE		= c_char_p("OtherJobActive")
LAUNCH_JOBKEY_KEEPALIVE_OTHERJOBENABLED		= c_char_p("OtherJobEnabled")
LAUNCH_JOBKEY_KEEPALIVE_AFTERINITIALDEMAND	= c_char_p("AfterInitialDemand")

LAUNCH_JOBKEY_CAL_MINUTE					= c_char_p("Minute")
LAUNCH_JOBKEY_CAL_HOUR						= c_char_p("Hour")
LAUNCH_JOBKEY_CAL_DAY						= c_char_p("Day")
LAUNCH_JOBKEY_CAL_WEEKDAY					= c_char_p("Weekday")
LAUNCH_JOBKEY_CAL_MONTH						= c_char_p("Month")
                                    
LAUNCH_JOBKEY_RESOURCELIMIT_CORE			= c_char_p("Core")
LAUNCH_JOBKEY_RESOURCELIMIT_CPU				= c_char_p("CPU")
LAUNCH_JOBKEY_RESOURCELIMIT_DATA			= c_char_p("Data")
LAUNCH_JOBKEY_RESOURCELIMIT_FSIZE			= c_char_p("FileSize")
LAUNCH_JOBKEY_RESOURCELIMIT_MEMLOCK			= c_char_p("MemoryLock")
LAUNCH_JOBKEY_RESOURCELIMIT_NOFILE			= c_char_p("NumberOfFiles")
LAUNCH_JOBKEY_RESOURCELIMIT_NPROC			= c_char_p("NumberOfProcesses")
LAUNCH_JOBKEY_RESOURCELIMIT_RSS				= c_char_p("ResidentSetSize")
LAUNCH_JOBKEY_RESOURCELIMIT_STACK			= c_char_p("Stack")

LAUNCH_JOBKEY_DISABLED_MACHINETYPE			= c_char_p("MachineType")
LAUNCH_JOBKEY_DISABLED_MODELNAME			= c_char_p("ModelName")

LAUNCH_JOBSOCKETKEY_TYPE					= c_char_p("SockType")
LAUNCH_JOBSOCKETKEY_PASSIVE					= c_char_p("SockPassive")
LAUNCH_JOBSOCKETKEY_BONJOUR					= c_char_p("Bonjour")
LAUNCH_JOBSOCKETKEY_SECUREWITHKEY			= c_char_p("SecureSocketWithKey")
LAUNCH_JOBSOCKETKEY_PATHNAME				= c_char_p("SockPathName")
LAUNCH_JOBSOCKETKEY_PATHMODE				= c_char_p("SockPathMode")
LAUNCH_JOBSOCKETKEY_NODENAME				= c_char_p("SockNodeName")
LAUNCH_JOBSOCKETKEY_SERVICENAME				= c_char_p("SockServiceName")
LAUNCH_JOBSOCKETKEY_FAMILY					= c_char_p("SockFamily")
LAUNCH_JOBSOCKETKEY_PROTOCOL				= c_char_p("SockProtocol")
LAUNCH_JOBSOCKETKEY_MULTICASTGROUP			= c_char_p("MulticastGroup")


(
    LAUNCH_DATA_DICTIONARY,
    LAUNCH_DATA_ARRAY,
    LAUNCH_DATA_FD,
    LAUNCH_DATA_INTEGER,
    LAUNCH_DATA_REAL,
    LAUNCH_DATA_BOOL,
    LAUNCH_DATA_STRING,
    LAUNCH_DATA_OPAQUE,
    LAUNCH_DATA_ERRNO,
    LAUNCH_DATA_MACHPORT
) = range(1, 11)


class LaunchDCheckInError(Exception):
    pass

def get_launchd_socket_fds():
    """Check in with launchd to get socket file descriptors."""
    
    # Returna dictionary with lists of file descriptors.
    launchd_socket_fds = dict()
    
    # Callback for dict iterator.
    def add_socket(launch_array, name, context=None):
        if launch_data_get_type(launch_array) != LAUNCH_DATA_ARRAY:
            raise LaunchDCheckInError("Could not get file descriptor array: Type mismatch")
        fds = list()
        for i in range(launch_data_array_get_count(launch_array)):
            data_fd = launch_data_array_get_index(launch_array, i)
            if launch_data_get_type(data_fd) != LAUNCH_DATA_FD:
                raise LaunchDCheckInError("Could not get file descriptor array entry: Type mismatch")
            fds.append(launch_data_get_fd(data_fd))
        launchd_socket_fds[name] = fds
    
    # Wrap in try/finally to free resources allocated during lookup.
    try:
        # Create a checkin request.
        checkin_request = launch_data_new_string(LAUNCH_KEY_CHECKIN);
        if checkin_request == None:
            raise LaunchDCheckInError("Could not create checkin request")
        
        # Check the checkin response.
        checkin_response = launch_msg(checkin_request);
        if checkin_response == None:
            raise LaunchDCheckInError("Error checking in")
        
        if launch_data_get_type(checkin_response) == LAUNCH_DATA_ERRNO:
            errno = launch_data_get_errno(checkin_response)
            raise LaunchDCheckInError("Checkin failed")
        
        # Get a dictionary of sockets.
        sockets = launch_data_dict_lookup(checkin_response, LAUNCH_JOBKEY_SOCKETS);
        if sockets == None:
            raise LaunchDCheckInError("Could not get socket dictionary from checkin response")
        
        if launch_data_get_type(sockets) != LAUNCH_DATA_DICTIONARY:
            raise LaunchDCheckInError("Could not get socket dictionary from checkin response: Type mismatch")
        
        # Iterate over the items with add_socket callback.
        launch_data_dict_iterate(sockets, DICTITCALLBACK(add_socket), None)
        
        return launchd_socket_fds
    
    finally:
        if checkin_response is not None:
            launch_data_free(checkin_response)
        if checkin_request is not None:
            launch_data_free(checkin_request)
    

########NEW FILE########
__FILENAME__ = packager
#!/usr/bin/env python
#
# Copyright 2010-2012 Per Olofsson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import plistlib
import stat
import shutil
import subprocess
import re
import tempfile
import pwd
import grp


__all__ = [
    'Packager',
    'PackagerError'
]


class PackagerError(Exception):
    pass

class Packager(object):
    """Create an Apple installer package.
    
    Must be run as root."""
    
    re_pkgname = re.compile(r'^[a-z0-9][a-z0-9 ._\-]*$', re.I)
    re_id      = re.compile(r'^[a-z0-9]([a-z0-9 \-]*[a-z0-9])?$', re.I)
    re_version = re.compile(r'^[a-z0-9_ ]*[0-9][a-z0-9_ ]*$', re.I)
    
    def __init__(self, log, request, name, uid, gid):
        """Arguments:
        
        log     A logger instance.
        request A request in plist format.
        name    Name of the component to package.
        uid     The UID of the user that made the request.
        gid     The GID of the user that made the request.
        """
        
        self.log = log
        self.request = request
        self.name = name
        self.uid = uid
        self.gid = gid
        self.tmproot = None
    
    def package(self):
        """Main method."""
        
        try:
            self.verify_request()
            self.copy_pkgroot()
            self.apply_chown()
            self.make_component_property_list()
            return self.create_pkg()
        finally:
            self.cleanup()
    
    def verify_request(self):
        """Verify that the request is valid."""
        
        self.log.debug("Verifying packaging request")
        
        def verify_dir_and_owner(path, uid):
            try:
                info = os.lstat(path)
            except OSError as e:
                raise PackagerError("Can't stat %s: %s" % (path, e))
            if info.st_uid != uid:
                raise PackagerError("%s isn't owned by %d" % (path, uid))
            if stat.S_ISLNK(info.st_mode):
                raise PackagerError("%s is a soft link" % path)
            if not stat.S_ISDIR(info.st_mode):
                raise PackagerError("%s is not a directory" % path)
        
        # Check owner and type of directories.
        verify_dir_and_owner(self.request.pkgroot, self.uid)
        self.log.debug("pkgroot ok")
        verify_dir_and_owner(self.request.pkgdir, self.uid)
        self.log.debug("pkgdir ok")
        
        # Check name.
        if len(self.request.pkgname) > 80:
            raise PackagerError("Package name too long")
        if not self.re_pkgname.search(self.request.pkgname):
            raise PackagerError("Invalid package name")
        if self.request.pkgname.lower().endswith(".pkg"):
            raise PackagerError("Package name mustn't include '.pkg'")
        self.log.debug("pkgname ok")
        
        # Check ID.
        if len(self.request.id) > 80:
            raise PackagerError("Package id too long")
        components = self.request.id.split(".")
        if len(components) < 2:
            raise PackagerError("Invalid package id")
        for comp in components:
            if not self.re_id.search(comp):
                raise PackagerError("Invalid package id")
        self.log.debug("id ok")
        
        # Check version.
        if len(self.request.version) > 40:
            raise PackagerError("Version too long")
        components = self.request.version.split(".")
        if len(components) < 1:
            raise PackagerError("Invalid version")
        for comp in components:
            if not self.re_version.search(comp):
                raise PackagerError("Invalid version")
        self.log.debug("version ok")
        
        # Make sure infofile and resources exist and can be read.
        if self.request.infofile:
            try:
                with open(self.request.infofile, "rb") as f:
                    pass
            except (IOError, OSError) as e:
                raise PackagerError("Can't open infofile: %s" % e)
            self.log.debug("infofile ok")

        # Make sure scripts is a directory and its contents
        # are executable.
        if self.request.scripts:
            if self.request.pkgtype == "bundle":
                raise PackagerError(
                    "Installer scripts are not supported with "
                    "bundle package types.")
            if not os.path.isdir(self.request.scripts):
                raise PackagerError(
                    "Can't find scripts directory: %s"
                    % self.request.scripts)
            for script in ["preinstall", "postinstall"]:
                script_path = os.path.join(self.request.scripts, script)
                if os.path.exists(script_path) \
                    and not os.access(script_path, os.X_OK):
                    raise PackagerError(
                        "%s script found in %s but it is not executable!"
                        % (script, self.request.scripts))
            self.log.debug("scripts ok")
        
        # FIXME: resources temporarily unsupported.
        #if self.request.resources:
        #    try:
        #        os.listdir(self.request.resources)
        #    except OSError as e:
        #        raise PackagerError("Can't list Resources: %s" % e)
        #    self.log.debug("resources ok")
        
        # Leave chown verification until after the pkgroot has been copied.
        
        self.log.info("Packaging request verified")
    
    def copy_pkgroot(self):
        """Copy pkgroot to temporary directory."""
        
        name = self.request.pkgname
        
        self.log.debug("Copying package root")
        
        self.tmproot = tempfile.mkdtemp()
        self.tmp_pkgroot = os.path.join(self.tmproot, self.name)
        os.mkdir(self.tmp_pkgroot)
        os.chmod(self.tmp_pkgroot, 01775)
        os.chown(self.tmp_pkgroot, 0, 80)
        try:
            p = subprocess.Popen(("/usr/bin/ditto",
                                  self.request.pkgroot,
                                  self.tmp_pkgroot),
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            out, err = p.communicate()
        except OSError as e:
            raise PackagerError("ditto execution failed with error code %d: %s" % (
                                 e.errno, e.strerror))
        if p.returncode != 0:
            raise PackagerError("Couldn't copy pkgroot from %s to %s: %s" % (
                                 self.request.pkgroot,
                                 self.tmp_pkgroot,
                                 " ".join(str(err).split())))
        
        self.log.info("Package root copied to %s" % self.tmp_pkgroot)
    
    def apply_chown(self):
        """Change owner and group, and permissions if the 'mode' key was set."""
        
        self.log.debug("Applying chown")
        
        def verify_relative_valid_path(root, path):
            if len(path) < 1:
                raise PackagerError("Empty chown path")
            
            checkpath = root
            parts = path.split(os.sep)
            for part in parts:
                if part in (".", ".."):
                    raise PackagerError(". and .. is not allowed in chown path")
                checkpath = os.path.join(checkpath, part)
                relpath = checkpath[len(root) + 1:]
                if not os.path.exists(checkpath):
                    raise PackagerError("chown path %s does not exist" % relpath)
                if os.path.islink(checkpath):
                    raise PackagerError("chown path %s is a soft link" % relpath)
        
        for entry in self.request.chown:
            # Check path.
            verify_relative_valid_path(self.tmp_pkgroot, entry.path)
            # Check user.
            if isinstance(entry.user, str):
                try:
                    uid = pwd.getpwnam(entry.user).pw_uid
                except KeyError:
                    raise PackagerError("Unknown chown user %s" % entry.user)
            else:
                uid = int(entry.user)
            if uid < 0:
                raise PackagerError("Invalid uid %d" % uid)
            # Check group.
            if isinstance(entry.group, str):
                try:
                    gid = grp.getgrnam(entry.group).gr_gid
                except KeyError:
                    raise PackagerError("Unknown chown group %s" % entry.group)
            else:
                gid = int(entry.group)
            if gid < 0:
                raise PackagerError("Invalid gid %d" % gid)
            
            self.log.info("Setting owner and group of %s to %s:%s" % (
                     entry.path,
                     str(entry.user),
                     str(entry.group)))
            
            chownpath = os.path.join(self.tmp_pkgroot, entry.path)
            if "mode" in entry.keys():
                chmod_present = True
            else:
                chmod_present = False
            if os.path.isfile(chownpath):
                os.lchown(chownpath, uid, gid)
                if chmod_present:
                    self.log.info("Setting mode of %s to %s" % (
                        entry.path,
                        str(entry.mode)))
                    os.chmod(chownpath, int(entry.mode, 8))
            else:
                for (dirpath,
                     dirnames,
                     filenames) in os.walk(chownpath):
                    try:
                        os.lchown(dirpath, uid, gid)
                    except OSError as e:
                        raise PackagerError("Can't lchown %s: %s" % (dirpath, e))
                    for entry in dirnames + filenames:
                        path = os.path.join(dirpath, entry)
                        try:
                            os.lchown(path, uid, gid)
                            if chmod_present:
                                os.chmod(path, int(entry.mode, 8))
                        except OSError as e:
                            raise PackagerError("Can't lchown %s: %s" % (path, e))
        
        self.log.info("Chown applied")
    
    def random_string(self, len):
        rand = os.urandom((len + 1) / 2)
        randstr = "".join(["%02x" % ord(c) for c in rand])
        return randstr[:len]
        
    def make_component_property_list(self):
        """Use pkgutil --analyze to build a component property list; then
        turn off package relocation"""
        self.component_plist = os.path.join(self.tmproot, "component.plist")
        try:
            p = subprocess.Popen(("/usr/bin/pkgbuild",
                                  "--analyze",
                                  "--root", self.tmp_pkgroot,
                                  self.component_plist),
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
            (out, err) = p.communicate()
        except OSError as e:
            raise PackagerError(
                "pkgbuild execution failed with error code %d: %s" 
                % (e.errno, e.strerror))
        if p.returncode != 0:
            raise PackagerError(
                "pkgbuild failed with exit code %d: %s" 
                % (p.returncode, " ".join(str(err).split())))
        try:
            plist = plistlib.readPlist(self.component_plist)
        except BaseException as err:
            raise PackagerError("Couldn't read %s" % self.component_plist)
        # plist is an array of dicts, iterate through
        for bundle in plist:
            if bundle.get("BundleIsRelocatable"):
                bundle["BundleIsRelocatable"] = False
        try:
            plistlib.writePlist(plist, self.component_plist)
        except BaseException as err:
            raise PackagerError("Couldn't write %s" % self.component_plist)
    
    def create_pkg(self):
        self.log.info("Creating package")
        if self.request.pkgtype != "flat":
            raise PackagerError("Unsupported pkgtype %s" % (
                                repr(self.request.pkgtype)))
        
        pkgname = self.request.pkgname + ".pkg"
        pkgpath = os.path.join(self.request.pkgdir, pkgname)
        
        # Remove existing pkg if it exists and is owned by uid.
        if os.path.exists(pkgpath):
            try:
                if os.lstat(pkgpath).st_uid != self.uid:
                    raise PackagerError("Existing pkg %s not owned by %d" % (
                                         pkgpath, self.uid))
                if os.path.islink(pkgpath) or os.path.isfile(pkgpath):
                    os.remove(pkgpath)
                else:
                    shutil.rmtree(pkgpath)
            except OSError as e:
                raise PackagerError("Can't remove existing pkg %s: %s" % (
                                     pkgpath, e.strerror))
        
        # Use a temporary name while building.
        temppkgname = "autopkgtmp-%s-%s.pkg" % (self.random_string(16),
                                     self.request.pkgname)
        temppkgpath = os.path.join(self.request.pkgdir, temppkgname)
        
        # Wrap package building in try/finally to remove temporary package if
        # it fails.
        try:
            # make a pkgbuild cmd
            cmd = ["/usr/bin/pkgbuild",
                    "--root", self.tmp_pkgroot,
                    "--identifier", self.request.id,
                    "--version", self.request.version,
                    "--ownership", "preserve",
                    "--component-plist", self.component_plist]
            if self.request.infofile:
                cmd.extend(["--info", self.request.infofile])
            if self.request.scripts:
                cmd.extend(["--scripts", self.request.scripts])
            cmd.append(temppkgpath)
            
            # Execute pkgbuild.
            try:
                p = subprocess.Popen(cmd,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
                (out, err) = p.communicate()
            except OSError as e:
                raise PackagerError(
                    "pkgbuild execution failed with error code %d: %s" 
                    % (e.errno, e.strerror))
            if p.returncode != 0:
                raise PackagerError("pkgbuild failed with exit code %d: %s" % (
                                     p.returncode,
                                     " ".join(str(err).split())))
            
            # Change to final name and owner.
            os.rename(temppkgpath, pkgpath)
            os.chown(pkgpath, self.uid, self.gid)
            
            self.log.info("Created package at %s" % pkgpath)
            return pkgpath
        
        finally:
            # Remove temporary package.
            try:
                os.remove(temppkgpath)
            except OSError as e:
                if e.errno != 2:
                    self.log.warn("Can't remove temporary package at %s: %s" % (
                                  temppkgpath, e.strerror))
    
    def cleanup(self):
        """Clean up resources."""
        
        if self.tmproot:
            shutil.rmtree(self.tmproot)
    

########NEW FILE########
__FILENAME__ = FoundationPlist
#!/usr/bin/python
# encoding: utf-8
#
# Copyright 2009-2014 Greg Neagle.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""FoundationPlist.py -- a tool to generate and parse MacOSX .plist files.

This is intended as a drop-in replacement for Python's included plistlib,
with a few caveats:
    - readPlist() and writePlist() operate only on a filepath,
        not a file object.
    - there is no support for the deprecated functions:
        readPlistFromResource()
        writePlistToResource()
    - there is no support for the deprecated Plist class.

The Property List (.plist) file format is a simple XML pickle supporting
basic object types, like dictionaries, lists, numbers and strings.
Usually the top level object is a dictionary.

To write out a plist file, use the writePlist(rootObject, filepath)
function. 'rootObject' is the top level object, 'filepath' is a
filename.

To parse a plist from a file, use the readPlist(filepath) function,
with a file name. It returns the top level object (again, usually a
dictionary).

To work with plist data in strings, you can use readPlistFromString()
and writePlistToString().
"""

import os

from Foundation import NSData, \
                       NSPropertyListSerialization, \
                       NSPropertyListMutableContainersAndLeaves, \
                       NSPropertyListXMLFormat_v1_0


class FoundationPlistException(Exception):
    '''Base error for this module'''
    pass


class NSPropertyListSerializationException(FoundationPlistException):
    '''Read error for this module'''
    pass


class NSPropertyListWriteException(FoundationPlistException):
    '''Write error for this module'''
    pass


# private functions
def _dataToPlist(data):
    '''low-level function that parses a data object into a propertyList object'''
    darwin_vers = int(os.uname()[2].split('.')[0])
    if darwin_vers > 10:
        (plistObject, plistFormat, error) = (
            NSPropertyListSerialization.propertyListWithData_options_format_error_(
                data, NSPropertyListMutableContainersAndLeaves, None, None))
    else:
        # 10.5 doesn't support propertyListWithData:options:format:error:
        # 10.6's PyObjC wrapper for propertyListWithData:options:format:error:
        #        is broken
        # so use the older NSPropertyListSerialization function
        (plistObject, plistFormat, error) = (
            NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(
                         data, NSPropertyListMutableContainersAndLeaves, None, None))
    if error:
        raise NSPropertyListSerializationException(error)
    else:
        return plistObject


def _plistToData(plistObject):
    '''low-level function that creates NSData from a plist object'''
    darwin_vers = int(os.uname()[2].split('.')[0])
    if darwin_vers > 10:
        (data, error) = (
            NSPropertyListSerialization.dataWithPropertyList_format_options_error_(
                plistObject, NSPropertyListXMLFormat_v1_0, 0, None))
    else:
        # use the older NSPropertyListSerialization function on 10.6 and 10.5
        (data, error) = (
            NSPropertyListSerialization.dataFromPropertyList_format_errorDescription_(
                plistObject, NSPropertyListXMLFormat_v1_0, None))
    if error:
        raise NSPropertyListSerializationException(error)
    return data


# public functions
def readPlist(filepath):
    '''Read a .plist file from filepath.  Return the unpacked root object
    (which is usually a dictionary).'''
    try:
        data = NSData.dataWithContentsOfFile_(filepath)
    except NSPropertyListSerializationException, error:
        # insert filepath info into error message
        errmsg = (u'%s in %s' % (error, filepath))
        raise NSPropertyListSerializationException(errmsg)
    return _dataToPlist(data)


def readPlistFromString(aString):
    '''Read a plist data from a string. Return the root object.'''
    data = buffer(aString)
    return _dataToPlist(data)


def writePlist(plistObject, filepath):
    '''Write 'plistObject' as a plist to filepath.'''
    plistData = _plistToData(plistObject)
    if plistData.writeToFile_atomically_(filepath, True):
        return
    else:
        raise NSPropertyListWriteException(
            u"Failed to write plist data to %s" % filepath)


def writePlistToString(plistObject):
    '''Create a plist-formatted string from plistObject.'''
    return str(_plistToData(plistObject))

########NEW FILE########
__FILENAME__ = generate_processor_docs
#!/usr/bin/env python
#
# Copyright 2013 Greg Neagle
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import imp
import os
import optparse
import re
import sys

from tempfile import mkdtemp

# Grabbing some functions from the Code directory
code_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../Code"))
sys.path.append(code_dir)
from autopkglib import get_processor, \
                       processor_names, \
                       get_autopkg_version

# Additional helper function(s) from the CLI tool
# Don't make an "autopkgc" file
sys.dont_write_bytecode = True
imp.load_source("autopkg", os.path.join(code_dir, "autopkg"))
from autopkg import run_git


def writefile(stringdata, path):
    '''Writes string data to path.'''
    try:
        fileobject = open(path, mode='w', buffering=1)
        print >> fileobject, stringdata.encode('UTF-8')
        fileobject.close()
    except (OSError, IOError):
        print >> sys.stderr, "Couldn't write to %s" % path


def escape(thing):
    '''Returns string with underscores and asterisks escaped
    for use with Markdown'''
    string = str(thing)
    string = string.replace("_", r"\_")
    string = string.replace("*", r"\*")
    return string


def generate_markdown(dict_data, indent=0):
    '''Returns a string with Markup-style formatting of dict_data'''
    string = ""
    for key, value in dict_data.items():
        if isinstance(value, dict):
            string += " " * indent + "- **%s:**\n" % escape(key)
            string += generate_markdown(value, indent=indent + 4)
        else:
            string += " " * indent + "- **%s:** %s\n" % (
                                                escape(key), escape(value))
    return string
        

def clone_wiki_dir(clone_dir=None):
    '''Clone the AutoPkg GitHub repo and return the path to where it was 
    cloned. The path can be specified with 'clone_dir', otherwise a 
    temporary directory will be used.'''

    if not clone_dir:
        outdir = mkdtemp()
    else:
        outdir = clone_dir
    git_output = run_git([
        "clone",
        "https://github.com/autopkg/autopkg.wiki",
        outdir])
    return os.path.abspath(outdir)


def indent_length(line_str):
    '''Returns the indent length of a given string as an integer.'''
    return len(line_str) - len(line_str.lstrip())


def main(argv):
    p = optparse.OptionParser()
    p.description = (
        "Generate GitHub Wiki documentation from the core processors present "
        "in autopkglib. The autopkg.wiki repo is cloned locally, changes are "
        "committed and the user is interactively given the option to push it "
        "to the remote.")
    p.add_option("-d", "--directory", metavar="CLONEDIRECTORY",
        help=("Directory path in which to clone the repo. If not "
              "specified, a temporary directory will be used."))
    options, arguments = p.parse_args()
    
    print "Cloning AutoPkg wiki.."
    print

    if options.directory:
        output_dir = clone_wiki_dir(clone_dir=options.directory)
    else:
        output_dir = clone_wiki_dir()

    print "Cloned to %s." % output_dir
    print
    print


    # Generate markdown pages for each processor attributes
    for processor_name in processor_names():
        processor_class = get_processor(processor_name)
        try:
            description = processor_class.description
        except AttributeError:
            try:
                description = processor_class.__doc__
            except AttributeError:
                description = ""
        try:
            input_vars = processor_class.input_variables
        except AttributeError:
            input_vars = {}
        try:
            output_vars = processor_class.output_variables
        except AttributeError:
            output_vars = {}
        
        filename = "Processor-%s.md" % processor_name
        pathname = os.path.join(output_dir, filename)
        output = "# %s\n" % escape(processor_name)
        output += "\n"
        output += "## Description\n%s\n" % escape(description)
        output += "\n"
        output += "## Input Variables\n"
        output += generate_markdown(input_vars)
        output += "\n"
        output += "## Output Variables\n"
        output += generate_markdown(output_vars)
        output += "\n"
        writefile(output, pathname)
    
    # Generate the Processors section of the Sidebar
    processor_heading = "  * **Processors**"  
    toc_string = ""
    toc_string += processor_heading + "\n"
    for processor_name in processor_names():
        page_name = "Processor-%s" % processor_name
        page_name.replace(" ", "-")
        toc_string += "      * [[%s|%s]]\n" % (processor_name, page_name)


    # Merge in the new stuff!
    # - Scrape through the current _Sidebar.md, look for where the existing
    # processors block starts and ends
    # - Copy the lines up to where the Processors section starts
    # - Copy the new Processors TOC
    # - Copy the lines following the Processors section

    sidebar_path = os.path.join(output_dir, "_Sidebar.md")
    with open(sidebar_path, "r") as fd:
        current_sidebar_lines = fd.read().splitlines()

    # Determine our indent amount
    section_indent = indent_length(processor_heading)

    past_processors_section = False
    for index, line in enumerate(current_sidebar_lines):
        if line == processor_heading:
            past_processors_section = True
            processors_start = index
        if (indent_length(line) <= section_indent) and \
        past_processors_section:
            processors_end = index

    # Build the new sidebar
    new_sidebar = ""
    new_sidebar += "\n".join(current_sidebar_lines[0:processors_start]) + "\n"
    new_sidebar += toc_string
    new_sidebar += "\n".join(current_sidebar_lines[processors_end:]) + "\n"

    with open(sidebar_path, "w") as fd:
        fd.write(new_sidebar)

    # Grab the version for the commit log.
    version = get_autopkg_version()

    # Git commit everything
    os.chdir(output_dir)
    run_git([
        "add",
        "--all"])
    run_git([
        "commit",
        "-m", "Updating Wiki docs for release %s" % version])

    # Show the full diff
    print run_git([
        "log",
        "-p",
        "--color",
        "-1"])

    # Do we accept?
    print "-------------------------------------------------------------------"
    print
    print ("Shown above is the commit log for the changes to the wiki markdown. \n"
           "Type 'push' to accept and push the changes to GitHub. The wiki repo \n"
           "local clone can be also inspected at:\n"
           "%s." % output_dir)

    push_commit = raw_input()
    if push_commit == "push":
        run_git([
            "push",
            "origin",
            "master"])

if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = make_new_release
#!/usr/bin/python
#
# Script to run the AutoPkg GitHub release workflow as outlined here:
# https://github.com/autopkg/autopkg/wiki/Packaging-AutoPkg-For-Release-on-GitHub
#
# This includes tagging and setting appropriate release notes for the release,
# uploading the actual built package, and incrementing the version number for the
# next version to be released.
#
# This skips the bootstrap installation script at 'Scripts/install.sh', because this
# step would require root.
#
# Requires an OAuth token with push access to the repo. Currently the GitHub Releases
# API is in a 'preview' status, and this script does very little error handling.

import json
import optparse
import os
import plistlib
import re
import subprocess
import sys
import tempfile
import urllib2

from distutils.version import LooseVersion
from pprint import pprint
from shutil import rmtree
from time import strftime

GITHUB_REPO = 'autopkg/autopkg'

class GitHubAPIError(BaseException):
    pass


def api_call(endpoint, token, baseurl='https://api.github.com', data=None, json_data=True, additional_headers={}):
    '''endpoint: of the form '/repos/username/repo/etc'.
    token: the API token for Authorization.
    baseurl: the base URL for the API endpoint. for asset uploads this ends up needing to be overridden.
    data: takes a standard python object and serializes to json for a POST, unless json_data is False.
    additional_headers: a dict of additional headers for the API call'''
    if data and json_data:
        data = json.dumps(data, ensure_ascii=False)
    headers = {'Accept': 'application/vnd.github.v3+json',
               'Authorization': 'token %s' % token}
    for header, value in additional_headers.items():
        headers[header] = value
        
    req = urllib2.Request(baseurl + endpoint, headers=headers)
    try:
        results = urllib2.urlopen(req, data=data)
    except urllib2.HTTPError as e:
        print >> sys.stderr, "HTTP error making API call!"
        print >> sys.stderr, e
        error_json = e.read()
        error = json.loads(error_json)
        print >> sys.stderr, "API message: %s" % error['message']
        sys.exit(1)
    if results:
        try:
            parsed = json.loads(results.read())
            return parsed
        except BaseException as e:
            print >> sys.stderr, e
            raise GitHubAPIError
    return None


def main():
    usage="""Builds and pushes a new AutoPkg release from an existing Git clone
of AutoPkg.

Requirements:

API token:
You'll need an API OAuth token with push access to the repo. You can create a
Personal Access Token in your user's Account Settings:
https://github.com/settings/applications

autopkgserver components:
This script does not perform the bootstrap steps performed by the install.sh
script, which are needed to have a working pkgserver component. This must
be done as root, so it's best done as a separate process.
"""
    o = optparse.OptionParser(usage=usage)
    o.add_option('-t', '--token',
        help="""GitHub API OAuth token. Required.""")
    o.add_option('-v', '--next-version',
        help="""Next version to which AutoPkg will be incremented. Required.""")

    opts, args = o.parse_args()
    if not opts.next_version:
        sys.exit("Option --next-version is required!")
    if not opts.token:
        sys.exit("Option --token is required!")
    next_version = opts.next_version
    token = opts.token
    # ensure our OAuth token works before we go any further
    api_call('/users/autopkg', token)

    # set up some paths and important variables
    autopkg_root = tempfile.mkdtemp()
    version_plist_path = os.path.join(autopkg_root, 'Code/autopkglib/version.plist')
    changelog_path = os.path.join(autopkg_root, 'CHANGELOG.md')

    # clone Git master
    subprocess.check_call(['git', 'clone', 'https://github.com/autopkg/autopkg', autopkg_root])
    os.chdir(autopkg_root)

    # get the current autopkg version
    try:
        plist = plistlib.readPlist(version_plist_path)
        current_version = plist['Version']
    except:
        sys.exit("Couldn't determine current autopkg version!")
    print "Current AutoPkg version: %s" % current_version
    if LooseVersion(next_version) <= LooseVersion(current_version):
        sys.exit("Next version (gave %s) must be greater than current version %s!"
            % (next_version, current_version))

    tag_name = 'v%s' % current_version
    published_releases = api_call('/repos/%s/releases' % GITHUB_REPO, token)
    for r in published_releases:
        if r['tag_name'] == tag_name:
            print >> sys.stderr, ("There's already a published release on GitHub with the tag {0}. "
                "It should first be manually removed. Release data printed below:".format(tag_name))
            pprint(r, stream=sys.stderr)
            sys.exit()

    # write today's date in the changelog
    with open(changelog_path, 'r') as fd:
        changelog = fd.read()
    release_date = strftime("%B %d, %Y")
    new_changelog = re.sub('Unreleased', release_date, changelog)
    with open(changelog_path, 'w') as fd:
        fd.write(new_changelog)

    # commit and push the new release
    subprocess.check_call(['git', 'add', changelog_path])
    subprocess.check_call(['git', 'commit', '-m', 'Release version %s.' % current_version])
    subprocess.check_call(['git', 'tag', tag_name])
    subprocess.check_call(['git', 'push', 'origin', 'master'])
    subprocess.check_call(['git', 'push', '--tags', 'origin', 'master'])
    # extract release notes for this new version
    match = re.search("(?P<current_ver_notes>\#\#\# %s.+?)\#\#\#" % current_version, new_changelog, re.DOTALL)
    if not match:
        sys.exit("Couldn't extract release notes for this version!")
    release_notes = match.group('current_ver_notes')

    # run the actual AutoPkg.pkg recipe
    recipes_dir = tempfile.mkdtemp()
    subprocess.check_call(['git', 'clone', 'https://github.com/autopkg/recipes', recipes_dir])
    # running using the system AutoPkg directory so that we ensure we're at the minimum
    # required version to run the AutoPkg recipe
    p = subprocess.Popen(['/Library/AutoPkg/autopkg',
        'run',
        '-k', 'force_pkg_build=true',
        '--search-dir', recipes_dir,
        '--report-plist',
        'AutoPkg.pkg'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    out, err = p.communicate()
    print >> sys.stderr, err
    try:
        report = plistlib.readPlistFromString(out)
    except BaseException as e:
        print >> sys.stderr, "Couldn't parse a valid report plist from the autopkg run!"
        sys.exit(e)

    if report['failures']:
        sys.exit("Recipe run error: %s" % report['failures'][0]['message'])

    # collect pkg file data
    built_pkg_path = report['new_packages'][0]['pkg_path']
    pkg_filename = os.path.basename(built_pkg_path)
    with open(built_pkg_path, 'rb') as fd:
        pkg_data = fd.read()

    # prepare release metadata
    release_data = dict()
    release_data['tag_name'] = tag_name
    release_data['target_commitish'] = 'master'
    release_data['name'] = "AutoPkg " + current_version
    release_data['body'] = release_notes
    release_data['draft'] = False

    # create the release
    create_release = api_call(
        '/repos/%s/releases' % GITHUB_REPO,
        token,
        data=release_data)
    if create_release:
        print "Release successfully created. Server response:"
        pprint(create_release)
        print

        # upload the pkg as a release asset
        new_release_id = create_release['id']
        endpoint = '/repos/%s/releases/%s/assets?name=%s' % (GITHUB_REPO, new_release_id, pkg_filename)
        upload_asset = api_call(
            endpoint,
            token,
            baseurl='https://uploads.github.com',
            data=pkg_data,
            json_data=False,
            additional_headers={'Content-Type': 'application/octet-stream'})
        if upload_asset:
            print "Successfully attached .pkg release asset. Server response:"
            pprint(upload_asset)
            print

    # increment version
    print "Incrementing version to %s.." % next_version
    plist['Version'] = next_version
    plistlib.writePlist(plist, version_plist_path)

    # increment changelog
    new_changelog = "### %s (Unreleased)\n\n" % next_version + new_changelog
    with open(changelog_path, 'w') as fd:
        fd.write(new_changelog)

    # commit and push increment
    subprocess.check_call(['git', 'add', version_plist_path, changelog_path])
    subprocess.check_call(['git', 'commit', '-m', 'Bumping to v%s for development.' % next_version])
    subprocess.check_call(['git', 'push', 'origin', 'master'])

    # clean up
    rmtree(recipes_dir)


if __name__ == '__main__':
    main()

########NEW FILE########
