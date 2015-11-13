__FILENAME__ = haproxy-dconv
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2012 Cyril Bonté
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''
TODO : ability to split chapters into several files
TODO : manage keyword locality (server/proxy/global ; ex : maxconn)
TODO : Remove global variables where possible
'''
import os
import subprocess
import sys
import cgi
import re
import time
import datetime

from optparse import OptionParser

from mako.template import Template
from mako.lookup import TemplateLookup
from mako.exceptions import TopLevelLookupException

from parser import PContext
from parser import remove_indent
from parser import *

from urllib import quote

VERSION = ""
HAPROXY_GIT_VERSION = False

def main():
    global VERSION, HAPROXY_GIT_VERSION

    usage="Usage: %prog --infile <infile> --outfile <outfile>"

    optparser = OptionParser(description='Generate HTML Document from HAProxy configuation.txt',
                          version=VERSION,
                          usage=usage)
    optparser.add_option('--infile', '-i', help='Input file mostly the configuration.txt')
    optparser.add_option('--outfile','-o', help='Output file')
    optparser.add_option('--base','-b', default = '', help='Base directory for relative links')
    (option, args) = optparser.parse_args()

    if not (option.infile  and option.outfile) or len(args) > 0:
        optparser.print_help()
        exit(1)

    option.infile = os.path.abspath(option.infile)
    option.outfile = os.path.abspath(option.outfile)

    os.chdir(os.path.dirname(__file__))

    VERSION = get_git_version()
    if not VERSION:
        sys.exit(1)

    HAPROXY_GIT_VERSION = get_haproxy_git_version(os.path.dirname(option.infile))

    convert(option.infile, option.outfile, option.base)


# Temporarily determine the version from git to follow which commit generated
# the documentation
def get_git_version():
    if not os.path.isdir(".git"):
        print >> sys.stderr, "This does not appear to be a Git repository."
        return
    try:
        p = subprocess.Popen(["git", "describe", "--tags", "--match", "v*"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except EnvironmentError:
        print >> sys.stderr, "Unable to run git"
        return
    version = p.communicate()[0]
    if p.returncode != 0:
        print >> sys.stderr, "Unable to run git"
        return

    if len(version) < 2:
        return

    version = version[1:].strip()
    version = re.sub(r'-g.*', '', version)
    return version

def get_haproxy_git_version(path):
    try:
        p = subprocess.Popen(["git", "describe", "--tags", "--match", "v*"], cwd=path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except EnvironmentError:
        return False
    version = p.communicate()[0]

    if p.returncode != 0:
        return False

    if len(version) < 2:
        return False

    version = version[1:].strip()
    version = re.sub(r'-g.*', '', version)
    return version

def getTitleDetails(string):
    array = string.split(".")

    title    = array.pop().strip()
    chapter  = ".".join(array)
    level    = max(1, len(array))
    if array:
        toplevel = array[0]
    else:
        toplevel = False

    return {
            "title"   : title,
            "chapter" : chapter,
            "level"   : level,
            "toplevel": toplevel
    }

# Parse the whole document to insert links on keywords
def createLinks():
    global document, keywords, keywordsCount, keyword_conflicts, chapters

    print >> sys.stderr, "Generating keywords links..."

    delimiters = [
        dict(start='&quot;', end='&quot;', multi=True ),
        dict(start='- '    , end='\n'    , multi=False),
    ]

    for keyword in keywords:
        keywordsCount[keyword] = 0
        for delimiter in delimiters:
            keywordsCount[keyword] += document.count(delimiter['start'] + keyword + delimiter['end'])
        if (keyword in keyword_conflicts) and (not keywordsCount[keyword]):
            # The keyword is never used, we can remove it from the conflicts list
            del keyword_conflicts[keyword]

        if keyword in keyword_conflicts:
            chapter_list = ""
            for chapter in keyword_conflicts[keyword]:
                chapter_list += '<li><a href="#%s">%s</a></li>' % (quote("%s (%s)" % (keyword, chapters[chapter]['title'])), chapters[chapter]['title'])
            for delimiter in delimiters:
                if delimiter['multi']:
                    document = document.replace(delimiter['start'] + keyword + delimiter['end'],
                            delimiter['start'] + '<span class="dropdown">' +
                            '<a class="dropdown-toggle" data-toggle="dropdown" href="#">' +
                            keyword +
                            '<span class="caret"></span>' +
                            '</a>' +
                            '<ul class="dropdown-menu">' +
                            '<li class="dropdown-header">This keyword is available in sections :</li>' +
                            chapter_list +
                            '</ul>' +
                            '</span>' + delimiter['end'])
                else:
                    document = document.replace(delimiter['start'] + keyword + delimiter['end'], delimiter['start'] + '<a href="#' + quote(keyword) + '">' + keyword + '</a>' + delimiter['end'])
        else:
            for delimiter in delimiters:
                document = document.replace(delimiter['start'] + keyword + delimiter['end'], delimiter['start'] + '<a href="#' + quote(keyword) + '">' + keyword + '</a>' + delimiter['end'])
        if keyword.startswith("option "):
            shortKeyword = keyword[len("option "):]
            keywordsCount[shortKeyword] = 0
            for delimiter in delimiters:
                keywordsCount[keyword] += document.count(delimiter['start'] + shortKeyword + delimiter['end'])
            if (shortKeyword in keyword_conflicts) and (not keywordsCount[shortKeyword]):
            # The keyword is never used, we can remove it from the conflicts list
                del keyword_conflicts[shortKeyword]
            for delimiter in delimiters:
                document = document.replace(delimiter['start'] + shortKeyword + delimiter['start'], delimiter['start'] + '<a href="#' + quote(keyword) + '">' + shortKeyword + '</a>' + delimiter['end'])

def documentAppend(text, retline = True):
    global document
    document += text
    if retline:
        document += "\n"

def init_parsers(pctxt):
    return [
        underline.Parser(pctxt),
        arguments.Parser(pctxt),
        seealso.Parser(pctxt),
        example.Parser(pctxt),
        table.Parser(pctxt),
        underline.Parser(pctxt),
        keyword.Parser(pctxt),
    ]

# The parser itself
def convert(infile, outfile, base=''):
    global document, keywords, keywordsCount, chapters, keyword_conflicts

    if len(base) > 0 and base[:-1] != '/':
	base += '/'

    hasSummary = False

    data = []
    fd = file(infile,"r")
    for line in fd:
        line.replace("\t", " " * 8)
        line = line.rstrip()
        data.append(line)
    fd.close()

    pctxt = PContext(
        TemplateLookup(
            directories=[
                'templates'
            ]
        )
    )

    parsers = init_parsers(pctxt)

    pctxt.context = {
            'headers':      {},
            'document':     ""
    }

    sections = []
    currentSection = {
            "details": getTitleDetails(""),
            "content": "",
    }

    chapters = {}

    keywords = {}
    keywordsCount = {}

    specialSections = {
            "default": {
                    "hasKeywords": True,
            },
            "4.1": {
                    "hasKeywords": True,
            },
    }

    pctxt.keywords = keywords
    pctxt.keywordsCount = keywordsCount
    pctxt.chapters = chapters

    print >> sys.stderr, "Importing %s..." % infile

    nblines = len(data)
    i = j = 0
    while i < nblines:
        line = data[i].rstrip()
        if i < nblines - 1:
            next = data[i + 1].rstrip()
        else:
            next = ""
        if (line == "Summary" or re.match("^[0-9].*", line)) and (len(next) > 0) and (next[0] == '-') \
                and ("-" * len(line)).startswith(next):  # Fuzzy underline length detection
            sections.append(currentSection)
            currentSection = {
                "details": getTitleDetails(line),
                "content": "",
            }
            j = 0
            i += 1 # Skip underline
            while not data[i + 1].rstrip():
                i += 1 # Skip empty lines

        else:
            if len(line) > 80:
                print >> sys.stderr, "Line `%i' exceeds 80 columns" % (i + 1)

            currentSection["content"] = currentSection["content"] + line + "\n"
            j += 1
            if currentSection["details"]["title"] == "Summary" and line != "":
		hasSummary = True
                # Learn chapters from the summary
                details = getTitleDetails(line)
                if details["chapter"]:
                    chapters[details["chapter"]] = details
        i += 1
    sections.append(currentSection)

    chapterIndexes = sorted(chapters.keys())

    document = ""

    # Complete the summary
    for section in sections:
        details = section["details"]
        title = details["title"]
        if title:
            fulltitle = title
            if details["chapter"]:
                #documentAppend("<a name=\"%s\"></a>" % details["chapter"])
                fulltitle = details["chapter"] + ". " + title
                if not details["chapter"] in chapters:
                    print >> sys.stderr, "Adding '%s' to the summary" % details["title"]
                    chapters[details["chapter"]] = details
                    chapterIndexes = sorted(chapters.keys())

    for section in sections:
        details = section["details"]
        pctxt.details = details
        level = details["level"]
        title = details["title"]
        content = section["content"].rstrip()

        print >> sys.stderr, "Parsing chapter %s..." % title

        if (title == "Summary") or (title and not hasSummary):
            summaryTemplate = pctxt.templates.get_template('summary.html')
            documentAppend(summaryTemplate.render(
                chapters = chapters,
                chapterIndexes = chapterIndexes,
            ))
            if title and not hasSummary:
                hasSummary = True
            else:
                continue

        if title:
            documentAppend('<a class="anchor" id="%s" name="%s"></a>' % (details["chapter"], details["chapter"]))
            if level == 1:
                documentAppend("<div class=\"page-header\">", False)
            documentAppend('<h%d id="chapter-%s" data-target="%s"><small><a class="small" href="#%s">%s.</a></small> %s</h%d>' % (level, details["chapter"], details["chapter"], details["chapter"], details["chapter"], cgi.escape(title, True), level))
            if level == 1:
                documentAppend("</div>", False)

        if content:
            if False and title:
                # Display a navigation bar
                documentAppend('<ul class="well pager">')
                documentAppend('<li><a href="#top">Top</a></li>', False)
                index = chapterIndexes.index(details["chapter"])
                if index > 0:
                    documentAppend('<li class="previous"><a href="#%s">Previous</a></li>' % chapterIndexes[index - 1], False)
                if index < len(chapterIndexes) - 1:
                    documentAppend('<li class="next"><a href="#%s">Next</a></li>' % chapterIndexes[index + 1], False)
                documentAppend('</ul>', False)
            content = cgi.escape(content, True)
            content = re.sub(r'section ([0-9]+(.[0-9]+)*)', r'<a href="#\1">section \1</a>', content)

            pctxt.set_content(content)

            if not title:
                lines = pctxt.get_lines()
                pctxt.context['headers'] = {
                        'title':        lines[1].strip(),
                        'subtitle':     lines[2].strip(),
                        'version':      lines[4].strip(),
                        'author':       lines[5].strip(),
                        'date':         lines[6].strip()
                }
                if HAPROXY_GIT_VERSION:
                    pctxt.context['headers']['version'] = 'version ' + HAPROXY_GIT_VERSION

                # Skip header lines
                pctxt.eat_lines()
                pctxt.eat_empty_lines()

            documentAppend('<div>', False)

            delay = []
            while pctxt.has_more_lines():
                try:
                    specialSection = specialSections[details["chapter"]]
                except:
                    specialSection = specialSections["default"]

                line = pctxt.get_line()
                if i < nblines - 1:
                    nextline = pctxt.get_line(1)
                else:
                    nextline = ""

                oldline = line
                pctxt.stop = False
                for parser in parsers:
                    line = parser.parse(line)
                    if pctxt.stop:
                        break
                if oldline == line:
                    # nothing has changed,
                    # delays the rendering
                    if delay or line != "":
                        delay.append(line)
                    pctxt.next()
                elif pctxt.stop:
                    while delay and delay[-1].strip() == "":
                        del delay[-1]
                    if delay:
                        remove_indent(delay)
                        documentAppend('<pre class="text">%s\n</pre>' % "\n".join(delay), False)
                    delay = []
                    documentAppend(line, False)
                else:
                    while delay and delay[-1].strip() == "":
                        del delay[-1]
                    if delay:
                        remove_indent(delay)
                        documentAppend('<pre class="text">%s\n</pre>' % "\n".join(delay), False)
                    delay = []
                    documentAppend(line, True)
                    pctxt.next()

            while delay and delay[-1].strip() == "":
                del delay[-1]
            if delay:
                remove_indent(delay)
                documentAppend('<pre class="text">%s\n</pre>' % "\n".join(delay), False)
            delay = []
            documentAppend('</div>')

    if not hasSummary:
        summaryTemplate = pctxt.templates.get_template('summary.html')
        print chapters
        document = summaryTemplate.render(
            chapters = chapters,
            chapterIndexes = chapterIndexes,
        ) + document


    # Log warnings for keywords defined in several chapters
    keyword_conflicts = {}
    for keyword in keywords:
        keyword_chapters = list(keywords[keyword])
        keyword_chapters.sort()
        if len(keyword_chapters) > 1:
            print >> sys.stderr, 'Multi section keyword : "%s" in chapters %s' % (keyword, list(keyword_chapters))
            keyword_conflicts[keyword] = keyword_chapters

    keywords = list(keywords)
    keywords.sort()

    createLinks()

    # Add the keywords conflicts to the keywords list to make them available in the search form
    # And remove the original keyword which is now useless
    for keyword in keyword_conflicts:
        sections = keyword_conflicts[keyword]
        offset = keywords.index(keyword)
        for section in sections:
            keywords.insert(offset, "%s (%s)" % (keyword, chapters[section]['title']))
            offset += 1
        keywords.remove(keyword)

    print >> sys.stderr, "Exporting to %s..." % outfile

    template = pctxt.templates.get_template('template.html')
    try:
	footerTemplate = pctxt.templates.get_template('footer.html')
	footer = footerTemplate.render(
            headers = pctxt.context['headers'],
            document = document,
            chapters = chapters,
            chapterIndexes = chapterIndexes,
            keywords = keywords,
            keywordsCount = keywordsCount,
            keyword_conflicts = keyword_conflicts,
            version = VERSION,
            date = datetime.datetime.now().strftime("%Y/%m/%d"),
	)
    except TopLevelLookupException:
	footer = ""

    fd = open(outfile,'w')

    print >> fd, template.render(
            headers = pctxt.context['headers'],
            base = base,
            document = document,
            chapters = chapters,
            chapterIndexes = chapterIndexes,
            keywords = keywords,
            keywordsCount = keywordsCount,
            keyword_conflicts = keyword_conflicts,
            version = VERSION,
            date = datetime.datetime.now().strftime("%Y/%m/%d"),
            footer = footer
    )
    fd.close()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = arguments
import sys
import re
import parser

'''
TODO: Allow inner data parsing (this will allow to parse the examples provided in an arguments block)
'''
class Parser(parser.Parser):
    def __init__(self, pctxt):
        parser.Parser.__init__(self, pctxt)
        #template = pctxt.templates.get_template("parser/arguments.tpl")
        #self.replace = template.render().strip()

    def parse(self, line):
        #return re.sub(r'(Arguments *:)', self.replace, line)
        pctxt = self.pctxt

        result = re.search(r'(Arguments? *:)', line)
        if result:
            label = result.group(0)
            content = []

            desc_indent = False
            desc = re.sub(r'.*Arguments? *:', '', line).strip()

            indent = parser.get_indent(line)

            pctxt.next()
            pctxt.eat_empty_lines()

            arglines = []
            if desc != "none":
                add_empty_lines = 0
                while pctxt.has_more_lines() and (parser.get_indent(pctxt.get_line()) > indent):
                    for j in xrange(0, add_empty_lines):
                        arglines.append("")
                    arglines.append(pctxt.get_line())
                    pctxt.next()
                    add_empty_lines = pctxt.eat_empty_lines()
                    '''
                    print line

                    if parser.get_indent(line) == arg_indent:
                        argument = re.sub(r' *([^ ]+).*', r'\1', line)
                        if argument:
                            #content.append("<b>%s</b>" % argument)
                            arg_desc = [line.replace(argument, " " * len(self.unescape(argument)), 1)]
                            #arg_desc = re.sub(r'( *)([^ ]+)(.*)', r'\1<b>\2</b>\3', line)
                            arg_desc_indent = parser.get_indent(arg_desc[0])
                            arg_desc[0] = arg_desc[0][arg_indent:]
                            pctxt.next()
                            add_empty_lines = 0
                            while pctxt.has_more_lines and parser.get_indent(pctxt.get_line()) >= arg_indent:
                                for i in xrange(0, add_empty_lines):
                                    arg_desc.append("")
                                arg_desc.append(pctxt.get_line()[arg_indent:])
                                pctxt.next()
                                add_empty_lines = pctxt.eat_empty_lines()
                            # TODO : reduce space at the beginnning
                            content.append({
                                'name': argument,
                                'desc': arg_desc
                            })
                    '''

                if arglines:
                    new_arglines = []
                    #content = self.parse_args(arglines)
                    parser.remove_indent(arglines)
                    '''
                    pctxt2 = parser.PContext(pctxt.templates)
                    pctxt2.set_content_list(arglines)
                    while pctxt2.has_more_lines():
                        new_arglines.append(parser.example.Parser(pctxt2).parse(pctxt2.get_line()))
                        pctxt2.next()
                    arglines = new_arglines
                    '''

            pctxt.stop = True

            template = pctxt.templates.get_template("parser/arguments.tpl")
            return template.render(
                label=label,
                desc=desc,
                content=arglines
                #content=content
            )
            return line

        return line

'''
    def parse_args(self, data):
        args = []

        pctxt = parser.PContext()
        pctxt.set_content_list(data)

        while pctxt.has_more_lines():
            line = pctxt.get_line()
            arg_indent = parser.get_indent(line)
            argument = re.sub(r' *([^ ]+).*', r'\1', line)
            if True or argument:
                arg_desc = []
                trailing_desc = line.replace(argument, " " * len(self.unescape(argument)), 1)[arg_indent:]
                if trailing_desc.strip():
                    arg_desc.append(trailing_desc)
                pctxt.next()
                add_empty_lines = 0
                while pctxt.has_more_lines() and parser.get_indent(pctxt.get_line()) > arg_indent:
                    for i in xrange(0, add_empty_lines):
                        arg_desc.append("")
                    arg_desc.append(pctxt.get_line()[arg_indent:])
                    pctxt.next()
                    add_empty_lines = pctxt.eat_empty_lines()

                parser.remove_indent(arg_desc)

                args.append({
                    'name': argument,
                    'desc': arg_desc
                })
        return args

    def unescape(self, s):
        s = s.replace("&lt;", "<")
        s = s.replace("&gt;", ">")
        # this has to be last:
        s = s.replace("&amp;", "&")
        return s
'''
########NEW FILE########
__FILENAME__ = example
import re
import parser

# Detect examples blocks
class Parser(parser.Parser):
    def __init__(self, pctxt):
        parser.Parser.__init__(self, pctxt)
        template = pctxt.templates.get_template("parser/example/comment.tpl")
        self.comment = template.render().strip()


    def parse(self, line):
        pctxt = self.pctxt

        result = re.search(r'(Examples? *:)', line)
        if result:
            label = result.group(0)

            desc_indent = False
            desc = re.sub(r'.*Examples? *:', '', line).strip()

            # Some examples have a description
            if desc:
                desc_indent = len(line) - len(desc)

            indent = parser.get_indent(line)

            if desc:
                # And some description are on multiple lines
                while pctxt.get_line(1) and parser.get_indent(pctxt.get_line(1)) == desc_indent:
                    desc += " " + pctxt.get_line(1).strip()
                    pctxt.next()

            pctxt.next()
            add_empty_line = pctxt.eat_empty_lines()

            content = []

            if parser.get_indent(pctxt.get_line()) > indent:
                if desc:
                    desc = desc[0].upper() + desc[1:]
                add_empty_line = 0
                while pctxt.has_more_lines() and ((not pctxt.get_line()) or (parser.get_indent(pctxt.get_line()) > indent)):
                    if pctxt.get_line():
                        for j in xrange(0, add_empty_line):
                            content.append("")

                        content.append(re.sub(r'(#.*)$', self.comment, pctxt.get_line()))
                        add_empty_line = 0
                    else:
                        add_empty_line += 1
                    pctxt.next()
            elif parser.get_indent(pctxt.get_line()) == indent:
                # Simple example that can't have empty lines
                if add_empty_line and desc:
                    # This means that the example was on the same line as the 'Example' tag
                    # and was not a description
                    content.append(" " * indent + desc)
                    desc = False
                else:
                    while pctxt.has_more_lines() and (parser.get_indent(pctxt.get_line()) >= indent):
                        content.append(pctxt.get_line())
                        pctxt.next()
                    pctxt.eat_empty_lines() # Skip empty remaining lines

            pctxt.stop = True

            parser.remove_indent(content)

            template = pctxt.templates.get_template("parser/example.tpl")
            return template.render(
                label=label,
                desc=desc,
                content=content
            )
        return line

########NEW FILE########
__FILENAME__ = keyword
import re
import parser
from urllib import quote

class Parser(parser.Parser):
    def __init__(self, pctxt):
        parser.Parser.__init__(self, pctxt)
        self.keywordPattern = re.compile(r'^(%s%s)(%s)' % (
            '([a-z][a-z0-9\-_\.]*[a-z0-9\-_)])', # keyword
            '( [a-z0-9\-_]+)*',                  # subkeywords
            '(\([^ ]*\))?',   # arg (ex: (<backend>), (<frontend>/<backend>), (<offset1>,<length>[,<offset2>]) ...
        ))

    def parse(self, line):
        pctxt = self.pctxt
        keywords = pctxt.keywords
        keywordsCount = pctxt.keywordsCount
        chapters = pctxt.chapters

        res = ""

        if line != "" and not re.match(r'^ ', line):
            parsed = self.keywordPattern.match(line)
            if parsed != None:
                keyword = parsed.group(1)
                arg     = parsed.group(4)
                parameters = line[len(keyword) + len(arg):]
                if (parameters != "" and not re.match("^ +((&lt;|\[|\{|/).*|(: [a-z +]+))?(\(deprecated\))?$", parameters)):
                    # Dirty hack
                    # - parameters should only start with the characer "<", "[", "{", "/"
                    # - or a column (":") followed by a alpha keywords to identify fetching samples (optionally separated by the character "+")
                    # - or the string "(deprecated)" at the end
                    keyword = False
                else:
                    splitKeyword = keyword.split(" ")

                parameters = arg + parameters
            else:
                keyword = False

            if keyword and (len(splitKeyword) <= 5):
                toplevel = pctxt.details["toplevel"]
                for j in xrange(0, len(splitKeyword)):
                    subKeyword = " ".join(splitKeyword[0:j + 1])
                    if subKeyword != "no":
                        if not subKeyword in keywords:
                            keywords[subKeyword] = set()
                        keywords[subKeyword].add(pctxt.details["chapter"])
                    res += '<a class="anchor" name="%s"></a>' % subKeyword
                    res += '<a class="anchor" name="%s-%s"></a>' % (toplevel, subKeyword)
                    res += '<a class="anchor" name="%s-%s"></a>' % (pctxt.details["chapter"], subKeyword)
                    res += '<a class="anchor" name="%s (%s)"></a>' % (subKeyword, chapters[toplevel]['title'])
                    res += '<a class="anchor" name="%s (%s)"></a>' % (subKeyword, chapters[pctxt.details["chapter"]]['title'])

                deprecated = parameters.find("(deprecated)")
                if deprecated != -1:
                    prefix = ""
                    suffix = ""
                    parameters = parameters.replace("(deprecated)", '<span class="label label-warning">(deprecated)</span>')
                else:
                    prefix = ""
                    suffix = ""

                nextline = pctxt.get_line(1)

                while nextline.startswith("   "):
                    # Found parameters on the next line
                    parameters += "\n" + nextline
                    pctxt.next()
                    if pctxt.has_more_lines(1):
                        nextline = pctxt.get_line(1)
                    else:
                        nextline = ""


                parameters = self.colorize(parameters)
                res += '<div class="keyword">%s<b><a class="anchor" name="%s"></a><a href="#%s">%s</a></b>%s%s</div>' % (prefix, keyword, quote("%s-%s" % (pctxt.details["chapter"], keyword)), keyword, parameters, suffix)
                pctxt.next()
                pctxt.stop = True
            elif line.startswith("/*"):
                # Skip comments in the documentation
                while not pctxt.get_line().endswith("*/"):
                    pctxt.next()
                pctxt.next()
            else:
                # This is probably not a keyword but a text, ignore it
                res += line
        else:
            res += line

        return res

    # Used to colorize keywords parameters
    # TODO : use CSS styling
    def colorize(self, text):
        colorized = ""
        tags = [
                [ "["   , "]"   , "#008" ],
                [ "{"   , "}"   , "#800" ],
                [ "&lt;", "&gt;", "#080" ],
        ]
        heap = []
        pos = 0
        while pos < len(text):
            substring = text[pos:]
            found = False
            for tag in tags:
                if substring.startswith(tag[0]):
                    # Opening tag
                    heap.append(tag)
                    colorized += '<span style="color: %s">%s' % (tag[2], substring[0:len(tag[0])])
                    pos += len(tag[0])
                    found = True
                    break
                elif substring.startswith(tag[1]):
                    # Closing tag

                    # pop opening tags until the corresponding one is found
                    openingTag = False
                    while heap and openingTag != tag:
                        openingTag = heap.pop()
                        if openingTag != tag:
                            colorized += '</span>'
                    # all intermediate tags are now closed, we can display the tag
                    colorized += substring[0:len(tag[1])]
                    # and the close it if it was previously opened
                    if openingTag == tag:
                        colorized += '</span>'
                    pos += len(tag[1])
                    found = True
                    break
            if not found:
                colorized += substring[0]
                pos += 1
        # close all unterminated tags
        while heap:
            tag = heap.pop()
            colorized += '</span>'

        return colorized



########NEW FILE########
__FILENAME__ = seealso
import re
import parser

class Parser(parser.Parser):
    def parse(self, line):
        pctxt = self.pctxt

        result = re.search(r'(See also *:)', line)
        if result:
            label = result.group(0)

            desc = re.sub(r'.*See also *:', '', line).strip()

            indent = parser.get_indent(line)

            # Some descriptions are on multiple lines
            while pctxt.has_more_lines(1) and parser.get_indent(pctxt.get_line(1)) >= indent:
                desc += " " + pctxt.get_line(1).strip()
                pctxt.next()

            pctxt.eat_empty_lines()
            pctxt.next()
            pctxt.stop = True

            template = pctxt.templates.get_template("parser/seealso.tpl")
            return template.render(
                label=label,
                desc=desc,
            )

        return line

########NEW FILE########
__FILENAME__ = table
import re
import sys
import parser

class Parser(parser.Parser):
    def __init__(self, pctxt):
        parser.Parser.__init__(self, pctxt)
        self.table1Pattern = re.compile(r'^ *(-+\+)+-+')
        self.table2Pattern = re.compile(r'^ *\+(-+\+)+')

    def parse(self, line):
        global document, keywords, keywordsCount, chapters, keyword_conflicts

        pctxt = self.pctxt

        if pctxt.context['headers']['subtitle'] != 'Configuration Manual':
            # Quick exit
            return line
        elif pctxt.details['chapter'] == "4":
            # BUG: the matrix in chapter 4. Proxies is not well displayed, we skip this chapter
            return line

        if pctxt.has_more_lines(1):
            nextline = pctxt.get_line(1)
        else:
            nextline = ""

        if self.table1Pattern.match(nextline):
            # activate table rendering only for the Configuration Manual
            lineSeparator = nextline
            nbColumns = nextline.count("+") + 1
            extraColumns = 0
            print >> sys.stderr, "Entering table mode (%d columns)" % nbColumns
            table = []
            if line.find("|") != -1:
                row = []
                while pctxt.has_more_lines():
                    line = pctxt.get_line()
                    if pctxt.has_more_lines(1):
                        nextline = pctxt.get_line(1)
                    else:
                        nextline = ""
                    if line == lineSeparator:
                        # New row
                        table.append(row)
                        row = []
                        if nextline.find("|") == -1:
                            break # End of table
                    else:
                        # Data
                        columns = line.split("|")
                        for j in xrange(0, len(columns)):
                            try:
                                if row[j]:
                                    row[j] += "<br />"
                                row[j] += columns[j].strip()
                            except:
                                row.append(columns[j].strip())
                    pctxt.next()
            else:
                row = []
                headers = nextline
                while pctxt.has_more_lines():
                    line = pctxt.get_line()
                    if pctxt.has_more_lines(1):
                        nextline = pctxt.get_line(1)
                    else:
                        nextline = ""

                    if nextline == "":
                        if row: table.append(row)
                        break # End of table

                    if (line != lineSeparator) and (line[0] != "-"):
                        start = 0

                        if row and not line.startswith(" "):
                            # Row is complete, parse a new one
                            table.append(row)
                            row = []

                        tmprow = []
                        while start != -1:
                            end = headers.find("+", start)
                            if end == -1:
                                end = len(headers)

                            realend = end
                            if realend == len(headers):
                                realend = len(line)
                            else:
                                while realend < len(line) and line[realend] != " ":
                                    realend += 1
                                    end += 1

                            tmprow.append(line[start:realend])

                            start = end + 1
                            if start >= len(headers):
                                start = -1
                        for j in xrange(0, nbColumns):
                            try:
                                row[j] += tmprow[j].strip()
                            except:
                                row.append(tmprow[j].strip())

                        deprecated = row[0].endswith("(deprecated)")
                        if deprecated:
                            row[0] = row[0][: -len("(deprecated)")].rstrip()

                        nooption = row[1].startswith("(*)")
                        if nooption:
                            row[1] = row[1][len("(*)"):].strip()

                        if deprecated or nooption:
                            extraColumns = 1
                            extra = ""
                            if deprecated:
                                extra += '<span class="label label-warning">(deprecated)</span>'
                            if nooption:
                                extra += '<span>(*)</span>'
                            row.append(extra)

                    pctxt.next()
            print >> sys.stderr, "Leaving table mode"
            pctxt.next() # skip useless next line
            pctxt.stop = True

            return self.renderTable(table, nbColumns, pctxt.details["toplevel"])
        # elif self.table2Pattern.match(line):
        #    return self.parse_table_format2()
        elif line.find("May be used in sections") != -1:
            nextline = pctxt.get_line(1)
            rows = []
            headers = line.split(":")
            rows.append(headers[1].split("|"))
            rows.append(nextline.split("|"))
            table = {
                    "rows": rows,
                    "title": headers[0]
            }
            pctxt.next(2)  # skip this previous table
            pctxt.stop = True

            return self.renderTable(table)

        return line


    def parse_table_format2(self):
        pctxt = self.pctxt

        linesep = pctxt.get_line()
        rows = []

        pctxt.next()
        maxcols = 0
        while pctxt.get_line().strip().startswith("|"):
            row = pctxt.get_line().strip()[1:-1].split("|")
            rows.append(row)
            maxcols = max(maxcols, len(row))
            pctxt.next()
            if pctxt.get_line() == linesep:
                # TODO : find a way to define a special style for next row
                pctxt.next()
        pctxt.stop = True

        return self.renderTable(rows, maxcols)

    # Render tables detected by the conversion parser
    def renderTable(self, table, maxColumns = 0, toplevel = None):
        pctxt  = self.pctxt
        template = pctxt.templates.get_template("parser/table.tpl")

        res = ""

        title = None
        if isinstance(table, dict):
            title = table["title"]
            table = table["rows"]

        if not maxColumns:
            maxColumns = len(table[0])

        rows = []

        mode = "th"
        headerLine = ""
        hasKeywords = False
        i = 0
        for row in table:
            line = ""

            if i == 0:
                row_template = pctxt.templates.get_template("parser/table/header.tpl")
            else:
                row_template = pctxt.templates.get_template("parser/table/row.tpl")

            if i > 1 and (i  - 1) % 20 == 0 and len(table) > 50:
                # Repeat headers periodically for long tables
                rows.append(headerLine)

            j = 0
            cols = []
            for column in row:
                if j >= maxColumns:
                    break

                tplcol = {}

                data = column.strip()
                keyword = column
                if j == 0 and i == 0 and keyword == 'keyword':
                    hasKeywords = True
                if j == 0 and i != 0 and hasKeywords:
                    if keyword.startswith("[no] "):
                        keyword = keyword[len("[no] "):]
                    tplcol['toplevel'] = toplevel
                    tplcol['keyword'] = keyword
                tplcol['extra'] = []
                if j == 0 and len(row) > maxColumns:
                    for k in xrange(maxColumns, len(row)):
                        tplcol['extra'].append(row[k])
                tplcol['data'] = data
                cols.append(tplcol)
                j += 1
            mode = "td"

            line = row_template.render(
                columns=cols
            ).strip()
            if i == 0:
                headerLine = line

            rows.append(line)

            i += 1

        return template.render(
            title=title,
            rows=rows
        )

########NEW FILE########
__FILENAME__ = underline
import parser

class Parser(parser.Parser):
    # Detect underlines
    def parse(self, line):
        pctxt = self.pctxt
        if pctxt.has_more_lines(1):
            nextline = pctxt.get_line(1)
            if (len(line) > 0) and (len(nextline) > 0) and (nextline[0] == '-') and ("-" * len(line) == nextline):
                template = pctxt.templates.get_template("parser/underline.tpl")
                line = template.render(data=line).strip()
                pctxt.next(2)
                pctxt.eat_empty_lines()
                pctxt.stop = True

        return line

########NEW FILE########
