__FILENAME__ = classification
from feature_extraction import FEATURE_DATATYPE
import numpy
import cv2

CLASS_DATATYPE=     numpy.uint16
CLASS_SIZE=         1
CLASSES_DIRECTION=  0 #vertical - a classes COLUMN

BLANK_CLASS=        chr(35) #marks unclassified elements

def classes_to_numpy( classes ):
    '''given a list of unicode chars, transforms it into a numpy array'''
    import array
    #utf-32 starts with constant ''\xff\xfe\x00\x00', then has little endian 32 bits chars
    #this assumes little endian architecture!
    assert unichr(15).encode('utf-32')=='\xff\xfe\x00\x00\x0f\x00\x00\x00'
    assert array.array("I").itemsize==4
    int_classes= array.array( "I", "".join(classes).encode('utf-32')[4:])
    assert len(int_classes) == len(classes)
    classes=  numpy.array( int_classes,  dtype=CLASS_DATATYPE, ndmin=2) #each class in a column. numpy is strange :(
    classes= classes if CLASSES_DIRECTION==1 else numpy.transpose(classes)
    return classes

def classes_from_numpy(classes):
    '''reverses classes_to_numpy'''
    classes= classes if CLASSES_DIRECTION==0 else classes.tranpose()
    classes= map(unichr, classes)
    return classes

class Classifier( object ):
    def train( self, features, classes ):
        '''trains the classifier with the classified feature vectors'''
        raise NotImplementedError()

    @staticmethod
    def _filter_unclassified( features, classes ):
        classified= (classes != classes_to_numpy(BLANK_CLASS)).reshape(-1)
        return features[classified], classes[classified]
        
    def classify( self, features):
        '''returns the classes of the feature vectors'''
        raise NotImplementedError

class KNNClassifier( Classifier ):
    def __init__(self, k=1, debug=False):
        self.knn= cv2.KNearest()
        self.k=k
        self.debug= debug

    def train( self, features, classes ):
        if FEATURE_DATATYPE!=numpy.float32:
            features= numpy.asarray( features, dtype=numpy.float32 )
        if CLASS_DATATYPE!=numpy.float32:
            classes= numpy.asarray( classes, dtype=numpy.float32 )
        features, classes= Classifier._filter_unclassified( features, classes )
        self.knn.train( features, classes )
        
    def classify( self, features):
        if FEATURE_DATATYPE!=numpy.float32:
            features= numpy.asarray( features, dtype=numpy.float32 )
        retval, result_classes, neigh_resp, dists= self.knn.find_nearest(features, k= 1)
        return result_classes

########NEW FILE########
__FILENAME__ = example
from files import ImageFile
from segmentation import ContourSegmenter, draw_segments
from feature_extraction import SimpleFeatureExtractor
from classification import KNNClassifier
from ocr import OCR, accuracy, show_differences, reconstruct_chars

segmenter=  ContourSegmenter( blur_y=5, blur_x=5, block_size=11, c=10)
extractor=  SimpleFeatureExtractor( feature_size=10, stretch=False )
classifier= KNNClassifier()
ocr= OCR( segmenter, extractor, classifier )

ocr.train( ImageFile('digits1') )

test_image= ImageFile('digits2')
test_classes, test_segments= ocr.ocr( test_image, show_steps=True )

print "accuracy:", accuracy( test_image.ground.classes, test_classes )
print "OCRed text:\n", reconstruct_chars( test_classes )
show_differences( test_image.image, test_segments, test_image.ground.classes, test_classes)

########NEW FILE########
__FILENAME__ = feature_extraction
import numpy
import cv2
from segmentation import region_from_segment
from opencv_utils import background_color

FEATURE_DATATYPE=   numpy.float32
#FEATURE_SIZE is defined on the specific feature extractor instance
FEATURE_DIRECTION=  1 #horizontal - a COLUMN feature vector
FEATURES_DIRECTION= 0 # vertical - ROWS of feature vectors

class FeatureExtractor( object ):
    '''given a list of segments, returns a list of feature vectors'''
    def extract( self, image, segments ):
        raise NotImplementedError()

class SimpleFeatureExtractor( FeatureExtractor ):
    def __init__(self, feature_size=10, stretch=False):
        self.feature_size= feature_size
        self.stretch=stretch

    def extract(self, image, segments):
        image= cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
        fs= self.feature_size
        bg= background_color( image )
 
        regions=numpy.ndarray( shape=(0,fs), dtype=FEATURE_DATATYPE )
        for segment in segments:
            region= region_from_segment( image, segment )
            if self.stretch:
                region = cv2.resize(region, (fs,fs) )
            else:
                x,y,w,h= segment
                proportion= float(min(h,w))/max(w,h)
                new_size= (fs, int(fs*proportion)) if min(w,h)==h else (int(fs*proportion), fs)
                region = cv2.resize(region, new_size)
                s= region.shape
                newregion= numpy.ndarray( (fs,fs), dtype= region.dtype )
                newregion[:,:]= bg
                newregion[:s[0],:s[1]]= region
                region=newregion
            regions= numpy.append( regions, region, axis=0 )
        regions.shape=( len(segments), fs**2 )
        return regions



########NEW FILE########
__FILENAME__ = files
import os
import cv2
from tesseract_utils import read_boxfile, write_boxfile

IMAGE_EXTENSIONS= ['.png','.tif','.jpg', '.jpeg']
DATA_DIRECTORY= 'data/'
GROUND_EXTENSIONS= ['.box']
GROUND_EXTENSIONS_DEFAULT=GROUND_EXTENSIONS[0]

def split_extension( path ):
    '''splits filename (with extension) into filename and extension'''
    try:
        i=path.index(".", -5)
        return path[:i], path[i:]
    except ValueError:
        return path, ""

def try_extensions( path, extensions ):
    '''checks if various extensions of a path exist'''
    if os.path.exists( path ):
        return path
    for ext in extensions:
        p= path+ext
        if os.path.exists( p ):
            return p
    return None

class GroundFile( object ):
    def __init__(self, path):
        self.path=      path
        self.segments=  None
        self.classes=    None

    def read(self):
        self.classes, self.segments= read_boxfile( self.path )

    def write(self):
        write_boxfile( self.path, self.classes, self.segments )


class ImageFile( object ):
    '''An OCR image file. Has an image and its file path, and optionally 
    a ground (ground segments and classes) and it's file path'''
    def __init__( self, image_path):
        good_path= try_extensions( image_path, IMAGE_EXTENSIONS ) 
        good_path= try_extensions( os.path.join( DATA_DIRECTORY, image_path ), IMAGE_EXTENSIONS )
        if not good_path:
            raise Exception( "could not find file: "+path)
        self.image_path=     good_path
        self.image= cv2.imread(self.image_path)
        basename= split_extension(good_path)[0]
        self.ground_path=    try_extensions( basename, GROUND_EXTENSIONS )
        if self.ground_path:
            self.ground= GroundFile(self.ground_path)
            self.ground.read()
        else:
            self.ground_path= basename+GROUND_EXTENSIONS_DEFAULT
            self.ground=None

    def isGrounded(self):
        '''checks if this file is grounded'''
        return not (self.ground is None)

    def set_ground( self, segments, classes, write_file=False):
        '''creates the ground, saves it to a file'''
        if self.isGrounded():
            print "Warning: grounding already grounded file"
        self.ground= GroundFile(self.ground_path)
        self.ground.segments= segments
        self.ground.classes= classes
        if write_file:
            self.ground.write()

    def remove_ground(self, remove_file=False):
        '''removes ground, optionally deleting it's file'''
        if not self.isGrounded():
            print "Warning: ungrounding ungrounded file"
        self.ground= None
        if remove_file:
            os.remove( self.ground_path )

########NEW FILE########
__FILENAME__ = grounding
'''various classis for establishing ground truth'''

from files import ImageFile
from classification import classes_to_numpy, classes_from_numpy, BLANK_CLASS
from opencv_utils import background_color, show_image_and_wait_for_key, draw_segments, draw_classes
import numpy
import string

NOT_A_SEGMENT=unichr(10)

class Grounder( object ):
    def ground(self, imagefile, segments, external_data):
        '''given an ImageFile, grounds it, through arbirary data (better defined in subclasses)'''
        raise NotImplementedError()

class TextGrounder( Grounder ):
    '''labels from a string'''
    def ground( self, imagefile, segments, text ):
        '''tries to grounds from a simple string'''
        text= unicode( text )
        text= filter( lambda c: c in string.ascii_letters+string.digits, list(text))
        if len(segments)!=len(text):
            raise Exception( "segments/text length mismatch")
        classes= classes_to_numpy( text )
        imagefile.set_ground( segments, classes)

class UserGrounder( Grounder ):
    '''labels by interactively asking the user'''
    def ground( self, imagefile, segments, _=None ):
        '''asks the user to label each segment as either a character or "<" for unknown'''
        print '''For each shown segment, please write the character that it represents, or spacebar if it's not a character. To undo a classification, press backspace. Press ESC when completed, arrow keys to move'''
        i=0
        if imagefile.isGrounded():
            classes= classes_from_numpy( imagefile.ground.classes)
            segments= imagefile.ground.segments
        else:
            classes= [BLANK_CLASS]*len(segments) #char(10) is newline. it represents a non-assigned label, and will b filtered
        done= False
        allowed_chars= map( ord,  string.digits+string.letters+string.punctuation )
        while not done:
            image= imagefile.image.copy()
            draw_segments( image, [segments[ i ]])
            draw_classes( image, segments, classes )
            key= show_image_and_wait_for_key( image, "segment "+str(i))
            if key==27: #ESC
                break
            elif key==8:  #backspace
                classes[i]= BLANK_CLASS
                i+=1
            elif key==32: #space
                classes[i]= NOT_A_SEGMENT
                i+=1
            elif key==65361: #<-
                i-=1
            elif key==65363: #->
                i+=1
            elif key in allowed_chars:
                classes[i]= unichr(key)
                i+=1
            if i>=len(classes):
                i=0
            if i<0:
                i=len(classes)-1
                
        classes= numpy.array( classes )
        is_segment= classes != NOT_A_SEGMENT
        classes= classes[ is_segment ]
        segments= segments[ is_segment ]
        classes= list(classes)
        
        classes= classes_to_numpy( classes )
        print "classified ",numpy.count_nonzero( classes != classes_to_numpy(BLANK_CLASS) ), "characters out of", max(classes.shape)
        imagefile.set_ground( segments, classes )
        

########NEW FILE########
__FILENAME__ = numpy_utils
import numpy

class OverflowPreventer( object ):
    '''A context manager that exposes a numpy array preventing simple operations from overflowing.
    Example:
    array= numpy.array( [255], dtype=numpy.uint8 )
    with OverflowPreventer( array ) as prevented:
        prevented+=1
    print array'''
    inverse_operator= { '__iadd__':'__sub__', '__isub__':'__add__', '__imul__': '__div__', '__idiv__':'__mul__'}
    bypass_operators=['__str__', '__repr__', '__getitem__']
    def __init__( self, matrix ):
        class CustomWrapper( object ):
            def __init__(self, matrix):
                assert matrix.dtype==numpy.uint8
                self.overflow_matrix= matrix
                self.overflow_lower_range= float(0)
                self.overflow_upper_range= float(2**8-1)
                for op in OverflowPreventer.bypass_operators:
                    setattr(CustomWrapper, op, getattr(self.overflow_matrix, op))
            
            def _overflow_operator( self, b, forward_operator):
                m, lr, ur= self.overflow_matrix, self.overflow_lower_range, self.overflow_upper_range
                assert type(b) in (int, float)
                reverse_operator= OverflowPreventer.inverse_operator[forward_operator]
                uro= getattr( ur, reverse_operator)
                lro= getattr( lr, reverse_operator)
                afo= getattr( m, forward_operator )
                overflows= m > uro( b )
                underflows= m < lro( b )
                afo( b )
                m[overflows]= ur
                m[underflows]= lr
                return self
                
            def __getattr__(self, attr):
                if hasattr(self.wrapped, attr):
                    return getattr(self.wrapped,attr)
                else:
                    raise AttributeError

        self.wrapper= CustomWrapper(matrix)
        import functools
        for op in OverflowPreventer.inverse_operator.keys():
            setattr( CustomWrapper, op, functools.partial(self.wrapper._overflow_operator, forward_operator=op))

    def __enter__( self ):
        return self.wrapper
    
    def __exit__( self, type, value, tb ):
        pass

########NEW FILE########
__FILENAME__ = ocr
from opencv_utils import show_image_and_wait_for_key, draw_segments
import numpy
import cv2

def show_differences( image, segments, ground_classes, result_classes):
    image= image.copy()
    good= (ground_classes==result_classes)
    good.shape= (len(good),) #transform nx1 matrix into vector
    draw_segments( image, segments[good,:], (0,255,0) )
    draw_segments( image, segments[numpy.logical_not(good),:], (0,0,255)  )   
    show_image_and_wait_for_key(image, "differences")


def reconstruct_chars( classes ):
    result_string= "".join(map(unichr, classes))
    return result_string

def accuracy( expected, result ):
    if( expected.shape!=result.shape ):
        raise Exception("expected "+str(expected.shape)+", got "+str(result.shape))
    correct= expected==result
    return float(numpy.count_nonzero(correct))/correct.shape[0]


class OCR( object ):
    def __init__( self, segmenter, feature_extractor, classifier):
        self.segmenter= segmenter
        self.feature_extractor= feature_extractor
        self.classifier= classifier

    def train( self, image_file ):
        '''feeds the training data to the OCR'''
        if not image_file.isGrounded():
            raise Exception("The provided file is not grounded")
        features= self.feature_extractor.extract( image_file.image, image_file.ground.segments )
        self.classifier.train( features, image_file.ground.classes )
        
    def ocr( self, image_file, show_steps=False ):
        '''performs ocr used trained classifier'''
        segments= self.segmenter.process( image_file.image )
        if show_steps:
            self.segmenter.display()
        features= self.feature_extractor.extract( image_file.image , segments )
        classes= self.classifier.classify( features )
        return classes, segments

########NEW FILE########
__FILENAME__ = opencv_utils
from numpy_utils import OverflowPreventer
from processor import DisplayingProcessor, ProcessorStack
import numpy
import cv2

class ImageProcessor( DisplayingProcessor ):
    def display( self, display_before=True ):
        if display_before:
            show_image_and_wait_for_key(self._input, "before "+self.__class__.__name__)
        show_image_and_wait_for_key(self._output,  "after " +self.__class__.__name__)
    def _process( self, image ):
        return self._image_processing( image )
    def _image_processing( self , image ):
        raise NotImplementedError( str(self.__class__) )

class BrightnessProcessor( ImageProcessor ):
    '''changes image brightness. 
    A brightness of -1 will make the image all black; 
    one of 1 will make the image all white'''
    PARAMETERS= ImageProcessor.PARAMETERS + {"brightness":0.0}
    def _image_processing( self , image ):
        b= self.brightness
        assert image.dtype==numpy.uint8
        assert -1<=b<=1
        image= image.copy()
        with OverflowPreventer(image) as img:
            img+=b*256
        return image

class ContrastProcessor( ImageProcessor ):
    '''changes image contrast. a scale of 1 will make no changes'''
    PARAMETERS= ImageProcessor.PARAMETERS + {"scale":1.0, "center":0.5}
    def _image_processing( self , image ):
        assert image.dtype==numpy.uint8
        image= image.copy()
        s,c= self.scale, self.center
        c= int(c*256)
        with OverflowPreventer(image) as img:
            if scale<=1:
                img*=scale
                img+= int(center*(1-scale))
            else:
                img-=center*(1 - 1/scale)
                img*=scale
        return image

class BlurProcessor( ImageProcessor ):
    '''changes image contrast. a scale of 1 will make no changes'''
    PARAMETERS= ImageProcessor.PARAMETERS + {"blur_x":0, "blur_y":0}
    def _image_processing( self , image ):
        assert image.dtype==numpy.uint8
        image= image.copy()
        x,y= self.blur_x, self.blur_y
        if x or y:
            x+= (x+1)%2 #opencv needs a
            y+= (y+1)%2 #odd number...
            image = cv2.GaussianBlur(image,(x,y),0)
        return image

def ask_for_key( return_arrow_keys=True ):
    key=128
    while key > 127:
        key=cv2.waitKey(0)
        if return_arrow_keys:
            if key in (65362,65364,65361,65363): #up, down, left, right
                return key
        key %= 256
    return key

def background_color( image, numpy_result=True ):
    result= numpy.median(numpy.median(image, 0),0).astype( numpy.int )
    if not numpy_result:
        try:
            result= tuple(map(int, result))
        except TypeError:
            result= (int(result),)
    return result
    
def show_image_and_wait_for_key( image, name="Image" ):
    '''Shows an image, outputting name. keygroups is a dictionary of keycodes to functions; they are executed when the corresponding keycode is pressed'''
    print "showing",name,"(waiting for input)"
    cv2.imshow('norm',image)
    return ask_for_key()




def draw_segments( image , segments, color=(255,0,0), line_width=1):
        '''draws segments on image'''
        for segment in segments:
            x,y,w,h= segment
            cv2.rectangle(image,(x,y),(x+w,y+h),color,line_width)

def draw_lines( image, ys, color= (255,0,0), line_width=1):
    '''draws horizontal lines'''
    for y in ys:
        cv2.line( image, (0,y), (image.shape[1], y), color, line_width )

def draw_classes( image, segments, classes ):
    assert len(segments)==len(classes)
    for s,c in zip(segments, classes):
        x,y,w,h=s
        cv2.putText(image,c,(x,y),0,0.5,(128,128,128))

########NEW FILE########
__FILENAME__ = processor
def _same_type(a,b):
    type_correct=False
    if type(a)==type(b):
        type_correct=True
    try: 
        if isinstance(a, b):
            type_correct=True
    except TypeError: #v may not be a class or type, but an int, a string, etc
        pass
    return type_correct

def _broadcast( src_processor, src_atr_name, dest_processors, dest_atr_name, transform_function):
    '''To be used exclusively by create_broadcast.
    A broadcast function gets an attribute on the src_processor and 
    sets it (possibly under a different name) on dest_processors'''
    value= getattr( src_processor, src_atr_name)
    value= transform_function( value )
    for d in dest_processors:
        setattr(d, dest_atr_name, value )

def create_broadcast( src_atr_name, dest_processors, dest_atr_name=None, transform_function= lambda x:x):
    '''This method creates a function, intended to be called as a 
    Processor posthook, that copies some of the processor's attributes
    to other processors'''
    from functools import partial
    if dest_atr_name==None:
        dest_atr_name= src_atr_name
    if not hasattr( dest_processors, "__iter__"): # a single processor was given instead
        dest_processors= [dest_processors]
    return partial( _broadcast, src_atr_name=src_atr_name, dest_processors=dest_processors, dest_atr_name=dest_atr_name, transform_function=transform_function)

class Parameters( dict ):
    def __add__(self, other):
        d3= Parameters()
        d3.update(self)
        d3.update(other)
        return d3

class Processor( object ):
    '''In goes something, out goes another. Processor.process() models 
    the behaviour of a function, where there are some stored parameters 
    in the Processor instance. Further, it optionally calls arbitrary 
    functions before and after processing (prehooks, posthooks)'''
    PARAMETERS= Parameters()
    def __init__(self, **args):
        '''sets default parameters'''
        for k,v in self.PARAMETERS.items():
            setattr(self, k, v)
        self.set_parameters(**args)
        self._prehooks= [] #functions (on input) to be executed before processing
        self._poshooks= [] #functions (on output) to be executed after processing

    def get_parameters( self ):
        '''returns a dictionary with the processor's stored parameters'''
        parameter_names= self.PARAMETERS.keys()
        parameter_values= [getattr(processor, n) for n in parameter_names]
        return dict( zip(parameter_names, parameter_values ) )
        
    def set_parameters( self, **args ):
        '''sets the processor stored parameters'''
        for k,v in self.PARAMETERS.items():
            new_value= args.get(k)
            if new_value!=None:
                if not _same_type(new_value, v):
                    raise Exception( "On processor {0}, argument {1} takes something like {2}, but {3} was given".format( self, k, v, new_value))
                setattr(self, k, new_value)
        not_used= set(args.keys()).difference( set(self.PARAMETERS.keys()))
        not_given= set(self.PARAMETERS.keys()).difference( set(args.keys()) )
        return not_used, not_given

    def _process( self, arguments ):
        raise NotImplementedError(str(self.__class__)+"."+"_process")
    

    
    def add_prehook( self, prehook_function ):
        self._prehooks.append( prehook_function )
    
    def add_poshook( self, poshook_function ):
        self._poshooks.append( poshook_function )
    
     
    def process( self, arguments):
        self._input= arguments
        for prehook in self._prehooks:
            prehook( self )
        output= self._process(arguments)
        self._output= output
        for poshook in self._poshooks:
            poshook( self )
        return output

class DisplayingProcessor( Processor ):
    def display(self, display_before=False):
        '''Show the last effect this processor had - on a GUI, for 
        example. If show_before is True, show the "state before 
        processor" before'''
        raise NotImplementedError

class ProcessorStack( Processor ):
    '''a stack of processors. Each processor's output is fed to the next'''
    def __init__(self, processor_instances=[], **args):
        self.set_processor_stack( processor_instances )
        Processor.__init__(self, **args)

    def set_processor_stack( self, processor_instances ):
        assert all( isinstance(x, Processor) for x in processor_instances )
        self.processors= processor_instances

    def get_parameters( self ):
        '''gets from all wrapped processors'''
        d= {}
        for p in self.processors:
            parameter_names= p.PARAMETERS.keys()
            parameter_values= [getattr(p, n) for n in parameter_names]
            d.update( dict(zip(parameter_names, parameter_values )) )
        return d

    def set_parameters( self, **args ):
        '''sets to all wrapped processors'''
        not_used= set()
        not_given=set()
        for p in self.processors:
            nu, ng= p.set_parameters( **args )
            not_used=  not_used.union(nu)
            not_given= not_given.union(ng)
        return not_used, not_given

    def _process( self, arguments ):
        for p in self.processors:
            arguments= p.process( arguments )
        return arguments

class DisplayingProcessorStack( ProcessorStack ):
    def display(self, display_before=False):
        if display_before:
            pr= self.processors[1:]
            self.processors.display( display_before=True )
        else:
            pr= self.processors
        for p in pr:
            if hasattr(p, "display"):
                p.display( display_before= False )

########NEW FILE########
__FILENAME__ = segmentation
from opencv_utils import show_image_and_wait_for_key, draw_segments, BlurProcessor
from processor import DisplayingProcessor, DisplayingProcessorStack, create_broadcast
from segmentation_aux import SegmentOrderer
from segmentation_filters import create_default_filter_stack, Filter, NearLineFilter
import numpy
import cv2

SEGMENT_DATATYPE=   numpy.uint16
SEGMENT_SIZE=       4
SEGMENTS_DIRECTION= 0 # vertical axis in numpy

def segments_from_numpy( segments ):
    '''reverses segments_to_numpy'''
    segments= segments if SEGMENTS_DIRECTION==0 else segments.tranpose()
    segments= [map(int,s) for s in segments]
    return segments

def segments_to_numpy( segments ):
    '''given a list of 4-element tuples, transforms it into a numpy array'''
    segments= numpy.array( segments, dtype=SEGMENT_DATATYPE, ndmin=2)   #each segment in a row
    segments= segments if SEGMENTS_DIRECTION==0 else numpy.transpose(segments)
    return segments

def best_segmenter(image):
    '''returns a segmenter instance which segments the given image well'''
    return ContourSegmenter()

def region_from_segment( image, segment ):
    '''given a segment (rectangle) and an image, returns it's corresponding subimage'''
    x,y,w,h= segment
    return image[y:y+h,x:x+w]


class RawSegmenter( DisplayingProcessor ):
    '''A image segmenter. input is image, output is segments'''    
    def _segment( self, image ):
        '''segments an opencv image for OCR. returns list of 4-element tuples (x,y,width, height).'''
        #return segments
        raise NotImplementedError()

    def _process( self, image):
        segments= self._segment(image)
        self.image, self.segments= image, segments
        return segments

class FullSegmenter( DisplayingProcessorStack ):
    pass

class RawContourSegmenter( RawSegmenter ):
    PARAMETERS=  RawSegmenter.PARAMETERS + {"block_size":11, "c":10 }
    def _segment( self, image ):
        self.image= image
        image= cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
        image = cv2.adaptiveThreshold(image, maxValue=255, adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C, thresholdType=cv2.THRESH_BINARY, blockSize=self.block_size, C=self.c)
        contours,hierarchy = cv2.findContours(image,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
        segments= segments_to_numpy( [cv2.boundingRect(c) for c in contours] )
        self.contours, self.hierarchy= contours, hierarchy #store, may be needed for debugging
        return segments
    def display(self, display_before=False):
        copy= self.image.copy()
        if display_before:
            show_image_and_wait_for_key(copy, "image before segmentation")
        copy.fill( (255,255,255) )
        cv2.drawContours(copy, self.contours, contourIdx=-1, color=(0,0,0))
        show_image_and_wait_for_key( copy, "ContourSegmenter contours")
        copy= self.image.copy()
        draw_segments( copy, self.segments)
        show_image_and_wait_for_key(copy, "image after segmentation by "+self.__class__.__name__)

class ContourSegmenter( FullSegmenter ):
    def __init__(self, **args):
        filters= create_default_filter_stack()
        stack = [BlurProcessor(), RawContourSegmenter()] + filters + [SegmentOrderer()]
        FullSegmenter.__init__(self, stack, **args)
        stack[0].add_prehook( create_broadcast( "_input", filters, "image" ) )


########NEW FILE########
__FILENAME__ = segmentation_aux
from processor import Processor, DisplayingProcessor
from opencv_utils import draw_lines, show_image_and_wait_for_key
import numpy
import cv2

class SegmentOrderer( Processor ):
    PARAMETERS= Processor.PARAMETERS + {"max_line_height":20, "max_line_width":10000}
    def _process( self, segments ):
        '''sort segments in read order - left to right, up to down'''
        #sort_f= lambda r: max_line_width*(r[1]/max_line_height)+r[0]
        #segments= sorted(segments, key=sort_f)
        #segments= segments_to_numpy( segments )
        #return segments
        mlh, mlw= self.max_line_height, self.max_line_width
        s= segments.astype( numpy.uint32 ) #prevent overflows
        order= mlw*(s[:,1]/mlh)+s[:,0]
        sort_order= numpy.argsort( order )
        return segments[ sort_order ]
        

class LineFinder( DisplayingProcessor ):
    @staticmethod
    def _guess_lines( ys, max_lines=50, confidence_minimum=0.0 ):
        '''guesses and returns text inter-line distance, number of lines, y_position of first line'''
        ys= ys.astype( numpy.float32 )
        compactness_list, means_list, diffs, deviations= [], [], [], []
        start_n= 1
        for k in range(start_n,max_lines):
            compactness, classified_points, means = cv2.kmeans( data=ys, K=k, bestLabels=None, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER, 1, 10), attempts=2, flags=cv2.KMEANS_PP_CENTERS)
            means=numpy.sort(means, axis=0)
            means_list.append( means )
            compactness_list.append( compactness )
            if k<3:
                tmp1= [1,2,500, 550] #forge data for bad clusters
            else:
                #calculate the center of each cluster. Assuming lines are equally spaced...
                tmp1=numpy.diff(means, axis=0) #diff will be equal or very similar
            tmp2= numpy.std(tmp1)/numpy.mean(means) #so variance is minimal
            tmp3= numpy.sum( (tmp1-numpy.mean(tmp1))**2) #root mean square deviation, more sensitive than std
            diffs.append(tmp1)
            deviations.append(tmp3)
        
        compactness_list= numpy.diff(numpy.log( numpy.array(compactness_list)+0.01 )) #sum small amount to avoid log(0)
        deviations= numpy.array( deviations[1:] )
        deviations[0]= numpy.mean( deviations[1:] )
        compactness_list= (compactness_list-numpy.mean(compactness_list))/numpy.std(compactness_list)
        deviations= (deviations-numpy.mean(deviations))/numpy.std(deviations)
        aglomerated_metric= 0.1*compactness_list + 0.9*deviations
        
        i= numpy.argmin(aglomerated_metric)+1
        lines= means_list[i]
        
        #calculate confidence
        betterness= numpy.sort(aglomerated_metric, axis=0)
        confidence= ( betterness[1] - betterness[0]) / ( betterness[2] - betterness[1])
        if confidence<confidence_minimum:
            raise Exception("low confidence")
        return lines #still floating points
        
    def _process( self, segments ):
        segment_tops=       segments[:,1]
        segment_bottoms=    segment_tops+segments[:,3]
        tops=               self._guess_lines( segment_tops )
        bottoms=            self._guess_lines( segment_bottoms )
        if len(tops)!=len(bottoms):
            raise Exception("different number of lines")
        middles=                    (tops+bottoms)/2
        topbottoms=                 numpy.sort( numpy.append( tops, bottoms ) )
        topmiddlebottoms=           numpy.sort( reduce(numpy.append, ( tops, middles, bottoms )) )
        self.lines_tops=             tops
        self.lines_bottoms=          bottoms
        self.lines_topbottoms=       topbottoms
        self.lines_topmiddlebottoms= topmiddlebottoms
        return segments
    
    def display(self, display_before=False):
        copy= self.image.copy()
        draw_lines( copy, self.lines_tops,    (0,0,255) )
        draw_lines( copy, self.lines_bottoms, (0,255,0) )
        show_image_and_wait_for_key( copy, "line starts and ends")
        

def guess_segments_lines( segments, lines, nearline_tolerance=5.0 ):
    '''given segments, outputs a array of line numbers, or -1 if it 
    doesn't belong to any'''
    ys= segments[:,1]
    closeness= numpy.abs( numpy.subtract.outer(ys,lines) ) #each row a y, each collumn a distance to each line 
    line_of_y= numpy.argmin( closeness, axis=1)
    distance= numpy.min(closeness, axis=1)
    bad= distance > numpy.mean(distance)+nearline_tolerance*numpy.std(distance)
    line_of_y[bad]= -1
    return line_of_y



def contained_segments_matrix( segments ):
    '''givens a n*n matrix m, n=len(segments), in which m[i,j] means
    segments[i] is contained inside segments[j]'''
    x1,y1= segments[:,0], segments[:,1]
    x2,y2= x1+segments[:,2], y1+segments[:,3]
    n=len(segments)
    
    x1so, x2so,y1so, y2so= map(numpy.argsort, (x1,x2,y1,y2))
    x1soi,x2soi, y1soi, y2soi= map(numpy.argsort, (x1so, x2so, y1so, y2so)) #inverse transformations
    o1= numpy.triu(numpy.ones( (n,n) ), k=1).astype(bool) # let rows be x1 and collumns be x2. this array represents where x1<x2
    o2= numpy.tril(numpy.ones( (n,n) ), k=0).astype(bool) # let rows be x1 and collumns be x2. this array represents where x1>x2
    
    a_inside_b_x= o2[x1soi][:,x1soi] * o1[x2soi][:,x2soi] #(x1[a]>x1[b] and x2[a]<x2[b])
    a_inside_b_y= o2[y1soi][:,y1soi] * o1[y2soi][:,y2soi] #(y1[a]>y1[b] and y2[a]<y2[b])
    a_inside_b= a_inside_b_x*a_inside_b_y
    return a_inside_b

########NEW FILE########
__FILENAME__ = segmentation_filters
from opencv_utils import show_image_and_wait_for_key, BrightnessProcessor, draw_segments, draw_lines
from segmentation_aux import contained_segments_matrix, LineFinder, guess_segments_lines
from processor import DisplayingProcessor, create_broadcast
import numpy


def create_default_filter_stack():
    stack= [LargeFilter(), SmallFilter(), LargeAreaFilter(), ContainedFilter(), LineFinder(), NearLineFilter()]
    stack[4].add_poshook( create_broadcast( "lines_topmiddlebottoms", stack[5] ) )
    return stack


class Filter( DisplayingProcessor ):
    PARAMETERS= DisplayingProcessor.PARAMETERS
    '''A filter processes given segments, returning only the desirable
    ones'''
    def display( self, display_before=False, image_override=None ):
        '''shows the effect of this filter'''
        if not image_override is None:
            copy= image_override
        else:
            try:
                copy= self.image.copy()
            except AttributeError:
                raise Exception("You need to set the Filter.image attribute for displaying")
            copy= BrightnessProcessor(brightness=0.6).process( copy )
        s, g= self._input, self.good_segments_indexes
        draw_segments( copy, s[g], (0,255,0) )
        draw_segments( copy, s[True-g], (0,0,255) )
        show_image_and_wait_for_key( copy, "segments filtered by "+self.__class__.__name__)
    def _good_segments( self, segments ):
        raise NotImplementedError
    def _process( self, segments):
        good= self._good_segments(segments)
        self.good_segments_indexes= good
        segments= segments[good]  
        if not len(segments):
            raise Exception("0 segments after filter "+self.__class__.__name__)
        return segments

class LargeFilter( Filter ):
    '''desirable segments are larger than some width or height'''
    PARAMETERS= Filter.PARAMETERS + {"min_width":4, "min_height":8}
    def _good_segments( self, segments ):
        good_width=  segments[:,2] >= self.min_width
        good_height= segments[:,3] >= self.min_height
        return good_width * good_height  #AND

class SmallFilter( Filter ):
    '''desirable segments are smaller than some width or height'''
    PARAMETERS= Filter.PARAMETERS + {"max_width":30, "max_height":50}
    def _good_segments( self, segments ):
        good_width=  segments[:,2]  <= self.max_width
        good_height= segments[:,3] <= self.max_height
        return good_width * good_height  #AND
        
class LargeAreaFilter( Filter ):
    '''desirable segments' area is larger than some'''
    PARAMETERS= Filter.PARAMETERS + {"min_area":45}
    def _good_segments( self, segments ):
        return (segments[:,2]*segments[:,3]) >= self.min_area

class ContainedFilter( Filter ):
    '''desirable segments are not contained by any other'''
    def _good_segments( self, segments ):
        m= contained_segments_matrix( segments )
        return (True - numpy.max(m, axis=1))

class NearLineFilter( Filter ):
    PARAMETERS= Filter.PARAMETERS + {"nearline_tolerance":5.0} # percentage distance stddev
    '''desirable segments have their y near a line'''
    def _good_segments( self, segments ):
        lines= guess_segments_lines(segments, self.lines_topmiddlebottoms, nearline_tolerance=self.nearline_tolerance)
        good= lines!=-1
        return good

########NEW FILE########
__FILENAME__ = tesseract_utils
import numpy

from classification import classes_from_numpy, classes_to_numpy
from segmentation import segments_from_numpy, segments_to_numpy


    
def read_boxfile( path ):
    classes=  []
    segments= []
    with open(path) as f:
        for line in f:
            s= line.split(" ")
            assert len(s)==6
            assert s[5]=='0\n'
            classes.append( s[0].decode('utf-8') )
            segments.append( map(int, s[1:5]))
    return classes_to_numpy(classes), segments_to_numpy(segments)

def write_boxfile(path, classes, segments):
    classes, segments= classes_from_numpy(classes), segments_from_numpy(segments)
    with open(path, 'w') as f:
        for c,s in zip(classes, segments):
            f.write( c.encode('utf-8')+' '+ ' '.join(map(str, s))+" 0\n")

########NEW FILE########
