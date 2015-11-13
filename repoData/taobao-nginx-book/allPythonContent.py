__FILENAME__ = basic
# -*- coding: utf-8 -*-
import sphinx

def setup(app):
    app.add_javascript('booktools.js')
########NEW FILE########
__FILENAME__ = block
# -*- coding: utf-8 -*-
from sphinx.util.compat import Directive
import shutil
import pdb
import os.path as path
from docutils.parsers.rst import directives
from docutils import nodes

def build_finished(app, ex):
    if app.builder.name == "latex":
        import glob
        curpath = path.split(__file__)[0]
        for fn in glob.glob(path.join(curpath, "latexstyle", "*.*")):
            print "copy %s" % fn
            shutil.copy(fn, path.join(app.builder.outdir, path.split(fn)[-1]))

class timgblock(nodes.Part, nodes.Element):
    pass

def latex_visit_timgblock(self, node):
    text = r"""
\framebox[1.0 \textwidth]{
\includegraphics[width=2.5em]{%(image)s.pdf}
\raisebox{1.0em}{\parbox{0.9 \textwidth}{\small
    """
    self.body.append( text % node)
    self.context.append("}}}")

def latex_depart_timgblock(self, node):
    self.body.append(self.context.pop())

def html_visit_timgblock(self, node):
    text = r"""<div class="imagebox" style="background-image: url(_static/%(image)s.png)">"""
    self.body.append(text % node)
    self.context.append("</div>")
    
def html_depart_timgblock(self, node):
    self.body.append(self.context.pop())

def empty_visit(self, node):
    raise nodes.SkipNode
    
class ImageBlockDirective(Directive):
    has_content = True
    required_arguments = 0
    optional_arguments = 2
    final_argument_whitespace = True
    option_spec = {
        'text': directives.unchanged
    }
    image = ""

    def run(self):
        node = timgblock()
        node["image"] = self.image
        if self.arguments and self.arguments[0]:
            node['argument'] = u" ".join(self.arguments)        
        self.state.nested_parse(self.content, self.content_offset, node)
        ret = [node]
        return ret    
    
def MakeFileDirective(imgname):
    #curpath = path.split(__file__)[0]
    #shutil.copy(path.join(curpath, imgname + ".pdf"), path.join(curpath, "..\\..\\build\\latex"))
    return type(imgname+"Directive",(ImageBlockDirective,),{"image":imgname})

def setup(app):
    #pdb.set_trace()
    app.add_node(timgblock, 
        latex=(latex_visit_timgblock, latex_depart_timgblock),
        text=(empty_visit, None), 
        html=(html_visit_timgblock, html_depart_timgblock))
    app.add_directive('tcode', MakeFileDirective("code"))
    app.add_directive('tanim', MakeFileDirective("anim"))
    app.add_directive('twarning', MakeFileDirective("warning"))
    app.add_directive('tlink', MakeFileDirective("link"))
    app.add_directive('ttip', MakeFileDirective("tip"))
    app.add_directive('tthink', MakeFileDirective("think"))
    app.connect("build-finished", build_finished)
########NEW FILE########
__FILENAME__ = chinese_search
# -*- coding: utf-8 -*- 

def setup(app): 
    import sphinx.search as search
    import zh
    search.languages["zh_CN"] = zh.SearchChinese
########NEW FILE########
__FILENAME__ = code_question
# -*- coding: utf-8 -*-
from docutils import nodes
import sphinx.writers.latex as latex
import sphinx.writers.html as html

def replace_latex_question_mark(t):
    return t.replace(r"\PYGZsh{}\textless{}?\textgreater{}", u"\\large{【你的程序】}")
       
def replace_html_question_mark(t):
    return t.replace("#&lt;?&gt;", u'<span style="font-size:16px;font-weight:bold;">【你的程序】</span>')
    
def setup(app):
    print "code question loaded"
    old_depart_literal_block = latex.LaTeXTranslator.depart_literal_block
    def depart_literal_block(self, node):
        old_depart_literal_block(self, node)
        self.body[-1] = replace_latex_question_mark(self.body[-1])
    latex.LaTeXTranslator.depart_literal_block = depart_literal_block
    latex.LaTeXTranslator.depart_doctest_block = depart_literal_block
       
    old_visit_literal_block = html.HTMLTranslator.visit_literal_block
    def visit_literal_block(self, node):
        try:
            old_visit_literal_block(self, node)
        finally:
            self.body[-1] = replace_html_question_mark(self.body[-1])
            
    html.HTMLTranslator.visit_literal_block = visit_literal_block
    html.HTMLTranslator.visit_doctest_block = visit_literal_block
########NEW FILE########
__FILENAME__ = html_figref
# -*- coding: utf-8 -*-
from docutils import nodes
import sphinx.writers.html as html
import pdb

def setup(app):
    old_visit_reference = html.HTMLTranslator.visit_reference
    def visit_reference(self, node):
        if node.get('refid','').startswith("fig-"):
            text = node.children[0].children[0].astext()
            node.children[0].children[0] = nodes.Text(u"【图:%s】" % text)
        old_visit_reference(self, node)
    html.HTMLTranslator.visit_reference = visit_reference
########NEW FILE########
__FILENAME__ = image
# -*- coding: utf-8 -*-  
import os.path as path
import os
from docutils import nodes
from glob import glob
import imghdr
from sphinx.environment import BuildEnvironment
from docutils.utils import relative_path
from sphinx.builders.latex import LaTeXBuilder
from sphinx.builders.html import StandaloneHTMLBuilder
def process_images(self, docname, doctree):
    """
    Process and rewrite image URIs.
    """
    docdir = path.dirname(self.doc2path(docname, base=None))
    for node in doctree.traverse(nodes.image):
        # Map the mimetype to the corresponding image.  The writer may
        # choose the best image from these candidates.  The special key * is
        # set if there is only single candidate to be used by a writer.
        # The special key ? is set for nonlocal URIs.
        node['candidates'] = candidates = {}
        imguri = node['uri']
        if imguri.find('://') != -1:
            self.warn(docname, 'nonlocal image URI found: %s' % imguri,
                      node.line)
            candidates['?'] = imguri
            continue
        # imgpath is the image path *from srcdir*
        if imguri.startswith('/') or imguri.startswith(os.sep):
            # absolute path (= relative to srcdir)
            imgpath = path.normpath(imguri[1:])
        else:
            imgpath = path.normpath(path.join(docdir, imguri))
        # set imgpath as default URI
        node['uri'] = imgpath
        if imgpath.endswith(os.extsep + '*'):
            for filename in glob(path.join(self.srcdir, imgpath)):
                new_imgpath = relative_path(self.srcdir, filename)
                if filename.lower().endswith('.pdf'):
                    candidates['application/pdf'] = new_imgpath
                elif filename.lower().endswith('.svg'):
                    candidates['image/svg+xml'] = new_imgpath
                elif ".latex." in filename.lower():
                    candidates['latex'] = new_imgpath
                elif ".html." in filename.lower():
                    candidates['html'] = new_imgpath
                else:
                    try:
                        f = open(filename, 'rb')
                        try:
                            imgtype = imghdr.what(f)
                        finally:
                            f.close()
                    except (OSError, IOError), err:
                        self.warn(docname, 'image file %s not '
                                  'readable: %s' % (filename, err),
                                  node.line)
                    if imgtype:
                        candidates['image/' + imgtype] = new_imgpath
        else:
            candidates['*'] = imgpath
        # map image paths to unique image names (so that they can be put
        # into a single directory)
        for imgpath in candidates.itervalues():
            self.dependencies.setdefault(docname, set()).add(imgpath)
            if not os.access(path.join(self.srcdir, imgpath), os.R_OK):
                self.warn(docname, 'image file not readable: %s' % imgpath,
                          node.line)
                continue
            self.images.add_file(docname, imgpath)
 
from sphinx.util import url_re, get_matching_docs, docname_join, \
     FilenameUniqDict          

def add_file(self, docname, newfile):
    if newfile in self:
        self[newfile][0].add(docname)
        return self[newfile][1]
    uniquename = path.basename(newfile)
    self[newfile] = (set([docname]), uniquename)
    self._existing.add(uniquename)
    return uniquename

def setup(app):
    FilenameUniqDict.add_file = add_file
    BuildEnvironment.process_images = process_images
    LaTeXBuilder.supported_image_types.insert(0, "latex")
    StandaloneHTMLBuilder.supported_image_types.insert(0, "html")

########NEW FILE########
__FILENAME__ = latex_fix
# -*- coding: utf-8 -*-
from docutils import nodes
import sphinx.writers.latex as latex

def setup(app):
    latex.LaTeXTranslator.default_elements["babel"] = '\\usepackage[english]{babel}'
    #latex.LaTeXTranslator.default_elements["inputenc"] = ''    
    
########NEW FILE########
__FILENAME__ = literal_include
# -*- coding: utf-8 -*-
import os
import os.path as path
import codecs
from docutils.parsers.rst import directives
from docutils import nodes
import sphinx.directives.code as code
import re
from sphinx.util import parselinenos

from number_label import CircleNumbers

def replace_number_label(text):
    def f(mo):
        return u"#"+CircleNumbers[int(mo.group(1))-1]
    return re.sub(r"#{(\d+)}", f, text)

def run(self):
    document = self.state.document
    filename = self.arguments[0]
    #print filename
    if not document.settings.file_insertion_enabled:
        return [document.reporter.warning('File insertion disabled',
                                          line=self.lineno)]
    env = document.settings.env
    if filename.startswith('/') or filename.startswith(os.sep):
        rel_fn = filename[1:]
    else:
        docdir = path.dirname(env.doc2path(env.docname, base=None))
        rel_fn = path.normpath(path.join(docdir, filename))
    fn = path.join(env.srcdir, rel_fn)

    if 'pyobject' in self.options and 'lines' in self.options:
        return [document.reporter.warning(
            'Cannot use both "pyobject" and "lines" options',
            line=self.lineno)]

    encoding = self.options.get('encoding', env.config.source_encoding)
    try:
        f = codecs.open(fn, 'rU', encoding)
        lines = f.readlines()
        f.close()
        # 去掉编码指示
        if fn.endswith(".py") and lines[0].startswith("#") and "coding" in lines[0]:
            lines = lines[1:]
        # 去掉文档说明
        if fn.endswith(".py"):
            if lines[0].startswith('"""'):
                for lineno, line in enumerate(lines[1:]):
                    if line.strip().endswith('"""'):
                        lines = lines[lineno+2:]
                        break
        # 去掉每行末尾空格
        for i in xrange(len(lines)):
            lines[i] = lines[i].rstrip() + "\n"
        
    except (IOError, OSError):
        return [document.reporter.warning(
            'Include file %r not found or reading it failed' % filename,
            line=self.lineno)]
    except UnicodeError:
        return [document.reporter.warning(
            'Encoding %r used for reading included file %r seems to '
            'be wrong, try giving an :encoding: option' %
            (encoding, filename))]

    objectname = self.options.get('pyobject')
    if objectname is not None:
        from sphinx.pycode import ModuleAnalyzer
        analyzer = ModuleAnalyzer.for_file(fn, '')
        tags = analyzer.find_tags()
        if objectname not in tags:
            return [document.reporter.warning(
                'Object named %r not found in include file %r' %
                (objectname, filename), line=self.lineno)]
        else:
            lines = lines[tags[objectname][1]-1 : tags[objectname][2]-1]

    linespec = self.options.get('lines')
    if linespec is not None:
        try:
            linelist = parselinenos(linespec, len(lines))
        except ValueError, err:
            return [document.reporter.warning(str(err), line=self.lineno)]
        lines = [lines[i] for i in linelist]

    startafter = self.options.get('start-after')
    endbefore = self.options.get('end-before')
    if startafter is not None or endbefore is not None:
        use = not startafter
        res = []
        for line in lines:
            if not use and startafter in line:
                use = True
            elif use and endbefore in line:
                use = False
                break
            elif use:
                res.append(line)
        lines = res
        
    section = self.options.get("section")
    if section is not None:
        section = "###%s###" % section
        print section
        use = False
        res = []
        for line in lines:
            if not use and section in line:
                use = True
                continue
            elif use and section in line:
                use = False
                break
            if use:
                res.append(line)
        lines = res
        indent = len(lines[0]) - len(lines[0].lstrip())
        for i,line in enumerate(lines):
            lines[i] = line[indent:]
      
    text = replace_number_label(''.join(lines))
    text = re.sub(r"(?s)#<\?(.*?)>.+?#<\?/>", lambda mo:u"#<?>%s" % mo.group(1), text)
    #text = (u"#程序文件:%s\n" % filename) + text
    retnode = nodes.literal_block(text, text, source=fn)
    retnode.line = 1
    if self.options.get('language', ''):
        retnode['language'] = self.options['language']
    if 'linenos' in self.options:
        retnode['linenos'] = True
    document.settings.env.note_dependency(rel_fn)
    #print "LiteralInclude hacked"
    return [retnode]    

def setup(app):
    code.LiteralInclude.option_spec["section"] = directives.unchanged_required
    code.LiteralInclude.run = run
########NEW FILE########
__FILENAME__ = nohighlight
from sphinx import highlighting
def highlight_block(self, source, lang, linenos=False, warn=None):
    return self.unhighlighted(source)
highlighting.PygmentsBridge.highlight_block = highlight_block
########NEW FILE########
__FILENAME__ = number_label
# -*- coding: utf-8 -*-
from docutils import nodes
import sphinx.writers.latex as latex
import sphinx.writers.html as html

CircleNumbers = u"❶❷❸❹❺❻❼❽❾❿"

def replace_latex_code_labels(t):
    for i, n in enumerate(CircleNumbers):
        target = r"{\normalsize\ding{%s}}" % (202+i)
        target2 = r"[@normalsize@ding[%s]]" % (202+i)
        t = t.replace(r"\PYG{c}{\PYGZsh{}%s}" % n, target)
        t = t.replace(r"\PYG{c}{\#%s}" % n, target)
        t = t.replace(r"@#%s" % n, target2)
    return t
    
def replace_latex_text_labels(t):
    for i, n in enumerate(CircleNumbers):
        t = t.replace(n, r"{\Large\ding{%s}}\hspace{1mm}" % (202+i))
    return t
    
def replace_html_code_labels(t):
    for i, n in enumerate(CircleNumbers):
        target = '<span class="prebc">#</span><span class="codenumber">%s</span>' % n
        t = t.replace("#%s" % n, target).replace("#{%d}" % (i+1), target).replace("#{{%d}}" % (i+1), "#{%d}" % (i+1))
    return t
    
def setup(app):
    print "number_label loaded"
    old_depart_literal_block = latex.LaTeXTranslator.depart_literal_block
    def depart_literal_block(self, node):
        old_depart_literal_block(self, node)
        self.body[-1] = replace_latex_code_labels(self.body[-1])
    latex.LaTeXTranslator.depart_literal_block = depart_literal_block
    latex.LaTeXTranslator.depart_doctest_block = depart_literal_block
    
    old_visit_Text = latex.LaTeXTranslator.visit_Text
    def visit_Text(self, node):
        old_visit_Text(self, node)
        self.body[-1] = replace_latex_text_labels(self.body[-1])
    latex.LaTeXTranslator.visit_Text = visit_Text
    
    old_visit_literal_block = html.HTMLTranslator.visit_literal_block
    def visit_literal_block(self, node):
        try:
            old_visit_literal_block(self, node)
        finally:
            self.body[-1] = replace_html_code_labels(self.body[-1])
            
    html.HTMLTranslator.visit_literal_block = visit_literal_block
    html.HTMLTranslator.visit_doctest_block = visit_literal_block
########NEW FILE########
__FILENAME__ = number_ref
# -*- coding: utf-8 -*-
from docutils import nodes
import sphinx.writers.latex as latex
from sphinx.util.nodes import clean_astext
import pdb
def doctree_resolved(app, doctree, docname):
    """将带sec-开头的target标签名添加到标签的父节点之上
    这样就可以在section节点之下定义章节的标签。便于用
    leo的auto-rst功能编辑rst文档。
    
    例如：
    
    章节名称
    --------
    
    .. _sec-test:

    章节内容
    """
    for node in doctree.traverse(nodes.target):
        if node.get("refid", "").startswith("sec-"):
            section = node.parent
            section["ids"].append(node["refid"])
            node["refid"] = "-" + node["refid"]

def doctree_read(app, doctree):
    """
    为了sec-开头标签能正常工作需要将其添加进：
    env.domains["std"].data["labels"]
    sec-test: 文章名, 标签名, 章节名，
    """
    labels = app.env.domains["std"].data["labels"]
    for name, _ in doctree.nametypes.iteritems():
        if not name.startswith("sec-"): continue
        labelid = doctree.nameids[name]
        node = doctree.ids[labelid].parent
        if node.tagname == 'section':
            sectname = clean_astext(node[0])
            labels[name] = app.env.docname, labelid, sectname
            
def setup(app):
    print "number_ref loaded"
    old_visit_reference = latex.LaTeXTranslator.visit_reference
    def visit_reference(self, node):
        uri = node.get('refuri', '')
        hashindex = uri.find('#')
        if hashindex == -1:
            id = uri[1:] + '::doc'
        else:
            id = uri[1:].replace('#', ':')
        if uri.startswith("%") and "#fig-" in uri:
            self.body.append(self.hyperlink(id))
            self.body.append(u"图\\ref*{%s}" % id)
            self.context.append("}}")
            raise nodes.SkipChildren
        elif uri.startswith("%") and "#sec-" in uri:
            self.body.append(self.hyperlink(id))
            self.body.append(u"第\\ref*{%s}节" % id)
            self.context.append("}}")
            raise nodes.SkipChildren        
        else:
            return old_visit_reference(self, node)
    latex.LaTeXTranslator.visit_reference = visit_reference
    
    app.connect("doctree-read", doctree_read)
    app.connect("doctree-resolved", doctree_resolved)
########NEW FILE########
__FILENAME__ = smallseg
# -*- coding: utf-8 -*-
import re
import os
import sys
class SEG(object):
    def __init__(self):
        _localDir=os.path.dirname(__file__)
        _curpath=os.path.normpath(os.path.join(os.getcwd(),_localDir))
        curpath=_curpath
        self.d = {}
        print >> sys.stderr,"loading dict..."
        self.set([x.rstrip() for x in file(os.path.join(curpath,"main.dic")) ])
        self.specialwords= set([x.rstrip().decode('utf-8') for x in file(os.path.join(curpath,"suffix.dic"))])
        print >> sys.stderr,'dict ok.'
    #set dictionary(a list)
    def set(self,keywords):
        p = self.d
        q = {}
        k = ''
        for word in keywords:
            word = (chr(11)+word).decode('utf-8')
            if len(word)>5:
                continue
            p = self.d
            ln = len(word)
            for i in xrange(ln-1,-1,-1):
                char = word[i].lower()
                if p=='':
                    q[k] = {}
                    p = q[k]
                if not (char in p):
                    p[char] = ''
                    q = p
                    k = char
                p = p[char]
        
        pass
    
    def _binary_seg(self,s):
        ln = len(s)
        if ln==1:
            return [s]
        R = []
        for i in xrange(ln,1,-1):
            tmp = s[i-2:i]
            R.append(tmp)
        return R
    
    def _pro_unreg(self,piece):
        #print piece
        R = []
        tmp = re.sub(u"。|，|,|！|…|!|《|》|<|>|\"|'|:|：|？|\?|、|\||“|”|‘|’|；|—|（|）|·|\(|\)|　"," ",piece).split()
        ln1 = len(tmp)
        for i in xrange(len(tmp)-1,-1,-1):
            mc = re.split(r"([0-9A-Za-z\-\+#@_\.]+)",tmp[i])
            for j in xrange(len(mc)-1,-1,-1):
                r = mc[j]
                if re.search(r"([0-9A-Za-z\-\+#@_\.]+)",r)!=None:
                    R.append(r)
                else:
                    R.extend(self._binary_seg(r))
        return R
        
        
    def cut(self,text):
        """
        """
        text = text.decode('utf-8','ignore')
        p = self.d
        ln = len(text)
        i = ln 
        j = 0
        z = ln
        q = 0
        recognised = []
        mem = None
        mem2 = None
        while i-j>0:
            t = text[i-j-1].lower()
            #print i,j,t,mem
            if not (t in p):
                if (mem!=None) or (mem2!=None):
                    if mem!=None:
                        i,j,z = mem
                        mem = None
                    elif mem2!=None:
                        delta = mem2[0]-i
                        if delta>=1:
                            if (delta<5) and (re.search(ur"[\w\u2E80-\u9FFF]",t)!=None):
                                pre = text[i-j]
                                #print pre
                                if not (pre in self.specialwords):
                                    i,j,z,q = mem2
                                    del recognised[q:]
                            mem2 = None
                            
                    p = self.d
                    if((i<ln) and (i<z)):
                        unreg_tmp = self._pro_unreg(text[i:z])
                        recognised.extend(unreg_tmp)
                    recognised.append(text[i-j:i])
                    #print text[i-j:i],mem2
                    i = i-j
                    z = i
                    j = 0
                    continue
                j = 0
                i -= 1
                p = self.d
                continue
            p = p[t]
            j+=1
            if chr(11) in p:
                if j<=2:
                    mem = i,j,z
                    #print text[i-1]
                    if (z-i<2) and (text[i-1] in self.specialwords) and ((mem2==None) or ((mem2!=None and mem2[0]-i>1))):
                        #print text[i-1]
                        mem = None
                        mem2 = i,j,z,len(recognised)
                        p = self.d
                        i -= 1
                        j = 0
                    continue
                    #print mem
                p = self.d
                #print i,j,z,text[i:z]
                if((i<ln) and (i<z)):
                    unreg_tmp = self._pro_unreg(text[i:z])
                    recognised.extend(unreg_tmp)
                recognised.append(text[i-j:i])
                i = i-j
                z = i
                j = 0
                mem = None
                mem2 = None
        #print mem
        if mem!=None:
            i,j,z = mem
            recognised.extend(self._pro_unreg(text[i:z]))
            recognised.append(text[i-j:i])        
        else:
            recognised.extend(self._pro_unreg(text[i-j:z]))
        return recognised
########NEW FILE########
__FILENAME__ = zh
# -*- coding: utf-8 -*-
from sphinx.search import SearchLanguage
from smallseg import SEG 

class SearchChinese(SearchLanguage):
    lang = 'zh'

    def init(self, options):
        print "reading Chiniese dictionary"
        self.seg = SEG() 

    def split(self, input):
        return self.seg.cut(input.encode("utf8")) 

    def word_filter(self, stemmed_word):
        return len(stemmed_word) > 1
########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# sphinxdoc documentation build configuration file, created by
# sphinx-quickstart on Tue Jul 19 09:39:30 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

_exts = "../exts"
TITLE = u"Nginx开发从入门到精通"

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
sys.path.append(os.path.abspath(_exts))
extensions = ['sphinx.ext.todo', 'sphinx.ext.pngmath', 'sphinx.ext.ifconfig', 'number_ref',
              'number_label', 'literal_include', 'block', 'image', 'basic', "latex_fix"]

#extensions.append('nohighlight')
extensions.append('chinese_search')

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Nginx开发从入门到精通'
copyright = u'2012, taobao'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1'
# The full version, including alpha/beta/rc tags.
release = '0.1'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
language = "zh_CN"

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = []

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'book'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = [_exts +"/theme"]

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = TITLE

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = "cover_sphinx.png"

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'nginx_bookdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'nginxbook.tex', TITLE,
   u'taobao server platform', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
latex_preamble = r"""
% \pdfpagewidth 195mm
% \pdfpageheight 271mm
% \textwidth 6.0in
% \textheight 8.8in
% \oddsidemargin -0.1in
% \evensidemargin -0.1in

\textwidth 6.8in
\oddsidemargin -0.2in
\evensidemargin -0.3in

\usepackage{pdfpages}
\usepackage[BoldFont,CJKchecksingle]{xeCJK}
\usepackage{float}
\usepackage{ccaption}
\usepackage{pifont}
% \usepackage{fancybox}
\usepackage{fontspec,xunicode,xltxtra}

\setsansfont{DejaVu Serif}
% \setromanfont{DejaVu Sans Mono}
\setmainfont{DejaVu Serif}
\setmonofont{DejaVu Sans Mono}

% \setsansfont{WenQuanYi Micro Hei Light}
% \setromanfont{WenQuanYi Micro Hei Light}
% \setmainfont{WenQuanYi Micro Hei Light}
% \setmonofont{WenQuanYi Micro Hei Mono Light}
% STXihei
\setCJKsansfont[BoldFont={SimSun},ItalicFont={SimSun}]{SimSun}
\setCJKromanfont[BoldFont={SimSun},ItalicFont={SimSun}]{SimSun}
\setCJKmainfont[BoldFont={SimSun},ItalicFont={SimSun}]{SimSun}
\setCJKmonofont[BoldFont={SimSun},ItalicFont={SimSun}]{SimSun}

% \setCJKsansfont{Microsoft YaHei}
% \setCJKromanfont{Microsoft YaHei}
% \setCJKmainfont{Microsoft YaHei}
% \setCJKmonofont{Microsoft YaHei}

% \CJKaddspaces\CJKsetecglue{\hskip 0.15em plus 0.05em minus 0.05em}

\XeTeXlinebreaklocale "zh"
\XeTeXlinebreakskip = 0pt plus 1pt
\renewcommand{\baselinestretch}{1.3} 
\setcounter{tocdepth}{3}
\captiontitlefont{\small\sffamily}
\captiondelim{ - }
\renewcommand\today{\number\year年\number\month月\number\day日}      
\makeatletter
\renewcommand*\l@subsection{\@dottedtocline{2}{2.0em}{4.0em}}
\renewcommand*\l@subsubsection{\@dottedtocline{3}{3em}{5em}}
\makeatother
\titleformat{\chapter}[display]
{\bfseries\Huge}
{\filleft \Huge 第 \hspace{2 mm} \thechapter \hspace{4 mm} 章}
{4ex}
{\titlerule
\vspace{1ex}%
\filright}
[\vspace{1ex}%
\titlerule]
%\definecolor{VerbatimBorderColor}{rgb}{0.2,0.2,0.2}
\definecolor{VerbatimColor}{rgb}{0.95,0.95,0.95}
""".decode("utf-8")

latex_elements = {
    "maketitle":ur"""
\maketitle
\renewcommand\contentsname{目 录}
\renewcommand\partname{部分} 
\renewcommand{\chaptermark}[1]{\markboth{\textnormal{第 \thechapter\ 章 \hspace{4mm} #1}}{}}
\renewcommand{\sectionmark}[1]{\markright{\textnormal{\thesection \hspace{2mm} #1}}{}}
\renewcommand{\figurename}{\textsc{图}}
\renewcommand{\tablename}{\textsc{表}}
\chapter*{前言}
\addcontentsline{toc}{chapter}{前言}
""",
    "tableofcontents":ur"""
\tableofcontents
\fancyhead[LE,RO]{%s}
""" % TITLE
}

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'Nginx开发从入门到精通', u'Nginx开发从入门到精通 Documentation',
     [u'taobao'], 1)
]


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = u'Nginx开发从入门到精通'
epub_author = u'taobao server platform'
epub_publisher = u'taobao'
epub_copyright = u'2012, taobao'

# The language of the text. It defaults to the language option
# or en if the language is not set.
#epub_language = ''

# The scheme of the identifier. Typical schemes are ISBN or URL.
#epub_scheme = ''

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#epub_identifier = ''

# A unique identification for the text.
#epub_uid = ''

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_post_files = []

# A list of files that should not be packed into the epub file.
#epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
#epub_tocdepth = 3

# Allow duplicate toc entries.
#epub_tocdup = True

########NEW FILE########
