__FILENAME__ = ajaxterm
#!/usr/bin/env python

""" Ajaxterm """

import array,cgi,fcntl,glob,mimetypes,optparse,os,pty,random,re,signal,select,sys,threading,time,termios,struct,pwd

os.chdir(os.path.normpath(os.path.dirname(__file__)))
# Optional: Add QWeb in sys path
sys.path[0:0]=glob.glob('../../python')

import qweb

class Terminal:
	def __init__(self,width=80,height=24):
		self.width=width
		self.height=height
		self.init()
		self.reset()
	def init(self):
		self.esc_seq={
			"\x00": None,
			"\x05": self.esc_da,
			"\x07": None,
			"\x08": self.esc_0x08,
			"\x09": self.esc_0x09,
			"\x0a": self.esc_0x0a,
			"\x0b": self.esc_0x0a,
			"\x0c": self.esc_0x0a,
			"\x0d": self.esc_0x0d,
			"\x0e": None,
			"\x0f": None,
			"\x1b#8": None,
			"\x1b=": None,
			"\x1b>": None,
			"\x1b(0": None,
			"\x1b(A": None,
			"\x1b(B": None,
			"\x1b[c": self.esc_da,
			"\x1b[0c": self.esc_da,
			"\x1b]R": None,
			"\x1b7": self.esc_save,
			"\x1b8": self.esc_restore,
			"\x1bD": None,
			"\x1bE": None,
			"\x1bH": None,
			"\x1bM": self.esc_ri,
			"\x1bN": None,
			"\x1bO": None,
			"\x1bZ": self.esc_da,
			"\x1ba": None,
			"\x1bc": self.reset,
			"\x1bn": None,
			"\x1bo": None,
		}
		for k,v in self.esc_seq.items():
			if v==None:
				self.esc_seq[k]=self.esc_ignore
		# regex
		d={
			r'\[\??([0-9;]*)([@ABCDEFGHJKLMPXacdefghlmnqrstu`])' : self.csi_dispatch,
			r'\]([^\x07]+)\x07' : self.esc_ignore,
		}
		self.esc_re=[]
		for k,v in d.items():
			self.esc_re.append((re.compile('\x1b'+k),v))
		# define csi sequences
		self.csi_seq={
			'@': (self.csi_at,[1]),
			'`': (self.csi_G,[1]),
			'J': (self.csi_J,[0]),
			'K': (self.csi_K,[0]),
		}
		for i in [i[4] for i in dir(self) if i.startswith('csi_') and len(i)==5]:
			if not self.csi_seq.has_key(i):
				self.csi_seq[i]=(getattr(self,'csi_'+i),[1])
		# Init 0-256 to latin1 and html translation table
		self.trl1=""
		for i in range(256):
			if i<32:
				self.trl1+=" "
			elif i<127 or i>160:
				self.trl1+=chr(i)
			else:
				self.trl1+="?"
		self.trhtml=""
		for i in range(256):
			if i==0x0a or (i>32 and i<127) or i>160:
				self.trhtml+=chr(i)
			elif i<=32:
				self.trhtml+="\xa0"
			else:
				self.trhtml+="?"
	def reset(self,s=""):
		self.scr=array.array('i',[0x000700]*(self.width*self.height))
		self.st=0
		self.sb=self.height-1
		self.cx_bak=self.cx=0
		self.cy_bak=self.cy=0
		self.cl=0
		self.sgr=0x000700
		self.buf=""
		self.outbuf=""
		self.last_html=""
	def peek(self,y1,x1,y2,x2):
		return self.scr[self.width*y1+x1:self.width*y2+x2]
	def poke(self,y,x,s):
		pos=self.width*y+x
		self.scr[pos:pos+len(s)]=s
	def zero(self,y1,x1,y2,x2):
		w=self.width*(y2-y1)+x2-x1+1
		z=array.array('i',[0x000700]*w)
		self.scr[self.width*y1+x1:self.width*y2+x2+1]=z
	def scroll_up(self,y1,y2):
		self.poke(y1,0,self.peek(y1+1,0,y2,self.width))
		self.zero(y2,0,y2,self.width-1)
	def scroll_down(self,y1,y2):
		self.poke(y1+1,0,self.peek(y1,0,y2-1,self.width))
		self.zero(y1,0,y1,self.width-1)
	def scroll_right(self,y,x):
		self.poke(y,x+1,self.peek(y,x,y,self.width))
		self.zero(y,x,y,x)
	def cursor_down(self):
		if self.cy>=self.st and self.cy<=self.sb:
			self.cl=0
			q,r=divmod(self.cy+1,self.sb+1)
			if q:
				self.scroll_up(self.st,self.sb)
				self.cy=self.sb
			else:
				self.cy=r
	def cursor_right(self):
		q,r=divmod(self.cx+1,self.width)
		if q:
			self.cl=1
		else:
			self.cx=r
	def echo(self,c):
		if self.cl:
			self.cursor_down()
			self.cx=0
		self.scr[(self.cy*self.width)+self.cx]=self.sgr|ord(c)
		self.cursor_right()
	def esc_0x08(self,s):
		self.cx=max(0,self.cx-1)
	def esc_0x09(self,s):
		x=self.cx+8
		q,r=divmod(x,8)
		self.cx=(q*8)%self.width
	def esc_0x0a(self,s):
		self.cursor_down()
	def esc_0x0d(self,s):
		self.cl=0
		self.cx=0
	def esc_save(self,s):
		self.cx_bak=self.cx
		self.cy_bak=self.cy
	def esc_restore(self,s):
		self.cx=self.cx_bak
		self.cy=self.cy_bak
		self.cl=0
	def esc_da(self,s):
		self.outbuf="\x1b[?6c"
	def esc_ri(self,s):
		self.cy=max(self.st,self.cy-1)
		if self.cy==self.st:
			self.scroll_down(self.st,self.sb)
	def esc_ignore(self,*s):
		pass
#		print "term:ignore: %s"%repr(s)
	def csi_dispatch(self,seq,mo):
	# CSI sequences
		s=mo.group(1)
		c=mo.group(2)
		f=self.csi_seq.get(c,None)
		if f:
			try:
				l=[min(int(i),1024) for i in s.split(';') if len(i)<4]
			except ValueError:
				l=[]
			if len(l)==0:
				l=f[1]
			f[0](l)
#		else:
#			print 'csi ignore',c,l
	def csi_at(self,l):
		for i in range(l[0]):
			self.scroll_right(self.cy,self.cx)
	def csi_A(self,l):
		self.cy=max(self.st,self.cy-l[0])
	def csi_B(self,l):
		self.cy=min(self.sb,self.cy+l[0])
	def csi_C(self,l):
		self.cx=min(self.width-1,self.cx+l[0])
		self.cl=0
	def csi_D(self,l):
		self.cx=max(0,self.cx-l[0])
		self.cl=0
	def csi_E(self,l):
		self.csi_B(l)
		self.cx=0
		self.cl=0
	def csi_F(self,l):
		self.csi_A(l)
		self.cx=0
		self.cl=0
	def csi_G(self,l):
		self.cx=min(self.width,l[0])-1
	def csi_H(self,l):
		if len(l)<2: l=[1,1]
		self.cx=min(self.width,l[1])-1
		self.cy=min(self.height,l[0])-1
		self.cl=0
	def csi_J(self,l):
		if l[0]==0:
			self.zero(self.cy,self.cx,self.height-1,self.width-1)
		elif l[0]==1:
			self.zero(0,0,self.cy,self.cx)
		elif l[0]==2:
			self.zero(0,0,self.height-1,self.width-1)
	def csi_K(self,l):
		if l[0]==0:
			self.zero(self.cy,self.cx,self.cy,self.width-1)
		elif l[0]==1:
			self.zero(self.cy,0,self.cy,self.cx)
		elif l[0]==2:
			self.zero(self.cy,0,self.cy,self.width-1)
	def csi_L(self,l):
		for i in range(l[0]):
			if self.cy<self.sb:
				self.scroll_down(self.cy,self.sb)
	def csi_M(self,l):
		if self.cy>=self.st and self.cy<=self.sb:
			for i in range(l[0]):
				self.scroll_up(self.cy,self.sb)
	def csi_P(self,l):
		w,cx,cy=self.width,self.cx,self.cy
		end=self.peek(cy,cx,cy,w)
		self.csi_K([0])
		self.poke(cy,cx,end[l[0]:])
	def csi_X(self,l):
		self.zero(self.cy,self.cx,self.cy,self.cx+l[0])
	def csi_a(self,l):
		self.csi_C(l)
	def csi_c(self,l):
		#'\x1b[?0c' 0-8 cursor size
		pass
	def csi_d(self,l):
		self.cy=min(self.height,l[0])-1
	def csi_e(self,l):
		self.csi_B(l)
	def csi_f(self,l):
		self.csi_H(l)
	def csi_h(self,l):
		if l[0]==4:
			pass
#			print "insert on"
	def csi_l(self,l):
		if l[0]==4:
			pass
#			print "insert off"
	def csi_m(self,l):
		for i in l:
			if i==0 or i==39 or i==49 or i==27:
				self.sgr=0x000700
			elif i==1:
				self.sgr=(self.sgr|0x000800)
			elif i==7:
				self.sgr=0x070000
			elif i>=30 and i<=37:
				c=i-30
				self.sgr=(self.sgr&0xff08ff)|(c<<8)
			elif i>=40 and i<=47:
				c=i-40
				self.sgr=(self.sgr&0x00ffff)|(c<<16)
#			else:
#				print "CSI sgr ignore",l,i
#		print 'sgr: %r %x'%(l,self.sgr)
	def csi_r(self,l):
		if len(l)<2: l=[0,self.height]
		self.st=min(self.height-1,l[0]-1)
		self.sb=min(self.height-1,l[1]-1)
		self.sb=max(self.st,self.sb)
	def csi_s(self,l):
		self.esc_save(0)
	def csi_u(self,l):
		self.esc_restore(0)
	def escape(self):
		e=self.buf
		if len(e)>32:
#			print "error %r"%e
			self.buf=""
		elif e in self.esc_seq:
			self.esc_seq[e](e)
			self.buf=""
		else:
			for r,f in self.esc_re:
				mo=r.match(e)
				if mo:
					f(e,mo)
					self.buf=""
					break
#		if self.buf=='': print "ESC %r\n"%e
	def write(self,s):
		for i in s:
			if len(self.buf) or (i in self.esc_seq):
				self.buf+=i
				self.escape()
			elif i == '\x1b':
				self.buf+=i
			else:
				self.echo(i)
	def read(self):
		b=self.outbuf
		self.outbuf=""
		return b
	def dump(self):
		r=''
		for i in self.scr:
			r+=chr(i&255)
		return r
	def dumplatin1(self):
		return self.dump().translate(self.trl1)
	def dumphtml(self,color=1):
		h=self.height
		w=self.width
		r=""
		span=""
		span_bg,span_fg=-1,-1
		for i in range(h*w):
			q,c=divmod(self.scr[i],256)
			if color:
				bg,fg=divmod(q,256)
			else:
				bg,fg=0,7
			if i==self.cy*w+self.cx:
				bg,fg=1,7
			if (bg!=span_bg or fg!=span_fg or i==h*w-1):
				if len(span):
					r+='<span class="f%d b%d">%s</span>'%(span_fg,span_bg,cgi.escape(span.translate(self.trhtml)))
				span=""
				span_bg,span_fg=bg,fg
			span+=chr(c)
			if i%w==w-1:
				span+='\n'
		r='<?xml version="1.0" encoding="ISO-8859-1"?><pre class="term">%s</pre>'%r
		if self.last_html==r:
			return '<?xml version="1.0"?><idem></idem>'
		else:
			self.last_html=r
#			print self
			return r
	def __repr__(self):
		d=self.dumplatin1()
		r=""
		for i in range(self.height):
			r+="|%s|\n"%d[self.width*i:self.width*(i+1)]
		return r

class SynchronizedMethod:
	def __init__(self,lock,orig):
		self.lock=lock
		self.orig=orig
	def __call__(self,*l):
		self.lock.acquire()
		r=self.orig(*l)
		self.lock.release()
		return r

class Multiplex:
	def __init__(self,cmd=None):
		signal.signal(signal.SIGCHLD, signal.SIG_IGN)
		self.cmd=cmd
		self.proc={}
		self.lock=threading.RLock()
		self.thread=threading.Thread(target=self.loop)
		self.alive=1
		# synchronize methods
		for name in ['create','fds','proc_read','proc_write','dump','die','run']:
			orig=getattr(self,name)
			setattr(self,name,SynchronizedMethod(self.lock,orig))
		self.thread.start()
	def create(self,w=80,h=25):
		pid,fd=pty.fork()
		if pid==0:
			try:
				fdl=[int(i) for i in os.listdir('/proc/self/fd')]
			except OSError:
				fdl=range(256)
			for i in [i for i in fdl if i>2]:
				try:
					os.close(i)
				except OSError:
					pass
			if self.cmd:
				cmd=['/bin/sh','-c',self.cmd]
			elif os.getuid()==0:
				cmd=['/bin/login']
			else:
				sys.stdout.write("Login: ")
				login=sys.stdin.readline().strip()
				if re.match('^[0-9A-Za-z-_. ]+$',login):
					cmd=['ssh']
					cmd+=['-oPreferredAuthentications=keyboard-interactive,password']
					cmd+=['-oNoHostAuthenticationForLocalhost=yes']
					cmd+=['-oLogLevel=FATAL']
					cmd+=['-F/dev/null','-l',login,'localhost']
				else:
					os._exit(0)
			env={}
			env["COLUMNS"]=str(w)
			env["LINES"]=str(h)
			env["TERM"]="linux"
			env["PATH"]=os.environ['PATH']
			os.execvpe(cmd[0],cmd,env)
		else:
			fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK)
			# python bug http://python.org/sf/1112949 on amd64
			fcntl.ioctl(fd, struct.unpack('i',struct.pack('I',termios.TIOCSWINSZ))[0], struct.pack("HHHH",h,w,0,0))
			self.proc[fd]={'pid':pid,'term':Terminal(w,h),'buf':'','time':time.time()}
			return fd
	def die(self):
		self.alive=0
	def run(self):
		return self.alive
	def fds(self):
		return self.proc.keys()
	def proc_kill(self,fd):
		if fd in self.proc:
			self.proc[fd]['time']=0
		t=time.time()
		for i in self.proc.keys():
			t0=self.proc[i]['time']
			if (t-t0)>120:
				try:
					os.close(i)
					os.kill(self.proc[i]['pid'],signal.SIGTERM)
				except (IOError,OSError):
					pass
				del self.proc[i]
	def proc_read(self,fd):
		try:
			t=self.proc[fd]['term']
			t.write(os.read(fd,65536))
			reply=t.read()
			if reply:
				os.write(fd,reply)
			self.proc[fd]['time']=time.time()
		except (KeyError,IOError,OSError):
			self.proc_kill(fd)
	def proc_write(self,fd,s):
		try:
			os.write(fd,s)
		except (IOError,OSError):
			self.proc_kill(fd)
	def dump(self,fd,color=1):
		try:
			return self.proc[fd]['term'].dumphtml(color)
		except KeyError:
			return False
	def loop(self):
		while self.run():
			fds=self.fds()
			i,o,e=select.select(fds, [], [], 1.0)
			for fd in i:
				self.proc_read(fd)
			if len(i):
				time.sleep(0.002)
		for i in self.proc.keys():
			try:
				os.close(i)
				os.kill(self.proc[i]['pid'],signal.SIGTERM)
			except (IOError,OSError):
				pass

class AjaxTerm:
	def __init__(self,cmd=None,index_file='ajaxterm.html'):
		self.files={}
		for i in ['css','html','js']:
			for j in glob.glob('*.%s'%i):
				self.files[j]=file(j).read()
		self.files['index']=file(index_file).read()
		self.mime = mimetypes.types_map.copy()
		self.mime['.html']= 'text/html; charset=UTF-8'
		self.multi = Multiplex(cmd)
		self.session = {}
	def __call__(self, environ, start_response):
		req = qweb.QWebRequest(environ, start_response,session=None)
		if req.PATH_INFO.endswith('/u'):
			s=req.REQUEST["s"]
			k=req.REQUEST["k"]
			c=req.REQUEST["c"]
			w=req.REQUEST.int("w")
			h=req.REQUEST.int("h")
			if s in self.session:
				term=self.session[s]
			else:
				if not (w>2 and w<256 and h>2 and h<100):
					w,h=80,25
				term=self.session[s]=self.multi.create(w,h)
			if k:
				self.multi.proc_write(term,k)
			time.sleep(0.002)
			dump=self.multi.dump(term,c)
			req.response_headers['Content-Type']='text/xml'
			if isinstance(dump,str):
				req.write(dump)
				req.response_gzencode=1
			else:
				del self.session[s]
				req.write('<?xml version="1.0"?><idem></idem>')
#			print "sessions %r"%self.session
		else:
			n=os.path.basename(req.PATH_INFO)
			if n in self.files:
				req.response_headers['Content-Type'] = self.mime.get(os.path.splitext(n)[1].lower(), 'application/octet-stream')
				req.write(self.files[n])
			else:
				req.response_headers['Content-Type'] = 'text/html; charset=UTF-8'
				req.write(self.files['index'])
		return req

def main():
	parser = optparse.OptionParser()
	parser.add_option("-p", "--port", dest="port", default="8022", help="Set the TCP port (default: 8022)")
	parser.add_option("-c", "--command", dest="cmd", default=None,help="set the command (default: /bin/login or ssh localhost)")
	parser.add_option("-l", "--log", action="store_true", dest="log",default=0,help="log requests to stderr (default: quiet mode)")
	parser.add_option("-d", "--daemon", action="store_true", dest="daemon", default=0, help="run as daemon in the background")
	parser.add_option("-P", "--pidfile",dest="pidfile",default="/var/run/ajaxterm.pid",help="set the pidfile (default: /var/run/ajaxterm.pid)")
	parser.add_option("-i", "--index", dest="index_file", default="ajaxterm.html",help="default index file (default: ajaxterm.html)")
	parser.add_option("-u", "--uid", dest="uid", help="Set the daemon's user id")
	(o, a) = parser.parse_args()
	if o.daemon:
		pid=os.fork()
		if pid == 0:
			#os.setsid() ?
			os.setpgrp()
			nullin = file('/dev/null', 'r')
			nullout = file('/dev/null', 'w')
			os.dup2(nullin.fileno(), sys.stdin.fileno())
			os.dup2(nullout.fileno(), sys.stdout.fileno())
			os.dup2(nullout.fileno(), sys.stderr.fileno())
			if os.getuid()==0 and o.uid:
				try:
					os.setuid(int(o.uid))
				except:
					os.setuid(pwd.getpwnam(o.uid).pw_uid)
		else:
			try:
				file(o.pidfile,'w+').write(str(pid)+'\n')
			except:
				pass
			print 'AjaxTerm at http://localhost:%s/ pid: %d' % (o.port,pid)
			sys.exit(0)
	else:
		print 'AjaxTerm at http://localhost:%s/' % o.port
	at=AjaxTerm(o.cmd,o.index_file)
#	f=lambda:os.system('firefox http://localhost:%s/&'%o.port)
#	qweb.qweb_wsgi_autorun(at,ip='localhost',port=int(o.port),threaded=0,log=o.log,callback_ready=None)
	try:
		qweb.QWebWSGIServer(at,ip='localhost',port=int(o.port),threaded=0,log=o.log).serve_forever()
	except KeyboardInterrupt,e:
		sys.excepthook(*sys.exc_info())
	at.multi.die()

if __name__ == '__main__':
	main()


########NEW FILE########
__FILENAME__ = demo_wsgi3_testapp
#/usr/bin/python

def testapp(environ, start_response):
	start_response('200 OK',[('Content-type','text/plain')])
	php=environ['php']

	if 'PHP_AUTH_USER' not in php._SERVER:
		php.header('WWW-Authenticate: Basic realm="My Realm"')
		php.header('HTTP/1.0 401 Unauthorized')
		print 'Text to send if user hits Cancel button';
		php.exit()
	else:
		print "<p>Hello '%s'.</p>"%(php._SERVER['PHP_AUTH_USER'],)
		print "<p>You entered '%s' as your password.</p>"%(php._SERVER['PHP_AUTH_PW'])

	return ['done\n']


########NEW FILE########
__FILENAME__ = Makedoc
#!/usr/bin/python
import os,cgi


s="""
<!-- EXAMPLE -->

"""
l=[i for i in os.listdir(".") if i.startswith("demo")]
l.sort()
for i in l:
	s+="""
	Example : %s<br>

	<pre style="padding: 10px 10px 10px 3em; background-color: #f0f0f0;border: 1px solid #dddddd;">%s</pre>
	<br>
	<br>
	"""%(i,cgi.escape(file(i).read()))

s+= """ </div> </div> """


ff=file("README.html").read()
v=ff.find("<!-- EXAMPLE")
tmp=ff[:v]
file("README.html","w").write( tmp+s)


########NEW FILE########
__FILENAME__ = pyphp
#!/usr/bin/python
"""PyPHP, python - PHP bridge

Type Mapping

Python <=> PHP
str <=> string
unicode => string
int <=> integer
long <=> integer
float <=> double
list <=> array
tuple => array
dict <=> array
object => array
PHPObject <=> object

"""

__version__ = "$Id$"
__license__ = "Public Domain"
__author__ = "Antony Lesuisse"

import StringIO,os,re,signal,socket,struct,sys,types,urllib
#----------------------------------------------------------
# Serialization
#----------------------------------------------------------

class PHPObject:
	def __init__(self,name,attr={}):
		self.__doc__=name
		for i in attr:
			self.__dict__[i]=attr[i]

def serialize(v):
	t = type(v)
	if t == types.IntType or t == types.LongType:
		return 'i:%d;'%v
	elif t == types.FloatType:
		return 'd:'+str(v)+';'
	elif t is types.BooleanType:
		if v:
			return 'b:1;'
		else:
			return 'b:0;'
	elif t == types.NoneType:
		return 'N;'
	elif t == types.StringType:
		return 's:%d:"%s";'%(len(v),v)
	elif t == types.UnicodeType:
		v=v.encode("utf8")
		return 's:%d:"%s";'%(len(v),v)
	elif t == types.TupleType or t == types.ListType:
		i=0
		s=''
		for item in v:
			s+='i:%d;%s'%(i,serialize(item))
			i+=1
		return 'a:%d:{%s}'%(len(v),s)
	elif t == types.DictType:
		s=''
		for k in v:
			s+=serialize(k)+serialize(v[k])
		return 'a:%d:{%s}'%(len(v),s)
	elif isinstance(v,PHPObject):
		name=v.__doc__
		s='O:%d:"%s":%d:{'%(len(name),name,len(v.__dict__)-1)
		for k in v.__dict__:
			if k!='__doc__':
				s+=serialize(k)+serialize(v.__dict__[k])
		return s+'}'
	elif t == types.InstanceType:
		return serialize(v.__dict__)
	else:
		return 'N;'

def unserialize(l):
	if isinstance(l,str):
		l=re.split(';',l)
	a=l.pop(0)
	if a[0]=="i":
		return int(a[2:])
	elif a[0]=="d":
		return float(a[2:])
	elif a[0]=="b":
		return bool(int(a[2:]))
	elif a[0]=="N":
		return None
	elif a[0]=="s":
		h=a.split(":",2)
		size=int(h[1])
		val=h[2][1:]
		while len(val)<=size:
			val+=";"+l.pop(0)
		return val[0:-1]
	elif a[0]=="a":
		h=a.split(":",2)
		size=int(h[1])
		val=h[2][1:]
		l.insert(0,val)
		r={}
#		pure=1
		k_prev=-1
		for i in xrange(size):
			k=unserialize(l)
			v=unserialize(l)
			r[k]=v
#			pure=pure and isinstance(k,int) and k==k_prev+1
			k_prev=k
		l[0]=l[0][1:]
#		if pure:
#			return [r[i] for i in range(len(r))]
		return r
	elif a[0]=="O":
		h=a.split(":",3)
		name=h[2][1:-1]
		l.insert(0,"a:"+h[3])
		return PHPObject(name,unserialize(l))

#----------------------------------------------------------
# Python bindings
#----------------------------------------------------------

class PHPStdout:
	def __init__(self,proxy):
		self.proxy=proxy
	def write(self,data):
		self.proxy.pyphp_write(data)

class PHPFunction:
	def __init__(self,proxy,name):
		self.proxy=proxy
		self.name=name
	def __call__(self, *param):
		return self.proxy.pyphp_call(self.name,param)

class PHPSession:
	def __init__(self,proxy,dic={}):
		self.proxy=proxy
		if isinstance(dic,dict):
			self.dic=dic
		else:
			self.dic={}
	def __getitem__(self,key):
		return self.dic[key]
	def __setitem__(self,key,val):
		self.dic[key]=val
		self.proxy.pyphp_call('pyphp_session_add',(key,val))
	def __contains__(self,item):
		return item in self.dic
	def __len__(self):
		return len(self.dic)
	def __iter__(self):
		return self.dic.__iter__()

class PHPDict(dict):
	def __init__(self,*p):
		dict.__init__(self,*p)
	def __getitem__(self,key):
		return self.get(key,"")
	def int(self,key):
		try:
			return int(self.get(key,"0"))
		except ValueError:
			return 0

class PHPProxy:
	def __init__(self,sock):
		self._sock=sock
		self.pyphp_init()

	def __str__(self):
		return "PHPProxy"

	def __getattr__(self, name):
		return PHPFunction(self,name)

	def __repr__(self):
		return "<PHPProxy instance>"

	def __nonzero__(self):
		return 1

	def pyphp_msg_dec(self):
		msg=self._sock.recv(5)
		if msg[0]!="S":
			raise "py: protocol error"
		size=struct.unpack("i",msg[1:5])[0]
		serial=self._sock.recv(size)
		return unserialize(serial)

	def pyphp_send(self, msg):
		size=len(msg)
		sent=self._sock.send(msg)
		while sent<size:
			sent+=self._sock.send(msg[sent:])

	def pyphp_call(self,func,param):
		data="%s\x00%s"%(func,serialize(param))
		msg="C%s%s"%(struct.pack("i",len(data)),data)
		self.pyphp_send(msg)
		return self.pyphp_msg_dec();

	def pyphp_init(self):
		tmp=self.pyphp_call('pyphp_request',())
		stdout=PHPStdout(self)
		sys.stdout=stdout
		sys.stderr=stdout
		self._OUT=stdout
		self._SERVER=tmp["_SERVER"]
		self._ENV=tmp["_ENV"]
		self._GET=tmp["_GET"]
		self._POST=tmp["_POST"]
		self._ARG=PHPDict(self._GET)
		self._ARG.update(self._POST)
		self._COOKIE=tmp["_COOKIE"]
		self._REQUEST=tmp["_REQUEST"]
		self._FILES=tmp["_FILES"]
		self._SESSION=PHPSession(self,tmp["_SESSION"])
		self._SCRIPT_FILENAME=self._SERVER["SCRIPT_FILENAME"]

	def pyphp_write(self, data):
		msg="W%s%s"%(struct.pack("i",len(data)),data)
		self.pyphp_send(msg)

	def pyphp_echo(self, *param):
		data=""
		for i in param:
			data+=str(i)
		self.pyphp_write(data)

	def pyphp_wsgi_start_response(self,code,headlist):
#		if not code.startswith("200"):
		self.header("HTTP/1.1 %s"%code)
		for (n,v) in headlist:
			self.header("%s: %s"%(n,v))

	def echo(self, *param):
		self.pyphp_echo(*param)
	def eval(self, data):
		return self.pyphp_call('pyphp_eval',(data))
	def exit(self):
		self.pyphp_send("E\x00\x00\x00\x00")

def skipphp(f):
	while 1:
		li=f.readline()
		if li.find("?>")!=-1 or len(li)==0:
			break

def wsgicall(php,wsgiobj):
	environ=php._SERVER.copy()
	post=urllib.urlencode(php._POST.items())
	input=StringIO.StringIO(post)
	scheme="http"
	if environ.has_key("HTTPS"):
		scheme="https"
	environ.update({
		"wsgi.version":(1,0),
		"wsgi.url_scheme":scheme,
		"wsgi.input":input,
		"wsgi.errors":StringIO.StringIO(),
		"wsgi.multithread":0,
		"wsgi.multiprocess":1,
		"wsgi.run_once":1,
		"php":php,
	})
	for i in wsgiobj(environ,php.pyphp_wsgi_start_response):
		php.pyphp_write(i)

def log(s):
	pass
#	sys.stdout.write("pyphp:%d: %s"%(os.getpid(),s))
#	sys.stdout.flush()

def main():
	try:
		fd=[int(i) for i in os.listdir('/proc/self/fd')]
	except OSError:
		fd=range(256)
	for i in fd:
		try:
			os.close(i)
		except OSError:
			pass
	sys.stdout=sys.stderr=file("/dev/null","a")
#	sys.stdout=sys.stderr=file("/tmp/pyphp.log","a")
	os.chdir(os.path.normpath(os.path.dirname(__file__)))
	sname=sys.argv[1]
	log("NEW server socket %s \n"%sname)
	sl=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
	try:
		os.unlink(sname)
	except OSError,e:
		log("unlink: "+str(e)+"\n")
	sl.bind(sname)
	sl.listen(10)
	signal.signal(signal.SIGCHLD,signal.SIG_IGN)
	if os.fork():
		sys.exit()
	else:
		os.setsid()
		#----------------------------------------------------------
		# WSGI Mode get the wsgiapp object
		#----------------------------------------------------------
		wsgi_file=sys.argv[2]
		wsgi_app=sys.argv[3]
		wsgi_obj=None
		if len(wsgi_file):
			log("WSGI init, running '%s' to get the wsgi application '%s' \n"%(wsgi_file,wsgi_app))
			f=file(wsgi_file)
			skipphp(f)
			d={}
			exec f in d
			if d.has_key(wsgi_app):
				wsgi_obj=d[wsgi_app]
				log("WSGI wsgi application '%s' ready.\n"%wsgi_app)
		#----------------------------------------------------------
		num=0
		while 1:
			log("accept request %d\n"%num)
			sl.settimeout(30.0)
			try:
				(s,addr)=sl.accept()
			except socket.timeout,e:
				log("suicide after 30sec idle.\n")
				sys.exit()
			log("serving request %d\n"%num)
			if os.fork():
				num+=1
				s.close()
				continue
			else:
				sl.close()
				signal.signal(signal.SIGALRM,lambda x,y: sys.exit())
				signal.alarm(30)
				php=PHPProxy(s)
				scope={'php':php}
				#
				#
				if wsgi_obj:
					wsgicall(php,wsgi_obj)
				else:
					f=file(php._SCRIPT_FILENAME)
					skipphp(f)
					try:
						exec f in scope
					except:
						print "<xmp>"
						sys.excepthook(*sys.exc_info())
				#
				#
				php.exit()
				sys.exit()

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = blog
#!/usr/bin/python2.3
# vim:set noet foldlevel=0:

import StringIO,cPickle,csv,datetime,email.Header,email.MIMEText,glob,os,quopri,random,re,sets,shutil,socket,sys,time,zipfile

sys.path.extend(glob.glob('lib/*.egg')+glob.glob('QWeb-*-py%d.%d.egg'%sys.version_info[:2])+glob.glob('../../python'))

import sqlobject as so
import qweb

#---------------------------------------------------------
# Sqlobject init
#---------------------------------------------------------
so.sqlhub.processConnection = so.connectionForURI('sqlite:'+os.path.realpath('database.db')+'?debug=False')
so.sqlhub.processConnection = so.connectionForURI('sqlite:'+os.path.realpath('database.db'))

#---------------------------------------------------------
# Databases
#---------------------------------------------------------
class post(so.SQLObject):
	ctime = so.DateTimeCol(notNone=1,default=so.DateTimeCol.now)
	title = so.StringCol(length=128, notNone=1,default='')
	body = so.StringCol(notNone=1,default='')
	comments = so.MultipleJoin('comment')

class comment(so.SQLObject):
	post = so.ForeignKey('post', notNone=1)
	ctime = so.DateTimeCol(notNone=1,default=so.DateTimeCol.now)
	name = so.StringCol(length=128, notNone=1,default='')
	email = so.StringCol(length=128, notNone=1,default='')
	title = so.StringCol(length=128, notNone=1,default='')
	body = so.StringCol(notNone=1,default='')

def so2dict(row):
	d={}
	for n in row.sqlmeta.columns:
		d[n]=str(getattr(row,n))
	return d

def initdb():
	for i in [post,comment]:
		i.dropTable(ifExists=True)
		i.createTable()
	for i in range(10):
		p=post(title='Post %d'%(i+1),body=("Body of %d, "%(i+1))*10)
		for j in range(3):
			comment(post=p,title='comment %d on post %d'%(j+1,i+1),name='John Doe%d'%(j+1),email='john.doe%d@example.com'%(j+1))

#---------------------------------------------------------
# Web interface
#---------------------------------------------------------
class BlogApp:
	# Called once per fcgi process, or only once for commandline
	def __init__(self):
		self.t = qweb.QWebHtml("template.xml")

	# Called for each request
	def __call__(self, environ, start_response):
		req = qweb.QWebRequest(environ, start_response)

		if req.PATH_INFO=="/":
			page='blog_home'
		else:
			page="blog"+req.PATH_INFO

		mo=re.search('blog/post_view/([0-9]+)',page)
		if mo:
			page='blog/post_view'
			req.REQUEST['post']=mo.group(1)

		if not qweb.qweb_control(self,page,[req,req.REQUEST,{}]):
			req.http_404()

		return req

	def blog(self, req, arg, v):
		v['url']=qweb.QWebURL("/",req.PATH_INFO)

	def blog_home(self, req, arg, v):
		v['posts'] = post.select(orderBy="-id")[:5]
		req.write(self.t.render("home", v))

	def blog_postlist(self, req, arg, v):
		v["posts"] = post.select(orderBy='-id')
		req.write(self.t.render("postlist", v))

	def blog_postadd(self, req, arg, v):
		v["post"] = post()
		return "blog_post_edit"

	# Ensure that all blog_post_* handlers have a valid 'post' argument
	def blog_post(self, req, arg, v):
		if not "post" in v:
			try:
				v['post'] = post.get(arg.int('post'))
			except Exception,e:
				req.write(str(e))
				return 'error'

	def blog_post_view(self, req, arg, v):
		req.write(self.t.render("post_view", v))

	def blog_post_edit(self, req, arg, v):
		f=v["form"]=self.t.form("post_edit",arg,so2dict(v["post"]))
		if f.valid:
			v["post"].set(**f.collect())
		req.write(self.t.render("post_edit", v))

	def blog_post_commentadd(self, req, arg, v):
		v["comment"] = comment(post=v['post'])
		return "blog_comment_edit"

	# Ensure that all blog_comment_* handlers have a valid 'comment' argument
	def blog_comment(self, req, arg, v):
		if not "comment" in v:
			v['comment'] = comment.get(arg.int('comment'))
			v['post']=v['comment'].post

	def blog_comment_edit(self, req, arg, v):
		f=v["form"]=self.t.form("comment_edit",arg,so2dict(v["comment"]))
		if f.valid:
			v["comment"].set(**f.collect())
			return "blog_post_view"
		req.write(self.t.render("comment_edit", v))


if __name__=='__main__':
	initdb()
	b=BlogApp()
	qweb.qweb_wsgi_autorun(b,threaded=0)


########NEW FILE########
__FILENAME__ = dbadmin
#!/usr/bin/python
# vim:set mouse=:
import glob, os, sys, re

#sys.path[0:0] = glob.glob('lib/QWeb-0.5-py%d.%d.egg'%sys.version_info[:2])+glob.glob('lib/')

import qweb, qweb_static

class DBATable:
	def __init__(self,cols):
		self.cols=cols
		self.hidden=0

class DBACol:
	def __init__(self):
		self.name=None
		self.type=None
		self.hidden=0
		# many2one
		self.dest=None


class DBAdmin:
	def __init__(self,urlroot,mod):
		self.urlroot = urlroot
		self.mod = mod
		self.template = qweb.QWebHtml(qweb_static.get_module_data('qweb_dbadmin','dbadmin.xml'))

		self.tables={}
		self.preprocess(mod)

	def preprocess(self,mod):
		for name in dir(mod):
			cls=getattr(mod,name)
			if hasattr(cls, '__mro__'):
				for basecls in cls.__mro__:
					if basecls.__name__=='SQLObject':
						self.pretable(mod, cls)
						self.tables[name]=cls
						break

	# dbview_* attributes
	# dbview_cols cols ordered
	# dbview_cols[0].longname
	# dbview_cols[0].type
	def pretable(self,mod,table):
		if not hasattr(table,'dba'):
			table.dba=DBATable([])
			tmp=[(col.creationOrder, col) for col in table.sqlmeta.columns.values() if col.name!='childName' if not getattr(col, 'hidden', False)]
			tmp.sort()
			for order, col in tmp:
				col.dba=DBACol()
				col.dba.name=col.name
				col.dba.nullable=not col.notNone
				col.dba.sqltype=col._sqliteType()
				if col.foreignKey:
					col.dba.longname=getattr(col, 'longname', col.name[:-2].replace('_',' '))
					col.dba.type="many2one"
					col.dba.name=col.name[:-2]
					col.dba.dest=getattr(mod, col.foreignKey)
					col.dba.form="select"
				else:
					col.dba.longname=getattr(col, 'longname', col.name.replace('_',' '))
					col.dba.type="scalar"
				table.dba.cols.append(col)
			table.dba.count=table.select().count()

	def process(self, req):
		path=req.PATH_INFO[len(self.urlroot):]
		if path=="":
			path="index"
		v={}
		if qweb.qweb_control(self, "dbview_" + path, [req,req.REQUEST,req,v]):
			r={}
			r['head']=self.template.render("head",v)
			r['body']=v.get('body','')
			return r
		else:
			req.http_404()
			return None

	def dbview(self,req,arg,out,v):
		req.response_headers['Content-type'] = 'text/html; charset=UTF-8'
		v['url'] = qweb.QWebURL(self.urlroot, req.PATH_INFO)

	def dbview_index(self,req,arg,out,v):
		v["tables"]=self.tables
		v["body"]=self.template.render("dbview_index",v)

	def dbview_table(self,req,arg,out,v):
		if self.tables.has_key(arg["table"]):
			v["table"]=arg["table"]
			v["tableo"]=self.tables[arg["table"]]
		else:
			return "error"

	def dbview_table_list(self,req,arg,out,v):
		v["start"]=arg.int("start")
		v["search"]=arg["search"]
		v["step"]=arg.int("step")
		v["order"]=arg.get("order","id")
		if v["step"]==0:
			v["step"]=50
		res=v["tableo"].select(orderBy=v["order"])
		v["total"]=res.count()
		v["rows"]=res[v["start"]:v["start"]+v["step"]]

		v["body"]=self.template.render("dbview_table_list",v)

	def rowform(self,arg,form,table,row=None,prefix="__"):
		print 'rowform %r'%table
		# denial.consigneeID
		for c in table.dba.cols:
			ca=c.dba
			fn=prefix + ca.name
			# ---------------------------------------------
			# Recurse
			# ---------------------------------------------
			if ca.type=="many2one":
				sub=fn+'__'
				if sub in arg and arg[sub] != 'Cancel':
					fi=qweb.QWebField(sub, default='1')
					form.add_field(fi)
					self.rowform(arg,form,ca.dest,row=None,prefix=sub)
			# ---------------------------------------------
			# Default
			# ---------------------------------------------
			default=""
			if row:
				default=str(getattr(row,ca.name))
				if ca.type=="many2one":
					default=str(getattr(row,ca.name+'ID'))
			elif c.default:
				# TODO
				default=str(c.default)
			# ---------------------------------------------
			# Null
			# ---------------------------------------------
			if c.dba.nullable:
				check=None
			elif c.dba.sqltype=='DATE':
				check="date"
			else:
				check="/.+/"
			# ---------------------------------------------
			# Add
			# ---------------------------------------------
			fi=qweb.QWebField(prefix+c.dba.name,default=default,check=check)
			form.add_field(fi)
		return form

	def rowadd(self,form,table,row=None,prefix="__"):
#		v["row"]=v["tableo"](**d)
		pass

	def rowsave(self,form,table,row=None,prefix="__"):
#		v["row"].set(**d)
#		resurce to rowadd
		pass

	def dbview_table_rowadd(self,req,arg,out,v):
		f=v["form"]=qweb.QWebForm()
		self.rowform(arg,f,v["tableo"])
		f.process_input(arg)
		v['pf']='__'
		if arg["save"] and f.valid:
			print "VALID"
			d=f.collect()
			self.rowsave()
			arg.clear()
			return "dbview_table_row_edit"
		else:
			v["body"]=self.template.render("dbview_table_rowadd",v)

	def dbview_table_row(self,req,arg,out,v):
		if not v.has_key("row"):
			res=v["tableo"].select(v["tableo"].q.id==arg["id"])
			if res.count():
				v["row"]=res[0]
			else:
				return "error"

	# ajouter inline
	def dbview_table_row_edit(self,req,arg,out,v):
		f=v["form"]=qweb.QWebForm()
		self.rowform(arg,f,v["tableo"],v["row"])
		f.process_input(arg)
		v['pf']='__'
		if arg["save"] and f.valid:
			print "VALID"
			d=f.collect()
			self.rowsave()
			print d
			v["saved"]=1
			v["body"]=self.template.render("dbview_table_row_edit",v)
		else:
			v["body"]=self.template.render("dbview_table_row_edit",v)

	def dbview_table_row_del(self,req,arg,out,v):
		v["row"]
		v["body"]="ok"

if __name__ == '__main__':
	pass



########NEW FILE########
__FILENAME__ = fcgi
#!/usr/bin/python
# Copyright (c) 2002, 2003, 2005 Allan Saddi <allan@saddi.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# $Id$

"""
fcgi - a FastCGI/WSGI gateway.

For more information about FastCGI, see <http://www.fastcgi.com/>.

For more information about the Web Server Gateway Interface, see
<http://www.python.org/peps/pep-0333.html>.

Example usage:

  #!/usr/bin/env python
  from myapplication import app # Assume app is your WSGI application object
  from fcgi import WSGIServer
  WSGIServer(app).run()

See the documentation for WSGIServer/Server for more information.

On most platforms, fcgi will fallback to regular CGI behavior if run in a
non-FastCGI context. If you want to force CGI behavior, set the environment
variable FCGI_FORCE_CGI to "Y" or "y".
"""

__author__ = 'Allan Saddi <allan@saddi.com>'
__version__ = '$Revision$'

import sys
import os
import signal
import struct
import cStringIO as StringIO
import select
import socket
import errno
import traceback

try:
    import thread
    import threading
    thread_available = True
except ImportError:
    import dummy_thread as thread
    import dummy_threading as threading
    thread_available = False

# Apparently 2.3 doesn't define SHUT_WR? Assume it is 1 in this case.
if not hasattr(socket, 'SHUT_WR'):
    socket.SHUT_WR = 1

__all__ = ['WSGIServer']

# Constants from the spec.
FCGI_LISTENSOCK_FILENO = 0

FCGI_HEADER_LEN = 8

FCGI_VERSION_1 = 1

FCGI_BEGIN_REQUEST = 1
FCGI_ABORT_REQUEST = 2
FCGI_END_REQUEST = 3
FCGI_PARAMS = 4
FCGI_STDIN = 5
FCGI_STDOUT = 6
FCGI_STDERR = 7
FCGI_DATA = 8
FCGI_GET_VALUES = 9
FCGI_GET_VALUES_RESULT = 10
FCGI_UNKNOWN_TYPE = 11
FCGI_MAXTYPE = FCGI_UNKNOWN_TYPE

FCGI_NULL_REQUEST_ID = 0

FCGI_KEEP_CONN = 1

FCGI_RESPONDER = 1
FCGI_AUTHORIZER = 2
FCGI_FILTER = 3

FCGI_REQUEST_COMPLETE = 0
FCGI_CANT_MPX_CONN = 1
FCGI_OVERLOADED = 2
FCGI_UNKNOWN_ROLE = 3

FCGI_MAX_CONNS = 'FCGI_MAX_CONNS'
FCGI_MAX_REQS = 'FCGI_MAX_REQS'
FCGI_MPXS_CONNS = 'FCGI_MPXS_CONNS'

FCGI_Header = '!BBHHBx'
FCGI_BeginRequestBody = '!HB5x'
FCGI_EndRequestBody = '!LB3x'
FCGI_UnknownTypeBody = '!B7x'

FCGI_EndRequestBody_LEN = struct.calcsize(FCGI_EndRequestBody)
FCGI_UnknownTypeBody_LEN = struct.calcsize(FCGI_UnknownTypeBody)

if __debug__:
    import time

    # Set non-zero to write debug output to a file.
    DEBUG = 0
    DEBUGLOG = '/tmp/fcgi.log'

    def _debug(level, msg):
        if DEBUG < level:
            return

        try:
            f = open(DEBUGLOG, 'a')
            f.write('%sfcgi: %s\n' % (time.ctime()[4:-4], msg))
            f.close()
        except:
            pass

class InputStream(object):
    """
    File-like object representing FastCGI input streams (FCGI_STDIN and
    FCGI_DATA). Supports the minimum methods required by WSGI spec.
    """
    def __init__(self, conn):
        self._conn = conn

        # See Server.
        self._shrinkThreshold = conn.server.inputStreamShrinkThreshold

        self._buf = ''
        self._bufList = []
        self._pos = 0 # Current read position.
        self._avail = 0 # Number of bytes currently available.

        self._eof = False # True when server has sent EOF notification.

    def _shrinkBuffer(self):
        """Gets rid of already read data (since we can't rewind)."""
        if self._pos >= self._shrinkThreshold:
            self._buf = self._buf[self._pos:]
            self._avail -= self._pos
            self._pos = 0

            assert self._avail >= 0

    def _waitForData(self):
        """Waits for more data to become available."""
        self._conn.process_input()

    def read(self, n=-1):
        if self._pos == self._avail and self._eof:
            return ''
        while True:
            if n < 0 or (self._avail - self._pos) < n:
                # Not enough data available.
                if self._eof:
                    # And there's no more coming.
                    newPos = self._avail
                    break
                else:
                    # Wait for more data.
                    self._waitForData()
                    continue
            else:
                newPos = self._pos + n
                break
        # Merge buffer list, if necessary.
        if self._bufList:
            self._buf += ''.join(self._bufList)
            self._bufList = []
        r = self._buf[self._pos:newPos]
        self._pos = newPos
        self._shrinkBuffer()
        return r

    def readline(self, length=None):
        if self._pos == self._avail and self._eof:
            return ''
        while True:
            # Unfortunately, we need to merge the buffer list early.
            if self._bufList:
                self._buf += ''.join(self._bufList)
                self._bufList = []
            # Find newline.
            i = self._buf.find('\n', self._pos)
            if i < 0:
                # Not found?
                if self._eof:
                    # No more data coming.
                    newPos = self._avail
                    break
                else:
                    # Wait for more to come.
                    self._waitForData()
                    continue
            else:
                newPos = i + 1
                break
        if length is not None:
            if self._pos + length < newPos:
                newPos = self._pos + length
        r = self._buf[self._pos:newPos]
        self._pos = newPos
        self._shrinkBuffer()
        return r

    def readlines(self, sizehint=0):
        total = 0
        lines = []
        line = self.readline()
        while line:
            lines.append(line)
            total += len(line)
            if 0 < sizehint <= total:
                break
            line = self.readline()
        return lines

    def __iter__(self):
        return self

    def next(self):
        r = self.readline()
        if not r:
            raise StopIteration
        return r

    def add_data(self, data):
        if not data:
            self._eof = True
        else:
            self._bufList.append(data)
            self._avail += len(data)

class MultiplexedInputStream(InputStream):
    """
    A version of InputStream meant to be used with MultiplexedConnections.
    Assumes the MultiplexedConnection (the producer) and the Request
    (the consumer) are running in different threads.
    """
    def __init__(self, conn):
        super(MultiplexedInputStream, self).__init__(conn)

        # Arbitrates access to this InputStream (it's used simultaneously
        # by a Request and its owning Connection object).
        lock = threading.RLock()

        # Notifies Request thread that there is new data available.
        self._lock = threading.Condition(lock)

    def _waitForData(self):
        # Wait for notification from add_data().
        self._lock.wait()

    def read(self, n=-1):
        self._lock.acquire()
        try:
            return super(MultiplexedInputStream, self).read(n)
        finally:
            self._lock.release()

    def readline(self, length=None):
        self._lock.acquire()
        try:
            return super(MultiplexedInputStream, self).readline(length)
        finally:
            self._lock.release()

    def add_data(self, data):
        self._lock.acquire()
        try:
            super(MultiplexedInputStream, self).add_data(data)
            self._lock.notify()
        finally:
            self._lock.release()

class OutputStream(object):
    """
    FastCGI output stream (FCGI_STDOUT/FCGI_STDERR). By default, calls to
    write() or writelines() immediately result in Records being sent back
    to the server. Buffering should be done in a higher level!
    """
    def __init__(self, conn, req, type, buffered=False):
        self._conn = conn
        self._req = req
        self._type = type
        self._buffered = buffered
        self._bufList = [] # Used if buffered is True
        self.dataWritten = False
        self.closed = False

    def _write(self, data):
        length = len(data)
        while length:
            toWrite = min(length, self._req.server.maxwrite - FCGI_HEADER_LEN)

            rec = Record(self._type, self._req.requestId)
            rec.contentLength = toWrite
            rec.contentData = data[:toWrite]
            self._conn.writeRecord(rec)

            data = data[toWrite:]
            length -= toWrite

    def write(self, data):
        assert not self.closed

        if not data:
            return

        self.dataWritten = True

        if self._buffered:
            self._bufList.append(data)
        else:
            self._write(data)

    def writelines(self, lines):
        assert not self.closed

        for line in lines:
            self.write(line)

    def flush(self):
        # Only need to flush if this OutputStream is actually buffered.
        if self._buffered:
            data = ''.join(self._bufList)
            self._bufList = []
            self._write(data)

    # Though available, the following should NOT be called by WSGI apps.
    def close(self):
        """Sends end-of-stream notification, if necessary."""
        if not self.closed and self.dataWritten:
            self.flush()
            rec = Record(self._type, self._req.requestId)
            self._conn.writeRecord(rec)
            self.closed = True

class TeeOutputStream(object):
    """
    Simple wrapper around two or more output file-like objects that copies
    written data to all streams.
    """
    def __init__(self, streamList):
        self._streamList = streamList

    def write(self, data):
        for f in self._streamList:
            f.write(data)

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def flush(self):
        for f in self._streamList:
            f.flush()

class StdoutWrapper(object):
    """
    Wrapper for sys.stdout so we know if data has actually been written.
    """
    def __init__(self, stdout):
        self._file = stdout
        self.dataWritten = False

    def write(self, data):
        if data:
            self.dataWritten = True
        self._file.write(data)

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def __getattr__(self, name):
        return getattr(self._file, name)

def decode_pair(s, pos=0):
    """
    Decodes a name/value pair.

    The number of bytes decoded as well as the name/value pair
    are returned.
    """
    nameLength = ord(s[pos])
    if nameLength & 128:
        nameLength = struct.unpack('!L', s[pos:pos+4])[0] & 0x7fffffff
        pos += 4
    else:
        pos += 1

    valueLength = ord(s[pos])
    if valueLength & 128:
        valueLength = struct.unpack('!L', s[pos:pos+4])[0] & 0x7fffffff
        pos += 4
    else:
        pos += 1

    name = s[pos:pos+nameLength]
    pos += nameLength
    value = s[pos:pos+valueLength]
    pos += valueLength

    return (pos, (name, value))

def encode_pair(name, value):
    """
    Encodes a name/value pair.

    The encoded string is returned.
    """
    nameLength = len(name)
    if nameLength < 128:
        s = chr(nameLength)
    else:
        s = struct.pack('!L', nameLength | 0x80000000L)

    valueLength = len(value)
    if valueLength < 128:
        s += chr(valueLength)
    else:
        s += struct.pack('!L', valueLength | 0x80000000L)

    return s + name + value
    
class Record(object):
    """
    A FastCGI Record.

    Used for encoding/decoding records.
    """
    def __init__(self, type=FCGI_UNKNOWN_TYPE, requestId=FCGI_NULL_REQUEST_ID):
        self.version = FCGI_VERSION_1
        self.type = type
        self.requestId = requestId
        self.contentLength = 0
        self.paddingLength = 0
        self.contentData = ''

    def _recvall(sock, length):
        """
        Attempts to receive length bytes from a socket, blocking if necessary.
        (Socket may be blocking or non-blocking.)
        """
        dataList = []
        recvLen = 0
        while length:
            try:
                data = sock.recv(length)
            except socket.error, e:
                if e[0] == errno.EAGAIN:
                    select.select([sock], [], [])
                    continue
                else:
                    raise
            if not data: # EOF
                break
            dataList.append(data)
            dataLen = len(data)
            recvLen += dataLen
            length -= dataLen
        return ''.join(dataList), recvLen
    _recvall = staticmethod(_recvall)

    def read(self, sock):
        """Read and decode a Record from a socket."""
        try:
            header, length = self._recvall(sock, FCGI_HEADER_LEN)
        except:
            raise EOFError

        if length < FCGI_HEADER_LEN:
            raise EOFError
        
        self.version, self.type, self.requestId, self.contentLength, \
                      self.paddingLength = struct.unpack(FCGI_Header, header)

        if __debug__: _debug(9, 'read: fd = %d, type = %d, requestId = %d, '
                             'contentLength = %d' %
                             (sock.fileno(), self.type, self.requestId,
                              self.contentLength))
        
        if self.contentLength:
            try:
                self.contentData, length = self._recvall(sock,
                                                         self.contentLength)
            except:
                raise EOFError

            if length < self.contentLength:
                raise EOFError

        if self.paddingLength:
            try:
                self._recvall(sock, self.paddingLength)
            except:
                raise EOFError

    def _sendall(sock, data):
        """
        Writes data to a socket and does not return until all the data is sent.
        """
        length = len(data)
        while length:
            try:
                sent = sock.send(data)
            except socket.error, e:
                if e[0] == errno.EPIPE:
                    return # Don't bother raising an exception. Just ignore.
                elif e[0] == errno.EAGAIN:
                    select.select([], [sock], [])
                    continue
                else:
                    raise
            data = data[sent:]
            length -= sent
    _sendall = staticmethod(_sendall)

    def write(self, sock):
        """Encode and write a Record to a socket."""
        self.paddingLength = -self.contentLength & 7

        if __debug__: _debug(9, 'write: fd = %d, type = %d, requestId = %d, '
                             'contentLength = %d' %
                             (sock.fileno(), self.type, self.requestId,
                              self.contentLength))

        header = struct.pack(FCGI_Header, self.version, self.type,
                             self.requestId, self.contentLength,
                             self.paddingLength)
        self._sendall(sock, header)
        if self.contentLength:
            self._sendall(sock, self.contentData)
        if self.paddingLength:
            self._sendall(sock, '\x00'*self.paddingLength)
            
class Request(object):
    """
    Represents a single FastCGI request.

    These objects are passed to your handler and is the main interface
    between your handler and the fcgi module. The methods should not
    be called by your handler. However, server, params, stdin, stdout,
    stderr, and data are free for your handler's use.
    """
    def __init__(self, conn, inputStreamClass):
        self._conn = conn

        self.server = conn.server
        self.params = {}
        self.stdin = inputStreamClass(conn)
        self.stdout = OutputStream(conn, self, FCGI_STDOUT)
        self.stderr = OutputStream(conn, self, FCGI_STDERR, buffered=True)
        self.data = inputStreamClass(conn)

    def run(self):
        """Runs the handler, flushes the streams, and ends the request."""
        try:
            protocolStatus, appStatus = self.server.handler(self)
        except:
            traceback.print_exc(file=self.stderr)
            self.stderr.flush()
            if not self.stdout.dataWritten:
                self.server.error(self)

            protocolStatus, appStatus = FCGI_REQUEST_COMPLETE, 0

        if __debug__: _debug(1, 'protocolStatus = %d, appStatus = %d' %
                             (protocolStatus, appStatus))

        self._flush()
        self._end(appStatus, protocolStatus)

    def _end(self, appStatus=0L, protocolStatus=FCGI_REQUEST_COMPLETE):
        self._conn.end_request(self, appStatus, protocolStatus)
        
    def _flush(self):
        self.stdout.close()
        self.stderr.close()

class CGIRequest(Request):
    """A normal CGI request disguised as a FastCGI request."""
    def __init__(self, server):
        # These are normally filled in by Connection.
        self.requestId = 1
        self.role = FCGI_RESPONDER
        self.flags = 0
        self.aborted = False
        
        self.server = server
        self.params = dict(os.environ)
        self.stdin = sys.stdin
        self.stdout = StdoutWrapper(sys.stdout) # Oh, the humanity!
        self.stderr = sys.stderr
        self.data = StringIO.StringIO()
        
    def _end(self, appStatus=0L, protocolStatus=FCGI_REQUEST_COMPLETE):
        sys.exit(appStatus)

    def _flush(self):
        # Not buffered, do nothing.
        pass

class Connection(object):
    """
    A Connection with the web server.

    Each Connection is associated with a single socket (which is
    connected to the web server) and is responsible for handling all
    the FastCGI message processing for that socket.
    """
    _multiplexed = False
    _inputStreamClass = InputStream

    def __init__(self, sock, addr, server):
        self._sock = sock
        self._addr = addr
        self.server = server

        # Active Requests for this Connection, mapped by request ID.
        self._requests = {}

    def _cleanupSocket(self):
        """Close the Connection's socket."""
        try:
            self._sock.shutdown(socket.SHUT_WR)
        except:
            return
        try:
            while True:
                r, w, e = select.select([self._sock], [], [])
                if not r or not self._sock.recv(1024):
                    break
        except:
            pass
        self._sock.close()
        
    def run(self):
        """Begin processing data from the socket."""
        self._keepGoing = True
        while self._keepGoing:
            try:
                self.process_input()
            except EOFError:
                break
            except (select.error, socket.error), e:
                if e[0] == errno.EBADF: # Socket was closed by Request.
                    break
                raise

        self._cleanupSocket()

    def process_input(self):
        """Attempt to read a single Record from the socket and process it."""
        # Currently, any children Request threads notify this Connection
        # that it is no longer needed by closing the Connection's socket.
        # We need to put a timeout on select, otherwise we might get
        # stuck in it indefinitely... (I don't like this solution.)
        while self._keepGoing:
            try:
                r, w, e = select.select([self._sock], [], [], 1.0)
            except ValueError:
                # Sigh. ValueError gets thrown sometimes when passing select
                # a closed socket.
                raise EOFError
            if r: break
        if not self._keepGoing:
            return
        rec = Record()
        rec.read(self._sock)

        if rec.type == FCGI_GET_VALUES:
            self._do_get_values(rec)
        elif rec.type == FCGI_BEGIN_REQUEST:
            self._do_begin_request(rec)
        elif rec.type == FCGI_ABORT_REQUEST:
            self._do_abort_request(rec)
        elif rec.type == FCGI_PARAMS:
            self._do_params(rec)
        elif rec.type == FCGI_STDIN:
            self._do_stdin(rec)
        elif rec.type == FCGI_DATA:
            self._do_data(rec)
        elif rec.requestId == FCGI_NULL_REQUEST_ID:
            self._do_unknown_type(rec)
        else:
            # Need to complain about this.
            pass

    def writeRecord(self, rec):
        """
        Write a Record to the socket.
        """
        rec.write(self._sock)

    def end_request(self, req, appStatus=0L,
                    protocolStatus=FCGI_REQUEST_COMPLETE, remove=True):
        """
        End a Request.

        Called by Request objects. An FCGI_END_REQUEST Record is
        sent to the web server. If the web server no longer requires
        the connection, the socket is closed, thereby ending this
        Connection (run() returns).
        """
        rec = Record(FCGI_END_REQUEST, req.requestId)
        rec.contentData = struct.pack(FCGI_EndRequestBody, appStatus,
                                      protocolStatus)
        rec.contentLength = FCGI_EndRequestBody_LEN
        self.writeRecord(rec)

        if remove:
            del self._requests[req.requestId]

        if __debug__: _debug(2, 'end_request: flags = %d' % req.flags)

        if not (req.flags & FCGI_KEEP_CONN) and not self._requests:
            self._cleanupSocket()
            self._keepGoing = False

    def _do_get_values(self, inrec):
        """Handle an FCGI_GET_VALUES request from the web server."""
        outrec = Record(FCGI_GET_VALUES_RESULT)

        pos = 0
        while pos < inrec.contentLength:
            pos, (name, value) = decode_pair(inrec.contentData, pos)
            cap = self.server.capability.get(name)
            if cap is not None:
                outrec.contentData += encode_pair(name, str(cap))

        outrec.contentLength = len(outrec.contentData)
        self.writeRecord(outrec)

    def _do_begin_request(self, inrec):
        """Handle an FCGI_BEGIN_REQUEST from the web server."""
        role, flags = struct.unpack(FCGI_BeginRequestBody, inrec.contentData)

        req = self.server.request_class(self, self._inputStreamClass)
        req.requestId, req.role, req.flags = inrec.requestId, role, flags
        req.aborted = False

        if not self._multiplexed and self._requests:
            # Can't multiplex requests.
            self.end_request(req, 0L, FCGI_CANT_MPX_CONN, remove=False)
        else:
            self._requests[inrec.requestId] = req

    def _do_abort_request(self, inrec):
        """
        Handle an FCGI_ABORT_REQUEST from the web server.

        We just mark a flag in the associated Request.
        """
        req = self._requests.get(inrec.requestId)
        if req is not None:
            req.aborted = True

    def _start_request(self, req):
        """Run the request."""
        # Not multiplexed, so run it inline.
        req.run()

    def _do_params(self, inrec):
        """
        Handle an FCGI_PARAMS Record.

        If the last FCGI_PARAMS Record is received, start the request.
        """
        req = self._requests.get(inrec.requestId)
        if req is not None:
            if inrec.contentLength:
                pos = 0
                while pos < inrec.contentLength:
                    pos, (name, value) = decode_pair(inrec.contentData, pos)
                    req.params[name] = value
            else:
                self._start_request(req)

    def _do_stdin(self, inrec):
        """Handle the FCGI_STDIN stream."""
        req = self._requests.get(inrec.requestId)
        if req is not None:
            req.stdin.add_data(inrec.contentData)

    def _do_data(self, inrec):
        """Handle the FCGI_DATA stream."""
        req = self._requests.get(inrec.requestId)
        if req is not None:
            req.data.add_data(inrec.contentData)

    def _do_unknown_type(self, inrec):
        """Handle an unknown request type. Respond accordingly."""
        outrec = Record(FCGI_UNKNOWN_TYPE)
        outrec.contentData = struct.pack(FCGI_UnknownTypeBody, inrec.type)
        outrec.contentLength = FCGI_UnknownTypeBody_LEN
        self.writeRecord(rec)
        
class MultiplexedConnection(Connection):
    """
    A version of Connection capable of handling multiple requests
    simultaneously.
    """
    _multiplexed = True
    _inputStreamClass = MultiplexedInputStream

    def __init__(self, sock, addr, server):
        super(MultiplexedConnection, self).__init__(sock, addr, server)

        # Used to arbitrate access to self._requests.
        lock = threading.RLock()

        # Notification is posted everytime a request completes, allowing us
        # to quit cleanly.
        self._lock = threading.Condition(lock)

    def _cleanupSocket(self):
        # Wait for any outstanding requests before closing the socket.
        self._lock.acquire()
        while self._requests:
            self._lock.wait()
        self._lock.release()

        super(MultiplexedConnection, self)._cleanupSocket()
        
    def writeRecord(self, rec):
        # Must use locking to prevent intermingling of Records from different
        # threads.
        self._lock.acquire()
        try:
            # Probably faster than calling super. ;)
            rec.write(self._sock)
        finally:
            self._lock.release()

    def end_request(self, req, appStatus=0L,
                    protocolStatus=FCGI_REQUEST_COMPLETE, remove=True):
        self._lock.acquire()
        try:
            super(MultiplexedConnection, self).end_request(req, appStatus,
                                                           protocolStatus,
                                                           remove)
            self._lock.notify()
        finally:
            self._lock.release()

    def _do_begin_request(self, inrec):
        self._lock.acquire()
        try:
            super(MultiplexedConnection, self)._do_begin_request(inrec)
        finally:
            self._lock.release()

    def _do_abort_request(self, inrec):
        self._lock.acquire()
        try:
            super(MultiplexedConnection, self)._do_abort_request(inrec)
        finally:
            self._lock.release()

    def _start_request(self, req):
        thread.start_new_thread(req.run, ())

    def _do_params(self, inrec):
        self._lock.acquire()
        try:
            super(MultiplexedConnection, self)._do_params(inrec)
        finally:
            self._lock.release()

    def _do_stdin(self, inrec):
        self._lock.acquire()
        try:
            super(MultiplexedConnection, self)._do_stdin(inrec)
        finally:
            self._lock.release()

    def _do_data(self, inrec):
        self._lock.acquire()
        try:
            super(MultiplexedConnection, self)._do_data(inrec)
        finally:
            self._lock.release()
        
class Server(object):
    """
    The FastCGI server.

    Waits for connections from the web server, processing each
    request.

    If run in a normal CGI context, it will instead instantiate a
    CGIRequest and run the handler through there.
    """
    request_class = Request
    cgirequest_class = CGIRequest

    # Limits the size of the InputStream's string buffer to this size + the
    # server's maximum Record size. Since the InputStream is not seekable,
    # we throw away already-read data once this certain amount has been read.
    inputStreamShrinkThreshold = 102400 - 8192

    def __init__(self, handler=None, maxwrite=8192, bindAddress=None,
                 multiplexed=False):
        """
        handler, if present, must reference a function or method that
        takes one argument: a Request object. If handler is not
        specified at creation time, Server *must* be subclassed.
        (The handler method below is abstract.)

        maxwrite is the maximum number of bytes (per Record) to write
        to the server. I've noticed mod_fastcgi has a relatively small
        receive buffer (8K or so).

        bindAddress, if present, must either be a string or a 2-tuple. If
        present, run() will open its own listening socket. You would use
        this if you wanted to run your application as an 'external' FastCGI
        app. (i.e. the webserver would no longer be responsible for starting
        your app) If a string, it will be interpreted as a filename and a UNIX
        socket will be opened. If a tuple, the first element, a string,
        is the interface name/IP to bind to, and the second element (an int)
        is the port number.

        Set multiplexed to True if you want to handle multiple requests
        per connection. Some FastCGI backends (namely mod_fastcgi) don't
        multiplex requests at all, so by default this is off (which saves
        on thread creation/locking overhead). If threads aren't available,
        this keyword is ignored; it's not possible to multiplex requests
        at all.
        """
        if handler is not None:
            self.handler = handler
        self.maxwrite = maxwrite
        if thread_available:
            try:
                import resource
                # Attempt to glean the maximum number of connections
                # from the OS.
                maxConns = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
            except ImportError:
                maxConns = 100 # Just some made up number.
            maxReqs = maxConns
            if multiplexed:
                self._connectionClass = MultiplexedConnection
                maxReqs *= 5 # Another made up number.
            else:
                self._connectionClass = Connection
            self.capability = {
                FCGI_MAX_CONNS: maxConns,
                FCGI_MAX_REQS: maxReqs,
                FCGI_MPXS_CONNS: multiplexed and 1 or 0
                }
        else:
            self._connectionClass = Connection
            self.capability = {
                # If threads aren't available, these are pretty much correct.
                FCGI_MAX_CONNS: 1,
                FCGI_MAX_REQS: 1,
                FCGI_MPXS_CONNS: 0
                }
        self._bindAddress = bindAddress

    def _setupSocket(self):
        if self._bindAddress is None: # Run as a normal FastCGI?
            isFCGI = True

            sock = socket.fromfd(FCGI_LISTENSOCK_FILENO, socket.AF_INET,
                                 socket.SOCK_STREAM)
            try:
                sock.getpeername()
            except socket.error, e:
                if e[0] == errno.ENOTSOCK:
                    # Not a socket, assume CGI context.
                    isFCGI = False
                elif e[0] != errno.ENOTCONN:
                    raise

            # FastCGI/CGI discrimination is broken on Mac OS X.
            # Set the environment variable FCGI_FORCE_CGI to "Y" or "y"
            # if you want to run your app as a simple CGI. (You can do
            # this with Apache's mod_env [not loaded by default in OS X
            # client, ha ha] and the SetEnv directive.)
            if not isFCGI or \
               os.environ.get('FCGI_FORCE_CGI', 'N').upper().startswith('Y'):
                req = self.cgirequest_class(self)
                req.run()
                sys.exit(0)
        else:
            # Run as a server
            if type(self._bindAddress) is str:
                # Unix socket
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                try:
                    os.unlink(self._bindAddress)
                except OSError:
                    pass
            else:
                # INET socket
                assert type(self._bindAddress) is tuple
                assert len(self._bindAddress) == 2
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            sock.bind(self._bindAddress)
            sock.listen(socket.SOMAXCONN)

        return sock

    def _cleanupSocket(self, sock):
        """Closes the main socket."""
        sock.close()

    def _installSignalHandlers(self):
        self._oldSIGs = [(x,signal.getsignal(x)) for x in
                         (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)]
        signal.signal(signal.SIGHUP, self._hupHandler)
        signal.signal(signal.SIGINT, self._intHandler)
        signal.signal(signal.SIGTERM, self._intHandler)

    def _restoreSignalHandlers(self):
        for signum,handler in self._oldSIGs:
            signal.signal(signum, handler)
        
    def _hupHandler(self, signum, frame):
        self._hupReceived = True
        self._keepGoing = False

    def _intHandler(self, signum, frame):
        self._keepGoing = False

    def run(self, timeout=1.0):
        """
        The main loop. Exits on SIGHUP, SIGINT, SIGTERM. Returns True if
        SIGHUP was received, False otherwise.
        """
        web_server_addrs = os.environ.get('FCGI_WEB_SERVER_ADDRS')
        if web_server_addrs is not None:
            web_server_addrs = map(lambda x: x.strip(),
                                   web_server_addrs.split(','))

        sock = self._setupSocket()

        self._keepGoing = True
        self._hupReceived = False

        # Install signal handlers.
        self._installSignalHandlers()

        while self._keepGoing:
            try:
                r, w, e = select.select([sock], [], [], timeout)
            except select.error, e:
                if e[0] == errno.EINTR:
                    continue
                raise

            if r:
                try:
                    clientSock, addr = sock.accept()
                except socket.error, e:
                    if e[0] in (errno.EINTR, errno.EAGAIN):
                        continue
                    raise

                if web_server_addrs and \
                       (len(addr) != 2 or addr[0] not in web_server_addrs):
                    clientSock.close()
                    continue

                # Instantiate a new Connection and begin processing FastCGI
                # messages (either in a new thread or this thread).
                conn = self._connectionClass(clientSock, addr, self)
                thread.start_new_thread(conn.run, ())

            self._mainloopPeriodic()

        # Restore signal handlers.
        self._restoreSignalHandlers()

        self._cleanupSocket(sock)

        return self._hupReceived

    def _mainloopPeriodic(self):
        """
        Called with just about each iteration of the main loop. Meant to
        be overridden.
        """
        pass

    def _exit(self, reload=False):
        """
        Protected convenience method for subclasses to force an exit. Not
        really thread-safe, which is why it isn't public.
        """
        if self._keepGoing:
            self._keepGoing = False
            self._hupReceived = reload

    def handler(self, req):
        """
        Default handler, which just raises an exception. Unless a handler
        is passed at initialization time, this must be implemented by
        a subclass.
        """
        raise NotImplementedError, self.__class__.__name__ + '.handler'

    def error(self, req):
        """
        Called by Request if an exception occurs within the handler. May and
        should be overridden.
        """
        import cgitb
        req.stdout.write('Content-Type: text/html\r\n\r\n' +
                         cgitb.html(sys.exc_info()))

class WSGIServer(Server):
    """
    FastCGI server that supports the Web Server Gateway Interface. See
    <http://www.python.org/peps/pep-0333.html>.
    """
    def __init__(self, application, environ=None, multithreaded=True, **kw):
        """
        environ, if present, must be a dictionary-like object. Its
        contents will be copied into application's environ. Useful
        for passing application-specific variables.

        Set multithreaded to False if your application is not MT-safe.
        """
        if kw.has_key('handler'):
            del kw['handler'] # Doesn't make sense to let this through
        super(WSGIServer, self).__init__(**kw)

        if environ is None:
            environ = {}

        self.application = application
        self.environ = environ
        self.multithreaded = multithreaded

        # Used to force single-threadedness
        self._app_lock = thread.allocate_lock()

    def handler(self, req):
        """Special handler for WSGI."""
        if req.role != FCGI_RESPONDER:
            return FCGI_UNKNOWN_ROLE, 0

        # Mostly taken from example CGI gateway.
        environ = req.params
        environ.update(self.environ)

        environ['wsgi.version'] = (1,0)
        environ['wsgi.input'] = req.stdin
        if self._bindAddress is None:
            stderr = req.stderr
        else:
            stderr = TeeOutputStream((sys.stderr, req.stderr))
        environ['wsgi.errors'] = stderr
        environ['wsgi.multithread'] = not isinstance(req, CGIRequest) and \
                                      thread_available and self.multithreaded
        # Rationale for the following: If started by the web server
        # (self._bindAddress is None) in either FastCGI or CGI mode, the
        # possibility of being spawned multiple times simultaneously is quite
        # real. And, if started as an external server, multiple copies may be
        # spawned for load-balancing/redundancy. (Though I don't think
        # mod_fastcgi supports this?)
        environ['wsgi.multiprocess'] = True
        environ['wsgi.run_once'] = isinstance(req, CGIRequest)

        if environ.get('HTTPS', 'off') in ('on', '1'):
            environ['wsgi.url_scheme'] = 'https'
        else:
            environ['wsgi.url_scheme'] = 'http'

        self._sanitizeEnv(environ)

        headers_set = []
        headers_sent = []
        result = None

        def write(data):
            assert type(data) is str, 'write() argument must be string'
            assert headers_set, 'write() before start_response()'

            if not headers_sent:
                status, responseHeaders = headers_sent[:] = headers_set
                found = False
                for header,value in responseHeaders:
                    if header.lower() == 'content-length':
                        found = True
                        break
                if not found and result is not None:
                    try:
                        if len(result) == 1:
                            responseHeaders.append(('Content-Length',
                                                    str(len(data))))
                    except:
                        pass
                s = 'Status: %s\r\n' % status
                for header in responseHeaders:
                    s += '%s: %s\r\n' % header
                s += '\r\n'
                req.stdout.write(s)

            req.stdout.write(data)
            req.stdout.flush()

        def start_response(status, response_headers, exc_info=None):
            if exc_info:
                try:
                    if headers_sent:
                        # Re-raise if too late
                        raise exc_info[0], exc_info[1], exc_info[2]
                finally:
                    exc_info = None # avoid dangling circular ref
            else:
                assert not headers_set, 'Headers already set!'

            assert type(status) is str, 'Status must be a string'
            assert len(status) >= 4, 'Status must be at least 4 characters'
            assert int(status[:3]), 'Status must begin with 3-digit code'
            assert status[3] == ' ', 'Status must have a space after code'
            assert type(response_headers) is list, 'Headers must be a list'
            if __debug__:
                for name,val in response_headers:
                    assert type(name) is str, 'Header names must be strings'
                    assert type(val) is str, 'Header values must be strings'

            headers_set[:] = [status, response_headers]
            return write

        if not self.multithreaded:
            self._app_lock.acquire()
        try:
            result = self.application(environ, start_response)
            try:
                for data in result:
                    if data:
                        write(data)
                if not headers_sent:
                    write('') # in case body was empty
            finally:
                if hasattr(result, 'close'):
                    result.close()
        finally:
            if not self.multithreaded:
                self._app_lock.release()

        return FCGI_REQUEST_COMPLETE, 0

    def _sanitizeEnv(self, environ):
        """Ensure certain values are present, if required by WSGI."""
        if not environ.has_key('SCRIPT_NAME'):
            environ['SCRIPT_NAME'] = ''
        if not environ.has_key('PATH_INFO'):
            environ['PATH_INFO'] = ''

        # If any of these are missing, it probably signifies a broken
        # server...
        for name,default in [('REQUEST_METHOD', 'GET'),
                             ('SERVER_NAME', 'localhost'),
                             ('SERVER_PORT', '80'),
                             ('SERVER_PROTOCOL', 'HTTP/1.0')]:
            if not environ.has_key(name):
                environ['wsgi.errors'].write('%s: missing FastCGI param %s '
                                             'required by WSGI!\n' %
                                             (self.__class__.__name__, name))
                environ[name] = default
            
if __name__ == '__main__':
    def test_app(environ, start_response):
        """Probably not the most efficient example."""
        import cgi
        start_response('200 OK', [('Content-Type', 'text/html')])
        yield '<html><head><title>Hello World!</title></head>\n' \
              '<body>\n' \
              '<p>Hello World!</p>\n' \
              '<table border="1">'
        names = environ.keys()
        names.sort()
        for name in names:
            yield '<tr><td>%s</td><td>%s</td></tr>\n' % (
                name, cgi.escape(`environ[name]`))

        form = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ,
                                keep_blank_values=1)
        if form.list:
            yield '<tr><th colspan="2">Form data</th></tr>'

        for field in form.list:
            yield '<tr><td>%s</td><td>%s</td></tr>\n' % (
                field.name, field.value)

        yield '</table>\n' \
              '</body></html>\n'

    WSGIServer(test_app,multithreaded=False).run()

########NEW FILE########
__FILENAME__ = qweb
#!/usr/bin/python2.3
#
# vim:set et ts=4 fdc=0 fdn=2 fdl=0:
#
# There are no blank lines between blocks beacause i use folding from:
# http://www.vim.org/scripts/script.php?script_id=515
#

"""= QWeb Framework =

== What is QWeb ? ==

QWeb is a python based [http://www.python.org/doc/peps/pep-0333/ WSGI]
compatible web framework, it provides an infratructure to quickly build web
applications consisting of:

 * A lightweight request handler (QWebRequest)
 * An xml templating engine (QWebXml and QWebHtml)
 * A simple name based controler (qweb_control)
 * A standalone WSGI Server (QWebWSGIServer)
 * A cgi and fastcgi WSGI wrapper (taken from flup)
 * A startup function that starts cgi, factgi or standalone according to the
   evironement (qweb_autorun).

QWeb applications are runnable in standalone mode (from commandline), via
FastCGI, Regular CGI or by any python WSGI compliant server.

QWeb doesn't provide any database access but it integrates nicely with ORMs
such as SQLObject, SQLAlchemy or plain DB-API.

Written by Antony Lesuisse (email al AT udev.org)

Homepage: http://antony.lesuisse.org/qweb/trac/

Forum: [http://antony.lesuisse.org/qweb/forum/viewforum.php?id=1 Forum]

== Quick Start (for Linux, MacOS X and cygwin) ==

Make sure you have at least python 2.3 installed and run the following commands:

{{{
$ wget http://antony.lesuisse.org/qweb/files/QWeb-0.7.tar.gz
$ tar zxvf QWeb-0.7.tar.gz
$ cd QWeb-0.7/examples/blog
$ ./blog.py
}}}

And point your browser to http://localhost:8080/

You may also try AjaxTerm which uses qweb request handler.

== Download ==

 * Version 0.7:
   * Source [/qweb/files/QWeb-0.7.tar.gz QWeb-0.7.tar.gz]
   * Python 2.3 Egg [/qweb/files/QWeb-0.7-py2.3.egg QWeb-0.7-py2.3.egg]
   * Python 2.4 Egg [/qweb/files/QWeb-0.7-py2.4.egg QWeb-0.7-py2.4.egg]

 * [/qweb/trac/browser Browse the source repository]

== Documentation ==

 * [/qweb/trac/browser/trunk/README.txt?format=raw Read the included documentation] 
 * QwebTemplating

== Mailin-list ==

 * Forum: [http://antony.lesuisse.org/qweb/forum/viewforum.php?id=1 Forum]
 * No mailing-list exists yet, discussion should happen on: [http://mail.python.org/mailman/listinfo/web-sig web-sig] [http://mail.python.org/pipermail/web-sig/ archives]

QWeb Components:
----------------

QWeb also feature a simple components api, that enables developers to easily
produces reusable components.

Default qweb components:

    - qweb_static:
        A qweb component to serve static content from the filesystem or from
        zipfiles.

    - qweb_dbadmin:
        scaffolding for sqlobject

License
-------
qweb/fcgi.py wich is BSD-like from saddi.com.
Everything else is put in the public domain.


TODO
----
    Announce QWeb to python-announce-list@python.org web-sig@python.org
    qweb_core
        rename request methods into
            request_save_files
            response_404
            response_redirect
            response_download
        request callback_generator, callback_function ?
        wsgi callback_server_local
        xml tags explicitly call render_attributes(t_att)?
        priority form-checkbox over t-value (for t-option)

"""

import BaseHTTPServer,SocketServer,Cookie
import cgi,datetime,email,email.Message,errno,gzip,os,random,re,socket,sys,tempfile,time,types,urllib,urlparse,xml.dom
try:
    import cPickle as pickle
except ImportError:
    import pickle
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

#----------------------------------------------------------
# Qweb Xml t-raw t-esc t-if t-foreach t-set t-call t-trim
#----------------------------------------------------------
class QWebEval:
    def __init__(self,data):
        self.data=data
    def __getitem__(self,expr):
        if self.data.has_key(expr):
            return self.data[expr]
        r=None
        try:
            r=eval(expr,self.data)
        except NameError,e:
            pass
        except AttributeError,e:
            pass
        except Exception,e:
            print "qweb: expression error '%s' "%expr,e
        if self.data.has_key("__builtins__"):
            del self.data["__builtins__"]
        return r
    def eval_object(self,expr):
        return self[expr]
    def eval_str(self,expr):
        if expr=="0":
            return self.data[0]
        if isinstance(self[expr],unicode):
            return self[expr].encode("utf8")
        return str(self[expr])
    def eval_format(self,expr):
        try:
            return str(expr%self)
        except:
            return "qweb: format error '%s' "%expr
#       if isinstance(r,unicode):
#           return r.encode("utf8")
    def eval_bool(self,expr):
        if self.eval_object(expr):
            return 1
        else:
            return 0
class QWebXml:
    """QWeb Xml templating engine
    
    The templating engine use a very simple syntax, "magic" xml attributes, to
    produce any kind of texutal output (even non-xml).
    
    QWebXml:
        the template engine core implements the basic magic attributes:
    
        t-att t-raw t-esc t-if t-foreach t-set t-call t-trim
    
    """
    def __init__(self,x=None,zipname=None):
        self.node=xml.dom.Node
        self._t={}
        self._render_tag={}
        prefix='render_tag_'
        for i in [j for j in dir(self) if j.startswith(prefix)]:
            name=i[len(prefix):].replace('_','-')
            self._render_tag[name]=getattr(self.__class__,i)

        self._render_att={}
        prefix='render_att_'
        for i in [j for j in dir(self) if j.startswith(prefix)]:
            name=i[len(prefix):].replace('_','-')
            self._render_att[name]=getattr(self.__class__,i)

        if x!=None:
            if zipname!=None:
                import zipfile
                zf=zipfile.ZipFile(zipname, 'r')
                self.add_template(zf.read(x))
            else:
                self.add_template(x)
    def register_tag(self,tag,func):
        self._render_tag[tag]=func
    def add_template(self,x):
        if hasattr(x,'documentElement'):
            dom=x
        elif x.startswith("<?xml"):
            import xml.dom.minidom
            dom=xml.dom.minidom.parseString(x)
        else:
            import xml.dom.minidom
            dom=xml.dom.minidom.parse(x)
        for n in dom.documentElement.childNodes:
            if n.nodeName=="t":
                self._t[str(n.getAttribute("t-name"))]=n
    def get_template(self,name):
        return self._t[name]

    def eval_object(self,expr,v):
        return QWebEval(v).eval_object(expr)
    def eval_str(self,expr,v):
        return QWebEval(v).eval_str(expr)
    def eval_format(self,expr,v):
        return QWebEval(v).eval_format(expr)
    def eval_bool(self,expr,v):
        return QWebEval(v).eval_bool(expr)

    def render(self,tname,v={},out=None):
        if self._t.has_key(tname):
            return self.render_node(self._t[tname],v)
        else:
            return 'qweb: template "%s" not found'%tname
    def render_node(self,e,v):
        r=""
        if e.nodeType==self.node.TEXT_NODE or e.nodeType==self.node.CDATA_SECTION_NODE:
            r=e.data.encode("utf8")
        elif e.nodeType==self.node.ELEMENT_NODE:
            pre=""
            g_att=""
            t_render=None
            t_att={}
            for (an,av) in e.attributes.items():
                an=str(an)
                if isinstance(av,types.UnicodeType):
                    av=av.encode("utf8")
                else:
                    av=av.nodeValue.encode("utf8")
                if an.startswith("t-"):
                    for i in self._render_att:
                        if an[2:].startswith(i):
                            g_att+=self._render_att[i](self,e,an,av,v)
                            break
                    else:
                        if self._render_tag.has_key(an[2:]):
                            t_render=an[2:]
                        t_att[an[2:]]=av
                else:
                    g_att+=' %s="%s"'%(an,cgi.escape(av,1));
            if t_render:
                if self._render_tag.has_key(t_render):
                    r=self._render_tag[t_render](self,e,t_att,g_att,v)
            else:
                r=self.render_element(e,g_att,v,pre,t_att.get("trim",0))
        return r
    def render_element(self,e,g_att,v,pre="",trim=0):
        g_inner=[]
        for n in e.childNodes:
            g_inner.append(self.render_node(n,v))
        name=str(e.nodeName)
        inner="".join(g_inner)
        if trim==0:
            pass
        elif trim=='left':
            inner=inner.lstrip()
        elif trim=='right':
            inner=inner.rstrip()
        elif trim=='both':
            inner=inner.strip()
        if name=="t":
            return inner
        elif len(inner):
            return "<%s%s>%s%s</%s>"%(name,g_att,pre,inner,name)
        else:
            return "<%s%s/>"%(name,g_att)

    # Attributes
    def render_att_att(self,e,an,av,v):
        if an.startswith("t-attf-"):
            att,val=an[7:],self.eval_format(av,v)
        elif an.startswith("t-att-"):
            att,val=(an[6:],self.eval_str(av,v))
        else:
            att,val=self.eval_object(av,v)
        return ' %s="%s"'%(att,cgi.escape(val,1))

    # Tags
    def render_tag_raw(self,e,t_att,g_att,v):
        return self.eval_str(t_att["raw"],v)
    def render_tag_rawf(self,e,t_att,g_att,v):
        return self.eval_format(t_att["rawf"],v)
    def render_tag_esc(self,e,t_att,g_att,v):
        return cgi.escape(self.eval_str(t_att["esc"],v))
    def render_tag_escf(self,e,t_att,g_att,v):
        return cgi.escape(self.eval_format(t_att["escf"],v))
    def render_tag_foreach(self,e,t_att,g_att,v):
        expr=t_att["foreach"]
        enum=self.eval_object(expr,v)
        if enum!=None:
            var=t_att.get('as',expr).replace('.','_')
            d=v.copy()
            size=-1
            if isinstance(enum,types.ListType):
                size=len(enum)
            elif isinstance(enum,types.TupleType):
                size=len(enum)
            elif hasattr(enum,'count'):
                size=enum.count()
            d["%s_size"%var]=size
            d["%s_all"%var]=enum
            index=0
            ru=[]
            for i in enum:
                d["%s_value"%var]=i
                d["%s_index"%var]=index
                d["%s_first"%var]=index==0
                d["%s_even"%var]=index%2
                d["%s_odd"%var]=(index+1)%2
                d["%s_last"%var]=index+1==size
                if index%2:
                    d["%s_parity"%var]='odd'
                else:
                    d["%s_parity"%var]='even'
                if isinstance(i,types.DictType):
                    d.update(i)
                else:
                    d[var]=i
                ru.append(self.render_element(e,g_att,d))
                index+=1
            return "".join(ru)
        else:
            return "qweb: t-foreach %s not found."%expr
    def render_tag_if(self,e,t_att,g_att,v):
        if self.eval_bool(t_att["if"],v):
            return self.render_element(e,g_att,v)
        else:
            return ""
    def render_tag_call(self,e,t_att,g_att,v):
        # TODO t-prefix
        if t_att.has_key("import"):
            d=v
        else:
            d=v.copy()
        d[0]=self.render_element(e,g_att,d)
        return self.render(t_att["call"],d)
    def render_tag_set(self,e,t_att,g_att,v):
        if t_att.has_key("eval"):
            v[t_att["set"]]=self.eval_object(t_att["eval"],v)
        else:
            v[t_att["set"]]=self.render_element(e,g_att,v)
        return ""

#----------------------------------------------------------
# QWeb HTML (+deprecated QWebFORM and QWebOLD)
#----------------------------------------------------------
class QWebURL:
    """ URL helper
    assert req.PATH_INFO== "/site/admin/page_edit"
    u = QWebURL(root_path="/site/",req_path=req.PATH_INFO)
    s=u.url2_href("user/login",{'a':'1'})
    assert s=="../user/login?a=1"
    
    """
    def __init__(self, root_path="/", req_path="/",defpath="",defparam={}):
        self.defpath=defpath
        self.defparam=defparam
        self.root_path=root_path
        self.req_path=req_path
        self.req_list=req_path.split("/")[:-1]
        self.req_len=len(self.req_list)
    def decode(self,s):
        h={}
        for k,v in cgi.parse_qsl(s,1):
            h[k]=v
        return h
    def encode(self,h):
        return urllib.urlencode(h.items())
    def request(self,req):
        return req.REQUEST
    def copy(self,path=None,param=None):
        npath=self.defpath
        if path:
            npath=path
        nparam=self.defparam.copy()
        if param:
            nparam.update(param)
        return QWebURL(self.root_path,self.req_path,npath,nparam)
    def path(self,path=''):
        if not path:
            path=self.defpath
        pl=(self.root_path+path).split('/')
        i=0
        for i in range(min(len(pl), self.req_len)):
            if pl[i]!=self.req_list[i]:
                break
        else:
            i+=1
        dd=self.req_len-i
        if dd<0:
            dd=0
        return '/'.join(['..']*dd+pl[i:])
    def href(self,path='',arg={}):
        p=self.path(path)
        tmp=self.defparam.copy()
        tmp.update(arg)
        s=self.encode(tmp)
        if len(s):
            return p+"?"+s
        else:
            return p
    def form(self,path='',arg={}):
        p=self.path(path)
        tmp=self.defparam.copy()
        tmp.update(arg)
        r=''.join(['<input type="hidden" name="%s" value="%s"/>'%(k,cgi.escape(str(v),1)) for k,v in tmp.items()])
        return (p,r)
class QWebField:
    def __init__(self,name=None,default="",check=None):
        self.name=name
        self.default=default
        self.check=check
        # optional attributes
        self.type=None
        self.trim=1
        self.required=1
        self.cssvalid="form_valid"
        self.cssinvalid="form_invalid"
        # set by addfield
        self.form=None
        # set by processing
        self.input=None
        self.css=None
        self.value=None
        self.valid=None
        self.invalid=None
        self.validate(1)
    def validate(self,val=1,update=1):
        if val:
            self.valid=1
            self.invalid=0
            self.css=self.cssvalid
        else:
            self.valid=0
            self.invalid=1
            self.css=self.cssinvalid
        if update and self.form:
            self.form.update()
    def invalidate(self,update=1):
        self.validate(0,update)
class QWebForm:
    class QWebFormF:
        pass
    def __init__(self,e=None,arg=None,default=None):
        self.fields={}
        # all fields have been submitted
        self.submitted=False
        self.missing=[]
        # at least one field is invalid or missing
        self.invalid=False
        self.error=[]
        # all fields have been submitted and are valid
        self.valid=False
        # fields under self.f for convenience
        self.f=self.QWebFormF()
        if e:
            self.add_template(e)
        # assume that the fields are done with the template
        if default:
            self.set_default(default,e==None)
        if arg!=None:
            self.process_input(arg)
    def __getitem__(self,k):
        return self.fields[k]
    def set_default(self,default,add_missing=1):
        for k,v in default.items():
            if self.fields.has_key(k):
                self.fields[k].default=str(v)
            elif add_missing:
                self.add_field(QWebField(k,v))
    def add_field(self,f):
        self.fields[f.name]=f
        f.form=self
        setattr(self.f,f.name,f)
    def add_template(self,e):
        att={}
        for (an,av) in e.attributes.items():
            an=str(an)
            if an.startswith("t-"):
                att[an[2:]]=av.encode("utf8")
        for i in ["form-text", "form-password", "form-radio", "form-checkbox", "form-select","form-textarea"]:
            if att.has_key(i):
                name=att[i].split(".")[-1]
                default=att.get("default","")
                check=att.get("check",None)
                f=QWebField(name,default,check)
                if i=="form-textarea":
                    f.type="textarea"
                    f.trim=0
                if i=="form-checkbox":
                    f.type="checkbox"
                    f.required=0
                self.add_field(f)
        for n in e.childNodes:
            if n.nodeType==n.ELEMENT_NODE:
                self.add_template(n)
    def process_input(self,arg):
        for f in self.fields.values():
            if arg.has_key(f.name):
                f.input=arg[f.name]
                f.value=f.input
                if f.trim:
                    f.input=f.input.strip()
                f.validate(1,False)
                if f.check==None:
                    continue
                elif callable(f.check):
                    pass
                elif isinstance(f.check,str):
                    v=f.check
                    if f.check=="email":
                        v=r"/^[^@#!& ]+@[A-Za-z0-9-][.A-Za-z0-9-]{0,64}\.[A-Za-z]{2,5}$/"
                    if f.check=="date":
                        v=r"/^(19|20)\d\d-(0[1-9]|1[012])-(0[1-9]|[12][0-9]|3[01])$/"
                    if not re.match(v[1:-1],f.input):
                        f.validate(0,False)
            else:
                f.value=f.default
        self.update()
    def validate_all(self,val=1):
        for f in self.fields.values():
            f.validate(val,0)
        self.update()
    def invalidate_all(self):
        self.validate_all(0)
    def update(self):
        self.submitted=True
        self.valid=True
        self.errors=[]
        for f in self.fields.values():
            if f.required and f.input==None:
                self.submitted=False
                self.valid=False
                self.missing.append(f.name)
            if f.invalid:
                self.valid=False
                self.error.append(f.name)
        # invalid have been submitted and 
        self.invalid=self.submitted and self.valid==False
    def collect(self):
        d={}
        for f in self.fields.values():
            d[f.name]=f.value
        return d
class QWebURLEval(QWebEval):
    def __init__(self,data):
        QWebEval.__init__(self,data)
    def __getitem__(self,expr):
        r=QWebEval.__getitem__(self,expr)
        if isinstance(r,str):
            return urllib.quote_plus(r)
        else:
            return r
class QWebHtml(QWebXml):
    """QWebHtml
    QWebURL:
    QWebField:
    QWebForm:
    QWebHtml:
        an extended template engine, with a few utility class to easily produce
        HTML, handle URLs and process forms, it adds the following magic attributes:
    
        t-href t-action t-form-text t-form-password t-form-textarea t-form-radio
        t-form-checkbox t-form-select t-option t-selected t-checked t-pager
    
    # explication URL:
    # v['tableurl']=QWebUrl({p=afdmin,saar=,orderby=,des=,mlink;meta_active=})
    # t-href="tableurl?desc=1"
    #
    # explication FORM: t-if="form.valid()"
    # Foreach i
    #   email: <input type="text" t-esc-name="i" t-esc-value="form[i].value" t-esc-class="form[i].css"/>
    #   <input type="radio" name="spamtype" t-esc-value="i" t-selected="i==form.f.spamtype.value"/>
    #   <option t-esc-value="cc" t-selected="cc==form.f.country.value"><t t-esc="cname"></option>
    # Simple forms:
    #   <input t-form-text="form.email" t-check="email"/>
    #   <input t-form-password="form.email" t-check="email"/>
    #   <input t-form-radio="form.email" />
    #   <input t-form-checkbox="form.email" />
    #   <textarea t-form-textarea="form.email" t-check="email"/>
    #   <select t-form-select="form.email"/>
    #       <option t-value="1">
    #   <input t-form-radio="form.spamtype" t-value="1"/> Cars
    #   <input t-form-radio="form.spamtype" t-value="2"/> Sprt
    """
    # QWebForm from a template
    def form(self,tname,arg=None,default=None):
        form=QWebForm(self._t[tname],arg,default)
        return form

    # HTML Att
    def eval_url(self,av,v):
        s=QWebURLEval(v).eval_format(av)
        a=s.split('?',1)
        arg={}
        if len(a)>1:
            for k,v in cgi.parse_qsl(a[1],1):
                arg[k]=v
        b=a[0].split('/',1)
        path=''
        if len(b)>1:
            path=b[1]
        u=b[0]
        return u,path,arg
    def render_att_url_(self,e,an,av,v):
        u,path,arg=self.eval_url(av,v)
        if not isinstance(v.get(u,0),QWebURL):
            out='qweb: missing url %r %r %r'%(u,path,arg)
        else:
            out=v[u].href(path,arg)
        return ' %s="%s"'%(an[6:],cgi.escape(out,1))
    def render_att_href(self,e,an,av,v):
        return self.render_att_url_(e,"t-url-href",av,v)
    def render_att_checked(self,e,an,av,v):
        if self.eval_bool(av,v):
            return ' %s="%s"'%(an[2:],an[2:])
        else:
            return ''
    def render_att_selected(self,e,an,av,v):
        return self.render_att_checked(e,an,av,v)

    # HTML Tags forms
    def render_tag_rawurl(self,e,t_att,g_att,v):
        u,path,arg=self.eval_url(t_att["rawurl"],v)
        return v[u].href(path,arg)
    def render_tag_escurl(self,e,t_att,g_att,v):
        u,path,arg=self.eval_url(t_att["escurl"],v)
        return cgi.escape(v[u].href(path,arg))
    def render_tag_action(self,e,t_att,g_att,v):
        u,path,arg=self.eval_url(t_att["action"],v)
        if not isinstance(v.get(u,0),QWebURL):
            action,input=('qweb: missing url %r %r %r'%(u,path,arg),'')
        else:
            action,input=v[u].form(path,arg)
        g_att+=' action="%s"'%action
        return self.render_element(e,g_att,v,input)
    def render_tag_form_text(self,e,t_att,g_att,v):
        f=self.eval_object(t_att["form-text"],v)
        g_att+=' type="text" name="%s" value="%s" class="%s"'%(f.name,cgi.escape(f.value,1),f.css)
        return self.render_element(e,g_att,v)
    def render_tag_form_password(self,e,t_att,g_att,v):
        f=self.eval_object(t_att["form-password"],v)
        g_att+=' type="password" name="%s" value="%s" class="%s"'%(f.name,cgi.escape(f.value,1),f.css)
        return self.render_element(e,g_att,v)
    def render_tag_form_textarea(self,e,t_att,g_att,v):
        type="textarea"
        f=self.eval_object(t_att["form-textarea"],v)
        g_att+=' name="%s" class="%s"'%(f.name,f.css)
        r="<%s%s>%s</%s>"%(type,g_att,cgi.escape(f.value,1),type)
        return r
    def render_tag_form_radio(self,e,t_att,g_att,v):
        f=self.eval_object(t_att["form-radio"],v)
        val=t_att["value"]
        g_att+=' type="radio" name="%s" value="%s"'%(f.name,val)
        if f.value==val:
            g_att+=' checked="checked"'
        return self.render_element(e,g_att,v)
    def render_tag_form_checkbox(self,e,t_att,g_att,v):
        f=self.eval_object(t_att["form-checkbox"],v)
        val=t_att["value"]
        g_att+=' type="checkbox" name="%s" value="%s"'%(f.name,val)
        if f.value==val:
            g_att+=' checked="checked"'
        return self.render_element(e,g_att,v)
    def render_tag_form_select(self,e,t_att,g_att,v):
        f=self.eval_object(t_att["form-select"],v)
        g_att+=' name="%s" class="%s"'%(f.name,f.css)
        return self.render_element(e,g_att,v)
    def render_tag_option(self,e,t_att,g_att,v):
        f=self.eval_object(e.parentNode.getAttribute("t-form-select"),v)
        val=t_att["option"]
        g_att+=' value="%s"'%(val)
        if f.value==val:
            g_att+=' selected="selected"'
        return self.render_element(e,g_att,v)

    # HTML Tags others
    def render_tag_pager(self,e,t_att,g_att,v):
        pre=t_att["pager"]
        total=int(self.eval_str(t_att["total"],v))
        start=int(self.eval_str(t_att["start"],v))
        step=int(self.eval_str(t_att.get("step","100"),v))
        scope=int(self.eval_str(t_att.get("scope","5"),v))
        # Compute Pager
        p=pre+"_"
        d={}
        d[p+"tot_size"]=total
        d[p+"tot_page"]=tot_page=total/step
        d[p+"win_start0"]=total and start
        d[p+"win_start1"]=total and start+1
        d[p+"win_end0"]=max(0,min(start+step-1,total-1))
        d[p+"win_end1"]=min(start+step,total)
        d[p+"win_page0"]=win_page=start/step
        d[p+"win_page1"]=win_page+1
        d[p+"prev"]=(win_page!=0)
        d[p+"prev_start"]=(win_page-1)*step
        d[p+"next"]=(tot_page>=win_page+1)
        d[p+"next_start"]=(win_page+1)*step
        l=[]
        begin=win_page-scope
        end=win_page+scope
        if begin<0:
            end-=begin
        if end>tot_page:
            begin-=(end-tot_page)
        i=max(0,begin)
        while i<=min(end,tot_page) and total!=step:
            l.append( { p+"page0":i, p+"page1":i+1, p+"start":i*step, p+"sel":(win_page==i) })
            i+=1
        d[p+"active"]=len(l)>1
        d[p+"list"]=l
        # Update v
        v.update(d)
        return ""

#----------------------------------------------------------
# QWeb Simple Controller
#----------------------------------------------------------
def qweb_control(self,jump='main',p=[]):
    """ qweb_control(self,jump='main',p=[]):
    A simple function to handle the controler part of your application. It
    dispatch the control to the jump argument, while ensuring that prefix
    function have been called.

    qweb_control replace '/' to '_' and strip '_' from the jump argument.

    name1
    name1_name2
    name1_name2_name3

    """
    jump=jump.replace('/','_').strip('_')
    if not hasattr(self,jump):
        return 0
    done={}
    todo=[]
    while 1:
        if jump!=None:
            tmp=""
            todo=[]
            for i in jump.split("_"):
                tmp+=i+"_";
                if not done.has_key(tmp[:-1]):
                    todo.append(tmp[:-1])
            jump=None
        elif len(todo):
            i=todo.pop(0)
            done[i]=1
            if hasattr(self,i):
                f=getattr(self,i)
                r=f(*p)
                if isinstance(r,types.StringType):
                    jump=r
        else:
            break
    return 1

#----------------------------------------------------------
# QWeb WSGI Request handler
#----------------------------------------------------------
class QWebSession(dict):
    def __init__(self,environ,**kw):
        dict.__init__(self)
        default={
            "path" : tempfile.gettempdir(),
            "cookie_name" : "QWEBSID",
            "cookie_lifetime" : 0,
            "cookie_path" : '/',
            "cookie_domain" : '',
            "limit_cache" : 1,
            "probability" : 0.01,
            "maxlifetime" : 3600,
            "disable" : 0,
        }
        for k,v in default.items():
            setattr(self,'session_%s'%k,kw.get(k,v))
        # Try to find session
        self.session_found_cookie=0
        self.session_found_url=0
        self.session_found=0
        self.session_orig=""
        # Try cookie
        c=Cookie.SimpleCookie()
        c.load(environ.get('HTTP_COOKIE', ''))
        if c.has_key(self.session_cookie_name):
            sid=c[self.session_cookie_name].value[:64]
            if re.match('[a-f0-9]+$',sid) and self.session_load(sid):
                self.session_id=sid
                self.session_found_cookie=1
                self.session_found=1
        # Try URL
        if not self.session_found_cookie:
            mo=re.search('&%s=([a-f0-9]+)'%self.session_cookie_name,environ.get('QUERY_STRING',''))
            if mo and self.session_load(mo.group(1)):
                self.session_id=mo.group(1)
                self.session_found_url=1
                self.session_found=1
        # New session
        if not self.session_found:
            self.session_id='%032x'%random.randint(1,2**128)
        self.session_trans_sid="&amp;%s=%s"%(self.session_cookie_name,self.session_id)
        # Clean old session
        if random.random() < self.session_probability:
            self.session_clean()
    def session_get_headers(self):
        h=[]
        if (not self.session_disable) and (len(self) or len(self.session_orig)):
            self.session_save()
            if not self.session_found_cookie:
                c=Cookie.SimpleCookie()
                c[self.session_cookie_name] = self.session_id
                c[self.session_cookie_name]['path'] = self.session_cookie_path
                if self.session_cookie_domain:
                    c[self.session_cookie_name]['domain'] = self.session_cookie_domain
#               if self.session_cookie_lifetime:
#                   c[self.session_cookie_name]['expires'] = TODO date localtime or not, datetime.datetime(1970, 1, 1)
                h.append(("Set-Cookie", c[self.session_cookie_name].OutputString()))
            if self.session_limit_cache:
                h.append(('Cache-Control','no-store, no-cache, must-revalidate, post-check=0, pre-check=0'))
                h.append(('Expires','Thu, 19 Nov 1981 08:52:00 GMT'))
                h.append(('Pragma','no-cache'))
        return h
    def session_load(self,sid):
        fname=os.path.join(self.session_path,'qweb_sess_%s'%sid)
        try:
            orig=file(fname).read()
            d=pickle.loads(orig)
        except:
            return
        self.session_orig=orig
        self.update(d)
        return 1
    def session_save(self):
        if not os.path.isdir(self.session_path):
            os.makedirs(self.session_path)
        fname=os.path.join(self.session_path,'qweb_sess_%s'%self.session_id)
        try:
            oldtime=os.path.getmtime(fname)
        except OSError,IOError:
            oldtime=0
        dump=pickle.dumps(self.copy())
        if (dump != self.session_orig) or (time.time() > oldtime+self.session_maxlifetime/4):
            tmpname=os.path.join(self.session_path,'qweb_sess_%s_%x'%(self.session_id,random.randint(1,2**32)))
            f=file(tmpname,'wb')
            f.write(dump)
            f.close()
            if sys.platform=='win32' and os.path.isfile(fname):
                os.remove(fname)
            os.rename(tmpname,fname)
    def session_clean(self):
        t=time.time()
        try:
            for i in [os.path.join(self.session_path,i) for i in os.listdir(self.session_path) if i.startswith('qweb_sess_')]:
                if (t > os.path.getmtime(i)+self.session_maxlifetime):
                    os.unlink(i)
        except OSError,IOError:
            pass
class QWebSessionMem(QWebSession):
    def session_load(self,sid):
        global _qweb_sessions
        if not "_qweb_sessions" in globals():
            _qweb_sessions={}
        if _qweb_sessions.has_key(sid):
            self.session_orig=_qweb_sessions[sid]
            self.update(self.session_orig)
            return 1
    def session_save(self):
        global _qweb_sessions
        if not "_qweb_sessions" in globals():
            _qweb_sessions={}
        _qweb_sessions[self.session_id]=self.copy()
class QWebSessionService:
    def __init__(self, wsgiapp, url_rewrite=0):
        self.wsgiapp=wsgiapp
        self.url_rewrite_tags="a=href,area=href,frame=src,form=,fieldset="
    def __call__(self, environ, start_response):
        # TODO
        # use QWebSession to provide environ["qweb.session"]
        return self.wsgiapp(environ,start_response)
class QWebDict(dict):
    def __init__(self,*p):
        dict.__init__(self,*p)
    def __getitem__(self,key):
        return self.get(key,"")
    def int(self,key):
        try:
            return int(self.get(key,"0"))
        except ValueError:
            return 0
class QWebListDict(dict):
    def __init__(self,*p):
        dict.__init__(self,*p)
    def __getitem__(self,key):
        return self.get(key,[])
    def appendlist(self,key,val):
        if self.has_key(key):
            self[key].append(val)
        else:
            self[key]=[val]
    def get_qwebdict(self):
        d=QWebDict()
        for k,v in self.items():
            d[k]=v[-1]
        return d
class QWebRequest:
    """QWebRequest a WSGI request handler.

    QWebRequest is a WSGI request handler that feature GET, POST and POST
    multipart methods, handles cookies and headers and provide a dict-like
    SESSION Object (either on the filesystem or in memory).

    It is constructed with the environ and start_response WSGI arguments:
    
      req=qweb.QWebRequest(environ, start_response)
    
    req has the folowing attributes :
    
      req.environ standard WSGI dict (CGI and wsgi ones)
    
    Some CGI vars as attributes from environ for convenience: 
    
      req.SCRIPT_NAME
      req.PATH_INFO
      req.REQUEST_URI
    
    Some computed value (also for convenience)
    
      req.FULL_URL full URL recontructed (http://host/query)
      req.FULL_PATH (URL path before ?querystring)
    
    Dict constructed from querystring and POST datas, PHP-like.
    
      req.GET contains GET vars
      req.POST contains POST vars
      req.REQUEST contains merge of GET and POST
      req.FILES contains uploaded files
      req.GET_LIST req.POST_LIST req.REQUEST_LIST req.FILES_LIST multiple arguments versions
      req.debug() returns an HTML dump of those vars
    
    A dict-like session object.
    
      req.SESSION the session start when the dict is not empty.
    
    Attribute for handling the response
    
      req.response_headers dict-like to set headers
      req.response_cookies a SimpleCookie to set cookies
      req.response_status a string to set the status like '200 OK'
    
      req.write() to write to the buffer
    
    req itselfs is an iterable object with the buffer, it will also also call
    start_response automatically before returning anything via the iterator.
    
    To make it short, it means that you may use
    
      return req
    
    at the end of your request handling to return the reponse to any WSGI
    application server.
    """
    #
    # This class contains part ripped from colubrid (with the permission of
    # mitsuhiko) see http://wsgiarea.pocoo.org/colubrid/
    #
    # - the class HttpHeaders
    # - the method load_post_data (tuned version)
    #
    class HttpHeaders(object):
        def __init__(self):
            self.data = [('Content-Type', 'text/html')]
        def __setitem__(self, key, value):
            self.set(key, value)
        def __delitem__(self, key):
            self.remove(key)
        def __contains__(self, key):
            key = key.lower()
            for k, v in self.data:
                if k.lower() == key:
                    return True
            return False
        def add(self, key, value):
            self.data.append((key, value))
        def remove(self, key, count=-1):
            removed = 0
            data = []
            for _key, _value in self.data:
                if _key.lower() != key.lower():
                    if count > -1:
                        if removed >= count:
                            break
                        else:
                            removed += 1
                    data.append((_key, _value))
            self.data = data
        def clear(self):
            self.data = []
        def set(self, key, value):
            self.remove(key)
            self.add(key, value)
        def get(self, key=False, httpformat=False):
            if not key:
                result = self.data
            else:
                result = []
                for _key, _value in self.data:
                    if _key.lower() == key.lower():
                        result.append((_key, _value))
            if httpformat:
                return '\n'.join(['%s: %s' % item for item in result])
            return result
    def load_post_data(self,environ,POST,FILES):
        length = int(environ['CONTENT_LENGTH'])
        DATA = environ['wsgi.input'].read(length)
        if environ.get('CONTENT_TYPE', '').startswith('multipart'):
            lines = ['Content-Type: %s' % environ.get('CONTENT_TYPE', '')]
            for key, value in environ.items():
                if key.startswith('HTTP_'):
                    lines.append('%s: %s' % (key, value))
            raw = '\r\n'.join(lines) + '\r\n\r\n' + DATA
            msg = email.message_from_string(raw)
            for sub in msg.get_payload():
                if not isinstance(sub, email.Message.Message):
                    continue
                name_dict = cgi.parse_header(sub['Content-Disposition'])[1]
                if 'filename' in name_dict:
                    # Nested MIME Messages are not supported'
                    if type([]) == type(sub.get_payload()):
                        continue
                    if not name_dict['filename'].strip():
                        continue
                    filename = name_dict['filename']
                    # why not keep all the filename? because IE always send 'C:\documents and settings\blub\blub.png'
                    filename = filename[filename.rfind('\\') + 1:]
                    if 'Content-Type' in sub:
                        content_type = sub['Content-Type']
                    else:
                        content_type = None
                    s = { "name":filename, "type":content_type, "data":sub.get_payload() }
                    FILES.appendlist(name_dict['name'], s)
                else:
                    POST.appendlist(name_dict['name'], sub.get_payload())
        else:
            POST.update(cgi.parse_qs(DATA,keep_blank_values=1))
        return DATA

    def __init__(self,environ,start_response,session=QWebSession):
        self.environ=environ
        self.start_response=start_response
        self.buffer=[]

        self.SCRIPT_NAME = environ.get('SCRIPT_NAME', '')
        self.PATH_INFO = environ.get('PATH_INFO', '')
        # extensions:
        self.FULL_URL = environ['FULL_URL'] = self.get_full_url(environ)
        # REQUEST_URI is optional, fake it if absent
        if not environ.has_key("REQUEST_URI"):
            environ["REQUEST_URI"]=urllib.quote(self.SCRIPT_NAME+self.PATH_INFO)
            if environ.get('QUERY_STRING'):
                environ["REQUEST_URI"]+='?'+environ['QUERY_STRING']
        self.REQUEST_URI = environ["REQUEST_URI"]
        # full quote url path before the ?
        self.FULL_PATH = environ['FULL_PATH'] = self.REQUEST_URI.split('?')[0]

        self.request_cookies=Cookie.SimpleCookie()
        self.request_cookies.load(environ.get('HTTP_COOKIE', ''))

        self.response_started=False
        self.response_gzencode=False
        self.response_cookies=Cookie.SimpleCookie()
        # to delete a cookie use: c[key]['expires'] = datetime.datetime(1970, 1, 1)
        self.response_headers=self.HttpHeaders()
        self.response_status="200 OK"

        self.php=None
        if self.environ.has_key("php"):
            self.php=environ["php"]
            self.SESSION=self.php._SESSION
            self.GET=self.php._GET
            self.POST=self.php._POST
            self.REQUEST=self.php._ARG
            self.FILES=self.php._FILES
        else:
            if isinstance(session,QWebSession):
                self.SESSION=session
            elif session:
                self.SESSION=session(environ)
            else:
                self.SESSION=None
            self.GET_LIST=QWebListDict(cgi.parse_qs(environ.get('QUERY_STRING', ''),keep_blank_values=1))
            self.POST_LIST=QWebListDict()
            self.FILES_LIST=QWebListDict()
            self.REQUEST_LIST=QWebListDict(self.GET_LIST)
            if environ['REQUEST_METHOD'] == 'POST':
                self.DATA=self.load_post_data(environ,self.POST_LIST,self.FILES_LIST)
                self.REQUEST_LIST.update(self.POST_LIST)
            self.GET=self.GET_LIST.get_qwebdict()
            self.POST=self.POST_LIST.get_qwebdict()
            self.FILES=self.FILES_LIST.get_qwebdict()
            self.REQUEST=self.REQUEST_LIST.get_qwebdict()
    def get_full_url(environ):
        # taken from PEP 333
        if 'FULL_URL' in environ:
            return environ['FULL_URL']
        url = environ['wsgi.url_scheme']+'://'
        if environ.get('HTTP_HOST'):
            url += environ['HTTP_HOST']
        else:
            url += environ['SERVER_NAME']
            if environ['wsgi.url_scheme'] == 'https':
                if environ['SERVER_PORT'] != '443':
                    url += ':' + environ['SERVER_PORT']
            else:
                if environ['SERVER_PORT'] != '80':
                    url += ':' + environ['SERVER_PORT']
        if environ.has_key('REQUEST_URI'):
            url += environ['REQUEST_URI']
        else:
            url += urllib.quote(environ.get('SCRIPT_NAME', ''))
            url += urllib.quote(environ.get('PATH_INFO', ''))
            if environ.get('QUERY_STRING'):
                url += '?' + environ['QUERY_STRING']
        return url
    get_full_url=staticmethod(get_full_url)
    def save_files(self):
        for k,v in self.FILES.items():
            if not v.has_key("tmp_file"):
                f=tempfile.NamedTemporaryFile()
                f.write(v["data"])
                f.flush()
                v["tmp_file"]=f
                v["tmp_name"]=f.name
    def debug(self):
        body=''
        for name,d in [
            ("GET",self.GET), ("POST",self.POST), ("REQUEST",self.REQUEST), ("FILES",self.FILES),
            ("GET_LIST",self.GET_LIST), ("POST_LIST",self.POST_LIST), ("REQUEST_LIST",self.REQUEST_LIST), ("FILES_LIST",self.FILES_LIST),
            ("SESSION",self.SESSION), ("environ",self.environ),
        ]:
            body+='<table border="1" width="100%" align="center">\n'
            body+='<tr><th colspan="2" align="center">%s</th></tr>\n'%name
            keys=d.keys()
            keys.sort()
            body+=''.join(['<tr><td>%s</td><td>%s</td></tr>\n'%(k,cgi.escape(repr(d[k]))) for k in keys])
            body+='</table><br><br>\n\n'
        return body
    def write(self,s):
        self.buffer.append(s)
    def echo(self,*s):
        self.buffer.extend([str(i) for i in s])
    def response(self):
        if not self.response_started:
            if not self.php:
                for k,v in self.FILES.items():
                    if v.has_key("tmp_file"):
                        try:
                            v["tmp_file"].close()
                        except OSError:
                            pass
                if self.response_gzencode and self.environ.get('HTTP_ACCEPT_ENCODING','').find('gzip')!=-1:
                    zbuf=StringIO.StringIO()
                    zfile=gzip.GzipFile(mode='wb', fileobj=zbuf)
                    zfile.write(''.join(self.buffer))
                    zfile.close()
                    zbuf=zbuf.getvalue()
                    self.buffer=[zbuf]
                    self.response_headers['Content-Encoding']="gzip"
                    self.response_headers['Content-Length']=str(len(zbuf))
                headers = self.response_headers.get()
                if isinstance(self.SESSION, QWebSession):
                    headers.extend(self.SESSION.session_get_headers())
                headers.extend([('Set-Cookie', self.response_cookies[i].OutputString()) for i in self.response_cookies])
                self.start_response(self.response_status, headers)
            self.response_started=True
        return self.buffer
    def __iter__(self):
        return self.response().__iter__()
    def http_redirect(self,url,permanent=1):
        if permanent:
            self.response_status="301 Moved Permanently"
        else:
            self.response_status="302 Found"
        self.response_headers["Location"]=url
    def http_404(self,msg="<h1>404 Not Found</h1>"):
        self.response_status="404 Not Found"
        if msg:
            self.write(msg)
    def http_download(self,fname,fstr,partial=0):
#       allow fstr to be a file-like object
#       if parital:
#           say accept ranages
#           parse range headers...
#           if range:
#               header("HTTP/1.1 206 Partial Content");
#               header("Content-Range: bytes $offset-".($fsize-1)."/".$fsize);
#               header("Content-Length: ".($fsize-$offset));
#               fseek($fd,$offset);
#           else:
        self.response_headers["Content-Type"]="application/octet-stream"
        self.response_headers["Content-Disposition"]="attachment; filename=\"%s\""%fname
        self.response_headers["Content-Transfer-Encoding"]="binary"
        self.response_headers["Content-Length"]="%d"%len(fstr)
        self.write(fstr)

#----------------------------------------------------------
# QWeb WSGI HTTP Server to run any WSGI app
# autorun, run an app as FCGI or CGI otherwise launch the server
#----------------------------------------------------------
class QWebWSGIHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def log_message(self,*p):
        if self.server.log:
            return BaseHTTPServer.BaseHTTPRequestHandler.log_message(self,*p)
    def address_string(self):
        return self.client_address[0]
    def start_response(self,status,headers):
        l=status.split(' ',1)
        self.send_response(int(l[0]),l[1])
        ctype_sent=0
        for i in headers:
            if i[0].lower()=="content-type":
                ctype_sent=1
            self.send_header(*i)
        if not ctype_sent:
            self.send_header("Content-type", "text/html")
        self.end_headers()
        return self.write
    def write(self,data):
        try:
            self.wfile.write(data)
        except (socket.error, socket.timeout),e:
            print e
    def bufferon(self):
        if not getattr(self,'wfile_buf',0):
            self.wfile_buf=1
            self.wfile_bak=self.wfile
            self.wfile=StringIO.StringIO()
    def bufferoff(self):
        if self.wfile_buf:
            buf=self.wfile
            self.wfile=self.wfile_bak
            self.write(buf.getvalue())
            self.wfile_buf=0
    def serve(self,type):
        path_info, parameters, query = urlparse.urlparse(self.path)[2:5]
        environ = {
            'wsgi.version':         (1,0),
            'wsgi.url_scheme':      'http',
            'wsgi.input':           self.rfile,
            'wsgi.errors':          sys.stderr,
            'wsgi.multithread':     0,
            'wsgi.multiprocess':    0,
            'wsgi.run_once':        0,
            'REQUEST_METHOD':       self.command,
            'SCRIPT_NAME':          '',
            'QUERY_STRING':         query,
            'CONTENT_TYPE':         self.headers.get('Content-Type', ''),
            'CONTENT_LENGTH':       self.headers.get('Content-Length', ''),
            'REMOTE_ADDR':          self.client_address[0],
            'REMOTE_PORT':          str(self.client_address[1]),
            'SERVER_NAME':          self.server.server_address[0],
            'SERVER_PORT':          str(self.server.server_address[1]),
            'SERVER_PROTOCOL':      self.request_version,
            # extention
            'FULL_PATH':            self.path,
            'qweb.mode':            'standalone',
        }
        if path_info:
            environ['PATH_INFO'] = urllib.unquote(path_info)
        for key, value in self.headers.items():
            environ['HTTP_' + key.upper().replace('-', '_')] = value
        # Hack to avoid may TCP packets
        self.bufferon()
        appiter=self.server.wsgiapp(environ, self.start_response)
        for data in appiter:
            self.write(data)
            self.bufferoff()
        self.bufferoff()
    def do_GET(self):
        self.serve('GET')
    def do_POST(self):
        self.serve('GET')
class QWebWSGIServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    """ QWebWSGIServer
        qweb_wsgi_autorun(wsgiapp,ip='127.0.0.1',port=8080,threaded=1)
        A WSGI HTTP server threaded or not and a function to automatically run your
        app according to the environement (either standalone, CGI or FastCGI).

        This feature is called QWeb autorun. If you want to  To use it on your
        application use the following lines at the end of the main application
        python file:

        if __name__ == '__main__':
            qweb.qweb_wsgi_autorun(your_wsgi_app)

        this function will select the approriate running mode according to the
        calling environement (http-server, FastCGI or CGI).
    """
    def __init__(self, wsgiapp, ip, port, threaded=1, log=1):
        BaseHTTPServer.HTTPServer.__init__(self, (ip, port), QWebWSGIHandler)
        self.wsgiapp = wsgiapp
        self.threaded = threaded
        self.log = log
    def process_request(self,*p):
        if self.threaded:
            return SocketServer.ThreadingMixIn.process_request(self,*p)
        else:
            return BaseHTTPServer.HTTPServer.process_request(self,*p)
def qweb_wsgi_autorun(wsgiapp,ip='127.0.0.1',port=8080,threaded=1,log=1,callback_ready=None):
    if sys.platform=='win32':
        fcgi=0
    else:
        fcgi=1
        sock = socket.fromfd(0, socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.getpeername()
        except socket.error, e:
            if e[0] == errno.ENOTSOCK:
                fcgi=0
    if fcgi or os.environ.has_key('REQUEST_METHOD'):
        import fcgi
        fcgi.WSGIServer(wsgiapp,multithreaded=False).run()
    else:
        if log:
            print 'Serving on %s:%d'%(ip,port)
        s=QWebWSGIServer(wsgiapp,ip=ip,port=port,threaded=threaded,log=log)
        if callback_ready:
            callback_ready()
        try:
            s.serve_forever()
        except KeyboardInterrupt,e:
            sys.excepthook(*sys.exc_info())

#----------------------------------------------------------
# Qweb Documentation
#----------------------------------------------------------
def qweb_doc():
    body=__doc__
    for i in [QWebXml ,QWebHtml ,QWebForm ,QWebURL ,qweb_control ,QWebRequest ,QWebSession ,QWebWSGIServer ,qweb_wsgi_autorun]:
        n=i.__name__
        d=i.__doc__
        body+='\n\n%s\n%s\n\n%s'%(n,'-'*len(n),d)
    return body

    print qweb_doc()

#

########NEW FILE########
__FILENAME__ = static
#!/usr/bin/python2.3
# vim:set noet ts=4 foldlevel=0:

# TODO support ranges

"""A QWeb Component to serve static content

Serve static contents, directories, zipfiles or python modules

"""

import calendar,cgi,md5,mimetypes,os,stat,sys,time,urllib,zipfile

def get_module_data(module,path):
	m=sys.modules[module]
	l=getattr(m,'__loader__',None)
	d=os.path.dirname(m.__file__)
	fname=os.path.join(d,path)
	if l:
		return l.get_data(fname)
	else:
		return file(fname).read()

def path_clean(path):
	path=path.replace('\\','/')
	pl=[i for i in path.split('/') if (i!='..' and i!='')]
	return '/'.join(pl)

def path_join(*l):
	return path_clean(os.path.join(*l))

class Entry:
	def  __init__(self,path,type,mtime,size,data=None):
		self.path=path
		self.name=os.path.basename(path)
		self.type=type
		self.mtime=mtime
		self.size=size
		self.data=data

class StaticBase:
	def __init__(self, urlroot="/", listdir=1):
		self.urlroot=urlroot
		self.listdir=listdir

		self.type_map=mimetypes.types_map.copy()
		self.type_map['.csv']='text/csv'
		self.type_map['.htm']='text/html; charset=UTF-8'
		self.type_map['.html']='text/html; charset=UTF-8'
		self.type_map['.svg']='image/svg+xml'
		self.type_map['.svgz']='image/svg+xml'
		self.gzencode={".css":1, ".js":1, ".htm":1, ".html":1, ".txt":1, ".xml":1}

	def serve_dir(self,req,path):
		if not req.PATH_INFO.endswith('/'):
			uri = req.FULL_PATH + '/'
			req.http_redirect(uri,1)
		else:
			l=self.fs_listdir(path)
			l.sort()
			body='<h1>Listing directory '+path+'</h1><a href="..">..</a><br>\n'
			for i in l:
				name=i.name
				if i.type=="dir":
					name+='/'
				body+='<a href="%s">%s</a><br>\n'%(name,name)
			return body
	def serve_file(self,req,path,entry):
		if req.SESSION!=None:
			req.SESSION.session_limit_cache=0
		lastmod=time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(entry.mtime))
		etag=md5.new(lastmod).hexdigest()[:16]
		req.response_headers['Last-Modified']=lastmod
		req.response_headers['ETag']=etag
		# cached output
		if lastmod==req.environ.get('HTTP_IF_MODIFIED_SINCE',"") or etag==req.environ.get('HTTP_IF_NONE_MATCH',""):
			req.response_status='304 Not Modified'
		# normal output
		else:
			ext = os.path.splitext(path)[1].lower()
			ctype = self.type_map.get(ext, 'application/octet-stream')
			req.response_headers['Content-Type']=ctype
			if entry.data!=None:
				f=entry.data
			else:
				f=self.fs_getfile(path)
				if not isinstance(f,str):
					f=f.read()
			if self.gzencode.has_key(ext):
				req.response_gzencode=1
			req.response_headers['Content-Length']=str(len(f))
			req.write(f)
	def process(self, req, inline=1):
		path=path_clean(req.PATH_INFO[len(self.urlroot):])
		e=self.fs_stat(path)
		if e:
			if e.type=="dir" and self.listdir:
				body=self.serve_dir(req, path)
				if inline:
					return {'head':"",'body':body}
				else:
					req.write(body)
			elif e.type=="file":
				self.serve_file(req,path,e)
		else:
			req.http_404()

class StaticDir(StaticBase):
	def __init__(self, urlroot="/", root=".", listdir=1):
		self.root=root
		StaticBase.__init__(self,urlroot,listdir)
	def fs_stat(self,path):
		fs_path = os.path.join(self.root,path)
		try:
			st = os.stat(fs_path)
			if stat.S_ISDIR(st.st_mode):
				type="dir"
			else:
				type="file"
			return Entry(path,type,st.st_mtime,st.st_size)
		except os.error:
			return None
	def fs_getfile(self,path):
		fs_path = os.path.join(self.root,path)
		return file(fs_path,'rb')
	def fs_listdir(self,path):
		fs_path = os.path.join(self.root,path)
		return [self.fs_stat(os.path.join(fs_path,i)) for i in os.listdir(fs_path)]

class StaticZip(StaticBase):
	def __init__(self, urlroot="/", zipname="",ziproot="/", listdir=1):
		StaticBase.__init__(self,urlroot,listdir)
		self.zipfile=zipfile.ZipFile(zipname)
		self.zipmtime=os.path.getmtime(zipname)
		self.ziproot=path_clean(ziproot)
		self.zipdir={}
		self.zipentry={}

		for zi in self.zipfile.infolist():
			if not zi.filename.endswith('/'):
				self.zipentry[zi.filename]=Entry(zi.filename,"file",self.zipmtime,zi.file_size)

		if listdir:
			# Build a directory index
			for k,v in self.zipentry.items():
				d=os.path.dirname(k)
				n=os.path.basename(k)
				if d in self.zipdir:
					self.zipdir[d][n]=v
				else:
					self.zipdir[d]={n:v}
				i=d
				while len(i):
					d=os.path.dirname(i)
					n=os.path.basename(i)
					e=Entry(i,"dir",self.zipmtime,0)
					if d in self.zipdir:
						self.zipdir[d][n]=e
					else:
						self.zipdir[d]={n:e}
					i=d
	def fs_stat(self,path):
		fs_path = path_join(self.ziproot,path)
		if fs_path in self.zipentry:
			return self.zipentry[fs_path]
		elif fs_path in self.zipdir:
			return Entry(path,"dir",self.zipmtime,0)
		else:
			return None
	def fs_getfile(self,path):
		fs_path = path_join(self.ziproot,path)
		return self.zipfile.read(fs_path)
	def fs_listdir(self,path):
		fs_path = path_join(self.ziproot,path)
		return self.zipdir[fs_path].values()

class StaticModule(StaticBase):
	def __init__(self, urlroot="/", module="", module_root="/", listdir=0):
		StaticBase.__init__(self,urlroot,listdir)
		self.module=module
		self.mtime=time.time()
		self.module_root=path_clean(module_root)
	def fs_stat(self,path):
		name=path_join(self.module_root,path)
		try:
			d=get_module_data(self.module,name)
			e=Entry(path,"file",self.mtime,len(d))
			e.data=d
			return e
		except IOError,e:
			return None

#----------------------------------------------------------
# OLD version: Pure WSGI
#----------------------------------------------------------
class WSGIStaticServe:
	def __init__(self, urlroot="/", root=".", listdir=1, banner=''):
		self.urlroot=urlroot
		self.root="."
		self.listdir=listdir
		self.banner=banner
		self.type_map=mimetypes.types_map.copy()
		self.type_map['.csv']='text/csv'
	def __call__(self, environ, start_response):
		pi=environ.get("PATH_INFO","")
		path = os.path.normpath("./" + pi[len(self.urlroot):] )
		if sys.platform=="win32":
			path="/".join(path.split('\\'))
		assert path[0]!='/'
		fullpath = os.path.join(self.root, path)
		if os.path.isdir(fullpath) and self.listdir:
			# redirects for directories
			if not pi.endswith('/'):
				uri = urllib.quote(environ["SCRIPT_NAME"] + environ["PATH_INFO"]) + '/'
				start_response("301 Moved Permanently", [("Content-type", "text/html"),("Location",uri)])
				return []
			body=self.banner
			body+='<h1>Listing directory '+path+'</h1><a href="..">..</a><br>\n'
			l=os.listdir(fullpath)
			l.sort()
			for i in l:
				if os.path.isdir(os.path.join(fullpath,i)):
					body+='<a href="%s/">%s/</a><br>\n'%(i,i)
				else:
					body+='<a href="%s">%s</a><br>\n'%(i,i)
			start_response("200 OK", [("Content-type", "text/html")])
			return [body]
		elif os.path.isfile(fullpath):
			f = open(fullpath,'rb')
			ext = os.path.splitext(fullpath)[1].lower()
			ctype = self.type_map.get(ext,'application/octet-stream')
			start_response("200 OK", [("Content-type", ctype)])
			return [f.read()]
		else:
			start_response("404 Not Found", [("Content-type", "text/html")])
			return ['<h1>404 Not Found</h1>']


#

########NEW FILE########
__FILENAME__ = tracsave
#!/usr/bin/python
# vim:set ts=4 et:
import sys, os, urllib, re, tempfile, urllib2
import mechanize

url=sys.argv[1]
base=os.path.basename(url)
urltxt='%s?format=txt'%url

orig=urllib2.urlopen(urltxt).read()
data=file(sys.argv[2]).read()

if data!=orig:

    # POST the file
    urledit='%s?action=edit'%url

    br = mechanize.Browser()
    br.set_handle_robots(False)
    br.add_password("http://antony.lesuisse.org/", "ticket", "nospam")
    br.open("http://antony.lesuisse.org/qweb/trac/login")
    br.open(urledit)
    editpage = br.response().read()
    mo=re.search('name="version" value="([^"]+)"',editpage)
    if mo:
        version=mo.group(1)
        post=urllib.urlencode({
            "action":"edit",
            "text":data,
            "version":version,
            "save":"Submit change",
            "author":"anonymous",
            "comment":"" } )
        br.open(url,post)
        br.response().read()
        print "%s saved."%url




########NEW FILE########
__FILENAME__ = vimtrac
#!/usr/bin/python
# vim:set ts=4 et:
import sys, os, urllib, re, tempfile, urllib2

if len(sys.argv)<2:
    print "usage: vimtrac.py http://hostname/trac/wiki/WikiStart"
    sys.exit()

url=sys.argv[1]
base=os.path.basename(url)
urltxt='%s?format=txt'%url


orig=urllib2.urlopen(urltxt).read()
f=tempfile.NamedTemporaryFile()
f.write(orig)
f.flush()
os.system("%s %s" % (os.getenv("EDITOR", "vi"), f.name))

f.seek(0)
data=f.read()
if data!=orig:

    # POST the file
    urledit='%s?action=edit'%url
    editpage=urllib2.urlopen(urledit).read()

    mo=re.search('name="version" value="([^"]+)"',editpage)
    if mo:
        version=mo.group(1)
        post=urllib.urlencode({
            "action":"edit",
            "text":data,
            "version":version,
            "save":"Submit change",
            "author":"anonymous",
            "comment":"" } )
        urllib2.urlopen(url,post).read()
        print "%s saved."%url




########NEW FILE########
