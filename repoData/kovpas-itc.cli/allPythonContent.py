__FILENAME__ = conf
import os
from tempfile import gettempdir
from cookielib import LWPCookieJar

ITUNESCONNECT_URL = 'https://itunesconnect.apple.com'
ITUNESCONNECT_MAIN_PAGE_URL = '/WebObjects/iTunesConnect.woa'
KEYRING_SERVICE_NAME = 'itc.cli'

class DEVICE_TYPE:
    iPad = 0
    iPhone = 1
    iPhone5 = 2
    deviceStrings = ['iPad', 'iPhone', 'iPhone 5']

temp_dir = gettempdir()
default_file_format = 'images/{language}/{device_type} {index}.png'
cookie_file_name = '.itc-cli-cookies.txt'
cookie_file = os.path.join(temp_dir, cookie_file_name)
cookie_jar = LWPCookieJar(cookie_file)

class ALIASES:
    language_aliases = {}
    device_type_aliases = {}

class config:
    options = {}

def __initCookies():
    if cookie_file:
        try:
            cookie_jar.load(cookie_file, ignore_discard=True)
        except IOError:
            pass

__initCookies()
########NEW FILE########
__FILENAME__ = application
# encoding: utf-8

import os
import re
import json
import logging
import sys
import codecs
from datetime import datetime, timedelta

import requests

from itc.core.inapp import ITCInappPurchase
from itc.core.imageuploader import ITCImageUploader
from itc.parsers.applicationparser import ITCApplicationParser
from itc.util import languages
from itc.util import dataFromStringOrFile
from itc.util import EnhancedFile
from itc.util import getElement
from itc.conf import *

class ITCApplication(ITCImageUploader):
    def __init__(self, name=None, applicationId=None, link=None, dict=None):
        if (dict):
            name = dict['name']
            link = dict['applicationLink']
            applicationId = dict['applicationId']

        self.name = name
        self.applicationLink = link
        self.applicationId = applicationId
        self.versions = {}
        self.inapps = {}

        self._manageInappsLink = None
        self._customerReviewsLink = None
        self._addVersionLink = None
        self._manageInappsTree = None
        self._createInappLink = None
        self._inappActionURLs = None
        self._parser = ITCApplicationParser()

        logging.info('Application found: ' + self.__str__())
        super(ITCApplication, self).__init__()


    def __repr__(self):
        return self.__str__()


    def __str__(self):
        strng = ""
        if self.name != None:
            strng += "\"" + self.name + "\""
        if self.applicationId != None:
            strng += " (" + str(self.applicationId) + ")"

        return strng


    def getAppInfo(self):
        if self.applicationLink == None:
            raise 'Can\'t get application versions'

        tree = self._parser.parseTreeForURL(self.applicationLink)
        versionsMetadata = self._parser.parseAppVersionsPage(tree)
        # get 'manage in-app purchases' link
        self._manageInappsLink = versionsMetadata.manageInappsLink
        self._customerReviewsLink = versionsMetadata.customerReviewsLink
        self._addVersionLink = versionsMetadata.addVersionLink
        self.versions = versionsMetadata.versions


    def __parseAppVersionMetadata(self, version, language=None):
        tree = self._parser.parseTreeForURL(version['detailsLink'])

        return self._parser.parseCreateOrEditPage(tree, version, language)

    def __parseAppReviewInformation(self, version):
        tree = self._parser.parseTreeForURL(version['detailsLink'])

        return self._parser.parseAppReviewInfoForm(tree)

    def __generateConfigForVersion(self, version):
        languagesDict = {}

        metadata = self.__parseAppVersionMetadata(version)
        formData = metadata.formData
        # activatedLanguages = metadata.activatedLanguages

        for languageId, formValuesForLang in formData.items():
            langCode = languages.langCodeForLanguage(languageId)
            resultForLang = {}

            resultForLang["name"]               = formValuesForLang['appNameValue']
            resultForLang["description"]        = formValuesForLang['descriptionValue']
            resultForLang["whats new"]          = formValuesForLang.get('whatsNewValue')
            resultForLang["keywords"]           = formValuesForLang['keywordsValue']
            resultForLang["support url"]        = formValuesForLang['supportURLValue']
            resultForLang["marketing url"]      = formValuesForLang['marketingURLValue']
            resultForLang["privacy policy url"] = formValuesForLang['pPolicyURLValue']

            languagesDict[langCode] = resultForLang

        resultDict = {'config':{}, 'application': {'id': self.applicationId, 'metadata': {'general': {}, 'languages': languagesDict}}}

        return resultDict


    def generateConfig(self, versionString=None, generateInapps=False):
        if len(self.versions) == 0:
            self.getAppInfo()
        if len(self.versions) == 0:
            raise 'Can\'t get application versions'
        if versionString == None: # Suppose there's one or less editable versions
            versionString = next((versionString for versionString, version in self.versions.items() if version['editable']), None)
        if versionString == None: # No versions to edit. Generate config from the first one
            versionString = self.versions.keys()[0]

        if self.versions[versionString]['editable'] == False:
            logging.error("Can't generate config for non-editable version.")
            return
        
        resultDict = self.__generateConfigForVersion(self.versions[versionString])

        if generateInapps:
            if len(self.inapps) == 0:
                self.getInapps()

            inapps = []
            for inappId, inapp in self.inapps.items():
                inapps.append(inapp.generateConfig())

            if len(inapps) > 0:
                resultDict['inapps'] = inapps

        filename = str(self.applicationId) + '.json'
        with open(filename, 'wb') as fp:
            json.dump(resultDict, fp, sort_keys=False, indent=4, separators=(',', ': '))


    def editVersion(self, dataDict, lang=None, versionString=None, filename_format=None):
        if dataDict == None or len(dataDict) == 0: # nothing to change
            return

        if len(self.versions) == 0:
            self.getAppInfo()
        if len(self.versions) == 0:
            raise 'Can\'t get application versions'
        if versionString == None: # Suppose there's one or less editable versions
            versionString = next((versionString for versionString, version in self.versions.items() if version['editable']), None)
        if versionString == None: # Suppose there's one or less editable versions
            raise 'No editable version found'
            
        version = self.versions[versionString]
        if not version['editable']:
            raise 'Version ' + versionString + ' is not editable'

        languageId = languages.appleLangIdForLanguage(lang)
        languageCode = languages.langCodeForLanguage(lang)

        metadata = self.__parseAppVersionMetadata(version, lang)
        # activatedLanguages = metadata.activatedLanguages
        # nonactivatedLanguages = metadata.nonactivatedLanguages
        formData = {} #metadata.formData[languageId]
        formNames = metadata.formNames[languageId]
        submitAction = metadata.submitActions[languageId]
        
        formData["save"] = "true"

        formData[formNames['appNameName']]      = dataDict.get('name', metadata.formData[languageId]['appNameValue'])
        formData[formNames['descriptionName']]  = dataFromStringOrFile(dataDict.get('description', metadata.formData[languageId]['descriptionValue']), languageCode)
        if 'whatsNewName' in formNames:
            formData[formNames['whatsNewName']] = dataFromStringOrFile(dataDict.get('whats new', metadata.formData[languageId]['whatsNewValue']), languageCode)
        formData[formNames['keywordsName']]     = dataFromStringOrFile(dataDict.get('keywords', metadata.formData[languageId]['keywordsValue']), languageCode)
        formData[formNames['supportURLName']]   = dataDict.get('support url', metadata.formData[languageId]['supportURLValue'])
        formData[formNames['marketingURLName']] = dataDict.get('marketing url', metadata.formData[languageId]['marketingURLValue'])
        formData[formNames['pPolicyURLName']]   = dataDict.get('privacy policy url', metadata.formData[languageId]['pPolicyURLValue'])

        iphoneUploadScreenshotForm  = formNames['iphoneUploadScreenshotForm'] 
        iphone5UploadScreenshotForm = formNames['iphone5UploadScreenshotForm']
        ipadUploadScreenshotForm    = formNames['ipadUploadScreenshotForm']

        iphoneUploadScreenshotJS = iphoneUploadScreenshotForm.xpath('../following-sibling::script/text()')[0]
        iphone5UploadScreenshotJS = iphone5UploadScreenshotForm.xpath('../following-sibling::script/text()')[0]
        ipadUploadScreenshotJS = ipadUploadScreenshotForm.xpath('../following-sibling::script/text()')[0]

        self._uploadSessionData[DEVICE_TYPE.iPhone] = dict({'action': iphoneUploadScreenshotForm.attrib['action']
                                                        , 'key': iphoneUploadScreenshotForm.xpath(".//input[@name='uploadKey']/@value")[0]
                                                      }, **self.parseURLSFromScript(iphoneUploadScreenshotJS))
        self._uploadSessionData[DEVICE_TYPE.iPhone5] = dict({'action': iphone5UploadScreenshotForm.attrib['action']
                                                         , 'key': iphone5UploadScreenshotForm.xpath(".//input[@name='uploadKey']/@value")[0]
                                                       }, **self.parseURLSFromScript(iphone5UploadScreenshotJS))
        self._uploadSessionData[DEVICE_TYPE.iPad] = dict({'action': ipadUploadScreenshotForm.attrib['action']
                                                      , 'key': ipadUploadScreenshotForm.xpath(".//input[@name='uploadKey']/@value")[0]
                                                    }, **self.parseURLSFromScript(ipadUploadScreenshotJS))

        self._uploadSessionId = iphoneUploadScreenshotForm.xpath('.//input[@name="uploadSessionID"]/@value')[0]

        # get all images
        for device_type in [DEVICE_TYPE.iPhone, DEVICE_TYPE.iPhone5, DEVICE_TYPE.iPad]:
            self._images[device_type] = self.imagesForDevice(device_type)

        logging.debug(self._images)
        # logging.debug(formData)

        if 'images' in dataDict:
            imagesActions = dataDict['images']
            languageCode = languages.langCodeForLanguage(lang)

            for dType in imagesActions:
                device_type = None
                if dType.lower() == 'iphone':
                    device_type = DEVICE_TYPE.iPhone
                elif dType.lower() == 'iphone 5':
                    device_type = DEVICE_TYPE.iPhone5
                elif dType.lower() == 'ipad':
                    device_type = DEVICE_TYPE.iPad
                else:
                    continue

                deviceImagesActions = imagesActions[dType]
                if deviceImagesActions == "":
                    continue

                for imageAction in deviceImagesActions:
                    imageAction.setdefault('cmd')
                    imageAction.setdefault('indexes')
                    cmd = imageAction['cmd']
                    indexes = imageAction['indexes']
                    replace_language = ALIASES.language_aliases.get(languageCode, languageCode)
                    replace_device = ALIASES.device_type_aliases.get(dType.lower(), DEVICE_TYPE.deviceStrings[device_type])

                    imagePath = filename_format.replace('{language}', replace_language) \
                           .replace('{device_type}', replace_device)
                    logging.debug('Looking for images at ' + imagePath)

                    if (indexes == None) and ((cmd == 'u') or (cmd == 'r')):
                        indexes = []
                        for i in range(0, 5):
                            realImagePath = imagePath.replace("{index}", str(i + 1))
                            logging.debug('img path: ' + realImagePath)
                            if os.path.exists(realImagePath):
                                indexes.append(i + 1)

                    logging.debug('indexes ' + indexes.__str__())
                    logging.debug('Processing command ' + imageAction.__str__())

                    if (cmd == 'd') or (cmd == 'r'): # delete or replace. To perform replace we need to delete images first
                        deleteIndexes = [img['id'] for img in self._images[device_type]]
                        if indexes != None:
                            deleteIndexes = [deleteIndexes[idx - 1] for idx in indexes]

                        logging.debug('deleting images ' + deleteIndexes.__str__())
                        
                        for imageIndexToDelete in deleteIndexes:
                            img = next(im for im in self._images[device_type] if im['id'] == imageIndexToDelete)
                            self.deleteScreenshot(device_type, img['id'])

                        self._images[device_type] = self.imagesForDevice(device_type)
                    
                    if (cmd == 'u') or (cmd == 'r'): # upload or replace
                        currentIndexes = [img['id'] for img in self._images[device_type]]

                        if indexes == None:
                            continue

                        indexes = sorted(indexes)
                        for i in indexes:
                            realImagePath = imagePath.replace("{index}", str(i))
                            if os.path.exists(realImagePath):
                                self.uploadScreenshot(device_type, realImagePath)

                        self._images[device_type] = self.imagesForDevice(device_type)

                        if cmd == 'r':
                            newIndexes = [img['id'] for img in self._images[device_type]][len(currentIndexes):]

                            if len(newIndexes) == 0:
                                continue

                            for i in indexes:
                                currentIndexes.insert(i - 1, newIndexes.pop(0))

                            self.sortScreenshots(device_type, currentIndexes)
                            self._images[device_type] = self.imagesForDevice(device_type)

                    if (cmd == 's'): # sort
                        if indexes == None or len(indexes) != len(self._images[device_type]):
                            continue
                        newIndexes = [self._images[device_type][i - 1]['id'] for i in indexes]

                        self.sortScreenshots(device_type, newIndexes)
                        self._images[device_type] = self.imagesForDevice(device_type)

        formData['uploadSessionID'] = self._uploadSessionId
        logging.debug(formData)
        # formData['uploadKey'] = self._uploadSessionData[DEVICE_TYPE.iPhone5]['key']

        postFormResponse = self._parser.requests_session.post(ITUNESCONNECT_URL + submitAction, data = formData, cookies=cookie_jar)

        if postFormResponse.status_code != 200:
            raise 'Wrong response from iTunesConnect. Status code: ' + str(postFormResponse.status_code)

        if len(postFormResponse.text) > 0:
            logging.error("Save information failed. " + postFormResponse.text)

########## App Review Information management ##########

    def editReviewInformation(self, appReviewInfo):
        if appReviewInfo == None or len(appReviewInfo) == 0: # nothing to change
            return

        if len(self.versions) == 0:
            self.getAppInfo()
        if len(self.versions) == 0:
            raise 'Can\'t get application versions'

        versionString = next((versionString for versionString, version in self.versions.items() if version['editable']), None)
        if versionString == None: # Suppose there's one or less editable versions
            raise 'No editable version found'
            
        version = self.versions[versionString]
        if not version['editable']:
            raise 'Version ' + versionString + ' is not editable'

        metadata = self.__parseAppReviewInformation(version)
        formData = {}
        formNames = metadata.formNames
        submitAction = metadata.submitAction
        
        formData["save"] = "true"

        formData[formNames['first name']]    = appReviewInfo.get('first name', metadata.formData['first name'])
        formData[formNames['last name']]     = appReviewInfo.get('last name', metadata.formData['last name'])
        formData[formNames['email address']] = appReviewInfo.get('email address', metadata.formData['email address'])
        formData[formNames['phone number']]  = appReviewInfo.get('phone number', metadata.formData['phone number'])
        formData[formNames['review notes']]  = dataFromStringOrFile(appReviewInfo.get('review notes', metadata.formData['review notes']))
        formData[formNames['username']]      = appReviewInfo.get('username', metadata.formData['username'])
        formData[formNames['password']]      = appReviewInfo.get('password', metadata.formData['password'])

        logging.debug(formData)
        postFormResponse = self._parser.requests_session.post(ITUNESCONNECT_URL + submitAction, data = formData, cookies=cookie_jar)

        if postFormResponse.status_code != 200:
            raise 'Wrong response from iTunesConnect. Status code: ' + str(postFormResponse.status_code)

        if len(postFormResponse.text) > 0:
            logging.error("Save information failed. " + postFormResponse.text)

################## In-App management ##################

    def __parseInappActionURLsFromScript(self, script):
        matches = re.findall('\'([^\']+)\'\s:\s\'([^\']+)\'', script)
        self._inappActionURLs = dict((k, v) for k, v in matches if k.endswith('Url'))
        ITCInappPurchase.actionURLs = self._inappActionURLs

        return self._inappActionURLs


    def __parseInappsFromTree(self, refreshContainerTree):
        logging.debug('Parsing inapps response')
        inappULs = refreshContainerTree.xpath('.//li[starts-with(@id, "ajaxListRow_")]')

        if len(inappULs) == 0:
            logging.info('No In-App Purchases found')
            return None

        logging.debug('Found ' + str(len(inappULs)) + ' inapps')

        inappsActionScript = refreshContainerTree.xpath('//script[contains(., "var arguments")]/text()')
        if len(inappsActionScript) > 0:
            inappsActionScript = inappsActionScript[0]
            actionURLs = self.__parseInappActionURLsFromScript(inappsActionScript)
            inappsItemAction = actionURLs['itemActionUrl']

        inapps = {}
        for inappUL in inappULs:
            appleId = inappUL.xpath('./div/div[5]/text()')[0].strip()
            if self.inapps.get(appleId) != None:
                inapps[appleId] = self.inapps.get(appleId)
                continue

            iaptype = inappUL.xpath('./div/div[4]/text()')[0].strip()  
            if not (iaptype in ITCInappPurchase.supportedIAPTypes):
                continue

            numericId = inappUL.xpath('./div[starts-with(@class,"ajaxListRowDiv")]/@itemid')[0]
            name = inappUL.xpath('./div/div/span/text()')[0].strip()
            productId = inappUL.xpath('./div/div[3]/text()')[0].strip()
            manageLink = inappsItemAction + "?itemID=" + numericId
            inapps[appleId] = ITCInappPurchase(name=name, appleId=appleId, numericId=numericId, productId=productId, iaptype=iaptype, manageLink=manageLink)

        return inapps


    def getInapps(self):
        if self._manageInappsLink == None:
            self.getAppInfo()
        if self._manageInappsLink == None:
            raise 'Can\'t get "Manage In-App purchases link"'

        # TODO: parse multiple pages of inapps.
        tree = self._parser.parseTreeForURL(self._manageInappsLink)

        self._createInappLink = tree.xpath('//img[contains(@src, "btn-create-new-in-app-purchase.png")]/../@href')[0]
        if ITCInappPurchase.createInappLink == None:
            ITCInappPurchase.createInappLink = self._createInappLink

        refreshContainerTree = getElement(tree.xpath('//span[@id="ajaxListListRefreshContainerId"]/ul'), 0, None)
        if refreshContainerTree == None:
            self.inapps = {}
        else:
            self.inapps = self.__parseInappsFromTree(refreshContainerTree)


    def getInappById(self, inappId):
        if self._inappActionURLs == None:
            self.getInapps()

        if len(self.inapps) == 0:
            return None

        if type(inappId) is int:
            inappId = str(inappId)

        if self.inapps.get(inappId) != None:
            return self.inapps[inappId]

        if self._manageInappsTree == None:
            self._manageInappsTree = self._parser.parseTreeForURL(self._manageInappsLink)

        tree = self._manageInappsTree
        reloadInappsAction = tree.xpath('//span[@id="ajaxListListRefreshContainerId"]/@action')[0]
        searchAction = self._inappActionURLs['searchActionUrl']

        logging.info('Searching for inapp with id ' + inappId)

        searchResponse = self._parser.requests_session.get(ITUNESCONNECT_URL + searchAction + "?query=" + inappId, cookies=cookie_jar)

        if searchResponse.status_code != 200:
            raise 'Wrong response from iTunesConnect. Status code: ' + str(searchResponse.status_code)

        statusJSON = json.loads(searchResponse.content)
        if statusJSON['totalItems'] <= 0:
            logging.warn('No matching inapps found! Search term: ' + inappId)
            return None

        inapps = self.__parseInappsFromTree(self._parser.parseTreeForURL(reloadInappsAction))

        if inapps == None:
            raise "Error parsing inapps"

        if len(inapps) == 1:
            return inapps[0]

        tmpinapps = []
        for numericId, inapp in inapps.items():
            if (inapp.numericId == inappId) or (inapp.productId == inappId):
                return inapp

            components = inapp.productId.partition(u'…')
            if components[1] == u'…': #split successful
                if inappId.startswith(components[0]) and inappId.endswith(components[2]):
                    tmpinapps.append(inapp)

        if len(tmpinapps) == 1:
            return tmpinapps[0]

        logging.error('Multiple inapps found for id (' + inappId + ').')
        logging.error(tmpinapps)

        # TODO: handle this situation. It is possible to avoid this exception by requesting
        # each result's page. Possible, but expensive :)
        raise 'Ambiguous search result.'


    def createInapp(self, inappDict):
        if self._createInappLink == None:
            self.getInapps()
        if self._createInappLink == None:
            raise 'Can\'t create inapp purchase'

        if not (inappDict['type'] in ITCInappPurchase.supportedIAPTypes):
            logging.error('Can\'t create inapp purchase: "' + inappDict['id'] + '" is not supported')
            return

        iap = ITCInappPurchase(name=inappDict['reference name']
                             , productId=inappDict['id']
                             , iaptype=inappDict['type'])
        iap.clearedForSale = inappDict['cleared']
        iap.priceTier = int(inappDict['price tier']) - 1
        iap.hostingContentWithApple = inappDict['hosting content with apple']
        iap.reviewNotes = inappDict['review notes']

        iap.create(inappDict['languages'], screenshot=inappDict.get('review screenshot'))

####################### Add version ########################

    def addVersion(self, version, langActions):
        if len(self.versions) == 0:
            self.getAppInfo()
        if len(self.versions) == 0:
            raise 'Can\'t get application versions'

        if self._addVersionLink == None:
            raise 'Can\'t find \'Add Version\' link.'

        logging.info('Parsing \'Add Version\' page')
        tree = self._parser.parseTreeForURL(self._addVersionLink)
        metadata = self._parser.parseAddVersionPageMetadata(tree)
        formData = {metadata.saveButton + '.x': 46, metadata.saveButton + '.y': 10}
        formData[metadata.formNames['version']] = version
        defaultWhatsNew = langActions.get('default', {}).get('whats new', '')
        logging.debug('Default what\'s new: ' + defaultWhatsNew)
        for lang, taName in metadata.formNames['languages'].items():
            languageCode = languages.langCodeForLanguage(lang)
            whatsNew = langActions.get(lang, {}).get('whats new', defaultWhatsNew)
            
            if (isinstance(whatsNew, dict)):
                whatsNew = dataFromStringOrFile(whatsNew, languageCode)
            formData[taName] = whatsNew
        self._parser.requests_session.post(ITUNESCONNECT_URL + metadata.submitAction, data = formData, cookies=cookie_jar)

        # TODO: Add error handling


################## Promo codes management ##################

    def getPromocodes(self, amount):
        if len(self.versions) == 0:
            self.getAppInfo()
        if len(self.versions) == 0:
            raise 'Can\'t get application versions'

        # We need non-editable version to get promocodes from
        versionString = next((versionString for versionString, version in self.versions.items() if version['statusString'] == "Ready for Sale"), None)
        if versionString == None:
            raise 'No "Ready for Sale" versions found'
            
        version = self.versions[versionString]
        if version['editable']:
            raise 'Version ' + versionString + ' is editable.'

        #get promocodes link
        logging.info('Getting promocodes link')
        tree = self._parser.parseTreeForURL(version['detailsLink'])
        promocodesLink = self._parser.getPromocodesLink(tree)
        logging.debug('Promocodes link: ' + promocodesLink)

        #enter number of promocodes
        logging.info('Requesting promocodes: ' + amount)
        tree = self._parser.parseTreeForURL(promocodesLink)
        metadata = self._parser.parsePromocodesPageMetadata(tree)
        formData = {metadata.continueButton + '.x': 46, metadata.continueButton + '.y': 10}
        formData[metadata.amountName] = amount
        postFormResponse = self._parser.requests_session.post(ITUNESCONNECT_URL + metadata.submitAction, data = formData, cookies=cookie_jar)

        #accept license agreement
        logging.info('Accepting license agreement')
        metadata = self._parser.parsePromocodesLicenseAgreementPage(postFormResponse.text)
        formData = {metadata.continueButton + '.x': 46, metadata.continueButton + '.y': 10}
        formData[metadata.agreeTickName] = metadata.agreeTickName
        postFormResponse = self._parser.requests_session.post(ITUNESCONNECT_URL + metadata.submitAction, data = formData, cookies=cookie_jar)

        #download promocodes
        logging.info('Downloading promocodes')
        downloadCodesLink = self._parser.getDownloadCodesLink(postFormResponse.text)
        codes = self._parser.requests_session.get(ITUNESCONNECT_URL + downloadCodesLink
                                      , cookies=cookie_jar)

        return codes.text

################## Reviews management ##################
    def _parseDate(self, date):
        returnDate = None
        if date == 'today':
            returnDate = datetime.today()
        elif date == 'yesterday':
            returnDate = datetime.today() - timedelta(1)
        elif not '/' in date:
            returnDate = datetime.today() - timedelta(int(date))
        else:
            returnDate = datetime.strptime(date, '%d/%m/%Y')

        return datetime(returnDate.year, returnDate.month, returnDate.day)

    def generateReviews(self, latestVersion=False, date=None, outputFileName=None):
        if self._customerReviewsLink == None:
            self.getAppInfo()
        if self._customerReviewsLink == None:
            raise 'Can\'t get "Customer Reviews link"'

        minDate = None
        maxDate = None
        if date:
            if not '-' in date:
                minDate = self._parseDate(date)
                maxDate = minDate
            else:
                dateArray = date.split('-')
                if len(dateArray[0]) > 0:
                    minDate = self._parseDate(dateArray[0])
                if len(dateArray[1]) > 0:
                    maxDate = self._parseDate(dateArray[1])
                if maxDate != None and minDate != None and maxDate < minDate:
                    tmpDate = maxDate
                    maxDate = minDate
                    minDate = tmpDate

        tree = self._parser.parseTreeForURL(self._customerReviewsLink)
        metadata = self._parser.getReviewsPageMetadata(tree)

        if metadata == None: # no reviews
            logging.info('There are currently no customer reviews for this app.')
            return

        logging.debug('From: %s' %minDate)
        logging.debug('To: %s' %maxDate)
        if (latestVersion):
            tree = self._parser.parseTreeForURL(metadata.currentVersion)
        else:
            tree = self._parser.parseTreeForURL(metadata.allVersions)
        tree = self._parser.parseTreeForURL(metadata.allReviews)

        reviews = {}
        logging.info('Fetching reviews for %d countries. Please wait...' % len(metadata.countries))
        percentDone = 0
        percentStep = 100.0 / len(metadata.countries)
        totalReviews = 0
        totalScore = 0
        for countryName, countryId in metadata.countries.items():
            logging.debug('Fetching reviews for ' + countryName)
            formData = {metadata.countriesSelectName: countryId}
            postFormResponse = self._parser.requests_session.post(ITUNESCONNECT_URL + metadata.countryFormSubmitAction, data = formData, cookies=cookie_jar)
            reviewsTuple = self._parser.parseReviews(postFormResponse.content, minDate=minDate, maxDate=maxDate)
            if (reviewsTuple != None):
                reviewsForCountry = reviewsTuple[0]
                totalScoreForCountry = reviewsTuple[1]
                if reviewsForCountry != None and len(reviewsForCountry) != 0:
                    reviews[countryName] = reviewsForCountry
                    totalReviews = totalReviews + len(reviewsForCountry)
                    totalScore = totalScore + totalScoreForCountry
                if not config.options['--silent'] and not config.options['--verbose']:
                    percentDone = percentDone + percentStep
                    print >> sys.stdout, "\r%d%%" %percentDone,
                    sys.stdout.flush()
                amountOfReviewsForCountry = len(reviewsForCountry)
                logging.debug('Got {0} reviews for {1}. Average mark is {2:.3f}'.format(amountOfReviewsForCountry, countryName, float(totalScoreForCountry) / amountOfReviewsForCountry) )
            else:
                logging.debug('No reviews for ' + countryName)

        if not config.options['--silent'] and not config.options['--verbose']:
            print >> sys.stdout, "\rDone\n",
            sys.stdout.flush()

        logging.info("Got %d reviews." % totalReviews)
        if totalReviews > 0:
            logging.info("Average mark is {0:.3f}".format(float(totalScore) / totalReviews))


        if outputFileName:
            with codecs.open(outputFileName, 'w', 'utf-8') as fp:
                json.dump(reviews, fp, sort_keys=False, indent=4, separators=(',', ': '), ensure_ascii=False)
        else:
            print str(reviews).decode('unicode-escape')

########NEW FILE########
__FILENAME__ = colorer
#!/usr/bin/env python
# encoding: utf-8
import logging
# now we patch Python code to add color support to logging.StreamHandler
def add_coloring_to_emit_windows(fn):
        # add methods we need to the class
    def _out_handle(self):
        import ctypes
        return ctypes.windll.kernel32.GetStdHandle(self.STD_OUTPUT_HANDLE)
    out_handle = property(_out_handle)

    def _set_color(self, code):
        import ctypes
        # Constants from the Windows API
        self.STD_OUTPUT_HANDLE = -11
        hdl = ctypes.windll.kernel32.GetStdHandle(self.STD_OUTPUT_HANDLE)
        ctypes.windll.kernel32.SetConsoleTextAttribute(hdl, code)

    setattr(logging.StreamHandler, '_set_color', _set_color)

    def new(*args):
        FOREGROUND_BLUE      = 0x0001 # text color contains blue.
        FOREGROUND_GREEN     = 0x0002 # text color contains green.
        FOREGROUND_RED       = 0x0004 # text color contains red.
        FOREGROUND_INTENSITY = 0x0008 # text color is intensified.
        FOREGROUND_WHITE     = FOREGROUND_BLUE|FOREGROUND_GREEN |FOREGROUND_RED
       # winbase.h
        STD_INPUT_HANDLE = -10
        STD_OUTPUT_HANDLE = -11
        STD_ERROR_HANDLE = -12

        # wincon.h
        FOREGROUND_BLACK     = 0x0000
        FOREGROUND_BLUE      = 0x0001
        FOREGROUND_GREEN     = 0x0002
        FOREGROUND_CYAN      = 0x0003
        FOREGROUND_RED       = 0x0004
        FOREGROUND_MAGENTA   = 0x0005
        FOREGROUND_YELLOW    = 0x0006
        FOREGROUND_GREY      = 0x0007
        FOREGROUND_INTENSITY = 0x0008 # foreground color is intensified.

        BACKGROUND_BLACK     = 0x0000
        BACKGROUND_BLUE      = 0x0010
        BACKGROUND_GREEN     = 0x0020
        BACKGROUND_CYAN      = 0x0030
        BACKGROUND_RED       = 0x0040
        BACKGROUND_MAGENTA   = 0x0050
        BACKGROUND_YELLOW    = 0x0060
        BACKGROUND_GREY      = 0x0070
        BACKGROUND_INTENSITY = 0x0080 # background color is intensified.     

        levelno = args[1].levelno
        if(levelno>=50):
            color = BACKGROUND_YELLOW | FOREGROUND_RED | FOREGROUND_INTENSITY | BACKGROUND_INTENSITY 
        elif(levelno>=40):
            color = FOREGROUND_RED | FOREGROUND_INTENSITY
        elif(levelno>=30):
            color = FOREGROUND_YELLOW | FOREGROUND_INTENSITY
        elif(levelno>=20):
            color = FOREGROUND_GREEN
        elif(levelno>=10):
            color = FOREGROUND_MAGENTA
        else:
            color =  FOREGROUND_WHITE
        args[0]._set_color(color)

        ret = fn(*args)
        args[0]._set_color( FOREGROUND_WHITE )
        #print "after"
        return ret
    return new

def add_coloring_to_emit_ansi(fn):
    # add methods we need to the class
    def new(*args):
        levelno = args[1].levelno
        if(levelno>=50):
            color = '\x1b[31m' # red
        elif(levelno>=40):
            color = '\x1b[31m' # red
        elif(levelno>=30):
            color = '\x1b[0m' # normal
        elif(levelno>=20):
            color = '\x1b[0m' # normal
        elif(levelno>=10):
            color = '\x1b[0m' # normal
        else:
            color = '\x1b[0m' # normal
        if isinstance(args[1].msg, basestring):
            args[1].msg = color + args[1].msg +  '\x1b[0m'  # normal
        else:
            args[1].msg = color + str(args[1].msg) +  '\x1b[0m'  # normal
        #print "after"
        return fn(*args)
    return new

import platform
if platform.system()=='Windows':
    # Windows does not support ANSI escapes and we are using API calls to set the console color
    logging.StreamHandler.emit = add_coloring_to_emit_windows(logging.StreamHandler.emit)
else:
    # all non-Windows platforms are supporting ANSI escapes so we use them
    logging.StreamHandler.emit = add_coloring_to_emit_ansi(logging.StreamHandler.emit)
    #log = logging.getLogger()
    #log.addFilter(log_filter())
    #//hdlr = logging.StreamHandler()
    #//hdlr.setFormatter(formatter())
########NEW FILE########
__FILENAME__ = imageuploader
# coding=utf-8

import re
import json
import logging

import requests

from itc.util import EnhancedFile
from itc.conf import *

class ITCImageUploader(object):
    _uploadSessionData = None
    _images = None
    def __init__(self):
        self._uploadSessionData = {}
        self._images = {}

    def parseURLSFromScript(self, script):
        matches = re.search('{.*statusURL:\s\'([^\']+)\',\sdeleteURL:\s\'([^\']+)\',\ssortURL:\s\'([^\']+)\'', script) 
        return {'statusURL': matches.group(1)
                , 'deleteURL': matches.group(2)
                , 'sortURL': matches.group(3)}

    def parseStatusURLSFromScript(self, script):
        matches = re.search('{.*statusURL:\s\'([^\']+)\'', script) 
        return {'statusURL': matches.group(1)}

    def imagesForDevice(self, device_type):
        if len(self._uploadSessionData) == 0:
            raise 'No session keys found'

        statusURL = self._uploadSessionData[device_type]['statusURL']
        result = None

        if statusURL:
            attempts = 3
            while attempts > 0 and result == None:
                status = self._parser.requests_session.get(ITUNESCONNECT_URL + statusURL
                                      , cookies=cookie_jar)
                statusJSON = None
                try:
                    statusJSON = json.loads(status.content)
                except ValueError:
                    logging.error('Can\'t parse status content. New attempt (%d of %d)' % (4 - attempts), attempts)
                    attempts -= 1
                    continue

                logging.debug(status.content)
                result = []

                for i in range(0, 5):
                    key = 'pictureFile_' + str(i + 1)
                    if key in statusJSON:
                        image = {}
                        pictureFile = statusJSON[key]
                        image['url'] = pictureFile['url']
                        image['orientation'] = pictureFile['orientation']
                        image['id'] = pictureFile['pictureId']
                        result.append(image)
                    else:
                        break

        return result


    def uploadScreenshot(self, upload_type, file_path):
        if self._uploadSessionId == None or len(self._uploadSessionData) == 0:
            raise 'Trying to upload screenshot without proper session keys'

        uploadScreenshotAction = self._uploadSessionData[upload_type]['action']
        uploadScreenshotKey = self._uploadSessionData[upload_type]['key']

        if uploadScreenshotAction != None and uploadScreenshotKey != None and os.path.exists(file_path):
            headers = { 'x-uploadKey' : uploadScreenshotKey
                        , 'x-uploadSessionID' : self._uploadSessionId
                        , 'x-original-filename' : os.path.basename(file_path)
                        , 'Content-Type': 'image/png'}
            logging.info('Uploading image ' + file_path)
            r = self._parser.requests_session.post(ITUNESCONNECT_URL + uploadScreenshotAction
                                , cookies=cookie_jar
                                , headers=headers
                                , data=EnhancedFile(file_path, 'rb'))

            if r.content == 'success':
                newImages = self.imagesForDevice(upload_type)
                if len(newImages) > len(self._images[upload_type]):
                    logging.info('Image uploaded')
                else:
                    logging.error('Upload failed: ' + file_path)


    def deleteScreenshot(self, type, screenshot_id):
        if len(self._uploadSessionData) == 0:
            raise 'Trying to delete screenshot without proper session keys'

        deleteScreenshotAction = self._uploadSessionData[type]['deleteURL']
        if deleteScreenshotAction != None:
            self._parser.requests_session.get(ITUNESCONNECT_URL + deleteScreenshotAction + "?pictureId=" + screenshot_id
                    , cookies=cookie_jar)

            # TODO: check status


    def sortScreenshots(self, type, newScreenshotsIndexes):
        if len(self._uploadSessionData) == 0:
            raise 'Trying to sort screenshots without proper session keys'

        sortScreenshotsAction = self._uploadSessionData[type]['sortURL']

        if sortScreenshotsAction != None:
            self._parser.requests_session.get(ITUNESCONNECT_URL + sortScreenshotsAction 
                                    + "?sortedIDs=" + (",".join(newScreenshotsIndexes))
                            , cookies=cookie_jar)

            # TODO: check status

########NEW FILE########
__FILENAME__ = inapp
import re
import logging

import requests

from itc.parsers.inappparser import ITCInappParser
from itc.util import EnhancedFile
from itc.util import languages
from itc.conf import *

class ITCInappPurchase(object):
    createInappLink = None
    actionURLs = None
    supportedIAPTypes = ['Consumable', 'Non-Consumable', 'Free Subscription', 'Non-Renewing Subscription']

    def __init__(self, name=None, numericId=None, productId=None, iaptype=None, manageLink=None, appleId=None):
        self.name = name
        self.numericId = numericId
        self.productId = productId
        self.appleId = appleId
        self.type = iaptype
        self.reviewNotes = None
        self.clearedForSale = False
        self.hostingContentWithApple = False
        self.manageLink = manageLink
        self._parser = ITCInappParser()

        logging.info('Inapp found: ' + self.__str__())
        logging.debug('productId: ' + (self.productId if self.productId != None else ""))
        logging.debug('type: ' + (self.type if self.type != None else ""))
        logging.debug('manage link: ' + (self.manageLink if self.manageLink != None else ""))


    def __repr__(self):
        return self.__str__()


    def __str__(self):
        strng = ""
        if self.name != None:
            strng += "\"" + self.name + "\""
        if self.numericId != None:
            strng += " (" + str(self.appleId) + ")"

        return strng

    def __uploadScreenshot(self, file_path):
        if self._uploadScreenshotAction == None or self._uploadScreenshotKey == None:
            raise 'Trying to upload screenshot without proper session keys'

        if os.path.exists(file_path):
            headers = { 'x-uploadKey' : self._uploadScreenshotKey
                        , 'x-uploadSessionID' : self._uploadSessionId
                        , 'x-original-filename' : os.path.basename(file_path)
                        , 'Content-Type': 'image/png'}
            logging.info('Uploading image ' + file_path)
            r = self._parser.requests_session.post(ITUNESCONNECT_URL + self._uploadScreenshotAction
                                , cookies=cookie_jar
                                , headers=headers
                                , data=EnhancedFile(file_path, 'rb'))

            if r.content == 'success':
                # newImages = self.__imagesForDevice(upload_type)
                # if len(newImages) > len(self._images[upload_type]):
                #     logging.info('Image uploaded')
                # else:
                #     logging.error('Upload failed: ' + file_path)
                pass

    def __createUpdateLanguage(self, localizationTree, langId, langVal, isEdit=False):
        langName = languages.languageNameForId(langId)
        localizationSaveAction = localizationTree.xpath('//div[@class="lcAjaxLightboxContents"]/@action')[0]
        languageSelect = None
        langSelectName = None
        langSelectValue = None
        langFormData = {}

        if isEdit == False:
            languageSelect = localizationTree.xpath('//select[@id="language-popup"]')[0]
            langSelectName = languageSelect.xpath('./@name')[0]
            langSelectValue = languageSelect.xpath('./option[.="' + langName + '"]/@value')[0]
            langFormData[langSelectName] = langSelectValue

        nameElementName = localizationTree.xpath('//div[@id="proposedDisplayName"]//input/@name')[0]
        descriptionElementName = localizationTree.xpath('//div[@id="proposedDescription"]//textarea/@name')[0]

        publicationName = localizationTree.xpath('//div[@id="proposedPublicationName"]//input/@name')
        if len(publicationName) > 0:
            publicationName = publicationName[0]
            langFormData[publicationName] = langVal['publication name']

        langFormData[nameElementName] = langVal['name']
        langFormData[descriptionElementName] = langVal['description']
        langFormData['save'] = "true"

        postFormResponse = self._parser.requests_session.post(ITUNESCONNECT_URL + localizationSaveAction, data = langFormData, cookies=cookie_jar)

        if postFormResponse.status_code != 200:
            raise 'Wrong response from iTunesConnect. Status code: ' + str(postFormResponse.status_code)

        if len(postFormResponse.text) > 0:
            logging.error("Save information failed. " + postFormResponse.text)


    def generateConfig(self):
        tree = self._parser.parseTreeForURL(ITCInappPurchase.actionURLs['itemActionUrl'] + "?itemID=" + self.numericId)
        metadata = self._parser.metadataForInappPurchase(tree)

        inappDict = {"id": metadata.numericid, "_id": metadata.textid, "type": self.type
                    , "reference name": metadata.refname
                    , "price tier": metadata.price_tier
                    , "cleared": metadata.cleared
                    , "hosting content with apple": metadata.hosted
                    , "review notes": metadata.reviewnotes
                    , "languages": metadata.languages}

        return inappDict

    def update(self, inappDict):
        tree = self._parser.parseTreeForURL(ITCInappPurchase.actionURLs['itemActionUrl'] + "?itemID=" + self.numericId)

        # for non-consumable iap we can change name, cleared-for-sale and pricing. Check if we need to:
        inappReferenceName = tree.xpath('//span[@id="iapReferenceNameUpdateContainer"]//span/text()')[0]
        clearedForSaleText = tree.xpath('//div[contains(@class,"cleared-for-sale")]//span/text()')[0]
        clearedForSale = False
        if clearedForSaleText == 'Yes':
            clearedForSale = True

        logging.debug('Updating inapp: ' + inappDict.__str__())

        self.name = inappDict.get('name', self.name)
        self.clearedForSale = inappDict.get('cleared', self.clearedForSale)
        self.hostingContentWithApple = inappDict.get('hosting content with apple', self.hostingContentWithApple)
        self.reviewNotes = inappDict.get('review notes', self.reviewNotes)

        # TODO: change price tier
        if (inappReferenceName != self.name) \
            or (clearedForSale != self.clearedForSale):
            editAction = tree.xpath('//div[@id="singleAddonPricingLightbox"]/@action')[0]

            inappTree = self._parser.parseTreeForURL(editAction)

            inappReferenceNameName = inappTree.xpath('//div[@id="referenceNameTooltipId"]/..//input/@name')[0]
            clearedForSaleName = inappTree.xpath('//div[contains(@class,"cleared-for-sale")]//input[@classname="radioTrue"]/@name')[0]
            clearedForSaleNames = {}
            clearedForSaleNames["true"] = inappTree.xpath('//div[contains(@class,"cleared-for-sale")]//input[@classname="radioTrue"]/@value')[0]
            clearedForSaleNames["false"] = inappTree.xpath('//div[contains(@class,"cleared-for-sale")]//input[@classname="radioFalse"]/@value')[0]
            inappPriceTierName = inappTree.xpath('//select[@id="price_tier_popup"]/@name')[0]

            dateComponentsNames = inappTree.xpath('//select[contains(@id, "_day")]/@name')
            dateComponentsNames.extend(inappTree.xpath('//select[contains(@id, "_month")]/@name'))
            dateComponentsNames.extend(inappTree.xpath('//select[contains(@id, "_year")]/@name'))

            postAction = inappTree.xpath('//div[@class="lcAjaxLightboxContents"]/@action')[0]

            formData = {}
            formData[inappReferenceNameName] = self.name
            formData[clearedForSaleName] = clearedForSaleNames["true" if self.clearedForSale else "false"]
            formData[inappPriceTierName] = 'WONoSelectionString'
            for dcn in dateComponentsNames:
                formData[dcn] = 'WONoSelectionString'
            formData['save'] = "true"

            postFormResponse = self._parser.requests_session.post(ITUNESCONNECT_URL + postAction, data = formData, cookies=cookie_jar)

            if postFormResponse.status_code != 200:
                raise 'Wrong response from iTunesConnect. Status code: ' + str(postFormResponse.status_code)


        idAddon = "autoRenewableL" if (inapptype == "Free Subscription") else "l"
        languagesSpan = inappTree.xpath('//span[@id="0' + idAddon + 'ocalizationListListRefreshContainerId"]')[0]
        activatedLanguages = languagesSpan.xpath('.//li[starts-with(@id, "0' + idAddon + 'ocalizationListRow")]/div[starts-with(@class, "ajaxListRowDiv")]/@itemid')
        activatedLangsIds = [languages.langCodeForLanguage(lang) for lang in activatedLanguages]
        languageAction = tree.xpath('//div[@id="0' + idAddon + 'ocalizationListLightbox"]/@action')[0]

        logging.info('Activated languages for inapp ' + self.numericId + ': ' + ', '.join(activatedLanguages))
        logging.debug('Activated languages ids: ' + ', '.join(activatedLangsIds))

        langDict = inappDict.get('languages', {})
        for langId, langVal in langDict.items():
            if type(langVal) is str:
                if langId in activatedLangsIds and langVal == 'd': # TODO: delete lang
                    pass
                return
            
            languageParamStr = ""
            isEdit = False

            if langId in activatedLangsIds: # edit
                languageParamStr = "&itemID=" + languages.appleLangIdForLanguage(langId)
                isEdit = True

            localizationTree = self._parser.parseTreeForURL(languageAction + "?open=true" + languageParamStr)
            self.__createUpdateLanguage(localizationTree, langId, langVal, isEdit=isEdit)

        # upload screenshot, edit review notes, hosting content with apple, etc
        formData = {"save":"true"}
        editHostedContentAction = tree.xpath('//div[@id="versionLightboxId0"]/@action')[0]
        hostedContentTree = self._parser.parseTreeForURL(editHostedContentAction + "?open=true")
        saveEditHostedContentAction = hostedContentTree.xpath('//div[@class="lcAjaxLightboxContents"]/@action')[0]

        if (self.type == "Non-Consumable"):
            hostingContentName = hostedContentTree.xpath('//div[contains(@class,"hosting-on-apple")]//input[@classname="radioTrue"]/@name')[0]
            hostingContentNames = {}
            hostingContentNames["true"] = hostedContentTree.xpath('//div[contains(@class,"hosting-on-apple")]//input[@classname="radioTrue"]/@value')[0]
            hostingContentNames["false"] = hostedContentTree.xpath('//div[contains(@class,"hosting-on-apple")]//input[@classname="radioFalse"]/@value')[0]
            formData[hostingContentName] = hostingContentNames["true" if self.hostingContentWithApple else "false"]

        if inappDict['review screenshot'] != None:
            uploadForm = hostedContentTree.xpath('//form[@name="FileUploadForm__screenshotId"]')[0]
            self._uploadScreenshotAction = uploadForm.xpath('./@action')[0]
            self._uploadSessionId = uploadForm.xpath('.//input[@id="uploadSessionID"]/@value')[0]
            self._uploadScreenshotKey = uploadForm.xpath('.//input[@id="uploadKey"]/@value')[0]
            statusURLScript = hostedContentTree.xpath('//script[contains(., "var uploader_screenshotId")]/text()')[0]
            matches = re.findall('statusURL:\s\'([^\']+)\'', statusURLScript)
            self._statusURL = matches[0]
            self.__uploadScreenshot(inappDict['review screenshot'])
            self._parser.requests_session.get(ITUNESCONNECT_URL + self._statusURL, cookies=cookie_jar)

            formData["uploadSessionID"] = self._uploadSessionId
            formData["uploadKey"] = self._uploadScreenshotKey
            formData["filename"] = inappDict['review screenshot']

 
        reviewNotesName = hostedContentTree.xpath('//div[@class="hosted-review-notes"]//textarea/@name')[0]
        formData[reviewNotesName] = self.reviewNotes
        self._parser.parseTreeForURL(saveEditHostedContentAction, method="POST", payload=formData)


    def create(self, langDict, screenshot=None):
        logging.debug('Creating inapp: ' + langDict.__str__())

        tree = self._parser.parseTreeForURL(ITCInappPurchase.createInappLink)

        inapptype = self.type
        newInappLink = tree.xpath('//form[@name="mainForm"]/@action')[0]
        newInappTypeLink = tree.xpath('//div[@class="type-section"]/h3[.="' + inapptype + '"]/following-sibling::a/@href')[0]
        
        inappTree = self._parser.parseTreeForURL(newInappTypeLink, method="GET")

        if ITCInappPurchase.actionURLs == None:
            inappsActionScript = inappTree.xpath('//script[contains(., "var arguments")]/text()')[0]
            matches = re.findall('\'([^\']+)\'\s:\s\'([^\']+)\'', inappsActionScript)
            ITCInappPurchase.actionURLs = dict((k, v) for k, v in matches if k.endswith('Url'))

        formData = {}

        inappReferenceNameName = inappTree.xpath('//span[@id="iapReferenceNameUpdateContainer"]//input/@name')[0]
        inappProductIdName = inappTree.xpath('//div[@id="productIdText"]//input/@name')[0]
        clearedForSaleName = inappTree.xpath('//div[contains(@class,"cleared-for-sale")]//input[@classname="radioTrue"]/@name')[0]
        clearedForSaleNames = {}
        clearedForSaleNames["true"] = inappTree.xpath('//div[contains(@class,"cleared-for-sale")]//input[@classname="radioTrue"]/@value')[0]
        clearedForSaleNames["false"] = inappTree.xpath('//div[contains(@class,"cleared-for-sale")]//input[@classname="radioFalse"]/@value')[0]

        if (inapptype != "Free Subscription"):
            inappPriceTierName = inappTree.xpath('//select[@id="price_tier_popup"]/@name')[0]
            formData[inappPriceTierName] = int(self.priceTier)

        if (inapptype == "Non-Consumable"):
            hostingContentName = inappTree.xpath('//div[contains(@class,"hosting-on-apple")]//input[@classname="radioTrue"]/@name')[0]
            hostingContentNames = {}
            hostingContentNames["true"] = inappTree.xpath('//div[contains(@class,"hosting-on-apple")]//input[@classname="radioTrue"]/@value')[0]
            hostingContentNames["false"] = inappTree.xpath('//div[contains(@class,"hosting-on-apple")]//input[@classname="radioFalse"]/@value')[0]
            formData[hostingContentName] = hostingContentNames["true" if self.hostingContentWithApple else "false"]

        reviewNotesName = inappTree.xpath('//div[@id="reviewNotesCreation"]//textarea/@name')[0]

        if (inapptype == "Free Subscription"):
            localizationLightboxAction = inappTree.xpath('//div[@id="autoRenewableLocalizationListLightbox"]/@action')[0]
        else:
            localizationLightboxAction = inappTree.xpath('//div[@id="localizationListLightbox"]/@action')[0]

        for langId, langVal in langDict.items():
            localizationTree = self._parser.parseTreeForURL(localizationLightboxAction + "?open=true")

            self.__createUpdateLanguage(localizationTree, langId, langVal)

        if screenshot != None:
            uploadForm = inappTree.xpath('//form[@name="FileUploadForm__screenshotId"]')[0]
            self._uploadScreenshotAction = uploadForm.xpath('./@action')[0]
            self._uploadSessionId = uploadForm.xpath('.//input[@id="uploadSessionID"]/@value')[0]
            self._uploadScreenshotKey = uploadForm.xpath('.//input[@id="uploadKey"]/@value')[0]
            statusURLScript = inappTree.xpath('//script[contains(., "var uploader_screenshotId")]/text()')[0]
            matches = re.findall('statusURL:\s\'([^\']+)\'', statusURLScript)
            self._statusURL = matches[0]
            self.__uploadScreenshot(screenshot)
            self._parser.requests_session.get(ITUNESCONNECT_URL + self._statusURL, cookies=cookie_jar)

            formData["uploadSessionID"] = self._uploadSessionId
            formData["uploadKey"] = self._uploadScreenshotKey
            formData["filename"] = screenshot

        postAction = inappTree.xpath('//form[@id="addInitForm"]/@action')[0]

        formData[inappReferenceNameName] = self.name
        formData[inappProductIdName] = self.productId
        formData[clearedForSaleName] = clearedForSaleNames["true" if self.clearedForSale else "false"]
        formData[reviewNotesName] = self.reviewNotes

        self._parser.parseTreeForURL(postAction, method="POST", payload=formData)
        postFormTree = self._parser.parseTreeForURL(newInappLink, method="POST", payload=formData)
        errorDiv = postFormTree.xpath('//div[@id="LCPurpleSoftwarePageWrapperErrorMessage"]')

        if len(errorDiv) > 0:
            logging.error("Save information failed. " + errorDiv[0].xpath('.//span/text()')[0])


########NEW FILE########
__FILENAME__ = itccli
# encoding: utf-8
"""Command line interface for iTunesConnect (https://github.com/kovpas/itc.cli)

Usage: 
    itc login [-n] [-k | -w] [-u USERNAME] [-p PASSWORD] [-z] [-v | -vv [-f] | -s]
    itc update -c FILE [-a APP_ID] [-n] [-k] [-u USERNAME] [-p PASSWORD] [-z] [-v | -vv [-f] | -s]
    itc version -c FILE [-a APP_ID] [-n] [-k] [-u USERNAME] [-p PASSWORD] [-z] [-v | -vv [-f] | -s]
    itc create -c FILE [-n] [-k] [-u USERNAME] [-p PASSWORD] [-z] [-v | -vv [-f] | -s]
    itc generate [-a APP_ID] [-e APP_VER] [-i] [-c FILE] [-n] [-k] [-u USERNAME] [-p PASSWORD] [-z] [-v | -vv [-f] | -s]
    itc promo -a APP_ID [-n] [-k] [-u USERNAME] [-p PASSWORD] [-z] [-v | -vv [-f] | -s] [-o FILE] <amount>
    itc reviews -a APP_ID [-d DATE] [-l] [-n] [-k] [-u USERNAME] [-p PASSWORD] [-z] [-v | -vv [-f] | -s] [-o FILE]
    itc (-h | --help)

Commands:
  login                       Logs in with specified credentials.
  update                      Update specified app with information provided in a config file.
  create                      Creates new app using information provided in a config file.
  generate                    Generate configuration file for a specified application id and version.
                                If no --application-id provided, configuration files for all 
                                applications will be created.
  promo                       Download specified <amount> of promocodes.
  reviews                     Get reviews for a specified application.

Options:
  --version                   Show version.
  -h --help                   Print help (this message) and exit.
  -v --verbose                Verbose mode. Enables debug print to console.
  -vv                         Enables HTTP response print to a console.
  -f                          Nicely format printed html response.
  -s --silent                 Silent mode. Only error messages are printed.
  -u --username USERNAME      iTunesConnect username.
  -p --password PASSWORD      iTunesConnect password.
  -e --application-version APP_VER  
                              Application version to generate config.
                                If not provided, config will be generated for latest version.
  -i --generate-config-inapp  Generate config for inapps as well.
  -c --config-file FILE       Configuration file. For more details on format see https://github.com/kovpas/itc.cli.
  -a --application-id APP_ID  Application id to process. This property has more priority than 'application id'
                                in configuration file.
  -n --no-cookies             Remove saved authentication cookies and authenticate again.
  -k --store-password         Store password in a system's secure storage. Removes authentication cookies first, so password has to be entered manually.
  -w --delete-password        Remove stored password system's secure storage.
  -z                          Automatically click 'Continue' button if appears after login.
  -o --output-file FILE       Name of file to save promocodes or reviews to.
  -d --date-range DATERANGE   Get reviews specified with this date range. Format [date][-][date].
                                For more information, please, refer to https://github.com/kovpas/itc.cli.
  -l --latest-version         Get reviews for current version only.

"""

import os
import logging
import colorer
import platform
import sys
import json
import getpass
import keyring
from copy import deepcopy 

from itc.core.server import ITCServer
from itc.core import __version__
from itc.util import *
from itc.conf import *
from docopt import docopt

options = None
config = {}

def __parse_options():
    args = docopt(__doc__, version=__version__)
    conf.config.options = args
    globals()['options'] = args
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    if args['--verbose']:
        logging.basicConfig(level=logging.DEBUG, format=log_format)
    elif not args['--silent']:
        requests_log = logging.getLogger('requests')
        requests_log.setLevel(logging.WARNING)
        
        logging.basicConfig(level=logging.INFO, format=log_format)
    else:
        requests_log = logging.getLogger('requests')
        requests_log.setLevel(logging.ERROR)
        
        logging.basicConfig(level=logging.ERROR, format=log_format)
    return args

def __parse_configuration_file():
    if options['--config-file'] != None:
        with open(options['--config-file']) as config_file:
            globals()['config'] = json.load(config_file)
        ALIASES.language_aliases = globals()['config'].get('config', {}) \
                                .get('language aliases', {})
        ALIASES.device_type_aliases = globals()['config'].get('config', {}) \
                                .get('device type aliases', {})

    return globals()['config']


def flattenDictIndexes(dict):
    for indexKey, val in dict.items():
        if "-" in indexKey:
            startIndex, endIndex = indexKey.split("-")
            for i in range(int(startIndex), int(endIndex) + 1):
                dict[i] = val
            del dict[indexKey]
        else: 
            try:
                dict[int(indexKey)] = val
                del dict[indexKey]
            except:
                pass

    return dict


def main():
    os.umask(0077)
    if not os.path.exists(temp_dir):
        os.mkdir(temp_dir);

    args = __parse_options()

    logging.debug('Python %s' % sys.version)
    logging.debug('Running on %s' % platform.platform())
    logging.debug('Temp path = %s' % temp_dir)
    logging.debug('Current Directory = %s' % os.getcwd())

    logging.debug('args %s' % args)

    if options['--no-cookies'] or options['--store-password']:
        logging.debug('Deleting cookie file: ' + cookie_file)
        if os.path.exists(cookie_file):
            os.remove(cookie_file)
            cookie_jar.clear()
            logging.info('Removed authentication cookies')
        else:
            logging.debug('Cookie file doesn\'t exist')

    if options['--username'] == None:
        options['--username'] = raw_input('Username: ')

    if options['--delete-password']:
        keyring.delete_password(KEYRING_SERVICE_NAME, options['--username'])

    if options['--password'] == None:
        logging.debug('Looking for password in a secure storage. Username: ' + options['--username'])
        options['--password'] = keyring.get_password(KEYRING_SERVICE_NAME, options['--username'])

    server = ITCServer(options['--username'], options['--password'])

    if not server.isLoggedIn:
        if options['--password'] == None:
            options['--password'] = getpass.getpass()
        server.login(password = options['--password'])

    if server.isLoggedIn and options['--store-password']:
        keyring.set_password(KEYRING_SERVICE_NAME, options['--username'], options['--password'])

    if len(server.applications) == 0:
        server.fetchApplicationsList()

    if len(server.applications) == 0:
        logging.info('No applications found.')
        return
        
    if options['--application-id']:
        options['--application-id'] = int(options['--application-id'])


    if options['generate']:
        if options['--application-id']:
            if options['--application-id'] in server.applications: 
                applications = {}
                applications[options['--application-id']] = server.applications[options['--application-id']]
            else:
                logging.error('No application with id ' + str(options['--application-id']))
                return
        else:
            applications = server.applications

        for applicationId, application in applications.items():
            updatedApplication = server.getApplicationById(applicationId)
            updatedApplication.generateConfig(options['--application-version'], generateInapps = options['--generate-config-inapp'])

        return

    if options['promo']:
        if not options['--application-id'] in server.applications: 
            logging.error("Provide correct application id (--application-id or -a option)")
        else:
            application = server.getApplicationById(options['--application-id'])
            promocodes = application.getPromocodes(options['<amount>'])
            if options['--output-file']:
                with open(options['--output-file'], 'a') as outFile:
                    outFile.write(promocodes)
            else: # just print to console. Using print as we want to suppress silence option
                print promocodes

        return

    if options['reviews']:
        if not options['--application-id'] in server.applications: 
            logging.error("Provide correct application id (--application-id or -a option)")
        else:
            application = server.getApplicationById(options['--application-id'])
            application.generateReviews(options['--latest-version'], options['--date-range'], options['--output-file'])

        return

    cfg = __parse_configuration_file()
    if len(cfg) == 0:
        logging.info('Nothing to do.')
        return

    applicationDict = cfg['application']
    applicationId = applicationDict.get('id', -1)
    if options['--application-id']:
        applicationId = int(options['--application-id'])
    application = None
    commonActions = applicationDict.get('metadata', {}).get('general', {})
    specificLangCommands = applicationDict.get('metadata', {}).get('languages', {})
    langActions = {}
    filename_format = cfg.get('config', {}) \
                           .get('images', {}) \
                              .get('file name format', default_file_format)

    for lang in specificLangCommands:
        langActions[languages.languageNameForId(lang)] = dict_merge(commonActions, specificLangCommands[lang])

    logging.debug(langActions)

    if applicationId not in server.applications and not options['create']:
        logging.warning('No application with id ' + str(applicationId))
        choice = raw_input('Do you want to create a new one? [y/n]')
        options['create'] = True if choice.strip().lower() in ('y', 'yes', '') else False

    if options['create']:
        server.createNewApp(applicationDict, filename_format=filename_format)
    elif applicationId in server.applications:
        application = server.getApplicationById(applicationId)
        if options['version']:
            langActions['default'] = commonActions
            application.addVersion(applicationDict['version'], langActions)
        else:
            for lang in langActions:
                actions = langActions[lang]
                application.editVersion(actions, lang=lang, filename_format=filename_format)

            appReviewInfo = applicationDict.get('app review information', None)

            if appReviewInfo != None:
                application.editReviewInformation(appReviewInfo)

            for inappDict in applicationDict.get('inapps', {}):
                isIterable = inappDict['id'].find('{index}') != -1
                iteratorDict = inappDict.get('index iterator')

                if isIterable and (iteratorDict == None):
                    logging.error('Inapp id contains {index} keyword, but no index_iterator object found. Skipping inapp: ' + inappDict['id'])
                    continue

                langsDict = inappDict['languages']
                genericLangsDict = inappDict['general']

                for langId in langsDict:
                    langsDict[langId] = dict_merge(genericLangsDict, langsDict[langId])

                inappDict['languages'] = langsDict
                del inappDict['general']

                indexes = [-1]
                if (isIterable):
                    indexes = iteratorDict.get('indexes')
                    if indexes == None:
                        indexes = range(iteratorDict.get('from', 1), iteratorDict['to'] + 1)

                if iteratorDict != None:
                    del inappDict['index iterator']

                for key, value in inappDict.items():
                    if (not key in ("index iterator", "general", "languages")) and isinstance(value, dict):
                        flattenDictIndexes(value)

                for langKey, value in inappDict["languages"].items():
                    for innerLangKey, langValue in inappDict["languages"][langKey].items():
                        if isinstance(langValue, dict):
                            flattenDictIndexes(langValue)

                realindex = 0
                for index in indexes:
                    inappIndexDict = deepcopy(inappDict)
                    if isIterable:
                        for key in inappIndexDict:
                            if key in ("index iterator", "general", "languages"):
                                continue

                            if (isinstance(inappIndexDict[key], basestring)):
                                inappIndexDict[key] = inappIndexDict[key].replace('{index}', str(index))
                            elif (isinstance(inappIndexDict[key], list)):
                                inappIndexDict[key] = inappIndexDict[key][realindex]
                            elif (isinstance(inappIndexDict[key], dict)):
                                inappIndexDict[key] = inappIndexDict[key][index]

                        langsDict = inappIndexDict['languages']

                        for langId, langDict in langsDict.items():
                            for langKey in langDict:
                                if (isinstance(langDict[langKey], basestring)):
                                    langDict[langKey] = langDict[langKey].replace('{index}', str(index))
                                elif (isinstance(langDict[langKey], list)):
                                    langDict[langKey] = langDict[langKey][realindex]
                                elif (isinstance(langDict[langKey], dict)):
                                    langDict[langKey] = langDict[langKey][index]

                    inapp = application.getInappById(inappIndexDict['id'])
                    if inapp == None:
                        application.createInapp(inappIndexDict)
                    else:
                        inapp.update(inappIndexDict)

                    realindex += 1
    else:
        logging.error('No application with id ' + str(applicationId))
        return


########NEW FILE########
__FILENAME__ = review
# coding=utf-8

import logging

from itc.util import languages
from itc.conf import *

class ITCReview(object):
    def __init__(self, reviewId=None, authorName=None, text=None, store=None, rating=0, date=None):
        self.reviewId = reviewId
        self.authorName = authorName
        self.text = text
        self.store = store
        self.rating = rating
        self.date = date

        logging.debug('Review: ' + self.__str__())


    def __repr__(self):
        return self.__str__()


    def __str__(self):
        return self.authorName + " (" + self.store + ", " + self.date + ") " + str(self.rating) + "\n" + self.text


########NEW FILE########
__FILENAME__ = server
import os
import logging
from datetime import datetime

import requests

from itc.core.application import ITCApplication
from itc.parsers.serverparser import ITCServerParser
from itc.core.imageuploader import ITCImageUploader
from itc.util import languages
from itc.util import dataFromStringOrFile
from itc.conf import *

class ITCServer(ITCImageUploader):
    def __init__(self, username, password):
        super(ITCServer, self).__init__()

        self._info                  = {'username': username, 'password': password}
        self._loginPageURL          = ITUNESCONNECT_MAIN_PAGE_URL
        self._parser                = ITCServerParser()
        self.applications           = {}
        self.isLoggedIn             = self.__checkLogin()


    def __cleanup(self):
        if os.path.exists(cookie_file):
            os.remove(cookie_file)
        

    def __checkLogin(self, mainPageTree=None):
        if mainPageTree == None:
            mainPageTree = self._parser.parseTreeForURL(self._loginPageURL)

        if (mainPageTree == None) or (not self._parser.isLoggedIn(self.checkContinueButton(mainPageTree))):
            logging.debug('Check login: not logged in!')
            self.__cleanup()
            return False

        logging.debug('Check login: logged in!')
        return True


    def logout(self):
        if not self.isLoggedIn or not self._logoutURL:
            return

        self._parser.requests_session.get(ITUNESCONNECT_URL + self._logoutURL, cookies=cookie_jar)
        self.__cleanup()

    def checkContinueButton(self, mainPageTree):
        continueHref = self._parser.loginContinueButton(mainPageTree)
        if continueHref != None and config.options['-z']:
            mainPageTree = self._parser.parseTreeForURL(continueHref)
            self.isLoggedIn = self.__checkLogin(mainPageTree=mainPageTree);
        elif continueHref != None:
            raise Exception('Cannot continue: There\'s a form after login, which needs your attention.\n\t\tPlease, use -z command line option in order to suppress this check and automatically continue.')

        return mainPageTree

    def login(self, login=None, password=None):
        if self.isLoggedIn:
            logging.debug('Login: already logged in')
            return

        tree = self._parser.parseTreeForURL(self._loginPageURL)
        forms = tree.xpath("//form")

        if len(forms) == 0:
            raise
        
        form = forms[0]
        actionURL = form.attrib['action']
        payload = {'theAccountName': (self._info['username'] if login == None else login)
                 , 'theAccountPW': (self._info['password'] if password == None else password)
                 , '1.Continue.x': 60
                 , '1.Continue.y': 27
                 , 'theAuxValue': ''}

        mainPageTree = self._parser.parseTreeForURL(actionURL, method="POST", payload=payload)

        self.isLoggedIn = self.__checkLogin(mainPageTree=mainPageTree);
        if not self.isLoggedIn:
            mainPageTree = self.checkContinueButton(mainPageTree)

        if self.isLoggedIn:
            logging.info("Login: logged in. Session cookies are saved to " + cookie_file)
            # logging.debug(cookie_jar)
            cookie_jar.save(cookie_file, ignore_discard=True)
        else:
            raise Exception('Cannot continue: login failed. Please check username/password')

    def getApplicationById(self, applicationId):
        if not self.isLoggedIn:
            raise Exception('Get applications list: not logged in')
        
        applicationData = self._parser.getApplicationDataById(applicationId)
        application = None
        if (applicationData != None):
            name = applicationData.name
            link = applicationData.link
            applicationId = applicationData.applicationId

            application = ITCApplication(name=name, applicationId=applicationId, link=link)
        
        return application

    def fetchApplicationsList(self):
        if not self.isLoggedIn:
            raise Exception('Get applications list: not logged in')

        applicationsData = self._parser.getApplicationsData()
        for applicationData in applicationsData:
            name = applicationData.name
            link = applicationData.link
            applicationId = applicationData.applicationId

            application = ITCApplication(name=name, applicationId=applicationId, link=link)
            self.applications[applicationId] = application

    def __manageCountries(self, serverCountries, countries, formData):
        include = countries \
            and isinstance(countries, dict) \
            and 'type' in countries and countries['type'] == 'include' \
            and 'list' in countries
        exclude = countries \
            and isinstance(countries, dict) \
            and 'type' in countries and countries['type'] == 'exclude' \
            and 'list' in countries

        if include:
            for country in countries['list']:
                logging.debug("Including " + country)
                formData[serverCountries[country]] = serverCountries[country]
        else:
            for country, val in serverCountries.items():
                if not exclude or country not in countries['list']:
                    formData[val] = val
                else:
                    logging.debug("Excluding " + country)


    def createNewApp(self, appDictionary=None, filename_format=None):
        if appDictionary == None or len(appDictionary) == 0 or 'new app' not in appDictionary: # no data to create app from
            return

        newAppMetadata = appDictionary['new app']
        metadata = self._parser.parseFirstAppCreatePageForm()
        formData = {}
        formNames = metadata.formNames
        submitAction = metadata.submitAction
        
        formData[formNames['default language']] = metadata.languageIds[languages.languageNameForId(newAppMetadata['default language'])]
        formData[formNames['app name']]         = newAppMetadata['name']
        formData[formNames['sku number']]       = newAppMetadata['sku number']
        formData[formNames['bundle id suffix']] = newAppMetadata['bundle id suffix']
        formData[formNames['bundle id']]        = next(value for (key, value) in metadata.bundleIds.iteritems() if key.endswith(' - ' + newAppMetadata['bundle id']))
        
        formData[formNames['continue action'] + '.x'] = "0"
        formData[formNames['continue action'] + '.y'] = "0"

        logging.debug(formData)
        secondPageTree = self._parser.parseTreeForURL(submitAction, method="POST", payload=formData)
        errors = self._parser.checkPageForErrors(secondPageTree)

        if errors != None and len(errors) != 0:
            for error in errors:
                logging.error(error)

            return

        metadata = self._parser.parseSecondAppCreatePageForm(secondPageTree)
        formData = {}
        formNames = metadata.formNames
        submitAction = metadata.submitAction
        date = datetime.strptime(newAppMetadata['availability date'], '%b %d %Y')

        formData[formNames['date day']]   = date.day - 1
        formData[formNames['date month']] = date.month - 1
        formData[formNames['date year']]  = date.year - datetime.today().year
        formData[formNames['price tier']] = newAppMetadata['price tier']
        if 'discount' in newAppMetadata and newAppMetadata['discount']:
            formData[formNames['discount']] = formNames['discount']

        if 'countries' in newAppMetadata:
            self.__manageCountries(metadata.countries, newAppMetadata['countries'], formData)

        formData[formNames['continue action'] + '.x'] = "0"
        formData[formNames['continue action'] + '.y'] = "0"

        thirdPageTree = self._parser.parseTreeForURL(submitAction, method="POST", payload=formData)
        errors = self._parser.checkPageForErrors(thirdPageTree)

        if errors != None and len(errors) != 0:
            for error in errors:
                logging.error(error)

            return

        metadata = self._parser.parseThirdAppCreatePageForm(thirdPageTree, fetchSubcategories=newAppMetadata['primary category'])
        
        formData = {}
        formNames = metadata.formNames

        iconUploadScreenshotForm    = formNames['iconUploadScreenshotForm'] 
        iphoneUploadScreenshotForm  = formNames['iphoneUploadScreenshotForm'] 
        iphone5UploadScreenshotForm = formNames['iphone5UploadScreenshotForm']
        ipadUploadScreenshotForm    = formNames['ipadUploadScreenshotForm']
        tfUploadForm                = formNames['tfUploadForm']

        iconUploadScreenshotJS    = iconUploadScreenshotForm.xpath('../following-sibling::script/text()')[0]
        iphoneUploadScreenshotJS  = iphoneUploadScreenshotForm.xpath('../following-sibling::script/text()')[0]
        iphone5UploadScreenshotJS = iphone5UploadScreenshotForm.xpath('../following-sibling::script/text()')[0]
        ipadUploadScreenshotJS    = ipadUploadScreenshotForm.xpath('../following-sibling::script/text()')[0]
        tfUploadJS                = tfUploadForm.xpath('../following-sibling::script/text()')[0]

        self._uploadSessionData['icon'] = dict({'action': iconUploadScreenshotForm.attrib['action']
                                                        , 'key': iconUploadScreenshotForm.xpath(".//input[@name='uploadKey']/@value")[0]
                                                      }, **self.parseStatusURLSFromScript(iconUploadScreenshotJS))
        self._uploadSessionData[DEVICE_TYPE.iPhone] = dict({'action': iphoneUploadScreenshotForm.attrib['action']
                                                        , 'key': iphoneUploadScreenshotForm.xpath(".//input[@name='uploadKey']/@value")[0]
                                                      }, **self.parseURLSFromScript(iphoneUploadScreenshotJS))
        self._uploadSessionData[DEVICE_TYPE.iPhone5] = dict({'action': iphone5UploadScreenshotForm.attrib['action']
                                                         , 'key': iphone5UploadScreenshotForm.xpath(".//input[@name='uploadKey']/@value")[0]
                                                       }, **self.parseURLSFromScript(iphone5UploadScreenshotJS))
        self._uploadSessionData[DEVICE_TYPE.iPad] = dict({'action': ipadUploadScreenshotForm.attrib['action']
                                                      , 'key': ipadUploadScreenshotForm.xpath(".//input[@name='uploadKey']/@value")[0]
                                                    }, **self.parseURLSFromScript(ipadUploadScreenshotJS))
        self._uploadSessionData['tf'] = dict({'action': tfUploadForm.attrib['action']
                                                      , 'key': tfUploadForm.xpath(".//input[@name='uploadKey']/@value")[0]
                                                    }, **self.parseStatusURLSFromScript(tfUploadJS))

        self._uploadSessionId = iphoneUploadScreenshotForm.xpath('.//input[@name="uploadSessionID"]/@value')[0]

        for device_type in ['icon', DEVICE_TYPE.iPhone, DEVICE_TYPE.iPhone5, DEVICE_TYPE.iPad]:
            self._images[device_type] = self.imagesForDevice(device_type)

        logging.debug(self._images)

        #uploading icon
        self.uploadScreenshot('icon', newAppMetadata['large app icon']['file name format'])
        self._images['icon'] = self.imagesForDevice('icon')

        screenshots = newAppMetadata['screenshots']
        replace_language = ALIASES.language_aliases.get(newAppMetadata['default language'], newAppMetadata['default language'])
        langImagePath = filename_format.replace('{language}', replace_language)

        for dType, indexes in screenshots.items():
            device_type = None
            if dType.lower() == 'iphone':
                device_type = DEVICE_TYPE.iPhone
            elif dType.lower() == 'iphone 5':
                device_type = DEVICE_TYPE.iPhone5
            elif dType.lower() == 'ipad':
                device_type = DEVICE_TYPE.iPad

            replace_device = ALIASES.device_type_aliases.get(dType.lower(), DEVICE_TYPE.deviceStrings[device_type])

            imagePath = langImagePath.replace('{device_type}', replace_device)
            logging.info('Looking for images at ' + imagePath)

            for i in indexes:
                realImagePath = imagePath.replace("{index}", str(i))
                self.uploadScreenshot(device_type, realImagePath)
            self._images[device_type] = self.imagesForDevice(device_type)

        formData[formNames['version number']] = newAppMetadata['version']
        formData[formNames['copyright']] = newAppMetadata['copyright']
        formData[formNames['primary category']] = metadata.categories[newAppMetadata['primary category']]

        if metadata.subcategories != None and len(metadata.subcategories) != 0:
            if 'primary subcategory 1' in newAppMetadata:
                formData[formNames['primary subcategory 1']] = metadata.subcategories[newAppMetadata['primary subcategory 1']]
            if 'primary subcategory 2' in newAppMetadata:
                formData[formNames['primary subcategory 2']] = metadata.subcategories[newAppMetadata['primary subcategory 2']]
            if 'secondary subcategory 1' in newAppMetadata:
                formData[formNames['secondary subcategory 1']] = metadata.subcategories[newAppMetadata['secondary subcategory 1']]
            if 'secondary subcategory 2' in newAppMetadata:
                formData[formNames['secondary subcategory 2']] = metadata.subcategories[newAppMetadata['secondary subcategory 2']]

        if 'secondary category' in newAppMetadata:
            formData[formNames['secondary category']] = metadata.categories[newAppMetadata['secondary category']]

        appRatings = metadata.appRatings

        for index, rating in enumerate(newAppMetadata['app rating']):
            formData[appRatings[index]['name']] = appRatings[index]['ratings'][rating]

        if 'eula text' in newAppMetadata:
            formData[formNames['eula text']] = dataFromStringOrFile(newAppMetadata['eula text'])
            if 'eula countries' in newAppMetadata:
                self.__manageCountries(metadata.eulaCountries, newAppMetadata['eula countries'], formData)

        formData[formNames['description']] = dataFromStringOrFile(newAppMetadata['description'])
        formData[formNames['keywords']] = dataFromStringOrFile(newAppMetadata['keywords'])
        formData[formNames['support url']] = newAppMetadata['support url']
        formData[formNames['marketing url']] = newAppMetadata.get('marketing url')
        formData[formNames['privacy policy url']] = newAppMetadata.get('privacy policy url')

        appReviewInfo = appDictionary['app review information']
        formData[formNames['first name']] = appReviewInfo['first name']
        formData[formNames['last name']] = appReviewInfo['last name']
        formData[formNames['email address']] = appReviewInfo['email address']
        formData[formNames['phone number']] = appReviewInfo['phone number']
        formData[formNames['review notes']] = dataFromStringOrFile(appReviewInfo.get('review notes'))
        formData[formNames['username']] = appReviewInfo.get('demo username')
        formData[formNames['password']] = appReviewInfo.get('demo password')

        finalPageTree = self._parser.parseTreeForURL(metadata.submitAction, method="POST", payload=formData)
        errors = self._parser.checkPageForErrors(finalPageTree)

        if errors != None and len(errors) != 0:
            for error in errors:
                logging.error(error)
        else:
            idText = finalPageTree.xpath("//div[@id='column-bg']/div/p/label[.='Apple ID']/../span/text()")
            if len(idText) > 0:
                logging.info('Successfully created application. ID: ' + idText[0])

########NEW FILE########
__FILENAME__ = applicationparser
# coding=utf-8

import logging
import re
from collections import namedtuple
from datetime import datetime

from itc.parsers.baseparser import BaseParser
from itc.util import getElement
from itc.util import languages

class ITCApplicationParser(BaseParser):
    def __init__(self):
        super(ITCApplicationParser, self).__init__()

    
    def parseAppVersionsPage(self, htmlTree):
        AppVersions = namedtuple('AppVersions', ['manageInappsLink', 'customerReviewsLink', 'addVersionLink', 'versions'])

        # get 'manage in-app purchases' link
        manageInappsLink = htmlTree.xpath("//ul[@id='availableButtons']/li/a[.='Manage In-App Purchases']/@href")[0]
        customerReviewsLinkTree = htmlTree.xpath("//td[@class='value']/a[.='Customer Reviews']/@href")
        customerReviewsLink = None
        if (len(customerReviewsLinkTree) > 0):
            customerReviewsLink = customerReviewsLinkTree[0]
        logging.debug("Manage In-App purchases link: " + manageInappsLink)
        logging.debug("Customer reviews link: " + manageInappsLink)

        versionsContainer = htmlTree.xpath("//h2[.='Versions']/following-sibling::div")
        if len(versionsContainer) == 0:
            return AppVersions(manageInappsLink=manageInappsLink, customerReviewsLink=customerReviewsLink, versions={})

        versionDivs = versionsContainer[0].xpath(".//div[@class='version-container']")
        if len(versionDivs) == 0:
            return AppVersions(manageInappsLink=manageInappsLink, customerReviewsLink=customerReviewsLink, versions={})

        versions = {}
        addVersionLink = None

        for versionDiv in versionDivs:
            version = {}            
            versionString = versionDiv.xpath(".//p/label[.='Version']/../span")

            if len(versionString) == 0: # Add version
                addVersionLink = versionDiv.xpath(".//a[.='Add Version']/@href")[0]
                logging.debug('Add version link: ' + addVersionLink)
                continue
            
            versionString = versionString[0].text.strip()
            version['detailsLink'] = versionDiv.xpath(".//a[.='View Details']/@href")[0]
            version['statusString'] = ("".join([str(x) for x in versionDiv.xpath(".//span/img[starts-with(@src, '/itc/images/status-')]/../text()")])).strip()
            version['editable'] = (version['statusString'] != 'Ready for Sale')
            version['versionString'] = versionString

            logging.info("Version found: " + versionString)
            logging.debug(version)

            versions[versionString] = version

        return AppVersions(manageInappsLink=manageInappsLink, customerReviewsLink=customerReviewsLink
                            , addVersionLink=addVersionLink, versions=versions)


    def parseCreateOrEditPage(self, htmlTree, version, language=None):
        tree = htmlTree

        AppMetadata = namedtuple('AppMetadata', ['activatedLanguages', 'nonactivatedLanguages'
                                                , 'formData', 'formNames', 'submitActions'])

        localizationLightboxAction = tree.xpath("//div[@id='localizationLightbox']/@action")[0] # if no lang provided, edit default
        #localizationLightboxUpdateAction = tree.xpath("//span[@id='localizationLightboxUpdate']/@action")[0] 

        activatedLanguages    = tree.xpath('//div[@id="modules-dropdown"] \
                                    /ul/li[count(preceding-sibling::li[@class="heading"])=1]/a/text()')
        nonactivatedLanguages = tree.xpath('//div[@id="modules-dropdown"] \
                                    /ul/li[count(preceding-sibling::li[@class="heading"])=2]/a/text()')
        
        activatedLanguages = [lng.replace("(Default)", "").strip() for lng in activatedLanguages]

        logging.info('Activated languages: ' + ', '.join(activatedLanguages))
        logging.debug('Nonactivated languages: ' + ', '.join(nonactivatedLanguages))

        langs = activatedLanguages

        if language != None:
            langs = [language]

        formData = {}
        formNames = {}
        submitActions = {}
        versionString = version['versionString']

        for lang in langs:
            logging.info('Processing language: ' + lang)
            languageId = languages.appleLangIdForLanguage(lang)
            logging.debug('Apple language id: ' + languageId)

            if lang in activatedLanguages:
                logging.info('Getting metadata for ' + lang + '. Version: ' + versionString)
            elif lang in nonactivatedLanguages:
                logging.info('Add ' + lang + ' for version ' + versionString)

            editTree = self.parseTreeForURL(localizationLightboxAction + "?open=true" 
                                                    + ("&language=" + languageId if (languageId != None) else ""))
            hasWhatsNew = False

            formDataForLang = {}
            formNamesForLang = {}

            submitActionForLang = editTree.xpath("//div[@class='lcAjaxLightboxContentsWrapper']/div[@class='lcAjaxLightboxContents']/@action")[0]

            formNamesForLang['appNameName'] = editTree.xpath("//div[@id='appNameUpdateContainerId']//input/@name")[0]
            formNamesForLang['descriptionName'] = editTree.xpath("//div[@id='descriptionUpdateContainerId']//textarea/@name")[0]
            whatsNewName = editTree.xpath("//div[@id='whatsNewinthisVersionUpdateContainerId']//textarea/@name")

            if len(whatsNewName) > 0: # there's no what's new section for first version
                hasWhatsNew = True
                formNamesForLang['whatsNewName'] = whatsNewName[0]

            formNamesForLang['keywordsName']     = editTree.xpath("//div/label[.='Keywords']/..//input/@name")[0]
            formNamesForLang['supportURLName']   = editTree.xpath("//div/label[.='Support URL']/..//input/@name")[0]
            formNamesForLang['marketingURLName'] = editTree.xpath("//div/label[contains(., 'Marketing URL')]/..//input/@name")[0]
            formNamesForLang['pPolicyURLName']   = editTree.xpath("//div/label[contains(., 'Privacy Policy URL')]/..//input/@name")[0]

            formDataForLang['appNameValue']     = editTree.xpath("//div[@id='appNameUpdateContainerId']//input/@value")[0]
            formDataForLang['descriptionValue'] = getElement(editTree.xpath("//div[@id='descriptionUpdateContainerId']//textarea/text()"), 0)
            whatsNewValue    = editTree.xpath("//div[@id='whatsNewinthisVersionUpdateContainerId']//textarea/text()")

            if len(whatsNewValue) > 0 and hasWhatsNew:
                formDataForLang['whatsNewValue'] = getElement(whatsNewValue, 0)

            formDataForLang['keywordsValue']     = getElement(editTree.xpath("//div/label[.='Keywords']/..//input/@value"), 0)
            formDataForLang['supportURLValue']   = getElement(editTree.xpath("//div/label[.='Support URL']/..//input/@value"), 0)
            formDataForLang['marketingURLValue'] = getElement(editTree.xpath("//div/label[contains(., 'Marketing URL')]/..//input/@value"), 0)
            formDataForLang['pPolicyURLValue']   = getElement(editTree.xpath("//div/label[contains(., 'Privacy Policy URL')]/..//input/@value"), 0)

            logging.debug("Old values:")
            logging.debug(formDataForLang)

            iphoneUploadScreenshotForm = editTree.xpath("//form[@name='FileUploadForm_35InchRetinaDisplayScreenshots']")[0]
            iphone5UploadScreenshotForm = editTree.xpath("//form[@name='FileUploadForm_iPhone5']")[0]
            ipadUploadScreenshotForm = editTree.xpath("//form[@name='FileUploadForm_iPadScreenshots']")[0]

            formNamesForLang['iphoneUploadScreenshotForm'] = iphoneUploadScreenshotForm
            formNamesForLang['iphone5UploadScreenshotForm'] = iphone5UploadScreenshotForm
            formNamesForLang['ipadUploadScreenshotForm'] = ipadUploadScreenshotForm

            formData[languageId] = formDataForLang
            formNames[languageId] = formNamesForLang
            submitActions[languageId] = submitActionForLang

        metadata = AppMetadata(activatedLanguages=activatedLanguages
                             , nonactivatedLanguages=nonactivatedLanguages
                             , formData=formData
                             , formNames=formNames
                             , submitActions=submitActions)

        return metadata

    def parseAppReviewInfoForm(self, tree):
        logging.info('Updating application review information')

        AppReviewInfo = namedtuple('AppReviewInfo', ['formData', 'formNames', 'submitAction'])

        appReviewLightboxAction = tree.xpath("//div[@id='reviewInfoLightbox']/@action")[0]
        editTree = self.parseTreeForURL(appReviewLightboxAction + "?open=true")

        formNames = {}
        formData = {}

        formNames['first name']       = editTree.xpath("//div/label[.='First Name']/..//input/@name")[0]
        formNames['last name']        = editTree.xpath("//div/label[.='Last Name']/..//input/@name")[0]
        formNames['email address']    = editTree.xpath("//div/label[.='Email Address']/..//input/@name")[0]
        formNames['phone number']     = editTree.xpath("//div/label[.='Phone Number']/..//input/@name")[0]

        formNames['review notes']     = editTree.xpath("//div[@id='reviewnotes']//textarea/@name")[0]

        formNames['username']         = editTree.xpath("//div/label[.='Username']/..//input/@name")[0]
        formNames['password']         = editTree.xpath("//div/label[.='Password']/..//input/@name")[0]

        formData['first name']        = getElement(editTree.xpath("//div/label[.='First Name']/..//input/@value"), 0)
        formData['last name']         = getElement(editTree.xpath("//div/label[.='Last Name']/..//input/@value"), 0)
        formData['email address']     = getElement(editTree.xpath("//div/label[.='Email Address']/..//input/@value"), 0)
        formData['phone number']      = getElement(editTree.xpath("//div/label[.='Phone Number']/..//input/@value"), 0)
        formData['review notes']      = getElement(editTree.xpath("//div[@id='reviewnotes']//textarea/@value"), 0)
        formData['username']          = getElement(editTree.xpath("//div/label[.='Username']/..//input/@value"), 0)
        formData['password']          = getElement(editTree.xpath("//div/label[.='Password']/..//input/@value"), 0)

        submitAction = editTree.xpath("//div[@class='lcAjaxLightboxContentsWrapper']/div[@class='lcAjaxLightboxContents']/@action")[0]

        metadata = AppReviewInfo(formData=formData
                               , formNames=formNames
                               , submitAction=submitAction)
        return metadata

    def parseAddVersionPageMetadata(self, htmlTree):
        AddVersionPageInfo = namedtuple('AddVersionPageInfo', ['formNames', 'submitAction', 'saveButton'])
        formNames = {'languages': {}}

        formNames['version'] = htmlTree.xpath("//div/label[.='Version Number']/..//input/@name")[0]
        defaultLanguage = htmlTree.xpath("//div[@class='app-info-container app-landing app-version']//h2/strong/text()")[0]
        formNames['languages'][defaultLanguage] = htmlTree.xpath("//div[@id='whatsNewinthisVersionUpdateContainerId']//textarea/@name")[0]
        
        otherLanguages = htmlTree.xpath("//span[@class='metadataField metadataFieldReadonly']/textarea/../..")
        for langDiv in otherLanguages:
            lang = langDiv.xpath(".//label/text()")[0]
            taName = langDiv.xpath(".//span/textarea/@name")[0]
            formNames['languages'][lang] = taName

        submitAction = htmlTree.xpath('//form[@name="mainForm"]/@action')[0]
        saveButton = htmlTree.xpath('//input[@class="saveChangesActionButton"]/@name')[0]

        metadata = AddVersionPageInfo(formNames=formNames
                                     , submitAction=submitAction
                                     , saveButton=saveButton)

        return metadata

    def getPromocodesLink(self, htmlTree):
        link = htmlTree.xpath("//a[.='Promo Codes']")
        if len(link) == 0:
            raise('Cannot find "Promo Codes" button.')

        return link[0].attrib['href'].strip()

    def parsePromocodesPageMetadata(self, tree):
        PromoPageInfo = namedtuple('PromoPageInfo', ['amountName', 'continueButton', 'submitAction'])
        amountName = getElement(tree.xpath("//td[@class='metadata-field-code']/input/@name"), 0).strip()
        continueButton = tree.xpath("//input[@class='continueActionButton']/@name")[0].strip()
        submitAction = tree.xpath('//form[@name="mainForm"]/@action')[0]
        metadata = PromoPageInfo(amountName=amountName
                               , continueButton=continueButton
                               , submitAction=submitAction)

        return metadata

    def parsePromocodesLicenseAgreementPage(self, pageText):
        tree = self.parser.parse(pageText)
        PromoPageInfo = namedtuple('PromoPageInfo', ['agreeTickName', 'continueButton', 'submitAction'])
        agreeTickName = getElement(tree.xpath("//input[@type='checkbox']/@name"), 0).strip()
        continueButton = tree.xpath("//input[@class='continueActionButton']/@name")[0].strip()
        submitAction = tree.xpath('//form[@name="mainForm"]/@action')[0]
        metadata = PromoPageInfo(agreeTickName=agreeTickName
                               , continueButton=continueButton
                               , submitAction=submitAction)

        return metadata

    def getDownloadCodesLink(self, pageText):
        tree = self.parser.parse(pageText)
        link = tree.xpath("//img[@alt='Download Codes']/../@href")
        if len(link) == 0:
            raise('Cannot find "Download Codes" button.')

        return link[0].strip()

    def getReviewsPageMetadata(self, tree):
        noReviews = tree.xpath('//div[@class="no-reviews"]')
        if len(noReviews) > 0:
            return None

        ReviewsPageInfo = namedtuple('ReviewsPageInfo', ['countries', 'countriesSelectName', 'countryFormSubmitAction', 'allVersions', 'currentVersion', 'allReviews'])
        countriesSelectName = tree.xpath('//select/@name')[0].strip()
        countriesSelect = tree.xpath('//select/option')
        countries = {}
        for countryOption in countriesSelect:
            countries[countryOption.text.strip()] = countryOption.attrib['value']

        countryFormSubmitAction = tree.xpath('//form/@action')[0]
        allVersionsLink = tree.xpath('//div[@class="button-container"]//a')[0].attrib['href'].strip()
        currentVersionLink = tree.xpath('//div[@class="button-container"]//a')[1].attrib['href'].strip()
        allReviewsLink = tree.xpath('//span[@class="paginatorBatchSizeList"]//a[.="All"]')[0].attrib['href'].strip()

        metadata = ReviewsPageInfo(countries=countries
                                 , countriesSelectName=countriesSelectName
                                 , allVersions=allVersionsLink
                                 , currentVersion=currentVersionLink
                                 , allReviews=allReviewsLink
                                 , countryFormSubmitAction=countryFormSubmitAction)

        return metadata

    def parseReviews(self, pageText, minDate=None, maxDate=None):
        tree = self.parser.parse(pageText)
        reviewDivs = tree.xpath('//div[@class="reviews-container"]')
        
        if len(reviewDivs) == 0:
            return None

        reviews = []
        totalMark = 0

        for reviewDiv in reviewDivs:
            review = {} 
            reviewerString = getElement(reviewDiv.xpath('./p[@class="reviewer"]'), 0).text.strip()
            regexp = re.compile('by\s+(.*)-\sVersion(.*)-\s*(.*)', re.DOTALL)
            m = regexp.search(reviewerString)
            review['reviewer'] = m.group(1).strip()
            review['version'] = m.group(2).strip()
            review['date'] = m.group(3).strip()
            reviewDate = datetime.strptime(review['date'], '%b %d, %Y')
            if minDate != None and reviewDate < minDate:
                break
            if maxDate != None and reviewDate > maxDate:
                continue

            title = getElement(reviewDiv.xpath('./p[@class="reviewer-title"]'), 0).text.strip()
            review['title'] = title.replace(u'★', '').strip()
            review['mark'] = len(title.replace(review['title'], '').strip())
            totalMark = totalMark + review['mark']

            review['text'] = getElement(reviewDiv.xpath('./p[@class="review-text"]'), 0).text.strip()
            reviews.append(review)

        return reviews, totalMark

########NEW FILE########
__FILENAME__ = baseparser
import logging

import requests
from bs4 import BeautifulSoup

from itc.parsers import htmlParser
from itc.conf import *

class BaseParser(object):
    parser = None
    requests_session = None
    def __init__(self):
        self.requests_session = requests.session()
        self.parser = htmlParser

    def parseTreeForURL(self, url, method="GET", payload=None, debugPrint=False):
        response = None
        if method == "GET":
            response = self.requests_session.get(ITUNESCONNECT_URL + url, cookies=cookie_jar)
        elif method == "POST":
            response = self.requests_session.post(ITUNESCONNECT_URL + url, payload, cookies=cookie_jar)

        if response == None:
            raise

        if debugPrint or config.options['--verbose'] == 2:
            if config.options['-f']:
                logging.debug(BeautifulSoup(response.content).prettify())
            elif debugPrint:
                logging.info(BeautifulSoup(response.content).prettify())
            else:
                logging.debug(response.content)

        if response.status_code != 200:
            logging.error('Wrong response from itunesconnect. Status code: ' + str(response.status_code) + '. Content:\n' + response.text)
            return None

        return self.parser.parse(response.text)
########NEW FILE########
__FILENAME__ = inappparser
import logging 
from collections import namedtuple

from itc.parsers.baseparser import BaseParser
from itc.util import languages

class ITCInappParser(BaseParser):
    def __init__(self):
        super(ITCInappParser, self).__init__()


    def metadataForInappPurchase(self, htmlTree):
        InappMetadata = namedtuple('InappMetadata', ['refname', 'cleared', 'languages', 'textid', 'numericid', 'price_tier', 'reviewnotes', 'hosted'])

        inappReferenceName = htmlTree.xpath('//span[@id="iapReferenceNameUpdateContainer"]//span/text()')[0].strip()
        textId = htmlTree.xpath('//div[@id="productIdText"]//span/text()')[0].strip()
        numericId = htmlTree.xpath('//label[.="Apple ID: "]/following-sibling::span/text()')[0].strip()
        hostedContent = len(htmlTree.xpath('//div[contains(@class,"hosted-content")]/following-sibling::p')) > 0
        reviewNotes = htmlTree.xpath('//div[@class="hosted-review-notes"]//span/text()')[0].strip()

        clearedForSaleText = htmlTree.xpath('//div[contains(@class,"cleared-for-sale")]//span/text()')[0]
        clearedForSale = False
        if clearedForSaleText == 'Yes':
            clearedForSale = True

        inapptype = htmlTree.xpath('//div[@class="status-label"]//span/text()')[0].strip()
        priceTier = None

        if inapptype != "Free Subscription":
            priceTier = htmlTree.xpath('//tr[@id="interval-row-0"]//a/text()')[0].strip().split(' ')
            priceTier = int(priceTier[-1])

        idAddon = "autoRenewableL" if (inapptype == "Free Subscription") else "l"
        languagesSpan = htmlTree.xpath('//span[@id="0' + idAddon + 'ocalizationListListRefreshContainerId"]')[0]
        activatedLanguages = languagesSpan.xpath('.//li[starts-with(@id, "0' + idAddon + 'ocalizationListRow")]/div[starts-with(@class, "ajaxListRowDiv")]/@itemid')
        activatedLangsIds = [languages.langCodeForLanguage(lang) for lang in activatedLanguages]
        languageAction = htmlTree.xpath('//div[@id="0' + idAddon + 'ocalizationListLightbox"]/@action')[0]

        # logging.info('Activated languages for inapp ' + self.numericId + ': ' + ', '.join(activatedLanguages))
        logging.debug('Activated languages ids: ' + ', '.join(activatedLangsIds))
        metadataLanguages = {}

        for langId in activatedLangsIds:
            metadataLanguages[langId] = {}
            languageParamStr = "&itemID=" + languages.appleLangIdForLanguage(langId)
            localizationTree = self.parseTreeForURL(languageAction + "?open=true" + languageParamStr)
            metadataLanguages[langId]['name'] = localizationTree.xpath('//div[@id="proposedDisplayName"]//input/@value')[0]
            metadataLanguages[langId]['description'] = localizationTree.xpath('//div[@id="proposedDescription"]//textarea/text()')[0].strip()
    
            localizedPublicationName = localizationTree.xpath('//div[@id="proposedPublicationName"]//input/@value')
            if len(localizedPublicationName) > 0:
                metadataLanguages[langId]['publication name'] = localizedPublicationName[0]

        return InappMetadata(refname=inappReferenceName
                            , cleared=clearedForSale
                            , languages=metadataLanguages
                            , price_tier=priceTier
                            , textid=textId
                            , numericid=int(numericId)
                            , hosted=hostedContent
                            , reviewnotes=reviewNotes)


########NEW FILE########
__FILENAME__ = serverparser
import logging
from collections import namedtuple

from itc.parsers.baseparser import BaseParser
import pprint

ApplicationData = namedtuple('SessionURLs', ['name', 'applicationId', 'link'])

class ITCServerParser(BaseParser):
    def __init__(self):
        self._manageAppsURL         = None
        self._createAppURL          = None
        self._getApplicationListURL = None
        self._logoutURL             = None
        super(ITCServerParser, self).__init__()


    def isLoggedIn(self, htmlTree):
        usernameInput = htmlTree.xpath("//input[@id='accountname']")
        passwordInput = htmlTree.xpath("//input[@id='accountpassword']")

        if not ((len(usernameInput) == 1) and (len(passwordInput) == 1)):
            try:
                self.parseSessionURLs(htmlTree)
            except:
                return False
            return True

        return False


    def parseSessionURLs(self, htmlTree):
        manageAppsLink = htmlTree.xpath("//a[.='Manage Your Apps']")
        if len(manageAppsLink) == 0:
            raise

        signOutLink = htmlTree.xpath("//li[contains(@class, 'sign-out')]/a[.='Sign Out']")
        if len(signOutLink) == 0:
            raise

        self._manageAppsURL = manageAppsLink[0].attrib['href']
        self._logoutURL = signOutLink[0].attrib['href']

        logging.debug('manage apps url: ' + self._manageAppsURL)
        logging.debug('logout url: ' + self._logoutURL)


    def __getInternalURLs(self):
        tree = self.parseTreeForURL(self._manageAppsURL)

        seeAllDiv = tree.xpath("//div[@class='seeAll']")[0]
        seeAllLink = seeAllDiv.xpath(".//a[starts-with(., 'See All')]")

        if len(seeAllLink) == 0:
            raise

        self._getApplicationListURL = seeAllLink[0].attrib['href']

        createAppLink = tree.xpath("//span[@class='upload-app-button']/a")

        if len(createAppLink) == 0:
            raise

        self._createAppURL = createAppLink[0].attrib['href']

    def getApplicationDataById(self, _applicationId):
        if self._manageAppsURL == None:
            raise Exception('Get applications list: not logged in')

        if not self._getApplicationListURL:
            self.__getInternalURLs()

        result = None
        nextLink = self._getApplicationListURL;
        while (nextLink != None):
            appsTree = self.parseTreeForURL(nextLink)
            nextLinkDiv = appsTree.xpath("//td[@class='previous']")
            if len(nextLinkDiv) > 0:
                nextLink = nextLinkDiv[0].xpath(".//a[contains(., ' Previous')]/@href")[0]
            else:
                nextLink = None

        nextLink = self._getApplicationListURL;
        while (nextLink != None) and (result == None):
            appsTree = self.parseTreeForURL(nextLink)
            applicationRows = appsTree.xpath("//div[@id='software-result-list'] \
                            /div[@class='resultList']/table/tbody/tr[not(contains(@class, 'column-headers'))]")
            for applicationRow in applicationRows:
                tds = applicationRow.xpath("td")
                applicationId = int(tds[4].xpath(".//p")[0].text.strip())
                if (applicationId == _applicationId):
                    nameLink = tds[0].xpath(".//a")
                    name = nameLink[0].text.strip()
                    link = nameLink[0].attrib["href"]
                    result = ApplicationData(name=name, link=link, applicationId=applicationId)
                    break;

            nextLinkDiv = appsTree.xpath("//td[@class='next']")
            if len(nextLinkDiv) > 0:
                nextLink = nextLinkDiv[0].xpath(".//a[starts-with(., ' Next')]/@href")[0]
            else:
                nextLink = None

        return result

    def getApplicationsData(self):
        if self._manageAppsURL == None:
            raise Exception('Get applications list: not logged in')

        if not self._getApplicationListURL:
            self.__getInternalURLs()

        result = []
        nextLink = self._getApplicationListURL;
        while nextLink!=None:
            appsTree = self.parseTreeForURL(nextLink)
            applicationRows = appsTree.xpath("//div[@id='software-result-list'] \
                            /div[@class='resultList']/table/tbody/tr[not(contains(@class, 'column-headers'))]")
            for applicationRow in applicationRows:
                tds = applicationRow.xpath("td")
                nameLink = tds[0].xpath(".//a")
                name = nameLink[0].text.strip()
                link = nameLink[0].attrib["href"]
                applicationId = int(tds[4].xpath(".//p")[0].text.strip())
                result.append(ApplicationData(name=name, link=link, applicationId=applicationId))

            nextLinkDiv = appsTree.xpath("//td[@class='next']")
            if len(nextLinkDiv) > 0:
                nextLink = nextLinkDiv[0].xpath(".//a[starts-with(., ' Next')]/@href")[0]
            else:
                nextLink = None

        return result

    def parseFirstAppCreatePageForm(self):
        if self._manageAppsURL == None:
            raise Exception('Create application: not logged in')

        if not self._createAppURL:
            self.__getInternalURLs()

        formNames = {}
        AppMetadata = namedtuple('AppMetadata', ['formNames', 'submitAction', 'languageIds', 'bundleIds', 'selectedLanguageId'])

        createAppTree = self.parseTreeForURL(self._createAppURL)
        createAppForm = createAppTree.xpath("//form[@id='mainForm']")[0]
        submitAction = createAppForm.attrib['action']

        formNames['default language'] = createAppForm.xpath("//select[@id='default-language-popup']/@name")[0]
        formNames['app name']         = createAppForm.xpath("//div/label[.='App Name']/..//input/@name")[0]
        formNames['sku number']       = createAppForm.xpath("//div/label[.='SKU Number']/..//input/@name")[0]
        formNames['bundle id']        = createAppForm.xpath("//select[@id='primary-popup']/@name")[0]
        formNames['bundle id suffix'] = createAppForm.xpath("//div/label[.='Bundle ID Suffix']/..//input/@name")[0]
        formNames['continue action']  = createAppForm.xpath("//input[@class='continueActionButton']/@name")[0]

        languageIds = {}
        languageIdOptions = createAppForm.xpath("//select[@id='default-language-popup']/option")
        selectedLanguageId = '-1'
        for langIdOption in languageIdOptions:
            if langIdOption.text.strip() != 'Select':
                languageIds[langIdOption.text.strip()] = langIdOption.attrib['value']
                if 'selected' in langIdOption.attrib:
                    selectedLanguageId = langIdOption.attrib['value']


        bundleIds = {}
        bundleIdOptions = createAppForm.xpath("//select[@id='primary-popup']/option")
        for bundIdOption in bundleIdOptions:
            if bundIdOption.text.strip() != 'Select':
                bundleIds[bundIdOption.text.strip()] = bundIdOption.attrib['value']

        metadata = AppMetadata(formNames=formNames
                             , submitAction=submitAction
                             , languageIds=languageIds
                             , bundleIds=bundleIds
                             , selectedLanguageId=selectedLanguageId)

        return metadata

    def parseSecondAppCreatePageForm(self, createAppTree):
        formNames = {}
        AppMetadata = namedtuple('AppMetadata', ['formNames', 'submitAction', 'countries'])

        createAppForm = createAppTree.xpath("//form[@id='mainForm']")[0]
        submitAction = createAppForm.attrib['action']

        formNames['date day']   = createAppForm.xpath("//span[@class='date-select-day']/select/@name")[0]
        formNames['date month'] = createAppForm.xpath("//span[@class='date-select-month']/select/@name")[0]
        formNames['date year']  = createAppForm.xpath("//span[@class='date-select-year']/select/@name")[0]
        formNames['price tier'] = createAppForm.xpath("//span[@id='pricingTierUpdateContainer']/select/@name")[0]
        formNames['discount']   = createAppForm.xpath("//input[@id='education-checkbox']/@name")[0]
        formNames['continue action']  = createAppForm.xpath("//input[@class='continueActionButton']/@name")[0]

        countries = {}
        countryInputs = createAppForm.xpath("//table[@id='countries-list']//input[@class='country-checkbox']/../..")
        for countryInput in countryInputs:
            countries[countryInput.xpath("td")[0].text.strip()] = countryInput.xpath("td/input[@class='country-checkbox']")[0].attrib['value']

        metadata = AppMetadata(formNames=formNames
                             , submitAction=submitAction
                             , countries=countries)

        return metadata

    def parseThirdAppCreatePageForm(self, htmlTree, fetchSubcategories=False):
        formNames = {}
        AppMetadata = namedtuple('AppMetadata', ['formNames', 'submitAction', 'categories', 'subcategories', 'appRatings', 'eulaCountries'])
        
        versionForm = htmlTree.xpath("//form[@id='versionInitForm']")[0]
        submitAction = versionForm.attrib['action']
        formNames['version number'] = versionForm.xpath("//div[@id='versionNumberTooltipId']/../input/@name")[0]
        formNames['copyright'] = versionForm.xpath("//div[@id='copyrightTooltipId']/../input/@name")[0]
        formNames['primary category'] = versionForm.xpath("//select[@id='version-primary-popup']/@name")[0]
        formNames['primary subcategory 1'] = versionForm.xpath("//select[@id='primary-first-popup']/@name")[0]
        formNames['primary subcategory 2'] = versionForm.xpath("//select[@id='primary-second-popup']/@name")[0]
        formNames['secondary category'] = versionForm.xpath("//select[@id='version-secondary-popup']/@name")[0]
        formNames['secondary subcategory 1'] = versionForm.xpath("//select[@id='secondary-first-popup']/@name")[0]
        formNames['secondary subcategory 2'] = versionForm.xpath("//select[@id='secondary-second-popup']/@name")[0]
        categories = {}
        subcategories = None

        categoryOptions = versionForm.xpath("//select[@id='version-primary-popup']/option")
        for categoryOption in categoryOptions:
            if categoryOption.text.strip() != 'Select':
                categories[categoryOption.text.strip()] = categoryOption.attrib['value']

        if fetchSubcategories:
            categoryId = categories[fetchSubcategories];
            subcategoriesURL = htmlTree.xpath('//span[@id="primaryCategoryContainer"]/@action')[0]
            formData = {'viaLCAjaxContainer':'true'}
            formData[formNames['primary category']] = categoryId
            formData[formNames['primary subcategory 1']] = 'WONoSelectionString'
            formData[formNames['primary subcategory 2']] = 'WONoSelectionString'

            subcategoriesTree = self.parseTreeForURL(subcategoriesURL, method="POST", payload=formData)
            subcategoryOptions = subcategoriesTree.xpath("//select[@id='primary-first-popup']/option")
            subcategories = {}
            for categoryOption in subcategoryOptions:
                if categoryOption.text.strip() != 'Select':
                    subcategories[categoryOption.text.strip()] = categoryOption.attrib['value']

        appRatings = []
        appRatingTable = versionForm.xpath('//tr[@id="game-ratings"]/td/table/tbody/tr')

        for ratingTr in appRatingTable:
            inputs = ratingTr.xpath('.//input')
            if len(inputs) < 2:
                continue
            appRating = {'name': inputs[0].attrib['name'], 'ratings': []}
            for inpt in inputs:
                appRating['ratings'].append(inpt.attrib['value'])
            appRatings.append(appRating)

        formNames['description'] = versionForm.xpath("//div[@id='descriptionUpdateContainerId']/div/span/textarea/@name")[0]
        formNames['keywords'] = versionForm.xpath("//div[@id='keywordsTooltipId']/../input/@name")[0]
        formNames['support url'] = versionForm.xpath("//div[@id='supportURLTooltipId']/../input/@name")[0]
        formNames['marketing url'] = versionForm.xpath("//div[@id='marketingURLOptionalTooltipId']/../input/@name")[0]
        formNames['privacy policy url'] = versionForm.xpath("//div[@id='privacyPolicyURLTooltipId']/../input/@name")[0]

        formNames['first name'] = versionForm.xpath("//div/label[.='First Name']/../span/input/@name")[0]
        formNames['last name'] = versionForm.xpath("//div/label[.='Last Name']/../span/input/@name")[0]
        formNames['email address'] = versionForm.xpath("//div/label[.='Email Address']/../span/input/@name")[0]
        formNames['phone number'] = versionForm.xpath("//div/label[.='Phone Number']/../span/input/@name")[0]
        formNames['review notes'] = versionForm.xpath("//div[@id='reviewnotes']/div/span/textarea/@name")[0]
        formNames['username'] = versionForm.xpath("//div/label[.='Username']/../span/input/@name")[0]
        formNames['password'] = versionForm.xpath("//div/label[.='Password']/../span/input/@name")[0]

        formNames['eula text'] = versionForm.xpath("//textarea[@id='eula-text']/@name")[0]
        eulaCountries = {}
        countryDivs = versionForm.xpath("//div[@class='country group']")
        for countryDiv in countryDivs:
            name = countryDiv.xpath("./div[@class='country-name']")[0].text.strip()
            eulaCountries[name] = countryDiv.xpath("./div[@class='country-check-box']/input[@class='country-checkbox']")[0].attrib['value']

        iconUploadScreenshotForm = versionForm.xpath("//form[@name='FileUploadForm_largeAppIcon']")[0]
        iphoneUploadScreenshotForm = versionForm.xpath("//form[@name='FileUploadForm_35InchRetinaDisplayScreenshots']")[0]
        iphone5UploadScreenshotForm = versionForm.xpath("//form[@name='FileUploadForm_iPhone5']")[0]
        ipadUploadScreenshotForm = versionForm.xpath("//form[@name='FileUploadForm_iPadScreenshots']")[0]
        tfUploadForm = versionForm.xpath("//form[@name='FileUploadForm_tfUploader']")[0]

        formNames['iconUploadScreenshotForm'] = iconUploadScreenshotForm
        formNames['iphoneUploadScreenshotForm'] = iphoneUploadScreenshotForm
        formNames['iphone5UploadScreenshotForm'] = iphone5UploadScreenshotForm
        formNames['ipadUploadScreenshotForm'] = ipadUploadScreenshotForm
        formNames['tfUploadForm'] = tfUploadForm

        metadata = AppMetadata(formNames=formNames
                             , submitAction=submitAction
                             , categories=categories
                             , subcategories=subcategories
                             , eulaCountries=eulaCountries
                             , appRatings=appRatings)

        return metadata

    def checkPageForErrors(self, htmlTree):
        errors = htmlTree.xpath("//div[@id='LCPurpleSoftwarePageWrapperErrorMessage']/div/ul/li/span/text()")

        return errors

    def loginContinueButton(self, htmlTree):
        continueButtonLink = htmlTree.xpath("//img[@class='customActionButton']/..")
        if len(continueButtonLink) == 0:
            return None

        return continueButtonLink[0].attrib['href']

########NEW FILE########
__FILENAME__ = languages
import json
import logging

languages_map = {}

def __parse_languages_map():
    try:
        try:
             import pkgutil
             data = pkgutil.get_data(__name__, 'languages.json')
        except ImportError:
             import pkg_resources
             data = pkg_resources.resource_string(__name__, 'languages.json')
        globals()['languages_map'] = json.loads(data)
    except BaseException:
        raise 

def __langs():
    if globals()['languages_map'] == None or len(globals()['languages_map']) == 0:
        __parse_languages_map()
        logging.debug(globals()['languages_map'])

    return globals()['languages_map']

def appleLangIdForLanguage(languageString):
    """
    returns apple language id (i.e. 'French_CA') for language name 
    (i.e. 'Canadian French') or code (i.e. 'fr-CA')
    """
    lang = __langs().get(languageString)
    if lang != None:
        if type(lang) is dict:
            return lang['name']

        return lang

    for langId, lang in __langs().items():
        if type(lang) is dict:
            if lang['name'] == languageString:
                return lang['id']
        else:
            if lang == languageString:
                return lang
                
    return None

def langCodeForLanguage(languageString):
    """
    returns language code (i.e. 'fr-CA') for language name 
    (i.e. 'Canadian French') or apple language id (i.e. 'French_CA')
    """
    for langId, lang in __langs().items():
        if type(lang) is dict:
            if (lang['name'] == languageString) or (lang['id'] == languageString):
                return langId
        else:
            if lang == languageString:
                return langId
                
    return None

def languageNameForId(languageId):
    lang = __langs()[languageId]
    if type(lang) is dict:
        return lang['name']

    return lang

########NEW FILE########
