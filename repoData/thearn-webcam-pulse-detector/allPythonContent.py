__FILENAME__ = get_pulse
from lib.device import Camera
from lib.processors import findFaceGetPulse
from lib.interface import plotXY, imshow, waitKey,destroyWindow, moveWindow
import numpy as np      
import datetime

class getPulseApp(object):
    """
    Python application that finds a face in a webcam stream, then isolates the
    forehead.

    Then the average green-light intensity in the forehead region is gathered 
    over time, and the detected person's pulse is estimated.
    """
    def __init__(self):
        #Imaging device - must be a connected camera (not an ip camera or mjpeg
        #stream)
        self.camera = Camera(camera=0) #first camera by default
        self.w,self.h = 0,0
        self.pressed = 0
        #Containerized analysis of recieved image frames (an openMDAO assembly)
        #is defined next.

        #This assembly is designed to handle all image & signal analysis,
        #such as face detection, forehead isolation, time series collection,
        #heart-beat detection, etc. 

        #Basically, everything that isn't communication
        #to the camera device or part of the GUI
        self.processor = findFaceGetPulse(bpm_limits = [50,160],
                                          data_spike_limit = 2500.,
                                          face_detector_smoothness = 10.)  

        #Init parameters for the cardiac data plot
        self.bpm_plot = False
        self.plot_title = "Cardiac info - raw signal, filtered signal, and PSD"

        #Maps keystrokes to specified methods
        #(A GUI window must have focus for these to work)
        self.key_controls = {"s" : self.toggle_search,
                             "d" : self.toggle_display_plot,
                             "f" : self.write_csv}
        
    def write_csv(self):
        """
        Writes current data to a csv file
        """
        bpm = " " + str(int(self.processor.measure_heart.bpm))
        fn = str(datetime.datetime.now()).split(".")[0] + bpm + " BPM.csv"
        
        data = np.array([self.processor.fft.times, 
                         self.processor.fft.samples]).T
        np.savetxt(fn, data, delimiter=',')
        


    def toggle_search(self):
        """
        Toggles a motion lock on the processor's face detection component.

        Locking the forehead location in place significantly improves
        data quality, once a forehead has been sucessfully isolated. 
        """
        state = self.processor.find_faces.toggle()
        if not state:
        	self.processor.fft.reset()
        print "face detection lock =",not state

    def toggle_display_plot(self):
        """
        Toggles the data display.
        """
        if self.bpm_plot:
            print "bpm plot disabled"
            self.bpm_plot = False
            destroyWindow(self.plot_title)
        else:
            print "bpm plot enabled"
            self.bpm_plot = True
            self.make_bpm_plot()
            moveWindow(self.plot_title, self.w,0)

    def make_bpm_plot(self):
        """
        Creates and/or updates the data display
        """
        plotXY([[self.processor.fft.times, 
                 self.processor.fft.samples],
                [self.processor.fft.even_times[4:-4], 
                 self.processor.measure_heart.filtered[4:-4]],
                [self.processor.measure_heart.freqs, 
                 self.processor.measure_heart.fft]], 
               labels = [False, False, True],
               showmax = [False,False, "bpm"], 
               label_ndigits = [0,0,0],
               showmax_digits = [0,0,1],
               skip = [3,3,4],
               name = self.plot_title, 
               bg = self.processor.grab_faces.slices[0])

    def key_handler(self):    
        """
        Handle keystrokes, as set at the bottom of __init__()

        A plotting or camera frame window must have focus for keypresses to be
        detected.
        """

        self.pressed = waitKey(10) & 255 #wait for keypress for 10 ms
        if self.pressed == 27: #exit program on 'esc'
            print "exiting..."
            self.camera.cam.release()
            exit()

        for key in self.key_controls.keys():
            if chr(self.pressed) == key:
                self.key_controls[key]()

    def main_loop(self):
        """
        Single iteration of the application's main loop.
        """
        # Get current image frame from the camera
        frame = self.camera.get_frame()
        self.h,self.w,_c = frame.shape
        

        #display unaltered frame
        #imshow("Original",frame)

        #set current image frame to the processor's input
        self.processor.frame_in = frame
        #process the image frame to perform all needed analysis
        self.processor.run()
        #collect the output frame for display
        output_frame = self.processor.frame_out

        #show the processed/annotated output frame
        imshow("Processed",output_frame)

        #create and/or update the raw data display if needed
        if self.bpm_plot:
            self.make_bpm_plot()

        #handle any key presses
        self.key_handler()

if __name__ == "__main__":
    App = getPulseApp()
    while True:
        App.main_loop()

########NEW FILE########
__FILENAME__ = get_pulse_ipcam
from lib.device import Camera, ipCamera
from lib.processors import findFaceGetPulse
from lib.interface import plotXY, imshow, waitKey,destroyWindow, moveWindow, resize
import numpy as np      


class getPulseApp(object):
    """
    Python application that finds a face in a webcam stream, then isolates the
    forehead.
    
    Then the average green-light intensity in the forehead region is gathered 
    over time, and the detected person's pulse is estimated.
    """
    def __init__(self, ip, user, password):
        #Imaging device - must be a connected camera (not an ip camera or mjpeg
        #stream)
        
        self.camera = ipCamera(ip,
                       user=user, 
                       password=password)
        self.w,self.h = 0,0
        
        #Containerized analysis of recieved image frames (an openMDAO assembly)
        #is defined next.
        
        #This assembly is designed to handle all image & signal analysis,
        #such as face detection, forehead isolation, time series collection,
        #heart-beat detection, etc. 
        
        #Basically, everything that isn't communication
        #to the camera device or part of the GUI
        self.processor = findFaceGetPulse(bpm_limits = [50,160],
                                          data_spike_limit = 25.,
                                          face_detector_smoothness = 10.)  
        
        #Init parameters for the cardiac data plot
        self.bpm_plot = False
        self.plot_title = "Cardiac info - raw signal, filtered signal, and PSD"
        
        #Maps keystrokes to specified methods
        #(A GUI window must have focus for these to work)
        self.key_controls = {"s" : self.toggle_search,
                        "d" : self.toggle_display_plot}
        
    
    def toggle_search(self):
        """
        Toggles a motion lock on the processor's face detection component.
        
        Locking the forehead location in place significantly improves
        data quality, once a forehead has been sucessfully isolated. 
        """
        state = self.processor.find_faces.toggle()
        print "face detection lock =",not state
    
    def toggle_display_plot(self):
        """
        Toggles the data display.
        """
        if self.bpm_plot:
            print "bpm plot disabled"
            self.bpm_plot = False
            destroyWindow(self.plot_title)
        else:
            print "bpm plot enabled"
            self.bpm_plot = True
            self.make_bpm_plot()
            moveWindow(self.plot_title, self.w,0)
    
    def make_bpm_plot(self):
        """
        Creates and/or updates the data display
        """
        plotXY([[self.processor.fft.times, 
                 self.processor.fft.samples],
            [self.processor.fft.even_times[4:-4], 
             self.processor.measure_heart.filtered[4:-4]],
                [self.processor.measure_heart.freqs, 
                 self.processor.measure_heart.fft]], 
               labels = [False, False, True],
               showmax = [False,False, "bpm"], 
               label_ndigits = [0,0,0],
               showmax_digits = [0,0,1],
               skip = [3,3,4],
               name = self.plot_title, 
               bg = self.processor.grab_faces.slices[0])
    
    def key_handler(self):    
        """
        Handle keystrokes, as set at the bottom of __init__()
        
        A plotting or camera frame window must have focus for keypresses to be
        detected.
        """
        pressed = waitKey(10) & 255 #wait for keypress for 10 ms
        if pressed == 27: #exit program on 'esc'
            quit()
        for key in self.key_controls.keys():
            if chr(pressed) == key:
                self.key_controls[key]()
                
    def main_loop(self):
        """
        Single iteration of the application's main loop.
        """
        # Get current image frame from the camera
        frame = self.camera.get_frame()
        self.h,self.w,_c = frame.shape
        
        #display unaltered frame
        #imshow("Original",frame)
        
        #set current image frame to the processor's input
        self.processor.frame_in = frame
        #process the image frame to perform all needed analysis
        self.processor.run()
        #collect the output frame for display
        output_frame = self.processor.frame_out
        
        #show the processed/annotated output frame
        
        output_frame = resize(output_frame, (640,480))
        imshow("Processed",output_frame)
        
        #create and/or update the raw data display if needed
        if self.bpm_plot:
            self.make_bpm_plot()
        
        #handle any key presses
        self.key_handler()

if __name__ == "__main__":
    # example (replace these values)
    url = "http://1.1.1.1/frame.jpg"
    user = "admin"
    password = "12345"
    App = getPulseApp(url,
                      user, 
                      password)
    while True:
        App.main_loop()
        
        

########NEW FILE########
__FILENAME__ = detectors
from openmdao.lib.datatypes.api import Float, Dict, Array, List, Int
from openmdao.main.api import Component, Assembly
import numpy as np
import cv2
import cv2.cv as cv


class cascadeDetection(Component):
    """
    Detects objects using pre-trained haar cascade files and cv2.
    
    Images should (at least ideally) be pre-grayscaled and contrast corrected,
    for best results.
    
    Outputs probable locations of these faces in an array with format:
    
    [[x pos, y pos, width, height], [x pos, y pos, width, height], ...]
    
    Detection locations can be smoothed against motion by setting values to the 
    input parameter 'smooth'.
    """
    
    def __init__(self, fn, 
                 scaleFactor = 1.3, 
                 minNeighbors = 4, 
                 minSize=(75, 75), 
                 flags = cv2.CASCADE_SCALE_IMAGE, 
                 persist = True, 
                 smooth = 10.,
                 return_one = True):
        super(cascadeDetection,self).__init__()  
        self.add("frame_in", Array(iotype="in"))
        self.add("detected", Array([[0,0,2,2]],iotype="out"))
        self.scaleFactor = scaleFactor
        self.persist = persist # keep last detected locations vs overwrite with none
        self.minNeighbors = minNeighbors
        self.minSize = minSize
        self.return_one = return_one #return either one detection location or all 
        self.flags = flags
        self.smooth = smooth
        self.cascade = cv2.CascadeClassifier(fn)
        self.find = True
        
        self.last_center = [0,0]
        
    def toggle(self):
        if self.find:
            self.find = False
        else:
            self.find = True
        return self.find
        
    def on(self):
        if not self.find:
            self.toggle()
    
    def off(self):
        if self.find:
            self.toggle()
    
    def shift(self,detected):
        x,y,w,h = detected
        center =  np.array([x+0.5*w,y+0.5*h])
        shift = np.linalg.norm(center - self.last_center)
        diag = np.sqrt(w**2 + h**2)
        
        self.last_center = center
        return shift
    
    def execute(self):
        if not self.find:
            return
        detected = self.cascade.detectMultiScale(self.frame_in, 
                                              scaleFactor=self.scaleFactor,
                                              minNeighbors=self.minNeighbors,
                                              minSize=self.minSize, 
                                              flags=self.flags)
        if not isinstance(detected,np.ndarray):
            return
        if self.smooth:
            if self.shift(detected[0]) < self.smooth: #regularizes against jitteryness
                return
        if self.return_one:            
            width = detected[0][2]
            height = detected[0][3]
            for i in range(1,len(detected)):
                if detected[i][2] > width and detected[i][3] > height: 
                    detected[0] = detected[i]
                    width = detected[i][2]
                    height = detected[i][3]
            self.detected[0] = detected[0]
        else:
            self.detected = detected
            
            


class faceDetector(cascadeDetection):
    """
    Detects a human face in a frame.
    
    The forehead area is then isolated.
    """

    def __init__(self, minSize=(50, 50), 
                 smooth = 10.,
                 return_one = True):
        #fn = "cascades/haarcascade_frontalface_default.xml"
        fn="cascades/haarcascade_frontalface_alt.xml"
        #fn="cascades/haarcascade_frontalface_alt2.xml"
        #fn = "cascades/haarcascade_frontalface_alt_tree"
        super(faceDetector, self).__init__(fn, 
                                           minSize = minSize,
                                           smooth = smooth,
                                           return_one = return_one)
        self.add("foreheads", Array([[0,0,2,2]],iotype="out"))
        

    def get_foreheads(self):
        """
        defines forehead location using offsets & multiplicative scalings
        """
        fh_x = 0.5  
        fh_y = 0.18
        fh_w = 0.25
        fh_h = 0.15
        forh = []
        for rect in self.detected:
            x,y,w,h = rect
            x += w * fh_x
            y += h * fh_y
            w *= fh_w
            h *= fh_h

            x -= (w / 2.0)
            y -= (h / 2.0)

            forh.append([int(x),int(y),int(w),int(h)])
        self.foreheads = np.array(forh)
        
    def execute(self):
        super(faceDetector, self).execute()
        if self.detected[0][2] != 2:
            self.get_foreheads()
########NEW FILE########
__FILENAME__ = device
import cv2, time
import urllib2, base64
import numpy as np

class ipCamera(object):

    def __init__(self,url, user = None, password = None):
        self.url = url
        auth_encoded = base64.encodestring('%s:%s' % (user, password))[:-1]
        
        self.req = urllib2.Request(self.url)
        self.req.add_header('Authorization', 'Basic %s' % auth_encoded)
        
    def get_frame(self):
        response = urllib2.urlopen(self.req)
        img_array = np.asarray(bytearray(response.read()), dtype=np.uint8)
        frame = cv2.imdecode(img_array, 1)
        return frame
    
class Camera(object):

    def __init__(self, camera = 0):
        self.cam = cv2.VideoCapture(camera)
        if not self.cam:
            raise Exception("Camera not accessible")

        self.shape = self.get_frame().shape

    def get_frame(self):
        _,frame = self.cam.read()
        return frame

    def release(self):
        self.cam.release()
########NEW FILE########
__FILENAME__ = imageProcess
from openmdao.lib.datatypes.api import Float, Dict, Array, List, Int, Bool
from openmdao.main.api import Component, Assembly
import numpy as np
import cv2

"""
Whole-frame image processing components & helper methods
"""

class RGBSplit(Component):
    """
    Extract the red, green, and blue channels from an (n,m,3) shaped 
    array representing a single image frame with RGB color coding.

    At its core, a pretty straighforward numpy slicing operation.
    """

    def __init__(self):
        super(RGBSplit,self).__init__()
        self.add("frame_in", Array(iotype="in"))

        self.add("R", Array(iotype="out"))
        self.add("G", Array(iotype="out"))
        self.add("B", Array(iotype="out"))

    def execute(self):
        self.R = self.frame_in[:,:,0]     
        self.G = self.frame_in[:,:,1]   
        self.B = self.frame_in[:,:,2]   

class RGBmuxer(Component):
    """
    Take three (m,n) matrices of equal size and combine them into a single
    RGB-coded color frame.
    """

    def __init__(self):
        super(RGBmuxer,self).__init__()
        self.add("R", Array(iotype="in"))
        self.add("G", Array(iotype="in"))
        self.add("B", Array(iotype="in"))

        self.add("frame_out", Array(iotype="out"))

    def execute(self):
        m,n = self.R.shape
        self.frame_out = cv2.merge([self.R,self.G,self.B])


class CVwrapped(Component):
    """
    Generic wrapper to take the simpler functions from the cv2 or scipy image
    libraries to generate connectable openMDAO components for image processing.

    The "simple" functions in mind here are the ones of the form:

    "matrix in" --> [single method call]--> "matrix out"    

    Other functionality (like object detection, frame annotation, etc) should 
    probably be wrapped individually.
    """
    def __init__(self, func, *args, **kwargs):
        super(CVwrapped,self).__init__()
        self.add("frame_in", Array(iotype="in"))
        self.add("frame_out", Array(iotype="out"))
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def execute(self):
        self.frame_out = self._func(self.frame_in, *self._args, **self._kwargs)


class Grayscale(CVwrapped):
    """
    Turn (m,n,3) shaped RGB image frame to a (m,n) frame 
    Discards color information to produce simple image matrix.
    """
    def __init__(self):
        super(Grayscale,self).__init__(cv2.cvtColor, cv2.COLOR_BGR2GRAY)

class equalizeContrast(CVwrapped):
    """
    Automatic contrast correction.
    Note: Only works for grayscale images!
    """
    def __init__(self):
        super(equalizeContrast,self).__init__(cv2.equalizeHist)
        
        
class showBPMtext(Component):
    """
    Shows the estimated BPM in the image frame
    """
    ready = Bool(False,iotype = "in")
    bpm = Float(iotype = "in")
    x = Int(iotype = "in")
    y = Int(iotype = "in")
    fps = Float(iotype = "in")
    size = Float(iotype = "in")
    n = Int(iotype = "in")
    
    def __init__(self):
        super(showBPMtext,self).__init__()
        self.add("frame_in", Array(iotype="in"))
        self.add("frame_out", Array(iotype="out"))
    
    def execute(self):
        if self.ready:
            col = (0,255,0)
            text = "%0.1f bpm" % self.bpm
            tsize = 2
        else:
            col = (100,255,100)
            gap = (self.n - self.size) / self.fps
            text = "(estimate: %0.1f bpm, wait %0.0f s)" % (self.bpm, gap)
            tsize = 1
        cv2.putText(self.frame_in,text,
                    (self.x,self.y),cv2.FONT_HERSHEY_PLAIN,tsize,col)
        self.frame_out = self.frame_in
########NEW FILE########
__FILENAME__ = interface
import cv2, time
import numpy as np

"""
Wraps up some interfaces to opencv user interface methods (displaying
image frames, event handling, etc).

If desired, an alternative UI could be built and imported into get_pulse.py 
instead. Opencv is used to perform much of the data analysis, but there is no
reason it has to be used to handle the UI as well. It just happens to be very
effective for our purposes.
"""
def resize(*args, **kwargs):
    return cv2.resize(*args, **kwargs)

def moveWindow(*args,**kwargs):
    return

def imshow(*args,**kwargs):
    return cv2.imshow(*args,**kwargs)
    
def destroyWindow(*args,**kwargs):
    return cv2.destroyWindow(*args,**kwargs)

def waitKey(*args,**kwargs):
    return cv2.waitKey(*args,**kwargs)


"""
The rest of this file defines some GUI plotting functionality. There are plenty
of other ways to do simple x-y data plots in python, but this application uses 
cv2.imshow to do real-time data plotting and handle user interaction.

This is entirely independent of the data calculation functions, so it can be 
replaced in the get_pulse.py application easily.
"""


def combine(left, right):
    """Stack images horizontally.
    """
    h = max(left.shape[0], right.shape[0])
    w = left.shape[1] + right.shape[1]
    hoff = left.shape[0]
    
    shape = list(left.shape)
    shape[0] = h
    shape[1] = w
    
    comb = np.zeros(tuple(shape),left.dtype)
    
    # left will be on left, aligned top, with right on right
    comb[:left.shape[0],:left.shape[1]] = left
    comb[:right.shape[0],left.shape[1]:] = right
    
    return comb   

def plotXY(data,size = (280,640),margin = 25,name = "data",labels=[], skip = [],
           showmax = [], bg = None,label_ndigits = [], showmax_digits=[]):
    for x,y in data:
        if len(x) < 2 or len(y) < 2:
            return
    
    n_plots = len(data)
    w = float(size[1])
    h = size[0]/float(n_plots)
    
    z = np.zeros((size[0],size[1],3))
    
    if isinstance(bg,np.ndarray):
        wd = int(bg.shape[1]/bg.shape[0]*h )
        bg = cv2.resize(bg,(wd,int(h)))
        if len(bg.shape) == 3:
            r = combine(bg[:,:,0],z[:,:,0])
            g = combine(bg[:,:,1],z[:,:,1])
            b = combine(bg[:,:,2],z[:,:,2])
        else:
            r = combine(bg,z[:,:,0])
            g = combine(bg,z[:,:,1])
            b = combine(bg,z[:,:,2])
        z = cv2.merge([r,g,b])[:,:-wd,]    
    
    i = 0
    P = []
    for x,y in data:
        x = np.array(x)
        y = -np.array(y)
        
        xx = (w-2*margin)*(x - x.min()) / (x.max() - x.min())+margin
        yy = (h-2*margin)*(y - y.min()) / (y.max() - y.min())+margin + i*h
        mx = max(yy)
        if labels:
            if labels[i]:
                for ii in xrange(len(x)):
                    if ii%skip[i] == 0:
                        col = (255,255,255)
                        ss = '{0:.%sf}' % label_ndigits[i]
                        ss = ss.format(x[ii]) 
                        cv2.putText(z,ss,(int(xx[ii]),int((i+1)*h)),
                                    cv2.FONT_HERSHEY_PLAIN,1,col)           
        if showmax:
            if showmax[i]:
                col = (0,255,0)    
                ii = np.argmax(-y)
                ss = '{0:.%sf} %s' % (showmax_digits[i], showmax[i])
                ss = ss.format(x[ii]) 
                #"%0.0f %s" % (x[ii], showmax[i])
                cv2.putText(z,ss,(int(xx[ii]),int((yy[ii]))),
                            cv2.FONT_HERSHEY_PLAIN,2,col)
        
        try:
            pts = np.array([[x_, y_] for x_, y_ in zip(xx,yy)],np.int32)
            i+=1
            P.append(pts)
        except ValueError:
            pass #temporary
    """ 
    #Polylines seems to have some trouble rendering multiple polys for some people
    for p in P:
        cv2.polylines(z, [p], False, (255,255,255),1)
    """
    #hack-y alternative:
    for p in P:
        for i in xrange(len(p)-1):
            cv2.line(z,tuple(p[i]),tuple(p[i+1]), (255,255,255),1)    
    cv2.imshow(name,z)

########NEW FILE########
__FILENAME__ = processors
from openmdao.lib.datatypes.api import Float, Dict, Array, List, Int
from openmdao.main.api import Component, Assembly

from imageProcess import RGBSplit, RGBmuxer, equalizeContrast, Grayscale, showBPMtext
from detectors import faceDetector
from sliceops import frameSlices, VariableEqualizerBlock, drawRectangles
from signalProcess import BufferFFT, Cardiac, PhaseController
from numpy import mean
import time, cv2


class findFaceGetPulse(Assembly):
    """
    An openMDAO assembly to detect a human face in an image frame, and then 
    isolate the forehead.
    
    Collects and buffers mean value of the green channel in the forehead locations 
    over time, with each run.
    
    This information is then used to estimate the detected individual's heartbeat
    
    Basic usage: 
    
    -Instance this assembly, then create a loop over frames collected
    from an imaging device. 
    -For each iteration of the loop, populate the assembly's 
    'frame_in' input array with the collected frame, then call the assembly's run()
    method to conduct all of the analysis. 
    -Finally, display annotated results
    from the output 'frame_out' array.
    
    """
    def __init__(self, 
                 bpm_limits = [50,160],
                 data_spike_limit = 13.,
                 face_detector_smoothness = 10):
        super(findFaceGetPulse, self).__init__()
        
        #-----------assembly-level I/O-----------
        
        #input array
        self.add("frame_in", Array(iotype="in"))
        #output array
        self.add("frame_out", Array(iotype="out"))
        #array of detected faces (as single frame)
        self.add("faces", Array(iotype="out"))
        
        #-----------components-----------
        # Each component we want to use must be added to the assembly, then also
        # added to the driver's workflow 
        
        #splits input color image into R,G,B channels
        self.add("RGBsplitter", RGBSplit())
        self.driver.workflow.add("RGBsplitter")
        
        #converts input color image to grayscale
        self.add("grayscale", Grayscale())
        self.driver.workflow.add("grayscale")        
        
        #equalizes contast on the grayscale'd input image
        self.add("contrast_eq", equalizeContrast())
        self.driver.workflow.add("contrast_eq")       
        
        #finds faces within the grayscale's and contast-adjusted input image
        #Sets smoothness parameter to help prevent 'jitteriness' in the face tracking
        self.add("find_faces", faceDetector(smooth = face_detector_smoothness))
        self.driver.workflow.add("find_faces")
        
        #collects subimage samples of the detected faces
        self.add("grab_faces", frameSlices())
        self.driver.workflow.add("grab_faces")
        
        #collects subimage samples of the detected foreheads
        self.add("grab_foreheads", frameSlices())
        self.driver.workflow.add("grab_foreheads")     
        
        #highlights the locations of detected faces using contrast equalization
        self.add("highlight_faces", VariableEqualizerBlock(channels=[0,1,2]))
        self.driver.workflow.add("highlight_faces")
        
        #highlights the locations of detected foreheads using 
        #contrast equalization (green channel only)
        self.add("highlight_fhd", VariableEqualizerBlock(channels=[1], 
                                                         zerochannels=[0,2]))
        self.driver.workflow.add("highlight_fhd")
        
        #collects data over time to compute a 1d temporal FFT
        # 'n' sets the internal buffer length (number of samples)
        # 'spike_limit' limits the size of acceptable spikes in the raw measured
        # data. When exceeeded due to poor data, the fft component's buffers 
        # are reset
        self.add("fft", BufferFFT(n=425,
                                  spike_limit = data_spike_limit))
        self.driver.workflow.add("fft")
        
        #takes in a computed FFT and estimates cardiac data
        # 'bpm_limits' sets the lower and upper limits (in bpm) for heartbeat
        # detection. 50 to 160 bpm is a pretty fair range here.
        self.add("measure_heart", Cardiac(bpm_limits = bpm_limits))
        self.driver.workflow.add("measure_heart")
        
        #toggles flashing of the detected foreheads in sync with the detected 
        #heartbeat. the 'default_a' and 'default_b' set the nominal contrast
        #correction that will occur when phase pulsing isn't enabled.
        #Pulsing is set by toggling the boolean variable 'state'.
        self.add("bpm_flasher", PhaseController(default_a=1., 
                                                default_b=0.,
                                                state = True))
        self.driver.workflow.add("bpm_flasher")   
        
        self.add("show_bpm_text", showBPMtext())
        self.driver.workflow.add("show_bpm_text")
        
        #-----------connections-----------
        # here is where we establish the relationships between the components 
        # that were added above.
        
        #--First, set up the connectivity for components that will do basic
        #--input, decomposition, and annotation of the inputted image frame
        
        # pass image frames from the assembly-level input arrays to the RGB 
        # splitter & grayscale converters (separately)
        self.connect("frame_in", "RGBsplitter.frame_in")
        self.connect("frame_in", "grayscale.frame_in")
        
        #pass grayscaled image to the contrast equalizer
        self.connect("grayscale.frame_out", "contrast_eq.frame_in")
        
        #pass the contrast adjusted grayscale image to the face detector
        self.connect("contrast_eq.frame_out", "find_faces.frame_in")
        
        # now pass our original image frame and the detected faces locations 
        # to the face highlighter
        self.connect("frame_in", "highlight_faces.frame_in")
        self.connect("find_faces.detected", "highlight_faces.rects_in")
        
        # pass the original image frame and detected face locations
        # to the forehead highlighter
        self.connect("highlight_faces.frame_out", "highlight_fhd.frame_in")
        self.connect("find_faces.foreheads", "highlight_fhd.rects_in")
        
        # pass the original image frame and detected face locations
        # to the face subimage collector
        self.connect("find_faces.detected", "grab_faces.rects_in")
        self.connect("contrast_eq.frame_out", "grab_faces.frame_in")
        
        # --Now we set the connectivity for the components that will do the 
        # --actual analysis
        
        #pass the green channel of the original image frame and detected 
        #face locations to the forehead subimage collector
        self.connect("find_faces.foreheads", "grab_foreheads.rects_in")
        self.connect("RGBsplitter.G", "grab_foreheads.frame_in")   
        
        #send the mean of the first detected forehead subimage (green channel)
        #to the buffering FFT component
        #Should probably be an intermediate component here, but that isn't 
        #actually necessary - we can do a connection between expressions in
        #addition to input/output variables.
        #self.connect("grab_foreheads.slices[0]", "fft.data_in")
        self.connect("grab_foreheads.zero_mean", "fft.data_in")
        
        #Send the FFT outputs (the fft & associated freqs in hz) to the cardiac
        #data estimator
        self.connect("fft.fft", "measure_heart.fft_in")
        self.connect("fft.freqs", "measure_heart.freqs_in")
        
        #connect the estimated heartbeat phase to the forehead flashing controller
        self.connect("measure_heart.phase", "bpm_flasher.phase")
        self.connect("fft.ready", "bpm_flasher.state")
        
        #connect the flash controller to the forehead highlighter 
        self.connect("bpm_flasher.alpha", "highlight_fhd.alpha")
        self.connect("bpm_flasher.beta", "highlight_fhd.beta")
        
        #connect collection of all detected faces up to assembly level for output
        self.connect("grab_faces.combined", "faces")
        
        # text display of estimated bpm
        self.connect("highlight_fhd.frame_out", "show_bpm_text.frame_in") 
        self.connect("measure_heart.bpm", "show_bpm_text.bpm")
        self.connect("find_faces.detected[0][0]", "show_bpm_text.x")
        self.connect("find_faces.detected[0][1]", "show_bpm_text.y")
        self.connect("fft.fps", "show_bpm_text.fps")
        self.connect("fft.size", "show_bpm_text.size")
        self.connect("fft.n", "show_bpm_text.n")
        
        self.connect("fft.ready", "show_bpm_text.ready")
        self.connect("show_bpm_text.frame_out", "frame_out") 
        
########NEW FILE########
__FILENAME__ = signalProcess
from openmdao.lib.datatypes.api import Float, Dict, Array, List, Int, Bool
from openmdao.main.api import Component, Assembly
import numpy as np
import time
     
"""
Some 1D signal processing methods used for the analysis of image frames
"""
        
class PhaseController(Component):
    """
    Outputs either a convex combination of two floats generated from an inputted 
    phase angle, or a set of two default values
    
    The inputted phase should be an angle ranging from 0 to 2*pi
    
    The behavior is toggled by the boolean "state" input, which may be connected
    by another component or set directly by the user during a run
    
    (In short, this component can help make parts of an image frame flash in 
    sync to a detected heartbeat signal, in real time)
    """
    phase = Float(iotype="in")
    state = Bool(iotype="in")
    
    alpha = Float(iotype="out")
    beta = Float(iotype="out")
    
    def __init__(self, default_a, default_b,state = False):
        super(PhaseController,self).__init__()
        self.state = state
        self.default_a = default_a
        self.default_b = default_b
    
    def toggle(self):
        if self.state:
            self.state = False
        else:
            self.state = True
        return self.state
        
    def on(self):
        if not self.state:
            self.toggle()
    
    def off(self):
        if self.state:
            self.toggle()
    
    def execute(self):
        if self.state:
            t = (np.sin(self.phase) + 1.)/2.
            t = 0.9*t + 0.1
            self.alpha = t
            self.beta = 1-t
        else:
            self.alpha = self.default_a
            self.beta = self.default_b


class BufferFFT(Component):
    """
    Collects data from a connected input float over each run and buffers it
    internally into lists of maximum size 'n'.
    
    (So, each run increases the size of these buffers by 1.)
    
    Computes an FFT of this buffered data, along with timestamps and 
    correspondonding frequencies (hz), as output arrays.
    
    When the internal buffer is full to size 'n', the boolean 'ready' is 
    toggled to True. This indicates that this component is providing output 
    data corresponding to an n-point FFT. The 'ready' state can be outputed as
    a digital control to another component taking a boolean input.
    
    Can be reset to clear out internal buffers using the reset() method. This
    toggles the 'ready' state to False.
    """
    ready = Bool(False, iotype="out")
    fps = Float(iotype = "out")
    size = Int(iotype = "out")
    n = Int(iotype = "out")
    def __init__(self, n = 322, spike_limit = 5.):
        super(BufferFFT,self).__init__()
        self.n = n
        self.add("data_in", Float(iotype="in"))
        self.samples = []
        self.fps = 1.
        self.add("times", List(iotype="out"))
        self.add("fft", Array(iotype="out"))
        self.add("freqs", Array(iotype="out"))
        self.interpolated = np.zeros(2)
        self.even_times = np.zeros(2)
        
        self.spike_limit = spike_limit


    def get_fft(self):
        n = len(self.times)
        self.fps = float(n) / (self.times[-1] - self.times[0])
        self.even_times = np.linspace(self.times[0], self.times[-1], n)
        interpolated = np.interp(self.even_times, self.times, self.samples)
        interpolated = np.hamming(n) * interpolated
        self.interpolated = interpolated
        interpolated = interpolated - np.mean(interpolated)
        # Perform the FFT
        fft = np.fft.rfft(interpolated)
        self.freqs = float(self.fps)/n*np.arange(n/2 + 1)
        return fft      
    
    def find_offset(self):
        N = len(self.samples)
        for i in xrange(2,N):
            samples = self.samples[i:]
            delta =  max(samples)-min(samples)
            if delta < self.spike_limit:
                return N-i
    
    def reset(self):
        N = self.find_offset()
        self.ready = False
        self.times = self.times[N:]
        self.samples = self.samples[N:]

    def execute(self):
        self.samples.append(self.data_in)
        self.times.append(time.time())
        self.size = len(self.samples)
        if self.size > self.n:
            self.ready = True
            self.samples = self.samples[-self.n:]
            self.times = self.times[-self.n:]
        if self.size>4:
            self.fft = self.get_fft()
            if self.spike_limit:
                if max(self.samples)-min(self.samples) > self.spike_limit:
                    self.reset()

class bandProcess(Component):
    """
    Component to isolate specific frequency bands
    """
    hz = Float(iotype="out")
    peak_hz = Float(iotype="out")
    phase = Float(iotype="out")
    def __init__(self, limits = [0.,3.], make_filtered = True, 
                 operation = "pass"):
        super(bandProcess,self).__init__()
        self.add("freqs_in",Array(iotype="in"))
        self.add("fft_in", Array(iotype="in"))
        
        self.add("freqs", Array(iotype="out"))
        self.make_filtered = make_filtered
        if make_filtered:
            self.add("filtered", Array(iotype="out"))
        self.add("fft", Array(iotype="out"))
        self.limits = limits
        self.operation = operation
        
    def execute(self):
        if self.operation == "pass":
            idx = np.where((self.freqs_in > self.limits[0]) 
                           & (self.freqs_in < self.limits[1]))
        else:
            idx = np.where((self.freqs_in < self.limits[0]) 
                           & (self.freqs_in > self.limits[1]))
        self.freqs = self.freqs_in[idx] 
        self.fft = np.abs(self.fft_in[idx])**2
        
        if self.make_filtered:
            fft_out = 0*self.fft_in
            fft_out[idx] = self.fft_in[idx]
            
            if len(fft_out) > 2:
                self.filtered = np.fft.irfft(fft_out) 
                
                self.filtered = self.filtered / np.hamming(len(self.filtered))
        try:
            maxidx = np.argmax(self.fft)
            self.peak_hz = self.freqs[maxidx]
            self.phase = np.angle(self.fft_in)[idx][maxidx]
        except ValueError:
            pass #temporary fix for no-data situations

class Cardiac(bandProcess):
    """
    Component to isolate portions of a pre-computed time series FFT 
    corresponding to human heartbeats
    """
    
    def __init__(self, bpm_limits = [50,160]):
        super(Cardiac,self).__init__()
        self.add("bpm", Float(iotype="out"))
        self.limits = [bpm_limits[0]/60., bpm_limits[1]/60.]
        
    def execute(self):
        super(Cardiac,self).execute()
        self.freqs = 60*self.freqs
        self.bpm = 60*self.peak_hz
        

########NEW FILE########
__FILENAME__ = sliceops
from openmdao.lib.datatypes.api import Float, Dict, Array, List, Int
from openmdao.main.api import Component, Assembly
import numpy as np
import cv2

"""
Image frame analysis components written to operate only on inputted regions
(slices of numpy arrays) which are inputted. 

Typically these recieve, as input, the output of some object detection components
"""

class processRect(Component):
    """
    Process inputted rectangles, using specification 
    [ [x pos, y pos, width, height], ... ]
    into an inputted frame.
    
    (Used as a prototype for most of the region-specific image analysis 
    components)
    """
    
    def __init__(self, channels = [0,1,2], zerochannels = []):
        super(processRect,self).__init__()
        self.add("frame_in", Array(iotype="in"))
        self.add("rects_in", Array(iotype="in"))
        self.add("frame_out", Array(iotype="out"))
        self.channels = channels
        self.zerochannels = zerochannels
        
    def execute(self):
        temp = np.array(self.frame_in) # bugfix for strange cv2 error
        if self.rects_in.size > 0:
            for rect in self.rects_in:
                if len(self.frame_in.shape) == 3:
                    for chan in self.channels:
                        temp[:,:,chan] = self.process(rect, temp[:,:,chan])
                    x,y,w,h = rect
                    for chan in self.zerochannels:
                        temp[y:y+h,x:x+w,chan]= 0*temp[y:y+h,x:x+w,chan]
                else:
                    temp = self.process(rect, temp)
        self.frame_out = temp
        
    def process(self):
        return 

class drawRectangles(processRect):
    """
    Draws rectangles outlines in a specific region within the inputted frame
    """
        
    def process(self, rect, frame):
        x,y,w,h = rect
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0,255,0), 3)
        return frame

class VariableEqualizerBlock(processRect):
    """
    Equalizes the contrast in a specific region within the inputted frame
    
    Balance between fully equalized contrast and the un-altered frame can be
    varied by setting the 'alpha' and 'beta' inputs.
    """
    beta = Float(0., iotype="in")
    alpha = Float(1., iotype="in")
    def process(self, rect, frame):
        x,y,w,h = rect
        subimg = np.array(frame[y:y+h,x:x+w]) 
        subimg = self.beta*subimg + self.alpha*cv2.equalizeHist(subimg)   
        frame[y:y+h,x:x+w]  = subimg
        return frame
        

class frameSlices(Component):
    """
    Collect slices of inputted frame using rectangle specifications. 
    
    This component is typically used to grab regions of interest of an image for
    GUI display.
    """
    def __init__(self, channels = [0,1,2]):
        super(frameSlices,self).__init__()    
        self.add("frame_in", Array(iotype="in"))
        self.add("rects_in", Array(iotype="in"))
        self.add("slices", List([ np.array([0,0]) ],iotype="out"))
        self.add("combined", Array(iotype="out"))

        self.add("zero_mean", Float(0., iotype="out"))
        
        self.channels = channels
        
    def combine(self,left, right):
        """Stack images horizontally.
        """
        h = max(left.shape[0], right.shape[0])
        w = left.shape[1] + right.shape[1]
        hoff = left.shape[0]
        
        shape = list(left.shape)
        shape[0] = h
        shape[1] = w
        
        comb = np.zeros(tuple(shape),left.dtype)
        
        # left will be on left, aligned top, with right on right
        comb[:left.shape[0],:left.shape[1]] = left
        comb[:right.shape[0],left.shape[1]:] = right
        
        return comb            
        
    def execute(self):
        comb = 150*np.ones((2,2))
        if self.rects_in.size > 0:
            self.slices = []
            for x,y,w,h in self.rects_in:
                output = self.frame_in[y:y+h,x:x+w]
                self.slices.append(output)
                
                comb = self.combine(output, comb)
        self.combined = comb
        self.zero_mean = self.slices[0].mean()
        

        
########NEW FILE########
__FILENAME__ = make_design_graph
from lib.processors import findFaceGetPulse
import networkx as nx

"""
Simple tool to visualize the design of the real-time image analysis

Everything needed to produce the graph already exists in an instance of the
assembly.
"""

#get the component/data dependancy graph (depgraph) of the assembly
assembly = findFaceGetPulse()
graph = assembly._depgraph._graph

#prune a few unconnected nodes not related to the actual analysis
graph.remove_node("@xin")
graph.remove_node("@xout")
graph.remove_node("driver")

#plot the graph to disc as a png image
ag = nx.to_agraph(graph)
ag.layout('dot')
ag.draw('design.png')

########NEW FILE########
__FILENAME__ = test_webcam
import cv2, numpy

#Create object to read images from camera 0
cam = cv2.VideoCapture(0)

while True:
    #Get image from webcam
    ret, img = cam.read()
    
    #create some test points
    pts1 = numpy.array([[0,0],[100,100]], numpy.int32)
    pts2 = numpy.array([[0,0],[0,500],[200,200]], numpy.int32)
    pts3 = numpy.array([[10,3],[10,300],[100,250]], numpy.int32)
    
    #test out line function
    for i in xrange(len(pts3)-1):
        cv2.line(img,tuple(pts3[i]),tuple(pts3[i+1]), (255,255,255),1)
        
    #test out the polylines function
    cv2.polylines(img, [pts1, pts2], False, (255,255,255),1)
        
    #show the result
    cv2.imshow("Camera", img)

    #Sleep infinite loop for ~10ms
    #Exit if user presses <Esc>
    if cv2.waitKey(10) == 27:
        break
    
########NEW FILE########
