__FILENAME__ = backward_compatibility_test
# -*- coding: utf-8 -*-
import sys
import pyffmpeg

stream = pyffmpeg.VideoStream()
stream.open(sys.argv[1])
image = stream.GetFrameNo(0)
image.save('firstframe.png')
########NEW FILE########
__FILENAME__ = fast_keyframes_extraction
# -*- coding: utf-8 -*-
## Simple demo for pyffmpegb 
## 
## Copyright -- Bertrand Nouvel 2009

## import your modules

from pyffmpeg import *
from PyQt4 import QtCore
from PyQt4 import QtGui

import sys, numpy
#import alsaaudio

try:
    LazyDisplayQt__imgconvarray={
                      1:QtGui.QImage.Format_Indexed8,
                      3:QtGui.QImage.Format_RGB888,
                      4:QtGui.QImage.Format_RGB32
                      }
except:
    LazyDisplayQt__imgconvarray={
                      1:QtGui.QImage.Format_Indexed8,
                      4:QtGui.QImage.Format_RGB32
                      }

qapp = QtGui.QApplication(sys.argv)
qapp.processEvents()

class LazyDisplayQt(QtGui.QMainWindow):
        imgconvarray=LazyDisplayQt__imgconvarray
        def __init__(self, *args):
            QtGui.QMainWindow.__init__(self, *args)
            self._i=numpy.zeros((1,1,4),dtype=numpy.uint8)
            self.i=QtGui.QImage(self._i.data,self._i.shape[1],self._i.shape[0],self.imgconvarray[self._i.shape[2]])
            self.show()
        def __del__(self):
            self.hide()
        def f(self,thearray):
            self._i=thearray.astype(numpy.uint8).copy('C')
            self.i=QtGui.QImage(self._i.data,self._i.shape[1],self._i.shape[0],self.imgconvarray[self._i.shape[2]])
            self.update()
            qapp.processEvents()
        def paintEvent(self, ev):
            self.p = QtGui.QPainter()
            self.p.begin(self)
            self.p.drawImage(QtCore.QRect(0,0,self.width(),self.height()),
                             self.i,
                             QtCore.QRect(0,0,self.i.width(),self.i.height()))
            self.p.end()


TS_VIDEO_RGB24={ 'video1':(0, -1, {'pixel_format':PixelFormats.RGB24,'videoframebanksz':1, 'skip_frame':32})}#, 'audio1':(1,-1,{}) }
TS_VIDEO_BGR24={ 'video1':(0, -1, {'pixel_format':PixelFormats.BGR24,'videoframebanksz':1, 'skip_frame':32})}#, 'audio1':(1,-1,{})}
TS_VIDEO_GRAY8={ 'video1':(0, -1, {'pixel_format':PixelFormats.GRAY8,'videoframebanksz':1, 'skip_frame':32})}#, 'audio1':(1,-1,{})}


## create the reader object
mp=FFMpegReader()


## open an audio video file
vf=sys.argv[1]
mp.open(vf,TS_VIDEO_RGB24)
tracks=mp.get_tracks()

## connect video and audio to their respective device
ld=LazyDisplayQt()
tt=0

def obs(x):
   global tt
   #print tracks[0].get_current_frame_type()
   #print tracks[0].get_current_frame_pts()/1000000
   tt+=1
   if (tt%100==0):
     print tracks[0].get_cur_pts()/1000000
     if (x.shape[2]==1):
       ld.f(x.reshape(x.shape[0],x.shape[1],1).repeat(3,axis=2))
     else:
       ld.f(x)
   
 
tracks[0].set_observer(obs)

import time
print time.clock()
dur=mp.duration()/1000000
print "Duration = ",dur
try:
   mp.run()
except Exception, e:
  print "Exception e=", e
  print "Processing time=",time.clock()
  print tt," keyframes"
  print (dur*30.)/tt ," frames per keyframe"
  print (dur)/time.clock() ," times faster than rt"



########NEW FILE########
__FILENAME__ = motionvectors
# -*- coding: utf-8 -*-
## Simple demo for pyffmpegb 
## 
## Copyright -- Bertrand Nouvel 2009

## import your modules

from pyffmpeg import *
from PyQt4 import QtCore
from PyQt4 import QtGui

import sys, numpy

  
try:
    LazyDisplayQt__imgconvarray={
                      1:QtGui.QImage.Format_Indexed8,
                      3:QtGui.QImage.Format_RGB888,
                      4:QtGui.QImage.Format_RGB32
                      }
except:
    LazyDisplayQt__imgconvarray={
                      1:QtGui.QImage.Format_Indexed8,
                      4:QtGui.QImage.Format_RGB32
                      }

qapp = QtGui.QApplication(sys.argv)
qapp.processEvents()


class LazyDisplayQt(QtGui.QMainWindow):
        imgconvarray=LazyDisplayQt__imgconvarray
        def __init__(self, *args):
            QtGui.QMainWindow.__init__(self, *args)
            self._i=numpy.zeros((1,1,4),dtype=numpy.uint8)
            self.i=QtGui.QImage(self._i.data,self._i.shape[1],self._i.shape[0],self.imgconvarray[self._i.shape[2]])
            self.show()
        def __del__(self):
            self.hide()
        def f(self,thearray):
            #print "ARRAY",
            #print thearray
            self._i=thearray.astype(numpy.uint8).copy('C')
            self.i=QtGui.QImage(self._i.data,self._i.shape[1],self._i.shape[0],self.imgconvarray[self._i.shape[2]])
            self.update()
            qapp.processEvents()
        def paintEvent(self, ev):
            self.p = QtGui.QPainter()
            self.p.begin(self)
            self.p.drawImage(QtCore.QRect(0,0,self.width(),self.height()),
                             self.i,
                             QtCore.QRect(0,0,self.i.width(),self.i.height()))
            self.p.end()


TS_VIDEO_RGB24={ 'video1':(0, -1, {'pixel_format':PixelFormats.RGB24,'with_motion_vectors':1})}
TS_VIDEO_BGR24={ 'video1':(0, -1, {'pixel_format':PixelFormats.BGR24,'with_motion_vectors':1})}


## create the reader object

mp=FFMpegReader(0,False)


## open an audio video file

vf=sys.argv[1]
#vf="/home/tranx/conan1.flv"
sys.stderr.write("opening\n")
mp.open(vf,TS_VIDEO_RGB24)
print "opened"
tracks=mp.get_tracks()


## connect video and audio to their respective device

ld=LazyDisplayQt()
tracks[0].set_observer(ld.f)

print "duration=",mp.duration()

tracks[0].seek_to_seconds(10)
print tracks[0].get_current_frame()

## play the movie !

#mp.run()



########NEW FILE########
__FILENAME__ = multiplayer
# -*- coding: utf-8 -*-
import numpy,random,re,sys,os
from pyffmpeg import *

from PyQt4 import QtCore
from PyQt4 import QtGui


try:
    LazyDisplayQt__imgconvarray={
                      1:QtGui.QImage.Format_Indexed8,
                      3:QtGui.QImage.Format_RGB888,
                      4:QtGui.QImage.Format_RGB32
                      }
except:
    LazyDisplayQt__imgconvarray={
                      1:QtGui.QImage.Format_Indexed8,
                      4:QtGui.QImage.Format_RGB32
                      }

qapp = QtGui.QApplication(sys.argv)
qapp.processEvents()


class LazyDisplayQt(QtGui.QMainWindow):
        imgconvarray=LazyDisplayQt__imgconvarray
        def __init__(self, *args):
            QtGui.QMainWindow.__init__(self, *args)
            self._i=numpy.zeros((1,1,4),dtype=numpy.uint8)
            self.i=QtGui.QImage(self._i.data,self._i.shape[1],self._i.shape[0],self.imgconvarray[self._i.shape[2]])
            self.show()
        def __del__(self):
            self.hide()
        def f(self,thearray):
            self._i=thearray.astype(numpy.uint8).copy('C')
            self.i=QtGui.QImage(self._i.data,self._i.shape[1],self._i.shape[0],self.imgconvarray[self._i.shape[2]])
            self.update()
            qapp.processEvents()
        def paintEvent(self, ev):
            self.p = QtGui.QPainter()
            self.p.begin(self)
            self.p.drawImage(QtCore.QRect(0,0,self.width(),self.height()),
                             self.i,
                             QtCore.QRect(0,0,self.i.width(),self.i.height()))
            self.p.end()


# select your database
directory=sys.argv[1]

# instantiate the display
ld=LazyDisplayQt()


# set parameters
display_sz=(600,800)
n=(len(sys.argv)>2) and int(sys.argv[2]) or 8
subdisplay_nb=(n,n)


#compute the size of each video
shp=(display_sz[0]//subdisplay_nb[0], display_sz[1]//subdisplay_nb[1])

# initials buffers
img=numpy.zeros(display_sz+(3,),dtype=numpy.uint8)
subdisplay=numpy.zeros(subdisplay_nb,dtype=object)

# look for videofiles
files=filter(lambda x:re.match("(.*).(mpg|avi|flv)",x),os.listdir(directory))

# specify to open only video at the correct size
TS={ 'video1':(0, -1, {'pixel_format':PixelFormats.RGB24,'videoframebanksz':1, 'dest_width':shp[1], 'dest_height':shp[0] })}


# do play, and reinstantiate players in case of error
while True:
  ld.f(img)
  for xx in numpy.ndindex(subdisplay_nb):
    try:
      subdisplay[xx].step()
    except:
        mp=FFMpegReader()
        maxtries=4
        def do_display(subimg):
          x=shp[1]*xx[1]
          y=shp[0]*xx[0]
          dy,dx=shp
          img[y:(y+dy),x:(x+dx) ]=subimg

        while (maxtries>0):
          try:
             mp.open(directory+"/"+random.choice(files),TS)
             mp.seek_to(random.randint(1,1024))
             mp.get_tracks()[0].set_observer(do_display)
             mp.step()
             maxtries=0
          except:
             maxtries-=1
        subdisplay[xx]=mp
        




########NEW FILE########
__FILENAME__ = playvideo_gtk_oss
# -*- coding: utf-8 -*-
## Simple demo for pyffmpegb and pygtk
## 
## Copyright -- Sebastien Campion

## import your modules

import sys, numpy, time, StringIO, Image, threading
from pyffmpeg import *

try:
  import ossaudiodev as oss
except:
  import oss
  
import pygtk, gtk
pygtk.require('2.0')
gtk.gdk.threads_init()




class play(threading.Thread):
    def run(self):
      global mp
      mp.run()


class pyffplay:
    def __init__(self,width,height):
        self.builder = gtk.Builder()
        self.builder.add_from_file("example2.xml")
        self.window = self.builder.get_object("window")
        self.screen = self.builder.get_object("screen")
        self.builder.connect_signals(self)
        self.size = (width,height)
        
    def image2pixbuf(self,im):
      """
      convert a PIL image to pixbuff
      """
      file1 = StringIO.StringIO()  
      im.save(file1, "ppm")  
      contents = file1.getvalue()  
      file1.close()  
      loader = gtk.gdk.PixbufLoader("pnm")  
      loader.write(contents, len(contents))  
      pixbuf = loader.get_pixbuf()  
      loader.close()  
      return pixbuf  
   

    def displayframe(self,thearray):
      """
      pyffmpeg callback
      """
      _i = thearray.astype(numpy.uint8).copy('C')
      _i_height=_i.shape[0]
      _i_width = _i.shape[1]
     
      frame = Image.fromstring("RGB",(_i_width,_i_height),_i.data)
      frame = frame.resize(self.size)
      self.screen.set_from_pixbuf(self.image2pixbuf(frame))

    def on_play_clicked(self,widget):
      play().start()
    
 


# create a pygtk window
pyff = pyffplay(320,240)
pyff.window.show_all()

TS_VIDEO_RGB24={ 'video1':(0, -1, {'pixel_format':PixelFormats.RGB24}), 'audio1':(1,-1,{})}
TS_VIDEO_BGR24={ 'video1':(0, -1, {'pixel_format':PixelFormats.BGR24}), 'audio1':(1,-1,{})}


## create the reader object
mp=FFMpegReader()

## open an audio video file
vf=sys.argv[1]


mp.open(vf,TS_VIDEO_RGB24)
tracks=mp.get_tracks()


## connect video and audio to their respective device
tracks[0].set_observer(pyff.displayframe)

ao=oss.open('w')

ao.speed(tracks[1].get_samplerate())
ao.setfmt(oss.AFMT_S16_LE)
ao.channels(tracks[1].get_channels())
tracks[1].set_observer(lambda x:ao.write(x[0].data))
tracks[0].seek_to_seconds(10)


gtk.main()




########NEW FILE########
__FILENAME__ = playvideo_nosound
# -*- coding: utf-8 -*-
## Simple demo for pyffmpegb 
## 
## Copyright -- Bertrand Nouvel 2009

## import your modules

from pyffmpeg import *
from PyQt4 import QtCore
from PyQt4 import QtGui

import sys, numpy

  
try:
    LazyDisplayQt__imgconvarray={
                      1:QtGui.QImage.Format_Indexed8,
                      3:QtGui.QImage.Format_RGB888,
                      4:QtGui.QImage.Format_RGB32
                      }
except:
    LazyDisplayQt__imgconvarray={
                      1:QtGui.QImage.Format_Indexed8,
                      4:QtGui.QImage.Format_RGB32
                      }

qapp = QtGui.QApplication(sys.argv)
qapp.processEvents()


class LazyDisplayQt(QtGui.QMainWindow):
        imgconvarray=LazyDisplayQt__imgconvarray
        def __init__(self, *args):
            QtGui.QMainWindow.__init__(self, *args)
            self._i=numpy.zeros((1,1,4),dtype=numpy.uint8)
            self.i=QtGui.QImage(self._i.data,self._i.shape[1],self._i.shape[0],self.imgconvarray[self._i.shape[2]])
            self.show()
        def __del__(self):
            self.hide()
        def f(self,thearray):
            #print "ARRAY",
            #print thearray
            self._i=thearray.astype(numpy.uint8).copy('C')
            self.i=QtGui.QImage(self._i.data,self._i.shape[1],self._i.shape[0],self.imgconvarray[self._i.shape[2]])
            self.update()
            qapp.processEvents()
        def paintEvent(self, ev):
            self.p = QtGui.QPainter()
            self.p.begin(self)
            self.p.drawImage(QtCore.QRect(0,0,self.width(),self.height()),
                             self.i,
                             QtCore.QRect(0,0,self.i.width(),self.i.height()))
            self.p.end()


TS_VIDEO_RGB24={ 'video1':(0, -1, {'pixel_format':PixelFormats.RGB24})}
TS_VIDEO_BGR24={ 'video1':(0, -1, {'pixel_format':PixelFormats.BGR24})}


## create the reader object

mp=FFMpegReader(0,False)


## open an audio video file

vf=sys.argv[1]
#vf="/home/tranx/conan1.flv"
sys.stderr.write("opening\n")
mp.open(vf,TS_VIDEO_RGB24)
print "opened"
tracks=mp.get_tracks()


## connect video and audio to their respective device

ld=LazyDisplayQt()
tracks[0].set_observer(ld.f)

print "duration=",mp.duration()

#tracks[0].seek_to_seconds(10)


## play the movie !

mp.run()



########NEW FILE########
__FILENAME__ = playvideo_qt_alsa
# -*- coding: utf-8 -*-
## Simple demo for pyffmpegb 
## 
## Copyright -- Bertrand Nouvel 2009

## import your modules

from pyffmpeg import *
from PyQt4 import QtCore
from PyQt4 import QtGui

import sys, numpy, time
import alsaaudio

try:
    LazyDisplayQt__imgconvarray={
                      1:QtGui.QImage.Format_Indexed8,
                      3:QtGui.QImage.Format_RGB888,
                      4:QtGui.QImage.Format_RGB32
                      }
except:
    LazyDisplayQt__imgconvarray={
                      1:QtGui.QImage.Format_Indexed8,
                      4:QtGui.QImage.Format_RGB32
                      }

qapp = QtGui.QApplication(sys.argv)
qapp.processEvents()

class AlsaSoundLazyPlayer:
    def __init__(self,rate=44100,channels=2,fps=25):
        self.fps=fps
        self._rate=rate
        self._channels=channels
        self._d = alsaaudio.PCM()
        self._d.setchannels(channels)
        self._d.setformat(alsaaudio.PCM_FORMAT_S16_LE)
        self._d.setperiodsize((rate*channels)//fps)
        self._d.setrate(rate)
    def push_nowait(self,stamped_buffer):
        self._d.write(stamped_buffer[0].data)
    def push_wait(self,stamped_buffer):
        self._d.write(stamped_buffer[0].data)
        time.sleep(0.96/self.fps)


class LazyDisplayQt(QtGui.QMainWindow):
        imgconvarray=LazyDisplayQt__imgconvarray
        def __init__(self, *args):
            QtGui.QMainWindow.__init__(self, *args)
            self._i=numpy.zeros((1,1,4),dtype=numpy.uint8)
            self.i=QtGui.QImage(self._i.data,self._i.shape[1],self._i.shape[0],self.imgconvarray[self._i.shape[2]])
            self.show()
        def __del__(self):
            self.hide()
        def f(self,thearray):
            self._i=thearray.astype(numpy.uint8).copy('C')
            self.i=QtGui.QImage(self._i.data,self._i.shape[1],self._i.shape[0],self.imgconvarray[self._i.shape[2]])
            self.update()
            qapp.processEvents()
        def paintEvent(self, ev):
            self.p = QtGui.QPainter()
            self.p.begin(self)
            self.p.drawImage(QtCore.QRect(0,0,self.width(),self.height()),
                             self.i,
                             QtCore.QRect(0,0,self.i.width(),self.i.height()))
            self.p.end()


TS_VIDEO_RGB24={ 'video1':(0, -1, {'pixel_format':PixelFormats.RGB24}), 'audio1':(1,-1,{})}
TS_VIDEO_BGR24={ 'video1':(0, -1, {'pixel_format':PixelFormats.BGR24}), 'audio1':(1,-1,{})}


## create the reader object
mp=FFMpegReader(0,False)


## open an audio video file
vf=sys.argv[1]
mp.open(vf,TS_VIDEO_RGB24)
tracks=mp.get_tracks()

## connect video and audio to their respective device
ld=LazyDisplayQt()
tracks[0].set_observer(ld.f)

ap=AlsaSoundLazyPlayer(tracks[1].get_samplerate(),tracks[1].get_channels(),tracks[0].get_fps())
tracks[1].set_observer(ap.push_wait)

#tracks[0].seek_to_seconds(10)
## play the movie !

mp.run()



########NEW FILE########
__FILENAME__ = playvideo_qt_oss
# -*- coding: utf-8 -*-
## Simple demo for pyffmpegb
##
## Copyright -- Bertrand Nouvel 2009

## import your modules

from pyffmpeg import *
from PyQt4 import QtCore
from PyQt4 import QtGui

import sys, numpy
try:
    import ossaudiodev as oss
except:
    import oss

try:
    LazyDisplayQt__imgconvarray={
                      1:QtGui.QImage.Format_Indexed8,
                      3:QtGui.QImage.Format_RGB888,
                      4:QtGui.QImage.Format_RGB32
                      }
except:
    LazyDisplayQt__imgconvarray={
                      1:QtGui.QImage.Format_Indexed8,
                      4:QtGui.QImage.Format_RGB32
                      }

qapp = QtGui.QApplication(sys.argv)
qapp.processEvents()


class LazyDisplayQt(QtGui.QMainWindow):
    imgconvarray=LazyDisplayQt__imgconvarray
    def __init__(self, *args):
        QtGui.QMainWindow.__init__(self, *args)
        self._i=numpy.zeros((1,1,4),dtype=numpy.uint8)
        self.i=QtGui.QImage(self._i.data,self._i.shape[1],self._i.shape[0],self.imgconvarray[self._i.shape[2]])
        self.show()
    def __del__(self):
        self.hide()
    def f(self,thearray):
        self._i=thearray.astype(numpy.uint8).copy('C')
        self.i=QtGui.QImage(self._i.data,self._i.shape[1],self._i.shape[0],self.imgconvarray[self._i.shape[2]])
        self.update()
        qapp.processEvents()
    def paintEvent(self, ev):
        self.p = QtGui.QPainter()
        self.p.begin(self)
        self.p.drawImage(QtCore.QRect(0,0,self.width(),self.height()),
                         self.i,
                         QtCore.QRect(0,0,self.i.width(),self.i.height()))
        self.p.end()


TS_VIDEO_RGB24={ 'video1':(0, -1, {'pixel_format':PixelFormats.RGB24}), 'audio1':(1,-1,{})}
TS_VIDEO_BGR24={ 'video1':(0, -1, {'pixel_format':PixelFormats.BGR24}), 'audio1':(1,-1,{})}


## create the reader object

mp=FFMpegReader()


## open an audio video file

vf=sys.argv[1]
#vf="/home/tranx/conan1.flv"
mp.open(vf,TS_VIDEO_RGB24)
tracks=mp.get_tracks()


## connect video and audio to their respective device

ld=LazyDisplayQt()
tracks[0].set_observer(ld.f)

ao=oss.open_audio()
ao.stereo(1)
ao.speed(tracks[1].get_samplerate())
ao.format(oss.AFMT_S16_LE)
tracks[1].set_observer(lambda x:ao.write(x[0].data))
tracks[0].seek_to_seconds(10)
ao.channels(tracks[1].get_channels())


## play the movie !

mp.run()

########NEW FILE########
__FILENAME__ = seek_test
# -*- coding: utf-8 -*-
import sys
import pyffmpeg

reader = pyffmpeg.FFMpegReader(False)
reader.open(sys.argv[1],pyffmpeg.TS_VIDEO_PIL)
vt=reader.get_tracks()[0]
print dir(vt)
nframes=31
try:
  rdrdur=reader.duration()
  rdrdurtime=reader.duration_time()
except:
  print "no duration information in reader"
try:
  cdcdur=vt.duration()
  cdcdurtime=vt.duration_time()
  mt=max(cdcdurtime,rdrdurtime)
  print rdrdurtime, cdcdurtime
  print "FPS=",vt.get_fps()
  nframes=min(mt*vt.get_fps(),1000)
  print "NFRAMES= (max=1000)",nframes
except KeyError: 
  print "no duration information in track"
for i in range(nframes,0,-1):
  try:
    vt.seek_to_frame(i)
    image=vt.get_current_frame()[2]
    image.save('frame-%04d.png'%(i,))
  except:
    print "missing frame %d"%(i,)

########NEW FILE########
__FILENAME__ = spectrogram
# -*- coding: utf-8 -*-
###############################################################
###############################################################
###############################################################
# Example of spectrogram computations from sound/video file 
###############################################################

import sys
import numpy 
import pylab
import Image

def NumPy2PIL(input):
    """Converts a numpy array to a PIL image.

    Supported input array layouts:
       2 dimensions of numpy.uint8
       3 dimensions of numpy.uint8
       2 dimensions of numpy.float32
    """
    if not isinstance(input, numpy.ndarray):
        raise TypeError, 'Must be called with numpy.ndarray!'
    # Check the number of dimensions of the input array
    ndim = input.ndim
    if not ndim in (2, 3):
        raise ValueError, 'Only 2D-arrays and 3D-arrays are supported!'
    if ndim == 2:
        channels = 1
    else:
        channels = input.shape[2]
    # supported modes list: [(channels, dtype), ...]
    modes_list = [(1, numpy.uint8), (3, numpy.uint8), (1, numpy.float32), (4,numpy.uint8)]
    mode = (channels, input.dtype)
    if not mode in modes_list:
        raise ValueError, 'Unknown or unsupported input mode'
    return Image.fromarray(input)



def hamming(lw):
   return 0.54-0.46*numpy.cos(numpy.pi*2.*numpy.arange(0,1.,1./lw))


from pyffmpeg import *
frate=44100.
freq=8
df=2048
do=df-(df/freq)
di=df-do
nx=df//di

TS_AUDIO={ 'audio1':(1, -1, {'hardware_queue_len':1000,'dest_frame_size':df, 'dest_frame_overlap':do} )}

class Observer():
  def __init__(self):
     self.ctr=0
     self.ark=[]
     self.arp=[]     
  def observe(self,x):
     self.ctr+=1
     fftsig=numpy.fft.fft(x[0].mean(axis=1)/32768.)
     spectra=numpy.roll(fftsig,fftsig.shape[0]//2,axis=0)
     spect=(20*numpy.log10(0.0001+numpy.abs(spectra)))*4
     specp=numpy.angle(spectra)
#     print spect.min() , spect.max()
     spect=spect.clip(0,255)
     spect=spect.astype(numpy.uint8)
     self.arp.append(((specp/numpy.pi)*127).astype(numpy.int8))
     self.ark.append(spect.copy('C'))

observer=Observer()


for f in sys.argv[1:]:
  observer.ark=[]
  print "processing ",f
  rdr=FFMpegReader()
  rdr.open(f,track_selector=TS_AUDIO)    
  track=rdr.get_tracks()
  track[0].set_observer(observer.observe)
  try:
    rdr.run()
  except IOError:
    pass
  arim=numpy.vstack(observer.ark)
  arip=numpy.vstack(observer.arp) 
  for i in range(0,arim.shape[0],5000):
     xcmap=(pylab.cm.hsv(arip[i:(i+5000),:].astype(numpy.float)/255.)*arim[i:(i+5000),:].reshape(arim[i:(i+5000),:].shape+(1,)).repeat(4,axis=2)).astype(numpy.uint8)[:,:,:3].copy('C')
     NumPy2PIL(xcmap).save("spectrogram-%s-%d.png"%(f.split('/')[-1].split('.')[0] ,i,))

########NEW FILE########
