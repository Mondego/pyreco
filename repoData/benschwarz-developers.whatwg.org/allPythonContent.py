__FILENAME__ = domtreewalker
"""Implementation of DOM 2 treewalker for lxml.etree trees"""
class NodeFilter(object):
    FILTER_ACCEPT = 1
    FILTER_REJECT = 2
    FILTER_SKIP = 3
    
    def acceptNode(self, node):
        raise NotImplementedError

class DOMTreeWalker(object):
    def __init__(self, root, filter):
        self.root = root
        self.currentNode = root
        if hasattr(filter, "acceptNode"):
            self.filter = filter.acceptNode
        else:
            self.filter = filter
    
    def firstChild(self):
        node = self._getNext(self.currentNode)
        if (node is not None and
            (self._getParent(node) == self.currentNode or
            self.currentNode == self.root and self._getParent(node) is None)):
            self.currentNode = node
            return node
        return None
    
    def lastChild(self):
        raise NotImplementedError
    
    def _getNext(self, node):
        node = self._treeOrderNextNode(node)
        while node is not None:
            accept = self.filter(node)
            if accept == NodeFilter.FILTER_SKIP:
                node = self._treeOrderNextNode(node)
            elif accept == NodeFilter.FILTER_REJECT:
                node = self._treeOrderNextNode(node, skipChildren=True)
            else:
                break
        return node
    
    def nextNode(self):
        node = self._getNext(self.currentNode)
        
        if node is not None:
            self.currentNode = node
            return node
        else:
            return None
    
    def nextSibling(self):
        node = self.currentNode.getnext()
        #Find the next acceptable node that is not a child 
        while (node is not None and self.filter(node) != NodeFilter.FILTER_ACCEPT
               and self._getParent(node) == self._getParent(self.currentNode)):
            accept = self.filter(node)
            if accept == NodeFilter.FILTER_SKIP:
                node = self._treeOrderNextNode(node)
            elif accept == NodeFilter.FILTER_REJECT:
                node = self._treeOrderNextNode(node, skipChildren=True)
        
        #If the node is a child of the current node's parent it is the node
        #we are looking for
        if (node is not None and self._getParent(node) ==
            self._getParent(self.currentNode)):
            self.currentNode = node
            return node
        
        return None
    
    def parentNode(self):
        node = self._getParent(self.currentNode)
        if node is not None:
            self.currentNode = node
            return node
        else:
            return None
    
    def _getParent(self, node):
        node = node.getparent()
        while node is not None and self.filter(node) != NodeFilter.FILTER_ACCEPT:
            node = node.getparent()
        return node
    
    def previousNode(self):
        #This doesn't handle the case where the current node is changed to a
        #subnode of a skipped node
        node = self._treeOrderPreviousNode(self.currentNode)
        if node is not None:
            self.currentNode = node
            return node
        else:
            return None
    
    def previousSibling(self):
        raise NotImplementedError
    
    def _treeOrderNextNode(self, node, skipChildren=False):
        if not skipChildren and len(node):
            #If the node has a child node, that is the next node
            return node[0]
        
        #Try the next sibling
        tmp_node = node.getnext()
        if tmp_node is None:
            #There are no siblings so we have to walk up the tree until
            #we find a node with a later sibling or hit the root element
            tmp_node = node
            parent = node.getparent()
            while (parent is not None and
                   len(parent) == tmp_node.getparent().index(tmp_node)+1):
                tmp_node = parent
                parent = tmp_node.getparent()
            if parent is not None and len(parent) > tmp_node.getparent().index(tmp_node)+1:
                #If the node we end up on has a sibling, that is the
                #next node in tree order
                node = tmp_node.getnext()
            else:
                #We must have iterated to the last child of the root
                assert parent == None
                node = None
        else:
           node = tmp_node 
        return node
    
    def _treeOrderPreviousNode(self, node):
        parent = node.getparent()
        tmp_node = node
        
        #Iterate up the parent chain until we find one that has a previous
        #sibling
        while (parent is not None and
               tmp_node.getparent().index(tmp_node) == 0):
            tmp_node = parent
            parent = tmp_node.getparent()
        
        if parent is not None and tmp_node.getparent().index(tmp_node) != 0:
            #If the node we end up on has a previous sibling, the previous node
            #in document order is found at the bottom of the last child chain
            #of that previous sibling
            node = parent[tmp_node.getparent().index(tmp_node)-1]
            while len(node):
                node = node[-1]
        else:
            #We must have iterated to a child of the root with no previous sibling
            assert parent == None
            node = None
        return node
########NEW FILE########
__FILENAME__ = headers
import domtreewalker
from domtreewalker import NodeFilter
import lxml.etree
import html5lib

heading_tags = ("h1", "h2", "h3", "h4", "h5", "h6")

def outline_filter(n):
    #Skip any descendants of headings.
    if (n.getparent() is not None and
        (n.getparent().tag == 'h1' or n.getparent().tag == 'h2' or
         n.getparent().tag == 'h3' or n.getparent().tag == 'h4' or
         n.getparent().tag == 'h5' or n.getparent().tag == 'h6' or
         n.getparent().tag == 'header')):
        return NodeFilter.FILTER_REJECT

    #Skip any blockquotes.
    elif (n.tag == 'blockquote'):
        return NodeFilter.FILTER_REJECT
  
    #Accept HTML elements in the list given in the prose
    elif (n.tag == 'body' or
          n.tag == 'section' or n.tag == 'nav' or
          n.tag == 'article' or n.tag == 'aside' or
          n.tag == 'h1' or n.tag == 'h2' or
          n.tag == 'h3' or n.tag == 'h4' or
          n.tag == 'h5' or n.tag == 'h6' or
          n.tag == 'header'):
        return NodeFilter.FILTER_ACCEPT
    else:
        # Skip the rest.
        return NodeFilter.FILTER_SKIP

def copyTree(treewalker):
    """Copy the tree in a dom treewalker into a new lxml.etree tree"""
    node_map = {} #Mapping between nodes in the output tree and those
                  #in the input tree
    
    def copySubtree(in_root, out_root):
        treewalker.currentNode = in_root
        out_root.text = in_root.text
        out_root.tail = in_root.tail
        node = treewalker.firstChild()
        while node is not None:
            if isinstance(node.tag, basestring):
                new_node = lxml.etree.SubElement(out_root, node.tag,
                                                attrib=node.attrib)
                copySubtree(node, new_node)
            elif node.tag is lxml.etree.Comment:
                new_node = lxml.etree.Comment(node.text)
                new_element.tail = node.tail
                out_root.append(new_element)
            node_map[new_node] = node
            
            treewalker.currentNode = node
            node = treewalker.nextSibling()
    
    new_root = lxml.etree.Element(treewalker.currentNode.tag)
    for k, v in treewalker.currentNode.attrib.iteritems():
        new_root.attrib[k] = v
    node_map[new_root] = treewalker.currentNode
    copySubtree(treewalker.currentNode, new_root)
    
    return new_root, node_map

def mutateTreeToOutline(outline_tree):
    for node in outline_tree.iterdescendants():
        parent = node.getparent()
        this_idx = parent.index(node)
        if (node.tag in list(heading_tags) + ["header"] and
            this_idx != 0):
            new_sectioning_element = lxml.etree.Element("section")
            if (node.tag == "header" or
                (node.tag in heading_tags and parent[0].tag in heading_tags and
                 node.tag[-1] <= parent[0].tag[-1]) or
                parent[0].tag not in list(heading_tags) + ["header"]):
                #Insert the new sectioning element as the immediately following
                #sibling of the parent sectioning element
                grandparent = parent.getparent()
                grandparent.insert(grandparent.index(parent) + 1, new_sectioning_element)
                #move all the elements from the current heading element up to
                #the end of the parent sectioning element into the new
                #sectioning element
                while len(parent) > this_idx:
                    child = parent[this_idx]
                    parent.remove(child)
                    new_sectioning_element.append(child)
            else:
                this_idx = parent.index(node)
                parent.remove(node)
                new_sectioning_element.append(node)
                while (len(parent) > this_idx and
                       parent[this_idx].tag in heading_tags and
                       parent[this_idx].tag[-1] > node.tag[-1]):
                    child = parent[this_idx]
                    parent.remove(child)
                    new_sectioning_element.append(child)
                parent.insert(this_idx, new_sectioning_element)
    return outline_tree

def printOutline(outline_tree):
    rv = []
    def print_node(node, indent):
        for child in node:
            if child.tag in list(heading_tags) + ["header"]:
                rv.append("-"*(indent-2) + child.text)
            else:
                print_node(child, indent+2)
            
    print_node(outline_tree, 0)
    return "\n".join(rv)
    
def getOutlineTree(html_file):
    p = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder("etree",
                                                                      lxml.etree, fullTree=False))
    t = p.parse(html_file)
    dtw = domtreewalker.DOMTreeWalker(t, outline_filter)
    #tb = html5lib.treebuilders.getTreeBuilder("etree", lxml.etree)()
    outline_tree, node_map = copyTree(dtw)
    outline_tree = mutateTreeToOutline(outline_tree)
    return outline_tree
########NEW FILE########
__FILENAME__ = support
import os
import sys
import glob

#Allow us to import the parent module
os.chdir(os.path.split(os.path.abspath(__file__))[0])
sys.path.insert(0, os.path.abspath(os.path.join(os.pardir, "src")))

import html5lib
from html5lib import html5parser, treebuilders

#Define the location of the tests as this changes in release versions
#RELEASE remove
test_dir = os.path.join(os.path.pardir,os.path.pardir,'testdata')
#END RELEASE
#RELEASE add
#test_dir = './testdata'
#END RELEASE

try:
    import simplejson
except:
    import re
    class simplejson:
        def load(f):
            true, false, null = True, False, None
            input = re.sub(r'(".*?(?<!\\)")',r'u\1',f.read().decode('utf-8'))
            return eval(input.replace('\r',''))
        load = staticmethod(load)

#Build a dict of avaliable trees
treeTypes = {"simpletree":treebuilders.getTreeBuilder("simpletree"),
             "DOM":treebuilders.getTreeBuilder("dom")}

#Try whatever etree implementations are avaliable from a list that are
#"supposed" to work
try:
    import xml.etree.ElementTree as ElementTree
    treeTypes['ElementTree'] = treebuilders.getTreeBuilder("etree", ElementTree, fullTree=True)
except ImportError:
    try:
        import elementtree.ElementTree as ElementTree
        treeTypes['ElementTree'] = treebuilders.getTreeBuilder("etree", ElementTree, fullTree=True)
    except ImportError:
        pass

try:
    import xml.etree.cElementTree as cElementTree
    treeTypes['cElementTree'] = treebuilders.getTreeBuilder("etree", cElementTree, fullTree=True)
except ImportError:
    try:
        import cElementTree
        treeTypes['cElementTree'] = treebuilders.getTreeBuilder("etree", cElementTree, fullTree=True)
    except ImportError:
        pass
    
try:
    import lxml.etree as lxml
    treeTypes['lxml'] = treebuilders.getTreeBuilder("etree", lxml, fullTree=True)
except ImportError:
    pass

try:
    import BeautifulSoup
    treeTypes["beautifulsoup"] = treebuilders.getTreeBuilder("beautifulsoup", fullTree=True)
except ImportError:
    pass

def html5lib_test_files(subdirectory, files='*.dat'):
    return glob.glob(os.path.join(test_dir,subdirectory,files))

class DefaultDict(dict):
    def __init__(self, default, *args, **kwargs):
        self.default = default
        dict.__init__(self, *args, **kwargs)
    
    def __getitem__(self, key):
        return dict.get(self, key, self.default)

class TestData(object):
    def __init__(self, filename, newTestHeading="data"):
        self.f = open(filename)
        self.newTestHeading = newTestHeading
    
    def __iter__(self):
        data = DefaultDict(None)
        key=None
        for line in self.f:
            heading = self.isSectionHeading(line)
            if heading:
                if data and heading == self.newTestHeading:
                    #Remove trailing newline
                    data[key] = data[key][:-1]
                    yield self.normaliseOutput(data)
                    data = DefaultDict(None)
                key = heading
                data[key]=""
            elif key is not None:
                data[key] += line
        if data:
            yield self.normaliseOutput(data)
        
    def isSectionHeading(self, line):
        """If the current heading is a test section heading return the heading,
        otherwise return False"""
        if line.startswith("#"):
            return line[1:].strip()
        else:
            return False
    
    def normaliseOutput(self, data):
        #Remove trailing newlines
        for key,value in data.iteritems():
            if value.endswith("\n"):
                data[key] = value[:-1]
        return data

def convert(stripChars):
    def convertData(data):
        """convert the output of str(document) to the format used in the testcases"""
        data = data.split("\n")
        rv = []
        for line in data:
            if line.startswith("|"):
                rv.append(line[stripChars:])
            else:
                rv.append(line)
        return "\n".join(rv)
    return convertData

convertExpected = convert(2)

########NEW FILE########
__FILENAME__ = test
#XXX
#import sys
#import os
#sys.path.insert(0, os.path.abspath("../html5lib/python/src/"))

import support
import headers
import cStringIO
import glob

def compareExpected(test):
    tree = headers.getOutlineTree(test["data"])
    received = headers.printOutline(tree)
    print "Data\n%s\nReceived\n%s\nExpected:\n%s"%(test["data"], received, test["outline"])
    assert received == test["outline"]

def testAll():
    for fn in glob.glob("tests/*.dat"):
        for test in support.TestData(fn):
            compareExpected(test)
########NEW FILE########
__FILENAME__ = parsetree
#!/usr/bin/env python2.4
import sys
import os
#sys.path.insert(0, os.path.expanduser("~/lib/python/"))
#sys.path.insert(0, os.path.expanduser("~/lib/python2.4/site-packages/"))

import urllib
import httplib2
import urlparse
import cgi
#import cgitb
#cgitb.enable()

import html5lib
from html5lib.treebuilders import simpletree

from genshi.template import MarkupTemplate
from genshi.builder import tag

try:
    import psyco
    psyco.full()
except ImportError:
    pass

tagClasses = {"element":"markup element-name",
              "attr_name":"markup attribute-name",
              "attr_value":"markup attribute-value",
              "comment":"markup comment",
              "doctype":"markup doctype",
              "text":"text",
              "text_marker":"marker text_marker",
              "comment_marker":"marker comment_marker",
              "doctype_marker":"marker doctype_marker"}

class ParseTreeHighlighter(object):    
    def makeStream(self, node, indent=-2):
        if node.type not in (simpletree.Document.type,
                             simpletree.DocumentFragment.type):
            indent+=2
            rv = self.serializeNode(node, indent)
        else:
            rv = tag()
        for child in node.childNodes:
            rv.append(self.makeStream(child, indent))
        return rv

    def serializeNode(self, node, indent):
        rv = tag(" "*indent+"|")
        if node.type == simpletree.TextNode.type:
            text = node.value.split("\n")
            rv.append(tag(tag.code("#text: ", class_=tagClasses["text_marker"]),
                      tag.code(text[0], class_=tagClasses["text"])))
            for line in text[1:]:
                rv.append(tag(tag("\n" + " "*indent+"|"),
                              tag.code(line, class_=tagClasses["text"])))
        elif node.type == simpletree.Element.type:
            rv.append(tag.code(node.name, class_=tagClasses["element"]))
            if node.attributes:
                for key, value in node.attributes.iteritems():
                    rv.append(tag(" ", tag.code(key,
                                                class_=tagClasses["attr_name"]),
                              "=", tag.code("\""+value+"\"",
                                            class_=tagClasses["attr_value"])))
        elif node.type == simpletree.CommentNode.type:
            rv.append(tag(tag.code("#comment: ", class_=tagClasses["comment_marker"]),
                      tag.code(node.data, class_=tagClasses["comment"])))
        elif node.type == simpletree.DocumentType.type:
            rv.append(tag(tag.code("DOCTYPE: ", class_=tagClasses["doctype_marker"]),
                          tag.code(node.name, class_=tagClasses["doctype"])))
        rv.append(tag("\n"))
        return rv

class InnerHTMLHighlighter(object):
    def makeStream(self, node, indent=-2):
        if node.type == simpletree.Element.type:
            indent+=2
        if node.type not in (simpletree.Document.type,
                             simpletree.DocumentFragment.type):
            rv = self.serializeNode(node, indent)
        else:
            rv = tag()
        for child in node.childNodes:
            rv.append(self.makeStream(child, indent))
        if node.type == simpletree.Element.type:
            rv.append(tag.code("</" + node.name + ">",
                               class_=tagClasses["element"]))
        return rv
    
    def serializeNode(self, node, indent):
        if node.type == simpletree.TextNode.type:
            if (node.parent.name not in html5lib.constants.rcdataElements
                and node.parent.name != "plaintext"):
                value = cgi.escape(node.value, True)
            else:
                value = node.value
            if node.parent.name in ("pre", "textarea"):
                value = "\n" + value
            rv = tag.code(value, class_="text")
        elif node.type == simpletree.Element.type:
            rv = tag("")
            rv.append(tag.code("<" + node.name, class_=tagClasses["element"]))
            if node.attributes:
                for key, value in node.attributes.iteritems():
                    value = cgi.escape(value, True)
                    rv.append(tag(" ", tag.code(key,
                                                class_=tagClasses["attr_name"]),
                              "=", tag.code("\""+value+"\"",
                                            class_=tagClasses["attr_value"])))
            rv.append(tag.code(">", class_=tagClasses["element"]))    
        elif node.type == simpletree.CommentNode.type:
            rv = tag.code("<!--"+node.data+"-->", class_=tagClasses["comment"])
        elif node.type == simpletree.DocumentType.type:
            rv = tag.code("<!DOCTYPE " + node.name + ">", class_=tagClasses["doctype"])
        return rv

class Response(object):
    def __init__(self, document):
        self.parser = html5lib.HTMLParser()
        self.document = document
        
    def parse(self, source):
        return self.parser.parse(source)

    def responseString(self, document):
        raise NotImplementedError

class ParseTree(Response):
    max_source_length=1024
    def generateResponseStream(self, source, tree):
        template = MarkupTemplate(open("output.xml").read())
        treeHighlighter = ParseTreeHighlighter()
        htmlHighlighter = InnerHTMLHighlighter()

        parseTree = treeHighlighter.makeStream(tree)
        innerHTML = htmlHighlighter.makeStream(tree)
        
        #Arguably this should be defined in the document
        if (len(source) <= self.max_source_length or
            self.document.uri and len(self.document.uri) < self.max_source_length):
            viewURL = self.viewUrl()
        else:
            viewURL=""
        
        stream = template.generate(inputDocument=source,
                                   parseTree = parseTree,
                                   innerHTML = innerHTML,
                                   parseErrors=self.parser.errors,
                                   sourceString = source,
                                   viewURL=viewURL)
        return stream

    def responseString(self):
        source = self.document.source
        tree = self.parse(source)
        source = source.decode(self.parser.tokenizer.stream.charEncoding, "ignore")
        stream = self.generateResponseStream(source, tree)
        return stream.render('html', doctype=("html", "", ""))

    def viewUrl(self):
        if self.document.uri and len(self.document.source)>self.max_source_length:
            params = {"uri":self.document.uri}
        else:
            params = {"source":self.document.source}
        params["loaddom"]=1
        parameters = urllib.urlencode(params)
        urlparts = ["", "", "parsetree.py", parameters, ""]
        return urlparse.urlunsplit(urlparts)

class TreeToJS(object):
    def serialize(self, tree):
        rv = []
        rv.append("var node = document.getElementsByTagName('html')[0];")
        #Remove the <html> node
        rv.append("var currentNode = node.parentNode;")
        rv.extend(["currentNode.removeChild(node);"])
        for node in tree:
            if node.name == "html":
                rv.extend(self.buildSubtree(node))
                break
        return "\n".join(rv)
    
    def buildSubtree(self, node):
        rv = []
        rv.extend(self.serializeNode(node))
        for i, child in enumerate(node.childNodes):
            rv.extend(self.buildSubtree(child))
        #Set the current node back to the node constructed when we were called
        rv.append("currentNode = currentNode.parentNode;")    
        return rv
    
    def serializeNode(self, node):
        rv = []
        if node.type == simpletree.TextNode.type:
            rv.append("node = document.createTextNode('%s');"%self.escape(node.value))
        elif node.type == simpletree.Element.type:
            rv.append("node = document.createElement('%s');"%self.escape(node.name))
            if node.attributes:
                for key, value in node.attributes.iteritems():
                    rv.append("attr = node.setAttribute('%s', '%s')"%(key,self.escape(value)))
        elif node.type == simpletree.CommentNode.type:
            rv.append("node = document.createComment('%s')"%self.escape(node.data))
    
        rv.append("currentNode.appendChild(node)")
        #Set the current node to the node we just inserted
        rv.append("currentNode = currentNode.childNodes[currentNode.childNodes.length-1];")
        return rv
    
    def escape(self, str):
        replaces = (
            ("\\", "\\\\"),
            ("\b", "\\b"),
            ("\f", "\\f"),
            ("\n", "\\n"),
            ("\r", "\\r"),
            ("\t", "\\t"),
            ("\v", "\\v"),
            ("\"",  "\\\""),
            ("'", "\\'")
            )
        for key, value in replaces:
            str = str.replace(key, value)
        return str

class LoadSource(Response):
    attr_val_is_uri=('href', 'src', 'action', 'longdesc')

    def rewriteLinks(self, tree):
        uri = self.document.uri
        if not uri:
            return
        baseUri = urlparse.urlsplit(uri)
        for node in tree:
            if node.type == simpletree.Element.type and node.attributes:
                for key, value in node.attributes.iteritems():
                    if key in self.attr_val_is_uri:
                        node.attributes[key] = urlparse.urljoin(uri, value)

    def insertHtml5Doctype(self, tree):
        doctype = simpletree.DocumentType("html")
        tree.insertBefore(doctype, tree.childNodes[0])

    def parse(self, source):
        return self.parser.parse(source)

    def generateResponseStream(self, tree):
        template = MarkupTemplate("""<html xmlns="http://www.w3.org/1999/xhtml"
                                xmlns:py="http://genshi.edgewall.org/">
                                <head><script>${jsCode}</script></head>
                                <body></body>
                                </html>""")
        jsGenerator = TreeToJS()
        jsCode = jsGenerator.serialize(tree)
        stream = template.generate(jsCode = jsCode)
        return stream

    def responseString(self):
        tree = self.parse(self.document.source)
        self.rewriteLinks(tree)
        stream = self.generateResponseStream(tree)
        doctype=None
        for node in tree.childNodes:
            if node.type == simpletree.DocumentType.type:
                doctype = (tree.childNodes[0].name, "", "")
                break
        
        return stream.render('html', doctype=doctype)

class Error(Response):
    def generateResponseStream(self):
        template = MarkupTemplate(open("error.xml").read())
        stream = template.generate(document=self.document)
        return stream
    
    def responseString(self):
        stream = self.generateResponseStream()
        return stream.render('html', doctype=("html", "", ""))

class Document(object):
    errors = {"CANT_LOAD":1, "INVALID_URI":2, "INTERNAL_ERROR":3}
    def __init__(self, uri=None, source=None, ua=None):
        
        self.uri = uri
        self.source = source

        self.error=None
        
        if not source and uri:
            try:
                self.source = self.load(ua)
            except:
                self.error = self.errors["INTERNAL_ERROR"]
        elif not source and not uri:
            self.error = self.errors["INVALID_URI"]
        
    def load(self, ua=None):
        
        http = httplib2.Http()
        uri = self.uri
        
        #Check for invalid URIs
        if not (uri.startswith("http://") or uri.startswith("https://")):
            self.error = self.errors["INVALID_URI"]
            return
        
        headers = {}
        
        if ua:
            headers ={"User-Agent":ua}
        
        response=None
        content=None
        
        try:
            response, content = http.request(uri, headers=headers)
        except:
            self.error = self.errors["CANT_LOAD"]
        
        if content:
            return content
        else:
            self.error = self.errors["CANT_LOAD"]
            return

def cgiMain():
    print "Content-type: text/html; charset=utf-8\n\n"
    
    form = cgi.FieldStorage()
    source = form.getvalue("source")
    if not source:
        uri = form.getvalue("uri")
    else:
        uri=None
    ua = form.getvalue("ua")
    if source:
        uri=None

    loadDOM = form.getvalue("loaddom")
    
    try:
        document = Document(uri=uri, source=source, ua=ua)
    except:
        #This should catch any really unexpected error
        if "cgitb" in locals():
            raise
        else:
            print "Unexpected internal error"
            return
        
    if document.error:
        respStr = error(document)
    else:
        try:
            if loadDOM:
                resp = LoadSource(document)
            else:
                resp = ParseTree(document) 
            respStr = resp.responseString()
        except:
            if "cgitb" in locals():
                raise
            else:
                document.error = document.errors["INTERNAL_ERROR"]
                respStr = error(document)
    
    print respStr

def error(document):
    resp = Error(document)
    return resp.responseString()
    
if __name__ == "__main__":
    cgiMain()

########NEW FILE########
__FILENAME__ = spec-splitter
import sys
import re
from lxml import etree # requires lxml 2.0
from copy import deepcopy

print "HTML5 Spec Splitter"

absolute_uris = False
w3c = False
use_html5lib_parser = False
use_html5lib_serialiser = False
file_args = []

for arg in sys.argv[1:]:
    if arg == '--absolute':
        absolute_uris = True
    elif arg == '--w3c':
        w3c = True
    elif arg == '--html5lib-parser':
        use_html5lib_parser = True
    elif arg == '--html5lib-serialiser':
        use_html5lib_serialiser = True
    else:
        file_args.append(arg)

if len(file_args) != 2:
    print 'Run like "python [options] spec-splitter.py index multipage"'
    print '(The directory "multipage" must already exist)'
    print
    print 'Options:'
    print '  --absolute ............. convert relative URLs to absolute (e.g. for images)'
    print '  --w3c .................. use W3C variant instead of WHATWG'
    print '  --html5lib-parser ...... use html5lib parser instead of lxml'
    print '  --html5lib-serialiser .. use html5lib serialiser instead of lxml'
    sys.exit()

if use_html5lib_parser or use_html5lib_serialiser:
    import html5lib
    import html5lib.serializer
    import html5lib.treewalkers

if w3c:
    index_page = 'Overview'
else:
    index_page = 'index'

# The document is split on all <h2> elements, plus the following specific elements
# (which were chosen to split any pages that were larger than about 100-200KB, and
# may need to be adjusted as the spec changes):
split_exceptions = [
    'common-microsyntaxes', 'urls', # <-- infrastructure
    'elements', 'content-models', 'apis-in-html-documents', # <-- dom

    'scripting-1', 'sections', 'grouping-content', 'text-level-semantics', 'edits',
    'embedded-content-1', 'the-iframe-element', 'the-video-element', 'the-canvas-element', 'the-map-element', 'tabular-data',
    'forms', 'the-input-element', 'states-of-the-type-attribute', 'number-state', 'common-input-element-attributes', 'the-button-element', 'association-of-controls-and-forms',
    'interactive-elements', 'commands', # <-- semantics

    'predefined-vocabularies-0', 'converting-html-to-other-formats', # <-- microdata
    'origin-0', 'timers', 'offline', 'history', 'links', # <-- browsers
    'dnd', # <-- editing

    'parsing', 'tokenization', 'tree-construction', 'the-end', 'named-character-references', # <-- syntax
]


print "Parsing..."

# Parse document
if use_html5lib_parser:
    parser = html5lib.html5parser.HTMLParser(tree = html5lib.treebuilders.getTreeBuilder('lxml'))
    doc = parser.parse(open(file_args[0]), encoding='utf-8')
else:
    parser = etree.HTMLParser(encoding='utf-8')
    doc = etree.parse(open(file_args[0]), parser)

print "Splitting..."

doctitle = doc.getroot().find('.//title').text

# Absolutise some references, so the spec can be hosted elsewhere
if absolute_uris:
    for a in ('href', 'src'):
        for t in ('link', 'script', 'img'):
            for e in doc.findall('//%s[@%s]' % (t, a)):
                if e.get(a)[0] == '/':
                    e.set(a, 'http://www.whatwg.org' + e.get(a))
                else:
                    e.set(a, 'http://www.whatwg.org/specs/web-apps/current-work/' + e.get(a))

# Extract the body from the source document
original_body = doc.find('body')

# Create an empty body, for the page content to be added into later
default_body = etree.Element('body')
if original_body.get('class'): default_body.set('class', original_body.get('class'))
if original_body.get('onload'): default_body.set('onload', 'fixBrokenLink(); %s' % original_body.get('onload'))
original_body.getparent().replace(original_body, default_body)

# Extract the header, so we can reuse it in every page
header = original_body.find('.//*[@class="head"]')

# Make a stripped-down version of it
short_header = deepcopy(header)
del short_header[2:]

# Extract the items in the TOC (remembering their nesting depth)
def extract_toc_items(items, ol, depth):
    for li in ol.iterchildren():
        for c in li.iterchildren():
            if c.tag == 'a':
                assert c.get('href')[0] == '#'
                items.append( (depth, c.get('href')[1:], c) )
            elif c.tag == 'ol':
                extract_toc_items(items, c, depth+1)
toc_items = []
extract_toc_items(toc_items, original_body.find('.//ol[@class="toc"]'), 0)

# Prepare the link-fixup script
if not w3c:
    link_fixup_script = etree.XML('<script src="link-fixup.js"/>')
    doc.find('head')[-1].tail = '\n  '
    doc.find('head').append(link_fixup_script)
    link_fixup_script.tail = '\n  '

# Stuff for fixing up references:

def get_page_filename(name):
    return '%s.html' % name

# Finds all the ids and remembers which page they were on
id_pages = {}
def extract_ids(page, node):
    if node.get('id'):
        id_pages[node.get('id')] = page
    for e in node.findall('.//*[@id]'):
        id_pages[e.get('id')] = page

# Updates all the href="#id" to point to page#id
missing_warnings = set()
def fix_refs(page, node):
    for e in node.findall('.//a[@href]'):
        if e.get('href')[0] == '#':
            id = e.get('href')[1:]
            if id in id_pages:
                if id_pages[id] != page: # only do non-local links
                    e.set('href', '%s#%s' % (get_page_filename(id_pages[id]), id))
            else:
                missing_warnings.add(id)

def report_broken_refs():
    for id in sorted(missing_warnings):
        print "warning: can't find target for #%s" % id

pages = [] # for saving all the output, so fix_refs can be called in a second pass

# Iterator over the full spec's body contents
child_iter = original_body.iterchildren()

def add_class(e, cls):
    if e.get('class'):
        e.set('class', e.get('class') + ' ' + cls)
    else:
        e.set('class', cls)

# Contents/intro page:

page = deepcopy(doc)
add_class(page.getroot(), 'split index')
page_body = page.find('body')

# Keep copying stuff from the front of the source document into this
# page, until we find the first heading that isn't class="no-toc"
for e in child_iter:
    if e.getnext().tag == 'h2' and 'no-toc' not in (e.getnext().get('class') or '').split(' '):
        break
    page_body.append(e)

pages.append( (index_page, page, 'Front cover') )

# Section/subsection pages:

def should_split(e):
    if e.tag == 'h2': return True
    if e.get('id') in split_exceptions: return True
    if e.tag == 'div':
        c = e.getchildren()
        if len(c):
            if c[0].tag == 'h2': return True
            if c[0].get('id') in split_exceptions: return True
    return False

def get_heading_text_and_id(e):
    if e.tag == 'div':
        node = e.getchildren()[0]
    else:
        node = e
    title = re.sub('\s+', ' ', etree.tostring(node, method='text').strip())
    return title, node.get('id')

for heading in child_iter:
    # Handle the heading for this section
    title, name = get_heading_text_and_id(heading)
    if name == index_page: name = 'section-%s' % name
    print '  <%s> %s - %s' % (heading.tag, name, title)

    page = deepcopy(doc)
    add_class(page.getroot(), 'split chapter')
    page_body = page.find('body')

    page.find('//title').text = title + u' \u2014 ' + doctitle

    # Add the header
    page_body.append(deepcopy(short_header))

    # Add the page heading
    page_body.append(deepcopy(heading))
    extract_ids(name, heading)

    # Keep copying stuff from the source, until we reach the end of the
    # document or find a header to split on
    e = heading
    while e.getnext() is not None and not should_split(e.getnext()):
        e = child_iter.next()
        extract_ids(name, e)
        page_body.append(deepcopy(e))

    pages.append( (name, page, title) )

# Fix the links, and add some navigation:

for i in range(len(pages)):
    name, doc, title = pages[i]

    fix_refs(name, doc)

    if name == index_page: continue # don't add nav links to the TOC page

    head = doc.find('head')

    if w3c:
        nav = etree.Element('div') # HTML 4 compatibility
    else:
        nav = etree.Element('nav')
    nav.text = '\n   '
    nav.tail = '\n\n  '

    if i > 1:
        href = get_page_filename(pages[i-1][0])
        title = pages[i-1][2]
        a = etree.XML(u'<a href="%s">\u2190 %s</a>' % (href, title))
        a.tail = u' \u2013\n   '
        nav.append(a)
        link = etree.XML('<link href="%s" title="%s" rel="prev"/>' % (href, title))
        link.tail = '\n  '
        head.append(link)

    a = etree.XML('<a href="%s.html#contents">Table of contents</a>' % index_page)
    a.tail = '\n  '
    nav.append(a)
    link = etree.XML('<link href="%s.html#contents" title="Table of contents" rel="index"/>' % index_page)
    link.tail = '\n  '
    head.append(link)

    if i != len(pages)-1:
        href = get_page_filename(pages[i+1][0])
        title = pages[i+1][2]
        a = etree.XML(u'<a href="%s">%s \u2192</a>' % (href, title))
        a.tail = '\n  '
        nav.append(a)
        a.getprevious().tail = u' \u2013\n   '
        link = etree.XML('<link href="%s" title="%s" rel="next"/>' % (href, title))
        link.tail = '\n  '
        head.append(link)

    # Add a subset of the TOC to each page:

    # Find the items that are on this page
    new_toc_items = [ (d, id, e) for (d, id, e) in toc_items if id_pages[id] == name ]
    if len(new_toc_items) > 1: # don't bother if there's only one item, since it looks silly
        # Construct the new toc <ol>
        new_toc = etree.XML(u'<ol class="toc"/>')
        cur_ol = new_toc
        cur_li = None
        cur_depth = 0
        # Add each item, reconstructing the nested <ol>s and <li>s to preserve
        # the nesting depth of each item
        for (d, id, e) in new_toc_items:
            while d > cur_depth:
                if cur_li is None:
                    cur_li = etree.XML(u'<li/>')
                    cur_ol.append(cur_li)
                cur_ol = etree.XML('<ol/>')
                cur_li.append(cur_ol)
                cur_li = None
                cur_depth += 1
            while d < cur_depth:
                cur_li = cur_ol.getparent()
                cur_ol = cur_li.getparent()
                cur_depth -= 1
            cur_li = etree.XML(u'<li/>')
            cur_li.append(deepcopy(e))
            cur_ol.append(cur_li)
        nav.append(new_toc)

    doc.find('body').insert(1, nav) # after the header

report_broken_refs()

print "Outputting..."

# Output all the pages
for name, doc, title in pages:
    f = open('%s/%s' % (file_args[1], get_page_filename(name)), 'w')
    if w3c:
        f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN">\n')
    else:
        f.write('<!DOCTYPE html>\n')
    if use_html5lib_serialiser:
        tokens = html5lib.treewalkers.getTreeWalker('lxml')(doc)
        serializer = html5lib.serializer.HTMLSerializer(quote_attr_values=True, inject_meta_charset=False, omit_optional_tags=False)
        for text in serializer.serialize(tokens, encoding='us-ascii'):
            if text != '<!DOCTYPE html>': # some versions of lxml emit this; get rid of it if so
                f.write(text)
    else:
        f.write(etree.tostring(doc, pretty_print=False, method="html"))

# Generate the script to fix broken links
f = open('%s/fragment-links.js' % (file_args[1]), 'w')
links = ','.join("'%s':'%s'" % (k.replace("\\", "\\\\").replace("'", "\\'"), v) for (k,v) in id_pages.items())
f.write('var fragment_links = { ' + re.sub(r"([^\x20-\x7f])", lambda m: "\\u%04x" % ord(m.group(1)), links) + ' };\n')
f.write("""
var fragid = window.location.hash.substr(1);
if (!fragid) { /* handle section-foo.html links from the old multipage version, and broken foo.html from the new version */
    var m = window.location.pathname.match(/\/(?:section-)?([\w\-]+)\.html/);
    if (m) fragid = m[1];
}
var page = fragment_links[fragid];
if (page) {
    window.location.replace(page+'.html#'+fragid);
}
""")

print "Done."

########NEW FILE########
__FILENAME__ = experimental
import html4

class HeadingMatcher(html4.HeadingMatcher):
    def __init__(self, useScopeAttr=True, useHeadersAttr=True,
                 useTdBHeadings=False, useTdStrongHeadings=False,):
        self.useScopeAttr = useScopeAttr
        self.useHeadersAttr = useHeadersAttr
        self.useTdBHeadings = useTdBHeadings
        self.useTdStrongHeadings = useTdStrongHeadings
    
    def implicitHeaders(self, cell):
        row_headers = []
        col_headers = []
        
        #In some cases with overlapping cells we might try to examine a cell
        #more than once to see if it is a heading
        cells_examined = []
        
        def checkAxis(axis, axis_headers, start_x, start_y):
            axis_all_headings = True
            
            #Check if the cell is in a row/column that is all headings; if it
            #is do not add other headers from along that axis
            if axis=="row":
                origin = (0, cell.anchor[1])
            else:
                assert axis == "col"
                origin = (cell.anchor[0],1)
            
            for current_cell in self.table.iterAxis(origin,
                                               axis=axis, dir=1):
                if not self.isHeading(current_cell):
                    axis_all_headings = False
                    break
            
            if not axis_all_headings:
                last_cell = None
                for current_cell in self.table.iterAxis((start_x, start_y),
                                                    axis=axis, dir=-1):
                    if (self.isHeading(current_cell) and
                        current_cell not in axis_headers and
                        (not self.useScopeAttr or
                        not "scope" in current_cell.element.attrib)):
                        axis_headers.append(current_cell)
                        #If a header cell has the headers attribute set,
                        #then the headers referenced by this attribute are
                        #inserted into the list and the search stops for the
                        #current direction.
                        if (self.useHeadersAttr and
                            "headers" in current_cell.element.attrib):
                            axis_headers += self.headersAttrHeaders(current_cell)
                            break
                        #The search in a given direction stops when the edge of the
                        #table is reached or when a data cell is found after a
                        #header cell.
                        if last_cell in axis_headers:
                            break
                    last_cell == current_cell
        
        #Need to search over all rows and cols the cell covers
        
        #Start by searching up each column
        for x_cell in range(cell.anchor[0], cell.anchor[0] + cell.colspan):
            checkAxis("col", col_headers, x_cell, cell.anchor[1]-1)
        
        #Then search along the row
        for y_cell in range(cell.anchor[1], cell.anchor[1] + cell.rowspan):
            checkAxis("row", row_headers, cell.anchor[0]-1, y_cell)
        
        #Column headers are inserted after row headers, in the order
        #they appear in the table, from top to bottom.
        headers = row_headers[::-1] + col_headers[::-1]
        
        return headers
    
    def isHeading(self, cell):
        """HTML 4 defines cells with the axis attribute set to be headings"""
        heading = cell.isHeading
        if ((not cell.element.text or not cell.element.text.strip())
            and len(cell.element)):
            import sys
            if self.useTdBHeadings and cell.element[0].tag == "b":
                heading = True
            if self.useTdStrongHeadings and cell.element[0].tag == "strong":
                heading = True
        return heading

########NEW FILE########
__FILENAME__ = html4
import _base

class HeadingMatcher(_base.HeadingMatcher):
    """Cell -> headinglist matcher based on the HTML 4 specification

    Note that this specification is rather vauge, so there is some
    disagreement about the expected behaviour"""
    def __init__(self, useScopeAttr=True, useHeadersAttr=True):
        self.useScopeAttr = useScopeAttr
        self.useHeadersAttr = useHeadersAttr
    
    def matchAll(self, table):

        rv = {}
        self.table = table
        #Build a map of headers with @scope -> cells they apply to
        if self.useScopeAttr:
            scope_map = self.getScopeMap()
        #For each cell in the table, try to attach headers using @headers,
        #@scope and the implicit algorithm, in that order
        for slot in table:
            for cell in slot:
                #If the cell has a rowspan or colspan > 1 it will be
                #in multiple slots. In this case we only want to
                #process the cell once
                if cell in rv:
                    continue
                if self.useHeadersAttr:
                    rv[cell] = self.headersAttrHeaders(cell)
                    if rv[cell] is not None:
                        continue
                if self.useScopeAttr:
                    rv[cell] = self.scopeAttrHeaders(cell, scope_map)
                    if rv[cell] is not None:
                        continue
                #Finally we try the implicit algorithm. This therefore gets applied to all 
                #cells without any headers deriving from @scope or @headers. It's not
                #clear if this is right or if this algorithm is only supposed to be 
                #applied if there is no @scope or @headers in the whole table
                rv[cell] = self.implicitHeaders(cell)
                if cell not in rv:
                    rv[cell] = None
        return rv
    
    def implicitHeaders(self, cell):
        """Get headers using the implicit headers algorithm"""
        row_headers = []
        col_headers = []
        
        #In some cases with overlapping cells we might try to examine a cell
        #more than once to see if it is a heading
        cells_examined = []
        
        def checkAxis(axis, axis_headers, start_x, start_y):
            last_cell = None
            for current_cell in self.table.iterAxis((start_x, start_y),
                                                    axis=axis, dir=-1):
                if (self.isHeading(current_cell) and
                    current_cell not in axis_headers and
                    (not self.useScopeAttr or
                     not "scope" in current_cell.element.attrib)):
                    
                    axis_headers.append(current_cell)
                    #If a header cell has the headers attribute set,
                    #then the headers referenced by this attribute are
                    #inserted into the list and the search stops for the
                    #current direction.
                    if (self.useHeadersAttr and
                        "headers" in current_cell.element.attrib):
                        axis_headers += self.headersAttrHeaders(current_cell)
                        break
                else:
                    #The search in a given direction stops when the edge of the
                    #table is reached or when a data cell is found after a
                    #header cell.
                    if last_cell in axis_headers:
                        break
                last_cell = current_cell
        
        #Need to search over all rows and cols the cell covers
        
        #Start by searching up each column 
        for x_cell in range(cell.anchor[0], cell.anchor[0] + cell.colspan):
            checkAxis("col", col_headers, x_cell, cell.anchor[1]-1)
            
        for y_cell in range(cell.anchor[1], cell.anchor[1] + cell.rowspan):
            checkAxis("row", row_headers, cell.anchor[0]-1, y_cell)
        
        #Column headers are inserted after row headers, in the order
        #they appear in the table, from top to bottom.
        headers = row_headers[::-1] + col_headers[::-1]
        
        return headers
    
    def scopeAttrHeaders(self, cell, scopeMap=None):
        if scopeMap is None:
            scopeMap = self.getScopeMap(self.table)
        headers = []
        for header, cells in scopeMap.iteritems():
            if cell in cells:
                headers.append(header)
        if not headers:
            headers = None
        return headers
    
    def isHeading(self, cell):
        """Return a boolean indicating whether the element is a heading
        
        HTML 4 defines cells with the axis or scope attribute set to be headings"""
        return (cell.isHeading or "axis" in cell.element.attrib
                or "scope" in cell.element.attrib)
        
    
    def getScopeMap(self):
        """Return a dict matching a heading to a list of cells to which it is
        assosiated from the scope attribute"""
        rv = {}
        for heading_cell in self.table.headings:
            heading_element = heading_cell.element
            if not "scope" in heading_element.attrib:
                continue
            scope = heading_element.attrib["scope"]
            x,y = heading_cell.anchor
            if scope == "row":
                for s in range(heading_cell.rowspan):
                    rv[heading_cell] = [item for item in
                                        self.table.iterAxis((x+heading_cell.colspan, y+s), axis="row")]
            elif scope == "col":
                for s in range(heading_cell.colspan):
                    rv[heading_cell] = [item for item in
                                        self.table.iterAxis((x+s, y+heading_cell.rowspan), axis="col")]
            elif scope == "rowgroup":
                cells = []
                for rowgroup in self.table.rowgroups:
                    if y >= rowgroup.anchor[1] and y <= rowgroup.anchor[1] + rowgroup.span:
                        #This applies the heading to all other cells in the group
                        #below and to the right of the current heading
                        #This is hard to justify from the spec because it's
                        #not especially clear on this point
                        cells += [item for item in rowgroup if item != heading_cell and
                                  item.anchor[0] >= heading_cell.anchor[0] and
                                  item.anchor[1] >= heading_cell.anchor[1]]
                rv[heading_cell] = cells
            elif scope == "colgroup":
                cells = []
                for colgroup in self.table.colgroups:
                    if x >= colgroup.anchor[0] and x <= colgroup.anchor[0] + colgroup.span:
                        cells += [item for item in colgroup if item != heading_cell and
                                  item.anchor[0] >= heading_cell.anchor[0] and
                                  item.anchor[1] >= heading_cell.anchor[1]]
                rv[heading_cell] = cells
        return rv

########NEW FILE########
__FILENAME__ = html5
import _base
from collections import defaultdict

class HeadingMatcher(_base.HeadingMatcher):
    """Cell -> Headings list mapping using the September 2007 HTML 5
    algorithm"""
    def matchAll(self, table):
        rv = defaultdict(lambda:None)
        self.table = table
        scope_map = self.scopeAttributeHeaders()
        #Invert the headers->cells map
        for header, cells in scope_map.iteritems():
            for cell in cells:
                if cell not in rv:
                    rv[cell] = [header]
                else:
                    rv[cell].append(header)
        return rv
    
    def scopeAttributeHeaders(self):
        """Return a dict matching a heading to a list of cells to which it is
        assosiated"""
        rv = {}
        for heading_cell in self.table.headings:
            heading_element = heading_cell.element
            if "scope" in heading_element.attrib:
                scope = heading_element.attrib["scope"]
            else:
                scope = None
            x,y = heading_cell.anchor
            if scope == "row":
                #The cell != heading cell thing is not in the spec
                rv[heading_cell] = [item for item in 
                                    self.table.iterAxis((x+1, y), "row") 
                                    if not item.isHeading]
            elif scope == "col":
                rv[heading_cell] = [item for item in 
                                    self.table.iterAxis((x, y+1), axis="col") 
                                    if not item.isHeading]
            elif scope == "rowgroup":
                cells = []
                for rowgroup in self.table.rowgroups:
                    if (heading_cell.anchor[1] >= rowgroup.anchor[1] and
                        heading_cell.anchor[1] < rowgroup.anchor[1] + rowgroup.span):
                        cells += [item for item in rowgroup
                                  if item.anchor[0] >= heading_cell.anchor[0] and
                                  item.anchor[1] >= heading_cell.anchor[1] and
                                  not item.isHeading]
                rv[heading_cell] = cells
            elif scope == "colgroup":
                cells = []
                for colgroup in self.table.colgroups:
                    if (heading_cell.anchor[0] >= colgroup.anchor[0] and
                        heading_cell.anchor[0] < colgroup.anchor[0] + colgroup.span):
                        cells += [item for item in colgroup 
                                  if item.anchor[0] >= heading_cell.anchor[0] and
                                  item.anchor[1] >= heading_cell.anchor[1] and
                                  not item.isHeading]
                rv[heading_cell] = cells
            else:
                if x>0 and y>0:
                    #Do not assign the heading to any cells
                    continue
                elif y == 0:
                    rv[heading_cell] = [item for item in 
                                        self.table.iterAxis((x, y+1), axis="col") 
                                        if not item.isHeading]
                elif x == 0:
                    rv[heading_cell] = [item for item in 
                                        self.table.iterAxis((x+1, y), "row") if 
                                        not item.isHeading]
        return rv

########NEW FILE########
__FILENAME__ = smartcolspan
import _base

class HeadingMatcher(_base.HeadingMatcher):
    """Get a cell -> headers mapping using the method proposed by
    Ben Millard and Simon Pieters where headers are limited in scope to the
    next header down the column with the same colspan
    
    note - this algorithm has been superceeded by that in smartheaders.py"""

    def __init__(self, no_headings_if_spans_data_col = False):
        self.no_headings_if_spans_data_col = no_headings_if_spans_data_col

    def matchAll(self, table):
        rv = {}
        headers_dict = self.associateHeaders(table)
        for slot in table:
            for cell in slot:
                rv[cell] = headers_dict.get(cell)
        return rv

    def isHeading(self, table, cell):
        """Assume only <td> cells are headings"""
        return cell.isHeading
    
    def associateHeaders(self, table):
        rv = {}
        #For each cell at the top of the table
        cells_with_no_heading_col = []
        for current_heading in table.iterAxis((0, 0), axis="row", dir=1):
            #List of cells that span a column with no headings
            if self.isHeading(table, current_heading):
                #For each col this cell covers
                for x in range(current_heading.anchor[0], current_heading.anchor[0] + current_heading.colspan):
                    column_headings = [current_heading]
                    #Have we found the first data cell
                    td_found = False
                    for current_cell in table.iterAxis(
                        (x, current_heading.rowspan),
                        axis="col", dir=1):
                        if current_cell not in rv:
                            rv[current_cell] = []
                        #Go down the column
                        if self.isHeading(table, current_cell) and not td_found:
                            rv[current_cell].extend(column_headings)
                            column_headings.append(current_cell)
                        elif self.isHeading(table, current_cell):
                            for heading in column_headings[:]:
                                if heading.colspan == current_cell.colspan: 
                                    column_headings.remove(heading)
                            rv[current_cell].extend(column_headings[:])
                            column_headings.append(current_cell)
                        else:
                            td_found = True
                            rv[current_cell].extend(column_headings[:])
            else:
                #The top cell is not a heading cell. If scan down the column
                #for all data cells before we reach a heading cell
                
                #Give this a more sensible name
                top_cell = current_heading
                
                for x in range(top_cell.anchor[0], top_cell.anchor[0]+top_cell.colspan):
                    for current_cell in table.iterAxis((x, 0), axis="col", dir=1):
                        if not self.isHeading(table, current_cell):
                            cells_with_no_heading_col.append(current_cell)
                        else:
                            break
        if self.no_headings_if_spans_data_col:
            #Unassign headings from the cells
            for cell in cells_with_no_heading_col:
                rv[cell] = []
                
        return rv

########NEW FILE########
__FILENAME__ = smartheaders
import _base

class HeadingMatcher(_base.HeadingMatcher):
    """Smart span algorithm, based on an idea by Simon Pieters and Ben Millard

    Essentially, headings only apply as far down/across the table as
    there are no other headers with the same colspan/rowspan. This
    version also has support for the headers attribute and for the
    scope attribute"""

    def matchAll(self, table):
        """
        The basic algorithm is:
           1. For each cell in the table:
              2. If the cell has a headers attribute which lists the id of one
              or more heading cells in the table, set those as the headers for
              the cell
              3. Otherwise select the headers of the cell from the scope
              attribute of the headers
            4: Return the cell -> headers mapping (dict)
        """
        
        rv = {}
        self.table = table
        
        #Create a header -> cells mapping based on @scope or auto
        headers = {}
        for cell in table.iterCells():
            if self.isHeading(cell):
                headers[cell] = self.associateCellsWithHeader(cell)
        
        #Invert the headers -> cells mapping to a cell -> headers mapping
        headers_dict = {}
        for k, v in headers.iteritems():
            if v is None:
                continue
            for cell in v:
                if cell not in headers_dict:
                    headers_dict[cell] = [k]
                else:
                    headers_dict[cell].append(k)
        
        for cell in table.iterCells():
            headers_attr_headers = self.headersAttrHeaders(cell)
            #If the cell has a headers attribute add those headers and no others
            if headers_attr_headers:
                rv[cell] = headers_attr_headers
            elif cell in headers_dict:
                rv[cell] = headers_dict[cell]
            else:
                rv[cell] = None
        return rv

    def isHeading(self, cell):
        """Is the current cell a heading. Here we assume all <th> cells and no
        <td> cells are headings"""
        return cell.isHeading
    
    def associateCellsWithHeader(self, header):
        """Return the cells associated with a header according to its scope;
        either via the smart span algorithm for scope in (auto, row, col) or
        by selecting all cells below/right of the header in the (row|col)groups
        it spans (scope in (rowgroup, colgroup))
        """
        
        scope = None
        if "scope" in header.element.attrib:
            scope = header.element.attrib["scope"].lower()
        if scope is None or scope not in ("row", "col", "rowgroup", "colgroup"):
            scope = "auto"
        
        cells = []
        
        if scope == "auto":
            cells = self.getCellsFromAxes(header, ("row", "col"))
        elif scope == "row":
            cells = self.getCellsFromAxes(header, ("row",), skip_heading_only_axes=False)
        elif scope == "col":
            cells = self.getCellsFromAxes(header, ("col",), skip_heading_only_axes=False)
        elif scope == "rowgroup":
            groups = self.getHeaderGroups(header, "row")
            assert len(groups) == 1
            cells = self.getCellsFromGroup(header, groups[0])
        elif scope == "colgroup":
            groups = self.getHeaderGroups(header, "col")
            for group in groups:
                cells.extend([item for item in
                              self.getCellsFromGroup(header, group) if item not in cells])
        return cells
    
    def getCellsFromAxes(self, header, axes, skip_heading_only_axes=True):
        """
        Get cells associated with a header using the smart span algorithm
        
        The algorthm is this:
        1. cell_list be the list of cells with which header is associated
        2. For each axis in axes:
           3. let span be the number of rows spanned by header on axis
           4. for each row or column spanned by header on axis:
               5. If skip_heading_only_axes is set and all the cells on the
                  current row/column are headings, go to step 4 for the next row/column
               6. let data_found be false
               7. let current_cell be the cell immediatley adjacent to the header
                  on the current row/column
               8. If current_cell is a heading:
                  9. If current_cell's span across the current axis is equal to
                     span and data_cell_found is True then go to step XX
                  10. Otherwise, if current_cell's span across the current axis is
                      greater than or equal to span add current_cell to cell_list
               11. Otherwise current_cell is a data cell. Add current_cell to cell_list
                   and set data_cell_found to be true
        12. Return cell_list
        
        Notes: This does not associate a cell that overlaps with the header cell
               It is not clear that the handling of groups of headers in the middle of the table
               is sophisticated enough; however we deal with simple cases where the headers match those
               at the begginning of the axis
        """
        
        cells = []
        for axis in axes:
            if axis == "row":
                min_index = header.anchor[1]
                max_index = header.anchor[1] + header.rowspan
            else:
                min_index = header.anchor[0]
                max_index = header.anchor[0] + header.colspan
            span = axis + "span"
            for axis_index in xrange(min_index, max_index):
                heading_span = getattr(header, span)
                data_cell_found = False
                if axis == "row":
                    start_index = (header.anchor[0]+header.colspan, axis_index)
                else:
                    start_index = (axis_index, header.anchor[1]+header.rowspan)
                
                current_headings = []
                
                #If all the cells in the row/col are headings, none apply to each other
                if skip_heading_only_axes:
                    all_headings = True
                    for cell in self.table.iterAxis(start_index, axis=axis, dir=1):
                        all_headings = self.isHeading(cell)
                        if not all_headings:
                            break
                    if all_headings:
                        continue
                    
                for cell in self.table.iterAxis(start_index, axis=axis, dir=1):
                    if self.isHeading(cell):
                        current_span = getattr(cell, span)
                        if heading_span == current_span and data_cell_found:
                            break
                        elif heading_span >= current_span:
                            cells.append(cell)
                    elif not self.isHeading(cell):
                        cells.append(cell)
                        data_cell_found = True
        return cells
    
    def getCellsFromGroup(self, header, group):
        """Get all the matching cells for a heading that scopes a group
        
        Matching cells are those that lie below and to the right of the header in
        the group (assuming ltr)"""
        
        rv = []
        for cell in group:
            if (cell.anchor[0] >= header.anchor[0] and cell.anchor[1] >= header.anchor[1]
                and cell != header):
                rv.append(cell)
        return rv
    
    def getHeaderGroups(self, cell, axis):
        """Get all  (row|col)groups spanned by cell
        
        axis - row or col"""
        
        property_map = {"col":(0, "colgroups"),
            "row":(1, "rowgroups")}
        rv = []
        idx, group_type = property_map[axis]
        for group in getattr(self.table, group_type):
            if (cell.anchor[idx] >= group.anchor[idx]):
                if cell.anchor[idx] < group.anchor[idx] + group.span:    
                    rv.append(group)
            else:
                if group.anchor[idx] < cell.anchor[idx] + getattr(cell, axis + "span"):
                    rv.append(group)
        return rv

########NEW FILE########
__FILENAME__ = _base
class HeadingMatcher(object):
    """Base class for headings matchers."""
    def matchAll(self, table):
        """Get a dict mapping each cell to a list of header cells with which
        it is associated

        table - a Table object for the html table to be processed"""
        raise NotImplementedError
    
    def isHeading(self, cell):
        return cell.isHeading
    
    def headersAttrHeaders(self, cell):
        """Get all headers that apply to cell via a headers attribute
        
        The value of @headers is split on whitespace to give a series of tokens
        Each token is used as an id for a getElementById rooted on the table
        If no matching header is found, the token is skipped
        Otherwise the matching heading is added to the list of headers
        """
        
        #What to do if an item is missing or is not a header?
        headers = []
        if not "headers" in cell.element.attrib:
            return None
        attr = cell.element.attrib["headers"]
        #The value of this attribute is a space-separated list of cell names
        for id in attr.split(" "):
            headerElements = self.table.element.xpath("//td[@id='%s']|//th[@id='%s']"%(id, id))
            if headerElements:
                match = headerElements[0]
            else:
                continue
            header = self.table.getCellByElement(match)
            if header is not None:
                headers.append(header)
        return headers

########NEW FILE########
__FILENAME__ = tableparser
# coding=utf-8
import itertools

import html5lib
from html5lib import constants

def skipWhitespace(value, initialIndex):
    """Take a string value and an index into the string and return the index
    such that value[index] points to the first non-whitespace character in
    value[initialIndex:]"""
    index = initialIndex
    while value[index] in html5lib.constants.spaceCharacters:
        index += 1
    return index

def parseNonNegativeInteger(input_str):
    """HTML 5 algorithm for parsing a non-negative integer from an attribute"""
    position = 0
    value = 0
    position = skipWhitespace(input_str, position)
    if position == len(input_str):
        raise ValueError
    elif input_str[position] not in html5lib.constants.digits:
        raise ValueError
    else:
        while (position < len(input_str) and
               input_str[position] in html5lib.constants.digits):
            value *= 10
            value += int(input_str[position])
            position += 1
    return value

class TableParser(object):
    def parse(self, table):
        """Parse the table markup into a table structure, based on the HTML5
        algorithm"""
        #We index from 0 not 1; changes to enable this are marked with comments starting #ZIDX
        
        #1. Let xmax be zero.
        #2. Let ymax be zero.
        self.x_max = 0
        self.y_max = 0
        
        #3. Let the table be the table represented by the table element.
        #The xmax and ymax variables give the table's extent. The table is
        #initially empty.
        self.the_table = Table(table)
        
        #4. If the table element has no table children, then return the table
        #(which will be empty), and abort these steps.
        if not len(table):
            return self.the_table
    
        #5. Let the current element be the first element child of the table element.
        currentElement = table[0]
            
        #6. While the current element is not one of the following elements, advance
        #the current element to the next child of the table
        while currentElement.tag not in ("caption", "colgroup", "thead", "tbody",
                                         "tfoot", "tr"):
            currentElement = currentElement.getnext()
            if currentElement is None:
                return self.the_table
        
        #7. If the current element is a caption, then that is the caption element
        #associated with the table. Otherwise, it has no associated caption element.
        if currentElement.tag == "caption":
            self.the_table.caption = currentElement
            #8. If the current element is a caption, then while the current element
            #is not one of the following elements, advance the current element to
            #the next child of the table:
            while currentElement.tag not in ("colgroup", "thead", "tbody",
                                             "tfoot", "tr"):
                currentElement = currentElement.getnext()
                if currentElement is None:
                    return self.the_table
        
        #9. If the current element is a colgroup, follow these substeps:
        while currentElement.tag == "colgroup":
            #9.1 Column groups. Process the current element according to the
            # appropriate one of the following two cases:
        
            #If the current element has any col element children 
            if "col" in currentElement:
                #9.1.1.1 Let xstart have the value xmax+1.
                x_start = self.x_max + 1
                columns = currentElement.xpath("col")
                #9.1.1.2 Let the current column be the first col element child of the
                #colgroup element.
                for current_column in columns:
                    #9.1.1.3 Columns. If the current column col element has a span
                    #attribute, then parse its value using the rules for parsing
                    #non-negative integers. If the result of parsing the value is not an error or
                    #zero, then let span be that value. Otherwise, if the col element
                    #has no span attribute, or if trying to parse the attribute's value
                    #resulted in an error, then let span be 1.
                    if "span" in currentElement.attrib:
                        try:
                            span = parseNonNegativeInteger(currentElement.attrib["span"])
                        except ValueError:
                            span =  1
                    else:
                        span = 1
                    #9.1.1.4 Increase xmax by span.
                    self.x_max += span
                    #9.1.1.5 Let the last span columns in the table correspond to the
                    #current column col element.
                    for col_num in range(span):
                        self.the_table.columns.append(column)
                        #9.1.1.6 If current column is not the last col element child
                        #of the colgroup element, then let the current column be
                        #the next col element child of the colgroup element, and
                        #return to the third step of this innermost group of steps
                        #(columns).
                
                    #9.1.1.7 Let all the last columns in the table  from x=xstart
                    #to x=xmax  form a new column group, anchored at the slot
                    #(xstart, 1), with width xmax-xstart-1, corresponding to the
                    #colgroup element.
                    
                    #ZIDX coordinates are (x_start-1,0)
                    self.the_table.colgroups.append(
                        ColGroup(self.the_table,currentElement,(x_start-1,0),
                                 self.x_max-x_start-1))
                
            #If the current element has no col element children 
            else:
                #9.1.2.1 If the colgroup element has a span attribute, then
                #parse its value using the rules for parsing non-negative
                #integers. If the result of parsing the value is not an
                #error or zero, then let span be that value. Otherwise, if
                #the colgroup element has no span attribute, or if trying to
                #parse the attribute's value resulted in an error, then let
                #span be 1.
                if "span" in currentElement.attrib:
                    try:
                        span = parseNonNegativeInteger(currentElement.attrib["span"])
                    except ValueError:
                        span =  1
                else:
                    span = 1
                #9.1.2 Increase xmax by span.
                self.x_max += span
                #9.1.3 Let the last span columns in the table form a new
                #column group, anchored at the slot (xmax-span+1, 1), with
                #width span, corresponding to the colgroup element.

                #ZIDX coordinates are (self.x_max-span,0)
                self.the_table.colgroups.append(
                    ColGroup(self.the_table, currentElement,
                             (self.x_max-span, 0), span))

            #9.2 Advance the current element to the next child of the table.
            currentElement = currentElement.getnext()
            if currentElement is None:
                return self.the_table
            
            #9.3 While the current element is not one of the following
            #elements, advance the current element to the next child of the
            #table:
            while currentElement.tag not in ("colgroup", "thead", "tbody",
                                             "tfoot", "tr"):
                currentElement = currentElement.getnext()
                if currentElement is None:
                    return self.the_table
            #If the current element is a colgroup element, jump to step 1 in
            #these substeps (column groups).
    
        #10. Let ycurrent be zero. When the algorithm is aborted, if ycurrent
        #does not equal ymax, then that is a table model error.
        self.y_current = 0
        #11. Let the list of downward-growing cells be an empty list.
        self.downward_growing_cells = []
        while True:
            #12. Rows. While the current element is not one of the following
            #elements, advance the current element to the next child of the table:
            while currentElement.tag not in ("thead", "tbody", "tfoot", "tr"):
                currentElement = currentElement.getnext()
                if currentElement is None:
                    if self.y_current != self.y_max:
                        self.the_table.model_error.append("XXX")
                    return self.the_table
            if currentElement.tag == "tr":
                #13. If the current element is a tr, then run the algorithm for
                #processing rows (defined below), then return to the
                #previous step (rows).
                self.processRow(currentElement)
            else:
                #14. Otherwise, run the algorithm for ending a row group.
                self.endRowGroup()
                #15. Let ystart have the value ymax+1.
                y_start = self.y_max + 1
                #16. For each tr element that is a child of the current
                #element, in tree order, run the algorithm for processing
                #rows
                for tr_element in currentElement.xpath("tr"):
                    self.processRow(tr_element)
                #17/ If ymax ≥ ystart, then let all the last rows in the
                #table from y=ystart to y=ymax form a new row group,
                #anchored at the slot with coordinate (1, ystart), with
                #height ymax-ystart+1, corresponding to the current element.
                if self.y_max >= y_start:
                    #ZIDX coordinates are (0,y_start-1)
                    self.the_table.rowgroups.append(
                        RowGroup(self.the_table, currentElement, (0,y_start-1),
                                 self.y_max-y_start+1))
                #18. Run the algorithm for ending a row group again.
                self.endRowGroup()
                #19. Return to step 12 (rows).

                #XXX?
            currentElement = currentElement.getnext()
            if currentElement is None:
                if self.the_table.unfilledSlots():
                    self.the_table.model_errors.append("Unfilled slots in table")
                return self.the_table
    
    def endRowGroup(self):
        #1. If ycurrent is less than ymax, then this is a table model error.
        while self.y_current < self.y_max:
            self.the_table.error = True
            #2. While ycurrent is less than ymax, follow these steps:
            #2.1 Increase ycurrent by 1.
            self.y_current += 1
            #2.2 Run the algorithm for growing downward-growing cells.
            self.growDownwardCells()
        #3. Empty the list of downward-growing cells.
        self.downward_growing_cells = []
    
    def processRow(self, row_element):
        #1. Increase ycurrent by 1.
        self.y_current += 1
        #2. Run the algorithm for growing downward-growing cells.
        self.growDownwardCells()
        #3. Let xcurrent be 1.
        x_current = 1
        #4. If the tr element being processed contains no td or th elements,
        #then abort this set of steps and return to the algorithm above.
        #5. Let current cell be the first td or th element in the tr
        #element being processed.
        for current_cell in row_element.xpath("td|th"):
            #6. While xcurrent is less than or equal to xmax and the slot with
            #coordinate (xcurrent, ycurrent) already has a cell assigned to it,
            #increase xcurrent by 1.
            
            #ZIDX Coordinates are (x_current-1, y_current-1)
            while x_current < self.x_max and (x_current-1, self.y_current-1) in self.the_table and self.the_table[x_current-1, self.y_current-1]:
                x_current += 1
            #7.If xcurrent is greater than xmax, increase xmax by 1 (which will
            #make them equal).
            if x_current > self.x_max:
                self.x_max += 1
                assert x_current == self.x_max
            #8. If the current cell has a colspan attribute, then parse that
            #attribute's value, and let colspan be the result.
            #If parsing that value failed, or returned zero, or if the attribute
            #is absent, then let colspan be 1, instead.
            if 'colspan' in current_cell.attrib:
                try:
                    colspan = parseNonNegativeInteger(current_cell.attrib['colspan'])
                    if colspan == 0:
                        colspan = 1
                except ValueError:
                    colspan = 1
            else:
                colspan = 1
            #9. If the current cell has a rowspan attribute, then parse that
            #attribute's value, and let rowspan be the result.
            #If parsing that value failed or if the attribute is absent, then
            #let rowspan be 1, instead
            #10. If rowspan is zero, then let cell grows downward be true, and set
            #rowspan to 1. Otherwise, let cell grows downward be false.
            if 'rowspan' in current_cell.attrib:
                try:
                    rowspan = parseNonNegativeInteger(current_cell.attrib['rowspan'])
                    if rowspan == 0:
                        cell_grows_downwards = True
                        rowspan = 1
                    else:
                        cell_grows_downwards = False
                except ValueError:
                    rowspan = 1
            else:
                rowspan = 1
            
            #11. If xmax < xcurrent+colspan-1, then let xmax be
            #xcurrent+colspan-1.
            if self.x_max < x_current + colspan - 1:
                self.x_max = x_current + colspan - 1
            
            #12. If ymax < ycurrent+rowspan-1, then let ymax be
            #ycurrent+rowspan-1.
            if self.y_max < self.y_current + rowspan - 1:
                self.y_max = self.y_current + rowspan - 1
                
            #14. Let the slots with coordinates (x, y) such that xcurrent ≤ x <
            #xcurrent+colspan and ycurrent ≤ y < ycurrent+rowspan be covered by
            #a new cell c, anchored at (xcurrent, ycurrent), which has width
            #colspan and height rowspan, corresponding to the current cell
            #element.
            
            #ZIDX Coordinates are (x_current-1, y_current-1)
            new_cell = Cell(current_cell, (x_current-1, self.y_current-1), rowspan,
                             colspan)
            for x in range(x_current, x_current+colspan):
                for y in range(self.y_current, self.y_current+rowspan):
                    #ZIDX Slot indicies are (x-1, y-1)
                    self.the_table.appendToSlot((x-1,y-1), new_cell)    
            
            #15. Increase xcurrent by colspan.
            x_current += colspan
            
            #16. If current cell is the last td or th element in the tr element
            #being processed, then abort this set of steps and return to the
            #algorithm above.
            
            #17. Let current cell be the next td or th element in the tr element
            #being processed.

            #18. Return to step 5 (cells).
        
    def growDownwardCells(self):
        #1. If the list of downward-growing cells is empty, do nothing.
        #Abort these steps; return to the step that invoked this algorithm.
        if self.downward_growing_cells:
            #2. Otherwise, if ymax is less than ycurrent, then increase ymax
            #by 1 (this will make it equal to ycurrent).
            if self.y_max < self.y_current:
                self.y_max += 1
                assert self.y_max == self.y_current
            #3. For each {cell, cellx, width} tuple in the list of downward-growing
            #cells, extend the cell cell so that it also covers the slots with
            #coordinates (x, ycurrent), where cellx ≤ x < cellx+width-1.
            for (cell, cell_x, width) in self.downward_growing_cells:
                for x in range(cell_x, cell_x+width-1):
                    self.the_table.appendToSlot(x, self.y_current)


class Table(object):
    """Representation of a full html table"""
    def __init__(self, element):
        self.element = element #associated lxml element
        self.data = [] #List of Cells occupying each slot in the table
        self.colgroups = [] #List of colgroups in the table
        self.rowgroups = []
        self.columns = []
        self.caption = None #text of the table <caption>
        self.model_errors = [] #List of table model errors
        self.elementToCell = {} #Mapping between lxml elements and Cell objects
                                #to use in getCellByElement
        
    def __getitem__(self, slot):
        return self.data[slot[1]][slot[0]]
    
    def __contains__(self, slot):
        try:
            self.data[slot[1]][slot[0]]
            return True
        except IndexError:
            return False
    
    def __iter__(self):
        """Iterate over all the slots in a table in row order, returning a list
        of cells in each slot (overlapping cells may lead to > 1 cell per slot)"""
        x_max,y_max = self.x_max+1,self.y_max+1
        for x in range(x_max):
            for y in range(y_max):
                yield self[x,y]
    
    def iterCells(self):
        """Iterate over all cells in the table"""
        emitted_cells = set()
        for slot in self:
            for cell in slot:
                if cell not in emitted_cells:
                    emitted_cells.add(cell)
                    yield cell
    
    def iterAxis(self, starting_slot, axis="row", dir=1):
        """Iterate over all the cells (not slots) along one row or column in
        the table"""
        x,y = starting_slot
        emitted_cells = []
        if axis == "row":
            if dir == 1:
                x_end = self.x_max + 1
            else:
                x_end=-1
            indicies = [(x,y) for x,y in zip(range(starting_slot[0], x_end, dir),
                                             itertools.repeat(starting_slot[1]))]
        elif axis == "col":
            if dir == 1:
                y_end = self.y_max + 1
            else:
                y_end=-1
            indicies = [(x,y) for x,y in zip(itertools.repeat(starting_slot[0]),
                                             range(starting_slot[1], y_end, dir))]
        else:
            raise ValueError, "Unknown axis %s. Axis must be either 'row' or 'col'"%(axis,)

        for x,y in indicies:
            for cell in self[x,y]:
                if cell not in emitted_cells:
                    emitted_cells.append(cell)
                    yield cell
    
    def getXMax(self):
        try:
            return len(self.data[0])-1
        except IndexError:
            return -1
    
    def getYMax(self):
        return len(self.data)-1
    
    x_max = property(getXMax)
    y_max = property(getYMax)
    
    def unfilledSlots(self):
        rv = []
        for x in range(self.x_max):
            for y in range(self.y_max):
                if not self[x,y]:
                    rv.append((x,y))
        return rv
    
    def expandTable(self, slot):
        """Grow the storage to encompass the slot slot"""
         #Add any additional rows needed 
        if slot[1] > self.y_max:
            for i in range(slot[1]-self.y_max):
                self.data.append([[] for j in range(self.x_max+1)])
        #Add any additional columns needed
        if slot[0] > self.x_max:
            x_max = self.x_max
            for y in range(self.y_max+1):
                for x in range(slot[0]-x_max):
                    self.data[y].append([])
        assert all([len(item) == len(self.data[0]) for item in self.data])
    
    def appendToSlot(self, slot, item):
        """Add a Cell to a slot in the table"""
        if slot not in self:
            self.expandTable(slot)
        assert slot in self
        if self[slot]:
            #If there is already a cell assigned to the slot this is a
            #table model error
            self.model_errors.append("Multiple cells in slot %s"%str(slot))
        self.data[slot[1]][slot[0]].append(item)
        
        #Add the item to the element-cell mapping:
        if item.element in self.elementToCell:
            assert self.elementToCell[item.element] == item
        else:
            self.elementToCell[item.element] = item

    def getHeadings(self):
        """List of all headings in the table"""
        headings = []
        for slot in self:
            for cell in slot:
                if cell.isHeading and cell not in headings:
                    headings.append(cell)
        return headings
    headings = property(getHeadings)
    
    def row(self, index):
        """All the slots in a row"""
        return self.data[index-1]
    
    def col(self, index):
        """All the slots on a column"""
        return [row[index-1] for row in self.data[:]]
    
    def getCellByElement(self, element):
        """Return the cell object corresponding to the Element 'element'
        or None"""
        return self.elementToCell.get(element)
    
class Cell(object):
    """Cell type"""
    def __init__(self, element, anchor, rowspan, colspan):
        self.element = element
        self.anchor = anchor
        self.rowspan = rowspan
        self.colspan = colspan
    
    isHeading = property(lambda self:self.element.tag == "th", None, "Is the cell a <th> cell")

class Group(object):
    """Base class for row/column groups. These define a rectangle of cells
    anchored on a particular slot with a particular span across one axis of the
    table"""
    def __init__(self, table, element, anchor, span):
        self.table = table
        self.element = element
        self.anchor = anchor #Slot in the table to which the cell is anchored
        self.span = span #colspan or rowspan
    
    def __iter__(self):
        raise NotImplementedError
    
class RowGroup(Group):
    def __init__(self, table, element, anchor, span):
        Group.__init__(self, table, element, anchor, span)
        assert self.anchor[0] == 0
    def __iter__(self):
        """Return each unique cell in the row group"""
        emitted_elements = []
        for y in range(self.anchor[1], self.anchor[1]+self.span):
            for x in range(self.table.x_max+1):
                slot = self.table[x,y]
                for cell in slot:
                    if cell not in emitted_elements:
                        yield cell
                        emitted_elements.append(cell)
    
class ColGroup(Group):
    def __init__(self, table, element, anchor, span):
        Group.__init__(self, table, element, anchor, span)
        assert self.anchor[1] == 0
    
    def __iter__(self):
        """Return each unique cell in the column group"""
        emitted_elements = []
        for x in range(self.anchor[0], self.anchor[0]+self.span):
            for y in range(self.table.y_max+1):
                slot = self.table[x,y]
                for cell in slot:
                    if cell not in emitted_elements:
                        yield cell
                        emitted_elements.append(cell)
########NEW FILE########
__FILENAME__ = test_headers
import os
import glob

import simplejson
import html5lib

import tableparser
import headers

"""Test harness for headers code
The input is json format in a file testdata/headers/*.test

the file format is:
 {"tests":
          {"input":"html input string",
            "cases":[
                     ["algorithm_name", {"algorithm_option":option_value}, 
                       {"cell textContent":[list of header text content]}
                     ],
                      more cases... 
                    ]
           },
           more tests ...
 }
Each cell in input must have textContent that is unique in the table"""

matchers = dict([(item, getattr(headers, item).HeadingMatcher) for item in 
                 ("html4", "html5", "experimental", "smartcolspan", 
                  "smartheaders")])

def childText(node, addTail=False):
    """Return the textContent of an lxml node"""
    if node.text:
        rv = node.text
    else:
        rv = ""
    for child in node:
        child_text = childText(child, True)
        if child_text is not None:
            rv += child_text
    if addTail and node.tail is not None:
        rv += node.tail
    return rv

def parseTable(document):
    parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder("lxml"))
    tree = parser.parse(document)
    table = tree.xpath("//table")[0]
    tparser = tableparser.TableParser()
    return tparser.parse(table)

def compareHeaders(text_cell_map, headers_map, expected_results):
    """Actually compare the headers"""
    for cell_text, expected_headers_text in expected_results.iteritems():
        cell = text_cell_map[cell_text]
        expected_headers = set([text_cell_map[item] for item in expected_headers_text])
        received_headers = set(headers_map[cell] or [])
        try:
            assert received_headers == expected_headers
        except AssertionError:
            print "Cell:", cell_text
            print "Expected:", expected_results[cell_text]
            print "Got:", [childText(item.element) for item in received_headers]
            raise

def runtest(testdata):
    table = parseTable(testdata["input"])
    print "Input", testdata["input"]
    text_cell_map = {} #mapping between the textContent and cells
    for cell in table.iterCells():
        text_cell_map[childText(cell.element)] = cell

    for case in testdata["cases"]:
        algorithm, args, expected_results = case
        
        #Need to do unicode -> str conversion on kwargs
        kwargs = {}
        for k,v in args.iteritems():
            kwargs[str(k)] = v

        print "algorithm", algorithm
        print "args", kwargs

        matcher = matchers[algorithm](**kwargs)
        headers_map = matcher.matchAll(table)

        for result in expected_results:
            compareHeaders(text_cell_map, headers_map, expected_results)
    

def test_tableparser():
    """Load all the tests"""
    for testfile in glob.glob("testdata/headers/*.test"):
        tests = simplejson.load(open(testfile))
        for test in tests["tests"]:
            yield runtest, test

########NEW FILE########
__FILENAME__ = test_tables
import os
import glob

import simplejson
import html5lib
import lxml.etree

import tableparser

def parseDocument(document):
    parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder("etree", lxml.etree))
    tree = parser.parse(document)
    return tree

def compareSlots(expected, actual):
    assert actual.x_max >= 0 and actual.y_max >= 0
    for x in range(0, actual.x_max):
        for y in range(0, actual.y_max):
            expected_cells = expected[y][x]
            actual_cells = actual[x,y]
            assert len(expected_cells) == len(actual_cells)
            for i in range(len(expected_cells)):
                assert expected_cells[i] == actual_cells[i].element.text

def compareGroup(expected, actual):
    assert len(expected) == len(actual)
    for grp_actual, grp_expected in zip(actual, expected):
        print "Slot: expected %s got %s"%(str(grp_expected["slot"]), str(grp_actual.anchor))
        assert tuple(grp_expected["slot"]) == grp_actual.anchor
        print "Tag: expected %s got %s"%(str(grp_expected["tag"]), str(grp_actual.element.tag))
        assert grp_expected["tag"] == grp_actual.element.tag
        if "height" in grp_expected:
            print "Height: expected %s got %s"%(str(grp_expected["height"]), str(grp_actual.span))
            assert grp_expected["height"] == grp_actual.span
        else:
            print "Width: expected %s got %s"%(str(grp_expected["width"]), str(grp_actual.span))
            assert grp_expected["width"] == grp_actual.span

def runtest(testdata):
    table = parseDocument(testdata["data"]).xpath("//table")[0]
    tparser = tableparser.TableParser()
    actual = tparser.parse(table)
    compareSlots(testdata["slots"], actual)
    
    compareGroup(testdata["rowgroups"], actual.rowgroups)
    compareGroup(testdata["colgroups"], actual.colgroups)
    
    if testdata["caption"] is not None:
        assert actual.caption.text == testdata["caption"]
    else:
        assert actual.caption == None

def test_tableparser():
    for testfile in glob.glob("testdata/*.test"):
        tests = simplejson.load(open(testfile))
        for test in tests["tests"]:
            yield runtest, test
########NEW FILE########
__FILENAME__ = table_inspector
#!/usr/bin/env python
import sys
import os
import urlparse
import urllib2
import cgi
import cgitb
cgitb.enable()
import itertools
import httplib

import html5lib
from html5lib import treewalkers
import lxml.etree
import genshi
from genshi.template import MarkupTemplate
from genshi.core import QName, Attrs
from genshi.core import START, END, TEXT, COMMENT, DOCTYPE
    
import tableparser
import headers
from headers import html4, html5, experimental, smartcolspan, smartrowspan, smartheaders

debug=True

class InspectorException(Exception):
    """Base class for our local exceptions"""
    def __init__(self, type):
        self.type = type

class InputError(InspectorException):
    pass

class URIError(InspectorException):
    pass

class DocumentError(InspectorException):
    pass

#From the html5lib test suite
def GenshiAdapter(treewalker, tree):
    """Generator to convert html5lib treewalker tokens into Genshi
    stream tokens"""
    text = None
    for token in treewalker(tree):
        token_type = token["type"]
        if token_type in ("Characters", "SpaceCharacters"):
            if text is None:
                text = token["data"]
            else:
                text += token["data"]
        elif text is not None:
            assert type(text) in (unicode, None)
            yield TEXT, text, (None, -1, -1)
            text = None

        if token_type in ("StartTag", "EmptyTag"):
            yield (START,
                   (QName(token["name"]),
                    Attrs([(QName(attr),value) for attr,value in token["data"]])),
                   (None, -1, -1))
            if token_type == "EmptyTag":
                token_type = "EndTag"

        if token_type == "EndTag":
            yield END, QName(token["name"]), (None, -1, -1)

        elif token_type == "Comment":
            yield COMMENT, token["data"], (None, -1, -1)

        elif token_type == "Doctype":
            yield DOCTYPE, (token["name"], None, None), (None, -1, -1)

        else:
            pass # FIXME: What to do?

    if text is not None:
        yield TEXT, text, (None, -1, -1)

def parse(document):
    """Parse a html string or file-like object into a lxml tree"""
    if hasattr(document, "info"):
        charset = document.info().getparam("charset")
    else:
        charset="utf-8"
    parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder("lxml"))
    tree = parser.parse(document, encoding=charset).getroot()
    return tree

def copySubtree(in_root, out_root):
    """Copy all the desendants of in_node to out_node"""
    out_root.text = in_root.text
    out_root.tail = in_root.tail
    for element in in_root.iterchildren():
        if isinstance(element.tag, basestring):
            new_element = lxml.etree.SubElement(out_root, element.tag, attrib=element.attrib)
            copySubtree(element, new_element)
        elif element.tag is lxml.etree.Comment:
            new_element = lxml.etree.Comment(element.text)
            new_element.tail = element.tail
            out_root.append(new_element)

class TableAnnotator(object):
    """Class for taking an lxml <table> element, and annotating a copy with
    information about the headings relating to each cell"""
    def __init__(self, heading_matcher):
        """heading_matcher - a headers.HeadingMatcher """
        self.heading_matcher = heading_matcher
        self.tw = treewalkers.getTreeWalker("etree", lxml.etree)
        self.heading_counter = itertools.count()
    
    def annotate(self, in_tree, id):
        #Store some temporary state in the class
        self.in_tree = in_tree
        self.id = id
        self.table = tableparser.TableParser().parse(in_tree)
        self.headings_map = self.heading_matcher.matchAll(self.table)
        self.heading_ids = {} #mapping of headings to id values
        
        self.out_tree = lxml.etree.Element("table")
        #Copy the input tree into the output
        copySubtree(in_tree, self.out_tree)
        
        self.element_map = self.make_input_output_map()
        
        for in_element, out_element in self.element_map.iteritems():
            cell = self.table.getCellByElement(in_element)
            if not cell:
                continue
            headings = self.headings_map[cell]
            if headings:
                self.annotate_cell(cell, headings, out_element)
        
        return (self.table, GenshiAdapter(self.tw, self.out_tree))        

    def make_input_output_map(self):
        """Create a dict mapping input tree elements to output tree elements"""
        element_map = {}
        for in_element, out_element in itertools.izip(self.in_tree.iterdescendants(),
                                                      self.out_tree.iterdescendants()):
            if in_element.tag in ("td","th"):
                cell = self.table.getCellByElement(in_element)
                if not cell:
                    continue
            element_map[in_element] = out_element
        return element_map

    def annotate_cell(self, cell, headings, out_element):
        """Annotate cell with a list of all the headings it is associated with
        and attributs to be used by script and AT to make the association"""
        #Create a container element for the annotation
        container = lxml.etree.Element("div", attrib={"class":"__tableparser_heading_container"})
        #Add a paragraph to the cell identifying the headings
        title = lxml.etree.SubElement(container, "p", attrib={"class":"__tableparser_heading_title"})
        title.text = "Headings:"
        #Now create a list of actual headings
        heading_list = lxml.etree.SubElement(container, "ul", attrib={"class":"__tableparser_heading_list"})
        for heading in headings:
            #Check if the heading is one we have encountered before.
            #If not, add a unique identifier for it to use in the highlighting script
            if heading not in self.heading_ids:
                self.annotate_heading(heading)
            #For each heading, copy the list items to the cell
            heading_data = lxml.etree.Element("li", attrib={"class":"__tableparser_heading_listitem"})
            copySubtree(heading.element, heading_data)
            heading_list.append(heading_data)

            #Add a ref to the heading to the headers attribute for use in AT
            self.add_string_list_attr("headers", out_element, self.heading_ids[heading])
        out_element.insert(0, container)
        container.tail = out_element.text
        out_element.text=""
    
    def annotate_heading(self, heading):
        """Add id abd classnames o headings so they can be referenced from cells"""
        i= self.heading_counter.next()
        id = "__tableparser_heading_id_%s_%i"%(self.id, i)
        heading_out_element = self.element_map[heading.element]
        heading_out_element.attrib['id'] = id
        self.heading_ids[heading] = id
    
    def add_string_list_attr(self, attr_name, element, value):
        """Add a class name to an element""";
        if attr_name in element.attrib:
            element.attrib[attr_name] += " " + value
        else:
            element.attrib[attr_name] = value

    def add_class(self, element, class_name):
        return self.add_string_list_attr("class", element, class_name)


class Response(object):
    status = None
    
    def __init__(self, environ):
        self.headers = {}
        self.environ = environ
        self.body = self.create_body()
    
    def create_body(self, environ):
        return ""
    
    def send(self):
        print "Status: %i %s"%(self.status, httplib.responses[self.status])
        for header, value in self.headers.iteritems():
            print "%s: %s"%(header, value)
        print "\r"
        if self.environ["REQUEST_METHOD"] != "HEAD":
            print self.body

class OK(Response):
    status = 200
    def __init__(self, environ):
        Response.__init__(self, environ)
        self.headers["Content-type"] = "text/html; charset=utf-8"

class MethodNotAllowed(Response):
    status = 405
    def __init__(self, environ):
        Response.__init__(self, environ)
        self.headers = {"Allow":"GET, POST, HEAD"}

class InternalServerError(Response):
    status = 500

class Error(OK):
    def create_body(self):
        form = self.environ["cgi_storage"]
        out_template = MarkupTemplate(open("error.xml"))
        stream = out_template.generate(uri=(form.getfirst("uri") or ""), errorType=self.environ["error_type"])
        return stream.render('html', doctype=("html", "", ""))

class TableHeadersResponse(OK):
    headers_algorithms = {"html4":(html4, ["scope", "headers"]),
                          "html5":(html5, []),
                          "experimental":(experimental, ["scope", "headers",
                                                         "b_headings",
                                                         "strong_headings"]),
                          "smartcolspan":(smartcolspan,
                                            ["no_headings_if_spans_data_col"]),
                          "smartheaders":(smartheaders, [])}
    template_filename = "table_output.html"

    def create_body(self):
        form = self.environ["cgi_storage"]
        
        input_type = form.getfirst("input_type")
        if input_type == "type_uri":
            uri = form.getfirst("uri") or ""
            if not uri:
                raise InputError("MISSING_URI")
            else:
                if urlparse.urlsplit(uri)[0] not in ("http", "https"):
                    raise URIError("INVALID_SCHEME")
                try:
                    source = urllib2.urlopen(uri)
                except urllib2.URLError:
                    raise URIError("CANT_LOAD")
        elif input_type == "type_source":
            source = form.getfirst("source")
            if not source:
                raise InputError("MISSING_SOURCE")
        else:
            raise InputError("INVALID_INPUT")
        
        self.tables = parse(source).xpath("//table")
        if not self.tables:
            raise DocumentError("NO_TABLES")
        
        algorithm = form.getfirst("algorithm")
        
        headings_module, algorithm_options = self.headers_algorithms[algorithm]
        #This defaults all missing arguments to false, which is perhaps not
        #quite right
        args = [bool(form.getfirst(value)) for value in algorithm_options]
        sys.stderr.write(repr(args) + "\n")
        self.heading_matcher = headings_module.HeadingMatcher(*args)
        
        data = self._get_data()
        out_template = MarkupTemplate(open(self.template_filename))
        stream = out_template.generate(data=data)
        return stream.render('html', doctype=("html", "", ""))

    def _get_data(self):
        annotator = TableAnnotator(self.heading_matcher)
        data = [annotator.annotate(table, str(i)) for i, table in enumerate(self.tables)]
        return data

def main():
    environ = os.environ.copy()
    environ["cgi_storage"] = cgi.FieldStorage()

    #Check for the correct types of HTTP request
    if environ["REQUEST_METHOD"] not in ("GET", "POST", "HEAD"):
        response = MethodNotAllowed(environ)
        response.send()
        sys.exit(1)
    
    try:
        response = TableHeadersResponse(environ)
    except InspectorException, e:
        if hasattr(e, "type"):
            environ["error_type"] = e.type 
        else:
            environ["error_type"] = "UNKNOWN_ERROR"
        sys.stderr.write(repr(e.__dict__))
        response = Error(environ)
    except:
        raise
    response.send()


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = trackerlib
# Make sure we have a module for doing shell scripts and one for simple web forms.
import os
import cgi
import re

# This function can probably be beautified
def parseRawLog(svnLog):
    """Parses a raw svn log.

    Returns a list with entries, each list item containing a dictionary with
    two keys; info (string) and changes (list)
    """
    logList = cgi.escape(svnLog.read()).splitlines()
    entries = []
    current = 0
    separator = "-" * 72
    for i, line in enumerate(logList):
        if line != separator:
            # After the separator comes the log info
            if logList[i - 1] == separator:
                entries.append({"info": line, "changes": []})
            elif line:
                entries[current]["changes"].append(line)

            # If next list item is a separator, there are no more changes
            if logList[i + 1] == separator:
                current += 1
    return entries


def parseLogLine(logInfo):
    mapping = {
        "e": "editorial",
        "a": "authors",
        "c": "conformance-checkers",
        "g": "gecko",
        "i": "internet-explorer",
        "o": "opera",
        "w": "webkit",
        "r": "google-gears",
        "t": "tools",
        "0": "draft-content",
        "1": "stable-draft",
        "2": "implemented",
        "3": "stable"
        }
    changes = []
    classes = []
    bug = None
    for line in logInfo:
        if line.startswith("Fixing http://www.w3.org/Bugs/Public/show_bug.cgi?id="):
            bug = line[53:]
        elif line.startswith("["):
            for c in line:
                if c in mapping:
                    classes.append(mapping[c])
                if c == "]":
                    if (not classes) or (len(classes) == 1 and classes[0] == "editorial"):
                        classes.append("none")
                if c == ")":
                    break
            changes.append(line.split(") ", 1)[-1])
        else:
            changes.append(line)
    return {"changes": changes, "classes": classes, "bug": bug}


def getRevisionData(revision):
    revInfo = revision["info"] # This is the info line for a revision
    revChanges = parseLogLine(revision["changes"]) # Changes for the revision

    iconClasses = ["authors", "conformance-checkers", "gecko", "internet-explorer", "opera", "webkit", "google-gears", "tools"]
    titleClasses = ["editorial", "draft-content", "stable-draft", "implemented", "stable"]

    # Get the revision number
    number = getNumber(revInfo, 1)
    # Get the revision date and chop off the seconds and time zone
    date = re.split(" \(", re.split(" \| ", revInfo)[2])[0][:16]

    # Get stuff from the changes line(s)
    # TODO: fix the classAttr and titleAttr to only return if non-empty
    classAttr = " class=\"%s\"" % " ".join(revChanges["classes"])
    titleAttr = " title=\"%s\"" % ", ".join([title.replace("-", " ").title() for title in revChanges["classes"] if title in titleClasses])
    icons = "".join([("<img src=\"icons/%s\" alt=\"[%s]\"> ") % (class_, class_.replace("-", " ").title()) for class_ in revChanges["classes"] if class_ in iconClasses])
    changes = "<br>".join(revChanges["changes"])

    # TODO: Implement the source stuff to work with links
    link = "?from=%s&amp;to=%s" % (str(toInt(number) - 1), number)

    bug = ""
    if revChanges["bug"]:
        bug = "<a href=\"http://www.w3.org/Bugs/Public/show_bug.cgi?id=" + revChanges["bug"] + "\">" + revChanges["bug"] + "</a>"

    return {
        "number": number,
        "link": link,
        "classAttr": classAttr,
        "titleAttr": titleAttr,
        "icons": icons,
        "changes": changes,
        "date": date,
        "bug" : bug
        }


def formatLog(logList):
    output = ""
    if logList:
        output += "<table id=\"log\">\n   <tr>" \
            "<th>SVN</th>" \
            "<th>Bug</th>" \
            "<th>Comment</th>" \
            "<th>Time (UTC)</th></tr>"
        for revision in logList:
            revData = getRevisionData(revision)
            output += "\n   <tr%(classAttr)s%(titleAttr)s>" \
                "<td>%(number)s</td>" \
                "<td>%(bug)s</td>" \
                "<td><a href=\"%(link)s\">%(icons)s%(changes)s</a></td>" \
                "<td>%(date)s</td></tr>" % revData
        output += "\n  </table>"
    return output


def formatDiff(diff):
    """Takes a svn diff and marks it up with elements for styling purposes

    Returns a formatted diff
    """
    diff = diff.splitlines()
    diffList = []

    def formatLine(line):
        format = "<samp class=\"%s\">%s</samp>"
        formattingTypes = {"+": "addition", "-": "deletion", "@": "line-info"}
        diffType = line[0]
        if diffType in formattingTypes.keys():
            diffList.append(format % (formattingTypes[diffType], line))
        else:
            diffList.append("<samp>%s</samp>" % line)

    for line in diff:
        formatLine(line)

    return "\n".join(diffList)

def getDiffCommand(source, revFrom, revTo):
    command = "svn diff -r %s%s %s"
    if revTo:
        return command % (revFrom, ":%s" % revTo, source)
    else:
        return command % (revFrom, "", source)

def getLogCommand(source, revFrom, revTo):
    revFrom += 1
    return "svn log %s -r %s:%s" % (source, revFrom, revTo)

def getDiff(source, revFrom, revTo, identifier):
    if identifier == "":
        identifier = "html5"
    filename = identifier + "-" + str(revFrom) + "-" + str(revTo)

    # Specialcase revTo 0 so future revFrom=c&revTo=0 still show the latest
    if revTo != 0 and os.path.exists("diffs/" + filename):
        return open("diffs/" + filename, "r").read()
    else:
        diff = cgi.escape(os.popen(getDiffCommand(source, revFrom, revTo)).read())
        if not diff:
            return diff

        # Specialcase revTo 0 so future revFrom=c&revTo=0 still show the
        # latest
        if revTo == 0:
            filename = identifier + "-" + str(revFrom) + "-" + str(getNumber(diff, 2))

            # Return early if we already have this diff stored
            if os.path.exists("diffs/" + filename):
                return diff

        # Store the diff
        if not os.path.isdir("diffs"):
            os.mkdir("diffs")
        file = open("diffs/" + filename, "w")
        file.write(diff)
        file.close()
        return diff

def getNumber(s, n):
    return int(re.split("\D+", s)[n])


def toInt(s):
    return int(float(s))


def startFormatting(title, identifier, url, source):
    document = """Content-Type:text/html;charset=UTF-8

<!doctype html>
<html lang=en>
 <head>
  <title>%s Tracker</title>
  <style>
   html { background:#fff; color:#000; font:1em/1 Arial, sans-serif }
   form { margin:1em 0; font-size:.7em }
   fieldset { margin:0; padding:0; border:0 }
   legend { padding:0; font-weight:bold }
   input[type=number] { width:4.5em }
   table { border-collapse:collapse }
   table td { padding:.1em .5em }
   table td:last-child { white-space:nowrap }
   img { font-size:xx-small }

   .draft-content { background-color:#eee }
   .stable-draft { background-color:#fcc }
   .implemented { background-color:#f99 }
   .stable { background-color:#f66 }
   body .editorial { color:gray }

   :link { background:transparent; color:#00f }
   :visited { background:transparent; color:#066 }
   img { border:0; vertical-align:middle }

   td :link { color:inherit }
   td a { text-decoration:none; display:block }
   td a:hover { text-decoration:underline }

   .editorial tr.editorial { display:none }

   pre { display:table; white-space:normal }
   samp samp { margin:0; display:block; white-space:pre }
   .deletion { background:#fdd; color:#900 }
   .addition { background:#dfd; color:#000 }
   .line-info { background:#eee; color:#000 }
  </style>
  <script>
   function setCookie(name,value) { localStorage["tracker%s-" + name] = value }
   function readCookie(name) { return localStorage["tracker%s-" + name] }
   function setFieldValue(idName, n) { document.getElementById(idName).value = n }
   function getFieldValue(idName) { return document.getElementById(idName).value }
   function setFrom(n) {
     setCookie("from", n)
     setFieldValue("from", n)
     setFieldValue("to", "")
   }

   function showEdits() { return document.getElementById("editorial").checked }
   function updateEditorial() {
     var editorial = showEdits() ? "" : "editorial"
     setCookie("editorial", editorial)
     document.body.className = editorial
   }
  </script>
 </head>
 <body>
  <h1>%s</h1>
  <form>
   <fieldset>
    <legend>Diff</legend>
    <label>From: <input id=from type=number min=1 value="%s" name=from required></label>
    <label>To: <input id=to type=number min=0 value="%s" name=to></label> (omit for latest revision)
    <input type=submit value="Generate diff">
   </fieldset>
  </form>
  <form>
   <fieldset>
    <legend>Filter</legend>
    <label class="editorial">Show editorial changes <input type="checkbox" id="editorial" checked="" onchange="updateEditorial()"></label>
   </fieldset>
  </form>
  <script>
   if(getFieldValue("from") == "" && readCookie("from") != null)
     setFrom(readCookie("from"))
   if(readCookie("editorial") == "editorial") {
     document.getElementById("editorial").checked = false
     updateEditorial()
   }
  </script>
  %s
 </body>
</html>"""
    showDiff = False
    revFrom = 290 # basically ignored, but sometimes a useful fiction for debugging
    revTo = 0
    os.environ["TZ"] = "" # Set time zone to UTC. Kinda hacky, but works :-)
    form = cgi.FieldStorage()

    if "from" in form:
        try:
            revFrom = toInt(form["from"].value)
            showDiff = True
        except:
            pass

    if showDiff and "to" in form:
        try:
            revTo = toInt(form["to"].value)
            if 0 < revTo < revFrom:
                revFrom, revTo = revTo, revFrom
        except:
            pass

    # Put it on the screen
    if not showDiff:
        #
        # HOME
        #
        if "limit" in form and form["limit"].value == "-1":
            limit = ""
        else:
            limit = " --limit 100"
            try:
                limit = " --limit %s" % toInt(form["limit"].value)
            except:
                pass
        svnLog = os.popen("svn log %s%s" % (source, limit))
        parsedLog = parseRawLog(svnLog)
        formattedLog = formatLog(parsedLog)
        print document % (title, identifier, identifier, title + " Tracker", "", "", formattedLog)
    else:
        #
        # DIFF
        #
        diff = formatDiff(getDiff(source, revFrom, revTo, identifier))
        markuptitle = "<a href=" + url + ">" + title + " Tracker" + "</a>"
        try:
            # This fails if there is no diff -- hack
            revTo = getNumber(diff, 2)
            svnLog = os.popen(getLogCommand(source, revFrom, revTo))
            parsedLog = parseRawLog(svnLog)
            formattedLog = formatLog(parsedLog)
            result = """%s
  <pre id="diff"><samp>%s</samp></pre>
  <p><a href="?from=%s&amp;to=%s" rel=prev>Previous</a> | <a href="?from=%s&amp;to=%s" rel=next>Next</a>
  <p><input type="button" value="Prefill From field for next time!" onclick="setFrom(%s)">""" % (formattedLog, diff, revFrom-1, revFrom, revTo, revTo+1, revTo)

            # Short URL
            shorturlmarkup = ""
            if title == "HTML5":
                shorturl = "http://html5.org/r/"
                if revTo - revFrom == 1:
                    shorturl += str(revTo)
                else:
                    shorturl += str(revFrom) + "-" + str(revTo)
                shorturlmarkup = """<p>Short URL: <code><a href="%s">%s</a></code>\n  """ % (shorturl, shorturl)
            shorturlmarkup += result
            print document % (title, identifier, identifier, markuptitle, revFrom, revTo, shorturlmarkup)
        except:
            print document % (title, identifier, identifier, markuptitle, revFrom, "", "No result.")

########NEW FILE########
