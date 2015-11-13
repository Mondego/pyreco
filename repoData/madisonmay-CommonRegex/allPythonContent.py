__FILENAME__ = commonregex
from types import MethodType
import re

date        = re.compile(u'(?:(?<!\:)(?<!\:\d)[0-3]?\d(?:st|nd|rd|th)?\s+(?:of\s+)?(?:jan\.?|january|feb\.?|february|mar\.?|march|apr\.?|april|may|jun\.?|june|jul\.?|july|aug\.?|august|sep\.?|september|oct\.?|october|nov\.?|november|dec\.?|december)|(?:jan\.?|january|feb\.?|february|mar\.?|march|apr\.?|april|may|jun\.?|june|jul\.?|july|aug\.?|august|sep\.?|september|oct\.?|october|nov\.?|november|dec\.?|december)\s+(?<!\:)(?<!\:\d)[0-3]?\d(?:st|nd|rd|th)?)(?:\,)?\s*(?:\d{4})?|[0-3]?\d[-/][0-3]?\d[-/]\d{2,4}', re.IGNORECASE)
time        = re.compile(u'\d{1,2}:\d{2} ?(?:[ap]\.?m\.?)?|\d[ap]\.?m\.?', re.IGNORECASE)
phone       = re.compile(u'((?<![\d-])(?:\d[-.\s*])?(?:\(?\d{3}\)?[-.\s*]?)?\d{3}[-.\s*]?\d{4}(?![\d-]))')
link        = re.compile(u'(?:https?:\/\/)?(?:[\da-z\.-]+)\.(?:[a-z\.]{2,6})(?:[\/\w \.-]*)*\/', re.IGNORECASE)
email       = re.compile(u"([a-z0-9!#$%&'*+\/=?^_`{|.}~-]+@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)", re.IGNORECASE)
ip          = re.compile(u'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)', re.IGNORECASE)
ipv6        = re.compile(u'\s*(?!.*::.*::)(?:(?!:)|:(?=:))(?:[0-9a-f]{0,4}(?:(?<=::)|(?<!::):)){6}(?:[0-9a-f]{0,4}(?:(?<=::)|(?<!::):)[0-9a-f]{0,4}(?:(?<=::)|(?<!:)|(?<=:)(?<!::):)|(?:25[0-4]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-4]|2[0-4]\d|1\d\d|[1-9]?\d)){3})\s*', re.VERBOSE|re.IGNORECASE|re.DOTALL)
price       = re.compile(u'\$\s?[+-]?[0-9]{1,3}(?:,?[0-9])*(?:\.[0-9]{1,2})?')
hex_color   = re.compile(u'(#(?:[0-9a-fA-F]{8})|#(?:[0-9a-fA-F]{3}){1,2})\\b')
credit_card = re.compile(u'((?:(?:\\d{4}[- ]?){3}\\d{4}|\\d{16}))(?![\\d])')

regexes = {"dates"        : date,
           "times"        : time, 
           "phones"       : phone,
           "links"        : link,
           "emails"       : email,
           "ips"          : ip,
           "ipv6s"        : ipv6,
           "prices"       : price,
           "hex_colors"   : hex_color,
           "credit_cards" : credit_card}

class regex:

  def __init__(self, obj, regex):
    self.obj = obj
    self.regex = regex

  def __call__(self, *args):
    def regex_method(text=None):
      return [x.strip() for x in self.regex.findall(text or self.obj.text)]
    return regex_method

class CommonRegex(object):

    def __init__(self, text=""):
        self.text = text

        for k, v in regexes.items():
          setattr(self, k, regex(self, v)(self))

        if text:
            for key in regexes.keys():
                method = getattr(self, key)
                setattr(self, key, method())

if __name__ == "__main__":
    test = """"8:00 5:00AM Jan 9th 2012 8/23/12 www.google.com $4891.75
               2001:0db8::ff00:0042:8329 http://hotmail.com (520) 820 7123,
               1-230-241-2422 john_smith@gmail.com 127.0.0.1 #e9be4fff 1234567891011121
               1234-5678-9101-1121 """

    parse = CommonRegex(test)
    assert(parse.dates        == ['Jan 9th 2012', '8/23/12'])
    assert(parse.times        == ['8:00', '5:00AM', '00:00', '42:83'])
    assert(parse.phones       == ['(520) 820 7123', '1-230-241-2422'])
    assert(parse.links        == ['www.google.com', 'http://hotmail.com'])
    assert(parse.emails       == ['john_smith@gmail.com'])
    assert(parse.ips          == ['127.0.0.1'])
    assert(parse.ipv6s        == ['2001:0db8::ff00:0042:8329'])
    assert(parse.prices       == ['$4891.75'])
    assert(parse.hex_colors   == ['#e9be4fff'])
    assert(parse.credit_cards == ['1234567891011121', '1234-5678-9101-1121'])

########NEW FILE########
__FILENAME__ = commonregex
# coding: utf-8
from types import MethodType
import re

date        = re.compile(u'(?:(?<!\:)(?<!\:\d)[0-3]?\d(?:st|nd|rd|th)?\s+(?:of\s+)?(?:jan\.?|january|feb\.?|february|mar\.?|march|apr\.?|april|may|jun\.?|june|jul\.?|july|aug\.?|august|sep\.?|september|oct\.?|october|nov\.?|november|dec\.?|december)|(?:jan\.?|january|feb\.?|february|mar\.?|march|apr\.?|april|may|jun\.?|june|jul\.?|july|aug\.?|august|sep\.?|september|oct\.?|october|nov\.?|november|dec\.?|december)\s+(?<!\:)(?<!\:\d)[0-3]?\d(?:st|nd|rd|th)?)(?:\,)?\s*(?:\d{4})?|[0-3]?\d[-\./][0-3]?\d[-\./]\d{2,4}', re.IGNORECASE)
time        = re.compile(u'\d{1,2}:\d{2} ?(?:[ap]\.?m\.?)?|\d[ap]\.?m\.?', re.IGNORECASE)
phone       = re.compile(u'((?:(?<![\d-])(?:\+?\d{1,3}[-.\s*]?)?(?:\(?\d{3}\)?[-.\s*]?)?\d{3}[-.\s*]?\d{4}(?![\d-]))|(?:(?<![\d-])(?:(?:\(\+?\d{2}\))|(?:\+?\d{2}))\s*\d{2}\s*\d{3}\s*\d{4}(?![\d-])))')
link        = re.compile(u'(?i)((?:https?://|www\d{0,3}[.])?[a-z0-9.\-]+[.](?:(?:international)|(?:construction)|(?:contractors)|(?:enterprises)|(?:photography)|(?:immobilien)|(?:management)|(?:technology)|(?:directory)|(?:education)|(?:equipment)|(?:institute)|(?:marketing)|(?:solutions)|(?:builders)|(?:clothing)|(?:computer)|(?:democrat)|(?:diamonds)|(?:graphics)|(?:holdings)|(?:lighting)|(?:plumbing)|(?:training)|(?:ventures)|(?:academy)|(?:careers)|(?:company)|(?:domains)|(?:florist)|(?:gallery)|(?:guitars)|(?:holiday)|(?:kitchen)|(?:recipes)|(?:shiksha)|(?:singles)|(?:support)|(?:systems)|(?:agency)|(?:berlin)|(?:camera)|(?:center)|(?:coffee)|(?:estate)|(?:kaufen)|(?:luxury)|(?:monash)|(?:museum)|(?:photos)|(?:repair)|(?:social)|(?:tattoo)|(?:travel)|(?:viajes)|(?:voyage)|(?:build)|(?:cheap)|(?:codes)|(?:dance)|(?:email)|(?:glass)|(?:house)|(?:ninja)|(?:photo)|(?:shoes)|(?:solar)|(?:today)|(?:aero)|(?:arpa)|(?:asia)|(?:bike)|(?:buzz)|(?:camp)|(?:club)|(?:coop)|(?:farm)|(?:gift)|(?:guru)|(?:info)|(?:jobs)|(?:kiwi)|(?:land)|(?:limo)|(?:link)|(?:menu)|(?:mobi)|(?:moda)|(?:name)|(?:pics)|(?:pink)|(?:post)|(?:rich)|(?:ruhr)|(?:sexy)|(?:tips)|(?:wang)|(?:wien)|(?:zone)|(?:biz)|(?:cab)|(?:cat)|(?:ceo)|(?:com)|(?:edu)|(?:gov)|(?:int)|(?:mil)|(?:net)|(?:onl)|(?:org)|(?:pro)|(?:red)|(?:tel)|(?:uno)|(?:xxx)|(?:ac)|(?:ad)|(?:ae)|(?:af)|(?:ag)|(?:ai)|(?:al)|(?:am)|(?:an)|(?:ao)|(?:aq)|(?:ar)|(?:as)|(?:at)|(?:au)|(?:aw)|(?:ax)|(?:az)|(?:ba)|(?:bb)|(?:bd)|(?:be)|(?:bf)|(?:bg)|(?:bh)|(?:bi)|(?:bj)|(?:bm)|(?:bn)|(?:bo)|(?:br)|(?:bs)|(?:bt)|(?:bv)|(?:bw)|(?:by)|(?:bz)|(?:ca)|(?:cc)|(?:cd)|(?:cf)|(?:cg)|(?:ch)|(?:ci)|(?:ck)|(?:cl)|(?:cm)|(?:cn)|(?:co)|(?:cr)|(?:cu)|(?:cv)|(?:cw)|(?:cx)|(?:cy)|(?:cz)|(?:de)|(?:dj)|(?:dk)|(?:dm)|(?:do)|(?:dz)|(?:ec)|(?:ee)|(?:eg)|(?:er)|(?:es)|(?:et)|(?:eu)|(?:fi)|(?:fj)|(?:fk)|(?:fm)|(?:fo)|(?:fr)|(?:ga)|(?:gb)|(?:gd)|(?:ge)|(?:gf)|(?:gg)|(?:gh)|(?:gi)|(?:gl)|(?:gm)|(?:gn)|(?:gp)|(?:gq)|(?:gr)|(?:gs)|(?:gt)|(?:gu)|(?:gw)|(?:gy)|(?:hk)|(?:hm)|(?:hn)|(?:hr)|(?:ht)|(?:hu)|(?:id)|(?:ie)|(?:il)|(?:im)|(?:in)|(?:io)|(?:iq)|(?:ir)|(?:is)|(?:it)|(?:je)|(?:jm)|(?:jo)|(?:jp)|(?:ke)|(?:kg)|(?:kh)|(?:ki)|(?:km)|(?:kn)|(?:kp)|(?:kr)|(?:kw)|(?:ky)|(?:kz)|(?:la)|(?:lb)|(?:lc)|(?:li)|(?:lk)|(?:lr)|(?:ls)|(?:lt)|(?:lu)|(?:lv)|(?:ly)|(?:ma)|(?:mc)|(?:md)|(?:me)|(?:mg)|(?:mh)|(?:mk)|(?:ml)|(?:mm)|(?:mn)|(?:mo)|(?:mp)|(?:mq)|(?:mr)|(?:ms)|(?:mt)|(?:mu)|(?:mv)|(?:mw)|(?:mx)|(?:my)|(?:mz)|(?:na)|(?:nc)|(?:ne)|(?:nf)|(?:ng)|(?:ni)|(?:nl)|(?:no)|(?:np)|(?:nr)|(?:nu)|(?:nz)|(?:om)|(?:pa)|(?:pe)|(?:pf)|(?:pg)|(?:ph)|(?:pk)|(?:pl)|(?:pm)|(?:pn)|(?:pr)|(?:ps)|(?:pt)|(?:pw)|(?:py)|(?:qa)|(?:re)|(?:ro)|(?:rs)|(?:ru)|(?:rw)|(?:sa)|(?:sb)|(?:sc)|(?:sd)|(?:se)|(?:sg)|(?:sh)|(?:si)|(?:sj)|(?:sk)|(?:sl)|(?:sm)|(?:sn)|(?:so)|(?:sr)|(?:st)|(?:su)|(?:sv)|(?:sx)|(?:sy)|(?:sz)|(?:tc)|(?:td)|(?:tf)|(?:tg)|(?:th)|(?:tj)|(?:tk)|(?:tl)|(?:tm)|(?:tn)|(?:to)|(?:tp)|(?:tr)|(?:tt)|(?:tv)|(?:tw)|(?:tz)|(?:ua)|(?:ug)|(?:uk)|(?:us)|(?:uy)|(?:uz)|(?:va)|(?:vc)|(?:ve)|(?:vg)|(?:vi)|(?:vn)|(?:vu)|(?:wf)|(?:ws)|(?:ye)|(?:yt)|(?:za)|(?:zm)|(?:zw))(?:/[^\s()<>]+[^\s`!()\[\]{};:\'".,<>?\xab\xbb\u201c\u201d\u2018\u2019])?)', re.IGNORECASE)
email       = re.compile(u"([a-z0-9!#$%&'*+\/=?^_`{|.}~-]+@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)", re.IGNORECASE)
ip          = re.compile(u'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)', re.IGNORECASE)
ipv6        = re.compile(u'\s*(?!.*::.*::)(?:(?!:)|:(?=:))(?:[0-9a-f]{0,4}(?:(?<=::)|(?<!::):)){6}(?:[0-9a-f]{0,4}(?:(?<=::)|(?<!::):)[0-9a-f]{0,4}(?:(?<=::)|(?<!:)|(?<=:)(?<!::):)|(?:25[0-4]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-4]|2[0-4]\d|1\d\d|[1-9]?\d)){3})\s*', re.VERBOSE|re.IGNORECASE|re.DOTALL)
price       = re.compile(u'[$]\s?[+-]?[0-9]{1,3}(?:(?:,?[0-9]{3}))*(?:\.[0-9]{1,2})?')
hex_color   = re.compile(u'(#(?:[0-9a-fA-F]{8})|#(?:[0-9a-fA-F]{3}){1,2})\\b')
credit_card = re.compile(u'((?:(?:\\d{4}[- ]?){3}\\d{4}|\\d{15,16}))(?![\\d])')

regexes = {"dates"        : date,
           "times"        : time, 
           "phones"       : phone,
           "links"        : link,
           "emails"       : email,
           "ips"          : ip,
           "ipv6s"        : ipv6,
           "prices"       : price,
           "hex_colors"   : hex_color,
           "credit_cards" : credit_card}

class regex:

  def __init__(self, obj, regex):
    self.obj = obj
    self.regex = regex

  def __call__(self, *args):
    def regex_method(text=None):
      return [x.strip() for x in self.regex.findall(text or self.obj.text)]
    return regex_method

class CommonRegex(object):

    def __init__(self, text=""):
        self.text = text

        for k, v in regexes.items():
          setattr(self, k, regex(self, v)(self))

        if text:
            for key in regexes.keys():
                method = getattr(self, key)
                setattr(self, key, method())

########NEW FILE########
__FILENAME__ = test
# coding: utf-8
from commonregex import CommonRegex
import unittest


class RegexTestCase(unittest.TestCase):

    def setUp(self):
        self.parser = CommonRegex()


class TestDates(RegexTestCase):

    def test_numeric(self):
        matching = ["1-19-14", "1.19.14", "1.19.14", "01.19.14"]
        for s in matching:
            self.assertEqual(self.parser.dates(s), [s])

    def test_verbose(self):
        matching = ["January 19th, 2014", "Jan. 19th, 2014", "Jan 19 2014", "19 Jan 2014"]
        for s in matching:
            self.assertEqual(self.parser.dates(s), [s])


class TestTimes(RegexTestCase):

    def test_times(self):
        matching = ["09:45", "9:45", "23:45", "9:00am", "9am", "9:00 A.M.", "9:00 pm"]
        for s in matching:
            self.assertEqual(self.parser.times(s), [s])


class TestPhones(RegexTestCase):

    def test_phones(self):
        matching = ["12345678900", "1234567890", "+1 234 567 8900", "234-567-8900",
                   "1-234-567-8900", "1.234.567.8900", "5678900", "567-8900", 
                   "(123) 456 7890", "+41 22 730 5989", "(+41) 22 730 5989",
                   "+442345678900"]
        for s in matching:
            self.assertEqual(self.parser.phones(s), [s])


class TestLinks(RegexTestCase):

    def test_links(self):
        matching = ["www.google.com", "http://www.google.com", "www.google.com/?query=dog"
                   "sub.example.com", "http://www.google.com/%&#/?q=dog", "google.com"]
        non_matching = ["www.google.con"]
        for s in matching:
            self.assertEqual(self.parser.links(s), [s])
        for s in non_matching:
            self.assertNotEqual(self.parser.links(s), [s])


class TestEmails(RegexTestCase):

    def test_emails(self):
        matching = ["john.smith@gmail.com", "john_smith@gmail.com", "john@example.net"]
        non_matching = ["john.smith@gmail..com"]
        for s in matching:
            self.assertEqual(self.parser.emails(s), [s]) 
        for s in non_matching:
            self.assertNotEqual(self.parser.emails(s), [s])


class TestIPs(RegexTestCase):

    def test_ips(self):
        matching = ["127.0.0.1", "192.168.1.1", "8.8.8.8"]
        for s in matching:
            self.assertEqual(self.parser.ips(s), [s])


class TestIPv6s(RegexTestCase):

    def test_ipv6s(self):
        matching = ["fe80:0000:0000:0000:0204:61ff:fe9d:f156", "fe80:0:0:0:204:61ff:fe9d:f156",
                    "fe80::204:61ff:fe9d:f156", "fe80:0000:0000:0000:0204:61ff:254.157.241.86",
                    "fe80:0:0:0:0204:61ff:254.157.241.86", "fe80::204:61ff:254.157.241.86", "::1"]
        for s in matching:
            self.assertEqual(self.parser.ipv6s(s), [s])


class TestPrices(RegexTestCase):

    def test_prices(self):
        matching = ["$1.23", "$1", "$1,000", "$10,000.00"]
        non_matching = ["$1,10,0", "$100.000"]
        for s in matching:
            self.assertEqual(self.parser.prices(s), [s])
        for s in non_matching:
            self.assertNotEqual(self.parser.prices(s), [s])


class TestHexColors(RegexTestCase):

    def test_hexcolors(self):
        matching = ["#fff", "#123", "#4e32ff", "#12345678"]
        for s in matching:
            self.assertEqual(self.parser.hex_colors(s), [s])


class TestCreditCards(RegexTestCase):

    def test_creditcards(self):
        matching = ["0000-0000-0000-0000", "0123456789012345",
                    "0000 0000 0000 0000", "012345678901234"]
        for s in matching:
            self.assertEqual(self.parser.credit_cards(s), [s])


if __name__ == '__main__':
    test_cases = [TestDates, TestTimes, TestPhones, TestTimes, TestLinks, TestEmails,
                  TestIPs, TestIPv6s, TestPrices, TestHexColors, TestCreditCards]
    suites = []
    for case in test_cases:
        suites.append(unittest.TestLoader().loadTestsFromTestCase(case))

    all_tests = unittest.TestSuite(suites)
    unittest.TextTestRunner(verbosity=2).run(all_tests)
########NEW FILE########
