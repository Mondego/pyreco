__FILENAME__ = fusionyoudao
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from BeautifulSoup import BeautifulSoup
import os
import gl
import re
import popen2
def reconstruct(func):
    print "start fusionyoudao"
    soup = BeautifulSoup(open(gl.origindir))
    head=open(gl.headyoudao,'r')
    result = soup.find('div',{"id":"results"})
    #sousuo = soup.find('form',{"id":"f"})
    #sousuo  = str(sousuo).replace("action=\"/search\"","action=\"http://dict.youdao.com/search\"")
    #result  = str(result).replace("href=\"/example/","href=\"http://dict.youdao.com/example/")
    #os.system("echo "" > cache/result.html")
    f_tar=open(gl.resultdir,'w+')
    print >> f_tar,"<html>"
    print >> f_tar,head.read()
    print >> f_tar,"<body>"
    #print >> f_tar,"\n"
    #print >> f_tar,"<div class=\"c-header\">"
    #print >> f_tar,sousuo
    #print >> f_tar,"</div>"
    print >> f_tar,result
    print >> f_tar,"</body></html>"
    f_tar.close()
    head.close()
    os.system("sed -i -e 's/action=\"\/search/action=\"http:\/\/dict.youdao.com\/search/g' \'"+ gl.resultdir + "\'")
    os.system("sed -i -e 's/href=\"\/example/href=\"http:\/\/dict.youdao.com\/example/g' \'"+ gl.resultdir + "\'")
    os.system("sed -i -e 's/href=\"\/simplayer.swf/href=\"http:\/\/dict.youdao.com\/simplayer.swf/g' \'"+ gl.resultdir + "\'")
    #os.system("sed -i -e 's/href=\"\/simplayer.swf/href=\"http:\/\/dict.youdao.com\/simplayer.swf/g' \'"+ gl.resultdir + "\'")
    os.system("sed -i -e 's/<h3>目录<\/h3>/<h3>%index%<\/h3>/g' \'"+ gl.resultdir + "\'")
    os.system("sed -i -e 's/bilingual\">双语例句/bilingual\">%index%/g' \'"+ gl.resultdir + "\'")
    os.system("sed -i -e 's/详细内容//g' \'"+ gl.resultdir + "\'")
    os.system("sed -i -e 's/更多双语例句//g' \'"+ gl.resultdir + "\'")
    os.system("sed -i -e 's/更多原声例句//g' \'"+ gl.resultdir + "\'")
    os.system("sed -i -e 's/更多权威例句//g' \'"+ gl.resultdir + "\'")
    os.system("sed -i -e '/onmousedown/'d \'"+ gl.resultdir + "\'")
    os.system("sed -i -e '/百度百科/'d \'"+ gl.resultdir + "\'")
    if func=="lj":
        os.system("sed -i -e '/<li class=\"sub1_all sub-catalog-selected\">/'d \'"+ gl.resultdir + "\'")
        os.system("sed -i -e '/口语</'d \'"+ gl.resultdir + "\'")
        os.system("sed -i -e '/书面语</'d \'"+ gl.resultdir + "\'")
        os.system("sed -i -e '/论文</'d \'"+ gl.resultdir + "\'")
        os.system("sed -i -e '/原声例句</'d \'"+ gl.resultdir + "\'")
        os.system("sed -i -e '/全部</'d \'"+ gl.resultdir + "\'")
        os.system("sed -i -e '/音频例句</'d \'"+ gl.resultdir + "\'")
        os.system("sed -i -e '/视频例句</'d \'"+ gl.resultdir + "\'")
    os.system("sed -i -e 's/<li class=\"nav-collins\"><a href=\"http:\/\/dict.youdao.com\/writing\/?keyfrom=dictweb\" hidefocus=\"true\">英文写作助手<\/a><span class=\"collins-icon\"><\/span><\/li>//g' \'"+ gl.resultdir + "\'")
    #os.system("sed -i -e 's/http:\/\/dict.youdao.com\/writing\/?keyfrom=dictweb/file:\/\/\/usr\/share\/openyoudao\/config.html/g' \'"+ gl.resultdir + "\'")
    print "fusionyoudao completed"
    #os.system("sed -i -e 's/<\/div><\/div><\/div>/ /g' cache/result.html")

########NEW FILE########
__FILENAME__ = gl
#encoding=utf-8
import os
import sys
global pre_text
global cachedir
global homedir
global origindir
global resultdir
global homeurl
global headyoudao
global bodystartyoudao

pre_text=""
userdir=os.path.expanduser('~')
workdir = os.getcwd()
homedir = sys.path[0]
userdir=os.path.expanduser('~')
cachedir = userdir + "/.openyoudao"
origindir = userdir + "/.openyoudao/origin.html"
resultdir = userdir + "/.openyoudao/result.html"
headyoudao = "/usr/share/openyoudao/construction/youdao/head.html"
bodystartyoudao = "/usr/share/openyoudao/construction/youdao/body-start.txt"
homeurl = "file://" + "/usr/share/openyoudao/config.html"
helpurl = "file://" + "/usr/share/openyoudao/help.html"
baseurlyoudao="http://dict.youdao.com/search?q="
searchurl="http://dict.youdao.com/search?le=eng&q="
zh2en=searchurl
zh2jap="http://dict.youdao.com/search?le=jap&q="
zh2ko="http://dict.youdao.com/search?le=ko&q="
zh2fr="http://dict.youdao.com/search?le=fr&q="
zh2enlj="http://dict.youdao.com/search?le=eng&q=lj%3A"
zh2japlj="http://dict.youdao.com/search?le=jap&q=lj%3A"
zh2kolj="http://dict.youdao.com/search?le=ko&q=lj%3A"
zh2frlj="http://dict.youdao.com/search?le=fr&q=lj%3A"
func="default"

########NEW FILE########
__FILENAME__ = openyoudao
#!/usr/bin/python
#-*- coding: utf-8 -*-
# Simple demo for the RECORD extension
# Not very much unlike the xmacrorec2 program in the xmacro package.
import popen2
from time import sleep
import thread
import webshot
import sys
import fusionyoudao
import gl
import os
import webkit, gtk
# Change path so we find Xlib
sys.path.insert(1, os.path.join(sys.path[0], '..'))
from Xlib import X, XK, display
from Xlib.ext import record
from Xlib.protocol import rq
record_dpy = display.Display()

def record_callback(reply):
    if reply.category != record.FromServer:
        return
    if reply.client_swapped:
        print "* received swapped protocol data, cowardly ignored"
        return
    if not len(reply.data) or ord(reply.data[0]) < 2:
# not an event
        return
    data = reply.data
    while len(data):
        event, data = rq.EventField(None).parse_binary_value(data, record_dpy.display, None, None)

# deal with the event type
        if event.type == X.ButtonRelease:
            # get text
            global Alive
            pipe = os.popen("xclip -o")
            text = pipe.readline()
            pipe.readlines()    #清空管道剩余部分
            pipe.close()
            print "您选取的是: ", text
            text = text.strip('\r\n\x00').lower().strip()
            if(gl.pre_text != text and text!=""):
			         gl.pre_text = text
				 if(False==os.path.exists(gl.cachedir)):
				     os.system("mkdir  \'" + gl.cachedir + "\'")
				     os.system("touch  \'" + gl.origindir + "\'")
				     os.system("touch  \'" + gl.resultdir + "\'")
                                 if "%zh2enlj%" in text:
                                     gl.homeurl="file:///usr/share/openyoudao/zh2enlj.html"
                                     gl.searchurl=gl.zh2enlj
                                     url = ""
                                     gl.func="lj"
                                 elif "%zh2japlj%" in text:
                                     gl.homeurl="file:///usr/share/openyoudao/zh2japlj.html"
                                     gl.searchurl=gl.zh2japlj
                                     url = ""
                                     gl.func="lj"
                                 elif "%zh2kolj%" in text:
                                     gl.homeurl="file:///usr/share/openyoudao/zh2kolj.html"
                                     gl.searchurl=gl.zh2kolj
                                     url = ""
                                     gl.func="lj"
                                 elif "%zh2frlj%" in text:
                                     gl.homeurl="file:///usr/share/openyoudao/zh2frlj.html"
                                     gl.searchurl=gl.zh2frlj
                                     url = ""
                                     gl.func="lj"
                                 elif "%zh2en%" in text:
                                     gl.homeurl="file:///usr/share/openyoudao/zh2en.html"
                                     gl.searchurl=gl.zh2en
                                     url = ""
                                 elif "%zh2jap%" in text:
                                     gl.homeurl="file:///usr/share/openyoudao/zh2jap.html"
                                     gl.searchurl=gl.zh2jap
                                     url = ""
                                 elif "%zh2ko%" in text:
                                     gl.homeurl="file:///usr/share/openyoudao/zh2ko.html"
                                     gl.searchurl=gl.zh2ko
                                     url = ""
                                 elif "%zh2fr%" in text:
                                     gl.homeurl="file:///usr/share/openyoudao/zh2fr.html"
                                     gl.searchurl=gl.zh2fr
                                     url = ""
                                 elif "%index%" in text:
                                     gl.homeurl="file:///usr/share/openyoudao/config.html"
                                     url = ""
                                 elif "%helps%" in text:
                                     gl.homeurl="file:///usr/share/openyoudao/help.html"
                                     url = ""
                                 elif "%donate%" in text:
                                     gl.homeurl="file:///usr/share/openyoudao/donate.html"
                                     url = ""
                                 elif "%exits%" in text:
                                     Alive=0
                                 else:
			             url= gl.searchurl + text
                                 if url !="":
			             os.system("curl -s -w %{http_code}:%{time_connect}:%{time_starttransfer}:%{time_total}:%{speed_download} -o \'" + gl.origindir +"\' \'" + url+ "\'")       #获得网页(非代理)
			             fusionyoudao.reconstruct(gl.func)
			             gl.homeurl="file://" + gl.resultdir #合成最终缓冲访问地址
                                 if Alive==1:
			             window.load(gl.homeurl)
			             window.show()
if not record_dpy.has_extension("RECORD"):
  print "RECORD extension not found"
  sys.exit(1)
  r = record_dpy.record_get_version(0, 0)
  print "RECORD extension version %d.%d" % (r.major_version, r.minor_version)
# Create a recording context; we only want key and mouse events
ctx = record_dpy.record_create_context(
0,
[record.AllClients],
[{
'core_requests': (0, 0),
'core_replies': (0, 0),
'ext_requests': (0, 0, 0, 0),
'ext_replies': (0, 0, 0, 0),
'delivered_events': (0, 0),
'device_events': (X.KeyPress, X.MotionNotify),
'errors': (0, 0),
'client_started': False,
'client_died': False,
}])

def webshow():
  global window
  global Alive
  window = webshot.Window()
  window.load(gl.homeurl)
  window.show()
  gtk.main()
  record_dpy.record_free_context(ctx)
  os.system("ps aux | grep openyoudao.py |awk '{print $2}' |xargs kill -9 >/dev/null")
  Alive=0

def gettext():
  os.system("xclip -f /dev/null")           #清空剪切板
  record_dpy.record_enable_context(ctx,record_callback)
  record_dpy.record_free_context(ctx)
def lookup_keysym(keysym):
  for name in dir(XK):
    if name[:3] == "XK_" and getattr(XK, name) == keysym:
      return name[3:]
    return "[%d]" % keysym
def main():
  global Alive
  Alive=1
  thread.start_new_thread(webshow,())
  sleep(0.5)
  thread.start_new_thread(gettext,())
  while Alive:
	sleep(0.2)
        clip_id=os.popen("ps aux | grep xclip | grep -v grep |awk '{print $2}'| grep -v ^$ |wc -l")
        pid = clip_id.readline().strip('\r\n\x00')
        if int(pid)>=1:
            os.system("ps aux | grep xclip |awk '{print $2}' |xargs kill -9 >/dev/null")
if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = webshot
import sys
import gl
import os
import gtk
import time
import webkit

class OutputView(webkit.WebView):
    '''a class that represents the output widget of a conversation
    '''
    def __init__(self):
        webkit.WebView.__init__(self)
        self.load_finish_flag = False
        self.set_property('can-focus', True)
        self.set_property('can-default', True)
        self.set_full_content_zoom(1)
       # self.clipbord = gtk.Clipboard()
        #settings = self.get_settings()
        #try:
        #    settings.set_property('enable-universal-access-from-file-uris', True)
        #    settings.set_property('javascript-can-access-clipboard', False)
        #    settings.set_property('enable-default-context-menu', True)
        #    settings.set_property('enable-page-cache', True)
        #    settings.set_property('tab-key-cycles-through-elements', True)
        #    settings.set_property('enable-file-access-from-file-uris', True)
        #    settings.set_property('enable-spell-checking', False)
        #    settings.set_property('enable-caret-browsing', False)
        #    try:
        #         # Since 1.7.5
        #        settings.set_property('enable-accelerated-compositing', True)
        #    except TypeError:
        #         pass
        #except:
        #    print 'Error: settings property was not set.'


class Window(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)
        self.set_resizable(True)
        self.set_title("openyoudao")
        self.set_default_size(800, 240)
        self.set_icon_from_file("/usr/share/openyoudao/images/icon/icon.jpg")
        self.scroll = gtk.ScrolledWindow()
        self.scroll.props.hscrollbar_policy = gtk.POLICY_NEVER
        self.scroll.props.vscrollbar_policy = gtk.POLICY_NEVER
        self.output = OutputView()
        self.scroll.add(self.output)
        self.add(self.scroll)
        self.scroll.show_all()
        self.connect('delete-event', gtk.main_quit)
        #self.is_fullscreen = False
    def load(self, url):
        print url
        self.output.load_uri(url)
    def reload(self):
        self.output.reload()
        
#window = Window()
#window.load(sys.argv[1])
#window.load("http://dict.youdao.com/")
#window.show()
#gtk.main()

########NEW FILE########
