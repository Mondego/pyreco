__FILENAME__ = config
'''
Global configuration

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Thibault BRONCHAIN
'''

from ConfigParser import SafeConfigParser

from pysa.tools import *
from pysa.exception import *


# define who is a file
FILE_CLASS      = ['keys', 'repos', 'files']
# order
ORDER_LIST = [
    'hosts',
    'mounts',
    'groups',
    'users',
    'dirs',
    'keys',
    'repos',
    'packages',
    'files',
    'crons',
    'sources',
    'services',
    ]
# null objects (avoid 0)
NULL            = ['', {}, [], None]
# build-ins
VOID_EQ         = '_'
ACTION_ID       = '_'
MAIN_SECTION    = '_'
SINGLE_SEC      = '__'

# configuration class
class Config():

    # default values
    c = {
        'files' : {
            'path' : '/etc:/root/.ssh'
            },
        'keys' : {
            'path' : 'root/.ssh'
            },
        'hosts' : {
            'path' : '/etc/hosts'
            },
        'managers' : {
            '_autoadd' : True,
            'pear' : 'php-pear',
            'pecl' : 'php-pear',
            'pip'  : 'python-pip',
            'npm'  : 'npm',
            'gem'  : 'rubygems',
            },
        }
    files_path = c['files']['path']
    scan_host = c['hosts']['path']
    key_path = c['keys']['path']
    managers_eq = c['managers']
    platform = None

    # edit default values if config file
    def __init__(self, path=None):
        if not path: return
        self.__filename = path
        self.__parse_config()

    # parse config file
    @GeneralException
    def __parse_config(self):
        parser = SafeConfigParser()
        parser.read(self.__filename)
        for name in parser.sections():
            config.c.setdefault(name, {})
            for key, value in parser.items(name):
                if   value == "True" : value = True
                elif value == "False": value = False
                config.c[name][key] = value

########NEW FILE########
__FILENAME__ = dependencies
'''
List dependencies for all resources

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Thibault BRONCHAIN
'''


import re
import copy

from pysa.tools import *
from pysa.config import *
from pysa.exception import *


SCM_EQ = {
    'git' : ['git', 'git-all'],
    'svn' : ['subversion'],
    'hg'  : ['mercurial'],
}

SELF_ORDER_EQ = {
    'dirs'          : 'path',
    'sources'       : 'path',
    'mounts'        : 'name',
    }

PRIOR = ['sources']

BASED_ON_FIELD      = "BASED_ON_FIELD"
SELF_ORDER          = "SELF_ORDER"
GET_MOUNT_FROM_PATH = "GET_MOUNT_FROM_PATH"
GET_BASE_PATH       = "GET_BASE_PATH"
GET_PKG_FROM_SCM    = "GET_PKG_FROM_SCM"
PACKAGE_MANAGER     = "PACKAGE_MANAGER"


class Dependencies:
    def __init__(self, module):
        exec "from %s.converter import SECTION_CALL_EQ"%module
        exec "from %s.objects import *"%module
        self.__obj_maker = OBJ_MAKER
        self.__deps = DEPENDENCIES
        self.__calls = SECTION_CALL_EQ
        self.__handler = {
            BASED_ON_FIELD      : self.__based_on_field,
            SELF_ORDER          : self.__self_order,
            GET_MOUNT_FROM_PATH : self.__get_mount_from_path,
            GET_BASE_PATH       : self.__get_base_path,
            GET_PKG_FROM_SCM    : self.__get_pkg_from_scm,
            PACKAGE_MANAGER     : self.__package_manager,
            }
        self.__data = None
        self.__add_obj = {}

    @GeneralException
    def run(self, data):
        self.__data = copy.deepcopy(data)
        Tools.l(INFO, "running dependency cycle generation", 'run', self)
        for c in self.__data:
            if ((c not in self.__deps)
                or (c not in self.__calls)): continue
            for obj_name in self.__data[c]:
                obj = self.__data[c][obj_name]
                for dep_name in PRIOR:
                    if ((dep_name not in self.__data)
                        or (dep_name not in self.__calls)): continue
                    elif dep_name in self.__deps[c]:
                        self.__parse_dep(c, obj_name, obj, dep_name)
                for dep_name in self.__deps[c]:
                    if ((dep_name not in self.__data)
                        or (dep_name not in self.__calls)
                        or (dep_name in PRIOR)): continue
                    else: self.__parse_dep(c, obj_name, obj, dep_name)
        if self.__add_obj: self.__data = Tools.dict_merging(self.__add_obj, self.__data)
        Tools.l(INFO, "dependency cycle generated", 'run', self)
        return self.__data

    @GeneralException
    def __parse_dep(self, c, obj_name, obj, dep_name):
        dep = self.__deps[c][dep_name]
        if type(dep) is str:
            obj['require'] = Tools.dict_merging(obj.get('require'), {
                    dep : [dep_name]
                    })
        elif type(dep) is list:
            res = self.__handler[dep[0]](obj, dep_name, dep[1])
            if res:
                section_dep = self.__calls[dep_name]
                if type(self.__calls[dep_name]) is dict:
                    target_obj = (res[0] if type(res) is list else res)
                    tmp_data = (Tools.dict_merging(self.__add_obj, self.__data) if self.__add_obj else self.__data)
                    section_obj = tmp_data[dep_name].get(target_obj)
                    if not section_obj:
                        Tools.l(ERR, "Target object missing %s.%s"%(dep_name,target_obj), 'parse_dep', self)
                        return
                    section_key = section_obj.get(self.__calls[dep_name]['key'])
                    if not section_key:
                        Tools.l(ERR, "Section key missing for %s"%(dep_name), 'parse_dep', self)
                        return
                    section_dep = self.__calls[dep_name].get(section_key)
                    if not section_dep:
                        Tools.l(ERR, "Wrong section key %s[%s]"%(dep_name,section_key), 'parse_dep', self)
                        return
                obj['require'] = Tools.dict_merging(obj.get('require'), {
                        section_dep[len(ACTION_ID):] : res
                        })

    @GeneralException
    def __self_order(self, object, gclass, args):
        ref = object.get(args['field'])
        data = self.__data[gclass]
        if not data: return None
        res = None
        for key in sorted(data, key=lambda x: data[x][args['field']]):
            name = data[key][args['field']]
            if re.match(name, ref) and (ref != name):
                res = key
        if gclass == 'sources' and self.__data.get('dirs') and res:
            dirs = dict(self.__data['dirs'].items())
            for dir in dirs:
                comp = Tools.path_basename(ref)
                if dirs[dir]['path'] == comp:
                    self.__data['dirs'].pop(dir)
        return res

    @GeneralException
    def __get_mount_from_path(self, object, gclass, args):
        path = object.get(args['field'])
        mounts = self.__data['mounts']
        if not mounts: return None
        res = None
        for key in sorted(mounts, key=lambda x: mounts[x]['name']):
            name = mounts[key]['name']
            if re.match(name, path):
                res = key
        return res

    @GeneralException
    def __get_pkg_from_scm(self, object, gclass, args):
        scm = object.get(args['field'])
        return (SCM_EQ.get(scm) if scm else None)

    @GeneralException
    def __get_base_path(self, object, gclass, args):
        path = object.get(args['field'])
        return (Tools.path_basename(path) if path else None)

    @GeneralException
    def __based_on_field(self, object, gclass, args):
        if not args.get('field') or not args.get('key'):
            return []
        res = []
        v_field = (self.__handler[args['field'][0]](object, gclass, args['field'][1])
                   if type(args['field']) is list
                   else object.get(args['field']))
        if v_field:
            for obj_name in self.__data[gclass]:
                v_key = (args['key'][0](object, gclass, obj_name, args['key'][1])
                         if type(args['key']) is list
                         else self.__data[gclass][obj_name].get(args['key']))
                if (((type(v_field) is list) and (v_key in v_field))
                    or ((type(v_key) is list) and (v_field in v_key))
                    or (v_key == v_field)):
                    res.append(obj_name)
        return res

    @GeneralException
    def __package_manager(self, object, gclass, args):
        if not args.get('field'): return []
        provider = object.get(args['field'])
        managers = Config.managers_eq
        platform = Config.platform
        if provider and platform and managers and (provider in managers):
            package = managers[provider]
            if package not in self.__data['packages'] and managers['_autoadd']:
                self.__add_obj.setdefault(gclass, {})
                self.__add_obj[gclass][package] = self.__obj_maker['manager'](package, platform)
                return [package]
            elif package in self.__data['packages']:
                return [package]
        return []

########NEW FILE########
__FILENAME__ = exception
'''
Exception handler

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Thibault BRONCHAIN
'''

import logging

class ScannerException(Exception): pass

# Decorator
def GeneralException(func):
    def __action_with_decorator(self, *args, **kwargs):
        try:
            class_name = self.__class__.__name__
            func_name = func.__name__
            return func(self, *args, **kwargs)
        except Exception, e:
            logging.error("%s.%s() error: %s" % (class_name, func_name, str(e)))
            raise ScannerException, e
    return __action_with_decorator

########NEW FILE########
__FILENAME__ = filter
'''
Apply user filters

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Thibault BRONCHAIN
'''

from pysa.tools import *
from pysa.exception import *


# filter actions
class Filter():
    def __init__(self, filters):
        self.f = filters

    # preprocessing on packages section
    @GeneralException
    def update_package(self, package, pkg_name, update):
        Tools.l(INFO, "selection update packages", 'update_package', self)
        if (not self.f) or (not self.f.get('update')):
            return package
        mode = (self.f['update']['_update'] if self.f['update'].get('_update') else False)
        excp = self.f['update'].get('except')
        if self.exception_filter(mode, excp, pkg_name, ["*", ".*"]):
            package['version'] = update
        return package

    # item replacement
    @GeneralException
    def item_replace(self, gclass, key, val, name, eq = None):
        if not self.f:
            return val
        global1 = self.f.get('replace')
        global2 = (global1.get(gclass) if global1 else None)
        section = (global2.get(key) if global2 else None)

        replacelist = Tools.dict_merging(Tools.dict_merging(global1, global2), section)
        if not replacelist:
            return val

        mode = (replacelist.pop('_replaceall') if replacelist.get('_replaceall') != None else True)
        excp = (replacelist.pop('_except') if replacelist.get('_except') != None else None)

        replacelist = Tools.dict_cleaner(replacelist)
        if not replacelist:
            return val

        if (excp == None
            or self.exception_filter(mode, excp, name, eq)):
            for i in replacelist:
                c = val
                for data in replacelist[i]:
                    if (type(val) != list) and (type(val) != dict):
                        val = re.sub("%s" % (data),
                                     "%s" % (i),
                                     "%s" % (val))
                if c != val:
                    Tools.l(INFO,
                            "values updated for item %s in section %s"
                            % (name, key),
                            'item_replace',
                            self)
        return val

    # apply filter, replace: ["old", "new"]
    @GeneralException
    def exception_filter(self, mode, exceptions, value, exprep = None):
        if (exceptions == None and mode == True):
            return True
        elif (exceptions == None and mode == False):
            return False
        fl = False
        for name in exceptions:
            name = "%s$" % (name)
            if re.match((name.replace(exprep[0], exprep[1]) if exprep else name), value):
                fl = True
                break
        if (((mode == True) and (fl == False))
            or ((mode == False) and (fl == True))):
            return True
        return False

########NEW FILE########
__FILENAME__ = parser
'''
Apply user filters

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Thibault BRONCHAIN
'''

from ConfigParser import SafeConfigParser

from pysa.tools import *
from pysa.exception import *


class ParserException(Exception): pass

filters_split = ['discard', 'addition']
filters_req = {
    'replace': {
        '_replaceall': [True, False]
        },
    'update': {
        '_update': [True, False]
        }
}

global_filters = {
    'discard': {
        'file' : {
            'path' : [
                '/etc/fstab',
                '/etc/group',
                '/etc/gshadow-',
                '/etc/hosts',
                '/etc/passwd',
                '/etc/passwd-',
                '/etc/shadow',
                '/etc/shadow-',
                ]
            }
        }
}


# filters parser
class FParser():
    def __init__(self, filename):
        self.__filename = Tools.file_exists(filename)

    # action
    @GeneralException
    def run(self):
        if not self.__filename:
            return global_filters
        return self.__parse_filters()

    # check required fields
    @GeneralException
    def __parse_req(self, sec, basename):
        if basename in filters_req:
            for req in filters_req[basename]:
                if sec.get(req) == None:
                    return False
                elif filters_req[basename][req] == None:
                    continue
                elif sec[req] not in filters_req[basename][req]:
                    return False
        return True

    # values parsing
    @GeneralException
    def __parse_value(self, sec, key, value):
        if value == "true" or value == "True":
            sec[key] = True
        elif value == "false" or value == "False":
            sec[key] = False
        elif re.search(",", value):
            sec[key] = re.split("\s*,\s*", value)
        else:
            sec[key] = [value]
        return sec

    # parse sections
    @GeneralException
    def __parse_loop(self, parser, sec, name, refname=None):
        # define referer name
        if not refname:
            refname = name

        # get subsections
        keys = [refname]
        if re.search("\.", refname):
            keys = re.split("\.", refname)
        basename = keys[0]

        # create subsections
        curname = refname
        cursec = sec
        for key in keys:
            if cursec.get(key) == None:
                cursec[key] = {}
            cursec = cursec[key]

        # content parsing
        for key, value in parser.items(name):
            if key == '_contentrefer':
                if value == name:
                    raise ParserException, ("filter file error on section %s" % refname)
                return self.__parse_loop(parser, sec, value, name)
            elif re.search("\.", key) and ((name in filters_split) or (basename in filters_split)):
                skey = re.split("\.", key)
                if cursec.get(skey[0]) == None:
                    cursec[skey[0]] = {}
                cursec[skey[0]] = self.__parse_value(cursec[skey[0]], skey[1], value)
            else:
                cursec = self.__parse_value(cursec, key, value)
        # check required fields
        if (self.__parse_req(cursec, basename) == False):
            raise ParserException, ("filter file error on section %s" % refname)
        return sec

    # parse filters file
    @GeneralException
    def __parse_filters(self):
        parser = SafeConfigParser()
        parser.read(self.__filename)
        sec = {}
        for name in parser.sections():
            sec = self.__parse_loop(parser, sec, name)
        return Tools.dict_merging(global_filters, sec)

########NEW FILE########
__FILENAME__ = madeira
'''
Export output to Madeira account

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Thibault BRONCHAIN
'''

from pysa.exception import *
from pysa.tools import *

# TODO
# export data to madeira account
class Madeira():
    def __init__(self, user, user_id, output, module):
        self.__user = user
        self.__user_id = user_id
        self.__output = output
        self.__module = module

    # send data to Madeira account
    def send(self):
        Tools.l(ERR, "ABORTING: not yet implemented", func.__name__, self)

########NEW FILE########
__FILENAME__ = output
'''
Output container

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Thibault BRONCHAIN
'''

from pysa.exception import *
from pysa.config import *

# output container
class Output():
    def __init__(self):
        self.main = ''
        self.c = {}

    @GeneralException
    def add_dict(self, output, default = ''):
        self.c[output] = default

    @GeneralException
    def add(self, output, content):
        if output:
            self.c[output] = self.c.setdefault(output, '')
            self.c[output] += content
        else:
            self.main += content

    @GeneralException
    def dump(self, manifest_name=None):
        return (self.c[manifest_name] if manifest_name else self.main)

    @GeneralException
    def list(self):
        l = ([''] if self.main else [])
        for seq in ORDER_LIST:
            if seq in self.c:
                l.append(seq)
        return l

    @GeneralException
    def mod(self, content, output=None):
        if output:
            self.c[output] = content
        else:
            self.main = content

########NEW FILE########
__FILENAME__ = preprocessing
'''
Data preprocessing before modules

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Thibault BRONCHAIN
'''

from pysa.tools import *
from pysa.exception import *
from pysa.config import FILE_CLASS, ORDER_LIST

from pysa.dependencies import Dependencies

import copy

FILE_IDENT = FILE_CLASS + [
    'sources',
    ]

# preprocesser
class Preprocessing():
    def __init__(self, module):
        exec "from %s.objects import *"%module
        self.__obj_maker = OBJ_MAKER
        self.__cmlabel = CMLABEL
        self.__data = None
        self.__deps = Dependencies(module)

    # action
    @GeneralException
    def run(self, data):
        self.__data = copy.deepcopy(data)
        if self.__data:
            if self.__obj_maker.get('objkey'):
                self.__keys_mod()
            self.__prepross_files()
            self.__data = self.__deps.run(self.__data)
        return self.__data

    # create unique ids for salt
    @GeneralException
    def __keys_mod(self):
        new_data = {}
        for c in self.__data:
            if c not in ORDER_LIST: continue
            new_data[c] = {}
            for obj in self.__data[c]:
                key = self.__obj_maker['objkey'](c,obj)
                new_data[c][key] = self.__data[c][obj]
        self.__data = new_data

    # preprocessing on files section
    @GeneralException
    def __prepross_files(self):
        Tools.l(INFO, "preprocessing files", 'prepross_files', self)
        dds = self.__files_iter(self.__file_directory, FILE_IDENT)
        for file_item in dds:
            self.__data['dirs'] = Tools.s_dict_merging(self.__data.get('dirs'), dds[file_item])
        self.__files_iter(self.__file_item_removal, ['dirs']+FILE_CLASS)
        Tools.l(INFO, "preprocessing files done", 'prepross_files', self)

    # create config files directory
    @GeneralException
    def __file_directory(self, container, file_item, files, file, files_l):
        if container.get(file_item) == None:
            container[file_item] = {}
        fp = files[file]['path']
        drs = Tools.get_recurse_path(os.path.dirname(fp))
        for dr in drs:
            if (dr == '/') or (("-%s"%dr) in container[file_item]):
                continue
            container[file_item]["-%s"%dr] = self.__obj_maker['file'](dr)
        return container

    # remove items
    @GeneralException
    def __file_item_removal(self, container, file_item, files, file, files_l):
        r_files_l = files_l[:]
        r_files_l.reverse()
        for consumed in r_files_l:
            if consumed == file_item:
                break
            elif self.__data.get(consumed):
                flag = None
                for f in self.__data[consumed]:
                    path = self.__data[consumed][f]['path']
                    if path == files[file]['path']:
                        flag = f
                        break
                if flag:
                    self.__data[consumed].pop(flag)
        return container

    # iterate over files
    @GeneralException
    def __files_iter(self, action, files_l):
        container = {}
        for file_item in files_l:
            files = (dict(self.__data[file_item].items()) if self.__data.get(file_item) else {})
            for file in files:
                container = action(container, file_item, files, file, files_l)
        return container

########NEW FILE########
__FILENAME__ = build
'''
Generate puppet scripts

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Thibault BRONCHAIN
'''

import re

from pysa.exception import *
from pysa.config import *
from pysa.tools import *
from pysa.output import Output

from pysa.puppet.converter import GLOBAL_SEC_EQ

# define quoted variables
QUOTED_AVOIDED_KEYS = ['content', 'before']
QUOTED_FORCED_KEYS = ['checksum', 'name', 'group', 'owner']
QUOTED_FORCED_CONTENT = ['\W', '\d']

# puppet generation class
class PuppetBuild():
    def __init__(self, input_dict, output_path, module_name):
        self.__quoted_regex = "%s" % ('|'.join(QUOTED_FORCED_CONTENT))
        self.__module_name = module_name
        self.__input_dict = input_dict
        self.__output_container = Output()
        self.__output_path = output_path+'/'+self.__module_name
        self.__curent_manifest = ''

    # main function
    @GeneralException
    def run(self):
        Tools.l(INFO, "running generation engine", 'run', self)
        self.__generate(self.__input_dict)
        self.__create_init_file()
        self.dump_in_files()
        Tools.l(INFO, "generation complete", 'run', self)
        return True

    # print the puppet files
    @GeneralException
    def dump(self):
        for manifest_name in self.__output_container.list():
            manifest_fname = (manifest_name if manifest_name else 'init')
            print "%s:\n%s\n\n" % (manifest_fname,
                                   self.__output_container.dump(manifest_name))

    # dump puppet file in variable
    @GeneralException
    def dump_in_var(self, data=''):
        for manifest_name in self.__output_container.list():
            manifest_fname = (manifest_name if manifest_name else 'init')
            data += ("%s:\n%s\n\n" % (manifest_fname,
                                      self.__output_container.dump(manifest_name)))
        return data

    # dump the puppet files into the right files
    @GeneralException
    def dump_in_files(self):
        for manifest_name in self.__output_container.list():
            manifest_fname = (manifest_name if manifest_name else 'init')
            Tools.write_in_file(self.__output_path+'/manifests/'+manifest_fname+'.pp',
                                self.__output_container.dump(manifest_name))

    # init file generation
    @GeneralException
    def __create_init_file(self):
        includes = ''
        for manifest_name in self.__output_container.list():
            if not manifest_name: continue
            includes += "include %s\n" % (manifest_name)
        content = ''
        for line in re.split('\n',
                             self.__output_container.dump()+'\n'+includes):
            if not line: continue
            content += re.sub(r'^', r'\n\t', line)
        self.__output_container.mod("class %s {\n%s\n}\n" % (self.__module_name, content))

    # particular case for the single instructions
    @GeneralException
    def __single_instruction(self, parent, sections, section_name, tab):
        if not parent:
            return tab
        for content in sections[section_name]:
            if section_name == GLOBAL_SEC_EQ['require']:
                if content not in parent: continue
            self.__output_container.add(self.__curent_manifest,
                                        "%s%s %s\n" % (tab,section_name[len(SINGLE_SEC):],content))
        return tab

    # quote required values
    @GeneralException
    def __add_quotes(self, key, val):
        return (("'%s'" % (re.sub('\'', '\\\'', val))
                 if (key not in QUOTED_AVOIDED_KEYS)
                 and ((key in QUOTED_FORCED_KEYS)
                      or (re.search(self.__quoted_regex, val)))
                 else val)
                if type(val) is str else val)

    # content writing
    @GeneralException
    def __write_content(self, section_name, label, optlabel, content):
        out = ''
        out_size = 0
        if (type(content) is list):
            for value in content:
                out += (", " if out_size else '')+"'%s'" % (value)
                out_size += 1
            if out_size:
                return "%s%s%s" % (("[" if out_size > 1 else ''),out,("]" if out_size > 1 else ''))
        elif (type(content) is dict):
            for value_type in content:
                for value in content[value_type]:
                    out += (", " if out_size else '') + "%s['%s']" % (value_type,value)
                    out_size += 1
            if out_size:
                return "%s%s%s" % (("[" if out_size > 1 else ''),out,("]" if out_size > 1 else ''))
        else:
            if (self.__curent_manifest in FILE_CLASS) and (label[0] != '-') and optlabel == 'content':
                filename = ('/' if label[0] != '/' else '')+label
                Tools.write_in_file(self.__output_path+'/templates'+filename, content)
                content = "template('%s')" % (self.__module_name+filename)
            return self.__add_quotes(optlabel, content)
        return None

    # global content generation for pupept config file
    @GeneralException
    def __create_content(self, parent, data, section_name, tab):
        Tools.l(INFO, "creating section %s" % (section_name.lstrip(VOID_EQ)), 'create_content', self)
        if section_name[:len(SINGLE_SEC)] == SINGLE_SEC:
             return self.__single_instruction(parent, data, section_name, tab)
        self.__output_container.add(self.__curent_manifest, "%s%s {\n" % (tab,section_name.lstrip(ACTION_ID)))
        for label in sorted(data[section_name]):
            if label in NULL:
                continue
            if label[0] != ACTION_ID:
                tab = Tools.tab_inc(tab)
                self.__output_container.add(self.__curent_manifest, "%s'%s':\n" % (tab,label))
            tab = Tools.tab_inc(tab)
            wrote = False
            for optlabel in sorted(data[section_name][label]):
                if (data[section_name][label][optlabel] not in NULL) and (optlabel[0] != ACTION_ID):
                    out = self.__write_content(section_name,
                                               label,
                                               optlabel,
                                               data[section_name][label][optlabel])
                    if out:
                        self.__output_container.add(self.__curent_manifest,
                                                    "%s%s%s => %s"%((",\n" if wrote else ''),tab,optlabel,out))
                        wrote = True
            if wrote and label != MAIN_SECTION:
                self.__output_container.add(self.__curent_manifest, ";\n")
            elif wrote and label == MAIN_SECTION:
                self.__output_container.add(self.__curent_manifest, "\n")
            tab = Tools.tab_dec(tab)
            if label[0] != ACTION_ID:
                tab = Tools.tab_dec(tab)
        self.__output_container.add(self.__curent_manifest, "%s}\n" % (tab))
        return tab

    # class generation method, applies the recursion
    @GeneralException
    def __create_class(self, parent, data, section_name, tab):
        Tools.l(INFO, "generation class %s" % (section_name), 'create_class', self)
        self.__output_container.add(self.__curent_manifest, "%sclass %s {\n" % (tab,section_name))
        tab = Tools.tab_inc(tab)
        # recursion here
        tab = self.__generate(data[section_name], data, tab)
        tab = Tools.tab_dec(tab)
        self.__output_container.add(self.__curent_manifest, "%s}\n%sinclude %s\n" % (tab,tab,section_name))
        return tab

    # puppet file generation function
    # recursive function
    @GeneralException
    def __generate(self, data, parent = None, tab=''):
        # adding Exec section
        if GLOBAL_SEC_EQ['Exec'] in data:
            tab = self.__create_content(parent, data, GLOBAL_SEC_EQ['Exec'], tab)
        # global generation
        for section_name in sorted(data):
            # avoid exception
            if section_name == GLOBAL_SEC_EQ['Exec']:
                continue
            # content found
            elif section_name[0] == ACTION_ID and self.__curent_manifest:
                tab = self.__create_content(parent, data, section_name, tab)
                continue
            # new class
            if not parent:
                self.__curent_manifest = section_name
                self.__output_container.add_dict(self.__curent_manifest)
            # recursion here
            tab = self.__create_class(parent, data, section_name, tab)
        return tab

########NEW FILE########
__FILENAME__ = converter
'''
Dictionnary converter for puppet scripts generation

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Thibault BRONCHAIN
'''

import re
import copy

from pysa.tools import *
from pysa.config import *
from pysa.exception import *

from pysa.filter.filter import Filter


# define _order section

# list of ordered sections
ORDERED_LIST_EQ = ['sources']

# general modifiers
GLOBAL_SEC_EQ = {
    'Exec'      : ACTION_ID+'Exec',
    'exec'      : ACTION_ID+'exec',
    'order'     : ACTION_ID+'order',
    'require'   : SINGLE_SEC+'require'
}

# define _Exec section
GLOBAL_EXEC_EQ = {
    'path'      : '/usr/bin:/bin:/usr/sbin:/sbin'
}

# define _exec section
EXEC_EQ = {
    'apt'   : 'apt-get update',
    'yum'   : '/usr/sbin/yum-complete-transaction',
    'pip'   : 'easy_install pip',
    }

# define general sections
SECTION_EQ = {
    'dirs'      : ACTION_ID+'file',
    'files'     : ACTION_ID+'file',
    'packages'  : ACTION_ID+'package',
    'services'  : ACTION_ID+'service',
    'crons'     : ACTION_ID+'cron',
    'groups'    : ACTION_ID+'group',
    'mounts'    : ACTION_ID+'mount',
    'hosts'     : ACTION_ID+'host',
    'repos'     : ACTION_ID+'file',
    'keys'      : ACTION_ID+'file',
    'users'     : ACTION_ID+'user',
    'sources'   : ACTION_ID+'vcsrepo'
    }
SECTION_CALL_EQ = dict([(key,SECTION_EQ[key].capitalize()) for key in SECTION_EQ])

# define subsclasses equivalency
SUBCLASS_EQ = {
    'packages'  : {
        MAIN_SECTION : 'provider',
        'order'   : [
            ['apt', 'yum', 'rpm'],
            ['npm', 'pecl', 'pear', 'pip', 'gem']
            ]
        }
}

# add 'require' instruction
REQUIRE_EQ = [
    SUBCLASS_EQ['packages']['order']
    ]

# key modifier
CONTENTKEY_EQ = {
    MAIN_SECTION     : {
        'version'   : 'ensure',
        'key'       : 'content'
        },
    'sources'   : {
        'scm'       : 'provider'
        },
    'users'     : {
        'group'     : 'gid'
        }
}

# val modifier (on key)
CONTENTVAL_EQ = {
    'packages'  : {
        'provider'  : ['php', 'pear']
        }
}

# content add
CONTENTADD_EQ = {
    'sources'   : {
        'ensure'    : 'present'
        },
    'groups'    : {
        'ensure'    : 'present'
        }
}

# avoided sections
AVOIDSEC_EQ = {
    'mounts'    : ['size'],
    'packages'  : ['manager', 'config_files'],
    'sources'   : ['mode', 'password', 'branch', 'name', 'key'],
    'groups'    : ['gid'],
    'users'     : ['uid', 'gid'],
    'repos'     : ['provider'],
}

# Append sections
APPSEC_EQ = {
    'crons'     : ['environment', 'PATH=']
}

class PuppetConverter():
    def __init__(self, minput, filters = None):
        self.__output = {}
        self.__input = copy.deepcopy(minput)
        self.__filter = Filter(filters)
        self.__prev_obj = None

    # main method
    @GeneralException
    def run(self):
        Tools.l(INFO, "running", 'run', self)

        #empty imput
        if not self.__input:
            Tools.l(ERR, "empty input", 'run', self)
            return {}

        # convert
        self.__generate_classes(self.__input)

        # add exceptions
        if GLOBAL_EXEC_EQ:
            self.__add_global_exec()

        Tools.l(INFO, "complete", 'run', self)
        return self.__output

    # generate global exec
    @GeneralException
    def __add_global_exec(self):
        Tools.l(INFO, "adding Exec section", 'add_global_exec', self)
        self.__output[GLOBAL_SEC_EQ['Exec']] = {MAIN_SECTION : {}}
        for key in GLOBAL_EXEC_EQ:
            Tools.l(INFO, "adding key %s" % (key), 'add_global_exec', self)
            self.__output[GLOBAL_SEC_EQ['Exec']][MAIN_SECTION][key] = self.__process_values('', 'Exec', key, GLOBAL_EXEC_EQ[key])

    # generate sub execs
    @GeneralException
    def __add_top_class(self, key):
        c = {}
        for order in REQUIRE_EQ:
            if key in order[0]: break
            elif key in order[1]:
                req = []
                for r in order[0]:
                    req.append(r)
                if req:
                    c = Tools.dict_merging(c, {
                            GLOBAL_SEC_EQ['require'] : req
                            })
        if key in EXEC_EQ:
            Tools.l(INFO, "adding exec section for %s" % (key), 'add_exec', self)
            c = Tools.dict_merging(c, {
                    GLOBAL_SEC_EQ['exec'] : {
                        EXEC_EQ[key] : GLOBAL_EXEC_EQ
                        }
                    })
        return c

    # processing on values
    @GeneralException
    def __process_values(self, gclass, name, key, val):
        if type(val) is int:
            val = "%s" % (val)
        elif (type(val) is not str) or (not val):
            return val
        if (gclass in APPSEC_EQ) and (key == APPSEC_EQ[gclass][0]):
            val = APPSEC_EQ[gclass][1] + val
        return self.__filter.item_replace(gclass, key, val, name)


    # processing on data
    @GeneralException
    def __process_data(self, input, gclass, name, cur_class):
        Tools.l(INFO, "processing data", 'process_data', self)
        # modifications
        kcontent = Tools.list_merging(AVOIDSEC_EQ.get(MAIN_SECTION), AVOIDSEC_EQ.get(gclass))
        for key in kcontent:
            if key in input:
                input[key] = None
        kcontent = Tools.s_dict_merging(CONTENTADD_EQ.get(MAIN_SECTION), CONTENTADD_EQ.get(gclass), False)
        for key in kcontent:
            input[key] = kcontent[key]
        kcontent = Tools.s_dict_merging(CONTENTKEY_EQ.get(MAIN_SECTION), CONTENTKEY_EQ.get(gclass), False)
        for key in kcontent:
            if key in input:
                input[kcontent[key]] = input.pop(key)
        kcontent = Tools.s_dict_merging(CONTENTVAL_EQ.get(MAIN_SECTION), CONTENTVAL_EQ.get(gclass), False)
        for key in kcontent:
            if key in input:
                if input[key] == kcontent[key][0]:
                    input[key] = kcontent[key][1]

        # exec dependency
        if cur_class in EXEC_EQ:
            input['require'] = Tools.dict_merging(input.get('require'), {
                    GLOBAL_SEC_EQ['exec'][len(ACTION_ID):].capitalize() : [
                        EXEC_EQ[cur_class]
                        ]
                    })

        # main loop
        for key in input:
            if type(input[key]) is list:
                store = []
                for d in input[key]:
                    store.append(self.__process_values(gclass, name, key, d))
                input[key] = store
            else:
                input[key] = self.__process_values(gclass, name, key, input[key])
        return input

    # processing on section
    @GeneralException
    def __process_sec(self, data, gclass, name, cur_class):
        Tools.l(INFO, "creating section %s" % (SECTION_EQ[gclass]), 'process_sec', self)
        if (SECTION_EQ[gclass] == ACTION_ID+'package'):
            data[gclass][name] = self.__filter.update_package(data[gclass][name], name, 'latest')
        return self.__process_data(data[gclass][name], gclass, name, cur_class)

    # class generation
    @GeneralException
    def __generate_classes(self, data):
        for gclass in data:
            if gclass not in SECTION_EQ:
                Tools.l(INFO, "Ignored unknown class %s" % (gclass), 'generate_classes', self)
                continue
            Tools.l(INFO, "creating class %s" % (gclass), 'generate_classes', self)
            self.__prev_obj = None
            self.__output[gclass] = self.__add_top_class(gclass)
            for name in sorted(data[gclass]):
                if gclass in SUBCLASS_EQ:
                    subkey = data[gclass][name][SUBCLASS_EQ[gclass][MAIN_SECTION]]
                    Tools.l(INFO, "creating sub class %s" % (subkey), 'generate_classes', self)
                    self.__output[gclass].setdefault(subkey, self.__add_top_class(subkey))
                    self.__output[gclass][subkey].setdefault(SECTION_EQ[gclass], {})
                    self.__output[gclass][subkey][SECTION_EQ[gclass]][name] = self.__process_sec(data, gclass, name, subkey)
                else:
                    self.__output[gclass].setdefault(SECTION_EQ[gclass], {})
                    self.__output[gclass][SECTION_EQ[gclass]][name] = self.__process_sec(data, gclass, name, gclass)
                self.__prev_obj = name

########NEW FILE########
__FILENAME__ = objects
'''
Puppet Objects

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Thibault BRONCHAIN
'''

from pysa.exception import *

from pysa.scanner.actions.utils import get_stat
from pysa.dependencies import *

CMLABEL="puppet"

class PuppetObjects():
    @staticmethod
    def puppet_file_dir_obj(dr):
        # get group, mode and owner
        s = get_stat(dr)
        #DEBUG
        #s = ('root', oct(0777), 'root')
        #/DEBUG
        return {
            'path'      : dr,
            'ensure'    : 'directory',
            'name'      : dr,
            'group'     : s[0],
            'mode'      : s[1],
            'owner'     : s[2],
            }

    @staticmethod
    def puppet_pkg_manager_obj(package, provider):
        return {
            'name'      : package,
            'provider'  : provider,
            'version'   : 'latest',
            }


OBJ_MAKER = {
    'file' : PuppetObjects.puppet_file_dir_obj,
    'manager' : PuppetObjects.puppet_pkg_manager_obj,
    }

DEPENDENCIES = {
    'hosts'     : {},
    'mounts'    : {
        'hosts'     : 'Class',
        'mounts'    : [
            BASED_ON_FIELD, {
                'field' : [SELF_ORDER, {
                        'field'     : 'name',
                        }],
                'key'   : 'name',
                }
            ],
        },
    'groups'    : {
        'hosts'     : 'Class',
        },
    'users'     : {
        'hosts'     : 'Class',
        'groups'    : [
            BASED_ON_FIELD, {
                'field' : 'group',
                'key'   : 'name',
                }
            ],
        },
    'dirs'      : {
        'hosts'     : 'Class',
        'dirs'    : [
            BASED_ON_FIELD, {
                'field' : [SELF_ORDER, {
                        'field'     : 'path',
                        }],
                'key'   : 'path',
                }
            ],
        'groups'    : [
            BASED_ON_FIELD, {
                'field' : 'group',
                'key'   : 'name',
                }
            ],
        'users'     : [
            BASED_ON_FIELD, {
                'field' : 'owner',
                'key'   : 'name',
                }
            ],
        'mounts'    : [
            BASED_ON_FIELD, {
                'field' : [GET_MOUNT_FROM_PATH, {
                        'field'     : 'path',
                        }],
                'key'   : 'device',
                }
            ],
        },
    'keys'      : {
        'hosts'     : 'Class',
        'groups'    : [
            BASED_ON_FIELD, {
                'field' : 'group',
                'key'   : 'name',
                }
            ],
        'users'     : [
            BASED_ON_FIELD, {
                'field' : 'owner',
                'key'   : 'name',
                }
            ],
        'dirs'      : [
            BASED_ON_FIELD, {
                'field' : [GET_BASE_PATH, {
                        'field'     : 'path',
                        }],
                'key'   : 'path',
                }
            ],
        },
    'repos'     : {
        'hosts'     : 'Class',
        'groups'    : [
            BASED_ON_FIELD, {
                'field' : 'group',
                'key'   : 'name',
                }
            ],
        'users'     : [
            BASED_ON_FIELD, {
                'field' : 'owner',
                'key'   : 'name',
                }
            ],
        'dirs'      : [
            BASED_ON_FIELD, {
                'field' : [GET_BASE_PATH, {
                        'field'     : 'path',
                        }],
                'key'   : 'path',
                }
            ],
        },
    'packages'  : {
        'hosts'     : 'Class',
        'repos'     : [
            BASED_ON_FIELD, {
                'field' : 'provider',
                'key'   : 'provider',
                }
            ],
        'dirs'      : [
            BASED_ON_FIELD, {
                'field' : [GET_BASE_PATH, {
                        'field'     : 'path',
                        }],
                'key'   : 'path',
                }
            ],
        },
    'files'     : {
        'hosts'     : 'Class',
        'groups'    : [
            BASED_ON_FIELD, {
                'field' : 'group',
                'key'   : 'name',
                }
            ],
        'users'     : [
            BASED_ON_FIELD, {
                'field' : 'owner',
                'key'   : 'name',
                }
            ],
        'dirs'      : [
            BASED_ON_FIELD, {
                'field' : [GET_BASE_PATH, {
                        'field'     : 'path',
                        }],
                'key'   : 'path',
                }
            ],
        'packages'  : [
            BASED_ON_FIELD, {
                'field' : 'path',
                'key'   : 'config_files',
                }
            ],
        },
    'crons'     : {
        'hosts'     : 'Class',
        'users'     : [
            BASED_ON_FIELD, {
                'field' : 'user',
                'key'   : 'name',
                }
            ],
        },
    'sources'   : {
        'hosts'     : 'Class',
        'sources'   : [
            BASED_ON_FIELD, {
                'field' : [SELF_ORDER, {
                        'field'     : 'path',
                        }],
                'key'   : 'path',
                }
            ],
        'groups'    : [
            BASED_ON_FIELD, {
                'field' : 'group',
                'key'   : 'name',
                }
            ],
        'users'     : [
            BASED_ON_FIELD, {
                'field' : 'owner',
                'key'   : 'name',
                }
            ],
        'dirs'      : [
            BASED_ON_FIELD, {
                'field' : [GET_BASE_PATH, {
                        'field'     : 'path',
                        }],
                'key'   : 'path',
                }
            ],
        'keys'      : [
            BASED_ON_FIELD, {
                'field' : 'key',
                'key'   : 'name',
                }
            ],
        'packages'  : [
            BASED_ON_FIELD, {
                'field' : [GET_PKG_FROM_SCM, {
                        'field'     : 'scm',
                        }],
                'key'   : 'name',
                }
            ],
        },
    'services'  : {
        'files'     : 'Class',
        },
    }

########NEW FILE########
__FILENAME__ = build
'''
Generate salt manifests

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Thibault BRONCHAIN
'''

import re

from pysa.exception import *
from pysa.config import *
from pysa.tools import *
from pysa.output import Output

# salt generation class
class SaltBuild():
    def __init__(self, input_dict, output_path, module_name):
        self.__module_name = module_name
        self.__input_dict = input_dict
        self.__output_container = Output()
        self.__output_path = output_path+'/'+self.__module_name
        self.__curent_manifest = None
        self.__curent_state = None
        self.__curent_name = None

    # main function
    @GeneralException
    def run(self):
        Tools.l(INFO, "running generation engine", 'run', self)
        self.__generate(self.__input_dict)
        self.__create_init_file()
        self.dump_in_files()
        Tools.l(INFO, "generation complete", 'run', self)
        return True

    # print the puppet files
    @GeneralException
    def dump(self):
        for manifest_name in self.__output_container.list():
            manifest_fname = (manifest_name if manifest_name else 'init')
            print "%s:\n%s\n\n" % (manifest_fname,
                                   self.__output_container.dump(manifest_name))

    # dump puppet file in variable
    @GeneralException
    def dump_in_var(self, data=''):
        for manifest_name in self.__output_container.list():
            manifest_fname = (manifest_name if manifest_name else 'init')
            data += ("%s:\n%s\n\n" % (manifest_fname,
                                      self.__output_container.dump(manifest_name)))
        return data

    # dump the puppet files into the right files
    @GeneralException
    def dump_in_files(self):
        for manifest_name in self.__output_container.list():
            manifest_fname = (manifest_name if manifest_name else 'init')
            Tools.write_in_file(self.__output_path+'/'+manifest_fname+'.sls',
                                self.__output_container.dump(manifest_name))

    # init file generation
    @GeneralException
    def __create_init_file(self):
        self.__output_container.add(None, "include:\n")
        for manifest in self.__output_container.list():
            if not manifest: continue
            self.__output_container.add(None, "  - %s.%s\n"%(self.__module_name,manifest))

    # content writing
    @GeneralException
    def __write_content(self, key, val, tab):
        if (self.__curent_manifest in FILE_CLASS) and key == 'source':
            name = self.__input_dict[self.__curent_manifest][self.__curent_state][self.__curent_name]['name']
            filename = "%s" % (('/' if name[0] != '/' else '')+name)
            Tools.write_in_file(self.__output_path+'/templates'+filename, val)
            val = "salt://%s" % (self.__module_name+'/templates'+filename)
        self.__output_container.add(self.__curent_manifest, "%s"%(val))

    # section generation (recursive)
    @GeneralException
    def __create_section(self, key, val, tab):
        if (key in NULL) or (val == None): return
        self.__output_container.add(self.__curent_manifest, "%s- %s"%(tab,key))
        if val == MAIN_SECTION:
            self.__output_container.add(self.__curent_manifest, "\n")
        elif type(val) is dict:
            tab += "  "
            self.__output_container.add(self.__curent_manifest, ":\n")
            for sub_key in val:
                if key == "require":
                    for itm in val[sub_key]:
                        self.__create_section("%s: %s"%(sub_key,itm), MAIN_SECTION, tab)
                else:
                    self.__create_section(sub_key, val[sub_key], tab)
        elif type(val) is list:
            tab += "  "
            self.__output_container.add(self.__curent_manifest, ":\n")
            for d in val:
                self.__create_section(d, MAIN_SECTION, tab)
        else:
            self.__output_container.add(self.__curent_manifest, ": ")
            self.__write_content(key, val, tab)
            self.__output_container.add(self.__curent_manifest, "\n")

    # global content generation for salt config file
    @GeneralException
    def __create_content(self, data, manifest, state, name):
        cur_data = data[manifest][state][name]
        self.__output_container.add(self.__curent_manifest, "%s:\n"%(name if name[0] != '-' else name[1:]))
        self.__output_container.add(self.__curent_manifest, "  %s:\n"%(state[len(ACTION_ID):]))
        for key in cur_data:
            self.__create_section(key, cur_data[key], "    ")

    # puppet file generation function
    @GeneralException
    def __generate(self, data):
        # global generation
        for manifest in sorted(data):
            Tools.l(INFO, "generation manifest %s" % (manifest), 'generate', self)
            self.__curent_manifest = manifest
            for state in sorted(data[manifest]):
                self.__curent_state = state
                Tools.l(INFO, "module state %s" % (state), 'generate', self)
                for name in sorted(data[manifest][state]):
                    self.__curent_name = name
                    Tools.l(INFO, "item %s" % (name), 'generate', self)
                    self.__create_content(data, manifest, state, name)

########NEW FILE########
__FILENAME__ = converter
'''
Dictionnary converter for salt scripts generation

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Thibault BRONCHAIN
'''

import re
import hashlib
import copy

from pysa.tools import *
from pysa.config import *
from pysa.exception import *

from pysa.filter.filter import Filter


def handler_files_checksum(old, content):
    contents = ['content','key','source']
    c = None
    for c_name in contents:
        c = content.get(c_name)
        if c: break
    if not c: return None
    return "md5=%s"%(hashlib.md5(c).hexdigest())

def handler_actionkey_pkg(content):
    if (content.get('version') == 'latest') or not content.get('version'):
        content['version'] = None
        return 'latest'
    return 'installed'

def handler_hosts_names(old, content):
    return (old if type(old) is list else [old])

# TODO: sources

# define general sections
SECTION_EQ = {
#    'dirs'      : ACTION_ID+'file',
    'files'     : ACTION_ID+'file',
    'packages'  : {
        'key'   : 'provider',
        'apt'   : ACTION_ID+'pkg',
        'yum'   : ACTION_ID+'pkg',
        'rpm'   : ACTION_ID+'pkg',
#        'php'   : ACTION_ID+'pecl',
        'pecl'  : ACTION_ID+'pecl',
        'pear'  : ACTION_ID+'pecl',
        'pip'   : ACTION_ID+'pip',
        'npm'   : ACTION_ID+'npm',
        'gem'   : ACTION_ID+'gem',
        },
    'services'  : ACTION_ID+'service',
    'crons'     : ACTION_ID+'cron',
    'groups'    : ACTION_ID+'group',
    'mounts'    : ACTION_ID+'mount',
    'hosts'     : ACTION_ID+'host',
    'repos'     : ACTION_ID+'file',
    'keys'      : ACTION_ID+'file',
    'users'     : ACTION_ID+'user',
#    'sources'   : {
#        'key'   : 'provider',
#        'git'   : ACTION_ID+'git',
#        'svn'   : ACTION_ID+'svn',
#        'hg'    : ACTION_ID+'hg',
#        }
    }
SECTION_CALL_EQ = SECTION_EQ

# avoided sections
AVOIDSEC_EQ = {
    'cron'      : ['environment', 'name', 'target'],
    'files'     : ['provider','recurse','recurselimit','source'],
    'groups'    : ['member','gid'],
    'hosts'     : ['target'],
    'mounts'    : ['atboot','size'],
    ACTION_ID+'pkg' : ['config_files','description','responsefile','provider','instance','category','platform','root','manager','vendor'],
    ACTION_ID+'pecl' : ['version','config_files','description','responsefile','provider','instance','category','platform','root','manager','vendor'],
    ACTION_ID+'gem' : ['version','config_files','description','responsefile','provider','instance','category','platform','root','manager','vendor'],
    ACTION_ID+'npm' : ['version','config_files','description','responsefile','provider','instance','category','platform','root','manager','vendor'],
    ACTION_ID+'pip' : ['version','config_files','description','responsefile','provider','instance','category','platform','root','manager','vendor'],
    'repos'     : ['provider','recurse','recurselimit','source'],
    'services'  : ['hasrestart','path','provider','binary','control','ensure','hasstatus','manifest','start','stop','restart'],
    'keys'      : ['target','host_aliases','type','name'],
    'users'     : ['uid', 'gid', 'expiry'],
    }
# content add
CONTENTADD_EQ = {
    'files'     : {
        'makedirs'  : 'True',
        },
    'mounts'    : {
        'mkmnt'     : 'True',
        },
    'repos'     : {
        'makedirs'  : 'True',
        },
    'keys'      : {
        'source_hash' : 'md5',
        },
    'services'     : {
        'enable'    : 'True',
        },
    }
# key modifier
CONTENTKEY_EQ = {
    MAIN_SECTION : {
        },
    'crons'     : {
        'command'   : 'name',
        'monthday'  : 'daymonth',
        'weekday'   : 'dayweek',
        },
    'files'     : {
        'checksum'  : 'source_hash',
        'content'   : 'source',
        'owner'     : 'user',
        'path'      : 'name',
        'force'     : 'replace',
        },
    'hosts'     : {
        'name'      : 'names',
        'host_aliases' : 'names',
        },
    'mount'     : {
        'remounts'  : 'remount',
        'options'   : 'opts',
        },
    'repos' : {
        'checksum'  : 'source_hash',
        'content'   : 'source',
        'owner'     : 'user',
        'path'      : 'name',
        'force'     : 'replace',
        },
    'keys' : {
        'key'       : 'source',
        'content'   : 'source',
        'path'      : 'name',
        },
    'users'     : {
        'group'     : 'gid',
        }
    }
# val modifier (on key)
CONTENTVAL_EQ = {
    'files'    : {
        'source_hash' : [MAIN_SECTION,handler_files_checksum],
        },
    'repos'    : {
        'source_hash' : [MAIN_SECTION,handler_files_checksum],
        },
    'keys'     : {
        'source_hash' : [MAIN_SECTION,handler_files_checksum],
        },
    'hosts'    : {
        'names'       : [MAIN_SECTION,handler_hosts_names],
        },
    }

# action key
ACTIONKEY_EQ = {
    'crons'     : 'present',
    'files'     : 'managed',
    'groups'    : 'present',
    'hosts'     : 'present',
    'mounts'    : 'mounted',
    ACTION_ID+'pkg' : handler_actionkey_pkg,
    ACTION_ID+'pecl' : 'installed',
    ACTION_ID+'gem' : 'installed',
    ACTION_ID+'npm' : 'installed',
    ACTION_ID+'pip' : 'installed',
    'repos'     : 'managed',
    'services'  : 'running',
    'keys'      : 'managed',
    'users'     : 'present',
    }

# Append sections
APPSEC_EQ = {
    }


class SaltConverter():
    def __init__(self, minput, filters=None):
        self.__output = {}
        self.__input = copy.deepcopy(minput)
        self.__filter = Filter(filters)

    # main method
    @GeneralException
    def run(self):
        Tools.l(INFO, "running", 'run', self)

        #empty imput
        if not self.__input:
            Tools.l(ERR, "empty input", 'run', self)
            return {}

        self.__curent_state = None

        # convert
        self.__generate_classes(self.__input)

        Tools.l(INFO, "complete", 'run', self)
        return self.__output

    # processing on values
    @GeneralException
    def __process_values(self, manifest, name, key, val):
        if type(val) is int:
            val = "%s" % (val)
        elif (type(val) is not str) or (not val):
            return val
        if (manifest in APPSEC_EQ) and (key == APPSEC_EQ[manifest][0]):
            val = APPSEC_EQ[manifest][1] + val
        return self.__filter.item_replace(manifest, key, val, name)

    # processing on data
    # recursive
    @GeneralException
    def __structure_data(self, data, manifest, name):
        Tools.l(INFO, "building data structure", 'structure_data', self)
        for key in data:
            if type(data[key]) is dict:
                data[key] = self.__structure_data(data[key], manifest, name)
            elif type(data[key]) is list:
                store = []
                for d in data[key]:
                    store.append(self.__process_values(manifest, name, key, d))
                data[key] = store
            else:
                data[key] = self.__process_values(manifest, name, key, data[key])
        Tools.l(INFO, "building data structure complete", 'structure_data', self)
        return data

    # processing on data
    @GeneralException
    def __process_data(self, data, manifest, name):
        Tools.l(INFO, "processing data", 'process_data', self)
        sec_key = (self.__curent_state if type(SECTION_EQ[manifest]) is dict else manifest)

        # modifications
        kcontent = Tools.list_merging(AVOIDSEC_EQ.get(MAIN_SECTION), AVOIDSEC_EQ.get(sec_key))
        for key in kcontent:
            if key in data:
                data[key] = None
        kcontent = Tools.s_dict_merging(CONTENTADD_EQ.get(MAIN_SECTION), CONTENTADD_EQ.get(sec_key), False)
        for key in kcontent:
            data[key] = kcontent[key]
        kcontent = Tools.s_dict_merging(CONTENTKEY_EQ.get(MAIN_SECTION), CONTENTKEY_EQ.get(sec_key), False)
        for key in kcontent:
            if key in data:
                data[kcontent[key]] = Tools.merge_string_list(data.get(kcontent[key]), data.pop(key))
        kcontent = Tools.s_dict_merging(CONTENTVAL_EQ.get(MAIN_SECTION), CONTENTVAL_EQ.get(sec_key), False)
        for key in kcontent:
            if key in data:
                if (data[key] == kcontent[key][0]) or (kcontent[key][0] == MAIN_SECTION):
                    if type(kcontent[key][1]) is str:
                        data[key] = kcontent[key][1]
                    else:
                        data[key] = kcontent[key][1](data[key], data)

        # set action key
        kcontent = ACTIONKEY_EQ.get(sec_key)
        if type(kcontent) is str:
            data[kcontent] = MAIN_SECTION
        elif kcontent:
            data[kcontent(data)] = MAIN_SECTION

        # main loop
        data = self.__structure_data(data, manifest, name)
        Tools.l(INFO, "processing data complete", 'process_data', self)
        return data

    # ganaration method
    @GeneralException
    def __generate_classes(self, data):
        for manifest in sorted(data):
            if manifest not in SECTION_EQ:
                Tools.l(INFO, "Ignored unknown class %s" % (manifest), 'generate_classes', self)
                continue
            Tools.l(INFO, "creating manifest %s" % (manifest), 'generate_classes', self)
            for name in sorted(data[manifest]):
                if type(SECTION_EQ[manifest]) is dict:
                    ref = data[manifest][name].get(SECTION_EQ[manifest]['key'])
                    if not ref:
                        Tools.l(ERR, "Reference key not found %s" % (SECTION_EQ[manifest]['key']), 'generate_classes', self)
                        continue
                    state = SECTION_EQ[manifest].get(ref)
                    if not state:
                        Tools.l(ERR, "State not found ref %s, manifest %s"%(ref,manifest), 'generate_classes', self)
                        continue
                else:
                    state = SECTION_EQ.get(manifest)
                    if not state:
                        Tools.l(ERR, "State not found manifest %s"%(manifest), 'generate_classes', self)
                        continue
                if (manifest == 'packages'):
                    data[manifest][name] = self.__filter.update_package(data[manifest][name], name, 'latest')
                self.__output.setdefault(manifest, {})
                self.__output[manifest].setdefault(state, {})
                self.__curent_state = state
                self.__output[manifest][state][name] = self.__process_data(data[manifest][name], manifest, name)

########NEW FILE########
__FILENAME__ = objects
'''
Salt Objects

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Thibault BRONCHAIN
'''

import re

from pysa.exception import *
from pysa.dependencies import *

from pysa.scanner.actions.utils import get_stat

CMLABEL="salt"
ILLEGAL_OBJ_CHAR=None#['\W']

class SaltObjects():
    @staticmethod
    def salt_file_dir_obj(dr):
        # get group, mode and owner
        s = get_stat(dr)
        #DEBUG
        #s = ('root', oct(0777), 'root')
        #/DEBUG
        return {
            'path'      : dr,
            'ensure'    : 'directory',
            'name'      : dr,
            'group'     : s[0],
            'mode'      : s[1],
            'owner'     : s[2],
            }

    @staticmethod
    def salt_pkg_manager_obj(package, provider):
        return {
            'name'      : package,
            'provider'  : provider,
            'version'   : 'latest',
            }

    @staticmethod
    def salt_key_mod_obj(state, obj):
        key = "%s_%s"%(state,obj)
        if not ILLEGAL_OBJ_CHAR: return key
        illegal_char = "%s" % ('|'.join(ILLEGAL_OBJ_CHAR))
        key = re.sub(illegal_char, "_", key)
        return key


OBJ_MAKER = {
    'file' : SaltObjects.salt_file_dir_obj,
    'manager' : SaltObjects.salt_pkg_manager_obj,
    'objkey' : SaltObjects.salt_key_mod_obj,
    }

DEPENDENCIES = {
    'hosts'     : {},
    'mounts'    : {
#        'hosts'     : 'Class',
        'mounts'    : [
            BASED_ON_FIELD, {
                'field' : [SELF_ORDER, {
                        'field'     : 'name',
                        }],
                'key'   : 'name',
                }
            ],
        },
    'groups'    : {
#        'hosts'     : 'Class',
        },
    'users'     : {
#        'hosts'     : 'Class',
        'groups'    : [
            BASED_ON_FIELD, {
                'field' : 'group',
                'key'   : 'name',
                }
            ],
        },
#    'dirs'      : {
#        'hosts'     : 'Class',
#        'dirs'    : [
#            BASED_ON_FIELD, {
#                'field' : [SELF_ORDER, {
#                        'field'     : 'path',
#                        }],
#                'key'   : 'path',
#                }
#            ],
#        'groups'    : [
#            BASED_ON_FIELD, {
#                'field' : 'group',
#                'key'   : 'name',
#                }
#            ],
#        'users'     : [
#            BASED_ON_FIELD, {
#                'field' : 'owner',
#                'key'   : 'name',
#                }
#            ],
#        'mounts'    : [
#            BASED_ON_FIELD, {
#                'field' : [GET_MOUNT_FROM_PATH, {
#                        'field'     : 'path',
#                        }],
#                'key'   : 'device',
#                }
#            ],
#        },
    'keys'      : {
#        'hosts'     : 'Class',
        'groups'    : [
            BASED_ON_FIELD, {
                'field' : 'group',
                'key'   : 'name',
                }
            ],
        'users'     : [
            BASED_ON_FIELD, {
                'field' : 'owner',
                'key'   : 'name',
                }
            ],
#        'dirs'      : [
#            BASED_ON_FIELD, {
#                'field' : [GET_BASE_PATH, {
#                        'field'     : 'path',
#                        }],
#                'key'   : 'path',
#                }
#            ],
        },
    'repos'     : {
#        'hosts'     : 'Class',
        'groups'    : [
            BASED_ON_FIELD, {
                'field' : 'group',
                'key'   : 'name',
                }
            ],
        'users'     : [
            BASED_ON_FIELD, {
                'field' : 'owner',
                'key'   : 'name',
                }
            ],
#        'dirs'      : [
#            BASED_ON_FIELD, {
#                'field' : [GET_BASE_PATH, {
#                        'field'     : 'path',
#                        }],
#                'key'   : 'path',
#                }
#            ],
        },
    'packages'  : {
#        'hosts'     : 'Class',
        'repos'     : [
            BASED_ON_FIELD, {
                'field' : 'provider',
                'key'   : 'provider',
                }
            ],
        'packages'     : [
            PACKAGE_MANAGER, {
                'field' : 'provider',
                'key'   : None,
                }
            ],
#        'dirs'      : [
#            BASED_ON_FIELD, {
#                'field' : [GET_BASE_PATH, {
#                        'field'     : 'path',
#                        }],
#                'key'   : 'path',
#                }
#            ],
        },
    'files'     : {
#        'hosts'     : 'Class',
        'groups'    : [
            BASED_ON_FIELD, {
                'field' : 'group',
                'key'   : 'name',
                }
            ],
        'users'     : [
            BASED_ON_FIELD, {
                'field' : 'owner',
                'key'   : 'name',
                }
            ],
#        'dirs'      : [
#            BASED_ON_FIELD, {
#                'field' : [GET_BASE_PATH, {
#                        'field'     : 'path',
#                        }],
#                'key'   : 'path',
#                }
#            ],
        'packages'  : [
            BASED_ON_FIELD, {
                'field' : 'path',
                'key'   : 'config_files',
                }
            ],
        },
    'crons'     : {
#        'hosts'     : 'Class',
        'users'     : [
            BASED_ON_FIELD, {
                'field' : 'user',
                'key'   : 'name',
                }
            ],
        },
    'sources'   : {
#        'hosts'     : 'Class',
        'sources'   : [
            BASED_ON_FIELD, {
                'field' : [SELF_ORDER, {
                        'field'     : 'path',
                        }],
                'key'   : 'path',
                }
            ],
        'groups'    : [
            BASED_ON_FIELD, {
                'field' : 'group',
                'key'   : 'name',
                }
            ],
        'users'     : [
            BASED_ON_FIELD, {
                'field' : 'owner',
                'key'   : 'name',
                }
            ],
#        'dirs'      : [
#            BASED_ON_FIELD, {
#                'field' : [GET_BASE_PATH, {
#                        'field'     : 'path',
#                        }],
#                'key'   : 'path',
#                }
#            ],
        'keys'      : [
            BASED_ON_FIELD, {
                'field' : 'key',
                'key'   : 'name',
                }
            ],
        'packages'  : [
            BASED_ON_FIELD, {
                'field' : [GET_PKG_FROM_SCM, {
                        'field'     : 'scm',
                        }],
                'key'   : 'name',
                }
            ],
        },
    'services'  : {
        # how to identify services?
        },
    }

########NEW FILE########
__FILENAME__ = base
'''
Created on 2013-3-27

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Ken
'''

import subprocess
import logging
import re

from pysa.exception import *
from pysa.scanner.object.package import Package
from pysa.scanner.object.file import File
from pysa.scanner.object.user import User
from pysa.scanner.object.service import Service
from pysa.scanner.object.repository import Repository
from pysa.scanner.object.group import Group
from pysa.scanner.object.cron import Cron
from pysa.scanner.object.host import Host
from pysa.scanner.object.mount import Mount
from pysa.scanner.object.sshkey import SSHKey
from pysa.scanner.object.source import Source
from pysa.scanner.object.process import Process


class ScannerBase():
    def __init__(self, packages, files, crons, groups, mounts, hosts, repos, services, sshkeys, users, ips, sources, proces):
        self.packages = packages
        self.files = files
        self.crons = crons
        self.groups = groups
        self.mounts = mounts
        self.hosts = hosts
        self.repos = repos
        self.services = services
        self.keys = sshkeys
        self.users = users
        self.ips = ips
        self.sources = sources
        self.proces = proces

    def scan(self):
        '''
        Implement in ScannerYum, ScannerApt...
        '''
        pass

    @GeneralException
    def subprocess(self, command):
        logging.info('ScannerBase.subprocess(): Command, %s' % str(command))
        try:
            # redirect the err to /dev/null
            devnull = open('/dev/null', 'w')
            p = subprocess.Popen(
                                 command,
                                 close_fds=True,
                                 stdout=subprocess.PIPE,
                                 stderr=devnull
                                 )
            return self.__generator(p.stdout)
        except OSError:
            logging.debug("ScannerBase.subprocess(): commnand failed, command: %s" % str(command))
            return

    @GeneralException
    def __generator(self, stdout):
        for line in stdout:
            yield line

    @GeneralException
    def add_package(self, *args, **kargs):
        _package = Package(*args, **kargs)

        if self.rules:
            # attribute filter
            if _package.attr_filter(self.rules['discard']): return
            # additional filter
            _package.add_filter(self.rules['addition'])

        self.packages[_package.primaryvalue] = _package.prase()

    @GeneralException
    def get_packages(self):
        return self.packages

    @GeneralException
    def add_file(self, *args, **kargs):
        _file = File(*args, **kargs)

        if self.rules:
            if _file.attr_filter(self.rules['discard']): return
            _file.add_filter(self.rules['addition'])

        self.files[_file.primaryvalue] = _file.prase()

    @GeneralException
    def get_files(self):
        return self.files

    @GeneralException
    def add_user(self, *args, **kargs):
        _user = User(*args, **kargs)

        if self.rules:
            if _user.attr_filter(self.rules['discard']): return
            _user.add_filter(self.rules['addition'])

        self.users[_user.primaryvalue] = _user.prase()

    @GeneralException
    def get_users(self):
        return self.users

    @GeneralException
    def add_service(self, *args, **kargs):
        _service = Service(*args, **kargs)

        if self.rules:
            if _service.attr_filter(self.rules['discard']): return
            _service.add_filter(self.rules['addition'])

        self.services[_service.primaryvalue] = _service.prase()

    @GeneralException
    def get_services(self):
        return self.services

    @GeneralException
    def add_repo(self, *args, **kargs):
        _repo = Repository(*args, **kargs)  

        if self.rules:     
            if _repo.attr_filter(self.rules['discard']): return
            _repo.add_filter(self.rules['addition'])

        self.repos[_repo.primaryvalue] = _repo.prase()

    @GeneralException
    def get_repos(self):
        return self.repos

    @GeneralException
    def add_group(self, *args, **kargs):
        _group = Group(*args, **kargs)

        if self.rules:
            if _group.attr_filter(self.rules['discard']): return
            _group.add_filter(self.rules['addition'])

        self.groups[_group.primaryvalue] = _group.prase()

    @GeneralException
    def get_groups(self):
        return self.groups

    @GeneralException
    def add_cron(self, *args, **kargs):
        _cron = Cron(*args, **kargs)

        if self.rules:
            if _cron.attr_filter(self.rules['discard']): return
            _cron.add_filter(self.rules['addition'])

        self.crons[_cron.primaryvalue] = _cron.prase()

    @GeneralException
    def get_crons(self):
        return self.crons

    @GeneralException
    def add_host(self, *args, **kargs):
        _host = Host(*args, **kargs)

        if self.rules:
            if _host.attr_filter(self.rules['discard']): return
            _host.add_filter(self.rules['addition'])

        self.hosts[_host.primaryvalue] = _host.prase()

    @GeneralException
    def get_hosts(self):
        return self.hosts

    @GeneralException
    def add_mount(self, *args, **kargs):
        _mount = Mount(*args, **kargs)

        if self.rules:
            if _mount.attr_filter(self.rules['discard']): return
            _mount.add_filter(self.rules['addition'])

        self.mounts[_mount.primaryvalue] = _mount.prase()

    @GeneralException
    def get_mounts(self):
        return self.mounts

    @GeneralException
    def add_key(self, *args, **kargs):
        _key = SSHKey(*args, **kargs)

        if self.rules:
            if _key.attr_filter(self.rules['discard']): return
            _key.add_filter(self.rules['addition'])
            
        self.keys[_key.primaryvalue] = _key.prase()

    @GeneralException
    def get_keys(self):
        return self.keys

    @GeneralException
    def add_ip(self, mip):
        self.ips.append(mip)

    @GeneralException
    def get_ips(self):
        return self.ips

    @GeneralException
    def add_source(self, *args, **kargs):
        _source = Source(*args, **kargs)

        if self.rules:
            if _source.attr_filter(self.rules['discard']): return
            _source.add_filter(self.rules['addition'])

        self.sources[_source.primaryvalue] = _source.prase()

    @GeneralException
    def get_sources(self):
        return self.sources

    @GeneralException
    def add_proc(self, *args, **kargs):
        _process = Process(*args, **kargs)

        if self.rules:
            if _process.attr_filter(self.rules['discard']): return
            _process.add_filter(self.rules['addition'])

        self.proces[_process.primaryvalue] = _process.prase()

    @GeneralException
    def get_proces(self):
        return self.proces

    @GeneralException
    def init_filter(self, rules=None):
        """
        init the filter rules
        """
        
        self.rules = rules

        if self.rules:  # init the discard and addition rules if not
            if 'discard' not in self.rules: self.rules['discard'] = {}
            if 'addition' not in self.rules: self.rules['addition'] = {}

########NEW FILE########
__FILENAME__ = cron
'''
Scan cron files

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Michael
'''

import logging
import os

from pysa.scanner.actions.base import ScannerBase


class ScannerCron(ScannerBase):
    def scan(self):

        users = self.get_users()
        res = self.subprocess(['crontab', '-l'])
        for line in res:
            # ignore empty and the comment lines
            if not line.strip() or line.strip().startswith("#"): continue

            ary = line.split()
            if ary[5] in users.keys():
                paths = os.path.split(ary[6])
                self.add_cron(
                              name=paths[1],
                              command=" ".join(ary[6:]),
                              environment=paths[0],
                              user=ary[5],
                              minute=ary[0],
                              hour=ary[1],
                              monthday=ary[2],
                              month=ary[3],
                              weekday=ary[4]
                              )
            else:
                paths = os.path.split(ary[5])
                self.add_cron(
                              name=paths[1],
                              command=" ".join(ary[5:]),
                              environment=paths[0],
                              minute=ary[0],
                              hour=ary[1],
                              monthday=ary[2],
                              month=ary[3],
                              weekday=ary[4]
                              )

########NEW FILE########
__FILENAME__ = file
'''
Created on 2013-3-31

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Michael
'''

import os
import re
import logging

from pysa.config import *
from pysa.scanner.actions.utils import *
from pysa.scanner.actions.base import ScannerBase


class ScannerFile(ScannerBase):

    suf_list = ['.conf', '.cfg', '.ini']
    
    def scan(self):
        """
        scan config files
        """

        logging.info('searching for config files')

        # scan the system directories
        self.scandir(Config.files_path)
        
    # scan directory and add config files
    def scandir(self, pathdir): 
        # Visit every file in pathdir except those on the exclusion list above.
        pathdirs = re.split(":", pathdir)
        for p in pathdirs:
            if not p: continue
            for dirpath, dirnames, filenames in os.walk(p, followlinks=True):
                for filename in filenames:
                    self.addfile(os.path.join(dirpath, filename))

    # add per config file
    def addfile(self, pathname):
        # only plane text file
        if valid_txtfile(pathname) == False:     
            return

#        # only include above suffix config file
#        suf = os.path.splitext(pathname)[1]
#        if suf is None or suf not in self.suf_list:
#            return

        # get owner, group and mode
        s = get_stat(pathname)
        
        # read the config file's content
        c = get_content(pathname)

        # add the config file:
        # checksum, content, group, mode, owner, path, force=False, provider=None, 
        # recurse=None, recurselimit=None, source=None
        self.add_file('md5', c, s[0], s[1], s[2], pathname)

########NEW FILE########
__FILENAME__ = gem
'''
Created on 2013-3-29

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Michael
'''

import glob
import logging
import re
import os

from pysa.scanner.actions.utils import *
from pysa.scanner.actions.base import ScannerBase

class ScannerGem(ScannerBase):

    def scan(self):
        """
        scan gem
        """
        logging.info('searching for Ruby gems')

        # Precompile a pattern for extracting the version of Ruby that was used
        # to install the gem.
        pattern = re.compile(r'gems/([^/]+)/gems')

        # Look for gems in all the typical places.  This is easier than looking
        # for `gem` commands, which may or may not be on `PATH`.
        for globname in ('/usr/lib/ruby/gems/*/gems',
                         '/usr/lib64/ruby/gems/*/gems',
                         '/usr/local/lib/ruby/gems/*/gems',
                         '/var/lib/gems/*/gems'):
            for dirname in glob.glob(globname):
                # The `ruby1.9.1` (really 1.9.2) package on Maverick begins
                # including RubyGems in the `ruby1.9.1` package and marks the
                # `rubygems1.9.1` package as virtual.  So for Maverick and
                # newer, the manager is actually `ruby1.9.1`.
                match = pattern.search(dirname)
                if '1.9.1' == match.group(1) and rubygems_virtual():
                    manager = 'ruby{0}'.format(match.group(1))

                # Oneiric and RPM-based distros just have one RubyGems package.
                elif rubygems_unversioned():
                    manager = 'rubygems'

                # Debian-based distros qualify the package name with the version
                # of Ruby it will use.
                else:
                    manager = 'rubygems{0}'.format(match.group(1))

                for entry in os.listdir(dirname):
                    try:
                        package, version = entry.rsplit('-', 1)

                    except ValueError:
                        logging.warning('skipping questionably named gem {0}'.
                                        format(entry))
                        continue

                    self.add_package(package, manager=manager, version=version, provider='gem')

########NEW FILE########
__FILENAME__ = group
'''
Created on 2013-4-4

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Ken
'''

import logging
import grp

from pysa.scanner.actions.base import ScannerBase


class ScannerGroup(ScannerBase):
    
    def scan(self):
        for g in grp.getgrall():
            name, password, gid, member = g
            self.add_group(name=name, gid=gid, member=member)

########NEW FILE########
__FILENAME__ = host
'''
Created on 2013-04-03

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Michael
'''

import re
import logging
import os

from pysa.config import *
from pysa.scanner.actions.base import ScannerBase


class ScannerHost(ScannerBase):

    def scan(self):
        """
        scan host:
        parse the host config file (usually /etc/hosts)
        """
        logging.info('searching for hosts')
        hostlst = self.parse_hostfile()

        if len(hostlst)<=0:
            return

        for dict in hostlst:
            self.add_host(ip=dict['ip'], name=dict['name'],
                target=dict['target'], host_aliases=dict['host_aliases'])

    def parse_hostfile(self):
        hostfile = Config.scan_host

        hosts = []
        try:
            for line in open(hostfile):
                # ignore blank line
                if not line.strip(): continue
                # ignore comment line
                elif line.strip().startswith("#"): continue

                itemlst = line.strip().split()
                if len(itemlst) <= 1: continue

                hosts.append({'ip':itemlst[0], 'name':itemlst[1], 'target':hostfile, 'host_aliases':itemlst[2:]})

                #ip = re.search( r'[0-9]+(?:\.[0-9]+){3}', itemlst[0] )
                #if ip==None:
                #    continue
                #aliases = []
                #if len(itemlst)>=3:
                #    for i in range(2, len(itemlst)-1):
                #        aliases.append(itemlst[i])
                #print "aliases=%s"%aliases
                #hosts.append({'ip':ip.group(), 'name':itemlst[1], 'target':hostfile, 'host_aliases':aliases})

        except IOError:
            return hosts

        return hosts

########NEW FILE########
__FILENAME__ = mount
'''
Scans mount points

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Michael
'''

import logging
import os

from pysa.scanner.actions.base import ScannerBase


class ScannerMount(ScannerBase):
    
    def scan(self):
        self.__disk_usage()
    
    def __disk_partitions(self,all=False):  
        """
        Return all mountd partitions as a dict.    
        """  
        phydevs = []  
        f = open("/proc/filesystems", "r")  
        for line in f:  
            if not line.startswith("nodev"):  
                phydevs.append(line.strip())  
      
        retlist = {} 
        f = open('/etc/mtab', "r")  
        for line in f:  
            if not all and line.startswith('none'):
                continue
            fields                 = line.split()  
            device                 = fields[0]  
            mountpoint             = fields[1]  
            fstype                 = fields[2]  
            if not all and fstype not in phydevs:  
                continue  
            if device == 'none':  
                device             = ''
            retlist[device]        = (device, mountpoint, fstype)
        return retlist  
    
    def __disk_usage(self):  
        """Return disk usage associated with path."""  
        disk                     = self.__disk_partitions()
        for device in disk.keys():
            st = os.statvfs(device)
            size = st.f_blocks * st.f_frsize
            self.add_mount(device=device, fstype=disk[device][2], name=disk[device][1], size=size)

########NEW FILE########
__FILENAME__ = npm
'''
Created on 2013-3-29

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Michael
'''

import re
import logging

from pysa.scanner.actions.base import ScannerBase


class ScannerNpm(ScannerBase):
    def scan(self):
        """
        scan apt
        """
        logging.info('searching for npm packages')

        # Precompile a pattern for parsing the output of `npm list -g`.
        pattern = re.compile(r'^\S+ (\S+)@(\S+)$')

        lines = self.subprocess(['npm', 'ls', '-g'])    # only list global packages
        for line in lines:
            match = pattern.match(line.rstrip())
            if match is None:
                continue
            package, version = match.group(1), match.group(2)
            manager='nodejs'

            self.add_package(package, manager=manager, version=version, provider='npm')

########NEW FILE########
__FILENAME__ = package
'''
Created on 2013-04-10

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Michael
'''

import re
import os.path
import logging
import subprocess

from pysa.config import Config

from pysa.scanner.actions.utils import *
from pysa.scanner.actions.base import ScannerBase


# define the scan modes
scan_modes = ['yum', 'rpm', 'sub_rpm', 'apt', 'sub_dpkg']

class ScannerPackage(ScannerBase):
    def scan(self):
        """
        scan package
        first search with yum, next with apt and with subprocess at last
        """
        logging.info('searching for packages')

        self.core_pkgs = {}
        self.user_pkgs = {}
        self.ip_list = []

        if self.scan_yum()==False:
           if self.scan_rpm()==False:
                if self.scan_apt()==False:
                    self.scan_subprocess()
                else: Config.platform = "apt"
           else: Config.platform = "rpm"
        else: Config.platform = "yum"

        # add the user package list
        self.add_pkgs()

        # add ips
        for ip in self.ip_list:
            self.add_ip(ip)

    def scan_yum(self):
        """
        scan the redhat family platform with yum api
        """
        try:
            import yum
        except ImportError:
            return False

        logging.info('searching for yum packages')

        self.scan_mode = 'yum'

        yb = yum.YumBase()
        # get all installed packages and check each's dependency
        yb.conf.cache = 1
        for pkg in sorted(yb.rpmdb.returnPackages()):
            pkgtag = pkg.__str__()

            # skip the package which is in the core package list
            if pkgtag in self.core_pkgs:
                continue

            reqs = pkg.required_packages()
            # remove packages which is in the requiring list from user packages
            # and add packages which is not in core packages from dependency list
            for req in reqs:
                reqtag = req.__str__()
                if reqtag in self.user_pkgs:
                    del self.user_pkgs[reqtag]

                if reqtag not in self.core_pkgs:
                    self.core_pkgs[reqtag] = req

            thepkg = yb.pkgSack.searchNevra(pkg.name, pkg.epoch, pkg.version, pkg.release, pkg.arch)  #epoch=None, ver=None, rel=None, arch=None
            if len(thepkg)==0 or thepkg[0].verEQ(pkg)==False:
                continue

            self.user_pkgs[pkgtag] = pkg

        return True

    def scan_rpm(self):
        """
        scan the redhat family platform with rpm api
        """
        try:
            import rpm
        except ImportError:
            return False

        logging.info('searching for rpm packages')

        self.scan_mode = 'rpm'

        ts = rpm.TransactionSet()
        mi = ts.dbMatch()
        for h in mi:
            if h[rpm.RPMTAG_EPOCH]==None:
                epoch = '(none)'
            pkgtag = '%s-%s-%s.%s-%s' % (h[rpm.RPMTAG_NAME], h[rpm.RPMTAG_VERSION],
                h[rpm.RPMTAG_RELEASE], h[rpm.RPMTAG_ARCH], epoch)

            # skip the package in the core package list already
            if pkgtag in self.core_pkgs:
                continue

            # query the package dependency
            for req in h[rpm.RPMTAG_REQUIRENAME]:
                if req.find(' ')>=0:
                    req = req[0:req.find(' ')]
                if req.startswith('rpmlib'):    continue

                try:
                    p = subprocess.Popen(['rpm',
                                      '-q',
                                      '--qf=%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}-%{EPOCH}',
                                      '--whatprovides',
                                      req],
                                     close_fds=True,
                                     stdout=subprocess.PIPE)
                    reqtag, stderr = p.communicate()
                    # ignore the package itself
                    if reqtag==pkgtag: continue
                except OSError: continue

                if reqtag in self.user_pkgs:
                    del self.user_pkgs[reqtag]
                if reqtag not in self.core_pkgs:
                    self.core_pkgs[reqtag] = req   ### need to query the req_pkg's header

                self.user_pkgs[pkgtag] = h

        return True

    def scan_apt(self):
        """
        searching at the debian family platform with apt package
        http://apt.alioth.debian.org/python-apt-doc/
        """
        try:
            import apt
        except ImportError:
            return False

        logging.info('searching for Apt packages')

        self.scan_mode = 'apt'

        apt_cache = apt.Cache()
#        apt_cache.update()
#        apt_cache.open()

        DEP_TYPES = ['Depends', 'Recommends', 'Suggests', 'Replaces', 'Enhances']

        for package_name in apt_cache.keys():
            pkg = apt_cache[package_name]

            #Verify that the package is installed
            if hasattr(pkg, 'isInstalled'):
                if not pkg.isInstalled:    continue
            elif hasattr(pkg, 'is_installed'):
                if not pkg.is_installed:    continue
            else:
                continue


            pkgid = pkg.id

            for pkgv in pkg.versions:
                deps = self.ext_aptdeps(pkgv, 'Depends')

                for dep in deps:
                    # check the dep_pkg's name
                    if dep.name not in apt_cache: continue
                    # query the dep_pkg
                    dep_pkg = apt_cache[dep.name]

                    depid = dep_pkg.id

                    if hasattr(pkg, 'isInstalled'):
                        if not pkg.isInstalled:    continue
                    elif hasattr(pkg, 'is_installed'):
                        if not pkg.is_installed:    continue
                    else:
                        continue

                    if depid in self.user_pkgs:
                        del self.user_pkgs[depid]

                    if depid not in self.core_pkgs:
                        self.core_pkgs[depid] = dep_pkg

            self.user_pkgs[pkgid] = pkg

        return True

    def ext_aptdeps(self, pkg, dep_type):
        """
        generate the package's dependencies of particular dependency type
        """
        for dep_pkglst in pkg.get_dependencies(dep_type):
            for dep_pkg in dep_pkglst.or_dependencies:
                yield dep_pkg

    def scan_subprocess(self):
        """
        searching package with subprocess
        """
        logging.info('searching with subprocess')

        self.scan_mode = 'sub_rpm'
        Config.platform = 'rpm'
        lines = self.subprocess(['rpm', '--qf=%{NAME}\x1E%{VERSION}\x1E%{RELEASE}\x1E%{ARCH}\x1E%{EPOCH}\x1E%{SUMMARY}\x1E%{VENDOR}\n', '-qa'])
        if lines==None:
            # try apt of the Debian family system
            self.scan_mode = 'sub_dpkg'
            Config.platform = 'apt'

            lines = self.subprocess(['dpkg-query', '-W',
                '-f=${Status}\x1E${Package}\x1E${Version}\x1E${Architecture}\n'])

            if lines==None:
                logging.info('searching packages failed')
                return

        # parse the stdout [michael, 2013/03/28]
        for line in lines:
            if self.scan_mode=='sub_rpm':
                pkg, ver, rel, arch, epo, sum, ven = line.strip().split('\x1E')
                pkg_tag = pkg + '-' + ver + '-' + rel + '.' + arch + '-' +  epo
            elif self.scan_mode=='sub_dpkg':
                status, pkg, ver, arch = line.strip().split('\x1E')
                if 'install ok installed' != status: continue
                pkg_tag = pkg + '-' + ver + '-' + arch
            else:
                return

            if pkg_tag in self.core_pkgs:   continue

            # query the dependency
            self.query_deps(pkg)

            confs = []
            if self.scan_mode=='sub_rpm':
                # query config files
                conffiles = self.subprocess(['rpm', '-qc', pkg])
                for fi in conffiles:
                    file = fi.strip()
                    confs.append(file)

                self.user_pkgs[pkg_tag] = {
                    'name':pkg, 'version':ver, 'release':rel, 'arch':arch, 'epoch':epo, 'summary':sum, 'vendor':ven, 'configs':confs}

            if self.scan_mode=='sub_dpkg':
                conffiles = self.subprocess(['dpkg-query', '-W', '-f=${Conffiles}', pkg])
                for fi in conffiles:
                    file = fi.strip().split(' ')[0]
                    confs.append(file)

                self.user_pkgs[pkg_tag] = {'name':pkg, 'version':ver, 'arch':arch, 'configs':confs}

    def add_conffile(self, filepath):
        """
        check and add the package's config file
        """
        ### config file(in 'etc' directory)
        if filepath.startswith(('/etc/', '/home/'))==False:
            return False
        ### suffix list[conf, cfg, ini]
        filename, suffix = os.path.splitext(filepath)
        if suffix not in ['.conf', '.cfg', '.ini']:
            return False

        # get the config file's information and add it
        # only plane text file
        if valid_txtfile(filepath) == False:
            return False

        # get owner, group and mode
        s = get_stat(filepath)

        # read the config file's content
        c = get_content(filepath)

        # add the config file:
        # checksum, content, group, mode, owner, path, force=False, provider=None,
        # recurse=None, recurselimit=None, source=None
        self.add_file('md5', c, s[0], s[1], s[2], filepath)

        return True

    def query_deps(self, package):
        """
        query package's denpendency in the list and update the user/core package list
        """

        if self.scan_mode == 'sub_rpm':
            reqs = self.subprocess(['rpm', '-qR', package])

            for req in reqs:
                req = req.strip()
                # query the dependency package
                infos = self.subprocess(['rpm', '-q',
                    '--qf=%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}-%{EPOCH}\n',
                    '--whatprovides', req])

                for info in infos:
                    dep_tag = info.strip().split('\x1E')[0]

                    # check dependency package whether in the user package list
                    if dep_tag in self.user_pkgs: del self.user_pkgs[dep_tag]

                    # check dependency package whether in the core package list
                    if dep_tag not in self.core_pkgs: self.core_pkgs[dep_tag] = dep_tag

        elif self.scan_mode == 'sub_dpkg':
            # query the dependency
            deplines = self.subprocess(['dpkg-query', '-W', '-f=${Depends}\n', package])

            for line in deplines:
                deps = re.split(', |\|', line.strip())

                for dep in deps:
                    if dep.find(' '):
                        dep = dep[0:dep.find(' ')]

                    infos = self.subprocess(['dpkg-query', '-W',
                        '-f=${Status}\x1E${Package}-${Version}-${Architecture}\n', dep])
                    for line in infos:
                        status, dep_tag = line.strip().split('\x1E')

                        if 'install ok installed' != status:    continue

                        if dep_tag in self.user_pkgs:
                            del self.user_pkgs[dep_tag]

                        if dep_tag not in self.core_pkgs:
                            self.core_pkgs[dep_tag] = dep_tag

        else:
            return

    @property
    def user_pkgs(self):
        return self.user_pkgs

    @property
    def core_pkgs(self):
        return self.core_pkgs

    @property
    def ip_list(self):
        return self.ip_list

    def add_user_pkg(self, pkg_tag, pkg):
        self.user_pkgs[pkg_tag] = pkg

    def add_core_pkg(self, pkg_tag, pkg):
        self.core_pkgs[pkg_tag] = pkg

    def add_ips(self, ex_ips):
        self.ip_list = list(set(self.ip_list+ex_ips))

    @property
    def scan_mode(self):
        return self.scan_mode

    def set_scan_mode(self, mode):
        if mode not in scan_modes:
            self.scan_mode = 'yum'
        else:
            self.scan_mode = mode

    def add_pkgs(self):
        """
        add packages
        """
        if self.scan_mode=='yum' or self.scan_mode=='rpm':
            try:
                import rpm
            except ImportError:
                return

            ts = rpm.TransactionSet()
            for (pkg_tag, pkg) in self.user_pkgs.items():
                if self.scan_mode == 'yum':
                    name = pkg.name
                if self.scan_mode == 'rpm':
                    name = pkg[rpm.RPMTAG_NAME]

                ### search the yum api of searching package's config files
                mi = ts.dbMatch('name', name)
                for h in mi:
                    # save the config files
                    confs = []

                    fi = h.fiFromHeader()
                    for file in fi:
                        fipath = file[0]

                        if fipath in confs:
                            continue

                        if self.add_conffile(fipath)==False:
                            continue

                        tmpips = get_ips(fipath)
                        self.add_ips(tmpips)

                        confs.append(fipath)

                    # get the epoch
                    #epoch = h['epoch'] if h['epoch'] else 0

                    # add package
                    self.add_package(name, manager='yum', provider='yum', files=confs,
                                description=h['summary'], platform=h['arch'],
                                version=h['version']+'-'+h['release'], vendor=h['vendor'])

        elif self.scan_mode=='apt':
            for (id, pkg) in self.user_pkgs.items():

                # pkg's config files
                confs = []
                fi = pkg.installed_files
                for file in fi:
                    if file in confs: continue

                    if self.add_conffile(file)==False: continue

                    tmpips = get_ips(file)
                    self.add_ips(tmpips)

                    confs.append(file)

                for pkgv in pkg.versions:
                    self.add_package(pkg.shortname, manager='apt', provider='apt', files=confs,
                        description=pkgv.summary, platform=pkgv.architecture, version=pkgv.version)

        elif self.scan_mode=='sub_rpm':
            for (tag, info) in self.user_pkgs.items():
                #'name':name, 'version':ver, 'release':rel, 'arch':arch, 'epoch':epo, 'summary':sum, 'vendor':ven, 'configs':confs

                confs = []
                # parse the ips
                for file in info['configs']:
                    if file in confs: continue

                    if self.add_conffile(file)==False: continue

                    tmpips = get_ips(file)
                    self.add_ips(tmpips)

                    confs.append(file)

                #epoch = info['epoch'] if info['epoch'] else 0
                # add the package
                self.add_package(info['name'], manager='rpm', provider='rpm', files=confs,
                                 description=info['summary'], platform=info['arch'], version=info['version']+'-'+info['release'])

        elif self.scan_mode=='sub_dpkg':
            for (tag, info) in self.user_pkgs.items():
                confs = []
                for file in info['configs']:
                    #{'name':name, 'version':ver, 'arch':arch, 'description':desc, 'configs':conffiles}
                    if file in confs: continue

                    if self.add_conffile(file)==False: continue

                    tmpips = get_ips(file)
                    self.add_ips(tmpips)

                    confs.append(file)

                self.add_package(info['name'], manager='dpkg', provider='dpkg',
                                 files=confs, version=info['version'])


########NEW FILE########
__FILENAME__ = php
'''
Created on 2013-3-29

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Michael
'''

import logging
import re

from pysa.scanner.actions.utils import *
from pysa.scanner.actions.base import ScannerBase


class ScannerPhp(ScannerBase):
    def scan(self):
        """
        scan php
        """
        logging.info('searching for PEAR/PECL packages')

        # Precompile a pattern for parsing the output of `{pear,pecl} list`.
        pattern = re.compile(r'^([0-9a-zA-Z_]+)\s+([0-9][0-9a-zA-Z\.-]*)\s')

        # PEAR packages are managed by `php-pear` (obviously).  PECL packages
        # are managed by `php5-dev` because they require development headers
        # (less obvious but still makes sense).
        if lsb_release_codename() is None:
            pecl_manager = 'php-devel'
        else:
            pecl_manager = 'php5-dev'
        for manager, progname in (('php-pear', 'pear'),
                                  (pecl_manager, 'pecl')):

            lines = self.subprocess([progname, 'list'])
            if lines==None:
                return
                
            for line in lines:
                match = pattern.match(line)
                if match is None:
                    continue
                package, version = match.group(1), match.group(2)
                
                self.add_package(package, manager=manager, version=version, provider=progname)

########NEW FILE########
__FILENAME__ = process
'''
Created on 2013-04-19

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Michael
'''

import logging
import subprocess

from pysa.scanner.actions.base import ScannerBase


class ScannerProcess(ScannerBase):

    def scan(self):
        """
        scan process
        """
        logging.info('searching for process')

        self.get_processes()

    def get_processes(self):
        """
        get all the process info
        """

        try:
            p = subprocess.Popen(['-c', 'ps -eo pid,fuser,s,pcpu,pmem,comm,ppid'], shell=True, stdout=subprocess.PIPE)

            first = True
            for line in p.stdout:
                if first:   # ignore the headline
                    first = False
                    continue

                lst = line.strip().split()

                # check data completeness
                nonlst = [info for info in lst if info is None]
                if len(nonlst)>0: continue

                self.add_proc(lst[0], lst[1], lst[2], lst[3], lst[4], lst[5], lst[6])

        except OSError:
            return

    def get_accounts(self):
        """
        parse the system accounts config file('/etc/passwd')
        """

        try:
            data = open('/etc/passwd').read()
            for line in data:
                att = line.strip().split(':')
                if att[0] is not None and att[2] is not None:
                    self.add_accout(att[2], att[0])
        except IOError:
            return False

        return True

    @property
    def accounts(self):
        if accounts not in self:
            self.accounts = {}

        return self.accounts

    def add_accout(self, uid, name):
        if uid not in self.accounts:
            self.accounts[uid] = name

########NEW FILE########
__FILENAME__ = pypi
'''
Created on 2013-3-29

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Michael
'''

import glob
import logging
import os
import re
import subprocess

from pysa.scanner.actions.base import ScannerBase


# Precompile a pattern to extract the manager from a pathname.
PATTERN_MANAGER = re.compile(r'lib/(python[^/]*)/(dist|site)-packages')

# Precompile patterns for differentiating between packages built by
# `easy_install` and packages built by `pip`.
PATTERN_EGG = re.compile(r'\.egg$')
PATTERN_EGGINFO = re.compile(r'\.egg-info$')

# Precompile a pattern for extracting package names and version numbers.
PATTERN = re.compile(r'^([^-]+)-([^-]+).*\.egg(-info)?$')

class ScannerPypi(ScannerBase):

    def scan(self):
        """
        scan pypi
        """
        logging.info('searching for Python packages')

        # Look for packages in the typical places.
        globnames = ['/usr/lib/python*/dist-packages',
                     '/usr/lib/python*/site-packages',
                     '/usr/local/lib/python*/dist-packages',
                     '/usr/local/lib/python*/site-packages']
        virtualenv = os.getenv('VIRTUAL_ENV')
        if virtualenv is not None:
            globnames.extend(['{0}/lib/python*/dist-packages'.format(virtualenv),
                              '{0}/lib/python*/dist-packages'.format(virtualenv)])
        for globname in globnames:
            for dirname in glob.glob(globname):
                manager = PATTERN_MANAGER.search(dirname).group(1)
                for entry in os.listdir(dirname):
                    match = PATTERN.match(entry)
                    if match is None:
                        continue
                    package, version = match.group(1, 2)
                    
                    pathname = os.path.join(dirname, entry)

                    # Symbolic links indicate this is actually a system package
                    # that injects files into the PYTHONPATH.
                    if os.path.islink(pathname): continue

                    # check pathname
                    if not os.path.isdir(pathname):
                        pathname = os.path.join(dirname, package)
                        if not os.path.exists(pathname): continue

                    # installed via `easy_install`.
                    if PATTERN_EGG.search(entry):
                        self.add_package(package, manager='python', version=version, provider='pip')

                    # installed via `pip`.
                    elif PATTERN_EGGINFO.search(entry):
                        self.add_package(package, manager='pip', version=version, provider='pip')                    

########NEW FILE########
__FILENAME__ = repository
'''
Created on 2013-04-18

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Michael
'''

import os
import logging

from pysa.scanner.actions.utils import *
from pysa.scanner.actions.base import ScannerBase


class ScannerRepo(ScannerBase):

    def scan(self):
        """
        scan for repository config files
        """
        logging.info('searching for repository config files')

        if os.path.exists('/etc/yum.repos.d'):
            self.scan_yum()
        elif os.path.exists('/etc/apt'):
            self.scan_apt()

    def scan_yum(self):
        """
        scan yum repo config files
        """

        for dirpath, dirnames, files in os.walk('/etc/yum.repos.d'):
            for file in files:
                root, ext = os.path.splitext(file)
                if ext!='.repo': continue

                self.addfile(os.path.join(dirpath, file), 'yum')

    def scan_apt(self):
        """
        scan apt repo config files
        """

        try:
            with open('/etc/apt/sources.list'): self.addfile('/etc/apt/sources.list', 'apt')
        except IOError:
            return

        if os.path.exists('/etc/apt/sources.list.d'):
            for dirpath, dirnames, files in os.walk('/etc/apt/sources.list.d'):
                for file in files:
                    root, ext = os.path.splitext(file)
                    if ext!='.list': continue

                    self.addfile(os.path.join(dirpath, file), 'apt')


    # add per config file
    def addfile(self, pathname, prov):
        # only plane text file
        if valid_txtfile(pathname) == False:
            return

        # get owner, group and mode
        s = get_stat(pathname)

        # read the config file's content
        c = get_content(pathname)

        # add the config file:
        # checksum, content, group, mode, owner, path, force=False, provider=None,
        # recurse=None, recurselimit=None, source=None
        self.add_repo('md5', c, s[0], s[1], s[2], pathname, provider=prov)

########NEW FILE########
__FILENAME__ = service
'''
Created on 2013-04-03

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Michael
'''

import re
import logging
import os

from pysa.config import *
from pysa.scanner.actions.base import ScannerBase


class ScannerService(ScannerBase):
    # Patterns for determining which Upstart services should be included, based
    # on the events used to start them.
    UPSTART_PATTERN1 = re.compile(r'start\s+on\s+runlevel\s+\[[2345]', re.S)
    UPSTART_PATTERN2 = re.compile(r'start\s+on\s+\([^)]*(?:filesystem|filesystems|local-filesystems|mounted|net-device-up|remote-filesystems|startup|virtual-filesystems)[^)]*\)', re.S)
    
    def scan(self):
        """
        scan service:
        search the service config files
        """
        logging.info('searching for system services')

        for dir in ['/etc/init', 
                    '/etc/init.d',
                    '/etc/rc.d/init.d']:
            for dirname, dirnames, filenames in os.walk(dir):
                for filename in filenames:
                    try:
                        pathname = os.path.join(dirname, filename)
                        dict = self.parse_service(pathname)

                        # add service
                        if dict != None:
                            # format (provider, name, enable, hasrestart)
                            self.add_service(enable=dict['enable'], hasrestart=dict['hasrestart'], 
                                name=dict['name'], path=dirname, provider=dict['provider'], hasstatus=dict['hasstatus'])
                    except ValueError:
                        pass
            
    def parse_service(self, pathname):
        """
        Parse a potential service init script or config file into the
        manager and service name or raise `ValueError`.  Use the Upstart
        "start on" stanzas and SysV init's LSB headers to restrict services to
        only those that start at boot and run all the time.
        
        ###Need to add systemd service parse.
        """
        
        dirname, basename = os.path.split(pathname)
        if '/etc/init' == dirname:
            service, ext = os.path.splitext(basename)
            
            # Ignore extraneous files in /etc/init.
            if '.conf' != ext:
                raise ValueError('not an Upstart config')

            # Ignore services that don't operate on the (faked) main runlevels.
            try:
                content = open(pathname).read()
            except IOError:
                raise ValueError('not a readable Upstart config')
                
            enable = False    
            if (self.UPSTART_PATTERN1.search(content) \
                    or self.UPSTART_PATTERN2.search(content)):
                enable = True

            return {'provider':'upstart', 'name':service, 'enable':enable, 
                'hasrestart':False, 'hasstatus':False}
                
        elif '/etc/init.d' == dirname or '/etc/rc.d/init.d' == dirname:
            #import pdb
            #pdb.set_trace()

            # Let Upstart handle its services.
            if os.path.islink(pathname) \
                and '/lib/init/upstart-job' == os.readlink(pathname):
                raise ValueError('proxy for an Upstart config')

            # Ignore services that don't operate on the main runlevels.
            try:
                content = open(pathname).read()
            except IOError:
                raise ValueError('not a readable SysV init script')
                
            enable = False    
            if re.search(r'(?:Default-Start|chkconfig):\s*[-2345]', content):
                enable = True
            
            hasrestart = False
            if re.search(r'\s*(?:restart|reload)\)\s*', content):
                hasrestart = True
            
            hasstatus = False
            if re.search(r'\s*status\)\s*', content):
                hasstatus = True
            
            return {'provider':'init', 'name':basename, 'enable':enable,
                'hasrestart':hasrestart, 'hasstatus':hasstatus}       ### change sysvinit to init
        else:
            raise ValueError('not a service')

########NEW FILE########
__FILENAME__ = source
'''
Created on 2013-04-09

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Michael
'''

import os
import logging
import subprocess
from collections import defaultdict

from pysa.scanner.actions.utils import *
from pysa.scanner.actions.base import ScannerBase


class ScannerSource(ScannerBase):

    def scan(self):
        """
        scan repository
        """
        logging.info('searching for repository')

        self.user_repos = {'git':[], 'svn':[], 'hg':[]}    # save all the scm repos

        self.search_scm('/')
        #self.search_scm('svn', '/')
        #self.search_scm('hg', '/')
        self.add_repos()

    def search_scm(self, dir):
        """
        search all scm repositories in local directory dirname
        """
        for dirpath, dirnames, filenames in os.walk(dir):
            for dirname in dirnames:
                if dirname == '.git':
                    scm = 'git'
                elif dirname == '.svn':
                    scm = 'svn'
                elif dirname == '.hg':
                    scm = 'hg'
                else:
                    continue

                if scm=='svn':  #if svn scm, need to check subdirctory
                    head, tail = os.path.split(dirpath)
                    while head and tail:
                        if head in self.user_repos['svn']:
                            break
                        head, tail = os.path.split(head)
                    else:
                        subsvn = [ scmdir for scmdir in self.user_repos['svn'] if dirpath in scmdir ]
                        if len(subsvn)>0:
                            for subdir in subsvn: self.user_repos['svn'].remove(subdir)

                        self.add_local_repo(scm, dirpath)
                else:
                    self.add_local_repo(scm, dirpath)

    def add_repos(self):
        """
        get the repository info and add repo
        """
        for (scm, dirs) in self.user_repos.items():
            for dirname in dirs:
                sources = []    # http/ssh
                branches = []

                try:
                    if scm=='git':
                        p = subprocess.Popen(['-c', 'git --git-dir=' + dirname + '/.git --work-tree=' + dirname+' remote -v'],
                            stdout=subprocess.PIPE, shell=True)
                        for line in p.stdout:
                            src = line.split('\t')[1].split(' ')[0]
                            if src is not None and src not in sources:
                                sources.append(src)

                        # branches
                        p = subprocess.Popen(['-c', 'git --git-dir=' + dirname + '/.git --work-tree=' + dirname + ' branch'],
                            stdout=subprocess.PIPE, shell=True)
                        for line in p.stdout:
                            if line is not None:
                                lst = line.strip().split()
                                for br in lst:
                                    if br is not None and br!='*':
                                        branches.append(br)

                    elif scm=='svn':
                        p = subprocess.Popen(['-c', 'svn info ' + dirname + ' | grep URL | awk \'{print $NF}\''],
                            shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

                        for source in p.stdout:
                            if source is not None: sources.append(source.strip())

                        ### branches
                    elif scm=='hg':
                        # sources
                        p = subprocess.Popen(['-c', 'hg paths -R' + dirname], shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                        for line in p.stdout:
                            source = line.split('=')[1].strip()
                            if source is not None and source not in sources: sources.append(source)
                        # branches
                        p = subprocess.Popen(['-c', 'hg branches -R' + dirname], shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                        for line in p.stdout:
                            branch = line.strip().split(' ')[0]
                            if branch is not None and branch not in branches: branches.append(branch)
                    else:
                        continue

                except OSError:
                    continue

                # add the public info
                s = get_stat(dirname)

                if len(sources)<=0: continue

                self.add_source(sources[0], os.path.basename(dirname), dirname, s[2], s[0], s[1], scm, branches)

    @property
    def user_repos(self):
        """
        local repos
        """
        if user_repos not in self:
            self.user_repos = defaultdict(list)

        return self.user_repos

    def add_local_repo(self, scm, dirname):
        """
        add all repos to local repos
        """
        if scm not in self.user_repos:
            self.user_repos[scm] = []

        self.user_repos[scm].append(dirname)

########NEW FILE########
__FILENAME__ = sshkey
'''
Get SSH keys

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Michael
'''

import logging
import os
import re

from pysa.config import Config
from pysa.scanner.actions.base import ScannerBase
from pysa.scanner.actions.utils import *


class ScannerKey(ScannerBase):
    
    support_key_type = [
                        'ssh-rsa',
                        'ssh-dss',
                        'ecdsa-sha2-nistp256',
                        'ecdsa-sha2-nistp384',
                        'ecdsa-sha2-nistp521'
                        ]
    
    scan_file_type = [
                      '.pub',
                      '.pem'
                      ]
    
    re_pattern = "-----.+-----"

    path_dir = Config.key_path

    def scan(self):
        pathdirs = re.split(":", self.path_dir)
        for p in pathdirs:
            if not p: continue
            for dirpath, dirnames, filenames in os.walk(p):
                for filename in filenames:
                    try:
                        # key with specific name
                        if '.' in filename:
                            for file_type in self.scan_file_type:
                                if filename.endswith(file_type):
                                    full_path = os.path.join(dirpath, filename)
                                    mode = get_stat(full_path)[1]
                                    content = get_content(full_path)
                                    if content:
                                        _type = self.__get_type(content)
                                        self.add_key(key=content, name=filename, _type=_type, path=full_path, mode=mode)
                                        logging.debug('ScannerKey.scan(): Add key file %s' % filename)
                        # key without specific name
                        else:
                            full_path = os.path.join(dirpath, filename)
                            mode = get_stat(full_path)[1]
                            content = get_content(full_path)
                            if content and re.match(self.re_pattern, content):
                                _type = self.__get_type(content)
                                self.add_key(key=content, name=filename, _type=_type, path=full_path, mode=mode)
                                logging.debug('ScannerKey.scan(): Add key file %s' % filename)
                    except Exception, e:
                        #log
                        logging.error("ScannerKey.scan(): Add file %s failed, %s" % (filename, str(e)))

    def __get_type(self, content):
        for _type in self.support_key_type:
            if _type in content:
                return _type

########NEW FILE########
__FILENAME__ = user
'''
Created on 2013-4-4

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Ken
'''

import logging
import pwd
import grp

from pysa.scanner.actions.base import ScannerBase


class ScannerUser(ScannerBase):
    def scan(self):
        for p in pwd.getpwall():
            name, password, uid, gid, gecos, home, shell = p

            groups = [] 
            # get the secondary groups
            for gr in grp.getgrall():
                gr_name, gr_pwd, gr_gid, gr_mem = gr
                # check whether the main group
                if gid == gr_gid:   
                    group = gr_name
                    continue
                # check whether the group member
                if name in gr_mem:
                    groups.append(gr_name)

            if group is None or not group: continue

            self.add_user(name=name, uid=uid, gid=gid, group=group, groups=groups, shell=shell, home=home)

########NEW FILE########
__FILENAME__ = utils
'''
Created on 2013-3-28

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Ken
'''

import re
import os
import stat
import pwd
import grp
import subprocess
import logging
import string


PAT_IP = re.compile(r'^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$', re.S)
TEXT_CHARACTERS = "".join(map(chr, range(32, 127)) + list("\n\r\t\b"))
NULL_TRANS = string.maketrans("", "")

def lsb_release_codename():
    """
    Return the OS release's codename.
    """
    if hasattr(lsb_release_codename, '_cache'):
        return lsb_release_codename._cache
    try:
        p = subprocess.Popen(['lsb_release', '-c'], stdout=subprocess.PIPE)
    except OSError:
        lsb_release_codename._cache = None
        return lsb_release_codename._cache
    stdout, stderr = p.communicate()
    if 0 != p.returncode:
        lsb_release_codename._cache = None
        return lsb_release_codename._cache
    match = re.search(r'\t(\w+)$', stdout)
    if match is None:
        lsb_release_codename._cache = None
        return lsb_release_codename._cache
    lsb_release_codename._cache = match.group(1)
    return lsb_release_codename._cache

def rubygems_unversioned():
    """
    Determine whether RubyGems is suffixed by the Ruby language version.
    It ceased to be on Oneiric.  It always has been on RPM-based distros.
    """
    codename = lsb_release_codename()
    return codename is None or codename[0] >= 'o'

def rubygems_virtual():
    """
    Determine whether RubyGems is baked into the Ruby 1.9 distribution.
    It is on Maverick and newer systems.
    """
    codename = lsb_release_codename()
    return codename is not None and codename[0] >= 'm'

def rubygems_path():
    """
    Determine based on the OS release where RubyGems will install gems.
    """
    if lsb_release_codename() is None or rubygems_update():
        return '/usr/lib/ruby/gems'
    return '/var/lib/gems'

def mtime(pathname):
    try:
        return os.stat(pathname).st_mtime
    except OSError:
        return 0

# open the cache file
def open_cache(pathname, mode):
    f = open(pathname, mode)
    uid = int(os.environ['SUDO_UID'])
    gid = int(os.environ['SUDO_GID'])
    os.fchown(f.fileno(), uid, gid)
    return f

def valid_txtfile(pathname):
    # only file
    if os.path.isdir(pathname)==True:
        return False
        
    # only plane text file
    ###########################################
    #cmd = '/usr/bin/file -bi ' + pathname
    #f = os.popen(cmd, 'r')
    #if f.read().startswith('text') == False:
    #    return False
    ###########################################
    if istextfile(pathname)==0:
        return False

    # get the ctime;
    s = os.lstat(pathname)
    # And ignore block special files, character special files,
    # pipes, sockets and symbolic links.
    if stat.S_ISBLK(s.st_mode) \
    or stat.S_ISCHR(s.st_mode) \
    or stat.S_ISFIFO(s.st_mode) \
    or stat.S_ISSOCK(s.st_mode) \
    or stat.S_ISLNK(s.st_mode):
        return False

    return True

def istextfile(filename, blocksize = 512):
   try:
        ret = istext(open(filename).read(blocksize))
   except IOError:
        return 0
   return ret

def istext(s):
    if "\0" in s:
        return 0

    if not s:  # Empty files are considered text
        return 1

    # Get the non-text characters (maps a character to itself then
    # use the 'remove' option to get rid of the text characters.)
    t = s.translate(NULL_TRANS, TEXT_CHARACTERS)

    # If more than 30% non-text characters, then
    # this is considered a binary file
    if len(t)/len(s) > 0.30:
        return 0
    return 1

def get_stat(pathname):
    try:
        s = os.lstat(pathname)
        pw = pwd.getpwuid(s.st_uid)
        owner = pw.pw_name

        gr = grp.getgrgid(s.st_gid)
        group = gr.gr_name

        mode = oct( s.st_mode & 0777 )

    except KeyError:
        owner = s.st_uid
        group = s.st_gid
        mode = oct( 0777 )

    return (group, mode, owner)

def get_content(pathname):
    # read the config file's content
    try:
        content = open(pathname).read()
        return content
    except IOError, e:
        logging.error('utils.get_content(): Can not get file content, %s' % str(e))
        return  None

def get_ips(filename):
    ips = []
    try:
        file = open(filename, "r")

        # read through the file
        for line in file.readlines():
            line = line.rstrip()

            regex = re.findall(r'[0-9]+(?:\.[0-9]+){3}', line)
            # if the regex is not empty and is not already in ips list append
            for ip in regex:
                if ip is not None and ip not in ips:
                    if (PAT_IP.match(ip)) and (not ip.startswith('127.')) and (not ip.startswith('0.')):
                        ips.append(ip)

        file.close()

    except IOError, (errno, strerror):
        return ips

    return ips

########NEW FILE########
__FILENAME__ = cron
'''
Created on 2013-3-28

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Ken
'''

from pysa.scanner.object.object_base import ObjectBase


class Cron(ObjectBase):
    
    def __init__(self, name, command, minute, month, monthday, weekday, hour, target=None, user=None, environment=None):
        self.command = command
        self.environment = '/bin:/usr/bin:/usr/sbin:' + environment if environment else '/bin:/usr/bin:/usr/sbin'
        self.minute = minute
        self.month = month
        self.monthday = monthday
        self.name = name
        self.target = target
        self.user = user
        self.weekday = weekday
        self.hour = hour

########NEW FILE########
__FILENAME__ = file
'''
Created on 2013-3-27

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Ken
'''

from pysa.scanner.object.object_base import ObjectBase


class File(ObjectBase):
    
    def __init__(self, checksum, content, group, mode, owner, path, force=False, provider=None, recurse=None, recurselimit=None, source=None):
        self.checksum   =   checksum
        self.content    =   content
        self.group      =   group
        self.mode       =   mode
        self.owner      =   owner
        self.path       =   path
        self.force      =   force
        self.provider   =   provider
        self.recurse    =   recurse
        self.recurselimit   =   recurselimit
        self.source     =   source
    

########NEW FILE########
__FILENAME__ = group
'''
Created on 2013-3-28

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Ken
'''

from pysa.scanner.object.object_base import ObjectBase


class Group(ObjectBase):
    def __init__(self, name, gid, member=None):
        self.name = name
        self.gid = gid
        self.member = None

########NEW FILE########
__FILENAME__ = host
'''
Created on 2013-3-28

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Ken
'''

from pysa.scanner.object.object_base import ObjectBase


class Host(ObjectBase):
    
    def __init__(self, ip, name, target, host_aliases=None):
        self.ip = ip
        self.name = name
        self.target = target
        self.host_aliases = host_aliases

########NEW FILE########
__FILENAME__ = mount
'''
Created on 2013-3-28

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Ken
'''

from pysa.scanner.object.object_base import ObjectBase


class Mount(ObjectBase):
    
    def __init__(self, device, fstype, name, atboot=None, dump=None, remounts=None, options=None, size=None):
        self.device = device
        self.fstype = fstype
        self.name = name
        self.atboot = atboot
        self.dump = dump
        self.remounts = remounts
        self.options = options
        self.size = size

########NEW FILE########
__FILENAME__ = object_base
'''
Created on 2013-3-27

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Ken
'''

import re


class ObjectBase(object):

    def prase(self):
        format_object = {}
        for attr in dir(self):
            if type(eval("self.%s" % attr)) in (str, int, dict, list, unicode) and not attr.startswith('_') and attr not in ['primarykey', 'primaryvalue']:
                format_object[attr] = eval("self.%s" % attr)
        return format_object

    @property
    def primarykey(self):
        pk = {
            'Package'   :   'name',
            'File'      :   'path',
            'User'      :   'name',
            'Service'   :   'name',
            'Repository':   'path',
            'Group'     :   'name',
            'Cron'      :   'name',
            'Host'      :   'name',
            'Mount'     :   'device',
            'SSHKey'    :   'name',
            'Source'    :   'path',
            'Process'   :   'pid'
        }

        return pk.get(self.__class__.__name__)

    @property
    def primaryvalue(self):
        return getattr(self, self.primarykey)

    def attr_filter(self, attr_rules):
        """
        attribute filter
        """

        if not attr_rules: return False

        # ignore rule's case
        type_list = [ i for i in attr_rules.keys() if i.upper()==(self.__class__.__name__).upper() ]
        if not type_list: return False

        the_type = type_list[0]
        for (attr, rules) in attr_rules[the_type].items():
            if not hasattr(self, attr): continue

            # get the object's attribute value
            value = getattr(self, attr)

            # ignore the null attribute value
            if value is None or not value: continue

            for rule in rules:
                if isinstance(value, list):    # list value
                    if all(isinstance(i, str) for i in value) or all(isinstance(i, unicode) for i in value):
                        if len([ m.group(0) for i in value for m in [re.match("%s$"%rule, i)] if m ])>0: return True
                elif isinstance(value, str) or isinstance(value, unicode):    # string
                    if re.search(rule, value):  return True
        return False

    def add_filter(self, add_rules):
        """
        addition filter
        """

        if not add_rules: return

        type_list = [ i for i in add_rules.keys() if i.upper()==(self.__class__.__name__).upper() ]
        if not type_list: return False

        the_type = type_list[0]
        for attr in add_rules[the_type]:
            # check whether has the attribute
            if not hasattr(self, attr): continue

            values = add_rules[the_type][attr]
            # global setting
            if isinstance(values, str) or isinstance(values, unicode):
                setattr(self, attr, values)
            elif isinstance(values, list):
                setattr(self, attr, values[0])
            # single setting
            elif isinstance(values, dict):
                for value in values:
                    if getattr(self, attr) == value:    # check whether the object
                        rules = values[value]
                        # update
                        for (add_attr, add_value) in rules.items():
                            if hasattr(self, add_attr) and len(add_value)>0:
                                setattr(self, add_attr, add_value[0])

########NEW FILE########
__FILENAME__ = package
'''
Created on 2013-3-27

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Ken
'''

from pysa.scanner.object.object_base import ObjectBase


class Package(ObjectBase):

    def __init__(self, name, files=None, description=None, version=None, responsefile=None, provider=None,
                 instance=None, category=None, platform=None, manager=None, root=None, vendor=None):
        self.name = name
        self.config_files = files
        self.description = description
        self.version = version
        self.responsefile = responsefile
        self.provider = provider
        self.instance = instance
        self.category = category
        self.platform = platform
        self.root   =   root
        self.manager = manager
        self.vendor = vendor

########NEW FILE########
__FILENAME__ = process
'''
Created on 2013-04-19

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Michael
'''

from pysa.scanner.object.object_base import ObjectBase


class Process(ObjectBase):

    def __init__(self, pid, owner, status, cpu, mem, cmd, ppid=None):
        self.pid    =   pid     # process id
        self.owner  =   owner
        self.status =   status  # D:uninterruptible sleep, R:runnable, S:sleeping, T:raced or stopped, Z:defunct process
        self.cpu    =   cpu     # cpu%
        self.mem    =   mem     # mem%
        self.cmd    =   cmd
        self.ppid   =   ppid    # parent pid

########NEW FILE########
__FILENAME__ = repository
'''
Created on 2013-04-18

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Michael
'''

from pysa.scanner.object.object_base import ObjectBase


class Repository(ObjectBase):

    def __init__(self, checksum, content, group, mode, owner, path, force=False, provider=None, recurse=None, recurselimit=None, source=None):
        self.checksum   =   checksum
        self.content    =   content
        self.group      =   group
        self.mode       =   mode
        self.owner      =   owner
        self.path       =   path
        self.force      =   force
        self.provider   =   provider
        self.recurse    =   recurse
        self.recurselimit   =   recurselimit
        self.source     =   source

########NEW FILE########
__FILENAME__ = service
'''
Created on 2013-3-28

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Ken
'''

from pysa.scanner.object.object_base import ObjectBase


class Service(ObjectBase):
    
    def __init__(self, enable, hasrestart, name, path, \
                 provider=None, binary=None, control=None, ensure=None, \
                 hasstatus=None, manifest=None, start=None, stop=None, restart=None):
        self.enable = enable
        self.hasrestart = hasrestart
        self.name = name
        self.path = path
        self.provider = provider
        self.binary = binary
        self.control = control,
        self.ensure = ensure
        self.hasstatus = hasstatus
        self.manifest = manifest
        self.start = start
        self.stop = stop
        self.restart = restart
        
        
        

########NEW FILE########
__FILENAME__ = source
'''
Created on 2013-3-28

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Ken
'''

from pysa.scanner.object.object_base import ObjectBase


class Source(ObjectBase):

    def __init__(self, source, name, path, owner, group, mode, scm, branch, checksum=None, password=None, key=None):
        self.source = source
        self.path = path
        self.owner = owner
        self.name = name
        self.group = group
        self.mode = mode
        self.scm = scm
        self.branch = branch
        self.checksum = checksum
        self.password = password
        self.key = key

########NEW FILE########
__FILENAME__ = sshkey
'''
Created on 2013-3-28

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Ken
'''

from pysa.scanner.object.object_base import ObjectBase


class SSHKey(ObjectBase):
    
    def __init__(self, key, name, path, mode, _type=None, target=None, host_aliases=None, user=None):
        self.key = key
        self.name = name
        self.target = target
        self.host_aliases = host_aliases
        self.type = _type
        self.user = user
        self.path = path
        self.mode = mode


########NEW FILE########
__FILENAME__ = user
'''
Created on 2013-3-28

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Ken
'''

from pysa.scanner.object.object_base import ObjectBase


class User(ObjectBase):
    
    def __init__(self, name, uid, gid, group, groups=None, password=None, expiry=None, shell=None, home=None):
        self.name = name
        self.gid = gid
        self.group = group
        self.expiry = expiry
        self.groups = groups
        self.password = password
        self.uid = uid
        self.shell = shell
        self.home = home

########NEW FILE########
__FILENAME__ = scanner_handler
'''
Created on 2013-3-28

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Ken
'''
#------------------------------------------------------------
import logging
import time

from pysa.scanner.actions.file import ScannerFile
from pysa.scanner.actions.gem import ScannerGem
from pysa.scanner.actions.npm import ScannerNpm
from pysa.scanner.actions.php import ScannerPhp
from pysa.scanner.actions.pypi import ScannerPypi
from pysa.scanner.actions.service import ScannerService
from pysa.scanner.actions.host import ScannerHost
from pysa.scanner.actions.mount import ScannerMount
from pysa.scanner.actions.cron import ScannerCron
from pysa.scanner.actions.sshkey import ScannerKey
from pysa.scanner.actions.user import ScannerUser
from pysa.scanner.actions.group import ScannerGroup
from pysa.scanner.actions.package import ScannerPackage
from pysa.scanner.actions.source import ScannerSource
from pysa.scanner.actions.repository import ScannerRepo
from pysa.scanner.actions.process import ScannerProcess
from pysa.scanner.actions.base import ScannerBase
#------------------------------------------------------------

class ScannerHandler():

    # stay aware of the order
    handler = {
                "file"      : ScannerFile,
                "gem"       : ScannerGem,
                "npm"       : ScannerNpm,
                "php"       : ScannerPhp,
                "pypi"      : ScannerPypi,
                "service"   : ScannerService,
                "host"      : ScannerHost,
                'user'      : ScannerUser,
                'group'     : ScannerGroup,
                'mount'     : ScannerMount,
                'cron'      : ScannerCron,
                'key'       : ScannerKey,
                'package'   : ScannerPackage,
                'source'    : ScannerSource,
                'repository': ScannerRepo,
                'process'   : ScannerProcess
               }



    def __init__(self, rules):
        self.resources  =   {
                                'packages'  :   {},
                                'files'     :   {},
                                'crons'     :   {},
                                'groups'    :   {},
                                'mounts'    :   {},
                                'hosts'     :   {},
                                'repos'     :   {},
                                'services'  :   {},
                                'keys'      :   {},
                                'users'     :   {},
                                'ips'       :   [],
                                'sources'   :   {},
                                'proces'    :   {}

                             }

        self.rules = rules if rules else {}

    def scan(self):

        # init the base scanner
        s = ScannerBase(
                self.resources['packages'],
                self.resources['files'],
                self.resources['crons'],
                self.resources['groups'],
                self.resources['mounts'],
                self.resources['hosts'],
                self.resources['repos'],
                self.resources['services'],
                self.resources['keys'],
                self.resources['users'],
                self.resources['ips'],
                self.resources['sources'],
                self.resources['proces']
        )
        # init the filter rules
        s.init_filter(self.rules)

        for scanner_key in self.handler.keys():
            # ignore the discard resources
            if 'discard' in self.rules and '_resources' in self.rules['discard'] and scanner_key in self.rules['discard']['_resources']: continue

            # time begin
            time_begin = time.time()

            # log
            logging.info('ScannerHandler.scan(): Scanning Module %s, time begin at %s ' % (scanner_key, time_begin))

            # scan according to different modules
            try:
                s.__class__ = self.handler[scanner_key]
                
                s.scan()

            except Exception, e:
                logging.error('ScannerHandler.scan(): %s Error message, %s' % (scanner_key,str(e)))

            # time end
            time_consume = time.time() - time_begin
            logging.info('ScannerHandler.scan(): Scanning Module %s, time consume %s ' % (scanner_key, time_consume))

        return self.resources

def module_scan(filters = None):
    scanner = ScannerHandler(filters)
    return scanner.scan()

########NEW FILE########
__FILENAME__ = tools
'''
Common tools

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Thibault BRONCHAIN
'''

import os
import os.path
import logging
import re
import copy

from pysa.exception import *


INFO    = "INFO"
DEBUG   = "DEBUG"
ERR     = "ERROR"

LOGGING_EQ = {
    INFO        : logging.info,
    DEBUG       : logging.debug,
    ERR         : logging.error
}


# common tools collection
class Tools():
    # logging
    @staticmethod
    def l(action, content, f, c = None):
        out = ("%s." % (c.__class__.__name__) if c else "")
        out += "%s()" % (f)
        LOGGING_EQ[action]("%s: %s" % (out, content))

    # add a tab
    @staticmethod
    def tab_inc(tab):
        return tab+'\t'

    # delete a tab
    @staticmethod
    def tab_dec(tab):
        return tab[1:]

    # write data in a specific file
    @staticmethod
    def write_in_file(fname, content):
        Tools.l(INFO, "creating file %s" % (fname), 'write_in_file')
        dirname = os.path.dirname(fname)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        f = open(fname,'w')
        f.write(content)
        f.close()

    # get recursive path dirlist
    @staticmethod
    def get_recurse_path(path):
        rpath = re.split('/', path)
        i = 1
        while i < len(rpath):
#DEBUG
#            rpath[i] = "%s/%s" % (rpath[i-1] if i else "", rpath[i])
#/DEBUG
            rpath[i] = os.path.normpath("%s/%s" % (rpath[i-1] if i else "", rpath[i]))
            i += 1
        rpath[0] = '/'
        return rpath

    # get previous path
    @staticmethod
    def path_basename(path):
        if path == '/': return None
        if path[-1] == '/': path = path[:-1]
        rpath = re.split('/', path)
        i = 1
        while i < len(rpath):
# DEBUG
#            rpath[i] = "%s/%s" % (rpath[i-1] if i else "", rpath[i])
#/DEBUG
            rpath[i] = os.path.normpath("%s/%s" % (rpath[i-1] if i else "", rpath[i]))
            i += 1
        rpath[0] = '/'
        if len(rpath) < 2: return None
        return rpath[-2]

    # returns file content
    @staticmethod
    def get_file(filename):
        if not filename: return None
        file = None
        try:
            f = open(filename, 'r')
            file = f.read()
        except IOError:
            Tools.l(ERR, "%s: no such file or directory" % (filename), 'dump_file')
            return None
        return file

    # check if file exists
    @staticmethod
    def file_exists(filename):
        if not filename: return None
        try:
            with open(filename): pass
        except IOError:
            Tools.l(ERR, "%s: no such file or directory" % (filename), 'file_exists')
            return None
        return filename

    # merge lists recursive
    @staticmethod
    def list_merging(first, second):
        f = (first if first else [])
        s = (second if second else [])
        return f+s

    # remove childs after dict merging
    @staticmethod
    def dict_cleaner(input):
        output = {}
        for key in input:
            if type(input[key]) is not dict:
                output[key] = input[key]
        return output

    # ensure dictionary existency
    @staticmethod
    def s_dict_merging(first, second, duplicate = True):
        d = Tools.dict_merging(first,second, duplicate)
        return (d if d else {})

    # merge dicts /!\ recursive
    @staticmethod
    def dict_merging(first, second, duplicate = True):
        if (not first) and (not second):
            return None
        elif not first:
            return (copy.deepcopy(second) if duplicate else second)
        elif not second:
            return (copy.deepcopy(first) if duplicate else first)
        repl = copy.deepcopy(first)
        for item in second:
            if (first.get(item)) and (type(first[item]) != type (second[item])):
                continue
            elif not first.get(item):
                repl[item] = second[item]
            elif type(second[item]) is dict:
                # recursion here
                val = Tools.dict_merging(first[item], second.get(item), True)
                if val != None:
                    repl[item] = val
            elif type(second[item]) is list:
                repl[item] = first[item] + second[item]
            else:
                repl[item] = second[item]
        return repl

    # merge strings and lists
    @staticmethod
    def merge_string_list(first, second):
        if not first: return second
        elif not second: return first
        elif (type(first) is list) and (type(second) is list): return first+second
        elif (type(first) is list):
            first.append(second)
            return first
        elif (type(second) is list):
            second.append(first)
            return second
        else: return [first, second]

########NEW FILE########
__FILENAME__ = pysa
#!/usr/bin/python
'''
Main file

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Thibault BRONCHAIN
'''

from optparse import *
import logging
import re

from pysa.tools import Tools
from pysa.preprocessing import Preprocessing
from pysa.config import *
from pysa.exception import *
from pysa.madeira import *

from pysa.filter.parser import FParser
from pysa.scanner.scanner_handler import module_scan

from pysa.puppet.converter import PuppetConverter
from pysa.puppet.build import PuppetBuild

from pysa.salt.converter import SaltConverter
from pysa.salt.build import SaltBuild


# global defines
USAGE = 'usage: %prog [-hqps] [-m module_name] [-o output_path] [-c config_file_path] [-f filter_config_path] [-l {-u madeira_username}|{-i madeira_id}]'
VERSION_NBR = '0.3b'
VERSION = '%prog '+VERSION_NBR

# logger settings
LOG_FILENAME = '/tmp/scanner.log'
LOG_FORMAT = '%(asctime)s-%(name)s-%(levelname)s-%(message)s'
def __log(lvl):
    level = logging.getLevelName(lvl)
    formatter = logging.Formatter(LOG_FORMAT)
    handler = logging.StreamHandler()
    logger = logging.getLogger()
    handler.setFormatter(formatter)
    logger.setLevel(level)
    logger.addHandler(handler)


# scanner class
class Scanner():
    def __init__(self, filters=None):
        self.resources = None
        self.filters = filters
        self.preprocessed = None

    @GeneralException
    # get resource from different modules
    def scan(self):
        logging.info('Scanner.scan(): start scanning')
        self.resources = module_scan(self.filters if self.filters else None)

    @GeneralException
    # generate puppet files
    def preprocessing(self, module):
        if not self.resources:
            logging.error('Scanner.preprocessing(): No resources')
            return
        logging.info('Scanner.preprocessing(): Running')
        return Preprocessing(module).run(self.resources)

    @GeneralException
    # generate puppet files
    def show_puppet(self, path, module):
#        if not self.preprocessed:
#            logging.error('Scanner.show_puppet(): No data')
#            return
        logging.info('Scanner.show_puppet(): Puppet files will be stored in path: %s' % path)
        puppetdict = PuppetConverter(self.preprocessing('pysa.puppet'), self.filters)
        p = puppetdict.run()
        puppet = PuppetBuild(p, path, module)
        puppet.run()

    @GeneralException
    # generate salt files
    def show_salt(self, path, module):
#        if not self.preprocessed:
#            logging.error('Scanner.show_salt(): No data')
#            return
        logging.info('Scanner.show_salt(): Salt files will be stored in path: %s' % path)
        saltdict = SaltConverter(self.preprocessing('pysa.salt'), self.filters)
        s = saltdict.run()
        salt = SaltBuild(s, path, module)
        salt.run()

# print header
def print_header():
    print "Pysa v"+VERSION_NBR
    print '''

    pysa - reverse a complete computer setup
    Copyright (C) 2013  MadeiraCloud Ltd.

Thank you for using pysa!
Be aware that you are using an early-build (alpha release).
To provide the best result, ensure that you are not using an outdated version (check out http://github.com/MadeiraCloud/pysa or http://pypi.python.org/pypi/Pysa to get the latest version).
Please don't hesitate to report any bugs, requirements, advice, criticisms, hate or love messages to either pysa-user@googlegroups.com for public discussions and pysa@mc2.io for private messages.
'''

# option parser - user handler
def check_user(option, opt_str, value, parser):
    if parser.values.user or parser.values.id:
        setattr(parser.values, option.dest, True)
    else:
        raise OptionValueError("can't use -l without -u or -i (see usage)")

# option parser
def main_parse():
    parser = OptionParser(usage=USAGE, version=VERSION)
    parser.add_option("-c", "--config", action="store", dest="config",
                      help="specify config file"
                      )
    parser.add_option("-p", "--puppet", action="store_true", dest="puppet", default=False,
                      help="scan packages and generate the puppet manifests"
                      )
    parser.add_option("-s", "--salt", action="store_true", dest="salt", default=False,
                      help="[EXPERIMENTAL] scan packages and generate the salt manifests"
                      )
    parser.add_option("-q", "--quiet", action="store_true", dest="quiet", default=False,
                      help="operate quietly"
                      )
    parser.add_option("-m", "--module", action="store", dest="module", default="pysa",
                      help="define module name"
                      )
    parser.add_option("-o", "--output", action="store", dest="output", default="./output",
                      help="Path to output"
                      )
    parser.add_option("-f", "--filter", action="store", dest="filter",
                      help="add some user filters"
                      )
    parser.add_option("-l", "--madeira", action="callback", callback=check_user, dest='l',
                      help="post data to madeira"
                      )
    parser.add_option("-u", "--user", "--username", action="store", dest='user',
                      help="madeira username"
                      )
    parser.add_option("-i", "--id", action="store", dest='id',
                      help="identify user id"
                      )
    return parser.parse_args()

def main():
    # print header
    print_header()

    # options parsing
    options, args = main_parse()
    __log(('ERROR' if options.quiet else 'INFO'))
    output = (options.output if options.output else "./output")
    module = (options.module if options.module else "pysa")
    user = (options.user if options.user else None)
    uid = (options.id if options.id else None)

    # config parser
    Config(options.config if options.config else None)

    # filters parsing
    filter_parser = FParser(options.filter if options.filter else None)
    filters = filter_parser.run()

    # scan for files
    s = Scanner(filters)
    s.scan()
    # generate puppet output
    if options.puppet:
        s.show_puppet(output, module)
    # generate salt output
    if options.salt:
        s.show_salt(output, module)

    # save to madeira accound
    if options.l:
        m = Madeira(user, uid, output, module)
        m.send()


if __name__ == '__main__':
    main()

########NEW FILE########
