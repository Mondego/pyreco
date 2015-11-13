__FILENAME__ = local_graph
# -*- coding: utf-8 -*-

import random
import cPickle as pickle
import subprocess


import networkx as nx

from renren import FriendsStore, RenRenRelationShip


RENREN_FILE = 'renren_data'

def _dump(data):
    with open(RENREN_FILE, 'w') as f:
        pickle.dump(data, f, 2)
        
        
def _load():
    try:
        with open(RENREN_FILE, 'r') as f:
            return pickle.load(f)
    except IOError:
        from utils import get_accounts
        r = RenRenRelationShip(*get_accounts())
        
        print 'collect friends'
        data = r.collect_friends(level=2)
        _dump(data)
        return data



class GraphAnalysis(object):
    def __init__(self):
        self.G = nx.Graph()
        self.min_node_size = 5
        self.max_node_size = 10

    def import_data(self, fs_list, min_keep=20):
        for fs in fs_list:
            self.G.add_node(fs.uid, lv=fs.level)
            if fs.friends:
                edges = [(fs.uid, u) for u in fs.friends]
                self.G.add_edges_from(edges)
                
                
        # 删掉level 2点，否则最后生成的图片点重叠在一起，看不清
        for n in self.G.nodes():
            if self.G.node[n]['lv'] == 2:
                self.G.remove_node(n)
                

        self.clear_nodes()
        self.degree = nx.degree(self.G)
        self.max_degree_value = max(self.degree.values())
        self.max_degree_value_floated = float(self.max_degree_value)
        
        
        
    def _clear_nodes(self):
        need_clear = False
        for n in self.G.nodes():
            if self.G.degree(n) < 2:
                self.G.remove_node(n)
                need_clear = True
                
        return need_clear
    
    
    def clear_nodes(self):
        while self._clear_nodes():
            pass
                
                
                
    def one_node_size(self, n):
        d = self.degree[n]
        d = d / self.max_degree_value_floated * self.max_node_size
        if d < self.min_node_size:
            d = self.min_node_size
        return d
        
                
    
    def get_node_size(self, nodes):
        return [self.one_node_size(n) for n in nodes]
    
    
    def one_node_color(self, n):
        d = self.degree[n]
        if d > self.max_degree_value / 2:
            _range = [0.5, 0.8]
        else:
            _range = [0.8, 1.0]
            
        _make = lambda: random.uniform(*_range)
        _love = _make
        _ohyes = _make
        
        return (_make(), _love(), _ohyes())
    
    
    
    def get_node_color(self, nodes):
        return [self.one_node_color(n) for n in nodes]
            
        


    def save(self, f='result.png', it=55):
        import matplotlib.pyplot as plt
        
        pos = nx.spring_layout(self.G, iterations=it)
        
        nx.draw_networkx_edges(self.G, pos, alpha=0.1)
        
        nx.draw_networkx_nodes(
            self.G,
            pos,
            node_size = self.get_node_size(self.G.nodes()),
            node_color = self.get_node_color(self.G.nodes()),
            alpha = 0.8,
        )
        
        plt.axis('off')
        plt.savefig(f, dpi=200)
        plt.clf()




class DrawGraphviz(GraphAnalysis):
    COLORS = [
        '#F20010', '#FC4292', '#B94C4A', '#D19D39', '#A79D0F', '#A65FCC',
        '#9470E7', '#19CD1D', '#1DDF9A', '#52A79F', '#24B5D9', '#2080DC',
    ]
    
    def __init__(self):
        super(DrawGraphviz, self).__init__()
        self.min_node_size = 0.05
        self.max_node_size = 0.2
        
        
        
    def one_node_color(self, n):
        d = self.degree[n]
        for index, color in enumerate(self.COLORS):
            if d * (index+1) >= self.max_degree_value:
                return color
        return color
        
        
        
    def save(self, f='result.png'):
        node_attr_template = {
            'sharp': "point",
            'color': "",
            'style': "filled",
            'width': 0.1,
            'height': 0.1,
            'fixedsize': "true",
            'label': "",
        }
        
        
        
        for n in self.G.nodes():
            attr = node_attr_template.copy()
            attr['width'] = self.one_node_size(n)
            attr['height'] = attr['width']
            attr['color'] = self.one_node_color(n)
            
            self.G.node[n] = attr
            
            edges = self.G.edge[n]
            for ed in edges:
                self.G.edge[n][ed] = {'color': '{0}22'.format(attr['color'])}
                
        
        DOT_FILE = '_renren.dot'
        nx.write_dot(self.G, DOT_FILE)
        pipe = subprocess.PIPE
        
        graphviz_command = ['dot']
        graphviz_command.append(DOT_FILE)
        graphviz_command.extend(['-Tpng', '-Kneato', '-o'])
        graphviz_command.append(f)
        
        p = subprocess.Popen(graphviz_command, stdin=pipe, stdout=pipe, stderr=pipe)
        ret_code = p.wait()
        if ret_code !=0 :
            _, ret_error_msg = p.communicate()
            raise Exception(ret_error_msg)



if __name__ == '__main__':
    data = _load()
    g = DrawGraphviz()
    g.import_data(data)
    g.save()


########NEW FILE########
__FILENAME__ = renren
# -*- coding: utf-8 -*-

import gevent.monkey
gevent.monkey.patch_all()

import gevent
from gevent.pool import Pool


import re
import random
import urllib
import urllib2
import cookielib

from lxml import etree



from utils import retry, gtimeout



class FriendsStore(object):
    __slots__ = ('uid', 'level', 'parent', 'friends')

    def __init__(self, uid, level, parent=None):
        self.uid = uid
        self.level = level
        self.parent = parent
        self.friends = set()

    def has_friend(self, target_uid):
        return target_uid in self.friends
    
    def get_common_friends(self, friend_obj):
        return self.friends & friend_obj.friends




class RenRen(object):
    USER_AGENT = [
        'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.57 Safari/537.17',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Ubuntu Chromium/23.0.1271.97 Chrome/23.0.1271.97 Safari/537.11',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.56 Safari/537.17',
        'Mozilla/5.0 (X11; Linux i686) AppleWebKit/534.34 (KHTML, like Gecko) rekonq/1.1 Safari/534.34',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/536.26.17 (KHTML, like Gecko) Version/6.0.2 Safari/536.26.17',
    ]
    
    
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.login_times = 0
        self.login()
    
    
    @classmethod
    def random_user_agent(cls):
        return random.choice(cls.USER_AGENT)
    
    
    @property
    def headers(self):
        return [
            ('User-Agent', RenRen.random_user_agent()),
        ]
    

    def login(self):
        self.login_times += 1
        
        url  = 'http://www.renren.com/ajaxLogin/login'
        data = urllib.urlencode({
                'email': self.email,
                'password': self.password,
                'origURL': 'http://www.renren.com/home',
                'domain': 'renren.com',
            })

        self.cookie = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie))
        
        #self.opener.addheaders = self.headers
        #不知为何，这里不能带 headers，没有headers反而顺利请求
        self.opener.addheaders = []
        
        urllib2.install_opener(self.opener)
        request = urllib2.Request(url, data=data)
        urllib2.urlopen(request)
        
        own_uid_pattern = re.compile('renren\.com/(\d+)/profile')
        profile_page = self.opener.open('http://www.renren.com/profile.do')
        own_uid = own_uid_pattern.findall(profile_page.geturl())
        if not own_uid:
            if self.login_times >= 3:
                raise Exception("Login Failure!")
            
            gevent.sleep(2)
            self.login()
        else:
            self.uid = own_uid[0]


    def view_page(self, uid):
        url = 'http://www.renren.com/{0}/profile'.format(uid)
        self.opener.open(url)


    def get_friends(self, uid=None):
        uid = uid or self.uid
        
        URL = 'http://friend.renren.com/GetFriendList.do?curpage={0}&id=' + str(uid)
        first_page = self.opener.open(URL.format(0))

        parse = etree.HTMLParser()
        tree = etree.parse(first_page, parse)
        friends_amount = int(tree.xpath('//div[@id="toc"]/p[1]/span/text()')[0])


        friends_pages, _rest = divmod(friends_amount, 20)
        if _rest > 0:
            friends_pages += 1


        friends_xpath = '//div[@id="list-results"]//li/p/a/@href'
        all_friends = []


        first_page_friends = [f.split('=')[1] for f in tree.xpath(friends_xpath)]
        all_friends.extend(first_page_friends)


        @retry()
        @gtimeout()
        def _get(p):
            html = self.opener.open(URL.format(p))
            tree = etree.parse(html, parse)
            res = [f.split('=')[1] for f in tree.xpath(friends_xpath)]
            return res

        #this is sync version
        for i in range(1, friends_pages):
            all_friends.extend(_get(i))


        # 多次测试发现，对同一个人的好友不能并发请求，
        # 如果并发，这些请求全部会block住，没有响应。
        # 所以是对不同的人起多个并发请求

        ## this is gevent version
        #pool = Pool(2)
        #for p in pool.imap_unordered(_get, xrange(1, friends_pages)):
        #    all_friends.extend(p)
        #    gevent.sleep(0)


        return all_friends
    



class RenRenRelationShip(object):
    def __init__(self, email, password):
        self.renren = RenRen(email, password)
        
    

    def collect_friends(self, uid=None, level=1):
        slot = []
        slot_dict = {}
        
        uid = uid or self.renren.uid
        uid = str(uid)
        
        def get_fs_by_level(lv):
            return filter(lambda s: s.level == lv, slot)
        
        @gtimeout(360, mute=True)
        def _collect(fo):
            friends = set(self.renren.get_friends(fo.uid))
            if uid in friends:
                friends.remove(uid)
            fo.friends = friends
            return fo
        
        

        fs = FriendsStore(uid, 0)
        slot.append(fs)
        
        def find_fs(uid, lv, parent):
            if uid not in slot_dict:
                slot_dict[uid] = FriendsStore(uid, lv, parent)
            return slot_dict[uid]

        pool = Pool(30)
        for l in range(level):
            pool_jobs = pool.imap(_collect, get_fs_by_level(l))
            for fo in pool_jobs:
                if not fo:
                    continue
                
                slot.extend(
                    [find_fs(u, l+1, fo.uid) for u in fo.friends]
                )
                
                
        print 'collect done'
        slot.pop(0)
        return slot




########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

import functools

import gevent



class TooLong(Exception):
    pass



def retry(times=2):
    def deco(func):
        @functools.wraps(func)
        def wraps(*args, **kwargs):
            for t in range(times):
                try:
                    return func(*args, **kwargs)
                except TooLong:
                    gevent.sleep(1)
                    continue
            print 'try %d times, but still failure' % times
            return []
        return wraps
    return deco



def gtimeout(t=10, mute=False):
    def deco(func):
        @functools.wraps(func)
        def wrap(*args, **kwargs):
            try:
                with gevent.Timeout(t, TooLong):
                    return func(*args, **kwargs)
            except TooLong:
                if mute:
                    return []
                raise
        return wrap
    return deco



def get_accounts():
    with open('account', 'r') as f:
        data = f.readlines()
        email = data[0].rstrip('\n')
        password = data[1].rstrip('\n')
        return email, password
    
    
########NEW FILE########
