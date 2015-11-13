__FILENAME__ = IABackgroundRenderer
#
#  IABackgroundRenderer.py
from objc import *
from Foundation import *
from AppKit import *
from IAImageView import IAImageView
from  math import floor, ceil

class IABackgroundRenderer(object):
	def moveBy_(self,by):
		pass

	def canMove(self):
		return NO

class IAColorBackgroundRenderer(IABackgroundRenderer):
	color = None

	def __init__(self,nscolor):
		self.color = nscolor

	def drawRect_(self,rect):
		if self.color is None: return

		self.color.set()
		NSRectFill(rect)

class IAImageBackgroundRenderer(IABackgroundRenderer):
	backgroundImage = None
	backgroundOffset = (0,0)
	composite = NSCompositeCopy

	def __init__(self,image):
			self.backgroundImage = image
			size = image.size()

			# background may be tiny and somehow 2000 loop iterations in drawRect are SLOOOOOW
			# so make sure that image is large enough to be drawn in few iterations
			xtimes = ceil(320.0 / size.width)
			ytimes = ceil(240.0 / size.height)

			#if xtimes > 2 or ytimes > 2:
			# paint it anyway, to render over predictable background color
			# coreanimation ignores NSCompositeCopy
			bigimage = NSImage.alloc().initWithSize_((size.width*xtimes,size.height*ytimes))
			bigsize = bigimage.size()
			whole = NSMakeRect(0,0,bigsize.width,bigsize.height);
			self.composite = NSCompositeSourceOver
			bigimage.lockFocus();
			NSColor.magentaColor().set()
			NSRectFill(whole)
			self.drawRect_(whole);
			bigimage.unlockFocus();
			self.backgroundImage = bigimage
			self.composite = NSCompositeCopy

	def canMove(self):
		return YES

	def moveBy_(self,delta):
		size = self.backgroundImage.size()
		self.backgroundOffset = ((self.backgroundOffset[0] - delta[0]) % size.width,
								 (self.backgroundOffset[1] - delta[1]) % size.height)

	def drawRect_(self,rect):
		size = self.backgroundImage.size()

		widthend = rect.origin.x + rect.size.width
		heightend = rect.origin.y + rect.size.height

		currentx = rect.origin.x // size.width * size.width  - self.backgroundOffset[0]
		currenty = rect.origin.y // size.height * size.height  - self.backgroundOffset[1]
		wholeimage = ((0,0),size)

		# totally depends on view doing the clipping anyway
		while currenty < heightend:
			drawnwidth = 0
			currentx = rect.origin.x // size.width * size.width - self.backgroundOffset[0]
			while currentx < widthend:
				self.backgroundImage.drawInRect_fromRect_operation_fraction_(((currentx,currenty),size), wholeimage, self.composite, 1.0)
				currentx += size.width
			currenty += size.height


########NEW FILE########
__FILENAME__ = IACollectionItem
#
#  IACollectionItem.py

from Foundation import *
from objc import *
from AppKit import *
from random import randint
from IAImageView import IAImageView
from IAImageViewInteractive import IAImageViewInteractive
from IABackgroundRenderer import *

class IACollectionViewItem(NSCollectionViewItem):
    def setSelected_(self, sel):
        NSCollectionViewItem.setSelected_(self,sel)
        col = self.collectionView()
        if sel and col is not None:
            col.updateSelection()

    def imageChangedNotification_(self,sender):
        view = self.view()
        if view is not None:
            subview = view.viewWithTag_(1234);
            if subview is not None:
                subview.setImage_(sender.object().image);

class IACollectionImageView(IAImageView):
    collectionItem = None;
    drawBorder = False

    def initWithFrame_(self, frame):
        self = super(IACollectionImageView, self).initWithFrame_(frame)
        if self:
            # initialization code here
            types = [NSFilenamesPboardType]
            types.append(NSImage.imagePasteboardTypes())
            self.registerForDraggedTypes_(types);
            pass
        return self

    def draggingEntered_(self,sender):
        if NSImage.canInitWithPasteboard_(sender.draggingPasteboard()):
            self.imageFade = 0.2
            image = NSImage.alloc().initWithPasteboard_(sender.draggingPasteboard())
            if image is not None:
                self.setBackgroundRenderer_(IAImageBackgroundRenderer(image))
                self.setNeedsDisplay_(YES)
                return NSDragOperationCopy | NSDragOperationGeneric | NSDragOperationMove

    def draggingExited_(self,sender):
        self.imageFade = 1.0
        self.setBackgroundRenderer_(self.collectionItem.representedObject())
        self.setNeedsDisplay_(YES)

    def prepareForDragOperation_(self,sender):
        self.imageFade = 1.0
        self.setNeedsDisplay_(YES)
        if NSImage.canInitWithPasteboard_(sender.draggingPasteboard()):
            return YES
        else:
            self.draggingExited_(sender)

    def performDragOperation_(self,sender):
        image = NSImage.alloc().initWithPasteboard_(sender.draggingPasteboard())
        if image is not None:
            self.collectionItem.setSelected_(YES)
            self.collectionItem.collectionView().setBackgroundImage_(image);
            self.setNeedsDisplay_(YES)
            return YES
        else:
            self.draggingExited_(sender)


    def tag(self):
        return 1234; # magic for interface builder

    def mouseEntered_(self,event):
        self.imageFade = 0.85
        self.drawBorder = True

    def mouseExited_(self,event):
        self.imageFade = 1
        pass

    def drawRect_(self,rect):
        if self.drawBorder:
            self.imageFade = 0.85
            super(IACollectionImageView, self).drawRect_(rect);
            self.imageFade = 1
            path = NSBezierPath.bezierPath()
            size = self.frame().size;
            NSColor.selectedControlColor().colorWithAlphaComponent_(0.8).set()
            path.setLineWidth_(4)
            path.appendBezierPathWithRoundedRect_xRadius_yRadius_(((3,3),(size.width-6,size.height-6)),8,8)
            path.stroke()
        else:
            super(IACollectionImageView, self).drawRect_(rect);


    def mouseUp_(self,event):
        self.drawBorder = False
        self.setNeedsDisplay_(YES)
        if self.collectionItem is not None:
            self.collectionItem.setSelected_(YES)

    def mouseDown_(self,event):
        self.drawBorder = True
        self.setNeedsDisplay_(YES)



class IACollectionView(NSCollectionView):
    imageView = objc.IBOutlet()
    image = None

    #def frameChanged_(self,bla):
    #   self.setMaxItemSize_((300,300))
        #for i in self.content():
        #   i.view().setNeedsDisplay_(YES)
    #   pass

    def awakeFromNib(self):
        self.setAllowsMultipleSelection_(NO);
        self.sendNotification_(u"SelectionChanged");
        #self.setPostsFrameChangedNotifications_(YES)
#       NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self,self.frameChanged_,NSViewFrameDidChangeNotification,self);

    def sendNotification_(self,name):
        n = NSNotification.notificationWithName_object_(name,self)
        NSNotificationQueue.defaultQueue().enqueueNotification_postingStyle_coalesceMask_forModes_(n,NSPostWhenIdle,NSNotificationCoalescingOnName,None)


    def selectionChangedNotification_(self,sender):
        self.updateSelection();

    def updateSelection(self):
        idx = self.selectionIndexes().firstIndex()
        if idx != NSNotFound:
            self.imageView.setBackgroundRenderer_(self.content()[idx]);

    def setBackgroundImage_(self,img):
        bgr = IAImageBackgroundRenderer(img);
        content = NSMutableArray.arrayWithArray_(self.content());
        idx = self.selectionIndexes().firstIndex()
        if idx != NSNotFound:
            content[idx] = bgr
            self.setContent_(content);
            self.sendNotification_(u"SelectionChanged");

    def setImage_(self,img):
        self.image = img
        if img is not None:
            size = img.size()
            self.setMaxItemSize_((max(100,size.width*2),max(100,size.height*2)))
            self.setMinItemSize_((40,40))

        self.sendNotification_(u"ImageChanged");
        pass

    def newItemForRepresentedObject_(self,obj):
        colitem = super(IACollectionView,self).newItemForRepresentedObject_(obj);

        view  = colitem.view().viewWithTag_(1234);
        #view = IACollectionImageView.alloc().initWithFrame_(((0,0),image.size()))
        view.setImage_(self.image)
        view.setBackgroundRenderer_(obj)
        view.zoomToFill(0.8);
        #colitem = IACollectionViewItem.alloc().init()
        #colitem.setRepresentedObject_(obj)
        #colitem.setView_(view)
        view.collectionItem = colitem

        # FIXME: remove from notification queue when deallocing!
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(colitem,colitem.imageChangedNotification_, u"ImageChanged", self)
        return colitem;



########NEW FILE########
__FILENAME__ = IAImage
#
#  IAImage.py
from objc import *
from Foundation import *
from AppKit import *
from math import log

class Quantizer(object):
    def supportsIeMode(self):
        return False

    def preferredDithering(self):
        return True

    def numberOfColorsToQuality(self, colors):
        return colors;

    def versionId(self, colors, dithering, ieMode):
        return "c%d:m%s:d%d%d" % (self.numberOfColorsToQuality(colors), self.__class__.__name__, dithering, ieMode)

class Pngquant(Quantizer):
    def supportsIeMode(self):
        return True

    def launchArguments(self, dither, colors, ieMode):
        args = ["--floyd" if dither else "--nofs","%d" % colors];
        if ieMode:
            args.insert(0,"--iebug");
        return ("pngquant", args)

class Pngnq(Quantizer):
    def launchArguments(self, dither, colors, ieMode):
        return ("pngnq", ["-Q","f" if dither else "n","-n","%d" % colors])

class Posterizer(Quantizer):
    def preferredDithering(self):
        return False

    def numberOfColorsToQuality(self, c):
        return round(6+c*100/256)

    def launchArguments(self, dither, colors, ieMode):
        args = ["%d" % self.numberOfColorsToQuality(colors)];
        if dither:
            args.insert(0,"-d")
        return ("posterizer",args);

class Blurizer(Quantizer):
    def preferredDithering(self):
        return True

    def versionId(self, colors, dithering, ieMode):
        return "blur%d" % self.numberOfColorsToQuality(colors)

    def numberOfColorsToQuality(self, c):
        return int(2+ 24-log(c,2)*3)

    def launchArguments(self, dither, colors, ieMode):
        args = ["%d" % self.numberOfColorsToQuality(colors)];
        return ("blurizer",args);


class IAImage(NSObject):
    _image = None
    _imageData = None

    path = None
    _sourceFileSize = None

    versions = None

    _numberOfColors = 256;

    _quantizationMethod = 0; # 0 = pngquant; 1 = pngnq; 2 = posterizer
    _quantizationMethods = [
        Pngquant(),
        Pngnq(),
        None, # separator
        Blurizer(),
        Posterizer(),
    ]
    _dithering = YES
    _ieMode = NO

    callbackWhenImageChanges = None

    def init(self):
        self = super(IAImage, self).init()
        self.versions = {};
        return self

    def setCallbackWhenImageChanges_(self, documentToCallback):
        self.callbackWhenImageChanges = documentToCallback;
        self.update()

    def setImage_(self,image):
        self._image = image

    def image(self):
        return self._image

    def imageData(self):
        return self._imageData;

    def sourceFileSize(self):
		return self._sourceFileSize;

    def setPath_(self,path):
		self.path = path
		(attrs,error) = NSFileManager.defaultManager().attributesOfItemAtPath_error_(self.path,None);
		self._sourceFileSize = attrs.objectForKey_(NSFileSize) if attrs is not None and error is None else None;

    def ieMode(self):
        return self._ieMode

    def setIeMode_(self,val):
        self._ieMode = int(val) > 0;
        if self._ieMode and not self.quantizer().supportsIeMode():
            self.setQuantizationMethod_(0);
        self.update()

    def dithering(self):
        return self._dithering

    def setDithering_(self,val):
        self._dithering = int(val) > 0
        self.update()

    def numberOfColors(self):
        return self._numberOfColors

    def setNumberOfColors_(self,num):
        self._numberOfColors = int(num)
        self.update()

    def quantizationMethod(self):
        return self._quantizationMethod

    def quantizer(self):
        return self._quantizationMethods[self._quantizationMethod]

    def setQuantizationMethod_(self,num):
        self._quantizationMethod = num

        quantizer = self.quantizer()
        if not quantizer.supportsIeMode():
            self.setIeMode_(False)
        if quantizer.preferredDithering() is not None:
            self.setDithering_(quantizer.preferredDithering())
        self.update()

    def isBusy(self):
        if self.path is None: return False
        id = self.currentVersionId()
        if id not in self.versions: return False # not sure about this
        return not self.versions[id].isDone;

    def update(self):
        if self.path:
            id = self.currentVersionId()

            if self.numberOfColors() > 256:
                self._imageData = NSData.dataWithContentsOfFile_(self.path);
                self.setImage_(NSImage.alloc().initByReferencingFile_(self.path));

                if self.callbackWhenImageChanges is not None: self.callbackWhenImageChanges.imageChanged();

            elif id not in self.versions:
                self.versions[id] = IAImageVersion.alloc().init()
                self.versions[id].generateFromPath_method_dither_iemode_colors_callback_(self.path, self.quantizer(), self.dithering(), self.ieMode(), self.numberOfColors(), self)

                if self.callbackWhenImageChanges is not None: self.callbackWhenImageChanges.updateProgressbar();

            elif self.versions[id].isDone:
                self._imageData = self.versions[id].imageData
                self.setImage_(NSImage.alloc().initWithData_(self._imageData))

                if self.callbackWhenImageChanges is not None: self.callbackWhenImageChanges.imageChanged();

    def currentVersionId(self):
        return self.quantizer().versionId(self.numberOfColors(), self.dithering(), self.ieMode());

    def destroy(self):
        self.callbackWhenImageChanges = None
        for id in self.versions:
            self.versions[id].destroy()
        self.versions = {}


class IAImageVersion(NSObject):
    imageData = None
    isDone = False

    task = None
    outputPipe = None
    callbackWhenFinished = None

    def generateFromPath_method_dither_iemode_colors_callback_(self,path,quantizer,dither,ieMode,colors,callbackWhenFinished):

        self.isDone = False
        self.callbackWhenFinished = callbackWhenFinished

        (executable, args) = quantizer.launchArguments(dither, colors, ieMode)

        task = NSTask.alloc().init()

        task.setLaunchPath_(NSBundle.mainBundle().pathForResource_ofType_(executable, ""))
        task.setCurrentDirectoryPath_(NSBundle.mainBundle().resourcePath())
        task.setArguments_(args);

        # pngout works best via standard input/output
        file = NSFileHandle.fileHandleForReadingAtPath_(path);
        task.setStandardInput_(file);

        # get output via pipe
        # use pipe's file handle to construct NSData object asynchronously
        outputPipe = NSPipe.pipe();
        task.setStandardOutput_(outputPipe);

        # pipe *must* be read, otheriwse task will block waiting for I/O
        handle = outputPipe.fileHandleForReading();
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, self.onHandleReadToEndOfFile_, NSFileHandleReadToEndOfFileCompletionNotification, handle);
        handle.readToEndOfFileInBackgroundAndNotify()

        task.launch();
        return task;

    def onHandleReadToEndOfFile_(self,notification):
        self.isDone = True

        self.imageData = notification.userInfo().objectForKey_(NSFileHandleNotificationDataItem);
        if self.callbackWhenFinished is not None:
            self.callbackWhenFinished.update()

    # FIXME: use dealloc and super()?
    def destroy(self):
        NSNotificationCenter.defaultCenter().removeObserver_(self);
        self.callbackWhenFinished = None
        if self.task:
            self.task.terminate();
            self.task = None
        if self.outputPipe:
            self.outputPipe.fileHandleForReading().closeFile()
            self.outputPipe = None



########NEW FILE########
__FILENAME__ = IAImageView
#
#  IAImageView.py

from objc import *
from Foundation import *
from AppKit import *
from math import ceil, floor

class IAImageView(NSView):
    _zoom = 2.0
    _image = None
    _alternateImage = None
    _drawAlternateImage = NO
    backgroundRenderer = None
    _smooth = YES
    backgroundOffset = (0,0)
    imageOffset = (0,0)
    imageFade = 1.0
    zoomingToFill = 0

    def setFrame_(self,rect):
        NSView.setFrame_(self,rect)
        if self.zoomingToFill: self.zoomToFill(self.zoomingToFill)

    @objc.IBAction
    def zoomIn_(self, sender):
        self.setZoom_(self.zoom() * 2.0);

    @objc.IBAction
    def zoomOut_(self,sender):
        self.setZoom_(self.zoom() / 2.0);

    def zoomToFill(self, zoom=1.0):
        self.zoomingToFill = zoom
        if self.image() is None: return
        size = self.image().size()
        framesize = self.frame().size
        zoom = min(framesize.width/size.width, framesize.height/size.height)*self.zoomingToFill
        if zoom > 1.0:
            zoom = min(4.0,floor(zoom))
        self._setZoom(zoom)

    def _limitImageOffset(self):
        if self.image() is None: return
        size = self.frame().size
        imgsize = self.image().size()

        w = (size.width + imgsize.width * self.zoom()) /2
        h = (size.height + imgsize.height * self.zoom()) /2

        self.imageOffset = (max(-w+15, min(w-15, self.imageOffset[0])), \
                            max(-h+15, min(h-15, self.imageOffset[1])))

    def smooth(self):
        return self._smooth;

    def setSmooth_(self,smooth):
        self._smooth = smooth
        NSGraphicsContext.currentContext().setImageInterpolation_(NSImageInterpolationHigh if smooth else NSImageInterpolationNone)
        self.setNeedsDisplay_(YES)

    def zoom(self):
        return self._zoom;

    def setZoom_(self,zoom):
        self.zoomingToFill = 0
        self._setZoom(zoom);

    def _setZoom(self,zoom):
        self._zoom = min(16.0,max(1.0/128.0,zoom))
        self._limitImageOffset()
        self.setNeedsDisplay_(YES)

    def image(self):
        return self._image;

    def setImage_(self,aImage):
        self._image=aImage
        if self._alternateImage and aImage:
            self._setScale_ofImage_(self._getScaleOfImage_(self._alternateImage), aImage);
        if self.zoomingToFill:
            self.zoomToFill(self.zoomingToFill)
        self.setDrawAlternateImage_(NO)

    def _getScaleOfImage_(self, image):
        w,h = image.size()
        rep = image.representations();
        if not rep or not rep.count(): return (0,0);
        return (rep[0].pixelsWide()/w, rep[0].pixelsHigh()/h);

    def _setScale_ofImage_(self, scale, image):
        rep = image.representations();
        if not rep or not rep.count(): return (0,0);
        image.setSize_((rep[0].pixelsWide()/scale[0], rep[0].pixelsHigh()/scale[1]));

    def alternateImage(self):
        return self._alternateImage;

    def setAlternateImage_(self,aImage):
        if self._image and aImage:
            self._setScale_ofImage_(self._getScaleOfImage_(aImage), self._image);
        self._alternateImage = aImage
        self.setNeedsDisplay_(YES)

    def drawAlternateImage(self):
        return self._drawAlternateImage;

    def setDrawAlternateImage_(self,tf):
        self._drawAlternateImage = tf
        self.setNeedsDisplay_(YES)

    def drawAlternateImage(self):
        return self._drawAlternateImage == True

    def setBackgroundRenderer_(self,renderer):
        self.backgroundRenderer = renderer;
        self.setNeedsDisplay_(YES)

#    def initWithFrame_(self, frame):
#        self = super(IAImageView, self).initWithFrame_(frame)
#        if self:
#            # initialization code here
#            pass
#        return self

    def isOpaque(self):
        return self.backgroundRenderer is not None

    def drawRect_(self,rect):
        if self.backgroundRenderer is not None: self.backgroundRenderer.drawRect_(rect);

        image = self.image() if not self.drawAlternateImage() else self.alternateImage();
        if image is None: return

        unscaled = abs(self.zoom() - 1.0) < 0.01;

        NSGraphicsContext.currentContext().setImageInterpolation_(NSImageInterpolationHigh if self.smooth() and not unscaled else NSImageInterpolationNone)

        frame = self.frame();
        imgsize = image.size()
        offx = (frame.size.width  - imgsize.width * self.zoom() )/2 + self.imageOffset[0]
        offy = (frame.size.height - imgsize.height * self.zoom() )/2 + self.imageOffset[1]

        x = (rect.origin.x - offx) / self.zoom()
        y = (rect.origin.y - offy) / self.zoom()

        if unscaled:
            x = ceil(x)
            y = ceil(y)

        imgrect = ((x,y), (rect.size.width / self.zoom(), rect.size.height / self.zoom()));
        image.drawInRect_fromRect_operation_fraction_(rect, imgrect, NSCompositeSourceOver, self.imageFade)


########NEW FILE########
__FILENAME__ = IAImageViewInteractive
#
#  IAImageViewInteractive.py
from objc import *
from Foundation import *
from AppKit import *
from IAImageView import IAImageView
from  math import floor

class IAImageViewInteractive(IAImageView):
    def initWithFrame_(self, frame):
        self = super(IAImageViewInteractive, self).initWithFrame_(frame)
        if self:
            types = [NSFilenamesPboardType]
            types.extend(NSImage.imagePasteboardTypes())
            self.registerForDraggedTypes_(types)
            pass
        return self

    controller = objc.IBOutlet()

    mouseIsDown = False
    dragBackground = False
    dragStart = (0,0)

    def draggingEntered_(self,sender):
        if self.controller.canSetDocumentImageFromPasteboard_(sender.draggingPasteboard()):
            self.imageFade = 0.85
            self.setNeedsDisplay_(YES)
            return NSDragOperationCopy | NSDragOperationGeneric | NSDragOperationMove

    def draggingExited_(self,sender):
        self.imageFade = 1.0
        self.setNeedsDisplay_(YES)

    def prepareForDragOperation_(self,sender):
        self.imageFade = 1.0
        self.setNeedsDisplay_(YES)
        return self.controller.canSetDocumentImageFromPasteboard_(sender.draggingPasteboard())

    def performDragOperation_(self,sender):
        return self.controller.setDocumentImageFromPasteboard_(sender.draggingPasteboard())

    def resetCursorRects(self):
        if self.image() is not None or self.backgroundRenderer is not None:
            curs = NSCursor.closedHandCursor() if self.mouseIsDown else NSCursor.openHandCursor()
            self.addCursorRect_cursor_(self.visibleRect(), curs)
            curs.setOnMouseEntered_(YES)

    def scrollWheel_(self,event):
        if event.deltaY() > 0:
            self.zoomIn_(None)
        elif event.deltaY() < 0:
            self.zoomOut_(None)

    def mouseExited_(self,event):
        self.imageFade=1.0
        self.setNeedsDisplay_(YES)

    def mouseEntered_(self,event):
        self.imageFade = 0.5
        self.setNeedsDisplay_(YES)

    def pointIsInImage_(self,point):
        if self.image() is None: return NO
        size = self.image().size();

        fsize = self.frame().size;
        w = max(50,size.width * self.zoom() +15) / 2  # add "border" around image to ease dragging of small ones
        h = max(50,size.height * self.zoom() +15) / 2

        return point.x >= self.imageOffset[0]+fsize.width/2-w and point.y >= self.imageOffset[1]+fsize.height/2-h and \
               point.x <= self.imageOffset[0]+fsize.width/2+w and point.y <= self.imageOffset[1]+fsize.height/2+h

    def mouseDragged_(self,event):
        point = self.convertPoint_fromView_(event.locationInWindow(), None);
        delta = (point.x - self.dragStart[0], point.y - self.dragStart[1])
        self.dragStart = (point.x, point.y)
        if self.backgroundRenderer is not None and self.dragBackground:
            self.backgroundRenderer.moveBy_(delta)
        elif self.image() is not None:
            size = self.frame().size
            self.imageOffset = (self.imageOffset[0] + delta[0],
                                self.imageOffset[1] + delta[1])
            self._limitImageOffset()

        self.setNeedsDisplay_(YES)

    def mouseChange_(self, isDown):
        self.mouseIsDown = isDown
        self.window().invalidateCursorRectsForView_(self);

    def mouseDown_(self,event):
        point = self.convertPoint_fromView_(event.locationInWindow(), None)

        if self.backgroundRenderer is None or not self.backgroundRenderer.canMove():
            self.dragBackground = False
        else:
            self.dragBackground = not self.pointIsInImage_(point)
            if (event.modifierFlags() & (NSShiftKeyMask | NSAlternateKeyMask | NSCommandKeyMask)):
                self.dragBackground = not self.dragBackground


        self.dragStart = (point.x,point.y)
        if event.clickCount()&3==2:
            self.imageOffset = (0,0)
            if self.zoomingToFill:
                self.setZoom_(1)
            else:
                self.zoomToFill()
            self.setNeedsDisplay_(YES)
        else:
            self.mouseChange_(YES);
            self.mouseDragged_(event)

    def magnifyWithEvent_(self, event):
        #NSLog("magnified by %f z = %f" % (event.magnification(), self.zoom()));

        oldzoom = self.zoom();
        # zoom < 1 requires different zooming speed than > 1
        if (oldzoom + event.magnification() > 1):
            zoom = ((oldzoom / 20) + event.magnification()/4) * 20;
        else:
            zoom = 1 / (1/oldzoom - event.magnification());

        # avoid crossing of the 1.0 boundary at wrong speed
        if (zoom > 1.0 and oldzoom < 1.0) or (zoom < 1.0 and oldzoom > 1.0):
            zoom = 1.0;

        self.setZoom_(max(0.25,zoom));

    #def keyDown_(self,event):
        #NSLog("key! %s" % event);

    def mouseUp_(self,event):
        self.mouseChange_(NO);

    def updateTouches_(self,event):
        touches = event.touchesMatchingPhase_inView_( NSTouchPhaseStationary, self);
        #NSLog("touches %s" % touches.allObjects());
        self.setDrawAlternateImage_((touches.count() >= 3))

    def otherMouseDown_(self,event):
        self.setDrawAlternateImage_(YES)

    def otherMouseUp_(self,event):
        self.setDrawAlternateImage_(NO)


########NEW FILE########
__FILENAME__ = IASlider
# coding=utf-8
#
#  IASlider.py

from objc import YES, NO, IBAction, IBOutlet
from Foundation import *
from AppKit import *

from math import pow,log

class IASlider(NSSlider):
    zoomView = objc.IBOutlet()

    def scrollWheel_(self,event):
        if self.zoomView is not None:
            self.zoomView.scrollWheel_(event)


class IAZoomTransformer(NSValueTransformer):
    def transformedValueClass(self):
        return NSNumber.__class__

    def allowsReverseTransformation(self):
        return YES

    def reverseTransformedValue_(self,zoom):
        result = NSNumber.numberWithFloat_(1.0/(4.0-zoom) if zoom < 3.0 else zoom-2.0)
        return result

    def transformedValue_(self,zoom):
        zoom = zoom or 1.0
        result = NSNumber.numberWithFloat_(max(0,4.0-1.0/zoom) if zoom < 1.0 else zoom+2.0)
        return result

class IAZoomTimesTransformer(NSValueTransformer):
    def transformedValue_(self,zoom):
        return u"%d×" % zoom if zoom >= 1.0 else [u"½×",u"⅓×",u"¼×"][min(2,int(round(1.0/zoom))-2)];

# converts numbers 0-257 to 0-9 range
class IABitDepthTransformer(NSValueTransformer):
    def transformedValueClass(self):
        return NSNumber.__class__

    def allowsReverseTransformation(self):
        return YES

    # colors to depth
    def transformedValue_(self,value):
        if value is None: return None;
        value = int(value);
        if (value > 256): return 9;
        if (value <= 2): return 1;
        return log(value,2);

    # depth to colors
    def reverseTransformedValue_(self,value):
        if value is None: return None;
        value = int(value);
        #NSLog("Reverse transforming from %d" % value);
        if (value > 8): return 257;
        if (value <= 1): return 2;
        return round(pow(2,value));

# displays 0-9 range as 0-256 and 2^24
class IABitDepthNameTransformer(NSValueTransformer):
    def transformedValue_(self,value):
        if value is None: return None;
        value = int(value);
        if (value > 256): return u"2²⁴"
        return "%d" % value;


# converts numbers 0-8 to 0-256 range
class IABitDepthReverseTransformer(NSValueTransformer):
    def transformedValueClass(self):
        return NSNumber.__class__

    # depth to colors
    def transformedValue_(self,value):
        if value is None: return None;
        value = int(value);
        if (value <= 1): return 2;
        return pow(2,value);



########NEW FILE########
__FILENAME__ = ImageAlphaDocument
# coding=utf-8
#
#  IAController.py

from objc import *
from Foundation import *
import IAImageView
from IACollectionItem import *
from IABackgroundRenderer import *
from IAImage import IAImage

class ImageAlphaDocument(ImageAlphaDocumentC):

	statusBarView = objc.IBOutlet()
	backgroundsView = objc.IBOutlet()
	progressBarView = objc.IBOutlet()
	savePanelView = objc.IBOutlet()

	def windowNibName(self):
		return u"ImageAlphaDocument"

	def windowControllerDidLoadNib_(self, aController):
		super(ImageAlphaDocument, self).windowControllerDidLoadNib_(aController)

		self._startWork();

		bgs = [
			IAImageBackgroundRenderer(self._getImage("textures/photoshop","png")),
			IAColorBackgroundRenderer(NSColor.redColor()),
			IAColorBackgroundRenderer(NSColor.greenColor()),
			IAColorBackgroundRenderer(NSColor.blueColor()),
			IAImageBackgroundRenderer(self._getImage("textures/461223192","jpg")),
			IAImageBackgroundRenderer(self._getImage("textures/A_MIXRED","jpeg")),
			IAImageBackgroundRenderer(self._getImage("textures/nature71","jpg")),
			IAImageBackgroundRenderer(self._getImage("textures/seawaterfull2","jpg")),
			IAImageBackgroundRenderer(self._getImage("textures/STONE4","jpeg")),
			IAImageBackgroundRenderer(self._getImage("textures/Rustpattern","jpeg")),
			IAImageBackgroundRenderer(self._getImage("textures/461223185","jpg")),
			IAImageBackgroundRenderer(self._getImage("textures/G_IRON3","jpg")),
		]
		self.backgroundsView.setContent_(bgs);

		self.zoomedImageView().window().setAcceptsMouseMovedEvents_(YES);
		self.zoomedImageView().setBackgroundRenderer_(bgs[0])

		if self.documentImage() is not None:
			self.setDisplayImage_(self.documentImage().image())
		   # self.setStatusMessage_("Opened " + NSFileManager.defaultManager().displayNameAtPath_(self.documentImage().path));
		else:
			self.setStatusMessage_("To get started, drop PNG image onto main area on the right");

		self.updateZoomedImageViewAlternateImage()


		self._endWork();

	def updateZoomedImageViewAlternateImage(self, zoomToFill=False):
		if self.zoomedImageView() is not None and self.documentImage() is not None:
			self.zoomedImageView().setAlternateImage_(self.documentImage().image())
			if zoomToFill:
				self.zoomedImageView().zoomToFill()

	def validateUserInterfaceItem_(self,item):
		# I can't find nice way to compare selectors in pyobjc, so here comes __repr__() hack (or non-hack I hope)
		if self.documentImage() is None and item.action().__repr__() in ["'saveDocument:'","'saveDocumentAs:'","'zoomIn:'","'zoomOut:'", "'toggleShowOriginal:'"]:
			return NO

		return super(ImageAlphaDocument, self).validateUserInterfaceItem_(item);


	def prepareSavePanel_(self, savePanel):
		delegate = NSApplication.sharedApplication().delegate()
		if delegate and delegate.imageOptimPath is not None:
			savePanel.setAccessoryView_(self.savePanelView);
		return YES

	def dataOfType_error_(self, typeName, outError):
		if url.isFileURL() or self.documentImage() is not None:
			return (self.documentImage().imageData(), None)
		return (None,None)

	def writeToURL_ofType_error_(self, url, typeName, outErorr):
		NSLog("write to %s type %s" % (url.path(), typeName));

		if url.isFileURL() or self.documentImage() is not None:
			data = self.documentImage().imageData();
			if data is not None:
				if NSFileManager.defaultManager().createFileAtPath_contents_attributes_(url.path(), data, None):
					self.optimizeFileIfNeeded_(url);
					return (True, None)

		return (NO,None)

	def readFromURL_ofType_error_(self, url, typeName, outError):
		NSLog("Reading file %s" % url.path());
		if not url.isFileURL():
			return (NO,None)
		return (self.setDocumentImageFromPath_(url.path()),None)

	def optimizeFileIfNeeded_(self,url):
		delegate = NSApplication.sharedApplication().delegate();
		if not delegate or delegate.imageOptimPath is None or not NSUserDefaults.standardUserDefaults().boolForKey_("Optimize"):
			return

		w = NSWorkspace.sharedWorkspace();
		result = w.openURLs_withAppBundleIdentifier_options_additionalEventParamDescriptor_launchIdentifiers_([url], "net.pornel.imageoptim", NSWorkspaceLaunchAsync|NSWorkspaceLaunchWithoutAddingToRecents, None, None)
		if (not result):
			result = w.openFile_withApplication_(url.path(), delegate.imageOptimPath);
			if (not result):
				NSLog("Could not launch ImageOptim for %s" % url);

	def setStatusMessage_(self,msg):
		NSLog("(status) %s", msg);
		if self.statusBarView is not None: self.statusBarView.setStringValue_(msg);

	def canSetDocumentImageFromPasteboard_(self,pboard):
# disabled until in-memory image support is done
#		 if NSImage.canInitWithPasteboard_(pboard):
#			 NSLog("image will handle that");
#			 return YES

		type = pboard.availableTypeFromArray_([NSFilenamesPboardType]);
		if type is not None:
		# FIXME: check for PNGs here
#			filenames = self.filenamesFromPasteboard_(pboard)
#			NSLog("Filenames %s" % filenames);
#			for f in filenames:
#				NSLog("drop file %s" % f);
			return YES

	def filenamesFromPasteboard_(self,pboard):
		data = pboard.dataForType_(NSFilenamesPboardType)
		if data is None: return []

		filenames, format, errorDescription = NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(
					data , kCFPropertyListImmutable, None, None)
		return filenames;

	def setDocumentImageFromPasteboard_(self,pboard):
		type = pboard.availableTypeFromArray_([NSFilenamesPboardType]);
		if type is not None:
			filenames = self.filenamesFromPasteboard_(pboard)
			for file in filenames:
				if self.setDocumentImageFromPath_(file):
					return YES

# disabled until in-memory image support is done
#		 if NSImage.canInitWithPasteboard_(pboard):
#			 image = NSImage.alloc().initWithPasteboard_(pboard);
#			 self.setDocumentImageFromImage_(image)
#			 return YES

		return NO

	def setDocumentImageFromPath_(self,path):
		image = NSImage.alloc().initWithContentsOfFile_(path)
		if image is None:
			#NSLog("img is none");
			return NO

		docimg = IAImage.alloc().init();
		self.setFileURL_(NSURL.fileURLWithPath_(path))
		self.setFileType_("public.png.imagealpha");

		docimg.setPath_(path);
		docimg.setImage_(image);
		self.setNewDocumentImage_(docimg)
		return YES

	def setDocumentImageFromImage_(self,image):
		return NO # not supported until iaimage can save temp image

#		 if self.documentImage() is not None:
#			 NSLog("That's not supported yet");
#			 return NO

#		 docimg = IAImage.alloc().init();
#		 docimg.setImage_(image)
#		 return self.setNewDocumentImage_(docimg);

	def setNewDocumentImage_(self,docimg):
		#NSLog("new dimage set");
		if self.documentImage() is not None:
			self.documentImage().destroy();

		self.setDocumentImage_(docimg);
		docimg.setCallbackWhenImageChanges_(self);
		self.setDisplayImage_(docimg.image());

		self.updateZoomedImageViewAlternateImage(zoomToFill=True)

	def setDisplayImage_(self,image):
		if self.zoomedImageView() is None or self.backgroundsView is None: return;
		self.zoomedImageView().setImage_(image)
		self.backgroundsView.setImage_(image)
		self.backgroundsView.setSelectable_(YES if image is not None else NO);
		#NSLog("Set new display image %s" % image);

	def imageChanged(self):
		assert self.documentImage() is not None
		self.setDisplayImage_(self.documentImage().image());
		data = self.documentImage().imageData()
		self.updateProgressbar()
		if data is not None:
			source_filesize = self.documentImage().sourceFileSize();
			if source_filesize is None or source_filesize < data.length():
				msg = "Image size: %d bytes" % data.length()
			else:
				percent = 100-data.length()*100/source_filesize
				msg = "Image size: %d bytes (saved %d%% of %d bytes)" % (data.length(), percent, source_filesize)
			self.setStatusMessage_(msg)

	def _getImage(self,name,ext="png"):
		path = NSBundle.mainBundle().resourcePath().stringByAppendingPathComponent_(name).stringByAppendingPathExtension_(ext);
		image = NSImage.alloc().initWithContentsOfFile_(path);
		if image is None:
			NSLog("Failed to load %s " % name);
		return image

	_busyLevel = 0

	def _startWork(self):
		self._busyLevel += 1
		self.updateProgressbar()

	def _endWork(self):
		self._busyLevel -= 1
		self.updateProgressbar()

	def updateProgressbar(self):
		if self.progressBarView is None: return

		isBusy = self._busyLevel > 0 or (self.documentImage() is not None and self.documentImage().isBusy());

		if isBusy:
			self.progressBarView.startAnimation_(self);
		else:
			self.progressBarView.stopAnimation_(self);

	@objc.IBAction
	def toggleShowOriginal_(self,action):
		if self.zoomedImageView() is not None:
			self.zoomedImageView().setDrawAlternateImage_(not self.zoomedImageView().drawAlternateImage());

	@objc.IBAction
	def revert_(self,action):
		pass

	@objc.IBAction
	def zoomIn_(self, sender):
		if self.zoomedImageView() is not None:
			self.zoomedImageView().zoomIn_(sender);

	@objc.IBAction
	def zoomOut_(self, sender):
		if self.zoomedImageView() is not None:
			self.zoomedImageView().zoomOut_(sender);

########NEW FILE########
__FILENAME__ = main
#
#  main.py

# can't avoid default encoding. Python dies in a system-initiated callback due to pretending it's still 1963.
import sys
reload(sys);
sys.setdefaultencoding("utf8");

#import modules required by application
import objc
import Foundation
import AppKit

objc.setVerbose(1)

from PyObjCTools import AppHelper

# import modules containing classes required to start application and load MainMenu.nib

import ImageAlphaDocument
import IASlider
import IACollectionItem
import IAImageViewInteractive
import IABackgroundRenderer
import IAImageView
import IAImage

# pass control to AppKit
AppHelper.runEventLoop()

########NEW FILE########
