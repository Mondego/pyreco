__FILENAME__ = gen_parsed_str_size_stats
#!/usr/bin/env python

# This script generates the info about sizes of various versions
# of ParsedStr class in a format suitable for including with
# optimization_story.textile

import sys, os.path, subprocess, string, re

SCRIPTDIR = os.path.realpath(sys.argv[0])
SCRIPTDIR = os.path.dirname(SCRIPTDIR)
SRCDIR = os.path.join(SCRIPTDIR, "..", "src")
TXTSRCDIR = os.path.join(SCRIPTDIR, "..", "txtsrc")
OBJDIR = os.path.join(SRCDIR, "obj-small")

def is_mac(): return sys.platform == 'darwin'
def is_win(): return sys.platform in ("win32", "cygwin")
def is_linux(): return sys.platform.startswith("linux") # on my Ubuntu it's "linux2"
def is_cygwin(): return sys.platform == "cygwin"

SYSTEM = "linux"
if is_mac():
    SYSTEM = "mac"
elif not is_linux():
    print("Not mac or linux. System is '%s'. Aborting." % sys.platform)
    sys.exit(1)

OUTFILEPATH = os.path.join(TXTSRCDIR, "parsedstr-size-stats-%s.html" % SYSTEM)

def log(txt):
    print txt,

# like cmdrun() but throws an exception on failure
def run_cmd_throw(*args):
    cmd = " ".join(args)
    log("Running '%s'\n" % cmd)
    cmdproc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    res = cmdproc.communicate()
    errcode = cmdproc.returncode
    if 0 != errcode:
        print "Failed with error code %d" % errcode
        print "Stdout:"
        print res[0]
        print "Stderr:"
        print res[1]
        raise Exception("'%s' failed with error code %d" % (cmd, errcode))
    return (res[0], res[1])

def cd(dir):
    log("cd to '%s'\n" % dir)
    os.chdir(dir)

# maps name of executable to user-readable name
FILES_TO_REPORT = ["parsed_str_dummy_stripped", "A no-op version", "parsed_str_opt_no_offsets_stripped", "Getting rid of offsets", "parsed_str_stl_stripped", "Naive STL version", "parsed_str_opt_alloc_stripped", "Optimizing allocations of strings",   "parsed_str_opt_offsets_stripped", "Offsets instead of pointers", "parsed_str_unopt_stripped", "Naive non-STL version", "parsed_str_opt_common_stripped", "Optimizing for common case", "parsed_str_opt_one_array_stripped", "One array instead of two", "parsed_str_opt_no_offsets_no_dup_stripped", "Avoiding copying the string"]

class FileInfo(object):
    def __init__(self, name, readablename, size):
        self.name = name
        self.readablename = readablename
        self.size = size
        self.size_vs_smallest = 0
        self.sizeof = 0

    def dump(self):
        print("name:     %s" % self.name)
        print("readable: %s" % self.readablename)
        print("size:     %d vs smallest: %d" % (self.size, self.size_vs_smallest))
        print("sizeof:   %d" % self.sizeof)

def write(path, data):
    fo = open(path, "wb")
    fo.write(data)
    fo.close()

def html_from_filesinfo(filesinfo):
    lines = []
    lines.append("<center>")
    lines.append("<table cellspacing=4>")
    lines.append("<tr>")
    lines.append("<th>Version</th>")
    lines.append("<th>File size</th>")
    lines.append("<th>File size delta</th>")
    lines.append("<th>sizeof(ParsedStr)</th>")
    lines.append("</tr>")
    for fi in filesinfo:
        lines.append("<tr>")
        lines.append("<td>%s</td>" % fi.readablename)
        lines.append("<td align=center>%d</td>" % fi.size)
        lines.append("<td align=center>%d</td>" % fi.size_vs_smallest)
        lines.append("<td align=center>%d</td>" % fi.sizeof)
        lines.append("</tr>")
    lines.append("<tr align=center bgcolor=#dedede><td colspan='4'><font size=-1>%s</font></td></tr>" % gcc_version())
    lines.append("</table>")
    lines.append("</center>")
    lines.append("")
    return string.join(lines, "\n")

def gcc_version():
    (stdout, stderr) = run_cmd_throw("gcc", "--version")
    lines = string.split(stdout, "\n")
    ver = lines[0].strip()
    return ver

def get_parsed_str_sizeof(exe):
    (stdout, stderr) = run_cmd_throw(exe)
    reg = "sizeof\(ParsedStr\)=(\d+)"
    regcomp = re.compile(reg, re.MULTILINE)
    m = regcomp.search(stdout)
    sizeoftxt = m.group(1)
    #print sizeoftxt
    return int(sizeoftxt)

def main():
    cd(SRCDIR)
    #run_cmd_throw("make", "rebuild")
    files = [os.path.join(OBJDIR, f) for f in os.listdir(OBJDIR)]
    filesinfo = []
    for filepath in files:
        filename = os.path.basename(filepath)
        if filename not in FILES_TO_REPORT:
            continue
        filesize = os.path.getsize(filepath)
        readablename = FILES_TO_REPORT[FILES_TO_REPORT.index(filename) + 1]
        fi = FileInfo(filename, readablename, filesize)
        fi.sizeof = get_parsed_str_sizeof(filepath)
        filesinfo.append(fi)
    filesinfo.sort(lambda x,y: cmp(x.size, y.size))
    smallest_size = filesinfo[0].size
    for fi in filesinfo:
        fi.size_vs_smallest = fi.size - smallest_size
    map(FileInfo.dump, filesinfo)
    html = html_from_filesinfo(filesinfo)
    #print html
    write(OUTFILEPATH, html)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = rebuild
#!/usr/bin/env python
import os.path
import sys
import string
import shutil
import textile

SCRIPT_DIR = os.path.dirname(__file__)
BASE_DIR = os.path.realpath(os.path.join(SCRIPT_DIR, ".."))
TXTSRCDIR = os.path.join(BASE_DIR, "txtsrc")
SRCDIR = os.path.join(BASE_DIR, "src")
OUTDIR = os.path.realpath(os.path.join(BASE_DIR, "..", "www", "extremeoptimizations"))
OUTSRCDIR = os.path.join(OUTDIR, "src")

def read(path):
    fo = open(path, "rb")
    d = fo.read()
    fo.close()
    return d

def write(path, data):
    fo = open(path, "wb")
    fo.write(data)
    fo.close()

g_header = None
def header():
    global g_header
    if g_header is None:
        g_header = read(os.path.join(TXTSRCDIR, "_header.html"))
    return g_header

g_footer = None
def footer():
    global g_footer
    if g_footer is None:
        g_footer = read(os.path.join(TXTSRCDIR, "_footer.html"))
    return g_footer

g_header_src = None
def headersrc():
    global g_header_src
    if g_header_src is None:
        g_header_src = read(os.path.join(TXTSRCDIR, "_header_src.html"))
    return g_header_src

g_footer_src = None
def footersrc():
    global g_footer_src
    if g_footer_src is None:
        g_footer_src = read(os.path.join(TXTSRCDIR, "_footer_src.html"))
    return g_footer_src

def dir_exists(path): return os.path.exists(path) and os.path.isdir(path)
def file_exists(path): return os.path.exists(path) and os.path.isfile(path)
def copy_file(src,dst): shutil.copy(src, dst)
def verify_dir_exists(path):
    if not dir_exists(path):
        txt = "dir '%s' doesn't exists" % path
        print(txt)
        raise Exception(txt)

def verify_file_exists(path):
    if not file_exists(path):
        txt = "file '%s' doesn't exists" % path
        print(txt)
        raise Exception(txt)

def ensure_dir(path):
    if not dir_exists(path):
        os.mkdir(path)

VALID_SUFFS = (".txt", ".textile")
def issrcfile(path):
    for suff in VALID_SUFFS:
        if path.endswith(suff):
            return True
    return False

def outfilename(path):
    base = os.path.basename(path)
    for suff in VALID_SUFFS:
        if base.endswith(suff):
            base = base.replace(suff, ".html")
            return os.path.join(OUTDIR, base)
    return None

def tmpfilename(path): return path + ".tmp"

def is_comment(line): return line.startswith("#")
def is_sep(line): return 0 == len(line.strip())
def is_key(line): return ':' in line
def is_includesrc(line): return line.startswith("@includesrc ")
def is_includetxt(line): return line.startswith("@includetxt ")

def readlines(filename, start, end):
    lines = []
    line_no = 1
    for l in open(filename, "rb"):
        if line_no > end:
            return string.join(lines, "")
        if line_no >= start:
            lines.append(l)
        line_no += 1
    return string.join(lines, "")

g_token = "asdflkasdfasdf:\n"
# A lame way to generate unique string that we can then string.replace()
# with destination text
def get_token():
    global g_token
    token = g_token
    g_token = g_token[:-2] + "a:\n"
    #print("Token: '%s'\n" % token)
    return token

# Returns a tuple (filename, filecontent)
def do_includesrc(line):
    parts = line.split(" ")
    if 4 != len(parts):
        txt = "Malformated @includesrc line:\n'%s'" % line
        print(txt)
        raise Exception(txt)
    filename = parts[1]
    startline = int(parts[2])
    endline = int(parts[3])
    filepath = os.path.join(SRCDIR, filename)
    verify_file_exists(filepath)
    txt = readlines(filepath, startline, endline)
    return (filepath, txt)

def do_includetxt(line, lines):
    parts = line.split(" ")
    if 2 != len(parts):
        txt = "Malformated @includetxt line:\n'%s'" % line
        print(txt)
        raise Exception(txt)
    filename = parts[1].strip()
    filepath = os.path.join(TXTSRCDIR, filename)
    txt = read(filepath)
    lines.append(txt)

g_do_tokens = True

# Generate sth. like this:
# "ParsedStrTest.cpp":src/ParsedStrTest.cpp.html ("raw":src/ParsedStrTest.cpp.txt):
def src_textile_link(basename):
    return '"%s":src/%s.html ("raw":src/%s.txt):' % (basename, basename, basename)

def src_html_link(basename):
    return "<a href='src/%s.html'>%s</a> (<a href='src/%s.txt'>raw</a>):" % (basename, basename, basename)

# Load a source *.textile file
# Returns (<txt>, <dict>) tuple, where <dict> is a dictionary of
# name/value pairs in the file and the <txt> is the rest of the file
def parse_textile(srcpath):
    (ST_START, ST_BODY) = range(2)
    keys = {}
    lines = []
    state = ST_START
    tokens = {}
    for l in open(srcpath, "rb"):
        if ST_START == state:
            if is_comment(l): continue
            if is_sep(l):
                state = ST_BODY
                continue
            if not is_key(l):
                print("Expected name: value line, got:\n'%s'" % l)
                raise Exception("Malformed file %s" % srcpath)
        if ST_BODY == state:
            if is_includesrc(l):
                (filepath, txt) = do_includesrc(l)
                token = get_token()
                tokens[token] = (filepath, txt)
                if g_do_tokens:
                    lines.append(token)
                else:
                    txt = "<pre><code>\n" + txt + "</code></pre>\n"
                    lines.append(txt)
            elif is_includetxt(l):
                do_includetxt(l, lines)
            else:
                lines.append(l)
    txt = string.join(lines, "")
    return (txt, tokens, keys)

def htmlify(text):
    text = text.replace("&","&amp;")
    text = text.replace("<","&lt;")
    text = text.replace(">","&gt;")
    return text

# Return a <code class=$x> where $x is a class name understood by highlight.js
# We auto-detect $x from file name.
def code_for_filename(filename):
    ext_to_classname = { 
        ".cpp" : "cpp",
        ".cc" : "cpp",
        ".h" : "cpp",
        ".c" : "cpp"}
    for ext in ext_to_classname.keys():
        if filename.endswith(ext):
            return '<code class="' + ext_to_classname[ext] + '">'
    return "<code>"

def dofile(srcpath):
    if not issrcfile(srcpath):
        print("Skipping '%s'" % srcpath)
        return
    dstpath = outfilename(srcpath)
    if dstpath is None:
        print("Ignoring file '%s'" % srcpath)
        return
    tmppath = tmpfilename(srcpath)
    (txt, tokens, keys) = parse_textile(srcpath)
    title = ""
    if "Title" in keys:
        title = keys["Title"]
    hdr = header()
    hdr = hdr.replace("$title", title)
    ftr = footer()        
    #write(tmppath, txt)
    html = textile.textile(txt)
    if g_do_tokens:
        #print tokens.keys()
        for token in tokens.keys():
            codetxt = tokens[token][1]
            filename = os.path.basename(tokens[token][0])
            c = code_for_filename(tokens[token][0])
            srclinktxt = src_html_link(filename)
            codehtml = srclinktxt + "\n<pre>" + c + "\n" + htmlify(codetxt) + "</code></pre>\n"
            token = token.strip()
            html = html.replace(token, codehtml)
    write(dstpath, hdr + html + ftr)

def issourcecodefile(path):
    for ext in [".cpp", ".cc", ".c", ".h", "makefile"]:
        if path.endswith(ext): return True
    return False

def dosrcfile(srcpath):
    if not issourcecodefile(srcpath):
        print("Skipping '%s'" % srcpath)
        return
    base = os.path.basename(srcpath)
    txtpath = os.path.join(OUTSRCDIR, base) + ".txt"
    htmlpath = os.path.join(OUTSRCDIR, base) + ".html"
    copy_file(srcpath, txtpath)
    hdr = headersrc()
    hdr = hdr.replace("$title", base)
    html = hdr + "<pre>" + code_for_filename(srcpath) + "\n" + htmlify(read(srcpath)) + "\n</code></pre>\n"
    html = html + footersrc()
    write(htmlpath, html)

def main():
    verify_dir_exists(TXTSRCDIR)
    verify_dir_exists(SRCDIR)
    verify_dir_exists(OUTDIR)
    ensure_dir(OUTSRCDIR)
    files = [os.path.join(TXTSRCDIR, f) for f in os.listdir(TXTSRCDIR)]
    map(dofile, [f for f in files if os.path.isfile(f)])
    files = [os.path.join(SRCDIR, f) for f in os.listdir(SRCDIR)]
    map(dosrcfile, [f for f in files if os.path.isfile(f)])

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = textile
#!/usr/bin/env python
# _*_ coding: latin1 _*_

"""This is Textile
A Humane Web Text Generator

TODO:
* Make it work with Python 2.1.
* Make it work with Python 1.5.2? Or that's too optimistic?

---
To get an overview of all PyTextile's features, simply
type 'tell me about textile.' in a single line.
"""

__authors__ = ["Roberto A. F. De Almeida (roberto@dealmeida.net)",
               "Mark Pilgrim (f8dy@diveintomark.org)"]
__version__ = "2.0.10"
__date__ = "2004/10/06"
__copyright__ = """
Copyright (c) 2004, Roberto A. F. De Almeida, http://dealmeida.net/
Copyright (c) 2003, Mark Pilgrim, http://diveintomark.org/
All rights reserved.

Original PHP version:
Version 1.0
21 Feb, 2003

Copyright (c) 2003, Dean Allen, www.textism.com
All rights reserved.

Parts of the documentation and some of the regular expressions are (c) Brad
Choate, http://bradchoate.com/. Thanks, Brad!
"""
__license__ = """
Redistribution and use in source and binary forms, with or without 
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, 
  this list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name Textile nor the names of its contributors may be used to
  endorse or promote products derived from this software without specific
  prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE 
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE 
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR 
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""
__history__ = """
1.0 - 2003/03/19 - MAP - initial release
1.01 - 2003/03/19 - MAP - don't strip whitespace within <pre> tags;
  map high-bit ASCII to HTML numeric entities
1.02 - 2003/03/19 - MAP - changed hyperlink qtag expression to only
  match valid URL characters (per RFC 2396); fixed preg_replace to
  not match across line breaks (solves lots of problems with
  mistakenly matching overlapping inline markup); fixed whitespace
  stripping to only strip whitespace from beginning and end of lines,
  not immediately before and after HTML tags.
1.03 - 2003/03/20 - MAP - changed hyperlink qtag again to more
  closely match original Textile (fixes problems with links
  immediately followed by punctuation -- somewhere Dean is
  grinning right now); handle curly apostrophe with "ve"
  contraction; clean up empty titles at end.
1.04 - 2003/03/23 - MAP - lstrip input to deal with extra spaces at
  beginning of first line; tweaked list loop to handle consecutive lists
1.1 - 2003/06/06 - MAP - created initial test suite for links and images,
  and fixed a bunch of related bugs to pass them
1.11 - 2003/07/20 - CL - don't demoronise unicode strings; handle
  "they're" properly
1.12 - 2003/07/23 - GW - print debug messages to stderr; handle bq(cite).
1.13 - 2003/07/23 - MAP - wrap bq. text in <p>...</p>
2 - 2004/03/26 - RAFA - rewritten from (almost) scratch to include
  all features from Textile 2 and a little bit more.
2.0.1 - 2004/04/02 - RAFA - Fixed validating function that uses uTidyLib.
2.0.2 - 2004/04/02 - RAFA - Fixed problem with caps letters in URLs.
2.0.3 - 2004/04/19 - RAFA - Multiple classes are allowed, thanks to Dave
  Anderson. The "lang" attribute is now removed from <code>, to be valid
  XHTML. Fixed <span class="caps">UCAS</span> problem.
2.0.4 - 2004/05/20 - RAFA, CLB - Added inline formatting to table cells.
  Curt Bergmann fixed a bug with the colspan formatting. Added Amazon
  Associated id.
2.0.5 - 2004/06/01 - CL - Applied patch from Chris Lawrence to (1) fix
  that Amazon associates ID was being added to all search URIs, (2)
  customize the Amazon site used with the AMAZON variable, and (3) added
  an "isbn" URI type that links directly to an Amazon product by ISBN or
  Amazon ASIN.
2.0.6 - 2004/06/02 - RAFA - Fixed CAPS problem, again. I hope this is
  the last time.
2.0.7 - 2004/06/04 - RAFA, MW - Fixed bullet macro, thanks to Adam
  Messinger. Added patch from Michal Wallace changing {}.pop() for
  compatibility with Python 2.2.x.
2.0.8 - 2004/06/25 - RAFA - Strip tags when adding the content from a
  footnote to the reference link. Escaped '<' and '>' in the self-
  generated documentation.
2.0.9 - 2004/10/04 - RAFA - In images, if ALT is not defined, add an
  empty attribute. Added "LaTeX" style open/close quotes. Fixed a bug 
  where the acronym definition was being formatted with inline rules. 
  Handle "broken" lines correctly, removing the <br /> from inside
  split HTML tags.
2.0.10 - 2004/10/06 - RAFA, LO - Escape all non-escaped ampersands.
  Applied "trivial patch" from Ludvig Omholt to remove newline right
  after the <pre> tag.
"""

# Set your encoding here.
ENCODING = 'latin-1'

# Output? Non-ASCII characters will be automatically
# converted to XML entities if you choose ASCII.
OUTPUT = 'ascii'

# PyTextile can optionally validate the generated
# XHTML code. We can use either mxTidy or uTidyLib.
# You can change the default behaviour here.
VALIDATE = 0

# If you want h1. to be translated to something other
# than <h1>, change this offset. You can also pass it
# as an argument to textile().
HEAD_OFFSET = 0

# If you want to use itex2mml, specify the full path
# to the binary here. You can download it from here:
# http://golem.ph.utexas.edu/~distler/blog/files/itexToMML.tar.gz
itex2mml = None
#itex2mml = '/usr/local/bin/itex2MML'
#itex2mml = '/usr/people/almeida/bin/itex2MML'

# PyTextile can optionally sanitize the generated XHTML,
# which is good for weblog comments or if you don't trust
# yourself.
SANITIZE = 0

# Turn debug on?
DEBUGLEVEL = 0

# Amazon associate for links: "keywords":amazon
# If you don't have one, please consider leaving mine here as
# a small compensation for writing PyTextile. It's commented
# off as default.
#amazon_associate_id = 'bomtempo-21'
amazon_associate_id = None 

#AMAZON = 'www.amazon.co.uk'
AMAZON = 'www.amazon.com'

import re
import sys
import os
import sgmllib
import unicodedata


def _in_tag(text, tag):
    """Extracts text from inside a tag.

    This function extracts the text from inside a given tag.
    It's useful to get the text between <body></body> or
    <pre></pre> when using the validators or the colorizer.
    """
    if text.count('<%s' % tag):
        text = text.split('<%s' % tag, 1)[1]
        if text.count('>'):
            text = text.split('>', 1)[1]
    if text.count('</%s' % tag):
        text = text.split('</%s' % tag, 1)[0]

    text = text.strip().replace('\r\n', '\n')

    return text


# If you want PyTextile to automatically colorize
# your Python code, you need the htmlizer module
# from Twisted. (You can just grab this file from
# the distribution, it has no other dependencies.)
try:
    #from twisted.python import htmlizer
    import htmlizer
    from StringIO import StringIO

    def _color(code):
        """Colorizer Python code.

        This function wraps a text string in a StringIO,
        and passes it to the htmlizer function from
        Twisted.
        """
        # Fix line continuations.
        code = preg_replace(r' \\\n', ' \\\\\n', code)
        
        code_in  = StringIO(code)
        code_out = StringIO()

        htmlizer.filter(code_in, code_out)

        # Remove <pre></pre> from input.
        code = _in_tag(code_out.getvalue(), 'pre')

        # Fix newlines.
        code = code.replace('<span class="py-src-newline">\n</span>', '<span class="py-src-newline"></span>\n')

        return code

except ImportError:
    htmlizer = None


# PyTextile can optionally validate the generated
# XHTML code using either mxTidy or uTidyLib.
try:
    # This is mxTidy.
    from mx.Tidy import Tidy
    
    def _tidy1(text):
        """mxTidy's XHTML validator.

        This function is a wrapper to mxTidy's validator.
        """
        nerrors, nwarnings, text, errortext = Tidy.tidy(text, output_xhtml=1, numeric_entities=1, wrap=0)
        return _in_tag(text, 'body')

    _tidy = _tidy1

except ImportError:
    try:
        # This is uTidyLib.
        import tidy

        def _tidy2(text):
            """uTidyLib's XHTML validator.

            This function is a wrapper to uTidyLib's validator.
            """
            text = tidy.parseString(text,  output_xhtml=1, add_xml_decl=0, indent=0, tidy_mark=0)
            return _in_tag(str(text), 'body')

        _tidy = _tidy2

    except ImportError:
        _tidy = None
    

# This is good for debugging.
def _debug(s, level=1):
    """Outputs debug information to sys.stderr.

    This function outputs debug information if DEBUGLEVEL is
    higher than a given treshold.
    """
    if DEBUGLEVEL >= level: print >> sys.stderr, s


#############################
# Useful regular expressions.
parameters = {
    # Horizontal alignment.
    'align':    r'''(?:(?:<>|[<>=])                 # Either '<>', '<', '>' or '='
                    (?![^\s]*(?:<>|[<>=])))         # Look-ahead to ensure it happens once
                 ''',

    # Horizontal padding.
    'padding':  r'''(?:[\(\)]+)                     # Any number of '(' and/or ')'
                 ''',

    # Class and/or id.
    'classid':  r'''(                               #
                        (?:\(\#[\w][\w\d\.:_-]*\))             # (#id)
                        |                           #
                        (?:\((?:[\w]+(?:\s[\w]+)*)  #
                            (?:\#[\w][\w\d\.:_-]*)?\))         # (class1 class2 ... classn#id) or (class1 class2 ... classn)
                    )                               #
                    (?![^\s]*(?:\([\w#]+\)))        # must happen once
                 ''',
           
    # Language.
    'lang':     r'''(?:\[[\w-]+\])                  # [lang]
                    (?![^\s]*(?:\[.*?\]))           # must happen once
                 ''',

    # Style.
    'style':    r'''(?:{[^\}]+})                    # {style}
                    (?![^\s]*(?:{.*?}))             # must happen once
                 ''',
}

res = {
    # Punctuation.
    'punct': r'''[\!"#\$%&'()\*\+,\-\./:;<=>\?@\[\\\]\^_`{\|}\~]''',
        
    # URL regular expression.
    'url':   r'''(?=[a-zA-Z0-9./#])                         # Must start correctly
                 (?:                                        # Match the leading part (proto://hostname, or just hostname)
                     (?:ftp|https?|telnet|nntp)             #     protocol
                     ://                                    #     ://
                     (?:                                    #     Optional 'username:password@'
                         \w+                                #         username
                         (?::\w+)?                          #         optional :password
                         @                                  #         @
                     )?                                     # 
                     [-\w]+(?:\.\w[-\w]*)+                  #     hostname (sub.example.com)
                 |                                          #
                     (?:mailto:)?                           #     Optional mailto:
                     [-\+\w]+                               #     username
                     \@                                     #     at
                     [-\w]+(?:\.\w[-\w]*)+                  #     hostname
                 |                                          #
                     (?:[a-z0-9](?:[-a-z0-9]*[a-z0-9])?\.)+ #     domain without protocol
                     (?:com\b                               #     TLD
                     |  edu\b                               #
                     |  biz\b                               #
                     |  gov\b                               #
                     |  in(?:t|fo)\b                        #     .int or .info
                     |  mil\b                               #
                     |  net\b                               #
                     |  org\b                               #
                     |  museum\b                            #
                     |  aero\b                              #
                     |  coop\b                              #
                     |  name\b                              #
                     |  pro\b                               #
                     |  [a-z][a-z]\b                        #     two-letter country codes
                     )                                      #
                 )?                                         #
                 (?::\d+)?                                  # Optional port number
                 (?:                                        # Rest of the URL, optional
                     /?                                     #     Start with '/'
                     [^.!,?;:"'<>()\[\]{}\s\x7F-\xFF]*      #     Can't start with these
                     (?:                                    #
                         [.!,?;:]+                          #     One or more of these
                         [^.!,?;:"'<>()\[\]{}\s\x7F-\xFF]+  #     Can't finish with these
                         #'"                                #     # or ' or "
                     )*                                     #
                 )?                                         #
              ''',


    # Block attributes.
    'battr': r'''(?P<parameters>                            # 
                     (?: %(align)s                          # alignment
                     |   %(classid)s                        # class and/or id
                     |   %(padding)s                        # padding tags
                     |   %(lang)s                           # [lang]
                     |   %(style)s                          # {style}
                     )+                                     #
                 )?                                         #
              ''' % parameters,

    # (Un)ordered list attributes.
    'olattr': r'''(?P<olparameters>                         # 
                      (?: %(align)s                         # alignment
                      | ((?:\(\#[\w]+\))                    # (#id)
                          |                                 #
                          (?:\((?:[\w]+(?:\s[\w]+)*)        #
                            (?:\#[\w]+)?\))                 # (class1 class2 ... classn#id) or (class1 class2 ... classn)
                      )                                     #
                      |   %(padding)s                       # padding tags
                      |   %(lang)s                          # [lang]
                      |   %(style)s                         # {style}
                      )+                                    #
                  )?                                        #
              ''' % parameters,

    # List item attributes.
    'liattr': r'''(?P<liparameters>                         # 
                      (?: %(align)s                         # alignment
                      |   %(classid)s                       # class and/or id
                      |   %(padding)s                       # padding tags
                      |   %(lang)s                          # [lang]
                      |   %(style)s                         # {style}
                      )+                                    #
                  )?                                        #
              ''' % parameters,

    # Qtag attributes.
    'qattr': r'''(?P<parameters>                            #
                     (?: %(classid)s                        # class and/or id
                     |   %(lang)s                           # [lang]
                     |   %(style)s                          # {style}
                     )+                                     #
                 )?                                         #
              ''' % parameters,

    # Link attributes.
    'lattr': r'''(?P<parameters>                            # Links attributes
                     (?: %(align)s                          # alignment
                     |   %(classid)s                        # class and/or id
                     |   %(lang)s                           # [lang]
                     |   %(style)s                          # {style}
                     )+                                     #
                 )?                                         #
              ''' % parameters,

    # Image attributes.
    'iattr': r'''(?P<parameters>                            #
                     (?:                                    #
                     (?: [<>]+                              # horizontal alignment tags
                         (?![^\s]*(?:[<>])))                #     (must happen once)
                     |                                      # 
                     (?: [\-\^~]+                           # vertical alignment tags
                         (?![^\s]*(?:[\-\^~])))             #     (must happen once)
                     | %(classid)s                          # class and/or id
                     | %(padding)s                          # padding tags
                     | %(style)s                            # {style}
                     )+                                     #
                 )?                                         #
              ''' % parameters,

    # Resize attributes.
    'resize': r'''(?:                                       #
                      (?:([\d]+%?)x([\d]+%?))               # 20x10
                      |                                     #
                      (?:                                   # or
                          (?:([\d]+)%?w\s([\d]+)%?h)        #     10h 20w
                          |                                 #     or
                          (?:([\d]+)%?h\s([\d]+)%?w)        #     20w 10h 
                      )                                     #
                  )?                                        #
               ''',

    # Table attributes.
    'tattr': r'''(?P<parameters>                            #
                     (?:                                    #
                     (?: [\^~]                              # vertical alignment
                         (?![^\s]*(?:[\^~])))               #     (must happen once)
                     |   %(align)s                          # alignment
                     |   %(lang)s                           # [lang]
                     |   %(style)s                          # {style}
                     |   %(classid)s                        # class and/or id
                     |   %(padding)s                        # padding
                     |   _                                  # is this a header row/cell?
                     |   \\\d+                              # colspan
                     |   /\d+                               # rowspan
                     )+                                     #
                 )?                                         #
              ''' % parameters,
}


def preg_replace(pattern, replacement, text):
    """Alternative re.sub that handles empty groups.

    This acts like re.sub, except it replaces empty groups with ''
    instead of raising an exception.
    """

    def replacement_func(matchobj):
        counter = 1
        rc = replacement
        _debug(matchobj.groups())
        for matchitem in matchobj.groups():
            if not matchitem:
                matchitem = ''

            rc = rc.replace(r'\%s' % counter, matchitem)
            counter += 1

        return rc
        
    p = re.compile(pattern)
    _debug(pattern)

    return p.sub(replacement_func, text)


def html_replace(pattern, replacement, text):
    """Replacement outside HTML tags.

    Does a preg_replace only outside HTML tags.
    """
    # If there is no html, do a simple search and replace.
    if not re.search(r'''<.*>''', text):
        return preg_replace(pattern, replacement, text)

    else:
        lines = []
        # Else split the text into an array at <>.
        for line in re.split('(<.*?>)', text):
            if not re.match('<.*?>', line):
                line = preg_replace(pattern, replacement, line)

            lines.append(line)

        return ''.join(lines)


# PyTextile can optionally sanitize the generated XHTML,
# which is good for weblog comments. This code is from
# Mark Pilgrim's feedparser.
class _BaseHTMLProcessor(sgmllib.SGMLParser):
    elements_no_end_tag = ['area', 'base', 'basefont', 'br', 'col', 'frame', 'hr',
      'img', 'input', 'isindex', 'link', 'meta', 'param']
    
    def __init__(self):
        sgmllib.SGMLParser.__init__(self)
    
    def reset(self):
        self.pieces = []
        sgmllib.SGMLParser.reset(self)

    def normalize_attrs(self, attrs):
        # utility method to be called by descendants
        attrs = [(k.lower(), sgmllib.charref.sub(lambda m: unichr(int(m.groups()[0])), v).strip()) for k, v in attrs]
        attrs = [(k, k in ('rel', 'type') and v.lower() or v) for k, v in attrs]
        return attrs
    
    def unknown_starttag(self, tag, attrs):
        # called for each start tag
        # attrs is a list of (attr, value) tuples
        # e.g. for <pre class="screen">, tag="pre", attrs=[("class", "screen")]
        strattrs = "".join([' %s="%s"' % (key, value) for key, value in attrs])
        if tag in self.elements_no_end_tag:
            self.pieces.append("<%(tag)s%(strattrs)s />" % locals())
        else:
            self.pieces.append("<%(tag)s%(strattrs)s>" % locals())
        
    def unknown_endtag(self, tag):
        # called for each end tag, e.g. for </pre>, tag will be "pre"
        # Reconstruct the original end tag.
        if tag not in self.elements_no_end_tag:
            self.pieces.append("</%(tag)s>" % locals())

    def handle_charref(self, ref):
        # called for each character reference, e.g. for "&#160;", ref will be "160"
        # Reconstruct the original character reference.
        self.pieces.append("&#%(ref)s;" % locals())

    def handle_entityref(self, ref):
        # called for each entity reference, e.g. for "&copy;", ref will be "copy"
        # Reconstruct the original entity reference.
        self.pieces.append("&%(ref)s;" % locals())

    def handle_data(self, text):
        # called for each block of plain text, i.e. outside of any tag and
        # not containing any character or entity references
        # Store the original text verbatim.
        self.pieces.append(text)

    def handle_comment(self, text):
        # called for each HTML comment, e.g. <!-- insert Javascript code here -->
        # Reconstruct the original comment.
        self.pieces.append("<!--%(text)s-->" % locals())

    def handle_pi(self, text):
        # called for each processing instruction, e.g. <?instruction>
        # Reconstruct original processing instruction.
        self.pieces.append("<?%(text)s>" % locals())

    def handle_decl(self, text):
        # called for the DOCTYPE, if present, e.g.
        # <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
        #     "http://www.w3.org/TR/html4/loose.dtd">
        # Reconstruct original DOCTYPE
        self.pieces.append("<!%(text)s>" % locals())

    def output(self):
        """Return processed HTML as a single string"""
        return "".join(self.pieces)


class _HTMLSanitizer(_BaseHTMLProcessor):
    acceptable_elements = ['a', 'abbr', 'acronym', 'address', 'area', 'b', 'big',
      'blockquote', 'br', 'button', 'caption', 'center', 'cite', 'code', 'col',
      'colgroup', 'dd', 'del', 'dfn', 'dir', 'div', 'dl', 'dt', 'em', 'fieldset',
      'font', 'form', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img', 'input',
      'ins', 'kbd', 'label', 'legend', 'li', 'map', 'menu', 'ol', 'optgroup',
      'option', 'p', 'pre', 'q', 's', 'samp', 'select', 'small', 'span', 'strike',
      'strong', 'sub', 'sup', 'table', 'tbody', 'td', 'textarea', 'tfoot', 'th',
      'thead', 'tr', 'tt', 'u', 'ul', 'var']

    acceptable_attributes = ['abbr', 'accept', 'accept-charset', 'accesskey',
      'action', 'align', 'alt', 'axis', 'border', 'cellpadding', 'cellspacing',
      'char', 'charoff', 'charset', 'checked', 'cite', 'class', 'clear', 'cols',
      'colspan', 'color', 'compact', 'coords', 'datetime', 'dir', 'disabled',
      'enctype', 'for', 'frame', 'headers', 'height', 'href', 'hreflang', 'hspace',
      'id', 'ismap', 'label', 'lang', 'longdesc', 'maxlength', 'media', 'method',
      'multiple', 'name', 'nohref', 'noshade', 'nowrap', 'prompt', 'readonly',
      'rel', 'rev', 'rows', 'rowspan', 'rules', 'scope', 'selected', 'shape', 'size',
      'span', 'src', 'start', 'summary', 'tabindex', 'target', 'title', 'type',
      'usemap', 'valign', 'value', 'vspace', 'width']
    
    unacceptable_elements_with_end_tag = ['script', 'applet'] 
    
    # This if for MathML.
    mathml_elements = ['math', 'mi', 'mn', 'mo', 'mrow', 'msup']
    mathml_attributes = ['mode', 'xmlns']

    acceptable_elements = acceptable_elements + mathml_elements
    acceptable_attributes = acceptable_attributes + mathml_attributes
                  
    def reset(self):
        _BaseHTMLProcessor.reset(self)
        self.unacceptablestack = 0
        
    def unknown_starttag(self, tag, attrs):
        if not tag in self.acceptable_elements:
            if tag in self.unacceptable_elements_with_end_tag:
                self.unacceptablestack += 1
            return
        attrs = self.normalize_attrs(attrs)
        attrs = [(key, value) for key, value in attrs if key in self.acceptable_attributes]
        _BaseHTMLProcessor.unknown_starttag(self, tag, attrs)

    def unknown_endtag(self, tag):
        if not tag in self.acceptable_elements:
            if tag in self.unacceptable_elements_with_end_tag:
                self.unacceptablestack -= 1
            return
        _BaseHTMLProcessor.unknown_endtag(self, tag)

    def handle_pi(self, text):
        pass

    def handle_decl(self, text):
        pass

    def handle_data(self, text):
        if not self.unacceptablestack:
            _BaseHTMLProcessor.handle_data(self, text)


class Textiler:
    """Textile formatter.

    This is the base class for the PyTextile text processor.
    """
    def __init__(self, text=''):
        """Instantiate the class, passing the text to be formatted.
            
        Here we pre-process the text and collect all the link
        lookups for later.
        """
        self.text = text

        # Basic regular expressions.
        self.res = res

        # Smart searches.
        self.searches = {}
        self.searches['imdb']   = 'http://www.imdb.com/Find?for=%s'
        self.searches['google'] = 'http://www.google.com/search?q=%s'
        self.searches['python'] = 'http://www.python.org/doc/current/lib/module-%s.html'
        if amazon_associate_id:
            self.searches['isbn']   = ''.join(['http://', AMAZON, '/exec/obidos/ASIN/%s/', amazon_associate_id])
            self.searches['amazon'] = ''.join(['http://', AMAZON, '/exec/obidos/external-search?mode=blended&keyword=%s&tag=', amazon_associate_id])
        else:
            self.searches['isbn']   = ''.join(['http://', AMAZON, '/exec/obidos/ASIN/%s'])
            self.searches['amazon'] = ''.join(['http://', AMAZON, '/exec/obidos/external-search?mode=blended&keyword=%s'])

        # These are the blocks we know.
        self.signatures = [
                           # Paragraph.
                           (r'''^p                       # Paragraph signature
                                %(battr)s                # Paragraph attributes
                                (?P<dot>\.)              # .
                                (?P<extend>\.)?          # Extended paragraph denoted by a second dot
                                \s                       # whitespace
                                (?P<text>.*)             # text
                             ''' % self.res, self.paragraph),
   
                           # Pre-formatted text.
                           (r'''^pre                     # Pre signature
                                %(battr)s                # Pre attributes
                                (?P<dot>\.)              # .
                                (?P<extend>\.)?          # Extended pre denoted by a second dot
                                \s                       # whitespace
                                (?P<text>.*)             # text
                             ''' % self.res, self.pre),
   
                           # Block code.
                           (r'''^bc                      # Blockcode signature
                                %(battr)s                # Blockcode attributes
                                (?P<dot>\.)              # .
                                (?P<extend>\.)?          # Extended blockcode denoted by a second dot
                                \s                       # whitespace
                                (?P<text>.*)             # text
                             ''' % self.res, self.bc),
   
                           # Blockquote.
                           (r'''^bq                      # Blockquote signature
                                %(battr)s                # Blockquote attributes
                                (?P<dot>\.)              # .
                                (?P<extend>\.)?          # Extended blockquote denoted by a second dot
                                (:(?P<cite>              # Optional cite attribute
                                (                        #
                                    %(url)s              #     URL
                                |   "[\w]+(?:\s[\w]+)*"  #     "Name inside quotes"
                                ))                       #
                                )?                       #
                                \s                       # whitespace
                                (?P<text>.*)             # text
                             ''' % self.res, self.blockquote),
   
                           # Header.
                           (r'''^h                       # Header signature
                                (?P<header>\d)           # Header number
                                %(battr)s                # Header attributes
                                (?P<dot>\.)              # .
                                (?P<extend>\.)?          # Extended header denoted by a second dot
                                \s                       # whitespace
                                (?P<text>.*)             # text
                             ''' % self.res, self.header),
   
                           # Footnote.
                           (r'''^fn                      # Footnote signature
                                (?P<footnote>[\d]+)      # Footnote number
                                (?P<dot>\.)              # .
                                (?P<extend>\.)?          # Extended footnote denoted by a second dot
                                \s                       # whitespace
                                (?P<text>.*)             # text
                             ''', self.footnote),
   
                           # Definition list.
                           (r'''^dl                      # Definition list signature
                                %(battr)s                # Definition list attributes
                                (?P<dot>\.)              # .
                                (?P<extend>\.)?          # Extended definition list denoted by a second dot
                                \s                       # whitespace
                                (?P<text>.*)             # text
                             ''' % self.res, self.dl),
                           
                           # Ordered list (attributes to first <li>).
                           (r'''^%(olattr)s              # Ordered list attributes
                                \#                       # Ordered list signature
                                %(liattr)s               # List item attributes
                                (?P<dot>\.)?             # .
                                \s                       # whitespace
                                (?P<text>.*)             # text
                             ''' % self.res, self.ol),
   
                           # Unordered list (attributes to first <li>).
                           (r'''^%(olattr)s              # Unrdered list attributes
                                \*                       # Unordered list signature
                                %(liattr)s               # Unordered list attributes
                                (?P<dot>\.)?             # .
                                \s                       # whitespace
                                (?P<text>.*)             # text
                             ''' % self.res, self.ul),
   
                           # Escaped text.
                           (r'''^==?(?P<text>.*?)(==)?$  # Escaped text
                             ''', self.escape),
   
                           (r'''^(?P<text><.*)$          # XHTML tag
                             ''', self.escape),
   
                           # itex code.
                           (r'''^(?P<text>               # itex code
                                \\\[                     # starts with \[
                                .*?                      # complicated mathematical equations go here
                                \\\])                    # ends with \]
                             ''', self.itex),
   
                           # Tables.
                           (r'''^table                   # Table signature
                                %(tattr)s                # Table attributes
                                (?P<dot>\.)              # .
                                (?P<extend>\.)?          # Extended blockcode denoted by a second dot
                                \s                       # whitespace
                                (?P<text>.*)             # text
                             ''' % self.res, self.table),
                           
                           # Simple tables.
                           (r'''^(?P<text>
                                \|
                                .*)
                             ''', self.table),
   
                           # About.
                           (r'''^(?P<text>tell\sme\sabout\stextile\.)$''', self.about),
                          ]


    def preprocess(self):
        """Pre-processing of the text.

        Remove whitespace, fix carriage returns.
        """
        # Remove whitespace.
        self.text = self.text.strip()

        # Zap carriage returns.
        self.text = self.text.replace("\r\n", "\n")
        self.text = self.text.replace("\r", "\n")

        # Minor sanitizing.
        self.text = self.sanitize(self.text)


    def grab_links(self):
        """Grab link lookups.

        Check the text for link lookups, store them in a 
        dictionary, and clean them up.
        """
        # Grab links like this: '[id]example.com'
        links = {}
        p = re.compile(r'''(?:^|\n)\[([\w]+?)\](%(url)s)(?:$|\n)''' % self.res, re.VERBOSE)
        for key, link in p.findall(self.text):
            links[key] = link

        # And clear them from the text.
        self.text = p.sub('', self.text)

        return links


    def process(self, head_offset=HEAD_OFFSET, validate=VALIDATE, sanitize=SANITIZE, output=OUTPUT, encoding=ENCODING):
        """Process the text.

        Here we actually process the text, splitting the text in
        blocks and applying the corresponding function to each
        one of them.
        """
        # Basic global changes.
        self.preprocess()

        # Grab lookup links and clean them from the text.
        self._links = self.grab_links()

        # Offset for the headers.
        self.head_offset = head_offset

        # Process each block.
        self.blocks = self.split_text()

        text = []
        for [function, captures] in self.blocks:
            text.append(function(**captures))

        text = '\n\n'.join(text)

        # Add titles to footnotes.
        text = self.footnotes(text)

        # Convert to desired output.
        text = unicode(text, encoding)
        text = text.encode(output, 'xmlcharrefreplace')

        # Sanitize?
        if sanitize:
            p = _HTMLSanitizer()
            p.feed(text)
            text = p.output()

        # Validate output.
        if _tidy and validate:
            text = _tidy(text)

        return text


    def sanitize(self, text):
        """Fix single tags.

        Fix tags like <img />, <br /> and <hr />.

        ---
        h1. Sanitizing

        Textile can help you generate valid XHTML(eXtensible HyperText Markup Language).
        It will fix any single tags that are not properly closed, like
        @<img />@, @<br />@ and @<hr />@.

        If you have "mx.Tidy":http://www.egenix.com/files/python/mxTidy.html
        and/or "&micro;TidyLib":http://utidylib.sourceforge.net/ installed,
        it also can optionally validade the generated code with these wrappers
        to ensure 100% valid XHTML(eXtensible HyperText Markup Language).
        """
        # Fix single tags like <img /> and <br />.
        text = preg_replace(r'''<(img|br|hr)(.*?)(?:\s*/?\s*)?>''', r'''<\1\2 />''', text)

        # Remove ampersands.
        text = preg_replace(r'''&(?!#?[xX]?(?:[0-9a-fA-F]+|\w{1,8});)''', r'''&amp;''', text)

        return text


    def split_text(self):
        """Process the blocks from the text.

        Split the blocks according to the signatures, join extended
        blocks and associate each one of them with a function to
        process them.

        ---
        h1. Blocks

        Textile process your text by dividing it in blocks. Each block
        is identified by a signature and separated from other blocks by
        an empty line.

        All signatures should end with a period followed by a space. A
        header @<h1></h1>@ can be done this way:

        pre. h1. This is a header 1.

        Blocks may continue for multiple paragraphs of text. If you want
        a block signature to stay "active", use two periods after the
        signature instead of one. For example:

        pre.. bq.. This is paragraph one of a block quote.

        This is paragraph two of a block quote.

        =p. Now we're back to a regular paragraph.

        p. Becomes:
        
        pre.. <blockquote>
        <p>This is paragraph one of a block quote.</p>

        <p>This is paragraph two of a block quote.</p>
        </blockquote>

        <p>Now we&#8217;re back to a regular paragraph.</p>

        p. The blocks can be customised by adding parameters between the
        signature and the period. These include:

        dl. {style rule}:A CSS(Cascading Style Sheets) style rule.
        [ll]:A language identifier (for a "lang" attribute).
        (class) or (#id) or (class#id):For CSS(Cascading Style Sheets) class and id attributes.
        &gt;, &lt;, =, &lt;&gt;:Modifier characters for alignment. Right-justification, left-justification, centered, and full-justification. The paragraph will also receive the class names "right", "left", "center" and "justify", respectively.
        ( (one or more):Adds padding on the left. 1em per "(" character is applied. When combined with the align-left or align-right modifier, it makes the block float. 
        ) (one or more):Adds padding on the right. 1em per ")" character is applied. When combined with the align-left or align-right modifier, it makes the block float.

        Here's an overloaded example:

        pre. p(())>(class#id)[en]{color:red}. A simple paragraph.

        Becomes:

        pre. <p lang="en" style="color:red;padding-left:2em;padding-right:2em;float:right;" class="class right" id="id">A simple paragraph.</p>
        """
        # Clear signature.
        clear_sig = r'''^clear(?P<alignment>[<>])?\.$'''
        clear = None

        extending  = 0

        # We capture the \n's because they are important inside "pre..".
        blocks = re.split(r'''((\n\s*){2,})''', self.text)
        output = []
        for block in blocks:
            # Check for the clear signature.
            m = re.match(clear_sig, block)
            if m:
                clear = m.group('alignment')
                if clear:
                    clear = {'<': 'clear:left;', '>': 'clear:right;'}[clear]
                else:
                    clear = 'clear:both;'

            else:
                # Check each of the code signatures.
                for regexp, function in self.signatures:
                    p = re.compile(regexp, (re.VERBOSE | re.DOTALL))
                    m = p.match(block)
                    if m:
                        # Put everything in a dictionary.
                        captures = m.groupdict()

                        # If we are extending a block, we require a dot to
                        # break it, so we can start lines with '#' inside
                        # an extended <pre> without matching an ordered list.
                        if extending and not captures.get('dot', None):
                            output[-1][1]['text'] += block
                            break 
                        elif captures.has_key('dot'):
                            del captures['dot']
                            
                        # If a signature matches, we are not extending a block.
                        extending = 0

                        # Check if we should extend this block.
                        if captures.has_key('extend'):
                            extending = captures['extend']
                            del captures['extend']
                            
                        # Apply head_offset.
                        if captures.has_key('header'):
                            captures['header'] = int(captures['header']) + self.head_offset

                        # Apply clear.
                        if clear:
                            captures['clear'] = clear
                            clear = None

                        # Save the block to be processed later.
                        output.append([function, captures])

                        break

                else:
                    if extending:
                        # Append the text to the last block.
                        output[-1][1]['text'] += block
                    elif block.strip():
                        output.append([self.paragraph, {'text': block}])
    
        return output


    def parse_params(self, parameters, clear=None, align_type='block'):
        """Parse the parameters from a block signature.

        This function parses the parameters from a block signature,
        splitting the information about class, id, language and
        style. The positioning (indentation and alignment) is parsed
        and stored in the style.

        A paragraph like:

            p>(class#id){color:red}[en]. Paragraph.

        or:
            
            p{color:red}[en](class#id)>. Paragraph.

        will have its parameters parsed to:

            output = {'lang' : 'en',
                      'class': 'class',
                      'id'   : 'id',
                      'style': 'color:red;text-align:right;'}

        Note that order is not important.
        """
        if not parameters:
            if clear:
                return {'style': clear}
            else:
                return {}

        output = {}
        
        # Match class from (class) or (class#id).
        m = re.search(r'''\((?P<class>[\w]+(\s[\w]+)*)(\#[\w][\w\d\.:_-]*)?\)''', parameters)
        if m: output['class'] = m.group('class')

        # Match id from (#id) or (class#id).
        m = re.search(r'''\([\w]*(\s[\w]+)*\#(?P<id>[\w][\w\d\.:_-]*)\)''', parameters)
        if m: output['id'] = m.group('id')

        # Match [language].
        m = re.search(r'''\[(?P<lang>[\w-]+)\]''', parameters)
        if m: output['lang'] = m.group('lang')

        # Match {style}.
        m = re.search(r'''{(?P<style>[^\}]+)}''', parameters)
        if m:
            output['style'] = m.group('style').replace('\n', '')

            # If necessary, apppend a semi-comma to the style.
            if not output['style'].endswith(';'):
                output['style'] += ';'

        # Clear the block?
        if clear:
            output['style'] = output.get('style', '') + clear

        # Remove classes, ids, langs and styles. This makes the 
        # regular expression for the positioning much easier.
        parameters = preg_replace(r'''\([\#\w\d\.:_\s-]+\)''', '', parameters)
        parameters = preg_replace(r'''\[[\w-]+\]''', '', parameters)
        parameters = preg_replace(r'''{[\w:;#%-]+}''', '', parameters)

        style = []
        
        # Count the left indentation.
        l_indent = parameters.count('(')
        if l_indent: style.append('padding-left:%dem;' % l_indent)

        # Count the right indentation.
        r_indent = parameters.count(')')
        if r_indent: style.append('padding-right:%dem;' % r_indent)

        # Add alignment.
        if align_type == 'image':
            align = [('<', 'float:left;', ' left'),
                     ('>', 'float:right;', ' right')]

            valign = [('^', 'vertical-align:text-top;', ' top'),
                      ('-', 'vertical-align:middle;', ' middle'),
                      ('~', 'vertical-align:text-bottom;', ' bottom')]

            # Images can have both a vertical and a horizontal alignment.
            for alignments in [align, valign]:
                for _align, _style, _class in alignments:
                    if parameters.count(_align):
                        style.append(_style)
                        
                        # Append a class name related to the alignment.
                        output['class'] = output.get('class', '') + _class
                        break

        elif align_type == 'table':
            align = [('<', 'left'),
                     ('>', 'right'),
                     ('=', 'center'),
                     ('<>', 'justify')]

            valign = [('^', 'top'),
                      ('~', 'bottom')]

            # Horizontal alignment.
            for _align, _style, in align:
                if parameters.count(_align):
                    output['align'] = _style
            
            # Vertical alignment.
            for _align, _style, in valign:
                if parameters.count(_align):
                    output['valign'] = _style

            # Colspan and rowspan.
            m = re.search(r'''\\(\d+)''', parameters)
            if m:
                #output['colspan'] = m.groups()
                output['colspan'] = int(m.groups()[0])

            m = re.search(r'''/(\d+)''', parameters)
            if m:
                output['rowspan'] = int(m.groups()[0])

        else:
            if l_indent or r_indent:
                alignments = [('<>', 'text-align:justify;', ' justify'),
                              ('=', 'text-align:center;', ' center'),
                              ('<', 'float:left;', ' left'),
                              ('>', 'float:right;', ' right')]
            else:
                alignments = [('<>', 'text-align:justify;', ' justify'),
                              ('=', 'text-align:center;', ' center'),
                              ('<', 'text-align:left;', ' left'),
                              ('>', 'text-align:right;', ' right')]

            for _align, _style, _class in alignments:
                if parameters.count(_align):
                    style.append(_style)

                    # Append a class name related to the alignment.
                    output['class'] = output.get('class', '') + _class
                    break

        # Join all the styles.
        output['style'] = output.get('style', '') + ''.join(style)

        # Remove excess whitespace.
        if output.has_key('class'):
            output['class'] = output['class'].strip()

        return output 
        

    def build_open_tag(self, tag, attributes={}, single=0):
        """Build the open tag with specified attributes.

        This function is used by all block builders to 
        generate the opening tags with the attributes of
        the block.
        """
        # Open tag.
        open_tag = ['<%s' % tag]
        for k,v in attributes.items():
            # The ALT attribute can be empty.
            if k == 'alt' or v: open_tag.append(' %s="%s"' % (k, v))

        if single:
            open_tag.append(' /')

        # Close tag.
        open_tag.append('>')

        return ''.join(open_tag)


    def paragraph(self, text, parameters=None, attributes=None, clear=None):
        """Process a paragraph.

        This function processes the paragraphs, enclosing the text in a 
        <p> tag and breaking lines with <br />. Paragraphs are formatted
        with all the inline rules.

        ---
        h1. Paragraph
        
        This is how you write a paragraph:

        pre. p. This is a paragraph, although a short one.
        
        Since the paragraph is the default block, you can safely omit its
        signature ([@p@]). Simply write:

        pre. This is a paragraph, although a short one.

        Text in a paragraph block is wrapped in @<p></p>@ tags, and
        newlines receive a <br /> tag. In both cases Textile will process
        the text to:

        pre. <p>This is a paragraph, although a short one.</p>

        Text in a paragraph block is processed with all the inline rules.
        """
        # Split the lines.
        lines = re.split('\n{2,}', text)
        
        # Get the attributes.
        attributes = attributes or self.parse_params(parameters, clear)

        output = []
        for line in lines:
            if line:
                # Clean the line.
                line = line.strip()
                 
                # Build the tag.
                open_tag = self.build_open_tag('p', attributes)
                close_tag = '</p>'

                # Pop the id because it must be unique.
                if attributes.has_key('id'): del attributes['id']

                # Break lines. 
                line = preg_replace(r'(<br />|\n)+', '<br />\n', line)

                # Remove <br /> from inside broken HTML tags.
                line = preg_replace(r'(<[^>]*)<br />\n(.*?>)', r'\1 \2', line)

                # Inline formatting.
                line = self.inline(line)

                output.append(open_tag + line + close_tag)

        return '\n\n'.join(output)


    def pre(self, text, parameters=None, clear=None):
        """Process pre-formatted text.

        This function processes pre-formatted text into a <pre> tag.
        No HTML is added for the lines, but @<@ and @>@ are translated into
        HTML entities.

        ---
        h1. Pre-formatted text

        Pre-formatted text can be specified using the @pre@ signature.
        Inside a "pre" block, whitespace is preserved and @<@ and @>@ are
        translated into HTML(HyperText Markup Language) entities
        automatically.

        Text in a "pre" block is _not processed_ with any inline rule.

        Here's a simple example:

        pre. pre. This text is pre-formatted.
        Nothing interesting happens inside here...
        
        Will become:

        pre. <pre>
        This text is pre-formatted.
        Nothing interesting happens inside here...
        </pre>
        """

        # Remove trailing whitespace.
        text = text.rstrip()

        # Get the attributes.
        attributes = self.parse_params(parameters, clear)

        # Build the tag.
        #open_tag = self.build_open_tag('pre', attributes) + '\n'
        open_tag = self.build_open_tag('pre', attributes)
        close_tag = '\n</pre>'

        # Replace < and >.
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')

        return open_tag + text + close_tag


    def bc(self, text, parameters=None, clear=None):
        """Process block code.

        This function processes block code into a <code> tag inside a
        <pre>. No HTML is added for the lines, but @<@ and @>@ are translated
        into HTML entities.

        ---
        h1. Block code

        A block code, specified by the @bc@ signature, is a block of
        pre-formatted text which also receives a @<code></code>@ tag. As
        with "pre", whitespace is preserved and @<@ and @>@ are translated
        into HTML(HyperText Markup Language) entities automatically.

        Text in a "bc" code is _not processed_ with the inline rules.
        
        If you have "Twisted":http://www.twistedmatrix.com/ installed,
        Textile can automatically colorize your Python code if you
        specify its language as "Python":
        
        pre. bc[python]. from twisted.python import htmlizer

        This will become:

        pre. <pre>
        <code lang="python">
        <span class="py-src-keyword">from</span> <span class="py-src-variable">twisted</span><span class="py-src-op">.</span><span class="py-src-variable">python</span> <span class="py-src-keyword">import</span> <span class="py-src-variable">htmlizer</span>
        </code>
        </pre>

        The colors can be specified in your CSS(Cascading Style Sheets)
        file. If you don't want to install Twisted, you can download just
        the @htmlizer@ module "independently":http://dealmeida.net/code/htmlizer.py.txt.
        """

        # Get the attributes.
        attributes = self.parse_params(parameters, clear)

        # XHTML <code> can't have the attribute lang.
        if attributes.has_key('lang'):
            lang = attributes['lang']
            del attributes['lang']
        else:
            lang = None

        # Build the tag.
        open_tag = '<pre>\n' + self.build_open_tag('code', attributes) + '\n'
        close_tag = '\n</code>\n</pre>'

        # Colorize Python code?
        if htmlizer and lang == 'python':
            text = _color(text)
        else:
            # Replace < and >.
            text = text.replace('<', '&lt;')
            text = text.replace('>', '&gt;')

        return open_tag + text + close_tag


    def dl(self, text, parameters=None, clear=None):
        """Process definition list.

        This function process definition lists. The text inside
        the <dt> and <dd> tags is processed for inline formatting.

        ---
        h1. Definition list

        A definition list starts with the signature @dl@, and has
        its items separated by a @:@. Here's a simple example:

        pre. dl. name:Sir Lancelot of Camelot.
        quest:To seek the Holy Grail.
        color:Blue.

        Becomes:

        pre. <dl>
        <dt>name</dt>
        <dd>Sir Lancelot of Camelot.</dd>
        <dt>quest</dt>
        <dd>To seek the Holy Grail.</dd>
        <dt>color</dt>
        <dd>Blue.</dd>
        </dl>
        """
        # Get the attributes.
        attributes = self.parse_params(parameters, clear)

        # Build the tag.
        open_tag = self.build_open_tag('dl', attributes) + '\n'
        close_tag = '\n</dl>'

        lines = text.split('\n')
        output = []
        for line in lines:
            if line.count(':'):
                [dt, dd] = line.split(':', 1)
            else:
                dt,dd = line, ''

            if dt: output.append('<dt>%s</dt>\n<dd>%s</dd>' % (dt, dd))

        text = '\n'.join(output)

        text = self.inline(text)

        return open_tag + text + close_tag


    def blockquote(self, text, parameters=None, cite=None, clear=None):
        """Process block quote.

        The block quote is inserted into a <blockquote> tag, and
        processed as a paragraph. An optional cite attribute can
        be appended on the last line after two dashes (--), or
        after the period following ':' for compatibility with the
        Perl version.

        ---
        h1. Blockquote

        A blockquote is denoted by the signature @bq@. The text in this
        block will be enclosed in @<blockquote></blockquote>@ and @<p></p>@,
        receiving the same formatting as a paragraph. For example:

        pre. bq. This is a blockquote.

        Becomes:

        pre. <blockquote>
        <p>This is a blockquote.</p>
        </blockquote>

        You can optionally specify the @cite@ attribute of the blockquote,
        using the following syntax:

        pre. bq.:http://example.com Some text.

        pre. bq.:"John Doe" Some other text.

        Becomes:

        pre. <blockquote cite="http://example.com">
        <p>Some text.</p>
        </blockquote>

        pre. <blockquote cite="John Doe">
        <p>Some other text.</p>
        </blockquote>

        You can also specify the @cite@ using a pair of dashes on the
        last line of the blockquote:

        pre. bq. Some text.
        -- http://example.com
        """

        # Get the attributes.
        attributes = self.parse_params(parameters, clear)

        if cite:
            # Remove the quotes?
            cite = cite.strip('"')
            attributes['cite'] = cite
        else:
            # The citation should be on the last line.
            text = text.split('\n')
            if text[-1].startswith('-- '):
                attributes['cite'] = text.pop()[3:]    
        
            text = '\n'.join(text)

        # Build the tag.
        open_tag = self.build_open_tag('blockquote', attributes) + '\n'
        close_tag = '\n</blockquote>'

        # Process the paragraph, passing the attributes.
        # Does it make sense to pass the id, class, etc. to
        # the paragraph instead of applying it to the
        # blockquote tag?
        text = self.paragraph(text)
        
        return open_tag + text + close_tag


    def header(self, text, parameters=None, header=1, clear=None):
        """Process a header.

        The header number is captured by the regular 
        expression and lives in header. If head_offset is
        set, it is adjusted accordingly.

        ---
        h1. Header

        A header is produced by the signature @hn@, where @n@ goes
        from 1 to 6. You can adjust the relative output of the headers
        passing a @head_offset@ attribute when calling @textile()@.

        To make a header:

        pre. h1. This is a header.

        Becomes:

        pre. <h1>This is a header.</h1>
        """
        # Get the attributes.
        attributes = self.parse_params(parameters, clear)

        # Get the header number and limit it between 1 and 6.
        n = header
        n = min(n,6)
        n = max(n,1)

        # Build the tag.
        open_tag = self.build_open_tag('h%d' % n, attributes)
        close_tag = '</h%d>' % n

        text = self.inline(text)

        return open_tag + text + close_tag


    def footnote(self, text, parameters=None, footnote=1, clear=None):
        """Process a footnote.

        A footnote is formatted as a paragraph of class
        'footnote' and id 'fn%d', starting with the footnote
        number in a <sup> tag. Here we just build the
        attributes and pass them directly to self.paragraph().

        ---
        h1. Footnote

        A footnote is produced by the signature @fn@ followed by
        a number. Footnotes are paragraphs of a special CSS(Cascading Style Sheets)
        class. An example:

        pre. fn1. This is footnote number one.

        Will produce this:

        pre. <p class="footnote" id="fn1"><sup>1</sup> This is footnote number one.</p>

        This footnote can be referenced anywhere on the text by the
        following way:

        pre. This is a reference[1] to footnote number one.

        Which becomes:

        pre. <p>This is a reference<sup class="footnote"><a href="#fn1" title="This is footnote number one.">1</a></sup> to footnote number 1.</p>

        Note that the text from the footnote appears in the @title@ of the
        link pointing to it.
        """
        # Get the number.
        n = int(footnote)

        # Build the attributes to the paragraph.
        attributes = self.parse_params(parameters, clear)
        attributes['class'] = 'footnote'
        attributes['id']    = 'fn%d' % n

        # Build the paragraph text.
        text = ('<sup>%d</sup> ' % n) + text

        # And return the paragraph.
        return self.paragraph(text=text, attributes=attributes)


    def build_li(self, items, liattributes):
        """Build the list item.

        This function build the list item of an (un)ordered list. It
        works by peeking at the next list item, and searching for a
        multi-list. If a multi-list is found, it is processed and 
        appended inside the list item tags, as it should be.
        """
        lines = []
        while len(items):
            item = items.pop(0)

            # Clean the line.
            item = item.lstrip()
            item = item.replace('\n', '<br />\n')

            # Get list item attributes.
            p = re.compile(r'''^%(liattr)s\s''' % self.res, re.VERBOSE)
            m = p.match(item)
            if m:
                c = m.groupdict('')
                liparameters = c['liparameters']
                item = p.sub('', item)
            else:
                liparameters = ''

            liattributes = liattributes or self.parse_params(liparameters)
            
            # Build the item tag.
            open_tag_li = self.build_open_tag('li', liattributes) 

            # Reset the attributes, which should be applied
            # only to the first <li>.
            liattributes = {}

            # Build the closing tag.
            close_tag_li = '</li>'

            # Multi-list recursive routine.
            # Here we check the _next_ items for a multi-list. If we
            # find one, we extract all items of the multi-list and
            # process them recursively.
            if len(items):
                inlist = []

                # Grab all the items that start with # or *.
                n_item = items.pop(0)

                # Grab the <ol> parameters.
                p = re.compile(r'''^%(olattr)s''' % self.res, re.VERBOSE)
                m = p.match(n_item)
                if m:
                    c = m.groupdict('')
                    olparameters = c['olparameters']
                    tmp = p.sub('', n_item)
                else:
                    olparameters = ''

                # Check for an ordered list inside this one.
                if tmp.startswith('#'):
                    n_item = tmp
                    inlist.append(n_item)
                    while len(items):
                        # Peek into the next item.
                        n_item = items.pop(0)
                        if n_item.startswith('#'):
                            inlist.append(n_item)
                        else:
                            items.insert(0, n_item)
                            break
                        
                    inlist = self.ol('\n'.join(inlist), olparameters=olparameters)
                    item = item + '\n' + inlist + '\n'

                # Check for an unordered list inside this one.
                elif tmp.startswith('*'):
                    n_item = tmp
                    inlist.append(n_item)
                    while len(items):
                        # Peek into the next item.
                        n_item = items.pop(0)
                        if n_item.startswith('*'):
                            inlist.append(n_item)
                        else:
                            items.insert(0, n_item)
                            break

                    inlist = self.ul('\n'.join(inlist), olparameters=olparameters)
                    item = item + '\n' + inlist + '\n'

                # Otherwise we just put it back in the list.
                else:
                    items.insert(0, n_item)

            item = self.inline(item)

            item = open_tag_li + item + close_tag_li
            lines.append(item)

        return '\n'.join(lines)


    def ol(self, text, liparameters=None, olparameters=None, clear=None):
        """Build an ordered list.

        This function basically just sets the <ol></ol> with the
        right attributes, and then pass everything inside to 
        _build_li, which does the real tough recursive job.

        ---
        h1. Ordered lists

        Ordered lists can be constructed this way:

        pre. # Item number 1.
        # Item number 2.
        # Item number 3.

        And you get:

        pre. <ol>
        <li>Item number 1.</li>
        <li>Item number 2.</li>
        <li>Item number 3.</li>
        </ol>

        If you want a list to "break" an extended block, you should
        add a period after the hash. This is useful for writing 
        Python code:

        pre.. bc[python].. #!/usr/bin/env python

        # This is a comment, not an ordered list!
        # So this won't break the extended "bc".

        p. Lists can be nested:

        pre. # Item number 1.
        ## Item number 1a.
        ## Item number 1b.
        # Item number 2.
        ## Item number 2a.

        Textile will transform this to:

        pre. <ol>
        <li>Item number 1.
        <ol>
        <li>Item number 1a.</li>
        <li>Item number 1b.</li>
        </ol>
        </li>
        <li>Item number 2.
        <ol>
        <li>Item number 2a.</li>
        </ol>
        </li>
        </ol>

        You can also mix ordered and unordered lists:

        pre. * To write well you need:
        *# to read every day
        *# to write every day
        *# and X

        You'll get this:

        pre. <ul>
        <li>To write well you need:
        <ol>
        <li>to read every day</li>
        <li>to write every day</li>
        <li>and X</li>
        </ol>
        </li>
        </ul>

        To style a list, the parameters should go before the hash if you want
        to set the attributes on the @<ol>@ tag:

        pre. (class#id)# one
        # two
        # three

        If you want to customize the firsr @<li>@ tag, apply the parameters
        after the hash:

        pre. #(class#id) one
        # two
        # three
        """
        # Get the attributes.
        olattributes = self.parse_params(olparameters, clear)
        liattributes = self.parse_params(liparameters)

        # Remove list depth.
        if text.startswith('#'):
            text = text[1:]

        items = text.split('\n#')

        # Build the open tag.
        open_tag = self.build_open_tag('ol', olattributes) + '\n'

        close_tag = '\n</ol>'

        # Build the list items.
        text = self.build_li(items, liattributes)

        return open_tag + text + close_tag


    def ul(self, text, liparameters=None, olparameters=None, clear=None):
        """Build an unordered list.

        This function basically just sets the <ul></ul> with the
        right attributes, and then pass everything inside to 
        _build_li, which does the real tough recursive job.

        ---
        h1. Unordered lists

        Unordered lists behave exactly like the ordered lists, and are
        defined using a star:

        pre. * Python
        * Perl
        * PHP

        Becomes:

        pre. <ul>
        <li>Python</li>
        <li>Perl</li>
        <li><span class="caps">PHP</span></li>
        </ul>
        """
        # Get the attributes.
        olattributes = self.parse_params(olparameters, clear)
        liattributes = self.parse_params(liparameters)

        # Remove list depth.
        if text.startswith('*'):
            text = text[1:]

        items = text.split('\n*')

        # Build the open tag.
        open_tag = self.build_open_tag('ul', olattributes) + '\n'

        close_tag = '\n</ul>'

        # Build the list items.
        text = self.build_li(items, liattributes)

        return open_tag + text + close_tag
    

    def table(self, text, parameters=None, clear=None):
        """Build a table.

        To build a table we split the text in lines to get the
        rows, and split the rows between '|' to get the individual
        cells.

        ---
        h1. Tables

        Making a simple table is as easy as possible:

        pre. |a|b|c|
        |1|2|3|

        Will be processed into:

        pre. <table>
        <tr>
        <td>a</td>
        <td>b</td>
        <td>c</td>
        </tr>
        <tr>
        <td>1</td>
        <td>2</td>
        <td>3</td>
        </tr>
        </table>

        If you want to customize the @<table>@ tag, you must use the
        @table@ signature:

        pre. table(class#id)[en]. |a|b|c|
        |1|2|3|

        To customize a row, apply the modifier _before_ the first @|@:

        pre. table. (class)<>|a|b|c|
        |1|2|3|

        Individual cells can by customized by adding the parameters _after_
        the @|@, proceded by a period and a space:

        pre. |(#id). a|b|c|
        |1|2|3|

        The allowed modifiers are:

        dl. {style rule}:A CSS(Cascading Style Sheets) style rule. 
        (class) or (#id) or (class#id):A CSS(Cascading Style Sheets) class and/or id attribute. 
        ( (one or more):Adds 1em of padding to the left for each '(' character. 
        ) (one or more):Adds 1em of padding to the right for each ')' character. 
        &lt;:Aligns to the left (floats to left for tables if combined with the ')' modifier). 
        &gt;:Aligns to the right (floats to right for tables if combined with the '(' modifier). 
        =:Aligns to center (sets left, right margins to 'auto' for tables). 
        &lt;&gt;:For cells only. Justifies text. 
        ^:For rows and cells only. Aligns to the top. 
        ~ (tilde):For rows and cells only. Aligns to the bottom. 
        _ (underscore):Can be applied to a table row or cell to indicate a header row or cell. 
        \\2 or \\3 or \\4, etc.:Used within cells to indicate a colspan of 2, 3, 4, etc. columns. When you see "\\", think "push forward". 
        /2 or /3 or /4, etc.:Used within cells to indicate a rowspan of 2, 3, 4, etc. rows. When you see "/", think "push downward". 
        
        When a cell is identified as a header cell and an alignment is
        specified, that becomes the default alignment for cells below it.
        You can always override this behavior by specifying an alignment
        for one of the lower cells.
        """
        attributes = self.parse_params(parameters, clear, align_type='table')
        #attributes['cellspacing'] = '0'

        # Build the <table>.
        open_tag = self.build_open_tag('table', attributes) + '\n'
        close_tag = '</table>'

        output = []
        default_align = {}
        rows = re.split(r'''\n+''', text)
        for row in rows:
            # Get the columns.
            columns = row.split('|')

            # Build the <tr>.
            parameters = columns.pop(0)

            rowattr = self.parse_params(parameters, align_type='table')
            open_tr = self.build_open_tag('tr', rowattr) + '\n'
            output.append(open_tr)

            # Does the row define headers?
            if parameters.count('_'):
                td_tag = 'th'
            else:
                td_tag = 'td'
                
            col = 0
            for cell in columns[:-1]:
                p = re.compile(r'''(?:%(tattr)s\.\s)?(?P<text>.*)''' % self.res, re.VERBOSE)
                m = p.match(cell)
                if m:
                    c = m.groupdict('')
                    cellattr = self.parse_params(c['parameters'], align_type='table')

                    # Get the width of this cell.
                    width = cellattr.get('colspan', 1)

                    # Is this a header?
                    if c['parameters'].count('_'):
                        td_tag = 'th'

                    # If it is a header, let's set the default alignment.
                    if td_tag == 'th':
                        # Set the default aligment for all cells below this one.
                        # This is a little tricky because this header can have
                        # a colspan set.
                        for i in range(col, col+width):
                            default_align[i] = cellattr.get('align', None)

                    else:
                        # Apply the default align, if any.
                        cellattr['align'] = cellattr.get('align', default_align.get(col, None))

                    open_td = self.build_open_tag(td_tag, cellattr)
                    close_td = '</%s>\n' % td_tag

                    #output.append(open_td + c['text'].strip() + close_td)
                    output.append(open_td + self.inline(c['text'].strip()) + close_td)

                col += width

            output.append('</tr>\n')

        text = open_tag + ''.join(output) + close_tag

        return text


    def escape(self, text):
        """Do nothing.

        This is used to match escaped text. Nothing to see here!

        ---
        h1. Escaping

        If you don't want Textile processing a block, you can simply
        enclose it inside @==@:

        pre. p. Regular paragraph

        pre. ==
        Escaped portion -- will not be formatted
        by Textile at all
        ==

        pre. p. Back to normal.

        This can also be used inline, disabling the formatting temporarily:

        pre. p. This is ==*a test*== of escaping.
        """
        return text


    def itex(self, text):
        """Convert itex to MathML.

        If the itex2mml binary is set, we use it to convert the
        itex to MathML. Otherwise, the text is unprocessed and 
        return as is.

        ---
        h1. itex

        Textile can automatically convert itex code to MathML(Mathematical Markup Language)
        for you, if you have the itex2MML binary (you can download it
        from the "Movable Type plugin":http://golem.ph.utexas.edu/~distler/blog/files/itexToMML.tar.gz).

        Block equations should be enclosed inbetween @\[@ and @\]@:

        pre. \[ e^{i\pi} + 1 = 0 \]

        Will be translated to:

        pre. <math xmlns='http://www.w3.org/1998/Math/MathML' mode='display'>
        <msup><mi>e</mi> <mrow><mi>i</mi>
        <mi>&amp;pi;</mi></mrow></msup>
        <mo>+</mo><mn>1</mn><mo>=</mo><mn>0</mn>
        </math>

        Equations can also be displayed inline:

        pre. Euler's formula, $e^{i\pi}+1=0$, ...

        (Note that if you want to display MathML(Mathematical Markup Language)
        your content must be served as @application/xhtml+xml@, which is not
        accepted by all browsers.)
        """
        if itex2mml:
            try:
                text = os.popen("echo '%s' | %s" % (text, itex2mml)).read()
            except:
                pass

        return text


    def about(self, text=None):
        """Show PyTextile's functionalities.

        An introduction to PyTextile. Can be called when running the
        main script or if you write the following line:

            'tell me about textile.'

        But keep it a secret!
        """

        about = []
        about.append(textile('h1. This is Textile', head_offset=self.head_offset))
        about.append(textile(__doc__.split('---', 1)[1], head_offset=self.head_offset))

        functions = [(self.split_text, 1),
                     (self.paragraph,  2),
                     (self.pre,        2),
                     (self.bc,         2),
                     (self.blockquote, 2),
                     (self.dl,         2),
                     (self.header,     2),
                     (self.footnote,   2),
                     (self.escape,     2),
                     (self.itex,       2),
                     (self.ol,         2),
                     (self.ul,         2),
                     (self.table,      2),
                     (self.inline,     1),
                     (self.qtags,      2),
                     (self.glyphs,     2),
                     (self.macros,     2),
                     (self.acronym,    2),
                     (self.images,     1),
                     (self.links,      1),
                     (self.sanitize,   1),
                    ]

        for function, offset in functions:
            doc = function.__doc__.split('---', 1)[1]
            doc = doc.split('\n')
            lines = []
            for line in doc:
                line = line.strip()
                lines.append(line)
                
            doc = '\n'.join(lines)
            about.append(textile(doc, head_offset=self.head_offset+offset))

        about = '\n'.join(about)
        about = about.replace('<br />', '')

        return about


    def acronym(self, text):
        """Process acronyms.

        Acronyms can have letters in upper and lower caps, or even numbers,
        provided that the numbers and upper caps are the same in the
        abbreviation and in the description. For example:

            XHTML(eXtensible HyperText Markup Language)
            OPeNDAP(Open source Project for a Network Data Access Protocol)
            L94(Levitus 94)

        are all valid acronyms.

        ---
        h1. Acronyms

        You can define acronyms in your text the following way:

        pre. This is XHTML(eXtensible HyperText Markup Language).

        The resulting code is:

        pre. <p><acronym title="eXtensible HyperText Markup Language"><span class="caps">XHTML</span></acronym></p>

        Acronyms can have letters in upper and lower caps, or even numbers,
        provided that the numbers and upper caps are the same in the
        abbreviation and in the description. For example:

        pre. XHTML(eXtensible HyperText Markup Language)
        OPeNDAP(Open source Project for a Network Data Access Protocol)
        L94(Levitus 94)

        are all valid acronyms.
        """
        # Find the acronyms.
        acronyms = r'''(?P<acronym>[\w]+)\((?P<definition>[^\(\)]+?)\)'''

        # Check all acronyms.
        for acronym, definition in re.findall(acronyms, text):
            caps_acronym = ''.join(re.findall('[A-Z\d]+', acronym))
            caps_definition = ''.join(re.findall('[A-Z\d]+', definition))
            if caps_acronym and caps_acronym == caps_definition:
                text = text.replace('%s(%s)' % (acronym, definition), '<acronym title="%s">%s</acronym>' % (definition, acronym))
        
        text = html_replace(r'''(^|\s)([A-Z]{3,})\b(?!\()''', r'''\1<span class="caps">\2</span>''', text)

        return text


    def footnotes(self, text):
        """Add titles to footnotes references.

        This function searches for footnotes references like this [1], and 
        adds a title to the link containing the first paragraph of the
        footnote.
        """
        # Search for footnotes.
        p = re.compile(r'''<p class="footnote" id="fn(?P<n>\d+)"><sup>(?P=n)</sup>(?P<note>.*)</p>''')
        for m in p.finditer(text):
            n = m.group('n')
            note = m.group('note').strip()

            # Strip HTML from note.
            note = re.sub('<.*?>', '', note)

            # Add the title.
            text = text.replace('<a href="#fn%s">' % n, '<a href="#fn%s" title="%s">' % (n, note))

        return text


    def macros(self, m):
        """Quick macros.

        This function replaces macros inside brackets using a built-in
        dictionary, and also unicode names if the key doesn't exist.

        ---
        h1. Macros

        Textile has support for character macros, which should be enclosed
        in curly braces. A few useful ones are:

        pre. {C=} or {=C}: euro sign
        {+-} or {-+}: plus-minus sign
        {L-} or {-L}: pound sign.

        You can also make accented characters:

        pre. Expos{e'}

        Becomes:

        pre. <p>Expos&amp;#233;</p>

        You can also specify Unicode names like:

        pre. {umbrella}
        {white smiling face}
        """
        entity = m.group(1)

        macros = {'c|': '&#162;',       # cent sign
                  '|c': '&#162;',       # cent sign
                  'L-': '&#163;',       # pound sign
                  '-L': '&#163;',       # pound sign
                  'Y=': '&#165;',       # yen sign
                  '=Y': '&#165;',       # yen sign
                  '(c)': '&#169;',      # copyright sign
                  '<<': '&#171;',       # left-pointing double angle quotation
                  '(r)': '&#174;',      # registered sign
                  '+_': '&#177;',       # plus-minus sign
                  '_+': '&#177;',       # plus-minus sign
                  '>>': '&#187;',       # right-pointing double angle quotation
                  '1/4': '&#188;',      # vulgar fraction one quarter
                  '1/2': '&#189;',      # vulgar fraction one half
                  '3/4': '&#190;',      # vulgar fraction three quarters
                  'A`': '&#192;',       # latin capital letter a with grave
                  '`A': '&#192;',       # latin capital letter a with grave
                  'A\'': '&#193;',      # latin capital letter a with acute
                  '\'A': '&#193;',      # latin capital letter a with acute
                  'A^': '&#194;',       # latin capital letter a with circumflex
                  '^A': '&#194;',       # latin capital letter a with circumflex
                  'A~': '&#195;',       # latin capital letter a with tilde
                  '~A': '&#195;',       # latin capital letter a with tilde
                  'A"': '&#196;',       # latin capital letter a with diaeresis
                  '"A': '&#196;',       # latin capital letter a with diaeresis
                  'Ao': '&#197;',       # latin capital letter a with ring above
                  'oA': '&#197;',       # latin capital letter a with ring above
                  'AE': '&#198;',       # latin capital letter ae
                  'C,': '&#199;',       # latin capital letter c with cedilla
                  ',C': '&#199;',       # latin capital letter c with cedilla
                  'E`': '&#200;',       # latin capital letter e with grave
                  '`E': '&#200;',       # latin capital letter e with grave
                  'E\'': '&#201;',      # latin capital letter e with acute
                  '\'E': '&#201;',      # latin capital letter e with acute
                  'E^': '&#202;',       # latin capital letter e with circumflex
                  '^E': '&#202;',       # latin capital letter e with circumflex
                  'E"': '&#203;',       # latin capital letter e with diaeresis
                  '"E': '&#203;',       # latin capital letter e with diaeresis
                  'I`': '&#204;',       # latin capital letter i with grave
                  '`I': '&#204;',       # latin capital letter i with grave
                  'I\'': '&#205;',      # latin capital letter i with acute
                  '\'I': '&#205;',      # latin capital letter i with acute
                  'I^': '&#206;',       # latin capital letter i with circumflex
                  '^I': '&#206;',       # latin capital letter i with circumflex
                  'I"': '&#207;',       # latin capital letter i with diaeresis
                  '"I': '&#207;',       # latin capital letter i with diaeresis
                  'D-': '&#208;',       # latin capital letter eth
                  '-D': '&#208;',       # latin capital letter eth
                  'N~': '&#209;',       # latin capital letter n with tilde
                  '~N': '&#209;',       # latin capital letter n with tilde
                  'O`': '&#210;',       # latin capital letter o with grave
                  '`O': '&#210;',       # latin capital letter o with grave
                  'O\'': '&#211;',      # latin capital letter o with acute
                  '\'O': '&#211;',      # latin capital letter o with acute
                  'O^': '&#212;',       # latin capital letter o with circumflex
                  '^O': '&#212;',       # latin capital letter o with circumflex
                  'O~': '&#213;',       # latin capital letter o with tilde
                  '~O': '&#213;',       # latin capital letter o with tilde
                  'O"': '&#214;',       # latin capital letter o with diaeresis
                  '"O': '&#214;',       # latin capital letter o with diaeresis
                  'O/': '&#216;',       # latin capital letter o with stroke
                  '/O': '&#216;',       # latin capital letter o with stroke
                  'U`':  '&#217;',      # latin capital letter u with grave
                  '`U':  '&#217;',      # latin capital letter u with grave
                  'U\'': '&#218;',      # latin capital letter u with acute
                  '\'U': '&#218;',      # latin capital letter u with acute
                  'U^': '&#219;',       # latin capital letter u with circumflex
                  '^U': '&#219;',       # latin capital letter u with circumflex
                  'U"': '&#220;',       # latin capital letter u with diaeresis
                  '"U': '&#220;',       # latin capital letter u with diaeresis
                  'Y\'': '&#221;',      # latin capital letter y with acute
                  '\'Y': '&#221;',      # latin capital letter y with acute
                  'a`': '&#224;',       # latin small letter a with grave
                  '`a': '&#224;',       # latin small letter a with grave
                  'a\'': '&#225;',      # latin small letter a with acute
                  '\'a': '&#225;',      # latin small letter a with acute
                  'a^': '&#226;',       # latin small letter a with circumflex
                  '^a': '&#226;',       # latin small letter a with circumflex
                  'a~': '&#227;',       # latin small letter a with tilde
                  '~a': '&#227;',       # latin small letter a with tilde
                  'a"': '&#228;',       # latin small letter a with diaeresis
                  '"a': '&#228;',       # latin small letter a with diaeresis
                  'ao': '&#229;',       # latin small letter a with ring above
                  'oa': '&#229;',       # latin small letter a with ring above
                  'ae': '&#230;',       # latin small letter ae
                  'c,': '&#231;',       # latin small letter c with cedilla
                  ',c': '&#231;',       # latin small letter c with cedilla
                  'e`': '&#232;',       # latin small letter e with grave
                  '`e': '&#232;',       # latin small letter e with grave
                  'e\'': '&#233;',      # latin small letter e with acute
                  '\'e': '&#233;',      # latin small letter e with acute
                  'e^': '&#234;',       # latin small letter e with circumflex
                  '^e': '&#234;',       # latin small letter e with circumflex
                  'e"': '&#235;',       # latin small letter e with diaeresis
                  '"e': '&#235;',       # latin small letter e with diaeresis
                  'i`': '&#236;',       # latin small letter i with grave
                  '`i': '&#236;',       # latin small letter i with grave
                  'i\'': '&#237;',      # latin small letter i with acute
                  '\'i': '&#237;',      # latin small letter i with acute
                  'i^': '&#238;',       # latin small letter i with circumflex
                  '^i': '&#238;',       # latin small letter i with circumflex
                  'i"': '&#239;',       # latin small letter i with diaeresis
                  '"i': '&#239;',       # latin small letter i with diaeresis
                  'n~': '&#241;',       # latin small letter n with tilde
                  '~n': '&#241;',       # latin small letter n with tilde
                  'o`': '&#242;',       # latin small letter o with grave
                  '`o': '&#242;',       # latin small letter o with grave
                  'o\'': '&#243;',      # latin small letter o with acute
                  '\'o': '&#243;',      # latin small letter o with acute
                  'o^': '&#244;',       # latin small letter o with circumflex
                  '^o': '&#244;',       # latin small letter o with circumflex
                  'o~': '&#245;',       # latin small letter o with tilde
                  '~o': '&#245;',       # latin small letter o with tilde
                  'o"': '&#246;',       # latin small letter o with diaeresis
                  '"o': '&#246;',       # latin small letter o with diaeresis
                  ':-': '&#247;',       # division sign
                  '-:': '&#247;',       # division sign
                  'o/': '&#248;',       # latin small letter o with stroke
                  '/o': '&#248;',       # latin small letter o with stroke
                  'u`': '&#249;',       # latin small letter u with grave
                  '`u': '&#249;',       # latin small letter u with grave
                  'u\'': '&#250;',      # latin small letter u with acute
                  '\'u': '&#250;',      # latin small letter u with acute
                  'u^': '&#251;',       # latin small letter u with circumflex
                  '^u': '&#251;',       # latin small letter u with circumflex
                  'u"': '&#252;',       # latin small letter u with diaeresis
                  '"u': '&#252;',       # latin small letter u with diaeresis
                  'y\'': '&#253;',      # latin small letter y with acute
                  '\'y': '&#253;',      # latin small letter y with acute
                  'y"': '&#255',        # latin small letter y with diaeresis
                  '"y': '&#255',        # latin small letter y with diaeresis
                  'OE': '&#338;',       # latin capital ligature oe
                  'oe': '&#339;',       # latin small ligature oe
                  '*': '&#8226;',       # bullet
                  'Fr': '&#8355;',      # french franc sign
                  'L=': '&#8356;',      # lira sign
                  '=L': '&#8356;',      # lira sign
                  'Rs': '&#8360;',      # rupee sign
                  'C=': '&#8364;',      # euro sign
                  '=C': '&#8364;',      # euro sign
                  'tm': '&#8482;',      # trade mark sign
                  '<-': '&#8592;',      # leftwards arrow
                  '->': '&#8594;',      # rightwards arrow
                  '<=': '&#8656;',      # leftwards double arrow
                  '=>': '&#8658;',      # rightwards double arrow
                  '=/': '&#8800;',      # not equal to
                  '/=': '&#8800;',      # not equal to
                  '<_': '&#8804;',      # less-than or equal to
                  '_<': '&#8804;',      # less-than or equal to
                  '>_': '&#8805;',      # greater-than or equal to
                  '_>': '&#8805;',      # greater-than or equal to
                  ':(': '&#9785;',      # white frowning face
                  ':)': '&#9786;',      # white smiling face
                  'spade': '&#9824;',   # black spade suit
                  'club': '&#9827;',    # black club suit
                  'heart': '&#9829;',   # black heart suit
                  'diamond': '&#9830;', # black diamond suit
                 }

        try:
            # Try the key.
            entity = macros[entity]
        except KeyError:
            try:
                # Try a unicode entity.
                entity = unicodedata.lookup(entity)
                entity = entity.encode('ascii', 'xmlcharrefreplace')
            except:
                # Return the unmodified entity.
                entity = '{%s}' % entity

        return entity


    def glyphs(self, text):
        """Glyph formatting.

        This function replaces quotations marks, dashes and a few other
        symbol for numerical entities. The em/en dashes use definitions
        comes from http://alistapart.com/articles/emen/.

        ---
        h1. Glyphs

        Textile replaces some of the characters in your text with their
        equivalent numerical entities. These include:

        * Replace single and double primes used as quotation marks with HTML(HyperText Markup Language) entities for opening and closing quotation marks in readable text, while leaving untouched the primes required within HTML(HyperText Markup Language) tags.
        * Replace double hyphens (==--==) with an em-dash (&#8212;) entity.
        * Replace triple hyphens (==---==) with two em-dash (&#8212;&#8212;) entities.
        * Replace single hyphens surrounded by spaces with an en-dash (&#8211;) entity.
        * Replace triplets of periods (==...==) with an ellipsis (&#8230;) entity.
        * Convert many nonstandard characters to browser-safe entities corresponding to keyboard input.
        * Convert ==(TM)==, ==(R)==, and  ==(C)== to &#8482;, &#174;, and &#169;.
        * Convert the letter x to a dimension sign: 2==x==4 to 2x4 and 8 ==x== 10 to 8x10.
        """
        glyphs = [(r'''"(?<!\w)\b''', r'''&#8220;'''),                              # double quotes
                  (r'''"''', r'''&#8221;'''),                                       # double quotes
                  (r"""\b'""", r'''&#8217;'''),                                     # single quotes
                  (r"""'(?<!\w)\b""", r'''&#8216;'''),                              # single quotes
                  (r"""'""", r'''&#8217;'''),                                       # single single quote
                  (r'''(\b|^)( )?\.{3}''', r'''\1&#8230;'''),                       # ellipsis
                  (r'''\b---\b''', r'''&#8212;&#8212;'''),                          # double em dash
                  (r'''\s?--\s?''', r'''&#8212;'''),                                # em dash
                  (r'''(\d+)-(\d+)''', r'''\1&#8211;\2'''),                         # en dash (1954-1999)
                  (r'''(\d+)-(\W)''', r'''\1&#8212;\2'''),                          # em dash (1954--)
                  (r'''\s-\s''', r''' &#8211; '''),                                 # en dash
                  (r'''(\d+) ?x ?(\d+)''', r'''\1&#215;\2'''),                      # dimension sign
                  (r'''\b ?(\((tm|TM)\))''', r'''&#8482;'''),                       # trademark
                  (r'''\b ?(\([rR]\))''', r'''&#174;'''),                           # registered
                  (r'''\b ?(\([cC]\))''', r'''&#169;'''),                           # copyright
                  (r'''([^\s])\[(\d+)\]''',                                         #
                       r'''\1<sup class="footnote"><a href="#fn\2">\2</a></sup>'''),# footnote
                  ]

        # Apply macros.
        text = re.sub(r'''{([^}]+)}''', self.macros, text)

        # LaTeX style quotes.
        text = text.replace('\x60\x60', '&#8220;')
        text = text.replace('\xb4\xb4', '&#8221;')

        # Linkify URL and emails.
        url = r'''(?=[a-zA-Z0-9./#])                          # Must start correctly
                  ((?:                                        # Match the leading part (proto://hostname, or just hostname)
                      (?:ftp|https?|telnet|nntp)              #     protocol
                      ://                                     #     ://
                      (?:                                     #     Optional 'username:password@'
                          \w+                                 #         username
                          (?::\w+)?                           #         optional :password
                          @                                   #         @
                      )?                                      # 
                      [-\w]+(?:\.\w[-\w]*)+                   #     hostname (sub.example.com)
                  )                                           #
                  (?::\d+)?                                   # Optional port number
                  (?:                                         # Rest of the URL, optional
                      /?                                      #     Start with '/'
                      [^.!,?;:"'<>()\[\]{}\s\x7F-\xFF]*       #     Can't start with these
                      (?:                                     #
                          [.!,?;:]+                           #     One or more of these
                          [^.!,?;:"'<>()\[\]{}\s\x7F-\xFF]+   #     Can't finish with these
                          #'"                                 #     # or ' or "
                      )*                                      #
                  )?)                                         #
               '''

        email = r'''(?:mailto:)?            # Optional mailto:
                    ([-\+\w]+               # username
                    \@                      # at
                    [-\w]+(?:\.\w[-\w]*)+)  # hostname
                 '''

        # If there is no html, do a simple search and replace.
        if not re.search(r'''<.*>''', text):
            for glyph_search, glyph_replace in glyphs:
                text = preg_replace(glyph_search, glyph_replace, text)

            # Linkify.
            text = re.sub(re.compile(url, re.VERBOSE), r'''<a href="\1">\1</a>''', text)
            text = re.sub(re.compile(email, re.VERBOSE), r'''<a href="mailto:\1">\1</a>''', text)

        else:
            lines = []
            # Else split the text into an array at <>.
            for line in re.split('(<.*?>)', text):
                if not re.match('<.*?>', line):
                    for glyph_search, glyph_replace in glyphs:
                        line = preg_replace(glyph_search, glyph_replace, line)

                    # Linkify.
                    line = re.sub(re.compile(url, re.VERBOSE), r'''<a href="\1">\1</a>''', line)
                    line = re.sub(re.compile(email, re.VERBOSE), r'''<a href="mailto:\1">\1</a>''', line)

                lines.append(line)

            text = ''.join(lines)

        return text


    def qtags(self, text):
        """Quick tags formatting.

        This function does the inline formatting of text, like
        bold, italic, strong and also itex code.

        ---
        h1. Quick tags

        Quick tags allow you to format your text, making it bold, 
        emphasized or small, for example. The quick tags operators
        include:

        dl. ==*strong*==:Translates into @<strong>strong</strong>@.
        ==_emphasis_==:Translates into @<em>emphasis</em>@. 
        ==**bold**==:Translates into @<b>bold</b>@. 
        ==__italics__==:Translates into @<i>italics</i>@. 
        ==++bigger++==:Translates into @<big>bigger</big>@. 
        ==--smaller--==:Translates into: @<small>smaller</small>@. 
        ==-deleted text-==:Translates into @<del>deleted text</del>@. 
        ==+inserted text+==:Translates into @<ins>inserted text</ins>@. 
        ==^superscript^==:Translates into @<sup>superscript</sup>@. 
        ==~subscript~==:Translates into @<sub>subscript</sub>@. 
        ==%span%==:Translates into @<span>span</span>@. 
        ==@code@==:Translates into @<code>code</code>@. 
        
        Note that within a "==@==...==@==" section, @<@ and @>@ are
        translated into HTML entities automatically. 

        Inline formatting operators accept the following modifiers:

        dl. {style rule}:A CSS(Cascading Style Sheets) style rule. 
        [ll]:A language identifier (for a "lang" attribute). 
        (class) or (#id) or (class#id):For CSS(Cascading Style Sheets) class and id attributes. 
        """
        # itex2mml.
        text = re.sub('\$(.*?)\$', lambda m: self.itex(m.group()), text)

        # Add span tags to upper-case words which don't have a description.
        #text = preg_replace(r'''(^|\s)([A-Z]{3,})\b(?!\()''', r'''\1<span class="caps">\2</span>''', text)
        
        # Quick tags.
        qtags = [('**', 'b',      {'qf': '(?<!\*)\*\*(?!\*)', 'cls': '\*'}),
                 ('__', 'i',      {'qf': '(?<!_)__(?!_)', 'cls': '_'}),
                 ('??', 'cite',   {'qf': '\?\?(?!\?)', 'cls': '\?'}),
                 ('-',  'del',    {'qf': '(?<!\-)\-(?!\-)', 'cls': '-'}),
                 ('+',  'ins',    {'qf': '(?<!\+)\+(?!\+)', 'cls': '\+'}),
                 ('*',  'strong', {'qf': '(?<!\*)\*(?!\*)', 'cls': '\*'}),
                 ('_',  'em',     {'qf': '(?<!_)_(?!_)', 'cls': '_'}),
                 ('++', 'big',    {'qf': '(?<!\+)\+\+(?!\+)', 'cls': '\+\+'}),
                 ('--', 'small',  {'qf': '(?<!\-)\-\-(?!\-)', 'cls': '\-\-'}),
                 ('~',  'sub',    {'qf': '(?<!\~)\~(?!(\\\/~))', 'cls': '\~'}),
                 ('@',  'code',   {'qf': '(?<!@)@(?!@)', 'cls': '@'}),
                 ('%',  'span',   {'qf': '(?<!%)%(?!%)', 'cls': '%'}),
                ]

        # Superscript.
        text = re.sub(r'''(?<!\^)\^(?!\^)(.+?)(?<!\^)\^(?!\^)''', r'''<sup>\1</sup>''', text)

        # This is from the perl version of Textile.
        for qtag, htmltag, redict in qtags:
            self.res.update(redict)
            p = re.compile(r'''(?:                          #
                                   ^                        # Start of string
                                   |                        #
                                   (?<=[\s>'"])             # Whitespace, end of tag, quotes
                                   |                        #
                                   (?P<pre>[{[])            # Surrounded by [ or {
                                   |                        #
                                   (?<=%(punct)s)           # Punctuation
                               )                            #
                               %(qf)s                       # opening tag
                               %(qattr)s                    # attributes
                               (?P<text>[^%(cls)s\s].*?)    # text
                               (?<=\S)                      # non-whitespace
                               %(qf)s                       # 
                               (?:                          #
                                   $                        # End of string
                                   |                        #
                                   (?P<post>[\]}])          # Surrounded by ] or }
                                   |                        # 
                                   (?=%(punct)s{1,2}|\s)    # punctuation
                                )                           #
                             ''' % self.res, re.VERBOSE)

            def _replace(m):
                c = m.groupdict('')

                attributes = self.parse_params(c['parameters'])
                open_tag  = self.build_open_tag(htmltag, attributes) 
                close_tag = '</%s>' % htmltag

                # Replace < and > inside <code></code>.
                if htmltag == 'code':
                    c['text'] = c['text'].replace('<', '&lt;')
                    c['text'] = c['text'].replace('>', '&gt;')
         
                return open_tag + c['text'] + close_tag

            text = p.sub(_replace, text)

        return text


    def images(self, text):
        """Process images.

        This function process images tags, with or without links. Images
        can have vertical and/or horizontal alignment, and can be resized
        unefficiently using width and height tags.

        ---
        h1. Images

        An image is generated by enclosing the image source in @!@:

        pre. !/path/to/image!

        You may optionally specify an alternative text for the image, which
        will also be used as its title:

        pre. !image.jpg (Nice picture)!

        Becomes:

        pre. <p><img src="image.jpg" alt="Nice picture" title="Nice picture" /></p>

        If you want to make the image point to a link, simply append a
        comma and the URL(Universal Republic of Love) to the image:

        pre. !image.jpg!:http://diveintopython.org

        Images can also be resized. These are all equivalent:

        pre. !image.jpg 10x20!
        !image.jpg 10w 20h!
        !image.jpg 20h 10w!

        The image @image.jpg@ will be resized to width 10 and height 20.

        Modifiers to the @<img>@ tag go after the opening @!@:

        pre. !(class#id)^image.jpg!

        Allowed modifiers include:
        
        dl. &lt;:Align the image to the left (causes the image to float if CSS options are enabled). 
        &gt;:Align the image to the right (causes the image to float if CSS options are enabled). 
        - (dash):Aligns the image to the middle. 
        ^:Aligns the image to the top. 
        ~ (tilde):Aligns the image to the bottom. 
        {style rule}:Applies a CSS style rule to the image. 
        (class) or (#id) or (class#id):Applies a CSS class and/or id to the image. 
        ( (one or more):Pads 1em on the left for each '(' character. 
        ) (one or more):Pads 1em on the right for each ')' character. 

        Images receive the class "top" when using top alignment, "bottom" 
        for bottom alignment and "middle" for middle alignment.
        """
        # Compile the beast.
        p = re.compile(r'''\!               # Opening !
                           %(iattr)s        # Image attributes
                           (?P<src>%(url)s) # Image src
                           \s?              # Optional whitesapce
                           (                #
                               \(           #
                               (?P<alt>.*?) # Optional (alt) attribute
                               \)           #
                           )?               #
                           \s?              # Optional whitespace
                           %(resize)s       # Resize parameters
                           \!               # Closing !
                           (                # Optional link
                               :            #    starts with ':'
                               (?P<link>    #    
                               %(url)s      #    link HREF
                               )            #
                           )?               #
                        ''' % self.res, re.VERBOSE)

        for m in p.finditer(text):
            c = m.groupdict('')

            # Build the parameters for the <img /> tag.
            attributes = self.parse_params(c['parameters'], align_type='image')
            attributes.update(c)
            if attributes['alt']:
                attributes['title'] = attributes['alt']

            # Append height and width.
            attributes['width'] = m.groups()[5] or m.groups()[7] or m.groups()[10]
            attributes['height'] = m.groups()[6] or m.groups()[8] or m.groups()[9]

            # Create the image tag.
            tag = self.image(attributes)

            text = text.replace(m.group(), tag)
        
        return text


    def image(self, attributes):
        """Process each image.

        This method builds the <img> tag for each image in the text. It's
        separated from the 'images' method so it can be easily overriden when
        subclassing Textiler. Useful if you want to download and/or process
        the images, for example.
        """
        link = attributes['link']
        del attributes['link']
        del attributes['parameters']

        # Build the tag.
        tag = self.build_open_tag('img', attributes, single=1)

        if link:
            href = preg_replace('&(?!(#|amp))', '&amp;', link)
            tag = '<a href="%s">%s</a>' % (href, tag)

        return tag


    def links(self, text):
        """Process links.

        This function is responsible for processing links. It has
        some nice shortcuts to Google, Amazon and IMDB queries.

        ---
        h1. Links

        A links is done the following way:

        pre. "This is the text link":http://example.com

        The result from this markup is:

        pre. <p><a href="http://example.com">This is the text link</a></p>

        You can add an optional @title@ attribute:

        pre. "This is the text link(This is the title)":http://example.com

        The link can be customised as well:

        pre. "(nospam)E-mail me please":mailto:someone@example.com

        You can use either single or double quotes. They must be enclosed in
        whitespace, punctuation or brackets:

        pre. You["gotta":http://example.com]seethis!

        If you are going to reference the same link a couple of times, you
        can define a lookup list anywhere on your document:

        pre. [python]http://www.python.org

        Links to the Python website can then be defined the following way:

        pre. "Check this":python

        There are also shortcuts for Amazon, IMDB(Internet Movie DataBase) and
        Google queries:

        pre. "Has anyone seen this guy?":imdb:Stephen+Fry
        "Really nice book":amazon:Goedel+Escher+Bach
        "PyBlosxom":google
        ["Using Textile and Blosxom with Python":google:python blosxom textile]

        Becomes:

        pre. <a href="http://www.imdb.com/Find?for=Stephen+Fry">Has anyone seen this guy?</a>
        <a href="http://www.amazon.com/exec/obidos/external-search?index=blended&amp;keyword=Goedel+Escher+Bach">Really nice book</a>
        <a href="http://www.google.com/search?q=PyBlosxom">PyBlosxom</a>
        <a href="http://www.google.com/search?q=python+blosxom+textile">Using Textile and Blosxom with Python</a>
        """
        linkres = [r'''\[                           # [
                       (?P<quote>"|')               # Opening quotes
                       %(lattr)s                    # Link attributes
                       (?P<text>[^"]+?)             # Link text
                       \s?                          # Optional whitespace
                       (?:\((?P<title>[^\)]+?)\))?  # Optional (title)
                       (?P=quote)                   # Closing quotes
                       :                            # :
                       (?P<href>[^\]]+)             # HREF
                       \]                           # ]
                    ''' % self.res,
                   r'''(?P<quote>"|')               # Opening quotes
                       %(lattr)s                    # Link attributes
                       (?P<text>[^"]+?)             # Link text
                       \s?                          # Optional whitespace
                       (?:\((?P<title>[^\)]+?)\))?  # Optional (title)
                       (?P=quote)                   # Closing quotes
                       :                            # :
                       (?P<href>%(url)s)            # HREF
                    ''' % self.res]

        for linkre in linkres:
            p = re.compile(linkre, re.VERBOSE)
            for m in p.finditer(text):
                c = m.groupdict('')

                attributes = self.parse_params(c['parameters'])
                attributes['title'] = c['title'].replace('"', '&quot;')

                # Search lookup list.
                link = self._links.get(c['href'], None) or c['href']

                # Hyperlinks for Amazon, IMDB and Google searches.
                parts = link.split(':', 1)
                proto = parts[0]
                if len(parts) == 2:
                    query = parts[1]
                else:
                    query = c['text']

                query = query.replace(' ', '+')

                # Look for smart search.
                if self.searches.has_key(proto):
                    link = self.searches[proto] % query
                
                # Fix URL.
                attributes['href'] = preg_replace('&(?!(#|amp))', '&amp;', link)

                open_tag = self.build_open_tag('a', attributes)
                close_tag = '</a>'

                repl = open_tag + c['text'] + close_tag

                text = text.replace(m.group(), repl)

        return text


    def format(self, text):
        """Text formatting.

        This function basically defines the order on which the 
        formatting is applied.
        """
        text = self.qtags(text)
        text = self.images(text)
        text = self.links(text)
        text = self.acronym(text)
        text = self.glyphs(text)

        return text


    def inline(self, text):
        """Inline formatting.

        This function calls the formatting on the inline text,
        taking care to avoid the escaped parts.

        ---
        h1. Inline 

        Inline formatting is applied within a block of text.
        """
        if not re.search(r'''==(.*?)==''', text):
            text = self.format(text)

        else:
            lines = []
            # Else split the text into an array at <>.
            for line in re.split('(==.*?==)', text):
                if not re.match('==.*?==', line):
                    line = self.format(line)
                else:
                    line = line[2:-2]

                lines.append(line)
            
            text = ''.join(lines)

        return text
            

def textile(text, **args):
    """This is Textile.

    Generates XHTML from a simple markup developed by Dean Allen.

    This function should be called like this:
    
        textile(text, head_offset=0, validate=0, sanitize=0,
                encoding='latin-1', output='ASCII')
    """
    return Textiler(text).process(**args)


if __name__ == '__main__':
    print textile('tell me about textile.', head_offset=1)

########NEW FILE########
__FILENAME__ = fabfile
import sys, os, os.path, subprocess, json, zipfile
from fabric.api import *
from fabric.contrib import *

# force only in testing
g_force_deploy = False

env.hosts = ['blog.kowalczyk.info']
env.user = 'blog'
app_dir = 'www/app'

def git_ensure_clean():
	out = subprocess.check_output(["git", "status", "--porcelain"])
	if len(out) != 0:
		print("won't deploy because repo has uncommitted changes:")
		print(out)
		sys.exit(1)


def git_pull():
	local("git pull")


def git_trunk_sha1():
	return subprocess.check_output(["git", "log", "-1", "--pretty=format:%H"])


def delete_file(p):
	if os.path.exists(p):
		os.remove(p)


def ensure_remote_dir_exists(p):
	if not files.exists(p):
		abort("dir '%s' doesn't exist on remote server" % p)


def ensure_remote_file_exists(p):
	if not files.exists(p):
		abort("dir '%s' doesn't exist on remote server" % p)


def add_dir_files(zip_file, dir, dirInZip=None):
	if not os.path.exists(dir):
		abort("dir '%s' doesn't exist" % dir)
	for (path, dirs, files) in os.walk(dir):
		for f in files:
			p = os.path.join(path, f)
			zipPath = None
			if dirInZip is not None:
				zipPath = dirInZip + p[len(dir):]
				#print("Adding %s as %s" % (p, zipPath))
				zip_file.write(p, zipPath)
			else:
				zip_file.write(p)


def zip_files(zip_path):
	zf = zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED)
	zf.write("config.json")
	zf.write("blog_app_linux", "blog_app")
	add_dir_files(zf, "tmpl")
	add_dir_files(zf, os.path.join("..", "scripts"), "scripts")
	add_dir_files(zf, os.path.join("..", "www"), "www")
	zf.close()


def delete_old_deploys(to_keep=5):
	with cd(app_dir):
		out = run('ls -1trF')
		lines = out.split("\n")
		i = 0
		dirs_to_del = []
		while i < len(lines):
			s = lines[i].strip()
			# extra precaution: skip dirs right after "prev@", "current@", they
			# are presumed to be their symlink targets
			if s in ["prev@", "current@"]:
				i += 1
				to_keep -= 1
			else:
				if len(s) == 41:  # s == "0111cb7bdd014850e8c11ee4820dc0d7e12f4015/"
					dirs_to_del.append(s)
			i += 1
		if len(dirs_to_del) > to_keep:
			dirs_to_del = dirs_to_del[:-to_keep]
			print("deleting old deploys: %s" % str(dirs_to_del))
			for d in dirs_to_del:
				run("rm -rf %s" % d)


def check_config():
	needed_values = ["AwsAccess", "AwsSecret", "S3BackupBucket", "S3BackupDir",
					 "CookieEncrKeyHexStr", "CookieAuthKeyHexStr", "AnalyticsCode",
					"TwitterOAuthCredentials"]
	if not os.path.exists("config.json"): abort("config.json doesn't exist locally")
	j = json.loads(open("config.json").read())
	for k in needed_values:
		if k not in j:
			abort("config.json doesn't have key: %s" % k)
		v = j[k]
		if len(v) == 0:
			abort("config.json has empty key: %s" % k)


def deploy():
	check_config()
	if not g_force_deploy:
		git_ensure_clean()
	local("../scripts/build.sh")
	local("../scripts/tests.sh")
	ensure_remote_dir_exists(app_dir)
	ensure_remote_file_exists('www/data')
	sha1 = git_trunk_sha1()
	code_path_remote = app_dir + '/' + sha1
	if not g_force_deploy and files.exists(code_path_remote):
		abort('code for revision %s already exists on the server' % sha1)
	zip_path = sha1 + ".zip"
	zip_files(zip_path)
	zip_path_remote = app_dir + '/' + zip_path
	put(zip_path, zip_path_remote)
	delete_file(zip_path)
	with cd(app_dir):
		if g_force_deploy:
			run("rm -rf %s" % sha1)
		run('unzip -q -x %s -d %s' % (zip_path, sha1))
		run('rm -f %s' % zip_path)

	curr_dir = app_dir + '/current'
	if files.exists(curr_dir):
		# shut-down currently running instance
		sudo("/etc/init.d/blog stop", pty=False)
		# rename old current as prev for easy rollback of bad deploy
		with cd(app_dir):
			run('rm -f prev')
			run('mv current prev')

	# make this version current
	with cd(app_dir):
		run("ln -s %s current" % sha1)

	if not files.exists("/etc/init.d/blog"):
		sudo("ln -s /home/blog/www/app/current/scripts/blog.initd /etc/init.d/blog")
		# make sure it runs on startup
		sudo("update-rc.d blog defaults")

	# start it
	sudo("/etc/init.d/blog start", pty=False)
	run("ps aux | grep blog_app | grep -v grep")

	delete_old_deploys()

########NEW FILE########
__FILENAME__ = textile_copy
#!/usr/bin/env python

import re
import uuid
from urlparse import urlparse

class Textile(object):
    hlgn = r'(?:\<(?!>)|(?<!<)\>|\<\>|\=|[()]+(?! ))'
    vlgn = r'[\-^~]'
    clas = r'(?:\([^)]+\))'
    lnge = r'(?:\[[^\]]+\])'
    styl = r'(?:\{[^}]+\})'
    cspn = r'(?:\\\d+)'
    rspn = r'(?:\/\d+)'
    a = r'(?:%s|%s)*' % (hlgn, vlgn)
    s = r'(?:%s|%s)*' % (cspn, rspn)
    c = r'(?:%s)*' % '|'.join([clas, styl, lnge, hlgn])

    pnct = r'[-!"#$%&()*+,/:;<=>?@\'\[\\\]\.^_`{|}~]'
    # urlch = r'[\w"$\-_.+!*\'(),";/?:@=&%#{}|\\^~\[\]`]'
    urlch = '[\w"$\-_.+*\'(),";\/?:@=&%#{}|\\^~\[\]`]'

    glyph_defaults = (
        ('txt_quote_single_open',  '&#8216;'),
        ('txt_quote_single_close', '&#8217;'),
        ('txt_quote_double_open',  '&#8220;'),
        ('txt_quote_double_close', '&#8221;'),
        ('txt_apostrophe',         '&#8217;'),
        ('txt_prime',              '&#8242;'),
        ('txt_prime_double',       '&#8243;'),
        ('txt_ellipsis',           '&#8230;'),
        ('txt_emdash',             '&#8212;'),
        ('txt_endash',             '&#8211;'),
        ('txt_dimension',          '&#215;'),
        ('txt_trademark',          '&#8482;'),
        ('txt_registered',         '&#174;'),
        ('txt_copyright',          '&#169;'),
    )

    def __init__(self, restricted=False, lite=False, noimage=False):
        """docstring for __init__"""
        self.restricted = restricted
        self.lite = lite
        self.noimage = noimage
        self.fn = {}
        self.urlrefs = {}
        self.shelf = {}
        self.rel = ''
        self.html_type = 'xhtml'

    def pba(self, input, element=None):
        """
        Parse block attributes.

        >>> t = Textile()
        >>> t.pba(r'\3')
        ''
        >>> t.pba(r'\\3', element='td')
        ' colspan="3"'
        >>> t.pba(r'/4', element='td')
        ' rowspan="4"'
        >>> t.pba(r'\\3/4', element='td')
        ' colspan="3" rowspan="4"'

        >>> t.vAlign('^')
        'top'

        >>> t.pba('^', element='td')
        ' style="vertical-align:top;"'

        >>> t.pba('{line-height:18px}')
        ' style="line-height:18px;"'

        >>> t.pba('(foo-bar)')
        ' class="foo-bar"'

        >>> t.pba('(#myid)')
        ' id="myid"'

        >>> t.pba('(foo-bar#myid)')
        ' class="foo-bar" id="myid"'

        >>> t.pba('((((')
        ' style="padding-left:4em;"'

        >>> t.pba(')))')
        ' style="padding-right:3em;"'

        >>> t.pba('[fr]')
        ' lang="fr"'

        """
        style = []
        aclass = ''
        lang = ''
        colspan = ''
        rowspan = ''
        id = ''

        if not input:
            return ''

        matched = input
        if element == 'td':
            m = re.search(r'\\(\d+)', matched)
            if m:
                colspan = m.group(1)

            m = re.search(r'/(\d+)', matched)
            if m:
                rowspan = m.group(1)

        if element == 'td' or element == 'tr':
            m = re.search(r'(%s)' % self.vlgn, matched)
            if m:
                style.append("vertical-align:%s;" % self.vAlign(m.group(1)))

        m = re.search(r'\{([^}]*)\}', matched)
        if m:
            style.append(m.group(1).rstrip(';') + ';')
            matched = matched.replace(m.group(0), '')

        m = re.search(r'\[([^\]]+)\]', matched, re.U)
        if m:
            lang = m.group(1)
            matched = matched.replace(m.group(0), '')

        m = re.search(r'\(([^()]+)\)', matched, re.U)
        if m:
            aclass = m.group(1)
            matched = matched.replace(m.group(0), '')

        m = re.search(r'([(]+)', matched)
        if m:
            style.append("padding-left:%sem;" % len(m.group(1)))
            matched = matched.replace(m.group(0), '')

        m = re.search(r'([)]+)', matched)
        if m:
            style.append("padding-right:%sem;" % len(m.group(1)))
            matched = matched.replace(m.group(0), '')

        m = re.search(r'(%s)' % self.hlgn, matched)
        if m:
            style.append("text-align:%s;" % self.hAlign(m.group(1)))

        m = re.search(r'^(.*)#(.*)$', aclass)
        if m:
            id = m.group(2)
            aclass = m.group(1)

        if self.restricted:
            if lang:
                return ' lang="%s"'
            else:
                return ''

        result = []
        if style:
            result.append(' style="%s"' % "".join(style))
        if aclass:
            result.append(' class="%s"' % aclass)
        if lang:
            result.append(' lang="%s"' % lang)
        if id:
            result.append(' id="%s"' % id)
        if colspan:
            result.append(' colspan="%s"' % colspan)
        if rowspan:
            result.append(' rowspan="%s"' % rowspan)
        return ''.join(result)

    def hasRawText(self, text):
        """
        checks whether the text has text not already enclosed by a block tag

        >>> t = Textile()
        >>> t.hasRawText('<p>foo bar biz baz</p>')
        False

        >>> t.hasRawText(' why yes, yes it does')
        True

        """
        r = re.compile(r'<(p|blockquote|div|form|table|ul|ol|pre|h\d)[^>]*?>.*</\1>', re.S).sub('', text.strip()).strip()
        r = re.compile(r'<(hr|br)[^>]*?/>').sub('', r)
        return '' != r

    def table(self, text):
        r"""
        >>> t = Textile()
        >>> t.table('|one|two|three|\n|a|b|c|')
        '\t<table>\n\t\t<tr>\n\t\t\t<td>one</td>\n\t\t\t<td>two</td>\n\t\t\t<td>three</td>\n\t\t</tr>\n\t\t<tr>\n\t\t\t<td>a</td>\n\t\t\t<td>b</td>\n\t\t\t<td>c</td>\n\t\t</tr>\n\t</table>\n\n'
        """
        text = text + "\n\n"
        pattern = re.compile(r'^(?:table(_?%(s)s%(a)s%(c)s)\. ?\n)?^(%(a)s%(c)s\.? ?\|.*\|)\n\n' % {'s':self.s, 'a':self.a, 'c':self.c}, re.S|re.M|re.U)
        return pattern.sub(self.fTable, text)

    def fTable(self, match):
        tatts = self.pba(match.group(1), 'table')
        rows = []
        for row in [ x for x in match.group(2).split('\n') if x]:
            rmtch = re.search(r'^(%s%s\. )(.*)' % (self.a, self.c), row.lstrip())
            if rmtch:
                ratts = self.pba(rmtch.group(1), 'tr')
                row = rmtch.group(2)
            else:
                ratts = ''

            cells = []
            for cell in row.split('|')[1:-1]:
                ctyp = 'd'
                if re.search(r'^_', cell):
                    ctyp = "h"
                cmtch = re.search(r'^(_?%s%s%s\. )(.*)' % (self.s, self.a, self.c), cell)
                if cmtch:
                    catts = self.pba(cmtch.group(1), 'td')
                    cell = cmtch.group(2)
                else:
                    catts = ''

                cell = self.graf(self.span(cell))
                cells.append('\t\t\t<t%s%s>%s</t%s>' % (ctyp, catts, cell, ctyp))
            rows.append("\t\t<tr%s>\n%s\n\t\t</tr>" % (ratts, '\n'.join(cells)))
            cells = []
            catts = None
        return "\t<table%s>\n%s\n\t</table>\n\n" % (tatts, '\n'.join(rows))

    def lists(self, text):
        """
        >>> t = Textile()
        >>> t.lists("* one\\n* two\\n* three")
        '\\t<ul>\\n\\t\\t<li>one</li>\\n\\t\\t<li>two</li>\\n\\t\\t<li>three</li>\\n\\t</ul>'
        """
        pattern = re.compile(r'^([#*]+%s .*)$(?![^#*])' % self.c, re.U|re.M|re.S)
        return pattern.sub(self.fList, text)

    def fList(self, match):
        text = match.group(0).split("\n")
        result = []
        lists = []
        for i, line in enumerate(text):
            try:
                nextline = text[i+1]
            except IndexError:
                nextline = ''

            m = re.search(r"^([#*]+)(%s%s) (.*)$" % (self.a, self.c), line, re.S)
            if m:
                tl, atts, content = m.groups()
                nl = ''
                nm = re.search(r'^([#*]+)\s.*', nextline)
                if nm:
                    nl = nm.group(1)
                if tl not in lists:
                    lists.append(tl)
                    atts = self.pba(atts)
                    line = "\t<%sl%s>\n\t\t<li>%s" % (self.lT(tl), atts, self.graf(content))
                else:
                    line = "\t\t<li>" + self.graf(content)

                if len(nl) <= len(tl):
                    line = line + "</li>"
                for k in reversed(lists):
                    if len(k) > len(nl):
                        line = line + "\n\t</%sl>" % self.lT(k)
                        if len(k) > 1:
                            line = line + "</li>"
                        lists.remove(k)

            result.append(line)
        return "\n".join(result)

    def lT(self, input):
        if re.search(r'^#+', input):
            return 'o'
        else:
            return 'u'

    def doPBr(self, in_):
        return re.compile(r'<(p)([^>]*?)>(.*)(</\1>)', re.S).sub(self.doBr, in_)

    def doBr(self, match):
        if self.html_type == 'html':
            content = re.sub(r'(.+)(?:(?<!<br>)|(?<!<br />))\n(?![#*\s|])', '\\1<br>', match.group(3))
        else:
            content = re.sub(r'(.+)(?:(?<!<br>)|(?<!<br />))\n(?![#*\s|])', '\\1<br />', match.group(3))
        return '<%s%s>%s%s' % (match.group(1), match.group(2), content, match.group(4))

    def block(self, text, head_offset = 0):
        """
        >>> t = Textile()
        >>> t.block('h1. foobar baby')
        '\\t<h1>foobar baby</h1>'
        """
        if not self.lite:
            tre = '|'.join(self.btag)
        else:
            tre = '|'.join(self.btag_lite)
        text = text.split('\n\n')

        tag = 'p'
        atts = cite = graf = ext = ''

        out = []

        anon = False
        for line in text:
            pattern = r'^(%s)(%s%s)\.(\.?)(?::(\S+))? (.*)$' % (tre, self.a, self.c)
            match = re.search(pattern, line, re.S)
            if match:
                if ext:
                    out.append(out.pop() + c1)

                tag, atts, ext, cite, graf = match.groups()
                h_match = re.search(r'h([1-6])', tag)
                if h_match:
                    head_level, = h_match.groups()
                    tag = 'h%i' % max(1,
                                      min(int(head_level) + head_offset,
                                          6))
                o1, o2, content, c2, c1 = self.fBlock(tag, atts, ext,
                                                      cite, graf)
                # leave off c1 if this block is extended,
                # we'll close it at the start of the next block

                if ext:
                    line = "%s%s%s%s" % (o1, o2, content, c2)
                else:
                    line = "%s%s%s%s%s" % (o1, o2, content, c2, c1)

            else:
                anon = True
                if ext or not re.search(r'^\s', line):
                    o1, o2, content, c2, c1 = self.fBlock(tag, atts, ext,
                                                          cite, line)
                    # skip $o1/$c1 because this is part of a continuing
                    # extended block
                    if tag == 'p' and not self.hasRawText(content):
                        line = content
                    else:
                        line = "%s%s%s" % (o2, content, c2)
                else:
                    line = self.graf(line)

            line = self.doPBr(line)
            if self.html_type == 'xhtml':
                line = re.sub(r'<br>', '<br />', line)

            if ext and anon:
                out.append(out.pop() + "\n" + line)
            else:
                out.append(line)

            if not ext:
                tag = 'p'
                atts = ''
                cite = ''
                graf = ''

        if ext:
            out.append(out.pop() + c1)
        return '\n\n'.join(out)

    def fBlock(self, tag, atts, ext, cite, content):
        """
        >>> t = Textile()
        >>> t.fBlock("bq", "", None, "", "Hello BlockQuote")
        ('\\t<blockquote>\\n', '\\t\\t<p>', 'Hello BlockQuote', '</p>', '\\n\\t</blockquote>')

        >>> t.fBlock("bq", "", None, "http://google.com", "Hello BlockQuote")
        ('\\t<blockquote cite="http://google.com">\\n', '\\t\\t<p>', 'Hello BlockQuote', '</p>', '\\n\\t</blockquote>')

        >>> t.fBlock("bc", "", None, "", 'printf "Hello, World";') # doctest: +ELLIPSIS
        ('<pre>', '<code>', ..., '</code>', '</pre>')

        >>> t.fBlock("h1", "", None, "", "foobar")
        ('', '\\t<h1>', 'foobar', '</h1>', '')
        """
        atts = self.pba(atts)
        o1 = o2 = c2 = c1 = ''

        m = re.search(r'fn(\d+)', tag)
        if m:
            tag = 'p'
            if m.group(1) in self.fn:
                fnid = self.fn[m.group(1)]
            else:
                fnid = m.group(1)
            atts = atts + ' id="fn%s"' % fnid
            if atts.find('class=') < 0:
                atts = atts + ' class="footnote"'
            content = ('<sup>%s</sup>' % m.group(1)) + content

        if tag == 'bq':
            cite = self.checkRefs(cite)
            if cite:
                cite = ' cite="%s"' % cite
            else:
                cite = ''
            o1 = "\t<blockquote%s%s>\n" % (cite, atts)
            o2 = "\t\t<p%s>" % atts
            c2 = "</p>"
            c1 = "\n\t</blockquote>"

        elif tag == 'bc':
            o1 = "<pre%s>" % atts
            o2 = "<code%s>" % atts
            c2 = "</code>"
            c1 = "</pre>"
            content = self.shelve(self.encode_html(content.rstrip("\n") + "\n"))

        elif tag == 'notextile':
            content = self.shelve(content)
            o1 = o2 = ''
            c1 = c2 = ''

        elif tag == 'pre':
            content = self.shelve(self.encode_html(content.rstrip("\n") + "\n"))
            o1 = "<pre%s>" % atts
            o2 = c2 = ''
            c1 = '</pre>'

        else:
            o2 = "\t<%s%s>" % (tag, atts)
            c2 = "</%s>" % tag

        content = self.graf(content)
        return o1, o2, content, c2, c1

    def footnoteRef(self, text):
        """
        >>> t = Textile()
        >>> t.footnoteRef('foo[1] ') # doctest: +ELLIPSIS
        'foo<sup class="footnote"><a href="#fn...">1</a></sup> '
        """
        return re.sub(r'\b\[([0-9]+)\](\s)?', self.footnoteID, text)

    def footnoteID(self, match):
        id, t = match.groups()
        if id not in self.fn:
            self.fn[id] = str(uuid.uuid4())
        fnid = self.fn[id]
        if not t:
            t = ''
        return '<sup class="footnote"><a href="#fn%s">%s</a></sup>%s' % (fnid, id, t)

    def glyphs(self, text):
        """
        >>> t = Textile()

        >>> t.glyphs("apostrophe's")
        'apostrophe&#8217;s'

        >>> t.glyphs("back in '88")
        'back in &#8217;88'

        >>> t.glyphs('foo ...')
        'foo &#8230;'

        >>> t.glyphs('--')
        '&#8212;'

        >>> t.glyphs('FooBar[tm]')
        'FooBar&#8482;'

        >>> t.glyphs("<p><cite>Cat's Cradle</cite> by Vonnegut</p>")
        '<p><cite>Cat&#8217;s Cradle</cite> by Vonnegut</p>'

        """
         # fix: hackish
        text = re.sub(r'"\Z', '\" ', text)

        glyph_search = (
            re.compile(r"(\w)\'(\w)"),                                      # apostrophe's
            re.compile(r'(\s)\'(\d+\w?)\b(?!\')'),                          # back in '88
            re.compile(r'(\S)\'(?=\s|'+self.pnct+'|<|$)'),                       #  single closing
            re.compile(r'\'/'),                                             #  single opening
            re.compile(r'(\S)\"(?=\s|'+self.pnct+'|<|$)'),                       #  double closing
            re.compile(r'"'),                                               #  double opening
            re.compile(r'\b([A-Z][A-Z0-9]{2,})\b(?:[(]([^)]*)[)])'),        #  3+ uppercase acronym
            re.compile(r'\b([A-Z][A-Z\'\-]+[A-Z])(?=[\s.,\)>])'),           #  3+ uppercase
            re.compile(r'\b(\s{0,1})?\.{3}'),                                     #  ellipsis
            re.compile(r'(\s?)--(\s?)'),                                    #  em dash
            re.compile(r'\s-(?:\s|$)'),                                     #  en dash
            re.compile(r'(\d+)( ?)x( ?)(?=\d+)'),                           #  dimension sign
            re.compile(r'\b ?[([]TM[])]', re.I),                            #  trademark
            re.compile(r'\b ?[([]R[])]', re.I),                             #  registered
            re.compile(r'\b ?[([]C[])]', re.I),                             #  copyright
         )

        glyph_replace = [x % dict(self.glyph_defaults) for x in (
            r'\1%(txt_apostrophe)s\2',           # apostrophe's
            r'\1%(txt_apostrophe)s\2',           # back in '88
            r'\1%(txt_quote_single_close)s',     #  single closing
            r'%(txt_quote_single_open)s',         #  single opening
            r'\1%(txt_quote_double_close)s',        #  double closing
            r'%(txt_quote_double_open)s',             #  double opening
            r'<acronym title="\2">\1</acronym>', #  3+ uppercase acronym
            r'<span class="caps">\1</span>',     #  3+ uppercase
            r'\1%(txt_ellipsis)s',                  #  ellipsis
            r'\1%(txt_emdash)s\2',               #  em dash
            r' %(txt_endash)s ',                 #  en dash
            r'\1\2%(txt_dimension)s\3',          #  dimension sign
            r'%(txt_trademark)s',                #  trademark
            r'%(txt_registered)s',                #  registered
            r'%(txt_copyright)s',                #  copyright
        )]

        result = []
        for line in re.compile(r'(<.*?>)', re.U).split(text):
            if not re.search(r'<.*>', line):
                for s, r in zip(glyph_search, glyph_replace):
                    line = s.sub(r, line)
            result.append(line)
        return ''.join(result)

    def vAlign(self, input):
        d = {'^':'top', '-':'middle', '~':'bottom'}
        return d.get(input, '')

    def hAlign(self, input):
        d = {'<':'left', '=':'center', '>':'right', '<>': 'justify'}
        return d.get(input, '')

    def getRefs(self, text):
        """
        what is this for?
        """
        pattern = re.compile(r'(?:(?<=^)|(?<=\s))\[(.+)\]((?:http(?:s?):\/\/|\/)\S+)(?=\s|$)', re.U)
        text = pattern.sub(self.refs, text)
        return text

    def refs(self, match):
        flag, url = match.groups()
        self.urlrefs[flag] = url
        return ''

    def checkRefs(self, url):
        return self.urlrefs.get(url, url)

    def isRelURL(self, url):
        """
        Identify relative urls.

        >>> t = Textile()
        >>> t.isRelURL("http://www.google.com/")
        False
        >>> t.isRelURL("/foo")
        True

        """
        (scheme, netloc) = urlparse(url)[0:2]
        return not scheme and not netloc

    def relURL(self, url):
        scheme = urlparse(url)[0]
        if self.restricted and scheme and scheme not in self.url_schemes:
            return '#'
        return url

    def graf(self, text):
        if not self.lite:
            text = self.noTextile(text)
            text = self.code(text)

        text = self.links(text)

        if not self.noimage:
            text = self.image(text)

        if not self.lite:
            text = self.lists(text)
            text = self.table(text)

        text = self.span(text)
        text = self.footnoteRef(text)
        text = self.glyphs(text)

        return text.rstrip('\n')

    def links(self, text):
        """
        >>> t = Textile()
        >>> t.links('fooobar "Google":http://google.com/foobar/ and hello world "flickr":http://flickr.com/photos/jsamsa/ ') # doctest: +ELLIPSIS
        'fooobar ... and hello world ...'
        """

        punct = '!"#$%&\'*+,-./:;=?@\\^_`|~'

        pattern = r'''
            (?P<pre>    [\s\[{(]|[%s]   )?
            "                          # start
            (?P<atts>   %s       )
            (?P<text>   [^"]+?   )
            \s?
            (?:   \(([^)]+?)\)(?=")   )?     # $title
            ":
            (?P<url>    (?:ftp|https?)? (?: :// )? [-A-Za-z0-9+&@#/?=~_()|!:,.;]*[-A-Za-z0-9+&@#/=~_()|]   )
            (?P<post>   [^\w\/;]*?   )
            (?=<|\s|$)
        ''' % (re.escape(punct), self.c)

        text = re.compile(pattern, re.X).sub(self.fLink, text)

        return text

    def fLink(self, match):
        pre, atts, text, title, url, post = match.groups()

        if pre == None:
            pre = ''

        # assume ) at the end of the url is not actually part of the url
        # unless the url also contains a (
        if url.endswith(')') and not url.find('(') > -1:
            post = url[-1] + post
            url = url[:-1]

        url = self.checkRefs(url)

        atts = self.pba(atts)
        if title:
            atts = atts +  ' title="%s"' % self.encode_html(title)

        if not self.noimage:
            text = self.image(text)

        text = self.span(text)
        text = self.glyphs(text)

        url = self.relURL(url)
        out = '<a href="%s"%s%s>%s</a>' % (self.encode_html(url), atts, self.rel, text)
        out = self.shelve(out)
        return ''.join([pre, out, post])

    def span(self, text):
        """
        >>> t = Textile()
        >>> t.span(r"hello %(bob)span *strong* and **bold**% goodbye")
        'hello <span class="bob">span <strong>strong</strong> and <b>bold</b></span> goodbye'
        """
        qtags = (r'\*\*', r'\*', r'\?\?', r'\-', r'__', r'_', r'%', r'\+', r'~', r'\^')
        pnct = ".,\"'?!;:"

        for qtag in qtags:
            pattern = re.compile(r"""
                (?:^|(?<=[\s>%(pnct)s])|([\]}]))
                (%(qtag)s)(?!%(qtag)s)
                (%(c)s)
                (?::(\S+))?
                ([^\s%(qtag)s]+|\S[^%(qtag)s\n]*[^\s%(qtag)s\n])
                ([%(pnct)s]*)
                %(qtag)s
                (?:$|([\]}])|(?=%(selfpnct)s{1,2}|\s))
            """ % {'qtag':qtag, 'c':self.c, 'pnct':pnct,
                   'selfpnct':self.pnct}, re.X)
            text = pattern.sub(self.fSpan, text)
        return text


    def fSpan(self, match):
        _, tag, atts, cite, content, end, _ = match.groups()

        qtags = {
            '*': 'strong',
            '**': 'b',
            '??': 'cite',
            '_' : 'em',
            '__': 'i',
            '-' : 'del',
            '%' : 'span',
            '+' : 'ins',
            '~' : 'sub',
            '^' : 'sup'
        }
        tag = qtags[tag]
        atts = self.pba(atts)
        if cite:
            atts = atts + 'cite="%s"' % cite

        content = self.span(content)

        out = "<%s%s>%s%s</%s>" % (tag, atts, content, end, tag)
        return out

    def image(self, text):
        """
        >>> t = Textile()
        >>> t.image('!/imgs/myphoto.jpg!:http://jsamsa.com')
        '<a href="http://jsamsa.com"><img src="/imgs/myphoto.jpg" alt="" /></a>'
        """
        pattern = re.compile(r"""
            (?:[\[{])?          # pre
            \!                 # opening !
            (%s)               # optional style,class atts
            (?:\. )?           # optional dot-space
            ([^\s(!]+)         # presume this is the src
            \s?                # optional space
            (?:\(([^\)]+)\))?  # optional title
            \!                 # closing
            (?::(\S+))?        # optional href
            (?:[\]}]|(?=\s|$)) # lookahead: space or end of string
        """ % self.c, re.U|re.X)
        return pattern.sub(self.fImage, text)

    def fImage(self, match):
        # (None, '', '/imgs/myphoto.jpg', None, None)
        atts, url, title, href = match.groups()
        atts  = self.pba(atts)

        if title:
            atts = atts + ' title="%s" alt="%s"' % (title, title)
        else:
            atts = atts + ' alt=""'

        if href:
            href = self.checkRefs(href)

        url = self.checkRefs(url)
        url = self.relURL(url)

        out = []
        if href:
            out.append('<a href="%s" class="img">' % href)
        if self.html_type == 'html':
            out.append('<img src="%s"%s>' % (url, atts))
        else:
            out.append('<img src="%s"%s />' % (url, atts))
        if href:
            out.append('</a>')

        return ''.join(out)

    def code(self, text):
        text = self.doSpecial(text, '<code>', '</code>', self.fCode)
        text = self.doSpecial(text, '@', '@', self.fCode)
        text = self.doSpecial(text, '<pre>', '</pre>', self.fPre)
        return text

    def fCode(self, match):
        before, text, after = match.groups()
        if after == None:
            after = ''
        # text needs to be escaped
        if not self.restricted:
            text = self.encode_html(text)
        return ''.join([before, self.shelve('<code>%s</code>' % text), after])

    def fPre(self, match):
        before, text, after = match.groups()
        if after == None:
            after = ''
        # text needs to be escapedd
        if not self.restricted:
            text = self.encode_html(text)
        return ''.join([before, '<pre>', self.shelve(text), '</pre>', after])

    def doSpecial(self, text, start, end, method=None):
        if method == None:
            method = self.fSpecial
        pattern = re.compile(r'(^|\s|[\[({>])%s(.*?)%s(\s|$|[\])}])?' % (re.escape(start), re.escape(end)), re.M|re.S)
        return pattern.sub(method, text)

    def fSpecial(self, match):
        """
        special blocks like notextile or code
        """
        before, text, after = match.groups()
        if after == None:
            after = ''
        return ''.join([before, self.shelve(self.encode_html(text)), after])

    def noTextile(self, text):
        text = self.doSpecial(text, '<notextile>', '</notextile>', self.fTextile)
        return self.doSpecial(text, '==', '==', self.fTextile)

    def fTextile(self, match):
        before, notextile, after = match.groups()
        if after == None:
            after = ''
        return ''.join([before, self.shelve(notextile), after])


########NEW FILE########
__FILENAME__ = regen
#!/usr/bin/env python

"""
Re-generate html files from markdown (.md) files.
"""

import os, markdown, web, util
from util import read_file_utf8, write_file_utf8, list_files, ext

def is_markdown_file(path):
	return ext(path) in [".md"]

class MdInfo(object):
	def __init__(self, meta_data, s):
		self.meta_data = meta_data
		self.s = s

# returns MdInfo from content of the .md file
def parse_md(s):
	lines = s.split("\n")
	# lines at the top that are in the format:
	# Key: value
	# are considered meta-data
	meta_data = {}
	while len(lines) > 0:
		l = lines[0]
		parts = l.split(":", 1)
		if len(parts) != 2:
			break
		key = parts[0].lower().strip()
		val = parts[1].strip()
		meta_data[key] = val
		lines.pop(0)
	s = "\n".join(lines)
	return MdInfo(meta_data, s)

def tmpl_for_src_path(src):
	dir = os.path.dirname(src)
	path = os.path.join(dir, "_md.tmpl.html")
	tmpl_data = open(path).read()
	return web.template.Template(tmpl_data, filename="md_tmpl.html")

def md_to_html(src, dst):
	s = read_file_utf8(src)
	md_info = parse_md(s)
	body = markdown.markdown(md_info.s)
	tmpl = tmpl_for_src_path(src)
	#print("Found template: %s" % mdtmpl)
	title = md_info.meta_data["title"]
	#print(vars.keys())
	html = str(tmpl(title, body))
	util.delete_file(dst)
	print("wrote %s" % dst)
	write_file_utf8(dst, html)

def main():
	md_files = list_files("www", is_markdown_file, recur=True)
	for md_file in md_files:
		html_file = md_file[:-2] + "html"
		md_to_html(md_file, html_file)

if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = restore_backup_from_s3
# the backup is in kjkbackup bucket, directory blog:
# - directory blobs has articles blobs
# - directory blobs_crashes has crashes blobs
# - $date_$hash.zip has the rest (the latest has the most recent info)
import os, json, zipfile


g_aws_access = None
g_aws_secret = None
g_bucket = "kjkbackup"
g_conn = None


def memoize(func):
	memory = {}
	def __decorated(*args):
		if args not in memory:
			memory[args] = func(*args)
		return memory[args]
	return __decorated


def s3_get_conn():
  global g_conn
  from boto.s3.connection import S3Connection
  if g_conn is None:
    g_conn = S3Connection(g_aws_access, g_aws_secret, True)
  return g_conn


def s3_get_bucket():
  return s3_get_conn().get_bucket(g_bucket)


def s3_list(s3_dir):
  from boto.s3.bucketlistresultset import bucket_lister
  b = s3_get_bucket()
  return bucket_lister(b, s3_dir)


def delete_file(path):
  if os.path.exists(path):
    os.remove(path)


def create_dir(d):
  if not os.path.exists(d): os.makedirs(d)
  return d

@memoize
def script_dir(): return os.path.realpath(os.path.dirname(__file__))


# where we will download the files
# to ../../blogdata directory (if exists) - for local testing
# to the same directory where the script is - on the server
@memoize
def local_download_dir():
	d = os.path.join(script_dir(), "..", "..", "blogdata")
	if os.path.exists(d):
		return d
	return script_dir()


def get_config_json_path():
	d1 = script_dir()
	d2 = os.path.join(script_dir(), "..", "go")
	f_path = os.path.join(d1, "config.json")
	if os.path.exists(f_path):
		return f_path
	f_path = os.path.join(d2, "config.json")
	if os.path.exists(f_path):
		return f_path
	assert False, "config.json not found in %s or %s" % (d1, d2)


def find_latest_zip(zip_files):
	sorted_by_name = sorted(zip_files, key=lambda el: el.name)
	#print(sorted_by_name)
	sorted_by_mod_time = sorted(zip_files, key=lambda el: el.last_modified)
	#print(sorted_by_mod_time)
	v1 = sorted_by_name[-1]
	v2 = sorted_by_mod_time[-1]
	assert v1 == v2, "inconsistency in zip files, %s != %s" % (str(v1), str(v2))
	return v1


def restore_from_zip(s3_key):
	print("Restoring backup files from s3 zip: %s" % s3_key.name)
	tmp_path = os.path.join(local_download_dir(), "tmp.zip")
	delete_file(tmp_path)
	s3_key.get_contents_to_filename(tmp_path)
	zf = zipfile.ZipFile(tmp_path, "r")
	dst_dir = os.path.join(local_download_dir(), "data")
	create_dir(dst_dir)
	for name in zf.namelist():
		dst_path = os.path.join(dst_dir, name)
		delete_file(dst_path) # just in case
		zf.extract(name, dst_dir)
		print("  extracted %s to %s " % (name, dst_path))
	delete_file(tmp_path)


# limit is for testing, 0 means no limit
def restore_blobs(s3_keys, s3_prefix, relative_dst_dir, limit=0):
	print("Restoring %d blobs with s3_prefix '%s' to dir '%s'" % (len(s3_keys), s3_prefix, relative_dst_dir))
	restored = 0
	restored_with_existing = 0
	for key in s3_keys:
		restored_with_existing += 1
		assert key.name.startswith(s3_prefix)
		name = key.name[len(s3_prefix):]
		dst_path = os.path.join(local_download_dir(), relative_dst_dir, name)
		if os.path.exists(dst_path):
			# TODO: could check sha1 as well
			print("  %s already restored" % dst_path)
			continue
		# not sure if boto creates the dir, so ensure destination dir exists
		print("  downloading %s => %s" % (key.name, dst_path))
		dst_dir = os.path.dirname(dst_path)
		#print("  dst_path = '%s' dst_dir = '%s'" % (dst_path, dst_dir))
		create_dir(dst_dir)
		key.get_contents_to_filename(dst_path)
		restored += 1
		if limit != 0 and restored >= limit:
			return
		if restored % 100 == 0:
			left = len(s3_keys) - restored_with_existing
			print(" left: %d, restored %d" % (left, restored))


def main():
	global g_aws_access, g_aws_secret
	print("Will download to %s" % local_download_dir())
	f_path = get_config_json_path()
	#print(f_path)
	d = open(f_path).read()
	d = json.loads(d)
	g_aws_access = d["AwsAccess"]
	g_aws_secret = d["AwsSecret"]
	print("Listing files in s3...")
	files = s3_list("blog")
	zip_files = []
	blobs_files = []
	blobs_crashes_files = []
	n = 0
	for f in files:
		n += 1
		if n % 1000 == 0:
			print("%d files in s3" % n)
		name = f.name
		if name.endswith(".zip"):
			zip_files.append(f)
		elif name.startswith("blog/blobs/"):
			blobs_files.append(f)
		elif name.startswith("blog/blobs_crashes/"):
			blobs_crashes_files.append(f)
		else:
			assert False, "%s (%s) is unrecognized files in s3" % (str(f), name)
	print("%d zip files, %d blobs and %d crash blobs" % (len(zip_files), len(blobs_files), len(blobs_crashes_files)))
	latest_zip = find_latest_zip(zip_files)
	restore_from_zip(latest_zip)
	restore_blobs(blobs_files, "blog/blobs/", "blobs")
	restore_blobs(blobs_crashes_files, "blog/blobs_crashes/", "blobs_crashes")


if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = util
import os, codecs

def read_file_utf8(path):
	with codecs.open(path, "r", "utf8") as fo:
		s = fo.read()
	return s

def write_file_utf8(path, s):
	with codecs.open(path, "w", "utf8") as fo:
		s = fo.write(s)

def ext(path):
    return os.path.splitext(path)[1].lower()

# returns full paths of files in a given directory, potentially recursively,
# potentially filtering file names by filter_func (which takes file path as
# an argument)
def list_files_g(d, filter_func=None, recur=False):
    to_visit = [d]
    while len(to_visit) > 0:
        d = to_visit.pop(0)
        for f in os.listdir(d):
            path = os.path.join(d, f)
            isdir = os.path.isdir(path)
            if isdir:
                if recur:
                    to_visit.append(path)
            else:
                if filter_func is not None:
                    if filter_func(path):
                        yield path
                else:
                    yield path

# generator => array
def list_files(d, filter_func=None, recur=False):
    return [path for path in list_files_g(d, filter_func, recur)]

def delete_file(path):
    if os.path.exists(path):
        os.remove(path)

########NEW FILE########
__FILENAME__ = jsrefgen
#!/usr/bin/env python
import cgi
import re
import jsrefgentmpl

g_source = """
!number Number 2 1.5 2.5e3 0xFF 010
ass(_2_+2 == 4); // numbers are 64-bit floating point
ass(_1.5_ == 3/2); // no separate integer type
ass(_2.5e3_ == 2500; // 2.5 * 10^3 exponential notation
ass(_0xFF_ == 255); // hexadecimal
ass(_010_ == 8); // octal
---
ass(2 _+_ 2 == 4); // addition
ass(9 _-_ 3 == 6); // subtraction
ass(3 _*_ 8 == 24); // multiplication
ass(123 _/_ 10 == 12.3); // real (not integer) division
ass(1234 _%_ 100 == 34); // modulo (reminder)
---
var n=15; n _+=_ 14; ass(n == 29); // compute & store
var n=18; n _-=_ 11; ass(n == 7	); // x *= is the same
var n=12; n _*=_ 10; ass(n == 120); // as x=x*y
var n=19; n _/=_ 10; ass(n == 1.9);
var n=18; n _%=_ 10; ass(n == 8);
---
ass(_-_3+3 == 0); // negative number (unary minus)
var n=3; n_++_; ass(n == 4); // increment
var n=3; n_--_; ass(n == 2); // decrement
---
ass(50 _< _ 51); // less than
ass(50 _<=_ 51); // less than or equal
ass(51 _> _ 50); // greater than
ass(51 _>=_ 50); // greater than or equal
ass(51 _==_ 51); // equal
ass(50 _!=_ 51); // not equal
---
ass(1000 _<<_ 3 == 8000); // shift left
ass(1000 _>>_ 3 == 125); // shift right, signed
ass(0xFFFF0000 _>>>_ 8 == 0x00FFFF00); // unsigned
// always use parentheses around termsn with: & | ^
ass((0x55555555 _&_ 0xFF00FFFF) == 0x55005555); // and
ass((0x55555555 _|_ 0x00FF0000) == 0x55FF555555); // or
ass((0x55555555 _^_ 0x0FF000000) == 0x55AA5555); // xor
ass(((_~_0xAAAA) & 0xFFFF) == 0x5555);; // 1's complement
// mask (e.g. FFFF) to remove unwanted sign extension
var n = 0x555; n _&=_ 0xF0F; ass(n == 0x505);
var n = 0x555; n _|=_ 0x0F0; ass(n == 0x5F5);
var n = 0x555; n _^=_ 0x0F0; ass(n == 0x5A5);
var n = -10; n _<<=_ 1; ass(n == -20); // shift left
var n = -10; n _>>=_1; ass(n == -5); // signed right
var n = 0x8; n _>>>=_ 1; ass(n == 0x4); // unsigned
---
ass(__Number.MIN_VALUE__ < 1e-307); // special
ass(__Number.MAX_VALUE__ > 1e308); // numbers
ass(__Number.NEGATIVE_INFINITY__ == 1/0);
ass(__Number.POSITIVE_INFINITY__ == -1/0);
ass(_isNaN_(0/0)); // NaN stands for Not a Number
ass(0/0 != 0/0); // NaN is not equal to itself!
ass(!_isFinite_(1/0)); ass(isFinite(1));

!string String 'abc' "abc" "line\u000D\u000A"
var s=="str"; // double or single quotes
var s=='str';
ass("str" _+_ "ing" == "string"); // + concatenates
ass(s._length_ == 6);
ass(s._charAt_(0) == "s"); // 0-based indexing
ass(s._charAt_(5) == "g"); // no character type
ass(s._charCodeAt_(5) == 0x67); // ASCII character value
ass(_String.fromCahrCoe_(65,66,67) == "ABC");
---
ass(s._substring_(2) == "ring"); // istart
ass(s.substring(2,4) == "ri"); // istart, iend+1
ass(s.substring(4,2) == "ri"); // iend+1, istart
ass(substring(-1) != "ng"); // (negative values are
ass(s.substring(1,-1) != "tring"); // relative to the right)
ass(s._slice_(2) == "ring"); // istart
ass(s.slice(2,4) == "ri"); // istart, iend + 1
ass(s.slice(-1) != "ng");
ass(s.slice(1,-1) != "trin");
ass(s._substr_(2) == "ring"); // istart
ass(s.substr(2,2) == "ri"); // istart, inum
ass(s.substr(-2,2) == "ng");
---
ass('abc'._toUpperCase_() == 'ABC');
ass('ABC'._toLowerCase_() == 'abc');
ass('abc'._toLocaleUpperCase_() == 'ABC');
ass('ABC'._toLocaleLowerCase_() == 'abc');
---
ass('str'._concat_('ing') == 'str' + 'ing');
ass(s._indexOf_('ing') == 3); // find substring, -1 == can't
ass('strings'._lastIndexOf_('s') == 6); // find rightmost
---
// These involve Regular Expression and/or Arrays
ass(/ing/._test_(s));
ass(s._search_(/ing/) == 3);
ass('nature'._replace_(/a/,'ur') == 'nurture');
ass('a:b:c'._split_(':')._join_('..') == 'a..b..c');
ass('1-37/54'._match_(\d+/g).join() == '1,37,54');
RegExp.lastIndex = 0;
ass(/o(.)r/._exec_('courage').join() == 'our,u');
---
// search expects a regular expresion (where dot=any):
ass('imdb.com'.search(".") == 0); // see you must
ass('imdb.com'.search(/./) == 0); // not forget to
ass('imdb.com'.search(/\./) == 4); // double-escape
ass('imdb.com'.search("\\.") == 4); // your punctuation
---
// Slash Escapes
s="_\uFFFF_"; // hexadecimal Unicode
s="_\\xFF_"; // hexadecimal ASCII
x="_\\377_"; s="_\\77_"; s="_\\7_"; // 8-bit octal
ass('_\\0_' == '\u0000'); // NUL
ass('_\\b_' == '\u0008'); // backspace
ass('_\\t_' == '\u0009'); // tab
ass('_\\f_' == '\u000C); // formfeed
ass('_\\r_' == '\u000D); // return (CR)
ass('_\\n_' == '\u000A); // newline (LF)
ass('_\\v_' == '\u000B'); // vertical tab
ass("_\\"_" = '"');
ass('_\'_' == "'");
ass("_\\\\_" == '\u005C);
---
// multi-line strings
s = "this is a _\_
test"; // comments not allowed on the line above
ass(s == "this is a test");
s="this is a " _+_ // concatenate
"better test"; // comments allowed on both of those lines
ass(s == "this is a better test");
---
// NUL isn't special, it's a character like any other
ass('abc\\0def'.length == 7);
ass('abc\\0def' != 'abc\\0xyz');
---
// user-entered cookies or URLs must encode punctuation
ass(_escape_("that's all.") == "that%27s%20all.");
ass(_unescape_("that%27s%20all.") == "that's all.');
// These are escaped %<>[\]^`{|}#$&,:;=?!/'()~
// plus space. Alphanumerics and these are not *-._+/@
// _encodeURI_() translates %<>[\]^`{|}
// _encoeURIComponent_() %<>[\]^`{|}#$&+,/:;=?
// _decodeURI_() and _decodeURIComponent_() do the inverse

!number-to-string Number<->String conversions
ass(256 == "256"); // strings in a numeric context are
ass(256.0 == "256"); // converted to a number. This is
ass(256 == "256.0"); // usually reasonable and useful.
ass("256" != "256.0"); // (String context, no convert!)
ass(256 == "0x100"); // hexadecimal prefix 0x works
ass(256 == "0256");; // but no octal 0 prefix this way
ass(256 != "25 xyz"); // no extraneous characters
---
// Number <- String
ass(256 === "256" - 0); // - converts string to number
ass("2560" === "256" + 0); // + concatenates strings
ass(256 === _parseInt_("256"));
ass(256 === _parseInt_("256 xyz")); // extras forgiven
ass(256 === _parseInt_("0x100")); // hexadecimal
ass(256 === _parseInt_("0400")); // 0 for octal
ass(256 === _parseInt_("0256", 10)); // parse decimal
ass(256 === _parseInt_("100", 16)); // parse hex
ass(256 === _parseInt_("400", 8)); // parse octal
ass(256 === _parseFloat_("2.56e1"));
ass("256" === "256"._valueOf_());
ass(isNaN(_parseInt_("xyz")));
ass(isNaN(_parseFloat_("xyz")));
---
// Number -> String explicit conversions
ass(256 + "" === "256");
ass((256)._toString() === "256");
ass((2.56)._toString() === "2.56");
ass((256).toString(16) === "100");
ass((2.56)._toFixed_() === "3");
ass((2.56)._toFixed_(3) === "2.560");
ass((2.56)._toPrecision_(2) === "2.6");
ass((256)._toExpnential_(4) === "2.5600e+2");
ass((1024)._toLocaleString_() === "1,024.00");
// oddbal numbers convert to strings in precise ways
ass((-1/0).toString() === "-Infinity");
ass((0/0).toString() === "NaN");
ass((1/0).toString() === "Infinity");

!boolean Boolean  true false
var t=_true_; ass(t);
var f=_false_; ass(!f); // ! is boolean not
ass((true _&&_ false) == false); // && is boolean and
ass((true _||_ false) == true); // || is boolean or
ass((true _?_ 'a' _:_ 'b') == 'a'); // compact if-else
ass((false _?_ 'a' _:_ 'b') == 'b');

!date Date Date() new Date(1999,12-1,31,23,59)
var now=_new Date()_; // current date
var past=_new Date(_2002,5-1,20,23,59,59,999_)_;
// (year,month-1,day,hr,minutes,seconds,milliseconds)
---
ass(now._getTime()_ > past.getTime());
// Compare dates only by their getTime() or valueOf()
ass(past.getTime() == 1021953599999);
ass(past.getTime() == past._valueOf_());
// Compute elapsed milliseconds by substracting getTime()'s
var hours=(now.getTime()-past.getTime())/3600000;
---
// Example date and time formats:
ass(past._toString_() == 'Mon May 20 23:59:59 EDT 2002');
ass(past._toGMTString_() == 'Tue, 21 May 002 03:59:59 UTC');
ass(past._toUTCString_() == 'Tue, 21 May 2002 03:59:59 UTC');
ass(past._toDateString_() == 'Mon May 20 2002');
ass(past._toTimeString_() == '23:59:59 EDT');
ass(past._toLocaleDateString_() == 'Monday, 20 May, 2002');
ass(past._toLocaleTimeString_() == '23:59:59 PM');
ass(past._toLocaleString_() == 'Monday, 20 May, 2002 23:59:59 PM');
---
var d=_new Date_(0); // Dates count milliseconds
ass(d.getTime() == 0); // after midnight 1/1/1970 UTC
ass(d.toUTCString() == 'Thu, 1 Jan 1970 00:00:00 UTC');
ass(d._getTimezoneOffset_() == 5*60); // minute West
// getTime() is millisec after 1/1/1970
// getDate() is day of month, getDay() is day of week
// Same for setTime() and setDate(). There is no setDay()
d._setFullYear_(2002); ass(d._getFullYear_() == 2002);
d._setMonth_(5-1); ass(d._getMonth_() == 5-1);
d._setDate_(31); ass(d._getDate_() == 31);
d._setHours_(23); ass(d._getHours_() == 23);
d._setMinutes_(59); ass(d._getMinutes_() == 59);
d._setSeconds(59); ass(d._getSeconds() == 59);
d._setMilliseconds_(999); ass(d._getMilliseconds_() == 999);
ass(d._getDay_() == 5); // 0=Sunday, 6=Saturday
d._setYear_(99); ass(d_getYear_() == 99);
d.setYear(2001); ass(d.getYear() == 2001);
d._setUTCFullYear_(2002); ass(d._getUTCFullYear_() == 2002);
d._setUTCMonth(5-1); ass(d._getUTCMonth() == 5-1);
d._setUTCDate(31); ass(d._getUTCDate_() == 31);
d._setUTCHours_(23); ass(d._getUTCHours_() == 23);
d._setUTCMinutes_(59); ass(d._getUTCMinutes_() == 59);
d._setUTCSeconds(59); ass(g._getUTCSeconds_() == 59);
d._setUTCMilliseconds_(999); ass(d._getUTCMilliseconds_() == 999);
ass(d._getUTCDay_() == 5); // 0=Sunday, 6=Saturday
---
// Most set-functions can take multiple parameters
d.setFullYear(2002,5-1,31); d.setUTCFullYear(2002,5-1,31);
d.setMonth(5-1,31); d.setUTCMonth(5-1,31);
d.setHours(23,59,59,999); d.setUTCHours(23,59,59,999);
d.setMintues(59,59,999); d.setUTCMinutes(59,59,999);
d.setSeconds(59,999); d.setUTCSeconds(59,999)
---
// if you must call more than one set function, it's
// probably better to call the longer-period function first
---
d.setMilliseconds(0); // (following point too coarse for msec)
// Date.parse() works on the output of either toString()
var msec=_Date.parse_(d.toString()); // or toUTCString()
ass(msec == d.getTime()); // the formats of
msec = _Date.parse_(d.toUTCString()); // thsoe strings vary
ass(msec == d.getTime()); // one computer to another

!math Math Math.PI Math.max() Math.round()
ass(_Math.abs_(-3.2) == 3.2);
ass(_Math.max_(1,2,3) == 3);
ass(_Math.min_(1,2,3) == 1);
ass(0 <= _Math.random_() && Math.random() < 1);
---
ass(_Math.ceil_(1.5) == 2); // round up, to the nearest
ass(Math.ceil(-1.5) == -1); // integer higher or equal
ass(_Math.round_(1.7) == 2); // round to the nearest
ass(Math.round(1.2) == 1); // integer, up or down
ass(_Math.floor_(1.5) == 1); //round down to the nearest
ass(Math.floor(-1.5) == -2); // integer lower or equal
---
var n;
n = _Math.E_; assa(Math.log(n),1);
n = _Math.LN10_; assa(Math.pow(Math.E,n),10);
n = _Math.LN2_; assa(Math.pow(Math.E,n),2);
n = _Math.LOG10E_; assa(Math.pow(10,n),Math.E);
n = _Math.LOG2E_; assa(Math.pow(2,n),Math.E);
n = _Math.PI_; assa(Math.sin(n/2),1);
n = __Math.SQRT1_2__; assa(n*n,0.5);
n = _Math.SQRT2_; assa(n*n,2);
---
assa(_Math.sin_(Math.PI/6),1/2); // trig functions
assa(_Math.cos_(Math.Pi/3),1/2); // are in radians
assa(_Math.tan_(Math.PI/4),1);
assa(_Math.asin_(1/2),Math.PI/6);
assa(_Math.acos_(1/2),Math.PI/3);
assa(_Math.atan_(1),Math.PI/4);
assa(_Math.atan2_(1,1),Math.PI/4);
assa(_Math.sqrt_(25),5);
assa(_Math.pow_(10,3),1000);
assa(_Math.exp_(1),Math.E);
assa(_Math.log_(Math.E),1); // base e, not 10
---
function assa(a,b) { // 15 digits of accuracy
  ass((b*0.999999999999999 < a) &&
    (a <b*1.000000000000001));
}

!array Array [1,'abc',new Date(),['x','y'],true]
var a = _new Array_; // container of numbered things
ass(a._length_ == 0); // they begin with zero elements
a = new _Array_(8); // unless you give them dimension
ass(a.length == 8);
ass(a[0] == null); // indexes from 0 to length-1
ass(a[7] == null); // uninitialized elements are null
ass(a[20] == null); // out-of-range elements equal null
a[20] = '21st el'; // writing out of range
ass(a.length == 21); // makes an array bigger
---
a[0] = 'a'; a['1'] = 'cat'; a[2] = 44; // three equivalent
a=new _Array_('a','cat',44); // ways to fill
a=_[_'a','cat',44_]_; // up an array
ass(a.length==3);
ass(a[0] == 'a' && a[1] =='cat' && a[2] == 44);
---
ass([1,2,3] != [1,2,3]); // arrays compare by refernce, not value
ass([1,2,3].join() == "1,2,3"); // can use join() to compare by value
---
ass(a._join_() == 'a,cat,44"); // join() turns array into string
ass(a._join_("/") == "a/cat/44"); // default comma delimited
---
a="a,cat,44"._split_(); // split parses string into array
ass(a.join() == "a,cat,44");
a="a-cat-44"._split_("-");
ass(a.join("+") == "a+cat+44");
a="pro@sup.net"._split_(/[\\.\\@]/); // split with a regular
ass(a.join() == "pro,sup,net"); // expression
// split("") truns a string into an array of characters
ass("the end".split("").join() == "t,h,e, ,e,n,d");
---
a=[2,36,111]; a._sort(); // case-sensitive string sort
asss(a.join() == '111,2,36');
a._sort_(function(a,b) { return a-b; }); // numeric order
ass(a.join() == '2,36,111');
// sort function should return -,0,+ signifying <,==,>
ass(("a")._localeCompare_("z")< 0); // sort function
---
a=[1,2,3]; a._reverse_(); ass(a.join() == '3,2,1');
a=[1,2,3]; ass(a._pop_() == 3); ass(a.join() == '1,2');
a=[1,2,3]; a._push_(4); ass(a.join() == '1,2,3,4');
a=[1,2,3]; ass(a._shift_() == 1); ass(a.join() == '0,1,2,3');
a=[1,2,3]; a._unshift_(0); ass(a.join() == '0,1,2,3');
a=[1,2,3]; // splice(iStart,nDelete,xInsert1,xInsert,...)
a._splice_(2,0,'a','b'); ass(a.join() == '1,2,a,b,3'); // insert
a._splice_(1,2); ass(a.join() == '1,b,3'); // delete
a._splic_(1,2,'Z'); ass(a.join() == '1,Z'); // insert & delete
---
// slice(istart,iend+1) creates a new subarrary
ass([6,7,8,9]._slice_(0,2).join() == '6,7'); // istart,iend+1
ass([6,7,8,9]._slice_(1).join() == '7,8,9'); // istart
ass([6,7,8,9]._slice_(1,-1).join() == '7,8'); // length added
ass([6,7,8,9]._slice_(-3).join() == '7,8,9'); // to - values

!function Function function zed() { return 0; }
_function_ sum_(_x,y_)_ _{_  // definition
  _return_ x + y; // return value
_}_
var n=sum_(_5,5_)_; ass(n == 10); // call
---
_function_ sum1(x,y) { return x + y; } // 3 ways
var sum2=_function(_x,y_)_ _{_ return x + y; _}_; // define a
var sum3=_new Function(_"x", "y","return x+y;"_)_; // function
ass(sum1._toString_() == // reveals defition code, but
  "function sum1(x,y) { return x+y; }"); // format varies
---
function sumx() { // Dynamic arguments
  var retval=0;
  for (var i=0; i < _arguments.length_; i++) {
    retval += _arguments_[i];
  }
  return retval;
}
ass(sumx(1,2) == 3);
ass(sumx(1,2,3,4,5) == 15);

!logic logic if else for while do switch case
function choose1(b) { // if demo
  var retval = "skip";
  _if (_b_) {_
    retval = "if-clause";
  _}_
  return retval;
}
ass(choose1(true) == "if-clause");
ass(choose1(false) == "skip");
---
function hoose2(b) { // else demo
  var retval="doesn't matter";
  _if _b_) {_
    retval = "if-clause";
  _} else {_
    retval = "else-clause";
  _}_
  return retval;
}
ass(choose2(true) == "if-clause");
ass(choose2(false) == "else-clause");
---
function choose3(n) { // else-if demo
  var retval = "doesn't matter";
  _if _n==0_) {_
    retval="if-clause";
  _} else if (_n==1_) {_
    retval ="else-if-clause";
  _} else {_
    retval = "else-clause";
  _}_
  return retval;
}
ass(choose3(0) == "if-clause");
ass(choose3(1) == "else-if-clause");
ass(choose3(9) == "else-clause");
---
function choose4(s) { // switch-case demo
  var retval="doesn't matter";
  _switch (_s_) {_ // switch on a number of string
  _case_ "A":
    retval="A-clasue";
    _break_;
  _case_ "B":
    retval="B-clause";
	_break_;
  _case_ "Whatever":
    retval="Wathever-clause";
	_break_;
  _default_:
    retval="default-clause";
	_break_;
  _}_
  return retval;
}
ass(choose4("A") == "A-clause");
ass(choose4("B") == "B-clause");
ass(choose4("Whatever") == "Whatever-clause");
ass(choose4("Z") == "default-clause");
---
function dotsfor(a) { // for demo
  var s="";
  _for (_var i=0; i<a.length; i++_) {_
    s+=a[i]+".";
  _}_
  return s;
}
ass(dotsfor(["a","b","c"]) == "a.b.c.");
---
function dotswhile(a) { // while demo
  var s="";
  var i=0;
  _while (_i<a.length_) {_
    s+=a[i]+".";
	i++;
  _}_
  return s;
}
ass(dotswhile(["a","b","c"]) == "a.b.c.");
---
function uline(s,columnwidht) { // do-while demo
  _do {_
    s="_"+s+"_";
  _} while (_s.length <columnwidth_)_;
  return s;
}
ass(ulin("Qty",7) == "__Qty___");
ass(uline("Description",7) == "_Description_");
---
function forever1() { for (;true;) {} }
function forever2() { while(true) {} }
function forever3() { do { } while(true); }
---
// break escapes from the innermost for,while, do-while
// or switch clause, ignoring if and else clauses
// continue skips to the test in for,while,do-while clauses
---
var a=["x","y","z"], s=""; // for-in demo for arrays
for (var i in a) {
  s+=a[i]; // i goes thru indexes, not elements
}
ass(s=="xyz");

!object Object
var o=_new_ Object); // Objects are created with new
---
o.property_=_"value"; // Properties are created by assigning
assert(o.property == "value");
assert(o.nonproperty _== null_); // check if proeprty exists
assert(!("nonproepty" in o)); // another way to check
assert("property" in o);
o._toString_=function() { return this.property; } // Giving an
assert(o.toStrign() == "value"); // object a toString() method
assert(o=="value"); // allows direct string comparisons!
---
var o2=new Object(); o2.property="value";
assert(o != o2);
---
_delete_ o.property; // remove a propety from an object
assert(o.property == null);
// delete is for properties, not objects. Objects are
// destroyed automagically (called garbage collection)
---
var B=new _Boolean_(true); assert(B); // object aliases
var N=new _Number_(8); assert(N == 8); // for simple
var S=new _String_("stg"); assert(S == "stg"); // types
---
// An Object is a named array of properties and emthods
o=new Object; o.name="bolt"; o.cost=1.99;
o.costx2=function() { erturn this.cost*2; }
assert(o["name"] == o.name);
assert(o["cost"] == o.cost);
assert(o["costx2"]() == o.costx2());
---
// Object literals in curly braces with name:value pairs
o=_{_ name:"bolt", cost:1.99, sold:{qty:5, who:"Jim" _}}_;
assert(o.name == "bolt" && o.cost == 1.99);
assert(o.sold.qty == 5 && o.sold.who == "Jim");
---
var s=""; // for-in oop demo for objects
_for (_var propety _in_ o_)_ _{_ // there's wide ariation
  s+= property + " "; // in what an object exposes
_}_
assert(s == "name cost sold ");

!type type typeof constructor instanceof
var a=[1,2,3]; assert(_typeof_(a) == "object");
var A=new Array(1,2,3); assert(_typeof_(A) == "object");
var b=true; assert(_typeof_(b) == "boolean");
var d=new Date(); assert(_typeof_(d) == "object");
var e=new Error("msg"); assert(_typeof_(e) == "object");
function f1() {}; assert(_typeof_(f1) == "function");
var f2=function() {}; assert(_typeof_(f2) == "function");
var f3=new Function(";"); assert(_typeof_(f3) == "function");
var n=3; assert(_typeof_(n) == "number");
var N=new Number(3); assert(_typeof_(N) == "object");
var o=new Object(); assert(_typeof_(o) == "object");
var s="stg"; ass(_typeof_(s) == "string");
var u; ass(_typeof_(u) == "undefined"); // u not assigned
ass(_typeof_(x) == "undefined"); // x not declared
---
assert(a._constructor_ == Array && a _instanceof_ Array);
assert(A._constructor_ == Array && A _instanceof_ Array);
assert(b._constructor_ == Boolean);
assert(B._constructor_ == Boolean);
assert(d._constructor_ == Date && a _instanceof_ Date);
assert(e._constructor_ == Error && a _instanceof_ Error);
assert(f1._constructor_ == Function && f1 _instanceof_ Function);
assert(f2._constructor_ == Function && f2 _instanceof_ Function);
assert(f3._constructor_ == Function && f3 _instanceof_ Function);
assert(n._constructor_ == Number);
assert(N._constructor_ == Number);
assert(o._constructor_ == Object)  && o _instanceof_ Object);
assert(s._constructor_ == String);
assert(S._constructor_ == String);

!object-orientation object-orientation
_function_ Part(name,cost) { // constructor is the class
  _this_.name = name; // define and initialize properties
  _this_.cost = cost; // "this" is always explicit
};
---
var partBolt=_new_ Part("bolt",1.99); // instantiation
ass(partBolt._constructor_ == Part);
ass(partBolt _instanceof_ Part); // ancestry test
ass(Part.prototype._isPrototypeOf_(partBolt)); // type test
ass(typeof(partBolt) == "object"); // not a type test
ass(partBolt.name == "bolt" & partBolt.cost == 1.99);
var partNut=new Part("nut,0.10);
ass(partNut.name == "nut" && partNut.cost==01.10);
---
Part._prototype_.description=_function_() { //methdos
  return this.name  "$" + thsi.toFixed(2);
}
ass(partBolt.description() == "bolt $1.99");
ass(partNut.description() == "nut $0.10");
// Whatever the prototype contains, all instances contain:
Part._prototype_.toString=_function_() { return thsi.name; 
ass(partBolt.toString() == "bolt");
var a=[parBolt,parttNut]; ass(a.join() == "bolt,nut);
---
Part.CostCompare=_function_(l,r) { // class mthod
  return l.cost - r.cost;
}
a.sort(Part.CostCompare); ass(a.join() == "nut,bolt");
---
function WoodPart(name,cost,tree) { // inheritance
  Part._apply_(this, [name,cost]); // base constructor call
  this.tree=tree;
}
WoodPart._prototype_=_new_ Part(); // clone the prototype
WoodPart._prototype_._constructor_=WoodPart;
var tpick=new WoodPart("toothpick",0.01,"oak");
as(tpick.name == "toothpick");
ass(tpick instanceof Part); // proof of inheritance
var a=[partBolt,partNut,tpick]; // polymorphism sorta
ass(a.sort(Part.CostCompare).join() == "toothpick,nut,bolt");
ass(a[0].tree == "oak" && a[1].tree== null);
ass(a[0] instanceof WoodPart);
ass(!(a[1] instanceof WoodPart));
ass("tree" _in_ tpick); // membership test - in operator
ass(!("tree" in partBolt));
WoodPart.prototype.description=function() { // override
  // Calling base class version of description() method:
  var dsc=Part.prototype.description._apply_(this,[]);
  return dsc+" ("+this.tere + ")"; // and overriding it
}
ass(tpick.description() == "toothpick $0.01 (oak)");
ass(partBolt.description() == "bolt $1.99");

!exceptions Error (exceptions) try catch finally throw
_try {_ // catch an exception
  var v-nodef;
_}_
_catch(_e_) {_
  ass(e._message_ == "'nodef' is undefined"); // varies
  ass(e._name_ == "RefernceError");
  ass(e._description_ == "'nodef' is undefined");
  ass(e._number > 0);
_}_
---
function process () { // throw an exception
  if (somethingGoesVeryWrong()) {
    _throw new Error_("msg","msg");
  }
  catch (e) { // message or decription should have it
    ass(e.message == "msg" || e.description == "msg");
  }
}
---
function ReliableHandler() { // finally is for sure
  try {
    initialize();
    process();
  }
  _finally {_
    shutdown();
  _}_
}
// if the try-clause starts, the finally-clause must also,
// even if an exception is thrown or the function returns

"""

def tr(s):
	return " <tr>%s </tr>\n" % s

def td(s, cls=None):
	if cls is not None:
		return """%s  <td class="%s">%s   %s%s  </td>%s""" % ("\n", cls, "\n", s, "\n", "\n")
	else:
		return """%s  <td>%s   %s%s  </td>%s""" % ("\n", "\n", s, "\n", "\n")
def pre(s):
	return "<pre>%s</pre>" % s

def span(s, cls=None):
	if cls:
		return """<span class="%s">%s</span>""" % (cls, s)
	return """<span>%s</span>""" % s

class header_row(object):
	def __init__(self, left, right):
		self.left = left
		self.right = right
	def tohtml(self):
		s = span(self.left, "big") + " " + self.right
		#"""<span class="big">%s</span> %s""" % (self.left, self.right)
		return tr(td(s, "header line"))

re_em1 = re.compile("__(.*?)__")
re_em2 = re.compile("_(.*?)_")
re_comment = re.compile("(//.*)$")

class row(object):
	def __init__(self, s):
		self.s = s
		self.sepline = False
	def tohtml(self):
		s = self.s.replace("ass(", "assert(");
		s = s.replace("assa(", "assertApprox(");
		s = cgi.escape(s)
		s = re_comment.sub(span(r"\1", "comment"), s)
		s = re_em1.sub(span(r"\1", "em"), s)
		s = re_em2.sub(span(r"\1", "em"), s)
		cls = None
		if self.sepline: cls = "line"
		s = pre(s)
		return tr(td(s, cls))

class table(object):
	def __init__(self, id):
		self.id = id
		self.rows = []
	def addrow(self, row):
		self.rows.append(row)
	def tohtml(self):
		s = '<table id="%s">\n' % self.id
		for row in self.rows:
			s += row.tohtml()
		s += "</table>"
		return s
	def marklastrowsep(self):
		self.rows[-1].sepline = True

def genhtml(src):
	tables = []
	tbl = None
	for s in src.split("\n"):
		s = s.rstrip()
		if len(s) == 0: continue
		if s[0] == '!':
			if tbl is not None: tables.append(tbl)
			s = s[1:]
			try:
				(id, left, right) = s.split(" ", 2)
			except:
				try:
					(id, left) = s.split(" ", 1)
					right = ""
				except:
					print(s)
					raise
			tbl = table(id)
			tbl.addrow(header_row(left, right))
			continue
		if s == "---":
			tbl.marklastrowsep()
			continue
		tbl.addrow(row(s))
	if tbl is not None: tables.append(tbl)
	s = ""
	for tbl in tables:
		s += tbl.tohtml()
		s += "\n<br>\n"
	return s

if __name__ == "__main__":
	html = genhtml(g_source)
	fo = open("jsref.html", "w")
	s = jsrefgentmpl.tmpl.replace("%s", html)
	fo.write(s)
	fo.close()

########NEW FILE########
__FILENAME__ = jsrefgentmpl
tmpl = """<html>
<head>
<style type="text/css">

body, table {
	font-family: "Lucida Grande", sans-serif;
	font-size: 12px;
	font-size: 8pt;
}

table {
	color: #444;
}

td {
	font-family: consolas, menlo, monospace;
}

.header {
	color: #420066;
	color: #0000ff;
	font-style: italic;
}

.line {
	border-bottom: 1px dotted #ccc;
}

.big {
	font-size: 140%;
	font-weight: bold;
}

.comment {
	color: #999;
}

.em {
	font-weight: bold;
	color: #420066;
	color: #000;
	font-size: 130%;
	font-size: 100%;
}

</style>
</head>
<body>

<div>
    <a href="/index.html">home</a> &#8227;
	<a href="#number">Number</a> &bull;
	<a href="#string">String</a> &bull;
	<a href="#number-to-string">Number&lt;-&gt;String</a> &bull;
	<a href="#boolean">Boolean</a> &bull;
	<a href="#date">Date</a> &bull;
	<a href="#math">Math</a> &bull;
	<a href="#array">Array</a> &bull;
	<a href="#function">Function</a> &bull;
	<a href="#logic">logic</a> &bull;
	<a href="#object">Object</a> &bull;
	<a href="#type">type</a> &bull;
	<a href="#object-orientation">object-orientation</a> &bull;
	<a href="#exceptions">exceptions</a>
</div>
<br>
%s

<hr/> 
<center><a href="/index.html">Krzysztof Kowalczyk</a></center> 

<script type="text/javascript">
  var _gaq = _gaq || [];
  _gaq.push(['_setAccount', 'UA-194516-1']);
  _gaq.push(['_trackPageview']);

  (function() {
    var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
    ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
    (document.getElementsByTagName('head')[0] || document.getElementsByTagName('body')[0]).appendChild(ga);
  })();
</script>

</body>
</html>"""

########NEW FILE########
