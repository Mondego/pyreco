__FILENAME__ = cache
#!/usr/bin/env python
#
# Copyright 2009 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

import time
import functools

class NoCacheStrategy(object):
    """This cache strategy reloads the cache on every call.
    """
    
    def isCacheValid(self, f, *args, **kwargs):
        return False
    
class NoReloadStrategy(object):
    """This cache strategy never reloads the cache.
    """
    
    def isCacheValid(self, f, *args, **kwargs):
        return True

class TimeoutReloadStrategy(object):
    
    def __init__(self, timeoutDuration = 10 * 60):
        self.timeoutDuration = timeoutDuration
    
    def isCacheValid(self, f, *args, **kwargs):
        obj = args[0]
        
        timestampFieldName = '__' + f.__name__ + 'Timestamp'
        now = time.time()
    
        if not hasattr(obj, timestampFieldName):
            setattr(obj, timestampFieldName, now)
        
            return False
    
        lastTime = getattr(obj, timestampFieldName)
    
        if now - lastTime < self.timeoutDuration:
            return True
    
        setattr(obj, timestampFieldName, now)
    
        return False


def cache(f, reloadStrategy = NoReloadStrategy()):
    """This annotation is used to cache the result of a method call.
    
    @param f: This is the wrapped function which's return value will be cached.
    @param reload: This is the reload strategy. This function returns True when
    the cache should be reloaded. Otherwise False.
    @attention: The cache is never deleted. The first call initializes the
    cache. The method's parameters just passed to the called method. The cache
    is not evaluating the parameters.
    """
    
    @functools.wraps(f)
    def cacher(*args, **kwargs):
        obj = args[0]
        
        cacheMemberName = '__' + f.__name__ + 'Cache'
        
        # the reload(...) call has to be first as we always have to call the
        # method. not only when there is a cache member available in the object.
        if (not reloadStrategy.isCacheValid(f, *args, **kwargs)) or (not hasattr(obj, cacheMemberName)):
            value = f(*args, **kwargs)
            
            setattr(obj, cacheMemberName, value)
            
            return value
            
        return getattr(obj, cacheMemberName)
    
    return cacher


########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python
#
# Copyright 2009, 2010, 2012 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

import ConfigParser
import logging
import os

def parseConfig(itemsDir):
    config = ConfigParser.SafeConfigParser({
            'tagFileName': '.tag',
            'enableValueFilters': 'False',
            'enableRootItemLinks': 'False',
            })
    config.add_section(Config.GLOBAL_SECTION)

    parsedFiles = config.read([os.path.join('/', 'etc', 'tagfs', 'tagfs.conf'), 
                               os.path.expanduser(os.path.join('~', '.tagfs', 'tagfs.conf')),
                               os.path.join(itemsDir, '.tagfs', 'tagfs.conf'),
    ])

    logging.debug('Parsed the following config files: %s' % ', '.join(parsedFiles))

    return Config(config)

class Config(object):

    GLOBAL_SECTION = 'global'

    def __init__(self, _config):
        self._config = _config

    @property
    def tagFileName(self):
        return self._config.get(Config.GLOBAL_SECTION, 'tagFileName')

    @property
    def enableValueFilters(self):
        return self._config.getboolean(Config.GLOBAL_SECTION, 'enableValueFilters')

    @property
    def enableRootItemLinks(self):
        return self._config.getboolean(Config.GLOBAL_SECTION, 'enableRootItemLinks')

    def __str__(self):
        #return '[' + ', '.join([field + ': ' + str(self.__dict__[field]) for field in ['tagFileName', 'enableValueFilters', 'enableRootItemLinks']]) + ']'
        return '[tagFileName: %s, enableValueFilters: %s, enableRootItemLinks: %s]' % (self.tagFileName, self.enableValueFilters, self.enableRootItemLinks)

########NEW FILE########
__FILENAME__ = freebase_support
#
# Copyright 2012 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.

import json
import logging

def createFreebaseAdapter():
    # freebase is an optional dependency. tagfs should execute even if it's not
    # available.
    try:
        import freebase

        logging.info('freebase support enabled')

        return FreebaseAdapter()
    except ImportError:
        logging.warn('freebase support disabled')

        return FreebaseAdapterStub()
    
class FreebaseAdapterStub(object):

    def execute(self, *args, **kwargs):
        return {}

class FreebaseAdapter(object):

    def execute(self, query):
        import freebase

        fbResult = freebase.mqlread(query.freebaseQuery)

        result = {}

        for key in query.selectedKeys:
            result[key] = fbResult[key]

        return result

class Query(object):

    def __init__(self, queryObject):
        self.queryObject = queryObject

    @property
    def freebaseQuery(self):
        q = {}

        for key, value in self.queryObject.iteritems():
            if(value is None):
                q[key] = []
            else:
                q[key] = value

        return q

    @property
    def queryString(self):
        # TODO this func is only used in tests => remove
        return json.dumps(self.freebaseQuery, separators = (',', ':'))

    @property
    def selectedKeys(self):
        for key, value in self.queryObject.iteritems():
            if(value is None):
                yield key

class QueryParser(object):

    def parse(self, queryString):
        return Query(json.loads(queryString))

class QueryFileParser(object):

    def __init__(self, system, queryParser):
        self.system = system
        self.queryParser = queryParser

    def parseFile(self, path):
        with self.system.open(path, 'r') as f:
            for line in f:
                yield self.queryParser.parse(line)

class GenericQueryFactory(object):

    def __init__(self, resolveVar):
        self.resolveVar = resolveVar

    def evaluate(self, value):
        if(value is None):
            return None

        valueLen = len(value)

        if(valueLen < 2):
            return value

        if(value[0] != '$'):
            return value

        key = value[1:]

        return self.resolveVar(key)

    def createQuery(self, genericQuery):
        q = {}

        for key, genericValue in genericQuery.iteritems():
            value = self.evaluate(genericValue)

            q[key] = value

        return q

########NEW FILE########
__FILENAME__ = item_access
#
# Copyright 2009 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.

import logging
import os
import time
import traceback

from cache import cache
import sysIO
import freebase_support

class Tag(object):
    
    def __init__(self, value, context = None):
        if context == None:
            self.context = None
        else:
            self.context = context.strip()
        
        self.value = value.strip()
        
        if not self.context == None and len(self.context) == 0:
            # we don't allow empty strings as they can't be represented as a
            # directory very well
            raise ValueError()

        if len(self.value) == 0:
            # we don't allow empty strings as they can't be represented as a
            # directory very well
            raise ValueError()
        
    def __hash__(self):
        return (self.context, self.value).__hash__()
    
    def __eq__(self, other):
        return self.value == other.value and self.context == other.context
        
    def __repr__(self):
        return '<Tag %s: %s>' % (self.context, self.value)

def parseTagsFromFile(system, tagFileName):
    """Parses the tags from the specified file.
    
    @return: The parsed values are returned as a set containing Tag objects.
    @see: Tag
    """
    
    tags = set()
    
    with system.open(tagFileName, 'r') as tagFile:
        for rawTag in tagFile:
            rawTag = rawTag.strip()
            
            try:
                if len(rawTag) == 0:
                    continue
            
                tagTuple = rawTag.split(':', 1)
            
                if len(tagTuple) == 1:
                    tagContext = None
                    tagValue = tagTuple[0]
                else:
                    tagContext = tagTuple[0]
                    tagValue = tagTuple[1]
                
                tag = Tag(tagValue, context = tagContext)

                tags.add(tag)
            except:
                logging.warning('Skipping tagging \'%s\' from file \'%s\' as it can\'t be parsed\n%s.' % (rawTag, tagFileName, traceback.format_exc()))
        
    return tags
    
class NoSuchTagValue(Exception):

    pass

class Item(object):
    
    def __init__(self, name, system, itemAccess, freebaseQueryParser, freebaseAdapter, genericFreebaseQueries = [], parseTagsFromFile = parseTagsFromFile):
        self.name = name
        self.system = system
        self.itemAccess = itemAccess
        self.freebaseQueryParser = freebaseQueryParser
        self.freebaseAdapter = freebaseAdapter
        self.parseTagsFromFile = parseTagsFromFile
        self.genericFreebaseQueries = genericFreebaseQueries
        
        # TODO register at file system to receive tag file change events.
        
    @property
    @cache
    def itemDirectory(self):
        return os.path.join(self.itemAccess.dataDirectory, self.name)
    
    @property
    @cache
    def _tagFileName(self):
        """Returns the name of the tag file for this item.
        """
        
        return os.path.join(self.itemDirectory, self.itemAccess.tagFileName)

    @property
    @cache
    def tagFileExists(self):
        return self.system.pathExists(self._tagFileName)

    def __getFreebaseTags(self, query):
        try:
            for context, values in self.freebaseAdapter.execute(query).iteritems():
                for value in values:
                    # without the decode/encode operations fuse refuses to show
                    # directory entries which are based on freebase data
                    yield Tag(value.decode('ascii', 'ignore').encode('ascii'), context)
        except Exception as e:
            logging.error('Failed to execute freebase query %s: %s', query, e)
    
    def __parseTags(self):
        tagFileName = self._tagFileName
        
        for rawTag in self.parseTagsFromFile(self.system, tagFileName):
            if(rawTag.context == '_freebase'):
                query = self.freebaseQueryParser.parse(rawTag.value)
                
                for tag in self.__getFreebaseTags(query):
                    yield tag
            else:
                yield rawTag

    @property
    @cache
    def tagsCreationTime(self):
        if not self.tagFileExists:
            return None

        return os.path.getctime(self._tagFileName)
    
    @property
    @cache
    def tagsModificationTime(self):
        """Returns the last time when the tags have been modified.
        """
        
        if not self.tagFileExists:
            return None

        return os.path.getmtime(self._tagFileName)
    
    @property
    @cache
    def tags(self):
        """Returns the tags as a list for this item.
        """
        
        if not self.tagFileExists:
            return None

        tags = list(self.__parseTags())

        def getValue(context):
            for tag in tags:
                if(tag.context == context):
                    return tag.value

            raise NoSuchTagValue()

        queryFactory = freebase_support.GenericQueryFactory(getValue)
        for genericQuery in self.genericFreebaseQueries:
            try:
                query = queryFactory.createQuery(genericQuery.queryObject)

                for tag in self.__getFreebaseTags(freebase_support.Query(query)):
                    tags.append(tag)
            except NoSuchTagValue:
                pass

        return tags

    @property
    def values(self):
        for t in self.tags:
            yield t.value

    def getTagsByContext(self, context):
        for t in self.tags:
            if context != t.context:
                continue

            yield t

    def getValuesByContext(self, context):
        return [t.value for t in self.getTagsByContext(context)]

    def getValueByContext(self, context):
        values = self.getValuesByContext(context)
        valuesLen = len(values)
        
        if(valuesLen == 0):
            return None

        if(valuesLen == 1):
            return values[0]

        raise Exception('Too many values found for context %s' % (context,))

    def isTaggedWithContextValue(self, context, value):
        for t in self.getTagsByContext(context):
            if value == t.value:
                return True

        return False

    def isTaggedWithContext(self, context):
        # TODO don't create whole list... just check wheather list is empty
        return (len([c for c in self.getTagsByContext(context)]) > 0)

    def isTaggedWithValue(self, value):
        for v in self.values:
            if value == v:
                return True

        return False
    
    @property
    def tagged(self):
        return self.tagFileExists
    
    def __repr__(self):
        return '<Item %s, %s>' % (self.name, self.tags)
    
class ItemAccess(object):
    """This is the access point to the Items.
    """
    
    def __init__(self, system, dataDirectory, tagFileName, freebaseQueryParser, freebaseAdapter, genericFreebaseQueries):
        self.system = system
        self.dataDirectory = dataDirectory
        self.tagFileName = tagFileName
        self.freebaseQueryParser = freebaseQueryParser
        self.freebaseAdapter = freebaseAdapter
        self.genericFreebaseQueries = genericFreebaseQueries
        
        self.parseTime = 0
        
    def __parseItems(self):
        items = {}
        
        logging.debug('Start parsing items from dir: %s', self.dataDirectory)
        
        for itemName in os.listdir(self.dataDirectory):
            if itemName == '.tagfs':
                # skip directory with configuration
                continue

            try:
                item = Item(itemName, self.system, self, self.freebaseQueryParser, self.freebaseAdapter, self.genericFreebaseQueries)
                
                items[itemName] = item
                
            except IOError, (error, strerror):
                logging.error('Can \'t read tags for item %s: %s',
                              itemName,
                              strerror)
                
        logging.debug('Found %s items', len(items))
        
        self.parseTime = time.time()

        return items
    
    @property
    @cache
    def items(self):
        return self.__parseItems() 

    @property
    @cache
    def tags(self):
        tags = set()
        
        for item in self.items.itervalues():
            if not item.tagged:
                continue
          
            tags = tags | set(item.tags)
            
        return tags

    @property
    @cache
    def taggedItems(self):
        return set([item for item in self.items.itervalues() if item.tagged])
    
    @property
    @cache
    def untaggedItems(self):
        return set([item for item in self.items.itervalues() if not item.tagged])

    def getItemDirectory(self, item):
        return os.path.join(self.dataDirectory, item)
    
    def contextTags(self, context):
        contextTags = set()
        
        for tag in self.tags:
            if tag.context == context:
                contextTags.add(tag)
                
        return contextTags
    
    @property
    @cache
    def contexts(self):
        contexts = set()

        for tag in self.tags:
            if tag.context == None:
                continue

            contexts.add(tag.context)
        
        return contexts

    @property
    @cache
    def values(self):
        values = set()

        for tag in self.tags:
            values.add(tag.value)

        return values

    def __str__(self):
        return '[' + ', '.join([field + ': ' + str(self.__dict__[field]) for field in ['dataDirectory', 'tagFileName']]) + ']'

########NEW FILE########
__FILENAME__ = log
#
# Copyright 2010, 2011 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

import functools
import logging

def getLogger(*args):
    o = args[0]

    logger = logging.getLogger(o.__class__.__name__)

    return logger
    

def logCall(f):

    @functools.wraps(f)
    def logCall(*args, **kwargs):
        logger = getLogger(*args)

        if(logger.isEnabledFor(logging.DEBUG)):
            logger.debug(f.__name__ + '(' + (', '.join('\'' + str(a) + '\'' for a in args[1:])) + ')')

        return f(*args, **kwargs)

    return logCall

def logException(f):

    @functools.wraps(f)
    def logException(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except:
            logger = getLogger(*args)

            if(logger.isEnabledFor(logging.ERROR)):
                import traceback

                logger.warn(traceback.format_exc())

            raise

    return logException

########NEW FILE########
__FILENAME__ = log_config
#!/usr/bin/env python
#
# Copyright 2009, 2010 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

import logging
import sys

def setUpLogging():
    def exceptionCallback(eType, eValue, eTraceBack):
        import cgitb

        txt = cgitb.text((eType, eValue, eTraceBack))

        logging.critical(txt)
    
        # sys.exit(1)

    # configure file logger
    logging.basicConfig(level = logging.DEBUG,
                        format = '%(asctime)s %(levelname)s %(message)s',
                        filename = '/tmp/tagfs.log',
                        filemode = 'a')
    
    # configure console logger
    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setLevel(logging.DEBUG)
    
    consoleFormatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    consoleHandler.setFormatter(consoleFormatter)
    logging.getLogger().addHandler(consoleHandler)

    # replace default exception handler
    sys.excepthook = exceptionCallback
    
    logging.debug('Logging and exception handling has been set up')

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
#
# Copyright 2009, 2010 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#
#
# = tag fs =
# == glossary ==
# * item: An item is a directory in the item container directory. Items can be
# tagged using a tag file.
# * tag: A tag is a text string which can be assigned to an item. Tags can
# consist of any character except newlines.

import os
import stat
import errno
import exceptions
import time
import functools
import logging

import fuse
if not hasattr(fuse, '__version__'):
    raise RuntimeError, \
        "your fuse-py doesn't know of fuse.__version__, probably it's too old."
fuse.fuse_python_api = (0, 2)

from view import View
from cache import cache
from item_access import ItemAccess
from config import parseConfig
from log import logException

import sysIO
import freebase_support
    
class TagFS(fuse.Fuse):

    def __init__(self, initwd, *args, **kw):
        fuse.Fuse.__init__(self, *args, **kw)
        
        self._initwd = initwd
        self._itemsRoot = None

        self.system = sysIO.createSystem()

        # TODO change command line arguments structure
        # goal: tagfs <items dir> <mount dir>
        self.parser.add_option('-i',
                               '--items-dir',
                               dest = 'itemsDir',
                               help = 'items directory',
                               metavar = 'dir')
        self.parser.add_option('-t',
                               '--tag-file',
                               dest = 'tagFileName',
                               help = 'tag file name',
                               metavar = 'file',
                               default = None)
        self.parser.add_option('--value-filter',
                               action = 'store_true',
                               dest = 'enableValueFilters',
                               help = 'Displays value filter directories on toplevel instead of only context entries',
                               default = None)
        self.parser.add_option('--root-items',
                               action = 'store_true',
                               dest = 'enableRootItemLinks',
                               help = 'Display item links in tagfs root directory.',
                               default = None)

    def parseGenericFreebaseQueries(self, itemsRoot):
        freebaseQueriesFilePath = os.path.join(itemsRoot, '.tagfs', 'freebase')

        if(not os.path.exists(freebaseQueriesFilePath)):
            return []

        queries = list(freebase_support.QueryFileParser(self.system, freebase_support.QueryParser()).parseFile(freebaseQueriesFilePath))

        logging.info('Parsed %s generic freebase queries', len(queries))

        return queries

    def getItemAccess(self):
        # Maybe we should move the parser run from main here.
        # Or we should at least check if it was run once...
        opts, args = self.cmdline

        # Maybe we should add expand user? Maybe even vars???
        assert opts.itemsDir != None and opts.itemsDir != ''
        itemsRoot = os.path.normpath(
                os.path.join(self._initwd, opts.itemsDir))

        # TODO rel https://github.com/marook/tagfs/issues#issue/2
        # Ensure that mount-point and items dir are disjoined.
        # Something along
        # assert not os.path.normpath(itemsDir).startswith(itemsRoot)

        # try/except here?
        try:
            return ItemAccess(self.system, itemsRoot, self.config.tagFileName, freebase_support.QueryParser(), freebase_support.createFreebaseAdapter(), self.parseGenericFreebaseQueries(itemsRoot))
        except OSError, e:
            logging.error("Can't create item access from items directory %s. Reason: %s",
                    itemsRoot, str(e.strerror))
            raise
    
    @property
    @cache
    def config(self):
        opts, args = self.cmdline

        c = parseConfig(os.path.normpath(os.path.join(self._initwd, opts.itemsDir)))

        if opts.tagFileName:
            c.tagFileName = opts.tagFileName

        if opts.enableValueFilters:
            c.enableValueFilters = opts.enableValueFilters

        if opts.enableRootItemLinks:
            c.enableRootItemLinks = opts.enableRootItemLinks

        logging.debug('Using configuration %s' % c)

        return c

    @property
    @cache
    def view(self):
        itemAccess = self.getItemAccess()

        return View(itemAccess, self.config)

    @logException
    def getattr(self, path):
        return self.view.getattr(path)

    @logException
    def readdir(self, path, offset):
        return self.view.readdir(path, offset)
            
    @logException
    def readlink(self, path):
        return self.view.readlink(path)

    @logException
    def open(self, path, flags):
        return self.view.open(path, flags)

    @logException
    def read(self, path, size, offset):
        return self.view.read(path, size, offset)

    @logException
    def write(self, path, data, pos):
        return self.view.write(path, data, pos)

    @logException
    def symlink(self, path, linkPath):
        return self.view.symlink(path, linkPath)

def main():
    fs = TagFS(os.getcwd(),
            version = "%prog " + fuse.__version__,
            dash_s_do = 'setsingle')

    fs.parse(errex = 1)
    opts, args = fs.cmdline

    if opts.itemsDir == None:
        fs.parser.print_help()
        # items dir should probably be an arg, not an option.
        print "Error: Missing items directory option."
        # Quickfix rel https://github.com/marook/tagfs/issues/#issue/3
        # FIXME: since we run main via sys.exit(main()), this should
        #        probably be handled via some return code.
        import sys
        sys.exit()
        
    return fs.main()

if __name__ == '__main__':
    import sys
    sys.exit(main())

########NEW FILE########
__FILENAME__ = node
#
# Copyright 2009 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

import fuse
import stat

from cache import cache

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

    def __str__(self):
        return '[' + ', '.join([field + ': ' + str(self.__dict__[field]) for field in self.__dict__]) + ']'

class ItemLinkNode(object):

    def __init__(self, item):
        self.item = item

    @property
    def name(self):
        return self.item.name

    @property
    def attr(self):
        s = Stat()

        s.st_mode = stat.S_IFLNK | 0444
        s.st_nlink = 2
    
        return s

    def addsValue(self, items):
        return True

    @property
    def link(self):
        return self.item.itemDirectory

class DirectoryNode(object):

    @property
    def attr(self):
        s = Stat()

        s.st_mode = stat.S_IFDIR | 0555

        s.st_mtime = 0
        s.st_ctime = s.st_mtime
        s.st_atime = s.st_mtime

        return s

    def addsValue(self, items):
        return True

    def _addsValue(self, child):
        return True

    @property
    @cache
    def entries(self):
        return dict([[e.name, e] for e in self._entries if self._addsValue(e)])

########NEW FILE########
__FILENAME__ = node_export
#
# Copyright 2011 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

from cache import cache
from node import Stat, ItemLinkNode, DirectoryNode
from node_untagged_items import UntaggedItemsDirectoryNode
from node_export_csv import ExportCsvFileNode
from node_export_chart import ChartImageNode

class SumTransformation(object):

    def __init__(self):
        self.sum = 0.0

    def transform(self, y):
        self.sum += y

        return self.sum

class ExportDirectoryNode(DirectoryNode):

    def __init__(self, itemAccess, parentNode):
        self.itemAccess = itemAccess
        self.parentNode = parentNode

    @property
    def name(self):
        return '.export'

    @property
    def attr(self):
        s = super(ExportDirectoryNode, self).attr

        # TODO why nlink == 2?
        s.st_nlink = 2

        # TODO write test case which tests st_mtime == itemAccess.parseTime
        s.st_mtime = self.itemAccess.parseTime
        s.st_ctime = s.st_mtime
        s.st_atime = s.st_mtime

        return s

    @property
    def items(self):
        return self.parentNode.items
    
    @property
    def _entries(self):
        yield ExportCsvFileNode(self.itemAccess, self.parentNode)

        for context in self.parentNode.contexts:
            yield ChartImageNode(self.itemAccess, self.parentNode, context, 'value', lambda y: y)
            yield ChartImageNode(self.itemAccess, self.parentNode, context, 'sum', SumTransformation().transform)

########NEW FILE########
__FILENAME__ = node_export_chart
#
# Copyright 2013 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

from cache import cache
from node_file import FileNode
import pylab
import cStringIO

class ChartImageNode(FileNode):

    def __init__(self, itemAccess, parentNode, context, title, transform):
        self.itemAccess = itemAccess
        self.parentNode = parentNode
        self.context = context
        self.title = title
        self.transform = transform

    @property
    def name(self):
        return '%s-%s.png' % (self.title, self.context,)

    @property
    def items(self):
        return self.parentNode.items

    @property
    @cache
    def content(self):
        pylab.clf()

        xValues = []
        yValues = []

        for x, item in enumerate(sorted(self.items, key = lambda item: item.name)):
            for tag in item.tags:
                c = tag.context

                if(c != self.context):
                    continue

                try:
                    y = float(tag.value)
                except:
                    y = None

                if(y is None):
                    try:
                        # some love for our german people
                        y = float(tag.value.replace('.', '').replace(',', '.'))
                    except:
                        continue

                xValues.append(x)
                yValues.append(self.transform(y))

        pylab.plot(xValues, yValues, label = self.context)

        pylab.grid(True)

        out = cStringIO.StringIO()

        pylab.savefig(out, format = 'png')

        return out.getvalue()

########NEW FILE########
__FILENAME__ = node_export_csv
#
# Copyright 2011 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

from cache import cache
from node_file import FileNode

class ExportCsvFileNode(FileNode):

    COL_SEPARATOR = ';'

    TEXT_CHAR = '"'

    ROW_SEPARATOR = '\n'

    TAG_VALUE_SEPARATOR = '\n'

    def __init__(self, itemAccess, parentNode):
        self.itemAccess = itemAccess
        self.parentNode = parentNode

    @property
    def name(self):
        return 'export.csv'

    @property
    def items(self):
        return self.parentNode.items

    def formatRow(self, row):
        first = True

        for col in row:
            if first:
                first = False
            else:
                yield ExportCsvFileNode.COL_SEPARATOR

            # TODO escape TEXT_CHAR in col string
            yield ExportCsvFileNode.TEXT_CHAR
            yield str(col)
            yield ExportCsvFileNode.TEXT_CHAR

        yield ExportCsvFileNode.ROW_SEPARATOR

    @property
    def _content(self):
        contexts = set()
        for i in self.items:
            for t in i.tags:
                contexts.add(t.context)

        headline = ['name', ]
        for c in contexts:
            headline.append(c)
        for s in self.formatRow(headline):
            yield s

        for i in self.items:
            row = [i.name, ]

            for c in contexts:
                row.append(ExportCsvFileNode.TAG_VALUE_SEPARATOR.join([t.value for t in i.getTagsByContext(c)]))

            for s in self.formatRow(row):
                yield s

    @property
    @cache
    def content(self):
        return ''.join(self._content)

########NEW FILE########
__FILENAME__ = node_file
#
# Copyright 2013 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

import array
import stat
from node import Stat

class FileNode(object):
    
    @property
    def attr(self):
        s = Stat()

        s.st_mode = stat.S_IFREG | 0444
        s.st_nlink = 2

        # TODO replace with memory saving size calculation
        s.st_size = len(array.array('c', self.content))

        return s

    def open(self, path, flags):
        return

    def read(self, path, size, offset):
        return self.content[offset:offset + size]

########NEW FILE########
__FILENAME__ = node_filter
#
# Copyright 2011 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

from cache import cache
from node import Stat, ItemLinkNode, DirectoryNode
from node_export import ExportDirectoryNode

class FilterDirectoryNode(DirectoryNode):
    
    def __init__(self, itemAccess, config):
        self.itemAccess = itemAccess
        self.config = config

    @property
    def attr(self):
        s = super(FilterDirectoryNode, self).attr

        # TODO why nlink == 2?
        s.st_nlink = 2

        # TODO write test case which tests st_mtime == itemAccess.parseTime
        s.st_mtime = self.itemAccess.parseTime
        s.st_ctime = s.st_mtime
        s.st_atime = s.st_mtime

        return s

    @property
    def contexts(self):
        c = set()

        for item in self.items:
            for t in item.tags:
                context = t.context

                if context is None:
                    continue

                c.add(context)

        return c

    @property
    def _enableItemLinks(self):
        return True

    @property
    def _entries(self):
        # the import is not global because we want to prevent a cyclic
        # dependency (ugly but works)
        from node_filter_context import ContextValueListDirectoryNode
        from node_filter_value import ValueFilterDirectoryNode
        from node_filter_any_context import AnyContextValueListDirectoryNode

        yield ExportDirectoryNode(self.itemAccess, self)

        yield AnyContextValueListDirectoryNode(self.itemAccess, self.config, self)

        if(self.config.enableValueFilters):
            for value in self.itemAccess.values:
                yield ValueFilterDirectoryNode(self.itemAccess, self.config, self, value)

        for context in self.contexts:
            yield ContextValueListDirectoryNode(self.itemAccess, self.config, self, context)

        if(self._enableItemLinks):
            for item in self.items:
                yield ItemLinkNode(item)

    def addsValue(self, parentItems):
        itemsLen = len(list(self.items))
        if(itemsLen == 0):
            return False

        # TODO we should not compare the lengths but whether the child and
        # parent items are different
        parentItemsLen = len(list(parentItems))

        return itemsLen != parentItemsLen

    def _addsValue(self, child):
        return child.addsValue(self.items)

########NEW FILE########
__FILENAME__ = node_filter_any_context
#
# Copyright 2012 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

from cache import cache
from node import Stat, ItemLinkNode, DirectoryNode
from node_filter import FilterDirectoryNode
from node_untagged_items import UntaggedItemsDirectoryNode

class AnyContextValueFilterDirectoryNode(FilterDirectoryNode):

    def __init__(self, itemAccess, config, parentNode, value):
        super(AnyContextValueFilterDirectoryNode, self).__init__(itemAccess, config)
        self.parentNode = parentNode
        self.value = value

    @property
    def name(self):
        return self.value

    @property
    def items(self):
        for item in self.parentNode.items:
            if not item.isTaggedWithValue(self.value):
                continue

            yield item
    
class AnyContextValueListDirectoryNode(DirectoryNode):

    def __init__(self, itemAccess, config, parentNode):
        self.itemAccess = itemAccess
        self.config = config
        self.parentNode = parentNode

    @property
    def name(self):
        return '.any_context'

    @property
    def attr(self):
        s = super(AnyContextValueListDirectoryNode, self).attr

        # TODO why nlink == 2?
        s.st_nlink = 2

        # TODO write test case which tests st_mtime == itemAccess.parseTime
        s.st_mtime = self.itemAccess.parseTime
        s.st_ctime = s.st_mtime
        s.st_atime = s.st_mtime

        return s

    @property
    def items(self):
        return self.parentNode.items

    @property
    def contextValues(self):
        values = set()

        for item in self.parentNode.items:
            for v in item.values:
                values.add(v)

        return values

    @property
    def _entries(self):
        for value in self.contextValues:
            yield AnyContextValueFilterDirectoryNode(self.itemAccess, self.config, self, value)

    def addsValue(self, parentItems):
        if(super(AnyContextValueListDirectoryNode, self).addsValue(parentItems)):
            return True

        for e in self._entries:
            if(e.addsValue(parentItems)):
                return True

        return False

########NEW FILE########
__FILENAME__ = node_filter_context
#
# Copyright 2011 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

from cache import cache
from node import Stat, ItemLinkNode, DirectoryNode
from node_filter import FilterDirectoryNode
from node_untagged_items import UntaggedItemsDirectoryNode

class ContextValueFilterDirectoryNode(FilterDirectoryNode):

    def __init__(self, itemAccess, config, parentNode, context, value):
        super(ContextValueFilterDirectoryNode, self).__init__(itemAccess, config)
        self.parentNode = parentNode
        self.context = context
        self.value = value

    @property
    def name(self):
        return self.value

    @property
    def items(self):
        for item in self.parentNode.items:
            if not item.isTaggedWithContextValue(self.context, self.value):
                continue

            yield item
    
class UnsetContextFilterDirectoryNode(FilterDirectoryNode):

    def __init__(self, itemAccess, config, parentNode, context):
        super(UnsetContextFilterDirectoryNode, self).__init__(itemAccess, config)
        self.parentNode = parentNode
        self.context = context

    @property
    def name(self):
        return '.unset'

    @property
    def items(self):
        for item in self.parentNode.parentNode.items:
            if item.isTaggedWithContext(self.context):
                continue

            yield item

class ContextValueListDirectoryNode(DirectoryNode):
    
    def __init__(self, itemAccess, config, parentNode, context):
        self.itemAccess = itemAccess
        self.config = config
        self.parentNode = parentNode
        self.context = context

    @property
    def name(self):
        return self.context

    @property
    def attr(self):
        s = super(ContextValueListDirectoryNode, self).attr

        # TODO why nlink == 2?
        s.st_nlink = 2

        # TODO write test case which tests st_mtime == itemAccess.parseTime
        s.st_mtime = self.itemAccess.parseTime
        s.st_ctime = s.st_mtime
        s.st_atime = s.st_mtime

        return s

    @property
    def items(self):
        for item in self.parentNode.items:
            if not item.isTaggedWithContext(self.context):
                continue

            yield item

    @property
    def contextValues(self):
        values = set()

        for item in self.parentNode.items:
            for tag in item.getTagsByContext(self.context):
                values.add(tag.value)

        return values

    @property
    def _entries(self):
        yield UnsetContextFilterDirectoryNode(self.itemAccess, self.config, self, self.context)

        for value in self.contextValues:
            yield ContextValueFilterDirectoryNode(self.itemAccess, self.config, self, self.context, value)

    def addsValue(self, parentItems):
        for e in self._entries:
            if(e.addsValue(parentItems)):
                return True

        return False

########NEW FILE########
__FILENAME__ = node_filter_value
#
# Copyright 2012 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

from node_filter import FilterDirectoryNode

class ValueFilterDirectoryNode(FilterDirectoryNode):

    def __init__(self, itemAccess, config, parentNode, value):
        super(ValueFilterDirectoryNode, self).__init__(itemAccess, config)
        self.parentNode = parentNode
        self.value = value

    @property
    def name(self):
        return self.value

    @property
    def items(self):
        for item in self.parentNode.items:
            if not item.isTaggedWithValue(self.value):
                continue

            yield item
    

########NEW FILE########
__FILENAME__ = node_root
#
# Copyright 2011 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

from node_filter import FilterDirectoryNode
from node_untagged_items import UntaggedItemsDirectoryNode

class RootDirectoryNode(FilterDirectoryNode):

    def __init__(self, itemAccess, config):
        super(RootDirectoryNode, self).__init__(itemAccess, config)

    @property
    def items(self):
        return self.itemAccess.taggedItems

    @property
    def _enableItemLinks(self):
        return self.config.enableRootItemLinks

    @property
    def _entries(self):
        yield UntaggedItemsDirectoryNode('.untagged', self.itemAccess)

        for e in super(RootDirectoryNode, self)._entries:
            yield e

########NEW FILE########
__FILENAME__ = node_untagged_items
#
# Copyright 2011 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

from cache import cache
from node import Stat, ItemLinkNode, DirectoryNode

class UntaggedItemsDirectoryNode(DirectoryNode):
    
    def __init__(self, name, itemAccess):
        self.name = name
        self.itemAccess = itemAccess

    @property
    def attr(self):
        s = super(UntaggedItemsDirectoryNode, self).attr

        # TODO why nlink == 2?
        s.st_nlink = 2

        # TODO write test case which tests st_mtime == itemAccess.parseTime
        s.st_mtime = self.itemAccess.parseTime
        s.st_ctime = s.st_mtime
        s.st_atime = s.st_mtime

        return s

    @property
    def _entries(self):
        for item in self.itemAccess.untaggedItems:
            yield ItemLinkNode(item)

########NEW FILE########
__FILENAME__ = sysIO
#
# Copyright 2012 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.

import os.path

def createSystem():
    return System(open = open, pathExists = os.path.exists)

class System(object):
    '''Abstraction layer for system access.

    This class can be used to mock system access in tests.
    '''

    def __init__(self, open = None, pathExists = None):
        self.open = open
        self.pathExists = pathExists

########NEW FILE########
__FILENAME__ = transient_dict
#
# Copyright 2010 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

class TransientDict(object):

    class Version(object):
        
        def __init__(self, key):
            self.key = key

        def touch(self, version):
            self.version = version

    class Value(object):
        
        def __init__(self, value, version):
            self.value = value
            self.version = version

    def __init__(self, averageCapacity):
        self.averageCapacity = averageCapacity
        self.nextVersion = 0
        self.setCounter = 0
        self.data = {}
        self.versions = []
    
    def __getitem__(self, k):
        v = self.data[k]

        if not v:
            return None

        v.version.touch(self.nextVersion)
        self.nextVersion += 1

        return v.value

    def _cleanUpCache(self):
        if len(self.data) < self.averageCapacity:
            return

        def versionCmp(a, b):
            if a.version < b.version:
                return 1
            if b.version < a.version:
                return -1

            return 0

        self.versions.sort(versionCmp)

        while len(self.versions) > self.averageCapacity:
            version = self.versions.pop()

            self.data.pop(version.key)

    def __setitem__(self, k, v):
        if k in self.data:
            value = self.data[k]

            value.value = v
        else:
            self.setCounter += 1
            if self.setCounter % self.averageCapacity == 0:
                self._cleanUpCache()

            version = TransientDict.Version(k)
            self.versions.append(version)

            value = TransientDict.Value(v, version)
            self.data[k] = value

        value.version.touch(self.nextVersion)
        self.nextVersion += 1

    def __contains__(self, k):
        return k in self.data

########NEW FILE########
__FILENAME__ = view
#!/usr/bin/env python
#
# Copyright 2009, 2010 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

import errno
import logging
import os
from log import logCall, logException
from cache import cache
from transient_dict import TransientDict
from node_root import RootDirectoryNode
from fuse import Direntry

class View(object):
    """Abstraction layer from fuse API.

    This class is an abstraction layer from the fuse API. This should ease
    writing test cases for the file system.
    """

    DEFAULT_NODES = {
        # directory icons for rox filer
        '.DirIcon': None,

        # launch script for rox filer application directories
        'AppRun': None
        }
    
    def __init__(self, itemAccess, config):
        self.itemAccess = itemAccess
        self.config = config
        self._entryCache = TransientDict(100)

    @property
    @cache
    def rootNode(self):
        return RootDirectoryNode(self.itemAccess, self.config)

    def getNode(self, path):
        if path in self._entryCache:
            # simple path name based caching is implemented here

            logging.debug('tagfs _entryCache hit')

            return self._entryCache[path]

        # ps contains the path segments
        ps = [x for x in os.path.normpath(path).split(os.sep) if x != '']

        psLen = len(ps)
        if psLen > 0:
            lastSegment = ps[psLen - 1]
            
            if lastSegment in View.DEFAULT_NODES:
                logging.debug('Using default node for path ' + path)

                return View.DEFAULT_NODES[lastSegment]

        e = self.rootNode

        for pe in path.split('/')[1:]:
            if pe == '':
                continue

            entries = e.entries

            if not pe in entries:
                # it seems like we are trying to fetch a node for an illegal
                # path

                return None

            e = entries[pe]

        logging.debug('tagfs _entryCache miss')
        self._entryCache[path] = e

        return e

    @logCall
    def getattr(self, path):
        e = self.getNode(path)

        if not e:
            logging.debug('Try to read attributes from not existing node: ' + path)

            return -errno.ENOENT

        return e.attr

    @logCall
    def readdir(self, path, offset):
        e = self.getNode(path)

        if not e:
            logging.warn('Try to read not existing directory: ' + path)

            return -errno.ENOENT

        # TODO care about offset parameter

        return [Direntry(name) for name in e.entries.iterkeys()]

    @logCall
    def readlink(self, path):
        n = self.getNode(path)

        if not n:
            logging.warn('Try to read not existing link from node: ' + path)

            return -errno.ENOENT

        return n.link

    @logCall
    def symlink(self, path, linkPath):
        linkPathSegs = linkPath.split('/')

        n = self.getNode('/'.join(linkPathSegs[0:len(linkPathSegs) - 2]))

        if not n:
            return -errno.ENOENT

        return n.symlink(path, linkPath)

    @logCall
    def open(self, path, flags):
        n = self.getNode(path)

        if not n:
            logging.warn('Try to open not existing node: ' + path)

            return -errno.ENOENT

        return n.open(path, flags)

    @logCall
    def read(self, path, len, offset):
        n = self.getNode(path)

        if not n:
            logging.warn('Try to read from not existing node: ' + path)

            return -errno.ENOENT

        return n.read(path, len, offset)

    @logCall
    def write(self, path, data, pos):
        n = self.getNode(path)

        if not n:
            logging.warn('Try to write to not existing node: ' + path)

            return -errno.ENOENT

        return n.write(path, data, pos)
	

########NEW FILE########
__FILENAME__ = item_access_mock
#
# Copyright 2011 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

from tagfs_test.item_mock import ItemMock

class ItemAccessMock(object):

    def __init__(self):
        self.parseTime = 42
        self.taggedItems = []
        self.untaggedItems = []

########NEW FILE########
__FILENAME__ = item_mock
#
# Copyright 2011 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

class ItemMock(object):

    def __init__(self, name, tags = []):
        self.name = name
        self.tags = tags

def createItemMocks(itemNames):
    return [ItemMock(name, []) for name in itemNames]

########NEW FILE########
__FILENAME__ = node_asserter
#
# Copyright 2011 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

import stat

def hasMode(attr, mode):
    return (attr.st_mode & mode > 0)

def validateNodeInterface(test, node):
    attr = node.attr

    test.assertTrue(attr.st_atime >= 0)
    test.assertTrue(attr.st_mtime >= 0)
    test.assertTrue(attr.st_ctime >= 0)

def validateDirectoryInterface(test, node):
    attr = node.attr

    test.assertTrue(hasMode(attr, stat.S_IFDIR))

    validateNodeInterface(test, node)

def validateLinkInterface(test, node):
    attr = node.attr

    test.assertTrue(hasMode(attr, stat.S_IFLNK))

    validateNodeInterface(test, node)

########NEW FILE########
__FILENAME__ = systemMocks
#
# Copyright 2012 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.

class ReadLineFileMock(object):

    def __init__(self, lines):
        self.lines = lines

    def __enter__(self, *args, **kwargs):
        return self.lines

    def __exit__(self, *args, **kwargs):
        pass

class SystemMock(object):

    def __init__(self, test, readFiles = {}):
        self.test = test
        self.readFiles = readFiles

    def open(self, fileName, mode):
        if(mode == 'r'):
            return self.readFiles[fileName]

        self.test.fail('Unknown file mode %s' % mode)

    def pathExists(self, path):
        return path in self.readFiles

########NEW FILE########
__FILENAME__ = test_filter_context_value_filter_directory_node
#
# Copyright 2011 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

from unittest import TestCase

from tagfs.node_filter_context import ContextValueFilterDirectoryNode

from tagfs_test.node_asserter import validateDirectoryInterface, validateLinkInterface
from tagfs_test.item_access_mock import ItemAccessMock
from tagfs_test.item_mock import ItemMock

class TagMock(object):

    def __init__(self, context, value):
        self.context = context
        self.value = value

class TaggedItemMock(ItemMock):

    def __init__(self, name, context, value):
        super(TaggedItemMock, self).__init__(name, [TagMock(context, value), ])

        self._context = context
        self._value = value

    def isTaggedWithContext(self, context):
        return self._context == context

    def isTaggedWithContextValue(self, context, value):
        return self._context == context and self._value == value

    def getTagsByContext(self, context):
        if(context == self._context):
            return self.tags
        else:
            return []

class ParentNodeMock(object):

    def __init__(self, items):
        self.items = items

class ConfigMock(object):

    @property
    def enableValueFilters(self):
        return False

class TestContextValueFilterDirectoryNode(TestCase):

    def setUp(self):
        self.context = 'c1'
        self.value = 'v1'

        self.itemAccess = ItemAccessMock()
        self.itemAccess.taggedItems = [TaggedItemMock('item1', self.context, self.value), ]

        self.config = ConfigMock()

        self.parentNode = ParentNodeMock(self.itemAccess.taggedItems)
        self.node = ContextValueFilterDirectoryNode(self.itemAccess, self.config, self.parentNode, self.context, self.value)

    def testNodeAttrMTimeIsItemAccessParseTime(self):
        attr = self.node.attr

        self.assertEqual(self.itemAccess.parseTime, attr.st_mtime)

    def testNodeIsDirectory(self):
        validateDirectoryInterface(self, self.node)

    def testMatchingItemIsAvailableAsLink(self):
        e = self.node.entries['item1']

        validateLinkInterface(self, e)

########NEW FILE########
__FILENAME__ = test_filter_context_value_list_directory_node
#
# Copyright 2011 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

from unittest import TestCase

from tagfs.node_filter_context import ContextValueListDirectoryNode

from tagfs_test.node_asserter import validateDirectoryInterface, validateLinkInterface
from tagfs_test.item_access_mock import ItemAccessMock
from tagfs_test.item_mock import createItemMocks

class ParentNodeMock(object):

    pass

class TestContextValueListDirectoryNode(TestCase):

    def setUp(self):
        self.itemAccess = ItemAccessMock()
        self.itemAccess.taggedItems = createItemMocks(['item1'])

        self.parentNode = ParentNodeMock()
        self.context = 'c1'
        self.node = ContextValueListDirectoryNode(self.itemAccess, None, self.parentNode, self.context)

    def testNodeAttrMTimeIsItemAccessParseTime(self):
        attr = self.node.attr

        self.assertEqual(self.itemAccess.parseTime, attr.st_mtime)

    def testNodeIsDirectory(self):
        validateDirectoryInterface(self, self.node)

########NEW FILE########
__FILENAME__ = test_freebase_support_genericQueryFactory
#
# Copyright 2013 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.

import unittest
import tagfs.freebase_support as freebase_support

class WhenGenericQueryFactoryWithVariables(unittest.TestCase):

    def resolveVar(self, name):
        return self.variables[name]

    def setUp(self):
        super(WhenGenericQueryFactoryWithVariables, self).setUp()

        self.variables = {}
        self.factory = freebase_support.GenericQueryFactory(self.resolveVar)

        self.varValue = 'value'
        self.variables['var'] = self.varValue

    def testResolveExistingVariable(self):
        q = {'key': '$var',}

        self.assertEqual(self.factory.createQuery(q), {'key': self.varValue,})

    def testCreatedQueryIsNewInstance(self):
        q = {}

        self.assertTrue(not q is self.factory.createQuery(q))

    def testGenericQueryIsUntouched(self):
        q = {'key': '$var',}

        self.factory.createQuery(q)

        self.assertEqual(q, {'key': '$var',})

    def testResolveValueToNone(self):
        q = {'key': None,}

        self.assertEqual(self.factory.createQuery(q), q)

########NEW FILE########
__FILENAME__ = test_freebase_support_query
#
# Copyright 2012 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.

import unittest
import tagfs.freebase_support as freebase_support

class WhenQueryWithOneFilerAndOneSelector(unittest.TestCase):

    def setUp(self):
        super(WhenQueryWithOneFilerAndOneSelector, self).setUp()

        self.query = freebase_support.Query({'filter': 'filterValue', 'selector': None, })

    def testThenSelectedKeysIsSelector(self):
        self.assertEqual(list(self.query.selectedKeys), ['selector',])

    def testThenQueryStringIs(self):
        self.assertEqual(self.query.queryString, '{"filter":"filterValue","selector":[]}')

########NEW FILE########
__FILENAME__ = test_freebase_support_queryFileParser
#
# Copyright 2013 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.

import unittest
import tagfs.freebase_support as freebase_support
import systemMocks

class QueryParserMock(object):

    def parse(self, queryString):
        return 'rule'

class WhenFileWithOneLineExists(unittest.TestCase):

    def setUp(self):
        super(WhenFileWithOneLineExists, self).setUp()

        self.filePath = '/path/to/my/file'

        self.system = systemMocks.SystemMock(self)
        self.system.readFiles[self.filePath] = systemMocks.ReadLineFileMock(['line1',])

        self.queryParser = QueryParserMock()
        self.queryFileParser = freebase_support.QueryFileParser(self.system, self.queryParser)

    def testThenParsesOneLine(self):
        self.assertEqual(list(self.queryFileParser.parseFile(self.filePath)), ['rule',])

########NEW FILE########
__FILENAME__ = test_item_access_item
#
# Copyright 2012 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.

import unittest

import tagfs.item_access as item_access
import systemMocks

class ItemAccessMock(object):

    def __init__(self, dataDirectory, tagFileName):
        self.dataDirectory = dataDirectory
        self.tagFileName = tagFileName

class FreebaseQueryParserMock(object):

    def __init__(self, test):
        self.test = test

    def parse(self, queryString):
        return queryString

class FreebaseAdapterMock(object):

    def __init__(self, test):
        self.test = test

    def execute(self, query):
        return {
            'freebaseContext': ['freebaseValue'],
            }

class WhenItemHasFreebaseQueryTag(unittest.TestCase):

    def setUp(self):
        super(WhenItemHasFreebaseQueryTag, self).setUp()

        self.system = systemMocks.SystemMock(self)
        self.system.readFiles['/path/to/my/data/directory/myItem/.tag'] = systemMocks.ReadLineFileMock(['_freebase: myFreebaseQuery',])

        self.itemAccess = ItemAccessMock('/path/to/my/data/directory', '.tag')
        self.freebaseQueryParser = FreebaseQueryParserMock(self)
        self.freebaseAdapter = FreebaseAdapterMock(self)

        self.item = item_access.Item('myItem', self.system, self.itemAccess, self.freebaseQueryParser, self.freebaseAdapter)

    def testThenItemHasFreebaseTaggingsFromItemAccess(self):
        self.assertEqual(list(self.item.getTagsByContext('freebaseContext')), [item_access.Tag('freebaseValue', 'freebaseContext'),])

########NEW FILE########
__FILENAME__ = test_item_access_parseTagsFromFile
#
# Copyright 2012 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.

import unittest
import tagfs.item_access as item_access
import systemMocks

class ParseTagsFromFileTest(unittest.TestCase):

    def setUp(self):
        super(ParseTagsFromFileTest, self).setUp()

        self.system = systemMocks.SystemMock(self)

    def setTagFileContent(self, lines):
        self.system.readFiles['.tag'] = systemMocks.ReadLineFileMock(lines)

    def assertParseTags(self, expectedTags):
        self.assertEqual(list(item_access.parseTagsFromFile(self.system, '.tag')), expectedTags)

    def testParseTagWithoutContext(self):
        self.setTagFileContent(['value',])

        self.assertParseTags([item_access.Tag('value'),])

    def testParseTagWithContext(self):
        self.setTagFileContent(['context: value',])

        self.assertParseTags([item_access.Tag('value', 'context'),])

    def testIgnoreEmptyLines(self):
        self.setTagFileContent(['',])

        self.assertParseTags([])

    def testIgnoreLinesWithJustSpaces(self):
        self.setTagFileContent(['\t ',])

        self.assertParseTags([])

########NEW FILE########
__FILENAME__ = test_item_access_tag
#
# Copyright 2012 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

from unittest import TestCase

import tagfs.item_access as item_access

class TagTest(TestCase):

    def testTagValueInfluencesHash(self):
        self.assertTrue(item_access.Tag('a', None).__hash__() != item_access.Tag('b', None).__hash__())

    def testTagContextInfluencesHash(self):
        self.assertTrue(item_access.Tag('v', None).__hash__() != item_access.Tag('v', 'c').__hash__())

    def testEqualTagsEqWhenContextNone(self):
        self.assertTrue(item_access.Tag('t', None).__eq__(item_access.Tag('t', None)))

    def testEqualTagsEqWhenContextStr(self):
        self.assertTrue(item_access.Tag('t', 'c').__eq__(item_access.Tag('t', 'c')))

########NEW FILE########
__FILENAME__ = test_root_directory_node
#
# Copyright 2011 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

from unittest import TestCase

from tagfs.node_root import RootDirectoryNode

from tagfs_test.node_asserter import validateDirectoryInterface, validateLinkInterface
from tagfs_test.item_access_mock import ItemAccessMock
from tagfs_test.item_mock import createItemMocks

class ConfigMock(object):

    @property
    def enableValueFilters(self):
        return False

    @property
    def enableRootItemLinks(self):
        return True

class AbstractRootDirectoryNodeTest(TestCase):

    @property
    def _itemNames(self):
        return self._taggedItemNames
    
    def setUp(self):
        self._taggedItemNames = ['item1']

        self.itemAccess = ItemAccessMock()
        self.itemAccess.taggedItems = createItemMocks(self._itemNames)

        self.config = ConfigMock()

        self.node = RootDirectoryNode(self.itemAccess, self.config)

class TestRootDirectoryNode(AbstractRootDirectoryNodeTest):

    @property
    def _itemNames(self):
        return self._taggedItemNames + ['.untagged']

    def testNodeAttrMTimeIsItemAccessParseTime(self):
        attr = self.node.attr

        self.assertEqual(self.itemAccess.parseTime, attr.st_mtime)

    def testNodeIsDirectory(self):
        validateDirectoryInterface(self, self.node)

    def testItemLinksReplaceUntaggedDirectory(self):
        untaggedNode = self.node.entries['.untagged']

        # untagged node must be a link as the untagged directory node
        # weights less than the '.untagged' item from the tagged items.
        validateLinkInterface(self, untaggedNode)

    def testNodeContainerContainsTaggedNodeLinks(self):
        entries = self.node.entries

        for itemName in self._taggedItemNames:
            self.assertTrue(itemName in entries)

            validateLinkInterface(self, entries[itemName])

class TestRootDirectoryNodeUntaggedDirectory(AbstractRootDirectoryNodeTest):

    def testNodeContainsUntaggedDirectory(self):
        untaggedNode = self.node.entries['.untagged']

        validateDirectoryInterface(self, untaggedNode)

########NEW FILE########
__FILENAME__ = test_transient_dict
#
# Copyright 2010 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

import unittest
from tagfs.transient_dict import TransientDict

class TestTransientDict(unittest.TestCase):
    
    def testGetAndSetValues(self):
        d = TransientDict(10)

        self.assertTrue('1' not in d)

        d['1'] = 'a'
        d['2'] = 'b'

        self.assertTrue(d['1'] == 'a')
        self.assertTrue(d['2'] == 'b')

        self.assertTrue('1' in d)
        self.assertTrue('3' not in d)
        self.assertTrue('a' not in d)

    def testForgettValuesWhenDictSizeExceeded(self):
        d = TransientDict(2)

        d['1'] = 'a'
        d['2'] = 'b'
        d['1'] = 'a'
        d['3'] = 'c'
        d['1'] = 'a'
        d['4'] = 'c'

        self.assertTrue('1' in d)
        self.assertTrue('2' not in d)
        self.assertTrue('4' in d)

########NEW FILE########
__FILENAME__ = test_untagged_items_directory_node
#
# Copyright 2011 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

from unittest import TestCase

from tagfs.node_untagged_items import UntaggedItemsDirectoryNode

from tagfs_test.node_asserter import validateLinkInterface, validateDirectoryInterface
from tagfs_test.item_access_mock import ItemAccessMock
from tagfs_test.item_mock import createItemMocks

class TestUntaggedItemsDirectoryNode(TestCase):

    def setUp(self):
        self.itemAccess = ItemAccessMock()
        self.itemAccess.untaggedItems = createItemMocks(['item1', 'item2'])

        self.nodeName = 'e'
        self.node = UntaggedItemsDirectoryNode(self.nodeName, self.itemAccess)

    def testNodeAttrMTimeIsItemAccessParseTime(self):
        attr = self.node.attr

        self.assertEqual(self.itemAccess.parseTime, attr.st_mtime)

    def testNodeIsDirectory(self):
        validateDirectoryInterface(self, self.node)

    def testUntaggedItemAccessItemsAreUntaggedItemsDirectoryEntries(self):
        entries = self.node.entries

        self.assertEqual(len(self.itemAccess.untaggedItems), len(entries))

        for i in self.itemAccess.untaggedItems:
            self.assertTrue(i.name in entries)

            validateLinkInterface(self, entries[i.name])

    def testNodeHasName(self):
        self.assertEqual(self.nodeName, self.node.name)

########NEW FILE########
__FILENAME__ = trace_logfiles
#!/usr/bin/env python
#
# Copyright 2010 Markus Pielmeier
#
# This file is part of tagfs.
#
# tagfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tagfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tagfs.  If not, see <http://www.gnu.org/licenses/>.
#

import logging
import re

class TraceLogEntry(object):

    def __init__(self, context, path):
        self.context = context
        self.path = path

class TraceLog(object):

    LINE_BUFFER_SIZE = 100000

    TRACE_PATTERN = re.compile('[0-9\-,: ]+DEBUG (readlink|getattr|readdir) (.*)$')

    def __init__(self):
        self.entries = []

    def _readLogLine(self, line):
        m = TraceLog.TRACE_PATTERN.match(line)

        if not m:
            return

        context = m.group(1)
        path = m.group(2)

        self.entries.append(TraceLogEntry(context, path))

    def readLogFile(self, fileName):
        logging.info('Reading logfile ' + fileName)

        f = open(fileName)

        while True:
            lines = f.readlines(TraceLog.LINE_BUFFER_SIZE)
            if not lines:
                break;

            for line in lines:
                self._readLogLine(line)

class TraceResult(object):

    def __init__(self):
        self.contextHistogram = {}
        self.contextPathHistogram = {}

    def _analyzeContextHistogram(self, traceLog):
        for e in traceLog.entries:
            if not e.context in self.contextHistogram:
                self.contextHistogram[e.context] = 0

            self.contextHistogram[e.context] += 1

    def _analyzeContextPathHistogram(self, traceLog):
        for e in traceLog.entries:
            if not e.context in self.contextPathHistogram:
                self.contextPathHistogram[e.context] = {}

            ph = self.contextPathHistogram[e.context]

            if not e.path in ph:
                ph[e.path] = 0

            ph[e.path] += 1
            

    def _analyzeTraceLog(self, traceLog):
        self._analyzeContextHistogram(traceLog)
        self._analyzeContextPathHistogram(traceLog)

    def analyzeLogFile(self, fileName):
        tl = TraceLog()
        tl.readLogFile(fileName)

        self._analyzeTraceLog(tl)

def usage():
    # TODO print usage

    pass

def writeCSV(fileName, pathHistogram):
    import csv

    w = csv.writer(open(fileName, 'w'))
    
    for path, histogram in pathHistogram.iteritems():
        w.writerow([path, histogram])

if __name__ == '__main__':
    logging.basicConfig(level = logging.DEBUG)

    import getopt
    import sys

    try:
        opts, args = getopt.getopt(sys.argv[1:], "", [])
    except getopt.GetoptError:
        usage()

        sys.exit(1)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()

    tr = TraceResult()

    for fileName in args:
        tr.analyzeLogFile(fileName)

    print "Context Histogram"
    for context, calls in tr.contextHistogram.iteritems():
        print ' %s: %s' % (context, calls)

    for context, pathHistogram in tr.contextPathHistogram.iteritems():
        writeCSV('pathHistogram_' + context + '.csv', pathHistogram)

########NEW FILE########
