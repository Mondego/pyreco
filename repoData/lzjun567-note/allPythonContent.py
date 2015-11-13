__FILENAME__ = fibonacci
import cProfile, pstats, StringIO

def f0(n):
    if n==0:
        return 0
    elif n==1:
        return 1
    elif n>1:
        return f(n-1) + f(n-2)

def f(n):
      prev = 1
      p_prev = -1
      result = 0
      for i in range(n+1):
          result = prev+p_prev
          p_prev = prev
          prev = result
      return result   

def perfromce_profile():
    import time 
    start = time.time()
    f0(1000000)
    end = time.time()
    print end-start
    start = time.time()
    f(1000000)
    print time.time()-start



if __name__ == '__main__':
    perfromce_profile()

########NEW FILE########
__FILENAME__ = test
keys = [chr(i) for i in range(97,97+26)]
result = {}
for key in keys:
     k = hash(key)%4
     if k not in result:
         result[k] = [key,]
     else:
         result.get(k).append(key)


print result

########NEW FILE########
__FILENAME__ = index
#! encoding=utf-8

import MySQLdb
import random

try:
    conn = MySQLdb.connect(
                host='localhost', 
                user='root',
                passwd='root',
                db='django_blog'
            )
except MySQLdb.Error, e:
    print "MySQL error %d:%s" % [e.args[0], e.args[1]]


def create_table(conn):
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE  IF NOT EXISTS my_user\
                    (id int NOT NULL PRIMARY KEY AUTO_INCREMENT,\
                    name varchar(50) NOT NULL,\
                    code varchar(50) NOT NULL \
                    )'
                  )
    cursor.close()

def insert_data(conn):
    '''
    随机插入10万条数据
    '''
    cursor = conn.cursor()
    names = ((random_name(), random_code()) for i in xrange(100000))
    cursor.executemany('INSERT INTO my_user (name, code) VALUES (%s, %s)', names)
    conn.commit()

def random_name():
    a_z = [ chr(97+i) for i in range(26)]
    return ''.join(random.sample(a_z, random.randint(1,26)))

def random_code():
    
    return  ''.join((str(random.randint(0,10)) for i in range(18)))



if __name__ == '__main__':
    create_table(conn)
    insert_data(conn)


########NEW FILE########
__FILENAME__ = application
#! /usr/bin/env python
from wsgiref.simple_server import make_server
from cgi import parse_qs, escape

html = """
    <html>
    <body>
        <form method="post" action="application.py">
        <p>
            Age:<input type="text" name="age">
        </p>
        <p>
        Hobbies:
        <input name="hobbies" type="checkbox" value="software">Software
        <input name="hobbies" type="checkbox" value="tunning">Auto Tunning
        </p>
        <p>
        <input type="submit" value="Submit">
        </p>
    <p>
    Age:%s<br>
    Hobbies:%s
    </p>
    </body>
    </html>
    """

def application(environ, start_response):
    #response_body = "the request method was %s" % environ['REQUEST_METHOD']
    #response_body = response_body*1000
    #status = '200 OK'
    #response_headers = [('Content-Type', 'text/plain'),
    #                    ('Content-Length', str(len(response_body)))]

    #start_response(status, response_headers)
    #return [response_body]
    try:
        request_body_size = int(environ.get('CONTENT_LENGTH', 0))
    except:
        request_body_size = 0 

    request_body = environ['wsgi.input'].read(request_body_size)
    d = parse_qs(request_body)

    age = d.get('age', [''])[0]
    hobbies = d.get('hobbies',[])

    age = escape(age)
    hobbies = [escape(hobby) for hobby in hobbies]

    response_body = html % (age or 'Empty',','.join(hobbies or ['No Hobbies']))
    status = '200 OK'
    response_headers = [('Content-Type','text/html'),
                        ('Content-Length', str(len(response_body)))]
    start_response(status, response_headers)
    return [response_body]



class AppClass:

    def __call__(self, environ, start_reponse):
        status = "200 OK"
        response_header = [('Content_Type','text/plain'),]
        start_reponse(status, response_header)
        return ["hello world ok!"]

class Upperware(object):
    def __init__(self, app):
        self.wrapped_app = app
    def __call__(self,environ, start_response):
        for data in self.wrapped_app(environ, start_response):
            return data.upper()
        
httpd= make_server('localhost',
                    8051,
                    Upperware(AppClass()),
                    )

#httpd.handle_request()
httpd.serve_forever()

########NEW FILE########
__FILENAME__ = autologin
# -*-encoding=utf-8 -*-
#/usr/bin/env python

import requests
import urllib

theurl = "http://www.iteye.com/login/"

header = {"User-Agent":"Mozilla/5.0 (indows NT 6.2; WOW64) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.43"}

datas = {"authenticity_token":"Y/cTDEBcgE+NzvQxYB38RMsg8Hl7590Eb0KoaX2WUx0=",
        "name":"lantian_123",
        "password":"****"
        }

datas = urllib.urlencode(datas)

r = requests.post(theurl,data=datas,headers=header)
print "login....."
print r.url
print r.status_code

cookie =r.cookies

datas = {
            "authenticity_token":"Y/cTDEBcgE+NzvQxYB38RMsg8Hl7590Eb0KoaX2WUx0=",
            "blog[blog_type]":"0",
            "blog[whole_category_id]":"4",
            "blog[title]":"helloworld",
            "blog[category_list]":"Java",
            "blog[body]":"hello,iteye,just a test",
            "blog[diggable]":"1",
        }
theurl = "http://liuzhijun.iteye.com/admin/blogs"

datas = urllib.urlencode(datas)
r2 = requests.post(theurl,data=datas,headers=header,cookies=cookie)
print "post...."
print r2.url
print r2.status_code
print r2.text


########NEW FILE########
__FILENAME__ = bar
from foo import a


if __name__=='__main__':
    a = 2
    import foo
    print foo.a

########NEW FILE########
__FILENAME__ = foo
a=1

########NEW FILE########
__FILENAME__ = recipel
class RomanNumeralConverter(object):
    def __init__(self, roman_numeral):
        self.roman_numeral = roman_numeral
        self.digit_map = {
                            "M":1000, 
                            "D":500,
                            "C":100,
                            "L":50,
                            "X":10,
                            "V":5,
                            "I":1
                        }
    def convert_to_decimal(self):
        val = 0
        for char in self.roman_numeral:
            val += self.digit_map[char]
        return val

import unittest
class RomanNumeralConverterTest(unittest.TestCase):
    def setUp(self):
        print 'setup'
    def tearDown(self):
        print 'teardown'
    def test_parsing_millenia(self):
        value = RomanNumeralConverter("M")
        self.assertEquals(1000, value.convert_to_decimal())
        
    def test_no_roman_numeral(self):
        value = RomanNumeralConverter(None)
        self.assertRaises(TypeError, value.convert_to_decimal)

    def test_empty_roman_numeral(self):
        value = RomanNumeralConverter("")
        self.assertTrue(value.convert_to_decimal() == 0)
        self.assertFalse(value.convert_to_decimal() > 0)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = sqlalchemytest
# -*- encoding:utf-8 -*-
import sqlalchemy
from sqlalchemy import Column,Integer,String,ForeignKey
from sqlalchemy.orm import sessionmaker,relationship,backref
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()   #1.构建基类
engine = sqlalchemy.create_engine("mysql+mysqldb://root:@localhost/test2?charset=utf8",echo=True)
#2. 创建引擎

class Artist(Base):
    __tablename__ = 'artist'
    artist_id = Column('id',Integer,primary_key=True)
    name = Column('name',String(100))
    albums = relationship('Album',cascade='all,delete',backref='artist')   #定义在一的这一端就是这么写
                                                                            # album对象可以 通过album.artist对象访问他的artist
#http://stackoverflow.com/questions/5033547/sqlachemy-cascade-delete

class Album(Base):
    __tablename__ = 'album'
    album_id = Column('id',Integer,primary_key=True)
    name = Column('name',String(100))
    artist_id = Column('artist',ForeignKey('artist.id'))  #注意下这里的外键，就是关联对象的id属性
    #artist = relationship(Artist,backref=backref('albums',cascade='all,delete'))    #设置backref后，通过artist对象直接访问它有哪些albums --〉 artist.albums
                                                                                    #还有级联删除，删除artist后，相关的album也会被删除
                                                                                    #这里要明确调用backref函数

Session = sessionmaker(bind=engine)  #3、连接数据库的session
Base.metadata.create_all(engine)    #4.初始化表结构

def save_artist():
    artist = Artist(name='aki misawa')
    session = Session()
    try:
        session.add(artist)
        session.flush()
        #print "artist id:",artist.artist_id
        session.commit()
    finally:
        session.close()
    print "artist id:",artist.artist_id

def save():
    artist = Artist(name='liuzhijun3')
    album = Album(name='hello3',artist=artist)
    album = Album(name='hello4',artist=artist)
    session = Session()

    try:
        session.add(album)
        session.commit()
    finally:
        session.close()

def list_all():
    
    try:
        session = Session()
        print "artists"
        print type(session.query(Artist).all())
        for a in session.query(Artist).all():
            print 'artist name:',a.name
            for album in a.albums:
                print 'album name:',album.name

        for a in session.query(Album).all():
            print a.name
            print a.artist.name
    finally:
        session.close()


def remove():
    session = Session()
    artist = session.query(Artist).get(6)
    session.delete(artist)
    session.commit()
    session.close()

if __name__ == '__main__':
    list_all()

########NEW FILE########
__FILENAME__ = startup
#!/usr/bin/env python
#! -*- encoding:utf-8 -*-
import time
import requests
from bs4 import BeautifulSoup

url = 'http://news.dbanotes.net'
r = requests.get(url)
soup = BeautifulSoup(r.text)

tag_url = soup.find_all('a',text="Login/Register")[0]

login_url = url + tag_url['href']

r = requests.get(login_url)

soup = BeautifulSoup(r.text)

fnid = soup.find_all(attrs={'type':'hidden'})[0]['value']

param = {'fnid':fnid,'u':'qwerty','p':'qwerty'}

r = requests.post('http://news.dbanotes.net/y',data = param)

soup = BeautifulSoup(r.text)


centers = soup.find_all('center')[1:]

for center in centers:
    print center
    try:
        url1 = url + "/" + center.a['href']
        cookies = {'user':'igbj8JwX'}
        r = requests.get(url1,cookies = cookies)
        print r.text
        #time.sleep(1)
        #break
    except :
        pass


########NEW FILE########
__FILENAME__ = test
class Parrot(object):
    def __init__(self):
        self.__voltage = 10000
    @property
    def voltage(self):
        return self.__voltage + 1

class C(object):
    def __init__(self):
        self._x = None

    def getx(self):
        return self._x
    def setx(self, value):
        self._x = value
    def delx(self):
        del self._x
    x = property(getx, setx, delx, "I'm the 'x' property.")


class MyDescriptor(object):
    def __get__(self, subject_instance, subject_class):
        return (self, subject_instance, subject_class)

    def __set__(self, subject_instance, value):
        print "%r %r %r" (self, subject_instance, value)

my_descriptor = MyDescriptor()

class Spam(object):
    my = my_descriptor

import re

class Email(object):
    
        def __init__(self):
            self._name = ''
    
        def __get__(self, obj, type=None):
            return self._name
    
        def __set__(self, obj, value):
            m = re.match('\w+@\w+\.\w+', value)
            if not m:
                raise Exception('email not valid')
            self._name = value
    
        def __delete__(self, obj):
            del self._name

#class Person(object):
#    email = Email()
    #def __init__(self, email):
    #    m = re.match('\w+@\w+\.\w+', email)
    #    if not m:
    #        raise Exception('email not valid')
    #    self.email = email

#class Person(object):
#
#    def __init__(self):
#        self._email = None
#
#    def get_email(self):
#        return self._email
#
#    def set_email(self, value):
#         m = re.match('\w+@\w+\.\w+', value)
#         if not m:
#             raise Exception('email not valid')
#         self._email = value
#
#    def del_email(self):
#        del self._email
#
#    email = property(get_email, set_email, del_email, 'this is email property')
        

class Person(object):

    def __init__(self):
        self._email = None

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, value):
         m = re.match('\w+@\w+\.\w+', value)
         if not m:
             raise Exception('email not valid')
         self._email = value

    @email.deleter
    def email(self):
        del self._email



class C(object):

    def __init__(self):
        self._a = None
    @property
    def a(self):
        return self._a

    @a.setter
    def a(self, value):
        self._a = int(value)

########NEW FILE########
__FILENAME__ = test2
class Test(object):
    def __init__(self, a):
        print 'init'
        print a
    def __call__(self, a,b):
        print 'call'
        print a,b


t = Test(3)
print (Test)
print type(t)

print(t(4,5))


########NEW FILE########
