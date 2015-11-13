__FILENAME__ = benchmark
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from time import time
from timeit import timeit

start = time()
import zipcodetw
end = time()

print 'The package took {:.2f} seconds to load.'.format(end-start)

def test_find():

    zipcodetw.find('台北市')
    zipcodetw.find('台北市中正區')
    zipcodetw.find('台北市中正區仁愛路')
    zipcodetw.find('台北市中正區仁愛路2段')
    zipcodetw.find('台北市中正區仁愛路2段45號')

    zipcodetw.find('台中市')
    zipcodetw.find('台中市中區')
    zipcodetw.find('台中市中區台灣大道')
    zipcodetw.find('台中市中區台灣大道1段')
    zipcodetw.find('台中市中區台灣大道1段239號')

    zipcodetw.find('臺南市')
    zipcodetw.find('臺南市中西區')
    zipcodetw.find('臺南市中西區府前路')
    zipcodetw.find('臺南市中西區府前路1段')
    zipcodetw.find('臺南市中西區府前路1段226號')

n = 1000
print 'Timeit test_find with n={} took {:.2f} seconds.'.format(n, timeit(test_find, number=n))

########NEW FILE########
__FILENAME__ = stat
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import defaultdict
from pprint import pprint

def print_report(target_dict, key=None):

    len_pairs = len(target_dict)
    print 'Length of This Dict: {:>6,}'.format(len_pairs)
    print

    lenio_count_map = defaultdict(int)
    for k, v in target_dict.iteritems():
        lenio_count_map[(len(k), len(v))] += 1
    total_count = sum(lenio_count_map.itervalues())

    print 'Count of Each Length of Input, Output Pair:'
    print

    cum_pct = .0
    for lenio, count in sorted(lenio_count_map.iteritems(), key=key):
        pct = 100.*count/total_count
        cum_pct += pct
        print ' {:7} | {:>7,} | {:>6.2f}% | {:>6.2f}%'.format(lenio, count, pct, cum_pct)
    print

    print 'Total  : {:>6,}'.format(total_count)
    print 'Average: {:>9,.2f}'.format(1.*total_count/len(lenio_count_map))

if __name__ == '__main__':

    from time import time

    start = time()
    import zipcodetw
    end = time()

    print 'Took {:.2f}s to load.'.format(end-start)
    print

    print '# Tokens -> Rule Str, Zipcode Pairs (smaller is better)'
    print
    print_report(zipcodetw._dir.tokens_rzpairs_map)
    print
    print

    print '# Tokens -> Gradual Zipcode (bigger is better)'
    print
    print_report(zipcodetw._dir.tokens_gzipcode_map, key=lambda p: (p[0][0], -p[0][1]))

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from zipcodetw.util import Address

def test_address_init():

    expected_tokens = [(u'', u'', u'臺北', u'市'), (u'', u'', u'大安', u'區'), (u'', u'', u'市府', u'路'), (u'1', u'', u'', u'號')]
    assert Address(u'臺北市大安區市府路1號').tokens == expected_tokens
    assert Address('臺北市大安區市府路1號').tokens == expected_tokens

def test_address_init_subno():

    expected_tokens = [(u'', u'', u'臺北', u'市'), (u'', u'', u'大安', u'區'), (u'', u'', u'市府', u'路'), (u'1', u'之1', u'', u'號')]
    assert Address(u'臺北市大安區市府路1之1號').tokens == expected_tokens
    assert Address('臺北市大安區市府路1之1號').tokens == expected_tokens

def test_address_init_tricky_input():

    assert Address(u'桃園縣中壢市普義').tokens == [(u'', u'', u'桃園', u'縣'), (u'', u'', u'中壢', u'市'), (u'', u'', u'普義', u'')]
    assert Address(u'桃園縣中壢市普義10號').tokens == [(u'', u'', u'桃園', u'縣'), (u'', u'', u'中壢', u'市'), (u'', u'', u'普義', u''), (u'10', u'', u'', u'號')]

    assert Address(u'臺北市中山區敬業1路').tokens == [(u'', u'', u'臺北', u'市'), (u'', u'', u'中山', u'區'), (u'', u'', u'敬業1', u'路')]
    assert Address(u'臺北市中山區敬業1路10號').tokens == [(u'', u'', u'臺北', u'市'), (u'', u'', u'中山', u'區'), (u'', u'', u'敬業1', u'路'), (u'10', u'', u'', u'號')]

def test_address_init_normalization():

    expected_tokens = [(u'', u'', u'臺北', u'市'), (u'', u'', u'大安', u'區'), (u'', u'', u'市府', u'路'), (u'1', u'之1', u'', u'號')]
    assert Address(u'臺北市大安區市府路1之1號').tokens == expected_tokens
    assert Address(u'台北市大安區市府路1之1號').tokens == expected_tokens
    assert Address(u'臺北市大安區市府路１之１號').tokens == expected_tokens
    assert Address(u'臺北市　大安區　市府路 1 之 1 號').tokens == expected_tokens
    assert Address(u'臺北市，大安區，市府路 1 之 1 號').tokens == expected_tokens
    assert Address(u'臺北市, 大安區, 市府路 1 之 1 號').tokens == expected_tokens
    assert Address(u'臺北市, 大安區, 市府路 1 - 1 號').tokens == expected_tokens

def test_address_init_normalization_chinese_number():

    assert Address.normalize(u'八德路') == u'八德路'
    assert Address.normalize(u'三元街') == u'三元街'

    assert Address.normalize(u'三號') == u'3號'
    assert Address.normalize(u'十八號') == u'18號'
    assert Address.normalize(u'三十八號') == u'38號'

    assert Address.normalize(u'三段') == u'3段'
    assert Address.normalize(u'十八路') == u'18路'
    assert Address.normalize(u'三十八街') == u'38街'

    assert Address.normalize(u'信義路一段') == u'信義路1段'
    assert Address.normalize(u'敬業一路') == u'敬業1路'
    assert Address.normalize(u'愛富三街') == u'愛富3街'

def test_address_flat():

    addr = Address('臺北市大安區市府路1之1號')
    assert addr.flat(1) == addr.flat(-3) == u'臺北市'
    assert addr.flat(2) == addr.flat(-2) == u'臺北市大安區'
    assert addr.flat(3) == addr.flat(-1) == u'臺北市大安區市府路'
    assert addr.flat() == u'臺北市大安區市府路1之1號'

def test_address_repr():

    repr_str = "Address(u'\u81fa\u5317\u5e02\u5927\u5b89\u5340\u5e02\u5e9c\u8def1\u865f')"
    assert repr(Address('臺北市大安區市府路1號')) == repr_str
    assert repr(eval(repr_str)) == repr_str

from zipcodetw.util import Rule

def test_rule_init():

    rule = Rule('臺北市,中正區,八德路１段,全')
    assert rule.tokens == [(u'', u'', u'臺北', u'市'), (u'', u'', u'中正', u'區'), (u'', u'', u'八德', u'路'), (u'', u'', u'1', u'段')]
    assert rule.rule_tokens == set([u'全'])

    rule = Rule('臺北市,中正區,三元街,單全')
    assert rule.tokens == [(u'', u'', u'臺北', u'市'), (u'', u'', u'中正', u'區'), (u'', u'', u'三元', u'街')]
    assert rule.rule_tokens == set([u'單', u'全'])

    rule = Rule('臺北市,中正區,三元街,雙  48號以下')
    assert rule.tokens == [(u'', u'', u'臺北', u'市'), (u'', u'', u'中正', u'區'), (u'', u'', u'三元', u'街'), (u'48', u'', u'', u'號')]
    assert rule.rule_tokens == set([u'雙', u'以下'])

    rule = Rule('臺北市,中正區,大埔街,單  15號以上')
    assert rule.tokens == [(u'', u'', u'臺北', u'市'), (u'', u'', u'中正', u'區'), (u'', u'', u'大埔', u'街'), (u'15', u'', u'', u'號')]
    assert rule.rule_tokens == set([u'單', u'以上'])

    rule = Rule('臺北市,中正區,中華路１段,單  25之   3號以下')
    assert rule.tokens == [(u'', u'', u'臺北', u'市'), (u'', u'', u'中正', u'區'), (u'', u'', u'中華', u'路'), (u'', u'', u'1', u'段'), (u'25', u'之3', u'', u'號')]
    assert rule.rule_tokens == set([u'單', u'以下'])

    rule = Rule('臺北市,中正區,中華路１段,單  27號至  47號')
    assert rule.tokens == [(u'', u'', u'臺北', u'市'), (u'', u'', u'中正', u'區'), (u'', u'', u'中華', u'路'), (u'', u'', u'1', u'段'), (u'27', u'', u'', u'號'), (u'47', u'', u'', u'號')]
    assert rule.rule_tokens == set([u'單', u'至'])

    rule = Rule('臺北市,中正區,仁愛路１段,連   2之   4號以上')
    assert rule.tokens == [(u'', u'', u'臺北', u'市'), (u'', u'', u'中正', u'區'), (u'', u'', u'仁愛', u'路'), (u'', u'', u'1', u'段'), (u'2', u'之4', u'', u'號')]
    assert rule.rule_tokens == set([ u'以上'])

    rule = Rule('臺北市,中正區,杭州南路１段,　  14號含附號')
    assert rule.tokens == [(u'', u'', u'臺北', u'市'), (u'', u'', u'中正', u'區'), (u'', u'', u'杭州南', u'路'), (u'', u'', u'1', u'段'), (u'14', u'', u'', u'號')]
    assert rule.rule_tokens == set([u'含附號'])

    rule = Rule('臺北市,大同區,哈密街,　  47附號全')
    assert rule.tokens == [(u'', u'', u'臺北', u'市'), (u'', u'', u'大同', u'區'), (u'', u'', u'哈密', u'街'), (u'47', u'', u'', u'號')]
    assert rule.rule_tokens == set([u'附號全'])

    rule = Rule('臺北市,大同區,哈密街,雙  68巷至  70號含附號全')
    assert rule.tokens == [(u'', u'', u'臺北', u'市'), (u'', u'', u'大同', u'區'), (u'', u'', u'哈密', u'街'), (u'68', u'', u'', u'巷'), (u'70', u'', u'', u'號')]
    assert rule.rule_tokens == set([u'雙', u'至', u'含附號全'])

    rule = Rule('桃園縣,中壢市,普義,連  49號含附號以下')
    assert rule.tokens == [(u'', u'', u'桃園', u'縣'), (u'', u'', u'中壢', u'市'), (u'', u'', u'普義', u''), (u'49', u'', u'', u'號')]
    assert rule.rule_tokens == set([u'含附號以下'])

    rule = Rule('臺中市,西屯區,西屯路３段西平南巷,　   1之   3號及以上附號')
    assert rule.tokens == [(u'', u'', u'臺中', u'市'), (u'', u'', u'西屯', u'區'), (u'', u'', u'西屯', u'路'), (u'', u'', u'3', u'段'), (u'', u'', u'西平南', u'巷'), (u'1', u'之3', u'', u'號')]
    assert rule.rule_tokens == set([u'及以上附號'])

def test_rule_init_tricky_input():

    rule = Rule('新北市,中和區,連城路,雙 268之   1號以下')
    assert rule.tokens == [(u'', u'', u'新北', u'市'), (u'', u'', u'中和', u'區'), (u'', u'', u'連城', u'路'), (u'268', u'之1', u'', u'號')]
    assert rule.rule_tokens == set([u'雙', u'以下'])

    rule = Rule('新北市,泰山區,全興路,全')
    assert rule.tokens == [(u'', u'', u'新北', u'市'), (u'', u'', u'泰山', u'區'), (u'', u'', u'全興', u'路')]
    assert rule.rule_tokens == set([u'全'])

def test_rule_repr():

    repr_str = "Rule(u'\u81fa\u5317\u5e02\u5927\u5b89\u5340\u5e02\u5e9c\u8def1\u865f\u4ee5\u4e0a')"
    assert repr(Rule('臺北市大安區市府路1號以上')) == repr_str
    assert repr(eval(repr_str)) == repr_str

def test_rule_match():

    # standard address w/ standard rules

    addr = Address(u'臺北市大安區市府路5號')

    # 全單雙
    assert     Rule(u'臺北市大安區市府路全').match(addr)
    assert     Rule(u'臺北市大安區市府路單全').match(addr)
    assert not Rule(u'臺北市大安區市府路雙全').match(addr)

    # 以上 & 以下
    assert not Rule(u'臺北市大安區市府路6號以上').match(addr)
    assert     Rule(u'臺北市大安區市府路6號以下').match(addr)
    assert     Rule(u'臺北市大安區市府路5號以上').match(addr)
    assert     Rule(u'臺北市大安區市府路5號').match(addr)
    assert     Rule(u'臺北市大安區市府路5號以下').match(addr)
    assert     Rule(u'臺北市大安區市府路4號以上').match(addr)
    assert not Rule(u'臺北市大安區市府路4號以下').match(addr)

    # 至
    assert not Rule(u'臺北市大安區市府路1號至4號').match(addr)
    assert     Rule(u'臺北市大安區市府路1號至5號').match(addr)
    assert     Rule(u'臺北市大安區市府路5號至9號').match(addr)
    assert not Rule(u'臺北市大安區市府路6號至9號').match(addr)

    # 附號
    assert not Rule(u'臺北市大安區市府路6號及以上附號').match(addr)
    assert     Rule(u'臺北市大安區市府路6號含附號以下').match(addr)
    assert     Rule(u'臺北市大安區市府路5號及以上附號').match(addr)
    assert     Rule(u'臺北市大安區市府路5號含附號').match(addr)
    assert not Rule(u'臺北市大安區市府路5附號全').match(addr)
    assert     Rule(u'臺北市大安區市府路5號含附號以下').match(addr)
    assert     Rule(u'臺北市大安區市府路4號及以上附號').match(addr)
    assert not Rule(u'臺北市大安區市府路4號含附號以下').match(addr)

    # 單雙 x 以上, 至, 以下
    assert     Rule(u'臺北市大安區市府路單5號以上').match(addr)
    assert not Rule(u'臺北市大安區市府路雙5號以上').match(addr)
    assert     Rule(u'臺北市大安區市府路單1號至5號').match(addr)
    assert not Rule(u'臺北市大安區市府路雙1號至5號').match(addr)
    assert     Rule(u'臺北市大安區市府路單5號至9號').match(addr)
    assert not Rule(u'臺北市大安區市府路雙5號至9號').match(addr)
    assert     Rule(u'臺北市大安區市府路單5號以下').match(addr)
    assert not Rule(u'臺北市大安區市府路雙5號以下').match(addr)

def test_rule_match_gradual_address():

    # standard rule w/ gradual addresses

    rule = Rule('臺北市中正區丹陽街全')
    assert not rule.match(Address('臺北市'))
    assert not rule.match(Address('臺北市中正區'))
    assert not rule.match(Address('臺北市中正區仁愛路１段'))
    assert not rule.match(Address('臺北市中正區仁愛路１段1號'))

    rule = Rule('臺北市,中正區,仁愛路１段,　   1號')
    assert not rule.match(Address('臺北市'))
    assert not rule.match(Address('臺北市中正區'))
    assert not rule.match(Address('臺北市中正區仁愛路１段'))
    assert     rule.match(Address('臺北市中正區仁愛路１段1號'))

def test_rule_match_rule_all():

    # Be careful of the 全! It will bite you!

    rule = Rule('臺北市,中正區,八德路１段,全')
    assert     rule.match(Address('臺北市中正區八德路１段1號'))
    assert     rule.match(Address('臺北市中正區八德路１段9號'))
    assert not rule.match(Address('臺北市中正區八德路２段1號'))
    assert not rule.match(Address('臺北市中正區八德路２段9號'))

    rule = Rule('臺北市,中正區,三元街,單全')
    assert     rule.match(Address('臺北市中正區三元街1號'))
    assert not rule.match(Address('臺北市中正區三元街2號'))
    assert not rule.match(Address('臺北市中正區大埔街1號'))

    rule = Rule('臺北市,大同區,哈密街,　  45巷全')
    assert     rule.match(Address('臺北市大同區哈密街45巷1號'))
    assert     rule.match(Address('臺北市大同區哈密街45巷9號'))
    assert not rule.match(Address('臺北市大同區哈密街46巷1號'))
    assert not rule.match(Address('臺北市大同區哈密街46巷9號'))

def test_rule_match_tricky_input():

    # The address matched by it must have a even number.
    rule  = Rule('信義路一段雙全')

    addr1 = Address('信義路一段')
    addr2 = Address('信義路一段1號')
    addr3 = Address('信義路一段2號')

    assert not rule.match(addr1)
    assert not rule.match(addr2)
    assert     rule.match(addr3)

def test_rule_match_subno():

    rule = Rule('臺北市,中正區,杭州南路１段,　  14號含附號')
    assert not rule.match(Address('臺北市中正區杭州南路1段13號'))
    assert not rule.match(Address('臺北市中正區杭州南路1段13-1號'))
    assert     rule.match(Address('臺北市中正區杭州南路1段14號'))
    assert     rule.match(Address('臺北市中正區杭州南路1段14-1號'))
    assert not rule.match(Address('臺北市中正區杭州南路1段15號'))
    assert not rule.match(Address('臺北市中正區杭州南路1段15-1號'))

    rule = Rule('臺北市,大同區,哈密街,　  47附號全')
    assert not rule.match(Address('臺北市大同區哈密街46號'))
    assert not rule.match(Address('臺北市大同區哈密街46-1號'))
    assert not rule.match(Address('臺北市大同區哈密街47號'))
    assert     rule.match(Address('臺北市大同區哈密街47-1號'))
    assert not rule.match(Address('臺北市大同區哈密街48號'))
    assert not rule.match(Address('臺北市大同區哈密街48-1號'))

    rule = Rule('臺北市,大同區,哈密街,雙  68巷至  70號含附號全')
    assert not rule.match(Address('臺北市大同區哈密街66號'))
    assert not rule.match(Address('臺北市大同區哈密街66-1巷'))
    assert not rule.match(Address('臺北市大同區哈密街67號'))
    assert not rule.match(Address('臺北市大同區哈密街67-1巷'))
    assert     rule.match(Address('臺北市大同區哈密街68巷'))
    assert     rule.match(Address('臺北市大同區哈密街68-1號'))
    assert not rule.match(Address('臺北市大同區哈密街69號'))
    assert not rule.match(Address('臺北市大同區哈密街69-1巷'))
    assert     rule.match(Address('臺北市大同區哈密街70號'))
    assert     rule.match(Address('臺北市大同區哈密街70-1號'))
    assert not rule.match(Address('臺北市大同區哈密街71號'))
    assert not rule.match(Address('臺北市大同區哈密街71-1號'))

    rule = Rule('桃園縣,中壢市,普義,連  49號含附號以下')
    assert     rule.match(Address('桃園縣中壢市普義48號'))
    assert     rule.match(Address('桃園縣中壢市普義48-1號'))
    assert     rule.match(Address('桃園縣中壢市普義49號'))
    assert     rule.match(Address('桃園縣中壢市普義49-1號'))
    assert not rule.match(Address('桃園縣中壢市普義50號'))
    assert not rule.match(Address('桃園縣中壢市普義50-1號'))

    rule = Rule('臺中市,西屯區,西屯路３段西平南巷,　   2之   3號及以上附號')
    assert not rule.match(Address('臺中市西屯區西屯路3段西平南巷1號'))
    assert not rule.match(Address('臺中市西屯區西屯路3段西平南巷1-1號'))
    assert not rule.match(Address('臺中市西屯區西屯路3段西平南巷2號'))
    assert not rule.match(Address('臺中市西屯區西屯路3段西平南巷2-2號'))
    assert     rule.match(Address('臺中市西屯區西屯路3段西平南巷2-3號'))
    assert     rule.match(Address('臺中市西屯區西屯路3段西平南巷3號'))
    assert     rule.match(Address('臺中市西屯區西屯路3段西平南巷3-1號'))
    assert     rule.match(Address('臺中市西屯區西屯路3段西平南巷4號'))
    assert     rule.match(Address('臺中市西屯區西屯路3段西平南巷4-1號'))

from zipcodetw.util import Directory

class TestDirectory(object):

    def setup(self):

        chp_csv_lines = '''郵遞區號,縣市名稱,鄉鎮市區,原始路名,投遞範圍
10058,臺北市,中正區,八德路１段,全
10079,臺北市,中正區,三元街,單全
10070,臺北市,中正區,三元街,雙  48號以下
10079,臺北市,中正區,三元街,雙  50號以上
10068,臺北市,中正區,大埔街,單  15號以上
10068,臺北市,中正區,大埔街,雙  36號以上
10051,臺北市,中正區,中山北路１段,單   3號以下
10041,臺北市,中正區,中山北路１段,雙  48號以下
10051,臺北市,中正區,中山南路,單   5號以下
10041,臺北市,中正區,中山南路,雙  18號以下
10002,臺北市,中正區,中山南路,　   7號
10051,臺北市,中正區,中山南路,　   9號
10048,臺北市,中正區,中山南路,單  11號以上
10001,臺北市,中正區,中山南路,　  20號
10043,臺北市,中正區,中華路１段,單  25之   3號以下
10042,臺北市,中正區,中華路１段,單  27號至  47號
10010,臺北市,中正區,中華路１段,　  49號
10042,臺北市,中正區,中華路１段,單  51號以上
10065,臺北市,中正區,中華路２段,單  79號以下
10066,臺北市,中正區,中華路２段,單  81號至 101號
10068,臺北市,中正區,中華路２段,單 103號至 193號
10069,臺北市,中正區,中華路２段,單 195號至 315號
10067,臺北市,中正區,中華路２段,單 317號至 417號
10072,臺北市,中正區,中華路２段,單 419號以上
10055,臺北市,中正區,丹陽街,全
10051,臺北市,中正區,仁愛路１段,　   1號
10052,臺北市,中正區,仁愛路１段,連   2之   4號以上
10055,臺北市,中正區,仁愛路２段,單  37號以下
10060,臺北市,中正區,仁愛路２段,雙  48號以下
10056,臺北市,中正區,仁愛路２段,單  39號至  49號
10056,臺北市,中正區,仁愛路２段,雙  48之   1號至  64號
10062,臺北市,中正區,仁愛路２段,單  51號以上
10063,臺北市,中正區,仁愛路２段,雙  66號以上
20201,基隆市,中正區,義一路,　   1號
20241,基隆市,中正區,義一路,連   2號以上
20250,基隆市,中正區,義二路,全
20241,基隆市,中正區,義三路,單全
20248,基隆市,中正區,漁港一街,全
20249,基隆市,中正區,漁港二街,全
20249,基隆市,中正區,漁港三街,全
20249,基隆市,中正區,調和街,全
20248,基隆市,中正區,環港街,全
20243,基隆市,中正區,豐稔街,全
20249,基隆市,中正區,觀海街,全
36046,苗栗縣,苗栗市,大埔街,全
81245,高雄市,小港區,豐田街,全
81245,高雄市,小港區,豐登街,全
81245,高雄市,小港區,豐善街,全
81245,高雄市,小港區,豐街,全
81245,高雄市,小港區,豐點街,全
81257,高雄市,小港區,寶山街,全
81362,高雄市,左營區,大中一路,單 331號以上
81362,高雄市,左營區,大中一路,雙 386號以上
81362,高雄市,左營區,大中二路,單 241號以下
81368,高雄市,左營區,大中二路,雙 200號以下
81369,高雄市,左營區,大中二路,雙 202號至 698號
81369,高雄市,左營區,大中二路,單 243號至 479號
81365,高雄市,左營區,大中二路,單 481號以上
81354,高雄市,左營區,大中二路,雙 700號以上
81357,高雄市,左營區,大順一路,單  91號至  95號
81357,高雄市,左營區,大順一路,雙  96號至 568號
81357,高雄市,左營區,大順一路,單 201號至 389巷'''.split('\n')

        self.dir_ = Directory(':memory:', keep_alive=True)
        self.dir_.load_chp_csv(chp_csv_lines)

    def test_find(self):

        # It retuns a partial zipcode when the address doesn't match any rule in
        # our directory.

        # 10043,臺北市,中正區,中華路１段,單  25之   3號以下
        assert self.dir_.find('臺北市中正區中華路１段25號') == '10043'
        assert self.dir_.find('臺北市中正區中華路１段25-2號') == '10043'
        assert self.dir_.find('臺北市中正區中華路１段25-3號') == '10043'
        assert self.dir_.find('臺北市中正區中華路１段25-4號') == '100'
        assert self.dir_.find('臺北市中正區中華路１段26號') == '100'

        # 10042,臺北市,中正區,中華路１段,單  27號至  47號
        assert self.dir_.find('臺北市中正區中華路１段25號') == '10043'
        assert self.dir_.find('臺北市中正區中華路１段26號') == '100'
        assert self.dir_.find('臺北市中正區中華路１段27號') == '10042'
        assert self.dir_.find('臺北市中正區中華路１段28號') == '100'
        assert self.dir_.find('臺北市中正區中華路１段29號') == '10042'
        assert self.dir_.find('臺北市中正區中華路１段45號') == '10042'
        assert self.dir_.find('臺北市中正區中華路１段46號') == '100'
        assert self.dir_.find('臺北市中正區中華路１段47號') == '10042'
        assert self.dir_.find('臺北市中正區中華路１段48號') == '100'
        assert self.dir_.find('臺北市中正區中華路１段49號') == '10010'

        # 10010,臺北市,中正區,中華路１段,　  49號
        assert self.dir_.find('臺北市中正區中華路１段48號') == '100'
        assert self.dir_.find('臺北市中正區中華路１段49號') == '10010'
        assert self.dir_.find('臺北市中正區中華路１段50號') == '100'

        # 10042,臺北市,中正區,中華路１段,單  51號以上
        assert self.dir_.find('臺北市中正區中華路１段49號') == '10010'
        assert self.dir_.find('臺北市中正區中華路１段50號') == '100'
        assert self.dir_.find('臺北市中正區中華路１段51號') == '10042'
        assert self.dir_.find('臺北市中正區中華路１段52號') == '100'
        assert self.dir_.find('臺北市中正區中華路１段53號') == '10042'

    def test_find_gradually(self):

        assert self.dir_.find('臺北市') == '100'
        assert self.dir_.find('臺北市中正區') == '100'
        assert self.dir_.find('臺北市中正區仁愛路１段') == '1005'
        assert self.dir_.find('臺北市中正區仁愛路１段1號') == '10051'

    def test_find_middle_token(self):

        assert self.dir_.find('左營區') == '813'
        assert self.dir_.find('大中一路') == '81362'
        assert self.dir_.find('大中二路') == '813'
        assert self.dir_.find('左營區大中一路') == '81362'
        assert self.dir_.find('左營區大中二路') == '813'

        assert self.dir_.find('小港區') == '812'
        assert self.dir_.find('豐街') == '81245'
        assert self.dir_.find('小港區豐街') == '81245'

        assert self.dir_.find('中正區') == ''

        assert self.dir_.find('大埔街') == ''
        assert self.dir_.find('台北市大埔街') == '10068'
        assert self.dir_.find('苗栗縣大埔街') == '36046'

if __name__ == '__main__':
    import uniout
    #test_dir = TestDirectory()
    #test_dir.setup()
    #test_dir.test_find_middle_token()

    #r = Rule('台北市信義區市府路10號以下')
    #print r.tokens

    #a = Address('市府路1號')
    #print a.tokens
    #print r.match(a)

    #a = Address('台北市信義區市府路1號')
    #print a.tokens
    #print r.match(a)

    r = Rule('新北市,中和區,景平路,雙  64號以下')
    print r.tokens

    a = Address('新北市景平路64巷13弄13號')
    print a.tokens
    print r.match(a)

########NEW FILE########
__FILENAME__ = zipcodetw_server
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import zipcodetw
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('finder.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/api/find')
def api_find():
    return jsonify(result=zipcodetw.find(request.values.get('address')))

if __name__ == '__main__':
    app.run(debug=True)

########NEW FILE########
__FILENAME__ = builder
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from . import _chp_csv_path, _db_path
from .util import Directory

def build(chp_csv_path=None, db_path=None):

    # use default path if either path is not given.

    if chp_csv_path is None:
        chp_csv_path = _chp_csv_path
    if db_path is None:
        db_path = _db_path

    # build the index

    dir_ = Directory(db_path)
    with open(chp_csv_path) as csv_f:
        dir_.load_chp_csv(csv_f)

def build_cmd(chp_csv_path=None, db_path=None):
    '''Build a ZIP code index by the CSV from Chunghwa Post.

    -i, --chp-csv-path  The path of the CSV.
    -o, --db-path       The output path.
    '''

    print 'Building ZIP code index ...',
    sys.stdout.flush()
    build(chp_csv_path, db_path)
    print 'Done.'

if __name__ == '__main__':

    try:
        import clime
    except ImportError:
        build(*sys.argv[1:])
    else:
        clime.start(white_pattern=clime.CMD_SUFFIX)

########NEW FILE########
__FILENAME__ = util
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

class Address(object):

    TOKEN_RE = re.compile(u'''
        (?:
            (?P<no>\d+)
            (?P<subno>之\d+)?
            (?=[巷弄號樓]|$)
            |
            (?P<name>.+?)
        )
        (?:
            (?P<unit>[縣市鄉鎮市區村里鄰路街段巷弄號樓])
            |
            (?=\d+(?:之\d+)?[巷弄號樓]|$)
        )
    ''', re.X)

    NO    = 0
    SUBNO = 1
    NAME  = 2
    UNIT  = 3

    TO_REPLACE_RE = re.compile(u'''
        [ 　,，台~-]
        |
        [０-９]
        |
        [一二三四五六七八九]?
        十?
        [一二三四五六七八九]
        (?=[段路街巷弄號樓])
    ''', re.X)

    # the strs matched but not in here will be removed
    TO_REPLACE_MAP = {
        u'-': u'之', u'~': u'之', u'台': u'臺',
        u'１': u'1', u'２': u'2', u'３': u'3', u'４': u'4', u'５': u'5',
        u'６': u'6', u'７': u'7', u'８': u'8', u'９': u'9', u'０': u'0',
        u'一': u'1', u'二': u'2', u'三': u'3', u'四': u'4', u'五': u'5',
        u'六': u'6', u'七': u'7', u'八': u'8', u'九': u'9',
    }

    CHINESE_NUMERALS_SET = set(u'一二三四五六七八九十')

    @staticmethod
    def normalize(s):

        if isinstance(s, str):
            s = s.decode('utf-8')

        def replace(m):

            found = m.group()

            if found in Address.TO_REPLACE_MAP:
                return Address.TO_REPLACE_MAP[found]

            # for '十一' to '九十九'
            if found[0] in Address.CHINESE_NUMERALS_SET:
                len_found = len(found)
                if len_found == 2:
                    return u'1'+Address.TO_REPLACE_MAP[found[1]]
                if len_found == 3:
                    return Address.TO_REPLACE_MAP[found[0]]+Address.TO_REPLACE_MAP[found[2]]

            return u''

        s = Address.TO_REPLACE_RE.sub(replace, s)

        return s

    @staticmethod
    def tokenize(addr_str):
        return Address.TOKEN_RE.findall(Address.normalize(addr_str))

    def __init__(self, addr_str):
        self.tokens = Address.tokenize(addr_str)

    def __len__(self):
        return len(self.tokens)

    def flat(self, sarg=None, *sargs):
        return u''.join(u''.join(token) for token in self.tokens[slice(sarg, *sargs)])

    def pick_to_flat(self, *idxs):
        return u''.join(u''.join(self.tokens[idx]) for idx in idxs)

    def __repr__(self):
        return 'Address(%r)' % self.flat()

    def parse(self, idx):
        try:
            token = self.tokens[idx]
        except IndexError:
            return (0, 0)
        else:
            return (
                int(token[Address.NO]        or 0),
                int(token[Address.SUBNO][1:] or 0)
            )

class Rule(Address):

    RULE_TOKEN_RE = re.compile(u'''
        及以上附號|含附號以下|含附號全|含附號
        |
        以下|以上
        |
        附號全
        |
        [連至單雙全](?=[\d全]|$)
    ''', re.X)

    @staticmethod
    def part(rule_str):

        rule_str = Address.normalize(rule_str)

        rule_tokens = set()

        def extract(m):

            token = m.group()
            retval = u''

            if token == u'連':
                token = u''
            elif token == u'附號全':
                retval = u'號'

            if token:
                rule_tokens.add(token)

            return retval

        addr_str = Rule.RULE_TOKEN_RE.sub(extract, rule_str)

        return (rule_tokens, addr_str)

    def __init__(self, rule_str):
        self.rule_tokens, addr_str = Rule.part(rule_str)
        Address.__init__(self, addr_str)

    def __repr__(self):
        return 'Rule(%r)' % (self.flat()+u''.join(self.rule_tokens))

    def match(self, addr):

        # except tokens reserved for rule token

        my_last_pos = len(self.tokens)-1
        my_last_pos -= bool(self.rule_tokens) and u'全' not in self.rule_tokens
        my_last_pos -= u'至' in self.rule_tokens

        # tokens must be matched exactly

        if my_last_pos >= len(addr.tokens):
            return False

        i = my_last_pos
        while i >= 0:
            if self.tokens[i] != addr.tokens[i]:
                return False
            i -= 1

        # check the rule tokens

        his_no_pair = addr.parse(my_last_pos+1)
        if self.rule_tokens and his_no_pair == (0, 0):
            return False

        my_no_pair      = self.parse(-1)
        my_asst_no_pair = self.parse(-2)
        for rt in self.rule_tokens:
            if (
                (rt == u'單'         and not his_no_pair[0] & 1 == 1) or
                (rt == u'雙'         and not his_no_pair[0] & 1 == 0) or
                (rt == u'以上'       and not his_no_pair >= my_no_pair) or
                (rt == u'以下'       and not his_no_pair <= my_no_pair) or
                (rt == u'至'         and not (
                    my_asst_no_pair <= his_no_pair <= my_no_pair or
                    u'含附號全' in self.rule_tokens and his_no_pair[0] == my_no_pair[0]
                )) or
                (rt == u'含附號'     and not  his_no_pair[0] == my_no_pair[0]) or
                (rt == u'附號全'     and not (his_no_pair[0] == my_no_pair[0] and his_no_pair[1] > 0)) or
                (rt == u'及以上附號' and not  his_no_pair >= my_no_pair) or
                (rt == u'含附號以下' and not (his_no_pair <= my_no_pair  or his_no_pair[0] == my_no_pair[0]))
            ):
                return False

        return True

import sqlite3
import csv
from functools import wraps

class Directory(object):

    @staticmethod
    def get_common_part(str_a, str_b):

        if str_a is None: return str_b
        if str_b is None: return str_a

        i = 0 # for the case range is empty
        for i in range(min(len(str_a), len(str_b))):
            if str_a[i] != str_b[i]:
                break
        else:
            i += 1

        return str_a[:i]

    def __init__(self, db_path, keep_alive=False):
        self.db_path = db_path
        # It will always use a same connection if keep_alive is true.
        self.keep_alive = keep_alive
        self.conn = None
        self.cur = None

    def create_tables(self):

        self.cur.execute('''
            create table precise (
                addr_str text,
                rule_str text,
                zipcode  text,
                primary key (addr_str, rule_str)
            );
        ''')

        self.cur.execute('''
            create table gradual (
                addr_str text primary key,
                zipcode  text
            );
        ''')

    def put_precise(self, addr_str, rule_str, zipcode):

        self.cur.execute('insert or ignore into precise values (?, ?, ?);', (
            addr_str,
            rule_str,
            zipcode
        ))

        return self.cur.rowcount

    def put_gradual(self, addr_str, zipcode):

        self.cur.execute('''
            select zipcode
            from   gradual
            where  addr_str = ?;
        ''', (addr_str,))

        row = self.cur.fetchone()
        if row is None:
            stored_zipcode = None
        else:
            stored_zipcode = row[0]

        self.cur.execute('replace into gradual values (?, ?);', (
            addr_str,
            Directory.get_common_part(stored_zipcode, zipcode),
        ))

        return self.cur.rowcount

    def put(self, head_addr_str, tail_rule_str, zipcode):

        addr = Address(head_addr_str)

        # (a, b, c)

        self.put_precise(
            addr.flat(),
            head_addr_str+tail_rule_str,
            zipcode
        )

        # (a, b, c) -> (a,); (a, b); (a, b, c); (b,); (b, c); (c,)

        len_tokens = len(addr)
        for f in range(len_tokens):
            for l in range(f, len_tokens):
                self.put_gradual(
                    addr.flat(f, l+1),
                    zipcode
                )

        if len_tokens >= 3:
            # (a, b, c, d) -> (a, c)
            self.put_gradual(addr.pick_to_flat(0, 2), zipcode)

    def within_a_transaction(method):

        @wraps(method)
        def method_wrapper(self, *args, **kargs):

            if not self.keep_alive or self.conn is None:
                self.conn = sqlite3.connect(self.db_path)
            self.cur = self.conn.cursor()

            try:
                retval = method(self, *args, **kargs)
            except:
                self.conn.rollback()
                raise
            else:
                self.conn.commit()
            finally:
                self.cur.close()
                if not self.keep_alive:
                    self.conn.close()

            return retval

        return method_wrapper

    @within_a_transaction
    def load_chp_csv(self, chp_csv_lines):

        self.create_tables()

        lines_iter = iter(chp_csv_lines)
        next(lines_iter)

        for row in csv.reader(lines_iter):
            self.put(
                ''.join(row[1:-1]).decode('utf-8'),
                row[-1].decode('utf-8'),
                row[0].decode('utf-8'),
            )

    def get_rule_str_zipcode_pairs(self, addr_str):

        self.cur.execute('''
            select rule_str, zipcode
            from   precise
            where  addr_str = ?;
        ''', (addr_str,))

        return self.cur.fetchall()

    def get_gradual_zipcode(self, addr_str):

        self.cur.execute('''
            select zipcode
            from   gradual
            where  addr_str = ?;
        ''', (addr_str,))

        row = self.cur.fetchone()
        return row and row[0] or None

    @within_a_transaction
    def find(self, addr_str):

        addr = Address(addr_str)
        len_addr_tokens = len(addr.tokens)

        # avoid unnecessary iteration
        start_len = len_addr_tokens
        while start_len >= 0:
            if addr.parse(start_len-1) == (0, 0):
                break
            start_len -= 1

        for i in range(start_len, 0, -1):

            addr_str = addr.flat(i)

            rzpairs = self.get_rule_str_zipcode_pairs(addr_str)

            # for handling insignificant tokens and redundant unit
            if (
                # It only runs once, and must be the first iteration.
                i == start_len and
                len_addr_tokens >= 4 and
                addr.tokens[2][Address.UNIT] in u'村里' and
                not rzpairs
            ):

                if addr.tokens[3][Address.UNIT] == u'鄰':
                    # delete the insignificant token (whose unit is 鄰)
                    del addr.tokens[3]
                    len_addr_tokens -= 1

                if len_addr_tokens >= 4 and addr.tokens[3][Address.UNIT] == u'號':
                    # empty the redundant unit in the token
                    addr.tokens[2] = (u'', u'', addr.tokens[2][Address.NAME], u'')
                else:
                    # delete insignificant token (whose unit is 村 or 里)
                    del addr.tokens[2]

                rzpairs = self.get_rule_str_zipcode_pairs(addr.flat(3))

            if rzpairs:
                for rule_str, zipcode in rzpairs:
                    if Rule(rule_str).match(addr):
                        return zipcode

            gzipcode = self.get_gradual_zipcode(addr_str)
            if gzipcode:
                return gzipcode

        return u''

########NEW FILE########
