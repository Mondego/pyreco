__FILENAME__ = best_match
import urllib2
from lxml import etree

from utils import get_config_store


def findBestMatchItemDetailsAcrossStores(
        keywords,
        siteResultsPerPage,
        categoryId=None,
        entriesPerPage=None,
        ignoreFeatured=None,
        itemFilter=None,
        outputSelector=None,
        postSearchItemFilter=None,
        postSearchSellerFilter=None,
        encoding="JSON"):
    root = etree.Element("findBestMatchItemDetailsAcrossStoresRequest",
                         xmlns="http://www.ebay.com/marketplace/search/v1/services")
    root = get_generic_tags(
        root=root,
        keywords=keywords,
        siteResultsPerPage=siteResultsPerPage,
        categoryId=categoryId,
        entriesPerPage=entriesPerPage,
        ignoreFeatured=ignoreFeatured,
        itemFilter=itemFilter,
        outputSelector=outputSelector,
        postSearchItemFilter=postSearchItemFilter,
        postSearchSellerFilter=postSearchSellerFilter)

    request = etree.tostring(root, pretty_print=True)
    return get_response(findBestMatchItemDetailsAcrossStores.__name__, request, encoding)


def findBestMatchItemDetailsAdvanced(
        keywords,
        siteResultsPerPage,
        categoryId=None,
        entriesPerPage=None,
        ignoreFeatured=None,
        itemFilter=None,
        outputSelector=None,
        postSearchItemFilter=None,
        postSearchSellerFilter=None,
        encoding="JSON"):
    root = etree.Element("findBestMatchItemDetailsAdvancedRequest",
                         xmlns="http://www.ebay.com/marketplace/search/v1/services")
    root = get_generic_tags(
        root=root,
        keywords=keywords,
        siteResultsPerPage=siteResultsPerPage,
        categoryId=categoryId,
        entriesPerPage=entriesPerPage,
        ignoreFeatured=ignoreFeatured,
        itemFilter=itemFilter,
        outputSelector=outputSelector,
        postSearchItemFilter=postSearchItemFilter,
        postSearchSellerFilter=postSearchSellerFilter)

    request = etree.tostring(root, pretty_print=True)
    return get_response(findBestMatchItemDetailsAdvanced.__name__, request, encoding)


def findBestMatchItemDetailsByCategory(
        categoryId,
        siteResultsPerPage,
        entriesPerPage=None,
        ignoreFeatured=None,
        itemFilter=None,
        outputSelector=None,
        postSearchItemFilter=None,
        postSearchSellerFilter=None,
        encoding="JSON"):
    root = etree.Element("findBestMatchItemDetailsByCategoryRequest",
                         xmlns="http://www.ebay.com/marketplace/search/v1/services")
    root = get_generic_tags(
        root=root,
        categoryId=categoryId,
        siteResultsPerPage=siteResultsPerPage,
        entriesPerPage=entriesPerPage,
        ignoreFeatured=ignoreFeatured,
        itemFilter=itemFilter,
        outputSelector=outputSelector,
        postSearchItemFilter=postSearchItemFilter,
        postSearchSellerFilter=postSearchSellerFilter)

    request = etree.tostring(root, pretty_print=True)
    return get_response(findBestMatchItemDetailsByCategory.__name__, request, encoding)


def findBestMatchItemDetailsByKeywords(
        keywords,
        siteResultsPerPage,
        entriesPerPage=None,
        ignoreFeatured=None,
        itemFilter=None,
        outputSelector=None,
        postSearchItemFilter=None,
        postSearchSellerFilter=None,
        encoding="JSON"):
    root = etree.Element("root", xmlns="http://www.ebay.com/marketplace/search/v1/services")
    root = get_generic_tags(
        root=root,
        keywords=keywords,
        siteResultsPerPage=siteResultsPerPage,
        entriesPerPage=entriesPerPage,
        ignoreFeatured=ignoreFeatured,
        itemFilter=itemFilter,
        outputSelector=outputSelector,
        postSearchItemFilter=postSearchItemFilter,
        postSearchSellerFilter=postSearchItemFilter)

    request = etree.tostring(root, pretty_print=True)
    return get_response(findBestMatchItemDetailsByKeywords.__name__, request, encoding)


def findBestMatchItemDetailsByProduct(
        productId,
        siteResultsPerPage,
        entriesPerPage=None,
        ignoreFeatured=None,
        itemFilter=None,
        outputSelector=None,
        postSearchItemFilter=None,
        postSearchSellerFilter=None,
        encoding="JSON"):
    root = etree.Element("findBestMatchItemDetailsByProductRequest",
                         xmlns="http://www.ebay.com/marketplace/search/v1/services")
    root = get_generic_tags(
        root=root,
        productId=productId,
        siteResultsPerPage=siteResultsPerPage,
        entriesPerPage=entriesPerPage,
        ignoreFeatured=ignoreFeatured,
        itemFilter=itemFilter,
        outputSelector=outputSelector,
        postSearchItemFilter=postSearchItemFilter,
        postSearchSellerFilter=postSearchItemFilter)

    request = etree.tostring(root, pretty_print=True)
    return get_response(findBestMatchItemDetailsByProduct.__name__, request, encoding)


def findBestMatchItemDetailsBySeller(
        categoryId,
        sellerUserName,
        ignoreFeatured=None,
        itemFilter=None,
        paginationInput=None,
        encoding="JSON"):
    root = etree.Element("findBestMatchItemDetailsBySellerRequest",
                         xmlns="http://www.ebay.com/marketplace/search/v1/services")

    categoryId_elem = etree.SubElement(root, "categoryId")
    categoryId_elem.text = categoryId

    sellerUserName_elem = etree.SubElement(root, "sellerUserName")
    sellerUserName_elem.text = sellerUserName

    if ignoreFeatured:
        ignoreFeatured_elem = etree.SubElement(root, "ignoreFeatured")
        ignoreFeatured_elem.text = ignoreFeatured

    # itemFilter is a List of dicts: [{
    # "paramName" : "PriceMin",
    # "paramValue" : "50",
    # "name" : "Currency",
    # "value" : "USD"}]


    for item_filter in itemFilter:
        if len(item_filter) > 0:
            itemFilter_elem = etree.SubElement(root, "itemFilter")
            for key in item_filter.keys():
                item_elem = etree.SubElement(itemFilter_elem, key)
                item_elem.text = item_filter[key]

    # paginationInput is a dict: {entriesPerPage:5, pageNumber:10}
    if paginationInput and len(paginationInput) > 0:
        paginationInput_elem = etree.SubElement(root, "paginationInput")
        for key in paginationInput.keys():
            input_values_elem = etree.SubElement(paginationInput_elem, key)
            input_values_elem.text = paginationInput[key]

    request = etree.tostring(root, pretty_print=True)
    return get_response(findBestMatchItemDetailsBySeller.__name__, request, encoding)


#Not working
def findBestMatchItemDetails(encoding="JSON"):
    request = """<?xml version="1.0" encoding="utf-8"?>
<getBestMatchItemDetailsRequest xmlns="http://www.ebay.com/marketplace/search/v1/services">
  <itemId>13474073440</itemId>
  <itemId>23484479761</itemId>
</getBestMatchItemDetailsRequest>"""

    return get_response(findBestMatchItemDetails.__name__, request, encoding)


def getVersion():
    root = etree.Element("getVersionRequest", xmlns="http://www.ebay.com/marketplace/search/v1/services")
    request = etree.tostring(root, pretty_print=True)

    return get_response(getVersion.__name__, request, encoding="JSON")


def get_generic_tags(root, siteResultsPerPage, productId=None,
                     keywords=None, categoryId=None, entriesPerPage=None,
                     ignoreFeatured=None, itemFilter=None, outputSelector=None,
                     postSearchItemFilter=None,
                     postSearchSellerFilter=None):
    siteResultsPerPage_elem = etree.SubElement(root, "siteResultsPerPage")
    siteResultsPerPage_elem.text = siteResultsPerPage

    if keywords:
        keywords_elem = etree.SubElement(root, "keywords")
        keywords_elem.text = keywords

    if entriesPerPage:
        entriesPerPage_elem = etree.SubElement(root, "entriesPerPage")
        entriesPerPage_elem.text = entriesPerPage

    if ignoreFeatured:
        ignoreFeatured_elem = etree.SubElement(root, "ignoreFeatured")
        ignoreFeatured_elem.text = ignoreFeatured

    if categoryId:
        categoryId_elem = etree.SubElement(root, "categoryId")
        categoryId_elem.text = categoryId

    if productId:
        productId_elem = etree.SubElement(root, "productId")
        productId_elem.text = productId

    #itemFilter is a List of dicts: [{paramName=PriceMin, paramValue=50, name=Currency, value=USD}]
    for item_filter in itemFilter:
        if len(item_filter) > 0:
            itemFilter_elem = etree.SubElement(root, "itemFilter")
            for key in item_filter.keys():
                item_elem = etree.SubElement(itemFilter_elem, key)
                item_elem.text = item_filter[key]

    #outputSelector is a List
    if outputSelector and len(outputSelector) > 0:
        for output_selector in outputSelector:
            outputSelector_elem = etree.SubElement(root, "outputSelector")
            outputSelector_elem.text = output_selector

    # postSearchItemFilter is a List
    if postSearchItemFilter and len(postSearchItemFilter) > 0:
        postSearchItemFilter_elem = etree.SubElement(root, "postSearchItemFilter")
        for item_filter in postSearchItemFilter:
            itemId_elem = etree.SubElement(postSearchItemFilter_elem, "itemId")
            itemId_elem.text = item_filter

    # postSearchSellerFilter is a List
    if postSearchSellerFilter and len(postSearchSellerFilter) > 0:
        postSearchSellerFilter_elem = etree.SubElement(root, "postSearchSellerFilter")
        for seller in postSearchSellerFilter:
            seller_elem = etree.SubElement(postSearchSellerFilter_elem, "sellerUserName")
            seller_elem.text = seller

    return root


def get_response(operation_name, data, encoding, **headers):
    config = get_config_store()
    access_token = config.get("auth", "token")
    endpoint = config.get("endpoints", "best_match")

    http_headers = {"X-EBAY-SOA-OPERATION-NAME": operation_name,
                    "X-EBAY-SOA-SECURITY-TOKEN": access_token,
                    "X-EBAY-SOA-RESPONSE-DATA-FORMAT": encoding}

    http_headers.update(headers)

    req = urllib2.Request(endpoint, data, http_headers)
    res = urllib2.urlopen(req)
    return res.read()

########NEW FILE########
__FILENAME__ = client_alerts
import requests
from utils import get_config_store


def GetPublicAlerts(ChannelID, ChannelType, EventType,
                    MessageID=None, LastRequestTime=None,
                    encoding="JSON"):
    user_param = {
        'callname': GetPublicAlerts.__name__,
        'ChannelDescriptor(0).ChannelID': ChannelID,
        'ChannelDescriptor(0).ChannelType': ChannelType,
        'ChannelDescriptor(0).EventType': EventType,
        'responseencoding': encoding}

    if MessageID:
        user_param.update({"MessageID": MessageID})

    if LastRequestTime:
        user_param.update({"LastRequestTime": LastRequestTime})

    response = get_response(user_param)
    return response.content


def GetUserAlerts(SessionID, SessionData, MessageID=None, encoding="JSON"):
    user_param = {
        'callname': GetUserAlerts.__name__,
        'SessionData': SessionData,
        'SessionID': SessionID,
        'responseencoding': encoding}

    if MessageID:
        user_param.update({"MessageID": MessageID})

    response = get_response(user_param)
    return response.content


def Login(ClientAlertsAuthToken, MessageID=None, encoding="JSON"):
    user_param = {
        'callname': Login.__name__,
        'ClientAlertsAuthToken': ClientAlertsAuthToken,
        'responseencoding': encoding}

    if MessageID:
        user_param.update({"MessageID": MessageID})

    response = get_response(user_param)
    return response.content


def Logout(SessionID, SessionData, MessageID=None, encoding="JSON"):
    user_param = {
        'callname': Logout.__name__,
        'SessionData': SessionData,
        'SessionID': SessionID,
        'responseencoding': encoding}

    if MessageID:
        user_param.update({"MessageID": MessageID})

    response = get_response(user_param)
    return response.content


def get_response(user_params):
    config = get_config_store()
    app_id = config.get("keys", "app_name")
    site_id = config.get("call", "siteid")
    version = config.get("call", "compatibility_level")
    endpoint = config.get("endpoints", "client_alerts")

    d = dict(appid=app_id, siteid=site_id, version=version)
    d.update(user_params)

    return requests.get(endpoint, params=d)
########NEW FILE########
__FILENAME__ = feedback
import urllib2
from lxml import etree

from utils import get_config_store


def createDSRSummaryByCategory(
        categoryId, dateRangeFrom,
        dateRangeTo, dateRangeEventType=None,
        encoding="JSON"):
    root = etree.Element("createDSRSummaryByCategoryRequest",
                         xmlns="http://www.ebay.com/marketplace/services")

    #categoryId is a List
    for cat_id in categoryId:
        categoryId_elem = etree.SubElement(root, "categoryId")
        categoryId_elem.text = cat_id

    dateRange_elem = etree.SubElement(root, "dateRange")
    dateRangeFrom_elem = etree.SubElement(dateRange_elem, "dateFrom")
    dateRangeFrom_elem.text = dateRangeFrom

    dateRangeTo_elem = etree.SubElement(dateRange_elem, "dateTo")
    dateRangeTo_elem.text = dateRangeTo

    if dateRangeEventType:
        dateRangeEventType_elem = etree.SubElement(root, "dateRangeEventType")
        dateRangeEventType_elem.text = dateRangeEventType

    request = etree.tostring(root, pretty_print=True)
    return get_response(createDSRSummaryByCategory.__name__, request, encoding)


def createDSRSummaryByPeriod(
        dateRangeFrom, dateRangeTo,
        dateRangeEventType=None, encoding="JSON"):
    root = etree.Element("createDSRSummaryByPeriodRequest",
                         xmlns="http://www.ebay.com/marketplace/services")

    dateRange_elem = etree.SubElement(root, "dateRange")
    dateRangeFrom_elem = etree.SubElement(dateRange_elem, "dateFrom")
    dateRangeFrom_elem.text = dateRangeFrom

    dateRangeTo_elem = etree.SubElement(dateRange_elem, "dateTo")
    dateRangeTo_elem.text = dateRangeTo

    if dateRangeEventType:
        dateRangeEventType_elem = etree.SubElement(root, "dateRangeEventType")
        dateRangeEventType_elem.text = dateRangeEventType

    request = etree.tostring(root, pretty_print=True)
    return get_response(createDSRSummaryByPeriod.__name__, request, encoding)


def createDSRSummaryByShippingDetail(
        dateRangeFrom, dateRangeTo,
        dateRangeEventType=None, shippingCostType=None,
        shippingDestinationType=None, shippingService=None,
        shipToCountry=None, encoding="JSON"):
    root = etree.Element("createDSRSummaryByShippingDetailRequest",
                         xmlns="http://www.ebay.com/marketplace/services")

    dateRange_elem = etree.SubElement(root, "dateRange")
    dateRangeFrom_elem = etree.SubElement(dateRange_elem, "dateFrom")
    dateRangeFrom_elem.text = dateRangeFrom

    dateRangeTo_elem = etree.SubElement(dateRange_elem, "dateTo")
    dateRangeTo_elem.text = dateRangeTo

    if dateRangeEventType:
        dateRangeEventType_elem = etree.SubElement(root, "dateRangeEventType")
        dateRangeEventType_elem.text = dateRangeEventType

    if shippingCostType:
        shippingCostType_elem = etree.SubElement(root, "shippingCostType")
        shippingCostType_elem.text = shippingCostType

    if shippingDestinationType:
        shippingDestinationType_elem = etree.SubElement(root, "shippingDestinationType")
        shippingDestinationType_elem.text = shippingDestinationType

    #shippingService is a List
    if shippingService and len(shippingService) > 0:
        for service in shippingService:
            shippingService_elem = etree.SubElement(root, "shippingService")
            shippingService_elem.text = shippingService

    #shipToCountry is a List
    for country in shipToCountry:
        shipToCountry_elem = etree.SubElement(root, "shipToCountry")
        shipToCountry_elem.text = shipToCountry

    request = etree.tostring(root, pretty_print=True)
    return get_response(createDSRSummaryByShippingDetail.__name__, request, encoding)


#making transactionId required here, but it's not in the eBay API. Will fix it later
#transactionId is a list of dicts: [{itemId:123, transactionId:72}, {itemId:33, transactionId:21}]
def createDSRSummaryByTransaction(transactionKey, encoding="JSON"):
    root = etree.Element("createDSRSummaryByTransactionRequest",
                         xmlns="http://www.ebay.com/marketplace/services")

    for t in transactionKey:
        transactionKey_elem = etree.SubElement(root, "transactionKey")

        for key in t.keys():
            itemId_elem = etree.SubElement(transactionKey_elem, key)
            itemId_elem.text = t[key]

    request = etree.tostring(root, pretty_print=True)
    return get_response(createDSRSummaryByTransaction.__name__, request, encoding)


def getDSRSummary(jobId, encoding="JSON"):
    root = etree.Element("getDSRSummaryRequest",
                         xmlns="http://www.ebay.com/marketplace/services")

    jobId_elem = etree.SubElement(root, "jobId")
    jobId_elem.text = jobId

    request = etree.tostring(root, pretty_print=True)
    return get_response(getDSRSummary.__name__, request, encoding)


def get_response(operation_name, data, encoding, **headers):
    config = get_config_store()
    access_token = config.get("auth", "token")
    endpoint = config.get("endpoints", "feedback")

    http_headers = {
        "X-EBAY-SOA-OPERATION-NAME": operation_name,
        "X-EBAY-SOA-SECURITY-TOKEN": access_token,
        "X-EBAY-SOA-RESPONSE-DATA-FORMAT": encoding}

    http_headers.update(headers)

    req = urllib2.Request(endpoint, data, http_headers)
    res = urllib2.urlopen(req)
    return res.read()

########NEW FILE########
__FILENAME__ = finding
import urllib2
from lxml import etree

from utils import get_config_store


def getSearchKeywordsRecommendation(keywords, encoding="JSON"):
    root = etree.Element("getSearchKeywordsRecommendation",
                         xmlns="http://www.ebay.com/marketplace/search/v1/services")
    keywords_elem = etree.SubElement(root, "keywords")
    keywords_elem.text = keywords

    request = etree.tostring(root, pretty_print=True)
    return get_response(getSearchKeywordsRecommendation.__name__, request, encoding)


def findItemsByKeywords(
        keywords, affiliate=None,
        buyerPostalCode=None, paginationInput=None,
        sortOrder=None, aspectFilter=None,
        domainFilter=None, itemFilter=None,
        outputSelector=None, encoding="JSON"):
    root = etree.Element("findItemsByKeywords",
                         xmlns="http://www.ebay.com/marketplace/search/v1/services")

    keywords_elem = etree.SubElement(root, "keywords")
    keywords_elem.text = keywords

    #affiliate is a dict
    if affiliate:
        affiliate_elem = etree.SubElement(root, "affiliate")
        for key in affiliate:
            key_elem = etree.SubElement(affiliate_elem, key)
            key_elem.text = affiliate[key]

    if buyerPostalCode:
        buyerPostalCode_elem = etree.SubElement(root, "buyerPostalCode")
        buyerPostalCode_elem.text = buyerPostalCode

    #paginationInput is a dict
    if paginationInput:
        paginationInput_elem = etree.SubElement(root, "paginationInput")
        for key in paginationInput:
            key_elem = etree.SubElement(paginationInput_elem, key)
            key_elem.text = paginationInput[key]

    #itemFilter is a list of dicts
    if itemFilter:
        for item in itemFilter:
            itemFilter_elem = etree.SubElement(root, "itemFilter")
            for key in item:
                key_elem = etree.SubElement(itemFilter_elem, key)
                key_elem.text = item[key]

    #sortOrder
    if sortOrder:
        sortOrder_elem = etree.SubElement(root, "sortOrder")
        sortOrder_elem.text = sortOrder

    #aspectFilter is a list of dicts
    for item in aspectFilter:
        aspectFilter_elem = etree.SubElement(root, "aspectFilter")
        for key in item:
            key_elem = etree.SubElement(aspectFilter_elem, key)
            key_elem.text = item[key]

    #domainFilter is a list of dicts
    for item in domainFilter:
        domainFilter_elem = etree.SubElement(root, "domainFilter")
        for key in item:
            key_elem = etree.SubElement(domainFilter_elem, key)
            key_elem.text = item[key]

    #outputSelector is a list
    for item in outputSelector:
        outputSelector_elem = etree.SubElement(root, "outputSelector")
        outputSelector_elem.text = item

    request = etree.tostring(root, pretty_print=True)
    return get_response(findItemsByKeywords.__name__, request, encoding)


def findItemsByCategory(
        categoryId, affiliate=None,
        buyerPostalCode=None, sortOrder=None,
        paginationInput=None, aspectFilter=None,
        domainFilter=None, itemFilter=None,
        outputSelector=None, encoding="JSON"):
    root = etree.Element("findItemsByCategory",
                         xmlns="http://www.ebay.com/marketplace/search/v1/services")

    categoryId_elem = etree.SubElement(root, "categoryId")
    categoryId_elem.text = categoryId

    #affiliate is a dict
    if affiliate:
        affiliate_elem = etree.SubElement(root, "affiliate")
        for key in affiliate:
            key_elem = etree.SubElement(affiliate_elem, key)
            key_elem.text = affiliate[key]

    if buyerPostalCode:
        buyerPostalCode_elem = etree.SubElement(root, "buyerPostalCode")
        buyerPostalCode_elem.text = buyerPostalCode

    #paginationInput is a dict
    if paginationInput:
        paginationInput_elem = etree.SubElement(root, "paginationInput")
        for key in paginationInput:
            key_elem = etree.SubElement(paginationInput_elem, key)
            key_elem.text = paginationInput[key]

    #itenFilter is a list of dicts
    for item in itemFilter:
        itemFilter_elem = etree.SubElement(root, "itemFilter")
        for key in item:
            key_elem = etree.SubElement(itemFilter_elem, key)
            key_elem.text = item[key]

    #sortOrder
    if sortOrder:
        sortOrder_elem = etree.SubElement(root, "sortOrder")
        sortOrder_elem.text = sortOrder

    #aspectFilter is a list of dicts
    for item in aspectFilter:
        aspectFilter_elem = etree.SubElement(root, "aspectFilter")
        for key in item:
            key_elem = etree.SubElement(aspectFilter_elem, key)
            key_elem.text = item[key]

    #domainFilter is a list of dicts
    for item in domainFilter:
        domainFilter_elem = etree.SubElement(root, "domainFilter")
        for key in item:
            key_elem = etree.SubElement(domainFilter_elem, key)
            key_elem.text = item[key]

    #outputSelector is a list
    for item in outputSelector:
        outputSelector_elem = etree.SubElement(root, "outputSelector")
        outputSelector_elem.text = item

    request = etree.tostring(root, pretty_print=True)
    return get_response(findItemsByCategory.__name__, request, encoding)


def findItemsAdvanced(
        keywords=None, categoryId=None,
        affiliate=None, buyerPostalCode=None,
        paginationInput=None, sortOrder=None,
        aspectFilter=None, domainFilter=None,
        itemFilter=None, outputSelector=None,
        encoding="JSON"):
    root = etree.Element("findItemsAdvanced",
                         xmlns="http://www.ebay.com/marketplace/search/v1/services")

    if keywords:
        keywords_elem = etree.SubElement(root, "keywords")
        keywords_elem.text = keywords

    if categoryId:
        categoryId_elem = etree.SubElement(root, "categoryId")
        categoryId_elem.text = categoryId

    #affiliate is a dict
    if affiliate:
        affiliate_elem = etree.SubElement(root, "affiliate")
        for key in affiliate:
            key_elem = etree.SubElement(affiliate_elem, key)
            key_elem.text = affiliate[key]

    if buyerPostalCode:
        buyerPostalCode_elem = etree.SubElement(root, "buyerPostalCode")
        buyerPostalCode_elem.text = buyerPostalCode

    #paginationInput is a dict
    if paginationInput:
        paginationInput_elem = etree.SubElement(root, "paginationInput")
        for key in paginationInput:
            key_elem = etree.SubElement(paginationInput_elem, key)
            key_elem.text = paginationInput[key]

    #itenFilter is a list of dicts

    for item in itemFilter:
        itemFilter_elem = etree.SubElement(root, "itemFilter")
        for key in item:
            key_elem = etree.SubElement(itemFilter_elem, key)
            key_elem.text = item[key]

    #sortOrder
    if sortOrder:
        sortOrder_elem = etree.SubElement(root, "sortOrder")
        sortOrder_elem.text = sortOrder

    #aspectFilter is a list of dicts
    for item in aspectFilter:
        aspectFilter_elem = etree.SubElement(root, "aspectFilter")
        for key in item:
            key_elem = etree.SubElement(aspectFilter_elem, key)
            key_elem.text = item[key]

    #domainFilter is a list of dicts
    for item in domainFilter:
        domainFilter_elem = etree.SubElement(root, "domainFilter")
        for key in item:
            key_elem = etree.SubElement(domainFilter_elem, key)
            key_elem.text = item[key]

    #outputSelector is a list
    for item in outputSelector:
        outputSelector_elem = etree.SubElement(root, "outputSelector")
        outputSelector_elem.text = item

    request = etree.tostring(root, pretty_print=True)
    return get_response(findItemsAdvanced.__name__, request, encoding)


def findItemsByProduct(
        keywords=None, productId=None,
        affiliate=None, buyerPostalCode=None,
        paginationInput=None, sortOrder=None,
        itemFilter=None, outputSelector=None,
        encoding="JSON"):
    root = etree.Element("findItemsByProduct",
                         xmlns="http://www.ebay.com/marketplace/search/v1/services")

    if keywords:
        keywords_elem = etree.SubElement(root, "keywords")
        keywords_elem.text = keywords

    if productId:
        productId_elem = etree.SubElement(root, "productId", type="string")
        productId_elem.text = productId

    #affiliate is a dict
    if affiliate:
        affiliate_elem = etree.SubElement(root, "affiliate")
        for key in affiliate:
            key_elem = etree.SubElement(affiliate_elem, key)
            key_elem.text = affiliate[key]

    if buyerPostalCode:
        buyerPostalCode_elem = etree.SubElement(root, "buyerPostalCode")
        buyerPostalCode_elem.text = buyerPostalCode

    #paginationInput is a dict
    if paginationInput:
        paginationInput_elem = etree.SubElement(root, "paginationInput")
        for key in paginationInput:
            key_elem = etree.SubElement(paginationInput_elem, key)
            key_elem.text = paginationInput[key]

    #itenFilter is a list of dicts
    for item in itemFilter:
        itemFilter_elem = etree.SubElement(root, "itemFilter")
        for key in item:
            key_elem = etree.SubElement(itemFilter_elem, key)
            key_elem.text = item[key]

    #sortOrder
    if sortOrder:
        sortOrder_elem = etree.SubElement(root, "sortOrder")
        sortOrder_elem.text = sortOrder

    #outputSelector is a list
    for item in outputSelector:
        outputSelector_elem = etree.SubElement(root, "outputSelector")
        outputSelector_elem.text = item

    request = etree.tostring(root, pretty_print=True)
    return get_response(findItemsByProduct.__name__, request, encoding)


def findItemsIneBayStores(
        keywords=None,
        storeName=None, affiliate=None,
        buyerPostalCode=None, paginationInput=None,
        sortOrder=None, aspectFilter=None,
        domainFilter=None, itemFilter=None,
        outputSelector=None,
        encoding="JSON"):
    root = etree.Element("findItemsIneBayStores",
                         xmlns="http://www.ebay.com/marketplace/search/v1/services")

    if keywords:
        keywords_elem = etree.SubElement(root, "keywords")
        keywords_elem.text = keywords

    if storeName:
        storeName_elem = etree.SubElement(root, "storeName")
        storeName_elem.text = storeName

    #affiliate is a dict
    if affiliate:
        affiliate_elem = etree.SubElement(root, "affiliate")
        for key in affiliate:
            key_elem = etree.SubElement(affiliate_elem, key)
            key_elem.text = affiliate[key]

    if buyerPostalCode:
        buyerPostalCode_elem = etree.SubElement(root, "buyerPostalCode")
        buyerPostalCode_elem.text = buyerPostalCode

    #paginationInput is a dict
    if paginationInput:
        paginationInput_elem = etree.SubElement(root, "paginationInput")
        for key in paginationInput:
            key_elem = etree.SubElement(paginationInput_elem, key)
            key_elem.text = paginationInput[key]

    #itenFilter is a list of dicts
    for item in itemFilter:
        itemFilter_elem = etree.SubElement(root, "itemFilter")
        for key in item:
            key_elem = etree.SubElement(itemFilter_elem, key)
            key_elem.text = item[key]

    #sortOrder
    if sortOrder:
        sortOrder_elem = etree.SubElement(root, "sortOrder")
        sortOrder_elem.text = sortOrder

    #aspectFilter is a list of dicts
    for item in aspectFilter:
        aspectFilter_elem = etree.SubElement(root, "aspectFilter")
        for key in item:
            key_elem = etree.SubElement(aspectFilter_elem, key)
            key_elem.text = item[key]

    #domainFilter is a list of dicts
    for item in domainFilter:
        domainFilter_elem = etree.SubElement(root, "domainFilter")
        for key in item:
            key_elem = etree.SubElement(domainFilter_elem, key)
            key_elem.text = item[key]

    #outputSelector is a list
    for item in outputSelector:
        outputSelector_elem = etree.SubElement(root, "outputSelector")
        outputSelector_elem.text = item

    request = etree.tostring(root, pretty_print=True)
    return get_response(findItemsIneBayStores.__name__, request, encoding)


def getHistograms(categoryId, encoding="JSON"):
    root = etree.Element("getHistograms",
                         xmlns="http://www.ebay.com/marketplace/search/v1/services")

    categoryId_elem = etree.SubElement(root, "categoryId")
    categoryId_elem.text = categoryId

    request = etree.tostring(root, pretty_print=True)
    return get_response(getHistograms.__name__, request, encoding)


def get_response(operation_name, data, encoding, **headers):
    config = get_config_store()
    globalId = config.get("call", "global_id")
    app_name = config.get("keys", "app_name")
    endpoint = config.get("endpoints", "finding")

    http_headers = {
        "X-EBAY-SOA-OPERATION-NAME": operation_name,
        "X-EBAY-SOA-SECURITY-APPNAME": app_name,
        "X-EBAY-SOA-GLOBAL-ID": globalId,
        "X-EBAY-SOA-RESPONSE-DATA-FORMAT": encoding}

    http_headers.update(headers)

    req = urllib2.Request(endpoint, data, http_headers)
    res = urllib2.urlopen(req)
    data = res.read()
    return data

########NEW FILE########
__FILENAME__ = merchandising
import urllib2
from lxml import etree

from utils import get_config_store


def getDeals(keywords, encoding="JSON"):
    #not documented in ebay docs. Need to raise a ticket
    root = etree.Element("getDealsRequest",
                         xmlns="http://www.ebay.com/marketplace/services")

    keywords_elem = etree.SubElement(root, "keywords")
    keywords_elem.text = keywords

    request = etree.tostring(root, pretty_print=True)
    return get_response(getDeals.__name__, request, encoding)


def getMostWatchedItems(affiliate=None, maxResults=None,
                        categoryId=None, encoding="JSON"):
    root = etree.Element("getMostWatchedItemsRequest",
                         xmlns="http://www.ebay.com/marketplace/services")

    #affiliate is dict
    if affiliate:
        affiliate_elem = etree.SubElement(root, "affiliate")
        for key in affiliate.keys():
            key_elem = etree.SubElement(affiliate_elem, key)
            key_elem.text = affiliate[key]

    if maxResults:
        maxResults_elem = etree.SubElement(root, "maxResults")
        maxResults_elem.text = maxResults

    if categoryId:
        categoryId_elem = etree.SubElement(root, "categoryId")
        categoryId_elem.text = categoryId

    request = etree.tostring(root, pretty_print=True)
    return get_response(getMostWatchedItems.__name__, request, encoding)


#Takes categoryId or itemId
def getRelatedCategoryItems(
        affiliate=None, maxResults=None,
        categoryId=None, itemFilter=None,
        itemId=None, encoding="JSON"):
    root = etree.Element("getRelatedCategoryItemsRequest",
                         xmlns="http://www.ebay.com/marketplace/services")

    #affiliate is dict
    if affiliate:
        affiliate_elem = etree.SubElement(root, "affiliate")
        for key in affiliate.keys():
            key_elem = etree.SubElement(affiliate_elem, key)
            key_elem.text = affiliate[key]

    if maxResults:
        maxResults_elem = etree.SubElement(root, "maxResults")
        maxResults_elem.text = maxResults

    if categoryId:
        categoryId_elem = etree.SubElement(root, "categoryId")
        categoryId_elem.text = categoryId

    #itemFilter is list of dicts
    if itemFilter and len(itemFilter) > 0:
        for item in itemFilter:
            itemFilter_elem = etree.SubElement(root, "itemFilter")
            for key in itemFilter.keys():
                itemId_elem = etree.SubElement(itemFilter_elem, key)
                itemId_elem.text = itemFilter[key]

    if itemId:
        itemId_elem = etree.SubElement(root, "itemId")
        itemId_elem.text = itemId

    request = etree.tostring(root, pretty_print=True)
    return get_response(getRelatedCategoryItems.__name__, request, encoding)


def getSimilarItems(
        affiliate=None, maxResults=None,
        categoryId=None, categoryIdExclude=None,
        endTimeFrom=None, endTimeTo=None,
        itemFilter=None, itemId=None,
        listingType=None, maxPrice=None,
        encoding="JSON"):
    root = etree.Element("getSimilarItemsRequest",
                         xmlns="http://www.ebay.com/marketplace/services")

    #affiliate is dict
    if affiliate:
        affiliate_elem = etree.SubElement(root, "affiliate")
        for key in affiliate.keys():
            key_elem = etree.SubElement(affiliate_elem, key)
            key_elem.text = affiliate[key]

    if maxResults:
        maxResults_elem = etree.SubElement(root, "maxResults")
        maxResults_elem.text = maxResults

    #categoryId is list
    if categoryId:
        categoryId_elem = etree.SubElement(root, "categoryId")
        categoryId_elem.text = categoryId

    #categoryIdExclude is list
    for cat_id in categoryIdExclude:
        categoryIdExclude_elem = etree.SubElement(root, "categoryIdExclude")
        categoryIdExclude_elem.text = cat_id

    if endTimeFrom and endTimeTo:
        endTimeFrom_elem = etree.SubElement(root, "endTimeFrom")
        endTimeFrom_elem = endTimeFrom
        endTimeTo_elem = etree.SubeElement(root, "endTimeTo")
        endTimeTo_elem = endTimeTo

    #itemFilter is list of dicts
    if itemFilter and len(itemFilter) > 0:
        for item in itemFilter:
            itemFilter_elem = etree.SubElement(root, "itemFilter")
            for key in itemFilter.keys():
                itemId_elem = etree.SubElement(itemFilter_elem, key)
                itemId_elem.text = itemFilter[key]

    if itemId:
        itemId_elem = etree.SubElement(root, "itemId")
        itemId_elem.text = itemId

    if listingType:
        listingType_elem = etree.SubElement(root, "listingType")
        listingType_elem.text = listingType

    if maxPrice:
        maxPrice_elem = etree.SubElement(root, "maxPrice")
        maxPrice_elem.text = maxPrice

    request = etree.tostring(root, pretty_print=True)
    return get_response(getSimilarItems.__name__, request, encoding)


def getTopSellingProducts(affiliate=None, maxResults=None, encoding="JSON"):
    root = etree.Element("getTopSellingProductsRequest", xmlns="http://www.ebay.com/marketplace/services")

    #affiliate is dict
    if affiliate:
        affiliate_elem = etree.SubElement(root, "affiliate")
        for key in affiliate.keys():
            key_elem = etree.SubElement(affiliate_elem, key)
            key_elem.text = affiliate[key]

    if maxResults:
        maxResults_elem = etree.SubElement(root, "maxResults")
        maxResults_elem.text = maxResults

    request = etree.tostring(root, pretty_print=True)
    return get_response(getTopSellingProducts.__name__, request, encoding)


def get_response(operation_name, data, encoding, **headers):
    config = get_config_store()
    app_name = config.get("keys", "app_name")
    endpoint = config.get("endpoints", "merchandising")

    http_headers = {
        "X-EBAY-SOA-OPERATION-NAME": operation_name,
        "EBAY-SOA-CONSUMER-ID": app_name,
        "X-EBAY-SOA-RESPONSE-DATA-FORMAT": encoding}

    http_headers.update(headers)

    req = urllib2.Request(endpoint, data, http_headers)
    res = urllib2.urlopen(req)
    return res.read()


########NEW FILE########
__FILENAME__ = platform_notifications
def SetNotificationPreferences():
    pass


def GetNotificationPreferences():
    pass


def GetNotificationsUsage():
    pass
########NEW FILE########
__FILENAME__ = product
import urllib2
from lxml import etree

from utils import (get_config_store   )


def findCompatibilitiesBySpecification(
        specification, categoryId,
        compatibilityPropertyFilter=None, dataSet=None,
        datasetPropertyName=None, exactMatch=None,
        paginationInput=None, sortOrder=None,
        encoding="JSON"):
    root = etree.Element("findCompatibilitiesBySpecificationRequest",
                         xmlns="http://www.ebay.com/marketplace/marketplacecatalog/v1/services")

    #specification is an array of objects in Utils.py
    for spec in specification:
        specification_elem = etree.SubElement(root, "specification")
        propertyName_elem = etree.SubElement(specification_elem, "propertyName")
        propertyName_elem.text = spec.propertyName

        for v in spec.values:
            value_elem = etree.SubElement(specification_elem, "value")
            if v.number:
                number_elem = etree.SubElement(value_elem, "number")
                subValue_elem = etree.SubElement(number_elem, "value")
                subValue_elem.text = v.number

            if v.text:
                text_elem = etree.SubElement(value_elem, "text")
                subValue_elem = etree.SubElement(text_elem, "value")
                subValue_elem.text = v.text

            if v.url:
                url_elem = etree.SubElement(value_elem, "URL")
                subValue_elem = etree.SubElement(url_elem, "value")
                subValue_elem.text = v.url

    #compatibilityPropertyFilter is an array of objects in Utils.py
    for cp_filter in compatibilityPropertyFilter:
        compatibilityPropertyFilter_elem = etree.SubElement(root, "compatibilityPropertyFilter")
        propertyName_elem = etree.SubElement(compatibilityPropertyFilter_elem, "propertyName")
        propertyName_elem.text = cp_filter.propertyName

        for v in cp_filter.values:
            value_elem = etree.SubElement(compatibilityPropertyFilter_elem, "value")
            if v.number:
                number_elem = etree.SubElement(value_elem, "number")
                subValue_elem = etree.SubElement(number_elem, "value")
                subValue_elem.text = v.number

            if v.text:
                text_elem = etree.SubElement(value_elem, "text")
                subValue_elem = etree.SubElement(text_elem, "value")
                subValue_elem.text = v.text

            if v.url:
                url_elem = etree.SubElement(value_elem, "URL")
                subValue_elem = etree.SubElement(url_elem, "value")
                subValue_elem.text = v.url

    categoryId_elem = etree.SubElement(root, "categoryId")
    categoryId_elem.text = categoryId

    #dataSet is a List
    for ds in dataSet:
        ds_elem = etree.SubElement(root, "dataSet")
        ds_elem.text = ds

    #datasetPropertyName is a List
    for dpn in datasetPropertyName:
        dpn_elem = etree.SubElement(root, "datasetPropertyName")
        dpn_elem.text = dpn

    if exactMatch:
        exactMatch_elem = etree.SubElement(root, "exactMatch")
        exactMatch_elem.text = exactMatch

    #paginationInput is Dict
    for key in paginationInput:
        key_elem = etree.SubElement(root, key)
        key_elem.text = paginationInput[key]

    #Really weirdly written API by eBay, sortOrder is used two times, confusing naming
    for so in sortOrder:
        sortOrder_elem = etree.SubElement(root, "sortOrder")
        sortPriority_elem = etree.SubElement(sortOrder_elem, "sortPriority")
        sortPriority_elem.text = so.sortPriority

        subSortOrder_elem = etree.SubElement(sortOrder_elem, "sortOrder")
        order_elem = etree.SubElement(subSortOrder_elem, "order")
        order_elem.text = so.order
        propertyName_elem = etree.SubElement(subSortOrder_elem, "propertyName")
        propertyName_elem.text = so.propertyName

    request = etree.tostring(root, pretty_print=True)
    print request
    return get_response(findCompatibilitiesBySpecification.__name__, request, encoding)


def getProductCompatibilities(
        datasetPropertyName, productIdentifier,
        applicationPropertyFilter=None, dataset=None,
        disabledProductFilter=None, paginationInput=None,
        sortOrder=None, encoding="JSON"):
    root = etree.Element("findProductsByCompatibilityRequest",
                         xmlns="http://www.ebay.com/marketplace/marketplacecatalog/v1/services")

    #datasetPropertyName is a List
    for dpn in datasetPropertyName:
        dpn_elem = etree.SubElement(root, "datasetPropertyName")
        dpn_elem.text = dpn

    #compatibilityPropertyFilter is an object in Utils.py
    #TODO: compatibilityPropertyFilter is MISSING ???
    for cp_filter in compatibilityPropertyFilter:
        compatibilityPropertyFilter_elem = etree.SubElement(root, "compatibilityPropertyFilter")
        propertyName_elem = etree.SubElement(compatibilityPropertyFilter_elem, "propertyName")
        propertyName_elem.text = cp_filter.propertyName

        for v in cp_filter.values:
            value_elem = etree.SubElement(compatibilityPropertyFilter_elem, "value")
            if v.number:
                number_elem = etree.SubElement(value_elem, "number")
                number_elem.text = v.number

            if v.text:
                text_elem = etree.SubElement(value_elem, "text")
                text_elem.text = v.text

            if v.url:
                url_elem = etree.SubElement(value_elem, "URL")
                url_elem.text = v.url

    #dataSet is a List
    for ds in dataSet:
        ds_elem = etree.SubElement(root, "dataSet")
        ds_elem.text = ds

    #disabledProductFilter is dict
    if disabledProductFilter:
        disabledProductFilter_elem = etree.SubElement(root, "disabledProductFilter")
        for key in disabledProductFilter.keys():
            key_elem = etree.SubElement(disabledProductFilter_elem, key)
            key_elem.text = disabledProductFilter[key]

    #paginationInput is Dict
    for key in paginationInput:
        key_elem = etree.SubElement(root, key)
        key_elem.text = paginationInput[key]

    #productIdentifier is dict
    productIdentifier_elem = etree.SubElement(root, "productIdentifier")
    for key in productIdentifier.keys():
        key_elem = etree.SubElement(productIdentifier_elem, key)
        key_elem.text = productIdentifier[key]

    #Really weirdly written API by eBay, sortOrder is used two times, confusing naming
    for so in sortOrder:
        sortOrder_elem = etree.SubElement(root, "sortOrder")
        sortPriority_elem = etree.SubElement(sortOrder_elem, "sortPriority")
        sortPriority_elem.text = so.sortPriority

        subSortOrder_elem = etree.SubElement(sortOrder_elem, "sortOrder")
        order_elem = etree.SubElement(subSortOrder_elem, "order")
        order_elem.text = so.order
        propertyName_elem = etree.SubElement(subSortOrder_elem, "propertyName")
        propertyName_elem.text = so.propertyName

    request = etree.tostring(root, pretty_print=True)
    return get_response(getProductCompatibilities.__name__, request, encoding)


def findProducts(
        invocationId, dataset=None,
        datasetPropertyName=None, keywords=None,
        paginationInput=None, productStatusFilter=None,
        propertyFilter=None, sortOrder=None,
        encoding="JSON"):
    root = etree.Element("findProductsRequest",
                         xmlns="http://www.ebay.com/marketplace/marketplacecatalog/v1/services")

    #Really messed up! : http://developer.ebay.com/DevZone/product/CallRef/findProducts.html#Samples

    request = etree.tostring(root, pretty_print=True)
    return get_response(findProducts.__name__, request, encoding)


def findProductsByCompatibility(encoding="JSON"):
    root = etree.Element("findProductsByCompatibilityRequest",
                         xmlns="http://www.ebay.com/marketplace/marketplacecatalog/v1/services")

    #Problem with getProductDetails, findProductsByCompatibility and findProducts
    # method: http://developer.ebay.com/DevZone/product/CallRef/index.html

    request = etree.tostring(root, pretty_print=True)
    return get_response(findProductsByCompatibility.__name__, request, encoding)


def getProductDetails(encoding="JSON"):
    root = etree.Element("getProductDetailsRequest",
                         xmlns="http://www.ebay.com/marketplace/marketplacecatalog/v1/services")

    #Problem with getProductDetails, findProductsByCompatibility and findProducts
    # method: http://developer.ebay.com/DevZone/product/CallRef/index.html

    request = etree.tostring(root, pretty_print=True)
    return get_response(getProductDetails.__name__, request, encoding)


def get_response(operation_name, data, encoding, **headers):
    config = get_config_store()
    app_name = config.get("keys", "app_name")
    endpoint = config.get("endpoints", "product")

    http_headers = {
        "X-EBAY-SOA-OPERATION-NAME": operation_name,
        "X-EBAY-SOA-SECURITY-APPNAME": app_name,
        "X-EBAY-SOA-RESPONSE-DATA-FORMAT": encoding}

    http_headers.update(headers)

    req = urllib2.Request(endpoint, data, http_headers)
    res = urllib2.urlopen(req)
    return res.read()

########NEW FILE########
__FILENAME__ = research
#This sucks: http://developer.researchadvanced.com/contact.php

def GetPriceResearch():
    pass
########NEW FILE########
__FILENAME__ = resolution_case_management
import urllib2
from lxml import etree

from utils import get_config_store

# case retrieval calls
def getUserCases(caseStatusFilter=None,
                 caseTypeFilter=None,
                 creationDateRangeFilterFrom=None,
                 creationDateRangeFilterTo=None,
                 itemFilter=None,
                 paginationInput=None,
                 sortOrder=None,
                 encoding="JSON"):
    root = etree.Element("getUserCasesRequest",
                         xmlns="http://www.ebay.com/marketplace/search/v1/services")

    #caseStatusFilter is a List
    if caseStatusFilter:
        caseStatusFilter_elem = etree.SubElement(root, "caseStatusFilter")
        for status in caseStatusFilter:
            caseStatus_elem = etree.SubElement(caseStatusFilter_elem, "caseStatus")
            caseStatus_elem.text = status

    #caseTypeFilter is a List
    if caseTypeFilter:
        caseTypeFilter_elem = etree.SubElement(root, "caseTypeFilter")
        for case_type in caseTypeFilter:
            caseType_elem = etree.SubElement(caseStatusFilter_elem, "caseType")
            caseType_elem.text = case_type

    if creationDateRangeFilterFrom and creationDateRangeFilterTo:
        creationDateRangeFilter_elem = etree.SubElement(root, "creationDateRangeFilter")

        creationDateRangeFilterFrom_elem = etree.SubElement(creationDateRangeFilter_elem, "fromDate")
        creationDateRangeFilterFrom_elem.text = creationDateRangeFilterFrom
        creationDateRangeFilterTo_elem = etree.SubElement(creationDateRangeFilter_elem, "toDate")
        creationDateRangeFilterTo_elem.text = creationDateRangeFilterTo


    #itemFilter is a dict: {itemId:123, transactionId:72}
    if itemFilter and len(itemFilter) > 0:
        itemFilter_elem = etree.SubElement(root, "itemFilter")
        for key in itemFilter.keys():
            itemId_elem = etree.SubElement(itemFilter_elem, key)
            itemId_elem.text = itemFilter[key]


    # paginationInput is a dict: {entriesPerPage:5, pageNumber:10}
    if paginationInput and len(paginationInput) > 0:
        paginationInput_elem = etree.SubElement(root, "paginationInput")
        for key in paginationInput.keys():
            input_values_elem = etree.SubElement(paginationInput_elem, key)
            input_values_elem.text = paginationInput[key]

    if sortOrder:
        sortOrder_elem = etree.SubElement(root, "sortOrder")
        sortOrder_elem.text = sortOrder

    request = etree.tostring(root, pretty_print=True)
    return get_response(getUserCases.__name__, request, encoding)


def getEBPCaseDetail(caseId, caseType, encoding="JSON"):
    root = etree.Element("getEBPCaseDetailRequest",
                         xmlns="http://www.ebay.com/marketplace/search/v1/services")

    caseId_elem = etree.SubElement(root, "caseId")
    id_elem = etree.SubElement(caseId_elem, "id")
    id_elem.text = caseId
    type_elem = etree.SubElement(caseId_elem, "type")
    type_elem.text = caseType

    request = etree.tostring(root, pretty_print=True)
    return get_response(getEBPCaseDetail.__name__, request, encoding)


# Seller Option Calls
def provideTrackingInfo(caseId, caseType, carrierUsed, trackingNumber, comments=None, encoding="JSON"):
    root = etree.Element("provideTrackingInfoRequest",
                         xmlns="http://www.ebay.com/marketplace/search/v1/services")

    caseId_elem = etree.SubElement(root, "caseId")
    id_elem = etree.SubElement(caseId_elem, "id")
    id_elem.text = caseId
    type_elem = etree.SubElement(caseId_elem, "type")
    type_elem.text = caseType

    carrierUsed_elem = etree.SubElement(root, "carrierUsed")
    carrierUsed_elem.text = carrierUsed

    trackingNumber_elem = etree.SubElement(root, "trackingNumber")
    trackingNumber_elem.text = trackingNumber

    if comments:
        comments_elem = etree.SubElement(root, "comments")
        comments_elem.text = comments

    request = etree.tostring(root, pretty_print=True)
    return get_response(provideTrackingInfo.__name__, request, encoding)


def issueFullRefund(caseId, caseType, comments=None, encoding="JSON"):
    root = etree.Element("issueFullRefundRequest",
                         xmlns="http://www.ebay.com/marketplace/search/v1/services")

    caseId_elem = etree.SubElement(root, "caseId")
    id_elem = etree.SubElement(caseId_elem, "id")
    id_elem.text = caseId
    type_elem = etree.SubElement(caseId_elem, "type")
    type_elem.text = caseType

    if comments:
        comments_elem = etree.SubElement(root, "comments")
        comments_elem.text = comments

    request = etree.tostring(root, pretty_print=True)
    return get_response(issueFullRefund.__name__, request, encoding)


def offerOtherSolution(caseId, caseType, messageToBuyer, encoding="JSON"):
    root = etree.Element("offerOtherSolutionRequest",
                         xmlns="http://www.ebay.com/marketplace/search/v1/services")

    caseId_elem = etree.SubElement(root, "caseId")
    id_elem = etree.SubElement(caseId_elem, "id")
    id_elem.text = caseId
    type_elem = etree.SubElement(caseId_elem, "type")
    type_elem.text = caseType

    messageToBuyer_elem = etree.SubElement(root, "messageToBuyer")
    messageToBuyer_elem.text = messageToBuyer

    request = etree.tostring(root, pretty_print=True)
    return get_response(offerOtherSolution.__name__, request, encoding)

#NOT WORKING on SANDBOX, need to investigate
def escalateToCustomerSuppport(caseId, caseType, escalationReason,
                               comments=None, encoding="JSON"):
    root = etree.Element("escalateToCustomerSuppportRequest",
                         xmlns="http://www.ebay.com/marketplace/search/v1/services")

    caseId_elem = etree.SubElement(root, "caseId")
    id_elem = etree.SubElement(caseId_elem, "id")
    id_elem.text = caseId
    type_elem = etree.SubElement(caseId_elem, "type")
    type_elem.text = caseType

    #escalationReason is a dict
    escalationReason_elem = etree.SubElement(root, "escalationReason")
    for key in escalationReason.keys():
        key_elem = etree.SubElement(escalationReason_elem, key)
        key_elem.text = escalationReason[key]

    if comments:
        comments_elem = etree.SubElement(root, "comments")
        comments_elem.text = comments

    request = etree.tostring(root, pretty_print=True)
    return get_response(escalateToCustomerSuppport.__name__, request, encoding)


def appealToCustomerSupport(caseId, caseType, appealReason,
                            comments=None, encoding="JSON"):
    root = etree.Element("appealToCustomerSupportRequest",
                         xmlns="http://www.ebay.com/marketplace/search/v1/services")

    caseId_elem = etree.SubElement(root, "caseId")
    id_elem = etree.SubElement(caseId_elem, "id")
    id_elem.text = caseId
    type_elem = etree.SubElement(caseId_elem, "type")
    type_elem.text = caseType

    appealReason_elem = etree.SubElement(root, "appealReason")
    appealReason_elem.text = appealReason

    if comments:
        comments_elem = etree.SubElement(root, "comments")
        comments_elem.text = comments

    request = etree.tostring(root, pretty_print=True)
    return get_response(appealToCustomerSupport.__name__, request, encoding)


# Metadata calls
def getActivityOptions(caseId, caseType, encoding="JSON"):
    root = etree.Element("getActivityOptionsRequest",
                         xmlns="http://www.ebay.com/marketplace/search/v1/services")

    caseId_elem = etree.SubElement(root, "caseId")
    id_elem = etree.SubElement(caseId_elem, "id")
    id_elem.text = caseId
    type_elem = etree.SubElement(caseId_elem, "type")
    type_elem.text = caseType

    request = etree.tostring(root, pretty_print=True)
    return get_response(getActivityOptions.__name__, request, encoding)


def getVersion(encoding="JSON"):
    root = etree.Element("getVersionRequest",
                         xmlns="http://www.ebay.com/marketplace/search/v1/services")

    request = etree.tostring(root, pretty_print=True)
    return get_response(getVersion.__name__, request, encoding)


def get_response(operation_name, data, encoding, **headers):
    config = get_config_store()
    access_token = config.get("auth", "token")
    endpoint = config.get("endpoints", "resolution_case_management")

    http_headers = {
        "X-EBAY-SOA-OPERATION-NAME": operation_name,
        "X-EBAY-SOA-SECURITY-TOKEN": access_token,
        "X-EBAY-SOA-RESPONSE-DATA-FORMAT": encoding}

    http_headers.update(headers)

    req = urllib2.Request(endpoint, data, http_headers)
    res = urllib2.urlopen(req)
    data = res.read()
    return data

########NEW FILE########
__FILENAME__ = shopping
import requests
from utils import get_config_store


# Item Search
def FindProducts(query, available_items, max_entries, encoding="JSON"):
    user_param = {
        'callname': FindProducts.__name__,
        'responseencoding': encoding,
        'QueryKeywords': query,
        'AvailableItemsOnly': available_items,
        'MaxEntries': max_entries}

    response = get_response(user_param)
    return response.content


def FindHalfProducts(query=None, max_entries=None,
                     product_type=None, product_value=None,
                     include_selector=None,
                     encoding="JSON"):
    if product_type and product_value and include_selector:
        user_param = {
            'callname': FindHalfProducts.__name__,
            'responseencoding': encoding,
            'ProductId.type': product_type,
            'ProductId.Value': product_value,
            'IncludeSelector': include_selector}

    if query and max_entries:
        user_param = {
            'callname': FindHalfProducts.__name__,
            'responseencoding': encoding,
            'QueryKeywords': query,
            'MaxEntries': max_entries}

    response = get_response(user_param)
    return response.content

# Item Data
def GetSingleItem(item_id, include_selector=None, encoding="JSON"):
    user_param = {
        'callname': GetSingleItem.__name__,
        'responseencoding': encoding,
        'ItemId': item_id}

    if include_selector:
        user_param['IncludeSelector'] = include_selector

    response = get_response(user_param)
    return response.content


def GetItemStatus(item_id, encoding="JSON"):
    user_param = {
        'callname': GetItemStatus.__name__,
        'responseencoding': encoding,
        'ItemId': item_id}

    response = get_response(user_param)
    return response.content


def GetShippingCosts(item_id, destination_country_code, destination_postal_code, details, quantity_sold,
                     encoding="JSON"):
    user_param = {
        'callname': GetShippingCosts.__name__,
        'responseencoding': encoding,
        'ItemId': item_id,
        'DestinationCountryCode': destination_country_code,
        'DestinationPostalCode': destination_postal_code,
        'IncludeDetails': details,
        'QuantitySold': quantity_sold}

    response = get_response(user_param)
    return response.content


def GetMultipleItems(item_id, include_selector=None, encoding="JSON"):
    user_param = {
        'callname': GetMultipleItems.__name__,
        'responseencoding': encoding,
        'ItemId': item_id}

    if include_selector:
        user_param['IncludeSelector'] = include_selector

    response = get_response(user_param)
    return response.content

# User Reputation
def GetUserProfile(user_id, include_selector=None, encoding="JSON"):
    user_param = {
        'callname': GetUserProfile.__name__,
        'responseencoding': encoding,
        'UserID': user_id}

    if include_selector:
        user_param['IncludeSelector'] = include_selector

    response = get_response(user_param)
    return response.content


# eBay pop!
def FindPopularSearches(query, category_id=None, encoding="JSON"):
    user_param = {
        'callname': FindPopularSearches.__name__,
        'responseencoding': encoding,
        'QueryKeywords': query}

    if category_id:
        user_param['CategoryID'] = category_id

    response = get_response(user_param)
    return response.content


def FindPopularItems(query, category_id_exclude=None, encoding="JSON"):
    user_param = {
        'callname': FindPopularItems.__name__,
        'responseencoding': encoding,
        'QueryKeywords': query}

    if category_id_exclude:
        user_param['CategoryIDExclude'] = category_id_exclude

    response = get_response(user_param)
    return response.content


# Search: Bug in eBay documentation of Product Id:
# http://developer.ebay.com/devzone/shopping/docs/callref/FindReviewsAndGuides.html#Samples
def FindReviewsandGuides(category_id=None, product_id=None, encoding="JSON"):
    if category_id:
        user_param = {
            'callname': FindReviewsandGuides.__name__,
            'responseencoding': encoding,
            'CategoryID': category_id}

    if product_id:
        user_param = {
            'callname': FindReviewsandGuides.__name__,
            'responseencoding': encoding,
            'ProductID': product_id}

    response = get_response(user_param)
    return response.content


# Utilities
def GetCategoryInfo(category_id, include_selector=None, encoding="JSON"):
    if category_id:
        user_param = {
            'callname': GetCategoryInfo.__name__,
            'responseencoding': encoding,
            'CategoryID': category_id}

    if include_selector:
        user_param['IncludeSelector'] = include_selector

    response = get_response(user_param)
    return response.content


def GeteBayTime(encoding="JSON"):
    user_param = {
        'callname': GeteBayTime.__name__,
        'responseencoding': encoding}

    response = get_response(user_param)
    return response.content


#requests method
def get_response(user_params):
    config = get_config_store()
    app_id = config.get("keys", "app_name")
    site_id = config.get("call", "siteid")
    version = config.get("call", "compatibility_level")
    endpoint = config.get("endpoints", "shopping")

    d = dict(appid=app_id, siteid=site_id, version=version)

    d.update(user_params)

    return requests.get(endpoint, params=d)

########NEW FILE########
__FILENAME__ = trading
#!/usr/bin/env python
#-*- coding: utf-8 -*-
import sys
from xml.dom.minidom import parseString

from utils import (get_endpoint_response, get_config_store,
                   get_endpoint_response_with_file, add_e, imgur_post)
from lxml import etree, objectify


CID = {
    'new': '1000',
    'used': '3000',
}


def addItemWithPic(image, **kwargs):
    url = uploadSiteHostedPicture(image)
    kwargs['pictureDetails'] = [url]
    return addItem(**kwargs)


def addItem(
        title, description, primaryCategoryId,
        startPrice='0.99', buyItNowPrice=None, country='US',
        currency='USD', dispatchTimeMax='3', listingDuration='Days_7',
        listingType='Chinese', paymentMethods=['PayPal'],
        payPalEmailAddress='', pictureDetails=[], postalCode='',
        photoDisplay='PicturePack', condition='new',
        quantity=1, freeShipping=True, site='US', test=False):
    #get the user auth token
    token = get_config_store().get("auth", "token")
    oname = "AddItem" if not test else 'VerifyAddItem'
    rname = "%sRequest" % oname
    root = etree.Element(rname,
                         xmlns="urn:ebay:apis:eBLBaseComponents")
    #add it to the xml doc
    credentials_elem = etree.SubElement(root, "RequesterCredentials")
    token_elem = etree.SubElement(credentials_elem, "eBayAuthToken")
    token_elem.text = token

    item_e = etree.SubElement(root, "Item")
    t_e = add_e(item_e, "Title", str(title))
    d_e = add_e(item_e, "Description", str(description))
    pcat = add_e(item_e, "PrimaryCategory", None)
    cid = add_e(pcat, "CategoryID", primaryCategoryId)
    add_e(item_e, "ConditionID", CID.get(condition, 'new'))
    sp = add_e(item_e, "StartPrice", startPrice)
    if buyItNowPrice:
        sp = add_e(item_e, "BuyItNowPrice", buyItNowPrice)
    cma = add_e(item_e, "CategoryMappingAllowed", 'true')
    cnode = add_e(item_e, "Country", country)
    curre = add_e(item_e, "Currency", currency)
    dtme = add_e(item_e, "DispatchTimeMax", dispatchTimeMax)
    lde = add_e(item_e, "ListingDuration", listingDuration)
    for t in paymentMethods:
        pme = add_e(item_e, "PaymentMethods", t)
    ppea = add_e(item_e, "PayPalEmailAddress", payPalEmailAddress)
    picde = add_e(item_e, "PictureDetails", None)
    add_e(picde, "PhotoDisplay", photoDisplay)
    for url in pictureDetails:
        ure = add_e(picde, "PictureURL", url)
    pce = add_e(item_e, "PostalCode", postalCode)
    que = add_e(item_e, "Quantity", quantity)

    # default return
    returnPol_e = add_e(item_e, "ReturnPolicy", None)
    add_e(returnPol_e, "ReturnsAcceptedOption", "ReturnsAccepted")
    add_e(returnPol_e, "RefundOption", "MoneyBack")
    add_e(returnPol_e, "ReturnsWithinOption", "Days_30")
    add_e(returnPol_e, "Description", "If you are not satisfied, ship the item back for a full refund.")
    add_e(returnPol_e, "ShippingCostPaidByOption", "Buyer")
    # end default ret pol

    shipde_e = add_e(item_e, "ShippingDetails", None)
    if freeShipping:
        sst = add_e(shipde_e, "ShippingType", "Flat")
        sse = add_e(shipde_e, "ShippingServiceOptions", None)
        add_e(sse, "ShippingService", "USPSMedia")
        add_e(sse, "ShippingServiceCost", "0.0")
        add_e(sse, "ShippingServiceAdditionalCost", "0.0")
        add_e(sse, "ShippingServicePriority", "1")
        add_e(sse, "ExpeditedService", "false")
    site_e = add_e(item_e, "Site", site)

    #need to specify xml declaration and encoding or else will get error
    request = etree.tostring(root, pretty_print=True,
                             xml_declaration=True, encoding="utf-8")
    response = get_response(oname, request, "utf-8")

    return response


def getCategories(
        parentId=None,
        detailLevel='ReturnAll',
        errorLanguage=None,
        messageId=None,
        outputSelector=None,
        version=None,
        warningLevel="High",
        levelLimit=1,
        viewAllNodes=True,
        categorySiteId=0,
        encoding="JSON"):
    """
    Using a query string and parentId this function returns
    all the categories containing that string within the category name,
    and as a subcategory of the category defined by the parentId.
    If the parentId is missing, it simply returns a list of all the
    top-level categories.
    (based on
    http://developer.ebay.com/DevZone/XML/docs/Reference/eBay/GetCategories.html#Request)
    """
    #get the user auth token
    token = get_config_store().get("auth", "token")

    root = etree.Element("GetCategoriesRequest",
                         xmlns="urn:ebay:apis:eBLBaseComponents")
    #add it to the xml doc
    credentials_elem = etree.SubElement(root, "RequesterCredentials")
    token_elem = etree.SubElement(credentials_elem, "eBayAuthToken")
    token_elem.text = token

    if parentId == None and levelLimit:
        levelLimit_elem = etree.SubElement(root, "LevelLimit")
        levelLimit_elem.text = str(levelLimit)
    elif parentId:
        parentId_elem = etree.SubElement(root, "CategoryParent")
        parentId_elem.text = str(parentId)

    viewAllNodes_elem = etree.SubElement(root, "ViewAllNodes")
    viewAllNodes_elem.text = str(viewAllNodes).lower()

    categorySiteId_elem = etree.SubElement(root, "CategorySiteID")
    categorySiteId_elem.text = str(categorySiteId)

    if detailLevel:
        detailLevel_elem = etree.SubElement(root, "DetailLevel")
        detailLevel_elem.text = detailLevel

    if errorLanguage:
        errorLanguage_elem = etree.SubElement(root, "ErrorLanguage")
        errorLanguage_elem.text = errorLanguage

    if messageId:
        messageId_elem = etree.SubElement(root, "MessageID")
        messageId_elem.text = messageId

    if outputSelector:
        outputSelector_elem = etree.SubElement(root, "OutputSelector")
        outputSelector_elem.text = outputSelector

    if version:
        version_elem = etree.SubElement(root, "Version")
        version_elem.text = version

    if warningLevel:
        warningLevel_elem = etree.SubElement(root, "WarningLevel")
        warningLevel_elem.text = warningLevel

    #need to specify xml declaration and encoding or else will get error
    request = etree.tostring(root, pretty_print=False,
                             xml_declaration=True, encoding="utf-8")
    response = get_response("GetCategories", request, encoding)

    return response


def _get_single_value(node, tag):
    nl = node.getElementsByTagName(tag)
    if len(nl) > 0:
        tagNode = nl[0]
        if tagNode.hasChildNodes():
            return tagNode.firstChild.nodeValue
    return -1


def filterCategories(xml_data, query=''):
    to_return = []  # TODO: in future would be cool if categories were objects
    if xml_data:
        categoryList = parseString(xml_data)
        catNodes = categoryList.getElementsByTagName("Category")
        for node in catNodes:
            addNode = False  # assume it's not being added
            if query:
                lquery = query.lower()
                name = _get_single_value(node, "CategoryName")
                if name.lower().find(lquery) != -1:
                    addNode = True  # name contains our query, will add it
            else:
                addNode = True  # no filter given, add all
            if addNode:
                # add node to the list if we need to
                to_return.append(node.toxml())

    return to_return


def uploadSiteHostedPicture(filepath):
    isURL = 'http://' in filepath or 'https://' in filepath
    #get the user auth token
    token = get_config_store().get("auth", "token")
    oname = "UploadSiteHostedPictures"
    rname = "%sRequest" % oname
    root = etree.Element(rname, xmlns="urn:ebay:apis:eBLBaseComponents")
    credentials_elem = etree.SubElement(root, "RequesterCredentials")
    token_elem = etree.SubElement(credentials_elem, "eBayAuthToken")
    token_elem.text = token
    add_e(root, "PictureSet", "Supersize")
    if isURL:
        urlpath = filepath
    else:
        try:
            urlpath = imgur_post(filepath)
        except Exception as e:
            sys.stderr.write("Unable to upload img: %s. Abort -1.\n" % filepath)
            raise e

    epu = add_e(root, "ExternalPictureURL", urlpath)

    request = etree.tostring(root, pretty_print=True,
                             xml_declaration=True, encoding="UTF-8")

    response = get_response(oname, request, "UTF-8")

    return urlpath


def url_result(result):
    root = objectify.fromstring(result)
    url = root.FullURL.text
    return url


def get_response(operation_name, data, encoding, **headers):
    return get_endpoint_response(
        "trading", operation_name,
        data, encoding, **headers)


def get_response_with_file(operation_name, fobj, data, encoding, **headers):
    return get_endpoint_response_with_file(
        "trading", operation_name,
        fobj, data, encoding, **headers)

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env pythin
#-*- coding: utf-8 -*-
import sys
import base64
import json
import shutil
import os
import urllib2
from ConfigParser import ConfigParser
from os.path import join, dirname, abspath

import requests
from lxml import etree


CONFIG_STORE = None


def get_endpoint_response(
        endpoint_name, operation_name,
        data, encoding,
        **headers):
    config = get_config_store()
    endpoint = config.get("endpoints", endpoint_name)
    app_name = config.get("keys", "app_name")
    dev_name = config.get("keys", "dev_name")
    cert_name = config.get("keys", "cert_name")
    compatibility_level = config.get("call", "compatibility_level")
    siteId = config.get("call", "siteid")

    http_headers = {
        "X-EBAY-API-COMPATIBILITY-LEVEL": compatibility_level,
        "X-EBAY-API-DEV-NAME": dev_name,
        "X-EBAY-API-APP-NAME": app_name,
        "X-EBAY-API-CERT-NAME": cert_name,
        "X-EBAY-API-CALL-NAME": operation_name,
        "X-EBAY-API-SITEID": siteId,
        "Content-Type": "text/xml"}

    http_headers.update(headers)

    req = urllib2.Request(endpoint, data, http_headers)
    res = urllib2.urlopen(req)
    return res.read()


def get_endpoint_response_with_file(
        endpoint_name, operation_name,
        fobj, data,
        encoding, **headers):
    config = get_config_store()
    endpoint = config.get("endpoints", endpoint_name)
    app_name = config.get("keys", "app_name")
    dev_name = config.get("keys", "dev_name")
    cert_name = config.get("keys", "cert_name")
    compatibility_level = config.get("call", "compatibility_level")
    siteId = config.get("call", "siteid")

    http_headers = {
        "X-EBAY-API-COMPATIBILITY-LEVEL": compatibility_level,
        "X-EBAY-API-DEV-NAME": dev_name,
        "X-EBAY-API-APP-NAME": app_name,
        "X-EBAY-API-CERT-NAME": cert_name,
        "X-EBAY-API-CALL-NAME": operation_name,
        "X-EBAY-API-SITEID": siteId,
        "X-EBAY-API-DETAIL-LEVEL": "0",
        "Content-Type": "multipart/form-data"}

    http_headers.update(headers)

    files = {'file': ('image', fobj)}
    dataload = {'body': data}
    res = requests.post(endpoint, files=files, data=dataload,
                        headers=http_headers)
    return res.text


def relative(*paths):
    return join(dirname(abspath(__file__)), *paths)


def set_config_file(filename):
    """
    Change the configuration file. 
    Use configuration file in non standard location.
    """
    global CONFIG_STORE
    CONFIG_STORE = ConfigParser()
    CONFIG_STORE.read(filename)


def get_config_store():
    """
    Return storage object with configuration values.
    The returned object is a ConfigParser, that is queried like this::
    
        key = store.get("section", "key")
    """
    global CONFIG_STORE
    if CONFIG_STORE is None:
        CONFIG_STORE = ConfigParser()
        CONFIG_STORE.read(relative("config.ini"))

    return CONFIG_STORE


def write_config_example(dst=None):
    """
    Write an example configuration file for python-ebay.
    
    * If **dst** is None, the file is written into the current directory,
      and named ``config.ini.example``.
    * If **dst** is an existing directory, the file is written into this 
      directory, and named ``config.ini.example``.
    * If **dst** is a file name, the example is written into a file with this
      name.
    """
    if dst is None:
        dst = os.getcwd()
    config_example_path = relative("config.ini.example")
    shutil.copy(config_example_path, dst)


class Value(object):
    def __init__(self,
                 number=None,
                 text=None,
                 url=None):
        self.number = number
        self.text = text
        self.url = url


class Specification(object):
    def __init__(self, propertyName):
        self.propertyName = propertyName
        self.values = []


class CompatibilityPropertyFilter(object):
    def __init__(self, propertyName):
        self.propertyName = propertyName
        self.values = []


class ApplicationPropertyFilter(object):
    def __init__(self, propertyName):
        self.propertyName = propertyName
        self.values = []


class SortOrder(object):
    def __init__(self, sortPriority, order, propertyName):
        self.sortPriority = sortPriority
        self.order = order
        self.propertyName = propertyName


def add_e(parent, key, val=None):
    child = etree.SubElement(parent, key)
    if val:
        child.text = str(val)
    return child


def imgur_post(filepath):
    imgur_key = get_config_store().get("keys", "imgur_key")
    fobj = open(filepath, "rb")
    bimage = fobj.read()  #again, not string data, but binary data
    fobj.close()
    b64image = base64.b64encode(bimage)
    payload = {
        'key': imgur_key,
        'image': b64image,
        'title': 'an upload'
    }
    endpoint = 'http://api.imgur.com/2/upload.json'
    r = requests.post(endpoint, data=payload)
    j = json.loads(r.text)
    url = j['upload']['links']['original']
    sys.stderr.write('Upload Success!    %s    %s\n' % (filepath, url))
    return url


########NEW FILE########
__FILENAME__ = example_alternative_config
"""
Show haow to use alternative configuration files.
"""
from os import system
from os.path import join, dirname, abspath

from ebay.utils import set_config_file
from ebay.finding import findItemsByKeywords


#Create file paths that are relative to the location of this file.
def relative(*paths):
    return abspath(join(dirname(abspath(__file__)), *paths))

#File paths
std_conf = relative("../ebay/config.ini")
alt_conf = relative("../config.apikey")

#Copy initialization file to nonstandard location
system("cp " + std_conf + " " + alt_conf)
#Look where the initialization files really are
system("ls " + std_conf)
system("ls " + alt_conf)

#Set alternative configuration file and use the library
set_config_file(alt_conf)
print findItemsByKeywords(keywords="ipod", encoding="XML", 
                          paginationInput = {"entriesPerPage": "5", 
                                             "pageNumber"    : "1"})

########NEW FILE########
__FILENAME__ = example_best_match
from ebay.best_match import findBestMatchItemDetailsAcrossStores, getVersion, findBestMatchItemDetailsByKeywords, findBestMatchItemDetailsAdvanced, findBestMatchItemDetailsByCategory, findBestMatchItemDetailsByProduct, findBestMatchItemDetailsBySeller, findBestMatchItemDetails

items= [{"paramName":"PriceMin", "paramValue":"50", "name":"Currency", "value":"USD"}]
print findBestMatchItemDetailsAcrossStores(keywords="ipod", siteResultsPerPage="1", itemFilter=items)

print findBestMatchItemDetailsByKeywords(keywords="ipod", siteResultsPerPage="1", itemFilter=items, ignoreFeatured="True")
print findBestMatchItemDetailsAdvanced(keywords="ipod", siteResultsPerPage="1", itemFilter=items)
print findBestMatchItemDetailsByCategory(categoryId="12", siteResultsPerPage="1", itemFilter=items)
print findBestMatchItemDetailsByProduct(productId="11", siteResultsPerPage="1")
print findBestMatchItemDetailsBySeller(categoryId="267", sellerUserName="MegaSeller")
print getVersion()

#Not working
#print findBestMatchItemDetails()

########NEW FILE########
__FILENAME__ = example_client_alerts
from ebay.client_alerts import GetPublicAlerts, GetUserAlerts, Login, Logout 

#Taken from ebay dev site, as a sample. Not actual tokens

print GetPublicAlerts(ChannelID="370293550455", ChannelType="Item", EventType="ItemEnded", encoding="XML")
print GetUserAlerts(SessionData="p0SVs0iK4imqkoKkI1D", SessionID="MySessionID", encoding="JSON")

print Login(ClientAlertsAuthToken="AQAAARk1obQAAA0xfDE3ODcyNHw1MjQ2fDEyMDg1NDk0Njg0ODR8anFBcGlQeVVhVENzcVJtdGk0Q0JvRGJRbTZqUHZaNmtzeXBsdXJmb3lOd3d0R0dVaGZXRGU4dnJPZi83QW1WbG1lckJ5a0toUFhYb0JQZGo2K21FVVE9PdQH6Gx9OVytZOKHinBi79BRqcEn") 

print Logout(SessionID="AQAAARjtiKwAAA0xfDE4MXwyNTI4Mjc4OXw2MDA2fDEyMDcyNDU4MTUzNDPAcreR8zFN7kgYxffBN8IpNcfXFw", SessionData="AQAAARjtiKwAAA0xfExBQ1RWPTEyMDcxNTk0MjY1MDB8RUhXTT04NTY5Mjk4fFRJRFg9MnxMSVVQPTEyMDcxNTk0MTUyMzR8UExIUz1bMCwxMV21GsvUPVFhcxgMgs5bkosLlnW8rA")
########NEW FILE########
__FILENAME__ = example_feedback
from ebay.feedback import createDSRSummaryByCategory, createDSRSummaryByPeriod, createDSRSummaryByShippingDetail, createDSRSummaryByTransaction, getDSRSummary

transactionId= [{"itemId":"123", "transactionId":"72"}, {"itemId":"33", "transactionId":"21"}]

#WARNING: YOU WILL BE PLAYING WITH PRODUCTION EBAY.COM, SINCE THIS API IS NOT SUPPORTED IN SANDBOX
#print createDSRSummaryByCategory("12", "2011-04-30T09:00:00", "2011-05-30T09:00:00")
#print createDSRSummaryByPeriod("2011-04-30T09:00:00", "2011-05-30T09:00:00")
#print createDSRSummaryByShippingDetail("2011-04-30T09:00:00", "2011-05-30T09:00:00")
#print createDSRSummaryByTransaction(transactionId)
print getDSRSummary("1")

########NEW FILE########
__FILENAME__ = example_finding
from ebay.finding import (getSearchKeywordsRecommendation, findItemsByKeywords, 
                          findItemsByCategory, findItemsAdvanced, 
                          findItemsByProduct, findItemsIneBayStores, 
                          getHistograms)

#Use non standard configuration file
#from ebay.utils import set_config_file
#set_config_file("../config.ini")

print getSearchKeywordsRecommendation(encoding="XML", keywords="acordian")
print findItemsByKeywords(keywords="ipod", encoding="XML", 
                          paginationInput = {"entriesPerPage": "5", 
                                             "pageNumber"    : "1"})
print findItemsByCategory(categoryId="123")
print findItemsAdvanced()
print findItemsByProduct(productId="123")
print findItemsIneBayStores()
print getHistograms(categoryId="12")

########NEW FILE########
__FILENAME__ = example_merchandising
from ebay.merchandising import getDeals, getMostWatchedItems, getRelatedCategoryItems, getSimilarItems, getTopSellingProducts 


print getDeals(encoding="XML", keywords="ipod") #This operation is not documented
print getMostWatchedItems(encoding="JSON") 
print getRelatedCategoryItems(encoding="XML", categoryId="12") 
print getSimilarItems(encoding="XML", itemId="73")
print getTopSellingProducts(encoding="JSON") 

########NEW FILE########
__FILENAME__ = example_platform_notifications
from ebay.platform_notifications import SetNotificationPreferences, GetNotificationPreferences, GetNotificationsUsage 

print SetNotificationPreferences() 
print GetNotificationPreferences() 
print GetNotificationsUsage() 
########NEW FILE########
__FILENAME__ = example_product
from ebay.product import findCompatibilitiesBySpecification, getProductCompatibilities

from ebay.utils import Specification, Value 

spec1 = Specification(propertyName="Offset")
spec1.values = [Value(text="45.0")]
spec2 = Specification(propertyName="Rim Width")
spec2.values = [Value(text="8.0")]
spec = [spec1, spec2]

print findCompatibilitiesBySpecification(specification=spec, categoryId="170577") 
#print getProductCompatibilities()

# print findProducts()
# print findProductsByCompatibility()
# print getProductDetails()
########NEW FILE########
__FILENAME__ = example_resolution_case_management
from ebay.resolution_case_management import getUserCases, getEBPCaseDetail, provideTrackingInfo, issueFullRefund, offerOtherSolution, escalateToCustomerSuppport, appealToCustomerSupport, getActivityOptions, getVersion 

#DO NOT HAVE A CASE ID ON SANDBOX, NEED TO GENERATE AND CHECK ALL OPERATIONS

# case retrieval calls
print getUserCases() 
print getEBPCaseDetail() 

# Seller Option Calls
print provideTrackingInfo() 
print issueFullRefund() 
print offerOtherSolution() 
print escalateToCustomerSuppport() 
print appealToCustomerSupport() 

# Metadata calls
print getActivityOptions()
print getVersion()

########NEW FILE########
__FILENAME__ = example_shopping
from ebay.shopping import FindProducts, FindHalfProducts , GetSingleItem, GetItemStatus, GetShippingCosts, GetMultipleItems, GetUserProfile, FindPopularSearches, FindPopularItems, FindReviewsandGuides, GetCategoryInfo, GeteBayTime

print FindProducts(encoding='JSON', query='ipod', available_items='false', max_entries='10')
print FindHalfProducts(encoding='JSON', query='harry', max_entries='5')
print FindHalfProducts(encoding='JSON', product_type='ISBN', product_value='0439294827', include_selector='Items')
print GetSingleItem(encoding='JSON', item_id='110089122715')
print GetSingleItem(encoding='JSON', item_id='110089122716', include_selector='Description,ItemSpecifics,ShippingCosts')
print GetItemStatus(encoding='JSON', item_id='110089122716,110089122715')
print GetShippingCosts(encoding='JSON', item_id='110089122715', destination_country_code='US', destination_postal_code='95128', details='true', quantity_sold='1')
print GetMultipleItems(encoding='JSON', '110089122716')
print GetUserProfile(encoding='JSON', user_id='TESTUSER_magicalbookseller')
print GetUserProfile(encoding='JSON', user_id='TESTUSER_magicalbookseller', include_selector='Details')
print FindPopularSearches(encoding='JSON', query='dell', category_id='58058')
print FindPopularItems(encoding='JSON', query='potter', category_id_exclude='279')

#FindReviewsandGuides not working - Need to research later
#print FindReviewsandGuides(encoding='JSON', category_id='177')
#print FindReviewsandGuides(encoding='JSON', product_id='279')

print GetCategoryInfo(encoding='JSON', category_id='279', include_selector='ChildCategories')
print GeteBayTime(encoding='JSON');

########NEW FILE########
__FILENAME__ = example_trading
from ebay.trading import getCategories, filterCategories

print("All categories")
print(getCategories()) 

print("Antiques...")
for curCatXml in filterCategories(getCategories(), "Antiques"):
    print(curCatXml)
    
print("Everything with '&' character")
for curCatXml in filterCategories(getCategories(), "&"):
    print(curCatXml)
########NEW FILE########
__FILENAME__ = release
"""
===============================================================================
Create a release of "python-ebay". Upload files and metadata to PyPi.
===============================================================================

This script can be used to automate the release of new versions of the
"python-ebay" library, but it should also serve as documentation for the 
somewhat complex release process.

The PyPi site for "python-ebay" is at:
   https://pypi.python.org/pypi/python-ebay

Usage
======

The script has several options.

At the beginning of the release process you might want to run::

    python release.py -s
    
This stores your PyPi user name and password in "~/.pypirc". This step is not
necessary to make releases, but is convenient if you need several attempts to 
get the release right. If user name and password are not stored in in 
"~/.pypirc" Python's upload machinery will ask for them.

To upload metadata and files to PyPi run::

    python release.py -u
    
To clean up after a release, run::
    
    python release.py -c
    
This option deletes the "~/.pypirc" file.
"""

import argparse
import getpass
import os
import os.path as path 
import textwrap
import shutil
import subprocess

def relative(*path_fragments):
    'Create a file path that is relative to the location of this file.'
    return path.abspath(path.join(path.dirname(__file__), *path_fragments))


#Parse the command line arguments of the release script
parser = argparse.ArgumentParser(description=
    'Upload a new version of "python-ebay" to PyPi.')

parser.add_argument('-s, --start', dest='start', action='store_true',
                    help='Start the release process. '
                         'Temporarily store password and user name for PyPi '
                         'in "~/.pypirc".')
parser.add_argument('-u, --upload', dest='upload', action='store_true',
                    help='Upload files and metadata to PyPi.')
parser.add_argument('-c, --cleanup', dest='cleanup', action='store_true',
                    help='Cleanup after the release. '
                         'Especially remove "~/.pypirc".')

args = parser.parse_args()


#Do some necessary computations and checks
homedir = path.expanduser("~")
pypirc_path = path.join(homedir, ".pypirc")
if path.exists(pypirc_path):
    print ('"~/.pypirc" file exists. '
           'Delete it with "release -c" when you are done.\n')


#Default action: display help message. ----------------------------------------
if not (args.start or args.upload or args.cleanup):
    print "No action selected. You must select at least one action/option.\n"
    parser.print_help()
    exit(0)


#Start the release process ----------------------------------------------------
if args.start:
    #Create a ".pypirc" file 
    print 'Store PyPi username and password temporarily in "~/.pypirc" file.'
    username = raw_input("PyPi username:")
    password = getpass.getpass('PyPi password:')
    pypirc_text = textwrap.dedent(
        """
        [distutils]
        index-servers =
            pypi
        
        [pypi]
        repository: http://www.python.org/pypi
        username: {u}
        password: {p}
        """.format(u=username, p=password))
    with open(pypirc_path, "w") as pypirc_file:
        pypirc_file.write(pypirc_text)
        
    #Remind of necessary actions, that are easily forgotten. 
    print '\n=============================================='
    print "* Don't forget to increase the version."
    print '* Please run the tests before uploading a release!'
    print '============================================\n'
    #TODO: In the future, if tests really work, run the test suite.


#Do the release ---------------------------------------------------------------
if args.upload:
    #Backup "config.ini" because we need a working one for testing.
    config_ini_path = relative("ebay/config.ini")
    config_example_path = relative("ebay/config.ini.example")
    if path.exists(config_ini_path):
        #Test if "config.ini" is worth to be backed up
        config_ini_text = open(config_ini_path).read()
        config_example_text = open(config_example_path).read()
        if config_ini_text != config_example_text:
            #Backup the "config.ini" file
            for i in range(1000):
                config_bak_path = config_ini_path + ".{}.bak".format(i)
                if not path.exists(config_bak_path):
                    break
            shutil.copy(config_ini_path, config_bak_path)
    
    #Delete "config.ini" because it may contain secrets.
    #(However `python setup.py` will create a dummy "config.ini".)
    try: 
        os.remove(config_ini_path)
    except OSError: 
        pass
        
    #Build source distribution, upload metadata, upload distribution(s)
    subprocess.call(["python", "setup.py",
                     "sdist", 
                     "register", "-r", "pypi", 
                     "upload", "-r", "pypi",])


#Clean up from the release process. -------------------------------------------
if args.cleanup:
    #Remove the ".pypirc" file.
    if path.exists(pypirc_path):
        print 'Removing "~/.pypirc".'
        os.remove(pypirc_path)
    else:
        print 'Nothing to do.'

########NEW FILE########
__FILENAME__ = test_alternative_config
'''
Tests for functionality to use arbitrary configuration files.

The standard configuration file is part of the library itself. This is 
acceptable for web applications, but impossible for interactive programs.
For interactive program each user needs a separate configuration file. 

The test assumes the following directory layout::

    python-ebay/
        ebay/
            config.ini
        tests/
            test_alternative_config.py

The test script creates a copy of the initialization file: 

    ``config.ini.bak``
    
It can be used to restore the initialization file in case the original 
configuration file is lost.
'''
from os import system
from os.path import join, dirname, abspath
import unittest
from lxml import etree

from ebay.utils import set_config_file
from ebay.finding import findItemsByKeywords


def relative(*paths):
    "Create file paths that are relative to the location of this file."
    return abspath(join(dirname(abspath(__file__)), *paths))


#Arguments for `ebay.finding.findItemsByKeywords`
keywords = "ipod"
paginationInput = {"entriesPerPage": "5", "pageNumber" : "1"}
encoding = "XML"
#File paths
std_conf = relative("../ebay/config.ini")
std_conf_back = relative("../ebay/config.ini.bak")
alt_conf = relative("../config.apikey")
        

class TestAlternativeConfig(unittest.TestCase):

    def test_alternative_config(self):
        """
        Move configuration file ``config.ini`` to nonstandard location (one level
        up in directory hierarchy) and try to use the library.
        """
        #Backup the initialization file
        system("cp " + std_conf + " " + std_conf_back)
        #Move initialization file to nonstandard location
        system("mv " + std_conf + " " + alt_conf)
        #Look where the initialization files really are
        system("ls " + std_conf)
        system("ls " + std_conf_back)
        system("ls " + alt_conf)
        
        #Set alternative initialization file
        set_config_file(alt_conf)
        
        #Use the library and test if it works
        result = findItemsByKeywords(keywords=keywords, 
                                     paginationInput=paginationInput,
                                     encoding=encoding)
        root = etree.fromstring(result)
        ack = root.find("{http://www.ebay.com/marketplace/search/v1/services}ack").text
        self.assertEqual(ack, "Success")
        
        #Move initialization file back to original location
        system("mv " + alt_conf + " " + std_conf)
 

    def test_regular_config(self):
        "Test the library with the regular configuration file."
        #Look where the initialization files really are
        system("ls " + std_conf)
        system("ls " + std_conf_back)
        system("ls " + alt_conf)      #should not exist
        
        #Use the library and test if it works
        result = findItemsByKeywords(keywords=keywords, 
                                     paginationInput=paginationInput,
                                     encoding=encoding)
        root = etree.fromstring(result)
        ack = root.find("{http://www.ebay.com/marketplace/search/v1/services}ack").text
        self.assertEqual(ack, "Success")
    


if __name__ == "__main__":
    #Run single test manually. 
#    t = TestAlternativeConfig("test_alternative_config")
#    t.test_alternative_config()

    unittest.main()

########NEW FILE########
__FILENAME__ = test_best_match
import unittest
from lxml import etree

from ebay.best_match import *

#<!-- Standard Input Fields -->
siteResultsPerPage = "1"
ignoreFeatured = "false"
itemFilter = [{"paramName": "PriceMin", "paramValue": "50", "name": "Currency", "value": "USD"}]
outputSelector = ["FirstPageSummary", "SellerInfo"]
postSearchItemFilter = ["id1", "id2"]
postSearchSellerFilter = ["user1", "user2"]
Siteresultsperpage = "10"
entriesPerPage = "10"
paginationInput = {"entriesPerPage": "5", "pageNumber": "10"}


#<!-- Call-specific Input Fields -->
categoryId = "1"
keywords = "ipod"
productId = "123"
sellerUserName = "user1"


class TestBestMatchApi(unittest.TestCase):
    def test_keywords_findBestMatchItemDetailsAcrossStores(self):
        result = findBestMatchItemDetailsAcrossStores(keywords=keywords,\
                                                     siteResultsPerPage=siteResultsPerPage,\
                                                     categoryId=None, entriesPerPage=entriesPerPage,\
                                                     ignoreFeatured=ignoreFeatured,\
                                                     itemFilter=itemFilter,\
                                                     outputSelector=outputSelector,\
                                                     postSearchItemFilter=postSearchItemFilter,\
                                                     postSearchSellerFilter=postSearchSellerFilter,
                                                     encoding="XML")
        root = etree.fromstring(result)
        ack = root.find("{http://www.ebay.com/marketplace/search/v1/services}ack").text
        self.assertEqual(ack, "Success")


    def test_categoryId_findBestMatchItemDetailsAcrossStores(self):
        result = findBestMatchItemDetailsAcrossStores(keywords=None,\
                                                     siteResultsPerPage=siteResultsPerPage,\
                                                     categoryId=categoryId, entriesPerPage=entriesPerPage,\
                                                     ignoreFeatured=ignoreFeatured,\
                                                     itemFilter=itemFilter,\
                                                     outputSelector=outputSelector,\
                                                     postSearchItemFilter=postSearchItemFilter,\
                                                     postSearchSellerFilter=postSearchSellerFilter,
                                                     encoding="XML")
        root = etree.fromstring(result)
        ack = root.find("{http://www.ebay.com/marketplace/search/v1/services}ack").text
        self.assertEqual(ack, "Success")


    def test_findBestMatchItemDetailsAdvanced(self):
        result = findBestMatchItemDetailsAdvanced(keywords=keywords,\
                                                  siteResultsPerPage=siteResultsPerPage,\
                                                  categoryId=None,
                                                  entriesPerPage=entriesPerPage,
                                                  ignoreFeatured=ignoreFeatured,
                                                  itemFilter=itemFilter,
                                                  outputSelector=outputSelector,
                                                  postSearchItemFilter=postSearchItemFilter,
                                                  postSearchSellerFilter=postSearchSellerFilter,
                                                  encoding="XML")
        root = etree.fromstring(result)
        ack = root.find("{http://www.ebay.com/marketplace/search/v1/services}ack").text
        self.assertEqual(ack, "Success")


    def test_findBestMatchItemDetailsByCategory(self):
        result = findBestMatchItemDetailsByCategory(categoryId = categoryId,
                                                    siteResultsPerPage = siteResultsPerPage,
                                                    entriesPerPage = entriesPerPage,
                                                    ignoreFeatured = ignoreFeatured,
                                                    itemFilter = itemFilter,
                                                    outputSelector = outputSelector,
                                                    postSearchItemFilter = postSearchItemFilter,
                                                    postSearchSellerFilter = postSearchSellerFilter,
                                                    encoding="XML")
        root = etree.fromstring(result)
        ack = root.find("{http://www.ebay.com/marketplace/search/v1/services}ack").text
        self.assertEqual(ack, "Success")


    def test_findBestMatchItemDetailsByKeywords(self):
        result = findBestMatchItemDetailsByKeywords(keywords=keywords,
                                                    siteResultsPerPage = siteResultsPerPage,
                                                    entriesPerPage=entriesPerPage,
                                                    ignoreFeatured=ignoreFeatured,
                                                    itemFilter=itemFilter,
                                                    outputSelector=outputSelector,
                                                    postSearchItemFilter=postSearchItemFilter,
                                                    postSearchSellerFilter=postSearchSellerFilter,
                                                    encoding="XML")

        root = etree.fromstring(result)
        ack = root.find("{http://www.ebay.com/marketplace/search/v1/services}ack").text
        self.assertEqual(ack, "Success")


    def test_findBestMatchItemDetailsByProduct(self):
        result = findBestMatchItemDetailsByProduct(productId=productId,
                                                   siteResultsPerPage=siteResultsPerPage,
                                                   entriesPerPage=entriesPerPage,
                                                   ignoreFeatured=ignoreFeatured,
                                                   itemFilter=itemFilter,
                                                   outputSelector=outputSelector,
                                                   postSearchItemFilter=postSearchItemFilter,
                                                   postSearchSellerFilter=postSearchSellerFilter,
                                                   encoding="XML")

        root = etree.fromstring(result)
        ack = root.find("{http://www.ebay.com/marketplace/search/v1/services}ack").text
        self.assertEqual(ack, "Success")


    def test_findBestMatchItemDetailsBySeller(self):
        result = findBestMatchItemDetailsBySeller(categoryId=categoryId,
                                                  sellerUserName=sellerUserName,
                                                  ignoreFeatured=ignoreFeatured,
                                                  itemFilter=itemFilter,
                                                  paginationInput=paginationInput,
                                                  encoding="XML")
        root = etree.fromstring(result)
        ack = root.find("{http://www.ebay.com/marketplace/search/v1/services}ack").text
        self.assertEqual(ack, "Success")


    # def test_findBestMatchItemDetails(self):
        #     result = findBestMatchItemDetails()
        #     root = etree.fromstring(result)
        #     ack = root.find("{http://www.ebay.com/marketplace/search/v1/services}ack").text
        #     self.assertEqual(ack, "Success")


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_client_alerts
import unittest
from lxml import etree

from ebay.client_alerts import *

ChannelID = "370293550455"
ChannelType = "Item"
EventType = "ItemEnded"
MessageID = "1"
LastRequestTime = "2006-12-12T08:00:00"
encoding = "XML"
SessionID = "MySessionID"
SessionData = "p0SVs0iK4imqkoKkI1D"
ClientAlertsAuthToken = "AQAAARk1obQAAA0xfDE3ODcyNHw1MjQ2fDEyMDg1NDk0Njg0ODR8anFBcGlQeVVhVENzcVJtdGk0Q0JvRGJRbTZqUHZaNmtzeXBsdXJmb3lOd3d0R0dVaGZXRGU4dnJPZi83QW1WbG1lckJ5a0toUFhYb0JQZGo2K21FVVE9PdQH6Gx9OVytZOKHinBi79BRqcEn"


class TestClientAlertsApi(unittest.TestCase):
    def test_GetPublicAlerts(self):
        result = GetPublicAlerts(ChannelID=ChannelID,
                                 ChannelType=ChannelType,
                                 EventType=EventType, MessageID=MessageID,
                                 LastRequestTime=LastRequestTime,
                                 encoding=encoding)
        root = etree.fromstring(result)
        print root[0]
        ack = root.find("{urn:ebay:apis:eBLBaseComponents}Ack").text
        self.assertEqual(ack, "Success")


    def test_GetUserAlerts(self):
        result = GetUserAlerts(SessionID=SessionID,
                               SessionData=SessionData,
                               MessageID=MessageID,
                               encoding=encoding)
        root = etree.fromstring(result)
        ack = root.find("{urn:ebay:apis:eBLBaseComponents}Ack").text
        self.assertEqual(ack, "Failure")

    #Not sure how to fix it, the return value when request failing is:  issue#5
    def test_Login(self):
        result = Login(ClientAlertsAuthToken=ClientAlertsAuthToken,
                       MessageID=MessageID,
                       encoding=encoding)
        root = etree.fromstring(result)
        ack = root.find("{urn:ebay:apis:eBLBaseComponents}Ack").text
        self.assertEqual(ack, "Failure")


    def test_Logout(self):
        result = Logout(SessionID=SessionID,
                        SessionData=SessionData,
                        MessageID=MessageID,
                        encoding=encoding)
        root = etree.fromstring(result)
        ack = root.find("{urn:ebay:apis:eBLBaseComponents}Ack").text
        self.assertEqual(ack, "Failure")


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_feedback
import unittest
from lxml import etree

from ebay.feedback import *

#WARNING: YOU WILL BE PLAY`ING WITH PRODUCTION EBAY.COM, SINCE THIS API IS NOT SUPPORTED IN SANDBOX

categoryId = ["id1", "id2"]
dateRangeFrom = "date"
dateRangeTo = "date"
dateRangeEventType = "range type"
encoding = "XML"
shippingCostType = "Plane"
shippingDestinationType = "home"
shippingService = ["USPS"]
shipToCountry = ["USA", "CAN"]
transactionKey =  [{"itemId":"123", "transactionId":"72"}, {"itemId":"33", "transactionId":"21"}]


class TestFeedbackhApi(unittest.TestCase):
    def test_createDSRSummaryByCategory(self):
        result = createDSRSummaryByCategory(categoryId=categoryId,
                                            dateRangeFrom=dateRangeFrom,
                                            dateRangeTo=dateRangeTo,
                                            dateRangeEventType=dateRangeEventType,
                                            encoding=encoding)
        root = etree.fromstring(result)
        ack = root.find("ack").text
        self.assertEqual(ack, "Success")


    def test_createDSRSummaryByPeriod(self):
        result = createDSRSummaryByPeriod(dateRangeFrom=dateRangeFrom,
                                              dateRangeTo=dateRangeTo,
                                              dateRangeEventType=dateRangeEventType,
                                              encoding=encoding)
        root = etree.fromstring(result)
        ack = root.find("{http://www.ebay.com/marketplace/services}ack").text
        self.assertEqual(ack, "Success")


    def test_createDSRSummaryByShippingDetail(self):
        result = createDSRSummaryByShippingDetail(dateRangeFrom=dateRangeFrom,
                                                      dateRangeTo=dateRangeTo,
                                                      dateRangeEventType=dateRangeEventType,
                                                      shippingCostType=shippingCostType,
                                                      shippingDestinationType=shippingDestinationType,
                                                      shippingService=shippingService,
                                                      shipToCountry=shipToCountry,
                                                      encoding=encoding)
        root = etree.fromstring(result)
        ack = root.find("{http://www.ebay.com/marketplace/services}ack").text
        self.assertEqual(ack, "Success")


    def test_createDSRSummaryByTransaction(self):
        result = createDSRSummaryByTransaction(transactionKey=transactionKey, encoding=encoding)
        root = etree.fromstring(result)
        ack = root.find("{http://www.ebay.com/marketplace/services}ack").text
        self.assertEqual(ack, "Success")


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_finding
"""
Tests for package ``ebay.finding``

These tests are designed to work on the production system, not on Ebay's 
sandbox.
"""
import unittest
from lxml import etree

from ebay.finding import (getSearchKeywordsRecommendation, getHistograms,
                          findItemsAdvanced, findItemsByCategory, 
                          findItemsByKeywords, findItemsByProduct,
                          findItemsIneBayStores)


encoding = "XML" #default "JSON": Output encoding
keywords = "ipod"
#Get category IDs with function: `ebay.shopping.GetCategoryInfo`
categoryId = "73839" #iPods & MP3 Players
productId = "77767691" #iPod nano 5th gen. Black. Each product has unique ID.
storeName = "Fab Finds 4 U"
#This information is encoded in URLs so the affiliate can get his commission. 
affiliate = {"networkId":"9", "trackingId":"1234567890"}
buyerPostalCode = "10027" #central New York City, USA
paginationInput = {"entriesPerPage": "10", "pageNumber" : "1"}
#http://developer.ebay.com/DevZone/finding/CallRef/types/ItemFilterType.html
itemFilter = [{"name":"MaxPrice", "value":"100", 
               "paramName":"Currency", "paramValue":"EUR"}, 
              {"name":"MinPrice", "value":"50", 
               "paramName":"Currency", "paramValue":"EUR"}]
#http://developer.ebay.com/DevZone/finding/CallRef/findItemsByKeywords.html#Request.sortOrder
sortOrder = "EndTimeSoonest"
aspectFilter =  [{"aspectName":"Color", "aspectValueName":"Black"}, 
                 {"aspectName":"", "aspectValueName":""}]
#Multiple domain filters are currently unsupported
domainFilter = [{"domainName":"Other_MP3_Players"}] 
#http://developer.ebay.com/DevZone/finding/CallRef/types/OutputSelectorType.html
outputSelector =["StoreInfo", "SellerInfo", "AspectHistogram"]


class TestFindingApi(unittest.TestCase):
    def test_getSearchKeywordsRecommendation(self):
        result = getSearchKeywordsRecommendation(keywords="eipod", encoding=encoding)
#        print result
        root = etree.fromstring(result)
        ack = root.find("{http://www.ebay.com/marketplace/search/v1/services}ack").text
        self.assertEqual(ack, "Success")
        keyword = root.find("{http://www.ebay.com/marketplace/search/v1/services}keywords").text
        self.assertEqual(keyword, "ipod")
        

    def test_findItemsByKeywords(self):
        result = findItemsByKeywords(
                        keywords=keywords,
                        affiliate=affiliate, \                       buyerPostalCode=buyerPostalCode, \
                      paginationInput=paginationInput, \
                      sortOrder=sortOrder, \
                      aspectFilter=aspectFilter, \
                      domainFilter=domainFilter, \
                      itemFilter=itemFilter, \
                      outputSelector=outputSelector, \
                      encoding=encoding)
#        print result
        root = etree.fromstring(result)
        ack = root.find("{http://www.ebay.com/marketplace/search/v1/services}ack").text
        self.assertEqual(ack, "Success")
        #Number of Items between 0 and 10, because of paginationInput
        res_items = root.find("{http://www.ebay.com/marketplace/search/v1/services}searchResult")
        self.assertTrue(0 <= len(res_items) <= 10)


    def test_findItemsByCategory(self):
        result = findItemsByCategory(
                        categoryId=categoryId, \
                      affiliate=affiliate, \
                      buyerPostalCode=buyerPostalCode, \
                      sortOrder=sortOrder, \
                      paginationInput = paginationInput, \
                       spectFilter=aspectFilter, \
                        dainFilter=domainFilter, \
                        iteilter=itemFilter, \
                        outpuelector=outputSelector, \
                        encodinencoding)
#        print result
        root = etree.fromstring(result)
        ack = root.find("{http://www.ebay.com/marketplace/search/v1/services}ack").text
        self.assertEqual(ack, "Success")
        #Number of Items between 0 and 10, because of paginationInput
        res_items = root.find("{http://www.ebay.com/marketplace/search/v1/services}searchResult")
        self.assertTrue(0 <= len(res_items) <= 10)


    def test_findItemsAdvanced(self):
        result = findItemsAdvanced(
                      keywords=keywords, \
                      categoryId=tegoryId, \
                      affiliate=affiate, \
                      buyerPostalCodeuyerPostalCode, \
                      paginationInput= ginationInput, \
                      sortOrder=sortOrder\
                      aspectFilter=aspectFier, \
                      domainFilter=domainFilt, \
                      itemFilter=itemFilter, \
                    outputSelector=outputSelect, \
                      encoding=encoding)
#        pnt result
        root = etree.fromstring(result)
        ack = root.find("{http://www.ebay.com/marketplace/search/v1/services}ack").text
        self.assertEqual(ack, "Success")
        #Number of Items between 0 and 10, because of paginationInput
        res_items = root.find("{http://www.ebay.com/marketplace/search/v1/services}searchResult")
        self.assertTrue(0 <= len(res_items) <= 10)


    def test_findItemsByProduct(self):
        result = findItemsByProduct(
                       keywords=keywords, \
                       productId=productId, \
                     affiliate=affiliate, \
                     buyerPostalCode=buyerPostalCode, \                      paginationInput= paginationInput, \
                     sortOrder=sortOrder, \
                     itemFilter=itemFilter, \
                     outputSelector=outputSelector, \
                     encoding=encoding)
#        print result
      root = etree.fromstring(result)
        ack = root.find("{http://www.ebay.com/marketplace/search/v1/services}ack").text
        self.assertEqual(ack, "Failure") 


    def test_findItemsIneBayStores(self):
        result = findItemsIneBayStores(
                          keywords=keywords, \
                          storeName=storeName, \
                        affiliate=affiliate, \
                        buyerPostalCode=buyerPostalCode, \
                        paginationInput=paginationInput, \
                        sortOrder=sortOrder, \
                          asctFilter=aspectFilter, \
                        domainFilter=domainFilter, \
                          emFilter=itemFilter, \
                          outputlector=outputSelector, \
                          encoding=encoding)
        root = etree.fromstring(result)
        ack = root.find("{http://www.ebay.com/marketplace/search/v1/services}ack").text
        self.assertEqual(ack, "Success")
        #Number of Items between 0 and 10, because of paginationInput
        res_items = root.find("{http://www.ebay.com/marketplace/search/v1/services}searchResult")
        self.assertTrue(0 <= len(res_items) <= 10)


    def test_getHistograms(self):
        result = getHistograms(categoryId=categoryId, encoding=encoding)
#        print result
        root = etree.fromstring(result)
        ack = root.find("{http://www.ebay.com/marketplace/search/v1/services}ack").text
        self.assertEqual(ack, "Success")


if __name__ == '__main__':
#    #Run single test manually. 
#    t = TestFindingApi("test_findItemsByProduct")
#    t.test_findItemsByProduct()
    
    unittest.main()

########NEW FILE########
__FILENAME__ = test_merchandising
import unittest
from lxml import objectify

from ebay.merchandising import *

keywords = "ipod"


class TestMerchandisingApi(unittest.TestCase):
    def test_getDeals(self):
        result = getDeals(keywords=keywords, encoding="XML")
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Success")


    def test_getMostWatchedItems(self):
        result = getMostWatchedItems(affiliate=None, maxResults=None,categoryId=None, encoding="XML")
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Success")


    def test_getRelatedCategoryItems(self):
        result = getRelatedCategoryItems(affiliate=None,
                                         maxResults=None, \                                        categoryId=None, \
                                       itemFilter=None, \
                                       itemId=None, \
                                       encoding="XML")
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Success")


    def test_getSimilarItems(self):
        result = getSimilarItems(affiliate=None, \
                      maxResults=None, \
                      categoryId=None, \
                      categoryIdExclude=None, \
                      endTimeFrom=None, \
                      endTimeTo=None, \
                      itemFilter=None, \
                      itemId=None, \
                      listingType=None, \
                       axPrice=None, \
                        encoding="XML")
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Success")


    def test_getTopSellingProducts(self):
        result = getTopSellingProducts(affiliate=None, maxResults=None, encoding="XML")
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Success")


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_product
import unittest
from lxml import objectify

from ebay.product import *

categoryId = "170577"
#The Specification array of objects
spec1 = Specification(propertyName="Offset")
spec1.values = [Value(text="45.0")]
spec2 = Specification(propertyName="Rim Width")
spec2.values = [Value(text="8.0")]
spec = [spec1, spec2]



#The CompatibilityPropertyFilter array of objects
cpf1 = CompatibilityPropertyFilter(propertyName="Year")
cpf1.values = [Value(text="2006")]
cpf2 = CompatibilityPropertyFilter(propertyName="Make")
cpf2.values = [Value(text="Honda")]
cpf = [cpf1, cpf2]

dataSet = ["DisplayableProductDetails", "Searchable"]
datasetPropertyName = ["Make", "Model", "Year", "Trim", "Engine"]
exactMatch = "True"
paginationInput = {"entriesPerPage":"10", "totalPages":"10"}
sortOrder = [SortOrder(sortPriority="Sort1", order="Ascending", propertyName="Offset"), SortOrder(sortPriority="Sort2", order="Ascending", propertyName="Rim Width")]
encoding = "XML"


class TestProductApi(unittest.TestCase):
    def test_findCompatibilitiesBySpecification(self):
        result = findCompatibilitiesBySpecification(specification=spec, \
                                                    categoryId=categoryId, \
                                                    compatibilityPropertyFilter=None, \
                                                    dataSet=None, \
                                                    datasetPropertyName=None, \
                                                    exactMatch=None, \
                                                    paginationInput=None, \
                                                    sortOrder=None, \
                                                    encoding=encoding)
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Success")


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_resolution_case_management
import unittest
from lxml import objectify

from ebay.resolution_case_management import *


caseStatusFilter = ["OPEN","CLOSED"]
caseTypeFilter =  ["EBP_INR","RETURN"]
creationDateRangeFilterFrom = "2011-01-01T19:09:02.768Z"
creationDateRangeFilterTo = "2011-04-01T19:09:02.768Z"
itemFilter = {"itemId":"123", "transactionId":"72"}
paginationInput = {"entriesPerPage":"5", "pageNumber":"10"}
sortOrder = "CASE_STATUS_ASCENDING"

caseId = "1"
caseType = "2"
carrierUsed = "US"
trackingNumber = "3"
comments = "MyComment"
messageToBuyer = "Hello Buyer"
escalationReason = {"sellerSNADReason" : "BUYER_STILL_UNHAPPY_AFTER_REFUND"}
appealReason = "Buyer is dumb!"

encoding = "XML"


class TestResolutionCaseManagementApi(unittest.TestCase):

    def test_getUserCases(self):
        result = getUserCases(caseStatusFilter = caseStatusFilter,
                              caseTypeFilter = caseTypeFilter,
                              creationDateRangeFilterFrom = creationDateRangeFilterFrom,
                              creationDateRangeFilterTo = creationDateRangeFilterTo,
                              itemFilter = itemFilter,
                              paginationInput = paginationInput,
                              sortOrder = sortOrder,
                              encoding = encoding)
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Warning")

    def test_getEBPCaseDetail(self):
        result = getEBPCaseDetail(caseId=caseId, caseType=caseType, encoding=encoding)
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Failure")

    def test_provideTrackingInfo(self):
        result = provideTrackingInfo(caseId = caseId,
                                         caseType = caseType,
                                         carrierUsed = carrierUsed,
                                         trackingNumber = trackingNumber,
                                         comments = comments,
                                         encoding = encoding)
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Failure")

    def test_issueFullRefund(self):
        result = issueFullRefund(caseId = caseId,
                                     caseType = caseType,
                                     comments = comments,
                                     encoding = encoding)
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Failure")

    def test_offerOtherSolution(self):
        result = offerOtherSolution(caseId = caseId,
                                        caseType = caseType,
                                        messageToBuyer = messageToBuyer,
                                        encoding = encoding)
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Failure")

    def test_escalateToCustomerSuppport(self):
        result = escalateToCustomerSuppport(caseId = caseId,
                                            caseType = caseType,
                                            escalationReason = escalationReason,
                                            comments = comments,
                                            encoding = encoding)
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Warning")

    def test_appealToCustomerSupport(self):
        result = appealToCustomerSupport(caseId = caseId,
                                             caseType = caseType,
                                             appealReason = appealReason,
                                             comments = comments,
                                             encoding = encoding)
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Failure")

    def test_getActivityOptions(self):
        result = getActivityOptions(caseId = caseId,
                                        caseType = caseType,
                                        encoding = encoding)
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Failure")

    def test_getVersion(self):
        result = getVersion(encoding = encoding)
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Success")


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_shopping
import unittest
from lxml import objectify

from ebay.shopping import *

class TestShoppingApi(unittest.TestCase):
    def test_FindProducts(self):
        result = FindProducts()
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Success")

    def test_FindHalfProducts(self):
        result = FindHalfProducts()
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Success")

    def test_GetSingleItem(self):
        result = GetSingleItem()
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Success")

    def test_GetItemStatus(self):
        result = GetSingleItem()
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Success")

    def test_GetShippingCosts(self):
        result = GetShippingCosts()
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Success")

    def test_GetMultipleItems(self):
        result = GetMultipleItems()
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Success")

    def test_GetUserProfile(self):
        result = GetUserProfile()
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Success")

    def test_FindPopularSearches(self):
        result = FindPopularSearches()
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Success")

    def test_FindPopularItems(self):
        result = FindPopularItems()
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Success")

    def test_FindReviewsandGuides(self):
        result = FindReviewsandGuides()
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Success")

    def test_GetCategoryInfo(self):
        result = GetCategoryInfo()
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Success")

    def test_GeteBayTime(self):
        result = GeteBayTime()
        root = objectify.fromstring(result)
        ack = root.ack.text
        self.assertEqual(ack, "Success")


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
