__FILENAME__ = accentista
from mojo.UI import CurrentGlyphWindow, UpdateCurrentGlyphView
from mojo.events import addObserver, removeObserver
from defconAppKit.windows.baseWindow import BaseWindowController
from mojo.drawingTools import *
from AppKit import * #@PydevCodeAnalysisIgnore
from vanilla import * #@PydevCodeAnalysisIgnore 

import unicodedata
from lib.tools.drawing import strokePixelPath
from mojo.extensions import getExtensionDefault, setExtensionDefault, getExtensionDefaultColor, setExtensionDefaultColor


#anchorMap = {
#'top': ['gravecmb', 'acutecmb', 'circumflexcmb', 'tildecmb', 'macroncmb', 'brevecmb', 'dotaccentcmb', 'dieresiscmb', 'ringcmb', 'hungarumlautcmb', 'caroncmb', 'commaturnedabovecmb', 'commaaccentcmb', 'cedillacmb', 'cyrillicbrevecmb', 'dieresistonoscmb', 'tonoscmb', 'caroncmb.salt'],

#'bottom': ['cedillacmb', 'commaaccentcmb', 'ogonekcmb']
#}

COMBINING2FLOATING = {
        768 : 96,
        769 : 180,
        770 : 710,
        771 : 732,
        #772 : 175,
        #773 : 175,
        774 : 728,
        775 : 729,
        776 : 168,
        778 : 730,
        779 : 733,
        780 : 711,
        807 : 184,
        808 : 731
        }
 
class OriginAnchor:
    name = "__Origin__"
    x = 0
    y = 0
   
class MojoGlyphDisplay:

    source = None

    def setSource(self, source):
        self.source = source
        
    def getSource(self):
        return self.source

    def setOffset(self, offset):
        self.offset = offset
        
    def getOffset(self):
        return self.offset

    def setScale(self, scale):
        self.scale = scale
        
    def getScale(self):
        return self.scale

    def drawGlyph(self, info={}, stroke=True, fill=True):
        glyph = self.getSource()
        translate(self.offset[0], self.offset[1])
        scale(self.scale[0], self.scale[1])
        drawGlyphPath = TX.naked(glyph).getRepresentation("defconAppKit.NSBezierPath")
        if fill:
            drawGlyphPath.fill()
        if stroke:
            strokePixelPath(drawGlyphPath)
        translate(-self.offset[0], -self.offset[1])
        scale(1/float(self.scale[0]), 1/float(self.scale[1]))

    def __init__(self, dest, source, offset=(0, 0), scale=(1, 1)):
        self.setSource(source)
        self.setOffset(offset)
        self.setScale(scale)

    def updateView(self, sender=None):
        UpdateCurrentGlyphView()
        
        
class TX:
    @classmethod
    def hex2dec(cls, s):
        	try:
        		return int(s, 16)
        	except:
        		pass
        		
    @classmethod
    def naked(cls, p):
        if hasattr(p, 'naked'):
            p = p.naked()
        return p
        
    @classmethod
    def hasAnchor(cls, anchorName, g):
        for a in g.anchors:
            if a.name == anchorName:
                return True
        return False
                
    @classmethod
    def getItalicOffset(cls, yoffset, italicAngle):
        '''
        Given a y offset and an italic angle, calculate the x offset.
        '''
        from math import radians, tan
        ritalicAngle = radians(italicAngle)
        xoffset = int(round(tan(ritalicAngle) * yoffset))
        return xoffset*-1

    @classmethod
    def getItalicCoordinates(cls, coords, italicAngle):
        """
        Given (x, y) coords and an italic angle, get new coordinates accounting for italic offset.
        """
        x, y = coords
        x += cls.getItalicOffset(y, italicAngle)
        return x, y
                
class CharacterTX:
    
    @classmethod
    def char2Glyph(cls, char, f):
        d = ord(char)
        for g in f:
            if d in g.unicodes:
                return g
    
    @classmethod
    def glyph2Char(cls, glyph):
        f = glyph.getParent()
        u = f.naked().unicodeData.pseudoUnicodeForGlyphName(glyph.name)
        if isinstance(u, int):
            return unichr(u)
        else:
            return None

    @classmethod
    def getDecomposition(cls, char):
        u"""
        <doc>
        Decomposition.
        </doc>
        """
        charDec = ord(char)
        decompString = unicodedata.decomposition(char)
        if decompString:
            decompHex = decompString.split(' ')
            decomp = [TX.hex2dec(i) for i in decompHex]
            overrides = {
                290: {807: 806}, # u'Ģ': {u'̦': u'̧'}
                291: {807: 806}, # u'ģ': {u'̦': u'̧'}
                325: {807: 806}, # u'Ņ': {u'̦': u'̧'}
                311: {807: 806}, # u'ķ': {u'̦': u'̧'}
                310: {807: 806}, # u'Ķ': {u'̦': u'̧'}
                342: {807: 806}, # u'Ŗ': {u'̦': u'̧'}
                343: {807: 806}, # u'ŗ': {u'̦': u'̧'}
                536: {807: 806}, # u'Ș': {u'̦': u'̧'}
                537: {807: 806}, # u'ș': {u'̦': u'̧'}
                538: {807: 806}, # u'Ț': {u'̦': u'̧'}
                539: {807: 806}, # u'ț': {u'̦': u'̧'}
                316: {807: 806}, # u'ļ': {u'̦': u'̧'}
                315: {807: 806}, # u'Ļ': {u'̦': u'̧'}
                291: {807: 786}, # gcommaccent
                319: {183: 775},
                320: {183: 775}
                }
            for x, u in enumerate(decomp):
                if overrides.has_key(charDec) and overrides[charDec].has_key(u):
                    decomp[x] = overrides[charDec][u]
            charList = []
            for d in decomp:
                if isinstance(d, int):
                    charList.append(unichr(d))
            return charList
        return None
        
class AnchorPlacer(BaseWindowController):

    DEFAULTKEY = "com.fontbureau.diacriticView"
    DEFAULTKEY_FILLCOLOR = "%s.fillColor" %DEFAULTKEY
    DEFAULTKEY_STROKECOLOR = "%s.strokeColor" %DEFAULTKEY
    DEFAULTKEY_STROKE = "%s.stroke" %DEFAULTKEY
    DEFAULTKEY_FILL = "%s.fill" %DEFAULTKEY
    FALLBACK_FILLCOLOR = NSColor.colorWithCalibratedRed_green_blue_alpha_(0, .5, .5, .3)
    FALLBACK_STROKECOLOR = NSColor.colorWithCalibratedRed_green_blue_alpha_(0, .5, .5, .5)
    VERSION = 1.0
    NAME = u'Accentista'
    MANUAL = u"""TK"""

    bottomAccentFind = ['below', 'cedilla', 'commaaccent', 'ogonek']
    BASEUNICODES = list(range(0, 383)) + list(range(880, 1279)) + [536, 537, 538, 539]
    BASECHARSET = [unichr(u) for u in BASEUNICODES if unicodedata.category(unichr(u)) in ["Lu", "Ll"]]
    
    def updateView(self, sender=None):
        UpdateCurrentGlyphView()
    
    def getCharsThatIncludeChar(self, char):
        accentChars = []
        for base in self.BASECHARSET:
            decomp = CharacterTX.getDecomposition(base)
            if decomp and char in decomp:
                accentChars.append(base)
        return accentChars
    
    def getDefaultAnchorName(self, char):
        anchorName = 'top'
        accentUnicodeName = unicodedata.name(char)
        for searchString in self.bottomAccentFind:
            if accentUnicodeName.find(searchString.upper()) != -1:
                anchorName = 'bottom'
        return anchorName
     
    def currentGlyphChanged(self, info={}):
        self.current = CurrentGlyph()
        self.setShowAccents(self.current)
    
    def getAccentGlyphFromChar(self, d, char, f):
        name = unicodedata.name(char)
        if 'ABOVE' in name and d == 'i':
            d = u'ı'
        g = CharacterTX.char2Glyph(d, f)
        if g is None and COMBINING2FLOATING.has_key(ord(d)):
            g = CharacterTX.char2Glyph(unichr(COMBINING2FLOATING[ord(d)]), f)
        if g is not None:
            if CurrentGlyph() and '.sc' in CurrentGlyph().name:
                if f.has_key(g.name+'.sc'):
                    g = f[g.name+'.sc']
            elif unicodedata.category(char) == 'Lu' and f.has_key(g.name+'.uc'):
                g = f[g.name+'.uc']
        if ord(char) in [317, 271, 318, 357] and ord(d) in [780, 711]:
            if f.has_key('caroncmb.salt'):
                g = f['caroncmb.salt']
            elif f.has_key('caron.salt'):
                g = f['caron.salt']
        return g
    
    def getAnchorName(self, accentGlyph, d, g):
        accentName = accentGlyph.name
        if TX.hasAnchor('top_'+accentName, g):
            anchorName = 'top_'+accentName
        elif TX.hasAnchor('bottom_'+accentName, g):
            anchorName = 'bottom_'+accentName
        else:
            anchorName = self.getDefaultAnchorName(d)
        return anchorName
        
    def setShowAccents(self, g):
        source = g
        accentView = []
        accents = {}
        if g is not None:
            f = g.getParent()
            char = CharacterTX.glyph2Char(g)
            chars = self.getCharsThatIncludeChar(char)
            for baseChar in chars:
                accentViewItem = {}
                decomp = CharacterTX.getDecomposition(baseChar)
                decomp.remove(char)
                for d in decomp:
                    accentGlyph = self.getAccentGlyphFromChar(d, baseChar, f)
                    if accentGlyph is not None:
                        if unicodedata.category(d) not in ["Lu", "Ll"]:
                            accentName = accentGlyph.name
                            anchorName = self.getAnchorName(accentGlyph, d, g)
                            accents[accentName] = (accentGlyph, anchorName)
                            accentViewItem['Accent'] = accentName
                            accentViewItem['Anchor'] = anchorName
                if accentViewItem:
                    accentView.append(accentViewItem)
            
            if not accents:
                decomp = CharacterTX.getDecomposition(char) or []
                for i, d in enumerate(decomp):
                    if unicodedata.category(d) in ["Lu", "Ll"]:
                        baseGlyph = self.getAccentGlyphFromChar(d, char, f)
                        if baseGlyph is not None:
                            anchorName = '__Origin__'
                            accentView.append({'Accent': baseGlyph.name, 'Anchor': anchorName})
                            source = baseGlyph
                            accents[baseGlyph.name] = (baseGlyph, anchorName)
                        decomp.pop(i)
                        break
                for d in decomp:
                    accentViewItem = {}
                    accentGlyph = self.getAccentGlyphFromChar(d, char, f)
                    if accentGlyph is not None:
                        accentName = accentGlyph.name
                        anchorName = anchorName = self.getAnchorName(accentGlyph, d, source)
                        accents[accentName] = (accentGlyph, anchorName)
                        accentViewItem['Accent'] = accentName
                        accentViewItem['Anchor'] = anchorName
                    if accentViewItem:
                        accentView.append(accentViewItem)
            
            self.getView().glyphName.set(g.name)
            self.getView().diacriticList.set(accentView)
        self.showAccents = accents
        self.showAccentSource = source
    
    
    def getShowAccentSource(self):
        return self.showAccentSource
        
    def getShowAccents(self):
        return self.showAccents or {}

    def activateModule(self):
        addObserver(self, "drawAccents", "drawBackground")
        addObserver(self, "currentGlyphChanged", "currentGlyphChanged")

    def deactivateModule(self):
        removeObserver(self, "drawBackground")
        removeObserver(self, "currentGlyphChanged")

    def __init__(self, doWindow=True):
        self.current = CurrentGlyph()
        self.showAccents = {}
        self.w = FloatingWindow((425, 200), self.NAME, minSize=(350, 200))
        self.populateView()
        self.activateModule()
        self.getView().open()
    
    def getView(self):
        return self.w

    
    def populateView(self):
        
        self.fillColor = getExtensionDefaultColor(self.DEFAULTKEY_FILLCOLOR, self.FALLBACK_FILLCOLOR)
        self.strokeColor = getExtensionDefaultColor(self.DEFAULTKEY_STROKECOLOR, self.FALLBACK_STROKECOLOR)

        doWindow = True
        if doWindow:
            view = self.getView()
            x = 10
            y = 10
            y += 30
            view.diacriticList = List((x, y, -10, -10), [],
                    columnDescriptions=[
                                    {"title": "Accent", "editable": False, 'enableDelete': True, 'typingSensitive': True}, 
                                    {"title": "Anchor", "editable": True, 'enableDelete': True, 'typingSensitive': True}, 
                                    ], 
                        doubleClickCallback=self.doubleClickCallback, 
                        #editCallback=self.modifyCallback,
                        selectionCallback=self.selectionCallback                  
                        )

            y-=30            
            view.glyphName = TextBox((x, y, 200, 25), '')

            x = -240
            view.guides = CheckBox((x, y, 60, 22), "Guides", sizeStyle="small", 
                #value=getExtensionDefault("%s.%s" %(self.DEFAULTKEY, "stroke"), False),
                value = True, 
                callback=self.updateView)
            x += 60            
            view.fill = CheckBox((x, y, 40, 22), "Fill", sizeStyle="small", 
                #value=getExtensionDefault("%s.%s" %(self.DEFAULTKEY, "fill"), True),
                value = True,
                callback=self.fillCallback)
            x += 40
            view.stroke = CheckBox((x, y, 60, 22), "Stroke", sizeStyle="small", 
                #value=getExtensionDefault("%s.%s" %(self.DEFAULTKEY, "stroke"), False),
                value = True, 
                callback=self.strokeCallback)
            x += 60
            color = getExtensionDefaultColor(self.DEFAULTKEY_FILLCOLOR, self.FALLBACK_FILLCOLOR)
            view.color = ColorWell((x, y, 30, 22), 
                color=color,
                callback=self.colorCallback)
            x += 40
            view.reset = Button((x, y, 30, 22), unichr(8634), callback=self.clearSelectionCallback)



          
            self.setUpBaseWindowBehavior()
        
        self.setShowAccents(self.current)

        UpdateCurrentGlyphView()

    def colorCallback(self, sender):
        """
        Change the color.
        """
        selectedColor = sender.get()
        r = selectedColor.redComponent()
        g = selectedColor.greenComponent()
        b = selectedColor.blueComponent()
        a = 1
        strokeColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, a)
        setExtensionDefaultColor(self.DEFAULTKEY_FILLCOLOR, selectedColor)
        setExtensionDefaultColor(self.DEFAULTKEY_STROKECOLOR, strokeColor)
        self.fillColor = selectedColor
        self.strokeColor = strokeColor
        self.updateView()

    def fillCallback(self, sender):
        """
        Change the fill status.
        """
        setExtensionDefault(self.DEFAULTKEY_FILL, sender.get())
        self.updateView()

    def strokeCallback(self, sender):
        """
        Change the stroke status.
        """
        setExtensionDefault(self.DEFAULTKEY_STROKE, sender.get())
        self.updateView()

    def selectionCallback(self, sender):
        self.updateView()
    
    def modifyCallback(self, sender):
        accents = self.getShowAccents()
        for accentName, accentBunch in accents.items():
            accentGlyph, anchorName = accentBunch
            for item in sender.get():
                if item.get('Accent') == accentName and item.get('Anchor') != anchorName:
                    newBunch = accentGlyph, item.get('Anchor')
                    self.getShowAccents()[accentName] = newBunch
    
    def doubleClickCallback(self, sender):
        for i in sender.getSelection():
            item = sender.get()[i]
            self.current.appendAnchor(item['Anchor']+'_'+item['Accent'], (0, 0))
            self.setShowAccents(self.current)
    
    def clearSelectionCallback(self, sender={}):
        self.getView().diacriticList.setSelection([])
    
    def drawAccents(self, info):
        #fill = getExtensionDefault(self.DEFAULTKEY_FILL, True)
        #stroke = getExtensionDefault(self.DEFAULTKEY_STROKE, True)
        #fillcolor = getExtensionDefaultColor(self.DEFAULTKEY_FILLCOLOR, self.FALLBACK_FILLCOLOR)

        self.fillColor.setFill()
        self.strokeColor.setStroke()

        g = self.getShowAccentSource()
        accents = self.getShowAccents()

        diacriticList = self.getView().diacriticList.get()
        currentSelectionIndexes = self.w.diacriticList.getSelection()
        selectedAccentNames = [diacriticList[i]['Accent'] for i in currentSelectionIndexes]
        for accentName, accentBunch in accents.items():
            accentGlyph, anchorName = accentBunch
            compatibleAnchorName = '_' + anchorName.split('_')[0]
            anchorMatch = False
            accentOffset = 0, 0
            offset = 0, 0
            if not selectedAccentNames or accentName in selectedAccentNames:
                for anchor in g.anchors:
                    if anchor.name == anchorName:
                        baseOffset = anchor.x, anchor.y
                        for accentAnchor in accentGlyph.anchors:
                            
                            if accentAnchor.name == compatibleAnchorName:
                                accentOffset = accentAnchor.x, accentAnchor.y
                        offset = baseOffset[0] - accentOffset[0], baseOffset[1] - accentOffset[1]
                        d = MojoGlyphDisplay(self.current, accentGlyph, offset=offset)
                        d.drawGlyph(fill=self.getView().fill.get(),
                        stroke=self.getView().stroke.get()
                        )
                        anchorMatch = True
            #if not anchorMatch:
            if anchorName == '__Origin__':
                d = MojoGlyphDisplay(self.current, accentGlyph, offset=offset)
                d.drawGlyph(fill=self.getView().fill.get(),
                        stroke=self.getView().stroke.get()
                        )
        if g.box and self.getView().guides.get():
            boxWidth = g.box[2] - g.box[0]
            leftX = g.angledLeftMargin or 0 + g.getParent().lib.get('com.typemytype.robofont.italicSlantOffset') or 0
            rightX = g.width - g.angledRightMargin or 0 + g.getParent().lib.get('com.typemytype.robofont.italicSlantOffset') or 0
            midX = leftX + (g.width - g.angledLeftMargin or 0 - g.angledRightMargin or 0) / 2.0
            dashLine(2)
            stroke(0, 0, 0, .3)
            
            topY = self.current.getParent().info.ascender * 2
            bottomY = self.current.getParent().info.descender * 2
            italicAngle = self.current.getParent().info.italicAngle or 0
            topX = TX.getItalicOffset(topY, italicAngle)
            bottomX = TX.getItalicOffset(bottomY, italicAngle)
            line(leftX+topX, topY, leftX+bottomX, bottomY)
            line(midX+topX, topY, midX+bottomX, bottomY)
            line(rightX+topX, topY, rightX+bottomX, bottomY)
            
    def windowCloseCallback(self, sender):
        self.deactivateModule()
        UpdateCurrentGlyphView()
        BaseWindowController.windowCloseCallback(self, sender)

a = AnchorPlacer()

########NEW FILE########
__FILENAME__ = adjustMetrics
# -*- coding: UTF-8 -*-  
#
# ----------------------------------------------------------------------------------
from vanilla import *
from defconAppKit.windows.baseWindow import BaseWindowController
from AppKit import *
import os.path

def sortFonts(fonts):
    """
    Some day I will implement this.
    """
    return fonts

    # ---------------------------------------------------------------------------------------------------------
    #    A D J U S T  M E T R I C S
    #
    # Adjust metrics.
    #
    """
    
    Adjust both margins, left margin, or right margin
    To current glyph selection or all glyphs
    In current font or a selection of opened fonts
    
    Options:
        
        Adjust components (on by default): If 'A' is selected but not 'Aacute', 'Aacute' will be shifted back so it does not affect the original position.
    
        Adjust Comps with Selected (off by default): If 'A' is selected, also transform 'Aacute' et. al.
    
    """

def addMargins(f, gnames=[], leftUnits=0, rightUnits=0, adjustComponents=True):
    for gname in gnames:
        if f.has_key(gname):
            g = f[gname]
            g.prepareUndo('addMargins')
            # do left side
            if leftUnits != 0:
                if g.box:
                    g.leftMargin += leftUnits
                else:
                    g.width += leftUnits
                if adjustComponents:
                    for comp in g.components:
                        if comp.baseGlyph in gnames:
                            comp.offset = (comp.offset[0]-leftUnits, comp.offset[1])
                    #print 'adjusting', g, 'leftMargin by', leftUnits, 'units'
            if rightUnits != 0:
                if g.box:
                    g.rightMargin += rightUnits
                else:
                    g.width += rightUnits
            g.performUndo()
    
def multiplyMargins(f, gnames, leftMultiplier=1, rightMultiplier=1, roundValues=1, adjustComponents=True):
    marginRecords = {}
    # Step 1: Compile records
    for gname in gnames:
        leftUnits, rightUnits = 0, 0
        if f.has_key(gname):
            g = f[gname]
            if leftMultiplier != 1:
                leftUnits = (leftMultiplier * g.leftMargin) - g.leftMargin
            if rightMultiplier != 1:
                rightUnits = (rightMultiplier * g.rightMargin ) - g.rightMargin
            if roundValues != 0:
                leftUnits = round(leftUnits, roundValues)
                rightUnits = round(rightUnits, roundValues)
            marginRecords[g.name] = leftUnits, rightUnits
    # Make changes
    for gname in gnames:
        if f.has_key(gname):
            g = f[gname]
            g.prepareUndo('multiplyMargins')
            leftUnits, rightUnits = marginRecords[gname]
            g.leftMargin += leftUnits
            g.rightMargin += rightUnits
            if adjustComponents:
                for comp in g.components:
                    if comp.baseGlyph in gnames:
                        compLeftUnits, compRightUnits = marginRecords[comp.baseGlyph]
                        comp.offset = (comp.offset[0]-compLeftUnits, comp.offset[1])
            g.performUndo()

class AdjustMetrics(BaseWindowController):

    WINDOWTITLE                  = u'Adjust Metrics'

    def __init__(self):
        
        #layout variables
        width = 250
        height = 500
        x = 20
        y = 20
        rightMargin = -20
        itemHeight = 22
        lineHeight = 25

        fonts = AllFonts()
        self.fonts = sortFonts(fonts)
        current = CurrentFont()

        # Window
                
        self.w = Window((width, height), self.WINDOWTITLE, autosaveName=self.WINDOWTITLE, minSize=(width, height))
                
        # Adjust Both
        self.w.adjustBothText = TextBox((x, y, rightMargin, itemHeight), 'Adjust Both Margins')
        y+=lineHeight
        self.w.adjustBothValue = EditText((x, y, 50, itemHeight), callback=self.adjustBothValueCallback)
        x+=60
        self.w.adjustBothUnit = RadioGroup((x, y, 120, itemHeight*2), ['Units', 'Percent'], callback=self.adjustBothUnitCallback)
        self.w.adjustBothUnit.set(0)
        x = 20
        y += lineHeight * 2.5

        # Adjust Left
        self.w.adjustLeftText = TextBox((x, y, rightMargin, itemHeight), 'Adjust Left Margin')
        y+=lineHeight
        self.w.adjustLeftValue = EditText((x, y, 50, itemHeight), callback=self.clearBothCallback)
        x+=60
        self.w.adjustLeftUnit = RadioGroup((x, y, 120, itemHeight*2), ['Units', 'Percent'], callback=self.clearBothCallback)
        self.w.adjustLeftUnit.set(0)
        x = 20
        y += lineHeight * 2.5       

        # Adjust Right
        self.w.adjustRightText = TextBox((x, y, rightMargin, itemHeight), 'Adjust Right Margin')
        y+=lineHeight
        self.w.adjustRightValue = EditText((x, y, 50, itemHeight), callback=self.clearBothCallback)
        x+=60
        self.w.adjustRightUnit = RadioGroup((x, y-3, 120, itemHeight*2), ['Units', 'Percent'], callback=self.clearBothCallback)
        self.w.adjustRightUnit.set(0)
        x = 20
        y += lineHeight * 2.5
 
        # Glyph Selection
        self.w.glyphSelection = RadioGroup((x, y, rightMargin, itemHeight*2), ['Current Glyph Selection', 'All Glyphs'])
        self.w.glyphSelection.set(0)

        y += lineHeight * 2.5

        # Components
        self.w.adjustComponents = CheckBox((x, y, rightMargin, itemHeight), 'Adjust Components')
        self.w.adjustComponents.set(1)

        y += lineHeight
        
        # Transform
        self.w.adjustBaseComponents = CheckBox((x, y, rightMargin, itemHeight), 'Adjust Comps with Selected')
        self.w.adjustBaseComponents.set(0)
        
        y += lineHeight
        
        # Transform
        self.w.ignoreZeroWidth = CheckBox((x, y, rightMargin, itemHeight), 'Ignore Zero-Width Glyphs')
        self.w.ignoreZeroWidth.set(1)
        
        self.w.apply = Button((x, -40, 100, itemHeight), 'Apply', callback=self.apply)
        self.w.cancel = Button((x+110, -40, 100, itemHeight), 'Close', callback=self.cancel)
        
        # Font Selection Drawer

        self.fs = Drawer((200, 150), self.w)
        fsx = 5
        fsy = 5
        
        self.fs.selectAllFonts = Button((fsx, fsy, -55, itemHeight), 'Select All Fonts', callback=self.selectAllFonts, sizeStyle='small')
        self.fs.refreshFontList = Button((-35, fsy, 30, 22), unichr(8634), callback=self.refreshFontList)

        fsy += 25
        self.fs.deselectAllFonts = Button((fsx, fsy, -55, itemHeight), 'Deselect All Fonts', callback=self.deselectAllFonts, sizeStyle='small')
        fsy += 25
        self.fs.selectCurrentFont = Button((fsx, fsy, -55, itemHeight), 'Select Current Font', callback=self.selectCurrentFont, sizeStyle='small')
        fsy += 25

        fontNameList = []
        currentIndex = None
        for x, f in enumerate(self.fonts):
            fontName = str(f.info.familyName)+' '+str(f.info.styleName)
            if fontName in fontNameList:
                fontName = f.path
            fontNameList.append(fontName)
            if f == CurrentFont():
                currentIndex = x
        fsy += 5
        self.fs.fontSelect = List((fsx, fsy, -5, -5), fontNameList)
        if currentIndex is not None:
            self.fs.fontSelect.setSelection([currentIndex])
        
        self.w.open()
        self.fs.open()

    def refreshFontList(self, sender):
        self.fonts = sortFonts(AllFonts())
        fontNameList = []
        currentIndex = None
        for x, f in enumerate(self.fonts):
            fontName = str(f.info.familyName)+' '+str(f.info.styleName)
            if fontName in fontNameList:
                fontName = f.path
            fontNameList.append(fontName)
            if f == CurrentFont():
                currentIndex = x
        self.fs.fontSelect.set(fontNameList)
        self.fs.fontSelect.setSelection([currentIndex])
    
    def adjustBothUnitCallback(self, sender):
        self.w.adjustLeftUnit.set(sender.get())
        self.w.adjustRightUnit.set(sender.get())
        
    def adjustBothValueCallback(self, sender):
        self.w.adjustLeftValue.set(sender.get())
        self.w.adjustRightValue.set(sender.get())
    
    def clearBothCallback(self, sender):
        self.w.adjustBothValue.set('')
     
    def selectAllFonts(self, sender):
        indexRange = range(0, len(self.fonts))
        self.fs.fontSelect.setSelection(indexRange)

    def deselectAllFonts(self, sender):
        self.fs.fontSelect.setSelection([])

    def selectCurrentFont(self, sender):
        for x, f in enumerate(self.fonts):
            if f == CurrentFont():
                currentIndex = x
        self.fs.fontSelect.setSelection([currentIndex])

    def getSelectedFonts(self):
        selectedFonts = []
        for index in self.fs.fontSelect.getSelection():
            selectedFonts.append(self.fonts[index])
        return selectedFonts

    def makeMetricsAdjustment(self, f, gnames):
        """
        """
        if self.w.ignoreZeroWidth.get():
            newGnames = []
            for gname in gnames:
                if f[gname].width != 0:
                    newGnames.append(gname)
            gnames = newGnames
        
        if self.w.adjustComponents.get():
            adjustComponents = True
        else:
            adjustComponents = False
        # get values
        adjustLeftUnit = self.w.adjustLeftUnit.get()
        adjustRightUnit = self.w.adjustRightUnit.get()

        try:
            leftValue = int(self.w.adjustLeftValue.get())
        except:
            if adjustLeftUnit == 0:
                leftValue = 0
            else:
                leftValue = 1
        try:
            rightValue = int(self.w.adjustRightValue.get())
        except:
            if adjustRightUnit == 0:
                rightValue = 0
            else:
                rightValue = 1
        
        if adjustLeftUnit == 0:
            if adjustRightUnit == 0:
                addMargins(f, gnames, leftValue, rightValue, adjustComponents=adjustComponents)
            else:
                addMargins(f, gnames, leftValue, 0, adjustComponents=adjustComponents)    
                multiplyMargins(f, gnames, 1, rightValue*.01, adjustComponents=adjustComponents)    
        if adjustLeftUnit == 1:
            if adjustRightUnit == 1:
                multiplyMargins(f, gnames, leftValue*.01, rightValue*.01, adjustComponents=adjustComponents)
            else:
                multiplyMargins(f, gnames, leftValue*.01, 1, adjustComponents=adjustComponents)    
                addMargins(f, gnames, 0, rightValue, adjustComponents=adjustComponents)    
        f.update()
  

  
    def apply(self, sender):

        fonts = self.getSelectedFonts()
                
        for f in fonts:

            if self.w.glyphSelection.get() == 0:
                gnames = CurrentFont().selection
            else:
                gnames = f._object.keys()
                
        
            if self.w.adjustBaseComponents.get():
                additionalGnames = []
                for g in f:
                    if len(g.components) >= 1 and ( g.components[0].baseGlyph in gnames ) and ( g.name not in gnames ):
                        additionalGnames.append(g.name)
                gnames += additionalGnames
                        
            print f, gnames
            self.makeMetricsAdjustment(f, gnames)
                       
    def cancel(self, sender):
        self.w.close()

OpenWindow(AdjustMetrics)


########NEW FILE########
__FILENAME__ = boundingTool
#coding=utf-8
###########
# BOUNDING TOOL
###########
# BY DJR, with help from Nina Stössinger. Thanks Nina!

# I should probably redo this at some point using angled point instead of doing the math myself. Next time...

from mojo.UI import CurrentGlyphWindow, UpdateCurrentGlyphView
from mojo.events import BaseEventTool, installTool, EditingTool
from AppKit import *
from defconAppKit.windows.baseWindow import BaseWindowController
from mojo.drawingTools import *
from mojo.extensions import ExtensionBundle
from vanilla import *
from mojo.extensions import getExtensionDefault, setExtensionDefault, getExtensionDefaultColor, setExtensionDefaultColor
from lib.tools.defaults import getDefault
from lib.tools import bezierTools

bundle = ExtensionBundle("BoundingTool")
toolbarIcon = bundle.getResourceImage("boundingTool")
try:
    toolbarIcon.setSize_((16, 16))
except:
    pass

class TX:
    
    @classmethod
    def formatStringValue(cls, f): return format(f, '.1f').rstrip('0').rstrip('.')    
    @classmethod
    def getItalicOffset(cls, yoffset, italicAngle):
        '''
        Given a y offset and an italic angle, calculate the x offset.
        '''
        from math import radians, tan
        ritalicAngle = radians(italicAngle)
        xoffset = int(round(tan(ritalicAngle) * yoffset))
        return xoffset*-1

    @classmethod
    def getItalicshowCoordinates(cls, coords, italicAngle):
        """
        Given (x, y) coords and an italic angle, get new showCoordinates accounting for italic offset.
        """
        x, y = coords
        x += cls.getItalicOffset(y, italicAngle)
        return x, y

class BoundingTool(EditingTool, BaseWindowController):
    slantPointCoordinates = int(getDefault("glyphViewShouldSlantPointCoordinates"))
    offsetPointCoordinates = getDefault("glyphViewShouldOffsetPointCoordinates")

    DEFAULTKEY = "com.fontbureau.boundingTool"
    DEFAULTKEY_FILLCOLOR = "%s.fillColor" %DEFAULTKEY
    DEFAULTKEY_STROKECOLOR = "%s.strokeColor" %DEFAULTKEY
    DEFAULTKEY_SHOWCOORDINATES = "%s.showCoordinates" %DEFAULTKEY
    DEFAULTKEY_SHOWDIMENSIONS = "%s.showCoordinates" %DEFAULTKEY
    DEFAULTKEY_SELECTION = "%s.selection" %DEFAULTKEY
    DEFAULTKEY_DIVISIONSX = "%s.divisionsX" %DEFAULTKEY
    DEFAULTKEY_DIVISIONSY = "%s.divisionsY" %DEFAULTKEY
    DEFAULTKEY_USEITALIC = "%s.useItalic" %DEFAULTKEY
    FALLBACK_FILLCOLOR = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, .5, .5, .3)
    FALLBACK_STROKECOLOR = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, .5, .5, .5)
    VERSION = 1.0
    NAME = u'Bounding Tool'
    MANUAL = u"""TK"""



    color = (1, 0, .2)
    alpha = 1
    divisionsStringList = ['1', '2', '3', '4']
    divisionsList = [1, 2, 3, 4]
    
    def getToolbarTip(self):
        return self.NAME
        
    def getToolbarIcon(self):
        return toolbarIcon

    def getBox(self, selected=True):
        g = self.getGlyph()
        if g is not None and g.box is not None:
            n = g
            if selected:
                hasSelection = False
                copyGlyph = g.naked().selection.getCopyGlyph()
                if copyGlyph and copyGlyph[1].get('contours'):
                    n = RGlyph(copyGlyph[0])
                else:
                    n = g
            if self.w.useItalic.get():
                italicAngle = g.getParent().info.italicAngle or 0
                if n.box:
                    boxTop = n.box[3]
                    boxBottom = n.box[1]
                    boxWidth = n.box[2] - n.box[0]
                else:
                    boxTop = g.getParent().info.ascender
                    boxBottom = g.getParent().info.descender
                    boxWidth = g.width
                #print n.angledLeftMargin, g.getParent().lib.get('com.typemytype.robofont.italicSlantOffset')
                try:
                    leftX = n.angledLeftMargin or 0 + g.getParent().lib.get('com.typemytype.robofont.italicSlantOffset') or 0
                    rightX = n.width - n.angledRightMargin or 0 + g.getParent().lib.get('com.typemytype.robofont.italicSlantOffset') or 0
                except:
                    leftX = rightX = 0

                topY = n.box[3]
                bottomY = n.box[1]

                topX = TX.getItalicOffset(topY, italicAngle)
                bottomX = TX.getItalicOffset(bottomY, italicAngle)
                
                box = (
                (leftX+bottomX, bottomY), # bottom left
                (leftX+topX, topY), # top left
                (rightX+topX, topY), # top right
                (rightX+bottomX, bottomY), # bottom right
                (n.naked().angledBounds[2]-n.naked().angledBounds[0], n.naked().angledBounds[3]-n.naked().angledBounds[1])
                )
            else:
                box = (
                    (n.box[0], n.box[1]),
                    (n.box[0], n.box[3]),
                    (n.box[2], n.box[3]),
                    (n.box[2], n.box[1]),
                    (n.box[2]-n.box[0], n.box[3]-n.box[1])
                    ) 
        else:
            box = None #((0, 0), (0, 0), (0, 0), (0, 0), (0, 0))
        return box


    def drawBackground(self, scale):
        g = self.getGlyph()
        self.fillColor.setFill()
        
        slantCoordinates = self.slantPointCoordinates
        italicSlantOffset = 0
        if self.offsetPointCoordinates:
            italicSlantOffset = g.getParent().lib.get('com.typemytype.robofont.italicSlantOffset') or 0
        color = self.fillColor.colorUsingColorSpaceName_(NSCalibratedRGBColorSpace)
        red = color.redComponent()
        green = color.greenComponent()
        blue = color.blueComponent()
        alpha = color.alphaComponent()
        fill(red, green, blue, alpha)
        stroke(red, green, blue, alpha)
        strokeWidth(1*scale)
        dashLine(1)
        fontSizeValue = 8
        fontSize(fontSizeValue*scale)
        
        showCoordinates = self.w.showCoordinates.get()
        showDimensions = self.w.showDimensions.get()
        
        selectedBox = self.getBox(selected=True)
        
        if selectedBox:
            # switch them around so that we draw a line perpindicular to the axis we want to subdivide
            divisionsY = int(self.w.divisionsRadioX.get())
            divisionsX = int(self.w.divisionsRadioY.get())
            
            pt1, pt2, pt3, pt4, dimensions = selectedBox
            pt1X, pt1Y = pt1 # bottom left
            pt2X, pt2Y = pt2 # top left
            pt3X, pt3Y = pt3 # top right
            pt4X, pt4Y = pt4 # bottom right
            
            pt1X += italicSlantOffset
            pt2X += italicSlantOffset
            pt3X += italicSlantOffset
            pt4X += italicSlantOffset

            width, height = dimensions
            startRectX = pt1X
            startRectY = pt1Y
            rectWidth = width / float(divisionsY)
            rectHeight = height / float(divisionsX)
            if self.w.useItalic.get():
                italicAngle = g.getParent().info.italicAngle or 0
            else:
                italicAngle = 0
            margin = 0
            f = g.getParent()
            asc = f.info.ascender + f.info.unitsPerEm
            desc = f.info.descender - f.info.unitsPerEm
        
            ascOffset = TX.getItalicOffset(asc-pt3Y, italicAngle)
            descOffset = TX.getItalicOffset(desc-pt1Y, italicAngle)

            line(pt1X+descOffset, desc, pt2X+ascOffset, asc)
            line(pt4X+descOffset, desc, pt3X+ascOffset, asc)

            line(pt1X-f.info.unitsPerEm, pt1Y, pt4X+f.info.unitsPerEm, pt1Y)
            line(pt2X-f.info.unitsPerEm, pt2Y, pt3X+f.info.unitsPerEm, pt2Y)
            
            margin = 10*scale #((width + height) / 2) / 20
            
            
            if showDimensions:
                widthYBump = 0
                if italicAngle:
                    widthYBump = 20*scale

                widthString = 'w: %s' %(TX.formatStringValue(width))
                widthXPos = pt2X+(width/2.0)+TX.getItalicOffset(margin, italicAngle)-10*scale 
                widthYPos = pt2Y+margin+widthYBump               
                if divisionsY > 1:
                    subWidthString = '    %s' %(TX.formatStringValue(width/divisionsY))
                    text(subWidthString, widthXPos, widthYPos)
                    widthYPos += fontSizeValue*scale
                font("LucidaGrande-Bold")
                text(widthString,
                widthXPos,
                widthYPos)
                
            if divisionsY >= 1:
                xoffset = pt1X
                for divY in range(divisionsY+1):
                    if divY != 0 and divY != divisionsY:
                        line( 
                            xoffset-TX.getItalicOffset(margin, italicAngle),
                            pt1Y-margin,
                            xoffset + TX.getItalicOffset(pt2Y-pt1Y, italicAngle) + TX.getItalicOffset(margin, italicAngle),
                            pt3Y+margin
                            )
                    if showCoordinates:
                        font("LucidaGrande")
                        x, y = bezierTools.angledPoint((xoffset, pt1Y), italicAngle, roundValue=italicAngle, reverse=-1)
                        text('%s' %(TX.formatStringValue(x-italicSlantOffset)), xoffset-TX.getItalicOffset(margin, italicAngle)+2*scale, pt1Y-margin-fontSizeValue)
                        if italicAngle != 0:
                            x, y = bezierTools.angledPoint((xoffset, pt1Y), italicAngle, roundValue=italicAngle, reverse=-1)
                            text('%s' %(TX.formatStringValue(x-italicSlantOffset)), xoffset+TX.getItalicOffset(pt3Y-pt1Y, italicAngle)+TX.getItalicOffset(margin, italicAngle)+2*scale, pt3Y+margin)
                    xoffset += rectWidth

            ###################
            ###################
            ###################
            ###################
            margin = 10*scale

            if showDimensions:
                heightString = 'h: %s' %(TX.formatStringValue(height))
                heightXPos = pt4X + TX.getItalicOffset(height/2.0, italicAngle) + margin
                heightYPos = pt4Y+(height/2.0)-fontSizeValue/2

                if divisionsX > 1:
                    heightYPos -= fontSizeValue*scale/2
                    subHeightString = '    %s' %(TX.formatStringValue(height/divisionsX))
                    text(
                        subHeightString,
                        heightXPos,
                        heightYPos,
                        )
                    heightYPos += fontSizeValue*scale
                
                font("LucidaGrande-Bold")
                text(heightString, 
                heightXPos,
                heightYPos
                )
            if divisionsX >= 1:
                yoffset = pt1Y
                for divX in range(divisionsX+1):
                    if divX != 0 and divX != divisionsX:
                        line( 
                            pt1X + TX.getItalicOffset(yoffset-pt1Y, italicAngle) - margin,
                            yoffset,
                            pt1X + TX.getItalicOffset(yoffset-pt1Y, italicAngle) + width + margin,
                            yoffset
                            )
                    if showCoordinates:
                        font("LucidaGrande")
                        text('%s' %(TX.formatStringValue(yoffset)), 
                        pt1X + TX.getItalicOffset(yoffset-pt1Y, italicAngle) - margin - 14*scale, 
                        yoffset)
                    yoffset += rectHeight
            
                        
            
    def becomeActive(self):
        """
        Boot up the dialog.
        """
        
        self.fillColor = getExtensionDefaultColor(self.DEFAULTKEY_FILLCOLOR, self.FALLBACK_FILLCOLOR)
        self.strokeColor = getExtensionDefaultColor(self.DEFAULTKEY_STROKECOLOR, self.FALLBACK_STROKECOLOR)
        
        self.w = FloatingWindow((260, 130), "Bounding Options", minSize=(100, 100), closable=False)

        self.w.viewOptions = RadioGroup((10, 10, 150, 20),
                                        ['Selection', 'Glyph'],
                                        callback=self.selectionCallback, isVertical=False, sizeStyle="small")
        self.w.viewOptions.set(getExtensionDefault(self.DEFAULTKEY_SELECTION, 0))
        
        self.w.useItalic = CheckBox((165, 10, 100, 20), "Use Italic", value=getExtensionDefault(self.DEFAULTKEY_USEITALIC, True), sizeStyle="small", callback=self.useItalicCallback)

        self.w.xLabel = TextBox((10, 40, 70, 20), "Divisions: X", sizeStyle="small")

        self.w.divisionsRadioX = Slider((80, 40, 70, 20),
        value=getExtensionDefault(self.DEFAULTKEY_DIVISIONSX, 1),
        minValue=1,
        maxValue=4,
        tickMarkCount=4,
        stopOnTickMarks=True,
        continuous=True,
        sizeStyle="small",
        callback=self.divisionsXCallback)

        self.w.yLabel = TextBox((160, 40, 70, 20), "Y", sizeStyle="small")
        self.w.divisionsRadioY = Slider((175, 40, 70, 20),
        value=getExtensionDefault(self.DEFAULTKEY_DIVISIONSY, 1),
        minValue=1,
        maxValue=4,
        tickMarkCount=4,
        stopOnTickMarks=True,
        continuous=True,
        sizeStyle="small",
         callback=self.divisionsYCallback)

        self.w.drawGuidesButton = Button((10, 100, 90, 20), 'Div Guides', callback=self.drawDivGuides, sizeStyle="small")
        self.w.drawBoxGuidesButton = Button((120, 100, 90, 20), 'Box Guides', callback=self.drawBoxGuides, sizeStyle="small",)
            

        x = 10
        y = 70
        self.w.showCoordinates = CheckBox((x, y, 90, 20), "Coordinates", value=getExtensionDefault(self.DEFAULTKEY_SHOWCOORDINATES, True), sizeStyle="small", callback=self.showCoordinatesCallback)
        x += 90
        self.w.showDimensions = CheckBox((x, y, 90, 20), "Dimensions", value=getExtensionDefault(self.DEFAULTKEY_SHOWDIMENSIONS, True), sizeStyle="small", callback=self.showDimensionsCallback)
            
        
        x += 90
        color = getExtensionDefaultColor(self.DEFAULTKEY_FILLCOLOR, self.FALLBACK_FILLCOLOR)
        self.w.color = ColorWell((x, y, 30, 22), 
                color=color,
                callback=self.colorCallback)

        self.setUpBaseWindowBehavior()
        self.w.open()
        
    def becomeInactive(self):
        """
        Remove the dialog when the tool is inactive.
        """
        self.windowCloseCallback(None)
        self.w.close()
        
    def colorCallback(self, sender):
        """
        Change the color.
        """
        selectedColor = sender.get()
        r = selectedColor.redComponent()
        g = selectedColor.greenComponent()
        b = selectedColor.blueComponent()
        a = 1
        strokeColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, a)
        setExtensionDefaultColor(self.DEFAULTKEY_FILLCOLOR, selectedColor)
        setExtensionDefaultColor(self.DEFAULTKEY_STROKECOLOR, strokeColor)
        self.fillColor = selectedColor
        self.strokeColor = strokeColor
        self.updateView()

    def showCoordinatesCallback(self, sender):
        setExtensionDefault(self.DEFAULTKEY_SHOWCOORDINATES, sender.get())
        self.updateView()

    def showDimensionsCallback(self, sender):
        setExtensionDefault(self.DEFAULTKEY_SHOWDIMENSIONS, sender.get())
        self.updateView()

    def divisionsXCallback(self, sender):
        setExtensionDefault(self.DEFAULTKEY_DIVISIONSX, sender.get())
        self.updateView()

    def divisionsYCallback(self, sender):
        setExtensionDefault(self.DEFAULTKEY_DIVISIONSY, sender.get())
        self.updateView()

    def selectionCallback(self, sender):
        setExtensionDefault(self.DEFAULTKEY_SELECTION, sender.get())
        self.updateView()

    def useItalicCallback(self, sender):
        setExtensionDefault(self.DEFAULTKEY_USEITALIC, sender.get())
        self.updateView()

    def drawDivGuides(self, sender):
        """
        Draw guidelines for the current divisions.
        """
        g = self.getGlyph()
        if self.w.viewOptions.get() == 0:
            selectedBox = self.getBox(selected=True)
        else:
            selectedBox = self.getBox(selected=False)
        if selectedBox:
            divisionsX = int(self.w.divisionsRadioY.get())
            divisionsY = int(self.w.divisionsRadioX.get())
            pt1, pt2, pt3, pt4, dimensions = selectedBox
            pt1X, pt1Y = pt1 # bottom left
            pt2X, pt2Y = pt2 # top left
            pt3X, pt3Y = pt3 # top right
            pt4X, pt4Y = pt4 # bottom right
            width, height = dimensions
            italicAngle = 0
            if self.w.useItalic.get():
                italicAngle = g.getParent().info.italicAngle or 0
            g.prepareUndo()
            offset = pt1X
            advance = float(width) / divisionsX
            for i in range(divisionsX-1):
                xmid = offset + advance
                g.addGuide((xmid, pt1Y), 90+italicAngle)
                offset += advance
            offset = pt1Y
            advance = float(height) / divisionsY
            for i in range(divisionsY-1):
                ymid = offset + advance
                g.addGuide((pt1X, ymid), 0)
                offset += advance
            g.performUndo()
                    
    def drawBoxGuides(self, sender):
        """
        Draw guidelines for the current box.
        """
        g = self.getGlyph()
        selectedBox = self.getBox(selected=True)
        if selectedBox:
            divisionsX = int(self.w.divisionsRadioY.get())
            divisionsY = int(self.w.divisionsRadioX.get())
            pt1, pt2, pt3, pt4, dimensions = selectedBox
            pt1X, pt1Y = pt1 # bottom left
            pt2X, pt2Y = pt2 # top left
            pt3X, pt3Y = pt3 # top right
            pt4X, pt4Y = pt4 # bottom right
            width, height = dimensions
            italicAngle = 0
            if self.w.useItalic.get():
                italicAngle = g.getParent().info.italicAngle or 0
            g.prepareUndo()
            #if self.w.viewX.get():
            g.addGuide((pt1X, pt1Y), 90+italicAngle)
            g.addGuide((pt3X, pt3Y), 90+italicAngle)
            #if self.w.viewY.get():
            g.addGuide((pt1X, pt1Y), 0)
            g.addGuide((pt3X, pt3Y), 0)
            g.performUndo()

    def updateView(self, sender=None):
        UpdateCurrentGlyphView()
        

    
installTool(BoundingTool())
########NEW FILE########
__FILENAME__ = GlyphSelect
# -*- coding: UTF-8 -*-  
#
# ----------------------------------------------------------------------------------
from vanilla import *
from AppKit import *
from defconAppKit.windows.baseWindow import BaseWindowController
from fnmatch import fnmatch
import string

#############
# RESOURCES #
#############

def splitName(name):
    """Splits a glyph name into a (baseName string, suffix string) tuple."""
    baseName, suffix = '', ''
    nameElements = name.split('.')
    if len(nameElements) > 0:
        baseName = nameElements[0]
        if len(nameElements) > 1:
            suffix = '.'.join(nameElements[1:])
        else:
            suffix = ''
    return baseName, suffix

UNICODE_CATEGORY_ORDER = ['Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Mn', 'Mc', 'Me', 'Nd', 'Nl', 'No', 'Pc', 'Pd', 'Ps', 'Pe', 'Pi', 'Pf', 'Po', 'Sm', 'Sc', 'Sk', 'So', 'Zs', 'Zl', 'Zp', 'Cc', 'Cf', 'Cs', 'Co', 'Cn']
UNICODE_CATEGORIES = {
    'Lu': 'Letter, Uppercase',                #an uppercase letter
    'Ll': 'Letter, Lowercase',                #a lowercase letter
    'Lt': 'Letter, Titlecase',                #a digraphic character, with first part uppercase
    'Lm': 'Letter, Modifier',                #a modifier letter
    'Lo': 'Letter, Other',                    #other letters, including syllables and ideographs
    'Mn': 'Mark, Nonspacing',                #a nonspacing combining mark (zero advance width)
    'Mc': 'Mark, Spacing',                    #a spacing combining mark (positive advance width)
    'Me': 'Mark, Enclosing',                #an enclosing combining mark
    'Nd': 'Number, Decimal Digit',            #a decimal digit
    'Nl': 'Number, Letter',                    #a letterlike numeric character
    'No': 'Other Number',                    #a numeric character of other type
    'Pc': 'Punctuation, Connector',            #a connecting punctuation mark, like a tie
    'Pd': 'Punctuation, Dash',                #a dash or hyphen punctuation mark
    'Ps': 'Punctuation, Open',                #an opening punctuation mark (of a pair)
    'Pe': 'Punctuation, Close',                #a closing punctuation mark (of a pair)
    'Pi': 'Punctuation, Initial',            #an initial quotation mark
    'Pf': 'Punctuation, Final',                #a final quotation mark
    'Po': 'Punctuation, Other',                #a punctuation mark of other type
    'Sm': 'Symbol, Math',                    #a symbol of primarily mathematical use
    'Sc': 'Symbol, Currency',                #a currency sign
    'Sk': 'Symbol, Modifier',                #a non-letterlike modifier symbol
    'So': 'Symbol, Other',                    #a symbol of other type
    'Zs': 'Separator, Space',                #a space character (of various non-zero widths)
    'Zl': 'Separator, Line',                #U+2028 LINE SEPARATOR only
    'Zp': 'Separator, Paragraph',            #U+2029 PARAGRAPH SEPARATOR only
    'Cc': 'Other, Control',                    #a C0 or C1 control code
    'Cf': 'Other, Format',                    #a format control character
    'Cs': 'Other, Surrogate',                #a surrogate code point
    'Co': 'Other, Private Use',                #a private-use character
    'Cn': 'Other, Unassigned',                #a reserved unassigned code point or a noncharacter
}
UNICODE_CATEGORY_ORDER_COMBINED = ['Letter', 'Mark', 'Number', 'Punctuation', 'Symbol', 'Separator', 'Other']
UNICODE_CATEGORIES_COMBINED = {
    'Letter': ['Lu', 'Ll', 'Lt', 'Lm', 'Lo'],
    'Mark': ['Mn', 'Mc', 'Me'],
    'Number': ['Nd', 'Nl', 'No'],
    'Punctuation': ['Pc', 'Pd', 'Ps', 'Pe', 'Pi', 'Pf', 'Po'],
    'Symbol': ['Sm', 'Sc', 'Sk', 'So'],
    'Separator': ['Zs', 'Zl', 'Zp'],
    'Other': ['Cc', 'Cf', 'Cs', 'Co', 'Cn'],
}
def dec2hex(n, uni = 1):
    hex = "%X" % n
    if uni == 1:
    	while len(hex) <= 3:
    		hex = '0' + str(hex)
    return hex
def readUnicode(unicodeInteger):
    if isinstance(unicodeInteger, int):
        return dec2hex(unicodeInteger)
    else:
        return str(unicodeInteger)
def hex2dec(s):
    try:
        return int(s, 16)
    except:
        pass
def writeUnicode(unicodeString):
    if type(unicodeString) is str:
        return hex2dec(unicodeString)
    else:
        return int(unicodeString)
def reverseDict(d):
	"""
	Reverse a dictionary. This only works right when the dictionary has unique keys and unique values.
	"""
	newDict = {}
	keys = d.keys()
	keys.sort()
	for k in keys:
		v = d[k]
		if v not in newDict.keys():
			newDict[v] = k
	return newDict


# ----------------------------------------------------------------------------------
# Glyph Search

class SelectGlyphSearch(BaseWindowController):
    """
    Search for glyphs using a variety of parameters:
    
    - Glyph Name:
        Exact match for glyph name.
    
    - Base Name:
        Exact match for the basename of the glyph (anything before the first period in a glyph name)
    
    - Suffix
        Exact match for the suffix of the glyph name (anything after the first period).

    - Unicode value
        Find exact match for hexadecimal unicode value.
    
    - Unicode category
        The unicode category groups and individual categories are listed in a dropdown. 
        You might have to hit enter/return in the dropdown to select an item.
        These categories are inclusive, so they will match base glyphs and alternates ("number" will match 'zero' and also 'zero.sups'). 

    You can use the following wildcards:
        *	matches everything
        ?	matches any single character
        [seq]	matches any character in seq
        [!seq]	matches any character not in seq

    Then you can manually select glyphs (by default, all search results are selected)

    You can perform the following selection manipulations in the current font or in all open fonts:

    - Replace selection with results
    - Add results to selection
    - Subtract results from selection
    - Intersect results and seletion (select glyphs common to both) 
    - Print the glyph list to the output window.

    """
    
    def __init__(self):
        """
        Initialize the dialog.
        """        
        title = "Glyph Select from Current Font"    
        self.w = Window((400, 500), title, minSize=(400, 500))
        # get the current font and selection
        f = self.getFont()
        if not f:
            print "Open a font."
            return
        self.setExistingSelection(f.selection[:])
        # make tabs
        tabList = ['Name', 'Basename', 'Suffix', 'Unicode', 'Category']
        self.w.tabs = Tabs((10, 10, -10, -10), tabList, sizeStyle="small")
        for i, tabName in enumerate(tabList):
            # search box
            if i == 0 or i == 1 or i == 2 or i == 3:
                self.w.tabs[i].searchBox = SearchBox((10, 10, -50, 22), callback=self.searchBoxCallback, placeholder=tabName)
            else:
                self.w.tabs[i].searchBox = ComboBox((10, 10, -50, 22), self.getUnicodeCategoriesList(), callback=self.searchBoxCallback)
            # refresh button
            self.w.tabs[i].refresh = Button((-40, 10, 30, 22), unichr(8634), callback=self.refreshCallback)
            # glyph list
            self.w.tabs[i].glyphList = List((10, 40, -10, -115), [])
            #self.w.tabs[i].spinner = ProgressSpinner((-33, 5, 32, 32), displayWhenStopped=False, sizeStyle="small")
        # buttons
        y = -120
        self.w.sourceName = TextBox((20, y, -10, 22), 'Source:', sizeStyle="small")
        y += 22
        self.w.replaceSelection = Button((20, y, 170, 22), 'Replace Selection', sizeStyle="small", callback=self.replaceSelection)       
        self.w.addToSelection = Button((210, y, 170, 22), 'Add To Selection', sizeStyle="small", callback=self.addToSelection)
        y += 27
        self.w.intersectWithSelection = Button((20, y, 170, 22), 'Intersect with Selection', sizeStyle="small", callback=self.intersectWithSelection)
        self.w.subtractFromSelection = Button((210, y, 170, 22), 'Subtract from Selection', sizeStyle="small", callback=self.subtractFromSelection)
        y += 30
        self.w.applySelectionText = TextBox((20, y, 120, 22), 'Apply selection:', sizeStyle="small")
        self.w.applySelectionRadio = RadioGroup((120, y-3, 210, 22),
                                        ["Current Font", "All Open Fonts"],
                                        isVertical=False, sizeStyle="small")
        self.w.applySelectionRadio.set(0)
        #10169
        self.w.printButton = Button((-50, y-3, 30, 22), unichr(9998), callback=self.printCallback, sizeStyle="small")
        self.setUpBaseWindowBehavior()
        self.w.open()

    def windowCloseCallback(self, sender):
        BaseWindowController.windowCloseCallback(self, sender)
    
    ###################
    ## GETS AND SETS ##
    ###################
        
    def getFont(self):
        """
        Returns the current font.
        The other option was to do this with an observer, but that just seemed...complicated.
        """
        f = CurrentFont()
        return f

    def setFontSource(self, f):
        if f is not None:
            self.w.sourceName.set('Source: ' + self.getFontName(f))
        else:
            self.w.sourceName.set('Source:')
    
    def getFontName(self, f=None):
        if f is None:
            f = self.getFont()
        return ' '.join([f.info.familyName, f.info.styleName])
    
    def getAllFonts(self):
        return AllFonts()
    
    def getGlyphOrder(self):
        return self.getFont().glyphOrder
    
    def getUnicodeData(self):
        return self.getFont().naked().unicodeData
    
    def getFontAndGlyphOrderAndUnicodeData(self):
        """
        Convenience function.
        """
        f = self.getFont()
        glyphOrder = f.glyphOrder
        unicodeData = f.naked().unicodeData
        return f, glyphOrder, unicodeData

    def getExistingSelection(self):
        return self.selection
        
    def setExistingSelection(self, selection):
        self.selection = selection
        
    def getNewSelection(self):
        """
        Return the current selection within glyphList.
        """
        i = self.w.tabs.get()
        tabAll = self.w.tabs[i].glyphList.get()
        tabSelectedIndexes = self.w.tabs[i].glyphList.getSelection()
        newSelection = []
        for selectedIndex in tabSelectedIndexes:
            newSelection.append(tabAll[selectedIndex])
        return newSelection

    ###############
    ## CALLBACKS ##
    ###############
    
    def searchBoxCallback(self, sender):
        """
        """
        searchTerm = sender.get()
        self.doSearch(searchTerm)

    def refreshCallback(self, sender):
        """
        Refresh the search with the current font.
        """
        i = self.w.tabs.get()
        self.doSearch(self.w.tabs[i].searchBox.get())
    
    def printCallback(self, sender):
        print self.getNewSelection()
    
    ###############
    ## DO SEARCH ##
    ###############
    
    def doSearchInGlyphName(self, searchTerm, searchIn):
        searchResults = []
        for gname in searchIn:
            if fnmatch(gname, searchTerm):
                searchResults.append(gname)
        return searchResults
        
    def doSearchInBaseName(self, searchTerm, searchIn):
        searchResults = []
        for gname in searchIn:
            baseName, suffix = splitName(gname)
            if fnmatch(baseName, searchTerm):
                searchResults.append(gname)
        return searchResults

    def doSearchInSuffix(self, searchTerm, searchIn):
        searchResults = []
        for gname in searchIn:
            baseName, suffix = splitName(gname)
            if fnmatch(suffix, searchTerm):
                searchResults.append(gname)
        return searchResults

    def getUnicodeCategoriesList(self):
        categoryList = []
        for metaCategoryName in UNICODE_CATEGORY_ORDER_COMBINED:
            categoryList.append(metaCategoryName)
        categoryList.append('')
        for catshort in UNICODE_CATEGORY_ORDER:
            categoryList.append(UNICODE_CATEGORIES[catshort])
        return categoryList

    def doSearchInUnicode(self, searchTerm, searchIn, unicodeData=None):
        searchResults = []

        if unicodeData is None:
            unicodeData = self.getUnicodeData()

        for gname in searchIn:
            dec = unicodeData.unicodeForGlyphName(gname)
            hex = readUnicode(dec)
            if fnmatch(hex, searchTerm) and not gname in searchResults:
                searchResults.append(gname)
        searchResults.sort()
        return searchResults

        """
        # at some point in the future, implement unicode ranges...
        searchRanges = searchTerm.split(',')
        for x, searchRange in enumerate(searchRanges):
            searchRange = string.strip(searchRange)
            searchRanges[x] = searchRange.split('-')
        
        # [[min, max], [min, max]]
        
        for gname in searchIn:
            dec = unicodeData.unicodeForGlyphName(gname)
            if dec:
                hex = dec2hex(dec)
                for searchRange in searchRanges:
                    if len(searchRange) == 1:
                        if fnmatch(hex, searchTerm) and not gname in searchResults:
                            searchResults.append(gname)
                    elif len(searchRange) == 2 and len(searchRange[0]) == 4 and len(searchRange[1]) == 4:
                        min, max = searchRange
                        mindec, maxdec = hex2dec(min), hex2dec(max)
                        if mindec and maxdec:
                            print min, max, mindec, maxdec, dec, min < dec, max
                            if mindec < dec < maxdec:
                                searchResults.append(gname)
        """
        
        searchResults.sort()
        return searchResults

        
        
    def doSearchInUnicodeCategory(self, searchTerm, searchIn, unicodeData=None):
        searchResults = []
        if unicodeData is None:
            unicodeData = self.getUnicodeData()
        reverseUnicodeCategories = reverseDict(UNICODE_CATEGORIES)
        try:
            searchTerms = [reverseUnicodeCategories[searchTerm]]
        except:
            searchTerms = UNICODE_CATEGORIES_COMBINED[searchTerm]
        for gname in searchIn:
            if unicodeData.categoryForGlyphName(gname) in searchTerms:
                searchResults.append(gname)
        return searchResults

    def doSearch(self, searchTerm):
        f, glyphOrder, unicodeData = self.getFontAndGlyphOrderAndUnicodeData()
        self.setFontSource(f)        
        i = self.w.tabs.get()
        if not searchTerm:
            self.setFontSource(None)
        searchResults = []
        #start the spinner
        #self.w.tabs[i].spinner.start()
        if i == 0:   # glyph name
            searchResults = self.doSearchInGlyphName(searchTerm, glyphOrder)
        elif i == 1:  # base name
            searchResults = self.doSearchInBaseName(searchTerm, glyphOrder)
        elif i == 2:    # suffix
            searchResults = self.doSearchInSuffix(searchTerm, glyphOrder)
        elif i == 3:    # unicode value
            searchResults = self.doSearchInUnicode(searchTerm, glyphOrder, unicodeData)
        elif i == 4:    # unicode category
            searchResults = self.doSearchInUnicodeCategory(searchTerm, glyphOrder, unicodeData)
        else:
            print 'tab error', i
        # set the search results
        self.w.tabs[i].glyphList.set(searchResults)
        # select all by default
        self.w.tabs[i].glyphList.setSelection(range(0, len(searchResults)))
        # stop the spinner
        #self.w.tabs[i].spinner.stop()

    ############################
    ##  MANIPULATE SELECTION  ##
    ############################
    

    
    def selectInFont(self):
        # figure out whether we are selecting in current font, or all fonts
        applySelectionIndex = self.w.applySelectionRadio.get()
        if applySelectionIndex == 1:
            fonts = self.getAllFonts()
        elif applySelectionIndex == 0:
            fonts = [self.getFont()]
        # apply selection
        for f in fonts:
            fontSet = set(f.keys())
            selectionSet = set(self.getExistingSelection())
            resultSet = fontSet.intersection(selectionSet)
            f.selection = list(resultSet)
            f.update()
    
    def addToSelection(self, sender):
        existingSet = set(self.getExistingSelection())
        newSet = set(self.getNewSelection())
        bothSet = existingSet | newSet
        self.setExistingSelection(list(bothSet))
        self.selectInFont()
 
    def intersectWithSelection(self, sender):
        existingSet = set(self.getExistingSelection())
        newSet = set(self.getNewSelection())
        bothSet = existingSet & newSet
        self.setExistingSelection(list(bothSet))
        self.selectInFont()
 
    def subtractFromSelection(self, sender):
        existingSet = set(self.getExistingSelection())
        newSet = set(self.getNewSelection())
        diffSet = existingSet - newSet
        self.setExistingSelection(list(diffSet))
        self.selectInFont()

    def replaceSelection(self, sender):
        self.setExistingSelection(self.getNewSelection())
        self.selectInFont()

    def clearSelection(self, sender):
        self.setExistingSelection([])
        self.selectInFont()

if __name__ is "__main__":
    OpenWindow(SelectGlyphSearch)
########NEW FILE########
__FILENAME__ = ItalicBowtie
#coding=utf-8
from fontTools.pens.basePen import BasePen
from defconAppKit.windows.baseWindow import BaseWindowController
from mojo.events import addObserver, removeObserver
from AppKit import * #@PydevCodeAnalysisIgnore
from vanilla import * #@PydevCodeAnalysisIgnore 
from mojo.drawingTools import *
from mojo.UI import UpdateCurrentGlyphView, CurrentGlyphWindow
from mojo.extensions import getExtensionDefault, setExtensionDefault
from fontTools.misc.transform import Identity
import math

class M:
    ##################
    # ITALIC OFFSET MATH
    ##################
    
    @classmethod
    def getItalicOffset(cls, yoffset, italicAngle):
        '''
        Given a y offset and an italic angle, calculate the x offset.
        '''
        from math import radians, tan
        ritalicAngle = radians(italicAngle)
        xoffset = int(round(tan(ritalicAngle) * yoffset))
        return xoffset*-1

    @classmethod
    def getItalicRise(cls, xoffset, italicAngle):
        '''
        Given a x offset and an italic angle, calculate the y offset.
        '''
        from math import radians, tan
        if italicAngle == 0:
            return 0
        ritalicAngle = radians(italicAngle)
        yoffset = int(round( float(xoffset) / tan(ritalicAngle) ))
        return yoffset

    @classmethod
    def getItalicCoordinates(cls, coords, italicAngle):
        """
        Given (x, y) coords and an italic angle, get new coordinates accounting for italic offset.
        """
        x, y = coords
        x += cls.getItalicOffset(y, italicAngle)
        return x, y
        
class DrawingToolsPen(BasePen):
    """
    A quick and easy pen that converts to DrawBot/Mojo Drawing Tools.
    """
    def _moveTo(self, p1):
        moveTo(p1)
    def _lineTo(self, p1):
        lineTo(p1)
    def _curveToOne(self, p1, p2, p3):
        curveTo(p1, p2, p3)
    def _closePath(self):
        closepath()

class Italicalc:
    """
    Some classmethods for doing Italic calculations.
    """
    
    @classmethod
    def drawItalicBowtie(cls, italicAngle=0, crossHeight=0, italicSlantOffset=0, ascender=0, descender=0, xoffset=0):
        """
        Draw an italic Bowtie.
        """
        topBowtie = ascender
        topBowtieOffset = M.getItalicOffset(topBowtie, italicAngle)
        bottomBowtie = descender
        bottomBowtieOffset = M.getItalicOffset(bottomBowtie, italicAngle)
        path = DrawingToolsPen(None)
        newPath()
        path.moveTo((xoffset, descender))
        path.lineTo((xoffset+bottomBowtieOffset+italicSlantOffset, descender))
        path.lineTo((xoffset+topBowtieOffset+italicSlantOffset, ascender))
        path.lineTo((xoffset, ascender))
        closePath()
        drawPath()
    
    @classmethod
    def calcItalicSlantOffset(cls, italicAngle=0, crossHeight=0):
        """
        Get italic slant offset.
        """
        return M.getItalicOffset(-crossHeight, italicAngle)
    
    @classmethod
    def calcCrossHeight(cls, italicAngle=0, italicSlantOffset=0):
        return M.getItalicRise(italicSlantOffset, italicAngle)        
    
    @classmethod
    def makeReferenceLayer(cls, source, italicAngle, backgroundName='com.fontbureau.italicReference'):
        """
        Store a vertically skewed copy in the mask.
        """
        italicSlant = abs(italicAngle)
        g = source.getLayer(backgroundName)
        g.decompose()
        source.copyToLayer(backgroundName)
        #use for vertical offset later
        top1 = g.box[3]
        bottom1 = g.box[1]
        height1 = top1 + abs(bottom1)
        #vertical skew
        m = Identity
        dx = 0
        dy = italicSlant/2.0 # half the italic angle
        x = math.radians(dx)
        y = math.radians(dy)
        m = m.skew(x,-y)
        g.transform(m)
        top2 = g.box[3]
        bottom2 = g.box[1]
        height2 = top2 + abs(bottom2)
        dif = (height1-height2) / 2
        yoffset = (abs(bottom2)-abs(bottom1)) + dif
        g.move((0,yoffset))

    @classmethod
    def italicize(cls, g, 
        italicAngle=None, 
        offset=0, 
        doContours = True,
        doAnchors = True,
        doGuides = True,
        doComponents = True,
        doImage = True,
        makeReferenceLayer=True,
        DEBUG=False,
        ):
        """
        Oblique a glyph using cap height and italic angle.
        """
        g.prepareUndo()
        f = g.getParent()
        xoffset = offset
        # skew the glyph horizontally
        g.skew(-italicAngle, (0, 0))
        g.prepareUndo()
        if doContours:
            for c in g.contours:
                c.move((xoffset, 0))
                if DEBUG: print '\t\t\t', c
        # anchors
        if doAnchors:
            for anchor in g.anchors:
                anchor.move((xoffset, 0))
                if DEBUG: print '\t\t\t', anchor
        # guides
        if doGuides:
            for guide in g.guides:
                guide.x += xoffset
                if DEBUG: print '\t\t\t', guide, guide.x
                # image
                if doImage:
                    if g.image:
                        g.image.move((xoffset, 0))
                        if DEBUG: print '\t\t\t', image 
        if doComponents:
            for c in g.components:
                cxoffset = M.getItalicOffset(c.offset[1], italicAngle)
                c.offset = (c.offset[0]-cxoffset, c.offset[1])
        
        if not g.components and makeReferenceLayer:
            cls.makeReferenceLayer(g, italicAngle)
        g.mark = (0, .1, 1, .2)
        g.performUndo()

class Tool():
    """
    The tool object manages the font list. This is a simplification.
    """
    
    def addObserver(self, target, method, action):
        addObserver(target, method, action)

    def removeObserver(self, target, method, action):
        removeObserver(target, method, action)


class ItalicBowtie(BaseWindowController, Italicalc):
    DEFAULTKEY = 'com.fontbureau.italicBowtie'
    DEFAULTKEY_REFERENCE = DEFAULTKEY + '.drawReferenceGlyph'
    italicSlantOffsetKey = 'com.typemytype.robofont.italicSlantOffset'
    
    def activateModule(self):
        self.tool.addObserver(self, 'drawInactive', 'drawInactive')
        self.tool.addObserver(self, 'drawBackground', 'drawBackground')

    def deactivateModule(self):
        removeObserver(self, 'drawBackground')
        removeObserver(self, 'drawInactive')

    def __init__(self):
        self.tool = Tool()
        self.w = FloatingWindow((325, 250), "Italic Bowtie")
        self.populateView()
        self.getView().open()
        
    def getView(self):
        return self.w
        
    def populateView(self):
        lineHeight = 30
        view = self.getView()
        y = 10
        x = 10
        view.italicAngleLabel = TextBox((x, y+4, 100, 22), 'Italic Angle', sizeStyle="small")
        x += 100
        view.italicAngle = EditText((x, y, 40, 22), '', sizeStyle="small", callback=self.calcItalicCallback)

        y += 30
        x = 10
        view.crossHeightLabel = TextBox((x, y+4, 95, 22), 'Cross Height', sizeStyle="small")
        x += 100
        view.crossHeight = EditText((x, y, 40, 22), '', sizeStyle="small", callback=self.calcItalicCallback)
        x += 50
        view.crossHeightSetUC = Button((x, y, 65, 22), 'Mid UC', sizeStyle="small", callback=self.calcItalicCallback)
        x += 75
        view.crossHeightSetLC = Button((x, y, 65, 22), 'Mid LC', sizeStyle="small", callback=self.calcItalicCallback)
        
        
        y += 30
        x = 10        
        view.italicSlantOffsetLabel = TextBox((x, y+4, 100, 22), 'Italic Slant Offset', sizeStyle="small")
        x += 100
        view.italicSlantOffset = EditText((x, y, 40, 22), '', sizeStyle="small", callback=self.calcItalicCallback)
        x += 60

        y += 30
        x = 10
        view.refresh = Button((x, y, 140, 22), u'Values from Current', callback=self.refresh, sizeStyle="small")
        
        y += 30
        
        view.fontSelection = RadioGroup((x, y, 120, 35), ['Current Font', 'All Fonts'], sizeStyle="small")
        view.fontSelection.set(0)
        

        x += 160
        view.glyphSelection = RadioGroup((x, y, 120, 55), ['Current Glyph', 'Selected Glyphs', 'All Glyphs'], sizeStyle="small")
        view.glyphSelection.set(0)
        y += 60
        x = 10
        view.setInFont = Button((x, y, 140, 22), 'Set Font Italic Values', sizeStyle="small", callback=self.setInFontCallback)       
        x += 160
        view.italicize = Button((x, y, 140, 22), 'Italicize Glyphs', sizeStyle="small", callback=self.italicizeCallback)
        y += 25
        view.makeReferenceLayer = CheckBox((x, y, 145, 22), 'Make Reference Layer', value=getExtensionDefault(self.DEFAULTKEY_REFERENCE, False), sizeStyle="small", callback=self.makeReferenceLayerCallback)
        x = 10

        self.refresh()
        if self.getItalicAngle() == 0 and CurrentFont() is not None:
            self.setCrossHeight((CurrentFont().info.capHeight or 0) / 2)
        self.activateModule()
        self.setUpBaseWindowBehavior()
        self.updateView()

    def makeReferenceLayerCallback(self, sender):
        setExtensionDefault(self.DEFAULTKEY_REFERENCE, sender.get())
        
    def italicizeCallback(self, sender=None):
        view = self.getView()
        italicAngle = self.getItalicAngle()
        italicSlantOffset = self.getItalicSlantOffset()
        if view.fontSelection.get() == 0:
            if CurrentFont() is not None:
                fonts = [CurrentFont()]
            else:
                fonts = []
        else:
            fonts = AllFonts()
        
        if view.glyphSelection.get() == 0 and CurrentGlyph() is not None:
            glyphs = [CurrentGlyph()] 
        elif view.glyphSelection.get() == 1:
            glyphs = []
            for f in fonts:
                for gname in CurrentFont().selection:
                    if f.has_key(gname):
                        glyphs.append(f[gname])
        else:
            glyphs = []
            for f in fonts:
                for g in f:
                    glyphs.append(g.name)
        
        for glyph in glyphs:
            Italicalc.italicize(glyph, italicAngle, offset=italicSlantOffset, makeReferenceLayer=view.makeReferenceLayer.get())
                
    
    def refresh(self, sender=None):
        f = CurrentFont()
        if f:
            view = self.getView()
            italicSlantOffset = f.lib.get(self.italicSlantOffsetKey) or 0
            italicAngle = f.info.italicAngle or 0
            crossHeight = Italicalc.calcCrossHeight(italicAngle=italicAngle, italicSlantOffset=italicSlantOffset)
            self.setItalicSlantOffset(italicSlantOffset)
            self.setItalicAngle(italicAngle)
            self.setCrossHeight(crossHeight)
        else:
            self.setItalicSlantOffset(0)
            self.setItalicAngle(0)
            self.setCrossHeight(0)
        self.updateView()

    def setInFontCallback(self, sender):
        view = self.getView()
        if view.fontSelection.get() == 0:
            if CurrentFont() is not None:
                fonts = [CurrentFont()]
            else:
                fonts = []
        else:
            fonts = AllFonts()
        for f in fonts:
            f.prepareUndo()
            f.info.italicAngle = self.getItalicAngle()
            f.lib[self.italicSlantOffsetKey] = self.getItalicSlantOffset()
            f.performUndo()
        try:
            window = CurrentGlyphWindow()
            window.setGlyph(CurrentGlyph().naked())
        except:
            print self.DEFAULTKEY, 'error resetting window, please refresh it'
        self.updateView()
    
    def calcItalicCallback(self, sender):
        view = self.getView()
        italicAngle = self.getItalicAngle()
        italicSlantOffset = self.getItalicSlantOffset()
                
        if sender == view.crossHeightSetUC and CurrentFont() is not None:
            crossHeight = ( CurrentFont().info.capHeight or 0 ) / 2.0
            sender = view.crossHeight
        elif sender == view.crossHeightSetLC and CurrentFont() is not None:
            crossHeight = ( CurrentFont().info.xHeight or 0 ) / 2.0        
            sender = view.crossHeight
        else:
            crossHeight = self.getCrossHeight()
        if sender == view.italicAngle or sender == view.italicSlantOffset:
            self.setCrossHeight(Italicalc.calcCrossHeight(italicAngle=italicAngle, italicSlantOffset=italicSlantOffset))
        elif sender == view.crossHeight:
            self.setItalicSlantOffset(Italicalc.calcItalicSlantOffset(italicAngle=italicAngle, crossHeight=crossHeight))
            self.setCrossHeight(crossHeight)    
        self.updateView()
    
    def updateView(self, sender=None):
        UpdateCurrentGlyphView()

    def windowCloseCallback(self, sender):
        self.deactivateModule()
        self.updateView()
        BaseWindowController.windowCloseCallback(self, sender)
    
    ################################
    ################################
    ################################
    
    def getItalicAngle(self):
        a = self.getView().italicAngle.get()
        try:
            return float(a)
        except:
            return 0
    
    def getItalicSlantOffset(self):
        a = self.getView().italicSlantOffset.get()
        try:
            return float(a)
        except:
            return 0
            
    def getCrossHeight(self):
        a = self.getView().crossHeight.get()
        try:
            return float(a)
        except:
            print 'error', a
            return 0
            
    def setItalicAngle(self, italicAngle):
        view = self.getView()
        view.italicAngle.set(str(italicAngle))

    def setItalicSlantOffset(self, italicSlantOffset):
        view = self.getView()
        view.italicSlantOffset.set(str(italicSlantOffset))

    def setCrossHeight(self, crossHeight):
        view = self.getView()
        view.crossHeight.set(str(crossHeight))
        
    def drawBackground(self, info):
        view = self.getView()
        g = info.get('glyph')
        scale = info.get('scale') or 1
        if g is None:
            return
        fill(.2, .1, .5, .05)
        #lineDash(2)
        stroke(.2, .1, .5, .5)
        strokeWidth(.5*scale)
        dashLine(0)
        f = g.getParent()
        italicAngle = self.getItalicAngle()
        italicSlantOffset = self.getItalicSlantOffset()
        crossHeight = self.getCrossHeight()
        ascender = f.info.ascender
        descender = f.info.descender
        italicSlantOffsetOffset = italicSlantOffset
        for xoffset in (0, g.width):
            self.drawItalicBowtie(italicAngle=italicAngle, crossHeight=crossHeight, ascender=ascender, descender=descender, italicSlantOffset=italicSlantOffsetOffset, xoffset=xoffset)
        dashLine(2)
        strokeWidth(1*scale)
        line(0, crossHeight, g.width, crossHeight)        



    
    drawInactive = drawBackground
    
ItalicBowtie()

########NEW FILE########
__FILENAME__ = OverlayUFOs
#coding=utf-8
from __future__ import division
"""
# OVERLAY UFOS

For anyone looking in here, sorry the code is so messy. This is a standalone version of a script with a lot of dependencies.
"""
import os
from AppKit import * #@PydevCodeAnalysisIgnore
from vanilla import * #@PydevCodeAnalysisIgnore 

from mojo.drawingTools import *
from mojo.events import addObserver, removeObserver
from mojo.extensions import getExtensionDefault, setExtensionDefault, getExtensionDefaultColor, setExtensionDefaultColor
from mojo.UI import UpdateCurrentGlyphView
from fontTools.pens.transformPen import TransformPen
from defconAppKit.windows.baseWindow import BaseWindowController
import unicodedata

#from lib.tools.defaults import getDefaultColor
from lib.tools.drawing import strokePixelPath
from lib.UI.spaceCenter.glyphSequenceEditText import splitText

selectedSymbol = u'•'

def SmallTextListCell(editable=False):
    cell = NSTextFieldCell.alloc().init()
    size = NSSmallControlSize #NSMiniControlSize
    cell.setControlSize_(size)
    font = NSFont.systemFontOfSize_(NSFont.systemFontSizeForControlSize_(size))
    cell.setFont_(font)
    cell.setEditable_(editable)
    return cell

class TX:
    """
    An agnostic way to get a naked font.
    """
    @classmethod
    def naked(cls, f):
        try:
            return f.naked()
        except:
            return f
            
class Tool():
    """
    The tool object manages the font list. This is a simplification.
    """
    fonts = AllFonts()
    
    def addObserver(self, target, method, action):
        addObserver(target, method, action)

    def removeObserver(self, target, method, action):
        removeObserver(target, method, action)

    def getCurrentFont(self):
        return CurrentFont()
    
    def getFonts(self):
        u"""Answers the list of selected fonts, ordered by their path.
        """
        return self.fonts
        
    def appendToFonts(self, path):
        f = OpenFont(path, showUI=False)
        self.fonts.append(f)
        
    def removeFromFonts(self, path):
        for i, f in enumerate(self.fonts):
            if f.path == path:
                del self.fonts[i]

    def getFontPaths(self):
        return [f.path or str(f.info.familyName)+" "+str(f.info.styleName) for f in self.getFonts()]
    
    def getFontLabel(self, path):
        if path is None:
            return None
        if not path:
            return 'Untitled'
        name = path.split('/')[-1]
        status = selectedSymbol
        return status, path, name
    
    def getFontLabels(self):
        labels = {}
        for path in self.getFontPaths():
            if path:
                label = self.getFontLabel(path)
                name = label[-1]
            else:
                name = 'Untitled'
            if not labels.has_key(name):
                labels[name] = []
            labels[name].append(label)
        sortedLabels = []
        for _, labelSet in sorted(labels.items()):
            if len(labelSet) == 1: # There is only a single font with this name
                sortedLabels.append(labelSet[0])
            else: # Otherwise we'll have to construct new names to show the difference
                for status, path, name in sorted(labelSet):
                    sortedLabels.append((status, path, '%s "%s"' % (name, '/'.join(path.split('/')[:-1]))))
        return sortedLabels

class C:
    """
    Some constants.
    """
    C2 = 100
    BUTTON_WIDTH = 80
    STYLE_CHECKBOXSIZE = 'small'
    STYLE_LABELSIZE = 'small'
    STYLE_RADIOSIZE = 'small'
    L = 22
    LL = 25

class OverlayUFOs(BaseWindowController):
    
    DEFAULTKEY = "com.fontbureau.overlayUFO"
    DEFAULTKEY_FILLCOLOR = "%s.fillColor" %DEFAULTKEY
    DEFAULTKEY_STROKECOLOR = "%s.strokeColor" %DEFAULTKEY
    DEFAULTKEY_STROKE = "%s.stroke" %DEFAULTKEY
    DEFAULTKEY_FILL = "%s.fill" %DEFAULTKEY
    FALLBACK_FILLCOLOR = NSColor.colorWithCalibratedRed_green_blue_alpha_(.5, 0, .5, .1)
    FALLBACK_STROKECOLOR = NSColor.colorWithCalibratedRed_green_blue_alpha_(.5, 0, .5, .5)
   
    VERSION = 1.0
    
    NAME = u'Overlay UFOs'

    MANUAL = u"""In the current glyph window, this will present the view the same glyph from a separate 
    UFO or set of UFOs.<br/>
    This does NOT import the UFO into a background layer. Instead, it renders a outline directly from the UFO into the glyph window view.
    <ul>
    <li>There is no need to import duplicate data into a background layer.</li>
    <li>The source outline is always live; when changes are made to the source, they will automatically 
    appear in the current without re-importing.</li>
    <li>The source font does not need to be opened with a UI.</li>
    </ul>
    <h3>DIALOG</h3> 
    <ul>
    <li>A floating dialog is present to let you open and select source fonts, fill, stroke, color.</li>
    <li>Source Fonts: The default source font list is self.getOpenFonts(). The refresh button will 
    return this list to self.getOpenFonts().</li>
    <li>Adding Fonts: You can manually add fonts by selecting a UFO file. 
    The UFO file will open without an interface.</li>
    <li>Removing Fonts: There are buttons for removing selected fonts and for clearing the source font list.</li>
    </ul> 
    <h3>BUGS/IMPROVEMENTS</h3>
    <ul>
    <li>Known Issue: The source font is drawn on top of the current font, instead of behind it. 
    So, it is good to select a color with a low opacity.</li>
    <li>Known Bug: If the glyph window for both source and current fonts are open, it is possible 
    to select and inadvertently edit the source outline in the current window. I don't know how to solve this.</li>
    <li>Improvement?: Add options to scale the source font.</li>
    <li>Improvement?: Set different colors, fill settings for each font?</li>
    </ul>
    """

    # Fixed width of the window.
    VIEWMINSIZE = 400
    VIEWSIZE = VIEWMINSIZE
    VIEWMAXSIZE = VIEWMINSIZE

    WINDOW_POSSIZE = (130, 20, VIEWSIZE, 260)
    WINDOW_MINSIZE = (VIEWMINSIZE, 260)
    WINDOW_MAXSIZE = (VIEWMAXSIZE, 260)

    def getPathListDescriptor(self): 
        return [
            dict(title='Status', key='status', cell=SmallTextListCell(editable=False), width=12, editable=False),
            dict(title='Name',  key='name', width=300, cell=SmallTextListCell(editable=False), editable=False),
            dict(title='Path', key='path', width=0, editable=False),
        ]
    
    ################
    # OBSERVERS AND UPDATERS
    ################
    
    def fontSelectionChanged(self):  
        self.setSourceFonts()
    
    def activateModule(self):
        self.tool.addObserver(self, 'drawInactive', 'drawInactive')
        self.tool.addObserver(self, 'drawBackground', 'drawBackground')
        self.tool.addObserver(self, 'fontDidOpen', 'fontDidOpen')
        self.tool.addObserver(self, 'fontWillClose', 'fontWillClose')
        
    def deactivateModule(self):
        removeObserver(self, 'drawBackground')
        removeObserver(self, 'drawInactive')
        removeObserver(self, 'fontDidOpen')
        removeObserver(self, 'fontWillClose')
        
    ################
    # CONTEXTS
    ################

    def fontDidOpen(self, info):
        font = info.get('font')
        if font:
            self.tool.fonts.append(font)
            self.refreshCallback()

    def fontWillClose(self, info):
        font = info.get('font')
        path = font.path
        if path:
            self.tool.removeFromFonts(path)
            self.refreshCallback()
    
    def __init__(self):
        self.tool = Tool()
        self.w = FloatingWindow((400, 200), "Overlay UFOs", minSize=(400, 200))
        self.populateView()
        self.getView().open()

    def getView(self):
        return self.w
    
    def refreshCallback(self, sender=None):
        """
        Update the font list.
        """
        self.getView().fontList.set(self.getFontItems())
    
    def resetCallback(self, sender=None):
        """
        Resets the view to the currently opened fonts.
        """
        self.tool.fonts = AllFonts()
        self.getView().fontList.set(self.getFontItems())
    
    def addCallback(self, sender=None):
        """
        Open a font without UI and add it to the font list.
        """
        f = OpenFont(None, showUI=False)
        if f is None:
            return
        self.tool.appendToFonts(f.path)
        self.refreshCallback()
        
    def populateView(self):
        """
        The UI
        """
        self.fillColor = getExtensionDefaultColor(self.DEFAULTKEY_FILLCOLOR, self.FALLBACK_FILLCOLOR)
        self.strokeColor = getExtensionDefaultColor(self.DEFAULTKEY_STROKECOLOR, self.FALLBACK_STROKECOLOR)
        self.contextBefore = self.contextAfter = ''
        
        # Populating the view can only happen after the view is attached to the window,
        # or else the relative widths go wrong.
        view = self.getView()
        view.add = Button((-40, 3, 30, 22), '+', callback=self.addCallback)
        view.reset = Button((-40, 30, 30, 22), unichr(8634), callback=self.resetCallback)
        # Flag to see if the selection list click is in progress. We are resetting the selection
        # ourselves, using the list "buttons", but changing that selection will cause another
        # list update, that should be ignored.
        self._selectionChanging = False
        # Indicate that we are a drawing module
        self._canDraw = True
    
        self.sources = []

        x = y = 4

        view.fontList = List((C.C2, y, 250, -65), self.getFontItems(), 
            selectionCallback=self.fontListCallback,
            drawFocusRing=False, 
            enableDelete=False, 
            allowsMultipleSelection=False,
            allowsEmptySelection=True,
            drawHorizontalLines=True,
            showColumnTitles=False,
            columnDescriptions=self.getPathListDescriptor(),
            rowHeight=16,
        )         
        view.viewEnabled = CheckBox((x, y, C.BUTTON_WIDTH, 22), "Show", 
             callback=self.viewCallback, sizeStyle=C.STYLE_CHECKBOXSIZE, 
             value=True)
        y += C.L
        view.fill = CheckBox((x, y, 60, 22), "Fill", sizeStyle=C.STYLE_CHECKBOXSIZE, 
            #value=getExtensionDefault("%s.%s" %(self.DEFAULTKEY, "fill"), True),
            value = True,
            callback=self.fillCallback)
        y += C.L
        color = getExtensionDefaultColor(self.DEFAULTKEY_FILLCOLOR, self.FALLBACK_FILLCOLOR)
        view.color = ColorWell((x, y, 60, 22), 
            color=color,
            callback=self.colorCallback)
        y += C.L + 5
        view.stroke = CheckBox((x, y, 60, 22), "Stroke", sizeStyle=C.STYLE_CHECKBOXSIZE, 
            #value=getExtensionDefault("%s.%s" %(self.DEFAULTKEY, "stroke"), False),
            value = False, 
            callback=self.strokeCallback)

        y += C.LL
        view.alignText = TextBox((x, y, 90, 50), 'Alignment', sizeStyle=C.STYLE_LABELSIZE)
        y += C.L
        view.align = RadioGroup((x, y, 90, 50), ['Left', 'Center', 'Right'], isVertical=True, 
            sizeStyle=C.STYLE_RADIOSIZE, callback=self.alignCallback)
        view.align.set(0)
        
        #view.contextLabel = TextBox((C.C2, -58, 90, 50), 'Contexts', sizeStyle=C.STYLE_LABELSIZE)

        view.viewCurrent = CheckBox((C.C2, -60, 150, 22), "Always View Current", sizeStyle=C.STYLE_CHECKBOXSIZE,
            value = False,
            callback=self.contextEditCallback)

        #view.contextUandlc = CheckBox((C.C2+170, -60, 85, 22), "Match Case", sizeStyle=C.STYLE_CHECKBOXSIZE,
        #    value = False,
        #    callback=self.contextEditCallback)

        view.contextBefore = EditText((C.C2, -30, 85, 20), callback=self.contextEditCallback, continuous=True, sizeStyle="small", placeholder='Left Context')
        view.contextCurrent = EditText((C.C2+95, -30, 60, 20), callback=self.contextCurrentEditCallback, continuous=True, sizeStyle="small")
        view.contextAfter = EditText((C.C2+165, -30, 85, 20), callback=self.contextEditCallback, continuous=True, sizeStyle="small", placeholder='Right Context')
        self.activateModule()
        self.setUpBaseWindowBehavior()

    def fontListCallback(self, sender):
        u"""If there is a selection, toggle the status of these fonts."""
        # Avoid recursive loop because of changing font selection
        if not self._selectionChanging:
            for selectedIndex in sender.getSelection():
                item = sender.get()[selectedIndex]
                if item['status']:
                    item['status'] = ''
                else:
                    item['status'] = selectedSymbol
            self._selectionChanging = True
            # Avoid recursive loop because of changing font selection
            sender.setSelection([])
            self._selectionChanging = False
        self.updateView()

    def canDraw(self):
        return True

    """
    There is an experimental feature that will change the case of the context characters based on the case of the current glyph. But I'm disabling that for now.
    """
    #def isUpper(self, g):
    #    char = CharacterTX.glyph2Char(g)
    #    if len(char) > 1:
    #        char = char[0]
    #    if unicodedata.category(char) == 'Lu':
    #        return True
    #    return False

    #def isLower(self, g):
    #    char = CharacterTX.glyph2Char(g)
    #    if len(char) > 1:
    #        char = char[0]
    #    if unicodedata.category(char) == 'Ll':
    #        return True
    #    return False

    def getHiddenFont(self, path):
        for f in self.tool.getFonts():
            if f.path == path:
                return f
            elif path == str(f.info.familyName)+" "+str(f.info.styleName):
                return f

    def drawBackground(self, info):
        u"""Draw the background of defined glyphs and fonbts. 
        Scale is available as mouse.scale."""        
        view = self.getView()
        if not view.viewEnabled.get():
            return
        fill = getExtensionDefault(self.DEFAULTKEY_FILL, True)
        stroke = getExtensionDefault(self.DEFAULTKEY_STROKE, True)
        fillcolor = getExtensionDefaultColor(self.DEFAULTKEY_FILLCOLOR, self.FALLBACK_FILLCOLOR)

        
        glyph = info.get('glyph')
        if glyph is not None:
            current = glyph.getParent()
        else:
            current = self.tool.getCurrentFont()
        if glyph is None or current is None:
            return 
        align = self.getAlignment()
        
        # Get the fonts from the list and see if they are selected.
        sourceItems = self.getSourceFonts()
        showFonts = []
        for item in sourceItems:
            if not item['status']:
                continue
            path = item['path']
            font = self.getHiddenFont(path)
            showFonts.append(font)
        
        if view.viewCurrent.get() and current not in showFonts:
            showFonts.append(current)
    
        for font in showFonts:
            self.fillColor.setFill()
            self.strokeColor.setStroke()
            
            contextBefore, contextCurrent, contextAfter = self.getContexts()
            
            if font is not None:   
                contextBefore = splitText(contextBefore, TX.naked(font).unicodeData, TX.naked(font).groups)
                contextBefore = [font[gname] for gname in contextBefore if gname in font.keys()]
                contextAfter = splitText(contextAfter, TX.naked(font).unicodeData, TX.naked(font).groups)
                contextAfter = [font[gname] for gname in contextAfter if gname in font.keys()]
                contextCurrent = splitText(contextCurrent, TX.naked(font).unicodeData, TX.naked(font).groups)
                if len(contextCurrent) > 0:
                    contextCurrent = [font[gname] for gname in [contextCurrent[0]] if gname in font.keys()]
                    if len(contextCurrent) > 0:
                        sourceGlyph = contextCurrent[0]
                    else:
                        sourceGlyph = None
                elif glyph.name in font.keys():
                    sourceGlyph = font[glyph.name]
                else:
                    sourceGlyph = None       
                
                """
                #There is an experimental feature that will change the case of the context characters based on the case of the current glyph. But I'm disabling that for now.
                
                if view.contextUandlc.get():
                    caseTransform = None
                    if self.isUpper(glyph):
                        caseTransform = FontTX.unicodes.getUpperFromLower
                    elif self.isLower(glyph):
                        caseTransform = FontTX.unicodes.getLowerFromUpper
                    if caseTransform:
                        for i, g in enumerate(contextBefore):
                            newG = caseTransform(g)
                            if newG is not None:
                                contextBefore[i] = newG
                        newG = caseTransform(sourceGlyph)
                        if newG is not None:
                            sourceGlyph = newG
                    if caseTransform:
                        for i, g in enumerate(contextAfter):
                            newG = caseTransform(g)
                            if newG is not None:
                                contextAfter[i] = newG  
                """                      
                                         
                scale(current.info.unitsPerEm/float(font.info.unitsPerEm))
                 
                widthOffset = 0
                if sourceGlyph is not None:
                    if align == 'center':
                        destCenter = float(glyph.width/2) / current.info.unitsPerEm
                        sourceCenter = float(sourceGlyph.width/2) / font.info.unitsPerEm
                        widthOffset = (destCenter-sourceCenter) * font.info.unitsPerEm
                    elif align == 'right':
                        widthOffset = ( (  glyph.width / glyph.getParent().info.unitsPerEm ) - (sourceGlyph.width / sourceGlyph.getParent().info.unitsPerEm ) ) * font.info.unitsPerEm
                translate(widthOffset, 0)
                
                previousGlyph = sourceGlyph
                contextBefore.reverse()
                totalWidth = 0
                for i, cbGlyph in enumerate(contextBefore):
                    kernValue = 0
                    if previousGlyph is not None and previousGlyph.getParent() == cbGlyph.getParent():
                        # Uncomment to activate kerning. Requires FontTX.
                        #kernValue += FontTX.kerning.getValue((previousGlyph.name, cbGlyph.name), font.kerning, font.groups)
                        kernValue += 0
                        
                    translate(-cbGlyph.width-kernValue, 0)
                    totalWidth += cbGlyph.width + kernValue
                    drawGlyphPath = TX.naked(cbGlyph).getRepresentation("defconAppKit.NSBezierPath")
                    if view.fill.get():
                        drawGlyphPath.fill()
                    if view.stroke.get():
                        strokePixelPath(drawGlyphPath)
                    previousGlyph = cbGlyph
                translate(totalWidth, 0)
                
                totalWidth = 0
                contextCurrentAndAfter = [sourceGlyph]+contextAfter

                for i, cbGlyph in enumerate(contextCurrentAndAfter):
                    if cbGlyph is None:
                        cbGlyph = sourceGlyph
                    nextGlyph = None
                    if i + 1 < len(contextCurrentAndAfter):
                        nextGlyph = contextCurrentAndAfter[i+1]
                    if (i == 0 and cbGlyph == glyph) or sourceGlyph is None:
                        pass
                    else:
                        drawGlyphPath = TX.naked(cbGlyph).getRepresentation("defconAppKit.NSBezierPath")
                        if view.fill.get():
                            drawGlyphPath.fill()
                        if view.stroke.get():
                            strokePixelPath(drawGlyphPath)
                    kernValue = 0
                    
                    if cbGlyph is not None and nextGlyph is not None and nextGlyph.getParent() == cbGlyph.getParent():
                        #kernValue = FontTX.kerning.getValue((cbGlyph.name, nextGlyph.name), font.kerning, font.groups)
                        # Uncomment to activate kerning. Requires FontTX.
                        kernValue = 0
                    
                    width = 0
                    if cbGlyph is not None:
                        width = cbGlyph.width
                    translate(width+kernValue, 0)
                    totalWidth += width + kernValue
                    previousGlyph = cbGlyph
                
                translate(-totalWidth, 0)
                
                translate(-widthOffset, 0)
                scale(font.info.unitsPerEm/float(current.info.unitsPerEm))
        #restore()
    
    drawInactive = drawBackground

    def viewCallback(self, sender):
        self.updateView()

    def getSourceFonts(self):
        """
        Get the fonts in the list.
        """
        view = self.getView()
        return view.fontList.get()

    def setSourceFonts(self):
        u"""
        Set the font list from the current set of open fonts.
        """
        view = self.getView()
        labels = []
        currentSelection = []
        for d in self.getSourceFonts():
            if d['status']:
                currentSelection.append(d['path'])
        for status, path, name in self.tool.getFontLabels():
            if path in currentSelection:
                status = selectedSymbol
            else:
                status = ''
            labels.append(dict(status=status, path=path, name=name))
        view.fontList.set(labels)

    def colorCallback(self, sender):
        """
        Change the color.
        """
        selectedColor = sender.get()
        r = selectedColor.redComponent()
        g = selectedColor.greenComponent()
        b = selectedColor.blueComponent()
        a = 1
        strokeColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, a)
        setExtensionDefaultColor(self.DEFAULTKEY_FILLCOLOR, selectedColor)
        setExtensionDefaultColor(self.DEFAULTKEY_STROKECOLOR, strokeColor)
        self.fillColor = selectedColor
        self.strokeColor = strokeColor
        self.updateView()

    def fillCallback(self, sender):
        """
        Change the fill status.
        """
        setExtensionDefault(self.DEFAULTKEY_FILL, sender.get())
        self.updateView()

    def strokeCallback(self, sender):
        """
        Change the stroke status.
        """
        setExtensionDefault(self.DEFAULTKEY_STROKE, sender.get())
        self.updateView()

    def alignCallback(self, sender):
        """
        Change the alignment status.
        """
        self.updateView()

    def getAlignment(self):
        """
        Get the alignment as a string.
        """
        view = self.getView()
        index = view.align.get()
        if index == 0:
            return 'left'
        elif index == 1:
            return 'center'
        elif index == 2:
            return 'right'

    def updateView(self, sender=None):
        UpdateCurrentGlyphView()

    def windowCloseCallback(self, sender):
        self.deactivateModule()
        self.updateView()
        BaseWindowController.windowCloseCallback(self, sender)

    def getFontItems(self, update=False):
        """
        Get all fonts in a way that can be set into a vanilla list.
        """
        paths = set() # Set of all unique paths in the merges lists
        itemsByName = {}
        if update: # If update flag is set, then keep the existing selected fonts.
            for item in self.getSourceFonts():
                if item['status']:
                    itemsByName[item['name']] = item
        currentStatuses = {}
        if hasattr(self.getView(), 'fontList'):
            for d in self.getSourceFonts():
                currentStatuses[d['path']] = d['status']

        for status, path, uniqueName in self.tool.getFontLabels():
            if currentStatuses.has_key(path):
                status = currentStatuses[path]
            else:
                status = selectedSymbol

            if not uniqueName in itemsByName.keys():# If it is not already there, add this to the list
                itemsByName[uniqueName] = dict(status=status, path=path, name=uniqueName)
        fontList = []
        for key, item in sorted(itemsByName.items()):
            fontList.append(item)
        return fontList
    
    ################
    # CONTEXTS
    ################
    
    def getContexts(self):
        if not hasattr(self, 'contextBefore'):
            self.contextBefore = ''
        if not hasattr(self, 'contextAfter'):
            self.contextAfter = ''
        if not hasattr(self, 'contextCurrent'):
            self.contextCurrent = None
        return self.contextBefore, self.contextCurrent, self.contextAfter
        
    def setContexts(self, contextBefore, contextCurrent, contextAfter):
        
        self.contextBefore = contextBefore
        self.contextCurrent = contextCurrent
        self.contextAfter = contextAfter
        
    def contextEditCallback(self, sender):
        before = self.getView().contextBefore.get()
        current = self.getView().contextCurrent.get() or None
        after = self.getView().contextAfter.get()
        self.setContexts(before, current, after)
        self.updateView()
            
    def contextCurrentEditCallback(self, sender):
        #if sender.get():
            #sender.set(sender.get()[0])
        self.contextEditCallback(sender)



if __name__ == "__main__":
    
    OverlayUFOs()
########NEW FILE########
__FILENAME__ = peanutGallery
#coding=utf-8
from mojo.events import BaseEventTool, installTool
from collections import OrderedDict
from AppKit import *
from defconAppKit.windows.baseWindow import BaseWindowController
from mojo.drawingTools import *
from mojo.extensions import ExtensionBundle
from vanilla import *
from mojo.UI import UpdateCurrentGlyphView, setGlyphViewDisplaySettings, getGlyphViewDisplaySettings, CurrentGlyphWindow

class TX: # Transformer
    @classmethod
    def isUniqueDict(cls, d):
        if cls.isUniqueList(d.values()):
            return True
        else:
            return False

    @classmethod
    def reverseDict(cls, d):
        if not cls.isUniqueDict(d):
            usedValues = []
            duplicateValues = []
            for v in d.values():
                if v in usedValues:
                    duplicateValues.append(v)
                usedValues.append(v)

COMMENT_LIB_KEY = 'com.fontbureau.comments'
COMMENT_TYPE_ICONS = {
                      
                'comment': u'💬',
                #'moveLeft': u'◀',
                #'moveRight': u'▶',
                #'moveUp': u'▲',
                #'moveDown': u'▼',
                'moveLeft': u'←',
                'moveRight': u'→',
                'moveUp': u'↑',
                'moveDown': u'↓',
                'moveUpLeft': u'↖',
                'moveUpRight': u'↗',
                'moveDownLeft': u'↙',
                'moveDownRight': u'↘',
                'round': u'◯',
                'add': u'╋',
                'subtract': u'━',
                'happy': u'😀',
                'surprise': u'😮',
                'cyclone': u'🌀',
                'saltire': u'☓',
                }

COMMENT_TYPE_ORDER_1 = ['moveUpLeft', 'moveUp',  'moveUpRight', 'add', 'happy',
                        'moveLeft', 'comment', 'moveRight', 'subtract', 'surprise',
                        'moveDownLeft', 'moveDown', 'moveDownRight', 'saltire', 'cyclone']

import unicodedata

try:
    bundle = ExtensionBundle("PeanutGallery")
    toolbarIcon = bundle.getResourceImage("peanutGallery")
    toolbarIcon.setSize_((16, 16))
except:
    pass


class Comment(OrderedDict):
    pass        
    
class Commentary(OrderedDict):
    pass


class CommentDialog(BaseWindowController):
    
    COMMENT_LIB_KEY = COMMENT_LIB_KEY
    COMMENT_TYPE_ORDER = COMMENT_TYPE_ORDER_1
    COMMENT_TYPE_ORDER_1 = COMMENT_TYPE_ORDER_1
    COMMENT_TYPE_ICONS = COMMENT_TYPE_ICONS

        
    def __init__(self, parent, commentInfo={}, edit=False):
        self.parent = parent
        self.original = commentInfo
        self.commentInfo = commentInfo
        
        # title
        if edit:
            title = 'Edit Comment'
            buttonTitle = u'Edit →'
        else:
            title = 'Add Comment'
            buttonTitle = u'Add →'
        self.w = Window((400, 110), title, closable=True)
        yoffset = 10
        lineHeight = 22
        itemHeight = 22
        
        # text
        self.w.commentText = EditText((10, yoffset, -10, itemHeight), commentInfo.get('commentText') or '')
        yoffset += lineHeight
    
        # type
        commentType = 'comment'
        if commentInfo.has_key('commentType'):
            commentType = commentInfo.get('commentType')
        if commentType in self.COMMENT_TYPE_ICONS:
            currentIcon = self.COMMENT_TYPE_ICONS[commentType]
        else:
            currentIcon = self.parent.getIcon()
        self.w.commentTypePreview = TextBox((10, yoffset+5, 35, itemHeight), currentIcon)
        xoffset = 35
        for i, buildType in enumerate(self.COMMENT_TYPE_ORDER_1):
            icon = self.COMMENT_TYPE_ICONS[buildType]
            setattr(self.w, buildType+'Button', Button((xoffset, yoffset, 35, itemHeight), icon, callback=self.commentTypeCallback, sizeStyle="mini"))
            xoffset += 35
            if (i+1)/5 == int((i+1)/5):
                xoffset = 35
                yoffset += lineHeight
        yoffset -= lineHeight * 3
        
        # buttons
        self.w.ok = Button((-100, yoffset, -10, 20), buttonTitle, callback=self.okCallback, sizeStyle='mini')
        yoffset += lineHeight * 2
        self.w.ok.bind("rightarrow", [])
        if edit:
            self.w.delete = Button((-100, yoffset, -10, 20), 'Delete', callback=self.deleteCallback, sizeStyle='mini')
        else:
            self.w.clear = Button((-100, yoffset, -10, 20), 'Clear', callback=self.clearCallback, sizeStyle='mini')
        self.w.open()
        self.setUpBaseWindowBehavior()
    
    def commentTypeCallback(self, sender):
        for i, buildType in enumerate(self.COMMENT_TYPE_ORDER_1):
            icon = self.COMMENT_TYPE_ICONS[buildType]
            if getattr(self.w, buildType+'Button') == sender:
                self.commentInfo['commentType'] = buildType
                self.w.commentTypePreview.set(icon)
    
    def okCallback(self, sender):
        commentInfo = Comment()
        commentInfo['coords'] = self.commentInfo['coords']
        commentText = self.w.commentText.get()
        if commentText:
            commentInfo['commentText'] = commentText
        commentType = self.commentInfo.get('commentType') or 'comment'
        if commentType:
            commentInfo['commentType'] = commentType
        self.parent.addComment(commentInfo)
        self.w.close()
       
    def deleteCallback(self, sender):
        commentInfo = self.commentInfo
        id = self.parent.getID(commentInfo.get('coords'))
        self.parent.removeComment(id)
        if sender:
            self.w.close()
        
    def clearCallback(self, sender):
        self.parent.clearComments()
        if sender:
            self.w.close()

class PeanutGallery(BaseEventTool):
    u"""
    Shows the bounding box and useful divisions.
    """
    
    COMMENT_LIB_KEY = COMMENT_LIB_KEY
    COMMENT_TYPE_ICONS = COMMENT_TYPE_ICONS
    

    xBufferLeft = 20
    xBufferRight = 20
    yBufferTop = 20
    yBufferBottom = 20
    
    def getCurrentFont(self):
        if hasattr(self, 'f'):
            return self.f
        else:
            return CurrentFont()
    
    def setCurrentFont(self, f):
        self.f = f
        
    def prepareUndo(self, g=None):
        if g is None:
            g = self.getGlyph()
        try:
            g.prepareUndo()
        except:
            pass
            
    def performUndo(self, g=None):
        if g is None:
            g = self.getGlyph()
        try:
            g.performUndo()
        except:
            pass  

    def readComments(self, g=None):
        if g is None:
            g = self.getGlyph()
        if g is not None and g.lib.has_key(self.COMMENT_LIB_KEY):
            return Commentary(g.lib[self.COMMENT_LIB_KEY])
        else:
            return Commentary()
    
    def writeComments(self, g=None):
        if g is None:
            g = self.getGlyph()
        if g is not None:
            comments = self.getComments()
            g.lib[self.COMMENT_LIB_KEY] = comments
        
    def setComments(self, comments):
        self.comments = comments
        self.writeComments()
        #self.setFontComments()
        self.updateView()
    
    def setComment(self, commentKey, commentValue):
        self.getComments()[commentKey] = commentValue
        self.writeComments()
        #self.setFontComments()
        self.updateView()
        
    def addComment(self, commentInfo):
        self.prepareUndo()
        comment = Comment(commentInfo)
        self.getComments()[self.getID(commentInfo['coords'])] = comment
        self.writeComments()
        #self.setFontComments()
        self.updateView()
        self.performUndo()
        
    def clearComments(self):
        self.prepareUndo()
        self.setComments(Commentary())
        self.writeComments()
        #self.setFontComments()
        self.updateView()
        self.performUndo()
        
    def removeComment(self, commentKey):
        self.prepareUndo()
        if self.getComments().has_key(commentKey):
            del self.getComments()[commentKey]
        self.writeComments()
        #self.setFontComments()
        self.updateView()
        self.performUndo()
    
    def getComments(self):
        if not hasattr(self, 'comments'):
            self.comments = Commentary()
        return self.comments

    def getIcon(self, commentType=None):
        if self.COMMENT_TYPE_ICONS.has_key(commentType):
            return self.COMMENT_TYPE_ICONS[commentType]
        else:
            return u'💬'
            
    def getNameForIcon(self, icon=""):
        map = TX.reverseDict(COMMENT_TYPE_ICONS)
        if map.has_key(icon):
            return map[icon]

    def getID(self, coords):
        x, y = coords
        return '%s,%s' %(int(x), int(y))

    def getSelectedComments(self):
        if hasattr(self, 'selectedComments'):
            return self.selectedComments
        else:
            return []

    def readFontComments(self, f=None):
        if f is None:
            g = self.getGlyph()
            if g is None:
                f = CurrentFont()
            else:
                f = g.getParent()
        self.setCurrentFont(f)
        allComments = []
        for gname in f.glyphOrder:
            if f.has_key(gname):
                g = f[gname]
                comments = self.readComments(g)
                if comments:
                    for commentID, comment in comments.items():
                        coords = comment.get('coords')
                        x, y = coords
                        x = int(round(x))
                        y = int(round(y))
                        c = {
                             'Coords': coords,
                             'ID': commentID,
                             'Glyph': g.name, 
                             'Type': self.getIcon(comment.get('commentType')), 
                             'Text': comment.get('commentText') or '', 
                             'Done': comment.get('done') or False,
                             }
                        allComments.append(c)
        return allComments
        
    def setFontComments(self):
        if hasattr(self, 'w'):
            allComments = self.readFontComments()
            self.w.fontCommentsList.set(allComments)
        else:
            print 'no window to set'

    def refreshFontComments(self, sender):
        self.setFontComments()

    # ACTIVITY

    def becomeActive(self):
        #print 'becoming active'
        # read the comments into the tool    
        self.setComments(self.readComments())
        # do custom display settings
        self.originalDisplaySettings = getGlyphViewDisplaySettings()
        self.setCustomViewSettings()
        self.windowSelection = []
        fontComments = self.readFontComments()
        self.w = Window( (300, 500), 'Commentary', minSize=(200, 400), closable=True )
        self.w.fontCommentsList = List((10, 10, -10, -40),
                             fontComments,
                             columnDescriptions=[
                                                 {"title": "Glyph", "width": 60, 'editable': False}, 
                                                 {"title": "Type", "width": 40, 'editable': False}, 
                                                 {"title": "Text", 'editable': True, "width": 130},
                                                 {"title": "Done", 'cell': CheckBoxListCell(), "width": 40},

                                                 {"title": "Coords", "width": 0, 'editable': False}, 
                                                 {"title": "ID", "width": 0, 'editable': False}
                                                 ],
                             selectionCallback=self.selectionCallback,
                             allowsMultipleSelection=False,
                             editCallback=self.editCallback,
                             #dragSettings=dict(type="smartListPboardType", callback=self.dragCallback),
                             enableDelete=True
                             )
        self.w.goButton = Button((10, -30, 30, -10), unichr(8634), self.refreshFontComments)
        
        #'moveLeft': u'←',
        #'moveRight': u'→',
        
        self.w.previous = Button((-80, -30, 35, -10), u'←', self.goToPrevious)
        self.w.next = Button((-40, -30, 35, -10), u'→', self.goToNext)
        
        self.w.toggle = Button((-160, -30, 35, -10), u'👀', self.toggleView)
        
        self.w.open()

    def becomeInactive(self):
        """
        
        """
        self.setOriginalViewSettings()
        # close any open dialogs
        if hasattr(self, 'openDialog'):
            try:
                self.openDialog.w.close()
            except:
                pass
        try:
            self.w.close()
        except:
            pass

    def setOriginalViewSettings(self, sender=None):
        # return display settings to how they were
        setGlyphViewDisplaySettings(self.originalDisplaySettings)
        self.viewMode = 'original'

    def setCustomViewSettings(self, sender=None):
        settings = {u'Component Indexes': False, 
                    u'Component info': False, 
                    u'Anchors': False, 
                    u'Point Indexes': False, 
                    u'Labels': False, 
                    u'Blues': False, 
                    u'Bitmap': False, 
                    u'Metrics': True, 
                    u'Rulers': True, 
                    u'Stroke': False, 
                    u'Family Blues': False, 
                    u'Grid': False, 
                    u'Point Coordinates': False, 
                    u'Anchor Indexes': False, 
                    u'Outline Errors': 0L, 
                    u'Off Curve Points': False, 
                    u'On Curve Points': False, 
                    u'Contour Indexes': False, 
                    u'Curve Length': False, 
                    u'Fill': True,
                    }
        setGlyphViewDisplaySettings(settings)
        self.viewMode = 'custom'
        
    def toggleView(self, sender=None):
        if self.viewMode == 'custom':
            self.setOriginalViewSettings()
        else:
            self.setCustomViewSettings()

    def selectionCallback(self, sender):
        self.changeCommentCallback(sender)
    
    def editCallback(self, sender):
        commentDicts = sender.get()
        selection = sender.getSelection()
        if selection:
            commentDict = commentDicts[selection[0]]
            comment = {}
            id = commentDict['ID']
            comment['coords'] = commentDict['Coords']
            comment['commentText'] = commentDict['Text']            
            comment['commentType'] = self.getNameForIcon(commentDict['Type'])
            comment['done'] = commentDict['Done']
            self.addComment(comment)
        
    def goToNext(self, sender):
        selection = self.w.fontCommentsList.getSelection()
        if selection:
            selection = selection[0]
            if selection < len(self.w.fontCommentsList):
                self.w.fontCommentsList.setSelection([selection+1])
            #else:
            #    self.w.fontCommentsList.setSelection([0])
        self.changeCommentCallback(sender)
        
    def goToPrevious(self, sender):
        selection = self.w.fontCommentsList.getSelection()
        if selection:
            selection = selection[0]
            if selection > 0:
                self.w.fontCommentsList.setSelection([selection-1])
            #else:
            #    self.w.fontCommentsList.setSelection([len(self.w.fontCommentsList)-1])
        self.changeCommentCallback(sender)
             
    def changeCommentCallback(self, sender):
        selection = self.w.fontCommentsList.getSelection()
        commentDicts = self.w.fontCommentsList.get()
        if selection:
            commentDict = commentDicts[selection[0]]
            if hasattr(self, 'f') and self.f.has_key(commentDict['Glyph']):
                CurrentGlyphWindow().setGlyph(self.f[commentDict['Glyph']].naked()) 
                self.selectedComments = [commentDict['ID']]

    def getToolbarTip(self):
        return "Peanut Gallery"
        
    def getToolbarIcon(self):
        return toolbarIcon
    
    def mouseMoved(self, point):
        self.coords = point.x, point.y

    def getMouseCoords(self):
        if hasattr(self, 'coords'):
            return self.coords
        else:
            return (0, 0)

    def closeOpenDialogs(self):
        if hasattr(self, 'openDialogs'):
            for dialog in openDialogs:
                dialog.close()

    def getSelected(self, coords):

        coords = self.getMouseCoords()
        for commentIDs, commentInfo in self.getComments().items():
            commentCoords = commentInfo.get('coords') or (0, 0)
            xmin = commentCoords[0] - self.xBufferLeft
            ymin = commentCoords[1] - self.yBufferBottom
            xmax = commentCoords[0] + self.xBufferRight
            ymax = commentCoords[1] + self.yBufferTop
            if xmin <= coords[0] <= xmax and ymin <= coords[1] <= ymax:
                return commentInfo
    
    def mouseDown(self, point, clickCount):
        if hasattr(self, 'openDialog'):
            try:
                self.openDialog.w.close()
            except:
                pass
        coords = self.getMouseCoords()
        self.dragSelected = self.getSelected(coords)
        if clickCount == 2:
            selected = self.getSelected(coords)
            if selected:
                self.openDialog = CommentDialog(self, selected, edit=True)
            else:
                commentInfo = Comment(coords=coords)
                self.openDialog = CommentDialog(self, commentInfo)
    
    def mouseDragged(self, point, delta):
        if self.dragSelected:
            commentInfo = self.dragSelected

            commentCoords = commentInfo.get('coords')
            commentID = self.getID(commentCoords)
            newCoordX = point.x + delta.x/2.0
            newCoordY = point.y + delta.y/2.0
            newCoords = newCoordX, newCoordY
            # remove the entry, and replace it
            if self.getComments().has_key(commentID):
                self.removeComment(commentID)
                commentInfo['coords'] = newCoords
                self.addComment(commentInfo)
                self.dragSelected = commentInfo
            
    def keyUp(self, event):
        char = event.charactersIgnoringModifiers()        
        commentType = None
        #char == unichr(63232) or 
        if char == 'W':
            commentType = 'moveUp'
        # char == unichr(63233)
        elif char == 'X':
            commentType = 'moveDown'
        # char == unichr(63234) or
        elif char == 'A':
            commentType = 'moveLeft'
        #char == unichr(63235) or
        elif char == 'D':
            commentType = 'moveRight'
        elif char == 'Q':
            commentType = 'moveUpLeft'
        elif char == 'E':
            commentType = 'moveUpRight'
        elif char == 'Z':
            commentType = 'moveDownLeft'
        elif char == 'C':
            commentType = 'moveDownRight'
        elif char == 'S':
            commentType = 'comment'
        elif char == '!':
            commentType = 'subtract'
        elif char == '@':
            commentType = 'add'

        if commentType:
            self.addComment({'commentType': commentType, 'coords': self.getMouseCoords()})
    
    
    def viewDidChangeGlyph(self):
        self.setComments(self.readComments())
        
    def updateView(self):
        #print 'updating view'
        #self.setFontComments()
        UpdateCurrentGlyphView()
    
    def draw(self, scaleValue):
        
        iconSize = 30
        
        commentBoxes = []
        for commentID, commentInfo in self.getComments().items():
            commentCoords = commentInfo.get('coords') or (0, 0)

            commentType = commentInfo.get('commentType')
            if self.COMMENT_TYPE_ICONS.has_key(commentType):
                icon = self.COMMENT_TYPE_ICONS[commentType]
            else:
                icon = self.COMMENT_TYPE_ICONS['comment']
            commentText = commentInfo.get('commentText') or ''
            drawCoordsX, drawCoordsY = commentCoords

            if commentInfo.get("done"):
                fillr, fillg, fillb = (.5, .5, 1)
            else:
                fillr, fillg, fillb = (1, .5, .5)
            
            if commentID in self.getSelectedComments():
                fill(fillr, fillg, fillb, .5)
                rect(drawCoordsX-iconSize/2, drawCoordsY-10, iconSize, iconSize)


            fill(fillr, fillg, fillb, 1)
                
            strokeWidth(0)
            stroke()
            font('LucidaGrande')
            fontSize(iconSize)        
            
            text(icon, (drawCoordsX-iconSize/2, drawCoordsY-iconSize/2 ) )
            #fill(1, 0, 0, 1)
            #oval(drawCoordsX-4, drawCoordsY-4, 8, 8)

            fontSize(10*scaleValue)
            
            text(commentText, (drawCoordsX+17, drawCoordsY+0))
            
    
    def drawInactive(self, scaleValue, glyph, view):
        self.draw(scaleValue)
    
installTool(PeanutGallery())
########NEW FILE########
__FILENAME__ = randomWordGenerator
# a quick random word generator for typeface design class
"""
If you have a space center open, this will replace the text with a bunch of random words. Otherwise it will simply print to the output window!

I am not responsible for naughty or otherwise inappropriate words!

"""
import random
from vanilla import *
from mojo.UI import *

class RandomWordsWindow:
    def __init__(self):
        self.words = []
        self.charsInFont = []
        
        wordsFile = open('/usr/share/dict/words', 'r')
        wordsText = wordsFile.read()
        self.allWords = wordsText.split('\n')

        y = 10        
        self.w = Window((350, 100), 'Random Words')

        self.w.countText = TextBox((10, y, 100, 22), 'Word Count') 
        
        self.w.wordCount = Slider((100, y, -10, 22), value=10,
                                        maxValue=100,
                                        minValue=0,
                                        tickMarkCount = 10,
                                        #stopOnTickMarks = True,
                                        callback= self.set)
        
        #self.w.wordLength = TextBox((10, 40, 100, 22), 'Word Length') 
        #self.w.minWordLength = EditText((110, 40, 30, 22), "5", callback=self.makeWordsCallback) 
        #self.w.maxWordLength = EditText((150, 40, 30, 22), "12", callback=self.makeWordsCallback)
        y += 30
        self.w.capitalize = CheckBox((10, y, 100, 22), 'Capitalize', value=True, callback=self.set)
        self.w.allCaps = CheckBox((110, y, 100, 22), 'All Caps', value=False, callback=self.set)
        self.w.newWords = Button((200, y, -10, 22), 'New Words', callback=self.makeWordsCallback)

        y += 30
        self.w.charLimit = CheckBox((10, y, -10, 22), 'Limit to characters in font', value=False, callback=self.set)


        self.w.open()
        self.makeWordsCallback()
    
    def getCharsInFont(self, f):
        chars = []
        for g in f:
            if not g.template:
                for u in g.unicodes:
                    chars.append(unichr(u))
        return chars
    
    def addWord(self, min=0, max=100, charLimit=None):
        complete = False
        tick = 0
        while complete is not True:
            tick += 1
            word = random.choice(self.allWords)
            go = True
            if len(word) > min and len(word) < max:
                go = False
            #if self.w.charLimit.get() and charLimit:
            #    print 'analyzing charLimit', word, u''.join(charLimit)
            #    for c in word:
            #        if c not in charLimit:
            #            go = False
            #            print word, c
            #            break
            if go:    
                self.words.append(word)
                complete = True
            if tick > 500:
                complete = True

    def trimWords(self, count):
        self.words = self.words[:count-1]

    def makeWordsCallback(self, sender=None):
        self.words = []
        wordCount = 200
        
        # these are set explicitly! too much of a pain otherwise!
        wordLengthMin = 3  
        wordLengthMax = 12
        
        for x in range(0, wordCount):
            self.addWord(wordLengthMin, wordLengthMax)
        self.set()
    
    def set(self, sender=None):
        c = CurrentSpaceCenter()
        if c:
            charLimit = self.getCharsInFont(c.font)
        else:
            charLimit = None
        
        words = self.words[:int(self.w.wordCount.get())]
        if self.w.capitalize.get():
            words = [w.capitalize() for w in words]
        if self.w.allCaps.get():
            words = [w.upper() for w in words]
        if self.w.charLimit.get() and charLimit:
            for i, origWord in enumerate(words):
                newWord = []
                for char in origWord:
                    if char in charLimit:
                        newWord.append(char)
                words[i] = ''.join(newWord)
        try:
            c.setRaw(' '.join(words))
        except:
            print ' '.join(words)

RandomWordsWindow()
########NEW FILE########
__FILENAME__ = italicSlantOffsetAdjust
#coding=utf-8
### Italic Slant Offset Adjust
"""
Takes all open fonts that have been skewed from the baseline, and offsets them by the Italic Slant Offset value accessible in Font Info > RoboFont. Offsets contours, anchors, guides, and the image for foreground layer and all other layers.
"""

# override the italic slant offset that exists in the fonts?
italicSlantOffsetOverride = None
# Print every object that is offset?
DEBUG = False

def offsetGlyph(g, xoffset, doContours=True, doAnchors=True, doGuides=True, doImage=True, DEBUG=DEBUG):
    """
    Offsets one glyph.
    """
    # contours
    g.prepareUndo()
    if doContours:
        for c in g.contours:
            c.move((xoffset, 0))
            if DEBUG: print '\t\t\t', c
    # anchors
    if doAnchors:
        for anchor in g.anchors:
            anchor.move((xoffset, 0))
            if DEBUG: print '\t\t\t', anchor
    # guides
    if doGuides:
        for guide in g.guides:
            guide.x += xoffset
            if DEBUG: print '\t\t\t', guide, guide.x
    # image
    if doImage:
        if g.image:
            g.image.move((xoffset, 0))
            if DEBUG: print '\t\t\t', image 
    g.performUndo() 

#process all font
fonts = AllFonts()
for f in fonts:
    xoffset = f.lib.get("com.typemytype.robofont.italicSlantOffset", 0)
    if italicSlantOffsetOverride:
        xoffset = italicSlantOffsetOverride
    if xoffset:
        print f, 'offset', xoffset, 'units'
        for g in f:
            if DEBUG: print '\t', g
            # offset glyph
            offsetGlyph(g, xoffset)
            # offset other layers of glyph
            for layerName in f.layerOrder:
                layer = g.getLayer(layerName)
                if DEBUG: print '\t\t', layer
                # apparently the guides are layer independent. don’t shift them twice!
                offsetGlyph(layer, xoffset, doGuides=False)
print 'done'
        
########NEW FILE########
__FILENAME__ = showCharacterInfo
#coding=utf-8
"""
SHOW CHARACTER INFO

"""

from vanilla import *
from defconAppKit.windows.baseWindow import BaseWindowController
from mojo.events import addObserver, removeObserver
from mojo.UI import CurrentGlyphWindow
import unicodedata
try:
    from lib.tools.agl import AGL2UV
except:
    from fontTools.agl import AGL2UV
import json
import os

nameMap = {
        'ALT': 'Alternate',
        'SALT': 'Stylistic Alternate',
        'CALT': 'Contextual Alternate',
        'SC': 'Small Cap',
        'SMCP': 'Small Cap',
        'SUPS': 'Superior',
        'SINF': 'Inferior',
        'NUMR': 'Numerator',
        'DNOM': 'Denominator',
        }

BIGUNI = None

class TX:
    @classmethod
    def hex2dec(cls, s):
            try:
                return int(s, 16)
            except:
                pass
    @classmethod
    def dec2hex(cls, n, uni = 1):
            hex = "%X" % n
            if uni == 1:
                while len(hex) <= 3:
                    hex = '0' + str(hex)
            return hex
            
    @classmethod
    def splitFourDigitUnicodeSequence(cls, l):
        u"""
        <doc><code>splitFourDigitUnicodeSequence</code> helps process unicode values.</doc>
        """
        return [l[i:i + 4] for i in range(0, len(l), 4)]

    @classmethod
    def getUnicodeSequence(cls, name, VERBOSE=False):
        """
        <doc><code>getUnicodeSequence</code> gets a unicode sequence from a unicode name, following the rules.
        <blockquote>If the component is of the form "uni" (U+0075 U+006E U+0069) followed by a sequence of uppercase
        hexadecimal digits (0 .. 9, A .. F, i.e. U+0030 .. U+0039, U+0041 .. U+0046), the length of that sequence is a
        multiple of four, and each group of four digits represents a number in the set {0x0000 .. 0xD7FF, 0xE000 ..
        0xFFFF}, then interpret each such number as a Unicode scalar value and map the component to the string made of
        those scalar values. Note that the range and digit length restrictions mean that the "uni" prefix can be used
        only with Unicode values from the Basic Multilingual Plane (BMP).</blockquote>
        
        <blockquote>Otherwise, if the component is of the form "u" (U+0075) followed by a sequence of four to six
        uppercase hexadecimal digits {0 .. 9, A .. F} (U+0030 .. U+0039, U+0041 .. U+0046), and those digits represent a
        number in {0x0000 .. 0xD7FF, 0xE000 .. 0x10FFFF}, then interpret this number as a Unicode scalar value and map
        the component to the string made of this scalar value.</blockquote></doc>
        """
        unicodeList = None
        if VERBOSE: print 'isUnicodeName, %s' % name
        if len(name) > 3 and name[:3] == 'uni':
            unicodeSequence = name[3:]
            if len(unicodeSequence) / 4 == int(len(unicodeSequence) / 4):
                unicodeList = cls.splitFourDigitUnicodeSequence(unicodeSequence)
                for unicodeHex in unicodeList:
                    if not cls.isHexDigit(unicodeHex):
                        return None
        elif len(name) > 1 and name[0] == 'u':
            unicodeSequence = name[1:]
            if len(unicodeSequence) >= 4 and len(unicodeSequence) <= 6 and cls.isHexDigit(unicodeSequence):
                if unicodeSequence:
                    unicodeList = [unicodeSequence]
                else:
                    unicodeList = unicodeSequence
        decUnicodeList = []
        if unicodeList:
            for u in unicodeList:
                try:
                    decUnicodeList.append(TX.hex2dec(u))
                except:
                    decUnicodeList.append(u)
            return decUnicodeList
        else:
            return unicodeList

    @classmethod
    def isHexDigit(cls, name):
        u"""
        <doc><code>isHexDigit</code> returns True if the given name matches a hexadecimal unicode value.</doc>
        """
        for n in name:
            if n not in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F']:
                return False
        return True


def getCharName(char, dec=None, BIGUNI=BIGUNI):
    if dec is None:
        dec = ord(char)
    try:
        return unicodedata.name(char)
    except:
        if not BIGUNI:
            bigUniFile = open(os.path.join(os.path.split(__file__)[0], 'bigUni.json'))
            BIGUNI = json.loads(bigUniFile.read())
        return BIGUNI.get(str(dec))
        
def getChar(dec):
    try:
        return unichr(dec)
    except:
        try:
            hexVersion = TX.dec2hex(dec)
            return (r'\U' + hexVersion.zfill(8)).decode('unicode-escape')
        except:
            return ''

def getGlyphInfo(g):
    # break down the name into baseName elements and suffix Elements
    if g is None:
        return ''
    gname = g.name
    nameElements = gname.split('.')
    baseName = nameElements[0]
    suffix = ''
    if len(nameElements) > 1:
        suffix = u'.'.join(nameElements[1:])
    baseNameElements = baseName.split('_')
    suffixElements = suffix.split('_')
    if suffixElements == ['']:
        suffixElements = []
    f = g.getParent()
    unicodeNameElements = []
    unicodeValueElements = []
    charString = u''
    isLig = False
    # if the glyph has unicodes, use those
    if not unicodeValueElements:
        for i, uv in enumerate(g.unicodes):
            char = getChar(uv)
            if i == 0:
                charString = char
            unicodeValueElements.append('U+'+TX.dec2hex(uv))
            charName = getCharName(char, uv)
            if charName:
                unicodeNameElements.append(charName)
    # the glyph name is a uniXXXX or a uXXXXX name, use those!
    if not unicodeValueElements:
        for i, uv in enumerate(TX.getUnicodeSequence(baseName) or []):
            char = getChar(uv)
            charString += char
            unicodeValueElements.append(u'! · ~U+'+TX.dec2hex(uv))
            if i > 0:
                isLig = True
            charName = getCharName(char, uv)
            if charName:
                unicodeNameElements.append(charName)
    # the base name is in the adobe glyph list
    if not unicodeValueElements:
        for i, baseNameElement in enumerate(baseNameElements):
            uv = AGL2UV.get(baseNameElement)
            if i > 0:
                isLig = True
            if uv:
                char = getChar(uv)
                charString += char
                unicodeValueElements.append('~U+'+TX.dec2hex(uv))
                charName = getCharName(char, uv)
                if charName:
                    unicodeNameElements.append(charName)
    # interpret this stuff into something to display
    suffixNameWords = []
    for suffixElement in suffixElements:
        suffixLabel = nameMap.get(suffixElement.upper()) or "'"+suffixElement+"'"
        if suffixLabel:
            suffixNameWords.append(suffixLabel)
    featureInfo = u' '.join(suffixNameWords)
    unicodeNameDisplay = ''

    # do special treatments for ligatures
    if isLig and charString:
        unicodeNameDisplay += 'LIGATURE ' + charString
    else:
        if unicodeNameElements:
            unicodeNameDisplay += unicodeNameElements[0]
    if isLig:
        uniValueSeparator = u'+'
    else:
        uniValueSeparator = u' '
        
    displayElements = []
    if unicodeValueElements:
        displayElements.append(uniValueSeparator.join(unicodeValueElements))
    if unicodeNameDisplay:
        displayElements.append(unicodeNameDisplay)
    if featureInfo:
        displayElements.append(featureInfo)
    if charString:
        displayElements.append(charString)
    #if not displayElements:
    #    displayElements.append('UNRECOGNIZED')
    charDisplay = u' · '.join(displayElements)
    return charDisplay


class ShowCharacterInfoBox(TextBox):
    """
    The subclassed vanilla text box.
    """
    def __init__(self, *args, **kwargs):

        self.window = kwargs['window']
        del kwargs['window']
        super(ShowCharacterInfoBox, self).__init__(*args, **kwargs)
        addObserver(self, "currentGlyphChanged", "currentGlyphChanged")
    
    def currentGlyphChanged(self, info):
        try:
            self.set(getGlyphInfo(self.window.getGlyph()))
        except:
            pass

    def _breakCycles(self):
        super(ShowCharacterInfoBox, self)._breakCycles()
        removeObserver(self, "currentGlyphChanged")

class ShowCharacterInfo(BaseWindowController):
    """
    Attach a vanilla text box to a window.
    """
    def __init__(self):
        addObserver(self, "glyphWindowDidOpen", "glyphWindowDidOpen")
        self.window = None

    def glyphWindowDidOpen(self, info):
        window = info["window"]
        self.window = window
        vanillaView = ShowCharacterInfoBox((20, -30, -20, 22), getGlyphInfo(self.window.getGlyph()), window=self.window, alignment="right", sizeStyle="mini")
        superview = window.editGlyphView.enclosingScrollView().superview()
        view = vanillaView.getNSTextField()
        frame = superview.frame()
        vanillaView._setFrame(frame)
        superview.addSubview_(view)
                
    def windowCloseCallback(self, sender):
        super(ShowCharacterInfoBox, self).windowCloseCallback(sender)
        removeObserver(self, "glyphWindowDidOpen")

ShowCharacterInfo()
#print getGlyphInfo(CurrentGlyph())
########NEW FILE########
__FILENAME__ = showDelta
from mojo.events import BaseEventTool, installTool
from AppKit import *
from mojo.events import addObserver, removeObserver
from lib.eventTools.eventManager import getActiveEventTool


fontSize = 9
bgColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 0, 0, .2)
textAttributes = {
                  NSFontAttributeName : NSFont.systemFontOfSize_(fontSize),
                  NSForegroundColorAttributeName : NSColor.whiteColor()
                  }

class ShowDelta(object):
    def __init__(self):
        addObserver(self, "_mouseDragged", "mouseDragged")
        addObserver(self, "_mouseUp", "mouseUp")
        addObserver(self, "_draw", "draw")
        self.drawAtPoint = None

    def _mouseDragged(self, info):
        self.x = round(info['delta'].x)
        self.y = round(info['delta'].y)
        self.drawAtPoint = (info['point'].x+40, info['point'].y+fontSize)

    def _mouseUp(self, info):
        self.drawAtPoint = None
    
    def _draw(self, info):
        currentTool = getActiveEventTool()
        view = currentTool.getNSView()
        if self.drawAtPoint:
            view._drawTextAtPoint("%i %i" %(self.x, self.y), textAttributes, self.drawAtPoint, yOffset=0, backgroundColor=bgColor, drawBackground=True, roundBackground=True)
        
ShowDelta()
########NEW FILE########
__FILENAME__ = showDelta
from mojo.events import BaseEventTool, installTool
from AppKit import *
from mojo.events import addObserver, removeObserver
from lib.eventTools.eventManager import getActiveEventTool


fontSize = 9
textAttributes = {
                  NSFontAttributeName : NSFont.systemFontOfSize_(fontSize),
                  NSForegroundColorAttributeName : NSColor.grayColor()
                  }

class ShowDelta(object):
    def __init__(self):
        addObserver(self, "_mouseDragged", "mouseDragged")
        addObserver(self, "_mouseUp", "mouseUp")
        addObserver(self, "_draw", "draw")
        self.drawAtPoint = None

    def _mouseDragged(self, info):
        self.x = round(info['delta'].x)
        self.y = round(info['delta'].y)
        self.drawAtPoint = (info['point'].x+10, info['point'].y + 10)

    def _mouseUp(self, info):
        self.drawAtPoint = None
    
    def _draw(self, info):
        currentTool = getActiveEventTool()
        view = currentTool.getNSView()
        if self.drawAtPoint:
            view._drawTextAtPoint("%i %i" %(self.x, self.y), textAttributes, self.drawAtPoint, yOffset=fontSize)
        else:
            print 'mouse is up'
        
ShowDelta()
########NEW FILE########
__FILENAME__ = showMouseCoordinates
#coding=utf-8
"""
SHOW MOUSE COORDINATES
2013-04-16 DJR

In the current glyph window, this extension will provide a readout of information about the mouse: its current position, how far it has been dragged, the dragging angle, and the dragging distance. The readout is positioned at the bottom left corner of the glyph window (thanks to Frederik Berlaen for his help figuring this out!).

Installing this extension will activate it; it doesn’t appear in menus.

Theoretically it should work alongside any tool: edit, pen, knife, measure, etc. For some reason I have been getting weird results with the Shape Tool though.

Released under MIT license.

## Future improvements?

- Adjust readout position when window is resized?
- Remove display when in preview mode?
- Add info relative to a given reference point? Perhaps it could look for an anchor called "reference" and use that?
- Detect when rulers are on? Too complicated, probably...

"""

from vanilla import *
from defconAppKit.windows.baseWindow import BaseWindowController
from mojo.events import addObserver, removeObserver
import math

class ShowMouseCoordinatesTextBox(TextBox):
    """
    A vanilla text box with some goodies about the mouse.
    """
    def __init__(self, *args, **kwargs):
        super(ShowMouseCoordinatesTextBox, self).__init__(*args, **kwargs)
        addObserver(self, "mouseMoved", "mouseMoved")
        addObserver(self, "mouseDragged", "mouseDragged")
        addObserver(self, "mouseUp", "mouseUp")
    
    def mouseMoved(self, info):
        point = info["point"]
        text = u"⌖ %.0f %.0f" % (point.x, point.y)
        self.set(text)

    def mouseDragged(self, info):
        point = info["point"]
        positionSymbol = unichr(8982)
        deltaPoint = info["delta"]
        angle = math.degrees(math.atan2(deltaPoint.y, deltaPoint.x))
        distance = math.hypot(deltaPoint.x, deltaPoint.y)
        text = u"⌖ %.0f %.0f   Δ %.0f %.0f   ∠ %.2f°   ↔ %.0f" % (point.x, point.y, deltaPoint.x, deltaPoint.y, angle, distance)
        self.set(text)
        
    def mouseUp(self, info):
        point = info["point"]
        text = u"⌖ %.0f %.0f" % (point.x, point.y)
        self.set(text)

    def _breakCycles(self):
        super(ShowMouseCoordinatesTextBox, self)._breakCycles()
        removeObserver(self, "mouseMoved")
        removeObserver(self, "mouseDragged")
        removeObserver(self, "mouseUp")

class ShowMouseCoordinates(BaseWindowController):
    """
    Attach a vanilla text box to a window.
    """
    def __init__(self):
        addObserver(self, "glyphWindowDidOpen", "glyphWindowDidOpen")

    def glyphWindowDidOpen(self, info):
        window = info["window"]
        vanillaView = ShowMouseCoordinatesTextBox((20, -30, -20, 22), "", alignment="left", sizeStyle="mini")
        superview = window.editGlyphView.enclosingScrollView().superview()
        view = vanillaView.getNSTextField()
        frame = superview.frame()
        vanillaView._setFrame(frame)
        superview.addSubview_(view)
                
    def windowCloseCallback(self, sender):
        super(ShowMouseCoordinatesTextBox, self).windowCloseCallback(sender)
        removeObserver(self, "glyphWindowDidOpen")

ShowMouseCoordinates()
########NEW FILE########
