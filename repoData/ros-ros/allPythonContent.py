__FILENAME__ = make_pydev_project
#!/usr/bin/python

# Software License Agreement (BSD License)
#
# Copyright (c) 2010. Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import sys
import os
PKG = os.path.split(os.getcwd())[1]
print("Creating pydev project for package '%s'" % PKG)
import roslib; roslib.load_manifest(PKG)

pathlist = "\n".join(["<path>%s</path>"%path for path in sys.path if os.path.exists(path)])

pydev_project= '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<?eclipse-pydev version="1.0"?>

<pydev_project>
<pydev_property name="org.python.pydev.PYTHON_PROJECT_INTERPRETER">Default</pydev_property>
<pydev_property name="org.python.pydev.PYTHON_PROJECT_VERSION">python 2.6</pydev_property>
<pydev_pathproperty name="org.python.pydev.PROJECT_EXTERNAL_SOURCE_PATH">
%s
</pydev_pathproperty>
</pydev_project>
'''%pathlist

print("Writing .pydevproject, adding %d modules" % len(sys.path))
f = open(".pydevproject","w")
f.write(pydev_project)
f.close()

########NEW FILE########
__FILENAME__ = check_same_directories
#!/usr/bin/env python

# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following
# disclaimer in the documentation and/or other materials provided
# with the distribution.
# * Neither the name of Willow Garage, Inc. nor the names of its
# contributors may be used to endorse or promote products derived
# from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


# Simple script to check whether two directories are the same.  I'm doing
# it in this script because the following command-line invocation produces
# a syntax error for reasons that I don't understand:
#
#  python -c 'import os; if os.path.realpath("/u/gerkey/code/ros/ros/core/rosconsole") != os.path.realpath("/u/gerkey/code/ros/ros/core/rosconsole"): raise Exception'

import sys, os

if __name__ == '__main__':
  if len(sys.argv) != 3:
    raise Exception
  if os.path.realpath(sys.argv[1]) != os.path.realpath(sys.argv[2]):
    raise Exception

########NEW FILE########
__FILENAME__ = download_checkmd5
#!/usr/bin/env python

# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following
# disclaimer in the documentation and/or other materials provided
# with the distribution.
# * Neither the name of Willow Garage, Inc. nor the names of its
# contributors may be used to endorse or promote products derived
# from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


NAME="download_checkmd5.py"

import urllib, hashlib, os, sys
from optparse import OptionParser

def main():
  parser = OptionParser(usage="usage: %prog URI dest [md5sum]", prog=NAME)
  options, args = parser.parse_args()
  md5sum = None
  if len(args) == 2:
    uri, dest = args
  elif len(args) == 3:
    uri, dest, md5sum = args
  else:
    parser.error("wrong number of arguments")

  # Create intermediate directories as necessary, #2970
  d = os.path.dirname(dest)
  if len(d) and not os.path.exists(d):
    os.makedirs(d)

  fresh = False
  if not os.path.exists(dest):
    sys.stdout.write('[rosbuild] Downloading %s to %s...'%(uri, dest))
    sys.stdout.flush()
    urllib.urlretrieve(uri, dest)
    sys.stdout.write('Done\n')
    fresh = True

  if md5sum:
    m = hashlib.md5(open(dest).read())
    d = m.hexdigest()

    print('[rosbuild] Checking md5sum on %s'%(dest))
  
    if d != md5sum:
      if not fresh:
        print('[rosbuild] WARNING: md5sum mismatch (%s != %s); re-downloading file %s' % (d, md5sum, dest))
        os.remove(dest)

        # Try one more time
        urllib.urlretrieve(uri, dest)
        m = hashlib.md5(open(dest).read())
        d = m.hexdigest()
    
      if d != md5sum:
        print('[rosbuild] ERROR: md5sum mismatch (%s != %s) on %s; aborting' % (d, md5sum, dest))
        return 1

  return 0


if __name__ == '__main__':
  sys.exit(main())

########NEW FILE########
__FILENAME__ = count_cores
#!/usr/bin/env python

import os
print(os.sysconf(os.sysconf_names['SC_NPROCESSORS_ONLN']))

########NEW FILE########
__FILENAME__ = exceptions
# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$
# $Author$

"""
Provides the L{ROSLibException} class, which is common to many roslib libraries.
"""

class ROSLibException(Exception):
    """
    Base class for exceptions in roslib    
    """
    pass

########NEW FILE########
__FILENAME__ = gentools
#! /usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$
# $Author$

"""
Library for supporting message and service generation for all ROS
client libraries. This is mainly responsible for calculating the
md5sums and message definitions of classes.
"""

# NOTE: this should not contain any rospy-specific code. The rospy
# generator library is rospy.genpy.

import sys

try:
    from cStringIO import StringIO # Python 2.x
except ImportError:
    from io import StringIO # Python 3.x

import rospkg

import roslib.msgs
from roslib.msgs import MsgSpecException
import roslib.names
import roslib.srvs

# name of the Header type as gentools knows it
_header_type_name = 'std_msgs/Header'

def _add_msgs_depends(rospack, spec, deps, package_context):
    """
    Add the list of message types that spec depends on to depends.
    @param spec: message to compute dependencies for
    @type  spec: roslib.msgs.MsgSpec/roslib.srvs.SrvSpec
    @param deps [str]: list of dependencies. This list will be updated
    with the dependencies of spec when the method completes
    @type  deps: [str]
    @raise KeyError for invalid dependent types due to missing package dependencies.
    """
    def _get_valid_packages(package_context, rospack):
        valid_packages = ['', package_context]
        try:
            valid_packages = valid_packages + rospack.get_depends(package_context, implicit=True)
        except rospkg.ResourceNotFound:
            # this happens in dynamic generation situations where the
            # package is not present.  we soft fail here because we assume
            # missing messages will be caught later during lookup.
            pass
        return valid_packages

    valid_packages = None

    for t in spec.types:
        t = roslib.msgs.base_msg_type(t)
        if not roslib.msgs.is_builtin(t):
            t_package, t_base = roslib.names.package_resource_name(t)

            # special mapping for header
            if t == roslib.msgs.HEADER:
                # have to re-names Header
                deps.append(_header_type_name)

            if roslib.msgs.is_registered(t):
                depspec = roslib.msgs.get_registered(t)
                if t != roslib.msgs.HEADER:
                    if '/' in t:
                        deps.append(t)
                    else:
                        deps.append(package_context+'/'+t)
            else:
                if valid_packages is None:
                    valid_packages = _get_valid_packages(package_context, rospack)
                if t_package in valid_packages:
                    # if we are allowed to load the message, load it.
                    key, depspec = roslib.msgs.load_by_type(t, package_context)
                    if t != roslib.msgs.HEADER:
                      deps.append(key)
                    roslib.msgs.register(key, depspec)
                else:
                    # not allowed to load the message, so error.
                    raise KeyError(t)
            _add_msgs_depends(rospack, depspec, deps, package_context)

def compute_md5_text(get_deps_dict, spec, rospack=None):
    """
    Compute the text used for md5 calculation. MD5 spec states that we
    removes comments and non-meaningful whitespace. We also strip
    packages names from type names. For convenience sake, constants are
    reordered ahead of other declarations, in the order that they were
    originally defined.

    @return: text for ROS MD5-processing
    @rtype: str
    """
    uniquedeps = get_deps_dict['uniquedeps']
    package = get_deps_dict['package']
    # #1554: need to suppress computation of files in dynamic generation case
    compute_files = 'files' in get_deps_dict

    buff = StringIO()

    for c in spec.constants:
        buff.write("%s %s=%s\n"%(c.type, c.name, c.val_text))
    for type_, name in zip(spec.types, spec.names):
        base_msg_type = roslib.msgs.base_msg_type(type_)
        # md5 spec strips package names
        if roslib.msgs.is_builtin(base_msg_type):
            buff.write("%s %s\n"%(type_, name))
        else:
            # recursively generate md5 for subtype.  have to build up
            # dependency representation for subtype in order to
            # generate md5

            # - ugly special-case handling of Header
            if base_msg_type == roslib.msgs.HEADER:
                base_msg_type = _header_type_name

            sub_pkg, _ = roslib.names.package_resource_name(base_msg_type)
            sub_pkg = sub_pkg or package
            sub_spec = roslib.msgs.get_registered(base_msg_type, package)
            sub_deps = get_dependencies(sub_spec, sub_pkg, compute_files=compute_files, rospack=rospack)
            sub_md5 = compute_md5(sub_deps, rospack)
            buff.write("%s %s\n"%(sub_md5, name))

    return buff.getvalue().strip() # remove trailing new line

def _compute_hash(get_deps_dict, hash, rospack=None):
    """
    subroutine of compute_md5()
    @param get_deps_dict: dictionary returned by get_dependencies call
    @type  get_deps_dict: dict
    @param hash: hash instance
    @type  hash: hash instance
    """
    # accumulate the hash
    # - root file
    from roslib.msgs import MsgSpec
    from roslib.srvs import SrvSpec
    spec = get_deps_dict['spec']
    if isinstance(spec, MsgSpec):
        hash.update(compute_md5_text(get_deps_dict, spec, rospack=rospack).encode())
    elif isinstance(spec, SrvSpec):
        hash.update(compute_md5_text(get_deps_dict, spec.request, rospack=rospack).encode())
        hash.update(compute_md5_text(get_deps_dict, spec.response, rospack=rospack).encode())
    else:
        raise Exception("[%s] is not a message or service"%spec)
    return hash.hexdigest()

def _compute_hash_v1(get_deps_dict, hash):
    """
    subroutine of compute_md5_v1()
    @param get_deps_dict: dictionary returned by get_dependencies call
    @type  get_deps_dict: dict
    @param hash: hash instance
    @type  hash: hash instance
    """
    uniquedeps = get_deps_dict['uniquedeps']
    spec = get_deps_dict['spec']
    # accumulate the hash
    # - root file
    hash.update(spec.text)
    # - dependencies
    for d in uniquedeps:
        hash.update(roslib.msgs.get_registered(d).text)
    return hash.hexdigest()

def compute_md5_v1(get_deps_dict):
    """
    Compute original V1 md5 hash for message/service. This was replaced with V2 in ROS 0.6.
    @param get_deps_dict: dictionary returned by get_dependencies call
    @type  get_deps_dict: dict
    @return: md5 hash
    @rtype: str
    """
    import hashlib
    return _compute_hash_v1(get_deps_dict, hashlib.md5())

def compute_md5(get_deps_dict, rospack=None):
    """
    Compute md5 hash for message/service
    @param get_deps_dict dict: dictionary returned by get_dependencies call
    @type  get_deps_dict: dict
    @return: md5 hash
    @rtype: str
    """
    try:
        # md5 is deprecated in Python 2.6 in favor of hashlib, but hashlib is
        # unavailable in Python 2.4
        import hashlib
        return _compute_hash(get_deps_dict, hashlib.md5(), rospack=rospack)
    except ImportError:
        import md5
        return _compute_hash(get_deps_dict, md5.new(), rospack=rospack)

## alias
compute_md5_v2 = compute_md5

def compute_full_text(get_deps_dict):
    """
    Compute full text of message/service, including text of embedded
    types.  The text of the main msg/srv is listed first. Embedded
    msg/srv files are denoted first by an 80-character '=' separator,
    followed by a type declaration line,'MSG: pkg/type', followed by
    the text of the embedded type.

    @param get_deps_dict dict: dictionary returned by get_dependencies call
    @type  get_deps_dict: dict
    @return: concatenated text for msg/srv file and embedded msg/srv types.
    @rtype:  str
    """
    buff = StringIO()
    sep = '='*80+'\n'

    # write the text of the top-level type
    buff.write(get_deps_dict['spec'].text)
    buff.write('\n')
    # append the text of the dependencies (embedded types)
    for d in get_deps_dict['uniquedeps']:
        buff.write(sep)
        buff.write("MSG: %s\n"%d)
        buff.write(roslib.msgs.get_registered(d).text)
        buff.write('\n')
    # #1168: remove the trailing \n separator that is added by the concatenation logic
    return buff.getvalue()[:-1]

def get_file_dependencies(f, stdout=sys.stdout, stderr=sys.stderr, rospack=None):
    """
    Compute dependencies of the specified message/service file
    @param f: message or service file to get dependencies for
    @type  f: str
    @param stdout pipe: stdout pipe
    @type  stdout: file
    @param stderr pipe: stderr pipe
    @type  stderr: file
    @return: 'files': list of files that \a file depends on,
    'deps': list of dependencies by type, 'spec': Msgs/Srvs
    instance.
    @rtype: dict
    """
    package = rospkg.get_package_name(f)
    spec = None
    if f.endswith(roslib.msgs.EXT):
        _, spec = roslib.msgs.load_from_file(f)
    elif f.endswith(roslib.srvs.EXT):
        _, spec = roslib.srvs.load_from_file(f)
    else:
        raise Exception("[%s] does not appear to be a message or service"%spec)
    return get_dependencies(spec, package, stdout, stderr, rospack=rospack)

def get_dependencies(spec, package, compute_files=True, stdout=sys.stdout, stderr=sys.stderr, rospack=None):
    """
    Compute dependencies of the specified Msgs/Srvs
    @param spec: message or service instance
    @type  spec: L{roslib.msgs.MsgSpec}/L{roslib.srvs.SrvSpec}
    @param package: package name
    @type  package: str
    @param stdout: (optional) stdout pipe
    @type  stdout: file
    @param stderr: (optional) stderr pipe
    @type  stderr: file
    @param compute_files: (optional, default=True) compute file
    dependencies of message ('files' key in return value)
    @type  compute_files: bool
    @return: dict:
      * 'files': list of files that \a file depends on
      * 'deps': list of dependencies by type
      * 'spec': Msgs/Srvs instance.
      * 'uniquedeps': list of dependencies with duplicates removed,
      * 'package': package that dependencies were generated relative to.
    @rtype: dict
    """

    # #518: as a performance optimization, we're going to manually control the loading
    # of msgs instead of doing package-wide loads.

    #we're going to manipulate internal apis of msgs, so have to
    #manually init
    roslib.msgs._init()

    deps = []
    try:
        if not rospack:
            rospack = rospkg.RosPack()
        if isinstance(spec, roslib.msgs.MsgSpec):
            _add_msgs_depends(rospack, spec, deps, package)
        elif isinstance(spec, roslib.srvs.SrvSpec):
            _add_msgs_depends(rospack, spec.request, deps, package)
            _add_msgs_depends(rospack, spec.response, deps, package)
        else:
            raise MsgSpecException("spec does not appear to be a message or service")
    except KeyError as e:
        raise MsgSpecException("Cannot load type %s.  Perhaps the package is missing a dependency."%(str(e)))

    # convert from type names to file names

    if compute_files:
        files = {}
        for d in set(deps):
            d_pkg, t = roslib.names.package_resource_name(d)
            d_pkg = d_pkg or package # convert '' -> local package
            files[d] = roslib.msgs.msg_file(d_pkg, t)
    else:
        files = None

    # create unique dependency list
    uniquedeps = []
    for d in deps:
        if not d in uniquedeps:
            uniquedeps.append(d)

    if compute_files:
        return { 'files': files, 'deps': deps, 'spec': spec, 'package': package, 'uniquedeps': uniquedeps }
    else:
        return { 'deps': deps, 'spec': spec, 'package': package, 'uniquedeps': uniquedeps }




########NEW FILE########
__FILENAME__ = launcher
#! /usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
Python path loader for python scripts and applications. Paths are
derived from dependency structure declared in ROS manifest files.
"""

import os
import sys

import rospkg

# bootstrapped keeps track of which packages we've loaded so we don't
# update the path multiple times
_bootstrapped = []
# _rospack is our cache of ROS package data
_rospack = rospkg.RosPack()

def get_depends(package, rospack):
    vals = rospack.get_depends(package, implicit=True)
    return [v for v in vals if not rospack.get_manifest(v).is_catkin]

def load_manifest(package_name, bootstrap_version="0.7"):
    """
    Update the Python sys.path with package's dependencies

    :param package_name: name of the package that load_manifest() is being called from, ``str``
    """
    if package_name in _bootstrapped:
        return
    sys.path = _generate_python_path(package_name, _rospack) + sys.path
    
def _append_package_paths(manifest_, paths, pkg_dir):
    """
    Added paths for package to paths
    :param manifest_: package manifest, ``Manifest``
    :param pkg_dir: package's filesystem directory path, ``str``
    :param paths: list of paths, ``[str]``
    """
    exports = manifest_.get_export('python','path')
    if exports:
        for export in exports:
            if ':' in export:
                export = export.split(':')
            else:
                export = [export]
            for e in export:
                paths.append(e.replace('${prefix}', pkg_dir))
    else:
        dirs = [os.path.join(pkg_dir, d) for d in ['src', 'lib']]
        paths.extend([d for d in dirs if os.path.isdir(d)])
    
def _generate_python_path(pkg, rospack):
    """
    Recursive subroutine for building dependency list and python path
    :raises: :exc:`rospkg.ResourceNotFound` If an error occurs while attempting to load package or dependencies
    """
    if pkg in _bootstrapped:
        return []

    # short-circuit if this is a catkin-ized package
    m = rospack.get_manifest(pkg)
    if m.is_catkin:
        _bootstrapped.append(pkg)
        return []

    packages = get_depends(pkg, rospack) 
    packages.append(pkg)

    paths = []
    try:
        for p in packages:
            m = rospack.get_manifest(p)
            d = rospack.get_path(p)
            _append_package_paths(m, paths, d)
            _bootstrapped.append(p)
    except:
        if pkg in _bootstrapped:
            _bootstrapped.remove(pkg)
        raise
    return paths

########NEW FILE########
__FILENAME__ = manifest
#! /usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$
# $Author$

"""
Warning: do not use this library.  It is unstable and most of the routines
here have been superceded by other libraries (e.g. rospkg).  These
routines will likely be *deleted* in future releases.
"""

import sys
import os
import getopt

import roslib.packages

MANIFEST_FILE = 'manifest.xml'

import roslib.manifestlib
# re-export symbols for backwards compatibility
from roslib.manifestlib import ManifestException, Depend, Export, ROSDep, VersionControl

class Manifest(roslib.manifestlib._Manifest):
    """
    Object representation of a ROS manifest file
    """
    __slots__ = []
    def __init__(self):
        """
        Initialize new empty manifest.
        """
        super(Manifest, self).__init__('package')
        
    def get_export(self, tag, attr):
        """
        @return: exports that match the specified tag and attribute, e.g. 'python', 'path'
        @rtype: [L{Export}]
        """
        return [e.get(attr) for e in self.exports if e.tag == tag if e.get(attr) is not None]

def _manifest_file_by_dir(package_dir, required=True, env=None):
    """
    @param package_dir: path to package directory
    @type  package_dir: str
    @param env: environment dictionary
    @type  env: dict
    @param required: require that the directory exist
    @type  required: bool
    @return: path to manifest file of package
    @rtype:  str
    @raise InvalidROSPkgException: if required is True and manifest file cannot be located
    """
    if env is None:
        env = os.environ
    try:
        p = os.path.join(package_dir, MANIFEST_FILE)
        if not required and not os.path.exists(p):
            return p
        if not os.path.isfile(p):
            raise roslib.packages.InvalidROSPkgException("""
Package '%(package_dir)s' is improperly configured: no manifest file is present.
"""%locals())
        return p
    except roslib.packages.InvalidROSPkgException as e:
        if required:
            raise

def manifest_file(package, required=True, env=None):
    """
    @param package str: package name
    @type  package: str
    @param env: override os.environ dictionary
    @type  env: dict
    @param required: require that the directory exist
    @type  required: bool
    @return: path to manifest file of package
    @rtype: str
    @raise InvalidROSPkgException: if required is True and manifest file cannot be located
    """
    # ros_root needs to be determined from the environment or else
    # everything breaks when trying to launch nodes via ssh where the
    # path isn't setup correctly.
    if env is None:
        env = os.environ
    d = roslib.packages.get_pkg_dir(package, required, ros_root=env['ROS_ROOT']) 
    return _manifest_file_by_dir(d, required=required, env=env)

def load_manifest(package):
    """
    Load manifest for specified package.
    @param pacakge: package name
    @type  package: str
    @return: Manifest instance
    @rtype: L{Manifest}
    @raise InvalidROSPkgException: if package is unknown
    """
    return parse_file(manifest_file(package))
    
def parse_file(file):
    """
    Parse manifest.xml file
    @param file: manifest.xml file path
    @type  file: str
    @return: Manifest instance
    @rtype: L{Manifest}
    """
    return roslib.manifestlib.parse_file(Manifest(), file)

def parse(string, filename='string'):
    """
    Parse manifest.xml string contents
    @param string: manifest.xml contents
    @type  string: str
    @return: Manifest instance
    @rtype: L{Manifest}
    """
    v = roslib.manifestlib.parse(Manifest(), string, filename)
    if v.version:
        raise ManifestException("<version> tag is not valid in a package manifest.xml file")
    return v

########NEW FILE########
__FILENAME__ = manifestlib
#! /usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$
# $Author$

"""
Internal library for processing 'manifest' files, i.e. manifest.xml and stack.xml.
For external code apis, see L{roslib.manifest} and L{roslib.stack_manifest}.
"""

import sys
import os
import xml.dom
import xml.dom.minidom as dom

import roslib.exceptions

# stack.xml and manifest.xml have the same internal tags right now
REQUIRED = ['author', 'license']
ALLOWXHTML = ['description']
OPTIONAL = ['logo', 'url', 'brief', 'description', 'status',
            'notes', 'depend', 'rosdep', 'export', 'review',
            'versioncontrol', 'platform', 'version', 'rosbuild2',
            'catkin']
VALID = REQUIRED + OPTIONAL

class ManifestException(roslib.exceptions.ROSLibException): pass

def get_nodes_by_name(n, name):
    return [t for t in n.childNodes if t.nodeType == t.ELEMENT_NODE and t.tagName == name]
    
def check_optional(name, allowXHTML=False, merge_multiple=False):
    """
    Validator for optional elements.
    @raise ManifestException: if validation fails
    """
    def check(n, filename):
        n = get_nodes_by_name(n, name)
        if len(n) > 1 and not merge_multiple:
            raise ManifestException("Invalid manifest file: must have a single '%s' element"%name)
        if n:
            values = []
            for child in n:
                if allowXHTML:
                    values.append(''.join([x.toxml() for x in child.childNodes]))
                else:
                    values.append(_get_text(child.childNodes).strip())
            return ', '.join(values)
    return check

def check_required(name, allowXHTML=False, merge_multiple=False):
    """
    Validator for required elements.
    @raise ManifestException: if validation fails
    """
    def check(n, filename):
        n = get_nodes_by_name(n, name)
        if not n:
            #print >> sys.stderr, "Invalid manifest file[%s]: missing required '%s' element"%(filename, name)
            return ''
        if len(n) != 1 and not merge_multiple:
            raise ManifestException("Invalid manifest file: must have only one '%s' element"%name)
        values = []
        for child in n:
            if allowXHTML:
                values.append(''.join([x.toxml() for x in child.childNodes]))
            else:
                values.append(_get_text(child.childNodes).strip())
        return ', '.join(values)
    return check

def check_platform(name):
    """
    Validator for manifest platform.
    @raise ManifestException: if validation fails
    """
    def check(n, filename):
        platforms = get_nodes_by_name(n, name)
        try:
            vals = [(p.attributes['os'].value, p.attributes['version'].value, p.getAttribute('notes')) for p in platforms]
        except KeyError as e:
            raise ManifestException("<platform> tag is missing required '%s' attribute"%str(e))
        return [Platform(*v) for v in vals]
    return check

def check_depends(name):
    """
    Validator for manifest depends.
    @raise ManifestException: if validation fails
    """
    def check(n, filename):
        nodes = get_nodes_by_name(n, name)
        # TDS 20110419:  this is a hack.
        # rosbuild2 has a <depend thirdparty="depname"/> tag,
        # which is confusing this subroutine with 
        # KeyError: 'package'
        # for now, explicitly don't consider thirdparty depends
        depends = [e.attributes for e in nodes if 'thirdparty' not in e.attributes.keys()]
        try:
            packages = [d['package'].value for d in depends]
        except KeyError:
            raise ManifestException("Invalid manifest file: depends is missing 'package' attribute")

        return [Depend(p) for p in packages]
    return check

def check_stack_depends(name):
    """
    Validator for stack depends.
    @raise ManifestException: if validation fails
    """
    def check(n, filename):
        nodes = get_nodes_by_name(n, name)
        depends = [e.attributes for e in nodes]
        packages = [d['stack'].value for d in depends]
        return [StackDepend(p) for p in packages]
    return check

def check_rosdeps(name):
    """
    Validator for stack rosdeps.    
    @raise ManifestException: if validation fails
    """
    def check(n, filename):
        nodes = get_nodes_by_name(n, name)
        rosdeps = [e.attributes for e in nodes]
        names = [d['name'].value for d in rosdeps]
        return [ROSDep(n) for n in names]
    return check

def _attrs(node):
    attrs = {}
    for k in node.attributes.keys(): 
        attrs[k] = node.attributes.get(k).value
    return attrs
    
def check_exports(name):
    def check(n, filename):
        ret_val = []
        for e in get_nodes_by_name(n, name):
            elements = [c for c in e.childNodes if c.nodeType == c.ELEMENT_NODE]
            ret_val.extend([Export(t.tagName, _attrs(t), _get_text(t.childNodes)) for t in elements])
        return ret_val 
    return check

def check_versioncontrol(name):
    def check(n, filename):
        e = get_nodes_by_name(n, name)
        if not e:
            return None
        # note: 'url' isn't actually required, but as we only support type=svn it implicitly is for now
        return VersionControl(e[0].attributes['type'].value, e[0].attributes['url'].value)
    return check

def check(name, merge_multiple=False):
    if name == 'depend':
        return check_depends('depend')
    elif name == 'export':
        return check_exports('export')
    elif name == 'versioncontrol':
        return check_versioncontrol('versioncontrol')
    elif name == 'rosdep':
        return check_rosdeps('rosdep')
    elif name == 'platform':
        return check_platform('platform')
    elif name in REQUIRED:
        if name in ALLOWXHTML:
            return check_required(name, True, merge_multiple)
        return check_required(name, merge_multiple=merge_multiple)
    elif name in OPTIONAL:
        if name in ALLOWXHTML:
            return check_optional(name, True, merge_multiple)
        return check_optional(name, merge_multiple=merge_multiple)
    
class Export(object):
    """
    Manifest 'export' tag
    """
    
    def __init__(self, tag, attrs, str):
        """
        Create new export instance.
        @param tag: name of the XML tag
        @type  tag: str
        @param attrs: dictionary of XML attributes for this export tag
        @type  attrs: dict
        @param str: string value contained by tag, if any
        @type  str: str
        """
        self.tag = tag
        self.attrs = attrs
        self.str = str

    def get(self, attr):
        """
        @return: value of attribute or None if attribute not set
        @rtype:  str
        """
        return self.attrs.get(attr, None)
    def xml(self):
        """
        @return: export instance represented as manifest XML
        @rtype: str
        """        
        attrs = ' '.join([' %s="%s"'%(k,v) for k,v in self.attrs.items()]) #py3k
        if self.str:
            return '<%s%s>%s</%s>'%(self.tag, attrs, self.str, self.tag)
        else:
            return '<%s%s />'%(self.tag, attrs)
        
class Platform(object):
    """
    Manifest 'platform' tag
    """
    __slots__ = ['os', 'version', 'notes']

    def __init__(self, os, version, notes=None):
        """
        Create new depend instance.
        @param os: OS name. must be non-empty
        @type  os: str
        @param version: OS version. must be non-empty
        @type  version: str
        @param notes: (optional) notes about platform support
        @type  notes: str
        """
        if not os:
            raise ValueError("bad 'os' attribute")
        if not version:
            raise ValueError("bad 'version' attribute")
        self.os = os
        self.version = version
        self.notes = notes
        
    def __str__(self):
        return "%s %s"%(self.os, self.version)
    def __repr__(self):
        return "%s %s"%(self.os, self.version)
    def __eq__(self, obj):
        """
        Override equality test. notes *are* considered in the equality test.
        """
        if not isinstance(obj, Platform):
            return False
        return self.os == obj.os and self.version == obj.version and self.notes == obj.notes 
    def xml(self):
        """
        @return: instance represented as manifest XML
        @rtype: str
        """
        if self.notes is not None:
            return '<platform os="%s" version="%s" notes="%s"/>'%(self.os, self.version, self.notes)
        else:
            return '<platform os="%s" version="%s"/>'%(self.os, self.version)

class Depend(object):
    """
    Manifest 'depend' tag
    """
    __slots__ = ['package']

    def __init__(self, package):
        """
        Create new depend instance.
        @param package: package name. must be non-empty
        @type  package: str
        """
        if not package:
            raise ValueError("bad 'package' attribute")
        self.package = package
    def __str__(self):
        return self.package
    def __repr__(self):
        return self.package
    def __eq__(self, obj):
        if not isinstance(obj, Depend):
            return False
        return self.package == obj.package 
    def xml(self):
        """
        @return: depend instance represented as manifest XML
        @rtype: str
        """
        return '<depend package="%s" />'%self.package
        
class StackDepend(object):
    """
    Stack Manifest 'depend' tag
    """
    __slots__ = ['stack', 'annotation']

    def __init__(self, stack):
        """
        @param stack: stack name. must be non-empty
        @type  stack: str
        """
        if not stack:
            raise ValueError("bad 'stack' attribute")
        self.stack = stack
        self.annotation = None
        
    def __str__(self):
        return self.stack
    def __repr__(self):
        return self.stack
    def __eq__(self, obj):
        if not isinstance(obj, StackDepend):
            return False
        return self.stack == obj.stack 
    def xml(self):
        """
        @return: stack depend instance represented as stack manifest XML
        @rtype: str
        """
        if self.annotation:
            return '<depend stack="%s" /> <!-- %s -->'%(self.stack, self.annotation)
        else:
            return '<depend stack="%s" />'%self.stack            

class ROSDep(object):
    """
    Manifest 'rosdep' tag    
    """
    __slots__ = ['name',]

    def __init__(self, name):
        """
        Create new rosdep instance.
        @param name: dependency name. Must be non-empty.
        @type  name: str
        """
        if not name:
            raise ValueError("bad 'name' attribute")
        self.name = name
    def xml(self):
        """
        @return: rosdep instance represented as manifest XML
        @rtype: str
        """        
        return '<rosdep name="%s" />'%self.name

class VersionControl(object):
    """
    Manifest 'versioncontrol' tag
    """
    __slots__ = ['type', 'url']

    def __init__(self, type_, url):
        """
        @param type_: version control type (e.g. 'svn'). must be non empty
        @type  type_: str
        @param url: URL associated with version control. must be non empty
        @type  url: str
        """
        def is_string_type(obj):
            try:
                return isinstance(obj, basestring)
            except NameError:
                return isinstance(obj, str)

        if not type_ or not is_string_type(type_):
            raise ValueError("bad 'type' attribute")
        if not url is None and not is_string_type(url):
            raise ValueError("bad 'url' attribute")
        self.type = type_
        self.url = url
    def xml(self):
        """
        @return: versioncontrol instance represented as manifest XML
        @rtype: str
        """        
        if self.url:
            return '<versioncontrol type="%s" url="%s" />'%(self.type, self.url)
        else:
            return '<versioncontrol type="%s" />'%self.type
    
class _Manifest(object):
    """
    Object representation of a ROS manifest file
    """
    __slots__ = ['description', 'brief', \
                 'author', 'license', 'license_url', 'url', \
                 'depends', 'rosdeps','platforms',\
                 'logo', 'exports', 'version',\
                 'versioncontrol', 'status', 'notes',\
                 'unknown_tags',\
                 '_type']
    def __init__(self, _type='package'):
        self.description = self.brief = self.author = \
                           self.license = self.license_url = \
                           self.url = self.logo = self.status = \
                           self.version = self.notes = ''
        self.depends = []
        self.rosdeps = []
        self.exports = []
        self.platforms = []
        self._type = _type
        
        # store unrecognized tags during parsing
        self.unknown_tags = []
        
    def __str__(self):
        return self.xml()
    def get_export(self, tag, attr):
        """
        @return: exports that match the specified tag and attribute, e.g. 'python', 'path'
        @rtype: [L{Export}]
        """
        return [e.get(attr) for e in self.exports if e.tag == tag if e.get(attr) is not None]
    def xml(self):
        """
        @return: Manifest instance as ROS XML manifest
        @rtype: str
        """
        if not self.brief:
            desc = "  <description>%s</description>"%self.description
        else:
            desc = '  <description brief="%s">%s</description>'%(self.brief, self.description) 
        author  = "  <author>%s</author>"%self.author
        if self.license_url:
            license = '  <license url="%s">%s</license>'%(self.license_url, self.license)
        else:
            license = "  <license>%s</license>"%self.license
        versioncontrol = url = logo = exports = version = ""
        if self.url:
            url     = "  <url>%s</url>"%self.url
        if self.version:
            version = "  <version>%s</version>"%self.version
        if self.logo:
            logo    = "  <logo>%s</logo>"%self.logo
        depends = '\n'.join(["  %s"%d.xml() for d in self.depends])
        rosdeps = '\n'.join(["  %s"%rd.xml() for rd in self.rosdeps])
        platforms = '\n'.join(["  %s"%p.xml() for p in self.platforms])
        if self.exports:
            exports = '  <export>\n' + '\n'.join(["  %s"%e.xml() for e in self.exports]) + '  </export>'
        if self.versioncontrol:
            versioncontrol = "  %s"%self.versioncontrol.xml()
        if self.status or self.notes:
            review = '  <review status="%s" notes="%s" />'%(self.status, self.notes)


        fields = filter(lambda x: x,
                        [desc, author, license, review, url, logo, depends,
                         rosdeps, platforms, exports, versioncontrol, version])
        return "<%s>\n"%self._type + "\n".join(fields) + "\n</%s>"%self._type

def _get_text(nodes):
    """
    DOM utility routine for getting contents of text nodes
    """
    return "".join([n.data for n in nodes if n.nodeType == n.TEXT_NODE])

def parse_file(m, file):
    """
    Parse manifest file (package, stack)
    @param m: field to populate
    @type  m: L{_Manifest}
    @param file: manifest.xml file path
    @type  file: str
    @return: return m, populated with parsed fields
    @rtype: L{_Manifest}
    """
    if not file:
        raise ValueError("Missing manifest file argument")
    if not os.path.isfile(file):
        raise ValueError("Invalid/non-existent manifest file: %s"%file)
    with open(file, 'r') as f:
        text = f.read()
    try:
        return parse(m, text, file)
    except ManifestException as e:
        raise ManifestException("Invalid manifest file [%s]: %s"%(os.path.abspath(file), e))

def parse(m, string, filename='string'):
    """
    Parse manifest.xml string contents
    @param string: manifest.xml contents
    @type  string: str
    @param m: field to populate
    @type  m: L{_Manifest}
    @return: return m, populated with parsed fields
    @rtype: L{_Manifest}
    """
    try:
        d = dom.parseString(string)
    except Exception as e:
        raise ManifestException("invalid XML: %s"%e)
    
    p = get_nodes_by_name(d, m._type)
    if len(p) != 1:
        raise ManifestException("manifest must have a single '%s' element"%m._type)
    p = p[0]
    m.description = check('description')(p, filename)
    m.brief = ''
    try:
        tag = get_nodes_by_name(p, 'description')[0]
        m.brief = tag.getAttribute('brief') or ''
    except:
        # means that 'description' tag is missing
        pass
    #TODO: figure out how to multiplex
    if m._type == 'package':
        m.depends = check_depends('depend')(p, filename)
    elif m._type == 'stack':
        m.depends = check_stack_depends('depend')(p, filename)
    elif m._type == 'app':
        # not implemented yet
        pass
    m.rosdeps = check('rosdep')(p, filename)    
    m.platforms = check('platform')(p, filename)    
    m.exports = check('export')(p, filename)
    m.versioncontrol = check('versioncontrol')(p,filename)
    m.license = check('license')(p, filename)
    m.license_url = ''
    try:
        tag = get_nodes_by_name(p, 'license')[0]
        m.license_url = tag.getAttribute('url') or ''
    except:
        pass #manifest is missing required 'license' tag
  
    m.status='unreviewed'
    try:
        tag = get_nodes_by_name(p, 'review')[0]
        m.status=tag.getAttribute('status') or ''
    except:
        pass #manifest is missing optional 'review status' tag

    m.notes=''
    try:
        tag = get_nodes_by_name(p, 'review')[0]
        m.notes=tag.getAttribute('notes') or ''
    except:
        pass #manifest is missing optional 'review notes' tag

    m.author = check('author', True)(p, filename)
    m.url = check('url')(p, filename)
    m.version = check('version')(p, filename)
    m.logo = check('logo')(p, filename)

    # do some validation on what we just parsed
    if m._type == 'stack':
        if m.exports:
            raise ManifestException("stack manifests are not allowed to have exports")
        if m.rosdeps:
            raise ManifestException("stack manifests are not allowed to have rosdeps") 

    # store unrecognized tags
    m.unknown_tags = [e for e in p.childNodes if e.nodeType == e.ELEMENT_NODE and e.tagName not in VALID]
    return m

########NEW FILE########
__FILENAME__ = message
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$

"""
Support library for Python autogenerated message files. This defines
the Message base class used by genmsg_py as well as support
libraries for type checking and retrieving message classes by type
name.
"""

import os
import sys
import rospkg
import roslib

import genmsg
import genpy.message #for wrapping get_message_class, get_service_class

# forward a bunch of old symbols from genpy for backwards compat
from genpy import Message, DeserializationError, SerializationError, \
     Time, Duration, TVal
from genpy.message import get_printable_message_args, fill_message_args
from genpy.message import check_type, strify_message

def _get_message_or_service_class(type_str, message_type, reload_on_error=False):
    ## parse package and local type name for import
    package, base_type = genmsg.package_resource_name(message_type)
    if not package:
        if base_type == 'Header':
            package = 'std_msgs'
        else:
            raise ValueError("message type is missing package name: %s"%str(message_type))
    pypkg = val = None
    try: 
        # bootstrap our sys.path
        roslib.launcher.load_manifest(package)
        # import the package and return the class
        pypkg = __import__('%s.%s'%(package, type_str))
        val = getattr(getattr(pypkg, type_str), base_type)
    except rospkg.ResourceNotFound:
        val = None
    except ImportError:
        val = None
    except AttributeError:
        val = None

    # this logic is mainly to support rosh, so that a user doesn't
    # have to exit a shell just because a message wasn't built yet
    if val is None and reload_on_error:
        try:
            if pypkg:
                reload(pypkg)
            val = getattr(getattr(pypkg, type_str), base_type)
        except:
            val = None
    return val
        
## cache for get_message_class
_message_class_cache = {}

## cache for get_service_class
_service_class_cache = {}

def get_message_class(message_type, reload_on_error=False):
    if message_type in _message_class_cache:
        return _message_class_cache[message_type]
    # try w/o bootstrapping
    cls = genpy.message.get_message_class(message_type, reload_on_error=reload_on_error)
    if cls is None:
        # try old loader w/ bootstrapping
        cls = _get_message_or_service_class('msg', message_type, reload_on_error=reload_on_error)
    if cls:
        _message_class_cache[message_type] = cls
    return cls

def get_service_class(service_type, reload_on_error=False):
    if service_type in _service_class_cache:
        return _service_class_cache[service_type]
    cls = genpy.message.get_service_class(service_type, reload_on_error=reload_on_error)
    # try w/o bootstrapping
    if cls is None:
        # try old loader w/ bootstrapping
        cls = _get_message_or_service_class('srv', service_type, reload_on_error=reload_on_error)
    if cls:
        _service_class_cache[service_type] = cls
    return cls

########NEW FILE########
__FILENAME__ = msgs
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$
# $Author$

from __future__ import print_function

"""
Warning: do not use this library.  It is unstable and most of the routines
here have been superceded by other libraries (e.g. genmsg).  These
routines will likely be *deleted* in future releases.
"""

try:
    from cStringIO import StringIO # Python 2.x
except ImportError:
    from io import StringIO # Python 3.x

import os
import sys
import string

import rospkg

import roslib.manifest
import roslib.packages
import roslib.names
import roslib.resources

VERBOSE = False

## @return: True if msg-related scripts should print verbose output
def is_verbose():
    return VERBOSE

## set whether msg-related scripts should print verbose output
def set_verbose(v):
    global VERBOSE
    VERBOSE = v

EXT = '.msg'
SEP = '/' #e.g. std_msgs/String
## character that designates a constant assignment rather than a field
CONSTCHAR   = '='
COMMENTCHAR = '#'

class MsgSpecException(Exception): pass

#TODOXXX: unit test
def base_msg_type(type_):
    """
    Compute the base data type, e.g. for arrays, get the underlying array item type
    @param type_: ROS msg type (e.g. 'std_msgs/String')
    @type  type_: str
    @return: base type
    @rtype: str
    """
    if type_ is None:
        return None
    if '[' in type_:
        return type_[:type_.find('[')]
    return type_

def resolve_type(type_, package_context):
    """
    Resolve type name based on current package context.

    NOTE: in ROS Diamondback, 'Header' resolves to
    'std_msgs/Header'. In previous releases, it resolves to
    'roslib/Header' (REP 100).

    e.g.::
      resolve_type('String', 'std_msgs') -> 'std_msgs/String'
      resolve_type('String[]', 'std_msgs') -> 'std_msgs/String[]'
      resolve_type('std_msgs/String', 'foo') -> 'std_msgs/String'    
      resolve_type('uint16', 'std_msgs') -> 'uint16'
      resolve_type('uint16[]', 'std_msgs') -> 'uint16[]'
    """
    bt = base_msg_type(type_)
    if bt in BUILTIN_TYPES:
        return type_
    elif bt == 'Header':
        return 'std_msgs/Header'
    elif SEP in type_:
        return type_
    else:
        return "%s%s%s"%(package_context, SEP, type_)    

#NOTE: this assumes that we aren't going to support multi-dimensional

def parse_type(type_):
    """
    Parse ROS message field type
    @param type_: ROS field type
    @type  type_: str
    @return: base_type, is_array, array_length
    @rtype: str, bool, int
    @raise MsgSpecException: if type_ cannot be parsed
    """
    if not type_:
        raise MsgSpecException("Invalid empty type")
    if '[' in type_:
        var_length = type_.endswith('[]')
        splits = type_.split('[')
        if len(splits) > 2:
            raise MsgSpecException("Currently only support 1-dimensional array types: %s"%type_)
        if var_length:
            return type_[:-2], True, None
        else:
            try:
                length = int(splits[1][:-1])
                return splits[0], True, length
            except ValueError:
                raise MsgSpecException("Invalid array dimension: [%s]"%splits[1][:-1])
    else:
        return type_, False, None
   
################################################################################
# name validation 

def is_valid_msg_type(x):
    """
    @return: True if the name is a syntatically legal message type name
    @rtype: bool
    """
    if not x or len(x) != len(x.strip()):
        return False
    base = base_msg_type(x)
    if not roslib.names.is_legal_resource_name(base):
        return False
    #parse array indicies
    x = x[len(base):]
    state = 0
    i = 0
    for c in x:
        if state == 0:
            if c != '[':
                return False
            state = 1 #open
        elif state == 1:
            if c == ']':
                state = 0 #closed
            else:
                try:
                    int(c)
                except:
                    return False
    return state == 0

def is_valid_constant_type(x):
    """
    @return: True if the name is a legal constant type. Only simple types are allowed.
    @rtype: bool
    """
    return x in PRIMITIVE_TYPES

def is_valid_msg_field_name(x):
    """
    @return: True if the name is a syntatically legal message field name
    @rtype: bool
    """
    return roslib.names.is_legal_resource_base_name(x)

# msg spec representation ##########################################

class Constant(object):
    """
    Container class for holding a Constant declaration
    """
    __slots__ = ['type', 'name', 'val', 'val_text']
    
    def __init__(self, type_, name, val, val_text):
        """
        @param type_: constant type
        @type  type_: str 
        @param name: constant name
        @type  name: str
        @param val: constant value
        @type  val: str
        @param val_text: Original text definition of \a val
        @type  val_text: str
        """
        if type is None or name is None or val is None or val_text is None:
            raise ValueError('Constant must have non-None parameters')
        self.type = type_
        self.name = name.strip() #names are always stripped of whitespace
        self.val = val
        self.val_text = val_text

    def __eq__(self, other):
        if not isinstance(other, Constant):
            return False
        return self.type == other.type and self.name == other.name and self.val == other.val

    def __repr__(self):
        return "%s %s=%s"%(self.type, self.name, self.val)

    def __str__(self):
        return "%s %s=%s"%(self.type, self.name, self.val)

def _strify_spec(spec, buff=None, indent=''):
    """
    Convert spec into a string representation. Helper routine for MsgSpec.
    @param indent: internal use only
    @type  indent: str
    @param buff: internal use only
    @type  buff: StringIO
    @return: string representation of spec
    @rtype: str
    """
    if buff is None:
        buff = StringIO()
    for c in spec.constants:
        buff.write("%s%s %s=%s\n"%(indent, c.type, c.name, c.val_text))
    for type_, name in zip(spec.types, spec.names):
        buff.write("%s%s %s\n"%(indent, type_, name))
        base_type = base_msg_type(type_)
        if not base_type in BUILTIN_TYPES:
            subspec = get_registered(base_type)
            _strify_spec(subspec, buff, indent + '  ')
    return buff.getvalue()

class Field(object):
    """
    Container class for storing information about a single field in a MsgSpec
    
    Contains:
    name
    type
    base_type
    is_array
    array_len
    is_builtin
    is_header
    """
    
    def __init__(self, name, type):
        self.name = name
        self.type = type
        (self.base_type, self.is_array, self.array_len) = parse_type(type)
        self.is_header = is_header_type(self.base_type)
        self.is_builtin = is_builtin(self.base_type)

    def __repr__(self):
        return "[%s, %s, %s, %s, %s]"%(self.name, self.type, self.base_type, self.is_array, self.array_len)

class MsgSpec(object):
    """
    Container class for storing loaded msg description files. Field
    types and names are stored in separate lists with 1-to-1
    correspondence. MsgSpec can also return an md5 of the source text.
    """

    def __init__(self, types, names, constants, text, full_name = '', short_name = '', package = ''):
        """
        @param types: list of field types, in order of declaration
        @type  types: [str]
        @param names: list of field names, in order of declaration    
        @type  names: [str]
        @param constants: Constant declarations
        @type  constants: [L{Constant}]
        @param text: text of declaration
        @type  text: str
        @raise MsgSpecException: if spec is invalid (e.g. fields with the same name)
        """
        self.types = types
        if len(set(names)) != len(names):
            raise MsgSpecException("Duplicate field names in message: %s"%names)
        self.names = names
        self.constants = constants
        assert len(self.types) == len(self.names), "len(%s) != len(%s)"%(self.types, self.names)
        #Header.msg support
        if (len(self.types)):
            self.header_present = self.types[0] == HEADER and self.names[0] == 'header'
        else:
            self.header_present = False
        self.text = text
        self.full_name = full_name
        self.short_name = short_name
        self.package = package
        self._parsed_fields = [Field(name, type) for (name, type) in zip(self.names, self.types)]
        
    def fields(self):
        """
        @return: zip list of types and names (e.g. [('int32', 'x'), ('int32', 'y')]
        @rtype: [(str,str),]
        """
        return list(zip(self.types, self.names)) #py3k
    
    def parsed_fields(self):
        """
        @return: list of Field classes
        @rtype: [Field,]
        """
        return self._parsed_fields

    def has_header(self):
        """
        @return: True if msg decription contains a 'Header header'
        declaration at the beginning
        @rtype: bool
        """
        return self.header_present
    def __eq__(self, other):
        if not other or not isinstance(other, MsgSpec):
            return False 
        return self.types == other.types and self.names == other.names and \
               self.constants == other.constants and self.text == other.text
    def __ne__(self, other):
        if not other or not isinstance(other, MsgSpec):
            return True
        return not self.__eq__(other)

    def __repr__(self):
        if self.constants:
            return "MsgSpec[%s, %s, %s]"%(repr(self.constants), repr(self.types), repr(self.names))
        else:
            return "MsgSpec[%s, %s]"%(repr(self.types), repr(self.names))        

    def __str__(self):
        return _strify_spec(self)
    
# msg spec loading utilities ##########################################

def reinit():
    """
    Reinitialize roslib.msgs. This API is for message generators
    (e.g. genpy) that need to re-initialize the registration table.
    """
    global _initialized , _loaded_packages
    # unset the initialized state and unregister everything 
    _initialized = False
    del _loaded_packages[:]
    REGISTERED_TYPES.clear()
    _init()
    
_initialized = False
def _init():
    #lazy-init
    global _initialized
    if _initialized:
        return

    fname = '%s%s'%(HEADER, EXT)
    std_msgs_dir = roslib.packages.get_pkg_dir('std_msgs')
    if std_msgs_dir is None:
        raise MsgSpecException("Unable to locate roslib: %s files cannot be loaded"%EXT)
    
    header = os.path.join(std_msgs_dir, 'msg', fname)
    if not os.path.isfile(header):
        sys.stderr.write("ERROR: cannot locate %s. Expected to find it at '%s'\n"%(fname, header))
        return False

    # register Header under both contexted and de-contexted name
    _, spec = load_from_file(header, '')
    register(HEADER, spec)
    register('std_msgs/'+HEADER, spec)    
    # backwards compat, REP 100
    register('roslib/'+HEADER, spec)    
    for k, spec in EXTENDED_BUILTINS.items():
        register(k, spec)
        
    _initialized = True

# .msg file routines ##############################################################       

def _msg_filter(f):
    """
    Predicate for filtering directory list. matches message files
    @param f: filename
    @type  f: str
    """
    return os.path.isfile(f) and f.endswith(EXT)

# also used by doxymaker
def list_msg_types(package, include_depends):
    """
    List all messages in the specified package
    @param package str: name of package to search
    @param include_depends bool: if True, will also list messages in package dependencies
    @return [str]: message type names
    """
    types = roslib.resources.list_package_resources(package, include_depends, 'msg', _msg_filter)
    return [x[:-len(EXT)] for x in types]

def msg_file(package, type_):
    """
    Determine the file system path for the specified .msg
    resource. .msg resource does not have to exist.
    
    @param package: name of package .msg file is in
    @type  package: str
    @param type_: type name of message, e.g. 'Point2DFloat32'
    @type  type_: str
    @return: file path of .msg file in specified package
    @rtype: str
    """
    return roslib.packages.resource_file(package, 'msg', type_+EXT)

def get_pkg_msg_specs(package):
    """
    List all messages that a package contains.
    
    @param package: package to load messages from
    @type  package: str
    @return: list of message type names and specs for package, as well as a list
        of message names that could not be processed. 
    @rtype: [(str, L{MsgSpec}), [str]]
    """
    _init()
    types = list_msg_types(package, False)
    specs = [] #no fancy list comprehension as we want to show errors
    failures = []
    for t in types:
        try: 
            typespec = load_from_file(msg_file(package, t), package)
            specs.append(typespec)
        except Exception as e:
            failures.append(t)
            print("ERROR: unable to load %s, %s"%(t, e))
    return specs, failures

def load_package_dependencies(package, load_recursive=False):
    """
    Register all messages that the specified package depends on.
    
    @param load_recursive: (optional) if True, load all dependencies,
        not just direct dependencies. By default, this is false to
        prevent packages from incorrectly inheriting dependencies.
    @type  load_recursive: bool
    """
    global _loaded_packages
    _init()    
    if VERBOSE:
        print("Load dependencies for package", package)
        
    if not load_recursive:
        manifest_file = roslib.manifest.manifest_file(package, True)
        m = roslib.manifest.parse_file(manifest_file)
        depends = [d.package for d in m.depends] # #391
    else:
        depends = rospkg.RosPack().get_depends(package, implicit=True)

    msgs = []
    failures = []
    for d in depends:
        if VERBOSE:
            print("Load dependency", d)
        #check if already loaded
        # - we are dependent on manifest.getAll returning first-order dependencies first
        if d in _loaded_packages or d == package:
            continue
        _loaded_packages.append(d)
        specs, failed = get_pkg_msg_specs(d)
        msgs.extend(specs)
        failures.extend(failed)
    for key, spec in msgs:
        register(key, spec)

def load_package(package):
    """
    Load package into the local registered namespace. All messages found
    in the package will be registered if they are successfully
    loaded. This should only be done with one package (i.e. the 'main'
    package) per Python instance.

    @param package: package name
    @type  package: str
    """
    global _loaded_packages
    _init()    
    if VERBOSE:
        print("Load package", package)
        
    #check if already loaded
    # - we are dependent on manifest.getAll returning first-order dependencies first
    if package in _loaded_packages:
        if VERBOSE:
            print("Package %s is already loaded"%package)
        return

    _loaded_packages.append(package)
    specs, failed = get_pkg_msg_specs(package)
    if VERBOSE:
        print("Package contains the following messages: %s"%specs)
    for key, spec in specs:
        #register spec under both local and fully-qualified key
        register(key, spec)
        register(package + roslib.names.PRN_SEPARATOR + key, spec)        

def _convert_val(type_, val):
    """
    Convert constant value declaration to python value. Does not do
    type-checking, so ValueError or other exceptions may be raised.
    
    @param type_: ROS field type
    @type  type_: str
    @param val: string representation of constant
    @type  val: str:
    @raise ValueError: if unable to convert to python representation
    @raise MsgSpecException: if value exceeds specified integer width
    """
    if type_ in ['float32','float64']:
        return float(val)
    elif type_ in ['string']:
        return val.strip() #string constants are always stripped 
    elif type_ in ['int8', 'uint8', 'int16','uint16','int32','uint32','int64','uint64', 'char', 'byte']:
        # bounds checking
        bits = [('int8', 8), ('uint8', 8), ('int16', 16),('uint16', 16),\
                ('int32', 32),('uint32', 32), ('int64', 64),('uint64', 64),\
                ('byte', 8), ('char', 8)]
        b = [b for t, b in bits if t == type_][0]
        import math
        if type_[0] == 'u' or type_ == 'char':
            lower = 0
            upper = int(math.pow(2, b)-1)
        else:
            upper = int(math.pow(2, b-1)-1)   
            lower = -upper - 1 #two's complement min
        val = int(val) #python will autocast to long if necessary
        if val > upper or val < lower:
            raise MsgSpecException("cannot coerce [%s] to %s (out of bounds)"%(val, type_))
        return val
    elif type_ == 'bool':
        # TODO: need to nail down constant spec for bool
        return True if eval(val) else False
    raise MsgSpecException("invalid constant type: [%s]"%type_)
        
def load_by_type(msgtype, package_context=''):
    """
    Load message specification for specified type
    
    @param package_context: package name to use for the type name or
        '' to use the local (relative) naming convention.
    @type  package_context: str
    @return: Message type name and message specification
    @rtype: (str, L{MsgSpec})
    """
    pkg, basetype = roslib.names.package_resource_name(msgtype)
    pkg = pkg or package_context # convert '' -> local package
    try:
        m_f = msg_file(pkg, basetype)
    except roslib.packages.InvalidROSPkgException:
        raise MsgSpecException("Cannot locate message type [%s], package [%s] does not exist"%(msgtype, pkg)) 
    return load_from_file(m_f, pkg)

def load_from_string(text, package_context='', full_name='', short_name=''):
    """
    Load message specification from a string.
    @param text: .msg text 
    @type  text: str
    @param package_context: package name to use for the type name or
        '' to use the local (relative) naming convention.
    @type  package_context: str
    @return: Message specification
    @rtype: L{MsgSpec}
    @raise MsgSpecException: if syntax errors or other problems are detected in file
    """
    types = []
    names = []
    constants = []
    for orig_line in text.split('\n'):
        l = orig_line.split(COMMENTCHAR)[0].strip() #strip comments
        if not l:
            continue #ignore empty lines
        splits = [s for s in [x.strip() for x in l.split(" ")] if s] #split type/name, filter out empties
        type_ = splits[0]
        if not is_valid_msg_type(type_):
            raise MsgSpecException("%s is not a legal message type"%type_)
        if CONSTCHAR in l:
            if not is_valid_constant_type(type_):
                raise MsgSpecException("%s is not a legal constant type"%type_)
            if type_ == 'string':
                # strings contain anything to the right of the equals sign, there are no comments allowed
                idx = orig_line.find(CONSTCHAR)
                name = orig_line[orig_line.find(' ')+1:idx]
                val = orig_line[idx+1:]
            else:
                splits = [x.strip() for x in ' '.join(splits[1:]).split(CONSTCHAR)] #resplit on '='
                if len(splits) != 2:
                    raise MsgSpecException("Invalid declaration: %s"%l)
                name = splits[0]
                val = splits[1]
            try:
                val_converted  = _convert_val(type_, val)
            except Exception as e:
                raise MsgSpecException("Invalid declaration: %s"%e)
            constants.append(Constant(type_, name, val_converted, val.strip()))
        else:
            if len(splits) != 2:
                raise MsgSpecException("Invalid declaration: %s"%l)
            name = splits[1]
            if not is_valid_msg_field_name(name):
                raise MsgSpecException("%s is not a legal message field name"%name)
            if package_context and not SEP in type_:
                if not base_msg_type(type_) in RESERVED_TYPES:
                    #print "rewrite", type_, "to", "%s/%s"%(package_context, type_)
                    type_ = "%s/%s"%(package_context, type_)
            types.append(type_)
            names.append(name)
    return MsgSpec(types, names, constants, text, full_name, short_name, package_context)

def load_from_file(file_path, package_context=''):
    """
    Convert the .msg representation in the file to a MsgSpec instance.
    This does *not* register the object.
    @param file_path: path of file to load from
    @type  file_path: str:
    @param package_context: package name to prepend to type name or
        '' to use local (relative) naming convention.
    @type  package_context: str
    @return: Message type name and message specification
    @rtype:  (str, L{MsgSpec})
    @raise MsgSpecException: if syntax errors or other problems are detected in file
    """
    if VERBOSE:
        if package_context:
            print("Load spec from", file_path, "into package [%s]"%package_context)
        else:
            print("Load spec from", file_path)

    file_name = os.path.basename(file_path)
    type_ = file_name[:-len(EXT)]
    base_type_ = type_
    # determine the type name
    if package_context:
        while package_context.endswith(SEP):
            package_context = package_context[:-1] #strip message separators
        type_ = "%s%s%s"%(package_context, SEP, type_)
    if not roslib.names.is_legal_resource_name(type_):
        raise MsgSpecException("%s: [%s] is not a legal type name"%(file_path, type_))
    
    f = open(file_path, 'r')
    try:
        try:
            text = f.read()
            return (type_, load_from_string(text, package_context, type_, base_type_))
        except MsgSpecException as e:
            raise MsgSpecException('%s: %s'%(file_name, e))
    finally:
        f.close()

# data structures and builtins specification ###########################

# adjustable constants, in case we change our minds
HEADER   = 'Header'
TIME     = 'time'
DURATION = 'duration'

def is_header_type(type_):
    """
    @param type_: message type name
    @type  type_: str
    @return: True if \a type_ refers to the ROS Header type
    @rtype:  bool
    """
    # for backwards compatibility, include roslib/Header. REP 100
    return type_ in [HEADER, 'std_msgs/Header', 'roslib/Header']
       
# time and duration types are represented as aggregate data structures
# for the purposes of serialization from the perspective of
# roslib.msgs. genmsg_py will do additional special handling is required
# to convert them into rospy.msg.Time/Duration instances.

## time as msg spec. time is unsigned 
TIME_MSG     = "uint32 secs\nuint32 nsecs"
## duration as msg spec. duration is just like time except signed
DURATION_MSG = "int32 secs\nint32 nsecs"

## primitive types are those for which we allow constants, i.e. have  primitive representation
PRIMITIVE_TYPES = ['int8','uint8','int16','uint16','int32','uint32','int64','uint64','float32','float64',
                   'string',
                   'bool',
                   # deprecated:
                   'char','byte']
BUILTIN_TYPES = PRIMITIVE_TYPES + [TIME, DURATION]

def is_builtin(msg_type_name):
    """
    @param msg_type_name: name of message type
    @type  msg_type_name: str
    @return: True if msg_type_name is a builtin/primitive type
    @rtype: bool
    """
    return msg_type_name in BUILTIN_TYPES

## extended builtins are builtin types that can be represented as MsgSpec instances
EXTENDED_BUILTINS = { TIME : load_from_string(TIME_MSG), DURATION: load_from_string(DURATION_MSG) }

RESERVED_TYPES  = BUILTIN_TYPES + [HEADER]

REGISTERED_TYPES = { } 
_loaded_packages = [] #keep track of packages so that we only load once (note: bug #59)

def is_registered(msg_type_name):
    """
    @param msg_type_name: name of message type
    @type  msg_type_name: str
    @return: True if msg spec for specified msg type name is
    registered. NOTE: builtin types are not registered.
    @rtype: bool
    """
    return msg_type_name in REGISTERED_TYPES

def get_registered(msg_type_name, default_package=None):
    """
    @param msg_type_name: name of message type
    @type  msg_type_name: str
    @return: msg spec for msg type name
    @rtype: L{MsgSpec}
    """
    if msg_type_name in REGISTERED_TYPES:
        return REGISTERED_TYPES[msg_type_name]
    elif default_package:
        # if msg_type_name has no package specifier, try with default package resolution
        p, n = roslib.names.package_resource_name(msg_type_name)
        if not p:
            return REGISTERED_TYPES[roslib.names.resource_name(default_package, msg_type_name)]
    raise KeyError(msg_type_name)

def register(msg_type_name, msg_spec):
    """
    Load MsgSpec into the type dictionary
    
    @param msg_type_name: name of message type
    @type  msg_type_name: str
    @param msg_spec: spec to load
    @type  msg_spec: L{MsgSpec}
    """
    if VERBOSE:
        print("Register msg %s"%msg_type_name)
    REGISTERED_TYPES[msg_type_name] = msg_spec


########NEW FILE########
__FILENAME__ = names
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$

"""
Warning: do not use this library.  It is unstable and most of the routines
here have been superceded by other libraries (e.g. genmsg).  These
routines will likely be *deleted* in future releases.
"""

import os
import sys

#TODO: deprecate PRN_SEPARATOR
PRN_SEPARATOR = '/'
TYPE_SEPARATOR = PRN_SEPARATOR #alias
SEP = '/'
GLOBALNS = '/'
PRIV_NAME = '~'
REMAP = ":="
ANYTYPE = '*'

if sys.hexversion > 0x03000000: #Python3
    def isstring(s):
        return isinstance(s, str) #Python 3.x
else:
    def isstring(s):
        """
        Small helper version to check an object is a string in a way that works
        for both Python 2 and 3
        """
        return isinstance(s, basestring) #Python 2.x

def get_ros_namespace(env=None, argv=None):
    """
    @param env: environment dictionary (defaults to os.environ)
    @type  env: dict
    @param argv: command-line arguments (defaults to sys.argv)
    @type  argv: [str]
    @return: ROS namespace of current program
    @rtype: str
    """    
    #we force command-line-specified namespaces to be globally scoped
    if argv is None:
        argv = sys.argv
    for a in argv:
        if a.startswith('__ns:='):
            return make_global_ns(a[len('__ns:='):])
    if env is None:
        env = os.environ
    return make_global_ns(env.get('ROS_NAMESPACE', GLOBALNS))

def make_caller_id(name):
    """
    Resolve a local name to the caller ID based on ROS environment settings (i.e. ROS_NAMESPACE)

    @param name: local name to calculate caller ID from, e.g. 'camera', 'node'
    @type  name: str
    @return: caller ID based on supplied local name
    @rtype: str
    """    
    return make_global_ns(ns_join(get_ros_namespace(), name))

def make_global_ns(name):
    """
    Convert name to a global name with a trailing namespace separator.
    
    @param name: ROS resource name. Cannot be a ~name.
    @type  name: str
    @return str: name as a global name, e.g. 'foo' -> '/foo/'.
        This does NOT resolve a name.
    @rtype: str
    @raise ValueError: if name is a ~name 
    """    
    if is_private(name):
        raise ValueError("cannot turn [%s] into a global name"%name)
    if not is_global(name):
        name = SEP + name
    if name[-1] != SEP:
        name = name + SEP
    return name

def is_global(name):
    """
    Test if name is a global graph resource name.
    
    @param name: must be a legal name in canonical form
    @type  name: str
    @return: True if name is a globally referenced name (i.e. /ns/name)
    @rtype: bool
    """    
    return name and name[0] == SEP

def is_private(name):
    """
    Test if name is a private graph resource name.
    
    @param name: must be a legal name in canonical form
    @type  name: str
    @return bool: True if name is a privately referenced name (i.e. ~name)
    """    
    return name and name[0] == PRIV_NAME

def namespace(name):
    """
    Get the namespace of name. The namespace is returned with a
    trailing slash in order to favor easy concatenation and easier use
    within the global context.
        
    @param name: name to return the namespace of. Must be a legal
        name. NOTE: an empty name will return the global namespace.
    @type  name: str
    @return str: Namespace of name. For example, '/wg/node1' returns '/wg/'. The
        global namespace is '/'. 
    @rtype: str
    @raise ValueError: if name is invalid
    """    
    "map name to its namespace"
    if name is None: 
        raise ValueError('name')
    if not isstring(name):
        raise TypeError('name')
    if not name:
        return SEP
    elif name[-1] == SEP:
        name = name[:-1]
    return name[:name.rfind(SEP)+1] or SEP

def ns_join(ns, name):
    """
    Join a namespace and name. If name is unjoinable (i.e. ~private or
    /global) it will be returned without joining

    @param ns: namespace ('/' and '~' are both legal). If ns is the empty string, name will be returned.
    @type  ns: str
    @param name str: a legal name
    @return str: name concatenated to ns, or name if it is
        unjoinable.
    @rtype: str
    """    
    if is_private(name) or is_global(name):
        return name
    if ns == PRIV_NAME:
        return PRIV_NAME + name
    if not ns: 
        return name
    if ns[-1] == SEP:
        return ns + name
    return ns + SEP + name

def load_mappings(argv):
    """
    Load name mappings encoded in command-line arguments. This will filter
    out any parameter assignment mappings (see roslib.param.load_param_mappings()).

    @param argv: command-line arguments
    @type  argv: [str]
    @return: name->name remappings. 
    @rtype: dict {str: str}
    """    
    mappings = {}
    for arg in argv:
        if REMAP in arg:
            try:
                src, dst = [x.strip() for x in arg.split(REMAP)]
                if src and dst:
                    if len(src) > 1 and src[0] == '_' and src[1] != '_':
                        #ignore parameter assignment mappings
                        pass
                    else:
                        mappings[src] = dst
            except:
                sys.stderr.write("ERROR: Invalid remapping argument '%s'\n"%arg)
    return mappings

#######################################################################
# RESOURCE NAMES
# resource names refer to entities in a file system

def resource_name(res_pkg_name, name, my_pkg=None):
    """
    Convert package name + resource into a fully qualified resource name

    @param res_pkg_name: name of package resource is located in
    @type  res_pkg_name: str
    @param name: resource base name
    @type  name: str
    @param my_pkg: name of package resource is being referred to
        in. If specified, name will be returned in local form if 
        res_pkg_name is my_pkg
    @type  my_pkg: str
    @return: name for resource 
    @rtype: str
    """    
    if res_pkg_name != my_pkg:
        return res_pkg_name+PRN_SEPARATOR+name
    return name

def resource_name_base(name):
    """
    pkg/typeName -> typeName, typeName -> typeName
    
    Convert fully qualified resource name into the package-less resource name
    @param name: package resource name, e.g. 'std_msgs/String'
    @type  name: str
    @return: resource name sans package-name scope
    @rtype: str
    """    

    return name[name.rfind(PRN_SEPARATOR)+1:]

def resource_name_package(name):
    """
    pkg/typeName -> pkg, typeName -> None
    
    @param name: package resource name, e.g. 'std_msgs/String'
    @type  name: str
    @return: package name of resource
    @rtype: str
    """    

    if not PRN_SEPARATOR in name:
        return None
    return name[:name.find(PRN_SEPARATOR)]

def package_resource_name(name):
    """
    Split a name into its package and resource name parts, e.g. 'std_msgs/String -> std_msgs, String'

    @param name: package resource name, e.g. 'std_msgs/String'
    @type  name: str
    @return: package name, resource name
    @rtype: str
    @raise ValueError: if name is invalid
    """    
    if PRN_SEPARATOR in name:
        val = tuple(name.split(PRN_SEPARATOR))
        if len(val) != 2:
            raise ValueError("invalid name [%s]"%name)
        else:
            return val
    else:
        return '', name

def _is_safe_name(name, type_name):
    #windows long-file name length is 255
    if not isstring(name) or not name or len(name) > 255:
        return False
    return is_legal_resource_name(name)

################################################################################
# NAME VALIDATORS

import re
#ascii char followed by (alphanumeric, _, /)
RESOURCE_NAME_LEGAL_CHARS_P = re.compile('^[A-Za-z][\w_\/]*$') 
def is_legal_resource_name(name):
    """
    Check if name is a legal ROS name for filesystem resources
    (alphabetical character followed by alphanumeric, underscore, or
    forward slashes). This constraint is currently not being enforced,
    but may start getting enforced in later versions of ROS.

    @param name: Name
    @type  name: str
    """
    # resource names can be unicode due to filesystem
    if name is None:
        return False
    m = RESOURCE_NAME_LEGAL_CHARS_P.match(name)
    # '//' check makes sure there isn't double-slashes
    return m is not None and m.group(0) == name and not '//' in name

#~,/, or ascii char followed by (alphanumeric, _, /)
NAME_LEGAL_CHARS_P = re.compile('^[\~\/A-Za-z][\w_\/]*$') 
def is_legal_name(name):
    """
    Check if name is a legal ROS name for graph resources
    (alphabetical character followed by alphanumeric, underscore, or
    forward slashes). This constraint is currently not being enforced,
    but may start getting enforced in later versions of ROS.

    @param name: Name
    @type  name: str
    """    
    # should we enforce unicode checks?
    if name is None:
        return False
    # empty string is a legal name as it resolves to namespace
    if name == '':
        return True
    m = NAME_LEGAL_CHARS_P.match(name)
    return m is not None and m.group(0) == name and not '//' in name
    
BASE_NAME_LEGAL_CHARS_P = re.compile('^[A-Za-z][\w_]*$') #ascii char followed by (alphanumeric, _)
def is_legal_base_name(name):
    """
    Validates that name is a legal base name for a graph resource. A base name has
    no namespace context, e.g. "node_name".
    """
    if name is None:
        return False
    m = BASE_NAME_LEGAL_CHARS_P.match(name)
    return m is not None and m.group(0) == name

BASE_RESOURCE_NAME_LEGAL_CHARS_P = re.compile('^[A-Za-z][\w_]*$') #ascii char followed by (alphanumeric, _)
def is_legal_resource_base_name(name):
    """
    Validates that name is a legal resource base name. A base name has
    no package context, e.g. "String".
    """
    # resource names can be unicode due to filesystem
    if name is None:
        return False
    m = BASE_NAME_LEGAL_CHARS_P.match(name)
    return m is not None and m.group(0) == name

def canonicalize_name(name):
    """
    Put name in canonical form. Extra slashes '//' are removed and
    name is returned without any trailing slash, e.g. /foo/bar
    @param name: ROS name
    @type  name: str
    """
    if not name or name == SEP:
        return name
    elif name[0] == SEP:
        return '/' + '/'.join([x for x in name.split(SEP) if x])
    else:
        return '/'.join([x for x in name.split(SEP) if x])        

def resolve_name(name, namespace_, remappings=None):
    """
    Resolve a ROS name to its global, canonical form. Private ~names
    are resolved relative to the node name. 

    @param name: name to resolve.
    @type  name: str
    @param namespace_: node name to resolve relative to.
    @type  namespace_: str
    @param remappings: Map of resolved remappings. Use None to indicate no remapping.
    @return: Resolved name. If name is empty/None, resolve_name
    returns parent namespace_. If namespace_ is empty/None,
    @rtype: str
    """
    if not name: #empty string resolves to parent of the namespace_
        return namespace(namespace_)

    name = canonicalize_name(name)
    if name[0] == SEP: #global name
        resolved_name = name
    elif is_private(name): #~name
        # #3044: be careful not to accidentally make rest of name global
        resolved_name = canonicalize_name(namespace_ + SEP + name[1:])
    else: #relative
        resolved_name = namespace(namespace_) + name

    #Mappings override general namespace-based resolution
    # - do this before canonicalization as remappings are meant to
    #   match the name as specified in the code
    if remappings and resolved_name in remappings:
        return remappings[resolved_name]
    else:
        return resolved_name

def anonymous_name(id):
    """
    Generate a ROS-legal 'anonymous' name

    @param id: prefix for anonymous name
    @type  id: str
    """
    import socket, random
    name = "%s_%s_%s_%s"%(id, socket.gethostname(), os.getpid(), random.randint(0, sys.maxsize))
    # RFC 952 allows hyphens, IP addrs can have '.'s, both
    # of which are illegal for ROS names. For good
    # measure, screen ipv6 ':'. 
    name = name.replace('.', '_')
    name = name.replace('-', '_')                
    return name.replace(':', '_')


########NEW FILE########
__FILENAME__ = network
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$

"""
Warning: do not use this library.  It is unstable and most of the routines
here have been superceded by other libraries (e.g. rosgraph).  These
routines will likely be *deleted* in future releases.
"""

import os
import socket
import struct
import sys
import platform

try:
    from cStringIO import StringIO #Python 2.x
    python3 = 0
except ImportError:
    from io import BytesIO #Python 3.x
    python3 = 1

try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

#TODO: change this to rosgraph equivalents once we have ported this module
ROS_IP = 'ROS_IP'
ROS_HOSTNAME = 'ROS_HOSTNAME'

SIOCGIFCONF = 0x8912
SIOCGIFADDR = 0x8915
if platform.system() == 'FreeBSD':
    SIOCGIFADDR = 0xc0206921
    if platform.architecture()[0] == '64bit':
        SIOCGIFCONF = 0xc0106924
    else:
        SIOCGIFCONF = 0xc0086924

if 0:
    # disabling netifaces as it accounts for 50% of startup latency
    try:
        import netifaces
        _use_netifaces = True
    except:
        # NOTE: in rare cases, I've seen Python fail to extract the egg
        # cache when launching multiple python nodes.  Thus, we do
        # except-all instead of except ImportError (kwc).
        _use_netifaces = False
else:
    _use_netifaces = False

def _is_unix_like_platform():
    """
    @return: true if the platform conforms to UNIX/POSIX-style APIs
    @rtype: bool
    """
    #return platform.system() in ['Linux', 'Mac OS X', 'Darwin']
    return platform.system() in ['Linux', 'FreeBSD']

def get_address_override():
    """
    @return: ROS_IP/ROS_HOSTNAME override or None
    @rtype: str
    @raise ValueError: if ROS_IP/ROS_HOSTNAME/__ip/__hostname are invalidly specified
    """
    # #998: check for command-line remappings first
    for arg in sys.argv:
        if arg.startswith('__hostname:=') or arg.startswith('__ip:='):
            try:
                _, val = arg.split(':=')
                return val
            except: #split didn't unpack properly
                raise ValueError("invalid ROS command-line remapping argument '%s'"%arg)

    # check ROS_HOSTNAME and ROS_IP environment variables, which are
    # aliases for each other
    if ROS_HOSTNAME in os.environ:
        return os.environ[ROS_HOSTNAME]
    elif ROS_IP in os.environ:
        return os.environ[ROS_IP]
    return None

def is_local_address(hostname):
    """
    @param hostname: host name/address
    @type  hostname: str
    @return True: if hostname maps to a local address, False otherwise. False conditions include invalid hostnames.
    """
    try:
        reverse_ip = socket.gethostbyname(hostname)
    except socket.error:
        return False
    # 127. check is due to #1260
    if reverse_ip not in get_local_addresses() and not reverse_ip.startswith('127.'):
        return False
    return True
    
def get_local_address():
    """
    @return: default local IP address (e.g. eth0). May be overriden by ROS_IP/ROS_HOSTNAME/__ip/__hostname
    @rtype: str
    """
    override = get_address_override()
    if override:
        return override
    addrs = get_local_addresses()
    if len(addrs) == 1:
        return addrs[0]
    for addr in addrs:
        # pick first non 127/8 address
        if not addr.startswith('127.'):
            return addr
    else: # loopback 
        return '127.0.0.1'

# cache for performance reasons
_local_addrs = None
def get_local_addresses():
    """
    @return: known local addresses. Not affected by ROS_IP/ROS_HOSTNAME
    @rtype:  [str]
    """
    # cache address data as it can be slow to calculate
    global _local_addrs
    if _local_addrs is not None:
        return _local_addrs

    local_addrs = None
    if _use_netifaces:
        # #552: netifaces is a more robust package for looking up
        # #addresses on multiple platforms (OS X, Unix, Windows)
        local_addrs = []
        # see http://alastairs-place.net/netifaces/
        for i in netifaces.interfaces():
            try:
                local_addrs.extend([d['addr'] for d in netifaces.ifaddresses(i)[netifaces.AF_INET]])
            except KeyError: pass
    elif _is_unix_like_platform():
        # unix-only branch
        # adapted from code from Rosen Diankov (rdiankov@cs.cmu.edu)
        # and from ActiveState recipe

        import fcntl
        import array

        ifsize = 32
        if platform.system() == 'Linux' and platform.architecture()[0] == '64bit':
            ifsize = 40 # untested

        # 32 interfaces allowed, far more than ROS can sanely deal with

        max_bytes = 32 * ifsize
        # according to http://docs.python.org/library/fcntl.html, the buffer limit is 1024 bytes
        buff = array.array('B', '\0' * max_bytes)
        # serialize the buffer length and address to ioctl
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)        
        info = fcntl.ioctl(sock.fileno(), SIOCGIFCONF,
                           struct.pack('iL', max_bytes, buff.buffer_info()[0]))
        retbytes = struct.unpack('iL', info)[0]
        buffstr = buff.tostring()
        if platform.system() == 'Linux':
            local_addrs = [socket.inet_ntoa(buffstr[i+20:i+24]) for i in range(0, retbytes, ifsize)]
        else:
            # in FreeBSD, ifsize is variable: 16 + (16 or 28 or 56) bytes
            # When ifsize is 32 bytes, it contains the interface name and address,
            # else it contains the interface name and other information
            # This means the buffer must be traversed in its entirety
            local_addrs = []
            bufpos = 0
            while bufpos < retbytes:
                bufpos += 16
                ifreqsize = ord(buffstr[bufpos])
                if ifreqsize == 16:
                    local_addrs += [socket.inet_ntoa(buffstr[bufpos+4:bufpos+8])]
                bufpos += ifreqsize
    else:
        # cross-platform branch, can only resolve one address
        local_addrs = [socket.gethostbyname(socket.gethostname())]
    _local_addrs = local_addrs
    return local_addrs


def get_bind_address(address=None):
    """
    @param address: (optional) address to compare against
    @type  address: str
    @return: address TCP/IP sockets should use for binding. This is
    generally 0.0.0.0, but if \a address or ROS_IP/ROS_HOSTNAME is set
    to localhost it will return 127.0.0.1
    @rtype: str
    """
    if address is None:
        address = get_address_override()
    if address and \
           (address == 'localhost' or address.startswith('127.')):
        #localhost or 127/8
        return '127.0.0.1' #loopback
    else:
        return '0.0.0.0'

# #528: semi-complicated logic for determining XML-RPC URI
def get_host_name():
    """
    Determine host-name for use in host-name-based addressing (e.g. XML-RPC URIs):
     - if ROS_IP/ROS_HOSTNAME is set, use that address
     - if the hostname returns a non-localhost value, use that
     - use whatever L{get_local_address()} returns
    """
    hostname = get_address_override()
    if not hostname:
        try:
            hostname = socket.gethostname()
        except:
            pass
        if not hostname or hostname == 'localhost' or hostname.startswith('127.'):
            hostname = get_local_address()
    return hostname

def create_local_xmlrpc_uri(port):
    """
    Determine the XMLRPC URI for local servers. This handles the search
    logic of checking ROS environment variables, the known hostname,
    and local interface IP addresses to determine the best possible
    URI.
    
    @param port: port that server is running on
    @type  port: int
    @return: XMLRPC URI    
    @rtype: str
    """
    #TODO: merge logic in roslib.xmlrpc with this routine
    # in the future we may not want to be locked to http protocol nor root path
    return 'http://%s:%s/'%(get_host_name(), port)


## handshake utils ###########################################

class ROSHandshakeException(Exception):
    """
    Exception to represent errors decoding handshake
    """
    pass

def decode_ros_handshake_header(header_str):
    """
    Decode serialized ROS handshake header into a Python dictionary

    header is a list of string key=value pairs, each prefixed by a
    4-byte length field. It is preceeded by a 4-byte length field for
    the entire header.
    
    @param header_str: encoded header string. May contain extra data at the end.
    @type  header_str: str
    @return: key value pairs encoded in \a header_str
    @rtype: {str: str} 
    """
    (size, ) = struct.unpack('<I', header_str[0:4])
    size += 4 # add in 4 to include size of size field
    header_len = len(header_str)
    if size > header_len:
        raise ROSHandshakeException("Incomplete header. Expected %s bytes but only have %s"%((size+4), header_len))

    d = {}
    start = 4
    while start < size:
        (field_size, ) = struct.unpack('<I', header_str[start:start+4])
        if field_size == 0:
            raise ROSHandshakeException("Invalid 0-length handshake header field")
        start += field_size + 4
        if start > size:
            raise ROSHandshakeException("Invalid line length in handshake header: %s"%size)
        line = header_str[start-field_size:start]
        
        #python3 compatibility
        if python3 == 1:
            line = line.decode()
        
        idx = line.find("=")
        if idx < 0:
            raise ROSHandshakeException("Invalid line in handshake header: [%s]"%line)
        key = line[:idx]
        value = line[idx+1:]
        d[key.strip()] = value
    return d
    
def read_ros_handshake_header(sock, b, buff_size):
    """
    Read in tcpros header off the socket \a sock using buffer \a b.
    
    @param sock: socket must be in blocking mode
    @type  sock: socket
    @param b: buffer to use
    @type  b: StringIO for Python2, BytesIO for Python 3
    @param buff_size: incoming buffer size to use
    @type  buff_size: int
    @return: key value pairs encoded in handshake
    @rtype: {str: str}
    @raise ROSHandshakeException: If header format does not match expected
    """
    header_str = None
    while not header_str:
        d = sock.recv(buff_size)
        if not d:
            raise ROSHandshakeException("connection from sender terminated before handshake header received. %s bytes were received. Please check sender for additional details."%b.tell())
        b.write(d)
        btell = b.tell()
        if btell > 4:
            # most likely we will get the full header in the first recv, so
            # not worth tiny optimizations possible here
            bval = b.getvalue()
            (size,) = struct.unpack('<I', bval[0:4])
            if btell - 4 >= size:
                header_str = bval
                    
                # memmove the remnants of the buffer back to the start
                leftovers = bval[size+4:]
                b.truncate(len(leftovers))
                b.seek(0)
                b.write(leftovers)
                header_recvd = True
                    
    # process the header
    return decode_ros_handshake_header(bval)

def encode_ros_handshake_header(header):
    """
    Encode ROS handshake header as a byte string. Each header
    field is a string key value pair. The encoded header is
    prefixed by a length field, as is each field key/value pair.
    key/value pairs a separated by a '=' equals sign.

    FORMAT: (4-byte length + [4-byte field length + field=value ]*)

    @param header: header field keys/values
    @type  header: dict
    @return: header encoded as byte string
    @rtype: str
    """    
    fields = ["%s=%s"%(k,v) for k,v in header.items()]
    
    # in the usual configuration, the error 'TypeError: can't concat bytes to str' appears:
    if python3 == 0:
        #python 2
        s = ''.join(["%s%s"%(struct.pack('<I', len(f)), f) for f in fields])
        return struct.pack('<I', len(s)) + s
    else:
        #python 3 
        s = b''.join([(struct.pack('<I', len(f)) + f.encode("utf-8")) for f in fields])
        return struct.pack('<I', len(s)) + s
                                        
def write_ros_handshake_header(sock, header):
    """
    Write ROS handshake header header to socket sock
    @param sock: socket to write to (must be in blocking mode)
    @type  sock: socket.socket
    @param header: header field keys/values
    @type  header: {str : str}
    @return: Number of bytes sent (for statistics)
    @rtype: int
    """
    s = encode_ros_handshake_header(header)
    sock.sendall(s)
    return len(s) #STATS
    

########NEW FILE########
__FILENAME__ = packages
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$
# $Author$

"""
Warning: do not use this library.  It is unstable and most of the routines
here have been superceded by other libraries (e.g. rospkg).  These
routines will likely be *deleted* in future releases.
"""

import os
import sys
import stat
import string

from subprocess import Popen, PIPE

from catkin.find_in_workspaces import find_in_workspaces as catkin_find
import rospkg

import roslib.manifest

SRC_DIR = 'src'

# aliases
ROS_PACKAGE_PATH = rospkg.environment.ROS_PACKAGE_PATH
ROS_ROOT = rospkg.environment.ROS_ROOT

class ROSPkgException(Exception):
    """
    Base class of package-related errors.
    """
    pass
class InvalidROSPkgException(ROSPkgException):
    """
    Exception that indicates that a ROS package does not exist
    """
    pass
class MultipleNodesException(ROSPkgException):
    """
    Exception that indicates that multiple ROS nodes by the same name are in the same package.
    """
    pass

# TODO: go through the code and eliminate unused methods -- there's far too many combos here

MANIFEST_FILE = 'manifest.xml'
PACKAGE_FILE = 'package.xml'

#
# Map package/directory structure
#

def get_dir_pkg(d):
    """
    Get the package that the directory is contained within. This is
    determined by finding the nearest parent manifest.xml file. This
    isn't 100% reliable, but symlinks can fool any heuristic that
    relies on ROS_ROOT.
    @param d: directory path
    @type  d: str
    @return: (package_directory, package) of the specified directory, or None,None if not in a package
    @rtype: (str, str)
    """
    #TODO: the realpath is going to create issues with symlinks, most likely

    parent = os.path.dirname(os.path.realpath(d))
    #walk up until we hit ros root or ros/pkg
    while not os.path.exists(os.path.join(d, MANIFEST_FILE)) and not os.path.exists(os.path.join(d, PACKAGE_FILE)) and parent != d:
        d = parent
        parent = os.path.dirname(d)
    if os.path.exists(os.path.join(d, MANIFEST_FILE)) or os.path.exists(os.path.join(d, PACKAGE_FILE)):
        pkg = os.path.basename(os.path.abspath(d))
        return d, pkg
    return None, None

_pkg_dir_cache = {}

def get_pkg_dir(package, required=True, ros_root=None, ros_package_path=None):
    """
    Locate directory package is stored in. This routine uses an
    internal cache.

    NOTE: cache does *not* rebuild if packages are relocated after
    this process is initiated.
    
    @param package: package name
    @type  package: str
    @param required: if True, an exception will be raised if the
    package directory cannot be located.
    @type  required: bool
    @param ros_root: if specified, override ROS_ROOT
    @type  ros_root: str
    @param ros_package_path: if specified, override ROS_PACKAGE_PATH
    @type  ros_package_path: str
    @return: directory containing package or None if package cannot be found and required is False.
    @rtype: str
    @raise InvalidROSPkgException: if required is True and package cannot be located
    """    

    #UNIXONLY
    #TODO: replace with non-rospack-based solution (e.g. os.walk())
    try:
        penv = os.environ.copy()
        if ros_root:
            ros_root = rospkg.environment._resolve_path(ros_root)
            penv[ROS_ROOT] = ros_root
        elif ROS_ROOT in os.environ:
            # record setting for _pkg_dir_cache
            ros_root = os.environ[ROS_ROOT]

        # determine rospack exe name
        rospack = 'rospack'

        if ros_package_path is not None:
            ros_package_path = rospkg.environment._resolve_paths(ros_package_path)
            penv[ROS_PACKAGE_PATH] = ros_package_path
        elif ROS_PACKAGE_PATH in os.environ:
            # record setting for _pkg_dir_cache
            ros_package_path = os.environ[ROS_PACKAGE_PATH]

        # update cache if we haven't. NOTE: we only get one cache
        if not _pkg_dir_cache:
            _read_rospack_cache(_pkg_dir_cache, ros_root, ros_package_path)
            
        # now that we've resolved the args, check the cache
        if package in _pkg_dir_cache:
            dir_, rr, rpp = _pkg_dir_cache[package]
            if rr == ros_root and rpp == ros_package_path:
                if os.path.isfile(os.path.join(dir_, MANIFEST_FILE)):
                    return dir_
                else:
                    # invalidate cache
                    _invalidate_cache(_pkg_dir_cache)
            
        rpout, rperr = Popen([rospack, 'find', package], \
                                 stdout=PIPE, stderr=PIPE, env=penv).communicate()

        pkg_dir = (rpout or '').strip()
        #python3.1 popen returns as bytes
        if (isinstance(pkg_dir, bytes)):
            pkg_dir = pkg_dir.decode()
        if not pkg_dir:
            raise InvalidROSPkgException("Cannot locate installation of package %s: %s. ROS_ROOT[%s] ROS_PACKAGE_PATH[%s]"%(package, rperr.strip(), ros_root, ros_package_path))

        pkg_dir = os.path.normpath(pkg_dir)
        if not os.path.exists(pkg_dir):
            raise InvalidROSPkgException("Cannot locate installation of package %s: [%s] is not a valid path. ROS_ROOT[%s] ROS_PACKAGE_PATH[%s]"%(package, pkg_dir, ros_root, ros_package_path))
        elif not os.path.isdir(pkg_dir):
            raise InvalidROSPkgException("Package %s is invalid: file [%s] is in the way"%(package, pkg_dir))
        # don't update cache: this should only be updated from
        # rospack_cache as it will corrupt package list otherwise.
        #_pkg_dir_cache[package] = (pkg_dir, ros_root, ros_package_path)
        return pkg_dir
    except OSError as e:
        if required:
            raise InvalidROSPkgException("Environment configuration is invalid: cannot locate rospack (%s)"%e)
        return None
    except Exception as e:
        if required:
            raise
        return None

def _get_pkg_subdir_by_dir(package_dir, subdir, required=True, env=None):
    """
    @param required: if True, will attempt to  create the subdirectory
        if it does not exist. An exception will be raised  if this fails.
    @type  required: bool
    @param package_dir: directory of package
    @type  package_dir: str
    @param subdir: name of subdirectory to locate
    @type  subdir: str
    @param env: override os.environ dictionary    
    @type  env: dict
    @param required: if True, directory must exist    
    @type  required: bool
    @return: Package subdirectory if package exist, otherwise None.
    @rtype: str
    @raise InvalidROSPkgException: if required is True and directory does not exist
    """
    if env is None:
        env = os.environ
    try:
        if not package_dir:
            raise Exception("Cannot create a '%(subdir)s' directory in %(package_dir)s: package %(package) cannot be located"%locals())
        d = os.path.join(package_dir, subdir)
        if required and os.path.isfile(d):
            raise Exception("""Package '%(package)s' is improperly configured: 
file %(d)s is preventing the creation of a directory"""%locals())
        elif required and not os.path.isdir(d):
            try:
                os.makedirs(d) #lazy create
            except error:
                raise Exception("""Package '%(package)s' is improperly configured: 
Cannot create a '%(subdir)s' directory in %(package_dir)s.
Please check permissions and try again.
"""%locals())
        return d
    except Exception as e:
        if required:
            raise
        return None
    
def get_pkg_subdir(package, subdir, required=True, env=None):
    """
    @param required: if True, will attempt to create the subdirectory
        if it does not exist. An exception will be raised  if this fails.
    @type  required: bool
    @param package: name of package
    @type  package: str
    @param env: override os.environ dictionary
    @type  env: dict
    @param required: if True, directory must exist    
    @type  required: bool
    @return: Package subdirectory if package exist, otherwise None.
    @rtype: str
    @raise InvalidROSPkgException: if required is True and directory does not exist
    """
    if env is None:
        env = os.environ
    pkg_dir = get_pkg_dir(package, required, ros_root=env[ROS_ROOT]) 
    return _get_pkg_subdir_by_dir(pkg_dir, subdir, required, env)

#
# Map ROS resources to files
#

def resource_file(package, subdir, resource_name):
    """
    @param subdir: name of subdir -- these should be one of the
        string constants, e.g. MSG_DIR
    @type  subdir: str
    @return: path to resource in the specified subdirectory of the
        package, or None if the package does not exists
    @rtype: str
    @raise roslib.packages.InvalidROSPkgException: If package does not exist 
    """
    d = get_pkg_subdir(package, subdir, False)
    if d is None:
        raise InvalidROSPkgException(package)
    return os.path.join(d, resource_name)

def _update_rospack_cache(env=None):
    """
    Internal routine to update global package directory cache
    
    @return: True if cache is valid
    @rtype: bool
    """
    if env is None:
        env = os.environ
    cache = _pkg_dir_cache
    if cache:
        return True
    ros_root = env[ROS_ROOT]
    ros_package_path = env.get(ROS_PACKAGE_PATH, '')
    return _read_rospack_cache(cache, ros_root, ros_package_path)

def _invalidate_cache(cache):
    # I've only made this a separate routine because roslib.packages should really be using
    # the roslib.stacks cache implementation instead with the separate cache marker
    cache.clear()

def _read_rospack_cache(cache, ros_root, ros_package_path):
    """
    Read in rospack_cache data into cache. On-disk cache specifies a
    ROS_ROOT and ROS_PACKAGE_PATH, which must match the requested
    environment.
    
    @param cache: empty dictionary to store package list in. 
        If no cache argument provided, will use internal _pkg_dir_cache
        and will return cached answers if available.
        The format of the cache is {package_name: dir_path, ros_root, ros_package_path}.
    @type  cache: {str: str, str, str}
    @param ros_package_path: ROS_ROOT value
    @type  ros_root: str
    @param ros_package_path: ROS_PACKAGE_PATH value or '' if not specified
    @type  ros_package_path: str
    @return: True if on-disk cache matches and was loaded, false otherwise
    @rtype: bool
    """
    try:
        with open(os.path.join(rospkg.get_ros_home(), 'rospack_cache')) as f:
            for l in f.readlines():
                l = l[:-1]
                if not len(l):
                    continue
                if l[0] == '#':
                    # check that the cache matches our env
                    if l.startswith('#ROS_ROOT='):
                        if not l[len('#ROS_ROOT='):] == ros_root:
                            return False
                    elif l.startswith('#ROS_PACKAGE_PATH='):
                        if not l[len('#ROS_PACKAGE_PATH='):] == ros_package_path:
                            return False
                else:
                    cache[os.path.basename(l)] = l, ros_root, ros_package_path
        return True
    except:
        pass
    
def list_pkgs_by_path(path, packages=None, cache=None, env=None):
    """
    List ROS packages within the specified path.

    Optionally, a cache dictionary can be provided, which will be
    updated with the package->path mappings. list_pkgs_by_path() does
    NOT returned cached results -- it only updates the cache.
    
    @param path: path to list packages in
    @type  path: str
    @param packages: list of packages to append to. If package is
      already present in packages, it will be ignored.
    @type  packages: [str]
    @param cache: (optional) package path cache to update. Maps package name to directory path.
    @type  cache: {str: str}
    @return: complete list of package names in ROS environment. Same as packages parameter.
    @rtype: [str]
    """
    if packages is None:
        packages = []
    if env is None:
        env = os.environ
    # record settings for cache
    ros_root = env[ROS_ROOT]
    ros_package_path = env.get(ROS_PACKAGE_PATH, '')

    path = os.path.abspath(path)
    for d, dirs, files in os.walk(path, topdown=True):
        if MANIFEST_FILE in files:
            package = os.path.basename(d)
            if package not in packages:
                packages.append(package)
                if cache is not None:
                    cache[package] = d, ros_root, ros_package_path
            del dirs[:]
            continue #leaf
        elif 'rospack_nosubdirs' in files:
            del dirs[:]
            continue #leaf
        #small optimization
        elif '.svn' in dirs:
            dirs.remove('.svn')
        elif '.git' in dirs:
            dirs.remove('.git')

        for sub_d in dirs:
            # followlinks=True only available in Python 2.6, so we
            # have to implement manually
            sub_p = os.path.join(d, sub_d)
            if os.path.islink(sub_p):
                packages.extend(list_pkgs_by_path(sub_p, cache=cache))
            
    return packages

def find_node(pkg, node_type, rospack=None):
    """
    Warning: unstable API due to catkin.

    Locate the executable that implements the node
    
    :param node_type: type of node, ``str``
    :returns: path to node or None if node is not in the package ``str``
    :raises: :exc:rospkg.ResourceNotFound` If package does not exist 
    """

    if rospack is None:
        rospack = rospkg.RosPack()
    return find_resource(pkg, node_type, filter_fn=_executable_filter, rospack=rospack)

def _executable_filter(test_path):
    s = os.stat(test_path)
    flags = stat.S_IRUSR | stat.S_IXUSR
    if os.name == 'nt' and os.path.splitext(test_path)[1] == '.py':
        flags = stat.S_IRUSR
    return (s.st_mode & flags) == flags

def _find_resource(d, resource_name, filter_fn=None):
    """
    subroutine of find_resource
    """
    matches = []
    # TODO: figure out how to generalize find_resource to take multiple resource name options
    if sys.platform in ['win32', 'cygwin']:
        # Windows logic requires more file patterns to resolve and is
        # not case-sensitive, so leave it separate

        # in the near-term, just hack in support for .exe/.bat/.py. In the long
        # term this needs to:
        #
        #  * parse PATHEXT to generate matches
        #  * perform case-insensitive compares against potential
        #    matches, in path-ext order

        # - We still have to look for bare node_type as user may have
        #   specified extension manually
        resource_name = resource_name.lower()
        patterns = [resource_name, resource_name+'.exe', resource_name+'.bat', resource_name+'.py']
        for p, dirs, files in os.walk(d):
            # case insensitive
            files = [f.lower() for f in files]
            for name in patterns:
                if name in files:
                    test_path = os.path.join(p, name)
                    if filter_fn is not None:
                        if filter_fn(test_path):
                            matches.append(test_path)
                    else:
                        matches.append(test_path)
            # remove .svn/.git/etc
            to_prune = [x for x in dirs if x.startswith('.')]
            for x in to_prune:
                dirs.remove(x)
    else: #UNIX            
        for p, dirs, files in os.walk(d):
            if resource_name in files:
                test_path = os.path.join(p, resource_name)
                if filter_fn is not None:
                    if filter_fn(test_path):
                        matches.append(test_path)
                else:
                    matches.append(test_path)
            # remove .svn/.git/etc
            to_prune = [x for x in dirs if x.startswith('.')]
            for x in to_prune:
                dirs.remove(x)
    return [os.path.abspath(m) for m in matches]

# TODO: this routine really belongs in rospkg, but the catkin-isms really, really don't
# belong in rospkg.  With more thought, they can probably be abstracted out so as
# to no longer be catkin-specific. 
def find_resource(pkg, resource_name, filter_fn=None, rospack=None):
    """
    Warning: unstable API due to catkin.

    Locate the file named resource_name in package, optionally
    matching specified filter.  find_resource() will return a list of
    matches, but only for a given scope.  If the resource is found in
    the binary build directory, it will only return matches in that
    directory; it will not return matches from the ROS_PACKAGE_PATH as
    well in this case.
    
    :param filter: function that takes in a path argument and
        returns True if the it matches the desired resource, ``fn(str)``
    :param rospack: `rospkg.RosPack` instance to use
    :returns: lists of matching paths for resource within a given scope, ``[str]``
    :raises: :exc:`rospkg.ResourceNotFound` If package does not exist 
    """

    # New resource-location policy in Fuerte, induced by the new catkin 
    # build system:
    #   (1) Use catkin_find to find libexec and share locations, look
    #       recursively there.  If the resource is found, done.
    #       Else continue:
    #   (2) If ROS_PACKAGE_PATH is set, look recursively there.  If the
    #       resource is found, done.  Else raise
    #
    # NOTE: package *must* exist on ROS_PACKAGE_PATH no matter what

    if rospack is None:
        rospack = rospkg.RosPack()

    # lookup package as it *must* exist
    pkg_path = rospack.get_path(pkg)

    # if found in binary dir, start with that.  in any case, use matches
    # from ros_package_path
    matches = []
    search_paths = catkin_find(search_dirs=['libexec', 'share'], project=pkg, first_matching_workspace_only=True)
    for search_path in search_paths:
        matches.extend(_find_resource(search_path, resource_name, filter_fn=filter_fn))

    matches.extend(_find_resource(pkg_path, resource_name, filter_fn=filter_fn))

    # Uniquify the results, in case we found the same file twice, while keeping order
    unique_matches = []
    for match in matches:
        if match not in unique_matches:
            unique_matches.append(match)
    return unique_matches

########NEW FILE########
__FILENAME__ = resources
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#

"""
Warning: do not use this library.  It is unstable and most of the routines
here have been superceded by other libraries (e.g. rospkg).  These
routines will likely be *deleted* in future releases.
"""

import os

import roslib.manifest
import roslib.names
import roslib.packages

def _get_manifest_by_dir(package_dir):
    """
    Helper routine for loading Manifest instances
    @param package_dir: package directory location
    @type  package_dir: str
    @return: manifest for package
    @rtype: Manifest
    """
    f = os.path.join(package_dir, roslib.manifest.MANIFEST_FILE)
    if f:
        return roslib.manifest.parse_file(f)
    else:
        return None

def list_package_resources_by_dir(package_dir, include_depends, subdir, rfilter=os.path.isfile):
    """
    List resources in a package directory within a particular
    subdirectory. This is useful for listing messages, services, etc...
    @param package_dir: package directory location
    @type  package_dir: str
    @param subdir: name of subdirectory
    @type  subdir: str
    @param include_depends: if True, include resources in dependencies as well    
    @type  include_depends: bool
    @param rfilter: resource filter function that returns true if filename is the desired resource type
    @type  rfilter: fn(filename)->bool
    """
    package = os.path.basename(package_dir)
    resources = []
    dir = roslib.packages._get_pkg_subdir_by_dir(package_dir, subdir, False)
    if os.path.isdir(dir):
        resources = [roslib.names.resource_name(package, f, my_pkg=package) \
                     for f in os.listdir(dir) if rfilter(os.path.join(dir, f))]
    else:
        resources = []
    if include_depends:
        depends = _get_manifest_by_dir(package_dir).depends
        dirs = [roslib.packages.get_pkg_subdir(d.package, subdir, False) for d in depends]
        for (dep, dir_) in zip(depends, dirs): #py3k
            if not dir_ or not os.path.isdir(dir_):
                continue
            resources.extend(\
                [roslib.names.resource_name(dep.package, f, my_pkg=package) \
                 for f in os.listdir(dir_) if rfilter(os.path.join(dir_, f))])
    return resources

def list_package_resources(package, include_depends, subdir, rfilter=os.path.isfile):
    """
    List resources in a package within a particular subdirectory. This is useful for listing
    messages, services, etc...    
    @param package: package name
    @type  package: str
    @param subdir: name of subdirectory
    @type  subdir: str
    @param include_depends: if True, include resources in dependencies as well    
    @type  include_depends: bool
    @param rfilter: resource filter function that returns true if filename is the desired resource type
    @type  rfilter: fn(filename)->bool
    """    
    package_dir = roslib.packages.get_pkg_dir(package)
    return list_package_resources_by_dir(package_dir, include_depends, subdir, rfilter)


########NEW FILE########
__FILENAME__ = rosenv
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$


"""
Warning: do not use this library.  It is unstable and most of the routines
here have been superceded by other libraries (e.g. rospkg).  These
routines will likely be *deleted* in future releases.
"""

import os
import sys

# Global, usually set in setup
ROS_ROOT         = "ROS_ROOT"
ROS_MASTER_URI   = "ROS_MASTER_URI"
ROS_PACKAGE_PATH = "ROS_PACKAGE_PATH"
ROS_HOME         = "ROS_HOME"

# Build-related
ROS_BINDEPS_PATH = "ROS_BINDEPS_PATH"
ROS_BOOST_ROOT = "ROS_BOOST_ROOT"

# Per session
## hostname/address to bind XML-RPC services to. 
ROS_IP           ="ROS_IP"
ROS_HOSTNAME     ="ROS_HOSTNAME"
ROS_NAMESPACE    ="ROS_NAMESPACE"
## directory in which log files are written
ROS_LOG_DIR      ="ROS_LOG_DIR"
## directory in which test result files are written
CATKIN_TEST_RESULTS_DIR = "CATKIN_TEST_RESULTS_DIR"

class ROSEnvException(Exception):
    """Base class of roslib.rosenv errors."""
    pass

import warnings
warnings.warn("roslib.rosenv is deprecated, please use rospkg or rosgraph.rosenv", stacklevel=2)

def get_ros_root(required=True, env=None):
    """
    @param required: (default True). If True, ROS_ROOT must be set and point to a valid directory.
    @type  required: bool
    @param env: override environment dictionary
    @type  env: dict
    @raise ROSEnvException: if required is True and ROS_ROOT is not set
    """
    if env is None:
        env = os.environ
    p = None
    try:
        if ROS_ROOT not in env:
            raise ROSEnvException("""
The %(ROS_ROOT)s environment variable has not been set.
Please set to the location of your ROS installation
before continuing.
"""%globals())

        return env[ROS_ROOT]
    except Exception as e:
        if required:
            raise
        return p

def get_ros_package_path(required=False, env=None):
    """
    @param required: (default False) if True, ROS_PACKAGE_PATH must be
    set and point to a valid directory.
    @type  required: bool
    @raise ROSEnvException: if ROS_PACKAGE_PATH is not set and \a
    required is True
    """
    if env is None:
        env = os.environ
    try:
        return env[ROS_PACKAGE_PATH]
    except KeyError as e:
        if required:
            raise ROSEnvException("%s has not been configured"%ROS_PACKAGE_PATH)

def get_master_uri(required=True, env=None, argv=None):
    """
    Get the ROS_MASTER_URI setting from the command-line args or
    environment, command-line args takes precedence.
    @param required: if True, enables exception raising
    @type  required: bool
    @param env: override environment dictionary
    @type  env: dict
    @param argv: override sys.argv
    @type  argv: [str]
    @raise ROSEnvException: if ROS_MASTER_URI value is invalidly
    specified or if required and ROS_MASTER_URI is not set
    """    
    if env is None:
        env = os.environ
    if argv is None:
        argv = sys.argv
    try:
        for arg in argv:
            if arg.startswith('__master:='):
                val = None
                try:
                    _, val = arg.split(':=')
                except:
                    pass
                
                # we ignore required here because there really is no
                # correct return value as the configuration is bad
                # rather than unspecified
                if not val:
                    raise ROSEnvException("__master remapping argument '%s' improperly specified"%arg)
                return val
        return env[ROS_MASTER_URI]
    except KeyError as e:
        if required:
            raise ROSEnvException("%s has not been configured"%ROS_MASTER_URI)
        
def get_ros_home(env=None):
    """
    Get directory location of '.ros' directory (aka ROS home).
    possible locations for this. The ROS_LOG_DIR environment variable
    has priority. If that is not set, then ROS_HOME/log is used. If
    ROS_HOME is not set, $HOME/.ros/log is used.

    @param env: override os.environ dictionary
    @type  env: dict
    @return: path to use use for log file directory
    @rtype: str
    """
    if env is None:
        env = os.environ
    if ROS_HOME in env:
        return env[ROS_HOME]
    else:
        #slightly more robust than $HOME
        return os.path.join(os.path.expanduser('~'), '.ros')
    
def get_log_dir(env=None):
    """
    Get directory to use for writing log files. There are multiple
    possible locations for this. The ROS_LOG_DIR environment variable
    has priority. If that is not set, then ROS_HOME/log is used. If
    ROS_HOME is not set, $HOME/.ros/log is used.

    @param env: override os.environ dictionary
    @type  env: dict
    @return: path to use use for log file directory
    @rtype: str
    """
    if env is None:
        env = os.environ
    if ROS_LOG_DIR in env:
        return env[ROS_LOG_DIR]
    else:
        return os.path.join(get_ros_home(env), 'log')

def get_test_results_dir(env=None):
    """
    Get directory to use for writing test result files. There are multiple
    possible locations for this. The CATKIN_TEST_RESULTS_DIR environment variable
    has priority. If that is set, CATKIN_TEST_RESULTS_DIR is returned.
    If CATKIN_TEST_RESULTS_DIR is not set, then ROS_HOME/test_results is used. If
    ROS_HOME is not set, $HOME/.ros/test_results is used.

    @param env: environment dictionary (defaults to os.environ)
    @type  env: dict
    @return: path to use use for log file directory
    @rtype: str
    """
    if env is None:
        env = os.environ
        
    if CATKIN_TEST_RESULTS_DIR in env:
        return env[CATKIN_TEST_RESULTS_DIR]
    else:
        return os.path.join(get_ros_home(env), 'test_results')

# this is a copy of the roslogging utility. it's been moved here as it is a common
# routine for programs using accessing ROS directories
def makedirs_with_parent_perms(p):
    """
    Create the directory using the permissions of the nearest
    (existing) parent directory. This is useful for logging, where a
    root process sometimes has to log in the user's space.
    @param p: directory to create
    @type  p: str
    """    
    p = os.path.abspath(p)
    parent = os.path.dirname(p)
    # recurse upwards, checking to make sure we haven't reached the
    # top
    if not os.path.exists(p) and p and parent != p:
        makedirs_with_parent_perms(parent)
        s = os.stat(parent)
        os.mkdir(p)

        # if perms of new dir don't match, set anew
        s2 = os.stat(p)
        if s.st_uid != s2.st_uid or s.st_gid != s2.st_gid:
            os.chown(p, s.st_uid, s.st_gid)
        if s.st_mode != s2.st_mode:
            os.chmod(p, s.st_mode)    

########NEW FILE########
__FILENAME__ = rospack
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$
# $Author$

"""
Warning: do not use this library.  It is unstable and most of the routines
here have been superceded by other libraries (e.g. rospkg).  These
routines will likely be *deleted* in future releases.
"""

import os
import sys
import subprocess
import roslib.exceptions
import rospkg

if sys.hexversion > 0x03000000: #Python3
    python3 = True
else:
    python3 = False

import warnings
warnings.warn("roslib.rospack is deprecated, please use rospkg", stacklevel=2)

def rospackexec(args):
    """
    @return: result of executing rospack command (via subprocess). string will be strip()ed.
    @rtype: str
    @raise roslib.exceptions.ROSLibException: if rospack command fails
    """
    rospack_bin = 'rospack'
    if python3:
        val = subprocess.Popen([rospack_bin] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
        val = val.decode().strip()
    else:
        val = (subprocess.Popen([rospack_bin] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0] or '').strip()        
    if val.startswith('rospack:'): #rospack error message
        raise roslib.exceptions.ROSLibException(val)
    return val

def rospack_depends_on_1(pkg):
    """
    @param pkg: package name
    @type  pkg: str
    @return: A list of the names of the packages which depend directly on pkg
    @rtype: list
    """
    return rospackexec(['depends-on1', pkg]).split()

def rospack_depends_on(pkg):
    """
    @param pkg: package name
    @type  pkg: str
    @return: A list of the names of the packages which depend on pkg
    @rtype: list
    """
    return rospackexec(['depends-on', pkg]).split()

def rospack_depends_1(pkg):
    """
    @param pkg: package name
    @type  pkg: str
    @return: A list of the names of the packages which pkg directly depends on
    @rtype: list    
    """
    return rospackexec(['deps1', pkg]).split()

def rospack_depends(pkg):
    """
    @param pkg: package name
    @type  pkg: str
    @return: A list of the names of the packages which pkg depends on
    @rtype: list    
    """
    return rospackexec(['deps', pkg]).split()

def rospack_plugins(pkg):
    """
    @param pkg: package name
    @type  pkg: str
    @return: A list of the names of the packages which provide a plugin for pkg
    @rtype: list    
    """
    val = rospackexec(['plugins', '--attrib=plugin', pkg])
    if val:
      return [tuple(x.split(' ')) for x in val.split('\n')]
    else:
      return []

def rosstackexec(args):
    """
    @return: result of executing rosstack command (via subprocess). string will be strip()ed.
    @rtype:  str
    @raise roslib.exceptions.ROSLibException: if rosstack command fails
    """
    rosstack_bin = 'rosstack'
    if python3:
        val = subprocess.Popen([rosstack_bin] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
        val = val.decode().strip()
    else:
        val = (subprocess.Popen([rosstack_bin] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0] or '').strip()
    if val.startswith('rosstack:'): #rospack error message
        raise roslib.exceptions.ROSLibException(val)
    return val

def rosstack_depends_on(s):
    """
    @param s: stack name
    @type  s: str
    @return: A list of the names of the stacks which depend on s
    @rtype: list
    """
    return rosstackexec(['depends-on', s]).split()

def rosstack_depends_on_1(s):
    """
    @param s: stack name
    @type  s: str
    @return: A list of the names of the stacks which depend directly on s
    @rtype: list
    """
    return rosstackexec(['depends-on1', s]).split()

def rosstack_depends(s):
    """
    @param s: stack name
    @type  s: str
    @return: A list of the names of the stacks which s depends on 
    @rtype: list
    """
    return rosstackexec(['depends', s]).split()

def rosstack_depends_1(s):
    """
    @param s: stack name
    @type  s: str
    @return: A list of the names of the stacks which s depends on directly
    @rtype: list
    """
    return rosstackexec(['depends1', s]).split()

########NEW FILE########
__FILENAME__ = scriptutil
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$
# $Author$

"""
Warning: do not use this library.  It is unstable and most of the routines
here have been superceded by other libraries (e.g. rospkg).  These
routines will likely be *deleted* in future releases.
"""

import os
import sys

import roslib.names 

## caller ID for master calls where caller ID is not vital
_GLOBAL_CALLER_ID = '/script'


import warnings
def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emmitted
    when the function is used."""
    def newFunc(*args, **kwargs):
        warnings.warn("Call to deprecated function %s." % func.__name__,
                      category=DeprecationWarning, stacklevel=2)
        return func(*args, **kwargs)
    newFunc.__name__ = func.__name__
    newFunc.__doc__ = func.__doc__
    newFunc.__dict__.update(func.__dict__)
    return newFunc

@deprecated
def script_resolve_name(script_name, name):
    """
    Name resolver for scripts. Supports ROS_NAMESPACE.  Does not
    support remapping arguments.
    @param name: name to resolve
    @type  name: str
    @param script_name: name of script. script_name must not
    contain a namespace.
    @type  script_name: str
    @return: resolved name
    @rtype: str
    """
    if not name: #empty string resolves to namespace
        return roslib.names.get_ros_namespace()
    #Check for global name: /foo/name resolves to /foo/name
    if roslib.names.is_global(name):
        return name
    #Check for private name: ~name resolves to /caller_id/name
    elif roslib.names.is_private(name):
        return ns_join(roslib.names.make_caller_id(script_name), name[1:])
    return roslib.names.get_ros_namespace() + name

@deprecated
def get_master():
    """
    Get an XMLRPC handle to the Master. It is recommended to use the
    `rosgraph.masterapi` library instead, as it provides many
    conveniences.
    
    @return: XML-RPC proxy to ROS master
    @rtype: xmlrpclib.ServerProxy
    @raises ValueError if master URI is invalid
    """
    try:
        import xmlrpc.client as xmlrpcclient  #Python 3.x
    except ImportError:
        import xmlrpclib as xmlrpcclient #Python 2.x
    
    # changed this to not look as sys args and remove dependency on roslib.rosenv for cleaner cleanup
    uri = os.environ['ROS_MASTER_URI']
    return xmlrpcclient.ServerProxy(uri)

@deprecated
def get_param_server():
    """
    @return: ServerProxy XML-RPC proxy to ROS parameter server
    @rtype: xmlrpclib.ServerProxy
    """
    return get_master()

########NEW FILE########
__FILENAME__ = srvs
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$
# $Author$
"""
ROS Service Description Language Spec
Implements U{http://ros.org/wiki/srv}
"""

import os
import sys
import re

try:
    from cStringIO import StringIO # Python 2.x
except ImportError:
    from io import StringIO # Python 3.x

import roslib.msgs
import roslib.names
import roslib.packages
import roslib.resources

# don't directly use code from this, though we do depend on the
# manifest.Depend data type
import roslib.manifest

## file extension
EXT = '.srv' #alias
SEP = '/' #e.g. std_msgs/String
## input/output deliminator
IODELIM   = '---'
COMMENTCHAR = roslib.msgs.COMMENTCHAR

VERBOSE = False
## @return: True if msg-related scripts should print verbose output
def is_verbose():
    return VERBOSE

## set whether msg-related scripts should print verbose output
def set_verbose(v):
    global VERBOSE
    VERBOSE = v

class SrvSpecException(Exception): pass

# msg spec representation ##########################################

class SrvSpec(object):
    
    def __init__(self, request, response, text, full_name = '', short_name = '', package = ''):
        self.request = request
        self.response = response
        self.text = text
        self.full_name = full_name
        self.short_name = short_name
        self.package = package
        
    def __eq__(self, other):
        if not other or not isinstance(other, SrvSpec):
            return False
        return self.request == other.request and \
               self.response == other.response and \
               self.text == other.text and \
               self.full_name == other.full_name and \
               self.short_name == other.short_name and \
               self.package == other.package
    
    def __ne__(self, other):
        if not other or not isinstance(other, SrvSpec):
            return True
        return not self.__eq__(other)

    def __repr__(self):
        return "SrvSpec[%s, %s]"%(repr(self.request), repr(self.response))
    
# srv spec loading utilities ##########################################

## @internal
## predicate for filtering directory list. matches message files
def _srv_filter(f):
    return os.path.isfile(f) and f.endswith(EXT)

# also used by doxymaker
def list_srv_types(package, include_depends):
    """
    list all services in the specified package
    @param package: name of package to search
    @type  package: str
    @param include_depends: if True, will also list services in package dependencies
    @type  include_depends: bool
    @return: service type names
    @rtype: [str]
    """
    types = roslib.resources.list_package_resources(package, include_depends, 'srv', _srv_filter)
    return [x[:-len(EXT)] for x in types]

def srv_file(package, type_):
    """
    @param package: name of package .srv file is in
    @type  package: str
    @param type_: type name of service
    @type  type_: str
    @return: file path of .srv file in specified package
    @rtype: str
    """
    return roslib.packages.resource_file(package, 'srv', type_+EXT)

def get_pkg_srv_specs(package):
    """
    List all messages that a package contains
    @param depend: roslib.manifest.Depend object representing package
    to load messages from
    @type  depend: Depend
    @return: list of message type names and specs for package, as well as a list
    of message names that could not be processed. 
    @rtype: [(str,roslib.MsgSpec), [str]]
    """
    #almost identical to roslib.msgs.get_pkg_msg_specs
    types = list_srv_types(package, False)
    specs = [] #no fancy list comprehension as we want to show errors
    failures = []
    for t in types:
        try: 
            spec = load_from_file(srv_file(package, t), package)
            specs.append(spec)
        except Exception as e:
            failures.append(t)
            sys.stderr.write("ERROR: unable to load %s\n"%(t))
    return specs, failures

def load_from_string(text, package_context='', full_name='', short_name=''):
    """
    @param text: .msg text 
    @type  text: str
    @param package_context: context to use for msgTypeName, i.e. the package name,
    or '' to use local naming convention.
    @type  package_context: str
    @return: Message type name and message specification
    @rtype: roslib.MsgSpec
    @raise roslib.MsgSpecException: if syntax errors or other problems are detected in file
    """
    text_in  = StringIO()
    text_out = StringIO()
    accum = text_in
    for l in text.split('\n'):
        l = l.split(COMMENTCHAR)[0].strip() #strip comments        
        if l.startswith(IODELIM): #lenient, by request
            accum = text_out
        else:
            accum.write(l+'\n')
    # create separate roslib.msgs objects for each half of file
    
    msg_in = roslib.msgs.load_from_string(text_in.getvalue(), package_context, '%sRequest'%(full_name), '%sRequest'%(short_name))
    msg_out = roslib.msgs.load_from_string(text_out.getvalue(), package_context, '%sResponse'%(full_name), '%sResponse'%(short_name))
    return SrvSpec(msg_in, msg_out, text, full_name, short_name, package_context)

def load_from_file(file_name, package_context=''):
    """
    Convert the .srv representation in the file to a SrvSpec instance.
    @param file_name: name of file to load from
    @type  file_name: str
    @param package_context: context to use for type name, i.e. the package name,
    or '' to use local naming convention.
    @type package_context: str
    @return: Message type name and message specification
    @rtype: (str, L{SrvSpec})
    @raise SrvSpecException: if syntax errors or other problems are detected in file
    """
    if VERBOSE:
        if package_context:
            sys.stdout.write("Load spec from %s into namespace [%s]\n"%(file_name, package_context))
        else:
            sys.stdout.write("Load spec from %s\n"%(file_name))
    base_file_name = os.path.basename(file_name)
    type_ = base_file_name[:-len(EXT)]
    base_type_ = type_
    # determine the type name
    if package_context:
        while package_context.endswith(SEP):
            package_context = package_context[:-1] #strip message separators
        type_ = "%s%s%s"%(package_context, SEP, type_)
    if not roslib.names.is_legal_resource_name(type_):
        raise SrvSpecException("%s: %s is not a legal service type name"%(file_name, type_))
    
    f = open(file_name, 'r')
    try:
        text = f.read()
        return (type_, load_from_string(text, package_context, type_, base_type_))
    finally:
        f.close()





########NEW FILE########
__FILENAME__ = stacks
#! /usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$

"""
Warning: do not use this library.  It is unstable and most of the routines
here have been superceded by other libraries (e.g. rospkg).  These
routines will likely be *deleted* in future releases.
"""

import os
import sys
import re

import roslib.packages
import roslib.stack_manifest

import rospkg

ROS_ROOT=rospkg.environment.ROS_ROOT
ROS_PACKAGE_PATH=rospkg.environment.ROS_PACKAGE_PATH

STACK_FILE = 'stack.xml'
ROS_STACK = 'ros'

class ROSStackException(Exception): pass
class InvalidROSStackException(ROSStackException): pass

def stack_of(pkg, env=None):
    """
    @param env: override environment variables
    @type  env: {str: str}
    @return: name of stack that pkg is in, or None if pkg is not part of a stack
    @rtype: str
    @raise roslib.packages.InvalidROSPkgException: if pkg cannot be located
    """
    if env is None:
        env = os.environ
    pkg_dir = roslib.packages.get_pkg_dir(pkg, ros_root=env[ROS_ROOT], ros_package_path=env.get(ROS_PACKAGE_PATH, None))
    d = pkg_dir
    while d and os.path.dirname(d) != d:
        stack_file = os.path.join(d, STACK_FILE)
        if os.path.exists(stack_file):
            #TODO: need to resolve issues regarding whether the
            #stack.xml or the directory defines the stack name
            return os.path.basename(d)
        d = os.path.dirname(d)
        
def get_stack_dir(stack, env=None):
    """
    Get the directory of a ROS stack. This will initialize an internal
    cache and return cached results if possible.
    
    This routine is not thread-safe to os.environ changes.
    
    @param env: override environment variables
    @type  env: {str: str}
    @param stack: name of ROS stack to locate on disk
    @type  stack: str
    @return: directory of stack.
    @rtype: str
    @raise InvalidROSStackException: if stack cannot be located.
    """
    _init_rosstack(env=env)
    try:
        return _rosstack.get_path(stack)
    except rospkg.ResourceNotFound:
        # preserve old signature
        raise InvalidROSStackException(stack)

_rosstack = None
_ros_paths = None

def _init_rosstack(env=None):
    global _rosstack, _ros_paths
    if env is None:
        env = os.environ
    ros_paths = rospkg.get_ros_paths(env)
    if ros_paths != _ros_paths:
        _ros_paths = ros_paths
        _rosstack = rospkg.RosStack(ros_paths)
    
def list_stacks(env=None):
    """
    Get list of all ROS stacks. This uses an internal cache.

    This routine is not thread-safe to os.environ changes.

    @param env: override environment variables
    @type  env: {str: str}
    @return: complete list of stacks names in ROS environment
    @rtype: [str]
    """
    _init_rosstack(env=env)
    return _rosstack.list()

def list_stacks_by_path(path, stacks=None, cache=None):
    """
    List ROS stacks within the specified path.

    Optionally, a cache dictionary can be provided, which will be
    updated with the stack->path mappings. list_stacks_by_path() does
    NOT returned cached results -- it only updates the cache.
    
    @param path: path to list stacks in
    @type  path: str
    @param stacks: list of stacks to append to. If stack is
      already present in stacks, it will be ignored.
    @type  stacks: [str]
    @param cache: (optional) stack path cache to update. Maps stack name to directory path.
    @type  cache: {str: str}
    @return: complete list of stack names in ROS environment. Same as stacks parameter.
    @rtype: [str]
    """
    if stacks is None:
        stacks = []
    MANIFEST_FILE = rospkg.MANIFEST_FILE
    basename = os.path.basename
    for d, dirs, files in os.walk(path, topdown=True):
        if STACK_FILE in files:
            stack = basename(d)
            if stack not in stacks:
                stacks.append(stack)
                if cache is not None:
                    cache[stack] = d
            del dirs[:]
            continue #leaf
        elif MANIFEST_FILE in files:
            del dirs[:]
            continue #leaf     
        elif 'rospack_nosubdirs' in files:
            del dirs[:]
            continue  #leaf
        # remove hidden dirs (esp. .svn/.git)
        [dirs.remove(di) for di in dirs if di[0] == '.']
        for sub_d in dirs:
            # followlinks=True only available in Python 2.6, so we
            # have to implement manually
            sub_p = os.path.join(d, sub_d)
            if os.path.islink(sub_p):
                stacks.extend(list_stacks_by_path(sub_p, cache=cache))
    return stacks

# #2022
def expand_to_packages(names, env=None):
    """
    Expand names into a list of packages. Names can either be of packages or stacks.

    @param names: names of stacks or packages
    @type  names: [str]
    @return: ([packages], [not_found]). expand_packages() returns two
    lists. The first is of packages names. The second is a list of
    names for which no matching stack or package was found. Lists may have duplicates.
    @rtype: ([str], [str])
    """
    if env is None:
        env = os.environ
    ros_paths = rospkg.get_ros_paths(env)
    rospack = rospkg.RosPack(ros_paths)
    rosstack = rospkg.RosStack(ros_paths)
    return rospkg.expand_to_packages(names, rospack, rosstack)

def get_stack_version(stack, env=None):
    """
    @param env: override environment variables
    @type  env: {str: str}

    @return: version number of stack, or None if stack is unversioned.
    @rtype: str
    """
    _init_rosstack(env=env)
    return _rosstack.get_stack_version(stack)

def get_stack_version_by_dir(stack_dir):
    """
    Get stack version where stack_dir points to root directory of stack.
    
    @param env: override environment variables
    @type  env: {str: str}

    @return: version number of stack, or None if stack is unversioned.
    @rtype: str
    """
    # REP 109: check for <version> tag first, then CMakeLists.txt
    manifest_filename = os.path.join(stack_dir, STACK_FILE)
    if os.path.isfile(manifest_filename):
        m = roslib.stack_manifest.parse_file(manifest_filename)
        if m.version:
            return m.version
    
    cmake_filename = os.path.join(stack_dir, 'CMakeLists.txt')
    if os.path.isfile(cmake_filename):
        with open(cmake_filename) as f:
            return _get_cmake_version(f.read())
    else:
        return None

def _get_cmake_version(text):
    for l in text.split('\n'):
        if l.strip().startswith('rosbuild_make_distribution'):
            x_re = re.compile(r'[()]')
            lsplit = x_re.split(l.strip())
            if len(lsplit) < 2:
                raise ReleaseException("couldn't find version number in CMakeLists.txt:\n\n%s"%l)
            return lsplit[1]

########NEW FILE########
__FILENAME__ = stack_manifest
#! /usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$
# $Author$

"""
Warning: do not use this library.  It is unstable and most of the routines
here have been superceded by other libraries (e.g. rospkg).  These
routines will likely be *deleted* in future releases.
"""

import sys
import os
import getopt

STACK_FILE = 'stack.xml'

import roslib.manifestlib
# re-export symbols so that external code does not have to import manifestlib as well
from roslib.manifestlib import ManifestException, StackDepend

class StackManifest(roslib.manifestlib._Manifest):
    """
    Object representation of a ROS manifest file
    """
    __slots__ = []
    def __init__(self):
        """
        Create an empty stack manifest instance.
        """
        super(StackManifest, self).__init__('stack')
        
def _stack_file_by_dir(stack_dir, required=True):
    """
    @param stack_dir: path to stack directory
    @type  stack_dir: str
    @param required: require that the directory exist
    @type  required: bool
    @return: path to manifest file of stack
    @rtype: str
    @raise InvalidROSPkgException: if required is True and manifest file cannot be located
    """
    try:
        p = os.path.join(stack_dir, STACK_FILE)
        if not required and not os.path.exists(p):
            return p
        if not os.path.isfile(p):
            raise roslib.stacks.InvalidROSStackException("""
Stack '%(stack_dir)s' is improperly configured: no manifest file is present.
"""%locals())
        return p
    except roslib.stacks.InvalidROSStackException as e:
        if required:
            raise

def stack_file(stack, required=True):
    """
    @param stack: stack name
    @type  stack: str
    @param required: require that the directory exist
    @type  required: bool
    @return: path to manifest file of stack
    @rtype:  str
    @raise InvalidROSPkgException: if required is True and manifest file cannot be located
    """
    d = roslib.stacks.get_stack_dir(stack)
    return _stack_file_by_dir(d, required)
        
def parse_file(file):
    """
    Parse stack.xml file
    @param file: stack.xml file path
    @param file: str
    @return: StackManifest instance
    @rtype:  L{StackManifest}
    """
    return roslib.manifestlib.parse_file(StackManifest(), file)

def parse(string, filename='string'):
    """
    Parse stack.xml string contents
    @param string: stack.xml contents
    @type  string: str
    @return: StackManifest instance
    @rtype:  L{StackManifest}
    """
    s = roslib.manifestlib.parse(StackManifest(), string, filename)
    #TODO: validate
    return s

########NEW FILE########
__FILENAME__ = fake_node
#!/usr/bin/env python
# this node only exists to test find_node functionality

print("hello")

########NEW FILE########
__FILENAME__ = test_roslib
# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os
import sys
  
def test_load_manifest():
    # this is a bit of a noop as it's a prerequisite of running with rosunit
    import roslib
    roslib.load_manifest('roslib')
        
def test_interactive():
    import roslib
        
    # make sure that it's part of high-level API
    assert not roslib.is_interactive(), "interactive should be false by default"
    for v in [True, False]:
        roslib.set_interactive(v)        
        assert v == roslib.is_interactive()
        

########NEW FILE########
__FILENAME__ = test_roslib_exceptions
# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os
import sys

def test_exceptions():
    from roslib.exceptions import ROSLibException
    assert isinstance(ROSLibException(), Exception)

########NEW FILE########
__FILENAME__ = test_roslib_manifest
# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os
import sys
import unittest

import roslib

def get_test_path():
    return os.path.abspath(os.path.dirname(__file__))

class RoslibManifestTest(unittest.TestCase):
  
  def test_ManifestException(self):
    from roslib.manifest import ManifestException
    self.assert_(isinstance(ManifestException(), Exception))

  def test_Depend(self):
    from roslib.manifestlib import Depend, ManifestException
    for bad in [None, '']:
      try:
        Depend(bad)
        self.fail("should have failed on [%s]"%bad)
      except ValueError: pass
    
    d = Depend('roslib')
    self.assertEquals('roslib', str(d))
    self.assertEquals('roslib', repr(d))    

    self.assertEquals('<depend package="roslib" />',d.xml())
    self.assertEquals(d, Depend('roslib'))
    self.assertNotEquals(d, Depend('roslib2'))
    self.assertNotEquals(d, 1)

  def test_ROSDep(self):
    from roslib.manifest import ROSDep, ManifestException
    for bad in [None, '']:
      try:
        rd = ROSDep(bad)
        self.fail("should have failed on [%s]"%bad)
      except ValueError: pass
    
    rd = ROSDep('python')
    self.assertEquals('<rosdep name="python" />',rd.xml())
    
  def test_VersionControl(self):
    from roslib.manifest import VersionControl, ManifestException
    ros_svn = 'https://ros.svn.sf.net/svnroot'
    
    bad = [
      (None, ros_svn),
      ]
    for type_, url in bad:
      try:
        VersionControl(type_,url)
        self.fail("should have failed on [%s] [%s]"%(type_, url))
      except ValueError: pass
      
    tests = [
      ('svn', ros_svn, '<versioncontrol type="svn" url="%s" />'%ros_svn),
      ('cvs', None, '<versioncontrol type="cvs" />'),
      ]
    for type_, url, xml in tests:
      vc = VersionControl(type_, url)
      self.assertEquals(type_, vc.type)
      self.assertEquals(url, vc.url)      
      self.assertEquals(xml, vc.xml())

  def _subtest_parse_example1(self, m):
    from roslib.manifest import Manifest
    self.assert_(isinstance(m, Manifest))
    self.assertEquals("a brief description", m.brief)
    self.assertEquals("Line 1\nLine 2", m.description.strip())
    self.assertEquals("The authors\ngo here", m.author.strip())    
    self.assertEquals("Public Domain\nwith other stuff", m.license.strip())
    self.assertEquals("http://pr.willowgarage.com/package/", m.url)
    self.assertEquals("http://www.willowgarage.com/files/willowgarage/robot10.jpg", m.logo)
    dpkgs = [d.package for d in m.depends]
    self.assertEquals(set(['pkgname', 'common']), set(dpkgs))
    rdpkgs = [d.name for d in m.rosdeps]
    self.assertEquals(set(['python', 'bar', 'baz']), set(rdpkgs))
    
  def test_parse_example1_file(self):
    from roslib.manifest import parse_file, Manifest
    p = os.path.join(get_test_path(), 'manifest_tests', 'example1.xml')
    self._subtest_parse_example1(parse_file(p))

  def test_parse_example1_string(self):
    from roslib.manifest import parse, Manifest
    self._subtest_parse_example1(parse(EXAMPLE1))

  def test_Manifest_str(self):
    # just make sure it doesn't crash
    from roslib.manifest import parse
    str(parse(EXAMPLE1))
    
  def test_Manifest_xml(self):
    from roslib.manifest import parse
    m = parse(EXAMPLE1)
    self._subtest_parse_example1(m)
    # verify roundtrip
    m2 = parse(m.xml())
    self._subtest_parse_example1(m2)
    
    
  def test_parse_bad_file(self):
    from roslib.manifest import parse_file, Manifest
    # have to import from ManifestException due to weirdness when run in --cov mode
    from roslib.manifestlib import ManifestException
    base_p = os.path.join(get_test_path(), 'manifest_tests')
    for b in ['bad1.xml', 'bad2.xml', 'bad3.xml']:
      p = os.path.join(base_p, b)
      try:
        parse_file(p)
        self.fail("parse should have failed on bad manifest")
      except ManifestException as e:
        print(str(e))
        self.assert_(b in str(e), "file name should be in error message: %s"%(str(e)))
    
EXAMPLE1 = """<package>
  <description brief="a brief description">Line 1
Line 2
  </description>
  <author>The authors
go here</author>
  <license>Public Domain
with other stuff</license>
  <url>http://pr.willowgarage.com/package/</url>
  <logo>http://www.willowgarage.com/files/willowgarage/robot10.jpg</logo>
  <depend package="pkgname" />
  <depend package="common"/>
  <export>
    <cpp cflags="-I${prefix}/include" lflags="-L${prefix}/lib -lros"/>
    <cpp os="osx" cflags="-I${prefix}/include" lflags="-L${prefix}/lib -lrosthread -framework CoreServices"/>
  </export>
  <rosdep name="python" />
  <rosdep name="bar" />
  <rosdep name="baz" />
  <rosbuild2> 
    <depend thirdparty="thisshouldbeokay"/> 
  </rosbuild2>
</package>"""

########NEW FILE########
__FILENAME__ = test_roslib_manifestlib
# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os
import struct
import sys
import unittest

import roslib

class RoslibManifestlibTest(unittest.TestCase):
  
  def test_ManifestException(self):
    from roslib.manifestlib import ManifestException
    self.assert_(isinstance(ManifestException(), Exception))

  def test_Platform(self):
    from roslib.manifestlib import Platform, ManifestException
    for bad in [None, '']:
      try:
        Platform(bad, '1')
        self.fail("should have failed on [%s]"%bad)
      except ValueError: pass
      try:
        Platform('ubuntu', bad)
        self.fail("should have failed on [%s]"%bad)
      except ValueError: pass
    
    p = Platform('ubuntu', '8.04')
    self.assertEquals('ubuntu 8.04', str(p))
    self.assertEquals('ubuntu 8.04', repr(p))

    self.assertEquals('<platform os="ubuntu" version="8.04"/>',p.xml())
    self.assertEquals(p, Platform('ubuntu', '8.04'))
    self.assertEquals(p, Platform('ubuntu', '8.04', notes=None))
    self.assertNotEquals(p, Platform('ubuntu', '8.04', 'some notes'))
    self.assertNotEquals(p, 'foo')
    self.assertNotEquals(p, 1)

    # note: probably actually "osx"
    p = Platform('OS X', '10.6', 'macports')
    self.assertEquals('OS X 10.6', str(p))
    self.assertEquals('OS X 10.6', repr(p))

    self.assertEquals('<platform os="OS X" version="10.6" notes="macports"/>',p.xml())
    self.assertEquals(p, p)
    self.assertEquals(p, Platform('OS X', '10.6', 'macports'))
    self.assertNotEquals(p, Platform('OS X', '10.6'))
    self.assertNotEquals(p, 'foo')
    self.assertNotEquals(p, 1)
    

  def test_Depend(self):
    from roslib.manifestlib import Depend, StackDepend, ManifestException
    for bad in [None, '']:
      try:
        Depend(bad)
        self.fail("should have failed on [%s]"%bad)
      except ValueError: pass
    
    d = Depend('roslib')
    self.assertEquals('roslib', str(d))
    self.assertEquals('roslib', repr(d))    

    self.assertEquals('<depend package="roslib" />',d.xml())
    self.assertEquals(d, Depend('roslib'))
    self.assertNotEquals(d, StackDepend('roslib'))
    self.assertNotEquals(d, Depend('roslib2'))
    self.assertNotEquals(d, 1)
    
  def test_StackDepend(self):
    from roslib.manifestlib import Depend, StackDepend, ManifestException
    for bad in [None, '']:
      try:
        StackDepend(bad)
        self.fail("should have failed on [%s]"%bad)
      except ValueError: pass
    
    d = StackDepend('common')
    self.assertEquals('common', str(d))
    self.assertEquals('common', repr(d))    

    self.assertEquals('<depend stack="common" />',d.xml())
    self.assertEquals(d, StackDepend('common'))
    self.assertNotEquals(d, Depend('common'))
    self.assertNotEquals(d, StackDepend('common2'))
    self.assertNotEquals(d, 1)

  def test_ROSDep(self):
    from roslib.manifestlib import ROSDep, ManifestException
    for bad in [None, '']:
      try:
        rd = ROSDep(bad)
        self.fail("should have failed on [%s]"%bad)
      except ValueError: pass
    
    rd = ROSDep('python')
    self.assertEquals('<rosdep name="python" />',rd.xml())
    
  def test_VersionControl(self):
    from roslib.manifestlib import VersionControl, ManifestException
    ros_svn = 'https://ros.svn.sf.net/svnroot'
    
    bad = [
      (None, ros_svn),
      ]
    for type_, url in bad:
      try:
        VersionControl(type_,url)
        self.fail("should have failed on [%s] [%s]"%(type_, url))
      except ValueError: pass
      
    tests = [
      ('svn', ros_svn, '<versioncontrol type="svn" url="%s" />'%ros_svn),
      ('cvs', None, '<versioncontrol type="cvs" />'),
      ]
    for type_, url, xml in tests:
      vc = VersionControl(type_, url)
      self.assertEquals(type_, vc.type)
      self.assertEquals(url, vc.url)      
      self.assertEquals(xml, vc.xml())

  def _subtest_parse_example1(self, m):
    from roslib.manifestlib import _Manifest
    self.assert_(isinstance(m, _Manifest))
    self.assertEquals("a brief description", m.brief)
    self.assertEquals("Line 1\nLine 2", m.description.strip())
    self.assertEquals("The authors\ngo here", m.author.strip())    
    self.assertEquals("Public Domain\nwith other stuff", m.license.strip())
    self.assertEquals("http://pr.willowgarage.com/package/", m.url)
    self.assertEquals("http://www.willowgarage.com/files/willowgarage/robot10.jpg", m.logo)
    dpkgs = [d.package for d in m.depends]
    self.assertEquals(set(['pkgname', 'common']), set(dpkgs))
    rdpkgs = [d.name for d in m.rosdeps]
    self.assertEquals(set(['python', 'bar', 'baz']), set(rdpkgs))
    for p in m.platforms:
      if p.os == 'ubuntu':
        self.assertEquals("8.04", p.version)
        self.assertEquals('', p.notes)        
      elif p.os == 'OS X':
        self.assertEquals("10.6", p.version)
        self.assertEquals("macports", p.notes)        
      else:
        self.fail("unknown platform "+str(p))

  def _subtest_parse_stack_example1(self, m):
    from roslib.manifestlib import _Manifest
    self.assert_(isinstance(m, _Manifest))
    self.assertEquals('stack', m._type)
    self.assertEquals("a brief description", m.brief)
    self.assertEquals("Line 1\nLine 2", m.description.strip())
    self.assertEquals("The authors\ngo here", m.author.strip())    
    self.assertEquals("Public Domain\nwith other stuff", m.license.strip())
    self.assertEquals("http://ros.org/stack/", m.url)
    self.assertEquals("http://www.willowgarage.com/files/willowgarage/robot10.jpg", m.logo)
    dpkgs = [d.stack for d in m.depends]
    self.assertEquals(set(['stackname', 'common']), set(dpkgs))
    self.assertEquals([], m.rosdeps)
    self.assertEquals([], m.exports)    

  def _subtest_parse_stack_version(self, m):
    self.assertEquals("1.2.3", m.version)

  def test_parse_example1_file(self):
    from roslib.manifestlib import parse_file, _Manifest
    p = os.path.join(get_test_path(), 'manifest_tests', 'example1.xml')
    self._subtest_parse_example1(parse_file(_Manifest(), p))
    
    p = os.path.join(get_test_path(), 'manifest_tests', 'stack_example1.xml')
    self._subtest_parse_stack_example1(parse_file(_Manifest('stack'), p))

    p = os.path.join(get_test_path(), 'manifest_tests', 'stack_version.xml')
    self._subtest_parse_stack_version(parse_file(_Manifest('stack'), p))

  def test_parse_example1_string(self):
    from roslib.manifestlib import parse, _Manifest
    self._subtest_parse_example1(parse(_Manifest(), EXAMPLE1))
    self._subtest_parse_stack_example1(parse(_Manifest('stack'), STACK_EXAMPLE1))
    
  def test__Manifest(self):
    from roslib.manifestlib import _Manifest
    m = _Manifest()
    # check defaults
    self.assertEquals('package', m._type)
    m = _Manifest('stack')
    self.assertEquals('stack', m._type)    
    
  def test_Manifest_str(self):
    # just make sure it doesn't crash
    from roslib.manifestlib import parse, _Manifest
    str(parse(_Manifest(), EXAMPLE1))
    
  def test_Manifest_xml(self):
    from roslib.manifestlib import parse, _Manifest
    m = _Manifest()
    parse(m, EXAMPLE1)
    self._subtest_parse_example1(m)
    # verify roundtrip
    m2 = _Manifest()
    parse(m2, m.xml())
    self._subtest_parse_example1(m2)
    
  # bad file examples should be more like the roslaunch tests where there is just 1 thing wrong
  def test_parse_bad_file(self):
    from roslib.manifestlib import parse_file, _Manifest, ManifestException
    base_p = os.path.join(get_test_path(), 'manifest_tests')
    m = _Manifest()
    for b in ['bad1.xml', 'bad2.xml', 'bad3.xml']:
      p = os.path.join(base_p, b)
      try:
        parse_file(m, p)
        self.fail("parse should have failed on bad manifest")
      except ManifestException as e:
        print(str(e))
        self.assert_(b in str(e), "file name should be in error message [%s]"%(str(e)))
    
EXAMPLE1 = """<package>
  <description brief="a brief description">Line 1
Line 2
  </description>
  <author>The authors
go here</author>
  <license>Public Domain
with other stuff</license>
  <url>http://pr.willowgarage.com/package/</url>
  <logo>http://www.willowgarage.com/files/willowgarage/robot10.jpg</logo>
  <depend package="pkgname" />
  <depend package="common"/>
  <export>
    <cpp cflags="-I${prefix}/include" lflags="-L${prefix}/lib -lros"/>
    <cpp os="osx" cflags="-I${prefix}/include" lflags="-L${prefix}/lib -lrosthread -framework CoreServices"/>
  </export>
  <rosdep name="python" />
  <rosdep name="bar" />
  <rosdep name="baz" />
  <platform os="ubuntu" version="8.04" />
  <platform os="OS X" version="10.6" notes="macports" />
  <rosbuild2> 
    <depend thirdparty="thisshouldbeokay"/> 
  </rosbuild2>
</package>"""

STACK_EXAMPLE1 = """<stack>
  <description brief="a brief description">Line 1
Line 2
  </description>
  <author>The authors
go here</author>
  <license>Public Domain
with other stuff</license>
  <url>http://ros.org/stack/</url>
  <logo>http://www.willowgarage.com/files/willowgarage/robot10.jpg</logo>
  <depend stack="stackname" />
  <depend stack="common"/>
</stack>"""

STACK_INVALID1 = """<stack>
  <description brief="a brief description">Line 1</description>
  <author>The authors</author>
  <license>Public Domain</license>
  <rosdep name="python" />
</stack>"""

STACK_INVALID2 = """<stack>
  <description brief="a brief description">Line 1</description>
  <author>The authors</author>
  <license>Public Domain</license>
  <export>
    <cpp cflags="-I${prefix}/include" lflags="-L${prefix}/lib -lros"/>
    <cpp os="osx" cflags="-I${prefix}/include" lflags="-L${prefix}/lib -lrosthread -framework CoreServices"/>
  </export>
</stack>"""


def get_test_path():
    return os.path.abspath(os.path.dirname(__file__))

########NEW FILE########
__FILENAME__ = test_roslib_names
# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os
import sys
import unittest

import roslib.names

class NamesTest(unittest.TestCase):
  
  def test_get_ros_namespace(self):
    if 'ROS_NAMESPACE' in os.environ:
      rosns = os.environ['ROS_NAMESPACE']
      del os.environ['ROS_NAMESPACE']
    else:
      rosns = None
    sysargv = sys.argv

    try:
      sys.argv = []
      self.assertEquals('/', roslib.names.get_ros_namespace())
      self.assertEquals('/', roslib.names.get_ros_namespace(argv=[]))
      self.assertEquals('/', roslib.names.get_ros_namespace(env={}))
      self.assertEquals('/', roslib.names.get_ros_namespace(env={}, argv=[]))

      os.environ['ROS_NAMESPACE'] = 'unresolved'
      self.assertEquals('/unresolved/', roslib.names.get_ros_namespace())
      self.assertEquals('/unresolved/', roslib.names.get_ros_namespace(env={'ROS_NAMESPACE': 'unresolved'}))
      sys.argv = ['foo', '__ns:=unresolved_override']
      self.assertEquals('/unresolved_override/', roslib.names.get_ros_namespace(env={'ROS_NAMESPACE': 'unresolved'}))
      self.assertEquals('/override2/', roslib.names.get_ros_namespace(env={'ROS_NAMESPACE': 'unresolved'}, argv=['foo', '__ns:=override2']))

      sys.argv = []
      os.environ['ROS_NAMESPACE'] = '/resolved/'
      self.assertEquals('/resolved/', roslib.names.get_ros_namespace())
      self.assertEquals('/resolved/', roslib.names.get_ros_namespace(env={'ROS_NAMESPACE': '/resolved'}))

      del os.environ['ROS_NAMESPACE']

      sys.argv = ['foo', '__ns:=unresolved_ns']
      self.assertEquals('/unresolved_ns/', roslib.names.get_ros_namespace())
      self.assertEquals('/unresolved_ns2/', roslib.names.get_ros_namespace(argv=['foo', '__ns:=unresolved_ns2']))
      sys.argv = ['foo', '__ns:=/resolved_ns/']
      self.assertEquals('/resolved_ns/', roslib.names.get_ros_namespace())
      self.assertEquals('/resolved_ns2/', roslib.names.get_ros_namespace(argv=['foo', '__ns:=resolved_ns2']))
    finally:
      sys.argv = sysargv

      # restore
      if rosns:
        os.environ['ROS_NAMESPACE'] = rosns

  def test_make_global_ns(self):
    from roslib.names import make_global_ns

    for n in ['~foo']:
      try:
        make_global_ns(n)
        self.fail("make_global_ns should fail on %s"%n)
      except ValueError: pass

    self.assertEquals('/foo/', make_global_ns('foo'))
    self.assertEquals('/', make_global_ns(''))
    self.assertEquals('/foo/', make_global_ns('/foo'))
    self.assertEquals('/foo/', make_global_ns('/foo/'))    
    self.assertEquals('/foo/bar/', make_global_ns('/foo/bar'))
    self.assertEquals('/foo/bar/', make_global_ns('/foo/bar/'))             

  def test_is_global(self):
    try:
      roslib.names.is_global(None)
      self.fail("is_global should raise exception on invalid param")
    except: pass
    tests = ['/', '/global', '/global2']
    for t in tests:
      self.assert_(roslib.names.is_global(t))
    fails = ['', 'not_global', 'not/global']
    for t in fails:
      self.failIf(roslib.names.is_global(t))
    
  def test_is_private(self):
    try:
      roslib.names.is_private(None)
      self.fail("is_private should raise exception on invalid param")
    except: pass
    tests = ['~name', '~name/sub']
    for t in tests:
      self.assert_(roslib.names.is_private(t))
    fails = ['', 'not_private', 'not/private', 'not/~private', '/not/~private']
    for t in fails:
      self.failIf(roslib.names.is_private(t))
      
  def test_namespace(self):
    from roslib.names import namespace
    try:
      namespace(1)
      self.fail("1")
    except TypeError: pass
    try:
      namespace(None)
      self.fail("None")
    except ValueError: pass
    self.assertEquals('/', namespace(''))
    self.assertEquals('/', namespace('/'))
    self.assertEquals('/', namespace('/foo'))
    self.assertEquals('/', namespace('/foo/'))      
    self.assertEquals('/foo/', namespace('/foo/bar'))
    self.assertEquals('/foo/', namespace('/foo/bar/'))      
    self.assertEquals('/foo/bar/', namespace('/foo/bar/baz'))
    self.assertEquals('/foo/bar/', namespace('/foo/bar/baz/'))

    # unicode tests
    self.assertEquals(u'/', namespace(u''))
    self.assertEquals(u'/', namespace(u'/'))    
    self.assertEquals(u'/foo/bar/', namespace(u'/foo/bar/baz/'))

  def test_nsjoin(self):
    from roslib.names import ns_join

    # private and global names cannot be joined
    self.assertEquals('~name', ns_join('/foo', '~name'))
    self.assertEquals('/name', ns_join('/foo', '/name'))
    self.assertEquals('~name', ns_join('~', '~name'))
    self.assertEquals('/name', ns_join('/', '/name'))

    # ns can be '~' or '/'
    self.assertEquals('~name', ns_join('~', 'name'))
    self.assertEquals('/name', ns_join('/', 'name'))

    self.assertEquals('/ns/name', ns_join('/ns', 'name'))
    self.assertEquals('/ns/name', ns_join('/ns/', 'name'))    
    self.assertEquals('/ns/ns2/name', ns_join('/ns', 'ns2/name'))
    self.assertEquals('/ns/ns2/name', ns_join('/ns/', 'ns2/name'))

    # allow ns to be empty
    self.assertEquals('name', ns_join('', 'name'))
    

  def test_load_mappings(self):
    from roslib.names import load_mappings
    self.assertEquals({}, load_mappings([]))
    self.assertEquals({}, load_mappings(['foo']))
    self.assertEquals({}, load_mappings([':=']))
    self.assertEquals({}, load_mappings([':=:=']))
    self.assertEquals({}, load_mappings(['f:=']))
    self.assertEquals({}, load_mappings([':=b']))
    self.assertEquals({}, load_mappings(['foo:=bar:=baz']))
    # should ignore node param assignments
    self.assertEquals({}, load_mappings(['_foo:=bar']))        
    
    self.assertEquals({'foo': 'bar'}, load_mappings(['foo:=bar']))
    # should allow double-underscore names
    self.assertEquals({'__foo': 'bar'}, load_mappings(['__foo:=bar']))
    self.assertEquals({'foo': 'bar'}, load_mappings(['./f', '-x', '--blah', 'foo:=bar']))
    self.assertEquals({'a': '1', 'b': '2', 'c': '3'}, load_mappings(['c:=3', 'c:=', ':=3', 'a:=1', 'b:=2']))

  def test_resource_name(self):
    from roslib.names import resource_name
    self.assertEquals('foo/bar', resource_name('foo', 'bar'))
    self.assertEquals('bar', resource_name('foo', 'bar', my_pkg='foo'))
    self.assertEquals('foo/bar', resource_name('foo', 'bar', my_pkg='bar'))
    self.assertEquals('foo/bar', resource_name('foo', 'bar', my_pkg=''))
    self.assertEquals('foo/bar', resource_name('foo', 'bar', my_pkg=None))        

  def test_resource_name_base(self):
    from roslib.names import resource_name_base
    self.assertEquals('', resource_name_base('')) 
    self.assertEquals('bar', resource_name_base('bar'))    
    self.assertEquals('bar', resource_name_base('foo/bar'))
    self.assertEquals('bar', resource_name_base('/bar'))
    self.assertEquals('', resource_name_base('foo/'))    

  def test_resource_name_package(self):
    from roslib.names import resource_name_package
    self.assertEquals(None, resource_name_package(''))
    self.assertEquals(None, resource_name_package('foo'))    
    self.assertEquals('foo', resource_name_package('foo/'))
    self.assertEquals('foo', resource_name_package('foo/bar'))    

  def test_package_resource_name(self):
    from roslib.names import package_resource_name
    self.assertEquals(('', ''), package_resource_name(''))
    self.assertEquals(('', 'foo'), package_resource_name('foo'))
    self.assertEquals(('foo', 'bar'), package_resource_name('foo/bar'))
    self.assertEquals(('foo', ''), package_resource_name('foo/'))
    try:
      # only allowed single separator
      package_resource_name("foo/bar/baz")
      self.fail("should have raised ValueError")
    except ValueError:
      pass
      

  def test_is_legal_resource_name(self):
    from roslib.names import is_legal_resource_name
    failures = [None, '', 'hello\n', '\t', 'foo++', 'foo-bar', '#foo', 
                ' name', 'name ',
                '~name', '/name',
                '1name', 'foo\\']
    for f in failures:
      self.failIf(is_legal_resource_name(f), f)
    tests = ['f', 'f1', 'f_', 'foo', 'foo_bar', 'foo/bar', 'roslib/Log']
    for t in tests:
      self.assert_(is_legal_resource_name(t), t)

  def test_is_legal_name(self):
    from roslib.names import is_legal_name
    failures = [None,
                'foo++', 'foo-bar', '#foo',
                'hello\n', '\t', ' name', 'name ',
                'f//b',
                '1name', 'foo\\']
    for f in failures:
      self.failIf(is_legal_name(f), f)
    tests = ['',
             'f', 'f1', 'f_', 'f/', 'foo', 'foo_bar', 'foo/bar', 'foo/bar/baz',
             '~f', '~a/b/c',
             '~/f',
             '/a/b/c/d', '/']
    for t in tests:
      self.assert_(is_legal_name(t), "[%s]"%t)

  def test_is_legal_base_name(self):
    from roslib.names import is_legal_base_name
    failures = [None, '', 'hello\n', '\t', 'foo++', 'foo-bar', '#foo',
                'f/', 'foo/bar', '/', '/a',
                'f//b',
                '~f', '~a/b/c',                
                ' name', 'name ',
                '1name', 'foo\\']
    for f in failures:
      self.failIf(is_legal_base_name(f), f)
    tests = ['f', 'f1', 'f_', 'foo', 'foo_bar']
    for t in tests:
      self.assert_(is_legal_base_name(t), "[%s]"%t)

  def test_is_legal_resource_base_name(self):
    from roslib.names import is_legal_resource_base_name
    failures = [None, '', 'hello\n', '\t', 'foo++', 'foo-bar', '#foo',
                'f/', 'foo/bar', '/', '/a',
                'f//b',
                '~f', '~a/b/c',
                '~/f',
                ' name', 'name ',
                '1name', 'foo\\']
    for f in failures:
      self.failIf(is_legal_resource_base_name(f), f)
    tests = ['f', 'f1', 'f_', 'foo', 'foo_bar']
    for t in tests:
      self.assert_(is_legal_resource_base_name(t), "[%s]"%t)
      
  def test_resolve_name(self):
      from roslib.names import resolve_name
      # TODO: test with remappings
      tests = [
          ('', '/', '/'),
          ('', '/node', '/'),
          ('', '/ns1/node', '/ns1/'),

          ('foo', '', '/foo'),
          ('foo/', '', '/foo'),
          ('/foo', '', '/foo'),
          ('/foo/', '', '/foo'),
          ('/foo', '/', '/foo'),
          ('/foo/', '/', '/foo'),
          ('/foo', '/bar', '/foo'),
          ('/foo/', '/bar', '/foo'),

          ('foo', '/ns1/ns2', '/ns1/foo'),
          ('foo', '/ns1/ns2/', '/ns1/foo'),
          ('foo', '/ns1/ns2/ns3/', '/ns1/ns2/foo'),
          ('foo/', '/ns1/ns2', '/ns1/foo'),
          ('/foo', '/ns1/ns2', '/foo'),
          ('foo/bar', '/ns1/ns2', '/ns1/foo/bar'),
          ('foo//bar', '/ns1/ns2', '/ns1/foo/bar'),
          ('foo/bar', '/ns1/ns2/ns3', '/ns1/ns2/foo/bar'),
          ('foo//bar//', '/ns1/ns2/ns3', '/ns1/ns2/foo/bar'),

          ('~foo', '/', '/foo'),            
          ('~foo', '/node', '/node/foo'),            
          ('~foo', '/ns1/ns2', '/ns1/ns2/foo'),            
          ('~foo/', '/ns1/ns2', '/ns1/ns2/foo'),            
          ('~foo/bar', '/ns1/ns2', '/ns1/ns2/foo/bar'),

          # #3044
          ('~/foo', '/', '/foo'),            
          ('~/foo', '/node', '/node/foo'),            
          ('~/foo', '/ns1/ns2', '/ns1/ns2/foo'),            
          ('~/foo/', '/ns1/ns2', '/ns1/ns2/foo'),            
          ('~/foo/bar', '/ns1/ns2', '/ns1/ns2/foo/bar'),

          ]
      for name, node_name, v in tests:
          self.assertEquals(v, resolve_name(name, node_name))

########NEW FILE########
__FILENAME__ = test_roslib_packages
# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os
import struct
import sys
import unittest

import roslib.packages

class RoslibPackagesTest(unittest.TestCase):
  
  def test_find_node(self):
    import roslib.packages
    d = roslib.packages.get_pkg_dir('roslib')
    p = os.path.join(d, 'test', 'fake_node.py')
    self.assertEquals([p], roslib.packages.find_node('roslib', 'fake_node.py'))
    
    self.assertEquals([], roslib.packages.find_node('roslib', 'not_a_node'))
    
  def test_get_pkg_dir(self):
    import roslib.packages
    import roslib.rospack
    path = os.path.normpath(roslib.rospack.rospackexec(['find', 'roslib']))
    self.assertEquals(path, roslib.packages.get_pkg_dir('roslib'))
    try:
      self.assertEquals(path, roslib.packages.get_pkg_dir('fake_roslib'))      
      self.fail("should have raised")
    except roslib.packages.InvalidROSPkgException: pass

  def test_get_dir_pkg(self):
    import roslib.packages
    path = get_roslib_path()

    res = roslib.packages.get_dir_pkg(path)
    res = (os.path.realpath(res[0]), res[1])
    self.assertEquals((path, 'roslib'), res)
    res = roslib.packages.get_dir_pkg(os.path.join(path, 'test'))
    res = (os.path.realpath(res[0]), res[1])
    self.assertEquals((path, 'roslib'), res)

    # must fail on parent of roslib
    self.assertEquals((None, None), roslib.packages.get_dir_pkg(os.path.dirname(path)))
    
def get_roslib_path():
    return os.path.realpath(os.path.abspath(os.path.join(get_test_path(), '..')))

def get_test_path():
    return os.path.abspath(os.path.dirname(__file__))

########NEW FILE########
__FILENAME__ = test_roslib_rosenv
# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os
import sys
import unittest

import roslib.rosenv

class EnvTest(unittest.TestCase):
  
  def test_get_ros_root(self):
    from roslib.rosenv import get_ros_root
    self.assertEquals(None, get_ros_root(required=False, env={}))
    self.assertEquals(None, get_ros_root(False, {}))    
    try:
      get_ros_root(required=True, env={})
      self.fail("get_ros_root should have failed")
    except: pass

    env = {'ROS_ROOT': '/fake/path'}
    self.assertEquals('/fake/path', get_ros_root(required=False, env=env))
    try:
      get_ros_root(required=True, env=env)
      self.fail("get_ros_root should have failed")
    except: pass

  def test_get_ros_package_path(self):
    from roslib.rosenv import get_ros_package_path
    self.assertEquals(None, get_ros_package_path(required=False, env={}))
    self.assertEquals(None, get_ros_package_path(False, {}))
    try:
      get_ros_package_path(required=True, env={})
      self.fail("get_ros_package_path should have raised")
    except: pass
    env = {'ROS_PACKAGE_PATH': ':'}
    self.assertEquals(':', get_ros_package_path(True, env=env))
    self.assertEquals(':', get_ros_package_path(False, env=env))

    # trip-wire tests. Cannot guarantee that ROS_PACKAGE_PATH is set
    # to valid value on test machine, just make sure logic doesn't crash
    self.assertEquals(os.environ.get('ROS_PACKAGE_PATH', None), get_ros_package_path(required=False))

  def test_get_ros_master_uri(self):
    from roslib.rosenv import get_master_uri
    self.assertEquals(None, get_master_uri(required=False, env={}))
    self.assertEquals(None, get_master_uri(False, {}))
    try:
      get_master_uri(required=True, env={})
      self.fail("get_ros_package_path should have raised")
    except: pass
    env = {'ROS_MASTER_URI': 'http://localhost:1234'}
    self.assertEquals('http://localhost:1234', get_master_uri(True, env=env))
    self.assertEquals('http://localhost:1234', get_master_uri(False, env=env))

    argv = ['__master:=http://localhost:5678']
    self.assertEquals('http://localhost:5678', get_master_uri(False, env=env, argv=argv))

    try:
      argv = ['__master:=http://localhost:5678:=http://localhost:1234']
      get_master_uri(required=False, env=env, argv=argv)
      self.fail("should have thrown")
    except roslib.rosenv.ROSEnvException: pass

    try:
      argv = ['__master:=']
      get_master_uri(False, env=env, argv=argv)
      self.fail("should have thrown")
    except roslib.rosenv.ROSEnvException: pass
    
    # make sure test works with os.environ
    self.assertEquals(os.environ.get('ROS_MASTER_URI', None), get_master_uri(required=False))


########NEW FILE########
__FILENAME__ = test_roslib_stacks
# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os
import sys
import unittest

import roslib
import rospkg

class RoslibStacksTest(unittest.TestCase):
  
    def test_list_stacks(self):
        from roslib.stacks import list_stacks
        l = list_stacks()
        self.assert_('ros' in l)

        # test with env
        test_dir = os.path.join(roslib.packages.get_pkg_dir('roslib'), 'test', 'stack_tests', 's1')
        env = os.environ.copy()
        env['ROS_PACKAGE_PATH'] = test_dir
        val = set(list_stacks(env=env))
        # ros stack not guaranteed to list anymore as ROS_ROOT may not be set
        if 'ros' in val:
            val.remove('ros')
        self.assertEquals(set(['foo', 'bar']), val)


    def test_list_stacks_by_path(self):
        from roslib.stacks import list_stacks_by_path

        # test with synthetic stacks
        test_dir = os.path.join(roslib.packages.get_pkg_dir('roslib'), 'test', 'stack_tests')
        self.assertEquals(set(['bar', 'foo']), set(list_stacks_by_path(test_dir)))

        test_dir = os.path.join(roslib.packages.get_pkg_dir('roslib'), 'test', 'stack_tests', 's1')
        self.assertEquals(set(['bar', 'foo']), set(list_stacks_by_path(test_dir)))

        test_dir = os.path.join(roslib.packages.get_pkg_dir('roslib'), 'test', 'stack_tests', 's1', 'bar')
        self.assertEquals(['bar'], list_stacks_by_path(test_dir))
        
        # test symlink following

        test_dir = os.path.join(roslib.packages.get_pkg_dir('roslib'), 'test', 'stack_tests2')
        self.assertEquals(set(['foo', 'bar']), set(list_stacks_by_path(test_dir)))
        
    def test_list_stacks_by_path_unary(self):
        from roslib.stacks import list_stacks_by_path
        # test with synthetic stacks
        test_dir = os.path.join(roslib.packages.get_pkg_dir('roslib'), 'test', 'stack_tests_unary')
        self.assertEquals(set(['bar', 'foo', 'baz']), set(list_stacks_by_path(test_dir)))

    def test_get_stack_dir_unary(self):
        # now manipulate the environment to test precedence
        # - save original RPP as we popen rosstack in other tests
        d = roslib.packages.get_pkg_dir('roslib')
        d = os.path.join(d, 'test', 'stack_tests_unary')
        s1_d = os.path.join(d, 's1')
        rpp = rospkg.get_ros_package_path()
        try:
            paths = [d]
            os.environ[rospkg.environment.ROS_PACKAGE_PATH] = os.pathsep.join(paths)
            self.assertEquals(os.path.join(s1_d, 'foo'), roslib.stacks.get_stack_dir('foo'))
            self.assertEquals(os.path.join(s1_d, 'bar'), roslib.stacks.get_stack_dir('bar'))
            self.assertEquals(os.path.join(s1_d, 'baz'), roslib.stacks.get_stack_dir('baz'))
        finally:
            #restore rpp
            if rpp is not None:
                os.environ[rospkg.environment.ROS_PACKAGE_PATH] = rpp
            else:
                del os.environ[rospkg.environment.ROS_PACKAGE_PATH] 
        
    def test_get_stack_dir(self):
        import roslib.packages
        from roslib.stacks import get_stack_dir, InvalidROSStackException, list_stacks
        try:
            get_stack_dir('non_existent')
            self.fail("should have raised")
        except roslib.stacks.InvalidROSStackException:
            pass

        # now manipulate the environment to test precedence
        # - save original RPP as we popen rosstack in other tests
        rpp = os.environ.get(rospkg.environment.ROS_PACKAGE_PATH, None)
        try:
            d = roslib.packages.get_pkg_dir('roslib')
            d = os.path.join(d, 'test', 'stack_tests')

            # - s1/s2/s3
            print("s1/s2/s3")
            paths = [os.path.join(d, p) for p in ['s1', 's2', 's3']]
            os.environ[rospkg.environment.ROS_PACKAGE_PATH] = os.pathsep.join(paths)
            # - run multiple times to test caching
            for i in range(2):
                stacks = roslib.stacks.list_stacks()
                self.assert_('foo' in stacks)
                self.assert_('bar' in stacks)

                foo_p = os.path.join(d, 's1', 'foo')
                bar_p = os.path.join(d, 's1', 'bar')
                self.assertEquals(foo_p, roslib.stacks.get_stack_dir('foo'))
                self.assertEquals(bar_p, roslib.stacks.get_stack_dir('bar'))

            # - s2/s3/s1
            print("s2/s3/s1")
            
            paths = [os.path.join(d, p) for p in ['s2', 's3', 's1']]
            os.environ[rospkg.environment.ROS_PACKAGE_PATH] = os.pathsep.join(paths)
            stacks = roslib.stacks.list_stacks()
            self.assert_('foo' in stacks)
            self.assert_('bar' in stacks)

            foo_p = os.path.join(d, 's2', 'foo')
            bar_p = os.path.join(d, 's1', 'bar')
            self.assertEquals(foo_p, roslib.stacks.get_stack_dir('foo'))
            self.assertEquals(bar_p, roslib.stacks.get_stack_dir('bar'))
        finally:
            #restore rpp
            if rpp is not None:
                os.environ[rospkg.environment.ROS_PACKAGE_PATH] = rpp
            else:
                del os.environ[rospkg.environment.ROS_PACKAGE_PATH] 
            
    def test_expand_to_packages_unary(self):
        # test unary
        test_dir = os.path.join(roslib.packages.get_pkg_dir('roslib'), 'test', 'stack_tests_unary')

        env = os.environ.copy()
        env[rospkg.environment.ROS_PACKAGE_PATH] = test_dir

        from roslib.stacks import expand_to_packages      
        self.assertEquals((['foo'], []), expand_to_packages(['foo'], env=env))
        self.assertEquals((['foo', 'bar'], []), expand_to_packages(['foo', 'bar'], env=env))

    def test_expand_to_packages(self):
        from roslib.stacks import expand_to_packages
        try:
            # it's possible to accidentally pass in a sequence type
            # like a string and get weird results, so check that we
            # don't
            self.assertEquals(([], []), expand_to_packages('ros'))
            self.fail("expand_to_packages should only take in a list of strings")
        except ValueError: pass
        
        self.assertEquals(([], []), expand_to_packages([]))
        self.assertEquals((['rosmake', 'roslib', 'roslib'], []), expand_to_packages(['rosmake', 'roslib', 'roslib']))
        self.assertEquals(([], ['bogus_one', 'bogus_two']), expand_to_packages(['bogus_one', 'bogus_two']))

        # this test case is no more valid in a package-only world
        # TODO: setup directory tree so that this can be more precisely calculated
        #valid, invalid = expand_to_packages(['ros', 'bogus_one'])
        #self.assertEquals(['bogus_one'], invalid)
        #check = ['rosbuild', 'rosunit', 'roslib']
        #print valid
        #for c in check:
        #    self.assert_(c in valid, "expected [%s] to be in ros expansion"%c)
            
    def test_get_stack_version(self):
        from roslib.stacks import get_stack_version
        
        test_dir = os.path.join(get_test_path(), 'stack_tests', 's1')
        env = os.environ.copy()
        env[rospkg.environment.ROS_PACKAGE_PATH] = test_dir

        # REP 109: stack.xml has precedence over CMakeLists.txt, version is whitespace stripped
        self.assertEquals('1.6.0-manifest', roslib.stacks.get_stack_version('foo', env=env))
        # REP 109: test fallback to CMakeLists.txt version
        self.assertEquals('1.5.0-cmake', roslib.stacks.get_stack_version('bar', env=env))

        if 0:
            test_dir = os.path.join(roslib.packages.get_pkg_dir('roslib'), 'test', 'stack_tests_unary')
            env = os.environ.copy()
            env[rospkg.environment.ROS_PACKAGE_PATH] = test_dir

def get_test_path():
    return os.path.abspath(os.path.dirname(__file__))

########NEW FILE########
__FILENAME__ = test_roslib_stack_manifest
# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os
import sys
import unittest

import roslib

def get_test_path():
    return os.path.abspath(os.path.dirname(__file__))

class RoslibStackManifestTest(unittest.TestCase):
  
  def _subtest_parse_stack_example1(self, m):
    from roslib.manifestlib import _Manifest
    self.assert_(isinstance(m, _Manifest))
    self.assertEquals('stack', m._type)
    self.assertEquals("a brief description", m.brief)
    self.assertEquals("Line 1\nLine 2", m.description.strip())
    self.assertEquals("The authors\ngo here", m.author.strip())    
    self.assertEquals("Public Domain\nwith other stuff", m.license.strip())
    self.assertEquals("http://ros.org/stack/", m.url)
    self.assertEquals("http://www.willowgarage.com/files/willowgarage/robot10.jpg", m.logo)
    dpkgs = [d.stack for d in m.depends]
    self.assertEquals(set(['stackname', 'common']), set(dpkgs))
    self.assertEquals([], m.rosdeps)
    self.assertEquals([], m.exports)    

  def _subtest_parse_stack_version(self, m):
    self.assertEquals("1.2.3", m.version)

  def test_parse_example1_file(self):
    from roslib.stack_manifest import parse_file, StackManifest
    
    p = os.path.join(get_test_path(), 'manifest_tests', 'stack_example1.xml')
    self._subtest_parse_stack_example1(parse_file(p))

    p = os.path.join(get_test_path(), 'manifest_tests', 'stack_version.xml')
    self._subtest_parse_stack_version(parse_file(p))

  def test_parse_example1_string(self):
    from roslib.manifestlib import parse, _Manifest
    self._subtest_parse_stack_example1(parse(_Manifest('stack'), STACK_EXAMPLE1))
    
  def test_StackManifest(self):
    from roslib.stack_manifest import StackManifest
    m = StackManifest()
    self.assertEquals('stack', m._type)    
    
  def test_StackManifest_str(self):
    # just make sure it doesn't crash
    from roslib.stack_manifest import parse
    str(parse(STACK_EXAMPLE1))
    
  def test_StackManifest_xml(self):
    from roslib.stack_manifest import parse, StackManifest
    m = parse(STACK_EXAMPLE1)
    self._subtest_parse_stack_example1(m)
    # verify roundtrip
    m2 = parse(m.xml())
    self._subtest_parse_stack_example1(m2)
    
  # bad file examples should be more like the roslaunch tests where there is just 1 thing wrong
STACK_EXAMPLE1 = """<stack>
  <description brief="a brief description">Line 1
Line 2
  </description>
  <author>The authors
go here</author>
  <license>Public Domain
with other stuff</license>
  <url>http://ros.org/stack/</url>
  <logo>http://www.willowgarage.com/files/willowgarage/robot10.jpg</logo>
  <depend stack="stackname" />
  <depend stack="common"/>
</stack>"""

STACK_INVALID1 = """<stack>
  <description brief="a brief description">Line 1</description>
  <author>The authors</author>
  <license>Public Domain</license>
  <rosdep name="python" />
</stack>"""

STACK_INVALID2 = """<stack>
  <description brief="a brief description">Line 1</description>
  <author>The authors</author>
  <license>Public Domain</license>
  <export>
    <cpp cflags="-I${prefix}/include" lflags="-L${prefix}/lib -lros"/>
    <cpp os="osx" cflags="-I${prefix}/include" lflags="-L${prefix}/lib -lrosthread -framework CoreServices"/>
  </export>
</stack>"""

########NEW FILE########
__FILENAME__ = test_scripts
#!/usr/bin/env python

import os
import subprocess
import unittest
import tempfile
import shutil

PKG_PATH = os.getcwd()
TEST_PATH = os.path.join(PKG_PATH, 'test')

def make_bash_pre_command(strings, currentword):
    return "bash -c '. %s; export COMP_WORDS=(%s); export COMP_CWORD=%s;"%(os.path.join(PKG_PATH, 'rosbash'), ' '.join(['"%s"'%w for w in strings]), currentword)

class TestRosBash(unittest.TestCase):

    def setUp(self):
        self.cmdbash = os.path.join(TEST_PATH, 'test_rosbash.bash')
        self.assertTrue(os.path.exists(self.cmdbash))
        
        self.cmdzsh = os.path.join(TEST_PATH, 'test_roszsh.zsh')
        self.assertTrue(os.path.exists(self.cmdzsh))
        
    def test_rosbash_completion(self):
        subprocess.check_call([self.cmdbash], cwd = TEST_PATH)
 
    def test_roszsh_completion(self):
        subprocess.check_call([self.cmdzsh], cwd = TEST_PATH)


class TestWithFiles(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.test_root_path = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.test_root_path)

    def test_make_precommand(self):
        self.assertEqual( "bash -c '. %s; export COMP_WORDS=(\"foo\" \"bar\"); export COMP_CWORD=1;"%os.path.join(PKG_PATH, 'rosbash'), make_bash_pre_command(['foo', 'bar'], 1))
        self.assertEqual( "bash -c '. %s; export COMP_WORDS=(\"foo\"); export COMP_CWORD=2;"%os.path.join(PKG_PATH, 'rosbash'), make_bash_pre_command(['foo'], 2))
        
    def test_roslaunch_completion(self):
        # regression test that roslaunch completion works even in the presence of launchfiles
        subprocess.check_call("touch foo.launch", shell=True, cwd=self.test_root_path)
        subprocess.check_call("touch bar.launch", shell=True, cwd=self.test_root_path)

        cmd = make_bash_pre_command(['rosbash', 'rosbash'], 2)
        cmd += "_roscomplete_launch rosbash rosbash; echo $COMPREPLY'"
        p = subprocess.Popen(cmd,
                             shell=True,
                             stdout=subprocess.PIPE,
                             cwd=self.test_root_path)
        output = p.communicate()
        self.assertEqual(0, p.returncode, (p.returncode, output, cmd))
        
        self.assertTrue('example.launch' in output[0], (p.returncode, output[0], cmd))

########NEW FILE########
__FILENAME__ = rosboost_cfg
#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2010, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function

import sys
import os
import string
from glob import glob
import subprocess
import platform
from optparse import OptionParser

lib_suffix = "so"
if (sys.platform == "darwin"):
  lib_suffix = "dylib"

link_static = 'ROS_BOOST_LINK' in os.environ and os.environ['ROS_BOOST_LINK'] == "static"
if (link_static):
  lib_suffix = "a"

no_L_or_I = 'ROS_BOOST_NO_L_OR_I' in os.environ

boost_version = None
if ('ROS_BOOST_VERSION' in os.environ and len(os.environ['ROS_BOOST_VERSION']) > 0):
    ver = os.environ['ROS_BOOST_VERSION']
    ver = ver.split('.')
    
    boost_version = [int(v) for v in ver]
    if (len(boost_version) == 2):
        boost_version.append(0)

def print_usage_and_exit():
  print("Usage: rosboost-cfg --lflags [thread,regex,graph,...]")
  print("       rosboost-cfg --cflags")
  print("       rosboost-cfg --libs [thread,regex,graph,...]")
  print("       rosboost-cfg --include_dirs")
  print("       rosboost-cfg --lib_dirs")
  print("       rosboost-cfg --root")
  sys.exit(1)

class BoostError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Version(object):
    def __init__(self, major, minor, patch, root, include_dir, lib_dir, is_default_search_location):
        self.major = major
        self.minor = minor
        self.patch = patch
        self.root = root
        self.include_dir = include_dir
        self.lib_dir = lib_dir
        self.is_default_search_location = is_default_search_location
        self.is_system_install = os.path.split(self.include_dir)[0] == self.root
        
    def __cmp__(self, other):
        if (self.major != other.major):
            if self.major < other.major: 
                return -1 
            else: 
                return 1
        if (self.minor != other.minor):
            if self.minor < other.minor: 
                return -1 
            else: 
                return 1
        if (self.patch != other.patch):
            if self.patch < other.patch: 
                return -1 
            else: 
                return 1
        
        return 0
    def __repr__(self):
        return repr((self.major, self.minor, self.patch, self.root, self.include_dir, self.is_default_search_location, self.is_system_install))

def find_lib_dir(root_dir):
  # prefer lib64 unless explicitly specified in the environment
  if ('ROS_BOOST_LIB_DIR_NAME' in os.environ):
    possible_dirs = [os.path.join(root_dir, os.environ['ROS_BOOST_LIB_DIR_NAME'])]
  else:
    possible_dirs = [os.path.join(root_dir, "lib64"), os.path.join(root_dir, "lib")]

  for p in possible_dirs:
    glob_files = glob("%s*"%(os.path.join(p, "libboost*")))
    if (len(glob_files) > 0):
      return p

  return None

def extract_versions(dir, is_default_search_location):
    version_paths = [os.path.join(dir, "version.hpp"),
                    os.path.join(dir, "boost", "version.hpp")]
    glob_dirs = glob("%s*"%(os.path.join(dir, "boost-")))
    [version_paths.append(os.path.join(gdir, "boost", "version.hpp")) for gdir in glob_dirs]
    
    versions = []
    
    for p in version_paths:
        ver_string = "" 
        if (os.path.isfile(p)):  
            fh = open(p,"r") 
            lines = fh.readlines()
            fh.close() 
            for line in lines: 
                if line.find("#define BOOST_VERSION ") > -1: 
                    def_string = line.split() 
                    ver_string = def_string[2]
                    ver_int = int(ver_string)
                    patch = ver_int % 100
                    minor = ver_int / 100 % 1000
                    major = ver_int / 100000
                    include_dir = os.path.split(os.path.split(p)[0])[0]
                    root_dir = os.path.split(dir)[0]
                    lib_dir = find_lib_dir(root_dir)
                    versions.append(Version(major, minor, patch, root_dir, include_dir, lib_dir, is_default_search_location))
    
    return versions
  
def find_versions(search_paths):
    vers = []
    
    for path, system in search_paths:
        path = os.path.join(path, "include")
        pvers = extract_versions(path, system)
        [vers.append(ver) for ver in pvers]
        
    if (len(vers) == 0):
        return None
    
    if (boost_version is not None):
        for v in vers:
            if (v.major == boost_version[0] and v.minor == boost_version[1] and v.patch == boost_version[2]):
                return [v]
        
        raise BoostError('Could not find boost version %s required by ROS_BOOST_VERSION environment variable'%(boost_version))
    
    vers.sort()
    return vers
  
def find_boost(search_paths):
    result = find_versions(search_paths)
    if result is None:
      return None
    if len(result) > 1:
      sys.stderr.write("WARN, found multiple boost versions '%s', using latest"%result)
    return result[-1]

def search_paths(sysroot):
    _search_paths = [(sysroot+'/usr', True), 
                 (sysroot+'/usr/local', True),
                 (None if 'INCLUDE_DIRS' not in os.environ else os.environ['INCLUDE_DIRS'], True), 
                 (None if 'CPATH' not in os.environ else os.environ['CPATH'], True),
                 (None if 'C_INCLUDE_PATH' not in os.environ else os.environ['C_INCLUDE_PATH'], True),
                 (None if 'CPLUS_INCLUDE_PATH' not in os.environ else os.environ['CPLUS_INCLUDE_PATH'], True),
                 (None if 'ROS_BOOST_ROOT' not in os.environ else os.environ['ROS_BOOST_ROOT'], False)]

    search_paths = []
    for (str, system) in _search_paths:
        if (str is not None):
            dirs = str.split(':')
            for dir in dirs:
                if (len(dir) > 0):
                    if (dir.endswith('/include')):
                        dir = dir[:-len('/include')]
                    search_paths.append((dir, system))
    return search_paths

def lib_dir(ver):
    return ver.lib_dir

def find_lib(ver, name, full_lib = link_static):
    global lib_suffix
    global link_static
    
    dynamic_search_paths = []
    static_search_paths = []
    
    if (ver.is_system_install):
        dynamic_search_paths = ["libboost_%s-mt.%s"%(name, lib_suffix),
                                "libboost_%s.%s"%(name, lib_suffix)]
        static_search_paths = ["libboost_%s-mt.a"%(name),
                               "libboost_%s.a"%(name)]
    else:
        dynamic_search_paths = ["libboost_%s*%s_%s*.%s"%(name, ver.major, ver.minor, lib_suffix),
                                "libboost_%s-mt*.%s"%(name, lib_suffix),
                                "libboost_%s*.%s"%(name, lib_suffix)]
        static_search_paths = ["libboost_%s*%s_%s*.a"%(name, ver.major, ver.minor),
                               "libboost_%s-mt*.a"%(name),
                               "libboost_%s*.a"%(name)]
        
    # Boost.Python needs some special handling on some systems (Karmic), since it may have per-python-version libs
    if (name == "python"):
        python_ver = platform.python_version().split('.')
        dynamic_search_paths = ["libboost_%s-mt-py%s%s.%s"%(name, python_ver[0], python_ver[1], lib_suffix),
                                "libboost_%s-py%s%s.%s"%(name, python_ver[0], python_ver[1], lib_suffix)] + dynamic_search_paths
        static_search_paths = ["libboost_%s-mt-py%s%s.a"%(name, python_ver[0], python_ver[1]),
                               "libboost_%s-py%s%s.a"%(name, python_ver[0], python_ver[1])] + static_search_paths
    
    search_paths = static_search_paths if link_static else dynamic_search_paths
    
    dir = lib_dir(ver)

    if dir is None:
      raise BoostError('Could not locate library [%s], version %s'%(name, ver))
    
    for p in search_paths:
        globstr = os.path.join(dir, p) 
        libs = glob(globstr)
        if (len(libs) > 0):
            if (full_lib):
                return libs[0]
            else:
                return os.path.basename(libs[0])
            
    raise BoostError('Could not locate library [%s], version %s in lib directory [%s]'%(name, ver, dir))
  
def include_dirs(ver, prefix = ''):
    if ver.is_system_install or no_L_or_I:
        return ""
    
    return " %s%s"%(prefix, ver.include_dir)
  
def cflags(ver):
    return include_dirs(ver, '-I')

def lib_dir_flags(ver):
    if not ver.is_default_search_location:
        dir = lib_dir(ver)
        return ' -L%s -Wl,-rpath,%s'%(dir, dir)
    
    return '' 

def lib_flags(ver, name):
    lib = find_lib(ver, name)
    if (link_static):
        return ' %s'%(lib)
    else:
        # Cut off "lib" and extension (.so/.a/.dylib/etc.)
        return ' -l%s'%(os.path.splitext(lib)[0][len('lib'):])

def lflags(ver, libs):
    s= lib_dir_flags(ver) + " "
    for lib in libs:
        s += lib_flags(ver, lib) + " "
    return s

def libs(ver, libs):
    s = ""
    for lib in libs:
        s += find_lib(ver, lib, True) + " "
    return s

def lib_dirs(ver):
    if (ver.is_default_search_location or no_L_or_I):
        return ""
    
    return lib_dir(ver)

OPTIONS = ['libs', 'include_dirs', 'lib_dirs', 'cflags', 'lflags', 'root', 'print_versions', 'version']

def check_one_option(options, key):
    for k in dir(options):
        if (k in OPTIONS):
            v = getattr(options, k)
            if (k != key and v):
                raise BoostError("Only one option (excepting sysroot) is allowed at a time")

def main():
    if (len(sys.argv) < 2):
        print_usage_and_exit()
    
    parser = OptionParser()
    parser.add_option("-l", "--libs", dest="libs", type="string", help="")
    parser.add_option("-i", "--include_dirs", dest="include_dirs", action="store_true", default=False, help="")
    parser.add_option("-d", "--lib_dirs", dest="lib_dirs", action="store_true", help="")
    parser.add_option("-c", "--cflags", dest="cflags", action="store_true", default=False, help="")
    parser.add_option("-f", "--lflags", dest="lflags", type="string", help="")
    parser.add_option("-r", "--root", dest="root", action="store_true", default=False, help="")
    parser.add_option("-p", "--print_versions", dest="print_versions", action="store_true", default=False, help="")
    parser.add_option("-v", "--version", dest="version", action="store_true", default=False, help="")
    parser.add_option("-s", "--sysroot", dest="sysroot", type="string", default='', help="Location of the system root (usually toolchain root).")
    
    (options, args) = parser.parse_args()
    
    if (options.print_versions):
        check_one_option(options, 'print_versions')
        for ver in find_versions(search_paths(options.sysroot)):
            print('%s.%s.%s root=%s include_dir=%s'%(ver.major, ver.minor, ver.patch, ver.root, ver.include_dir))
        return
       
    ver = find_boost(search_paths(options.sysroot))
    
    if ver is None:
        raise BoostError("Cannot find boost in any of %s"%search_paths(options.sysroot))
        sys.exit(0)
    
    if options.version:
        check_one_option(options, 'version')
        print('%s.%s.%s root=%s include_dir=%s'%(ver.major, ver.minor, ver.patch, ver.root, ver.include_dir))
        return
    
    if ver.major < 1 or (ver.major == 1 and ver.minor < 37):
        raise BoostError('Boost version %s.%s.%s does not meet the minimum requirements of boost 1.37.0'%(ver.major, ver.minor, ver.patch))
    
    

    output = ""
    if (options.root):
        check_one_option(options, 'root')
        output = ver.root
    elif (options.libs):
        check_one_option(options, 'libs')
        output = libs(ver, options.libs.split(','))
    elif (options.include_dirs):
        check_one_option(options, 'include_dirs')
        output = include_dirs(ver)
    elif (options.lib_dirs):
        check_one_option(options, 'lib_dirs')
        output = lib_dirs(ver)
    elif (options.cflags):
        check_one_option(options, 'cflags')
        output = cflags(ver)
    elif (options.lflags):
        check_one_option(options, 'lflags')
        output = lflags(ver, options.lflags.split(','))
    else:
        print_usage_and_exit()
    
    print(output.strip())

if __name__ == "__main__":
    main()
            

########NEW FILE########
__FILENAME__ = test_rosclean
# Software License Agreement (BSD License)
#
# Copyright (c) 2012, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os
import sys

def test__get_check_dirs():
    # just a tripwire, no way to assert the actual values w/o identical reimplementation
    from rosclean import _get_check_dirs
    vals = _get_check_dirs()
    for path, desc in vals:
        assert os.path.isdir(path)
    
def test_get_human_readable_disk_usage():
    from rosclean import get_human_readable_disk_usage
    val = get_human_readable_disk_usage(get_test_path())
    assert val
    
def get_test_path():
    return os.path.abspath(os.path.join(os.path.dirname(__file__)))

def test_get_disk_usage():
    from rosclean import get_disk_usage
    val = get_disk_usage(get_test_path())
    assert val > 0

def test_cmd():
    from rosclean import rosclean_main
    try:
        rosclean_main(['rosclean', 'fake'])
        assert False, "should have raised sys exit"
    except SystemExit:
        pass

    # should run cleanly
    try:
        rosclean_main(['rosclean', 'check'])
    except SystemExit:
        assert False, "failed with sys exit"

########NEW FILE########
__FILENAME__ = core
#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function

import os
import sys

import rospkg
import pkg_resources

def print_warning(msg):
    """print warning to screen (bold red)"""
    print('\033[31m%s\033[0m'%msg, file=sys.stderr)
    
def author_name():
    """
    Utility to compute logged in user name
    
    :returns: name of current user, ``str``
    """
    import getpass
    name = getpass.getuser()
    try:
        import pwd
        login = name
        name = pwd.getpwnam(login)[4]
        name = ''.join(name.split(',')) # strip commas
        # in case pwnam is not set
        if not name:
            name = login
    except:
        #pwd failed
        pass
    try:
        name = name.decode('utf-8')
    except AttributeError:
        pass
    return name

def read_template(tmplf):
    """
    Read resource template from egg installation, or fallback on rospkg otherwise.

    :returns: text of template file
    """
    if pkg_resources.resource_exists('roscreate', tmplf):
        f = pkg_resources.resource_stream('roscreate', tmplf)
        t = f.read()
    else:
        # fallback on rospkg
        r = rospkg.RosPack()
        with open(os.path.join(r.get_path('roscreate'), 'templates', tmplf)) as f:
            t = f.read()
    try:
        t = t.decode('utf-8')
    except AttributeError:
        pass
    return t

    

########NEW FILE########
__FILENAME__ = roscreatepkg
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$

from __future__ import print_function

NAME='roscreate-pkg'

import os
import sys

import roslib.names

from roscreate.core import read_template, author_name
from rospkg import on_ros_path, RosPack, ResourceNotFound

def get_templates():
    templates = {}
    templates['CMakeLists.txt'] = read_template('CMakeLists.tmpl')
    templates['manifest.xml'] = read_template('manifest.tmpl')
    templates['mainpage.dox'] = read_template('mainpage.tmpl')
    templates['Makefile'] = read_template('Makefile.tmpl')
    return templates

def instantiate_template(template, package, brief, description, author, depends):
    return template%locals()

def create_package(package, author, depends, uses_roscpp=False, uses_rospy=False):
    p = os.path.abspath(package)
    if os.path.exists(p):
        print("%s already exists, aborting"%p, file=sys.stderr)
        sys.exit(1)

    os.makedirs(p)
    print("Created package directory", p)
        
    if uses_roscpp:
        # create package/include/package and package/src for roscpp code
        cpp_path = os.path.join(p, 'include', package)
        try:        
            os.makedirs(cpp_path)
            print("Created include directory", cpp_path)
            cpp_path = os.path.join(p, 'src')
            os.makedirs(cpp_path)
            print("Created cpp source directory", cpp_path)
        except:
            # file exists
            pass
    if uses_rospy:
        # create package/src/ for python files
        py_path = os.path.join(p, 'src')
        try:
            os.makedirs(py_path)
            print("Created python source directory", py_path)
        except:
            # file exists
            pass
        
    templates = get_templates()
    for filename, template in templates.items():
        contents = instantiate_template(template, package, package, package, author, depends)
        p = os.path.abspath(os.path.join(package, filename))
        with open(p, 'w') as f:
            f.write(contents.encode('utf-8'))
            print("Created package file", p)
    print("\nPlease edit %s/manifest.xml and mainpage.dox to finish creating your package"%package)

def roscreatepkg_main():
    from optparse import OptionParser    
    parser = OptionParser(usage="usage: %prog <package-name> [dependencies...]", prog=NAME)
    options, args = parser.parse_args()
    if not args:
        parser.error("you must specify a package name and optionally also list package dependencies")
    package = args[0]

    if not roslib.names.is_legal_resource_base_name(package):
        parser.error("illegal package name: %s\nNames must start with a letter and contain only alphanumeric characters\nand underscores."%package)

    # validate dependencies and turn into XML
    depends = args[1:]
    uses_roscpp = 'roscpp' in depends
    uses_rospy = 'rospy' in depends

    rospack = RosPack()
    for d in depends:
        try:
            rospack.get_path(d)
        except ResourceNotFound:
            print("ERROR: dependency [%s] cannot be found"%d, file=sys.stderr)
            sys.exit(1)

    depends = u''.join([u'  <depend package="%s"/>\n'%d for d in depends])

    if not on_ros_path(os.getcwd()):
        print('!'*80+"\nWARNING: current working directory is not on ROS_PACKAGE_PATH!\nPlease update your ROS_PACKAGE_PATH environment variable.\n"+'!'*80, file=sys.stderr)
    if type(package) == str:
        package = package.decode('utf-8')
    create_package(package, author_name(), depends, uses_roscpp=uses_roscpp, uses_rospy=uses_rospy)

########NEW FILE########
__FILENAME__ = test_roscreate_core
# Software License Agreement (BSD License)
#
# Copyright (c) 2012, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

def test_author_name():
    from roscreate.core import author_name
    val = author_name()
    assert val, val
    
def test_read_template():
    from roscreate.core import read_template
    s = set()
    # this unit test will break if any of the templates get removed/renamed
    tests = ['Makefile.tmpl', 'stack.tmpl', 'mainpage.tmpl', 'CMakeLists.stack.tmpl']
    for f in tests:
        text = read_template(f)
        s.add(text)
    # simple assert to make sure we didn't read the same thing from each template
    assert len(s) == len(tests)

    # hardcode test against a known template
    text = read_template('Makefile.tmpl')        
    assert text == 'include $(shell rospack find mk)/cmake.mk'

########NEW FILE########
__FILENAME__ = engine
#! /usr/bin/env python

# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Willow Garage, Inc. nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# Author Tully Foote/tfoote@willowgarage.com

from __future__ import print_function

import os
import re
import signal
import sys
import subprocess
import time
import threading
import traceback

import rospkg
from rospkg import ResourceNotFound

try: 
    from exceptions import SystemExit #Python 2.x
except ImportError: 
    pass #Python 3.x (in Python 3, 'exceptions' is always imported) 

from operator import itemgetter

from . import parallel_build
from . import package_stats

from optparse import OptionParser
from .gcc_output_parse import Warnings

# #3883
_popen_lock = threading.Lock()

def make_command():
    """
    @return: name of 'make' command
    @rtype: str
    """
    return os.environ.get("MAKE", "make")

# this is a copy of the roslogging utility. it's been moved here as it is a common
# routine for programs using accessing ROS directories
def makedirs_with_parent_perms(p):
    """
    Create the directory using the permissions of the nearest
    (existing) parent directory. This is useful for logging, where a
    root process sometimes has to log in the user's space.
    @param p: directory to create
    @type  p: str
    """    
    p = os.path.abspath(p)
    parent = os.path.dirname(p)
    # recurse upwards, checking to make sure we haven't reached the
    # top
    if not os.path.exists(p) and p and parent != p:
        makedirs_with_parent_perms(parent)
        s = os.stat(parent)
        os.mkdir(p)

        # if perms of new dir don't match, set anew
        s2 = os.stat(p)
        if s.st_uid != s2.st_uid or s.st_gid != s2.st_gid:
            os.chown(p, s.st_uid, s.st_gid)
        if s.st_mode != s2.st_mode:
            os.chmod(p, s.st_mode)    

class Printer:
   # storage for the instance reference
    __instance = None

    def __init__(self):
        """ Create singleton instance """
        # Check whether we already have an instance
        if Printer.__instance is None:
            # Create and remember instance
            Printer.__instance = Printer.__impl()

        # Store instance reference as the only member in the handle
        self.__dict__['_Printer__instance'] = Printer.__instance

    def __getattr__(self, attr):
        """ Delegate access to implementation """
        return getattr(self.__instance, attr)

    def __setattr__(self, attr, value):
        """ Delegate access to implementation """
        return setattr(self.__instance, attr, value)
    
    def __enter__(self):
        """Pass through for the __enter__ function for the __instance"""
        return self.__instance.__enter__()
    
    def __exit__(self, mtype, value, tb):
        """Pass through for the __exit__ function for the __instance"""
        return self.__instance.__exit__(mtype, value, tb)
    
    class __impl(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.build_queue = None
            self.condition = threading.Condition()
            self.running = True
            self.done = False
            self.status = ""
            self.verbose = False
            self.full_verbose = False
            self.duration = 1./10.
            self._last_status = None

            # Rosmake specific data
            self.cache_argument = None
            self.cache_right = ''
            self.pkg_start_times = {}

        def shutdown(self):
            self.running = False
            cycles = 10
            for i in range(0,cycles):# sleep for at least 2 cycles of the status testing 'cycles' times
                if self.done:
                    #print "SUCCESSFULLY SHUTDOWN"
                    return True
                #print "Sleeping for %f FOR SHUTDOWN.  %d threads running"%(max(self.duration/cycles*2, 0.01), threading.activeCount())
                time.sleep(max(self.duration, 0.1)/cycles*2) 
            raise Exception("Failed to shutdown status thread in %.2f seconds"%(self.duration * 2))

        def __enter__(self):
            self.start()
        def __exit__(self, mtype, value, tb):
            self.shutdown()
            if value:
                if not mtype == type(SystemExit()):
                    traceback.print_exception(mtype, value, tb)
                else:
                    sys.exit(value)

        def run(self):
            while self.running:
                #shutdown if duration set to zero
                if self.duration <= 0:
                    self.running = False
                    break
                self.set_status_from_cache()
                if len(self.pkg_start_times.keys()) > 0:
                    n = self.terminal_width() - len(self.status)
                    status = self.status
                    if n > 0:
                        status = " "*n + self.status
                    if status != self._last_status:
                        self._print_status("%s"%status)
                        self._last_status = status
                time.sleep(self.duration) 
            self.done = True
            #print "STATUS THREAD FINISHED"

        def rosmake_cache_info(self, argument, start_times, right):
            self.cache_argument = argument
            self.pkg_start_times = start_times
            self.cache_right = right

        def rosmake_pkg_times_to_string(self, start_times):
            threads = []
            for p, t in sorted(start_times.items(), key=itemgetter(1)): #py3k
                threads.append("[ %s: %.1f sec ]"%(p, time.time() - t))

            return " ".join(threads)

        def set_status_from_cache(self):
            if self.cache_argument:
                self.set_status("[ make %s ] "%self.cache_argument + self.rosmake_pkg_times_to_string(self.pkg_start_times), self.cache_right)
            else:
                self.set_status("[ make ] " + self.rosmake_pkg_times_to_string(self.pkg_start_times), self.cache_right)

        def set_status(self, left, right = ''):
            header = "[ rosmake ] "
            h = len(header)
            l = len(left)
            r = len(right)
            w = self.terminal_width()
            if l + r < w - h:
                padding = w - h - l - r
                self.status = header + left + " "*padding + right
            else:
                self.status = header + left[:(w - h - r - 4)] + "... " + right

        def print_all(self, s, thread_name=None):
            if thread_name is None:
                str = "[ rosmake ] %s"%s
                

            else:
                str = "[rosmake-%s] %s"%(thread_name, s)
            sys.stdout.write(self.pad_str_to_width(str, self.terminal_width())+"\n")
            sys.stdout.flush()

        def print_verbose(self, s, thread_name=None):
            if self.verbose or self.full_verbose:
                self.print_all(s, thread_name=thread_name)

        def print_full_verbose(self, s):
            if self.full_verbose:
                print("[ rosmake ] %s"%(s))

        def print_tail(self, s, tail_lines=40):
            lines = s.splitlines()
            if self.full_verbose:
                tail_lines = len(lines)

            num_lines = min(len(lines), tail_lines)
            if num_lines == tail_lines:
                print("[ rosmake ] Last %d lines"%(num_lines))
            else:
                print("[ rosmake ] All %d lines"%(num_lines))
            print("{" + "-"*79)
            for l in range(-num_lines, -1):
                print("  %s"%(lines[l]))
            print("-"*79 + "}")

        def _print_status(self, s):
            sys.stdout.write("%s\r"%(s))
            sys.stdout.flush()

        @staticmethod
        def terminal_width():
            """Estimate the width of the terminal"""
            width = 0
            try:
                import struct, fcntl, termios
                s = struct.pack('HHHH', 0, 0, 0, 0)
                x = fcntl.ioctl(1, termios.TIOCGWINSZ, s)
                width = struct.unpack('HHHH', x)[1]
            except IOError:
                pass
            if width <= 0:
                try:
                    width = int(os.environ['COLUMNS'])
                except:
                    pass
            if width <= 0:
                width = 80

            return width

        @staticmethod
        def pad_str_to_width(str, width):
            """ Pad the string to be terminal width"""
            length = len(str)
            excess = 0
            if length < width:
                excess = width - length
            return str + " "* excess



class RosMakeAll:
    def __init__(self):
        self._result_lock = threading.Lock()

        self.rospack = rospkg.RosPack()
        self.rosstack = rospkg.RosStack()

        self.printer = Printer()
        self.result = {}
        self.paths = {}
        self.dependency_tracker = parallel_build.DependencyTracker(rospack=self.rospack)
        self.flag_tracker = package_stats.PackageFlagTracker(self.dependency_tracker)
        self.output = {}
        self.profile = {}
        self.ros_parallel_jobs = 0
        self.build_list = []
        self.start_time = time.time()
        self.log_dir = ""
        self.logging_enabled = True

    def num_packages_built(self):
        """
        @return: number of packages that were built
        @rtype: int
        """
        return len(list(self.result[argument].keys())) #py3k

    def update_status(self, argument, start_times, right):
        self.printer.rosmake_cache_info(argument, start_times, right)

    def build_or_recurse(self,p):
        if p in self.build_list:
            return
        for d in self.dependency_tracker.get_deps_1(p):
            self.build_or_recurse(d)
        try: # append it ot the list only if present
          self.rospack.get_path(p)
          self.build_list.append(p)
        except rospkg.ResourceNotFound as ex:
          if not self.robust_build:
            self.printer.print_all("Exiting due to missing package: %s"%ex)
            sys.exit(-1)
          else:
            self.printer.print_all("!"*20 + " Package %s does not exist. %s"%(p, ex) + "!"*20)


    def parallel_build_pkgs(self, build_queue, argument = None, threads = 1):
        self.profile[argument] = {}
        self.output[argument] = {}
        with self._result_lock:
            if argument not in self.result.keys():
                self.result[argument] = {}

        cts = []
        for i in range(0, threads):
          ct = parallel_build.CompileThread(str(i), build_queue, self, argument)
          #print "TTTH starting thread ", ct
          ct.start()
          cts.append(ct)
        for ct in cts:
          try:
            #print "TTTT Joining", ct
            ct.join()
            #print "TTTH naturally ended thread", ct
          except KeyboardInterrupt:
            self.printer.print_all( "TTTH Caught KeyboardInterrupt. Stopping build.")
            build_queue.stop()
            ct.join()
          except: #catch all
              self.printer.print_all("TTTH OTHER exception thrown!!!!!!!!!!!!!!!!!!!!!")
              ct.join()
        #print "All threads joined"
        all_pkgs_passed = True
        with self._result_lock:
            for v in self.result[argument].values():
                all_pkgs_passed = v and all_pkgs_passed

        build_passed = build_queue.succeeded() and all_pkgs_passed
        return build_passed

    # This function taken from
    # http://www.chiark.greenend.org.uk/ucgi/~cjwatson/blosxom/2009-07-02-python-sigpipe.html
    def _subprocess_setup(self):
        # Python installs a SIGPIPE handler by default. This is usually not
        # what non-Python subprocesses expect.
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    def _build_package(self, package, argument=None):
        """
        Lower-level routine for building a package. Handles execution of actual build command.
        @param package: package name
        @type  package: str
        """
        local_env = os.environ.copy()
        if self.ros_parallel_jobs > 0:
            local_env['ROS_PARALLEL_JOBS'] = "-j%d -l%d" % (self.ros_parallel_jobs, self.ros_parallel_jobs)
        elif "ROS_PARALLEL_JOBS" not in os.environ: #if no environment setup and no args fall back to # cpus
            # num_cpus check can (on OS X) trigger a Popen(), which has
            #the multithreading bug we wish to avoid on Py2.7.
            with _popen_lock:
                num_cpus = parallel_build.num_cpus()
                local_env['ROS_PARALLEL_JOBS'] = "-j%d -l%d" % (num_cpus, num_cpus)
        local_env['SVN_CMDLINE'] = "svn --non-interactive"
        cmd = ["bash", "-c", "cd %s && %s "%(self.rospack.get_path(package), make_command()) ] #UNIXONLY
        if argument:
            cmd[-1] += argument
        self.printer.print_full_verbose (cmd)
        # #3883: make sure only one Popen command occurs at a time due to
        # http://bugs.python.org/issue13817
        with _popen_lock:
            command_line = subprocess.Popen(cmd, stdout=subprocess.PIPE,  stderr=subprocess.STDOUT, env=local_env, preexec_fn=self._subprocess_setup)
        (pstd_out, pstd_err) = command_line.communicate() # pstd_err should be None due to pipe above
        return (command_line.returncode, pstd_out.decode())

    def build(self, p, argument = None, robust_build=False):
        """
        Build package
        @param p: package name
        @type  p: str
        """
        return_string = ""
        try:
            # warn if ROS_BUILD_BLACKLIST encountered if applicable
            # do not build packages for which the build has failed
            if argument == "test":  # Tests are not build dependent
                failed_packages = []
            else:
                with self._result_lock:
                    failed_packages = [j for j in self.result[argument] if not self.result[argument][j] == True]

            (buildable, error, why) = self.flag_tracker.can_build(p, self.skip_blacklist, failed_packages)
            if buildable or self.robust_build:
                start_time = time.time()
                (returncode, pstd_out) = self._build_package(p, argument)
                self.profile[argument][p] = time.time() - start_time
                self.output[argument][p] = pstd_out
                if argument:
                    log_type = "build_%s"%argument
                else:
                    log_type = "build"
                if not returncode:
                    self.printer.print_full_verbose( pstd_out)
                    with self._result_lock:
                        self.result[argument][p] = True
                    warnings = Warnings( pstd_out )
                    num_warnings = len( warnings.warning_lines )
                    if num_warnings > 0:
                        return_string =  "[PASS] [ %.2f seconds ] [ %d warnings "%(self.profile[argument][p], num_warnings)
                        warning_dict = warnings.analyze();
                        for warntype,warnlines in warning_dict.items():
                            if len( warnlines ) > 0:
                                return_string = return_string + '[ {0:d} {1} ] '.format(len(warnlines),warntype)
                        return_string = return_string + ' ]'
                    else:
                        return_string =  ("[PASS] [ %.2f seconds ]"%( self.profile[argument][p]))
                    self.output_to_file(p, log_type, pstd_out, num_warnings > 0)
                else:
                    success = False
                    no_target = len(re.findall("No rule to make target", pstd_out)) > 0
                    interrupt = len(re.findall("Interrupt", pstd_out)) > 0
                    if no_target:
                        return_string = ( "[SKIP] No rule to make target %s"%( argument))
                        success = True
                    elif interrupt:
                        return_string = ("[Interrupted]" )
                    else:
                        return_string = ( "[FAIL] [ %.2f seconds ]"%( self.profile[argument][p]))
                    with self._result_lock:
                        self.result[argument][p] = True if no_target else False

                    if success == False: #don't print tail if [SKIP] target
                        self.printer.print_tail( pstd_out)
                    self.output_to_file(p, log_type, pstd_out, always_print= not (no_target or interrupt))

                    return (success, return_string)
            else:
                with self._result_lock:
                    self.result[argument][p] = error

                return_string += why
                return(error, return_string)
            return (True, return_string) # this means that we didn't error in any case above
        except rospkg.ResourceNotFound as ex:
            with self._result_lock:
                self.result[argument][p] = False
            self.printer.print_verbose ("[SKIP] Package %s not found\n" % p)
            self.output[argument][p] = "Package not found %s"%ex
            return (False, return_string)
            

    def output_to_file(self, package, log_type, stdout, always_print= False):
        if not self.logging_enabled:
            return
        package_log_dir = os.path.join(self.log_dir, package)

        std_out_filename = os.path.join(package_log_dir, log_type + "_output.log")
        if not os.path.exists (package_log_dir):
            makedirs_with_parent_perms(package_log_dir)
        with open(std_out_filename, 'w') as stdout_file:
            stdout_file.write(stdout)
            print_string = "Output from build of package %s written to:\n[ rosmake ]    %s"%(package, std_out_filename)
            if always_print:
                self.printer.print_all(print_string)
            else:
                self.printer.print_full_verbose(print_string)

    def generate_summary_output(self, log_dir):
        if not self.logging_enabled:
            return

        self.printer.print_all("Results:")
        if 'clean' in self.result.keys():
            self.printer.print_all("Cleaned %d packages."%len(self.result['clean']))
        if None in self.result.keys():
            build_failure_count = len([p for p in self.result[None].keys() if self.result[None][p] == False])
            self.printer.print_all("Built %d packages with %d failures."%(len(self.result[None]), build_failure_count))
        if 'test' in self.result.keys():
            test_failure_count = len([p for p in self.result['test'].keys() if self.result['test'][p] == False])
            self.printer.print_all("Tested %d packages with %d failures."%(len(self.result['test']), test_failure_count))
        self.printer.print_all("Summary output to directory")
        self.printer.print_all("%s"%self.log_dir)
        if self.rejected_packages:
            self.printer.print_all("WARNING: Skipped command line arguments: %s because they could not be resolved to a stack name or a package name. "%self.rejected_packages)

                           

        if None in self.result.keys():
            if len(self.result[None].keys()) > 0:
                buildfail_filename = os.path.join(log_dir, "buildfailures.txt")
                with open(buildfail_filename, 'w') as bf:
                    bf.write("Build failures:\n")
                    for key in self.build_list:
                        if key in self.result[None].keys() and self.result[None][key] == False:
                            bf.write("%s\n"%key)
                if  None in self.output.keys():
                    buildfail_context_filename = os.path.join(log_dir, "buildfailures-with-context.txt")
                    with open(buildfail_context_filename, 'w') as bfwc:
                        bfwc.write("Build failures with context:\n")
                        for key in self.build_list:
                            if key in self.result[None].keys() and self.result[None][key] == False:
                                bfwc.write("---------------------\n")
                                bfwc.write("%s\n"%key)
                                if key in self.output[None]:
                                    bfwc.write(self.output[None][key])

        if "test" in self.result.keys():
            if len(self.result["test"].keys()) > 0:
                testfail_filename = os.path.join(log_dir, "testfailures.txt")
                with open(testfail_filename, 'w') as btwc:
                    btwc.write("Test failures:\n")
                    for key in self.build_list:
                        if key in self.result["test"].keys() and self.result["test"][key] == False:
                            btwc.write("%s\n"%key)

                if "test" in self.output.keys():
                    testfail_filename = os.path.join(log_dir, "testfailures-with-context.txt")
                    with open(testfail_filename, 'w') as btwc:
                        btwc.write("Test failures with context:\n")
                        for key in self.build_list:
                            if key in self.result["test"].keys() and self.result["test"][key] == False:
                                btwc.write("%s\n"%key)
                                if key in self.output["test"]:
                                    btwc.write(self.output["test"][key])

        profile_filename = os.path.join(log_dir, "profile.txt")
        with open(profile_filename, 'w') as pf:
            pf.write(self.get_profile_string())
                            
                            

    def get_profile_string(self):
        output = '--------------\nProfile\n--------------\n'
        total = 0.0
        count = 1
        for key in self.build_list:
            build_results = ["[Not Built ]", "[  Built   ]", "[Build Fail]"];
            test_results =  ["[Untested ]", "[Test Pass]", "[Test Fail]"];
            build_result = 0
            test_result = 0
            test_time = 0.0
            build_time = 0.0

            if None in self.result.keys():
                if key in self.result[None].keys():
                    if self.result[None][key] == True:
                        build_result = 1
                    else:
                        build_result = 2

            if "test" in self.profile.keys():
                if key in self.result["test"].keys():
                    if self.result["test"][key] == True:
                        test_result = 1
                    else:
                        test_result = 2

            if None in self.profile.keys():
                if key in self.profile[None].keys():
                    build_time = self.profile[None][key]

            if "test" in self.profile.keys():
                if key in self.profile["test"].keys():
                    test_time = self.profile["test"][key]
                
                    
            output = output + "%3d: %s in %.2f %s in %.2f --- %s\n"% (count, build_results[build_result], build_time , test_results[test_result], test_time, key)
            total = total + build_time
            count = count + 1

        elapsed_time  =  self.finish_time - self.start_time
        output = output + "----------------\n" + "%.2f Cumulative,  %.2f Elapsed, %.2f Speedup \n"%(total, elapsed_time, float(total) / float(elapsed_time))
        return output

    def main(self):
        """
        main command-line entrypoint
        """
        parser = OptionParser(usage="usage: %prog [options] [PACKAGE]...",
                              description="rosmake recursively builds all dependencies before building a package", prog='rosmake')
        parser.add_option("--test-only", dest="test_only", default=False,
                          action="store_true", help="only run tests")
        parser.add_option("-t", dest="test", default=False,
                          action="store_true", help="build and test packages")
        parser.add_option("-a", "--all", dest="build_all", default=False,
                          action="store_true", help="select all packages")
        parser.add_option("-i", "--mark-installed", dest="mark_installed", default=False,
                          action="store_true", help="On successful build, mark specified packages as installed with ROS_NOBUILD")
        parser.add_option("-u", "--unmark-installed", dest="unmark_installed", default=False,
                          action="store_true", help="Remove ROS_NOBUILD from the specified packages.  This will not build anything.")
        parser.add_option("-v", dest="verbose", default=False,
                          action="store_true", help="display errored builds")
        parser.add_option("-r","-k", "--robust", dest="best_effort", default=False,
                           action="store_true", help="do not stop build on error")
        parser.add_option("--build-everything", dest="robust", default=False,
                           action="store_true", help="build all packages regardless of errors")
        parser.add_option("-V", dest="full_verbose", default=False,
                          action="store_true", help="display all builds")
        parser.add_option("-s", "--specified-only", dest="specified_only", default=False,
                          action="store_true", help="only build packages specified on the command line")
        parser.add_option("--buildtest", dest="buildtest",
                          action="append", help="package to buildtest")
        parser.add_option("--buildtest1", dest="buildtest1",
                          action="append", help="package to buildtest1")
        parser.add_option("--output", dest="output_dir",
                          action="store", help="where to output results")
        parser.add_option("--pre-clean", dest="pre_clean",
                          action="store_true", help="run make clean first")
        parser.add_option("--bootstrap", dest="bootstrap", default=False,
                          action="store_true", help="DEPRECATED, UNUSED")
        parser.add_option("--disable-logging", dest="logging_enabled", default=True,
                          action="store_false", help="turn off all logs")
        parser.add_option("--target", dest="target",
                          action="store", help="run make with this target")
        parser.add_option("--pjobs", dest="ros_parallel_jobs", type="int",
                          action="store", help="Override ROS_PARALLEL_JOBS environment variable with this number of jobs.")
        parser.add_option("--threads", dest="threads", type="int", default = os.environ.get("ROSMAKE_THREADS", parallel_build.num_cpus()),
                          action="store", help="Build up to N packages in parallel")
        parser.add_option("--profile", dest="print_profile", default=False,
                          action="store_true", help="print time profile after build")
        parser.add_option("--skip-blacklist", dest="skip_blacklist", 
                          default=False, action="store_true", 
                          help="skip packages containing a file called ROS_BUILD_BLACKLIST (Default behavior will ignore the presence of ROS_BUILD_BLACKLIST)")
        parser.add_option("--skip-blacklist-osx", dest="skip_blacklist_osx", 
                          default=False, action="store_true", 
                          help="deprecated option. it will do nothing, please use platform declarations and --require-platform instead")

        parser.add_option("--status-rate", dest="status_update_rate",
                          action="store", help="How fast to update the status bar in Hz.  Default: 5Hz")
        

        options, args = parser.parse_args()
        self.printer.print_all('rosmake starting...')

        rospack = self.rospack
        rosstack = self.rosstack

        testing = False
        building = True
        if options.test_only:
            testing = True
            building = False
        elif options.test:
            testing = True

        if options.ros_parallel_jobs:
            self.ros_parallel_jobs = options.ros_parallel_jobs

        self.robust_build = options.robust
        self.best_effort = options.best_effort
        self.threads = options.threads
        self.skip_blacklist = options.skip_blacklist
        if options.skip_blacklist_osx:
            self.printer.print_all("Option --skip-blacklist-osx is deprecated. It will do nothing, please use platform declarations and --require-platform instead");
        self.logging_enabled = options.logging_enabled

        # pass through verbosity options
        self.printer.full_verbose = options.full_verbose
        self.printer.verbose = options.verbose
        if options.status_update_rate:
            if float(options.status_update_rate)> 0:
                self.printer.duration = 1.0/float(options.status_update_rate)
            else:
                self.printer.duration = 0

        packages = []
        #load packages from arguments
        if options.build_all:
            packages = [x for x in rospack.list() if not self.rospack.get_manifest(x).is_catkin]
            self.printer.print_all( "Building all packages")
        else:      # no need to extend if all already selected   
            if options.buildtest:
              for p in options.buildtest:
                packages.extend(self.rospack.get_depends_on(p)) 
                self.printer.print_all( "buildtest requested for package %s adding it and all dependent packages: "%p)

            if options.buildtest1:
              for p in options.buildtest1:
                packages.extend(self.rospack.get_depends_on(p, implicit=False)) 
                self.printer.print_all( "buildtest1 requested for package %s adding it and all depends-on1 packages: "%p)

        if len(packages) == 0 and len(args) == 0:
            p = os.path.basename(os.path.abspath('.'))
            try:
              if os.path.samefile(rospack.get_path(p), '.'):
                packages = [p]
                self.printer.print_all( "No package specified.  Building %s"%packages)
              else:
                self.printer.print_all("No package selected and the current directory is not the correct path for package '%s'."%p)
                
            except rospkg.ResourceNotFound as ex:
                try:
                    stack_dir = rosstack.get_path(p)
                    if os.path.samefile(stack_dir, '.'):
                        packages = [p]
                        self.printer.print_all( "No package specified.  Building stack %s"%packages)
                    else:
                        self.printer.print_all("No package or stack arguments and the current directory is not the correct path for stack '%s'. Stack directory is: %s."%(p, rosstack.get_path(p)))
                except:
                    self.printer.print_all("No package or stack specified.  And current directory '%s' is not a package name or stack name."%p)
        else:
            packages.extend(args)

        self.printer.print_all( "Packages requested are: %s"%packages)
        
        # Setup logging
        if self.logging_enabled:
          date_time_stamp =  "rosmake_output-" + time.strftime("%Y%m%d-%H%M%S")
          if options.output_dir:
              #self.log_dir = os.path.join(os.getcwd(), options.output_dir, date_time_stamp);
              self.log_dir = os.path.abspath(options.output_dir)
          else:
              self.log_dir = os.path.join(rospkg.get_ros_home(), "rosmake", date_time_stamp);

          self.printer.print_all("Logging to directory %s"%self.log_dir)
          if os.path.exists (self.log_dir) and not os.path.isdir(self.log_dir):
              self.printer.print_all( "Log destination %s is a file; please remove it or choose a new destination"%self.log_dir)
              sys.exit(1)
          if not os.path.exists (self.log_dir):
              self.printer.print_verbose("%s doesn't exist: creating"%self.log_dir)
              makedirs_with_parent_perms(self.log_dir)

          self.printer.print_verbose("Finished setting up logging")

        stacks_arguments = [s for s in packages if s in rosstack.list()]
        (self.specified_packages, self.rejected_packages) = rospkg.expand_to_packages(packages, rospack, rosstack)

        self.printer.print_all("Expanded args %s to:\n%s"%(packages, self.specified_packages))
        if self.rejected_packages:
            self.printer.print_all("WARNING: The following args could not be parsed as stacks or packages: %s"%self.rejected_packages)
        if len(self.specified_packages) + len(stacks_arguments) == 0:
            self.printer.print_all("ERROR: No arguments could be parsed into valid package or stack names.")
            self.printer.running = False
            return False

        if options.unmark_installed:
            for p in self.specified_packages:
                if self.flag_tracker.remove_nobuild(p):
                    self.printer.print_all("Removed ROS_NOBUILD from %s"%p)
            self.printer.running = False
            return True
            
        required_packages = self.specified_packages[:]

        # catch packages of dependent stacks when specified stack is zero-sized #3528
        # add them to required list but not the specified list. 
        for s in stacks_arguments:
            if not rosstack.packages_of(s):
                for d in rosstack.get_depends(s, implicit=False):
                    try:
                        required_packages.extend(rosstack.packages_of(d))
                    except ResourceNotFound:
                        self.printer.print_all('WARNING: The stack "%s" was not found. We will assume it is using the new buildsystem and try to continue...' % d)

        # deduplicate required_packages
        required_packages = list(set(required_packages))

        # make sure all dependencies are satisfied and if not warn
        buildable_packages = []
        for p in required_packages:
            (buildable, error, str) = self.flag_tracker.can_build(p, self.skip_blacklist, [], False)
            if buildable: 
                buildable_packages.append(p)

        #generate the list of packages necessary to build(in order of dependencies)
        counter = 0
        for p in required_packages:

            counter = counter + 1
            self.printer.print_verbose( "Processing %s and all dependencies(%d of %d requested)"%(p, counter, len(packages)))
            self.build_or_recurse(p)

        # remove extra packages if specified-only flag is set
        if options.specified_only:
          new_list = []
          for pkg in self.build_list:
            if pkg in self.specified_packages:
              new_list.append(pkg)
              self.dependency_tracker = parallel_build.DependencyTracker(self.specified_packages, rospack=self.rospack) # this will make the tracker only respond to packages in the list
        
          self.printer.print_all("specified-only option was used, only building packages %s"%new_list)
          self.build_list = new_list

        if options.pre_clean:
          build_queue = parallel_build.BuildQueue(self.build_list, parallel_build.DependencyTracker([], rospack=self.rospack), robust_build = True)
          self.parallel_build_pkgs(build_queue, "clean", threads = options.threads)

        build_passed = True

        if building:
          self.printer.print_verbose ("Building packages %s"% self.build_list)
          build_queue = parallel_build.BuildQueue(self.build_list, self.dependency_tracker, robust_build = options.robust or options.best_effort)
          if None not in self.result.keys():
                self.result[None] = {}

          build_passed = self.parallel_build_pkgs(build_queue, options.target, threads = options.threads)

        tests_passed = True
        if build_passed and testing:
            self.printer.print_verbose ("Testing packages %s"% packages)
            build_queue = parallel_build.BuildQueue(self.specified_packages, parallel_build.DependencyTracker(self.specified_packages, rospack=self.rospack), robust_build = True)
            tests_passed = self.parallel_build_pkgs(build_queue, "test", threads = 1)


        if  options.mark_installed:
            if build_passed and tests_passed: 
                for p in self.specified_packages:
                    if self.flag_tracker.add_nobuild(p):
                        self.printer.print_all("Marking %s as installed with a ROS_NOBUILD file"%p)
            else:
                self.printer.print_all("All builds and tests did not pass cannot mark packages as installed. ")


        self.finish_time = time.time() #note: before profiling
        self.generate_summary_output(self.log_dir)
        
        if options.print_profile:
            self.printer.print_all (self.get_profile_string())

        self.printer.running = False
        return build_passed and tests_passed



########NEW FILE########
__FILENAME__ = gcc_output_parse
#! /usr/bin/env python

import re

class Warnings:
    """ Extract warnings from GCC's output

    Analyzes compiler output and classifies warnings.
    """

    _warning_pattern_map = {
        'antiquated':' antiquated',
        'deprecated' : ' deprecated',
        'unused_func' : ' defined but not used',
        'isoc' : ' ISO C',
        'missing_init' : ' missing initializer',
        'out_of_bounds' : ' subscript .*? bounds',
        'unused_var' : ' unused variable'
        }

    def __init__(self, console_output):
        self.warning_lines = [ x for x in console_output.splitlines() if x.find(" warning:") > 0 ]
    
    def byType(self, warntype):
        """ Extract warning messages corresponding to warntype.
        The warntypes can be all keys of the _warning_pattern_map dictionary.
        @param warntype: The type of warning message that should be extracted.
        @type warntype: str
        @return a list of warning messages
        @rtype list
        """
        return [ x for x in self.warning_lines if re.search(self._warning_pattern_map[warntype], x) ]
    
    def analyze(self):
        """ Get dictionary of classified warnings.

        @return A dictionary of lists of warning messages indexed by the warning type
        @rtype {str:[str]}
        """
        return dict( [ (t,self.byType(t)) for t,p in self._warning_pattern_map.items() ] )

########NEW FILE########
__FILENAME__ = package_stats
#! /usr/bin/env python

# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Willow Garage, Inc. nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


# Author Tully Foote/tfoote@willowgarage.com

import os
import sys
import subprocess

import rospkg
import rospkg.os_detect

def _platform_supported(m, os, version):
    for p in m.platforms:
        if os == p.os and version == p.version:
            return True
    return False

def platform_supported(rospack, pkg, os, version):
    """
    Return whether the platform defined by os and version is marked as supported in the package
    @param pkg The package to test for support
    @param os The os name to test for support
    @param version The os version to test for support
    """
    return _platform_supported(rospack.get_manifest(pkg), os, version)

class PackageFlagTracker:
  """ This will use the dependency tracker to test if packages are
  blacklisted and all their dependents. """
  def __init__(self, dependency_tracker, os_name = None, os_version = None):
    if not os_name and not os_version:
        try:
            osd = rospkg.os_detect.OsDetect()
            self.os_name = osd.get_codename()
            self.os_version = osd.get_version()
        except rospkg.os_detect.OsNotDetected as ex:
            sys.stderr.write("Could not detect OS. platform detection will not work\n")
    else:
        self.os_name = os_name
        self.os_version = os_version

    self.rospack = rospkg.RosPack()
    self.blacklisted = {}
    self.blacklisted_osx = {}
    self.nobuild = set()
    self.nomakefile = set()
    self.packages_tested = set()
    self.dependency_tracker = dependency_tracker
    self.build_failed = set()

  def register_blacklisted(self, blacklisted_package, dependent_package):
    if dependent_package in self.blacklisted.keys():
      self.blacklisted[dependent_package].append(blacklisted_package)
    else:
      self.blacklisted[dependent_package] = [blacklisted_package] 
      
  def register_blacklisted_osx(self, blacklisted_package, dependent_package):
    if dependent_package in self.blacklisted_osx:
      self.blacklisted_osx[dependent_package].append(blacklisted_package)
    else:
      self.blacklisted_osx[dependent_package] =  [blacklisted_package] 

  def _check_package_flags(self, package):
    if package in self.packages_tested:
      return
    rospack = self.rospack
    path = rospack.get_path(package)
    
    if os.path.exists(os.path.join(path, "ROS_BUILD_BLACKLIST")):
      self.register_blacklisted(package, package)
      for p in rospack.get_depends_on(package, implicit=True):
        self.register_blacklisted(package, p)
        
    if os.path.exists(os.path.join(path, "ROS_BUILD_BLACKLIST_OSX")):
      self.register_blacklisted_osx(package, package)
      for p in rospack.get_depends_on(package, implicit=True):
        self.register_blacklisted_osx(package, p)

    # NO_BUILD if marker file or catkin attribute in manifest
    if os.path.exists(os.path.join(path, "ROS_NOBUILD")):
      self.nobuild.add(package)
    if self.rospack.get_manifest(package).is_catkin:
      self.nobuild.add(package)

    if not os.path.exists(os.path.join(path, "Makefile")):
      self.nomakefile.add(package)                      

    self.packages_tested.add(package)

  def is_blacklisted(self, package):
    # this will noop if already run
    self._check_package_flags(package)

    # make sure it's not dependent on a blacklisted package
    for p in self.dependency_tracker.get_deps(package):
      if p not in self.packages_tested:
        self._check_package_flags(p)
        
    # test result after checking all dependents.
    if package in self.blacklisted:
      return self.blacklisted[package]
        
    return []

  def is_blacklisted_osx(self, package):
    # this will noop if already run
    self._check_package_flags(package)

    # make sure it's not dependent on a blacklisted_osx package
    for p in self.dependency_tracker.get_deps(package):
      if p not in self.packages_tested:
        self._check_package_flags(p)
        
    # test result after checking all dependents.
    if package in self.blacklisted_osx:
      return self.blacklisted_osx[package]
        
    return []

  def has_nobuild(self, package):
    # this will noop if already run
    self._check_package_flags(package)

    # Short circuit if known result
    if package in self.nobuild:
      return True
    return False

  def has_makefile(self, package):
    # this will noop if already run
    self._check_package_flags(package)

    # Short circuit if known result
    if package in self.nomakefile:
      return False
    return True

  def add_nobuild(self, package):
    if self.has_nobuild(package):
      return True
    with open(os.path.join(self.rospack.get_path(package), "ROS_NOBUILD"), 'w') as f:
      f.write("created by rosmake to mark as installed")
      self.nobuild.add(package)
      return True
    return False
    
  def remove_nobuild(self, package):
    if not self.has_nobuild(package):
      return True
    try:
      os.remove(os.path.join(self.rospack.get_path(package), "ROS_NOBUILD"))
      self.nobuild.remove(package)
      return True  
    except:
      return False

  def mark_build_failed(self, package):
      self.build_failed.add(package)

  def build_failed(self, package):
      return package in self.build_failed

  def can_build(self, pkg, use_blacklist = False, failed_packages = [], use_makefile = True):
    """
    Return (buildable, error, "reason why not")
    """
    output_str = ""
    output_state = True
    buildable = True
        
    previously_failed_pkgs = [ pk for pk in failed_packages if pk in self.dependency_tracker.get_deps(pkg)]
    if len(previously_failed_pkgs) > 0:
        buildable = False
        output_state = False
        output_str += " Package %s cannot be built for dependent package(s) %s failed. \n"%(pkg, previously_failed_pkgs)


    if use_blacklist:
        black_listed_dependents = self.is_blacklisted(pkg)
        if len(black_listed_dependents) > 0:
            buildable = False
            output_str += "Cannot build %s ROS_BUILD_BLACKLIST found in packages %s"%(pkg, black_listed_dependents)

    if self.has_nobuild(pkg):
        buildable = False
        output_state = True # dependents are ok, it should already be built
        output_str += "ROS_NOBUILD in package %s\n"%pkg


    if use_makefile and not self.has_makefile(pkg):
        output_state = True # dependents are ok no need to build
        buildable = False
        output_str += " No Makefile in package %s\n"%pkg

    if output_str and output_str[-1] == '\n':
        output_str = output_str[:-1]

    return (buildable, output_state, output_str)

########NEW FILE########
__FILENAME__ = parallel_build
#! /usr/bin/env python

# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Willow Garage, Inc. nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


# Author Tully Foote/tfoote@willowgarage.com

import os
import re
import sys
import subprocess
import time

import rospkg
import threading

if sys.hexversion > 0x03000000: #Python3
    python3 = True
else:
    python3 = False

def _read_stdout(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    std_out, std_err = p.communicate()
    if python3:
        return std_out.decode()
    else:
        return std_out    

def num_cpus():
  """
  Detects the number of CPUs on a system. Cribbed from pp.
  """
  # Linux, Unix and MacOS:
  if hasattr(os, "sysconf"):
    if "SC_NPROCESSORS_ONLN" in os.sysconf_names:
      # Linux & Unix:
      ncpus = os.sysconf("SC_NPROCESSORS_ONLN")
      if isinstance(ncpus, int) and ncpus > 0:
        return ncpus
    else: # OSX:
      return int(_read_stdout(["sysctl", "-n", "hw.ncpu"])) or 1
  # Windows:
  if "NUMBER_OF_PROCESSORS" in os.environ:
    ncpus = int(os.environ["NUMBER_OF_PROCESSORS"]);
    if ncpus > 0:
      return ncpus
  return 1 # Default

#TODO: may no longer need this now that we've ported to rospkg
class DependencyTracker:
  """ Track dependencies between packages.  This is basically a
  caching way to call rospkg. It also will allow you to specifiy a
  range of packages over which to track dependencies.  This is useful
  if you are only building a subset of the tree. For example with the
  --specified-only option. """
  def __init__(self, valid_packages=None, rospack=None):
    """
    @param valid_packages: defaults to rospack list
    """
    if rospack is None:
        self.rospack = rospkg.RosPack()
    else:
        self.rospack = rospack
    if valid_packages is None:
      valid_packages = self.rospack.list()
    self.valid_packages = valid_packages
    self.deps_1 = {}
    self.deps = {}

  def get_deps_1(self, package):
    if not package in self.deps_1:
      self.deps_1[package] = []
      try:
          potential_dependencies = self.rospack.get_depends(package, implicit=False)
      except rospkg.ResourceNotFound:
          potential_dependencies = []
      for p in potential_dependencies:
        if p in self.valid_packages:
          self.deps_1[package].append(p)
      
    return self.deps_1[package]

  def get_deps(self, package):
    if not package in self.deps:
      self.deps[package] = []
      try:
          potential_dependencies = self.rospack.get_depends(package) 
      except rospkg.ResourceNotFound:
          potential_dependencies = []

      for p in potential_dependencies:
        if p in self.valid_packages:
          self.deps[package].append(p)
    return self.deps[package]

  def load_fake_deps(self, deps, deps1):
    self.deps = deps
    self.deps_1 = deps1
    return


class CompileThread(threading.Thread):
  """ This is the class which is used as the thread for parallel
  builds.  This class will query the build queue object for new
  commands and block on its calls until the build queue says that
  building is done. """
  def __init__(self, name, build_queue, rosmakeall, argument = None):
    threading.Thread.__init__(self)
    self.build_queue = build_queue
    self.rosmakeall = rosmakeall
    self.argument = argument
    self.name = name
    self.logging_enabled = True

  def run(self):
    while not self.build_queue.is_done():
      pkg = self.build_queue.get_valid_package()
      if not pkg:
        if self.build_queue.succeeded():
          self.rosmakeall.printer.print_verbose("[ Build Completed Thread Exiting ]", thread_name=self.name);
        else:
          self.rosmakeall.printer.print_verbose("[ Build Terminated Thread Exiting ]", thread_name=self.name)
        break # no more packages must be done

      # update status after accepting build
      self.rosmakeall.update_status(self.argument ,
                                    self.build_queue.get_started_threads(),
                                    self.build_queue.progress_str())

      if self.argument:
        self.rosmakeall.printer.print_all ("Starting >>> %s [ make %s ]"%(pkg, self.argument), thread_name=self.name)
      else:
        self.rosmakeall.printer.print_all ("Starting >>> %s [ make ] "%pkg,  thread_name=self.name)
      (result, result_string) = self.rosmakeall.build(pkg, self.argument, self.build_queue.robust_build) 
      self.rosmakeall.printer.print_all("Finished <<< %s %s"%(pkg, result_string), thread_name= self.name)
      #print "Finished2"
      self.build_queue.return_built(pkg, result)
      #print "returned"
      if result or self.build_queue.robust_build:
        pass#print "result", result, "robust", self.build_queue.robust_build
      else:
        if result_string.find("[Interrupted]") != -1:
          self.rosmakeall.printer.print_all("Caught Interruption", thread_name=self.name)
          self.build_queue.stop() #todo move this logic into BuildQueue itself
          break # unnecessary since build_queue is done now while will quit
        self.rosmakeall.printer.print_all("Halting due to failure in package %s. \n[ rosmake ] Waiting for other threads to complete."%pkg)
        self.build_queue.stop()
        break # unnecessary since build_queue is done now, while will quit
      # update status after at end of build
      #print "updating status"
      self.rosmakeall.update_status(self.argument ,
                                    self.build_queue.get_started_threads(),
                                    self.build_queue.progress_str())
      #print "done built", len(self.build_queue.built), self.build_queue.built
      #print "failed", len(self.build_queue.failed), self.build_queue.failed
      #print "to_build", len(self.build_queue.to_build), self.build_queue.to_build
      #print "in progress", len(self.build_queue._started), self.build_queue._started

    #print "last update"
    # update status before ending thread
    self.rosmakeall.update_status(self.argument ,
                                  self.build_queue.get_started_threads(),
                                  self.build_queue.progress_str())
    #print "thread finished"

class BuildQueue:
  """ This class provides a thread safe build queue.  Which will do
  the sequencing for many CompileThreads. """
  def __init__(self, package_list, dependency_tracker, robust_build = False):
    self._total_pkgs = len(package_list)
    self.dependency_tracker = dependency_tracker
    self.to_build = package_list[:] # do a copy not a reference
    self.built = []
    self.failed = []
    self.condition = threading.Condition()
    self._done = False
    self.robust_build = robust_build
    self._started = {}
    self._hack_end_counter = 0

  def progress_str(self):
    return "[ %d Active %d/%d Complete ]"%(len(self._started), len(self.built), self._total_pkgs)

  def get_started_threads(self): #TODO sort this other than hash order
    return self._started.copy()

  def is_completed(self):
    """Return if the build queue has been completed """
    return len(self.built)+ len(self.failed) == self._total_pkgs

  def is_done(self):
    """Return if the build queue has been completed """
    return self.is_completed() or self._done # finished or halted

  def succeeded(self):
    """ Return whether the build queue has completed all packages successfully. """
    return len(self.built) == self._total_pkgs  #flag that we're finished

  def stop(self): 
    """ Stop the build queue, including waking all blocking
    threads. It will not stop in flight builds."""
    self._done = True
    with self.condition:
      self.condition.notifyAll() # wake any blocking threads
      
  def return_built(self, package, successful=True): # mark that a package is built
    """ The thread which completes a package marks it as done with
    this method."""
    with self.condition:
      if successful:
        self.built.append(package)
      else:
        self.failed.append(package)
      if package in self._started.keys():
        self._started.pop(package)
      else:
        pass #used early on print "\n\n\nERROR THIS SHOULDN't RETURN %s\n\n\n"%package
      if self.is_completed():
        self._done = True
      self.condition.notifyAll() #wake up any waiting threads

  def get_valid_package(self): # blocking call to get a package to build returns none if done
    """ This is a blocking call which will return a package which has
    all dependencies met.  If interrupted or done it will return
    None"""
    with self.condition:
      while (not self.is_done() and len(self.to_build) > 0):
        for p in self.to_build:
          dependencies_met = True
          for d in self.dependency_tracker.get_deps(p):
            if d not in self.built and not (self.robust_build and d in self.failed):
              dependencies_met = False
              #print "Dependency %s not met for %s"%(d, p)
              break
          if dependencies_met:  # all dependencies met
            self.to_build.remove(p)
            self._started[p] = time.time()
            self._hack_end_counter = 0 #reset end counter if success
            return p # break out and return package if found
          elif len(self._started) == 0 and self._hack_end_counter > 2:
            # we're hung with broken dependencies
            return None
        #print "TTGTTTTHTHT Waiting on condition"
        self.condition.wait(1.0)  # failed to find a package wait for a notify before looping
        
        self._hack_end_counter += 1 # if we're here too often we will quit 
        if self.is_done():
          break

    return None

########NEW FILE########
__FILENAME__ = test_parallel_build
#!/usr/bin/env python
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Willow Garage, Inc. nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import sys
import unittest

from rosmake import parallel_build

class TestDependencyTracker(unittest.TestCase):
    def setUp(self):
        self.deps = {}
        self.deps1 = {}
        self.deps["a"] = [ "b", "c", "d","e"]
        self.deps1["a"] = ["b"]
        self.deps["b"] = ["c"]
        self.deps1["b"] = ["c"]
        self.deps["d"] = ["c", "e"]
        self.deps1["d"] = ["c", "e"]
        self.dt = parallel_build.DependencyTracker()
        self.dt.load_fake_deps(self.deps, self.deps1)


    def test_deps_1(self):
        self.assertEquals(self.deps1["a"], self.dt.get_deps_1("a"))
        self.assertEquals(self.deps1["b"], self.dt.get_deps_1("b"))
        self.assertEquals(self.deps1["d"], self.dt.get_deps_1("d"))

    def test_deps(self):
        self.assertEquals(self.deps["a"], self.dt.get_deps("a"))
        self.assertEquals(self.deps["b"], self.dt.get_deps("b"))
        self.assertEquals(self.deps["d"], self.dt.get_deps("d"))

    def test_not_package(self):
        self.assertEquals([], self.dt.get_deps("This is not a valid package name"))
        self.assertEquals([], self.dt.get_deps_1("This is not a valid package name"))
        

class TestBuildQueue(unittest.TestCase):

    def setUp(self):
        deps = {}
        deps1 = {}
        deps1["a"] = ["b"]
        deps["a"] = ["b", "c", "d", "e", "f"]
        deps1["b"] = ["c"]
        deps["b"] = ["c", "d", "e", "f"]
        deps1["c"] = ["d"]
        deps["c"] = ["d", "e", "f"]
        deps1["d"] = ["e"]
        deps["d"] = ["e", "f"]
        deps["e"] = ["f"]
        deps1["e"] = ["f"]
        deps["f"] = []
        deps1["f"] = []

        self.serial_tracker = parallel_build.DependencyTracker()
        self.serial_tracker.load_fake_deps(deps, deps1)

        deps = {}
        deps1 = {}
        deps["a"] = ["b", "c", "d", "e", "f"]
        deps1["a"] = ["b", "c", "d", "e", "f"]
        deps["b"] = []
        deps1["b"] = []
        deps["c"] = []
        deps1["c"] = []
        deps["d"] = []
        deps1["d"] = []
        deps["e"] = []
        deps1["e"] = []
        deps["f"] = []
        deps1["f"] = []
        
        self.parallel_tracker = parallel_build.DependencyTracker()
        self.parallel_tracker.load_fake_deps(deps, deps1)

    # full queue
    def test_full_build(self):
        bq = parallel_build.BuildQueue(["a", "b", "c", "d", "e", "f"], self.serial_tracker)
        self.assertFalse(bq.is_done())
        self.assertFalse(bq.succeeded())
        
        self.assertEqual("f", bq.get_valid_package())
        self.assertEqual(0, len(bq.built))
        bq.return_built("f")
        self.assertEqual(1, len(bq.built))
        self.assertFalse(bq.is_done())
        self.assertFalse(bq.succeeded())

        self.assertEqual("e", bq.get_valid_package())
        bq.return_built("e")
        self.assertEqual(2, len(bq.built))
        self.assertFalse(bq.is_done())
        self.assertFalse(bq.succeeded())

        self.assertEqual("d", bq.get_valid_package())
        bq.return_built("d")
        self.assertEqual(3, len(bq.built))
        self.assertFalse(bq.is_done())
        self.assertFalse(bq.succeeded())

        self.assertEqual("c", bq.get_valid_package())
        bq.return_built("c")
        self.assertEqual(4, len(bq.built))
        self.assertFalse(bq.is_done())
        self.assertFalse(bq.succeeded())

        self.assertEqual("b", bq.get_valid_package())
        bq.return_built("b")
        self.assertEqual(5, len(bq.built))
        self.assertFalse(bq.is_done())
        self.assertFalse(bq.succeeded())

        self.assertEqual("a", bq.get_valid_package())
        self.assertFalse(bq.is_done())
        self.assertFalse(bq.succeeded())
        bq.return_built("a")
        self.assertEqual(6, len(bq.built))
        self.assertTrue (bq.is_done())
        self.assertTrue (bq.succeeded())


    # partial build
    def test_partial_build(self):
        bq = parallel_build.BuildQueue(["d", "e", "f"], self.serial_tracker)
        self.assertFalse(bq.is_done())
        self.assertFalse(bq.succeeded())
        
        self.assertEqual("f", bq.get_valid_package())
        self.assertEqual(0, len(bq.built))
        bq.return_built("f")
        self.assertEqual(1, len(bq.built))
        self.assertFalse(bq.is_done())
        self.assertFalse(bq.succeeded())

        self.assertEqual("e", bq.get_valid_package())
        bq.return_built("e")
        self.assertEqual(2, len(bq.built))
        self.assertFalse(bq.is_done())
        self.assertFalse(bq.succeeded())

        self.assertEqual("d", bq.get_valid_package())
        self.assertFalse(bq.is_done())
        self.assertFalse(bq.succeeded())
        bq.return_built("d")
        self.assertEqual(3, len(bq.built))
        self.assertTrue(bq.is_done())
        self.assertTrue(bq.succeeded())


    # abort early
    def test_abort_early(self):
        bq = parallel_build.BuildQueue(["a", "b", "c", "d", "e", "f"], self.serial_tracker)
        self.assertFalse(bq.is_done())
        self.assertFalse(bq.succeeded())
        self.assertEqual(0, len(bq.built))
        
        self.assertEqual("f", bq.get_valid_package())
        bq.return_built("f")
        self.assertEqual(1, len(bq.built))
        self.assertFalse(bq.is_done())
        self.assertFalse(bq.succeeded())

        self.assertEqual("e", bq.get_valid_package())
        bq.return_built("e")
        self.assertEqual(2, len(bq.built))
        self.assertFalse(bq.is_done())
        self.assertFalse(bq.succeeded())

        self.assertEqual("d", bq.get_valid_package())
        bq.return_built("d")
        self.assertEqual(3, len(bq.built))
        self.assertFalse(bq.is_done())
        self.assertFalse(bq.succeeded())

        bq.stop()
        self.assertTrue(bq.is_done())
        self.assertFalse(bq.succeeded())

        self.assertEqual(None, bq.get_valid_package())

    # many parallel
    def test_parallel_build(self):
        bq = parallel_build.BuildQueue(["a", "b", "c", "d", "e", "f"], self.parallel_tracker)
        self.assertFalse(bq.is_done())
        self.assertFalse(bq.succeeded())
        
        dependents = ["b", "c", "d", "e", "f"]
        count = 0
        total = 6
        while len(dependents) > 0:
            result= bq.get_valid_package()
            done = len(bq.built)
            pkgs = bq._total_pkgs
            self.assertTrue(result in dependents)
            #print result, done, pkgs
            dependents.remove(result)
            self.assertEqual(count, done)
            self.assertEqual(total, pkgs)
            self.assertFalse(bq.is_done())
            self.assertFalse(bq.succeeded())
            bq.return_built(result)
            count = count + 1
            self.assertFalse(bq.is_done())
            self.assertFalse(bq.succeeded())


        self.assertEqual("a", bq.get_valid_package())
        self.assertFalse(bq.is_done())
        self.assertFalse(bq.succeeded())
        bq.return_built("a")
        self.assertTrue (bq.is_done())
        self.assertTrue (bq.succeeded())


    # stalled(future)

########NEW FILE########
__FILENAME__ = test_rosmake_commandline
# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os
import sys
import subprocess

def test_Rosmake_commandline_usage():
    assert 0 == subprocess.call(["rosmake", "-h"])

########NEW FILE########
__FILENAME__ = check_test_ran
#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$

"""
Writes a test failure out to test file if it doesn't exist.
"""

from __future__ import print_function
NAME="check_test_ran.py"

import os
import sys

import rospkg
import rosunit

def usage():
    print("""Usage:
\t%s test-file.xml
or
\t%s --rostest pkg-name test-file.xml
"""%(NAME, NAME), file=sys.stderr)
    print(sys.argv)
    sys.exit(getattr(os, 'EX_USAGE', 1))

def check_main():
    if len(sys.argv) < 2:
        usage()
    if '--rostest' in sys.argv[1:]:
        if len(sys.argv) != 4:
            usage()
        test_pkg, test_file = [a for a in sys.argv[1:] if a != '--rostest']
        # this logic derives the output filename that rostest uses

        r = rospkg.RosPack()
        pkg_name = rospkg.get_package_name(test_file)
        pkg_dir = r.get_path(pkg_name)

        # compute test name for friendlier reporting
        outname = rosunit.rostest_name_from_path(pkg_dir, test_file)
            
        test_file = rosunit.xml_results_file(test_pkg, outname, is_rostest=True)
    else:
        if len(sys.argv) != 2:
            usage()
        test_file = sys.argv[1]
        
    print("Checking for test results in %s"%test_file)
    
    if not os.path.exists(test_file):
        if not os.path.exists(os.path.dirname(test_file)):
            os.makedirs(os.path.dirname(test_file))
            
        print("Cannot find results, writing failure results to", test_file)
        
        with open(test_file, 'w') as f:
            test_name = os.path.basename(test_file)
            d = {'test': test_name, 'test_file': test_file }
            f.write("""<?xml version="1.0" encoding="UTF-8"?>
<testsuite tests="1" failures="1" time="1" errors="0" name="%(test)s">
  <testcase name="test_ran" status="run" time="1" classname="Results">
    <failure message="Unable to find test results for %(test)s, test did not run.\nExpected results in %(test_file)s" type=""/>
  </testcase>
</testsuite>"""%d)

if __name__ == '__main__':
    check_main()

########NEW FILE########
__FILENAME__ = clean_junit_xml
#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$

from __future__ import print_function

"""
clean_junit_xml.py is a simple script that takes all the xml-formatted
Ant JUnit XML test output in test_results and aggregates them into
test_results/_hudson. In this process, it strips any characters that
tend to cause Hudson trouble.
"""

PKG = 'rosunit'

import os
import sys

import rospkg
import rosunit.junitxml as junitxml

def prepare_dirs(output_dir_name):
    test_results_dir = rospkg.get_test_results_dir()
    print("will read test results from", test_results_dir)
    output_dir = os.path.join(test_results_dir, output_dir_name)
    if not os.path.exists(output_dir):
        print("creating directory", output_dir)
        os.makedirs(output_dir)
    return test_results_dir, output_dir

def clean_results(test_results_dir, output_dir, filter):
    """
    Read results from test_results_dir and write them into output_dir.
    """
    for d in os.listdir(test_results_dir):
        if filter and d in filter:
            continue
        print("looking at", d)
        test_dir = os.path.join(test_results_dir, d)
        if not os.path.isdir(test_dir):
            continue
        base_test_name = os.path.basename(test_dir)
        # for each test result that a package generated, read it, then
        # rewrite it to our output directory. This will invoke our
        # cleaning rules on the XML that protect the result from Hudson
        # issues.
        for file in os.listdir(test_dir):
            if file.endswith('.xml'):
                test_name = base_test_name + '.' + file[:-4]
            file = os.path.join(test_dir, file)
            try:
                result = junitxml.read(file, test_name)
                output_path = os.path.join(output_dir, "%s.xml"%test_name)
                with open(output_path, 'w') as f:
                    print("re-writing", output_path)
                    f.write(result.xml().encode('utf-8'))
            except Exception as e:
                sys.stderr.write("ignoring [%s]: %s\n"%(file, e))

def main():
    
    print("[clean_junit_xml]: STARTING")
    
    output_dir_name = '_hudson'
    test_results_dir, output_dir = prepare_dirs(output_dir_name)
    
    print("[clean_junit_xml]: writing aggregated test results to %s"%output_dir)
    
    clean_results(test_results_dir, output_dir, [output_dir_name, '.svn'])
    
    print("[clean_junit_xml]: FINISHED")
  
if __name__ == '__main__':
    main()
  

########NEW FILE########
__FILENAME__ = pycoverage_to_html
#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$

"""
Generate HTML reports from coverage.py (aka python-coverage). This is
currently a no-frills backend tool.
"""

import sys
import roslib

try:
    import coverage
except ImportError as e:
    sys.stderr.write("ERROR: cannot import python-coverage, coverage report will not run.\nTo install coverage, run 'easy_install coverage'\n")
    sys.exit(1)

def coverage_html():
    import os.path
    if not os.path.isfile('.coverage-modules'):
        sys.stderr.write("No .coverage-modules file; nothing to do\n")
        return

    with open('.coverage-modules','r') as f:
        modules = [x for x in f.read().split('\n') if x.strip()]

    cov = coverage.coverage()
    cov.load()

    # import everything
    for m in modules:
        try:
            base = m.split('.')[0]
            roslib.load_manifest(base)
            __import__(m)
        except:
            sys.stderr.write("WARN: cannot import %s\n"%(base))

    modlist = '\n'.join([" * %s"%m for m in modules])
    sys.stdout.write("Generating for\n%s\n"%(modlist))

    # load the module instances to pass to coverage so it can generate annotation html reports
    mods = []

    # TODO: rewrite, buggy
    for m in modules:
        mods.extend([v for v in sys.modules.values() if v and v.__name__.startswith(m) and not v in mods])
        
    # dump the output to covhtml directory
    cov.html_report(mods, directory="covhtml")
    
if __name__ == '__main__':
    coverage_html()

########NEW FILE########
__FILENAME__ = summarize_results
#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$

"""
Prints summary of aggregated test results to stdout. This is useful
when running several tests across a package.
"""

from __future__ import print_function

import os
import sys
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

import rospkg
import rosunit.junitxml as junitxml

def create_summary(result, packages):
    buff = StringIO()

    buff.write('-'*80+'\n')
    buff.write('\033[1m[AGGREGATED TEST RESULTS SUMMARY]\033[0m\n\n')

    errors_failures = [r for r in result.test_case_results if r.errors or r.failures]
    if errors_failures:
        buff.write('ERRORS/FAILURES:\n')
        for tc_result in errors_failures:
            buff.write(tc_result.description)

    buff.write("PACKAGES: \n%s\n\n"%'\n'.join([" * %s"%p for p in packages]))

    buff.write('\nSUMMARY\n')
    if (result.num_errors + result.num_failures) == 0:
        buff.write("\033[32m * RESULT: SUCCESS\033[0m\n")
    else:
        buff.write("\033[1;31m * RESULT: FAIL\033[0m\n")

    # TODO: still some issues with the numbers adding up if tests fail to launch

    # number of errors from the inner tests, plus add in count for tests
    # that didn't run properly ('result' object).
    buff.write(" * TESTS: %s\n"%result.num_tests)
    if result.num_errors:
        buff.write("\033[1;31m * ERRORS: %s\033[0m\n"%result.num_errors)
    else:
        buff.write(" * ERRORS: 0\n")
    if result.num_failures:
        buff.write("\033[1;31m * FAILURES: %s\033[0m\n"%result.num_failures)
    else:
        buff.write(" * FAILURES: 0\n")
    return buff.getvalue()

def main():
    from optparse import OptionParser
    parser = OptionParser(usage="usage: summarize_results.py [options] package")
    parser.add_option("--nodeps",
                      dest="no_deps", default=False,
                      action="store_true",
                      help="don't compute test results for the specified package only")
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error("Only one package may be specified")
    
    package = args[0]
    r = rospkg.RosPack()
    if options.no_deps:
        packages = [package]
    else:
        packages = [package] + r.get_depends_on(package, implicit=True)
        packages = [p for p in packages if p]

    result = junitxml.read_all(packages)
    print(create_summary(result, packages))
    if result.num_errors or result.num_failures:
        sys.exit(1)
  
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_results_dir
#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$

"""
test_results_dir.py simply prints the directory that rosunit/rostest
results are stored in.
"""

from __future__ import print_function
import rospkg
print(rospkg.get_test_results_dir())

########NEW FILE########
__FILENAME__ = baretest
# Software License Agreement (BSD License)
#
# Copyright (c) 2010, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$

"""
rostest implementation of running bare (gtest-compatible) unit test
executables. These do not run in a ROS environment.
"""

from __future__ import print_function

import os
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
import unittest
import time
import signal
import subprocess
import traceback

import rospkg

from .core import xml_results_file, rostest_name_from_path, create_xml_runner, printlog, printerrlog, printlog_bold

from . import pmon
from . import junitxml

BARE_TIME_LIMIT = 60.
TIMEOUT_SIGINT  = 15.0 #seconds
TIMEOUT_SIGTERM = 2.0 #seconds

class TestTimeoutException(Exception): pass

class BareTestCase(unittest.TestCase):

    def __init__(self, exe, args, retry=0, time_limit=None, test_name=None, text_mode=False, package_name=None):
        """
        @param exe: path to executable to run
        @type  exe: str
        @param args: arguments to exe
        @type  args: [str]
        @type  retry: int
        @param time_limit: (optional) time limit for test. Defaults to BARE_TIME_LIMIT.
        @type  time_limit: float
        @param test_name: (optional) override automatically generated test name
        @type  test_name: str
        @param package_name: (optional) override automatically inferred package name
        @type  package_name: str
        """
        super(BareTestCase, self).__init__()
        self.text_mode = text_mode
        if package_name:
            self.package = package_name
        else:
            self.package = rospkg.get_package_name(exe)
        self.exe = os.path.abspath(exe)
        if test_name is None:
            self.test_name = os.path.basename(exe)
        else:
            self.test_name = test_name

        # invoke pyunit tests with python executable
        if self.exe.endswith('.py'):
            self.args = ['python', self.exe] + args
        else:
            self.args = [self.exe] + args
        if text_mode:
            self.args = self.args + ['--text']
            
        self.retry = retry
        self.time_limit = time_limit or BARE_TIME_LIMIT
        self.pmon = None
        self.results = junitxml.Result(self.test_name)
        
    def setUp(self):
        self.pmon = pmon.start_process_monitor()
        
    def tearDown(self):
        if self.pmon is not None:
            pmon.shutdown_process_monitor(self.pmon)
            self.pmon = None
        
    def runTest(self):
        self.failIf(self.package is None, "unable to determine package of executable")
            
        done = False
        while not done:
            test_name = self.test_name

            printlog("Running test [%s]", test_name)

            #setup the test
            # - we pass in the output test_file name so we can scrape it
            test_file = xml_results_file(self.package, test_name, False)
            if os.path.exists(test_file):
                printlog("removing previous test results file [%s]", test_file)
                os.remove(test_file)

            self.args.append('--gtest_output=xml:%s'%test_file)

            # run the test, blocks until completion
            printlog("running test %s"%test_name)
            timeout_failure = False

            run_id = None
            #TODO: really need different, non-node version of LocalProcess instead of these extra args
            process = LocalProcess(run_id, self.package, self.test_name, self.args, os.environ, False, cwd='cwd', is_node=False)

            pm = self.pmon
            pm.register(process)
            success = process.start()
            self.assert_(success, "test failed to start")

            #poll until test terminates or alloted time exceed
            timeout_t = time.time() + self.time_limit
            try:
                while process.is_alive():
                    #test fails on timeout
                    if time.time() > timeout_t:
                        raise TestTimeoutException("test max time allotted")
                    time.sleep(0.1)
                
            except TestTimeoutException as e:
                if self.retry:
                    timeout_failure = True
                else:
                    raise

            if not timeout_failure:
                printlog("test [%s] finished"%test_name)
            else:
                printerrlog("test [%s] timed out"%test_name)                
        
                
            if self.text_mode:
                results = self.results
            elif not self.text_mode:
                # load in test_file
                if not timeout_failure:
                    self.assert_(os.path.isfile(test_file), "test [%s] did not generate test results"%test_name)
                    printlog("test [%s] results are in [%s]", test_name, test_file)
                    results = junitxml.read(test_file, test_name)
                    test_fail = results.num_errors or results.num_failures
                else:
                    test_fail = True

            if self.retry > 0 and test_fail:
                self.retry -= 1
                printlog("test [%s] failed, retrying. Retries left: %s"%(test_name, self.retry))
            else:
                done = True
                self.results = results
                printlog("test [%s] results summary: %s errors, %s failures, %s tests",
                         test_name, results.num_errors, results.num_failures, results.num_tests)

        printlog("[ROSTEST] test [%s] done", test_name)


#TODO: this is a straight copy from roslaunch. Need to reduce, refactor
class LocalProcess(pmon.Process):
    """
    Process launched on local machine
    """
    
    def __init__(self, run_id, package, name, args, env, log_output, respawn=False, required=False, cwd=None, is_node=True):
        """
        @param run_id: unique run ID for this roslaunch. Used to
          generate log directory location. run_id may be None if this
          feature is not being used.
        @type  run_id: str
        @param package: name of package process is part of
        @type  package: str
        @param name: name of process
        @type  name: str
        @param args: list of arguments to process
        @type  args: [str]
        @param env: environment dictionary for process
        @type  env: {str : str}
        @param log_output: if True, log output streams of process
        @type  log_output: bool
        @param respawn: respawn process if it dies (default is False)
        @type  respawn: bool
        @param cwd: working directory of process, or None
        @type  cwd: str
        @param is_node: (optional) if True, process is ROS node and accepts ROS node command-line arguments. Default: True
        @type  is_node: False
        """    
        super(LocalProcess, self).__init__(package, name, args, env, respawn, required)
        self.run_id = run_id
        self.popen = None
        self.log_output = log_output
        self.started = False
        self.stopped = False
        self.cwd = cwd
        self.log_dir = None
        self.pid = -1
        self.is_node = is_node

    # NOTE: in the future, info() is going to have to be sufficient for relaunching a process
    def get_info(self):
        """
        Get all data about this process in dictionary form
        """    
        info = super(LocalProcess, self).get_info()
        info['pid'] = self.pid
        if self.run_id:
            info['run_id'] = self.run_id
        info['log_output'] = self.log_output
        if self.cwd is not None:
            info['cwd'] = self.cwd
        return info

    def _configure_logging(self):
        """
        Configure logging of node's log file and stdout/stderr
        @return: stdout log file name, stderr log file
        name. Values are None if stdout/stderr are not logged.
        @rtype: str, str
        """    
        log_dir = rospkg.get_log_dir(env=os.environ)
        if self.run_id:
            log_dir = os.path.join(log_dir, self.run_id)
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except OSError as e:
                if e.errno == 13:
                    raise RLException("unable to create directory for log file [%s].\nPlease check permissions."%log_dir)
                else:
                    raise RLException("unable to create directory for log file [%s]: %s"%(log_dir, e.msg))
        # #973: save log dir for error messages
        self.log_dir = log_dir

        # send stdout/stderr to file. in the case of respawning, we have to
        # open in append mode
        # note: logfileerr: disabling in favor of stderr appearing in the console.
        # will likely reinstate once roserr/rosout is more properly used.
        logfileout = logfileerr = None

        if self.log_output:
            outf, errf = [os.path.join(log_dir, '%s-%s.log'%(self.name, n)) for n in ['stdout', 'stderr']]
            if self.respawn:
                mode = 'a'
            else:
                mode = 'w'
            logfileout = open(outf, mode)
            if is_child_mode():
                logfileerr = open(errf, mode)

        # #986: pass in logfile name to node
        node_log_file = log_dir
        if self.is_node:
            # #1595: on respawn, these keep appending
            self.args = _cleanup_remappings(self.args, '__log:=')
            self.args.append("__log:=%s"%os.path.join(log_dir, "%s.log"%self.name))

        return logfileout, logfileerr

    def start(self):
        """
        Start the process.
        
        @raise pmon.FatalProcessLaunch: if process cannot be started and it
        is not likely to ever succeed
        """
        super(LocalProcess, self).start()
        try:
            self.lock.acquire()
            self.started = self.stopped = False

            full_env = self.env

            # _configure_logging() can mutate self.args
            try:
                logfileout, logfileerr = self._configure_logging()
            except Exception as e:
                printerrlog("[%s] ERROR: unable to configure logging [%s]"%(self.name, str(e)))
                # it's not safe to inherit from this process as
                # rostest changes stdout to a StringIO, which is not a
                # proper file.
                logfileout, logfileerr = subprocess.PIPE, subprocess.PIPE

            if self.cwd == 'node':
                cwd = os.path.dirname(self.args[0])
            elif self.cwd == 'cwd':
                cwd = os.getcwd()
            elif self.cwd == 'ros-root':
                cwd = get_ros_root()
            else:
                cwd = rospkg.get_ros_home()

            try:
                self.popen = subprocess.Popen(self.args, cwd=cwd, stdout=logfileout, stderr=logfileerr, env=full_env, close_fds=True, preexec_fn=os.setsid)
            except OSError as e:
                self.started = True # must set so is_alive state is correct
                if e.errno == 8: #Exec format error
                    raise pmon.FatalProcessLaunch("Unable to launch [%s]. \nIf it is a script, you may be missing a '#!' declaration at the top."%self.name)
                elif e.errno == 2: #no such file or directory
                    raise pmon.FatalProcessLaunch("""Roslaunch got a '%s' error while attempting to run:

%s

Please make sure that all the executables in this command exist and have
executable permission. This is often caused by a bad launch-prefix."""%(msg, ' '.join(self.args)))
                else:
                    raise pmon.FatalProcessLaunch("unable to launch [%s]: %s"%(' '.join(self.args), msg))
                
            self.started = True
            # Check that the process is either still running (poll returns
            # None) or that it completed successfully since when we
            # launched it above (poll returns the return code, 0).
            poll_result = self.popen.poll()
            if poll_result is None or poll_result == 0:
                self.pid = self.popen.pid
                printlog_bold("process[%s]: started with pid [%s]"%(self.name, self.pid))
                return True
            else:
                printerrlog("failed to start local process: %s"%(' '.join(self.args)))
                return False
        finally:
            self.lock.release()

    def is_alive(self):
        """
        @return: True if process is still running
        @rtype: bool
        """
        if not self.started: #not started yet
            return True
        if self.stopped or self.popen is None:
            return False
        self.exit_code = self.popen.poll()
        if self.exit_code is not None:
            return False
        return True

    def get_exit_description(self):
        """
        @return: human-readable description of exit state 
        @rtype: str
        """
        # #973: include location of output location in message
        if self.exit_code is not None:
            if self.exit_code:
                if self.log_dir:
                    return 'process has died [pid %s, exit code %s].\nlog files: %s*.log'%(self.pid, self.exit_code, os.path.join(self.log_dir, self.name))
                else:
                    return 'process has died [pid %s, exit code %s]'%(self.pid, self.exit_code)
            else:
                if self.log_dir:
                    return 'process has finished cleanly.\nlog file: %s*.log'%(os.path.join(self.log_dir, self.name))
                else:
                    return 'process has finished cleanly'
        else:
            return 'process has died'

    def _stop_unix(self, errors):
        """
        UNIX implementation of process killing

        @param errors: error messages. stop() will record messages into this list.
        @type  errors: [str]
        """
        self.exit_code = self.popen.poll() 
        if self.exit_code is not None:
            #print "process[%s].stop(): process has already returned %s"%(self.name, self.exit_code)                
            self.popen = None
            self.stopped = True
            return

        pid = self.popen.pid
        pgid = os.getpgid(pid)

        try:
            # Start with SIGINT and escalate from there.
            os.killpg(pgid, signal.SIGINT)
            timeout_t = time.time() + TIMEOUT_SIGINT
            retcode = self.popen.poll()                
            while time.time() < timeout_t and retcode is None:
                time.sleep(0.1)
                retcode = self.popen.poll()
            # Escalate non-responsive process
            if retcode is None:
                printerrlog("[%s] escalating to SIGTERM"%self.name)
                timeout_t = time.time() + TIMEOUT_SIGTERM
                os.killpg(pgid, signal.SIGTERM)                
                retcode = self.popen.poll()
                while time.time() < timeout_t and retcode is None:
                    time.sleep(0.2)
                    retcode = self.popen.poll()
                if retcode is None:
                    printerrlog("[%s] escalating to SIGKILL"%self.name)
                    errors.append("process[%s, pid %s]: required SIGKILL. May still be running."%(self.name, pid))
                    try:
                        os.killpg(pgid, signal.SIGKILL)
                        # #2096: don't block on SIGKILL, because this results in more orphaned processes overall
                    except OSError as e:
                        if e.args[0] == 3:
                            printerrlog("no [%s] process with pid [%s]"%(self.name, pid))
                        else:
                            printerrlog("errors shutting down [%s]: %s"%(self.name, e))
        finally:
            self.popen = None

    def stop(self, errors=[]):
        """
        Stop the process. Record any significant error messages in the errors parameter
        
        @param errors: error messages. stop() will record messages into this list.
        @type  errors: [str]
        """
        super(LocalProcess, self).stop(errors)
        self.lock.acquire()        
        try:
            try:
                if self.popen is None:
                    return
                #NOTE: currently POSIX-only. Need to add in Windows code once I have a test environment:
                # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/347462
                self._stop_unix(errors)
            except:
                printerrlog("[%s] EXCEPTION %s"%(self.name, traceback.format_exc()))
        finally:
            self.stopped = True
            self.lock.release()

def print_runner_summary(runner_results, junit_results, runner_name='ROSUNIT'):
    """
    Print summary of runner results and actual test results to
    stdout. For rosunit and rostest, the test is wrapped in an
    external runner. The results from this runner are important if the
    runner itself has a failure.

    @param runner_result: unittest runner result object
    @type  runner_result: _XMLTestResult
    @param junit_results: Parsed JUnit test results
    @type  junit_results: rosunit.junitxml.Result
    """
    # we have two separate result objects, which can be a bit
    # confusing. 'result' counts successful _running_ of tests
    # (i.e. doesn't check for actual test success). The 'r' result
    # object contains results of the actual tests.

    buff = StringIO()

    buff.write("[%s]"%(runner_name)+'-'*71+'\n\n')
    for tc_result in junit_results.test_case_results:
        buff.write(tc_result.description)
    for tc_result in runner_results.failures:
        buff.write("[%s][failed]\n"%tc_result[0]._testMethodName)

    buff.write('\nSUMMARY\n')
    if runner_results.wasSuccessful() and (junit_results.num_errors + junit_results.num_failures) == 0:
        buff.write("\033[32m * RESULT: SUCCESS\033[0m\n")
    else:
        buff.write("\033[1;31m * RESULT: FAIL\033[0m\n")

    # TODO: still some issues with the numbers adding up if tests fail to launch

    # number of errors from the inner tests, plus add in count for tests
    # that didn't run properly ('result' object).
    buff.write(" * TESTS: %s\n"%junit_results.num_tests)
    num_errors = junit_results.num_errors+len(runner_results.errors)
    if num_errors:
        buff.write("\033[1;31m * ERRORS: %s\033[0m\n"%num_errors)
    else:
        buff.write(" * ERRORS: 0\n")
    num_failures = junit_results.num_failures+len(runner_results.failures)
    if num_failures:
        buff.write("\033[1;31m * FAILURES: %s\033[0m\n"%num_failures)
    else:
        buff.write(" * FAILURES: 0\n")
        
    if runner_results.failures:
        buff.write("\nERROR: The following tests failed to run:\n")
        for tc_result in runner_results.failures:
            buff.write(" * " +tc_result[0]._testMethodName + "\n")

    print(buff.getvalue())

def _format_errors(errors):
    formatted = []
    for e in errors:
        if '_testMethodName' in e[0].__dict__:
            formatted.append(e[0]._testMethodName)
        elif 'description' in e[0].__dict__:
            formatted.append('%s: %s\n' % (str(e[0].description), str(e[1])))
        else:
            formatted.append(str(e[0].__dict__))
    return formatted

def print_unittest_summary(result):
    """
    Print summary of python unittest result to stdout
    @param result: test results
    """
    buff = StringIO()
    buff.write("-------------------------------------------------------------\nSUMMARY:\n")
    if result.wasSuccessful():
        buff.write("\033[32m * RESULT: SUCCESS\033[0m\n")
    else:
        buff.write(" * RESULT: FAIL\n")
    buff.write(" * TESTS: %s\n"%result.testsRun)
    buff.write(" * ERRORS: %s [%s]\n"%(len(result.errors), ', '.join(_format_errors(result.errors))))
    buff.write(" * FAILURES: %s [%s]\n"%(len(result.failures), ', '.join(_format_errors(result.failures))))
    print(buff.getvalue())


########NEW FILE########
__FILENAME__ = core
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function

import os
import sys
import logging

import rospkg

from .xmlrunner import XMLTestRunner

XML_OUTPUT_FLAG = '--gtest_output=xml:' #use gtest-compatible flag

def printlog(msg, *args):
    if args:
        msg = msg%args
    print("[ROSUNIT]"+msg)
    
def printlog_bold(msg, *args):
    if args:
        msg = msg%args
    print('\033[1m[ROSUNIT]' + msg + '\033[0m')
    
def printerrlog(msg, *args):
    if args:
        msg = msg%args
    print("[ROSUNIT]"+msg, file=sys.stderr)

# this is a copy of the roslogging utility. it's been moved here as it is a common
# routine for programs using accessing ROS directories
def makedirs_with_parent_perms(p):
    """
    Create the directory using the permissions of the nearest
    (existing) parent directory. This is useful for logging, where a
    root process sometimes has to log in the user's space.
    @param p: directory to create
    @type  p: str
    """    
    p = os.path.abspath(p)
    parent = os.path.dirname(p)
    # recurse upwards, checking to make sure we haven't reached the
    # top
    if not os.path.exists(p) and p and parent != p:
        makedirs_with_parent_perms(parent)
        s = os.stat(parent)
        os.mkdir(p)

        # if perms of new dir don't match, set anew
        s2 = os.stat(p)
        if s.st_uid != s2.st_uid or s.st_gid != s2.st_gid:
            os.chown(p, s.st_uid, s.st_gid)
        if s.st_mode != s2.st_mode:
            os.chmod(p, s.st_mode)    

def xml_results_file(test_pkg, test_name, is_rostest=False):
    """
    @param test_pkg: name of test's package 
    @type  test_pkg: str
    @param test_name str: name of test
    @type  test_name: str
    @param is_rostest: True if the results file is for a rostest-generated unit instance
    @type  is_rostest: bool
    @return: name of xml results file for specified test
    @rtype:  str
    """
    test_dir = os.path.join(rospkg.get_test_results_dir(), test_pkg)
    if not os.path.exists(test_dir):
        try:
            makedirs_with_parent_perms(test_dir)
        except OSError:
            raise IOError("cannot create test results directory [%s]. Please check permissions."%(test_dir))
        
    # #576: strip out chars that would bork the filename
    # this is fairly primitive, but for now just trying to catch some common cases
    for c in ' "\'&$!`/\\':
        if c in test_name:
            test_name = test_name.replace(c, '_')
    if is_rostest:
        return os.path.join(test_dir, 'rostest-%s.xml'%test_name)
    else:
        return os.path.join(test_dir, 'rosunit-%s.xml'%test_name)
    
def rostest_name_from_path(pkg_dir, test_file):
    """
    Derive name of rostest based on file name/path. rostest follows a
    certain convention defined above.
    
    @return: name of test
    @rtype: str
    """
    test_file_abs = os.path.abspath(test_file)
    if test_file_abs.startswith(pkg_dir):
        # compute package-relative path
        test_file = test_file_abs[len(pkg_dir):]
        if test_file[0] == os.sep:
            test_file = test_file[1:]
    outname = test_file.replace(os.sep, '_')
    if '.' in outname:
        outname = outname[:outname.rfind('.')]
    return outname

def create_xml_runner(test_pkg, test_name, results_file=None, is_rostest=False):
    """
    Create the unittest test runner with XML output
    @param test_pkg: package name
    @type  test_pkg: str
    @param test_name: test name
    @type  test_name: str
    @param is_rostest: if True, use naming scheme for rostest itself instead of individual unit test naming
    @type  is_rostest: bool
    """
    test_name = os.path.basename(test_name)
    # determine output xml file name
    if not results_file:
        results_file = xml_results_file(test_pkg, test_name, is_rostest)
    test_dir = os.path.abspath(os.path.dirname(results_file))
    if not os.path.exists(test_dir):
        try:
            makedirs_with_parent_perms(test_dir) #NOTE: this will pass up an error exception if it fails
        except OSError:
            raise IOError("cannot create test results directory [%s]. Please check permissions."%(test_dir))

    elif os.path.isfile(test_dir):
        raise Exception("ERROR: cannot run test suite, file is preventing creation of test dir: %s"%test_dir)
    
    print("[ROSUNIT] Outputting test results to " + results_file)
    outstream = open(results_file, 'w')
    outstream.write('<?xml version="1.0" encoding="utf-8"?>\n')
    return XMLTestRunner(stream=outstream)
    

########NEW FILE########
__FILENAME__ = junitxml
#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$

"""
Library for reading and manipulating Ant JUnit XML result files.
"""

from __future__ import print_function

import os
import sys
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
import string
import codecs
import re

from xml.dom.minidom import parse, parseString
from xml.dom import Node as DomNode

from functools import reduce
import rospkg

class TestInfo(object):
    """
    Common container for 'error' and 'failure' results
    """
    
    def __init__(self, type_, text):
        """
        @param type_: type attribute from xml 
        @type  type_: str
        @param text: text property from xml
        @type  text: str
        """
        self.type = type_
        self.text = text

class TestError(TestInfo):
    """
    'error' result container        
    """
    def xml(self):
        data = '<error type="%s"><![CDATA[%s]]></error>' % (self.type, self.text)
        try:
            data = unicode(data)
        except NameError:
            pass
        return data

class TestFailure(TestInfo):
    """
    'failure' result container        
    """
    def xml(self):
        data = '<failure type="%s"><![CDATA[%s]]></failure>' % (self.type, self.text)
        try:
            data = unicode(data)
        except NameError:
            pass
        return data


class TestCaseResult(object):
    """
    'testcase' result container
    """
    
    def __init__(self, name):
        """
        @param name: name of testcase
        @type  name: str
        """
        self.name = name
        self.failures = []
        self.errors = []
        self.time = 0.0
        self.classname = ''
        
    def _passed(self):
        """
        @return: True if test passed
        @rtype: bool
        """
        return not self.errors and not self.failures
    ## bool: True if test passed without errors or failures
    passed = property(_passed)
    
    def _failure_description(self):
        """
        @return: description of testcase failure
        @rtype: str
        """
        if self.failures:
            tmpl = "[%s][FAILURE]"%self.name
            tmpl = tmpl + '-'*(80-len(tmpl))
            tmpl = tmpl+"\n%s\n"+'-'*80+"\n\n"
            return '\n'.join(tmpl%x.text for x in self.failures)
        return ''

    def _error_description(self):
        """
        @return: description of testcase error
        @rtype: str
        """
        if self.errors:
            tmpl = "[%s][ERROR]"%self.name
            tmpl = tmpl + '-'*(80-len(tmpl))
            tmpl = tmpl+"\n%s\n"+'-'*80+"\n\n"
            return '\n'.join(tmpl%x.text for x in self.errors)
        return ''

    def _description(self):
        """
        @return: description of testcase result
        @rtype: str
        """
        if self.passed:
            return "[%s][passed]\n"%self.name
        else:
            return self._failure_description()+\
                   self._error_description()                   
    ## str: printable description of testcase result
    description = property(_description)
    def add_failure(self, failure):
        """
        @param failure TestFailure
        """
        self.failures.append(failure)

    def add_error(self, error):
        """
        @param failure TestError        
        """
        self.errors.append(error)

    def xml(self):
        data = '  <testcase classname="%s" name="%s" time="%s">\n' % (self.classname, self.name, self.time) + \
               '\n    '.join([f.xml() for f in self.failures]) + \
               '\n    '.join([e.xml() for e in self.errors]) + \
               '  </testcase>'
        try:
            data = unicode(data)
        except NameError:
            pass
        return data
        
class Result(object):
    __slots__ = ['name', 'num_errors', 'num_failures', 'num_tests', \
                 'test_case_results', 'system_out', 'system_err', 'time']
    def __init__(self, name, num_errors=0, num_failures=0, num_tests=0):
        self.name = name
        self.num_errors = num_errors
        self.num_failures = num_failures
        self.num_tests = num_tests
        self.test_case_results = []
        self.system_out = ''
        self.system_err = ''
        self.time = 0.0

    def accumulate(self, r):
        """
        Add results from r to this result
        @param r: results to aggregate with this result
        @type  r: Result
        """
        self.num_errors += r.num_errors
        self.num_failures += r.num_failures
        self.num_tests += r.num_tests
        self.time += r.time
        self.test_case_results.extend(r.test_case_results)
        if r.system_out:
            self.system_out += '\n'+r.system_out
        if r.system_err:
            self.system_err += '\n'+r.system_err

    def add_test_case_result(self, r):
        """
        Add results from a testcase to this result container
        @param r: TestCaseResult
        @type  r: TestCaseResult
        """
        self.test_case_results.append(r)

    def xml(self):
        """
        @return: document as unicode (UTF-8 declared) XML according to Ant JUnit spec
        """
        data = '<?xml version="1.0" encoding="utf-8"?>' + \
               '<testsuite name="%s" tests="%s" errors="%s" failures="%s" time="%s">' % \
               (self.name, self.num_tests, self.num_errors, self.num_failures, self.time) + \
               '\n'.join([tc.xml() for tc in self.test_case_results]) + \
               '  <system-out><![CDATA[%s]]></system-out>' % self.system_out + \
               '  <system-err><![CDATA[%s]]></system-err>' % self.system_err + \
               '</testsuite>'
        try:
            data = unicode(data)
        except NameError:
            pass
        return data

def _text(tag):
    return reduce(lambda x, y: x + y, [c.data for c in tag.childNodes if c.nodeType in [DomNode.TEXT_NODE, DomNode.CDATA_SECTION_NODE]], "").strip()

def _load_suite_results(test_suite_name, test_suite, result):
    nodes = [n for n in test_suite.childNodes \
             if n.nodeType == DomNode.ELEMENT_NODE]
    for node in nodes:
        name = node.tagName
        if name == 'testsuite':
            # for now we flatten this hierarchy
            _load_suite_results(test_suite_name, node, result)
        elif name == 'system-out':
            if _text(node):
                system_out = "[%s] stdout"%test_suite_name + "-"*(71-len(test_suite_name))
                system_out += '\n'+_text(node)
                result.system_out += system_out
        elif name == 'system-err':
            if _text(node):
                system_err = "[%s] stderr"%test_suite_name + "-"*(71-len(test_suite_name))
                system_err += '\n'+_text(node)
                result.system_err += system_err
        elif name == 'testcase':
            name = node.getAttribute('name') or 'unknown'
            classname = node.getAttribute('classname') or 'unknown'

            # mangle the classname for some sense of uniformity
            # between rostest/unittest/gtest
            if '__main__.' in classname:
              classname = classname[classname.find('__main__.')+9:]
            if classname == 'rostest.rostest.RosTest':
              classname = 'rostest'
            elif not classname.startswith(result.name):
              classname = "%s.%s"%(result.name,classname)
              
            time = float(node.getAttribute('time')) or 0.0
            tc_result = TestCaseResult("%s/%s"%(test_suite_name,name))
            tc_result.classname = classname
            tc_result.time = time            
            result.add_test_case_result(tc_result)
            for d in [n for n in node.childNodes \
                      if n.nodeType == DomNode.ELEMENT_NODE]:
                # convert 'message' attributes to text elements to keep
                # python unittest and gtest consistent
                if d.tagName == 'failure':
                    message = d.getAttribute('message') or ''
                    text = _text(d) or message
                    x = TestFailure(d.getAttribute('type') or '', text)
                    tc_result.add_failure(x)
                elif d.tagName == 'error':
                    message = d.getAttribute('message') or ''
                    text = _text(d) or message                    
                    x = TestError(d.getAttribute('type') or '', text)
                    tc_result.add_error(x)

## #603: unit test suites are not good about screening out illegal
## unicode characters. This little recipe I from http://boodebr.org/main/python/all-about-python-and-unicode#UNI_XML
## screens these out
try:
    char = unichr
except NameError:
    char = chr
RE_XML_ILLEGAL = '([%s-%s%s-%s%s-%s%s-%s])' + \
                 '|' + \
                 '([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])'
try:
    RE_XML_ILLEGAL = unicode(RE_XML_ILLEGAL)
except NameError:
    pass
RE_XML_ILLEGAL = RE_XML_ILLEGAL % \
                 (char(0x0000),char(0x0008),char(0x000b),char(0x000c),
                  char(0x000e),char(0x001f),char(0xfffe),char(0xffff),
                  char(0xd800),char(0xdbff),char(0xdc00),char(0xdfff),
                  char(0xd800),char(0xdbff),char(0xdc00),char(0xdfff),
                  char(0xd800),char(0xdbff),char(0xdc00),char(0xdfff))
_safe_xml_regex = re.compile(RE_XML_ILLEGAL)

def _read_file_safe_xml(test_file, write_back_sanitized=True):
    """
    read in file, screen out unsafe unicode characters
    """
    f = None
    try:
        # this is ugly, but the files in question that are problematic
        # do not declare unicode type.
        if not os.path.isfile(test_file):
            raise Exception("test file does not exist")
        try:
            f = codecs.open(test_file, "r", "utf-8" )
            x = f.read()
        except:
            if f is not None:
                f.close()
            f = codecs.open(test_file, "r", "iso8859-1" )
            x = f.read()        

        for match in _safe_xml_regex.finditer(x):
            x = x[:match.start()] + "?" + x[match.end():]
        x = x.encode("utf-8")
        if write_back_sanitized:
            with open(test_file, 'wb') as h:
                h.write(x)
        return x
    finally:
        if f is not None:
            f.close()

def read(test_file, test_name):
    """
    Read in the test_result file
    @param test_file: test file path
    @type  test_file: str
    @param test_name: name of test                    
    @type  test_name: str
    @return: test results
    @rtype: Result
    """
    try:
        xml_str = _read_file_safe_xml(test_file)
        if not xml_str.strip():
            print("WARN: test result file is empty [%s]"%(test_file))
            return Result(test_name, 0, 0, 0)
        test_suites = parseString(xml_str).getElementsByTagName('testsuite')
    except Exception as e:
        print("WARN: cannot read test result file [%s]: %s"%(test_file, str(e)))
        return Result(test_name, 0, 0, 0)
    if not test_suites:
        print("WARN: test result file [%s] contains no results"%(test_file))
        return Result(test_name, 0, 0, 0)

    results = Result(test_name, 0, 0, 0)
    for index, test_suite in enumerate(test_suites):
        # skip test suites which are already covered by a parent test suite
        if index > 0 and test_suite.parentNode in test_suites[0:index]:
            continue

        #test_suite = test_suite[0]
        vals = [test_suite.getAttribute(attr) for attr in ['errors', 'failures', 'tests']]
        vals = [v or 0 for v in vals]
        err, fail, tests = [int(val) for val in vals]

        result = Result(test_name, err, fail, tests)
        result.time = 0.0 if not len(test_suite.getAttribute('time')) else float(test_suite.getAttribute('time'))

        # Create a prefix based on the test result filename. The idea is to
        # disambiguate the case when tests of the same name are provided in
        # different .xml files.  We use the name of the parent directory
        test_file_base = os.path.basename(os.path.dirname(os.path.abspath(test_file)))
        fname = os.path.basename(test_file)
        if fname.startswith('TEST-'):
            fname = fname[5:]
        if fname.endswith('.xml'):
            fname = fname[:-4]
        test_file_base = "%s.%s"%(test_file_base, fname)
        _load_suite_results(test_file_base, test_suite, result)
        results.accumulate(result)
    return results

def read_all(filter_=[]):
    """
    Read in the test_results and aggregate into a single Result object
    @param filter_: list of packages that should be processed
    @type filter_: [str]
    @return: aggregated result
    @rtype: L{Result}
    """
    dir_ = rospkg.get_test_results_dir()
    root_result = Result('ros', 0, 0, 0)
    if not os.path.exists(dir_):
        return root_result
    for d in os.listdir(dir_):
        if filter_ and not d in filter_:
            continue
        subdir = os.path.join(dir_, d)
        if os.path.isdir(subdir):
            for filename in os.listdir(subdir):
                if filename.endswith('.xml'):
                    filename = os.path.join(subdir, filename)
                    result = read(filename, os.path.basename(subdir))
                    root_result.accumulate(result)
    return root_result


def test_failure_junit_xml(test_name, message, stdout=None):
    """
    Generate JUnit XML file for a unary test suite where the test failed
    
    @param test_name: Name of test that failed
    @type  test_name: str
    @param message: failure message
    @type  message: str
    @param stdout: stdout data to include in report
    @type  stdout: str
    """
    if not stdout:
      return """<?xml version="1.0" encoding="UTF-8"?>
<testsuite tests="1" failures="1" time="1" errors="0" name="%s">
  <testcase name="test_ran" status="run" time="1" classname="Results">
  <failure message="%s" type=""/>
  </testcase>
</testsuite>"""%(test_name, message)
    else:
      return """<?xml version="1.0" encoding="UTF-8"?>
<testsuite tests="1" failures="1" time="1" errors="0" name="%s">
  <testcase name="test_ran" status="run" time="1" classname="Results">
  <failure message="%s" type=""/>
  </testcase>
  <system-out><![CDATA[[
%s
]]></system-out>
</testsuite>"""%(test_name, message, stdout)

def test_success_junit_xml(test_name):
    """
    Generate JUnit XML file for a unary test suite where the test succeeded.
    
    @param test_name: Name of test that passed
    @type  test_name: str
    """
    return """<?xml version="1.0" encoding="UTF-8"?>
<testsuite tests="1" failures="0" time="1" errors="0" name="%s">
  <testcase name="test_ran" status="run" time="1" classname="Results">
  </testcase>
</testsuite>"""%(test_name)

def print_summary(junit_results, runner_name='ROSUNIT'):
    """
    Print summary of junitxml results to stdout.
    """
    # we have two separate result objects, which can be a bit
    # confusing. 'result' counts successful _running_ of tests
    # (i.e. doesn't check for actual test success). The 'r' result
    # object contains results of the actual tests.
    
    buff = StringIO()
    buff.write("[%s]"%runner_name+'-'*71+'\n\n')
    for tc_result in junit_results.test_case_results:
        buff.write(tc_result.description)

    buff.write('\nSUMMARY\n')
    if (junit_results.num_errors + junit_results.num_failures) == 0:
        buff.write("\033[32m * RESULT: SUCCESS\033[0m\n")
    else:
        buff.write("\033[1;31m * RESULT: FAIL\033[0m\n")

    # TODO: still some issues with the numbers adding up if tests fail to launch

    # number of errors from the inner tests, plus add in count for tests
    # that didn't run properly ('result' object).
    buff.write(" * TESTS: %s\n"%junit_results.num_tests)
    num_errors = junit_results.num_errors
    if num_errors:
        buff.write("\033[1;31m * ERRORS: %s\033[0m\n"%num_errors)
    else:
        buff.write(" * ERRORS: 0\n")
    num_failures = junit_results.num_failures
    if num_failures:
        buff.write("\033[1;31m * FAILURES: %s\033[0m\n"%num_failures)
    else:
        buff.write(" * FAILURES: 0\n")

    print(buff.getvalue())


########NEW FILE########
__FILENAME__ = pmon
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$

"""
Process monitor
"""

from __future__ import with_statement

import os
import sys
import time
import traceback
try:
    from queue import Empty, Queue
except ImportError:
    from Queue import Empty, Queue
import atexit
from threading import Thread, RLock, Lock

from .core import printlog, printlog_bold, printerrlog

class PmonException(Exception): pass

class FatalProcessLaunch(PmonException):
    """
    Exception to indicate that a process launch has failed in a fatal
    manner (i.e. relaunch is unlikely to succeed)
    """
    pass

# start/shutdown ################################################

_pmons = []
_pmon_counter = 0
_shutting_down = False
def start_process_monitor():
    global _pmon_counter
    if _shutting_down:
        return None
    _pmon_counter += 1
    name = "ProcessMonitor-%s"%_pmon_counter
    process_monitor = ProcessMonitor(name)
    with _shutdown_lock:
        # prevent race condition with pmon_shutdown() being triggered
        # as we are starting a ProcessMonitor (i.e. user hits ctrl-C
        # during startup)
        _pmons.append(process_monitor)
        process_monitor.start()
    return process_monitor

def shutdown_process_monitor(process_monitor):
    """
    @param process_monitor: process monitor to kill
    @type  process_monitor: L{ProcessMonitor}
    @return: True if process_monitor was successfully
    shutdown. False if it could not be shutdown cleanly or if there is
    a problem with process_monitor
    parameter. shutdown_process_monitor() does not throw any exceptions
    as this is shutdown-critical code.
    @rtype: bool
    """
    try:
        if process_monitor is None or process_monitor.is_shutdown:
            return False
        
        process_monitor.shutdown()
        process_monitor.join(20.0)
        if process_monitor.isAlive():
            return False
        else:
            return True
    except Exception as e:
        return False

_shutdown_lock = Lock()
def pmon_shutdown():
    global _pmons
    with _shutdown_lock:
        if not _pmons:
            return
        for p in _pmons:
            shutdown_process_monitor(p)
        del _pmons[:]

atexit.register(pmon_shutdown)

# ##############################################################

class Process(object):
    """
    Basic process representation for L{ProcessMonitor}. Must be subclassed
    to provide actual start()/stop() implementations.
    """

    def __init__(self, package, name, args, env, respawn=False, required=False):
        self.package = package
        self.name = name
        self.args = args
        self.env = env
        self.respawn = respawn
        self.required = required
        self.lock = Lock()
        self.exit_code = None
        # for keeping track of respawning
        self.spawn_count = 0

    def __str__(self):
        return "Process<%s>"%(self.name)

    # NOTE: get_info() is going to have to be sufficient for
    # generating respawn requests, so we must be complete about it
        
    def get_info(self):
        """
        Get all data about this process in dictionary form
        @return: dictionary of all relevant process properties
        @rtype: dict { str: val }
        """
        info = {
            'spawn_count': self.spawn_count,
            'args': self.args,
            'env': self.env,
            'package': self.package,
            'name': self.name,
            'alive': self.is_alive(),
            'respawn': self.respawn,
            'required': self.required,
            }
        if self.exit_code is not None:
            info['exit_code'] = self.exit_code
        return info

    def start(self):
        self.spawn_count += 1

    def is_alive(self):
        return False

    def stop(self, errors=[]):
        """
        Stop the process. Record any significant error messages in the errors parameter
        
        @param errors: error messages. stop() will record messages into this list.
        @type  errors: [str]
        """
        pass

    def get_exit_description(self):
        if self.exit_code is not None:
            if self.exit_code:
                return 'process has died [exit code %s]'%self.exit_code
            else:
                # try not to scare users about process exit
                return 'process has finished cleanly'
        else:
            return 'process has died'

class DeadProcess(Process):
    """
    Container class to maintain information about a process that has died. This
    container allows us to delete the actual Process but still maintain the metadata
    """
    def __init__(self, p):
        super(DeadProcess, self).__init__(p.package, p.name, p.args, p.env, p.respawn)
        self.exit_code = p.exit_code
        self.lock = None
        self.spawn_count = p.spawn_count
        self.info = p.get_info()
    def get_info(self):
        return self.info
    def start(self):
        raise Exception("cannot call start on a dead process!")
    def is_alive(self):
        return False

class ProcessListener(object):
    """
    Listener class for L{ProcessMonitor}
    """
    
    def process_died(self, process_name, exit_code):
        """
        Notifies listener that process has died. This callback only
        occurs for processes that die during normal process monitor
        execution -- processes that are forcibly killed during
        ProcessMonitor shutdown are not reported.
        @param process_name: name of process
        @type  process_name: str
        @param exit_code: exit code of process. If None, it means
        that ProcessMonitor was unable to determine an exit code.
        @type  exit_code: int
        """
        pass
    
class ProcessMonitor(Thread):

    def __init__(self, name="ProcessMonitor"):
        Thread.__init__(self, name=name)
        self.procs = []
        self.plock = RLock()
        self.is_shutdown = False
        self.done = False        
        self.setDaemon(True)
        self.listeners = []
        self.dead_list = []
        # #885: ensure core procs
        self.core_procs = []
        # #642: flag to prevent process monitor exiting prematurely
        self._registrations_complete = False
        
    def add_process_listener(self, l):
        """
        Listener for process events. MUST be called before
        ProcessMonitor is running.See ProcessListener class.
        @param l: listener instance
        @type  l: L{ProcessListener}
        """
        self.listeners.append(l)

    def register(self, p):
        """
        Register process with L{ProcessMonitor}
        @param p: Process
        @type  p: L{Process}
        @raise PmonException: if process with same name is already registered
        """
        e = None
        with self.plock:
            if self.has_process(p.name):
                e = PmonException("cannot add process with duplicate name '%s'"%p.name)
            elif self.is_shutdown:
                e = PmonException("cannot add process [%s] after process monitor has been shut down"%p.name)
            else:
                self.procs.append(p)
        if e:
            raise e

    def register_core_proc(self, p):
        """
        Register core process with ProcessMonitor. Coreprocesses
        have special shutdown semantics. They are killed after all
        other processes, in reverse order in which they are added.
        @param p Process
        @type  p: L{Process}
        @raise PmonException: if process with same name is already registered
        """
        self.register(p)
        self.core_procs.append(p)
        
    def registrations_complete(self):
        """
        Inform the process monitor that registrations are complete.
        After the registrations_complete flag is set, process monitor
        will exit if there are no processes left to monitor.
        """
        self._registrations_complete = True
        
    def unregister(self, p):
        with self.plock:
            self.procs.remove(p)

    def has_process(self, name):
        """
        @return: True if process is still be monitored. If False, process
        has died or was never registered with process
        @rtype: bool
        """
        return len([p for p in self.procs if p.name == name]) > 0

    def get_process(self, name):
        """
        @return: process registered under \a name, or None
        @rtype: L{Process}
        """
        with self.plock:
            v = [p for p in self.procs if p.name == name]
        if v:
            return v[0]

    def kill_process(self, name):
        """
        Kill process that matches name. NOTE: a killed process will
        continue to show up as active until the process monitor thread
        has caught that it has died.
        @param name: Process name
        @type  name: str
        @return: True if a process named name was removed from
        process monitor. A process is considered killed if its stop()
        method was called.
        @rtype: bool
        """
        if not isinstance(name, basestring):
            raise PmonException("kill_process takes in a process name but was given: %s"%name)
        printlog("[%s] kill requested"%name)
        with self.plock:
            p = self.get_process(name)
            if p:
                try:
                    # no need to accumulate errors, so pass in []
                    p.stop([])
                except Exception as e:
                    printerrlog("Exception: %s"%(str(e)))
                return True
            else:
                return False
        
    def shutdown(self):
        """
        Shutdown the process monitor thread
        """
        self.is_shutdown = True
        
    def get_active_names(self):
        """
        @return [str]: list of active process names
        """
        with self.plock:
            retval = [p.name for p in self.procs]
        return retval

    def get_process_names_with_spawn_count(self):
        """
        @return: Two lists, where first
        list of active process names along with the number of times
        that process has been spawned. Second list contains dead process names
        and their spawn count.
        @rtype: [[(str, int),], [(str,int),]]
        """
        with self.plock:
            actives = [(p.name, p.spawn_count) for p in self.procs]
            deads = [(p.name, p.spawn_count) for p in self.dead_list]
            retval = [actives, deads]
        return retval

    def run(self):
        """
        thread routine of the process monitor. 
        """
        try:
            #don't let exceptions bomb thread, interferes with exit
            try:
                self._run()
            except:
                traceback.print_exc()
        finally:
            self._post_run()
            
    def _run(self):
        """
        Internal run loop of ProcessMonitor
        """
        plock = self.plock
        dead = []
        respawn = []
        while not self.is_shutdown:
            with plock: #copy self.procs
                procs = self.procs[:]
            if self.is_shutdown:
                break

            for p in procs:
                try:
                    if not p.is_alive():
                        exit_code_str = p.get_exit_description()
                        if p.respawn:
                            printlog_bold("[%s] %s\nrespawning..."%(p.name, exit_code_str))
                            respawn.append(p)
                        elif p.required:
                            printerrlog('='*80+"REQUIRED process [%s] has died!\n%s\nInitiating shutdown!\n"%(p.name, exit_code_str)+'='*80)
                            self.is_shutdown = True
                        else:
                            if p.exit_code:
                                printerrlog("[%s] %s"%(p.name, exit_code_str))
                            else:
                                printlog_bold("[%s] %s"%(p.name, exit_code_str))
                            dead.append(p)
                            
                        ## no need for lock as we require listeners be
                        ## added before process monitor is launched
                        for l in self.listeners:
                            l.process_died(p.name, p.exit_code)

                except Exception as e:
                    traceback.print_exc()
                    #don't respawn as this is an internal error
                    dead.append(p)
                if self.is_shutdown:
                    break #stop polling
            for d in dead:
                try:
                    self.unregister(d)
                    # stop process, don't accumulate errors
                    d.stop([])

                    # save process data to dead list 
                    with plock:
                        self.dead_list.append(DeadProcess(d))
                except Exception as e:
                    printerrlog("Exception: %s"%(str(e)))
                    
            # dead check is to make sure that ProcessMonitor at least
            # waits until its had at least one process before exiting
            if self._registrations_complete and dead and not self.procs and not respawn:
                printlog("all processes on machine have died, roslaunch will exit")
                self.is_shutdown = True
            del dead[:]
            for r in respawn: 
                try:
                    if self.is_shutdown:
                        break
                    printlog("[%s] restarting process"%r.name)
                    # stop process, don't accumulate errors
                    r.stop([])
                    r.start()
                except:
                    traceback.print_exc()
            del respawn[:]
            time.sleep(0.1) #yield thread
        #moved this to finally block of _post_run
        #self._post_run() #kill all processes

    def _post_run(self):
        # this is already true entering, but go ahead and make sure
        self.is_shutdown = True
        # killall processes on run exit

        q = Queue()
        q.join()
        
        with self.plock:
            # make copy of core_procs for threadsafe usage
            core_procs = self.core_procs[:]

            # enqueue all non-core procs in reverse order for parallel kill
            # #526/885: ignore core procs
            [q.put(p) for p in reversed(self.procs) if not p in core_procs]

        # use 10 workers
        killers = []
        for i in range(10):
            t = _ProcessKiller(q, i)
            killers.append(t)
            t.start()

        # wait for workers to finish
        q.join()
        shutdown_errors = []

        # accumulate all the shutdown errors
        for t in killers:
            shutdown_errors.extend(t.errors)
        del killers[:]
            
        # #526/885: kill core procs last
        # we don't want to parallelize this as the master has to be last
        for p in reversed(core_procs):
            _kill_process(p, shutdown_errors)

        # delete everything except dead_list
        with self.plock:
            del core_procs[:]
            del self.procs[:]
            del self.core_procs[:]
            
        self.done = True

        if shutdown_errors:
            printerrlog("Shutdown errors:\n"+'\n'.join([" * %s"%e for e in shutdown_errors]))

def _kill_process(p, errors):
    """
    Routine for kill Process p with appropriate logging to screen and logfile
    
    @param p: process to kill
    @type  p: Process
    @param errors: list of error messages from killed process
    @type  errors: [str]
    """
    try:
        printlog("[%s] killing on exit"%p.name)
        # we accumulate errors from each process so that we can print these at the end
        p.stop(errors)
    except Exception as e:
        printerrlog("Exception: %s"%(str(e)))
    
class _ProcessKiller(Thread):
    
    def __init__(self, q, i):
        Thread.__init__(self, name="ProcessKiller-%s"%i)
        self.q = q
        self.errors = []
        
    def run(self):
        q = self.q
        while not q.empty():
            try:
                p = q.get(False)
                _kill_process(p, self.errors)
                q.task_done()
            except Empty:
                pass

        
    

########NEW FILE########
__FILENAME__ = pyunit
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$

"""
Wrapper for running Python unittest within rosunit/rostest framework.
"""
from __future__ import with_statement, print_function

import sys

from .core import create_xml_runner, XML_OUTPUT_FLAG
from .baretest import print_unittest_summary

def unitrun(package, test_name, test, sysargs=None, coverage_packages=None):
    """
    Wrapper routine from running python unitttests with
    JUnit-compatible XML output.  This is meant for unittests that do
    not not need a running ROS graph (i.e. offline tests only).

    This enables JUnit-compatible test reporting so that
    test results can be reported to higher-level tools.

    WARNING: unitrun() will trigger a sys.exit() on test failure in
    order to properly exit with an error code. This routine is meant
    to be used as a main() routine, not as a library.
    
    @param package: name of ROS package that is running the test
    @type  package: str
    @param coverage_packages: list of Python package to compute coverage results for. Defaults to package
    @type  coverage_packages: [str]
    @param sysargs: (optional) alternate sys.argv
    @type  sysargs: [str]
    """
    if sysargs is None:
        # lazy-init sys args
        import sys
        sysargs = sys.argv

    import unittest
    
    if coverage_packages is None:
        coverage_packages = [package]
        
    #parse sysargs
    result_file = None
    for arg in sysargs:
        if arg.startswith(XML_OUTPUT_FLAG):
            result_file = arg[len(XML_OUTPUT_FLAG):]
    text_mode = '--text' in sysargs

    coverage_mode = '--cov' in sysargs or '--covhtml' in sysargs
    if coverage_mode:
        start_coverage(coverage_packages)

    # create and run unittest suite with our xmllrunner wrapper
    suite = unittest.TestLoader().loadTestsFromTestCase(test)
    if text_mode:
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    else:
        result = create_xml_runner(package, test_name, result_file).run(suite)
    if coverage_mode:
        cov_html_dir = 'covhtml' if '--covhtml' in sysargs else None
        stop_coverage(coverage_packages, html=cov_html_dir)

    # test over, summarize results and exit appropriately
    print_unittest_summary(result)
    
    if not result.wasSuccessful():
        import sys
        sys.exit(1)

# coverage instance
_cov = None
def start_coverage(packages):
    global _cov
    try:
        import coverage
        try:
            _cov = coverage.coverage()
            # load previous results as we need to accumulate
            _cov.load()
            _cov.start()
        except coverage.CoverageException:
            print("WARNING: you have an older version of python-coverage that is not support. Please update to the version provided by 'easy_install coverage'", file=sys.stderr)
    except ImportError as e:
        print("""WARNING: cannot import python-coverage, coverage tests will not run.
To install coverage, run 'easy_install coverage'""", file=sys.stderr)

def stop_coverage(packages, html=None):
    """
    @param packages: list of packages to generate coverage reports for
    @type  packages: [str]
    @param html: (optional) if not None, directory to generate html report to
    @type  html: str
    """
    if _cov is None:
        return
    import sys, os
    try:
        _cov.stop()
        # accumulate results
        _cov.save()
        
        # - update our own .coverage-modules file list for
        #   coverage-html tool. The reason we read and rewrite instead
        #   of append is that this does a uniqueness check to keep the
        #   file from growing unbounded
        if os.path.exists('.coverage-modules'):
            with open('.coverage-modules','r') as f:
                all_packages = set([x for x in f.read().split('\n') if x.strip()] + packages)
        else:
            all_packages = set(packages)
        with open('.coverage-modules','w') as f:
            f.write('\n'.join(all_packages)+'\n')
            
        try:
            # list of all modules for html report
            all_mods = []

            # iterate over packages to generate per-package console reports
            for package in packages:
                pkg = __import__(package)
                m = [v for v in sys.modules.values() if v and v.__name__.startswith(package)]
                all_mods.extend(m)

                # generate overall report and per module analysis
                _cov.report(m, show_missing=0)
                for mod in m:
                    res = _cov.analysis(mod)
                    print("\n%s:\nMissing lines: %s"%(res[0], res[3]))
                    
            if html:
                
                print("="*80+"\ngenerating html coverage report to %s\n"%html+"="*80)
                _cov.html_report(all_mods, directory=html)
        except ImportError as e:
            print("WARNING: cannot import '%s', will not generate coverage report"%package, file=sys.stderr)
    except ImportError as e:
        print("""WARNING: cannot import python-coverage, coverage tests will not run.
To install coverage, run 'easy_install coverage'""", file=sys.stderr)
    
    

########NEW FILE########
__FILENAME__ = rosunit_main
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id$

from __future__ import with_statement, print_function

import os
import sys
import time
import unittest
import logging

import rospkg

from . import pmon
from . core import xml_results_file, create_xml_runner

from .junitxml import print_summary, Result
from .baretest import BareTestCase, print_runner_summary


_NAME = 'rosunit'

def rosunitmain():
    from optparse import OptionParser
    parser = OptionParser(usage="usage: %prog [options] <file> [test args...]", prog=_NAME)
    parser.add_option("-t", "--text",
                      action="store_true", dest="text_mode", default=False,
                      help="Run with stdout output instead of XML output")
    parser.add_option("--time-limit", metavar="TIME_LIMIT",
                      dest="time_limit", default=60,
                      help="Set time limit for test")
    parser.add_option("--name", metavar="TEST_NAME",
                      dest="test_name", default=None,
                      help="Test name")
    parser.add_option("--package", metavar="PACKAGE_NAME",
                      dest="pkg", default=None,
                      help="Package name (optional)")
    (options, args) = parser.parse_args()

    if len(args) < 1:
        parser.error("You must supply a test file.")

    test_file = args[0]
    
    if options.test_name:
        test_name = options.test_name
    else:
        test_name = os.path.basename(test_file)
        if '.' in test_name:
            test_name = test_name[:test_name.rfind('.')]
    time_limit = float(options.time_limit) if options.time_limit else None

    # If the caller didn't tell us the package name, we'll try to infer it.
    # compute some common names we'll be using to generate test names and files
    pkg = options.pkg
    if not pkg:
        pkg = rospkg.get_package_name(test_file)
    if not pkg:
        print("Error: failed to determine package name for file '%s'; maybe you should supply the --package argument to rosunit?"%(test_file))
        sys.exit(1)

    try:
        runner_result = None
        results = Result('rosunit', 0, 0, 0)

        test_case = BareTestCase(test_file, args[1:], \
                                 retry=0, time_limit=time_limit, \
                                 test_name=test_name, text_mode=options.text_mode, package_name=pkg)
        suite = unittest.TestSuite()
        suite.addTest(test_case)

        if options.text_mode:
            result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
        else:
            results_file = xml_results_file(pkg, test_name, True)
            # the is_rostest really just means "wrapper"
            xml_runner = create_xml_runner(pkg, test_name, \
                                               results_file=results_file, \
                                               is_rostest=True)
            runner_result = xml_runner.run(suite)
    finally:
        pmon.pmon_shutdown()

    # summary is worthless if textMode is on as we cannot scrape .xml results
    results = test_case.results
    if not options.text_mode:
        print_runner_summary(runner_result, results)
    else:
        print("WARNING: overall test result is not accurate when --text is enabled")

    if runner_result is not None and not runner_result.wasSuccessful():
        sys.exit(1)
    elif results.num_errors or results.num_failures:
        sys.exit(2)
    
if __name__ == '__main__':
    rosunitmain()

########NEW FILE########
__FILENAME__ = xmlrunner
"""
XML Test Runner for PyUnit
"""

# Written by Sebastian Rittau <srittau@jroger.in-berlin.de> and placed in
# the Public Domain. With contributions by Paolo Borelli.

from __future__ import print_function

__revision__ = "$Id$"

import os.path
import re
import sys
import time
import traceback
import unittest
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
from xml.sax.saxutils import escape


class _TestInfo(object):

    """Information about a particular test.
    
    Used by _XMLTestResult.
    
    """

    def __init__(self, test, time):
        (self._class, self._method) = test.id().rsplit(".", 1)
        self._time = time
        self._error = None
        self._failure = None

    @staticmethod
    def create_success(test, time):
        """Create a _TestInfo instance for a successful test."""
        return _TestInfo(test, time)

    @staticmethod
    def create_failure(test, time, failure):
        """Create a _TestInfo instance for a failed test."""
        info = _TestInfo(test, time)
        info._failure = failure
        return info

    @staticmethod
    def create_error(test, time, error):
        """Create a _TestInfo instance for an erroneous test."""
        info = _TestInfo(test, time)
        info._error = error
        return info

    def print_report(self, stream):
        """Print information about this test case in XML format to the
        supplied stream.

        """
        stream.write('  <testcase classname="%(class)s" name="%(method)s" time="%(time).4f">' % \
            {
                "class": self._class,
                "method": self._method,
                "time": self._time,
            })
        if self._failure != None:
            self._print_error(stream, 'failure', self._failure)
        if self._error != None:
            self._print_error(stream, 'error', self._error)
        stream.write('</testcase>\n')

    def print_report_text(self, stream):
        #stream.write('  <testcase classname="%(class)s" name="%(method)s" time="%(time).4f">' % \
        #    {
        #        "class": self._class,
        #        "method": self._method,
        #        "time": self._time,
        #    })
        stream.write(self._method)
        if self._failure != None:
            stream.write(' ... FAILURE!\n')
            self._print_error_text(stream, 'failure', self._failure)
        if self._error != None:
            stream.write(' ... ERROR!\n')            
            self._print_error_text(stream, 'error', self._error)
        if self._failure == None and self._error == None:
            stream.write(' ... ok\n')

    def _print_error(self, stream, tagname, error):
        """Print information from a failure or error to the supplied stream."""
        text = escape(str(error[1]))
        stream.write('\n')
        stream.write('    <%s type="%s">%s\n' \
            % (tagname, str(error[0].__name__), text))
        tb_stream = StringIO()
        traceback.print_tb(error[2], None, tb_stream)
        stream.write(escape(tb_stream.getvalue()))
        stream.write('    </%s>\n' % tagname)
        stream.write('  ')

    def _print_error_text(self, stream, tagname, error):
        """Print information from a failure or error to the supplied stream."""
        text = escape(str(error[1]))
        stream.write('%s: %s\n' \
            % (tagname.upper(), text))
        tb_stream = StringIO()
        traceback.print_tb(error[2], None, tb_stream)
        stream.write(escape(tb_stream.getvalue()))
        stream.write('-'*80 + '\n')

class _XMLTestResult(unittest.TestResult):

    """A test result class that stores result as XML.

    Used by XMLTestRunner.

    """

    def __init__(self, classname):
        unittest.TestResult.__init__(self)
        self._test_name = classname
        self._start_time = None
        self._tests = []
        self._error = None
        self._failure = None

    def startTest(self, test):
        unittest.TestResult.startTest(self, test)
        self._error = None
        self._failure = None
        self._start_time = time.time()

    def stopTest(self, test):
        time_taken = time.time() - self._start_time
        unittest.TestResult.stopTest(self, test)
        if self._error:
            info = _TestInfo.create_error(test, time_taken, self._error)
        elif self._failure:
            info = _TestInfo.create_failure(test, time_taken, self._failure)
        else:
            info = _TestInfo.create_success(test, time_taken)
        self._tests.append(info)

    def addError(self, test, err):
        unittest.TestResult.addError(self, test, err)
        self._error = err

    def addFailure(self, test, err):
        unittest.TestResult.addFailure(self, test, err)
        self._failure = err

    def print_report(self, stream, time_taken, out, err):
        """Prints the XML report to the supplied stream.
        
        The time the tests took to perform as well as the captured standard
        output and standard error streams must be passed in.a

        """
        stream.write('<testsuite errors="%(e)d" failures="%(f)d" ' % \
            { "e": len(self.errors), "f": len(self.failures) })
        stream.write('name="%(n)s" tests="%(t)d" time="%(time).3f">\n' % \
            {
                "n": self._test_name,
                "t": self.testsRun,
                "time": time_taken,
            })
        for info in self._tests:
            info.print_report(stream)
        stream.write('  <system-out><![CDATA[%s]]></system-out>\n' % out)
        stream.write('  <system-err><![CDATA[%s]]></system-err>\n' % err)
        stream.write('</testsuite>\n')

    def print_report_text(self, stream, time_taken, out, err):
        """Prints the text report to the supplied stream.
        
        The time the tests took to perform as well as the captured standard
        output and standard error streams must be passed in.a

        """
        #stream.write('<testsuite errors="%(e)d" failures="%(f)d" ' % \
        #    { "e": len(self.errors), "f": len(self.failures) })
        #stream.write('name="%(n)s" tests="%(t)d" time="%(time).3f">\n' % \
        #    {
        #        "n": self._test_name,
        #        "t": self.testsRun,
        #        "time": time_taken,
        #    })
        for info in self._tests:
            info.print_report_text(stream)


class XMLTestRunner(object):

    """A test runner that stores results in XML format compatible with JUnit.

    XMLTestRunner(stream=None) -> XML test runner

    The XML file is written to the supplied stream. If stream is None, the
    results are stored in a file called TEST-<module>.<class>.xml in the
    current working directory (if not overridden with the path property),
    where <module> and <class> are the module and class name of the test class.

    """

    def __init__(self, stream=None):
        self._stream = stream
        self._path = "."

    def run(self, test):
        """Run the given test case or test suite."""
        class_ = test.__class__
        classname = class_.__module__ + "." + class_.__name__
        if self._stream == None:
            filename = "TEST-%s.xml" % classname
            stream = file(os.path.join(self._path, filename), "w")
            stream.write('<?xml version="1.0" encoding="utf-8"?>\n')
        else:
            stream = self._stream

        result = _XMLTestResult(classname)
        start_time = time.time()

        # TODO: Python 2.5: Use the with statement
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()

        try:
            test(result)
            try:
                out_s = sys.stdout.getvalue()
            except AttributeError:
                out_s = ""
            try:
                err_s = sys.stderr.getvalue()
            except AttributeError:
                err_s = ""
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        time_taken = time.time() - start_time
        result.print_report(stream, time_taken, out_s, err_s)

        result.print_report_text(sys.stdout, time_taken, out_s, err_s)
        
        if self._stream == None:
            stream.close()

        return result

    def _set_path(self, path):
        self._path = path

    path = property(lambda self: self._path, _set_path, None,
            """The path where the XML files are stored.
            
            This property is ignored when the XML file is written to a file
            stream.""")


class XMLTestRunnerTest(unittest.TestCase):
    def setUp(self):
        self._stream = StringIO()

    def _try_test_run(self, test_class, expected):

        """Run the test suite against the supplied test class and compare the
        XML result against the expected XML string. Fail if the expected
        string doesn't match the actual string. All time attribute in the
        expected string should have the value "0.000". All error and failure
        messages are reduced to "Foobar".

        """

        runner = XMLTestRunner(self._stream)
        runner.run(unittest.makeSuite(test_class))

        got = self._stream.getvalue()
        # Replace all time="X.YYY" attributes by time="0.000" to enable a
        # simple string comparison.
        got = re.sub(r'time="\d+\.\d+"', 'time="0.000"', got)
        # Likewise, replace all failure and error messages by a simple "Foobar"
        # string.
        got = re.sub(r'(?s)<failure (.*?)>.*?</failure>', r'<failure \1>Foobar</failure>', got)
        got = re.sub(r'(?s)<error (.*?)>.*?</error>', r'<error \1>Foobar</error>', got)

        self.assertEqual(expected, got)

    def test_no_tests(self):
        """Regression test: Check whether a test run without any tests
        matches a previous run.
        
        """
        class TestTest(unittest.TestCase):
            pass
        self._try_test_run(TestTest, """<testsuite errors="0" failures="0" name="unittest.TestSuite" tests="0" time="0.000">
  <system-out><![CDATA[]]></system-out>
  <system-err><![CDATA[]]></system-err>
</testsuite>
""")

    def test_success(self):
        """Regression test: Check whether a test run with a successful test
        matches a previous run.
        
        """
        class TestTest(unittest.TestCase):
            def test_foo(self):
                pass
        self._try_test_run(TestTest, """<testsuite errors="0" failures="0" name="unittest.TestSuite" tests="1" time="0.000">
  <testcase classname="__main__.TestTest" name="test_foo" time="0.000"></testcase>
  <system-out><![CDATA[]]></system-out>
  <system-err><![CDATA[]]></system-err>
</testsuite>
""")

    def test_failure(self):
        """Regression test: Check whether a test run with a failing test
        matches a previous run.
        
        """
        class TestTest(unittest.TestCase):
            def test_foo(self):
                self.assert_(False)
        self._try_test_run(TestTest, """<testsuite errors="0" failures="1" name="unittest.TestSuite" tests="1" time="0.000">
  <testcase classname="__main__.TestTest" name="test_foo" time="0.000">
    <failure type="exceptions.AssertionError">Foobar</failure>
  </testcase>
  <system-out><![CDATA[]]></system-out>
  <system-err><![CDATA[]]></system-err>
</testsuite>
""")

    def test_error(self):
        """Regression test: Check whether a test run with a erroneous test
        matches a previous run.
        
        """
        class TestTest(unittest.TestCase):
            def test_foo(self):
                raise IndexError()
        self._try_test_run(TestTest, """<testsuite errors="1" failures="0" name="unittest.TestSuite" tests="1" time="0.000">
  <testcase classname="__main__.TestTest" name="test_foo" time="0.000">
    <error type="exceptions.IndexError">Foobar</error>
  </testcase>
  <system-out><![CDATA[]]></system-out>
  <system-err><![CDATA[]]></system-err>
</testsuite>
""")

    def test_stdout_capture(self):
        """Regression test: Check whether a test run with output to stdout
        matches a previous run.
        
        """
        class TestTest(unittest.TestCase):
            def test_foo(self):
                print("Test")
        self._try_test_run(TestTest, """<testsuite errors="0" failures="0" name="unittest.TestSuite" tests="1" time="0.000">
  <testcase classname="__main__.TestTest" name="test_foo" time="0.000"></testcase>
  <system-out><![CDATA[Test
]]></system-out>
  <system-err><![CDATA[]]></system-err>
</testsuite>
""")

    def test_stderr_capture(self):
        """Regression test: Check whether a test run with output to stderr
        matches a previous run.
        
        """
        class TestTest(unittest.TestCase):
            def test_foo(self):
                print("Test", file=sys.stderr)
        self._try_test_run(TestTest, """<testsuite errors="0" failures="0" name="unittest.TestSuite" tests="1" time="0.000">
  <testcase classname="__main__.TestTest" name="test_foo" time="0.000"></testcase>
  <system-out><![CDATA[]]></system-out>
  <system-err><![CDATA[Test
]]></system-err>
</testsuite>
""")

    class NullStream(object):
        """A file-like object that discards everything written to it."""
        def write(self, buffer):
            pass

    def test_unittests_changing_stdout(self):
        """Check whether the XMLTestRunner recovers gracefully from unit tests
        that change stdout, but don't change it back properly.

        """
        class TestTest(unittest.TestCase):
            def test_foo(self):
                sys.stdout = XMLTestRunnerTest.NullStream()

        runner = XMLTestRunner(self._stream)
        runner.run(unittest.makeSuite(TestTest))

    def test_unittests_changing_stderr(self):
        """Check whether the XMLTestRunner recovers gracefully from unit tests
        that change stderr, but don't change it back properly.

        """
        class TestTest(unittest.TestCase):
            def test_foo(self):
                sys.stderr = XMLTestRunnerTest.NullStream()

        runner = XMLTestRunner(self._stream)
        runner.run(unittest.makeSuite(TestTest))


class XMLTestProgram(unittest.TestProgram):
    def runTests(self):
        if self.testRunner is None:
            self.testRunner = XMLTestRunner()
        unittest.TestProgram.runTests(self)

main = XMLTestProgram


if __name__ == "__main__":
    main(module=None)

########NEW FILE########
__FILENAME__ = test_junitxml
#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Revision $Id: $

import os
import io
import sys
import unittest
import tempfile
import shutil

junitxml = None

## Basic test of xmlresult functionality of reading gtest xml files and
## summarizing their results into a new file.
class MockResult():
    def __init__(self, directory, filename, suites = [], noSuitesRoot = False):
        self.filename = os.path.join(directory, filename)
        self.suites = suites
        # whether to suppress <testsuites> root node
        self.noSuitesRoot = noSuitesRoot

class MockSuite():
    def __init__(self, cases, name, tests = 0, errors = 0, fail = 0, time = 1):
        self.cases = cases
        self.tests = tests
        self.time = time
        self.fail = fail
        self.errors = errors
        self.name = name

        
class MockCase():
    def __init__(self, name, errorList = [], classname="", time = 1):
        self.classname = classname
        self.name = name
        self.time = time
        self.errorList = errorList 

class MockErrorType(Exception):
    def __init__(self, value, etype = ''):
        self.value = value
        self.__name__ = value
        self.type = etype
        
def _writeMockResultFile(result):
    "writes a test result as a gtest compatible test runner would do"
    with open(result.filename, 'w') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        if len(result.suites) > 1 or result.noSuitesRoot == False:
            f.write('<testsuites>\n')
        for suite in result.suites:
            f.write('<testsuite tests="'+str(suite.tests)+'" failures="'+str(suite.fail)+'" time="'+str(suite.time)+'" errors="'+str(suite.errors)+'" name="'+suite.name+'">\n')
            for case in suite.cases:
                f.write('<testcase name="'+case.name+'" status="run" time="'+str(case.time)+'" classname="'+case.classname+'">\n')
                for error in case.errorList:
                    f.write('<failure message="'+error.value+'" type="'+error.value+'"/>\n')
                f.write('</testcase>\n')
            f.write('</testsuite>\n')
        if len(result.suites) > 1 or result.noSuitesRoot == False:
            f.write('</testsuites>\n')


class XmlResultTestRead(unittest.TestCase):

    def setUp(self):
        # lazy-import to get coverage
        global junitxml
        if junitxml is None:
            import rosunit.junitxml
            junitxml = rosunit.junitxml
            
        self.directory = tempfile.mkdtemp()

        # setting up mock results as dict so results can be checked individually
        self.mockresults={
            "empty":      MockResult(self.directory, "empty.xml", []),
            "emptysuite": MockResult(self.directory, "emptysuite.xml", [MockSuite([], "emptySuite", 0, 0, 0, 0)]),
            "succ1":      MockResult(self.directory, "succ1.xml", [MockSuite([MockCase("succCase")],"succ1suite", 1, 0, 0, 1)]),
            "err1":       MockResult(self.directory, "err1.xml",  [MockSuite([MockCase("errCase")],"err1suite", 1, 1, 0, 1)]),
            "fail1":      MockResult(self.directory, "fail1.xml", [MockSuite([MockCase("failCase")],"fail1suite", 1, 0, 1, 1)]),
            "noroot":     MockResult(self.directory, "succ1.xml", [MockSuite([MockCase("succCase")],"succ1suite", 1, 0, 0, 1)], noSuitesRoot = True),
            "multicase":  MockResult(self.directory,
                                     "multicase.xml",
                                     [MockSuite([MockCase("succCase"),
                                                 MockCase("errCase"),
                                                 MockCase("failCase")],
                                                "succ1suite", 3, 1, 1, time = 3)]),
            "multisuite": MockResult(self.directory,
                                     "multisuite.xml",
                                     [MockSuite([MockCase("succCase")],"succ1suite", 1, 0, 0, 1),
                                      MockSuite([MockCase("errCase")],"err1suite", 1, 1, 0, 1),
                                      MockSuite([MockCase("failCase")],"fail1suite", 1, 0, 1, 1)])
            }
        
        
        for name, result in self.mockresults.items():
            _writeMockResultFile(result)

    def tearDown(self):
        shutil.rmtree(self.directory)
        #pass

    def testReadNoSuites(self):
        result = junitxml.read(self.mockresults["empty"].filename, "fooname")
        self.assert_(result is not None)
        self.assertEquals(0.0, result.time)
        self.assertEquals(0, result.num_tests)
        self.assertEquals(0, result.num_errors)
        self.assertEquals(0, result.num_failures)

    def testReadEmptySuite(self):
        result = junitxml.read(self.mockresults["emptysuite"].filename, "fooname")
        self.assert_(result is not None)
        self.assertEquals(0.0, result.time)
        self.assertEquals(0, result.num_tests)
        self.assertEquals(0, result.num_errors)
        self.assertEquals(0, result.num_failures)
        
    def testReadSuccess(self):
        result = junitxml.read(self.mockresults["succ1"].filename, "fooname")
        self.assert_(result is not None)
        self.assertEquals(1.0, result.time)
        self.assertEquals(1, result.num_tests)
        self.assertEquals(0, result.num_errors)
        self.assertEquals(0, result.num_failures)

    def testReadError(self):
        result = junitxml.read(self.mockresults["err1"].filename, "fooname")
        self.assert_(result is not None)
        self.assertEquals(1.0, result.time)
        self.assertEquals(1, result.num_tests)
        self.assertEquals(1, result.num_errors)
        self.assertEquals(0, result.num_failures)

    def testReadFail(self):
        result = junitxml.read(self.mockresults["fail1"].filename, "fooname")
        self.assert_(result is not None)
        self.assertEquals(1.0, result.time)
        self.assertEquals(1, result.num_tests)
        self.assertEquals(0, result.num_errors)
        self.assertEquals(1, result.num_failures)

    def testReadMulticase(self):
        result = junitxml.read(self.mockresults["multicase"].filename, "fooname")
        self.assert_(result is not None)
        self.assertEquals(3.0, result.time)
        self.assertEquals(3, result.num_tests)
        self.assertEquals(1, result.num_errors)
        self.assertEquals(1, result.num_failures)

    def testReadMultisuite(self):
        result = junitxml.read(self.mockresults["multisuite"].filename, "fooname")
        self.assert_(result is not None)
        self.assertEquals(3.0, result.time)
        self.assertEquals(3, result.num_tests)
        self.assertEquals(1, result.num_errors)
        self.assertEquals(1, result.num_failures)

########NEW FILE########
