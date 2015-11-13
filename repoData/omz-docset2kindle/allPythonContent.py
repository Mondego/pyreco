__FILENAME__ = docset2kindle
#! /usr/bin/env python

import json
import codecs
import re
from optparse import OptionParser
from os import path, makedirs, remove, walk, getcwd
from subprocess import call
from shutil import copyfile, copytree, rmtree, move
from tempfile import mkdtemp
from sys import argv

def main():
    usage = "Usage: %prog [options] <Path to Docset>"
    parser = OptionParser(usage=usage)
    parser.add_option("-o", "--output", dest="output_dir",
                      help="write generated mobi files to DIRECTORY. If not specified, mobi files are written to the current working directory. If the directory doesn't exist, it is created automatically.", metavar="DIRECTORY")
                      
    parser.add_option("-f", "--format", dest="format", default="mobi", help="output format. Currently supported mobi and epub", metavar="FORMAT")
    
    (options, args) = parser.parse_args()
    if len(args) == 0:
        print "You did not specify a docset.\n"
        parser.print_help()
        return
    elif len(args) > 1:
        print 'Too many arguments.'
        return
    output_dir = options.output_dir
    if output_dir is None:
        output_dir = getcwd()
    
    docset_path = args[0]
    
    if not path.isdir(docset_path):
        print 'Error: Docset is not a directory.'
        return
    
    
    
    script_dir = path.split(argv[0])[0]
    
    
    try:
        import PIL
    except ImportError:
        print "PIL is not installed. Continue without dynamic cover support"
    
    if options.format=="mobi":
        #If kindlegen is found in the script's directory, use that version, 
        #otherwise check if kindlegen is in the PATH:
        kindlegen_command = path.join(script_dir, './kindlegen')
        if not path.isfile(kindlegen_command):
            kindlegen_installed = (call(['which', '-s', 'kindlegen']) == 0)
            if kindlegen_installed:
                kindlegen_command = 'kindlegen'
            else:
                print 'kindlegen not found. Please download the kindlegen commandline tool from\nhttp://www.amazon.com/gp/feature.html?ie=UTF8&docId=1000234621\nand place it in your PATH or the script\'s directory.'
                return
    
    if not path.isdir(output_dir): makedirs(output_dir)
    
    print 'Scanning docset for books...'
    valid_book_types = set(['Guide', 'Getting Started'])
    book_paths_by_title = books(docset_path, valid_book_types)
    print len(book_paths_by_title), ' books found. Starting conversion...'
    
    f = open(path.join(script_dir, 'kindle.css'), 'r')
    stylesheet = f.read()
    f.close()
    
    
    
    for book_path in book_paths_by_title.values():
        temp_dir = mkdtemp()
        book_title = build_pre(book_path, stylesheet, temp_dir, output_dir)

        if options.format=="mobi":
            build_mobi(book_title,temp_dir, output_dir, kindlegen_command)
        elif options.format=="epub":
            build_epub(book_title,temp_dir, output_dir)
        rmtree(temp_dir)

def  draw_book_title(file_path, book_title):

    import PIL
    from PIL import ImageFont
    from PIL import Image
    from PIL import ImageDraw
    import textwrap
    
    img=Image.open(file_path)
    draw = ImageDraw.Draw(img)
    
    offset = 315
    margin = 41
    
    wrapped_text = textwrap.wrap(book_title, width=12, break_long_words=False, break_on_hyphens=False)
    if len(wrapped_text)>3:
        wrapped_text = textwrap.wrap(book_title, width=16, break_long_words=False, break_on_hyphens=False)
        font_size = 69
    else:
        font_size = 81
    
    
    font = ImageFont.truetype("/Library/Fonts/Arial Narrow Bold.ttf", font_size)

    for line in wrapped_text:
        draw.text((margin, offset), line, font=font)
        offset += font.getsize(line)[1]
    
    img.save(file_path)


def build_pre(doc_path, stylesheet, work_dir, output_dir):
    
    book_path = path.join(doc_path, 'book.json')
    f = open(book_path, 'r')
    book = json.loads(f.read())
    book_title = book.get('title').lstrip().rstrip()
    print '  ' + book_title
    f.close()

    documents = document_paths(book)

    rmtree(work_dir)
    copytree(doc_path, work_dir)
    copyfile(path.join(path.split(argv[0])[0], 'cover.gif'), path.join(work_dir, 'cover.gif'))


    try:
        draw_book_title(path.join(work_dir, 'cover.gif'), book_title)
    except ImportError:
        pass
        
    absolute_paths = [path.join(work_dir, doc_path) for doc_path in documents]

    for absolute_path in absolute_paths:
        try:
            f = codecs.open(absolute_path, 'r', 'utf-8')
            doc = f.read()
            f.close()
            cleaned_doc = clean_doc(doc, stylesheet)
            f = codecs.open(absolute_path, 'w', 'utf-8')
            f.write(cleaned_doc)
            f.close()
        except IOError, error:
            print error
            continue

    html_toc = gen_html_toc(book)
    toc_path = path.join(work_dir, 'toc.html')
    f = codecs.open(toc_path, 'w', 'utf-8')
    f.write(html_toc)
    f.close()

    ncx = gen_ncx(book)
    ncx_path = path.join(work_dir, 'toc.ncx')
    f = codecs.open(ncx_path, 'w', 'utf-8')
    f.write(ncx)
    f.close()

    opf = gen_opf(book)
    opf_path = path.join(work_dir, 'content.opf')
    f = codecs.open(opf_path, 'w', 'utf_8')
    f.write(opf)
    f.close()
    
    return book_title

def build_mobi(book_title, work_dir, output_dir,kindlegen_command):
    """Builds a complete .mobi file from a book directory."""
    command = kindlegen_command + ' ' + path.join(work_dir, 'content.opf') + ' -o output.mobi > /dev/null'
    call(command, shell=True)

    filename = book_title.replace('/', '_') + '.mobi'
    dest_path = path.join(output_dir, filename)
    try:
        move(path.join(work_dir, 'output.mobi'), dest_path)
    except IOError, error:
        print error
        
        
import zipfile
    
        
def build_epub(book_title, work_dir, output_dir):
    """Builds a complete .epub file from a book directory."""



    filename = book_title.replace('/', '_') + '.epub'
    dest_path = path.join(output_dir, filename)
    


    epub = zipfile.ZipFile(dest_path, 'w', compression=zipfile.ZIP_DEFLATED)
    epub.writestr("mimetype", "application/epub+zip")
    epub.writestr("META-INF/container.xml", '''<container version="1.0"
           xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>''');
    
    
    
    root_len = len(path.abspath(work_dir))
    for root, dirs, files in walk(work_dir):
        archive_root = path.abspath(root)[root_len:]
        for f in files:
            fullpath = path.join(root, f)
            archive_name = path.join(archive_root, f)
            epub.write(fullpath, "OEBPS/"+ archive_name, zipfile.ZIP_DEFLATED)
    
    
    
    epub.close()



def books(docset_path, valid_book_types):
    """Returns a list of valid book directories in the specified docset bundle."""
    
    doc_paths = list()
    for paths in walk(docset_path):
        filenames = paths[2]
        if 'book.json' in filenames:
            doc_paths.append(paths[0])
    doc_path_dict = dict()
    
    for doc_path in doc_paths:
        book_path = path.join(doc_path, 'book.json')
        try:
            f = open(book_path, 'r')
            book = json.loads(f.read())
            book_type = get_book_type(book)
            book_title = book.get('title')
            f.close()
            if len(valid_book_types) == 0 or book_type in valid_book_types:
                doc_path_dict[book_title] = doc_path
        except ValueError:
            pass
    return doc_path_dict


def get_book_type(book):
    """Returns the type of the book (loaded from book.json)"""
    
    book_assignments = book.get('assignments')
    book_type = None
    if book_assignments:
        for assignment in book_assignments:
            if assignment.startswith('Type/'):
                book_type = assignment[len('Type/'):]
    return book_type


def gen_opf(book):
    """Generates an OPF file that contains the table of contents from a book (loaded from book.json)."""
    
    title = book.get('title')
    
    opf = '''<?xml version="1.0" encoding="utf-8"?>
        <package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="BookId">
        <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">'''
    opf += '<dc:title>' + title + '</dc:title>'
    opf += '<dc:language>en-us</dc:language>'
    opf += '<meta name="cover" content="My_Cover" />'
    opf += '<dc:creator>Apple Inc.</dc:creator>'
    opf += '<dc:publisher>Apple Inc.</dc:publisher>'
    opf += '<dc:subject>Reference</dc:subject>'
    opf += '</metadata>'
    
    opf += '<manifest>'
    opf += '<item id="My_Cover" media-type="image/gif" href="cover.gif" />'
    opf += '<item id="toc" media-type="application/xhtml+xml" href="toc.html" />'
    i = 1
    all_docs = document_paths(book)
    for doc in all_docs:
        opf += '<item id="chapter_' + str(i) + '" media-type="application/xhtml+xml" href="' + doc + '" />'
        i += 1
    opf += '<item id="My_Table_of_Contents" media-type="application/x-dtbncx+xml" href="toc.ncx"></item>'
    
    opf += '</manifest>'
    
    opf += '<spine toc="My_Table_of_Contents">'
    opf += '<itemref idref="toc"/>'
    i = 1
    for doc in all_docs:
        opf += '<itemref idref="chapter_' + str(i) + '"/>'
        i += 1
    opf += '</spine>'
    
    opf += '<guide>'
    opf += '<reference type="toc" title="Table of Contents" href="toc.html"/>'
    opf += '<reference type="text" title="Text" href="' + list(all_docs)[0] + '" />'
    opf += '</guide>'
    opf += '</package>'
    return opf
    
    
def gen_ncx(book):
    """Generates an NCX file with the logical table of contents (jump markers) from a book (loaded from book.json)."""
    
    header = '''<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN"
    	"http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
        <ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="en-US">
        <head>
        <meta name="dtb:uid" content="BookId"/>
        <meta name="dtb:depth" content="1"/>
        <meta name="dtb:totalPageCount" content="0"/>
        <meta name="dtb:maxPageNumber" content="0"/>
        </head>'''
    footer = '</ncx>' 
    navmap = '<navMap>' + gen_nav_map(book) + '</navMap>'
    ncx = header + navmap + footer
    return ncx


def gen_nav_map(book):
    """Generates a navigation map (part of the NCX file) from a book (loaded from book.json)."""
    
    sections = book.get('sections')
    navmap = ''
    navmap += '<navPoint class="chapter" id="chapter_0" playOrder="0"><navLabel><text>Table of Contents</text></navLabel><content src="toc.html"/></navPoint>'
    order = 1
    for section in sections:
        navmap += '<navPoint class="chapter" id="chapter_' + str(order) + '" playOrder="' + str(order) + '">'
        title = section.get('title')
        navmap += '<navLabel><text>' + title + '</text></navLabel>'
        href = section.get('href')
        navmap += '<content src="' + href + '"/>'
        navmap += '</navPoint>'
        order += 1
    return navmap


def gen_html_toc(book):
    """Generates an HTML table of contents from a book (loaded from book.json)."""
    
    toc = html_toc_fragment(book)
    book_title = book.get('title')
    header = '''<html><head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
        <title>Table of Contents</title>
        <body><h1>''' + book_title + '</h1><h2 style="margin-top: 1em;">Table of Contents</h2>'
    footer = '</body></html>'
    return header + toc + footer


def html_toc_fragment(book):
    """Recursively creates a nested list for the HTML table of contents (used by gen_html_toc)."""
    
    sections = book['sections']
    toc = '<ul>'
    for section in sections:
        href = section.get('href')
        title = section.get('title')
        toc += '<li><a href="' + href + '">' + title + '</a></li>'
        if section.get('sections'):
            toc += html_toc_fragment(section)
    toc += '</ul>'
    return toc


def clean_doc(doc, stylesheet):
    """Prepares an HTML document from a docset for use in mobi (removes javascript, modifies CSS, etc.)."""
    
    head_pattern = re.compile(r'(<meta id=.*)</head>', re.DOTALL)
    cleaned_doc = re.sub(head_pattern, '<style>' + stylesheet + '</style></head>', doc)
    feedback_pattern = re.compile(r'<div id="feedbackForm.*</div>', re.DOTALL)
    cleaned_doc = re.sub(feedback_pattern, '', cleaned_doc)
    tail_scripts_pattern = re.compile(r'</body>(.*)</html>', re.DOTALL)
    cleaned_doc = re.sub(tail_scripts_pattern, '</html>', cleaned_doc)
    cleaned_doc = re.sub('</?article.*>', '', cleaned_doc)
    navigation_links_pattern = re.compile(r'<div id="pageNavigationLinks.*?</div>', re.DOTALL)
    cleaned_doc = re.sub(navigation_links_pattern, '', cleaned_doc)
    copyright_footer_pattern = re.compile(r'<div class="copyright".*</div>', re.DOTALL)
    cleaned_doc = re.sub(copyright_footer_pattern, '', cleaned_doc)
    return cleaned_doc
    
    
def document_paths(book):
    """Returns a list of unique document paths that are present in a book (loaded from book.json)."""
    
    sections = book.get('sections')
    if sections is None: return []
    docs_set = set()
    docs_list = list()
    for section in sections:
        href = section.get('href')
        if href:
            path = href.split('#', 1)[0]
            if path not in docs_set:
                docs_set.add(path)
                docs_list.append(path)
        subsections = section.get('sections')
        if subsections:
            subsection_docs = document_paths(section)
            for path in subsection_docs:
                if path not in docs_set:
                    docs_set.add(path)
                    docs_list.append(path)
    return docs_list
    
    
if __name__ == '__main__':
    main()
    
########NEW FILE########
