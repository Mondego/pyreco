__FILENAME__ = renren
# -*- coding: utf8 -*-
import urllib
import urllib2,httplib
import cookielib
from bs4 import BeautifulSoup

class RenrenAutoAuth(object):
	'''
	人人自动认证授权
	'''
	def __init__(self,app_id, app_key, app_secret, redirect_uri, username, password, response_type='code'):
		self.app_key = app_key
		self.app_id = app_id
		self.app_secret = app_secret
		self.redirect_uri = redirect_uri
		self.response_type = response_type
		self.username = username
		self.password = password

	def get_authorize_url(self):
		base_url = 'https://graph.renren.com/oauth/authorize?client_id=%s&redirect_uri=%s&response_type=code'
		return base_url % (self.app_key,urllib2.quote(self.redirect_uri))

	def get_code(self):
		httplib.HTTPConnection.debuglevel = 0
		opener = urllib2.build_opener(
				urllib2.HTTPRedirectHandler(),
				urllib2.HTTPHandler(),
				urllib2.HTTPSHandler(),
				urllib2.HTTPCookieProcessor(cookielib.CookieJar())
			)
		# step1: 打开登陆框，并且记录cookies
		open_login_form = opener.open(self.get_authorize_url())
		login_form_url = open_login_form.geturl()
		login_form_html = open_login_form.read()

		# print (login_form_html)
		

		# step2:获取所有表单数据
		login_form_data = {}
		soup = BeautifulSoup(login_form_html)
		inputs = soup.find_all('input')
		for input in inputs:
			login_form_data[input.get('name')] = input.get('value')

		login_form_data['username'] = self.username
		login_form_data['email'] = self.username
		login_form_data['password'] = self.password
		del login_form_data['']
		# print login_form_data

		# step3:提交表单
		try:
			# print urllib.urlencode(login_form_data)
			login_request_url = 'https://graph.renren.com/login'
			login_request = urllib2.Request(login_request_url,urllib.urlencode(login_form_data))
			response = opener.open(login_request)
			# print response.geturl()
			location = response.geturl()

			#step 3.1 判断是否已经授权过，如果授权过则直接获取code
			if 'code=' in location:
				return location[-32:]

			to_make_sure_html = response.read()

		#step4：如果未授权过，则在新的表单中提交授权确认
			to_make_sure_form = 'https://graph.renren.com/oauth/grant'
			to_make_sure_data = {}

			# print to_make_sure_html

			soup = BeautifulSoup(to_make_sure_html)
			inputs = soup.find_all('input')
			for input in inputs:
				to_make_sure_data[input.get('name')] = input.get('value')
			# print to_make_sure_data
			response = opener.open(to_make_sure_form,urllib.urlencode(to_make_sure_data),100)
			return response.geturl()[-32:]
		except Exception as e:
			print e
			return 'error:',e


	def get_access_token(self):
		token_url = 'https://graph.renren.com/oauth/token?'+ urllib.urlencode({
						'grant_type':'authorization_code',
						'client_id':self.app_key,
						'client_secret':self.app_secret,
						'code':self.get_code(),
						'redirect_uri':self.redirect_uri
					})
		response = urllib2.urlopen(token_url)
		return response.read()




















########NEW FILE########
__FILENAME__ = test
from renren import RenrenAuthAutomatic

api = RenrenAutoAuth('你的app Id','你的 app Key','你的app secret','你的app redirect uri','人人账号','人人密码')

print api.get_access_token()

########NEW FILE########
__FILENAME__ = tencentweibo
# -*- coding: utf8 -*-
import urllib
import urllib2,httplib
import cookielib
from bs4 import BeautifulSoup

class TencentWeiboAutoAuth(object):
	'''
	腾讯微博自动认证客户端
	曲线救国，从wap端下手更容易
	'''
	def __init__(self, app_key,	app_secret, redirect_uri, username,	password, response_type='code'):
		self.app_key = app_key
		self.app_secret = app_secret
		self.redirect_uri = redirect_uri
		self.response_type = response_type
		self.username = username
		self.password = password
		self.__get_code()

	def __get_authorize_url(self):
		base_url = 'https://open.t.qq.com/cgi-bin/oauth2/authorize?client_id=%s&response_type=code&redirect_uri=%s&wap=2'
		return base_url % (self.app_key,urllib2.quote(self.redirect_uri))

	def __get_code(self):
		opener = urllib2.build_opener(
				urllib2.HTTPRedirectHandler(),
				urllib2.HTTPHandler(),
				urllib2.HTTPSHandler(),
				urllib2.HTTPCookieProcessor(cookielib.CookieJar())
		)
		# step1: 打开登陆框，记录cookies
		open_login_form = opener.open(self.__get_authorize_url())
		login_form_url = open_login_form.geturl()
		login_form_html = open_login_form.read()

		# step2: 获取表单
		login_form_data = {}
		soup = BeautifulSoup(login_form_html)
		inputs = soup.find_all('input')
		for input in inputs:
			login_form_data[input.get('name')] = input.get('value')

		del login_form_data[None]
		print login_form_data

		login_form_data['u'] = self.username
		login_form_data['p'] = self.password

		# step3：提交数据
		request_url = 'https://open.t.qq.com/cgi-bin/oauth2/authorize'
		response = opener.open(request_url,urllib.urlencode(login_form_data))
		htmlcontent = response.read()
		code_start = htmlcontent.index('code=')
		openid_start = htmlcontent.index('openid=')
		openkey_start = htmlcontent.index('openkey=')
		
		self.code = htmlcontent[code_start+5:code_start+5+32]
		self.openid = htmlcontent[openid_start+7:openid_start+7+32]
		self.openkey = htmlcontent[openkey_start+8:openkey_start+8+32]
	
	def get_code(self):
		return self.code

	def get_access_token(self):
		request_url = 'https://open.t.qq.com/cgi-bin/oauth2/access_token?client_id=%s&client_secret=%s&redirect_uri=%s&grant_type=authorization_code&code=%s'
		request_url = request_url % (self.app_key,self.app_secret,urllib.quote(self.redirect_uri),self.code)
		response = urllib2.urlopen(request_url)
		print response.read()

	def get_openid(self):
		return self.openid

	def get_openkey(self):
		return self.openkey



########NEW FILE########
__FILENAME__ = test

from tencentweibo import TencentWeiboAutoAuth

api = TencentWeiboAutoAuth('app id','app_secret','app_redirect_uri','qq号','qq 密码')
print api.get_access_token()
print 'OpenId:',api.get_openid()
print 'OpenKey:',api.get_openkey()
########NEW FILE########
__FILENAME__ = test
# -*- coding: utf8 -*-
from weibo import WeiboAutoAuth

app_key = '3530915833' #请修改成您的app_key
app_secret = 'f34a9eb3404c7f99b5e8466e18ce9b6e' #请修改成您的app_secret
redirect_uri = 'http://snsapi.sinaapp.com/auth.php' #请修改成您的redirect_uri
username = '' #请修改成您的测试用户名
password = '' #请修改成您的测试微博密码

api = WeiboAutoAuth(app_key,app_secret,redirect_uri,username,password)

print api.get_access_token()
########NEW FILE########
__FILENAME__ = weibo
# -*- coding: utf8 -*-
import urllib
import urllib2
import cookielib
import requests
from bs4 import BeautifulSoup

class WeiboAutoAuth(object):
	'''
	新浪微博自动认证
	'''
	def __init__(self,app_key,app_secret,redirect_uri,username,password,response_type='code'):
		self.app_key = app_key
		self.app_secret = app_secret
		self.redirect_uri = redirect_uri
		self.response_type = response_type
		self.username = username
		self.password = password

	def __get_authorize_url(self):
		base_url = 'https://api.weibo.com/oauth2/authorize?client_id=%s&response_type=code&redirect_uri=%s'
		return base_url % (self.app_key,self.redirect_uri)

	def get_code(self):

		print self.__get_authorize_url()
		# step1: 打开登陆框，并且记录cookies

		open_login_form = requests.get(self.__get_authorize_url())
		open_login_form_html = open_login_form.text
		open_login_form_url = open_login_form.url

		soup = BeautifulSoup(open_login_form_html)
		inputs = soup.find_all('input')

		#step2:获取表单数据
		login_form_data = {}
		for input in inputs:
			value = input.get('value')
			login_form_data[input.get('name')] = unicode(value).encode('utf-8')
		
		login_form_data['userId'] = self.username
		login_form_data['passwd'] = self.password

		print login_form_data

		#step3:提交表单
		headers = {
			"User-Agent": "Mozilla/5.0 (Windows NT 6.1; rv:11.0) Gecko/20100101 Firefox/11.0",
			"Host": "api.weibo.com",
			"Referer":self.__get_authorize_url(),
			"Origin":"http://api.weibo.com"
		}

		auth_url = 'https://api.weibo.com/oauth2/authorize'
		response = requests.post(auth_url,data = login_form_data,headers=headers)
		url = response.url

		#如果已经认证过，则地址中包含code=，然后直接返回
		if('code=' in url):
			return url[-32:]

		content = response.text

		soup = BeautifulSoup(content)
		auth_data = {}
		inputs = soup.find_all('input')

		for input in inputs:
			value = input.get('value')
			auth_data[input.get('name')] = unicode(value).encode('utf-8')

		# print auth_data

		sure_url = 'https://api.weibo.com/2/oauth2/authorize'
		r =  requests.post(sure_url,data = auth_data, headers = headers)
		print r.url[-32:]
		return r.url[-32:]

	def get_access_token(self):
		postdata = {
			'redirect_uri':self.redirect_uri,
			'client_id':self.app_key,
			'grant_type':'authorization_code',
			'code':self.get_code(),
			'client_secret':self.app_secret
		}
		request_url = 'https://api.weibo.com/oauth2/access_token'

		r = requests.post(request_url,data=postdata)
		return r.text

########NEW FILE########
__FILENAME__ = index
# -*- coding: utf8 -*-
from flask import Flask,request,jsonify
import json

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir) 

from local.weibo import WeiboAutoAuth

app = Flask(__name__)

app.debug = True
@app.route('/weibo',methods=['POST'])
def weibo_auth():
	keys = {'app_key','app_secret','redirect_uri','username','password'}
	for key in keys:
		if(request.form.has_key(key) == False):
			return jsonify(
					error=True,
					msg='mission param:'+key
			)

	app_key = request.form['app_key']
	app_secret = request.form['app_secret']
	redirect_uri = request.form['redirect_uri']
	username = request.form['username']
	password = request.form['password']

	app = WeiboAutoAuth(app_key,app_secret,redirect_uri,username,password)
	d = json.loads(app.get_access_token())
	d['error'] = False
	return jsonify(d)

if __name__ == '__main__':
    app.run()
########NEW FILE########
__FILENAME__ = test
# coding=utf8
import urllib
import urllib2
import json

auth_url = "http://localhost:5000/weibo"

def auth(username,password,app_key,app_secret,redirect_uri):
	params = urllib.urlencode({'username':username,'password':password,'app_key':app_key,'app_secret':app_secret,'redirect_uri':redirect_uri})
	req = urllib2.Request(url=auth_url,data=params);
	f = urllib2.urlopen(req)
	json_str = f.read()
	print json_str
		
if __name__ == '__main__':
	app_key = '3530915833' #请修改成您的app_key
	app_secret = 'f34a9eb3404c7f99b5e8466e18ce9b6e' #请修改成您的app_secret
	redirect_uri = 'http://snsapi.sinaapp.com/auth.php' #请修改成您的redirect_uri
	username = '' #请修改成您的测试用户名
	password = '' #请修改成您的测试微博密码
	auth(username,password,app_key,app_secret,redirect_uri)
########NEW FILE########
