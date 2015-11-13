__FILENAME__ = auth
#!/usr/bin/python
#coding:utf-8
"""
  royguo1988@gmail.com
"""
import cookielib
import os
import tempfile
import urllib
import urllib2

class Course(object):
  def __init__(self, username, password, class_name):
    self.username = username
    self.password = password
    self.class_name = class_name

    # 发送登陆POST数据的接口
    self.auth_url = "https://www.coursera.org/maestro/api/user/login"
    self.csrf_token = ""
    self.session = ""
    self.cookie_file = ""

    # 开启课程验证信息
    self.open()

  def __get_class_url(self):
      """获得当前课程的首页URL"""
      return 'https://class.coursera.org/%s/lecture/index' % self.class_name

  def __set_csrf(self):
    """设置登陆页面的CSRF Token"""
    # 模拟cookie行为，主要用来获得cookie中的数据，并不真正存储在本地
    cookies = cookielib.LWPCookieJar()
    handlers = [
        urllib2.HTTPHandler(),
        urllib2.HTTPSHandler(),
        urllib2.HTTPCookieProcessor(cookies)
    ]
    opener = urllib2.build_opener(*handlers)
    req = urllib2.Request(self.__get_class_url())
    print 'Request for csrf token...'
    opener.open(req)
    for cookie in cookies:
        if cookie.name == 'csrf_token':
            self.csrf_token = cookie.value
            # break
    opener.close()

  def __auth(self):
    """登陆验证"""
    # 创建临时文件用来存储cookie数据
    hn, fn = tempfile.mkstemp()
    # 使用临时文件创建本地cookie
    cj = cookielib.MozillaCookieJar(fn)
    handlers = [
        urllib2.HTTPHandler(),
        urllib2.HTTPSHandler(),
        urllib2.HTTPCookieProcessor(cj)
    ]
    opener = urllib2.build_opener(*handlers)
    # 模拟浏览器，告诉登陆页面我们是从首页refer过来的
    std_headers = {
            'Cookie': ('csrftoken=%s' % self.csrf_token),
            'Referer': 'https://www.coursera.org',
            'X-CSRFToken': self.csrf_token,
            }
    auth_data = {
            'email_address': self.username,
            'password': self.password
            }
    # 把表单数据编码到form中, formatted_data中有数据会自动使用POST提交
    formatted_data = urllib.urlencode(auth_data)
    req = urllib2.Request(self.auth_url, formatted_data, std_headers)
    # 发送请求，请求结束后会自动把cookie数据存放到cookie jar中
    print 'Send login request...'
    opener.open(req)
    cj.save()
    opener.close()
    # 关闭临时文件
    os.close(hn)
    self.cookie_file = fn

  def __set_session(self):
    """获得课程session，下载的时候需要"""
    target = urllib.quote_plus(self.__get_class_url())
    auth_redirector_url = 'https://class.coursera.org/'+self.class_name+'/auth/auth_redirector?type=login&subtype=normal&email=&visiting='+target
    print 'redirect url : ',auth_redirector_url
    cj = cookielib.MozillaCookieJar()
    cj.load(self.cookie_file)

    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj),
                                  urllib2.HTTPHandler(),
                                  urllib2.HTTPSHandler())

    req = urllib2.Request(auth_redirector_url)
    print 'Request for session ... '
    opener.open(req)
    for cookie in cj:
        if cookie.name == 'session':
            self.session = cookie.value
            break
    opener.close()

  def open(self):
    """登陆某个课程首页，同时在本地存储cookie，需要预先enroll课程"""
    self.__set_csrf()
    print 'Get csrf token : ', self.csrf_token
    self.__auth()
    print 'Login in success, cookie file: ', self.cookie_file
    self.__set_session()
    print 'Get session : ', self.session

########NEW FILE########
__FILENAME__ = config-sample
#!/usr/bin/python

USER = {
    "username" : "your username here",
    "password" : "your password here"
}

########NEW FILE########
__FILENAME__ = downloader
#!/usr/bin/python
#coding:utf-8
"""
  royguo1988@gmail.com
"""
from auth import Course
import os
import re
import sys
import subprocess
import time

class Downloader(object):
  """下载器,登陆后使用"""
  def __init__(self, course, path):
    self.course = course
    self.path = path
    # {[id, name],[id, name]}
    self.links = []
    # 解析课程首页，获得链接信息
    self.parse_links()
    # 监控子进程的状态
    self.tasks = []

  def parse_links(self):
    html = 'lectures.html'
    # 下载课程首页，根据页面html抽取页面链接，应该有更好的方式实现...
    cmd = ['curl', 'https://class.coursera.org/' + self.course.class_name+'/lecture/index', 
           '-k', '-#','-L', '-o', html, 
           '--cookie', 'csrf_token=%s; session=%s' % (self.course.csrf_token, self.course.session)]
    subprocess.call(cmd)
    with open('lectures.html','r') as f:
      arr = re.findall(r'data-lecture-id="(\d+)"|class="lecture-link">\n(.*)</a>',f.read())
      i = 0
      while i < len(arr):
        lecture_id = arr[i][0]
        lecture_name = arr[i+1][1]
        self.links.append([lecture_id, lecture_name])
        i += 2
    print 'total lectures : ', len(self.links)
    os.remove(html)

  def download(self, url, target):
    if os.path.exists(target):
      print target,' already exist, continue...'
    else:
      print 'downloading : ', target
    # print 'url : ', url

    # -k : allow curl connect ssl websites without certifications.
    # -# : display progress bar.
    # -L : follow redirects.
    # -o : output file.
    # -s : slient mode, don't show anything
    # -C - : continue the downloading from last break point.
    # --cookie : String or file to read cookies from.
    cmd = ['curl', url, '-k','-s','-L','-C -', '-o', target, '--cookie',
           'csrf_token=%s; session=%s' % (self.course.csrf_token, self.course.session)]
    p = subprocess.Popen(cmd)
    self.tasks.append(p)

  def fetchAll(self):
    # count作为文件名的前缀遍历所有链接
    count = 1
    for link in self.links:
      # 下载字幕
      srt_url = "https://class.coursera.org/"+self.course.class_name+"/lecture/subtitles?q=%s_en&format=srt" %link[0]
      srt_name = self.path + str(count) + '.' +link[1]+'.srt'
      self.download(srt_url, srt_name)
      # 下载视频
      video_url = "https://class.coursera.org/"+self.course.class_name+"/lecture/download.mp4?lecture_id=%s" %link[0]
      video_name = self.path + str(count) + '.' +link[1]+'.mp4'
      self.download(video_url, video_name)

      count += 1

def main():
  if len(sys.argv) != 3:
    # class name example "neuralnets-2012-001"
    print 'usage : ./downloader.py download_dir class_name'
    return
  path = re.sub(r'/$','',sys.argv[1]) + "/"
  if not os.path.exists(path):
    os.makedirs(path)
  print 'download dir : ', path

  # 账号和课程信息
  from config import USER
  c = Course(USER['username'], USER['password'], sys.argv[2])
  d = Downloader(c, path)
  d.fetchAll()
  while True:
    print 'reminding tasks : ', len(d.tasks)
    for t in d.tasks:
      if t.poll() == 0:
        d.tasks.remove(t)
    time.sleep(1)

if __name__ == '__main__':
  try:
    main()
  except KeyboardInterrupt, e:
    print 'downloader has been killed !'
  

########NEW FILE########
