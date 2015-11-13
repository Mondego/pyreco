__FILENAME__ = rest2pdf
#!/usr/bin/python
#-*- coding:utf-8 -*-
# pypdflib/widgets.py

# pypdflib is a pango/cairo framework for generating reports.
# Copyright © 2010  Santhosh Thottingal <santhosh.thottingal@gmail.com>

# This file is part of pypdflib.
#
# pypdflib is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.  
#
# pypdflib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pypdflib.  If not, see <http://www.gnu.org/licenses/>.

import sys
import codecs
from sgmllib import SGMLParser
from docutils.core import publish_parts
from docutils.writers.html4css1 import Writer
sys.path.append("../../src/")  #not good!
from pypdflib.writer import PDFWriter
from pypdflib.widgets import *
from pypdflib.styles import *

SETTINGS = {
    'cloak_email_addresses': True,
    'file_insertion_enabled': False,
    'raw_enabled': False,
    'strip_comments': True,
    'doctitle_xform': False,
    'report_level': 5,
}

class HTMLParser(SGMLParser):
    def __init__(self, verbose=0):

        "Initialise an object, passing 'verbose' to the superclass."

        SGMLParser.__init__(self, verbose)
        self.hyperlinks = []

        self.pdf = None
        
    def reset(self):                              
        SGMLParser.reset(self)
        self.images = []

        self.h1 = False
        self.h2 = False
        self.li = False
        self.p = False
        self.a = False
        self.ul = False
        self.ol = False
        self.span = False
        self.buffer = None
        
    def handle_data(self,data):
        if data.strip() == "": return
        if self.p or self.h1 or self.h2 or self.a or self.span:
            if self.buffer!=None:
                self.buffer+= data
            
                
    def start_img(self, attrs):         
        src = [value for key, value in attrs if key=='src'] 
        if src:
            self.images.extend(src)
            
    def start_h1(self, attrs):         
        self.h1=True
        self.buffer=""
        
    def end_h1(self):
        self.h1=False
        h1= Text(self.buffer,font="Serif",font_size=16) 
        self.pdf.add_text(h1)
        self.buffer = None
        
    def start_h2(self, attrs):         
        self.h2=True
        self.buffer=""
        
    def end_h2(self):
        self.h2=False
        if self.buffer and self.buffer.strip()>"":
            h2= Text(self.buffer,font="Serif",font_size=14) 
            self.pdf.add_text(h2)
        self.buffer = None
        
    def start_li(self, attrs):         
        self.li=True
        self.buffer=""
        
    def end_li(self):
        self.li=False
        if self.buffer and self.buffer.strip()>"":
            if self.ul:
                li= Text("• "+self.buffer,font_size=10) 
            else:
                li= Text(self.buffer,font_size=10)     
            self.pdf.add_text(li)
        self.buffer = None
                
    def start_a(self, attrs):         
        self.a = True
        
    def end_a(self):
        self.a = False
        
    def start_ol(self,attrs):
        self.ol=True    
    def end_ol(self):
        self.ol=False
        
    def start_ul(self,attrs):
        self.ul=True    
    def end_ul(self):
        self.ul=False
            
    def start_span(self, attrs):         
        self.span=True
        if self.buffer==None:
            self.buffer=""  
        
    def end_span(self):
        self.buffer+=" "
        self.span=False
            
    def start_p(self,attrs):
        self.p=True
        self.buffer=""
        
    def end_p(self) :
        self.p=False
        para = Paragraph(text=self.buffer, font="Serif",font_size=10,)
        para.set_justify(True)
        para.set_hyphenate(False)
        self.pdf.add_paragraph(para)   
        self.buffer = None

    def parse(self, filename, outputfile):
        try:
            text = codecs.open(filename, 'r', 'utf-8').read()
        except IOError: # given filename could not be found
            return ''
        parts = publish_parts(text, writer=Writer(), settings_overrides=SETTINGS)
        if 'html_body' in parts:
            html = parts['html_body']
        "Parse the given string 's'."
        self.pdf = PDFWriter(outputfile, StandardPaper.A4)
        footer = Footer()
        header = Header()
        self.pdf.set_footer(footer)
        self.pdf.set_header(header)
        self.feed(html)
        self.close()
        self.pdf.flush()


if __name__ == '__main__':
    parser = HTMLParser()
    parser.parse(sys.argv[1], sys.argv[2])

########NEW FILE########
__FILENAME__ = wiki2pdf
#!/usr/bin/python
#-*- coding: utf-8 -*-
# pypdflib/samples/wiki2pdf.py

# pypdflib is a pango/cairo framework for generating reports.
# Copyright © 2010  Santhosh Thottingal <santhosh.thottingal@gmail.com>

# This file is part of pypdflib.
#
# pypdflib is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.  
#
# pypdflib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pypdflib.  If not, see <http://www.gnu.org/licenses/>.


import sys
sys.path.append("../")   #not good!
sys.path.append("../../src/")  #not good!
from pypdflib.writer import PDFWriter
from pypdflib.widgets import *
from pypdflib.styles import *
import pango
import os
from HTMLParser import HTMLParser

from pyquery import PyQuery as pq
import urllib
import urlparse
import urllib2
from urllib import urlretrieve

lang_codes = {'en':'en_US',
              'ml':'ml_IN',
              'kn':'kn_IN',
              'as':'as_IN',
              'gu':'gu_IN',
              'bn':'bn_IN',
              'hi':'hi_IN',
              'mr':'mr_IN',
              'or':'or_IN',
              'pa':'pa_IN',
              'ta':'ta_IN',
              'te':'te_IN'}

class Wikiparser(HTMLParser):
    def __init__(self, url, verbose=0):
        "Initialise an object, passing 'verbose' to the superclass."
        HTMLParser.__init__(self)
        self.hyperlinks = []
        self.url = url
        self.language = detect_language(url)
        self.pdf = PDFWriter(urllib.unquote(self.url.split("/")[-1]) + ".pdf", StandardPaper.A4)
        header = Header(text_align=pango.ALIGN_CENTER)
        #TODO Alignment not working.
        header.set_text(urllib.unquote(self.url))
        self.pdf.set_header(header) 
        self.pdf.move_context(0, 500)
        h1 = Text(urllib.unquote(self.url.split("/")[-1]), font="serif", font_size=32) 
        h1.color = StandardColors.Blue
        self.pdf.add_text(h1)
        h2 = Text(urllib.unquote(self.url), font="serif", font_size=16) 
        h2.color = StandardColors.Blue
        self.pdf.add_text(h2)
        footer = Footer(text_align=pango.ALIGN_CENTER)
        footer.set_text("wiki2pdf")
        self.pdf.set_footer(footer)
        self.pdf.page_break()
        
    def reset(self):                              
        HTMLParser.reset(self)
        self.images = []
        #TODO Alignment not working.
        self.h1 = False
        self.h2 = False
        self.li = False
        self.p = False
        self.a = False
        self.ul = False
        self.ol = False
        self.span = False
        self.table = False
        self.tr = False
        self.th = False
        self.td = False
        self.caption = False
        self.reference = False
	self.ref_counter = 0
        self.column_counter = 0
        self.current_counter = 0
        self.buffer = None
        self.sup = False
        
    def handle_data(self, data):
        if data.strip() == "": return
	if self.p or self.h1 or self.h2 or self.a or self.span or self.li or self.td or self.th or self.caption:
            if self.buffer != None:
                self.buffer += data
    def handle_starttag(self, tag, attrs):
        if tag == 'img'and not self.table:
            self.start_img(attrs)
        elif tag == 'h1':
            self.start_h1(attrs)
        elif tag == 'h2':
            self.start_h2(attrs)
        elif tag == 'li':
            self.start_li(attrs)
        elif tag == 'p':
            self.start_p(attrs)
        elif tag == 'a':
            self.start_a(attrs)
        elif tag == 'ul':
            self.start_ul(attrs)
        elif tag == 'ol':
            self.start_ol(attrs)
        elif tag == 'table':
            self.start_table(attrs)
        elif tag == 'tr' and self.table:
            self.start_tr(attrs)
        elif tag == 'td' and self.table:
            self.start_td(attrs)
        elif tag == 'th'and self.table:
            self.start_th(attrs)
        elif tag == 'caption' and self.table:
            self.start_caption(attrs)
        elif tag == 'span':
	    self.start_span(attrs)
        elif tag == 'sup' or tag == 'sub' or tag == 'b' or tag == 'i' or tag == 's' or tag == 'small' or tag == 'big' or tag == 'tt' or tag == 'u':
            if self.reference == False and self.table == False:
               if self.buffer != None:
                  self.buffer += "<"+tag+">"
                  self.sup = True


    def handle_endtag(self, tag):
        if tag == 'img' and not self.table:
            self.end_img()
        elif tag == 'h1':
            self.end_h1()
        elif tag == 'h2':
            self.end_h2()
        elif tag == 'li':
            self.end_li()
        elif tag == 'p':
            self.end_p()
        elif tag == 'a':
            self.end_a()
        elif tag == 'ul':
            self.end_ul()
        elif tag == 'ol':
            self.end_ol()
        elif tag == 'table':
            self.end_table()
        elif tag == 'tr' and self.table:
            self.end_tr()
        elif tag == 'td' and self.table:
            self.end_td()
        elif tag == 'th' and self.table:
            self.end_th()
        elif tag == 'caption' and self.table:
            self.end_caption()
        elif tag == 'span':
            self.end_span()
        elif tag == 'sup' or tag == 'sub' or tag == 'b' or tag == 'i' or tag == 's' or tag == 'small' or tag == 'big' or tag == 'tt' or tag == 'u':
            if self.sup and self.buffer != None:
                self.buffer += "</"+str(tag)+">"
        

    def start_img(self, attrs):         
        src = [value for key, value in attrs if key == 'src'] 
        if src:
            self.images.extend(src)
            
    def end_img(self):
        for wiki_image in self.images:
            image  = Image()  
            outpath = self.grab_image(wiki_image, "/tmp")
            if outpath != None:
                image.set_image_file(outpath)
                self.pdf.add_image(image)
        self.images = []
        
    def start_h1(self, attrs):         
        self.h1 = True
        self.buffer = ""
        
    def end_h1(self):
        self.h1 = False
        h1 = Text(self.buffer, font="FreeSerif", font_size=16) 
        h1.color = StandardColors.Blue
        self.pdf.add_text(h1)
        self.buffer = None
        
    def start_h2(self, attrs):         
        self.h2 = True
        self.buffer = ""
        
    def end_h2(self):
        self.h2 = False
        if self.buffer and self.buffer.strip() > "":
            h2 = Text(self.buffer, font="FreeSerif", font_size=14) 
            h2.color = StandardColors.Blue
            self.pdf.add_text(h2)
        self.buffer = None
        
    def start_caption(self, attrs):         
        self.caption = True
        self.buffer = ""
        
    def end_caption(self):
        self.caption = False
        if self.buffer and self.buffer.strip() > "":
            caption = Text(self.buffer, font="FreeSerif", font_size=14) 
            caption.color = StandardColors.Blue
            self.pdf.add_text(caption)
        self.buffer = None

    def start_li(self, attrs):         
        self.li = True
        self.buffer = ""
        
    def end_li(self):
        self.li = False
#        print self.buffer
        if self.buffer and self.buffer.strip() > "":
            if self.ul:
                li = Text(markup = "• " + self.buffer,font="FreeSerif", font_size=10)
            elif self.ol:
                self.ref_counter+=1
                li = Text(markup = str(self.ref_counter) + ". "+ self.buffer.replace("↑",""), font = "FreeSerif", font_size=10)
            else:
                li = Text(markup = self.buffer,font="FreeSerif", font_size=10)     
            self.pdf.add_text(li)
        self.buffer = None
                
    def start_a(self, attrs):         
        self.a = True
        
    def end_a(self):
        self.a = False

    def start_table(self, attrs): 
        for tups in attrs:
	    if 'class' in tups:
		if tups[1] == 'wikitable':
                    self.table = True
                    self.wikitable = Table(border_width = 1)
                    self.wikitable.cell_padding = [2,2,2,2]
        
    def end_table(self):
        if self.table:
            self.table = False
            self.pdf.add_table(self.wikitable)

    def start_tr(self, attrs):         
        self.tr = True
        self.row = Row(height=25)
        self.current_counter = 0
        
    def end_tr(self):
        self.tr = False
        if self.current_counter == self.column_counter:
            self.wikitable.add_row(self.row)

    def start_td(self, attrs):         
        self.td = True
        self.buffer = ""
        
    def end_td(self):
        self.td = False
#        print self.buffer + " " + str(len(self.buffer))
        cell_content = Text(self.buffer,font_size=10)
        cell_content.color = Color(0.0,0.0,0.0,1.0)
        cell = Cell(cell_content, font_size=8,width=100)
        self.row.add_cell(cell)
        self.current_counter+=1
        self.buffer = None

    def start_th(self, attrs):         
        self.th = True
        self.buffer = ""
        
    def end_th(self):
        self.th = False
 #       print self.buffer + " " + str(len(self.buffer))
        cell_content = Text(self.buffer,font_size=10)
        cell_content.color = Color(0.0,0.0,0.0,1.0)
        cell = Cell(cell_content, font_size=8,width=100)
        self.row.add_cell(cell)
        self.column_counter+=1
        self.current_counter+=1
        self.buffer = None
    
#    def start_sup(self, attrs):         
#        self.sup = True
#        self.buffer += "<sup>"
#        
#    def end_sup(self):
#        print "test"
#        self.buffer += "</sup>"

        
    def start_ol(self, attrs):
        self.ol = True
        for tups in attrs:
	    if 'class' in tups:
		if tups[1] == 'references':
                    self.reference = True

    def end_ol(self):
        self.ol = False
        self.ref_counter = 0
        if self.reference:
            self.reference= False
            #self.sup = False
        
    def start_ul(self, attrs):
        self.ul = True    
    def end_ul(self):
        self.ul = False
            
    def start_span(self, attrs):         
        self.span = True
        if self.buffer == None:
            self.buffer = ""  
        
    def end_span(self):
        self.buffer += ""
        self.span = False
            
    def start_p(self, attrs):
        self.p = True
        self.buffer = ""
        
    def end_p(self) :
        self.p = False
        if self.sup:
            para = Paragraph(markup=self.buffer,text = self.buffer, font="FreeSerif", font_size=10,)
            self.sup = False
        else:
            #print self.buffer
            para = Paragraph(text=self.buffer, font="FreeSerif", font_size=10,)
           
        para.set_justify(True)
        if self.language:
            para.language = self.language
        else:
            para.language = None
            
        para.set_hyphenate(True)
        self.pdf.add_paragraph(para) 
#        f= open("computer_para.txt","aw")
#        f.write(self.buffer)
#        f.write("\n")
#        f.close()  
        self.buffer = None
    def set_header(self, text):
        self.header = text

    def grab_image(self, imageurl, outputfolder):
        """
        Get the image from wiki
        """
        excluded_images = """
            //bits.wikimedia.org/skins-1.18/common/images/magnify-clip.png,
            //bits.wikimedia.org/w/extensions-1.18/OggHandler/play.png
        """
        if imageurl in excluded_images:
            return None;
        output_filename = None
        try:
            link= "https:"+imageurl.strip()
            parts = link.split("/")
            filename = parts[len(parts)-1]
            output_filename = os.path.join(outputfolder , filename)
            #output_filename=urllib.unquote(output_filename)
            print("GET IMAGE " + link + " ==> " + output_filename)
            if os.path.isfile(output_filename):
                print("File " + output_filename + " already exists")
                return output_filename
            opener = urllib2.build_opener()
            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            infile = opener.open(link)
            page = infile.read()
            f= open(output_filename,"w")
            f.write(page)
            f.close()
        except KeyboardInterrupt:
            sys.exit()
        except urllib2.HTTPError:
            print("Error: Cound not download the image")
            pass
        return  output_filename
    def parse(self):
        opener = urllib2.build_opener()
        opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        infile = opener.open(self.url)
        page = infile.read()
        page = cleanup(page)
#        f= open("computer.txt","w")
#        f.write(page)
#        f.close()
#        f = open("computer.txt","r")
#        page=f.read()
#        f.close()
        "Parse the given string 's'."
        self.feed(page)
        self.close()
        self.pdf.flush()
        
def cleanup(page):
    """
    remove unwanted sections of the page.
    Uses pyquery.
    """
    document = pq(page)
    #If you want to remove any other section, just add the class or id of the section below with comma seperated
    unwanted_sections_list = """
    div#jump-to-nav, div.top, div#column-one, div#siteNotice, div#purl, div#head,div#footer, div#head-base, div#page-base, div#stub, div#noprint,
    div#disambig,div.NavFrame,#colophon,.editsection,.toctoggle,.tochidden,.catlinks,.navbox,.sisterproject,.ambox,
    .toccolours,.topicondiv#f-poweredbyico,div#f-copyrightico,div#featured-star,li#f-viewcount,
    li#f-about,li#f-disclaimer,li#f-privacy,.portal, #footer, #mw-head, #toc, #protected-icon, #featured-star, #ogg_player_1
    """
    unwanted_divs = unwanted_sections_list.split(",")
    for section in unwanted_divs:
        document.remove(section.strip())
    return document.wrap('<div></div>').html().encode("utf-8")

def detect_language(url):
    """
    
    Arguments:
    - `url`: Input url inform en.wikipedia.org
    return language code for the url
    """

    # Split on .
    # ml.wikipedia.org/ becomes
    # [ml,wikipedia,org/]

    if url.startswith("http://"):
        url = url.split("http://")[1]
        
    url_pieces = url.split(".")
    return lang_codes.get(url_pieces[0], None)
    

    
    
if __name__ == "__main__":
    if len(sys.argv) > 1:
        parser = Wikiparser(sys.argv[1]) #"http://ml.wikipedia.org/wiki/Computer"
        parser.parse()    
    else:
        print("Usage: wiki2pdf url")    
        print("Example: wiki2pdf http://en.wikipedia.org/wiki/Computer")    

########NEW FILE########
__FILENAME__ = styles
# -*- coding: utf-8 -*-
# pypdflib/styles.py

# pypdflib is a pango/cairo framework for generating reports.
# Copyright © 2010  Santhosh Thottingal <santhosh.thottingal@gmail.com>

# This file is part of pypdflib.
#
# pypdflib is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.  
#
# pypdflib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pypdflib.  If not, see <http://www.gnu.org/licenses/>.

import pango
from types import StringType
from copy import deepcopy

ALIGN_LEFT = 0
ALIGN_CENTER = 1
ALIGN_RIGHT = 2
ALIGN_TOP = 0
ALIGN_MIDDLE = 1
ALIGN_BOTTOM = 2

ATTRS = ('font', 'font_size', 'border', 'margin', 'padding', 'align', 'valign', 'text_align')

class Paper(object) :
    def __init__( self, name, width, height ) :
        self.name =  name 
        self.width = width
        self.height = height


class AttributedList( list ) :
    def __init__( self, accepted_type=None ) :
        super( AttributedList, self ).__init__()
        self.AcceptedType = accepted_type
        self._append = super( AttributedList, self ).append

    def append( self, *values ) :
            for value in values :
                if self.AcceptedType : assert isinstance( value, self.AcceptedType )
            self._append( value )

            name = getattr( value, 'name', None )

            if name :
                name = self._make_attributeName( value.name )
                setattr( self, name, value )
    
    def _make_attributeName(self, value ) :
        assert value and type( value ) is StringType
        value = value.replace( ' ', '' )
        return value

    def __deepcopy__( self, memo ) :
            result = self.__class__()
            result.append( *self[:] )
            return result

class Color(object):
	def __init__ (self, name, red, green, blue, alpha=1.0):
            	self.red = red
		self.green = green
		self.blue = blue
		self.alpha = alpha
                self.name = name

class Papers( AttributedList ) :
    def __init__( self ) :
        super( Papers, self ).__init__( Paper )

class Colors( AttributedList ) :
    def __init__( self ) :
        super( Colors, self ).__init__( Color )
"""
Standard Colors. 
"""
StandardColors = Colors()
StandardColors.append( Color( 'Black',         0,    0,   0 ) )
StandardColors.append( Color( 'Blue',          0,    0, 255 ) )
StandardColors.append( Color( 'Turquoise',     0,  255, 255 ) )
StandardColors.append( Color( 'Green',         0,  255,   0 ) )
StandardColors.append( Color( 'Pink',        255,    0, 255 ) )
StandardColors.append( Color( 'Red',         255,    0,   0 ) )
StandardColors.append( Color( 'Yellow',      255,  255,   0 ) )
StandardColors.append( Color( 'White',       255,  255, 255 ) )
StandardColors.append( Color( 'BlueDark',     0,    0, 128 ) )
StandardColors.append( Color( 'Teal',          0,  128, 128 ) )
StandardColors.append( Color( 'GreenDark',    0,  128,   0 ) )
StandardColors.append( Color( 'Violet',      128,    0, 128 ) )
StandardColors.append( Color( 'RedDark',    128,    0,   0 ) )
StandardColors.append( Color( 'YellowDark', 128,  128,   0 ) )
StandardColors.append( Color( 'GreyDark',   128,  128, 128 ) )
StandardColors.append( Color( 'Grey',        192,  192, 192 ) )

"""
Standard Paper sizes. Dimentions in 'points'
"""

StandardPaper = Papers()
StandardPaper.append( Paper( 'Letter',		 612,792))
StandardPaper.append( Paper( 'LetterSmall',	 612,792))
StandardPaper.append( Paper( 'Tabloid'	,	 792,1224))
StandardPaper.append( Paper( 'Ledger'	,	1224,792))
StandardPaper.append( Paper( 'Legal'	,	 612,1008))
StandardPaper.append( Paper( 'Statement',	 396,612))
StandardPaper.append( Paper( 'Executive',	 540,720))
StandardPaper.append( Paper( 'A0'        ,       2384,3371))
StandardPaper.append( Paper( 'A1'        ,     1685,2384))
StandardPaper.append( Paper( 'A2'	,	1190,1684))
StandardPaper.append( Paper( 'A3'	,	 842,1190))
StandardPaper.append( Paper( 'A4'	,	 595,842))
StandardPaper.append( Paper( 'A4Small'	,	 595,842))
StandardPaper.append( Paper( 'A5'	,	 420,595))
StandardPaper.append( Paper( 'B4'	,	 729,1032))
StandardPaper.append( Paper( 'B5'	,	 516,729))
StandardPaper.append( Paper( 'Folio'	,	 612,936))
StandardPaper.append( Paper( 'Quarto'	,	 610,780))
StandardPaper.append( Paper( '10x14'	,	 720,1008))


class BorderSide (object):
    def __init__ (self, width=0, color=None, dash=None, round=0):
        self.width = width
        if not color:
            self.color = (0, 0, 0, 1)
        else:
            self.color = color
        if not dash:
            self.dash = []
        else:
            self.dash = dash
        self.round = round

class Border (object):
    def __init__ (self, width=0, color=None, dash=None, round=0):
        self.left = BorderSide (width, color, dash, round)
        self.top = BorderSide (width, color, dash, round)
        self.right = BorderSide (width, color, dash, round)
        self.bottom = BorderSide (width, color, dash, round)

class Dimension (object):
    def __init__ (self, width=0, height=0):
        self.width = width
        self.height = height

    def valid (self):
        return self.width > 0 and self.height > 0

    def maximize (self, d):
        self.width = max (self.width, d.width)
        self.height = max (self.height, d.height)

    def max_width (self, width):
        return max (self.width, width)

    def max_height (self, height):
        return max (self.height, height)

    def min_width (self, width):
        if self.valid ():
            return min (self.width, width)
        else:
            return width

    def min_height (self, height):
        if self.valid ():
            return min (self.height, height)
        else:
            return height

    def __add__ (self, d):
        return Dimension (self.width + d.width, self.height + d.height)

    def __str__ (self):
        return "Dimension (%d, %d)" % (self.width, self.height)

class Rectangle (Dimension):
    def __init__ (self, x=0, y=0, width=0, height=0, page=1):
        Dimension.__init__ (self, width, height)
        self.x = x
        self.y = y
        self.page = page
        self.no_paging = False

    def __add__ (self, d):
        return Rectangle (self.x, self.y, self.width + d.width, self.height + d.height)

    def __str__ (self):
        return "Rectangle (%d, %d, %d, %d)" % (self.x, self.y, self.width, self.height)

class Spacing (object):
    def __init__ (self, left=0, top=0, right=0, bottom=0):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

    def __str__ (self):
        return "Spacing (%d, %d, %d, %d)" % (self.left, self.top, self.right, self.bottom)

class Style (object):
    def __init__ (self, name=""):
        self.name = name

    def inherit (self, style):
        for attr in ATTRS:
            if not hasattr (self, attr) or getattr (self, attr) is None:
                setattr (self, attr, getattr (style, attr))

    def copy (self):
        s = Style (self.name)
        s.inherit (self)
        return s

    def __str__ (self):
        return "Style (%s)" % self.name

class Stylesheet (dict):
    def __init__ (self):
        s = self['widget'] = Style ('widget')
        s.font = 'Sans 12'
        s.font_size = 12
        s.border = Border ()
        s.margin = Spacing ()
        s.padding = Spacing ()
        s.align = ALIGN_LEFT
        s.valign = ALIGN_TOP
        s.text_align = pango.ALIGN_LEFT
        s = self['paragraph'] = Style ('paragraph')
        s.inherit (self['widget'])

default_stylesheet = Stylesheet ()

__all__ = ['default_stylesheet', 'Style', 'Dimension', 'Spacing', 'Rectangle', 'Border', 'BorderSide', 'Color', 'Paper', 'StandardColors', 'StandardPaper']

########NEW FILE########
__FILENAME__ = hyphenator
#!/usr/bin/python
#-*- coding:utf-8 -*-
# pypdflib/utils/hyphenation/hyphenator.py

# pypdflib is a pango/cairo framework for generating reports.
# Copyright © 2010  Santhosh Thottingal <santhosh.thottingal@gmail.com>

# This file is part of pypdflib.
#
# pypdflib is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.  
#
# pypdflib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pypdflib.  If not, see <http://www.gnu.org/licenses/>.

import sys
import re
import os

#__all__ = ("Hyphenator")

# cache of per-file Hyph_dict objects
hdcache = {}

# precompile some stuff
parse_hex = re.compile(r'\^{2}([0-9a-f]{2})').sub
parse = re.compile(r'(\d?)(\D?)').findall

def hexrepl(matchObj):
    return unichr(int(matchObj.group(1), 16))


class parse_alt(object):
    """
    Parse nonstandard hyphen pattern alternative.
    The instance returns a special int with data about the current position
    in the pattern when called with an odd value.
    """
    def __init__(self, pat, alt):
        alt = alt.split(',')
        self.change = alt[0]
        if len(alt) > 2:
            self.index = int(alt[1])
            self.cut = int(alt[2]) + 1
        else:
            self.index = 1
            self.cut = len(re.sub(r'[\d\.]', '', pat)) + 1
        if pat.startswith('.'):
            self.index += 1

    def __call__(self, val):
        self.index -= 1
        val = int(val)
        if val & 1:
            return dint(val, (self.change, self.index, self.cut))
        else:
            return val


class dint(int):
    """
    Just an int some other data can be stuck to in a data attribute.
    Call with ref=other to use the data from the other dint.
    """
    def __new__(cls, value, data=None, ref=None):
        obj = int.__new__(cls, value)
        if ref and type(ref) == dint:
            obj.data = ref.data
        else:
            obj.data = data
        return obj


class Hyph_dict(object):
    """
    Reads a hyph_*.dic file and stores the hyphenation patterns.
    Parameters:
    -filename : filename of hyph_*.dic to read
    """
    def __init__(self, filename):
        self.patterns = {}
        f = open(filename)
        charset = f.readline().strip()
        if charset.startswith('charset '):
            charset = charset[8:].strip()

        for pat in f:
            pat = pat.decode(charset).strip()
            if not pat or pat[0] == '%': continue
            # replace ^^hh with the real character
            pat = parse_hex(hexrepl, pat)
            # read nonstandard hyphen alternatives
            if '/' in pat:
                pat, alt = pat.split('/', 1)
                factory = parse_alt(pat, alt)
            else:
                factory = int
            tag, value = zip(*[(s, factory(i or "0")) for i, s in parse(pat)])
            # if only zeros, skip this pattern
            if max(value) == 0: continue
            # chop zeros from beginning and end, and store start offset.
            start, end = 0, len(value)
            while not value[start]: start += 1
            while not value[end-1]: end -= 1
            self.patterns[''.join(tag)] = start, value[start:end]
        f.close()
        self.cache = {}
        self.maxlen = max(map(len, self.patterns.keys()))

    def positions(self, word):
        """
        Returns a list of positions where the word can be hyphenated.
        E.g. for the dutch word 'lettergrepen' this method returns
        the list [3, 6, 9].

        Each position is a 'data int' (dint) with a data attribute.
        If the data attribute is not None, it contains a tuple with
        information about nonstandard hyphenation at that point:
        (change, index, cut)

        change: is a string like 'ff=f', that describes how hyphenation
            should take place.
        index: where to substitute the change, counting from the current
            point
        cut: how many characters to remove while substituting the nonstandard
            hyphenation
        """
        word = word.lower()
        points = self.cache.get(word)
        if points is None:
            prepWord = '.%s.' % word
            res = [0] * (len(prepWord) + 1)
            for i in range(len(prepWord) - 1):
                for j in range(i + 1, min(i + self.maxlen, len(prepWord)) + 1):
                    p = self.patterns.get(prepWord[i:j])
                    if p:
                        offset, value = p
                        s = slice(i + offset, i + offset + len(value))
                        res[s] = map(max, value, res[s])

            points = [dint(i - 1, ref=r) for i, r in enumerate(res) if r % 2]
            self.cache[word] = points
        return points


class Hyphenator:
    """
    Reads a hyph_*.dic file and stores the hyphenation patterns.
    Provides methods to hyphenate strings in various ways.
    Parameters:
    -filename : filename of hyph_*.dic to read
    -left: make the first syllabe not shorter than this
    -right: make the last syllabe not shorter than this
    -cache: if true (default), use a cached copy of the dic file, if possible

    left and right may also later be changed:
    h = Hyphenator(file)
    h.left = 1
    """
    
    #self.left=2
    #def __init__(self, left=2, right=2, cache=True):
    left  = 2
    right = 2
    def __init__(self):
        self.template=os.path.join(os.path.dirname(__file__), 'hyphenator.html')
        self.hd=None
#        self.guess_language=guess_language.getInstance()
    def loadHyphDict(self,lang, cache=True):
        filename = os.path.join(os.path.dirname(__file__), "rules/hyph_"+lang+".dic")
        if not cache or filename not in hdcache:
            hdcache[filename] = Hyph_dict(filename)
        self.hd = hdcache[filename]
    def positions(self, word):
        """
        Returns a list of positions where the word can be hyphenated.
        See also Hyph_dict.positions. The points that are too far to
        the left or right are removed.
        """
        right = len(word) - self.right
        return [i for i in self.hd.positions(word) if self.left <= i <= right]

    def iterate(self, word):
        """
        Iterate over all hyphenation possibilities, the longest first.
        """
        if isinstance(word, str):
            word = word.decode('latin1')
        for p in reversed(self.positions(word)):
            if p.data:
                # get the nonstandard hyphenation data
                change, index, cut = p.data
                if word.isupper():
                    change = change.upper()
                c1, c2 = change.split('=')
                yield word[:p+index] + c1, c2 + word[p+index+cut:]
            else:
                yield word[:p], word[p:]

    def wrap(self, word, width, hyphen='-'):
        """
        Return the longest possible first part and the last part of the
        hyphenated word. The first part has the hyphen already attached.
        Returns None, if there is no hyphenation point before width, or
        if the word could not be hyphenated.
        """
        width -= len(hyphen)
        for w1, w2 in self.iterate(word):
            if len(w1) <= width:
                return w1 + hyphen, w2

    def inserted(self, word, hyphen='-'):
        """
        Returns the word as a string with all the possible hyphens inserted.
        E.g. for the dutch word 'lettergrepen' this method returns
        the string 'let-ter-gre-pen'. The hyphen string to use can be
        given as the second parameter, that defaults to '-'.
        """
        if isinstance(word, str):
            word = word.decode('utf-8')
        l = list(word)
        for p in reversed(self.positions(word)):
            if p.data:
                # get the nonstandard hyphenation data
                change, index, cut = p.data
                if word.isupper():
                    change = change.upper()
                l[p + index : p + index + cut] = change.replace('=', hyphen)
            else:
                l.insert(p, hyphen)
        return ''.join(l)
                      
    def hyphenate(self,text,language, hyphen=u'\u00AD'):
        response=""
        words = text.split(" ")
        self.loadHyphDict(language)
        for word in words:
             hyph_word = self.inserted(word, hyphen)
             response = response + hyph_word + " "
        return response   


########NEW FILE########
__FILENAME__ = normalizer
#!/usr/bin/python
#-*- coding:utf-8 -*-
# pypdflib/utis/normalizer.py

# pypdflib is a pango/cairo framework for generating reports.
# Copyright © 2010  Santhosh Thottingal <santhosh.thottingal@gmail.com>

# This file is part of pypdflib.
#
# pypdflib is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.  
#
# pypdflib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pypdflib.  If not, see <http://www.gnu.org/licenses/>.

import re
import unicodedata
def normalize(text):
    text = unicodedata.normalize('NFC', unicode(text))
    space_re = re.compile('\s+', re.UNICODE)
    text = space_re.sub(' ', text)
    text = normalize_ml (text)
    return text
    
def normalize_ml (text):
    
    zwnj_re =  re.compile(u'‍+', re.UNICODE) # remove muliple instances of zwnj
    zwj_re =  re.compile(u'‍+', re.UNICODE) # remove muliple instances of  zwj 
    text = zwj_re.sub(u'‍', text)
    text = zwnj_re.sub(u'‍', text)
    text = text.replace(u"ൺ" , u"ണ്‍")
    text = text.replace(u"ൻ", u"ന്‍")
    text = text.replace(u"ർ", u"ര്‍")
    text = text.replace(u"ൽ", u"ല്‍")
    text = text.replace(u"ൾ", u"ള്‍")
    text = text.replace(u"ൿ", u"ക്‍")
    text = text.replace(u"ന്‍റ", u"ന്റ")
    return text     


########NEW FILE########
__FILENAME__ = widgets
#!/usr/bin/python
#-*- coding:utf-8 -*-
# pypdflib/widgets.py

# pypdflib is a pango/cairo framework for generating reports.
# Copyright © 2010  Santhosh Thottingal <santhosh.thottingal@gmail.com>

# This file is part of pypdflib.
#
# pypdflib is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.  
#
# pypdflib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pypdflib.  If not, see <http://www.gnu.org/licenses/>.

import pango
import StringIO
from PIL import Image as pil_image
from utils import Hyphenator
from styles import *
class Widget(object):
    
    def __init__(self,style = None):
        self.style = style
        self.xoffset = 0.0
        self.yoffset = 0.0
        self.margin_top = 0.0
        self.margin_bottom = 0.0
        self.margin_left = 0.0
        self.margin_right = 0.0
        self.hyphenate = False
        self.language = None
        self.justify = True
        self.is_markup = False
        self.color = StandardColors.Black
        self.coordinates = [0,0,0,0]
        
    def set_justify(self, justify):
        self.justify = justify
        
    def set_hyphenate(self, hyphenate):
        self.hyphenate = hyphenate
        
    def set_language(self, language):
        self.language = language
        
    def set_margin(self, left,top, right,bottom) :
        self.margin_top = top
        self.margin_bottom = bottom
        self.margin_left = left   
        self.margin_right = right
        
    def set_style(self, style):
        self.style = style

    def set_xoffset(self,xoffset):
        self.xoffset = xoffset
        
    def set_yoffset(self, yoffset):
        self.yoffset = yoffset    
        
    def __getattribute__(self,name):
        if name == 'text':
            text = object.__getattribute__(self, 'text')
            if(self.justify and self.language and self.hyphenate):
                text = Hyphenator().hyphenate(text,self.language)
            return text
        else:
            return object.__getattribute__(self, name)

       
        
class Paragraph(Widget):
    
    def __init__(self,  text = None, markup = None, font = None, text_align = None, font_size = None):
        super(Paragraph,self).__init__()
        if font:
            self.font = font
        else:
            self.font = "Sans"    
        if font_size:
            self.font_size = font_size
        else:
            self.font_size = 10   
        if text_align:
            self.text_align = text_align
        else:
            self.text_align = pango.ALIGN_LEFT
        if markup:
            self.is_markup = True
            self.text = markup
        else:
            self.text = text
        self.markup = markup
   
        
    def set_text(self,text):
        self.text = text


    def set_markup(self, markup):
        self.markup = markup
        self.text = markup
        self.is_markup = True


class Header(Widget):
    
    def __init__(self,  text = None, markup = None, font = None, text_align = None, font_size = None):
        super(Header,self).__init__()
        if font:
            self.font = font
        else:
            self.font = "Sans"    
        if font_size:
            self.font_size = font_size
        else:
            self.font_size = 10    
        if text_align:
            self.text_align = text_align
        else:
            self.text_align = pango.ALIGN_LEFT    
        if markup:
            self.is_markup = True
        self.text = text
        self.markup = markup
        self.underline =  True
        self.underline_thickness = 1.0
        
    def set_text(self,text):
        self.text = text
        
    def set_markup(self, markup):
        self.markup = markup
        self.is_markup = True
    
    def set_underline(self, thickness=None):
        self.underline =  True
        if thickness:
            self.underline_thickness = thickness
            
class Text(Widget):
    
    def __init__(self,  text = None, markup = None, font = None, text_align = None, font_size = None, height = 0,width = 0):
        super(Text,self).__init__()
        if font:
            self.font = font
        else:
            self.font = "Sans"
        if font_size:
            self.font_size = font_size
        else:
            self.font_size = 10
        if text_align:
            self.text_align = text_align
        else:
            self.text_align = pango.ALIGN_LEFT
        if markup:
            self.is_markup = True
            self.text = markup
        else:
            self.text = text
        self.markup = markup
        self.underline =  False
        self.underline_thickness = 0.0
        
    def set_text(self,text):
        self.text = text
        
    def set_markup(self, markup):
        self.markup = markup
        self.is_markup = True
    
    def set_underline(self, thickness = None):
        self.underline =  True
        if thickness:
            self.underline_thickness = thickness


class Footer(Widget):
    
    def __init__(self,  text = None, markup = None, font = None, text_align = None, font_size = None):
        super(Footer,self).__init__()
        if font:
            self.font = font
        else:
            self.font = "Sans"
        if font_size:
            self.font_size = font_size
        else:
            self.font_size = 10
        if text_align:
            self.text_align = text_align
        else:
            self.text_align = pango.ALIGN_LEFT
        if markup:
            self.is_markup = True

        self.text = text
        self.markup = markup
        self.underline =  True
        self.underline_thickness = 1.0
        
    def set_text(self,text):
        self.text = text
        
        
    def set_markup(self, markup):
        self.markup = markup
        self.is_markup = True
    
    def set_underline(self, thickness=None):
        self.underline =  True
        if thickness:
            self.underline_thickness = thickness

    
class Line(Widget) :
    
    def __init__(self, x1, y1, x2, y2):
        self.x1=x1
        if x2:
            self.x2 = x2
        else:
            self.x2 = x1
        self.y1 = y1
        self.y2 = y2
        self.thickness = None
        
    def set_thickness(self,thickness):
        self.thickness = thickness

class Cell(Widget):
    def __init__(self,  content = None, border_width = 0, height = 0, width = 0, cell_spacing = [0,0,0,0], **kw):
       #Text.__init__ (self, **kw)
       super(Cell,self).__init__()
       self.height = height
       self.width = width
       self.cell_spacing = cell_spacing
       self.content = content 
    
class Row(Widget):
    def __init__(self, cells = None,  border_width = 0, height = 0):
        self.border_width = border_width
        self.cells = cells
        self.height = height
        
    def add_cell(self, cell) :
        if cell == None: return
        if self.cells == None:
            self.cells = []
        self.cells.append(cell) 

class Table(Widget) :
    def __init__(self, rows=None, border_width=0):
        super(Table,self).__init__()
        self.rows = rows
        self.border_width = border_width
        self.header_row = None
        self.subtitle = None
        self.column_count = 0
        self.row_count = 0
        self.padding = [0, 0, 0, 0]
        
    def add_row(self, row):
        if row == None:
            raise Error('row is null') 
        if self.rows == None: self.rows = []
        if self.column_count != 0:
            if len(row.cells) != self.column_count:
                raise Error('Number of cells differs in this row.') 
        self.column_count = len(row.cells)
        self.rows.append(row)
        self.row_count = len(self.rows)
        
    def set_header_row(self, row):
        self.header_row = row
   
    def set_subtitle(self, text):
        self.subtitle = text
    
      
class Image(Widget):
    
    def __init__(self, image_file = None, width = None, height = None, scale_x = None, scale_y = None,padding_bottom = 10):
        super(Image,self).__init__()
        self.image_file = image_file
        self.width = width
        self.height = height
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.padding_bottom = padding_bottom
        self.image_data = None
        self.subtitle = None
        
    def set_width(self, width):
        self.width = width
    
    def set_image_file(self, imagefile):
        self.image_file = imagefile
        image = pil_image.open(imagefile)
        self.image_data = StringIO.StringIO()
        image.save(self.image_data, format="PNG")
        self.image_data.seek(0) # rewind
        
    def set_height(self, height):
        self.height = height
        
    def set_size(self,width,height):
        self.width = width
        self.height = height
        
    def set_scale(self, scale_x, scale_y):
        self.scale_x = scale_x
        self.scale_y = scale_y


########NEW FILE########
__FILENAME__ = writer
#!/usr/bin/python
#-*- coding: utf-8 -*-
# pypdflib/writer.py

# pypdflib is a pango/cairo framework for generating reports.
# Copyright © 2010  Santhosh Thottingal <santhosh.thottingal@gmail.com>

# This file is part of pypdflib.
#
# pypdflib is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.  
#
# pypdflib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pypdflib.  If not, see <http://www.gnu.org/licenses/>.

import cairo
import pango
import pangocairo
from pypdflib.widgets import *
class PDFWriter():
    def __init__(self,filename, paper):
        self.width = paper.width
        self.height = paper.height
        surface = cairo.PDFSurface(filename, self.width, self.height, pointsize=1)
        self.context = cairo.Context(surface)
        self.context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
        self.pc = pangocairo.CairoContext(self.context)
        self.left_margin = self.width*0.1
        self.right_margin = self.width*0.1
        self.top_margin = self.width*0.1
        self.bottom_margin = self.width*0.1
        self.position_x = self.left_margin
        self.position_y = 0
        self.line_width = 10
        self.font_size = 10
        self.para_break_width = 10
        self.page_num = 0
        self.ybottom = self.height - self.bottom_margin*2
        self.header = None
        self.footer = None
        
    def set_header(self, header):
        """
        Sets the header of the page
        """
        self.header = header 
        self.write_header(self.header)
        
    def set_footer(self, footer):
        """
        Sets the footer of the page
        """
        self.footer = footer
        
    def add_text(self, text):
        """
        Add text widget
        """

        text_font_description = pango.FontDescription()
        text_font_description.set_family(text.font)
        text_font_description.set_size((int)(text.font_size* pango.SCALE))
        text_layout = pangocairo.CairoContext(self.context).create_layout()
        text_layout.set_font_description(text_font_description)
        self.position_x = self.left_margin
        if text.coordinates== None or text.coordinates == [0,0,0,0]:
            text_layout.set_width((int)((self.width - self.left_margin-self.right_margin) * pango.SCALE))
            if self.position_y == 0:
                self.position_y += self.top_margin 
            self.position_y += self.line_width
        else:    
            text_layout.set_width(int(text.coordinates[2]-text.coordinates[0])*pango.SCALE)
            self.position_x = text.coordinates[0]
            self.position_y = text.coordinates[1]
            
        text_layout.set_alignment(text.text_align)
        if text.is_markup:
            text_layout.set_markup(text.text)
        else:
            text_layout.set_text(str(text.text))    
        ink_rect, logical_rect = text_layout.get_extents()
        self.assert_page_break()
        self.context.move_to(self.position_x, self.position_y)
        self.context.set_source_rgba (text.color.red,text.color.green, text.color.blue,text.color.alpha)
        self.pc.show_layout(text_layout)
        if text.coordinates== None or  text.coordinates == [0,0,0,0]:
            self.position_y += logical_rect[3]/pango.SCALE+self.para_break_width
        
    def write_footer(self,footer):
        if footer == None: return 
        footer_font_description = pango.FontDescription()
        footer_font_description.set_family(footer.font)
        footer_font_description.set_size((int)(footer.font_size* pango.SCALE))
        footer_layout = pangocairo.CairoContext(self.context).create_layout()
        footer_layout.set_font_description(footer_font_description)
        footer_layout.set_width((int)((self.width - self.left_margin-self.right_margin) * pango.SCALE))
        footer_layout.set_alignment(footer.text_align)
        if footer.markup:
            footer_layout.set_markup(str(footer.markup))
        else:
            footer_layout.set_text(str(footer.text))
        ink_rect, logical_rect = footer_layout.get_extents()
        y_position= self.height - self.bottom_margin- logical_rect[3]/pango.SCALE
        self.context.move_to(self.left_margin, y_position)
        self.context.set_source_rgba (footer.color.red,footer.color.green, footer.color.blue,footer.color.alpha)
        self.pc.show_layout(footer_layout)
        self.draw_line(y_position)
        self.ybottom = y_position-self.line_width
        
    def write_header(self, header):
        if header == None: return 
        header_font_description = pango.FontDescription()
        header_font_description.set_family(header.font)
        header_font_description.set_size((int)(header.font_size * pango.SCALE))
        header_layout = pangocairo.CairoContext(self.context).create_layout()
        header_layout.set_font_description(header_font_description)
        header_layout.set_width((int)((self.width - self.left_margin-self.right_margin) * pango.SCALE))
        header_layout.set_alignment(header.text_align)
        if header.markup:
            header_layout.set_markup(str(header.markup))
        else:
            header_layout.set_text(str(header.text))
        ink_rect, logical_rect = header_layout.get_extents()
        self.context.move_to(self.left_margin, self.top_margin)
        self.context.set_source_rgba (header.color.red,header.color.green, header.color.blue,header.color.alpha)
        self.pc.show_layout(header_layout)
        y_position = self.top_margin+(logical_rect[3] / pango.SCALE)
        self.draw_line(y_position)
        self.position_y = y_position + self.line_width*2
        
    def draw_line(self, y_position=0):
        if y_position == 0 :
            y_position = self.position_y
        self.context.move_to(self.left_margin, y_position)
        self.context.set_source_rgba (0.0, 0.0, 0.0, 1.0)
        self.context.line_to(self.width-self.right_margin,  y_position)
        self.context.stroke()
        self.position_y+= self.line_width
        
    def line_break(self):
        self.assert_page_break();
        self.position_y+= self.line_width
        self.context.move_to(self.left_margin, self.position_y)

    def add_paragraph(self, paragraph):
        self.position_y+=self.para_break_width
        self.assert_page_break();
        self.position = (self.left_margin, self.position_y)
        self.context.set_source_rgba (0.0, 0.0, 0.0, 1.0)
        paragraph_layout = pangocairo.CairoContext(self.context).create_layout()
        paragraph_font_description = pango.FontDescription()
        paragraph_font_description.set_family(paragraph.font)
        paragraph_font_description.set_size((int)(paragraph.font_size * pango.SCALE))
        paragraph_layout.set_font_description(paragraph_font_description)
        paragraph_layout.set_width((int)((self.width - self.left_margin-self.right_margin) * pango.SCALE))
        if(paragraph.justify):
            paragraph_layout.set_justify(True)
        if paragraph.is_markup:
            #print paragraph.text
            if paragraph.language == 'en_US':
                paragraph_layout.set_markup(paragraph.markup+"\n")
            else:
                paragraph_layout.set_markup(paragraph.text+"\n")
        else:
            paragraph_layout.set_text(paragraph.text+"\n")#fix it , adding new line to keep the looping correct?!
        self.context.move_to(*self.position)
        pango_layout_iter = paragraph_layout.get_iter();
        itr_has_next_line=True
        while not pango_layout_iter.at_last_line():
            first_line = True
            self.context.move_to(self.left_margin, self.position_y)
            while not pango_layout_iter.at_last_line() :
                ink_rect, logical_rect = pango_layout_iter.get_line_extents()
                line = pango_layout_iter.get_line_readonly()
                has_next_line=pango_layout_iter.next_line()
                # Decrease paragraph spacing
                if  ink_rect[2] == 0 : #It is para break
                    dy = self.font_size / 2
                    self.position_y += dy
                    if not first_line:
                        self.context.rel_move_to(0, dy)
                else:
                    xstart = 1.0 * logical_rect[0] / pango.SCALE
                    self.context.rel_move_to(xstart, 0)
                    self.context.set_source_rgba (paragraph.color.red,paragraph.color.green, paragraph.color.blue,paragraph.color.alpha)
                    self.pc.show_layout_line( line)
                    line_height = (int)(logical_rect[3] / pango.SCALE)
                    self.context.rel_move_to(-xstart, line_height )
                    self.position_y += line_height 
 
                if self.position_y > self.ybottom:
                    self.page_num= self.page_num+1
                    self.write_header(self.header)
                    if self.footer:
                         self.write_footer(self.footer)
                    else:
                         self.footer.set_text(str(self.page_num))
                         self.write_footer(self.footer)
                    self.context.show_page()
                    break
                    
            first_line = False

    def flush(self) :   
        """
        Flush the contents before finishing and closing the PDF.
        This must be called at the end of the program. Otherwise the footer at the
        last page will be missing.
        """
        self.page_num= self.page_num+1
        self.write_header(self.header)
        if self.footer:
            self.write_footer(self.footer)
        else:
            self.footer.set_text(str(self.page_num))
            self.write_footer(self.footer)
        self.context.show_page()
    
    def add_table(self, table):
        if table.row_count == 0: 
            print("Table has no rows")
            return 
        self.context.identity_matrix()
        self.context.set_source_rgba (0.0, 0.0, 0.0, 1.0)
        x1 = self.position_x
        y1 = self.position_y 
        width=height=0
        for row in range(table.row_count):
            for column in range(table.column_count):
                height = table.rows[row].height
                cell = table.rows[row].cells[column]
                width  = cell.width    
                self.context.set_source_rgba (cell.color.red, cell.color.green, cell.color.blue, cell.color.alpha)
                self.context.set_line_width(table.border_width)
                self.context.rectangle(x1,y1,width,height)
                self.context.stroke()
                self._draw_cell(cell, x1, y1, x1+width, y1+height)
                x1 += width
            y1 += height    
            x1= self.left_margin
            self.position_y += height
                
    def _draw_cell(self, cell, x1, y1, x2, y2):
        widget = cell.content
        if cell.content.__class__ == Text:
            widget.coordinates = [x1, y1, x2, y2]
            self.add_text(widget)
        #TODO: Add other widgets
                
    def add_image(self, image):
        self.context.save ()
        self.context.move_to(self.left_margin, self.position_y)
        image_surface = cairo.ImageSurface.create_from_png (image.image_data)
        w = image_surface.get_width ()
        h = image_surface.get_height ()
        if (self.position_y + h*0.5) > self.ybottom:
            self.page_break()
        data =image_surface.get_data()
        stride = cairo.ImageSurface.format_stride_for_width (cairo.FORMAT_ARGB32, w)
        image_surface = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, w, h,stride)
        self.assert_page_break()
        self.context.scale(0.5, 0.5)
        self.context.set_source_surface (image_surface,self.left_margin/0.5, self.position_y/0.5)
        self.context.paint()
        self.context.restore ()        
        self.position_y+= h*0.5+ image.padding_bottom 
        
        
    def new_page(self):
        self.context.identity_matrix()
        self.context.set_source_rgba (1.0, 1.0, 1.0, 1.0)
        self.context.rectangle(0, self.position_y, self.width, self.height)
        self.context.fill()
        self.context.set_source_rgb (0.0, 0.0, 0.0)
        self.context.move_to(self.left_margin, self.top_margin)
        self.position_y=0    
        self.context.show_page()
        
    def blank_space(self, height):
        """
        Inserts vertical blank space 
        Color will be white.
        
        Arguments
        -height - The vertical measurement for the blank space.
        """
        self.context.identity_matrix()
        self.context.set_source_rgba (1.0, 1.0, 1.0, 1.0)
        self.context.rectangle(0, self.position_y, self.width, height)
        self.context.fill()
        self.context.set_source_rgb (0.0, 0.0, 0.0)
        self.context.move_to(self.left_margin, self.top_margin)
        self.position_y=0    
        
                    
    def page_break(self):
        """
        Insert a pagebreak.
        If the header and footer is set, they will be written to page.
        Page number will be incremented.
        """
        self.page_num= self.page_num+1
        self.write_header(self.header)
        if self.footer:
            self.write_footer(self.footer)
        else:
            self.footer.set_text(str(self.page_num))
            self.write_footer(self.footer)
        self.context.show_page()
        
    def assert_page_break(self):
        """
        Check if the current y position exceeds the page's height. 
        If so do the page break.
        """
        if  self.position_y > self.ybottom:
            self.page_break()

    def move_context(self, xoffset, yoffset):
        """
        Move the drawing context to given x,y offsets. 
        This is relative to the currect x,y drawing positions.
        
        Arguments:
    
        - xoffset: offset for the current x drawing postion 
        - yoffset: offset for the current y drawing postion 
        
        """
        self.position_x += xoffset
        self.position_y += yoffset
        
        

########NEW FILE########
__FILENAME__ = image_test
#!/usr/bin/python
#-*- coding: utf-8 -*-
# test.py

# pypdflib is a pango/cairo framework for generating reports.
# Copyright © 2010  Santhosh Thottingal <santhosh.thottingal@gmail.com>

# This file is part of pypdflib.
#
# pypdflib is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.  
#
# pypdflib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pypdflib.  If not, see <http://www.gnu.org/licenses/>.

import sys
sys.path.append("../src/")  #not good!
from pypdflib.writer import PDFWriter
from pypdflib.widgets import *
from pypdflib.styles import *
import pango

if __name__=="__main__":
    pdf = PDFWriter("image.pdf",StandardPaper.A4)
    header = Header(text_align = pango.ALIGN_CENTER)
    #TODO Alignment not working.
    header.set_text("test header")
    pdf.set_header(header)
    footer = Footer(text_align = pango.ALIGN_CENTER)
    footer.set_text("test footer")
    #TODO Alignment not working.
    pdf.set_footer(footer)
    image  = Image()  
    image.set_image_file("White_peacock.jpg")
    pdf.add_image(image)
    pdf.flush()
    """
    table = Table(border_width=1)
    row = Row(height=50)
    for i in range(4):
        cell = Cell("SampleCell "+str(i),font_size=8,width=100)
        row.add_cell(cell)
    for i in range(4):
        table.add_row(row)
        
    pdf.draw_table(table)
    pdf.flush()
    """

########NEW FILE########
__FILENAME__ = markup_test
#!/usr/bin/python
#-*- coding: utf-8 -*-
# markup_test.py

# pypdflib is a pango/cairo framework for generating reports.
# Copyright © 2011  Jinesh K J <jinesh@jinsbond.in>

# This file is part of pypdflib.
#
# pypdflib is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.  
#
# pypdflib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pypdflib.  If not, see <http://www.gnu.org/licenses/>.

import sys
sys.path.append("../src/")  #not good!
from pypdflib.writer import PDFWriter
from pypdflib.widgets import *
from pypdflib.styles import *
import pango

if __name__=="__main__":
    pdf = PDFWriter("markup.pdf",StandardPaper.A4)
    header = Header(text_align = pango.ALIGN_CENTER)
    #TODO Alignment not working.
    header.set_text("test header")
    pdf.set_header(header)
    footer = Footer(text_align = pango.ALIGN_CENTER)
    footer.set_text("test footer")
    #TODO Alignment not working.
    pdf.set_footer(footer)
    h1= Text("Samples",font_size=16) 
    pdf.add_text(h1)
    h2= Text("Malayalam",font_size=14) 
    h2.color = StandardColors.Blue
    pdf.add_text(h2)
    
    para_file_malayalam=open("markup.txt")
    #image = Image(image_file="Four_Sons_of_Dasaratha.png")
    #pdf.add_image(image)
    while True:
        para_content = para_file_malayalam.readline()
        if para_content ==None or para_content=="" : break 
        para = Paragraph(markup=para_content,text = para_content font="Serif")
        para.language = "ml_IN"
        print para_content
        pdf.add_paragraph(para)
    pdf.flush()
    """
    table = Table(border_width=1)
    row = Row(height=50)
    for i in range(4):
        cell = Cell("SampleCell "+str(i),font_size=8,width=100)
        row.add_cell(cell)
    for i in range(4):
        table.add_row(row)
        
    pdf.draw_table(table)
    pdf.flush()
    """

########NEW FILE########
__FILENAME__ = scripts_test
#!/usr/bin/python
#-*- coding: utf-8 -*-
# test.py

# pypdflib is a pango/cairo framework for generating reports.
# Copyright © 2010  Santhosh Thottingal <santhosh.thottingal@gmail.com>

# This file is part of pypdflib.
#
# pypdflib is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.  
#
# pypdflib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pypdflib.  If not, see <http://www.gnu.org/licenses/>.

import sys
sys.path.append("../src/")  #not good!
from pypdflib.writer import PDFWriter
from pypdflib.widgets import *
from pypdflib.styles import *
import pango

if __name__=="__main__":
    pdf = PDFWriter("scripts.pdf",StandardPaper.A4)
    header = Header(text_align = pango.ALIGN_CENTER)
    #TODO Alignment not working.
    header.set_text("test header")
    pdf.set_header(header)
    footer = Footer(text_align = pango.ALIGN_CENTER)
    footer.set_text("test footer")
    #TODO Alignment not working.
    pdf.set_footer(footer)
    h1= Text("Samples",font_size=16) 
    pdf.add_text(h1)
    h2= Text("Malayalam",font_size=14) 
    h2.color = StandardColors.Blue
    pdf.add_text(h2)
    
    para_file_malayalam=open("malayalam.txt")
    #image = Image(image_file="Four_Sons_of_Dasaratha.png")
    #pdf.add_image(image)
    while True:
        para_content = para_file_malayalam.readline()
        if para_content ==None or para_content=="" : break 
        para = Paragraph(text=para_content, font="Rachana")
        para.language = "ml_IN"
        pdf.add_paragraph(para)
    h2= Text("Hindi",font_size=14, font="Rachana") 
    h2.color = Color(0.0,0.0,0.8,1.0)
    pdf.add_text(h2)
    para_file_hindi=open("hindi.txt")
    
    while True:
        para_content = para_file_hindi.readline()
        if para_content ==None or para_content=="" : break 
        para = Paragraph(text=para_content)
        para.language = "hi_IN"
        pdf.add_paragraph(para)
        
    h2= Text("Bengali",font_size=14) 
    h2.color = Color(0.0,0.0,0.8,1.0)
    pdf.add_text(h2)   
     
    para_file_bengali=open("bengali.txt")
    while True:
        para_content = para_file_bengali.readline()
        if para_content ==None or para_content=="" : break 
        para = Paragraph(text=para_content)
        para.language = "bn_IN"
        pdf.add_paragraph(para)

    h2 = Text("Kannada",font_size=14)
    h2.color = Color(0.0,0.0,0.8,1.0)
    pdf.add_text(h2)

    para_file_kannada = open("kannada.txt")
    while True:
        para_content = para_file_kannada.readline()
        if para_content == None or para_content == "":break
        para = Paragraph(text=para_content)
        para.language = "kn_IN"
        pdf.add_paragraph(para)

    h2 = Text("Tamil",font_size=14)
    h2.color = Color(0.0,0.0,0.8,1.0)
    pdf.add_text(h2)

    para_file_tamil = open("tamil.txt")
    while True:
        para_content = para_file_tamil.readline()
        if para_content == None or para_content == "":break
        para = Paragraph(text=para_content)
        para.language = "ta_IN"
        pdf.add_paragraph(para)
    
    h2 = Text("Arabic",font_size=14)
    h2.color = Color(0.0,0.0,0.8,1.0)
    pdf.add_text(h2)    
    para_file_tamil = open("arabic.txt")
    while True:
        para_content = para_file_tamil.readline()
        if para_content == None or para_content == "":break
        para = Paragraph(text=para_content)
        para.language = "ar_AR"
        para.set_justify(False)
        pdf.add_paragraph(para)
    h2 = Text("Japanese",font_size=14)
    h2.color = Color(0.0,0.0,0.8,1.0)
    pdf.add_text(h2)    
    para_file_tamil = open("japanese.txt")
    while True:
        para_content = para_file_tamil.readline()
        if para_content == None or para_content == "":break
        para = Paragraph(text=para_content)
        para.language = "jp_JP"
        #para.set_justify(False)
        pdf.add_paragraph(para)            
    pdf.flush()
    """
    table = Table(border_width=1)
    row = Row(height=50)
    for i in range(4):
        cell = Cell("SampleCell "+str(i),font_size=8,width=100)
        row.add_cell(cell)
    for i in range(4):
        table.add_row(row)
        
    pdf.draw_table(table)
    pdf.flush()
    """

########NEW FILE########
__FILENAME__ = table_test
#!/usr/bin/python
#-*- coding: utf-8 -*-
# test.py

# pypdflib is a pango/cairo framework for generating reports.
# Copyright © 2010  Santhosh Thottingal <santhosh.thottingal@gmail.com>

# This file is part of pypdflib.
#
# pypdflib is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.  
#
# pypdflib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pypdflib.  If not, see <http://www.gnu.org/licenses/>.

import sys
sys.path.append("../src/")  #not good!
from pypdflib.writer import PDFWriter
from pypdflib.widgets import *
from pypdflib.styles import *
import pango

if __name__=="__main__":
    pdf = PDFWriter("tables.pdf",StandardPaper.A4)
    header = Header(text_align = pango.ALIGN_CENTER)
    #TODO Alignment not working.
    header.set_text("test header")
    pdf.set_header(header)
    footer = Footer(text_align = pango.ALIGN_CENTER)
    footer.set_text("test footer")
    #TODO Alignment not working.
    pdf.set_footer(footer)
    table = Table(border_width=1)
    table.cell_padding = [2, 2, 2, 2]
    row = Row(height=100)
    for i in range(4):
        cell_content = Text("SampleCell "+str(i),font_size=14)
        cell_content.color = Color(0.0,0.0,0.0,1.0)
        cell = Cell(cell_content, font_size=8,width=100)
        row.add_cell(cell)
    for i in range(4):
        table.add_row(row)
    pdf.add_table(table)
    pdf.flush()

########NEW FILE########
