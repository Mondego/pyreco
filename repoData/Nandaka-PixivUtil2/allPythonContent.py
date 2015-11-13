__FILENAME__ = PixivBrowserFactory
﻿# -*- coding: UTF-8 -*-
from mechanize import Browser
import mechanize
import cookielib
import socket
import socks
import urlparse
import urllib
import urllib2
import httplib

import PixivHelper

defaultCookieJar = None
defaultConfig = None

def getBrowser(config = None, cookieJar = None):
    global defaultCookieJar
    global defaultConfig

    if config != None:
        defaultConfig = config
    if cookieJar != None:
        defaultCookieJar = cookieJar
    if defaultCookieJar == None:
        PixivHelper.GetLogger().info("No default cookie jar available, creating... ")
        defaultCookieJar = cookielib.LWPCookieJar()
    browser = Browser(factory=mechanize.RobustFactory())
    configureBrowser(browser, defaultConfig)
    configureCookie(browser, defaultCookieJar)
    return browser

def configureBrowser(browser, config):
    if config == None:
        PixivHelper.GetLogger().info("No config given")
        return

    global defaultConfig
    if defaultConfig == None:
        defaultConfig = config

    if config.useProxy:
      if config.proxyAddress.startswith('socks'):
        parseResult = urlparse.urlparse(config.proxyAddress)
        assert parseResult.scheme and parseResult.hostname and parseResult.port
        socksType = socks.PROXY_TYPE_SOCKS5 if parseResult.scheme == 'socks5' else socks.PROXY_TYPE_SOCKS4

        socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, parseResult.hostname, parseResult.port)
        socks.wrapmodule(urllib)
        socks.wrapmodule(urllib2)
        socks.wrapmodule(httplib)

        PixivHelper.GetLogger().info("Using SOCKS Proxy: " + config.proxyAddress)
      else:
        browser.set_proxies(config.proxy)
        PixivHelper.GetLogger().info("Using Proxy: " + config.proxyAddress)

    browser.set_handle_equiv(True)
    #browser.set_handle_gzip(True)
    browser.set_handle_redirect(True)
    browser.set_handle_referer(True)
    browser.set_handle_robots(config.useRobots)

    browser.set_debug_http(config.debugHttp)
    if config.debugHttp :
        PixivHelper.GetLogger().info('Debug HTTP enabled.')

    browser.visit_response
    browser.addheaders = [('User-agent', config.useragent)]

    socket.setdefaulttimeout(config.timeout)

def configureCookie(browser, cookieJar):
    if cookieJar != None:
        browser.set_cookiejar(cookieJar)

        global defaultCookieJar
        if defaultCookieJar == None:
            defaultCookieJar = cookieJar

def addCookie(cookie):
    global defaultCookieJar
    if defaultCookieJar == None:
        defaultCookieJar = cookielib.LWPCookieJar()
    defaultCookieJar.set_cookie(cookie)


########NEW FILE########
__FILENAME__ = PixivConfig
﻿#!/usr/bin/python
# -*- coding: UTF-8 -*-

import ConfigParser
import sys
import os
import codecs
import traceback
import PixivHelper
import shutil
import time

script_path = PixivHelper.module_path()

class PixivConfig:
    '''Configuration class'''
    __logger = PixivHelper.GetLogger()
    ## default value
    proxyAddress = ''
    proxy = {'http': proxyAddress, 'https': proxyAddress, }
    useProxy = False

    username = ''
    password = ''

    useragent = 'Mozilla/5.0 (X11; U; Unix i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1'
    debugHttp = False

    numberOfPage = 0
    useRobots = True
    filenameFormat = unicode('%artist% (%member_id%)' + os.sep + '%urlFilename% - %title%')
    filenameMangaFormat = unicode('%artist% (%member_id%)' + os.sep + '%urlFilename% - %title%')
    rootDirectory = unicode('.')
    overwrite = False
    timeout = 60

    useList = False
    processFromDb = True
    dayLastUpdated = 7

    tagsSeparator = unicode(', ')

    retry = 3
    retryWait = 5

    alwaysCheckFileSize = False
    checkUpdatedLimit = 0
    downloadAvatar = True

    cookie = ''
    createMangaDir = False
    useTagsAsDir = False
    useBlacklistTags = False
    useSuppressTags = False
    tagsLimit = -1
    useSSL = False
    writeImageInfo = False
    r18mode = False
    dateDiff = 0
    keepSignedIn = 0

    #Yavos: added next three lines
    createDownloadLists = False
    downloadListDirectory = unicode('.')
    startIrfanView = False
    startIrfanSlide = False
    IrfanViewPath = unicode('C:\Program Files\IrfanView')

    backupOldFile = False

    logLevel = "DEBUG"
    enableDump = True
    skipDumpFilter = ""
    dumpMediumPage = False

    def loadConfig(self, path=None):
        if path != None:
            configFile = path
        else:
            configFile = script_path + os.sep + 'config.ini'
        
        print 'Reading', configFile, '...'
        oldSetting = False
        haveError = False
        config = ConfigParser.RawConfigParser()
        try:
            config.readfp(PixivHelper.OpenTextFile(configFile))

            self.username = config.get('Authentication','username')

            self.password = config.get('Authentication','password')

            self.cookie = config.get('Authentication','cookie')

            self.tagsSeparator = PixivHelper.toUnicode(config.get('Settings','tagsseparator'), encoding=sys.stdin.encoding)
            self.rootDirectory = PixivHelper.toUnicode(config.get('Settings','rootdirectory'), encoding=sys.stdin.encoding)

            try:
                self.IrfanViewPath = PixivHelper.toUnicode(config.get('Settings','IrfanViewPath'), encoding=sys.stdin.encoding)
                self.downloadListDirectory = PixivHelper.toUnicode(config.get('Settings','downloadListDirectory'), encoding=sys.stdin.encoding)
            except:
                pass

            try:
                self.processFromDb = config.getboolean('Settings','processfromdb')
            except ValueError:
                print "processFromDb = True"
                self.processFromDb = True
                haveError = True

            try:
                self.dayLastUpdated = config.getint('Settings','daylastupdated')
            except ValueError:
                print "dayLastUpdated = 7"
                self.dayLastUpdated = 7
                haveError = True

            try:
                self.dateDiff = config.getint('Settings','datediff')
            except ValueError:
                print "dateDiff = 0"
                self.dateDiff = 0
                haveError = True

            try:
                self.proxyAddress = config.get('Settings','proxyaddress')
            except ValueError:
                print "proxyAddress = ''"
                self.proxyAddress = ''
                haveError = True
            self.proxy = {'http': self.proxyAddress, 'https': self.proxyAddress}

            try:
                self.useProxy = config.getboolean('Settings','useproxy')
            except ValueError:
                print "useProxy = False"
                self.useProxy = False
                haveError = True

            try:
                self.useList = config.getboolean('Settings','uselist')
            except ValueError:
                print "useList = False"
                self.useList = False
                haveError = True

            try:
                self.r18mode = config.getboolean('Pixiv','r18mode')
            except ValueError:
                print "r18mode = False"
                self.r18mode = False
                haveError = True

            _useragent = config.get('Settings','useragent')
            if _useragent != None:
                self.useragent = _useragent

            _filenameFormat = config.get('Settings','filenameformat')
            _filenameFormat = PixivHelper.toUnicode(_filenameFormat, encoding=sys.stdin.encoding)
            if _filenameFormat != None:
                self.filenameFormat = _filenameFormat

            _filenameMangaFormat = config.get('Settings','filenamemangaformat')
            _filenameMangaFormat = PixivHelper.toUnicode(_filenameMangaFormat, encoding=sys.stdin.encoding)
            if _filenameMangaFormat != None:
                ## check if the filename format have page identifier if not using %urlFilename%
                if _filenameMangaFormat.find('%urlFilename%') == -1:
                    if _filenameMangaFormat.find('%page_index%') == -1 and _filenameMangaFormat.find('%page_number%') == -1:
                        print 'No page identifier, appending %page_index% to the filename manga format.'
                        _filenameMangaFormat = _filenameMangaFormat + unicode(' %page_index%')
                        print "_filenameMangaFormat =", _filenameMangaFormat
                        haveError = True
                self.filenameMangaFormat = _filenameMangaFormat

            try:
                self.debugHttp = config.getboolean('Settings','debughttp')
            except ValueError:
                self.debugHttp = False
                print "debugHttp = False"
                haveError = True

            try:
                self.useRobots = config.getboolean('Settings','userobots')
            except ValueError:
                self.useRobots = False
                print "useRobots = False"
                haveError = True

            try:
                self.overwrite = config.getboolean('Settings','overwrite')
            except ValueError:
                print "overwrite = False"
                self.overwrite = False
                haveError = True

            try:
                self.createMangaDir = config.getboolean('Settings','createMangaDir')
            except ValueError:
                print "createMangaDir = False"
                self.createMangaDir = False
                haveError = True

            try:
                self.timeout = config.getint('Settings','timeout')
            except ValueError:
                print "timeout = 60"
                self.timeout = 60
                haveError = True

            try:
                self.retry = config.getint('Settings','retry')
            except ValueError:
                print "retry = 3"
                self.retry = 3
                haveError = True

            try:
                self.retryWait = config.getint('Settings','retrywait')
            except ValueError:
                print "retryWait = 5"
                self.retryWait = 5
                haveError = True

            try:
                self.numberOfPage = config.getint('Pixiv','numberofpage')
            except ValueError:
                self.numberOfPage = 0
                print "numberOfPage = 0"
                haveError = True

            try:
                self.createDownloadLists = config.getboolean('Settings','createDownloadLists')
            except ValueError:
                self.createDownloadLists = False
                print "createDownloadLists = False"
                haveError = True

            try:
                self.startIrfanView = config.getboolean('Settings','startIrfanView')
            except ValueError:
                self.startIrfanView = False
                print "startIrfanView = False"
                haveError = True

            try:
                self.startIrfanSlide = config.getboolean('Settings','startIrfanSlide')
            except ValueError:
                self.startIrfanSlide = False
                print "startIrfanSlide = False"
                haveError = True

            try:
                self.alwaysCheckFileSize = config.getboolean('Settings','alwaysCheckFileSize')
            except ValueError:
                self.alwaysCheckFileSize = False
                print "alwaysCheckFileSize = False"
                haveError = True

            try:
                self.downloadAvatar = config.getboolean('Settings','downloadAvatar')
            except ValueError:
                self.downloadAvatar = False
                print "downloadAvatar = False"
                haveError = True

            try:
                self.checkUpdatedLimit = config.getint('Settings','checkUpdatedLimit')
            except ValueError:
                self.checkUpdatedLimit = 0
                print "checkUpdatedLimit = 0"
                haveError = True

            try:
                self.useTagsAsDir = config.getboolean('Settings','useTagsAsDir')
            except ValueError:
                self.useTagsAsDir = False
                print "useTagsAsDir = False"
                haveError = True

            try:
                self.useBlacklistTags = config.getboolean('Settings','useBlacklistTags')
            except ValueError:
                self.useBlacklistTags = False
                print "useBlacklistTags = False"
                haveError = True

            try:
                self.useSuppressTags = config.getboolean('Settings','useSuppressTags')
            except ValueError:
                self.useSuppressTags = False
                print "useSuppressTags = False"
                haveError = True

            try:
                self.tagsLimit = config.getint('Settings','tagsLimit')
            except ValueError:
                self.tagsLimit = -1
                print "tagsLimit = -1"
                haveError = True

            try:
                self.useSSL = config.getboolean('Authentication','useSSL')
            except ValueError:
                self.useSSL = False
                print "useSSL = False"
                haveError = True

            try:
                self.writeImageInfo = config.getboolean('Settings','writeImageInfo')
            except ValueError:
                self.writeImageInfo = False
                print "writeImageInfo = False"
                haveError = True

            try:
                self.keepSignedIn = config.getint('Authentication','keepSignedIn')
            except ValueError:
                print "keepSignedIn = 0"
                self.keepSignedIn = 0
                haveError = True

            try:
                self.backupOldFile = config.getboolean('Settings','backupOldFile')
            except ValueError:
                self.backupOldFile = False
                print "backupOldFile = False"
                haveError = True

            try:
                self.logLevel = config.get('Settings','logLevel').upper()
                if not self.logLevel in ['CRITICAL', 'ERROR', 'WARN', 'WARNING', 'INFO', 'DEBUG', 'NOTSET']:
                    raise ValueError("Value not in list: " + self.logLevel)
            except ValueError:
                print "logLevel = DEBUG"
                self.logLevel = 'DEBUG'
                haveError = True


            try:
                self.enableDump = config.getboolean('Settings','enableDump')
            except ValueError:
                print "enableDump = True"
                self.enableDump = True
                haveError = True

            try:
                self.skipDumpFilter = config.get('Settings','skipDumpFilter')
            except ValueError:
                print "skipDumpFilter = ''"
                self.skipDumpFilter = ''
                haveError = True

            try:
                self.dumpMediumPage = config.getboolean('Settings','dumpMediumPage')
            except ValueError:
                print "dumpMediumPage = False"
                self.dumpMediumPage = False
                haveError = True

##        except ConfigParser.NoOptionError:
##            print 'Error at loadConfig():',sys.exc_info()
##            print 'Failed to read configuration.'
##            self.writeConfig()
##        except ConfigParser.NoSectionError:
##            print 'Error at loadConfig():',sys.exc_info()
##            print 'Failed to read configuration.'
##            self.writeConfig()
        except:
            print 'Error at loadConfig():',sys.exc_info()
            self.__logger.exception('Error at loadConfig()')
            haveError = True

        if haveError:
            print 'Some configuration have invalid value, replacing with the default value.'
            self.writeConfig(error=True)

        print 'done.'


    #-UI01B------write config
    def writeConfig(self, error=False, path=None):
        '''Backup old config if exist and write updated config.ini'''
        print 'Writing config file...',
        config = ConfigParser.RawConfigParser()
        config.add_section('Settings')
        config.add_section('Pixiv')
        config.add_section('Authentication')

        config.set('Settings', 'proxyAddress',self.proxyAddress)
        config.set('Settings', 'useProxy', self.useProxy)
        config.set('Settings', 'useragent', self.useragent)
        config.set('Settings', 'debugHttp', self.debugHttp)
        config.set('Settings', 'useRobots', self.useRobots)
        config.set('Settings', 'filenameFormat', self.filenameFormat)
        config.set('Settings', 'filenameMangaFormat', self.filenameMangaFormat)
        config.set('Settings', 'timeout', self.timeout)
        config.set('Settings', 'useList', self.useList)
        config.set('Settings', 'processFromDb', self.processFromDb)
        config.set('Settings', 'overwrite', self.overwrite)
        config.set('Settings', 'tagsseparator', self.tagsSeparator)
        config.set('Settings', 'daylastupdated',self.dayLastUpdated)
        config.set('Settings', 'rootdirectory', self.rootDirectory)
        config.set('Settings', 'retry', self.retry)
        config.set('Settings', 'retrywait', self.retryWait)
        config.set('Settings', 'createDownloadLists', self.createDownloadLists)
        config.set('Settings', 'downloadListDirectory', self.downloadListDirectory)
        config.set('Settings', 'IrfanViewPath', self.IrfanViewPath)
        config.set('Settings', 'startIrfanView', self.startIrfanView)
        config.set('Settings', 'startIrfanSlide', self.startIrfanSlide)
        config.set('Settings', 'alwaysCheckFileSize', self.alwaysCheckFileSize)
        config.set('Settings', 'checkUpdatedLimit', self.checkUpdatedLimit)
        config.set('Settings', 'downloadAvatar', self.downloadAvatar)
        config.set('Settings', 'createMangaDir', self.createMangaDir)
        config.set('Settings', 'useTagsAsDir', self.useTagsAsDir)
        config.set('Settings', 'useBlacklistTags', self.useBlacklistTags)
        config.set('Settings', 'useSuppressTags', self.useSuppressTags)
        config.set('Settings', 'tagsLimit', self.tagsLimit)
        config.set('Settings', 'writeImageInfo', self.writeImageInfo)
        config.set('Settings', 'dateDiff', self.dateDiff)
        config.set('Settings', 'backupOldFile', self.backupOldFile)
        config.set('Settings', 'logLevel', self.logLevel)
        config.set('Settings', 'enableDump', self.enableDump)
        config.set('Settings', 'skipDumpFilter', self.skipDumpFilter)
        config.set('Settings', 'dumpMediumPage', self.dumpMediumPage)

        config.set('Authentication', 'username', self.username)
        config.set('Authentication', 'password', self.password)
        config.set('Authentication', 'cookie', self.cookie)
        config.set('Authentication', 'useSSL', self.useSSL)
        config.set('Authentication', 'keepSignedIn', self.keepSignedIn)

        config.set('Pixiv', 'numberOfPage', self.numberOfPage)
        config.set('Pixiv', 'R18Mode', self.r18mode)

        if path != None:
            configlocation = path
        else:
            configlocation = 'config.ini'

        try:
            ##with codecs.open('config.ini.bak', encoding = 'utf-8', mode = 'wb') as configfile:
            with open(configlocation + '.tmp', 'w') as configfile:
                config.write(configfile)
            if os.path.exists(configlocation):
                if error:
                    backupName = configlocation + '.error-' + str(int(time.time()))
                    print "Backing up old config (error exist!) to " + backupName
                    shutil.move(configlocation, backupName)
                else:
                    print "Backing up old config to config.ini.bak"
                    shutil.move(configlocation, configlocation + '.bak')
            os.rename(configlocation + '.tmp', configlocation)
        except:
            self.__logger.exception('Error at writeConfig()')
            raise

        print 'done.'

    def printConfig(self):
        print 'Configuration: '
        print ' [Authentication]'
        print ' - username     =', self.username
        print ' - password     = ', self.password
        print ' - cookie       = ', self.cookie
        print ' - useSSL       = ', self.useSSL
        print ' - keepSignedIn = ', self.keepSignedIn

        print ' [Settings]'
        print ' - filename_format       =', self.filenameFormat
        print ' - filename_manga_format =', self.filenameMangaFormat
        print ' - useproxy         =' , self.useProxy
        print ' - proxyaddress     =', self.proxyAddress
        print ' - debug_http       =', self.debugHttp
        print ' - use_robots       =', self.useRobots
        print ' - useragent        =', self.useragent
        print ' - overwrite        =', self.overwrite
        print ' - timeout          =', self.timeout
        print ' - useList          =', self.useList
        print ' - processFromDb    =', self.processFromDb
        print ' - tagsSeparator    =', self.tagsSeparator
        print ' - dayLastUpdated   =', self.dayLastUpdated
        print ' - rootDirectory    =', self.rootDirectory
        print ' - retry            =', self.retry
        print ' - retryWait        =', self.retryWait
        print ' - createDownloadLists   =', self.createDownloadLists
        print ' - downloadListDirectory =', self.downloadListDirectory
        print ' - IrfanViewPath    =', self.IrfanViewPath
        print ' - startIrfanView   =', self.startIrfanView
        print ' - startIrfanSlide  =', self.startIrfanSlide
        print ' - alwaysCheckFileSize   =', self.alwaysCheckFileSize
        print ' - checkUpdatedLimit     =', self.checkUpdatedLimit
        print ' - downloadAvatar   =', self.downloadAvatar
        print ' - createMangaDir   =', self.createMangaDir
        print ' - useTagsAsDir     =', self.useTagsAsDir
        print ' - useBlacklistTags =', self.useBlacklistTags
        print ' - useSuppressTags  =', self.useSuppressTags
        print ' - tagsLimit        =', self.tagsLimit
        print ' - writeImageInfo   =', self.writeImageInfo
        print ' - dateDiff         =', self.dateDiff
        print ' - backupOldFile    =', self.backupOldFile
        print ' - logLevel         =', self.logLevel
        print ' - enableDump       =', self.enableDump
        print ' - skipDumpFilter   =', self.skipDumpFilter
        print ' - dumpMediumPage   =', self.dumpMediumPage

        print ' [Pixiv]'
        print ' - numberOfPage =', self.numberOfPage
        print ' - R18Mode      =', self.r18mode
        print ''

########NEW FILE########
__FILENAME__ = PixivConstant
#!/usr/bin/python
# -*- coding: UTF-8 -*-

PIXIVUTIL_VERSION = '20140325'
PIXIVUTIL_LINK = 'https://nandaka.wordpress.com/tag/pixiv-downloader/'
PIXIV_URL = 'http://www.pixiv.net'
PIXIV_URL_SSL = 'https://ssl.pixiv.net/login.php'
PIXIV_CSS_LIST_ID = 'display_works'
PIXIV_CSS_PROFILE_NAME_CLASS = 'f18b'
PIXIV_CSS_IMAGE_TITLE_CLASS = 'works_data'
PIXIV_CSS_TAGS_ID = 'tags'
PIXIVUTIL_MODE_UPDATE_ONLY = '1'

## Login Settings
PIXIVUTIL_MODE_OVERWRITE = '2'
PIXIV_LOGIN_URL = '/login.php'
PIXIV_FORM_NUMBER = 1
PIXIV_FORM_NUMBER_SSL = 1

## Log Settings
PIXIVUTIL_LOG_FILE = 'pixivutil.log'
PIXIVUTIL_LOG_SIZE = 10485760
PIXIVUTIL_LOG_COUNT = 10
PIXIVUTIL_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

## Download Results
PIXIVUTIL_NOT_OK = -1
PIXIVUTIL_OK = 0
PIXIVUTIL_SKIP_OLDER = 1
PIXIVUTIL_SKIP_BLACKLIST = 2
PIXIVUTIL_KEYBOARD_INTERRUPT = 3

BUFFER_SIZE = 8192

########NEW FILE########
__FILENAME__ = PixivDBManager
﻿#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sqlite3

import sys
import os
import traceback
import logging

import codecs
from datetime import datetime

from PixivModel import PixivListItem
import PixivConfig
import PixivHelper
script_path = PixivHelper.module_path()

class PixivDBManager:
    """Pixiv Database Manager"""
    __config__ = None

    def __init__(self, target = script_path + os.sep + "db.sqlite", config=None):
        self.conn = sqlite3.connect(target)
        if config is not None:
            self.__config__ = config
        else:
            self.__config__ = PixivConfig.PixivConfig()
            self.__config__.loadConfig()

    def close(self):
        self.conn.close()

##########################################
## I. Create/Drop Database              ##
##########################################
    def createDatabase(self):
        print 'Creating database...',

        try:
            c = self.conn.cursor()

            c.execute('''CREATE TABLE IF NOT EXISTS pixiv_master_member (
                            member_id INTEGER PRIMARY KEY ON CONFLICT IGNORE,
                            name TEXT,
                            save_folder TEXT,
                            created_date DATE,
                            last_update_date DATE,
                            last_image INTEGER
                            )''')

            self.conn.commit()

            # add column isDeleted
            # 0 = false, 1 = true
            try:
                c.execute('''ALTER TABLE pixiv_master_member ADD COLUMN is_deleted INTEGER DEFAULT 0''')
                self.conn.commit()
            except:
                pass

            c.execute('''CREATE TABLE IF NOT EXISTS pixiv_master_image (
                            image_id INTEGER PRIMARY KEY,
                            member_id INTEGER,
                            title TEXT,
                            save_name TEXT,
                            created_date DATE,
                            last_update_date DATE
                            )''')
            self.conn.commit()

            print 'done.'
        except:
            print 'Error at createDatabase():',str(sys.exc_info())
            print 'failed.'
            raise
        finally:
            c.close()

    def dropDatabase(self):
        try:
            c = self.conn.cursor()
            c.execute('''DROP IF EXISTS TABLE pixiv_master_member''')
            self.conn.commit()

            c.execute('''DROP IF EXISTS TABLE pixiv_master_image''')
            self.conn.commit()
        except:
            print 'Error at dropDatabase():',str(sys.exc_info())
            print 'failed.'
            raise
        finally:
            c.close()
        print 'done.'

    def compactDatabase(self):
        print 'Compacting Database, this might take a while...'
        try:
            c = self.conn.cursor()
            c.execute('''VACUUM''')
            self.conn.commit()
        except:
            print 'Error at compactDatabase():',str(sys.exc_info())
            raise
        finally:
            c.close()
        print 'done.'
##########################################
## II. Export/Import DB                 ##
##########################################
    def importList(self,listTxt):
        print 'Importing list...',
        print 'Found', len(listTxt),'items',
        try:
            c = self.conn.cursor()

            for item in listTxt:
                c.execute('''INSERT OR IGNORE INTO pixiv_master_member VALUES(?, ?, ?, datetime('now'), '1-1-1', -1, 0)''',
                                  (item.memberId, str(item.memberId), 'N\A'))
                c.execute('''UPDATE pixiv_master_member
                             SET save_folder = ?
                             WHERE member_id = ? ''',
                          (item.path, item.memberId))
            self.conn.commit()
        except:
            print 'Error at importList():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()
        print 'done.'
        return 0

    def exportList(self,filename, includeArtistToken=True):
        print 'Exporting list...',
        try:
            c = self.conn.cursor()
            c.execute('''SELECT member_id, save_folder, name
                         FROM pixiv_master_member
                         WHERE is_deleted = 0
                         ORDER BY member_id''')
            if not filename.endswith(".txt"):
                filename = filename + '.txt'
            #writer = open(filename, 'w')
            writer = codecs.open(filename, 'wb', encoding='utf-8')
            writer.write('###Export date: ' + str(datetime.today()) +'###\r\n')
            for row in c:
                if includeArtistToken:
                    data = unicode(row[2])
                    writer.write("# ")
                    writer.write(data)
                    writer.write("\r\n")
                writer.write(str(row[0]))
                if len(row[1]) > 0:
                    writer.write(' ' + str(row[1]))
                writer.write('\r\n')
            writer.write('###END-OF-FILE###')
        except:
            print 'Error at exportList():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            if writer != None:
                writer.close()
            c.close()
        print 'done.'

    def exportDetailedList(self, filename):
        print 'Exporting detailed list...',
        try:
            c = self.conn.cursor()
            c.execute('''SELECT * FROM pixiv_master_member
                            WHERE is_deleted = 0
                            ORDER BY member_id''')
            filename = filename + '.csv'
            writer = codecs.open(filename, 'wb', encoding='utf-8')
            writer.write('member_id,name,save_folder,created_date,last_update_date,last_image,is_deleted\r\n')
            for row in c:
                for string in row:
                    #try:
                        ### TODO: Unicode write!!
                        #print unicode(string)
                        data = unicode(string)
                        writer.write(data)
                        writer.write(',')
                    #except:
                    #    print 'exception: write'
                    #    writer.write(u',')
                writer.write('\r\n')
            writer.write('###END-OF-FILE###')
            writer.close()
        except:
            print 'Error at exportDetailedList(): ' + str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()
        print 'done.'

##########################################
## III. Print DB                        ##
##########################################
    def printMemberList(self, isDeleted=False):
        print 'Printing member list:'
        try:
            c = self.conn.cursor()
            c.execute('''SELECT * FROM pixiv_master_member
                         WHERE is_deleted = ?
                            ORDER BY member_id''', (int(isDeleted), ))
            print '%10s %25s %25s %20s %20s %10s %s' % ('member_id','name','save_folder','created_date','last_update_date','last_image','is_deleted')
            i = 0
            for row in c:
                #for string in row:
                #    print '\t',
                #    PixivHelper.safePrint(unicode(string), False)
                PixivHelper.safePrint('%10d %#25s %#25s %20s %20s %10d %5s' % (row[0], unicode(row[1]).strip(), row[2], row[3], row[4], row[5], row[6]))
                #print ''
                i = i + 1
                if i == 79:
                    select = raw_input('Continue [y/n]? ')
                    if select == 'n':
                        break
                    else :
                        print 'member_id\tname\tsave_folder\tcreated_date\tlast_update_date\tlast_image'
                        i = 0
        except:
            print 'Error at printList():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()
        print 'done.'

    def printImageList(self):
        print 'Printing image list:'
        try:
            c = self.conn.cursor()
            c.execute(''' SELECT COUNT(*) FROM pixiv_master_image''')
            result = c.fetchall()
            if result[0][0] > 10000:
                print 'Row count is more than 10000 (actual row count:',str(result[0][0]),')'
                print 'It may take a while to retrieve the data.'
                answer = raw_input('Continue [y/n]')
                if answer == 'y':
                    c.execute('''SELECT * FROM pixiv_master_image
                                    ORDER BY member_id''')
                    print ''
                    for row in c:
                        for string in row:
                            print '   ',
                            PixivHelper.safePrint(unicode(string), False)
                        print ''
                else :
                    return
            #Yavos: it seems you forgot something ;P
            else:
                c.execute('''SELECT * FROM pixiv_master_image
                                    ORDER BY member_id''')
                print ''
                for row in c:
                    for string in row:
                        print '   ',
                        PixivHelper.safePrint(unicode(string), False) #would it make more sense to set output to file?
                    print ''
            #Yavos: end of change
        except:
            print 'Error at printImageList():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()
        print 'done.'

##########################################
## IV. CRUD Member Table                ##
##########################################
    def insertNewMember(self):
        try:
            c = self.conn.cursor()
            member_id = 0
            while True:
                temp = raw_input('Member ID: ')
                try:
                    member_id = int(temp)
                except:
                    pass
                if member_id > 0:
                    break

            c.execute('''INSERT OR IGNORE INTO pixiv_master_member VALUES(?, ?, ?, datetime('now'), '1-1-1', -1, 0)''',
                                  (member_id, str(member_id), 'N\A'))
        except:
            print 'Error at insertNewMember():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()

    def selectAllMember(self, isDeleted=False):
        l = list()
        try:
            c = self.conn.cursor()
            c.execute('''SELECT member_id, save_folder FROM pixiv_master_member WHERE is_deleted = ? ORDER BY member_id''', (int(isDeleted), ))
            result = c.fetchall()

            for row in result:
                item = PixivListItem(row[0], row[1])
                l.append(item)

        except:
            print 'Error at selectAllMember():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()

        return l

    def selectMembersByLastDownloadDate(self, difference):
        l = list()
        try:
            c = self.conn.cursor()
            try:
                int_diff = int(difference)
            except ValueError:
                int_diff = 7

            c.execute('''SELECT member_id, save_folder,  (julianday(Date('now')) - julianday(last_update_date)) as diff
                         FROM pixiv_master_member
                         WHERE is_deleted <> 1 AND ( last_image == -1 OR diff > '''+ str(int_diff) +''' ) ORDER BY member_id''')
            result = c.fetchall()
            for row in result:
                item = PixivListItem(row[0], row[1])
                l.append(item)

        except:
            print 'Error at selectMembersByLastDownloadDate():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()

        return l

    def selectMemberByMemberId(self, member_id):
        try:
            c = self.conn.cursor()
            c.execute('''SELECT * FROM pixiv_master_member WHERE member_id = ? ''', (member_id, ))
            return c.fetchone()
        except:
            print 'Error at selectMemberByMemberId():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()

    def selectMemberByMemberId2(self, member_id):
        try:
            c = self.conn.cursor()
            c.execute('''SELECT member_id, save_folder FROM pixiv_master_member WHERE member_id = ? ''', (member_id, ))
            row = c.fetchone()
            if row != None:
                return PixivListItem(row[0], row[1])
            else :
                return PixivListItem(int(member_id),'')
        except:
            print 'Error at selectMemberByMemberId():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()

    def printMembersByLastDownloadDate(self, difference):
        rows = self.selectMembersByLastDownloadDate(difference)

        for row in rows:
            for string in row:
                print '   ',
                PixivHelper.safePrint(unicode(string), False)
            print '\n'

    def updateMemberName(self, memberId, memberName):
        try:
            c = self.conn.cursor()
            c.execute('''UPDATE pixiv_master_member
                            SET name = ?
                            WHERE member_id = ?
                            ''', (memberName, memberId))
            self.conn.commit()
        except:
            print 'Error at updateMemberId():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()

    def updateSaveFolder(self, memberId, saveFolder):
        try:
            c = self.conn.cursor()
            c.execute('''UPDATE pixiv_master_member
                            SET save_folder = ?
                            WHERE member_id = ?
                            ''', (saveFolder, memberId))
            self.conn.commit()
        except:
            print 'Error at updateSaveFolder():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()

    def updateLastDownloadedImage(self, memberId, imageId):
        try:
            c = self.conn.cursor()
            c.execute('''UPDATE pixiv_master_member
                            SET last_image = ?, last_update_date = datetime('now')
                            WHERE member_id = ?''',
                            (imageId, memberId))
            self.conn.commit()
        except:
            print 'Error at updateMemberId():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()

    def deleteMemberByMemberId(self, memberId):
        try:
            c = self.conn.cursor()
            c.execute('''DELETE FROM pixiv_master_member
                            WHERE member_id = ?''',
                            (memberId, ))
            self.conn.commit()
        except:
            print 'Error at deleteMemberByMemberId():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()

    def deleteCascadeMemberByMemberId(self, memberId):
        try:
            c = self.conn.cursor()
            c.execute('''DELETE FROM pixiv_master_image
                            WHERE member_id = ?''',
                            (memberId, ))
            c.execute('''DELETE FROM pixiv_master_member
                            WHERE member_id = ?''',
                            (memberId, ))
            self.conn.commit()
        except:
            print 'Error at deleteCascadeMemberByMemberId():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()

    def setIsDeletedFlagForMemberId(self, memberId):
        try:
            c = self.conn.cursor()
            c.execute('''UPDATE pixiv_master_member
                            SET is_deleted = 1, last_update_date = datetime('now')
                            WHERE member_id = ?''',
                            (memberId,))
            self.conn.commit()
        except:
            print 'Error at setIsDeletedMemberId():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()

##########################################
## V. CRUD Image Table                  ##
##########################################
    def insertImage(self, memberId,ImageId):
        try:
            c = self.conn.cursor()
            memberId = int(memberId)
            ImageId = int(ImageId)
            c.execute('''INSERT OR IGNORE INTO pixiv_master_image VALUES(?, ?, 'N/A' ,'N/A' , datetime('now'), datetime('now') )''',
                              (ImageId, memberId))
            self.conn.commit()
        except:
            print 'Error at insertImage():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()

    def blacklistImage(self, memberId,ImageId):
        try:
            c = self.conn.cursor()
            c.execute('''INSERT OR REPLACE INTO pixiv_master_image VALUES(?, ?, '**BLACKLISTED**' ,'**BLACKLISTED**' , datetime('now'), datetime('now') )''',
                              (ImageId, memberId))
            self.conn.commit()
        except:
            print 'Error at insertImage():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()

    def selectImageByMemberId(self, memberId):
        try:
            c = self.conn.cursor()
            c.execute('''SELECT * FROM pixiv_master_image WHERE member_id = ? ''', (memberId, ))
            return c.fetchall()
        except:
            print 'Error at selectImageByImageId():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()

    def selectImageByMemberIdAndImageId(self, memberId, imageId):
        try:
            c = self.conn.cursor()
            c.execute('''SELECT image_id FROM pixiv_master_image WHERE image_id = ? AND save_name != 'N/A' AND member_id = ?''', (imageId, memberId))
            return c.fetchone()
        except:
            print 'Error at selectImageByImageId():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()

    def selectImageByImageId(self,imageId):
        try:
            c = self.conn.cursor()
            c.execute('''SELECT * FROM pixiv_master_image WHERE image_id = ? AND save_name != 'N/A' ''', (imageId, ))
            return c.fetchone()
        except:
            print 'Error at selectImageByImageId():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()

    def updateImage(self, imageId, title, filename):
        try:
            c = self.conn.cursor()
            c.execute('''UPDATE pixiv_master_image
                        SET title = ?, save_name = ?, last_update_date = datetime('now')
                        WHERE image_id = ?''',
                        (title, filename, imageId))
            self.conn.commit()
        except:
            print 'Error at updateImage():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()

    def deleteImage(self, imageId):
        try:
            c = self.conn.cursor()
            c.execute('''DELETE FROM pixiv_master_image
                        WHERE image_id = ?''',
                        (imageId, ))
            self.conn.commit()
        except:
            print 'Error at deleteImage():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()

    def cleanUp(self):
        import os
        try:
            print "Start clean-up operation."
            print "Selecting all images, this may take some times."
            c = self.conn.cursor()
            c.execute('''SELECT image_id, save_name from pixiv_master_image''')
            print "Checking images."
            for row in c:
                #print row[0],"==>",row[1]
                if not os.path.exists(row[1]):
                    PixivHelper.safePrint("Missing: " + str(row[0]) + " at " + row[1] + "\n")
                    self.deleteImage(row[0])
            self.conn.commit()
        except:
            print 'Error at cleanUp():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()

    def replaceRootPath(self):
        oldPath = raw_input("Old Path to Replace = ")
        PixivHelper.safePrint("Replacing " + oldPath + " to " + self.__config__.rootDirectory)
        cont = raw_input("continue[y/n]?") or 'n'
        if cont != "y":
            print "Aborted"
            return

        try:
            print "Start replace Root Path operation."
            print "Updating images, this may take some times."

            c = self.conn.cursor()
            c.execute('''UPDATE pixiv_master_image
                         SET save_name = replace(save_name, ?, ?)
                         WHERE save_name like ?''', (oldPath, self.__config__.rootDirectory, oldPath +  "%", ))
            print "Updated image:", c.rowcount
            print "Done"

        except:
            print 'Error at replaceRootPath():',str(sys.exc_info())
            print 'failed'
            raise
        finally:
            c.close()

##########################################
## VI. Utilities                        ##
##########################################
    def getInt(self, inputStr):
        inputInt = None
        while True:
            try:
                inputInt = int(inputStr)
            except:
                pass
            if inputInt != None:
                return inputInt


    def menu(self):
        print 'Pixiv DB Manager Console'
        print '1. Show all member'
        print '2. Show all images'
        print '3. Export list (member_id only)'
        print '4. Export list (detailed)'
        print '5. Show member by last downloaded date'
        print '6. Show image by image_id'
        print '7. Show member by member_id'
        print '8. Show image by member_id'
        print '9. Delete member by member_id'
        print '10. Delete image by image_id'
        print '11. Delete member and image (cascade deletion)'
        print '12. Blacklist image by image_id'
        print '13. Show all deleted member'
        print '==============================================='
        print 'c. Clean Up Database'
        print 'p. Compact Database'
        print 'r. Replace Root Path'
        print 'x. Exit'
        selection = raw_input('Select one?')
        return selection

    def main(self):
        try:
            while True:
                selection = self.menu()

                if selection == '1':
                    self.printMemberList()
                elif selection == '2':
                    self.printImageList()
                elif selection == '3':
                    filename = raw_input('Filename? ')
                    includeArtistToken = raw_input('Include Artist Token[y/n]? ')
                    if includeArtistToken.lower() == 'y':
                        includeArtistToken = True
                    else:
                        includeArtistToken = False
                    self.exportList(filename, includeArtistToken)
                elif selection == '4':
                    filename = raw_input('Filename? ')
                    self.exportDetailedList(filename)
                elif selection == '5':
                    date = raw_input('Number of date? ')
                    rows = self.selectMembersByLastDownloadDate(date)
                    if rows != None:
                        for row in rows:
                            for string in row:
                                print '	',
                                PixivHelper.safePrint(unicode(string), False)
                            print '\n'
                    else :
                        print 'Not Found!\n'
                elif selection == '6':
                    image_id = raw_input('image_id? ')
                    row = self.selectImageByImageId(image_id)
                    if row != None:
                        for string in row:
                            print '	',
                            PixivHelper.safePrint(unicode(string), False)
                        print '\n'
                    else :
                        print 'Not Found!\n'
                elif selection == '7':
                    member_id = raw_input('member_id? ')
                    row = self.selectMemberByMemberId(member_id)
                    if row != None:
                        for string in row:
                            print '	',
                            PixivHelper.safePrint(unicode(string), False)
                        print '\n'
                    else :
                        print 'Not Found!\n'
                elif selection == '8':
                    member_id = raw_input('member_id? ')
                    rows = self.selectImageByMemberId(member_id)
                    if rows != None:
                        for row in rows:
                            for string in row:
                                print '	',
                                PixivHelper.safePrint(unicode(string), False)
                            print '\n'
                    else :
                        print 'Not Found!\n'
                elif selection == '9':
                    member_id = raw_input('member_id? ')
                    self.deleteMemberByMemberId(member_id)
                elif selection == '10':
                    image_id = raw_input('image_id? ')
                    self.deleteImage(image_id)
                elif selection == '11':
                    member_id = raw_input('member_id? ')
                    self.deleteCascadeMemberByMemberId(member_id)
                elif selection == '12':
                    member_id = raw_input('member_id? ')
                    image_id = raw_input('image_id? ')
                    self.blacklistImage(member_id, image_id)
                elif selection == '13':
                    self.printMemberList(isDeleted = True)
                elif selection == 'c':
                    self.cleanUp()
                elif selection == 'p':
                    self.compactDatabase()
                elif selection == 'r':
                    self.replaceRootPath()
                elif selection == 'x':
                    break
            print 'end PixivDBManager.'
        except:
            print 'Error: ', sys.exc_info()
            ##raw_input('Press enter to exit.')
            self.main()

if __name__ == '__main__':
    apps = PixivDBManager()
    apps.main()

########NEW FILE########
__FILENAME__ = PixivException
﻿# -*- coding: UTF-8 -*-

class PixivException(Exception):
  ## Error Codes
  NOT_LOGGED_IN      = 100
  USER_ID_NOT_EXISTS = 1001
  USER_ID_SUSPENDED  = 1002
  OTHER_MEMBER_ERROR = 1003
  NO_IMAGES          = 1004

  PARSE_TOKEN_DIFFERENT_IMAGE_STRUCTURE = 1005
  PARSE_TOKEN_PARSE_NO_IMAGES           = 1006
  NO_PAGE_GIVEN                         = 1007

  FILE_NOT_EXISTS_OR_NO_WRITE_PERMISSION = 4002
  FILE_NOT_EXISTS_OR_NO_READ_PERMISSION  = 4001

  OTHER_IMAGE_ERROR    = 2001
  NOT_IN_MYPICK        = 2002
  NO_APPROPRIATE_LEVEL = 2003
  IMAGE_DELETED        = 2004
  R_18_DISABLED        = 2005
  UNKNOWN_IMAGE_ERROR  = 2006

  SERVER_ERROR  = 9005

  errorCode = 0

  def __init__(self, value, errorCode):
    self.value = value
    self.message = value
    self.errorCode = errorCode

  def __str__(self):
    return str(self.errorCode) + " " + repr(self.value)

########NEW FILE########
__FILENAME__ = PixivHelper
﻿# -*- coding: utf-8 -*-
import re
import os
import codecs
from HTMLParser import HTMLParser
import subprocess
import sys
import PixivModel, PixivConstant
import logging, logging.handlers
import datetime

import unicodedata

Logger = None
_config = None


def setConfig(config):
    global _config
    _config = config


def GetLogger(level=logging.DEBUG):
    '''Set up logging'''
    global Logger
    if Logger == None:
        script_path = module_path()
        Logger = logging.getLogger('PixivUtil' + PixivConstant.PIXIVUTIL_VERSION)
        Logger.setLevel(level)
        __logHandler__ = logging.handlers.RotatingFileHandler(script_path + os.sep + PixivConstant.PIXIVUTIL_LOG_FILE,
                                                              maxBytes=PixivConstant.PIXIVUTIL_LOG_SIZE,
                                                              backupCount=PixivConstant.PIXIVUTIL_LOG_COUNT)
        __formatter__ = logging.Formatter(PixivConstant.PIXIVUTIL_LOG_FORMAT)
        __logHandler__.setFormatter(__formatter__)
        Logger.addHandler(__logHandler__)
    return Logger


def setLogLevel(level):
    Logger.info("Setting log level to: " + level)
    GetLogger(level).setLevel(level)


if os.sep == '/':
    __badchars__ = re.compile(r'^\.|\.$|^ | $|^$|\?|:|<|>|\||\*|\"')
else:
    __badchars__ = re.compile(r'^\.|\.$|^ | $|^$|\?|:|<|>|/|\||\*|\"')
__badnames__ = re.compile(r'(aux|com[1-9]|con|lpt[1-9]|prn)(\.|$)')

__h__ = HTMLParser()
__re_manga_index = re.compile('_p(\d+)')


def sanitizeFilename(s, rootDir=None):
    '''Replace reserved character/name with underscore (windows), rootDir is not sanitized.'''
    ## get the absolute rootdir
    if rootDir != None:
        rootDir = os.path.abspath(rootDir)

    ## Unescape '&amp;', '&lt;', and '&gt;'
    s = __h__.unescape(s)

    ## Replace badchars with _
    name = __badchars__.sub('_', s)
    if __badnames__.match(name):
        name = '_' + name

    ## Replace new line with space
    name = name.replace("\r", '')
    name = name.replace("\n", ' ')

    #Yavos: when foldername ends with "." PixivUtil won't find it
    while name.find('.\\') != -1:
        name = name.replace('.\\', '\\')

    name = name.replace('\\', os.sep)

    #Replace tab character with space
    name = name.replace('\t', ' ')

    #Strip leading/trailing space for each directory
    temp = name.split(os.sep)
    temp2 = list()
    for item in temp:
        temp2.append(item.strip())
    name = os.sep.join(temp2)

    if rootDir != None:
        name = rootDir + os.sep + name

    #replace double os.sep
    while name.find(os.sep + os.sep) >= 0:
        name = name.replace(os.sep + os.sep, os.sep)

    ## cut to 255 char
    if len(name) > 255:
        newLen = 250
        name = name[:newLen]

    ## Remove unicode control character
    tempName = ""
    for c in name:
        if unicodedata.category(c) == 'Cc':
            tempName = tempName + '_'
        else:
            tempName = tempName + c
    Logger.debug("Sanitized Filename: " + tempName.strip())

    return tempName.strip()


def makeFilename(nameFormat, imageInfo, artistInfo=None, tagsSeparator=' ', tagsLimit=-1, fileUrl='',
                 appendExtension=True, bookmark=False, searchTags=''):
    '''Build the filename from given info to the given format.'''
    if artistInfo == None:
        artistInfo = imageInfo.artist

    ## Get the image extension
    fileUrl = os.path.basename(fileUrl)
    splittedUrl = fileUrl.split('.')
    imageExtension = splittedUrl[1]
    imageExtension = imageExtension.split('?')[0]

    nameFormat = nameFormat.replace('%artist%', artistInfo.artistName.replace(os.sep, '_'))
    nameFormat = nameFormat.replace('%title%', imageInfo.imageTitle.replace(os.sep, '_'))
    nameFormat = nameFormat.replace('%image_id%', str(imageInfo.imageId))
    nameFormat = nameFormat.replace('%member_id%', str(artistInfo.artistId))
    nameFormat = nameFormat.replace('%member_token%', artistInfo.artistToken)
    nameFormat = nameFormat.replace('%works_date%', imageInfo.worksDate)
    nameFormat = nameFormat.replace('%works_date_only%', imageInfo.worksDate.split(' ')[0])
    nameFormat = nameFormat.replace('%works_res%', imageInfo.worksResolution)
    nameFormat = nameFormat.replace('%works_tools%', imageInfo.worksTools)
    nameFormat = nameFormat.replace('%urlFilename%', splittedUrl[0])
    nameFormat = nameFormat.replace('%searchTags%', searchTags)

    ## date
    nameFormat = nameFormat.replace('%date%', datetime.date.today().strftime('%Y%m%d'))

    ## get the page index & big mode if manga
    page_index = ''
    page_number = ''
    page_big = ''
    if imageInfo.imageMode == 'manga':
        idx = __re_manga_index.findall(fileUrl)
        if len(idx) > 0:
            page_index = idx[0]#[0]
            page_number = str(int(page_index) + 1)
            padding = len(str(imageInfo.imageCount))
            page_number = str(page_number)
            page_number = page_number.zfill(padding)
        if fileUrl.find('_big') > -1 or not fileUrl.find('_m') > -1:
            page_big = 'big'
    nameFormat = nameFormat.replace('%page_big%', page_big)
    nameFormat = nameFormat.replace('%page_index%', page_index)
    nameFormat = nameFormat.replace('%page_number%', page_number)

    if tagsSeparator == '%space%':
        tagsSeparator = ' '
    if tagsLimit != -1:
        tagsLimit = tagsLimit if tagsLimit < len(imageInfo.imageTags) else len(imageInfo.imageTags)
        imageInfo.imageTags = imageInfo.imageTags[0:tagsLimit]
    tags = tagsSeparator.join(imageInfo.imageTags)
    r18Dir = ""
    if "R-18G" in imageInfo.imageTags:
        r18Dir = "R-18G"
    elif "R-18" in imageInfo.imageTags:
        r18Dir = "R-18"
    nameFormat = nameFormat.replace('%R-18%', r18Dir)
    nameFormat = nameFormat.replace('%tags%', tags.replace(os.sep, '_'))
    nameFormat = nameFormat.replace('&#039;', '\'') #Yavos: added html-code for "'" - works only when ' is excluded from __badchars__

    if bookmark: # from member bookmarks
        nameFormat = nameFormat.replace('%bookmark%', 'Bookmarks')
        nameFormat = nameFormat.replace('%original_member_id%', str(imageInfo.originalArtist.artistId))
        nameFormat = nameFormat.replace('%original_member_token%', imageInfo.originalArtist.artistToken)
        nameFormat = nameFormat.replace('%original_artist%', imageInfo.originalArtist.artistName.replace(os.sep, '_'))
    else:
        nameFormat = nameFormat.replace('%bookmark%', '')
        nameFormat = nameFormat.replace('%original_member_id%', str(artistInfo.artistId))
        nameFormat = nameFormat.replace('%original_member_token%', artistInfo.artistToken)
        nameFormat = nameFormat.replace('%original_artist%', artistInfo.artistName.replace(os.sep, '_'))

    if imageInfo.bookmark_count > 0:   # only applicable for search by tags
        nameFormat = nameFormat.replace('%bookmark_count%', str(imageInfo.bookmark_count))
    else:
        nameFormat = nameFormat.replace('%bookmark_count%', '')
    ## clean up double space
    while nameFormat.find('  ') > -1:
        nameFormat = nameFormat.replace('  ', ' ')

    if appendExtension:
        nameFormat = nameFormat.strip() + '.' + imageExtension

    return nameFormat.strip()


def safePrint(msg, newline=True):
    """Print empty string if UnicodeError raised."""
    for msgToken in msg.split(' '):
        try:
            print msgToken,
        except UnicodeError:
            print ('?' * len(msgToken)),
    if newline:
        print ''


def setConsoleTitle(title):
    if os.name == 'nt':
        subprocess.call('title' + ' ' + title, shell=True)
    else:
        sys.stdout.write("\x1b]2;" + title + "\x07")


def clearScreen():
    if os.name == 'nt':
        subprocess.call('cls', shell=True)
    else:
        subprocess.call('clear', shell=True)


def startIrfanView(dfilename, irfanViewPath, start_irfan_slide=False, start_irfan_view=False):
    print 'starting IrfanView...'
    if os.path.exists(dfilename):
        ivpath = irfanViewPath + os.sep + 'i_view32.exe' #get first part from config.ini
        ivpath = ivpath.replace('\\\\', '\\')
        ivpath = ivpath.replace('\\', os.sep)
        info = None
        if start_irfan_slide:
            info = subprocess.STARTUPINFO()
            info.dwFlags = 1
            info.wShowWindow = 6 #start minimized in background (6)
            ivcommand = ivpath + ' /slideshow=' + dfilename
            Logger.info(ivcommand)
            subprocess.Popen(ivcommand)
        elif start_irfan_view:
            ivcommand = ivpath + ' /filelist=' + dfilename
            Logger.info(ivcommand)
            subprocess.Popen(ivcommand, startupinfo=info)
    else:
        print 'could not load', dfilename


def OpenTextFile(filename, mode='r', encoding='utf-8'):
    ''' taken from: http://www.velocityreviews.com/forums/t328920-remove-bom-from-string-read-from-utf-8-file.html'''
    hasBOM = False
    if os.path.isfile(filename):
        f = open(filename, 'rb')
        header = f.read(4)
        f.close()

        # Don't change this to a map, because it is ordered
        encodings = [( codecs.BOM_UTF32, 'utf-32' ),
                     ( codecs.BOM_UTF16, 'utf-16' ),
                     ( codecs.BOM_UTF8, 'utf-8' )]

        for h, e in encodings:
            if header.startswith(h):
                encoding = e
                hasBOM = True
                break

    f = codecs.open(filename, mode, encoding)
    # Eat the byte order mark
    if hasBOM:
        f.read(1)
    return f


def toUnicode(obj, encoding='utf-8'):
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding)
    return obj


def uni_input(message=''):
    result = raw_input(message)
    return toUnicode(result, encoding=sys.stdin.encoding)


def CreateAvatarFilename(filenameFormat, tagsSeparator, tagsLimit, artistPage, targetDir):
    filename = ''
    if filenameFormat.find(os.sep) == -1:
        filenameFormat = os.sep + filenameFormat
    filenameFormat = filenameFormat.split(os.sep)[0]
    image = PixivModel.PixivImage(parent=artistPage)
    filename = makeFilename(filenameFormat, image, tagsSeparator=tagsSeparator, tagsLimit=tagsLimit,
                            fileUrl=artistPage.artistAvatar, appendExtension=False)
    filename = sanitizeFilename(filename + os.sep + 'folder.jpg', targetDir)
    return filename


def we_are_frozen():
    """Returns whether we are frozen via py2exe.
        This will affect how we find out where we are located.
        Get actual script directory
        http://www.py2exe.org/index.cgi/WhereAmI"""

    return hasattr(sys, "frozen")


def module_path():
    """ This will get us the program's directory,
  even if we are frozen using py2exe"""

    if we_are_frozen():
        return os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding()))

    return os.path.dirname(unicode(__file__, sys.getfilesystemencoding()))


def speedInStr(totalSize, totalTime):
    speed = totalSize / totalTime
    if speed < 1024:
        return "{0:.0f} B/s".format(speed)
    speed = speed / 1024
    if speed < 1024:
        return "{0:.2f} KiB/s".format(speed)
    speed = speed / 1024
    if speed < 1024:
        return "{0:.2f} MiB/s".format(speed)
    speed = speed / 1024
    return "{0:.2f} GiB/s".format(speed)


def dumpHtml(filename, html):
    isDumpEnabled = True
    if _config != None:
        isDumpEnabled = _config.enableDump
        if _config.enableDump:
            if len(_config.skipDumpFilter) > 0:
                matchResult = re.findall(_config.skipDumpFilter, filename)
                if matchResult != None and len(matchResult) > 0:
                    isDumpEnabled = False

    if isDumpEnabled:
        try:
            dump = file(filename, 'wb')
            dump.write(html)
            dump.close()
        except:
            pass
    else:
        print "No Dump"


def printAndLog(level, msg):
    safePrint(msg)
    if level == 'info':
        GetLogger().info(msg)
    elif level == 'error':
        GetLogger().error(msg)


def HaveStrings(page, strings):
    for string in strings:
       pattern = re.compile(string)
       test_2 = pattern.findall(str(page))
       if len(test_2) > 0 :
           if len(test_2[-1]) > 0 :
               return True
    return False
########NEW FILE########
__FILENAME__ = PixivModel
﻿# -*- coding: UTF-8 -*-
from BeautifulSoup import BeautifulSoup, Tag
import os
import re
import sys
import codecs
import collections
import PixivHelper
from PixivException import PixivException
import datetime
import json

class PixivArtist:
    '''Class for parsing member page.'''
    artistId     = 0
    artistName   = ""
    artistAvatar = ""
    artistToken  = ""
    imageList    = []
    isLastPage = None
    haveImages = None

    def __init__(self, mid=0, page=None, fromImage=False):
        if page != None:
            if self.IsNotLoggedIn(page):
                raise PixivException('Not Logged In!', errorCode=PixivException.NOT_LOGGED_IN)

            if self.IsUserNotExist(page):
                raise PixivException('User ID not exist/deleted!', errorCode=PixivException.USER_ID_NOT_EXISTS)

            if self.IsUserSuspended(page):
                raise PixivException('User Account is Suspended!', errorCode=PixivException.USER_ID_SUSPENDED)

            ## detect if there is any other error
            errorMessage = self.IsErrorExist(page)
            if errorMessage != None:
                raise PixivException('Member Error: ' + errorMessage, errorCode=PixivException.OTHER_MEMBER_ERROR)

            ## detect if there is server error
            errorMessage = self.IsServerErrorExist(page)
            if errorMessage != None:
                raise PixivException('Member Error: ' + errorMessage, errorCode=PixivException.SERVER_ERROR)

            ## detect if image count != 0
            if not fromImage:
                self.ParseImages(page)

            ## parse artist info
            self.ParseInfo(page, fromImage)

            ## check if no images
            if len(self.imageList) > 0:
                self.haveImages = True
            else:
                self.haveImages = False

            ## check if the last page
            self.CheckLastPage(page)


    def ParseInfo(self, page, fromImage=False):
        avatarBox = page.find(attrs={'class':'_unit profile-unit'})
        temp = str(avatarBox.find('a')['href'])
        self.artistId = int(re.search('id=(\d+)', temp).group(1))

        try:
            self.artistName = unicode(page.find('h1', attrs={'class':'user'}).string.extract())
        except:
            self.artistName = unicode(page.findAll(attrs={"class":"avatar_m"})[0]["title"])
        self.artistAvatar = str(page.find('img', attrs={'class':'user-image'})['src'])
        self.artistToken = self.ParseToken(page, fromImage)


    def ParseToken(self, page, fromImage=False):
        if self.artistAvatar.endswith("no_profile.png"):
            if fromImage:
                temp = page.findAll(attrs={'class':'works_display'})
                token = str(temp[0].find('img')['src'])
                return token.split('/')[-2]
            else :
                artistToken = None
                try:
                    temp = page.find(attrs={'class':'display_works linkStyleWorks'}).ul
                    if temp != None:
                        tokens = temp.findAll('img', attrs={'class':'_thumbnail'})
                        for token in tokens:
                            try:
                                tempImage = token['data-src']
                            except:
                                tempImage = token['src']
                            folders = tempImage.split('/')
                            ## skip http://i2.pixiv.net/img-inf/img/2013/04/07/03/08/21/34846113_s.jpg
                            if folders[3] == 'img-inf':
                                continue
                            artistToken = folders[-2]
                            if artistToken != 'common':
                                return artistToken

                        ## all thumb images are using img-inf
                        ## take the first image and check the medium page
                        if artistToken == None or artistToken != 'common':
                            PixivHelper.GetLogger().info("Unable to parse Artist Token from image list, try to parse from the first image")
                            import PixivBrowserFactory, PixivConstant
                            firstImageLink = temp.find('a', attrs={'class':'work'})['href']
                            if firstImageLink.find("http") != 0:
                                firstImageLink = PixivConstant.PIXIV_URL + firstImageLink
                            PixivHelper.GetLogger().info("Using: " + firstImageLink + " for parsing artist token")
                            imagePage = PixivBrowserFactory.getBrowser().open(firstImageLink)
                            imageResult = BeautifulSoup(imagePage.read())
                            token = str(imageResult.find(attrs={'class':'works_display'}).find('img')['src'])
                            return token.split('/')[-2]

                        raise PixivException('Cannot parse artist token, possibly different image structure.', errorCode = PixivException.PARSE_TOKEN_DIFFERENT_IMAGE_STRUCTURE)
                except TypeError:
                    raise PixivException('Cannot parse artist token, possibly no images.', errorCode = PixivException.PARSE_TOKEN_NO_IMAGES)
        else :
            temp = self.artistAvatar.split('/')
            return temp[-2]

    def ParseImages(self, page):
        del self.imageList[:]
        temp = page.find(attrs={'class':'display_works linkStyleWorks'}).ul
        temp = temp.findAll('a')
        if temp == None or len(temp) == 0:
            raise PixivException('No image found!', errorCode=PixivException.NO_IMAGES)
        for item in temp:
            href = re.search('member_illust.php.*illust_id=(\d+)', str(item))
            if href != None:
                href = href.group(1)
                self.imageList.append(int(href))

    def IsNotLoggedIn(self, page):
        check = page.findAll('a', attrs={'class':'signup_button'})
        if check != None and len(check) > 0:
            return True
        return False

    def IsUserNotExist(self, page):
        errorMessages = ['該当ユーザーは既に退会したか、存在しないユーザーIDです',
                         'The user has either left pixiv, or the user ID does not exist.',
                         '該当作品は削除されたか、存在しない作品IDです。',
                         'The following work is either deleted, or the ID does not exist.']
        return PixivHelper.HaveStrings(page, errorMessages)

    def IsUserSuspended(self, page):
        errorMessages = ['該当ユーザーのアカウントは停止されています。',
                         'This user account has been suspended.']
        return PixivHelper.HaveStrings(page, errorMessages)

    def IsErrorExist(self, page):
        check = page.findAll('span', attrs={'class':'error'})
        if len(check) > 0:
            check2 = check[0].findAll('strong')
            if len(check2) > 0:
                return check2[0].renderContents()
            return check[0].renderContents()
        return None

    def IsServerErrorExist(self, page):
        check = page.findAll('div', attrs={'class':'errorArea'})
        if len(check) > 0:
            check2 = check[0].findAll('h2')
            if len(check2) > 0:
                return check2[0].renderContents()
            return check[0].renderContents()
        return None

    def CheckLastPage(self, page):
        check = page.findAll('a', attrs={'class':'_button', 'rel':'next'})
        if len(check) > 0:
            self.isLastPage = False
        else:
            self.isLastPage = True
        return self.isLastPage

    def PrintInfo(self):
        PixivHelper.safePrint('Artist Info')
        PixivHelper.safePrint('id    : ' + str(self.artistId))
        PixivHelper.safePrint('name  : ' + self.artistName)
        PixivHelper.safePrint('avatar: ' + self.artistAvatar)
        PixivHelper.safePrint('token : ' + self.artistToken)
        PixivHelper.safePrint('urls  : ')
        for item in self.imageList:
            PixivHelper.safePrint('\t' + str(item))

class PixivImage:
    '''Class for parsing image page, including manga page and big image.'''
    artist     = None
    originalArtist  = None
    imageId    = 0
    imageTitle = ""
    imageCaption = ""
    imageTags  = []
    imageMode  = ""
    imageUrls  = []
    worksDate  = unicode("")
    worksResolution = unicode("")
    worksTools = unicode("")
    jd_rtv = 0
    jd_rtc = 0
    jd_rtt = 0
    imageCount = 0
    fromBookmark = False
    worksDateDateTime = datetime.datetime.fromordinal(1)
    bookmark_count = -1

    def __init__(self, iid=0, page=None, parent=None, fromBookmark=False, bookmark_count=-1):
        self.artist = parent
        self.fromBookmark = fromBookmark
        self.bookmark_count = bookmark_count
        self.imageUrls = []

        if page != None:
            ## check is error page
            if self.IsNotLoggedIn(page):
                raise PixivException('Not Logged In!', errorCode=PixivException.NOT_LOGGED_IN)
            if self.IsNeedPermission(page):
                raise PixivException('Not in MyPick List, Need Permission!', errorCode=PixivException.NOT_IN_MYPICK)
            if self.IsNeedAppropriateLevel(page):
                raise PixivException('Public works can not be viewed by the appropriate level!', errorCode=PixivException.NO_APPROPRIATE_LEVEL)
            if self.IsDeleted(page):
                raise PixivException('Image not found/already deleted!', errorCode=PixivException.IMAGE_DELETED)
            if self.IsGuroDisabled(page):
                raise PixivException('Image is disabled for under 18, check your setting page (R-18/R-18G)!', errorCode=PixivException.R_18_DISABLED)

            # check if there is any other error
            if self.IsErrorPage(page):
                raise PixivException('An error occurred!', errorCode=PixivException.OTHER_IMAGE_ERROR)

            ## detect if there is any other error
            errorMessage = self.IsErrorExist(page)
            if errorMessage != None:
                raise PixivException('Image Error: ' + errorMessage, errorCode=PixivException.UNKNOWN_IMAGE_ERROR)

            ## detect if there is server error
            errorMessage = self.IsServerErrorExist(page)
            if errorMessage != None:
                raise PixivException('Image Error: ' + errorMessage, errorCode=PixivException.SERVER_ERROR)

            ## parse artist information
            if self.artist == None:
                self.artist = PixivArtist(page=page, fromImage=True)

            if fromBookmark and self.originalArtist == None:
                self.originalArtist = PixivArtist(page=page, fromImage=True)

            ## parse image information
            self.ParseInfo(page)
            self.ParseTags(page)
            self.ParseWorksData(page)

    def IsNotLoggedIn(self, page):
        check = page.findAll('a', attrs={'class':'signup_button'})
        if check != None and len(check) > 0:
            return True
        return False

    def IsErrorPage(self, page):
        check = page.findAll('span', attrs={'class':'error'})
        if len(check) > 0:
            check2 = check[0].findAll('strong')
            if len(check2) > 0:
                return check2[0].renderContents()
            return check[0].renderContents()
        return None

    def IsNeedAppropriateLevel(self, page):
        errorMessages = ['該当作品の公開レベルにより閲覧できません。']
        return PixivHelper.HaveStrings(page, errorMessages)

    def IsNeedPermission(self, page):
        errorMessages = ['この作品は.+さんのマイピクにのみ公開されています|この作品は、.+さんのマイピクにのみ公開されています',
                         'This work is viewable only for users who are in .+\'s My pixiv list']
        return PixivHelper.HaveStrings(page, errorMessages)

    def IsDeleted(self, page):
        errorMessages = ['該当イラストは削除されたか、存在しないイラストIDです。|該当作品は削除されたか、存在しない作品IDです。',
                         'The following work is either deleted, or the ID does not exist.']
        return PixivHelper.HaveStrings(page, errorMessages)

    def IsGuroDisabled(self, page):
        errorMessages = ['表示されるページには、18歳未満の方には不適切な表現内容が含まれています。',
                         'The page you are trying to access contains content that may be unsuitable for minors']
        return PixivHelper.HaveStrings(page, errorMessages)

    def IsErrorExist(self, page):
        check = page.findAll('span', attrs={'class':'error'})
        if len(check) > 0:
            check2 = check[0].findAll('strong')
            if len(check2) > 0:
                return check2[0].renderContents()
            return check[0].renderContents()
        return None

    def IsServerErrorExist(self, page):
        check = page.findAll('div', attrs={'class':'errorArea'})
        if len(check) > 0:
            check2 = check[0].findAll('h2')
            if len(check2) > 0:
                return check2[0].renderContents()
            return check[0].renderContents()
        return None

    def ParseInfo(self, page):
        temp = str(page.find(attrs={'class':'works_display'}).find('a')['href'])
        self.imageId = int(re.search('illust_id=(\d+)',temp).group(1))
        self.imageMode = re.search('mode=(big|manga)',temp).group(1)

        # remove premium-introduction-modal so we can get caption from work-info
        # somehow selecting section doesn't works
        premium_introduction_modal = page.findAll('div', attrs={'id':'premium-introduction-modal'})
        for modal in premium_introduction_modal:
            modal.extract()

        meta_data = page.findAll('meta')
        for meta in meta_data:
            if meta.has_key("property"):
                if "og:title" == meta["property"]:
                    self.imageTitle = meta["content"].split("|")[0].strip()
                if "og:description" in meta["property"]:
                    self.imageCaption = meta["content"]

        self.jd_rtv = int(page.find(attrs={'class':'view-count'}).string)
        self.jd_rtc = int(page.find(attrs={'class':'rated-count'}).string)
        self.jd_rtt = int(page.find(attrs={'class':'score-count'}).string)

    def ParseWorksData(self, page):
        temp = page.find(attrs={'class':'meta'}).findAll('li')
        #07/22/2011 03:09|512×600|RETAS STUDIO
        #07/26/2011 00:30|Manga 39P|ComicStudio 鉛筆 つけペン
        #1/05/2011 07:09|723×1023|Photoshop SAI  [ R-18 ]
        #2013年3月16日 06:44 | 800×1130 | Photoshop ComicStudio | R-18
        #2013年12月14日 19:00 855×1133 PhotoshopSAI
        self.worksDate = PixivHelper.toUnicode(temp[0].string, encoding=sys.stdin.encoding).replace(u'/', u'-')
        if self.worksDate.find('-') > -1:
            try:
                self.worksDateDateTime = datetime.datetime.strptime(self.worksDate, u'%m-%d-%Y %H:%M')
            except ValueError as ve:
                PixivHelper.GetLogger().exception('Error when parsing datetime: {0} for imageId {1}'.format(self.worksDate, self.imageId))
                self.worksDateDateTime = datetime.datetime.strptime(self.worksDate.split(" ")[0], u'%Y-%m-%d')
        else:
            tempDate = self.worksDate.replace(u'年', '-').replace(u'月','-').replace(u'日', '')
            self.worksDateDateTime = datetime.datetime.strptime(tempDate, '%Y-%m-%d %H:%M')

        self.worksResolution = unicode(temp[1].string).replace(u'×',u'x')
        toolsTemp = page.find(attrs={'class':'meta'}).find(attrs={'class':'tools'})
        if toolsTemp!= None and len(toolsTemp) > 0:
            tools = toolsTemp.findAll('li')
            for tool in tools:
                self.worksTools = self.worksTools + ' ' + unicode(tool.string)
            self.worksTools = self.worksTools.strip()

    def ParseTags(self, page):
        del self.imageTags[:]
        temp = page.find(attrs={'class':'tags'})
        if temp != None and len(temp) > 0:
            temp2 = temp.findAll('a')
            if temp2 != None and len(temp2) > 0:
                for tag in temp2:
                    if not tag.string == None and tag['class'] == 'text':
                        self.imageTags.append(unicode(tag.string))

    def PrintInfo(self):
        PixivHelper.safePrint( 'Image Info')
        PixivHelper.safePrint( 'img id: ' + str(self.imageId))
        PixivHelper.safePrint( 'title : ' + self.imageTitle)
        PixivHelper.safePrint( 'caption : ' + self.imageCaption)
        PixivHelper.safePrint( 'mode  : ' + self.imageMode)
        PixivHelper.safePrint( 'tags  :')
        PixivHelper.safePrint( ', '.join(self.imageTags))
        PixivHelper.safePrint( 'views : ' + str(self.jd_rtv))
        PixivHelper.safePrint( 'rating: ' + str(self.jd_rtc))
        PixivHelper.safePrint( 'total : ' + str(self.jd_rtt))
        PixivHelper.safePrint( 'Date : ' + self.worksDate)
        PixivHelper.safePrint( 'Resolution : ' + self.worksResolution)
        PixivHelper.safePrint( 'Tools : ' + self.worksTools)
        return ""

    def ParseImages(self, page, mode=None):
        if page == None:
            raise PixivException('No page given', errorCode = PixivException.NO_PAGE_GIVEN)
        if mode == None:
            mode = self.imageMode

        del self.imageUrls[:]
        if mode == 'big':
            self.imageUrls.append(self.ParseBigImages(page))
        elif mode == 'manga':
            self.imageUrls = self.ParseMangaImages(page)
        if len(self.imageUrls) == 0:
            raise PixivException('No images found for: '+ str(self.imageId), errorCode = PixivException.NO_IMAGES)
        return self.imageUrls

    def ParseBigImages(self, page):
        temp = page.find('img')['src']
        imageCount = 1
        return str(temp)

    def ParseMangaImages(self, page):
        urls = []
        scripts = page.findAll('script')
        string = ''
        for script in scripts:
            string += str(script)
        # normal: http://img04.pixiv.net/img/xxxx/12345_p0.jpg
        # mypick: http://img04.pixiv.net/img/xxxx/12344_5baa86aaad_p0.jpg
        pattern = re.compile('http.*?(?<!mobile)\d+[_0-9a-z_]*_p\d+\..{3}')
        pattern2 = re.compile('http.*?(?<!mobile)(\d+[_0-9a-z_]*_p\d+)\..{3}')
        m = pattern.findall(string)

        # filter mobile thumb: http://i1.pixiv.net/img01/img/sokusekimaou/mobile/20592252_128x128_p8.jpg
        m2 = []
        for img in m:
            if img.find('/mobile/') == -1:
                m2.append(img)
        m = m2

        self.imageCount = len(m)
        for img in m:
            temp = str(img)
            m2 = pattern2.findall(temp)         ## 1234_p0
            temp = temp.replace(m2[0], m2[0].replace('_p', '_big_p'))
            urls.append(temp)
            temp = str(img)
            urls.append(temp)
        return urls

    def WriteInfo(self, filename):
        info = None
        try:
            info = codecs.open(filename, 'wb', encoding='utf-8')
        except IOError:
            info = codecs.open(str(self.imageId) + ".txt", 'wb', encoding='utf-8')
            PixivHelper.GetLogger().exception("Error when saving image info: " + filename + ", file is saved to: " + str(self.imageId) + ".txt")

        info.write("ArtistID   = " + str(self.artist.artistId) + "\r\n")
        info.write("ArtistName = " + self.artist.artistName + "\r\n")
        info.write("ImageID    = " + str(self.imageId) + "\r\n")
        info.write("Title      = " + self.imageTitle + "\r\n")
        info.write("Caption    = " + self.imageCaption + "\r\n")
        info.write("Tags       = " + ", ".join(self.imageTags) + "\r\n")
        info.write("Image Mode = " + self.imageMode + "\r\n")
        info.write("Pages      = " + str(self.imageCount) + "\r\n")
        info.write("Date       = " + self.worksDate + "\r\n")
        info.write("Resolution = " + self.worksResolution + "\r\n")
        info.write("Tools      = " + self.worksTools + "\r\n")
        info.write("Link       = http://www.pixiv.net/member_illust.php?mode=medium&illust_id=" + str(self.imageId) + "\r\n")
        info.close()

class PixivListItem:
    '''Class for item in list.txt'''
    memberId = ""
    path = ""

    def __init__(self, memberId, path):
        self.memberId = int(memberId)
        self.path = path.strip()
        if self.path == "N\A":
            self.path = ""

    @staticmethod
    def parseList(filename, rootDir=None):
        '''read list.txt and return the list of PixivListItem'''
        l = list()

        if not os.path.exists(filename) :
            raise PixivException("File doesn't exists or no permission to read: " + filename, errorCode=PixivException.FILE_NOT_EXISTS_OR_NO_WRITE_PERMISSION)

        reader = PixivHelper.OpenTextFile(filename)
        lineNo = 1
        try:
            for line in reader:
                originalLine = line
                ##PixivHelper.safePrint("Processing: " + line)
                if line.startswith('#') or len(line) < 1:
                    continue
                if len(line.strip()) == 0:
                    continue
                line = PixivHelper.toUnicode(line)
                line = line.strip()
                items = line.split(" ", 1)

                member_id = int(items[0])
                path = ""
                if len(items) > 1:
                    path = items[1].strip()

                    path = path.replace('\"', '')
                    if rootDir != None:
                        path = path.replace('%root%', rootDir)
                    else:
                        path = path.replace('%root%', '')

                    path = os.path.abspath(path)
                    # have drive letter
                    if re.match(r'[a-zA-Z]:', path):
                        dirpath = path.split(os.sep, 1)
                        dirpath[1] = PixivHelper.sanitizeFilename(dirpath[1], None)
                        path = os.sep.join(dirpath)
                    else:
                        path = PixivHelper.sanitizeFilename(path, rootDir)

                    path = path.replace('\\\\', '\\')
                    path = path.replace('\\', os.sep)

                listItem = PixivListItem(member_id, path)
                l.append(listItem)
                lineNo = lineNo + 1
                originalLine = ""
        except UnicodeDecodeError:
            PixivHelper.GetLogger().exception("PixivListItem.parseList(): Invalid value when parsing list")
            PixivHelper.printAndLog('error', 'Invalid value: {0} at line {1}, try to save the list.txt in UTF-8.'.format(originalLine, lineNo))
        except:
            PixivHelper.GetLogger().exception("PixivListItem.parseList(): Invalid value when parsing list")
            PixivHelper.printAndLog('error', 'Invalid value: {0} at line {1}'.format(originalLine, lineNo))

        reader.close()
        return l

class PixivNewIllustBookmark:
    '''Class for parsing New Illust from Bookmarks'''
    imageList  = None
    isLastPage = None
    haveImages = None

    def __init__(self, page):
        self.__ParseNewIllustBookmark(page)
        self.__CheckLastPage(page)
        if len(self.imageList) > 0:
            self.haveImages = True
        else:
            self.haveImages = False

    def __ParseNewIllustBookmark(self,page):
        self.imageList = list()
        try:
            result = page.find(attrs={'class':'image-items autopagerize_page_element'}).findAll('a')
            for r in result:
                href = re.search('member_illust.php?.*illust_id=(\d+)', r['href'])
                if href != None:
                    href = href.group(1)
                    self.imageList.append(int(href))
        except:
            pass
        return self.imageList

    def __CheckLastPage(self, page):
        check = page.findAll('a', attrs={'class':'_button', 'rel':'next'})
        if len(check) > 0:
            self.isLastPage = False
        else:
            self.isLastPage = True
        return self.isLastPage

class PixivBookmark:
    '''Class for parsing Bookmarks'''

    @staticmethod
    def parseBookmark(page):
        '''Parse favorite artist page'''
        import PixivDBManager
        l = list()
        db = PixivDBManager.PixivDBManager()
        __re_member = re.compile(r'member\.php\?id=(\d*)')
        try:
            result = page.find(attrs={'class':'members'}).findAll('a')

            ##filter duplicated member_id
            d = collections.OrderedDict()
            for r in result:
                member_id = __re_member.findall(r['href'])
                if len(member_id) > 0:
                    d[member_id[0]] = member_id[0]
            result2 = list(d.keys())

            for r in result2:
                item = db.selectMemberByMemberId2(r)
                l.append(item)
        except:
            pass
        return l

    @staticmethod
    def parseImageBookmark(page):
        imageList = list()
        temp = page.find(attrs={'class':'display_works linkStyleWorks'}).ul
        temp = temp.findAll('a')
        if temp == None or len(temp) == 0:
            return imageList
        for item in temp:
            href = re.search('member_illust.php?.*illust_id=(\d+)', str(item))
            if href != None:
                href = href.group(1)
                if not int(href) in imageList:
                    imageList.append(int(href))
        return imageList

    @staticmethod
    def exportList(l, filename):
        from datetime import datetime
        if not filename.endswith('.txt'):
            filename = filename + '.txt'
        writer = codecs.open(filename, 'wb', encoding='utf-8')
        writer.write(u'###Export date: ' + str(datetime.today()) +'###\n')
        for item in l:
            data = unicode(str(item.memberId))
            if len(item.path) > 0:
                data = data + unicode(' ' + item.path)
            writer.write(data)
            writer.write(u'\r\n')
        writer.write('###END-OF-FILE###')
        writer.close()

import collections
PixivTagsItem = collections.namedtuple('PixivTagsItem', ['imageId', 'bookmarkCount', 'imageResponse'])

class PixivTags:
    '''Class for parsing tags search page'''
    #imageList = None
    itemList = None
    haveImage = None
    isLastPage = None

    def parseTags(self, page):
        '''parse tags search page and return the image list with bookmarkCound and imageResponse'''
        self.itemList = list()

        __re_illust = re.compile(r'member_illust.*illust_id=(\d*)')

        ## get showcase
        ignore = list()
        showcases = page.findAll('section', attrs={'class': 'showcase'})
        for showcase in showcases:
            lis = showcase.findAll('li', attrs={'class':'image'})
            for li in lis:
                if str(li).find('member_illust.php?') > -1:
                    image_id = __re_illust.findall(li.find('a')['href'])[0]
                    ignore.append(image_id)

        ## new parse for bookmark items
        items = page.findAll('li', attrs={'class':'image-item'})
        for item in items:
            if str(item).find('member_illust.php?') > -1:
                image_id = __re_illust.findall(item.find('a')['href'])[0]
                if image_id in ignore:
                    continue
                bookmarkCount = -1
                imageResponse = -1
                countList = item.find('ul', attrs={'class':'count-list'})
                if countList != None:
                    countList = countList.findAll('li')
                    if len(countList) > 0 :
                        for count in countList:
                            temp = count.find('a')
                            if 'bookmark-count' in temp['class']:
                                bookmarkCount = temp.contents[1]
                            elif 'image-response-count' in temp['class'] :
                                imageResponse = temp.contents[1]
                self.itemList.append(PixivTagsItem(int(image_id), int(bookmarkCount), int(imageResponse)))
        self.checkLastPage(page)
        return self.itemList

    def parseMemberTags(self, page):
        '''parse member tags search page and return the image list'''
        self.itemList = list()

        __re_illust = re.compile(r'member_illust.*illust_id=(\d*)')
        linkList = page.findAll('a')
        for link in linkList:
            if link.has_key('href') :
                result = __re_illust.findall(link['href'])
                if len(result) > 0 :
                    image_id = int(result[0])
                    self.itemList.append(PixivTagsItem(int(image_id), 0, 0))
        self.checkLastPage(page, fromMember=True)
        return self.itemList

    def checkLastPage(self, page, fromMember=False):
        # Check if have image
        if len(self.itemList) > 0:
            self.haveImage = True
        else:
            self.haveImage = False

        # check if the last page
        check = page.findAll('i', attrs={'class':'_icon sprites-next-linked'})
        if len(check) > 0:
            self.isLastPage = False
        else:
            self.isLastPage = True

        if fromMember:
                # check if the last page for member tags
            if self.isLastPage:
                check = page.findAll(name='a', attrs={'class':'button', 'rel':'next'})
                if len(check) > 0:
                    self.isLastPage = False

    @staticmethod
    def parseTagsList(filename):
        '''read tags.txt and return the tags list'''
        l = list()

        if not os.path.exists(filename) :
            raise PixivException("File doesn't exists or no permission to read: " + filename, FILE_NOT_EXISTS_OR_NO_READ_PERMISSION)

        reader = PixivHelper.OpenTextFile(filename)
        for line in reader:
            if line.startswith('#') or len(line) < 1:
                continue
            line = line.strip()
            if len(line) > 0 :
                l.append(PixivHelper.toUnicode(line))
        reader.close()
        return l

class PixivGroup:
    short_pattern = re.compile("https?://www.pixiv.net/member_illust.php\?mode=(.*)&illust_id=(\d+)")
    imageList = None
    externalImageList = None
    maxId = 0

    def __init__(self, jsonResponse):
        data = json.loads(jsonResponse.read())
        self.maxId = data["max_id"]
        self.imageList = list()
        self.externalImageList = list()
        for imageData in data["imageArticles"]:
            if imageData["detail"].has_key("id"):
                imageId = imageData["detail"]["id"]
                self.imageList.append(imageId)
            elif imageData["detail"].has_key("fullscale_url"):
                fullscale_url = imageData["detail"]["fullscale_url"]
                member_id = PixivArtist()
                member_id.artistId     = imageData["user_id"]
                member_id.artistName   = imageData["user_name"]
                member_id.artistAvatar = self.parseAvatar(imageData["img"])
                member_id.artistToken  = self.parseToken(imageData["img"])
                image_data = PixivImage()
                image_data.artist = member_id
                image_data.originalArtist  = member_id
                image_data.imageId    = 0
                image_data.imageTitle = self.shortenPixivUrlInBody(imageData["body"])
                image_data.imageCaption = self.shortenPixivUrlInBody(imageData["body"])
                image_data.imageTags  = []
                image_data.imageMode  = ""
                image_data.imageUrls  = [fullscale_url]
                image_data.worksDate  = imageData["create_time"]
                image_data.worksResolution = unicode("")
                image_data.worksTools = unicode("")
                image_data.jd_rtv = 0
                image_data.jd_rtc = 0
                image_data.jd_rtt = 0
                image_data.imageCount = 0
                image_data.fromBookmark = False
                image_data.worksDateDateTime = datetime.datetime.strptime(image_data.worksDate, '%Y-%m-%d %H:%M:%S')

                self.externalImageList.append(image_data)

    def parseAvatar(self, url):
        return url.replace("_s", "")

    def parseToken(self, url):
        token = url.split('/')[-2]
        if token != "Common":
            return token
        return None

    def shortenPixivUrlInBody(self, string):
        shortened = ""
        result = self.short_pattern.findall(string)
        if result != None and len(result) > 0:
            if result[0][0] == 'medium':
                shortened = "Illust={0}".format(result[0][1])
            else:
                shortened = "Manga={0}".format(result[0][1])
        string = self.short_pattern.sub("", string).strip()
        string = string + " " + shortened
        return string


########NEW FILE########
__FILENAME__ = PixivUtil2
﻿#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import os
import re
import traceback
import gc
import time
import datetime
import urllib2
import urllib
import getpass
import httplib
import cookielib
import codecs

from BeautifulSoup import BeautifulSoup

import PixivConstant
import PixivConfig
import PixivDBManager
import PixivHelper
from PixivModel import PixivArtist, PixivImage, PixivListItem, PixivBookmark, PixivTags
from PixivModel import PixivNewIllustBookmark, PixivGroup
from PixivException import PixivException
import PixivBrowserFactory

from optparse import OptionParser

script_path = PixivHelper.module_path()

Yavos = True
np_is_valid = False
np = 0
op = ''

gc.enable()
##gc.set_debug(gc.DEBUG_LEAK)

__config__ = PixivConfig.PixivConfig()
__dbManager__ = PixivDBManager.PixivDBManager(config = __config__)
__br__ = None
__blacklistTags = list()
__suppressTags = list()
__log__ = PixivHelper.GetLogger()
__errorList = list()

## http://www.pixiv.net/member_illust.php?mode=medium&illust_id=18830248
__re_illust = re.compile(r'member_illust.*illust_id=(\d*)')
__re_manga_page = re.compile('(\d+(_big)?_p\d+)')


### Utilities function ###
def clear_all():
    all_vars = [var for var in globals() if (var[:2], var[-2:]) != ("__", "__") and var != "clear_all"]
    for var in all_vars:
        del globals()[var]


def custom_request(url):
    if __config__.useProxy:
        proxy = urllib2.ProxyHandler(__config__.proxy)
        opener = urllib2.build_opener(proxy)
        urllib2.install_opener(opener)
    req = urllib2.Request(url)
    return req


#-T04------For download file
#noinspection PyUnusedLocal
def download_image(url, filename, referer, overwrite, retry, backup_old_file=False):
    try:
        try:
            req = custom_request(url)

            if referer is not None:
                req.add_header('Referer', referer)
            else:
                req.add_header('Referer', 'http://www.pixiv.net')

            print "Using Referer:", str(referer)

            print 'Start downloading...',
            start_time = datetime.datetime.now()
            res = __br__.open_novisit(req)
            file_size = -1
            try:
                file_size = int(res.info()['Content-Length'])
            except KeyError:
                file_size = -1
                print "\tNo file size information!"
            except:
                raise

            if os.path.exists(filename) and os.path.isfile(filename):
                old_size = os.path.getsize(filename)
                if not overwrite and int(file_size) == old_size:
                    print "\tFile exist! (Identical Size)"
                    return 0  # Yavos: added 0 -> updateImage() will be executed
                else:
                    if backup_old_file:
                        split_name = filename.rsplit(".", 1)
                        new_name = filename + "." + str(int(time.time()))
                        if len(split_name) == 2:
                            new_name = split_name[0] + "." + str(int(time.time())) + "." + split_name[1]
                        PixivHelper.safePrint("\t Found file with different file size, backing up to: " + new_name)
                        __log__.info("Found file with different file size, backing up to: " + new_name)
                        os.rename(filename, new_name)
                    else:
                        print "\t Found file with different file size, removing..."
                        __log__.info(
                           "Found file with different file size, removing old file (old: {0} vs new: {1})".format(
                              old_size, file_size))
                        os.remove(filename)

            directory = os.path.dirname(filename)
            if not os.path.exists(directory):
                __log__.info('Creating directory: ' + directory)
                os.makedirs(directory)

            try:
                save = file(filename + '.pixiv', 'wb+', 4096)
            except IOError:
                msg = "Error at download_image(): Cannot save {0} to {1}: {2}".format(url, filename, sys.exc_info())
                PixivHelper.safePrint(msg)
                __log__.error(unicode(msg))
                filename = os.path.split(url)[1]
                filename = filename.split("?")[0]
                filename = PixivHelper.sanitizeFilename(filename)
                save = file(filename + '.pixiv', 'wb+', 4096)
                msg2 = 'File is saved to ' + filename
                __log__.info(msg2)

            prev = 0
            curr = 0

            print '{0:22} Bytes'.format(prev),
            try:
                while 1:
                    save.write(res.read(PixivConstant.BUFFER_SIZE))
                    curr = save.tell()
                    print '\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b',
                    print '{0:9} of {1:9} Bytes'.format(curr, file_size),

                    ## check if downloaded file is complete
                    if file_size > 0:
                        if curr == file_size:
                            total_time = (datetime.datetime.now() - start_time).total_seconds()
                            print ' Completed in {0}s ({1})'.format(total_time,
                                                                   PixivHelper.speedInStr(file_size, total_time))
                            break
                        elif curr == prev:  # no file size info
                            total_time = (datetime.datetime.now() - start_time).total_seconds()
                            print ' Completed in {0}s ({1})'.format(total_time,
                                                                   PixivHelper.speedInStr(curr, total_time))
                            break
                    elif curr == prev:  # no file size info
                        total_time = (datetime.datetime.now() - start_time).total_seconds()
                        print ' Completed in {0}s ({1})'.format(total_time, PixivHelper.speedInStr(curr, total_time))
                        break
                    prev = curr
                if start_iv or __config__.createDownloadLists:
                    dfile = codecs.open(dfilename, 'a+', encoding='utf-8')
                    dfile.write(filename + "\n")
                    dfile.close()
            except:
                if file_size > 0 and curr < file_size:
                    PixivHelper.printAndLog('error',
                                            'Downloaded file incomplete! {0:9} of {1:9} Bytes'.format(curr, file_size))
                    PixivHelper.printAndLog('error', 'Filename = ' + unicode(filename))
                    PixivHelper.printAndLog('error', 'URL      = {0}'.format(url))
                raise
            finally:
                save.close()
                if overwrite and os.path.exists(filename):
                    os.remove(filename)
                os.rename(filename + '.pixiv', filename)
                del save
                del req
                del res
        except urllib2.HTTPError as httpError:
            PixivHelper.printAndLog('error', '[download_image()] ' + str(httpError) + ' (' + url + ')')
            if httpError.code == 404:
                return -1
            if httpError.code == 502:
                return -1
            raise
        except urllib2.URLError as urlError:
            PixivHelper.printAndLog('error', '[download_image()] ' + str(urlError) + ' (' + url + ')')
            raise
        except IOError as ioex:
            if ioex.errno == 28:
                PixivHelper.printAndLog('error', ioex.message)
                raw_input("Press Enter to retry.")
                return -1
            raise
        except KeyboardInterrupt:
            PixivHelper.printAndLog('info', 'Aborted by user request => Ctrl-C')
            raise
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            __log__.exception('Error at download_image(): ' + str(sys.exc_info()) + '(' + url + ')')
            raise
    except KeyboardInterrupt:
        raise
    except:
        if retry > 0:
            repeat = range(1, __config__.retryWait)
            for t in repeat:
                print t,
                time.sleep(1)
            print ''
            return download_image(url, filename, referer, overwrite, retry - 1)
        else:
            raise
    print ' done.'
    return 0


def load_cookie(cookie_value):
    """ Load cookie to the Browser instance """
    ck = cookielib.Cookie(version=0, name='PHPSESSID', value=cookie_value, port=None,
                         port_specified=False, domain='pixiv.net', domain_specified=False,
                         domain_initial_dot=False, path='/', path_specified=True,
                         secure=False, expires=None, discard=True, comment=None,
                         comment_url=None, rest={'HttpOnly': None}, rfc2109=False)
    PixivBrowserFactory.addCookie(ck)


### Pixiv login related function ###
def pixiv_login_cookie():
    """  Log in to Pixiv using saved cookie, return True if success """

    PixivHelper.printAndLog('info', 'logging in with saved cookie')
    cookie_value = __config__.cookie
    if len(cookie_value) > 0:
        PixivHelper.printAndLog('info', 'Trying to log with saved cookie')
        load_cookie(cookie_value)
        req = custom_request('http://www.pixiv.net/mypage.php')
        __br__.open(req)
        res_url = __br__.response().geturl()
        if res_url == 'http://www.pixiv.net/mypage.php':
            print 'done.'
            __log__.info('Logged in using cookie')
            return True
        else:
            __log__.info('Failed to login using cookie, returned page: ' + res_url)
            PixivHelper.printAndLog('info', 'Cookie already expired/invalid.')
    return False


def pixiv_login(username, password):
    """ Log in to Pixiv, return 0 if success """

    try:
        PixivHelper.printAndLog('info', 'Log in using form.')
        req = custom_request(PixivConstant.PIXIV_URL + PixivConstant.PIXIV_LOGIN_URL)
        __br__.open(req)

        __br__.select_form(nr=PixivConstant.PIXIV_FORM_NUMBER)
        __br__['pixiv_id'] = username
        __br__['pass'] = password
        if __config__.keepSignedIn:
            __br__.find_control('skip').items[0].selected = True

        response = __br__.submit()
        return pixiv_process_login(response)
    except:
        print 'Error at pixiv_login():', sys.exc_info()
        print 'failed'
        __log__.exception('Error at pixiv_login(): ' + str(sys.exc_info()))
        raise


#noinspection PyProtectedMember
def pixiv_process_login(response):
    __log__.info('Logging in, return url: ' + response.geturl())
    ## failed login will return to either of these page:
    ## http://www.pixiv.net/login.php
    ## https://www.secure.pixiv.net/login.php
    if response.geturl().find('pixiv.net/login.php') == -1:
        print 'done.'
        __log__.info('Logged in')
        ## write back the new cookie value
        for cookie in __br__._ua_handlers['_cookies'].cookiejar:
            if cookie.name == 'PHPSESSID':
                print 'new cookie value:', cookie.value
                __config__.cookie = cookie.value
                __config__.writeConfig(path=configfile)
                break
        return True
    else:
        errors = parse_login_error(response)
        if len(errors) > 0:
            for error in errors:
                PixivHelper.printAndLog('error', 'Server Reply: ' + error.string)
        else:
            PixivHelper.printAndLog('info', 'Wrong username or password.')
        return False


def pixiv_login_ssl(username, password):
    try:
        PixivHelper.printAndLog('info', 'Log in using secure form.')
        req = custom_request(PixivConstant.PIXIV_URL_SSL)
        __br__.open(req)

        __br__.select_form(nr=PixivConstant.PIXIV_FORM_NUMBER_SSL)
        __br__['pixiv_id'] = username
        __br__['pass'] = password
        if __config__.keepSignedIn:
            __br__.find_control('skip').items[0].selected = True

        response = __br__.submit()
        return pixiv_process_login(response)
    except:
        print 'Error at pixiv_login_ssl():', sys.exc_info()
        __log__.exception('Error at pixiv_login_ssl(): ' + str(sys.exc_info()))
        raise


def parse_login_error(res):
    page = BeautifulSoup(res.read())
    r = page.findAll('span', attrs={'class': 'error'})
    return r


## Start of main processing logic
#noinspection PyUnusedLocal
def process_list(mode, list_file_name=None):
    result = None
    try:
        ## Getting the list
        if __config__.processFromDb:
            PixivHelper.printAndLog('info', 'Processing from database.')
            if __config__.dayLastUpdated == 0:
                result = __dbManager__.selectAllMember()
            else:
                print 'Select only last', __config__.dayLastUpdated, 'days.'
                result = __dbManager__.selectMembersByLastDownloadDate(__config__.dayLastUpdated)
        else:
            PixivHelper.printAndLog('info', 'Processing from list file: {0}'.format(list_file_name))
            result = PixivListItem.parseList(list_file_name, __config__.rootDirectory)

        print "Found " + str(len(result)) + " items."

        ## iterating the list
        for item in result:
            retry_count = 0
            while True:
                try:
                    process_member(mode, item.memberId, item.path)
                    break
                except KeyboardInterrupt:
                    raise
                except:
                    if retry_count > __config__.retry:
                        PixivHelper.printAndLog('error', 'Giving up member_id: ' + str(item.memberId))
                        break
                    retry_count = retry_count + 1
                    print 'Something wrong, retrying after 2 second (', retry_count, ')'
                    time.sleep(2)

            __br__.clear_history()
            print 'done.'
    except KeyboardInterrupt:
        raise
    except:
        print 'Error at process_list():', sys.exc_info()
        print 'Failed'
        __log__.exception('Error at process_list(): ' + str(sys.exc_info()))
        raise


def process_member(mode, member_id, user_dir='', page=1, end_page=0, bookmark=False):
    global __errorList
    # Yavos added dir-argument which will be initialized as '' when not given
    PixivHelper.printAndLog('info', 'Processing Member Id: ' + str(member_id))
    if page != 1:
        PixivHelper.printAndLog('info', 'Start Page: ' + str(page))
    if end_page != 0:
        PixivHelper.printAndLog('info', 'End Page: ' + str(end_page))
        if __config__.numberOfPage != 0:
            PixivHelper.printAndLog('info', 'Number of page setting will be ignored')
    elif np != 0:
        PixivHelper.printAndLog('info', 'End Page from command line: ' + str(np))
    elif __config__.numberOfPage != 0:
        PixivHelper.printAndLog('info', 'End Page from config: ' + str(__config__.numberOfPage))

    __config__.loadConfig(path=configfile)
    list_page = None
    try:
        no_of_images = 1
        is_avatar_downloaded = False
        flag = True
        updated_limit_count = 0

        while flag:
            print 'Page ', page
            set_console_title("MemberId: " + str(member_id) + " Page: " + str(page))
            ## Try to get the member page
            while True:
                try:
                    if bookmark:
                        member_url = 'http://www.pixiv.net/bookmark.php?id=' + str(member_id) + '&p=' + str(page)
                    else:
                        member_url = 'http://www.pixiv.net/member_illust.php?id=' + str(member_id) + '&p=' + str(page)
                    if __config__.r18mode:
                        member_url = member_url + '&tag=R-18'
                        PixivHelper.printAndLog('info', 'R-18 Mode only.')
                    PixivHelper.printAndLog('info', 'Member Url: ' + member_url)
                    try:
                        list_page = __br__.open(member_url)
                    except urllib2.HTTPError as hex:
                        if hex.code in [403, 404]:
                            list_page = hex
                        else:
                            raise
                    artist = PixivArtist(mid=member_id, page=BeautifulSoup(list_page.read()))
                    break
                except PixivException as ex:
                    PixivHelper.printAndLog('info', 'Member ID (' + str(member_id) + '): ' + str(ex))
                    if ex.errorCode == PixivException.NO_IMAGES:
                        pass
                    if ex.errorCode == PixivException.SERVER_ERROR:
                        print "Retrying... ",
                        repeat = range(1, __config__.retryWait)
                        for t in repeat:
                            print t,
                            time.sleep(1)
                        print ''
                    else:
                        PixivHelper.dumpHtml(
                           "Dump for " + str(member_id) + " Error Code " + str(ex.errorCode) + ".html",
                           list_page.get_data())
                        if ex.errorCode == PixivException.USER_ID_NOT_EXISTS or ex.errorCode == PixivException.USER_ID_SUSPENDED:
                            __dbManager__.setIsDeletedFlagForMemberId(int(member_id))
                            PixivHelper.printAndLog('info',
                                                    'Set IsDeleted for MemberId: ' + str(member_id) + ' not exist.')
                            #__dbManager__.deleteMemberByMemberId(member_id)
                            #PixivHelper.printAndLog('info', 'Deleting MemberId: ' + str(member_id) + ' not exist.')
                        if ex.errorCode == PixivException.OTHER_MEMBER_ERROR:
                            PixivHelper.safePrint(ex.message)
                            __errorList.append(dict(type="Member", id=str(member_id), message=ex.message, exception=ex))
                    return
                except AttributeError:
                    # Possible layout changes, try to dump the file below
                    raise
                except Exception:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    traceback.print_exception(exc_type, exc_value, exc_traceback)
                    PixivHelper.printAndLog('error', 'Error at processing Artist Info: ' + str(sys.exc_info()))
                    __log__.exception('Error at processing Artist Info: ' + str(member_id))
                    repeat = range(1, __config__.retryWait)
                    for t in repeat:
                        print t,
                        time.sleep(1)
                    print ''
            PixivHelper.safePrint('Member Name  : ' + artist.artistName)
            print 'Member Avatar:', artist.artistAvatar
            print 'Member Token :', artist.artistToken

            if artist.artistAvatar.find('no_profile') == -1 and not is_avatar_downloaded and __config__.downloadAvatar:
                ## Download avatar as folder.jpg
                filename_format = __config__.filenameFormat
                if user_dir == '':
                    target_dir = __config__.rootDirectory
                else:
                    target_dir = user_dir

                avatar_filename = PixivHelper.CreateAvatarFilename(filename_format, __config__.tagsSeparator,
                                                                   __config__.tagsLimit, artist, target_dir)
                download_image(artist.artistAvatar, avatar_filename, list_page.geturl(), __config__.overwrite,
                               __config__.retry, __config__.backupOldFile)
                is_avatar_downloaded = True

            __dbManager__.updateMemberName(member_id, artist.artistName)

            if not artist.haveImages:
                PixivHelper.printAndLog('info', "No image found for: " + str(member_id))
                flag = False
                continue

            result = PixivConstant.PIXIVUTIL_NOT_OK
            for image_id in artist.imageList:
                print '#' + str(no_of_images)
                if mode == PixivConstant.PIXIVUTIL_MODE_UPDATE_ONLY:
                    r = __dbManager__.selectImageByMemberIdAndImageId(member_id, image_id)
                    if r is not None and not __config__.alwaysCheckFileSize:
                        print 'Already downloaded:', image_id
                        updated_limit_count = updated_limit_count + 1
                        if updated_limit_count > __config__.checkUpdatedLimit:
                            if __config__.checkUpdatedLimit != 0:
                                print 'Skipping member:', member_id
                                __dbManager__.updateLastDownloadedImage(member_id, image_id)

                                del list_page
                                __br__.clear_history()
                                return
                        gc.collect()
                        continue

                retry_count = 0
                while True:
                    try:
                        total_image_page_count = ((page - 1) * 20) + len(artist.imageList)
                        title_prefix = "MemberId: {0} Page: {1} Image {2}+{3} of {4}".format(member_id,
                                                                                             page,
                                                                                             no_of_images,
                                                                                             updated_limit_count,
                                                                                             total_image_page_count)
                        result = process_image(mode, artist, image_id, user_dir, bookmark, title_prefix=title_prefix)  # Yavos added dir-argument to pass
                        __dbManager__.insertImage(member_id, image_id)
                        break
                    except KeyboardInterrupt:
                        result = PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT
                        break
                    except:
                        if retry_count > __config__.retry:
                            PixivHelper.printAndLog('error', "Giving up image_id: " + str(image_id))
                            return
                        retry_count = retry_count + 1
                        print "Stuff happened, trying again after 2 second (", retry_count, ")"
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        traceback.print_exception(exc_type, exc_value, exc_traceback)
                        __log__.exception(
                           'Error at process_member(): ' + str(sys.exc_info()) + ' Member Id: ' + str(member_id))
                        time.sleep(2)

                no_of_images = no_of_images + 1

                if result == PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT:
                    choice = raw_input("Keyboard Interrupt detected, continue to next image (Y/N)")
                    if choice.upper() == 'N':
                        PixivHelper.printAndLog("info", "Member: " + str(member_id) + ", processing aborted")
                        flag = False
                        break
                    else:
                        continue

                ## return code from process image
                if result == PixivConstant.PIXIVUTIL_SKIP_OLDER:
                    PixivHelper.printAndLog("info", "Reached older images, skippin to next member.")
                    flag = False
                    break

            if artist.isLastPage:
                print "Last Page"
                flag = False

            page = page + 1

            ## page limit checking
            if end_page > 0 and page > end_page:
                print "Page limit reached (from endPage limit =" + str(end_page) + ")"
                flag = False
            else:
                if np_is_valid:  # Yavos: overwriting config-data
                    if page > np and np > 0:
                        print "Page limit reached (from command line =" + str(np) + ")"
                        flag = False
                elif page > __config__.numberOfPage and __config__.numberOfPage > 0:
                    print "Page limit reached (from config =" + str(__config__.numberOfPage) + ")"
                    flag = False

            del artist
            del list_page
            __br__.clear_history()
            gc.collect()

        __dbManager__.updateLastDownloadedImage(member_id, image_id)
        print 'Done.\n'
        __log__.info('Member_id: ' + str(member_id) + ' complete, last image_id: ' + str(image_id))
    except KeyboardInterrupt:
        raise
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        PixivHelper.printAndLog('error', 'Error at process_member(): ' + str(sys.exc_info()))
        __log__.exception('Error at process_member(): ' + str(member_id))
        try:
            if list_page is not None:
                dump_filename = 'Error page for member ' + str(member_id) + '.html'
                PixivHelper.dumpHtml(dump_filename, list_page.get_data())
                PixivHelper.printAndLog('error', "Dumping html to: " + dump_filename)
        except:
            PixivHelper.printAndLog('error', 'Cannot dump page for member_id:' + str(member_id))
        raise


def process_image(mode, artist=None, image_id=None, user_dir='', bookmark=False, search_tags='', title_prefix=None, bookmark_count=-1):
    global __errorList
    #Yavos added dir-argument which will be initialized as '' when not given
    parse_big_image = None
    medium_page = None
    view_page = None
    image = None
    result = None

    try:
        filename = 'N/A'
        print 'Processing Image Id:', image_id
        ## check if already downloaded. images won't be downloaded twice - needed in process_image to catch any download
        r = __dbManager__.selectImageByImageId(image_id)
        if r is not None and not __config__.alwaysCheckFileSize:
            if mode == PixivConstant.PIXIVUTIL_MODE_UPDATE_ONLY:
                print 'Already downloaded:', image_id
                gc.collect()
                return

        retry_count = 0
        while 1:
            try:
                medium_page = __br__.open('http://www.pixiv.net/member_illust.php?mode=medium&illust_id=' + str(image_id))
                parse_medium_page = BeautifulSoup(medium_page.read())
                image = PixivImage(iid=image_id, page=parse_medium_page, parent=artist, fromBookmark=bookmark, bookmark_count=bookmark_count)
                # dump medium page
                if __config__.dumpMediumPage :
                    dump_filename = "medium page for image {0}.html".format(image_id)
                    PixivHelper.dumpHtml(dump_filename, medium_page.get_data())
                if title_prefix is not None:
                    set_console_title(title_prefix + " ImageId: {0}".format(image.imageId))
                else:
                    set_console_title('MemberId: ' + str(image.artist.artistId) + ' ImageId: ' + str(image.imageId))
                parse_medium_page.decompose()
                del parse_medium_page
                break
            except PixivException as ex:
                if ex.errorCode == PixivException.UNKNOWN_IMAGE_ERROR:
                    PixivHelper.safePrint(ex.message)
                    __errorList.append(dict(type="Image", id=str(image_id), message=ex.message, exception=ex))
                elif ex.errorCode == PixivException.SERVER_ERROR:
                    print ex
                    repeat = range(1, __config__.retryWait)
                    for t in repeat:
                        print t,
                        time.sleep(1)
                    print ''
                    retry_count = retry_count + 1
                    if retry_count > __config__.retry:
                        PixivHelper.printAndLog('error', 'Giving up image_id (medium): ' + str(image_id))
                        if medium_page is not None:
                            dump_filename = 'Error medium page for image ' + str(image_id) + '.html'
                            PixivHelper.dumpHtml(dump_filename, medium_page.get_data())
                            PixivHelper.printAndLog('error', 'Dumping html to: ' + dump_filename)
                        return
                else:
                    PixivHelper.printAndLog('info', 'Image ID (' + str(image_id) + '): ' + str(ex))
                return
            except urllib2.URLError as ue:
                print ue
                repeat = range(1, __config__.retryWait)
                for t in repeat:
                    print t,
                    time.sleep(1)
                print ''
                retry_count = retry_count + 1
                if retry_count > __config__.retry:
                    PixivHelper.printAndLog('error', 'Giving up image_id (medium): ' + str(image_id))
                    if medium_page is not None:
                        dump_filename = 'Error medium page for image ' + str(image_id) + '.html'
                        PixivHelper.dumpHtml(dump_filename, medium_page.get_data())
                        PixivHelper.printAndLog('error', 'Dumping html to: ' + dump_filename)
                    return

        download_image_flag = True

        if __config__.dateDiff > 0:
            if image.worksDateDateTime != datetime.datetime.fromordinal(1):
                if image.worksDateDateTime < datetime.datetime.today() - datetime.timedelta(__config__.dateDiff):
                    PixivHelper.printAndLog('info', 'Skipping image_id: ' + str(
                          image_id) + ' because contains older than: ' + str(__config__.dateDiff) + ' day(s).')
                    download_image_flag = False
                    result = PixivConstant.PIXIVUTIL_SKIP_OLDER

        if __config__.useBlacklistTags:
            for item in __blacklistTags:
                if item in image.imageTags:
                    PixivHelper.printAndLog('info', 'Skipping image_id: ' + str(
                          image_id) + ' because contains blacklisted tags: ' + item)
                    download_image_flag = False
                    result = PixivConstant.PIXIVUTIL_SKIP_BLACKLIST
                    break

        if download_image_flag:

            PixivHelper.safePrint("Title: " + image.imageTitle)
            PixivHelper.safePrint("Tags : " + ', '.join(image.imageTags))
            PixivHelper.safePrint("Date : " + str(image.worksDateDateTime))
            print "Mode :", image.imageMode

            if __config__.useSuppressTags:
                for item in __suppressTags:
                    if item in image.imageTags:
                        image.imageTags.remove(item)

            error_count = 0
            while True:
                try:
                    #big_url = 'http://www.pixiv.net/member_illust.php?mode={0}&illust_id={1}'.format(image.imageMode, image_id)
                    view_page = __br__.follow_link(url_regex='mode=' + image.imageMode + '&illust_id=' + str(image_id))
                    parse_big_image = BeautifulSoup(view_page.read())
                    if parse_big_image is not None:
                        image.ParseImages(page=parse_big_image)
                        parse_big_image.decompose()
                        del parse_big_image
                    break
                except PixivException as ex:
                    PixivHelper.printAndLog('info', 'Image ID (' + str(image_id) + '): ' + str(ex))
                    return
                except urllib2.URLError as ue:
                    if error_count > __config__.retry:
                        PixivHelper.printAndLog('error', 'Giving up image_id: ' + str(image_id))
                        return
                    error_count = error_count + 1
                    print ue
                    repeat = range(1, __config__.retryWait)
                    for t in repeat:
                        print t,
                        time.sleep(1)
                    print ''
            if image.imageMode == 'manga':
                print "Page Count :", image.imageCount

            result = PixivConstant.PIXIVUTIL_OK
            skip_one = False
            for img in image.imageUrls:
                if skip_one:
                    skip_one = False
                    continue
                print 'Image URL :', img
                url = os.path.basename(img)
                splitted_url = url.split('.')
                if splitted_url[0].startswith(str(image_id)):
                    #Yavos: filename will be added here if given in list
                    filename_format = __config__.filenameFormat
                    if image.imageMode == 'manga':
                        filename_format = __config__.filenameMangaFormat

                    if user_dir == '':  # Yavos: use config-options
                        target_dir = __config__.rootDirectory
                    else:  # Yavos: use filename from list
                        target_dir = user_dir

                    filename = PixivHelper.makeFilename(filename_format, image, tagsSeparator=__config__.tagsSeparator,
                                                        tagsLimit=__config__.tagsLimit, fileUrl=url, bookmark=bookmark,
                                                        searchTags=search_tags)
                    filename = PixivHelper.sanitizeFilename(filename, target_dir)

                    if image.imageMode == 'manga' and __config__.createMangaDir:
                        manga_page = __re_manga_page.findall(filename)
                        if len(manga_page) > 0:
                            splitted_filename = filename.split(manga_page[0][0], 1)
                            splitted_manga_page = manga_page[0][0].split("_p", 1)
                            filename = splitted_filename[0] + splitted_manga_page[0] + os.sep + "_p" + splitted_manga_page[1] + splitted_filename[1]

                    PixivHelper.safePrint('Filename  : ' + filename)
                    result = PixivConstant.PIXIVUTIL_NOT_OK
                    try:
                        overwrite = False
                        if mode == PixivConstant.PIXIVUTIL_MODE_OVERWRITE:
                            overwrite = True
                        result = download_image(img, filename, view_page.geturl(), overwrite, __config__.retry,
                                                __config__.backupOldFile)

                        if result == PixivConstant.PIXIVUTIL_NOT_OK and image.imageMode == 'manga' and img.find('_big') > -1:
                            print 'No big manga image available, try the small one'
                        elif result == PixivConstant.PIXIVUTIL_OK and image.imageMode == 'manga' and img.find('_big') > -1:
                            skip_one = True
                        elif result == PixivConstant.PIXIVUTIL_NOT_OK:
                            PixivHelper.printAndLog('error', 'Image url not found: ' + str(image.imageId))
                    except urllib2.URLError:
                        PixivHelper.printAndLog('error', 'Giving up url: ' + str(img))
                        __log__.exception('Error when download_image(): ' + str(img))
                    print ''

            if __config__.writeImageInfo:
                image.WriteInfo(filename + ".txt")

        ## Only save to db if all images is downloaded completely
        if result == PixivConstant.PIXIVUTIL_OK:
            try:
                __dbManager__.insertImage(image.artist.artistId, image.imageId)
            except:
                pass
            __dbManager__.updateImage(image.imageId, image.imageTitle, filename)

        if medium_page is not None:
            del medium_page
        if view_page is not None:
            del view_page
        if image is not None:
            del image
        gc.collect()
        ##clearall()
        print '\n'
        return result
    except KeyboardInterrupt:
        raise
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        PixivHelper.printAndLog('error', 'Error at process_image(): ' + str(sys.exc_info()))
        __log__.exception('Error at process_image(): ' + str(image_id))
        try:
            if view_page is not None:
                dump_filename = 'Error Big Page for image ' + str(image_id) + '.html'
                PixivHelper.dumpHtml(dump_filename, view_page.get_data())
                PixivHelper.printAndLog('error', 'Dumping html to: ' + dump_filename)
        except:
            PixivHelper.printAndLog('error', 'Cannot dump big page for image_id: ' + str(image_id))
        try:
            if medium_page is not None:
                dump_filename = 'Error Medium Page for image ' + str(image_id) + '.html'
                PixivHelper.dumpHtml(dump_filename, medium_page.get_data())
                PixivHelper.printAndLog('error', 'Dumping html to: ' + dump_filename)
        except:
            PixivHelper.printAndLog('error', 'Cannot medium dump page for image_id: ' + str(image_id))
        raise


def process_tags(mode, tags, page=1, end_page=0, wild_card=True, title_caption=False,
               start_date=None, end_date=None, use_tags_as_dir=False, member_id=None,
               bookmark_count=None):
    try:
        __config__.loadConfig(path=configfile)  # Reset the config for root directory

        try:
            if tags.startswith("%"):
                search_tags = PixivHelper.toUnicode(urllib.unquote_plus(tags))
            else:
                search_tags = PixivHelper.toUnicode(tags)
        except UnicodeDecodeError:
            ## From command prompt
            search_tags = tags.decode(sys.stdout.encoding).encode("utf8")
            search_tags = PixivHelper.toUnicode(search_tags)

        if use_tags_as_dir:
            print "Save to each directory using query tags."
            __config__.rootDirectory += os.sep + PixivHelper.sanitizeFilename(search_tags)

        if not tags.startswith("%"):
            try:
                ## Encode the tags
                tags = tags.encode('utf-8')
                tags = urllib.quote_plus(tags)
            except UnicodeDecodeError:
                try:
                    ## from command prompt
                    tags = urllib.quote_plus(tags.decode(sys.stdout.encoding).encode("utf8"))
                except UnicodeDecodeError:
                    PixivHelper.printAndLog('error', 'Cannot decode the tags, you can use URL Encoder (http://meyerweb.com/eric/tools/dencoder/) and paste the encoded tag.')
                    __log__.exception('decodeTags()')
        i = page
        images = 1
        skipped_count = 0

        date_param = ""
        if start_date is not None:
            date_param = date_param + "&scd=" + start_date
        if end_date is not None:
            date_param = date_param + "&ecd=" + end_date

        PixivHelper.printAndLog('info', 'Searching for: (' + search_tags + ") " + tags + date_param)
        flag = True
        while flag:
            if not member_id is None:
                url = 'http://www.pixiv.net/member_illust.php?id=' + str(member_id) + '&tag=' + tags + '&p=' + str(i)
            else:
                if title_caption:
                    url = 'http://www.pixiv.net/search.php?s_mode=s_tc&p=' + str(i) + '&word=' + tags + date_param
                else:
                    if wild_card:
                        url = 'http://www.pixiv.net/search.php?s_mode=s_tag&p=' + str(i) + '&word=' + tags + date_param
                        print "Using Wildcard (search.php)"
                    else:
                        url = 'http://www.pixiv.net/search.php?s_mode=s_tag_full&word=' + tags + '&p=' + str(
                           i) + date_param

            if __config__.r18mode:
                url = url + '&r18=1'

            # encode to ascii
            url = unicode(url).encode('iso_8859_1')

            PixivHelper.printAndLog('info', 'Looping... for ' + url)
            search_page = __br__.open(url)

            parse_search_page = BeautifulSoup(search_page.read())
            t = PixivTags()
            l = list()
            if not member_id is None:
                l = t.parseMemberTags(parse_search_page)
            else:
                try:
                    l = t.parseTags(parse_search_page)
                except:
                    PixivHelper.dumpHtml("Dump for SearchTags " + tags + ".html", search_page.get_data())
                    raise

            if len(l) == 0:
                print 'No more images'
                flag = False
            else:
                for item in t.itemList:
                    print 'Image #' + str(images)
                    print 'Image Id:', str(item.imageId)
                    print 'Bookmark Count:', str(item.bookmarkCount)
                    if bookmark_count is not None and bookmark_count > item.bookmarkCount:
                        PixivHelper.printAndLog('info', 'Skipping imageId=' + str(
                           item.imageId) + ' because less than bookmark count limit (' + str(bookmark_count) + ' > ' + str(item.bookmarkCount) + ')')
                        skipped_count = skipped_count + 1
                        continue
                    result = 0
                    while True:
                        try:
                            total_image = ((i - 1) * 20) + len(t.itemList)
                            title_prefix = "Tags:{0} Page:{1} Image {2}+{3} of {4}".format(tags, i, images, skipped_count, total_image)
                            if not member_id is None:
                                title_prefix = "MemberId: {0} Tags:{1} Page:{2} Image {3}+{4} of {5}".format(member_id,
                                                                                                              tags, i,
                                                                                                              images,
                                                                                                              skipped_count,
                                                                                                              total_image)
                            process_image(mode, None, item.imageId, search_tags=search_tags, title_prefix=title_prefix, bookmark_count=item.bookmarkCount)
                            break
                        except KeyboardInterrupt:
                            result = PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT
                            break
                        except httplib.BadStatusLine:
                            print "Stuff happened, trying again after 2 second..."
                            time.sleep(2)

                    images = images + 1

                    if result == PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT:
                        choice = raw_input("Keyboard Interrupt detected, continue to next image (Y/N)")
                        if choice.upper() == 'N':
                            PixivHelper.printAndLog("info", "Tags: " + tags + ", processing aborted")
                            flag = False
                            break
                        else:
                            continue

            __br__.clear_history()

            i = i + 1

            parse_search_page.decompose()
            del parse_search_page
            del search_page

            if end_page != 0 and end_page < i:
                print 'End Page reached.'
                flag = False
            if t.isLastPage:
                print 'Last page'
                flag = False
        print 'done'
    except KeyboardInterrupt:
        raise
    except:
        print 'Error at process_tags():', sys.exc_info()
        __log__.exception('Error at process_tags(): ' + str(sys.exc_info()))
        try:
            if search_page is not None:
                dump_filename = 'Error page for search tags ' + tags + '.html'
                PixivHelper.dumpHtml(dump_filename, search_page.get_data())
                PixivHelper.printAndLog('error', "Dumping html to: " + dump_filename)
        except:
            PixivHelper.printAndLog('error', 'Cannot dump page for search tags:' + search_tags)
        raise


def process_tags_list(mode, filename, page=1, end_page=0):
    try:
        print "Reading:", filename
        l = PixivTags.parseTagsList(filename)
        for tag in l:
            process_tags(mode, tag, page=page, end_page=end_page, use_tags_as_dir=__config__.useTagsAsDir)
    except KeyboardInterrupt:
        raise
    except:
        print 'Error at process_tags_list():', sys.exc_info()
        __log__.exception('Error at process_tags_list(): ' + str(sys.exc_info()))
        raise


def process_image_bookmark(mode, hide='n', start_page=1, end_page=0):
    global np_is_valid
    global np
    try:
        print "Importing image bookmarks..."
        #totalList = list()
        i = start_page
        image_count = 1
        while True:
            if end_page != 0 and i > end_page:
                print "Page Limit reached: " + str(end_page)
                break

            print "Importing user's bookmarked image from page", str(i),
            url = 'http://www.pixiv.net/bookmark.php?p=' + str(i)
            if hide == 'y':
                url = url + "&rest=hide"
            page = __br__.open(url)
            parse_page = BeautifulSoup(page.read())
            l = PixivBookmark.parseImageBookmark(parse_page)
            if len(l) == 0:
                print "No more images."
                break
            else:
                print " found " + str(len(l)) + " images."

            for item in l:
                print "Image #" + str(image_count)
                process_image(mode, artist=None, image_id=item)
                image_count = image_count + 1

            i = i + 1

            parse_page.decompose()
            del parse_page

            if np_is_valid:  # Yavos: overwrite config-data
                if i > np and np != 0:
                    break
            elif i > __config__.numberOfPage and __config__.numberOfPage != 0:
                break

        print "Done.\n"
    except KeyboardInterrupt:
        raise
    except:
        print 'Error at process_image_bookmark():', sys.exc_info()
        __log__.exception('Error at process_image_bookmark(): ' + str(sys.exc_info()))
        raise


def get_bookmarks(hide, start_page=1, end_page=0):
    """Get user/artists bookmark"""
    total_list = list()
    i = start_page
    while True:
        if end_page != 0 and i > end_page:
            print 'Limit reached'
            break
        print 'Exporting page', str(i),
        url = 'http://www.pixiv.net/bookmark.php?type=user&p=' + str(i)
        if hide:
            url = url + "&rest=hide"
        page = __br__.open(url)
        parse_page = BeautifulSoup(page.read())
        l = PixivBookmark.parseBookmark(parse_page)
        if len(l) == 0:
            print 'No more data'
            break
        total_list.extend(l)
        i = i + 1
        print str(len(l)), 'items'
    return total_list


def process_bookmark(mode, hide='n', start_page=1, end_page=0):
    try:
        total_list = list()
        if hide != 'o':
            print "Importing Bookmarks..."
            total_list.extend(get_bookmarks(False, start_page, end_page))
        if hide != 'n':
            print "Importing Private Bookmarks..."
            total_list.extend(get_bookmarks(True, start_page, end_page))
        print "Result: ", str(len(total_list)), "items."
        for item in total_list:
            process_member(mode, item.memberId, item.path)
    except KeyboardInterrupt:
        raise
    except:
        print 'Error at process_bookmark():', sys.exc_info()
        __log__.exception('Error at process_bookmark(): ' + str(sys.exc_info()))
        raise


def export_bookmark(filename, hide='n', start_page=1, end_page=0):
    try:
        total_list = list()
        if hide != 'o':
            print "Importing Bookmarks..."
            total_list.extend(get_bookmarks(False, start_page, end_page))
        if hide != 'n':
            print "Importing Private Bookmarks..."
            total_list.extend(get_bookmarks(True, start_page, end_page))
        print "Result: ", str(len(total_list)), "items."
        PixivBookmark.exportList(total_list, filename)
    except KeyboardInterrupt:
        raise
    except:
        print 'Error at export_bookmark():', sys.exc_info()
        __log__.exception('Error at export_bookmark(): ' + str(sys.exc_info()))
        raise


def process_new_illust_from_bookmark(mode, page_num=1, end_page_num=0):
    try:
        print "Processing New Illust from bookmark"
        i = page_num
        image_count = 1
        flag = True
        while flag:
            print "Page #" + str(i)
            url = 'http://www.pixiv.net/bookmark_new_illust.php?p=' + str(i)
            page = __br__.open(url)
            parsed_page = BeautifulSoup(page.read())
            pb = PixivNewIllustBookmark(parsed_page)
            if not pb.haveImages:
                print "No images!"
                break

            for image_id in pb.imageList:
                print "Image #" + str(image_count)
                result = process_image(mode, artist=None, image_id=int(image_id))
                image_count = image_count + 1

                if result == PixivConstant.PIXIVUTIL_SKIP_OLDER:
                    flag = False
                    break
            i = i + 1

            parsed_page.decompose()
            del parsed_page

            if (end_page_num != 0 and i > end_page_num) or i >= 100 or pb.isLastPage:
                print "Limit or last page reached."
                flag = False

        print "Done."
    except KeyboardInterrupt:
        raise
    except:
        print 'Error at process_new_illust_from_bookmark():', sys.exc_info()
        __log__.exception('Error at process_new_illust_from_bookmark(): ' + str(sys.exc_info()))
        raise


def process_from_group(mode, group_id, limit=0, process_external=True):
    try:
        print "Download by Group Id"
        if limit != 0:
            print "Limit: {0}".format(limit)
        if process_external:
            print "Include External Image: {0}".format(process_external)

        max_id = 0
        image_count = 0
        flag = True
        while flag:
            url = "http://www.pixiv.net/group/images.php?format=json&max_id={0}&id={1}".format(max_id, group_id)
            print "Getting images from: {0}".format(url)
            json_response = __br__.open(url)
            group_data = PixivGroup(json_response)
            max_id = group_data.maxId
            if group_data.imageList is not None and len(group_data.imageList) > 0:
                for image in group_data.imageList:
                    if image_count > limit and limit != 0:
                        flag = False
                        break
                    print "Image #{0}".format(image_count)
                    print "ImageId: {0}".format(image)
                    process_image(mode, image_id=image)
                    image_count = image_count + 1

            if process_external and group_data.externalImageList is not None and len(group_data.externalImageList) > 0:
                for image_data in group_data.externalImageList:
                    if image_count > limit and limit != 0:
                        flag = False
                        break
                    print "Image #{0}".format(image_count)
                    print "Member Id   : {0}".format(image_data.artist.artistId)
                    PixivHelper.safePrint("Member Name  : " + image_data.artist.artistName)
                    print "Member Token : {0}".format(image_data.artist.artistToken)
                    print "Image Url   : {0}".format(image_data.imageUrls[0])

                    filename = PixivHelper.makeFilename(__config__.filenameFormat, imageInfo=image_data,
                                                        tagsSeparator=__config__.tagsSeparator,
                                                        tagsLimit=__config__.tagsLimit, fileUrl=image_data.imageUrls[0])
                    filename = PixivHelper.sanitizeFilename(filename, __config__.rootDirectory)
                    PixivHelper.safePrint("Filename  : " + filename)
                    download_image(image_data.imageUrls[0], filename, url, __config__.overwrite, __config__.retry,
                                   __config__.backupOldFile)
                    image_count = image_count + 1

            if (group_data.imageList is None or len(group_data.imageList) == 0) and \
               (group_data.externalImageList is None or len(group_data.externalImageList) == 0):
                flag = False
            print ""

    except:
        print 'Error at process_from_group():', sys.exc_info()
        __log__.exception('Error at process_from_group(): ' + str(sys.exc_info()))
        raise


def header():
    print 'PixivDownloader2 version', PixivConstant.PIXIVUTIL_VERSION
    print PixivConstant.PIXIVUTIL_LINK


def get_start_and_end_number(start_only=False):
    global np_is_valid
    global np

    page_num = raw_input('Start Page (default=1): ') or 1
    try:
        page_num = int(page_num)
    except:
        print "Invalid page number:", page_num
        raise

    end_page_num = 0
    if np_is_valid:
        end_page_num = np
    else:
        end_page_num = __config__.numberOfPage

    if not start_only:
        end_page_num = raw_input('End Page (default=' + str(end_page_num) + ', 0 for no limit): ') or end_page_num
        try:
            end_page_num = int(end_page_num)
            if page_num > end_page_num and end_page_num != 0:
                print "page_num is bigger than end_page_num, assuming as page count."
                end_page_num = page_num + end_page_num
        except:
            print "Invalid end page number:", end_page_num
            raise

    return page_num, end_page_num


def get_start_and_end_number_from_args(args, offset=0, start_only=False):
    global np_is_valid
    global np
    page_num = 1
    if len(args) > 0 + offset:
        try:
            page_num = int(args[0 + offset])
            print "Start Page =", str(page_num)
        except:
            print "Invalid page number:", args[0 + offset]
            raise

    end_page_num = 0
    if np_is_valid:
        end_page_num = np
    else:
        end_page_num = __config__.numberOfPage

    if not start_only:
        if len(args) > 1 + offset:
            try:
                end_page_num = int(args[1 + offset])
                if page_num > end_page_num and end_page_num != 0:
                    print "page_num is bigger than end_page_num, assuming as page count."
                    end_page_num = page_num + end_page_num
                print "End Page =", str(end_page_num)
            except:
                print "Invalid end page number:", args[1 + offset]
                raise
    return page_num, end_page_num


def check_date_time(input_date):
    split = input_date.split("-")
    return datetime.date(int(split[0]), int(split[1]), int(split[2])).isoformat()


def get_start_and_end_date():
    start_date = None
    end_date = None
    while True:
        try:
            start_date = raw_input('Start Date [YYYY-MM-DD]: ') or None
            if start_date is not None:
                start_date = check_date_time(start_date)
            break
        except Exception as e:
            print str(e)

    while True:
        try:
            end_date = raw_input('End Date [YYYY-MM-DD]: ') or None
            if end_date is not None:
                end_date = check_date_time(end_date)
            break
        except Exception as e:
            print str(e)

    return start_date, end_date


def menu():
    set_console_title()
    header()
    print '1. Download by member_id'
    print '2. Download by image_id'
    print '3. Download by tags'
    print '4. Download from list'
    print '5. Download from online user bookmark'
    print '6. Download from online image bookmark'
    print '7. Download from tags list'
    print '8. Download new illust from bookmark'
    print '9. Download by Title/Caption'
    print '10. Download by Tag and Member Id'
    print '11. Download Member Bookmark'
    print '12. Download by Group Id'
    print '------------------------'
    print 'd. Manage database'
    print 'e. Export online bookmark'
    print 'r. Reload config.ini'
    print 'p. Print config.ini'
    print 'x. Exit'

    return raw_input('Input: ').strip()


def menu_download_by_member_id(mode, opisvalid, args):
    __log__.info('Member id mode.')
    page = 1
    end_page = 0
    if opisvalid and len(args) > 0:
        for member_id in args:
            try:
                test_id = int(member_id)
                process_member(mode, test_id)
            except:
                PixivHelper.printAndLog('error', "Member ID: {0} is not valid".format(member_id))
                continue
    else:
        member_id = raw_input('Member id: ')
        (page, end_page) = get_start_and_end_number()
        process_member(mode, member_id.strip(), page=page, end_page=end_page)


def menu_download_by_member_bookmark(mode, opisvalid, args):
    __log__.info('Member Bookmark mode.')
    page = 1
    end_page = 0
    if opisvalid and len(args) > 0:
        for member_id in args:
            try:
                test_id = int(member_id)
                process_member(mode, test_id)
            except:
                PixivHelper.printAndLog('error', "Member ID: {0} is not valid".format(member_id))
                continue
    else:
        member_id = raw_input('Member id: ')
        (page, end_page) = get_start_and_end_number()
        process_member(mode, member_id.strip(), page=page, end_page=end_page, bookmark=True)


def menu_download_by_image_id(mode, opisvalid, args):
    __log__.info('Image id mode.')
    if opisvalid and len(args) > 0:
        for image_id in args:
            try:
                test_id = int(image_id)
                process_image(mode, None, test_id)
            except:
                PixivHelper.printAndLog('error', "Image ID: {0} is not valid".format(image_id))
                continue
    else:
        image_id = raw_input('Image id: ')
        process_image(mode, None, int(image_id))


def menu_download_by_tags(mode, opisvalid, args):
    __log__.info('tags mode.')
    page = 1
    end_page = 0
    start_date = None
    end_date = None
    bookmark_count = None
    if opisvalid and len(args) > 0:
        wildcard = args[0]
        if wildcard.lower() == 'y':
            wildcard = True
        else:
            wildcard = False
        (page, end_page) = get_start_and_end_number_from_args(args, 1)
        tags = " ".join(args[3:])
    else:
        tags = PixivHelper.uni_input('Tags: ')
        bookmark_count = raw_input('Bookmark Count: ') or None
        wildcard = raw_input('Use Wildcard[y/n]: ') or 'n'
        if wildcard.lower() == 'y':
            wildcard = True
        else:
            wildcard = False
        (page, end_page) = get_start_and_end_number()
        (start_date, end_date) = get_start_and_end_date()
    if bookmark_count is not None:
        bookmark_count = int(bookmark_count)
    process_tags(mode, tags.strip(), page, end_page, wildcard, start_date=start_date, end_date=end_date,
                use_tags_as_dir=__config__.useTagsAsDir, bookmark_count=bookmark_count)


def menu_download_by_title_caption(mode, opisvalid, args):
    __log__.info('Title/Caption mode.')
    page = 1
    end_page = 0
    start_date = None
    end_date = None
    if opisvalid and len(args) > 0:
        (page, end_page) = get_start_and_end_number_from_args(args)
        tags = " ".join(args[2:])
    else:
        tags = PixivHelper.uni_input('Title/Caption: ')
        (page, end_page) = get_start_and_end_number()
        (start_date, end_date) = get_start_and_end_date()

    process_tags(mode, tags.strip(), page, end_page, wild_card=False, title_caption=True, start_date=start_date, end_date=end_date, use_tags_as_dir=__config__.useTagsAsDir)


def menu_download_by_tag_and_member_id(mode, opisvalid, args):
    __log__.info('Tag and MemberId mode.')
    member_id = 0
    tags = None

    if opisvalid and len(args) >= 2:
        member_id = int(args[0])
        (page, end_page) = get_start_and_end_number_from_args(args, 1)
        tags = " ".join(args[3:])
        PixivHelper.safePrint("Looking tags: " + tags + " from memberId: " + str(member_id))
    else:
        member_id = raw_input('Member Id: ')
        tags = PixivHelper.uni_input('Tag      : ')

    process_tags(mode, tags.strip(), member_id=int(member_id), use_tags_as_dir=__config__.useTagsAsDir)


def menu_download_from_list(mode, opisvalid, args):
    __log__.info('Batch mode.')
    global op
    global __config__

    list_file_name = __config__.downloadListDirectory + os.sep + 'list.txt'
    if opisvalid and op == '4' and len(args) > 0:
        test_file_name = __config__.downloadListDirectory + os.sep + args[0]
        if os.path.exists(test_file_name):
            list_file_name = test_file_name

    process_list(mode, list_file_name)


def menu_download_from_online_user_bookmark(mode, opisvalid, args):
    __log__.info('User Bookmark mode.')
    start_page = 1
    end_page = 0
    hide = 'n'
    if opisvalid:
        if len(args) > 0:
            arg = args[0].lower()
            if arg == 'y' or arg == 'n' or arg == 'o':
                hide = arg
            else:
                print "Invalid args: ", args
                return
            (start_page, end_page) = get_start_and_end_number_from_args(args, offset=1)
    else:
        arg = raw_input("Include Private bookmarks [y/n/o]: ") or 'n'
        arg = arg.lower()
        if arg == 'y' or arg == 'n' or arg == 'o':
            hide = arg
        else:
            print "Invalid args: ", arg
            return
        (start_page, end_page) = get_start_and_end_number()
    process_bookmark(mode, hide, start_page, end_page)


def menu_download_from_online_image_bookmark(mode, opisvalid, args):
    __log__.info("User's Image Bookmark mode.")
    start_page = 1
    end_page = 0
    hide = False

    if opisvalid and len(args) > 0:
        arg = args[0].lower()
        if arg == 'y' or arg == 'n':
            hide = arg
        else:
            print "Invalid args: ", args
            return
        (start_page, end_page) = get_start_and_end_number_from_args(args, offset=1)
    else:
        arg = raw_input("Only Private bookmarks [y/n]: ") or 'n'
        arg = arg.lower()
        if arg == 'y' or arg == 'n':
            hide = arg
        else:
            print "Invalid args: ", arg
            return
        (start_page, end_page) = get_start_and_end_number()

    process_image_bookmark(mode, hide, start_page, end_page)


def menu_download_from_tags_list(mode, opisvalid, args):
    __log__.info('Taglist mode.')
    page = 1
    end_page = 0
    if opisvalid and len(args) > 0:
        filename = args[0]
        (page, end_page) = get_start_and_end_number_from_args(args, offset=1)
    else:
        filename = raw_input("Tags list filename [tags.txt]: ") or './tags.txt'
        (page, end_page) = get_start_and_end_number()

    process_tags_list(mode, filename, page, end_page)


def menu_download_new_illust_from_bookmark(mode, opisvalid, args):
    __log__.info('New Illust from Bookmark mode.')

    if opisvalid:
        (page_num, end_page_num) = get_start_and_end_number_from_args(args, offset=0)
    else:
        (page_num, end_page_num) = get_start_and_end_number()

    process_new_illust_from_bookmark(mode, page_num, end_page_num)


def menu_download_by_group_id(mode, opisvalid, args):
    __log__.info('Group mode.')
    process_external = False
    limit = 0

    if opisvalid and len(args) > 0:
        group_id = args[0]
        limit = int(args[1])
        if args[2].lower() == 'y':
            process_external = True
    else:
        group_id = raw_input("Group Id: ")
        limit = int(raw_input("Limit: "))
        arg = raw_input("Process External Image [y/n]: ") or 'n'
        arg = arg.lower()
        if arg == 'y':
            process_external = True

    process_from_group(mode, group_id, limit, process_external)


def menu_export_online_bookmark(mode, opisvalid, args):
    __log__.info('Export Bookmark mode.')
    hide = False
    filename = raw_input("Filename: ")
    arg = raw_input("Include Private bookmarks [y/n/o]: ") or 'n'
    arg = arg.lower()
    if arg == 'y' or arg == 'n' or arg == 'o':
        hide = arg
    else:
        print "Invalid args: ", arg
    export_bookmark(filename, hide)


def menu_reload_config():
    __log__.info('Manual Reload Config.')
    __config__.loadConfig(path=configfile)


def menu_print_config():
    __log__.info('Manual Reload Config.')
    __config__.printConfig()


def set_console_title(title=''):
    set_title = 'PixivDownloader {0} {1}'.format(PixivConstant.PIXIVUTIL_VERSION, title)
    PixivHelper.setConsoleTitle(set_title)


def setup_option_parser():
    parser = OptionParser()
    parser.add_option('-s', '--startaction', dest='startaction',
                      help='Action you want to load your program with:            ' +
                            '1 - Download by member_id                              ' +
                            '2 - Download by image_id                              ' +
                            '3 - Download by tags                                    ' +
                            '4 - Download from list                                 ' +
                            '5 - Download from user bookmark                        ' +
                            '6 - Download from user\'s image bookmark               ' +
                            '7 - Download from tags list                           ' +
                            '8 - Download new illust from bookmark                  ' +
                            '9 - Download by Title/Caption                           ' +
                            '10 - Download by Tag and Member Id                     ' +
                            '11 - Download images from Member Bookmark               ' +
                            '12 - Download images by Group Id                        ' +
                            'e - Export online bookmark                              ' +
                            'd - Manage database')
    parser.add_option('-x', '--exitwhendone', dest='exitwhendone',
                      help='Exit programm when done. (only useful when not using DB-Manager)',
                      action='store_true', default=False)
    parser.add_option('-i', '--irfanview', dest='start_iv',
                      help='start IrfanView after downloading images using downloaded_on_%date%.txt',
                      action='store_true', default=False)
    parser.add_option('-n', '--numberofpages', dest='numberofpages',
                      help='temporarily overwrites numberOfPage set in config.ini')
    parser.add_option('-c', '--config', dest='configlocation',
                      help='load the config file from a custom location',
                      default=None)
    return parser


### Main thread ###
def main_loop(ewd, mode, op_is_valid, selection, np_is_valid, args):
    global __errorList
    while True:
        try:
            if len(__errorList) > 0:
                print "Unknown errors from previous operation"
                for err in __errorList:
                    message = err["type"] + ": " + str(err["id"]) + " ==> " + err["message"]
                    PixivHelper.printAndLog('error', message)
                __errorList = list()

            if op_is_valid:  # Yavos (next 3 lines): if commandline then use it
                selection = op
            else:
                selection = menu()

            if selection == '1':
                menu_download_by_member_id(mode, op_is_valid, args)
            elif selection == '2':
                menu_download_by_image_id(mode, op_is_valid, args)
            elif selection == '3':
                menu_download_by_tags(mode, op_is_valid, args)
            elif selection == '4':
                menu_download_from_list(mode, op_is_valid, args)
            elif selection == '5':
                menu_download_from_online_user_bookmark(mode, op_is_valid, args)
            elif selection == '6':
                menu_download_from_online_image_bookmark(mode, op_is_valid, args)
            elif selection == '7':
                menu_download_from_tags_list(mode, op_is_valid, args)
            elif selection == '8':
                menu_download_new_illust_from_bookmark(mode, op_is_valid, args)
            elif selection == '9':
                menu_download_by_title_caption(mode, op_is_valid, args)
            elif selection == '10':
                menu_download_by_tag_and_member_id(mode, op_is_valid, args)
            elif selection == '11':
                menu_download_by_member_bookmark(mode, op_is_valid, args)
            elif selection == '12':
                menu_download_by_group_id(mode, op_is_valid, args)
            elif selection == 'e':
                menu_export_online_bookmark(mode, op_is_valid, args)
            elif selection == 'd':
                __dbManager__.main()
            elif selection == 'r':
                menu_reload_config()
            elif selection == 'p':
                menu_print_config()
            elif selection == '-all':
                if not np_is_valid:
                    np_is_valid = True
                    np = 0
                    print 'download all mode activated'
                else:
                    np_is_valid = False
                    print 'download mode reset to', __config__.numberOfPage, 'pages'
            elif selection == 'x':
                break

            if ewd:  # Yavos: added lines for "exit when done"
                break
            op_is_valid = False  # Yavos: needed to prevent endless loop
        except KeyboardInterrupt:
            PixivHelper.printAndLog("info", "Keyboard Interrupt pressed, selection: " + selection)
            PixivHelper.clearScreen()
            print "Restarting..."
            selection = menu()
    return np_is_valid, op_is_valid, selection


def main():
    set_console_title()
    header()

    ## Option Parser
    global np_is_valid  # used in process image bookmark
    global np  # used in various places for number of page overwriting
    global start_iv  # used in download_image
    global op
    global __br__
    global configfile

    parser = setup_option_parser()
    (options, args) = parser.parse_args()

    op = options.startaction
    if op in ('1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', 'd', 'e'):
        op_is_valid = True
    elif op is None:
        op_is_valid = False
    else:
        op_is_valid = False
        parser.error('%s is not valid operation' % op)
        # Yavos: use print option instead when program should be running even with this error

    ewd = options.exitwhendone
    configfile = options.configlocation

    try:
        if options.numberofpages is not None:
            np = int(options.numberofpages)
            np_is_valid = True
        else:
            np_is_valid = False
    except:
        np_is_valid = False
        parser.error('Value %s used for numberOfPage is not an integer.' % options.numberofpages)
        # Yavos: use print option instead when program should be running even with this error
        ### end new lines by Yavos ###

    __log__.info('###############################################################')
    __log__.info('Starting...')
    try:
        __config__.loadConfig(path=configfile)
        PixivHelper.setConfig(__config__)
    except:
        print 'Failed to read configuration.'
        __log__.exception('Failed to read configuration.')

    PixivHelper.setLogLevel(__config__.logLevel)
    if __br__ is None:
        __br__ = PixivBrowserFactory.getBrowser(config=__config__)
    PixivBrowserFactory.configureBrowser(__br__, __config__)

    selection = None
    global dfilename

    #Yavos: adding File for downloadlist
    now = datetime.date.today()
    dfilename = __config__.downloadListDirectory + os.sep + 'Downloaded_on_' + now.strftime('%Y-%m-%d') + '.txt'
    if not re.match(r'[a-zA-Z]:', dfilename):
        dfilename = PixivHelper.toUnicode(sys.path[0], encoding=sys.stdin.encoding) + os.sep + dfilename
        #dfilename = sys.path[0].rsplit('\\',1)[0] + '\\' + dfilename #Yavos: only useful for myself
    dfilename = dfilename.replace('\\\\', '\\')
    dfilename = dfilename.replace('\\', os.sep)
    dfilename = dfilename.replace(os.sep + 'library.zip' + os.sep + '.', '')

    directory = os.path.dirname(dfilename)
    if not os.path.exists(directory):
        os.makedirs(directory)
        __log__.info('Creating directory: ' + directory)

    #Yavos: adding IrfanView-Handling
    start_irfan_slide = False
    start_irfan_view = False
    if __config__.startIrfanSlide or __config__.startIrfanView:
        start_iv = True
        start_irfan_slide = __config__.startIrfanSlide
        start_irfan_view = __config__.startIrfanView
    elif options.start_iv is not None:
        start_iv = options.start_iv
        start_irfan_view = True
        start_irfan_slide = False

    try:
        __dbManager__.createDatabase()

        if __config__.useList:
            list_txt = PixivListItem.parseList(__config__.downloadListDirectory + os.sep + 'list.txt')
            __dbManager__.importList(list_txt)
            print "Updated " + str(len(list_txt)) + " items."

        if __config__.overwrite:
            msg = 'Overwrite enabled.'
            print msg
            __log__.info(msg)

        if __config__.dayLastUpdated != 0 and __config__.processFromDb:
            PixivHelper.printAndLog('info',
                                    'Only process member where day last updated >= ' + str(__config__.dayLastUpdated))

        if __config__.dateDiff > 0:
            PixivHelper.printAndLog('info', 'Only process image where day last updated >= ' + str(__config__.dateDiff))

        if __config__.useBlacklistTags:
            global __blacklistTags
            __blacklistTags = PixivTags.parseTagsList("blacklist_tags.txt")
            PixivHelper.printAndLog('info', 'Using Blacklist Tags: ' + str(len(__blacklistTags)) + " items.")

        if __config__.useSuppressTags:
            global __suppressTags
            __suppressTags = PixivTags.parseTagsList("suppress_tags.txt")
            PixivHelper.printAndLog('info', 'Using Suppress Tags: ' + str(len(__suppressTags)) + " items.")

        username = __config__.username
        if username == '':
            username = raw_input('Username ? ')
        else:
            msg = 'Using Username: ' + username
            print msg
            __log__.info(msg)

        password = __config__.password
        if password == '':
            password = getpass.getpass('Password ? ')

        if np_is_valid and np != 0:  # Yavos: overwrite config-data
            msg = 'Limit up to: ' + str(np) + ' page(s). (set via commandline)'
            print msg
            __log__.info(msg)
        elif __config__.numberOfPage != 0:
            msg = 'Limit up to: ' + str(__config__.numberOfPage) + ' page(s).'
            print msg
            __log__.info(msg)

        ## Log in
        result = False
        if len(__config__.cookie) > 0:
            result = pixiv_login_cookie()

        if not result:
            if __config__.useSSL:
                result = pixiv_login_ssl(username, password)
            else:
                result = pixiv_login(username, password)

        if result:
            if __config__.overwrite:
                mode = PixivConstant.PIXIVUTIL_MODE_OVERWRITE
            else:
                mode = PixivConstant.PIXIVUTIL_MODE_UPDATE_ONLY

            np_is_valid, op_is_valid, selection = main_loop(ewd, mode, op_is_valid, selection, np_is_valid, args)

            if start_iv:  # Yavos: adding start_irfan_view-handling
                PixivHelper.startIrfanView(dfilename, __config__.IrfanViewPath, start_irfan_slide, start_irfan_view)
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        __log__.exception('Unknown Error: ' + str(exc_value))
    finally:
        __dbManager__.close()
        if not ewd:  # Yavos: prevent input on exitwhendone
            if selection is None or selection != 'x':
                raw_input('press enter to exit.')
        __log__.setLevel("INFO")
        __log__.info('EXIT')
        __log__.info('###############################################################')


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = test.PixivDBManager
#!/c/Python27/python.exe
# -*- coding: UTF-8 -*-

from PixivDBManager import PixivDBManager
from PixivModel import PixivListItem
from PixivConfig import PixivConfig

import unittest
LIST_SIZE = 4
config = PixivConfig()
config.loadConfig()

class TestPixivDBManager(unittest.TestCase):
    def testImportListTxt(self):
        DB = PixivDBManager(target = "test.db.sqlite")
        DB.createDatabase()
        l = PixivListItem.parseList("test.list.txt", config.rootDirectory)
        result = DB.importList(l)
        self.assertEqual(result, 0)

    def testSelectMembersByLastDownloadDate(self):
        DB = PixivDBManager(target = "test.db.sqlite")
        DB.createDatabase()
        l = PixivListItem.parseList("test.list.txt", config.rootDirectory)
        result = DB.selectMembersByLastDownloadDate(7)
        self.assertEqual(len(result), LIST_SIZE)
        for item in result:
            print item.memberId, item.path

    def testSelectAllMember(self):
        DB = PixivDBManager(target = "test.db.sqlite")
        DB.createDatabase()
        l = PixivListItem.parseList("test.list.txt", config.rootDirectory)
        result = DB.selectAllMember()
        self.assertEqual(len(result), LIST_SIZE)
        for item in result:
            print item.memberId, item.path

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivDBManager)
    unittest.TextTestRunner(verbosity=5).run(suite)
    print "================================================================"


########NEW FILE########
__FILENAME__ = test.PixivHelper
#!/c/Python27/python.exe
# -*- coding: UTF-8 -*-
import PixivHelper
import os
import unittest
from PixivModel import PixivImage, PixivArtist
from BeautifulSoup import BeautifulSoup

class TestPixivHelper(unittest.TestCase):
  currPath = unicode(os.path.abspath('.'))
  PixivHelper.GetLogger()

  def testSanitizeFilename(self):
    rootDir = '.'
    filename = u'12345.jpg'
    currentDir = os.path.abspath('.')
    expected = currentDir + os.sep + filename

    result = PixivHelper.sanitizeFilename(filename, rootDir)

    self.assertEqual(result, expected)
    self.assertTrue(len(result) < 255)

  def testSanitizeFilename2(self):
    rootDir = '.'
    filename = u'12345.jpg'
    currentDir = os.path.abspath('.')
    expected = currentDir + os.sep + filename

    result = PixivHelper.sanitizeFilename(filename, rootDir)

    self.assertEqual(result, expected)
    self.assertTrue(len(result) < 255)

  def testCreateMangaFilename(self):
    p = open('./test/test-image-manga.htm', 'r')
    page = BeautifulSoup(p.read())
    imageInfo = PixivImage(28820443, page)
    imageInfo.imageCount = 100
    page.decompose()
    del page
    ##print imageInfo.PrintInfo()
    nameFormat = '%member_token% (%member_id%)\%urlFilename% %page_number% %works_date_only% %works_res% %works_tools% %title%'

    expected = unicode(u'ffei (554800)\\28865189_p0 001 7-23-2012 Manga 2P Photoshop C82おまけ本 「沙耶は俺の嫁」サンプル.jpg')
    result = PixivHelper.makeFilename(nameFormat, imageInfo, artistInfo=None, tagsSeparator=' ', fileUrl='http://i2.pixiv.net/img26/img/ffei/28865189_p0.jpg')
    ##print result
    self.assertEqual(result, expected)

    expected = unicode(u'ffei (554800)\\28865189_p14 015 7-23-2012 Manga 2P Photoshop C82おまけ本 「沙耶は俺の嫁」サンプル.jpg')
    result = PixivHelper.makeFilename(nameFormat, imageInfo, artistInfo=None, tagsSeparator=' ', fileUrl='http://i2.pixiv.net/img26/img/ffei/28865189_p14.jpg')
    ##print result
    self.assertEqual(result, expected)

    expected = unicode(u'ffei (554800)\\28865189_p921 922 7-23-2012 Manga 2P Photoshop C82おまけ本 「沙耶は俺の嫁」サンプル.jpg')
    result = PixivHelper.makeFilename(nameFormat, imageInfo, artistInfo=None, tagsSeparator=' ', fileUrl='http://i2.pixiv.net/img26/img/ffei/28865189_p921.jpg')
    ##print result
    self.assertEqual(result, expected)

  def testCreateFilenameUnicode(self):
    p = open('./test/test-image-unicode.htm', 'r')
    page = BeautifulSoup(p.read())
    imageInfo = PixivImage(2493913, page)
    page.decompose()
    del page

    nameFormat = '%member_token% (%member_id%)\%urlFilename% %works_date_only% %works_res% %works_tools% %title%'
    expected = unicode(u'balzehn (267014)\\2493913 12-23-2008 852x1200 Photoshop SAI つけペン アラクネのいる日常２.jpg')
    result = PixivHelper.makeFilename(nameFormat, imageInfo, artistInfo=None, tagsSeparator=' ', fileUrl='http://i2.pixiv.net/img16/img/balzehn/2493913.jpg')
    ##print result
    self.assertEqual(result, expected)

  def testCreateAvatarFilenameFormatNoSubfolderNoRootDir(self):
    p = open('./test/test-helper-avatar-name.htm', 'r')
    page = BeautifulSoup(p.read())
    artist = PixivArtist(mid=1107124, page=page)
    filenameFormat = '%image_id% - %title%'
    tagsSeparator = ' '
    tagsLimit = 0
    targetDir = ''
    filename = PixivHelper.CreateAvatarFilename(filenameFormat, tagsSeparator, tagsLimit, artist, targetDir)
    ##print filename
    self.assertEqual(filename, self.currPath + os.sep + u'folder.jpg')

  def testCreateAvatarFilenameFormatWithSubfolderNoRootDir(self):
    p = open('./test/test-helper-avatar-name.htm', 'r')
    page = BeautifulSoup(p.read())
    artist = PixivArtist(mid=1107124, page=page)
    filenameFormat = '%member_token% (%member_id%)\%R-18%\%image_id% - %title% - %tags%'
    tagsSeparator = ' '
    tagsLimit = 0
    targetDir = ''
    filename = PixivHelper.CreateAvatarFilename(filenameFormat, tagsSeparator, tagsLimit, artist, targetDir)
    ##print filename
    self.assertEqual(filename, self.currPath + os.sep + u'kirabara29 (1107124)\\folder.jpg')

  def testCreateAvatarFilenameFormatNoSubfolderWithRootDir(self):
    p = open('./test/test-helper-avatar-name.htm', 'r')
    page = BeautifulSoup(p.read())
    artist = PixivArtist(mid=1107124, page=page)
    filenameFormat = '%image_id% - %title%'
    tagsSeparator = ' '
    tagsLimit = 0
    targetDir = os.path.abspath('.')
    filename = PixivHelper.CreateAvatarFilename(filenameFormat, tagsSeparator, tagsLimit, artist, targetDir)
    ##print filename
    self.assertEqual(filename, targetDir + os.sep + u'folder.jpg')

  def testCreateAvatarFilenameFormatWithSubfolderWithRootDir(self):
    p = open('./test/test-helper-avatar-name.htm', 'r')
    page = BeautifulSoup(p.read())
    artist = PixivArtist(mid=1107124, page=page)
    filenameFormat = '%member_token% (%member_id%)\%R-18%\%image_id% - %title% - %tags%'
    tagsSeparator = ' '
    tagsLimit = 0
    targetDir = os.path.abspath('.')
    filename = PixivHelper.CreateAvatarFilename(filenameFormat, tagsSeparator, tagsLimit, artist, targetDir)
    ##print filename
    self.assertEqual(filename, targetDir + os.sep + u'kirabara29 (1107124)\\folder.jpg')

  def testCreateAvatarFilenameFormatNoSubfolderWithCustomRootDir(self):
    p = open('./test/test-helper-avatar-name.htm', 'r')
    page = BeautifulSoup(p.read())
    artist = PixivArtist(mid=1107124, page=page)
    filenameFormat = '%image_id% - %title%'
    tagsSeparator = ' '
    tagsLimit = 0
    targetDir = 'C:\\images'
    filename = PixivHelper.CreateAvatarFilename(filenameFormat, tagsSeparator, tagsLimit, artist, targetDir)
    ##print filename
    self.assertEqual(filename, u'C:\\images\\folder.jpg')

  def testCreateAvatarFilenameFormatWithSubfolderWithCustomRootDir(self):
    p = open('./test/test-helper-avatar-name.htm', 'r')
    page = BeautifulSoup(p.read())
    artist = PixivArtist(mid=1107124, page=page)
    filenameFormat = '%member_token% (%member_id%)\%R-18%\%image_id% - %title% - %tags%'
    tagsSeparator = ' '
    tagsLimit = 0
    targetDir = 'C:\\images'
    filename = PixivHelper.CreateAvatarFilename(filenameFormat, tagsSeparator, tagsLimit, artist, targetDir)
    ##print filename
    self.assertEqual(filename, u'C:\\images\\kirabara29 (1107124)\\folder.jpg')

  def testParseLoginError(self):
    p = open('./test/test-login-error.htm', 'r')
    page = BeautifulSoup(p.read())
    r = page.findAll('span', attrs={'class':'error'})
    self.assertTrue(len(r)>0)
    self.assertEqual(u'Please ensure your pixiv ID, email address and password is entered correctly.', r[0].string)

if __name__ == '__main__':
    #unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivHelper)
    unittest.TextTestRunner(verbosity=5).run(suite)

########NEW FILE########
__FILENAME__ = test.PixivModel
﻿#!/c/Python27/python.exe
# -*- coding: UTF-8 -*-
from PixivModel import PixivArtist, PixivImage, PixivBookmark,PixivNewIllustBookmark, PixivTags, PixivGroup
from PixivException import PixivException
from BeautifulSoup import BeautifulSoup
from mechanize import Browser
import os
import unittest

class TestPixivArtist(unittest.TestCase):
    def testPixivArtistProfileDataSrc(self):
      #print '\nTesting member page ProfileDataSrc'
      p = open('./test/test-helper-avatar-name.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
        artist = PixivArtist(1107124, page)
      except PixivException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(artist, None)
      self.assertEqual(artist.artistId, 1107124)
      self.assertEqual(artist.artistToken, 'kirabara29')

    def testPixivArtistNoImage(self):
      #print '\nTesting member page - no image'
      p = open('./test/test-noimage.htm', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivException):
          PixivArtist(1233, page)
      page.decompose()
      del page

    def testPixivArtistNoMember(self):
      #print '\nTesting member page - no member'
      p = open('./test/test-nouser.htm', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivException):
          PixivArtist(1, page)
      page.decompose()
      del page

    def testPixivArtistNoAvatar(self):
      #print '\nTesting member page without avatar image'
      p = open('./test/test-member-noavatar.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
        artist = PixivArtist(26357, page)
        #artist.PrintInfo()
      except PixivException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(artist, None)
      self.assertEqual(artist.artistId, 26357)
      self.assertEqual(artist.artistToken, 'yukimaruko')

    def testPixivArtistSuspended(self):
      #print '\nTesting member page - suspended member'
      p = open('./test/test-member-suspended.htm', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivException) as ex:
          PixivArtist(123, page)
      self.assertEqual(ex.exception.errorCode, 1002)
      page.decompose()
      del page

    def testPixivArtistNotLoggedIn(self):
      p = open('./test/test-member-nologin.htm', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivException) as ex:
          PixivArtist(143229, page)
      self.assertEqual(ex.exception.errorCode, 100)
      page.decompose()
      del page

    def testPixivArtistBookmark(self):
      #print '\nTesting member page'
      p = open('./test/test-member-bookmark.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
        artist = PixivArtist(3281699, page)
        #artist.PrintInfo()
      except PixivException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(artist, None)
      self.assertEqual(artist.artistId, 3281699)

    def testPixivArtistServerError(self):
      #print '\nTesting member page'
      p = open('./test/test-server-error.html', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivException) as ex:
        artist = PixivArtist(234753, page)
      self.assertEqual(ex.exception.errorCode, PixivException.SERVER_ERROR)
      page.decompose()
      del page

class TestPixivImage(unittest.TestCase):
    def testPixivImageParseInfo(self):
      p = open('./test/test-image-info.html', 'r')
      page = BeautifulSoup(p.read())
      image2 = PixivImage(32039274, page)
      page.decompose()
      del page

      self.assertEqual(image2.imageId, 32039274)
      self.assertEqual(image2.imageTitle, u"新しいお姫様")

      self.assertTrue(u'MAYU' in image2.imageTags)
      self.assertTrue(u'VOCALOID' in image2.imageTags)
      self.assertTrue(u'VOCALOID3' in image2.imageTags)
      self.assertTrue(u'うさぎになりたい' in image2.imageTags)
      self.assertTrue(u'なにこれかわいい' in image2.imageTags)
      self.assertTrue(u'やはり存在する斧' in image2.imageTags)
      self.assertTrue(u'ヤンデレ' in image2.imageTags)
      self.assertTrue(u'吸いこまれそうな瞳の色' in image2.imageTags)

      self.assertEqual(image2.imageMode, "big")
      self.assertEqual(image2.worksDate,'12-11-2012 00:23')
      self.assertEqual(image2.worksResolution,'642x900')
      self.assertEqual(image2.worksTools, 'Photoshop SAI')
      #self.assertEqual(image2.jd_rtv, 88190)
      #self.assertEqual(image2.jd_rtc, 6711)
      #self.assertEqual(image2.jd_rtt, 66470)
      self.assertEqual(image2.artist.artistToken, 'nardack')

    def testPixivImageParseInfoJa(self):
      p = open('./test/test-image-parse-image-40273739-ja.html', 'r')
      page = BeautifulSoup(p.read())
      image2 = PixivImage(40273739, page)
      page.decompose()
      del page

      self.assertEqual(image2.imageId, 40273739)
      self.assertEqual(image2.imageTitle, u"Cos-Nurse")

      self.assertTrue(u'東方' in image2.imageTags)
      self.assertTrue(u'幽々子' in image2.imageTags)
      self.assertTrue(u'むちむち' in image2.imageTags)
      self.assertTrue(u'おっぱい' in image2.imageTags)
      self.assertTrue(u'尻' in image2.imageTags)
      self.assertTrue(u'東方グラマラス' in image2.imageTags)
      self.assertTrue(u'誰だお前' in image2.imageTags)

      self.assertEqual(image2.imageMode, "big")
      self.assertEqual(image2.worksDate,u"2013年12月14日 19:00")
      self.assertEqual(image2.worksResolution,'855x1133')
      self.assertEqual(image2.worksTools, 'Photoshop SAI')
      self.assertEqual(image2.artist.artistToken, 'k2321656')

    def testPixivImageParseInfoPixivPremiumOffer(self):
      p = open('./test/test-image-parse-image-38826533-pixiv-premium.html', 'r')
      page = BeautifulSoup(p.read())
      image2 = PixivImage(38826533, page)
      page.decompose()
      del page

      self.assertEqual(image2.imageId, 38826533)
      self.assertEqual(image2.imageTitle, u"てやり")
      self.assertEqual(image2.imageCaption, u'一応シーダ様です。')

      self.assertTrue(u'R-18' in image2.imageTags)
      self.assertTrue(u'FE' in image2.imageTags)
      self.assertTrue(u'ファイアーエムブレム' in image2.imageTags)
      self.assertTrue(u'シーダ' in image2.imageTags)

      self.assertEqual(image2.imageMode, "big")
      self.assertEqual(image2.worksDate,'9-30-2013 01:43')
      self.assertEqual(image2.worksResolution,'1000x2317')
      self.assertEqual(image2.worksTools, 'CLIP STUDIO PAINT')
      #self.assertEqual(image2.jd_rtv, 88190)
      #self.assertEqual(image2.jd_rtc, 6711)
      #self.assertEqual(image2.jd_rtt, 66470)
      self.assertEqual(image2.artist.artistToken, 'hvcv')

    def testPixivImageNoAvatar(self):
      #print '\nTesting artist page without avatar image'
      p = open('./test/test-image-noavatar.htm', 'r')
      page = BeautifulSoup(p.read())
      image = PixivImage(20496355, page)
      page.decompose()
      del page
      ##self.assertNotEqual(image, None)
      self.assertEqual(image.artist.artistToken, 'iymt')
      self.assertEqual(image.imageId, 20496355)
      #07/22/2011 03:09｜512×600｜RETAS STUDIO&nbsp;
      #print image.worksDate, image.worksResolution, image.worksTools
      self.assertEqual(image.worksDate,'7-22-2011 03:09')
      self.assertEqual(image.worksResolution,'512x600')
      self.assertEqual(image.worksTools,'RETAS STUDIO')

    def testPixivImageParseTags(self):
      p = open('./test/test-image-parse-tags.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
        image = PixivImage(11164869, page)
      except PixivException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(image, None)
      self.assertEqual(image.imageId, 11164869)
      self.assertEqual(image.worksDate,'6-9-2010 02:33')
      self.assertEqual(image.worksResolution,'1009x683')
      self.assertEqual(image.worksTools,u'SAI')
      ##print image.imageTags
      joinedResult = " ".join(image.imageTags)
      self.assertEqual(joinedResult.find("VOCALOID") > -1, True)

    def testPixivImageParseNoTags(self):
      p = open('./test/test-image-no_tags.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
        image = PixivImage(9175987, page)
      except PixivException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(image, None)
      self.assertEqual(image.imageId, 9175987)
      self.assertEqual(image.worksDate,'3-6-2010 03:04')
      self.assertEqual(image.worksResolution,'1155x768')
      self.assertEqual(image.worksTools,u'SAI')
      self.assertEqual(image.imageTags,[])

    def testPixivImageUnicode(self):
      #print '\nTesting image page - big'
      p = open('./test/test-image-unicode.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
        image = PixivImage(2493913, page)
        #image.PrintInfo()
      except PixivException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(image, None)
      self.assertEqual(image.imageId, 2493913)
      self.assertEqual(image.imageMode, 'big')
      self.assertEqual(image.worksDate,'12-23-2008 21:01')
      self.assertEqual(image.worksResolution,'852x1200')
      #print image.worksTools
      self.assertEqual(image.worksTools,u'Photoshop SAI つけペン')

    def testPixivImageRateCount(self):
      p = open('./test/test-image-rate_count.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
        image = PixivImage(28865189, page)
        #image.PrintInfo()
      except PixivException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(image, None)
      self.assertEqual(image.imageId, 28865189)
      self.assertEqual(image.imageMode, 'manga')
      self.assertTrue(image.jd_rtv > 0)
      self.assertTrue(image.jd_rtc > 0)
      self.assertTrue(image.jd_rtt > 0)
      self.assertEqual(image.worksTools, "Photoshop")

    def testPixivImageNoImage(self):
      #print '\nTesting image page - no image'
      p = open('./test/test-image-noimage.htm', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivException):
          PixivImage(123, page)
      page.decompose()
      del page

    def testPixivImageNoImageEng(self):
      #print '\nTesting image page - no image'
      p = open('./test/test-image-noimage-eng.htm', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivException):
          PixivImage(123, page)
      page.decompose()
      del page

    def testPixivImageModeManga(self):
      #print '\nTesting image page - manga'
      p = open('./test/test-image-manga.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
        image = PixivImage(28820443, page)
        #image.PrintInfo()
      except PixivException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(image, None)
      self.assertEqual(image.imageId, 28820443)
      self.assertEqual(image.imageMode, 'manga')

    def testPixivImageParseBig(self):
      #print '\nTesting parse Big Image'
      p = open('./test/test-image-parsebig.htm', 'r')
      page = BeautifulSoup(p.read())
      image = PixivImage()
      urls = image.ParseImages(page, mode='big')
      self.assertEqual(len(urls), 1)
      imageId = urls[0].split('/')[-1].split('.')[0]
      #print 'imageId:',imageId
      self.assertEqual(int(imageId), 20644633)

    def testPixivImageParseManga(self):
      #print '\nTesting parse Manga Images'
      p = open('./test/test-image-parsemanga.htm', 'r')
      page = BeautifulSoup(p.read())
      image = PixivImage()
      urls = image.ParseImages(page, mode='manga')
      #print urls
      self.assertEqual(len(urls), 39*2)
      imageId = urls[0].split('/')[-1].split('.')[0]
      #print 'imageId:',imageId
      self.assertEqual(imageId, '20592252_big_p0')

    def testPixivImageNoLogin(self):
      #print '\nTesting not logged in'
      p = open('./test/test-image-nologin.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
          image = PixivImage(9138317, page)
          self.assertRaises(PixivException)
      except PixivException as ex:
          self.assertEqual(ex.errorCode, PixivException.NOT_LOGGED_IN)

    def testPixivImageServerError(self):
      #print '\nTesting image page'
      p = open('./test/test-server-error.html', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivException) as ex:
        image = PixivImage(9138317, page)
      self.assertEqual(ex.exception.errorCode, PixivException.SERVER_ERROR)
      page.decompose()
      del page

    def testPixivImageServerError2(self):
      #print '\nTesting image page'
      p = open('./test/test-image-generic-error.html', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivException) as ex:
        image = PixivImage(37882549, page)
      self.assertEqual(ex.exception.errorCode, PixivException.SERVER_ERROR)
      page.decompose()
      del page

class TestPixivBookmark(unittest.TestCase):
    def testPixivBookmarkNewIlust(self):
      #print '\nTesting BookmarkNewIlust'
      p = open('./test/test-bookmarks_new_ilust.htm', 'r')
      page = BeautifulSoup(p.read())
      result = PixivNewIllustBookmark(page)

      self.assertEqual(len(result.imageList), 20)

    def testPixivImageBookmark(self):
      #print '\nTesting PixivImageBookmark'
      p = open('./test/test-image-bookmark.htm', 'r')
      page = BeautifulSoup(p.read())
      result = PixivBookmark.parseImageBookmark(page)

      self.assertEqual(len(result), 19)
      self.assertTrue(35303260 in result)
      self.assertTrue(28629066 in result)
      self.assertTrue(27249307 in result)
      self.assertTrue(30119925 in result)

class TestMyPickPage(unittest.TestCase):
    def testMyPickPage(self):
        try:
            br = Browser()
            path = 'file:///' + os.path.abspath('./test/test-image-my_pick.html').replace(os.sep,'/')
            p = br.open(path, 'r')
            page = BeautifulSoup(p.read())
            image = PixivImage(12467674,page)

            self.assertRaises(PixivException)
        except PixivException as ex:
            self.assertEqual(ex.errorCode, 2002)

    def testMyPickPageEng(self):
        try:
            br = Browser()
            path = 'file:///' + os.path.abspath('./test/test-image-my_pick-e.html').replace(os.sep,'/')
            p = br.open(path, 'r')
            page = BeautifulSoup(p.read())
            image = PixivImage(28688383,page)

            self.assertRaises(PixivException)
        except PixivException as ex:
            self.assertEqual(ex.errorCode, 2002)

    def testGuroPageEng(self):
        try:
            br = Browser()
            path = 'file:///' + os.path.abspath('./test/test-image-guro-e.html').replace(os.sep,'/')
            p = br.open(path, 'r')
            page = BeautifulSoup(p.read())
            image = PixivImage(31111130,page)

            self.assertRaises(PixivException)
        except PixivException as ex:
            self.assertEqual(ex.errorCode, 2005)

    def testEroPageEng(self):
        try:
            br = Browser()
            path = 'file:///' + os.path.abspath('./test/test-image-ero-e.html').replace(os.sep,'/')
            p = br.open(path, 'r')
            page = BeautifulSoup(p.read())
            image = PixivImage(31115956,page)

            self.assertRaises(PixivException)
        except PixivException as ex:
            self.assertEqual(ex.errorCode, 2005)


class TestPixivTags(unittest.TestCase):
    ## tags.php?tag=%E3%81%93%E3%81%AE%E4%B8%AD%E3%81%AB1%E4%BA%BA%E3%80%81%E5%A6%B9%E3%81%8C%E3%81%84%E3%82%8B%21
    def testTagsSearchExact(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-search-exact.htm').replace(os.sep,'/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)

        self.assertEqual(len(image.itemList), 20)
        self.assertEqual(image.isLastPage, False)

    def testTagsSearchExactLast(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-search-exact-last.htm').replace(os.sep,'/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)

        ##self.assertEqual(len(image.itemList), 3)
        self.assertEqual(image.itemList[-1].imageId, 15060554)
        self.assertEqual(image.isLastPage, True)

    ## search.php?s_mode=s_tag&word=%E5%88%9D%E6%98%A5%E9%A3%BE%E5%88%A9
    def testTagsSearchPartial(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-search-partial.htm').replace(os.sep,'/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)

        self.assertEqual(len(image.itemList), 20)
        self.assertEqual(image.isLastPage, False)

    def testTagsSearchPartialLast(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-search-partial-last.htm').replace(os.sep,'/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)

        self.assertEqual(image.itemList[-1].imageId, 15060554)
        self.assertEqual(image.isLastPage, True)

    def testTagsSearchParseDetails(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-search-exact-parse_details.htm').replace(os.sep,'/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)

        ##self.assertEqual(len(image.itemList), 20)
        self.assertEqual(image.itemList[-1].imageId, 33815932)
        self.assertEqual(image.itemList[-1].bookmarkCount, 4)
        self.assertEqual(image.itemList[-1].imageResponse, -1)

    def testTagsMemberSearch(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-member-search.htm').replace(os.sep,'/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseMemberTags(page)

        self.assertEqual(len(image.itemList), 20)
        self.assertEqual(image.itemList[0].imageId, 25757869)
        self.assertEqual(image.itemList[19].imageId, 14818847)
        self.assertEqual(image.isLastPage, False)

    def testTagsMemberSearchLast(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-member-search-last.htm').replace(os.sep,'/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseMemberTags(page)

        ##self.assertEqual(len(image.itemList), 10)
        self.assertEqual(image.itemList[-1].imageId, 1804545)
        self.assertEqual(image.isLastPage, True)

    def testTagsSkipShowcase(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-search-skip-showcase.htm').replace(os.sep,'/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)

        self.assertEqual(len(image.itemList), 20)

class TestPixivGroup(unittest.TestCase):
    def testParseJson(self):
        path = os.path.abspath('./test/group.json').replace(os.sep,'/')
        p = open(path)
        result = PixivGroup(p)

        self.assertEqual(len(result.imageList), 34)
        self.assertEqual(len(result.externalImageList), 2)
        self.assertEqual(result.maxId, 626288)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivArtist)
    unittest.TextTestRunner(verbosity=5).run(suite)
    print "================================================================"
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivImage)
    unittest.TextTestRunner(verbosity=5).run(suite)
    print "================================================================"
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivBookmark)
    unittest.TextTestRunner(verbosity=5).run(suite)
    print "================================================================"
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMyPickPage)
    unittest.TextTestRunner(verbosity=5).run(suite)
    print "================================================================"
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivTags)
    unittest.TextTestRunner(verbosity=5).run(suite)
    print "================================================================"
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivGroup)
    unittest.TextTestRunner(verbosity=5).run(suite)


########NEW FILE########
__FILENAME__ = test.updateHtml
# -*- coding: UTF-8 -*-
import PixivUtil2
import PixivBrowserFactory
import PixivConfig
import getpass

__config__    = PixivConfig.PixivConfig()
__config__.loadConfig()
__br__ = PixivUtil2.__br__ = PixivBrowserFactory.getBrowser(config=__config__)

def prepare():
    ## Log in
    username = __config__.username
    if username == '':
        username = raw_input('Username ? ')
    password = __config__.password
    if password == '':
        password = getpass.getpass('Password ? ')

    result = False
    if len(__config__.cookie) > 0:
        result = PixivUtil2.pixiv_login_cookie()

    if not result:
        if __config__.useSSL:
            result = PixivUtil2.pixiv_login_ssl(username,password)
        else:
            result = PixivUtil2.pixiv_login(username,password)

    return result

def downloadPage(url, filename):
    print "Dumping " + url + " to " + filename
    html = __br__.open(url).read()
    try:
        dump = file(filename, 'wb')
        dump.write(html)
        dump.close()
    except :
        pass

def main():
    result = prepare()
    if result:
        ## ./test/test-image-manga.htm
        ## http://www.pixiv.net/member_illust.php?mode=medium&illust_id=28820443
        downloadPage('http://www.pixiv.net/member_illust.php?mode=medium&illust_id=28820443', './test/test-image-manga.htm')

        ## ./test/test-image-unicode.htm
        ## http://www.pixiv.net/member_illust.php?mode=medium&illust_id=2493913
        downloadPage('http://www.pixiv.net/member_illust.php?mode=medium&illust_id=2493913', './test/test-image-unicode.htm')

        ## ./test/test-helper-avatar-name.htm
        ## http://www.pixiv.net/member_illust.php?id=1107124
        downloadPage('http://www.pixiv.net/member_illust.php?id=1107124', './test/test-helper-avatar-name.htm')

        downloadPage('http://www.pixiv.net/member_illust.php?id=1', './test/test-nouser.htm')
        downloadPage('http://www.pixiv.net/member_illust.php?id=26357', './test/test-member-noavatar.htm')
        downloadPage('http://www.pixiv.net/member_illust.php?id=1233', './test/test-noimage.htm')
        downloadPage('http://www.pixiv.net/bookmark.php?id=3281699', './test/test-member-bookmark.htm')

        downloadPage('http://www.pixiv.net/member_illust.php?mode=medium&illust_id=32039274', './test/test-image-info.html')
        downloadPage('http://www.pixiv.net/bookmark_new_illust.php', './test/test-bookmarks_new_ilust.htm')
        downloadPage('http://www.pixiv.net/member_illust.php?mode=medium&illust_id=12467674', './test/test-image-my_pick.html')
        downloadPage('http://www.pixiv.net/member_illust.php?mode=medium&illust_id=20496355', './test/test-image-noavatar.htm')
        downloadPage('http://www.pixiv.net/member_illust.php?mode=medium&illust_id=11164869', './test/test-image-parse-tags.htm')
        downloadPage('http://www.pixiv.net/member_illust.php?mode=medium&illust_id=9175987', './test/test-image-no_tags.htm')
        downloadPage('http://www.pixiv.net/member_illust.php?mode=medium&illust_id=28865189', './test/test-image-rate_count.htm')
        ## downloadPage('http://www.pixiv.net/member_illust.php?mode=big&illust_id=20644633', './test/test-image-parsebig.htm')
        downloadPage('http://www.pixiv.net/member_illust.php?mode=manga&illust_id=20592252', './test/test-image-parsemanga.htm')
        downloadPage('http://www.pixiv.net/bookmark.php', './test/test-image-bookmark.htm')

        downloadPage('http://www.pixiv.net/member_illust.php?id=313631&p=4', './test/test-tags-member-search-last.htm')
        downloadPage('http://www.pixiv.net/search.php?word=%E5%88%9D%E6%98%A5%E9%A3%BE%E5%88%A9&s_mode=s_tag_full', './test/test-tags-search-exact.htm')
        downloadPage('http://www.pixiv.net/search.php?word=%E3%81%93%E3%81%AE%E4%B8%AD%E3%81%AB1%E4%BA%BA%E3%80%81%E5%A6%B9%E3%81%8C%E3%81%84%E3%82%8B!&s_mode=s_tag_full&order=date_d&p=12', './test/test-tags-search-partial.htm')
        downloadPage('http://www.pixiv.net/search.php?s_mode=s_tag_full&word=XXXXXX','./test/test-tags-search-exact-parse_details.htm')
        downloadPage('http://www.pixiv.net/search.php?s_mode=s_tag&word=%E3%81%93%E3%81%AE%E4%B8%AD%E3%81%AB1%E4%BA%BA%E3%80%81%E5%A6%B9%E3%81%8C%E3%81%84%E3%82%8B!','./test/test-tags-search-partial.htm')
        downloadPage('http://www.pixiv.net/search.php?word=%E3%81%93%E3%81%AE%E4%B8%AD%E3%81%AB1%E4%BA%BA%E3%80%81%E5%A6%B9%E3%81%8C%E3%81%84%E3%82%8B!&order=date_d&p=12','./test/test-tags-search-partial-last.htm')

        downloadPage('http://www.pixiv.net/search.php?s_mode=s_tag&word=R-18%20K-On!','./test/test-tags-search-skip-showcase.htm')
        ## Not updated:
        ## ./test/test-login-error.htm
        ## ./test/test-member-suspended.htm
        ## ./test/test-member-nologin.htm

if __name__ == '__main__':
    main()

########NEW FILE########
