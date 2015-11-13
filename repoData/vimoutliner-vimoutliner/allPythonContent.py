__FILENAME__ = otl2html
#!/usr/bin/python2
# otl2html.py
# convert a tab-formatted outline from VIM to HTML
#
# Copyright 2001 Noel Henson All rights reserved
#
# ALPHA VERSION!!!

###########################################################################
# Basic function
#
#    This program accepts text outline files and converts them
#    to HTML.  The outline levels are indicated by tabs. A line with no
#    tabs is assumed to be part of the highest outline level.
#
#    10 outline levels are supported.  These loosely correspond to the
#    HTML H1 through H9 tags.  Alphabetic, numeric and bullet formats
#    are also supported.
#
#    CSS support has been added.
#

###########################################################################
# include whatever mdules we need

import sys
import re
import os
import time

###########################################################################
# global variables

formatMode = "indent"
copyright = ""
level = 0
div = 0
silentdiv = 0
slides = 0
hideComments = 0
showTitle = 1
inputFile = ""
outline = []
flatoutline = []
inBodyText = 0        # 0: no, 1: text, 2: preformatted text, 3: table
styleSheet = "nnnnnn.css"
inlineStyle = 0

###########################################################################
# function definitions

# usage
# print the simplest form of help
# input: none
# output: simple command usage is printed on the console


def showUsage():
    print """
    Usage:
        otl2html.py [options] inputfile > outputfile
    Options
        -p              Presentation: slide show output for use with
                        HtmlSlides.
        -D              First-level is divisions (<div> </div>) for making
                        pretty web pages.
        -s sheet        Use the specified style sheet with a link. This is the
                        default.
        -S sheet        Include the specified style sheet in-line the
                        output. For encapsulated style.
        -T              The first line is not the title. Treat it as
                        outline data
        -c              comments (line with [ as the first non-whitespace
                        character. Ending with ] is optional.
        -C copyright    Override the internal copyright notice with the
                        one supplied in the quoted string following this
                        flag. Single or double quotes can be used.
        -H              Show the file syntax help.
    output is on STDOUT
      Note: if neither -s or -S are specified, otl2html.py will default
            to -s. It will try to use the css file 'nnnnnn.css' if it
            exists. If it does not exist, it will be created automatically.
    """


def showSyntax():
    print """
    Syntax
    Syntax is Vim Outliner's normal syntax. The following are supported:

        Text
    :    Body text marker. This text will wrap in the output.
    ;    Preformmated text. This text will will not wrap.

        Tables
    ||    Table header line.
    |    Table and table columns. Example:
            || Name | Age | Animal |
            | Kirby | 9 | Dog |
            | Sparky | 1 | Bird |
            | Sophia | 8 | Cat |
            This will cause an item to be left-justified.
                | whatever  |
            This will cause an item to be right-justified.
                |  whatever |
            This will cause an item to be centered.
                |  whatever  |
            This will cause an item to be default aligned.
                | whatever |

        Character Styles
    **    Bold. Example: **Bold Text**
    //    Italic. Example: //Italic Text//
    +++    Highlight. Example: +++Highlight Text+++
    ---    Strikeout. Example: ---Strikeout Text---
    Insane    ---+++//**Wow! This is insane!**//+++---
        Just remember to keep it all on one line.
        Horizontal Rule
    ----------------------------------------  (40 dashes).
        Copyright
    (c) or (C)    Converts to a standard copyright symbol.

        Including Images (for web pages)
    [imagename]    Examples:
            [logo.gif] [photo.jpg] [car.png]
            [http://i.a.cnn.net/cnn/.element/img/1.1/logo/logl.gif]
            or from a database:
            [http://www.lab.com/php/image.php?id=4]

        Including links (for web pages)
    [link text-or-image]    Examples:
            [about.html About] [http://www.cnn.com CNN]
            or with an image:
            [http://www.ted.com [http://www.ted.com/logo.png]]
            Links starting with a '+' will be opened in a new
            window. Eg. [+about.html About]

        Including external files
    !filename!    Examples:
            !file.txt!

        Including external outlines (first line is parent)
    !!filename!!    Examples:
            !!menu.otl!!

        Including output from executing external programs
    !!!program args!!!    Examples:
            !!!date +%Y%m%d!!!

        Note:
    When using -D, the top-level headings become divisions (<div>)
    and will be created using a class of the heading name. Spaces
    are not allowed. If a top-level heading begins with '_', it
    will not be shown but the division name will be the same as
    without the '_'. Example: _Menu will have a division name of
    Menu and will not be shown.
    """


# getArgs
# Check for input arguments and set the necessary switches
# input: none
# output: possible console output for help, switch variables may be set
def getArgs():
    global inputFile, debug, formatMode, slides, hideComments, copyright, \
        styleSheet, inlineStyle, div, showTitle
    if (len(sys.argv) == 1):
        showUsage()
        sys.exit()()
    else:
        for i in range(len(sys.argv)):
            if (i != 0):
                if (sys.argv[i] == "-d"):
                    debug = 1                   # test for debug flag
                elif (sys.argv[i] == "-?"):     # test for help flag
                    showUsage()                 # show the help
                    sys.exit()                  # exit
                elif (sys.argv[i] == "-p"):     # test for the slides flag
                    slides = 1                  # set the slides flag
                elif (sys.argv[i] == "-D"):     # test for the divisions flag
                    div = 1                     # set the divisions flag
                elif (sys.argv[i] == "-T"):     # test for the no-title flag
                    showTitle = 0               # clear the show-title flag
                elif (sys.argv[i] == "-c"):     # test for the comments flag
                    hideComments = 1            # set the comments flag
                elif (sys.argv[i] == "-C"):     # test for the copyright flag
                    copyright = sys.argv[i + 1]  # get the copyright
                    i = i + 1                   # increment the pointer
                elif (sys.argv[i] == "-s"):     # test for the style sheet flag
                    styleSheet = sys.argv[i + 1]  # get the style sheet name
                    formatMode = "indent"       # set the format
                    i = i + 1                   # increment the pointer
                elif (sys.argv[i] == "-S"):     # test for the style sheet flag
                    styleSheet = sys.argv[i + 1]  # get the style sheet name
                    formatMode = "indent"       # set the format
                    inlineStyle = 1
                    i = i + 1                   # increment the pointer
                elif (sys.argv[i] == "--help"):
                    showUsage()
                    sys.exit()
                elif (sys.argv[i] == "-h"):
                    showUsage()
                    sys.exit()
                elif (sys.argv[i] == "-H"):
                    showSyntax()
                    sys.exit()
                elif (sys.argv[i][0] == "-"):
                    print "Error!  Unknown option.  Aborting"
                    sys.exit()
                else:                           # get the input file name
                    inputFile = sys.argv[i]


# getLineLevel
# get the level of the current line (count the number of tabs)
# input: linein - a single line that may or may not have tabs at the beginning
# output: returns a number 1 is the lowest
def getLineLevel(linein):
    strstart = linein.lstrip()      # find the start of text in line
    x = linein.find(strstart)       # find the text index in the line
    n = linein.count("\t", 0, x)    # count the tabs
    return(n + 1)                   # return the count + 1 (for level)


# getLineTextLevel
# get the level of the current line (count the number of tabs)
# input: linein - a single line that may or may not have tabs at the
#        beginning
# output: returns a number 1 is the lowest
def getLineTextLevel(linein):
    strstart = linein.lstrip()         # find the start of text in line
    x = linein.find(strstart)        # find the text index in the line
    n = linein.count("\t", 0, x)     # count the tabs
    n = n + linein.count(" ", 0, x)  # count the spaces
    return(n + 1)                     # return the count + 1 (for level)


# colonStrip(line)
# stip a leading ':', if it exists
# input: line
# output: returns a string with a stipped ':'
def colonStrip(line):
    if (line[0] == ":"):
        return line[1:].lstrip()
    else:
        return line


# semicolonStrip(line)
# stip a leading ';', if it exists
# input: line
# output: returns a string with a stipped ';'
def semicolonStrip(line):
    if (line[0] == ";"):
        return line[1:]
    else:
        return line


# dashStrip(line)
# stip a leading '-', if it exists
# input: line
# output: returns a string with a stipped '-'
def dashStrip(line):
    if (line[0] == "-"):
        return line[1:]
    else:
        return line


# pipeStrip(line)
# stip a leading '|', if it exists
# input: line
# output: returns a string with a stipped '|'
def pipeStrip(line):
    if (line[0] == "|"):
        return line[1:]
    else:
        return line


# plusStrip(line)
# stip a leading '+', if it exists
# input: line
# output: returns a string with a stipped '+'
def plusStrip(line):
    if (line[0] == "+"):
        return line[1:]
    else:
        return line


# handleBodyText
# print body text lines with a class indicating level, if style sheets
# are being used. otherwise print just <p>
# input: linein - a single line that may or may not have tabs at the beginning
# output: through standard out
def handleBodyText(linein, lineLevel):
    global inBodyText
    if (inBodyText == 2):
        print "</pre>"
    if (inBodyText == 3):
        print "</table>"
    print "<p",
    if (styleSheet != ""):
        print " class=\"P" + str(lineLevel) + "\"",
        inBodyText = 1
    print ">" + colonStrip(linein.strip()),


# handlePreformattedText
# print preformatted text lines with a class indicating level, if style sheets
# are being used. otherwise print just <pre>
# input: linein - a single line that may or may not have tabs at the beginning
# output: through standard out
def handlePreformattedText(linein, lineLevel):
    global inBodyText
    if (inBodyText == 1):
        print "</p>"
    if (inBodyText == 3):
        print "</table>"
    print "<pre",
    if (styleSheet != ""):
        print " class=\"PRE" + str(lineLevel) + "\"",
        inBodyText = 2
    print ">" + semicolonStrip(linein.strip()),


# isAlignRight
# return flag
# input: coldata, a string
def isAlignRight(coldata):
    l = len(coldata)
    if (coldata[0:2] == "  ") and (coldata[l - 2:l] != "  "):
        return 1
    else:
        return 0


# isAlignLeft
# return flag
# input: coldata, a string
def isAlignLeft(coldata):
    l = len(coldata)
    if (coldata[0:2] != "  ") and (coldata[l - 2:l] == "  "):
        return 1
    else:
        return 0


# isAlignCenter
# return flag
# input: coldata, a string
def isAlignCenter(coldata):
    l = len(coldata)
    if (coldata[0:2] == "  ") and (coldata[l - 2:l] == "  "):
        return 1
    else:
        return 0


# getColumnAlignment(string)
# return string
# input: coldata
# output:
#   <td align="left"> or <td align="right"> or <td align="center"> or <td>
def getColumnAlignment(coldata):
    if isAlignCenter(coldata):
        return '<td align="center">'
    if isAlignRight(coldata):
        return '<td align="right">'
    if isAlignLeft(coldata):
        return '<td align="left">'
    return '<td>'


# handleTableColumns
# return the souce for a row's columns
# input: linein - a single line that may or may not have tabs at the beginning
# output: string with the columns' source
def handleTableColumns(linein, lineLevel):
    out = ""
    coldata = linein.strip()
    coldata = coldata.split("|")
    for i in range(1, len(coldata) - 1):
        out += getColumnAlignment(coldata[i])
        out += coldata[i].strip() + '</td>'
    return out


# handleTableHeaders
# return the souce for a row's headers
# input: linein - a single line that may or may not have tabs at the beginning
# output: string with the columns' source
def handleTableHeaders(linein, lineLevel):
    out = ""
    coldata = linein.strip()
    coldata = coldata.split("|")
    for i in range(2, len(coldata) - 1):
        out += getColumnAlignment(coldata[i])
        out += coldata[i].strip() + '</td>'
    out = out.replace('<td', '<th')
    out = out.replace('</td', '</th')
    return out


# handleTableRow
# print a table row
# input: linein - a single line that may or may not have tabs at the beginning
# output: out
def handleTableRow(linein, lineLevel):
    out = "<tr>"
    if (lineLevel == linein.find("|| ") + 1):
        out += handleTableHeaders(linein, lineLevel)
    else:
        out += handleTableColumns(linein, lineLevel)
    out += "</tr>"
    return out


# handleTable
# print a table, starting with a <TABLE> tag if necessary
# input: linein - a single line that may or may not have tabs at the beginning
# output: through standard out
def handleTable(linein, lineLevel):
    global inBodyText
    if (inBodyText == 1):
        print "</p>"
    if (inBodyText == 2):
        print "</pre>"
    if (inBodyText != 3):
        print "<table class=\"TAB" + str(lineLevel) + "\">"
        inBodyText = 3
    print handleTableRow(linein, lineLevel),


# linkOrImage
# if there is a link to an image or another page, process it
# input: line
# output: modified line
def linkOrImage(line):
    line = re.sub('\[(\S+?)\]', '<img src="\\1" alt="\\1">', line)
    line = re.sub('\[(\S+)\s(.*?)\]', '<a href="\\1">\\2</a>', line)
    line = re.sub('(<a href=")\+(.*)"\>', '\\1\\2" target=_new>', line)
    line = line.replace('<img src="X" alt="X">', '[X]')
    line = line.replace('<img src="_" alt="_">', '[_]')
    return line


# tabs
# return a string with 'count' tabs
# input: count
# output: string of tabs
def tabs(count):
    out = ""
    if (count == 0):
        return ""
    for i in range(0, count - 1):
        out = out + "\t"
    return out


# includeFile
# include the specified file, if it exists
# input: line and lineLevel
# output: line is replaced by the contents of the file
def includeFile(line, lineLevel):
    filename = re.sub('!(\S+?)!', '\\1', line.strip())
    incfile = open(filename, "r")
    linein = incfile.readline()
    while linein != "":
        linein = re.sub('^', tabs(lineLevel), linein)
        processLine(linein)
        linein = incfile.readline()
    incfile.close()
    return


# includeOutline
# include the specified file, if it exists
# input: line and lineLevel
# output: line is replaced by the contents of the file
def includeOutline(line, lineLevel):
    filename = re.sub('!!(\S+?)!!', '\\1', line.strip())
    incfile = open(filename, "r")
    linein = incfile.readline()
    linein = re.sub('^', tabs(lineLevel), linein)
    processLine(linein)
    linein = incfile.readline()
    while linein != "":
        linein = re.sub('^', tabs(lineLevel + 1), linein)
        processLine(linein)
        linein = incfile.readline()
    incfile.close()
    return


# execProgram
# execute the specified program
# input: line
# output: program specified is replaced by program output
def execProgram(line):
    program = re.sub('.*!!!(.*)!!!.*', '\\1', line.strip())
    child = os.popen(program)
    out = child.read()
    err = child.close()
    out = re.sub('!!!(.*)!!!', out, line)
    processLine(out)
    if err:
        raise RuntimeError('%s failed w/ exit code %d' % (program, err))
    return


# divName
# create a name for a division
# input: line
# output: division name
def divName(line):
    global silentdiv
    line = line.strip()
    if (line[0] == '_'):
        silentdiv = 1
        line = line[1:]
    line = line.replace(' ', '_')
    return'<div class="' + line + '">'


# getTitleText(line)
# extract some meaningful text to make the document title from the line
# input: line
# output: modified line
def getTitleText(line):
    out = re.sub('.*#(.*)#.*', '\\1', line)
    out = re.sub('<.*>', '', out)
#  if (out != ""): out = re.sub('\"(.*?)\"', '\\1', line)
    return(out)


# stripTitleText(line)
# strip the title text if it is enclosed in double-quotes
# input: line
# output: modified line
def stripTitleText(line):
    out = re.sub('#\W*.*#', '', line)
    return(out)


# beautifyLine(line)
# do some optional, simple beautification of the text in a line
# input: line
# output: modified line
def beautifyLine(line):
    if (line.strip() == "-" * 40):
        return "<br><hr><br>"

    out = line
    line = ""

    while (line != out):
        line = out
        # out = replace(out, '---', '<strike>', 1)
        if (line[0].lstrip() != ";"):
            out = re.sub('\-\-\-(.*?)\-\-\-', '<strike>\\1</strike>', out)
        out = linkOrImage(out)
        # out = replace(out, '**', '<strong>', 1)
        out = re.sub('\*\*(.*?)\*\*', '<strong>\\1</strong>', out)
        # out = replace(out, '//', '<i>', 1)
        out = re.sub('\/\/(.*?)\/\/', '<i>\\1</i>', out)
        # out = replace(out, '+++', '<code>', 1)
        out = re.sub('\+\+\+(.*?)\+\+\+', '<code>\\1</code>', out)
        out = re.sub('\(c\)', '&copy;', out)
        out = re.sub('\(C\)', '&copy;', out)
    return out


# closeLevels
# generate the number of </ul> or </ol> tags necessary to proplerly finish
# input: format - a string indicating the mode to use for formatting
#        level - an integer between 1 and 9 that show the current level
#               (not to be confused with the level of the current line)
# output: through standard out
def closeLevels():
    global level, formatMode
    while (level > 0):
        if (formatMode == "bullets"):
            print "</ul>"
        if (formatMode == "alpha") or (formatMode == "numeric") or \
                (formatMode == "roman") or (formatMode == "indent"):
            print "</ol>"

        level = level - 1


# processLine
# process a single line
# input: linein - a single line that may or may not have tabs at the beginning
#        format - a string indicating the mode to use for formatting
#        level - an integer between 1 and 9 that show the current level
#               (not to be confused with the level of the current line)
# output: through standard out
def processLine(linein):
    global level, formatMode, slides, hideComments, inBodyText, styleSheet, \
        inlineStyle, div, silentdiv
    if (linein.lstrip() == ""):
        return
    linein = beautifyLine(linein)
    lineLevel = getLineLevel(linein)
    if ((hideComments == 0) or (lineLevel != linein.find("[") + 1)):

        if (lineLevel > level):  # increasing depth
            while (lineLevel > level):
                if (formatMode == "indent" or formatMode == "simple"):
                    if (inBodyText == 1):
                        print"</p>"
                        inBodyText = 0
                    elif (inBodyText == 2):
                        print"</pre>"
                        inBodyText = 0
                    elif (inBodyText == 3):
                        print"</table>"
                        inBodyText = 0
                    if not (div == 1 and lineLevel == 1):
                        print "<ol>"
                else:
                    sys.exit("Error! Unknown formatMode type")
                level = level + 1

        elif (lineLevel < level):  # decreasing depth
            while (lineLevel < level):
                if (inBodyText == 1):
                    print"</p>"
                    inBodyText = 0
                elif (inBodyText == 2):
                    print"</pre>"
                    inBodyText = 0
                elif (inBodyText == 3):
                    print"</table>"
                    inBodyText = 0
                print "</ol>"
                level = level - 1
                if (div == 1 and level == 1):
                    if (silentdiv == 0):
                        print'</ol>'
                    else:
                        silentdiv = 0
                    print'</div>'

        else:
            print  # same depth
        if (div == 1 and lineLevel == 1):
            if (lineLevel != linein.find("!") + 1):
                print divName(linein)
                if (silentdiv == 0):
                    print "<ol>"

        if (slides == 0):
            if (lineLevel == linein.find(" ") + 1) or \
                    (lineLevel == linein.find(":") + 1):
                if (inBodyText != 1):
                    handleBodyText(linein, lineLevel)
                elif (colonStrip(linein.strip()) == ""):
                    print "</p>"
                    handleBodyText(linein, lineLevel)
                else:
                    print colonStrip(linein.strip()),
            elif (lineLevel == linein.find(";") + 1):
                if (inBodyText != 2):
                    handlePreformattedText(linein, lineLevel)
                elif (semicolonStrip(linein.strip()) == ""):
                    print "</pre>"
                    handlePreformattedText(linein, lineLevel)
                else:
                    print semicolonStrip(linein.strip()),
            elif (lineLevel == linein.find("|") + 1):
                if (inBodyText != 3):
                    handleTable(linein, lineLevel)
                elif (pipeStrip(linein.strip()) == ""):
                    print "</table>"
                    handleTable(linein, lineLevel)
                else:
                    print handleTableRow(linein, lineLevel),
            elif (lineLevel == linein.find("!!!") + 1):
                execProgram(linein)
            elif (lineLevel == linein.find("!!") + 1):
                includeOutline(linein, lineLevel)
            elif (lineLevel == linein.find("!") + 1):
                includeFile(linein, lineLevel)
            else:
                if (inBodyText == 1):
                    print"</p>"
                    inBodyText = 0
                elif (inBodyText == 2):
                    print"</pre>"
                    inBodyText = 0
                elif (inBodyText == 3):
                    print"</table>"
                    inBodyText = 0
                if (silentdiv == 0):
                    print "<li",
                    if (styleSheet != ""):
                        if (lineLevel == linein.find("- ") + 1):
                            print " class=\"LB" + str(lineLevel) + "\"",
                            print ">" + \
                                  dashStrip(linein.strip()),
                        elif (lineLevel == linein.find("+ ") + 1):
                            print " class=\"LN" + str(lineLevel) + "\"",
                            print ">" + \
                                  plusStrip(linein.strip()),
                        else:
                            print " class=\"L" + str(lineLevel) + "\"",
                            print ">" + linein.strip(),
                else:
                    silentdiv = 0
        else:
            if (lineLevel == 1):
                if (linein[0] == " "):
                    if (inBodyText == 0):
                        handleBodyText(linein, lineLevel)
                    else:
                        print linein.strip(),
                else:
                    print "<address>"
                    print linein.strip(),
                    print "</address>\n"
            else:
                if (lineLevel == linein.find(" ") + 1) or \
                        (lineLevel == linein.find(":") + 1):
                    if (inBodyText == 0):
                        handleBodyText(linein, lineLevel)
                    else:
                        print linein.strip(),
                else:
                    if (inBodyText == 1):
                        print"</p>"
                        inBodyText = 0
                    print "<li",
                    if (styleSheet != ""):
                        print " class=\"LI.L" + str(lineLevel) + "\"",
                    print ">" + linein.strip(),


# flatten
# Flatten a subsection of an outline.  The index passed is the
# outline section title.  All sublevels that are only one level
# deeper are indcluded in the current subsection.  Then there is
# a recursion for those items listed in the subsection.  Exits
# when the next line to be processed is of the same or lower
# outline level.  (lower means shallower)
# input: idx - the index into the outline.  The indexed line is the title.
# output: adds reformatted lines to flatoutline[]
def flatten(idx):
    if (outline[idx] == ""):
        return
    if (len(outline) <= idx):
        return
    titleline = outline[idx]
    titlelevel = getLineLevel(titleline)
    if (getLineLevel(outline[idx + 1]) > titlelevel):
        if (titleline[titlelevel - 1] != " "):
            flatoutline.append(titleline.lstrip())
        exitflag = 0
        while (exitflag == 0):
            if (idx < len(outline) - 1):
                idx = idx + 1
                currlevel = getLineLevel(outline[idx])
                if (currlevel == titlelevel + 1):
                    if (currlevel == outline[idx].find(" ") + 1):
                        flatoutline.append("\t " + outline[idx].lstrip())
                    else:
                        flatoutline.append("\t" + outline[idx].lstrip())
                elif (currlevel <= titlelevel):
                    exitflag = 1
            else:
                exitflag = 1
    # level = titlelevel  # FIXME level assigned but never used
    return


def createCSS():
    global styleSheet
    output = """    /* copyright notice and filename */
    body {
            font-family: helvetica, arial, sans-serif;
            font-size: 10pt;
    }
        /* title at the top of the page */
    H1 {
            font-family: helvetica, arial, sans-serif;
            font-size: 14pt;
            font-weight: bold;
            text-align: center;
            color: black;
        background-color: #ddddee;
        padding-top: 20px;
        padding-bottom: 20px;
    }
    H2 {
            font-family: helvetica, arial, sans-serif;
            font-size: 12pt;
            font-weight: bold;
            text-align: left;
            color: black;
    }
    H3 {
            font-family: helvetica, arial, sans-serif;
            font-size: 12pt;
            text-align: left;
            color: black;
    }
    H4 {
            font-family: helvetica, arial, sans-serif;
            font-size: 12pt;
            text-align: left;
            color: black;
    }
    H5 {
            font-family: helvetica, arial, sans-serif;
            font-size: 10pt;
            text-align: left;
            color: black;
    }
        /* outline level spacing */
    OL {
            margin-left: 1.0em;
            padding-left: 0;
            padding-bottom: 8pt;
    }
        /* global heading settings */
    LI {
            font-family: helvetica, arial, sans-serif;
            color: black;
            font-weight: normal;
            list-style: lower-alpha;
        padding-top: 4px;
    }
        /* level 1 heading overrides */
    LI.L1 {
            font-size: 12pt;
            font-weight: bold;
            list-style: none;
    }
        /* level 2 heading overrides */
    LI.L2 {
            font-size: 10pt;
            font-weight: bold;
            list-style: none;
    }
        /* level 3 heading overrides */
    LI.L3 {
            font-size: 10pt;
            list-style: none;
    }
        /* level 4 heading overrides */
    LI.L4 {
            font-size: 10pt;
            list-style: none;
    }
        /* level 5 heading overrides */
    LI.L5 {
            font-size: 10pt;
            list-style: none;
    }
        /* level 6 heading overrides */
    LI.L6 {
            font-size: 10pt;
            list-style: none;
    }
        /* level 7 heading overrides */
    LI.L7 {
            font-size: 10pt;
            list-style: none;
    }
        /* level 1 bullet heading overrides */
    LI.LB1 {
            font-size: 12pt;
            font-weight: bold;
            list-style: disc;
    }
        /* level 2 bullet heading overrides */
    LI.LB2 {
            font-size: 10pt;
            font-weight: bold;
            list-style: disc;
    }
        /* level 3 bullet heading overrides */
    LI.LB3 {
            font-size: 10pt;
            list-style: disc;
    }
        /* level 4 bullet heading overrides */
    LI.LB4 {
            font-size: 10pt;
            list-style: disc;
    }
        /* level 5 bullet heading overrides */
    LI.LB5 {
            font-size: 10pt;
            list-style: disc;
    }
        /* level 6 bullet heading overrides */
    LI.LB6 {
            font-size: 10pt;
            list-style: disc;
    }
        /* level 7 bullet heading overrides */
    LI.LB7 {
            font-size: 10pt;
            list-style: disc;
    }
        /* level 1 numeric heading overrides */
    LI.LN1 {
            font-size: 12pt;
            font-weight: bold;
            list-style: decimal;
    }
        /* level 2 numeric heading overrides */
    LI.LN2 {
            font-size: 10pt;
            font-weight: bold;
            list-style: decimal;
    }
        /* level 3 numeric heading overrides */
    LI.LN3 {
            font-size: 10pt;
            list-style: decimal;
    }
        /* level 4 numeric heading overrides */
    LI.LN4 {
            font-size: 10pt;
            list-style: decimal;
    }
        /* level 5 numeric heading overrides */
    LI.LN5 {
            font-size: 10pt;
            list-style: decimal;
    }
        /* level 6 numeric heading overrides */
    LI.LN6 {
            font-size: 10pt;
            list-style: decimal;
    }
        /* level 7 numeric heading overrides */
    LI.LN7 {
            font-size: 10pt;
            list-style: decimal;
    }
               /* body text */
    P {
            font-family: helvetica, arial, sans-serif;
            font-size: 9pt;
            font-weight: normal;
            color: darkgreen;
    }
        /* preformatted text */
    PRE {
            font-family: fixed, monospace;
            font-size: 9pt;
            font-weight: normal;
            color: darkblue;
    }

    TABLE {
        margin-top: 1em;
            font-family: helvetica, arial, sans-serif;
            font-size: 12pt;
            font-weight: normal;
        border-collapse: collapse;
    }

    TH {
        border: 1px solid black;
        padding: 0.5em;
        background-color: #eeddee;
    }

    TD {
        border: 1px solid black;
        padding: 0.5em;
        background-color: #ddeeee;
    }

    CODE {
        background-color: yellow;
    }

    TABLE.TAB1 {
        margin-top: 1em;
            font-family: helvetica, arial, sans-serif;
            font-size: 12pt;
            font-weight: normal;
        border-collapse: collapse;
    }
    TABLE.TAB2 {
        margin-top: 1em;
            font-family: helvetica, arial, sans-serif;
            font-size: 11pt;
            font-weight: normal;
        border-collapse: collapse;
    }
    TABLE.TAB3 {
        margin-top: 1em;
            font-family: helvetica, arial, sans-serif;
            font-size: 10pt;
            font-weight: normal;
        border-collapse: collapse;
    }
    TABLE.TAB4 {
        margin-top: 1em;
            font-family: helvetica, arial, sans-serif;
            font-size: 10pt;
            font-weight: normal;
        border-collapse: collapse;
    }
    TABLE.TAB5 {
        margin-top: 1em;
            font-family: helvetica, arial, sans-serif;
            font-size: 10pt;
            font-weight: normal;
        border-collapse: collapse;
    }
    TABLE.TAB6 {
        margin-top: 1em;
            font-family: helvetica, arial, sans-serif;
            font-size: 10pt;
            font-weight: normal;
        border-collapse: collapse;
    """
    file = open(styleSheet, "w")
    file.write(output)


def printHeader(linein):
    global styleSheet, inlineStyle
    print """<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.01 Transitional//EN\"s
        \"http://www.w3.org/TR/html4/strict.dtd\">
    <html><head><title>""" + getTitleText(linein) + "</title></head>"
    try:
        file = open(styleSheet, "r")
    except IOError:
        createCSS()
        file = open(styleSheet, "r")
    if (styleSheet != "" and inlineStyle == 0):
        print "<link href=\"" + styleSheet + \
              "\" rel=\"stylesheet\" type=\"text/css\">"
    if (styleSheet != "" and inlineStyle == 1):
        print "<style type=\"text/css\">"
        csslinein = file.readline()
        while csslinein != "":
            print csslinein,
            csslinein = file.readline()
        file.close()
        print "</style></head>"
    print "<body>"


def printFirstLine(linein):
    print '''<div class="DocTitle">
    <h1>%s</h1>
    </div>
    <div class="MainPage">''' % stripTitleText(linein.strip())


def printFooter():
    global slides, div
    print "</div>"
    if (slides == 0 and div == 0):
        print "<div class=\"Footer\">"
        print "<hr>"
        print copyright
        print "<br>"
        print inputFile + "&nbsp&nbsp " + \
            time.strftime("%Y/%m/%d %H:%M", time.localtime(time.time()))
        print "</div>"
    print "</body></html>"


def main():
    global showTitle
    getArgs()
    file = open(inputFile, "r")
    if (slides == 0):
        firstLine = beautifyLine(file.readline().strip())
        printHeader(firstLine)
        if (showTitle == 1):
            printFirstLine(firstLine)
            linein = beautifyLine(file.readline().strip())
        else:
            linein = firstLine
        while linein != "":
            processLine(linein)
            linein = file.readline()
        closeLevels()
    else:
        linein = beautifyLine(file.readline().strip())
        outline.append(linein)
        linein = file.readline().strip()
        while linein != "":
            outline.append("\t" + linein)
            linein = file.readline().rstrip()
        for i in range(0, len(outline) - 1):
            flatten(i)
        printHeader(flatoutline[0])
        for i in range(0, len(flatoutline)):
            processLine(flatoutline[i])

    printFooter()
    file.close()


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = otl2latex
usage="""
otl2latex.py

Translate a Vim Outliner file to a LaTeX document.


Usage:
    otl2latex.py -[abp] file.otl [file.tex]

    -a: Output to article class
    -b: Output to book class 
    -p: Output to Beamer (presentation) class (default)


Author: Serge Rey <sjsrey@gmail.com>
Version 0.1 (2007-01-21)
"""

import os,sys

class Line:
    """Class for markup lines"""
    def __init__(self, content):
        ntabs=content.count("\t")
        content=content.lstrip("\t")
        level = ntabs - content.count("\t")
        self.level=level
        self.content = content
        self.markup=0
        if content[0]=="|":
            self.markup=1

#3 lines added here
        self.bullet=0
        if len(content) > 2 and (content[2]=='*' or content[1]=='*'):
            self.bullet=1
        #print "%d: %s"%(self.bullet,content)

class Manager:
    """Abstract class for LaTeX document classes"""
    def __init__(self, content, fileOut):
        self.content=content
        self.fileOut=open(fileOut,'w')
        self.parse()
        self.fileOut.write(self.markup)
        self.fileOut.close()
    def parse(self):
        self.lines=[ Line(line) for line in self.content]
        preambleStart=0
        nl=len(self.lines)
        id=zip(range(nl),self.lines)
        level1=[i for i,line in id if line.level==0]
        preambleEnd=level1[1]
        preamble=self.lines[0:preambleEnd]
        self.level1=level1
        preambleMarkup=[]
        for line in preamble:
            if line.content.count("@"):
                tmp=line.content.split("@")[1]
                tmp=tmp.split()
                env=tmp[0]
                content=" ".join(tmp[1:])
                mu="\\%s{%s}"%(env,content)
                preambleMarkup.append(mu)
        self.preamble=preambleMarkup
        self.preambleLines=preamble
        self.documentLines=self.lines[preambleEnd:]





class Beamer(Manager):
    """Manager for Beamer document class"""
    def __init__(self, content,fileOut):
        self.top1="""
\documentclass[nototal,handout]{beamer}
\mode<presentation>
{
  \usetheme{Madrid}
  \setbeamercovered{transparent}
}

\usepackage{verbatim}
\usepackage{fancyvrb}
\usepackage[english]{babel}
\usepackage[latin1]{inputenc}
\usepackage{times}
\usepackage{tikz}
\usepackage[T1]{fontenc}
\usepackage{graphicx} %sjr added
\graphicspath{{figures/}}
\usepackage{hyperref}"""
        self.top2="""
% Delete this, if you do not want the table of contents to pop up at
% the beginning of each subsection:
\AtBeginSubsection[]
{
  \\begin{frame}<beamer>
    \\frametitle{Outline}
    \\tableofcontents[currentsection,currentsubsection]
  \end{frame}
}


% If you wish to uncover everything in a step-wise fashion, uncomment
% the following command:
\\beamerdefaultoverlayspecification{<+->}
\\begin{document}
\\begin{frame}
  \\titlepage
\end{frame}
\\begin{frame}
  \\frametitle{Outline}
  \\tableofcontents[pausesections]
  % You might wish to add the option [pausesections]
\end{frame}
"""
        self.bulletLevel = 0
        Manager.__init__(self, content, fileOut)

    def itemize(self,line):
        nstars=line.content.count("*")
        content=line.content.lstrip("|").lstrip().lstrip("*")
        self.currentBLevel = nstars - content.count("*")
        stuff=[]
        if self.currentBLevel == self.bulletLevel and line.bullet:
            mu='\\item '+line.content.lstrip("|").lstrip().lstrip("*")
        elif line.bullet and self.currentBLevel > self.bulletLevel:
            self.bulletLevel += 1
            stuff.append("\\begin{itemize}\n")
            mu='\\item '+line.content.lstrip("|").lstrip().lstrip("*")
        elif self.currentBLevel < self.bulletLevel and line.bullet:
            self.bulletLevel -= 1
            stuff.append("\\end{itemize}\n")
            mu='\\item '+line.content.lstrip("|").lstrip().lstrip("*")
        elif self.currentBLevel < self.bulletLevel:
            self.bulletLevel -= 1
            stuff.append("\\end{itemize}\n")
            mu=line.content.lstrip("|")
        else:
            panic()
        return stuff,mu

    def parse(self):
        Manager.parse(self)
        #print self.content
        #print self.lines
        #print self.level1
        #for info in self.preamble:
        #    print info

        # do my own preamble
        field=("author ","instituteShort ","dateShort ","date ","subtitle ",
            "title ", "institute ", "titleShort ")
        pattern=["@"+token for token in field]
        f=zip(field,pattern)
        d={}
        for field,pattern in f:
            t=[line.content for line in self.preambleLines if line.content.count(pattern)]
            if t:
                d[field]= t[0].split(pattern)[1].strip()
            else:
                d[field]=""
        preamble="\n\n\\author{%s}\n"%d['author ']
        preamble+="\\institute[%s]{%s}\n"%(d['instituteShort '],d['institute '])
        preamble+="\\title[%s]{%s}\n"%(d['titleShort '],d['title '])
        preamble+="\\subtitle{%s}\n"%(d['subtitle '])
        preamble+="\\date[%s]{%s}\n"%(d['dateShort '],d['date '])

        print self.preamble
        self.preamble=preamble


        body=[]
        prev=0
        frameOpen=0
        blockOpen=0
        frameCount=0
        blockCount=0

        for line in self.documentLines:
            if line.level==0:
                for i in range(0,self.bulletLevel):
                    self.bulletLevel -= 1
                    body.append("\\end{itemize}\n")
                if blockOpen:
                    body.append("\\end{block}")
                    blockOpen=0
                if frameOpen:
                    body.append("\\end{frame}")
                    frameOpen=0
                mu="\n\n\n\\section{%s}"%line.content.strip()
            elif line.level==1:
                for i in range(0,self.bulletLevel):
                    self.bulletLevel -= 1
                    body.append("\\end{itemize}\n")
                if blockOpen:
                    body.append("\\end{block}")
                    blockOpen=0
                if frameOpen:
                    body.append("\\end{frame}")
                    frameOpen=0
                mu="\n\n\\subsection{%s}"%line.content.strip()
            elif line.level==2:
                # check if this frame has blocks or is nonblocked
                if line.markup:
                    if line.bullet or self.bulletLevel:
                        stuff,mu=self.itemize(line)
                        if len(stuff) > 0:
                            for i in stuff:
                                body.append(i)
                    else:
                        mu=line.content.lstrip("|")
                else:
                    for i in range(0,self.bulletLevel):
                        self.bulletLevel -= 1
                        body.append("\\end{itemize}\n")
                    if blockOpen:
                        body.append("\\end{block}")
                        blockOpen=0
                    if frameOpen:
                        body.append("\\end{frame}")
                    else:
                        frameOpen=1
                    # check for verbatim here
                    tmp=line.content.strip()
                    if tmp.count("@vb"):
                        tmp=tmp.split("@")[0]
                        mu="\n\n\\begin{frame}[containsverbatim]\n\t\\frametitle{%s}\n"%tmp
                    else:
                        mu="\n\n\\begin{frame}\n\t\\frametitle{%s}\n"%tmp
                    frameCount+=1
            elif line.level==3:
                # check if it is a block or body content
                if line.markup:
                    if line.bullet or self.bulletLevel:
                        stuff,mu=self.itemize(line)
                        if len(stuff) > 0:
                            for i in stuff:
                                body.append(i)
                    else:
                        mu=line.content.lstrip("\t")
                        mu=mu.lstrip("|")
                else:
                    for i in range(0,self.bulletLevel):
                        self.bulletLevel -= 1
                        body.append("\\end{itemize}\n")
                    #block title
                    if blockOpen:
                        body.append("\\end{block}")
                    else:
                        blockOpen=1
                    mu="\n\\begin{block}{%s}\n"%line.content.strip()
                    blockCount+=1
            else:
                mu=""
            body.append(mu)
        for i in range(0,self.bulletLevel):
            self.bulletLevel -= 1
            body.append("\\end{itemize}\n")
        if blockOpen:
            body.append("\\end{block}")
        if frameOpen:
            body.append("\\end{frame}")

        self.body=" ".join(body)
        self.markup=self.top1+self.preamble+self.top2
        self.markup+=self.body
        self.markup+="\n\\end{document}\n"
        print self.markup

# Process command line arguments
args = sys.argv
nargs=len(args)
dispatch={}
dispatch['beamer']=Beamer
inputFileName=None
outputFileName=None

def printUsage():
    print usage
    sys.exit()

if nargs==1:
    printUsage()
else:
    docType='beamer'
    options=args[1]
    if options.count("-"):
        if options.count("a"):
            docType='article'
        elif options.count("b"):
            docType='book'
        if nargs==2:
            printUsage()
        elif nargs==3:
            inputFileName=args[2]
        elif nargs==4:
            inputFileName=args[2]
            outputFileName=args[3]
        else:
            printUsage()
    elif nargs==2:
        inputFileName=args[1]
    elif nargs==3:
        inputFileName=args[1]
        outputFileName=args[3]
    else:
        printUsage()
    # Dispatch to correct document class manager
    fin=open(inputFileName,'r')
    content=fin.readlines()
    fin.close()
    dispatch[docType](content,outputFileName)

########NEW FILE########
__FILENAME__ = otl2ooimpress
#!/usr/bin/python2
# otl2ooimpress.py
# needs otl2ooimpress.sh to work in an automated way
#############################################################################
#
#  Tool for Vim Outliner files to Open Office Impress files.
#  Copyright (C) 2003 by Noel Henson, all rights reserved.
#
#       This tool is free software; you can redistribute it and/or
#       modify it under the terms of the GNU Library General Public
#       License as published by the Free Software Foundation; either
#       version 2 of the License, or (at your option) any later version.
#
#       This library is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#       Lesser General Public License for more details.
#
#       You should have received a copy of the GNU Library General Public
#       License along with this library; if not, see
#       <http://www.gnu.org/licenses/>.
#
#############################################################################
# ALPHA VERSION!!!

###########################################################################
# Basic function
#
#    This program accepts VO outline files and converts them
#    to the zipped XML files required by Open Office Impress.
#
#    10 outline levels are supported.  These loosely correspond to the
#    HTML H1 through H9 tags.
#


###########################################################################
# include whatever mdules we need

import sys
###########################################################################
# global variables

level = 0
inputFile = ""
outline = []
flatoutline = []
pageNumber = 0
inPage = 0
debug = 0

###########################################################################
# function definitions


# usage
# print the simplest form of help
# input: none
# output: simple command usage is printed on the console
def showUsage():
    print
    print "Usage:"
    print "otl2ooimpress.py [options] inputfile > outputfile"
    print ""
    print "output is on STDOUT"
    print


# getArgs
# Check for input arguments and set the necessary switches
# input: none
# output: possible console output for help, switch variables may be set
def getArgs():
    global inputfile, debug
    if (len(sys.argv) == 1):
        showUsage()
        sys.exit()()
    else:
        for i in range(len(sys.argv)):
            if (i != 0):
                if (sys.argv[i] == "-d"):
                    debug = 1  # test for debug flag
                elif (sys.argv[i] == "-?"):        # test for help flag
                    showUsage()                           # show the help
                    sys.exit()                            # exit
                elif (sys.argv[i] == "--help"):
                    showUsage()
                    sys.exit()
                elif (sys.argv[i] == "-h"):
                    showUsage()
                    sys.exit()
                elif (sys.argv[i][0] == "-"):
                    print "Error!  Unknown option.  Aborting"
                    sys.exit()
                else:     # get the input file name
                    inputfile = sys.argv[i]


# getLineLevel
# get the level of the current line (count the number of tabs)
# input: linein - a single line that may or may not have tabs at the beginning
# output: returns a number 1 is the lowest
def getLineLevel(linein):
    strstart = linein.lstrip()    # find the start of text in line
    x = linein.find(strstart)     # find the text index in the line
    n = linein.count("\t", 0, x)  # count the tabs
    return(n + 1)                   # return the count + 1 (for level)


# getLineTextLevel
# get the level of the current line (count the number of tabs)
# input: linein - a single line that may or may not have tabs at the beginning
# output: returns a number 1 is the lowest
def getLineTextLevel(linein):
    strstart = linein.lstrip()            # find the start of text in line
    x = linein.find(strstart)            # find the text index in the line
    n = linein.count("\t", 0, x)            # count the tabs
    n = n + linein.count(" ", 0, x)            # count the spaces
    return(n + 1)                    # return the count + 1 (for level)


# colonStrip(line)
# stip a leading ':', if it exists
# input: line
# output: returns a string with a stipped ':'
def colonStrip(line):
    if (line[0] == ":"):
        return line[1:].lstrip()
    else:
        return line


# processLine
# process a single line
# input: linein - a single line that may or may not have tabs at the beginning
#        level - an integer between 1 and 9 that show the current level
#               (not to be confused with the level of the current line)
# output: through standard out
def processLine(linein):
    global inPage, pageNumber
    if (linein.lstrip() == ""):
        print
        return
    if (getLineLevel(linein) == 1):
        if (inPage == 1):
            print '</draw:text-box></draw:page>'
            inPage = 0
        pageNumber += 1
        outstring = '<draw:page draw:name="'
        outstring += 'page'
        outstring += str(pageNumber)
        outstring += '" draw:style-name="dp1" draw:id="1" ' + \
            'draw:master-page-name="Default" ' + \
            'presentation:presentation-page-layout-name="AL1T0">'
        print outstring
        outstring = '<draw:text-box presentation:style-name="pr1" ' + \
            'draw:layer="layout" svg:width="23.911cm" ' + \
            'svg:height="3.508cm" svg:x="2.057cm" svg:y="1.0cm" ' + \
            'presentation:class="title">'
        print outstring
        outstring = '<text:p text:style-name="P1">'
        outstring += linein.lstrip()
        outstring += "</text:p></draw:text-box>"
        print outstring
        outstring = '<draw:text-box presentation:style-name="pr1" ' + \
            'draw:layer="layout" svg:width="23.911cm" ' + \
            'svg:height="3.508cm" svg:x="2.057cm" svg:y="5.38cm" ' + \
            'presentation:class="subtitle">'
        print outstring
        inPage = 1
    else:
        outstring = '<text:p text:style-name="P1">'
        outstring += linein.lstrip()
        outstring += '</text:p>'
        print outstring


# flatten
# Flatten a subsection of an outline.  The index passed is the outline section
# title.  All sublevels that are only one level deeper are indcluded in the
# current subsection.  Then there is a recursion for those items listed in the
# subsection.  Exits when the next line to be processed is of the same or lower
# outline level.
#  (lower means shallower)
# input: idx - the index into the outline.  The indexed line is the title.
# output: adds reformatted lines to flatoutline[]
def flatten(idx):
    if (outline[idx] == ""):
        return
    if (len(outline) <= idx):
        return
    titleline = outline[idx]
    titlelevel = getLineLevel(titleline)
    if (getLineLevel(outline[idx + 1]) > titlelevel):
        if (titleline[titlelevel - 1] != " "):
            flatoutline.append(titleline.lstrip())
        exitflag = 0
        while (exitflag == 0):
            if (idx < len(outline) - 1):
                idx = idx + 1
                currlevel = getLineLevel(outline[idx])
                if (currlevel == titlelevel + 1):
                    if (currlevel == outline[idx].find(" ") + 1):
                        flatoutline.append("\t " + outline[idx].lstrip())
                    else:
                        flatoutline.append("\t" + outline[idx].lstrip())
                elif (currlevel <= titlelevel):
                    exitflag = 1
            else:
                exitflag = 1
    return


def printHeader(linein):
    print'''<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE office:document-content PUBLIC
        "-//OpenOffice.org//DTD OfficeDocument 1.0//EN"
        "office.dtd">
    <office:document-content xmlns:office="http://openoffice.org/2000/office"
        xmlns:style="http://openoffice.org/2000/style"
        xmlns:text="http://openoffice.org/2000/text"
        xmlns:table="http://openoffice.org/2000/table"
        xmlns:draw="http://openoffice.org/2000/drawing"
        xmlns:fo="http://www.w3.org/1999/XSL/Format"
        xmlns:xlink="http://www.w3.org/1999/xlink"
        xmlns:number="http://openoffice.org/2000/datastyle"
        xmlns:presentation="http://openoffice.org/2000/presentation"
        xmlns:svg="http://www.w3.org/2000/svg"
        xmlns:chart="http://openoffice.org/2000/chart"
        xmlns:dr3d="http://openoffice.org/2000/dr3d"
        xmlns:math="http://www.w3.org/1998/Math/MathML"
        xmlns:form="http://openoffice.org/2000/form"
        xmlns:script="http://openoffice.org/2000/script"
        office:class="presentation" office:version="1.0">
    <office:script/>
    <office:body>'''


def printFooter():
    print '</draw:text-box></draw:page>'
    print'</office:body>'


def main():
    getArgs()
    file = open(inputFile, "r")
    linein = file.readline().strip()
    outline.append(linein)
    linein = file.readline().strip()
    while linein != "":
        outline.append("\t" + linein)
        linein = file.readline().rstrip()
    for i in range(0, len(outline) - 1):
        flatten(i)

    printHeader(flatoutline[0])
    for i in range(0, len(flatoutline)):
        processLine(flatoutline[i])
        printFooter()

    file.close()

main()

########NEW FILE########
__FILENAME__ = otl2table
#!/usr/bin/python2
# otl2table.py
# convert a tab-formatted outline from VIM to tab-delimited table
#
# Copyright (c) 2004 Noel Henson All rights reserved
#
# ALPHA VERSION!!!

###########################################################################
# Basic function
#
#	This program accepts text outline files and converts them
#	the tab-delimited text tables.
#	This:
#		Test
#			Dog
#				Barks
#				Howls
#			Cat
#				Meows
#				Yowls
#	Becomes this:
#		Test	Dog	Barks
#		Test	Dog	Howls
#		Test	Cat	Meows
#		Test	Cat	Yowls
#
#	This will make searching for groups of data and report generation easier.
#


###########################################################################
# include whatever mdules we need

import sys
from string import *
#from time import *

###########################################################################
# global variables

level = 0
inputFile = ""
formatMode = "tab"
noTrailing = 0
columns = []

###########################################################################
# function definitions

# usage
# print the simplest form of help
# input: none
# output: simple command usage is printed on the console

def showUsage():
  print
  print "Usage:"
  print "otl2table.py [options] inputfile > outputfile"
  print "Options"
  print "    -n              Don't include trailing columns."
  print "    -t type        Specify field separator type."
  print "                   Types:"
  print "                      tab - separate fields with tabs (default)"
  print "                      csv - separate fields with ,"
  print "                      qcsv - separate fields with \",\""
  print "                      bullets - uses HTML tags <ul> and <li>"
  print "output is on STDOUT"
  print

# getArgs
# Check for input arguments and set the necessary switches
# input: none
# output: possible console output for help, switch variables may be set

def getArgs():
  global inputfile, debug, noTrailing, formatMode
  if (len(sys.argv) == 1):
    showUsage()
    sys.exit()()
  else:
    for i in range(len(sys.argv)):
      if (i != 0):
        if   (sys.argv[i] == "-d"): debug = 1		# test for debug flag
        if   (sys.argv[i] == "-n"): noTrailing = 1	# test for noTrailing flag
        elif (sys.argv[i] == "-?"):			# test for help flag
          showUsage()                                   # show the help
          sys.exit()                                    # exit
        elif (sys.argv[i] == "--help"):
          showUsage()
          sys.exit()
        elif (sys.argv[i] == "-h"):
          showUsage()
          sys.exit()
        elif (sys.argv[i] == "-t"):             # test for the type flag
          formatMode = sys.argv[i+1]            # get the type
          i = i + 1                             # increment the pointer
        elif (sys.argv[i][0] == "-"):
          print "Error!  Unknown option.  Aborting"
          sys.exit()
        else:                                   # get the input file name
          inputfile = sys.argv[i]

# getLineLevel
# get the level of the current line (count the number of tabs)
# input: linein - a single line that may or may not have tabs at the beginning
# output: returns a number 1 is the lowest

def getLineLevel(linein):
  strstart = lstrip(linein)			# find the start of text in line
  x = find(linein,strstart)			# find the text index in the line
  n = count(linein,"\t",0,x)			# count the tabs
  return(n+1)					# return the count + 1 (for level)

# getLineTextLevel
# get the level of the current line (count the number of tabs)
# input: linein - a single line that may or may not have tabs at the beginning
# output: returns a number 1 is the lowest

def getLineTextLevel(linein):
  strstart = lstrip(linein)			# find the start of text in line
  x = find(linein,strstart)			# find the text index in the line
  n = count(linein,"\t",0,x)			# count the tabs
  n = n + count(linein," ",0,x)			# count the spaces
  return(n+1)					# return the count + 1 (for level)

# closeLevels
# print the assembled line
# input: columns - an array of 10 lines (for 10 levels)
#        level - an integer between 1 and 9 that show the current level
# 	          (not to be confused with the level of the current line)
# 	 noTrailing - don't print trailing, empty columns
# output: through standard out

def closeLevels():
  global level,columns,noTrailing,formatMode
  if noTrailing == 1 :
    colcount = level
  else:
     colcount = 10
  if formatMode == "tab":
    for i in range(1,colcount+1):
      print columns[i] + "\t",
    print
  elif formatMode == "csv":
    output = ""
    for i in range(1,colcount):
      output = output + columns[i] + ","
    output = output + columns[colcount]
    print output
  elif formatMode == "qcsv":
    output = "\""
    for i in range(1,colcount):
      output = output + columns[i] + "\",\""
    output = output + columns[colcount] + "\""
    print output
  for i in range(level+1,10):
    columns[i] = ""


# processLine
# process a single line
# input: linein - a single line that may or may not have tabs at the beginning
#        format - a string indicating the mode to use for formatting
#        level - an integer between 1 and 9 that show the current level
# 	          (not to be confused with the level of the current line)
# output: through standard out

def processLine(linein):
  global level, noTrailing, columns
  if (lstrip(linein) == ""): return
  lineLevel = getLineLevel(linein)
  if (lineLevel > level):
    columns[lineLevel] = lstrip(rstrip(linein))
    level = lineLevel
  elif (lineLevel == level):
    closeLevels()
    columns[lineLevel] = lstrip(rstrip(linein))
  else:
    closeLevels()
    level = lineLevel
    columns[lineLevel] = lstrip(rstrip(linein))


def main():
  global columns
  getArgs()
  file = open(inputfile,"r")
  for i in range(11):
    columns.append("")
  linein = lstrip(rstrip(file.readline()))
  while linein != "":
    processLine(linein)
    linein = file.readline()
  closeLevels()
  file.close()

main()


########NEW FILE########
__FILENAME__ = otl2tags
#!/usr/bin/python2
# otl2tags.py
# Convert an OTL file to any tags-based file using config user-
# definable configuration files. HTML, OPML, XML, LATEX and
# many, many others should be easily supportables.
#
# Copyright (c) 2005-2010 Noel Henson All rights reserved

###########################################################################
# Basic function
#
#    This program accepts text outline files in Vim Outliners .otl format
#    and converts them to a tags-based equivalent

###########################################################################
# include whatever mdules we need

import sys
from ConfigParser import ConfigParser
import re

###########################################################################
# global variables

config = ConfigParser()     # configuration
linecount = 0        # outline size in lines
parents = []        # parent stack, (linenum, enum) enum is an order numer
v = {}            # variable dictionary for substitution
outline = []        # line tuples (value, indent)
output = []        # output outline
escapeDict = {}        # dictionary of character escape codes
debug = 0
inputfile = ""

###########################################################################
# arugment, help and debug functions


# usage
# print debug statements
# input: string
# output: string printed to standard out
def dprint(*vals):
    global debug
    if debug != 0:
        print >> sys.stderr, vals


# usage
# print the simplest form of help
# input: none
# output: simple command usage is printed on the console
def showUsage():
    print """
        Usage:
        otl2table.py [options] inputfile
        Options
            -c             config-file
            -d             debug
            --help         show help
        output filenames are based on the input file name and the config file
        """


# getArgs
# Check for input arguments and set the necessary switches
# input: none
# output: possible console output for help, switch variables may be set
def getArgs():
    global inputfile, debug, noTrailing, formatMode, config
    if (len(sys.argv) == 1):
        showUsage()
        sys.exit()()
    else:
        for i in range(len(sys.argv)):
            if (i != 0):
                if (sys.argv[i] == "-c"):         # test for the type flag
                    config.read(sys.argv[i + 1])  # read the config
                    i = i + 1                     # increment the pointer
                elif (sys.argv[i] == "-d"):
                    debug = 1
                elif (sys.argv[i] == "-?"):     # test for help flag
                    showUsage()          # show the help
                    sys.exit()         # exit
                elif (sys.argv[i] == "--help"):
                    showUsage()
                    sys.exit()
                elif (sys.argv[i] == "-h"):
                    showUsage()
                    sys.exit()
                elif (sys.argv[i][0] == "-"):
                    print "Error!  Unknown option.  Aborting"
                    sys.exit()
            else:                  # get the input file name
                inputfile = sys.argv[i]


# printConfig
# Debugging routine to print the parsed configuration file
# input: none
# output: configuration data printed to console
def printConfig():
    global config
    print >> sys.stderr, "Config ---------------------------------------------"
    list = config.sections()
    for i in range(len(list)):
        print >> sys.stderr
        print >> sys.stderr, list[i]
        for x in config.options(list[i]):
            if (x != "name") and (x != "__name__"):
                print >> sys.stderr, x, ":", config.get(list[i], x)
    print >> sys.stderr, "----------------------------------------------------"
    print >> sys.stderr

###########################################################################
# low-level outline processing functions


# indentLevel
# get the level of the line specified by linenum
# input: line
# output: returns the level number, 1 is the lowest
def indentLevel(line):
    strstart = line.lstrip()    # find the start of text in line
    x = line.find(strstart)     # find the text index in the line
    n = line.count("\t", 0, x)      # count the tabs
    n = n + line.count(" ", 0, x)     # count the spaces
    return(n + 1)         # return the count + 1 (for level)


# stripMarker
# return a line without its marker and leading and trailing whitespace
# input: line, marker
# output: stripped line
def stripMarker(line, marker):
    return line.lstrip(marker).strip()


# getLineType
# return the type of the line specified by linenum
# input: line
# output: returns text, usertext, table, preftext, etc.
def getLineType(line):
    if (line[0] == ':'):
        return 'text'
    elif (line[0] == ';'):
        return 'preftext'
    elif (line[0] == '>'):
        return 'usertext'
    elif (line[0] == '<'):
        return 'userpreftext'
    elif (line[0] == '|'):
        return 'table'
    elif (line[0] == '-'):
        return 'bulletheading'
    elif (line[0] == '+'):
        return 'numberheading'
# elif (line[0] == '['):
#    return 'checkboxheading'
    elif (line[0] == ''):
        return 'blank'
    else:
        return 'heading'


# getChildren
# return a list of line numbers for children of the passed line number
# input: linenum
# output: a (possibly) empty list of children
def getChildren(linenum):
    global outline, linecount

    children = []
    mylevel = outline[linenum][1]
    childlevel = mylevel + 1
    linenum = linenum + 1
    while (linenum < linecount) and (outline[linenum][1] > mylevel):
        if (outline[linenum][1] == childlevel):
            children.append(linenum)
        linenum = linenum + 1
    return children


# subTags
# substitute variables in output expressions
# input: section - section from config
# input: type - object type (to look up in config)
# input:  - substitution item (by name) from config array
# output: string - the substitution expression with variables inserted
def subTags(section, type):
    global config, v, parents

    varlist = v.keys()
    pattern = config.get(section, type)
    if len(parents) > 0:
        v["%p"] = str(parents[len(parents) - 1])

    for var in varlist:
        x = ""
        x = var
        y = ""
        y = v.get(var)
        pattern = re.sub(x, y, pattern)
    return pattern


#getBlock
#return a list of lines that match a mark (like : or ;)
#input: line number
#output: list of stripped lines
def getBlock(linenum, marker):
    global outline, linecount

    lines = []
    line = outline[linenum][0]
    while line[0] == marker:
        lines.append(stripMarker(line, marker))
        linenum = linenum + 1
        if linenum == linecount:
            break
        line = outline[linenum][0]
    return lines


#getUnstrippedBlock
#return a list of lines that match a mark (like : or ;)
#input: line number
#output: list of stripped lines
def getUnstrippedBlock(linenum, marker):
    global outline, linecount

    lines = []
    line = outline[linenum][0]
    while line[0] == marker:
        lines.append(line)
        linenum = linenum + 1
        if linenum == linecount:
            break
        line = outline[linenum][0]
    return lines

###########################################################################
# embedded object processing functions


# buildEscapes
# construct the dictionary for escaping special characters
# intput: config:escapes
# output: filled escapes dictionary
def buildEscapes():
    escapes = config.get("Document", "escapes")
    if len(escapes):
        list = escapes.split(" ")
        for pair in list:
            key, value = pair.split(",")
            escapeDict[key] = value


# charEscape
# escape special characters
# input: line
# output: modified line
def charEscape(line):
    return "".join(escapeDict.get(c, c) for c in line)


# getURL
# if there is a url, [url text], return the extracted link, url and value
# input: line
# output: link, url, text
def getURL(line):
    tags = []
    for tag in line.split("]"):
        tags.append(tag.split("["))

    for tag in tags:
        if len(tag) > 1 and re.search(" ", tag[1]):
            link = tag[1]

            url, text = link.split(" ", 1)
            link = "[" + tag[1] + "]"
            return link, url, text

#        return link.group(0), url, text
#    else:
#        return None, None, None
    return None, None, None


def handleURL(line):
    link, url, text = getURL(line)
    if link is None:
        return re.replace(line, "[url]", "")

    v["%u"] = url
    v["%v"] = text

    text = subTags("URLs", "url")
    line = re.replace(line, link, text)

    url = subTags("URLs", "url-attr")
    line = re.replace(line, "[url]", url)

    return line


###########################################################################
# outline header processing functions


# all outline object processors accept and output the following:
# input: linenum, enum
# output: print the output for each object
def handleHeading(linenum, enum):
    global outline, parents

    line = outline[linenum][0]

# url handling
# extract url data from line
# replace url object in line
# subTags line
# replace url attribute marker

    v["%%"] = line
    v["%l"] = str(outline[linenum][1])
    v["%n"] = str(linenum)
    v["%c"] = str(enum)
    children = getChildren(linenum)
    if enum == 1:
        output.append(subTags("Headings", "before-headings"))
    if children:
        output.append(subTags("Headings", "branch-heading"))
        parents.append([linenum, enum])
        handleObjects(children)
        parents.pop()
        output.append(subTags("Headings", "after-headings"))
    else:
        output.append(subTags("Headings", "leaf-heading"))


def handleBulleted(linenum, enum):
    global outline, parents

    v["%%"] = outline[linenum][0]
    v["%l"] = str(outline[linenum][1])
    v["%n"] = str(linenum)
    v["%c"] = str(enum)
    children = getChildren(linenum)
    if enum == 1:
        output.append(subTags("Headings", "before-bulleted-headings"))
    if children:
        output.append(subTags("Headings", "bulleted-branch-heading"))
        parents.append([linenum, enum])
        handleObjects(children)
        parents.pop()
        output.append(subTags("Headings", "after-bulleted-headings"))
    else:
        output.append(subTags("Headings", "bulleted-leaf-heading"))


def handleNumbered(linenum, enum):
    global outline, parents

    v["%%"] = outline[linenum][0]
    v["%l"] = str(outline[linenum][1])
    v["%n"] = str(linenum)
    v["%c"] = str(enum)
    children = getChildren(linenum)
    if enum == 1:
        output.append(subTags("Headings", "before-numbered-headings"))
    if children:
        output.append(subTags("Headings", "numbered-branch-heading"))
        parents.append([linenum, enum])
        handleObjects(children)
        parents.pop()
        output.append(subTags("Headings", "after-numbered-headings"))
    else:
        output.append(subTags("Headings", "numbered-leaf-heading"))

###########################################################################
# outline text block processing functions


# all outline object processors accept and output the following:
# input: linenum, enum
# output: print the output for each object
def handleText(linenum, enum):
    global outline, parents

    if enum != 1:
        return  # only execute for first call

    v["%l"] = str(outline[linenum][1])
    v["%n"] = str(linenum)
    v["%c"] = str(enum)
    list = getBlock(linenum, ':')
    output.append(subTags("Text", "before"))
    lines = ""
    for line in list:
        if line == "":
            lines = lines + config.get("Text", "paragraph-sep")
        else:
            lines = lines + line + config.get("Text", "line-sep")
    v["%%"] = lines
    output.append(subTags("Text", "text"))
    output.append(subTags("Text", "after"))


def handleUserText(linenum, enum):
    global outline, parents

    if enum != 1:
        return  # only execute for first call

    v["%l"] = str(outline[linenum][1])
    v["%n"] = str(linenum)
    v["%c"] = str(enum)
    list = getBlock(linenum, '>')
    output.append(subTags("UserText", "before"))
    lines = ""
    for line in list:
        if line == "":
            lines = lines + config.get("UserText", "paragraph-sep")
        else:
            lines = lines + line + config.get("UserText", "line-sep")
    v["%%"] = lines.strip()  # remove a possible extra separator
    output.append(subTags("UserText", "text"))
    output.append(subTags("UserText", "after"))


def handlePrefText(linenum, enum):
    global outline, parents

    if enum != 1:
        return  # only execute for first call

    v["%l"] = str(outline[linenum][1])
    v["%n"] = str(linenum)
    v["%c"] = str(enum)
    list = getBlock(linenum, ';')
    output.append(subTags("PrefText", "before"))
    lines = ""
    for line in list:
        if line == "":
            lines = lines + config.get("PrefText", "paragraph-sep")
        else:
            lines = lines + line + config.get("PrefText", "line-sep")
    v["%%"] = lines.strip()  # remove a possible extra separator
    output.append(subTags("PrefText", "text"))
    output.append(subTags("PrefText", "after"))


def handleUserPrefText(linenum, enum):
    global outline, parents

    if enum != 1:
        return  # only execute for first call

    v["%l"] = str(outline[linenum][1])
    v["%n"] = str(linenum)
    v["%c"] = str(enum)
    list = getBlock(linenum, '<')
    output.append(subTags("UserPrefText", "before"))
    lines = ""
    for line in list:
        if line == "":
            lines = lines + config.get("UserPrefText", "paragraph-sep")
        else:
            lines = lines + line + config.get("UserPrefText", "line-sep")
    v["%%"] = lines.strip()  # remove a possible extra separator
    output.append(subTags("UserPrefText", "text"))
    output.append(subTags("UserPrefText", "after"))

###########################################################################
# outline table processing functions


# isAlignRight
# return flag
# input: col, a string
def isAlignRight(col):
    l = len(col)
    if (col[0:2] == "  ") and (col[l - 2:l] != "  "):
        return 1
    else:
        return 0


# isAlignLeft
# return flag
# input: col, a string
def isAlignLeft(col):
    l = len(col)
    if (col[0:2] != "  ") and (col[l - 2:l] == "  "):
        return 1
    else:
        return 0


# isAlignCenter
# return flag
# input: col, a string
def isAlignCenter(col):
    l = len(col)
    if (col[0:2] == "  ") and (col[l - 2:l] == "  "):
        return 1
    else:
        return 0


# handleHeaderRow
# process a non-header table row
# input: row
# output: print the output for each object
def handleHeaderRow(row):
    global outline, parents

    row = row.rstrip("|").lstrip("|")
    columns = row.split("|")
    output.append(subTags("Tables", "before-table-header"))
    for col in columns:
        v["%%"] = col.strip()
        if isAlignCenter:
            output.append(subTags("Tables", "table-header-column-center"))
        elif isAlignCenter:
            output.append(subTags("Tables", "table-header-column-center"))
        elif isAlignCenter:
            output.append(subTags("Tables", "table-header-column-center"))
        else:
            output.append(subTags("Tables", "table-header-column"))
    output.append(subTags("Tables", "after-table-header"))


# handleRow
# process a non-header table row
# input: row
# output: print the output for each object
def handleRow(row):
    global outline, parents

    if row[0:2] == "||":
        handleHeaderRow(row)
        return
    row = row.rstrip("|").lstrip("|")
    columns = row.split("|")
    output.append(subTags("Tables", "before-table-row"))
    for col in columns:
        v["%%"] = col.strip()
        if isAlignCenter:
            output.append(subTags("Tables", "table-column-center"))
        elif isAlignLeft:
            output.append(subTags("Tables", "table-column-left"))
        elif isAlignRight:
            output.append(subTags("Tables", "table-column-right"))
        else:
            output.append(subTags("Tables", "table-column"))
    output.append(subTags("Tables", "after-table-row"))


# handleTable
# process a table
# input: linenum, enum
# output: print the output for each object
def handleTable(linenum, enum):
    global outline, parents

    if enum != 1:
        return  # only execute for first call

    v["%l"] = str(outline[linenum][1])
    v["%n"] = str(linenum)
    v["%c"] = str(enum)
    list = getUnstrippedBlock(linenum, '|')
    output.append(subTags("Tables", "before"))
    for row in list:
        handleRow(row)
    output.append(subTags("Tables", "after"))

###########################################################################
# outline wrapper processing functions


# addPreamble
# create the 'header' for the output document
# input: globals
# output: standard out
def addPreamble():
    global outline, v

    v["%%"] = ""
    output.append(subTags("Document", "preamble"))


# addPostamble
# create the 'header' for the output document
# input: globals
# output: standard out
def addPostamble():
    global outline, v

    v["%%"] = ""
    output.append(subTags("Document", "postamble"))


###########################################################################
# outline tree fuctions


# handleObject
# take an object and invoke the appropriate fuction to precess it
# input: linenum, enum (enum is the child order number of a parent)
# output: print the output of a object
def handleObject(linenum, enum):
    global outline, linecount

    obj = getLineType(outline[linenum][0])
    if obj == 'heading':
        handleHeading(linenum, enum)
    elif obj == 'bulled':
        handleBulleted(linenum, enum)
    elif obj == 'numbered':
        handleNumbered(linenum, enum)
    elif obj == 'text':
        handleText(linenum, enum)
    elif obj == 'usertext':
        handleUserText(linenum, enum)
    elif obj == 'preftext':
        handlePrefText(linenum, enum)
    elif obj == 'userpreftext':
        handleUserPrefText(linenum, enum)
    elif obj == 'table':
        handleTable(linenum, enum)
    else:
        print
        print "Error: unknown line type @ ", linenum
        sys.exit(1)


# handleObjects
# take an object list and invoke the appropriate fuctions to precess it
# input: linenum
# output: print the output of a object
def handleObjects(objs):
    for i in range(len(objs)):
        handleObject(objs[i], i + 1)

###########################################################################
# file functions


# readFile
# read the selected file into lines[]
# input: filename to be loaded
# output: a loaded-up lines[]
def readFile(inputfile):
    global outline, linecount, config
    file = open(inputfile, "r")
    linein = file.readline()

    while linein != "":
        indent = indentLevel(linein)
        line = charEscape(linein.strip())
        outline.append([line, indent])
        linein = file.readline()

    file.close

    outline[0][1] = 0  # set the first line to level 0

    linecount = len(outline)

###########################################################################
# Main Program Loop


def main():
    global outline, inputfile, linecount

    # get the arguments
    getArgs()

    # constuct the escapes dictionary
    buildEscapes()

    # read the input file
    readFile(inputfile)

    # get the title
    v["%t"] = outline[0][0].strip()

    # construct the initial data
    # parsing headings, text and tables
    # but not parsing links or images
    addPreamble()
    if config.get("Document", "first-is-node") == "true":
        objs = [0]
    else:
        objs = getChildren(0)
    handleObjects(objs)
    addPostamble()

    # handle embeded objects
    # parsing and constructing links, images and other embedded objects
    for i in range(len(output)):
        output[i] = handleURL(output[i])

    # output the final data
    for line in output:
        if line.strip() != "":
            print line.strip()

main()

########NEW FILE########
__FILENAME__ = otlgrep
#!/usr/bin/python2
# otlgrep.py
# grep an outline for a regex and return the branch with all the leaves.
#
# Copyright 2005 Noel Henson All rights reserved

###########################################################################
# Basic function
#
#    This program searches an outline file for a branch that contains
#    a line matching the regex argument. The parent headings (branches)
#    and the children (sub-branches and leaves) of the matching headings
#    are returned.
#
#    Examples
#
#    Using this outline:
#
#    Pets
#    Indoor
#        Cats
#            Sophia
#            Hillary
#        Rats
#            Finley
#            Oliver
#        Dogs
#            Kirby
#    Outdoor
#        Dogs
#            Kirby
#            Hoover
#        Goats
#            Primrose
#            Joey
#
#    a grep for Sophia returns:
#
#    Indoor
#        Cats
#            Sophia
#
#    a grep for Dogs returns:
#
#    Indoor
#        Dogs
#            Kirby
#            Hoover
#    Outdoor
#        Dogs
#            Kirby
#            Hoover
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

###########################################################################
# include whatever mdules we need

import sys
import re

###########################################################################
# global variables

debug = 0
ignorecase = 0
pattern = ""
inputfiles = []

###########################################################################
# function definitions# usage
#
# print debug statements
# input: string
# output: string printed to standard out


def dprint(*vals):
    global debug
    if debug != 0:
        print vals


# usage
# print the simplest form of help
# input: none
# output: simple command usage is printed on the console
def showUsage():
    print """
    Usage:
    otlgrep.py [options] pattern [file...]
    Options
        -i            Ignore case
        --help        Show help.
    [file...] is zero or more files to search. Wildcards are supported.
            if no file is specified, input is expected on stdin.
    output is on STDOUT
    """


# getArgs
# Check for input arguments and set the necessary switches
# input: none
# output: possible console output for help, switch variables may be set

def getArgs():
    global debug, pattern, inputfiles, ignorecase
    if (len(sys.argv) == 1):
        showUsage()
        sys.exit()()
    else:
        for i in range(len(sys.argv)):
            if (i != 0):
                if (sys.argv[i] == "-d"):
                    debug = 1  # test for debug flag
                elif (sys.argv[i] == "-i"):
                    ignorecase = 1    # test for debug flag
                elif (sys.argv[i] == "-?"):        # test for help flag
                    showUsage()                           # show the help
                    sys.exit()                            # exit
                elif (sys.argv[i] == "--help"):
                    showUsage()
                    sys.exit()
                elif (sys.argv[i][0] == "-"):
                    print "Error!  Unknown option.  Aborting"
                    sys.exit()
                else:       # get the input file name
                    if (pattern == ""):
                        pattern = sys.argv[i]
                    else:
                        inputfiles.append(sys.argv[i])


# getLineLevel
# get the level of the current line (count the number of tabs)
# input: linein - a single line that may or may not have tabs at the beginning
# output: returns a number 1 is the lowest
def getLineLevel(linein):
    strstart = linein.lstrip()           # find the start of text in line
    x = linein.find(strstart)            # find the text index in the line
    n = linein.count("\t", 0, x)         # count the tabs
    return(n)                    # return the count + 1 (for level)


# processFile
# split an outline file
# input: file - the filehandle of the file we are splitting
# output: output files
def processFile(file):
    global debug, pattern, ignorecase

    parents = []
    parentprinted = []
    for i in range(10):
        parents.append("")
        parentprinted.append(0)

    matchlevel = 0
    line = file.readline()      # read the outline title
                                # and discard it
    line = file.readline()      # read the first parent heading
    while (line != ""):
        level = getLineLevel(line)
        parents[level] = line
        parentprinted[level] = 0
        if (ignorecase == 1):
            linesearch = re.search(pattern, line.strip(), re.I)
        else:
            linesearch = re.search(pattern, line.strip())
        if (linesearch is not None):
            matchlevel = level
            for i in range(level):  # print my ancestors
                if (parentprinted[i] == 0):
                    print parents[i][:-1]
                    parentprinted[i] = 1
            print parents[level][:-1]  # print myself
            line = file.readline()
            while (line != "") and (getLineLevel(line) > matchlevel):
                print line[:-1]
                line = file.readline()
        else:
            line = file.readline()


# main
# split an outline
# input: args and input file
# output: output files

def main():
    global inputfiles, debug
    getArgs()
    if (len(inputfiles) == 0):
        processFile(sys.stdin)
    else:
        for i in range(len(inputfiles)):
            file = open(inputfiles[i], "r")
            processFile(file)
        file.close()

main()

########NEW FILE########
__FILENAME__ = otlsplit
#!/usr/bin/python2
# otlslit.py
# split an outline into several files.
#
# Copyright 2005 Noel Henson All rights reserved

###########################################################################
# Basic function
#
#    This program accepts text outline files and splits them into
#    several smaller files. The output file names are produced from the
#    heading names of the parents.
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, see <http://www.gnu.org/licenses/>.

###########################################################################
# include whatever mdules we need

import sys
import re
###########################################################################
# global variables

debug = 0
subdir = ""
level = 1
title = 0
inputfile = ""


###########################################################################
# function definitions# usage
#
# print debug statements
# input: string
# output: string printed to standard out
def dprint(*vals):
    global debug
    if debug != 0:
        print vals


# usage
# print the simplest form of help
# input: none
# output: simple command usage is printed on the console
def showUsage():
    print """
    Usage:
    otlsplit.py [options] inputfile
    Options
        -l level  The number of levels to split down to. The default is 1
        -D dir    Specifiy a target directory for the output files
        -t        Include a title line (the parerent heading) in split files
        -h        Show help.
    output is on STDOUT
    """


# getArgs
# Check for input arguments and set the necessary switches
# input: none
# output: possible console output for help, switch variables may be set
def getArgs():
    global debug, level, inputfile, title, subdir
    if (len(sys.argv) == 1):
        showUsage()
        sys.exit()()
    else:
        for i in range(len(sys.argv)):
            if (i != 0):
                if (sys.argv[i] == "-d"):
                    debug = 1    # test for debug flag
                elif (sys.argv[i] == "-?"):        # test for help flag
                    showUsage()                           # show the help
                    sys.exit()                            # exit
                elif (sys.argv[i] == "-l"):       # test for the level flag
                    level = int(sys.argv[i + 1])  # get the level
                    i = i + 1                     # increment the pointer
                elif (sys.argv[i] == "-D"):       # test for the subdir flag
                    subdir = sys.argv[i + 1]        # get the subdir
                    i = i + 1                     # increment the pointer
                elif (sys.argv[i] == "-t"):
                    title = 1                     # test for title flag
                elif (sys.argv[i] == "--help"):
                    showUsage()
                    sys.exit()
                elif (sys.argv[i] == "-h"):
                    showUsage()
                    sys.exit()
                elif (sys.argv[i][0] == "-"):
                    print "Error!  Unknown option.  Aborting"
                    sys.exit()
                else:                             # get the input file name
                    inputfile = sys.argv[i]


# getLineLevel
# get the level of the current line (count the number of tabs)
# input: linein - a single line that may or may not have tabs at the beginning
# output: returns a number 1 is the lowest
def getLineLevel(linein):
    strstart = linein.lstrip()    # find the start of text in line
    x = linein.find(strstart)     # find the text index in the line
    n = linein.count("\t", 0, x)  # count the tabs
    return(n + 1)                   # return the count + 1 (for level)


# convertSensitiveChars
# get the level of the current line (count the number of tabs)
# input: line - a single line that may or may not have tabs at the beginning
# output: returns a string
def convertSensitiveChars(line):
    line = re.sub('\W', '_', line.strip())
    return(line)


# makeFileName
# make a file name from the string array provided
# input: line - a single line that may or may not have tabs at the beginning
# output: returns a string
def makeFileName(nameParts):
    global debug, level, subdir

    filename = ""
    for i in range(level):
        filename = filename + convertSensitiveChars(nameParts[i]).strip() + "-"
    filename = filename[:-1] + ".otl"
    if subdir != "":
        filename = subdir + "/" + filename
    return(filename.lower())


# processFile
# split an outline file
# input: file - the filehandle of the file we are splitting
# output: output files
def processFile(ifile):
    global debug, level, title

    nameparts = []
    for i in range(10):
        nameparts.append("")

    outOpen = 0

    line = ifile.readline()      # read the outline title
                                # and discard it
    line = ifile.readline()      # read the first parent heading
    dprint(level)
    while (line != ""):
        linelevel = getLineLevel(line)
        if (linelevel < level):
            if outOpen == 1:
                ifile.close()
                outOpen = 0
            nameparts[linelevel] = line
            dprint(level, linelevel, line)
        else:
            if outOpen == 0:
                ofile = open(makeFileName(nameparts), "w")
                outOpen = 1
                if title == 1:
                    dprint("title:", title)
                    ofile.write(nameparts[level - 1])
            ofile.write(line[level:])
        line = file.readline()


# main
# split an outline
# input: args and input file
# output: output files
def main():
    global inputfile, debug
    getArgs()
    file = open(inputfile, "r")
    processFile(file)
    file.close()

main()

########NEW FILE########
__FILENAME__ = freemind
#!/usr/bin/python2

'''
usage:
    freemind.py -o [fmt] <files>, where ofmt selects output format: {otl,mm}

freemind.py -o otl <files>:
    Read in an freemind XML .mm file and generate a outline file
    compatable with vim-outliner.
freemind.py -o mm <files>:
    Read in an otl file and generate an XML mind map viewable in freemind

NOTE:
    Make sure that you check that round trip on your file works.

Author: Julian Ryde
'''
import sys
import getopt
import codecs

import otl
import xml.etree.ElementTree as et
from xml.etree.ElementTree import XMLParser

debug = False


class Outline:                     # The target object of the parser
    depth = -1
    indent = '\t'
    current_tag = None

    def start(self, tag, attrib):  # Called for each opening tag.
        self.depth += 1
        self.current_tag = tag
        # print the indented heading
        if tag == 'node' and self.depth > 1:
            #if 'tab' in attrib['TEXT']:
                #import pdb; pdb.set_trace()
            print (self.depth - 2) * self.indent + attrib['TEXT']

    def end(self, tag):            # Called for each closing tag.
        self.depth -= 1
        self.current_tag = None

    def data(self, data):
        if self.current_tag == 'p':
            bodyline = data.rstrip('\r\n')
            bodyindent = (self.depth - 5) * self.indent + ": "
            #textlines = textwrap.wrap(bodytext, width=77-len(bodyindent),
            #   break_on_hyphens=False)
            #for line in textlines:
            print bodyindent + bodyline

    def close(self):    # Called when all data has been parsed.
        pass


def mm2otl(*arg, **kwarg):
    fname = arg[0][0]
    file = codecs.open(fname, 'r', encoding='utf-8')

    filelines = file.readlines()
    outline = Outline()
    parser = XMLParser(target=outline, encoding='utf-8')
    parser.feed(filelines[0].encode('utf-8'))
    parser.close()


# TODO body text with manual breaks
# TODO commandline arguments for depth, maxlength etc.
# TODO do not read whole file into memory?
# TODO handle decreasing indent by more than one tab
# TODO handle body text lines sometimes not ending with space

depth = 99


def attach_note(node, textlines):
    et.ElementTree
    # Format should look like
    #<richcontent TYPE="NOTE">
    #<html>
    #  <head> </head>
    #  <body>
    #  %s
    #  </body>
    #</html>
    #</richcontent>
    notenode = et.SubElement(node, 'richcontent')
    notenode.set('TYPE', 'NOTE')
    htmlnode = et.SubElement(notenode, 'html')
    bodynode = et.SubElement(htmlnode, 'body')
    for line in textlines:
        pnode = et.SubElement(bodynode, 'p')
        pnode.text = line


def otl2mm(*arg, **kwarg):
    fname = arg[0][0]

    # node ID should be based on the line number of line in the
    # otl file for easier debugging
    #for lineno, line in enumerate(open(fname)):
    # enumerate starts at 0 I want to start at 1
    # FIXME freemind.py|107| W806 local variable 'lineno' is assigned to but never used
    lineno = 0

    mapnode = et.Element('map')
    mapnode.set('version', '0.9.0')

    topnode = et.SubElement(mapnode, 'node')
    topnode.set('TEXT', fname)

    parents = [mapnode, topnode]

    #left_side = True # POSITION="right"

    # read otl file into memory
    filelines = codecs.open(fname, 'r', encoding='utf-8')

    # first handle the body texts turn it into a list of headings
    # with associated body text for each one this is because the
    # body text especially multi-line is what makes it awkward.
    headings = []
    bodytexts = []
    for line in filelines:
        if otl.is_heading(line):
            headings.append(line)
            bodytexts.append([])
        else:
            # TODO this ': ' removal should go in otl.py?
            bodytexts[-1].append(line.lstrip()[2:] + '\n')

    #import pdb; pdb.set_trace()
    oldheading = ''
    for heading, bodytext in zip(headings, bodytexts):
        if debug:
            print heading, bodytext

        level = otl.level(heading)
        oldlevel = otl.level(oldheading)

        if level == oldlevel:
            pass
        elif level > oldlevel:
            # about to go down in the hierarchy so add this line
            # as a parent to the stack
            # FIXME freemind.py|149| W802 undefined name 'node'
            parents.append(node)
        elif level < oldlevel:
            # about to go up in the hierarchy so remove parents from the stack
            leveldiff = oldlevel - level
            parents = parents[:-leveldiff]

        node = et.SubElement(parents[-1], 'node')
        node.set('TEXT', heading.lstrip().rstrip('\r\n'))
        #if len(bodytext) > 0:
        attach_note(node, bodytext)

        oldheading = heading

    xmltree = et.ElementTree(mapnode)
    xmltree.write(sys.stdout, 'utf-8')
    print


def usage():
    print "usage: %s -[mo] <files>" % (sys.argv[0])


def main():
    args = sys.argv
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'moh', [""])
    except getopt.GetoptError, err:
        usage()
        print str(err)
        sys.exit(2)

    for o, a in opts:
        if o == "-m":
            otl2mm(args)
        elif o == "-o":
            mm2otl(args)
        elif o == "-h":
            usage()
            sys.exit(0)
        else:
            usage()
            assert False, "unhandled option: %s" % o
    return args

if __name__ == "__main__":
    main()

# vim: set noet :

########NEW FILE########
__FILENAME__ = freemind_outline
#!/usr/bin/python2
'''Converts a freemind xml .mm file to an outline file compatable with vim 
outliner.

Make sure that you check that round trip on your file works.

Author: Julian Ryde
'''
import sys
from xml.etree.ElementTree import XMLParser
import textwrap
import codecs

class Outline:                     # The target object of the parser
    depth = -1
    indent = '\t'
    current_tag = None
    def start(self, tag, attrib):  # Called for each opening tag.
        self.depth += 1
        self.current_tag = tag
        # print the indented heading
        if tag == 'node' and self.depth > 1:
            #if 'tab' in attrib['TEXT']:
                #import pdb; pdb.set_trace()
            print (self.depth-2)*self.indent + attrib['TEXT']
    def end(self, tag):            # Called for each closing tag.
        self.depth -= 1
        self.current_tag = None
    def data(self, data):
        if self.current_tag == 'p':
            bodyline = data.rstrip('\r\n')
            bodyindent = (self.depth-5)*self.indent + ": "
            #textlines = textwrap.wrap(bodytext, width=77-len(bodyindent), break_on_hyphens=False)
            #for line in textlines: 
            print bodyindent + bodyline

    def close(self):    # Called when all data has been parsed.
        pass

outline = Outline()
parser = XMLParser(target=outline, encoding='utf-8')

fname = sys.argv[1]
file = codecs.open(fname, 'r', encoding='utf-8')
filelines = file.readlines();
print "filelines", type(filelines[0]), filelines[0]
parser.feed(filelines[0].encode('utf-8'))
parser.close()

########NEW FILE########
__FILENAME__ = otl
# Some integer IDs
# headings are 1, 2, 3, ....
bodynowrap = -1 # ;
bodywrap = 0 # :

def level(line):
    '''return the heading level 1 for top level and down and 0 for body text'''
    if line.lstrip().find(':')==0: return bodywrap
    if line.lstrip().find(';')==0: return bodynowrap 
    strstart = line.lstrip() # find the start of text in lin
    x = line.find(strstart)  # find the text index in the line
    n = line.count("\t",0,x) # count the tabs
    return(n+1)              # return the count + 1 (for level)

def is_bodywrap(line):
    return level(line) == bodywrap

def is_bodynowrap(line):
    return level(line) == bodynowrap

def is_heading(line):
    return level(line) > 0

def is_body(line):
    return not is_heading(line)


########NEW FILE########
__FILENAME__ = outline_freemind
#!/usr/bin/python2
'''Read in an otl file and generate an xml mind map viewable in freemind

Make sure that you check that round trip on your file works.

Author: Julian Ryde
'''

import sys
import os
import xml.etree.ElementTree as et
import otl
import codecs

fname = sys.argv[1]
max_length = 40
depth = 99

debug = False

# TODO body text with manual breaks
# TODO commandline arguments for depth, maxlength etc.
# TODO do not read whole file into memory?
# TODO handle decreasing indent by more than one tab 
# TODO handle body text lines sometimes not ending with space

otlfile = open(fname)
indent = '  '

def attach_note(node, textlines):
    et.ElementTree
    # Format should look like
    #<richcontent TYPE="NOTE">
    #<html>
    #  <head> </head>
    #  <body>
    #  %s
    #  </body>
    #</html>
    #</richcontent>
    notenode = et.SubElement(node, 'richcontent')
    notenode.set('TYPE', 'NOTE')
    htmlnode = et.SubElement(notenode, 'html')
    headnode = et.SubElement(htmlnode, 'head')
    bodynode = et.SubElement(htmlnode, 'body')
    for line in textlines:
        pnode = et.SubElement(bodynode, 'p')
        pnode.text = line

# node ID should be based on the line number of line in the otl file for easier 
# debugging
#for lineno, line in enumerate(open(fname)): 
# enumerate starts at 0 I want to start at 1
lineno = 0

mapnode = et.Element('map')
mapnode.set('version', '0.9.0')

topnode = et.SubElement(mapnode, 'node')
topnode.set('TEXT', fname)

parents = [mapnode, topnode]

#left_side = True # POSITION="right"

# read otl file into memory
filelines = codecs.open(fname, 'r', encoding='utf-8')

# remove those that are too deep or body text and pesky end of line characters
#filelines = [line.rstrip('\r\n') for line in filelines if otl.level(line) <= depth]
#filelines = [line for line in filelines if otl.is_heading(line)]

# first handle the body texts turn it into a list of headings with associated 
# body text for each one this is because the body text especially multi-line is 
# what makes it awkward.
headings = []
bodytexts = []
for line in filelines:
    if otl.is_heading(line):
        headings.append(line)
        bodytexts.append([])
    else:
        # TODO this ': ' removal should go in otl.py?
        bodytexts[-1].append(line.lstrip()[2:] + '\n')

#import pdb; pdb.set_trace()
oldheading = ''
for heading, bodytext in zip(headings, bodytexts):
    if debug: print heading, bodytext

    level = otl.level(heading)
    oldlevel = otl.level(oldheading)

    if level == oldlevel:
        pass
    elif level > oldlevel:
        # about to go down in the hierarchy so add this line as a parent to the 
        # stack
        parents.append(node)
    elif level < oldlevel:
        # about to go up in the hierarchy so remove parents from the stack
        leveldiff = oldlevel - level
        parents = parents[:-leveldiff]

    node = et.SubElement(parents[-1], 'node')
    node.set('TEXT', heading.lstrip().rstrip('\r\n'))
    #if len(bodytext) > 0:
    attach_note(node, bodytext)

    oldheading = heading

xmltree = et.ElementTree(mapnode)
xmltree.write(sys.stdout, 'utf-8')
print

########NEW FILE########
