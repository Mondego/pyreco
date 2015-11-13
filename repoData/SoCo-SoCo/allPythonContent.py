__FILENAME__ = analyse_ws
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=E0611,R0913

""" Script to analyse ws dumps """

import argparse
import os
import sys
import math
import textwrap
PLATFORM = sys.platform.lower()
if PLATFORM == 'win32':
    import msvcrt
    COLOR = False
else:
    import tty
    import termios
    COLOR = True
import re
import codecs
import ConfigParser
import StringIO
try:
    import pygments
    from pygments.lexers import XmlLexer
    from pygments.formatters import TerminalFormatter
except ImportError:
    print 'Module "pygments" could not be imported. Please install it. '\
        'Exiting!'
    sys.exit(100)
try:
    # Temporarily re-directing stderr to StringIO to prevent start-up message
    # from rdpcap import
    STDERR = sys.stderr
    sys.stderr = StringIO.StringIO()
    from scapy.all import rdpcap
    sys.stderr = STDERR
except ImportError:
    print 'Module "scapy" could not be imported. Please install it. Exiting!'
    sys.exit(101)
try:
    from lxml import etree
    PARSER = etree.XMLParser(remove_blank_text=True)
except ImportError:
    print 'Module "lxml" could not be imported. Please install it. Exiting!'
    sys.exit(102)
import subprocess

# Text bits that starts and ends the Sonos UPnP content
STARTS = ['<s:Envelope', '<e:propertyset']
ENDS = ['</s:Envelope>', '</e:propertyset>']


class AnalyzeWS(object):
    """ Class for analysis of WireShark dumps. Also shows the parts of the
    WireShark dumps syntax highlighted in the terminal and/or writes them to
    files and shows them in a browser.

    The order of processing a file with this class is the following. The
    class is initialized purely with options. All the content is added with
    the set_file method. This method will load the ws file with rdpcap. For
    each part in the ws file that has a load, it will look for Sonos
    content. If such content is present one of three things will happen. If
    it is the beginning of a Sonos message, it will initialize a WSPart. If
    it is the middle part, it will add it to the content of the current
    WSPart with WSPart.add_content. If it is the end, it will finalize the
    WSPart with WSPart.finalize_content. Finalizing the WSPart will, apart
    from closing it for writing also decode the body and parse the XML.

    """

    def __init__(self, args):
        self.messages = []
        self.args = args
        self.output_prefix = args.output_prefix
        try:
            this_dir = os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(this_dir, 'analyse_ws.ini')) as file__:
                self.config = ConfigParser.ConfigParser()
                self.config.readfp(file__)
        except IOError:
            self.config = None
        self.pages = {}

    def set_file(self, filename):
        """ Analyse the file with the captured content """
        # Use the file name as prefix if none is given
        if self.output_prefix is None:
            _, self.output_prefix = os.path.split(filename)
        # Check if the file is present, since rdpcap will not do that
        if not (os.path.isfile(filename) and os.access(filename, os.R_OK)):
            print 'The file \'{0}\' is either not present or not readable. '\
                  'Exiting!'.format(filename)
            sys.exit(1)
        try:
            packets = rdpcap(filename)
        except NameError:
            # Due probably to a bug in rdpcap, this kind of error raises a
            # NameError, because the exception that is tried to raise, is not
            # defined
            print 'The file \'{}\' is not a pcap capture file. Exiting!'\
                .format(filename)
            sys.exit(2)

        for number, packet in enumerate(packets):
            # See if there is a field called load
            self._debug('\nNUMBER {0}'.format(number), no_prefix=True)
            try:
                # Will cause AttributeError if there is no load
                packet.getfieldval('load')
                # Get the full load
                load = packet.sprintf('%TCP.payload%')
                self._debug('PAYLOAD LENGTH {0}'.format(len(load)),
                            no_prefix=True)
                self._debug(load, load=True)
                self._parse_load(load)
            except AttributeError:
                self._debug('LOAD EXCEPTION', no_prefix=True)
        if len(self.messages) > 0 and not self.messages[-1].write_closed:
            self._debug('DELETE LAST OPEN FILE')
            del self.messages[-1]

        if self.args.debug_analysis:
            sys.exit(0)

    def _parse_load(self, load):
        """ Parse the load from a single packet """
        # If the load is ??
        if load in ['??']:
            self._debug('IGNORING')
        # If there is a start in load
        elif any([start in load for start in STARTS]):
            self._debug('START')
            self.messages.append(WSPart(load, self.args))
            # and there is also an end
            if any([end in load for end in ENDS]):
                self.messages[-1].finalize_content()
                self._debug('AND END')
        # If there is an end in load
        elif any([end in load for end in ENDS]):
            # If there is an open WSPart
            if len(self.messages) > 0 and not\
                    self.messages[-1].write_closed:
                self._debug('END ON OPEN FILE')
                self.messages[-1].add_content(load)
                self.messages[-1].finalize_content()
            # Ignore ends before start
            else:
                self._debug('END BUT NO OPEN FILE')
        else:
            # If there is an open WSPart
            if len(self.messages) > 0 and not\
                    self.messages[-1].write_closed:
                self._debug('ADD TO OPEN FILE')
                self.messages[-1].add_content(load)
            # else ignore
            else:
                self._debug('NOTHING TO DO')

    def _debug(self, message, load=False, no_prefix=False):
        """ Output debug information """
        if self.args.debug_analysis:
            if load:
                message = '\r\n'.join(
                    ['# ' + line for line in message.strip().split('\r\n')]
                )
                print '{0}\n{1}\n{0}'.format('#' * 78, message)
            else:
                # If open message and no_prefix is False
                if (len(self.messages) > 0 and not
                        self.messages[-1].write_closed) and not no_prefix:
                    print '--OPEN--> {0}'.format(message)
                else:
                    print message

    def to_file_mode(self):
        """ Write all the messages to files """
        for message_no in range(len(self.messages)):
            self.__to_file(message_no)

    def __to_file(self, message_no):
        """ Write a single message to file """
        filename = self.__create_file_name(message_no)
        try:
            with codecs.open(filename, mode='w',
                             encoding=self.messages[message_no].encoding)\
                    as file__:
                file__.write(self.messages[message_no].output)
        except IOError as excep:
            print 'Unable for open the file \'{0}\' for writing. The '\
                  'following exception was raised:'.format(filename)
            print excep
            print 'Exiting!'
            sys.exit(2)
        return filename

    def __create_file_name(self, message_no):
        """ Create the filename to save to """
        cwd = os.getcwd()
        filename = '{0}_{1}.xml'.format(self.output_prefix, message_no)
        return os.path.join(cwd, filename)

    def to_browser_mode(self):
        """ Write all the messages to files and open them in the browser """
        for message_no in range(len(self.messages)):
            self.__to_browser(message_no)

    def __to_browser(self, message_no):
        """ Write a single message to file and open the file in a
        browser

        """
        filename = self.__to_file(message_no)
        try:
            command = self.config.get('General', 'browser_command')
        except (ConfigParser.NoOptionError, AttributeError):
            print 'Incorrect or missing .ini file. See --help.'
            sys.exit(5)
        command = str(command).format(filename)
        command_list = command.split(' ')
        try:
            subprocess.Popen(command_list, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        except OSError:
            print 'Unable to execute the browsercommand:'
            print command
            print 'Exiting!'
            sys.exit(21)

    def interactive_mode(self):
        """ Interactive mode """
        if PLATFORM == 'win32':
            # Defaulting to 80 on windows, better ideas are welcome, but the
            # solutions I found online are rather bulky
            height = 20
            width = 80
        else:
            height, width = os.popen('stty size', 'r').read().split()
            width = int(width)
            height = int(height)

        message_no = 0
        page_no = 0
        action = None
        while action != 'q':
            page_no = self.__update_window(width, height, message_no, page_no)
            action = getch()
            if action == 's':
                # Coerce in range
                message_no = \
                    max(min(len(self.messages) - 1, message_no + 1), 0)
                page_no = 0
            elif action == 'w':
                # Coerce in range
                message_no = \
                    max(min(len(self.messages) - 1, message_no - 1), 0)
                page_no = 0
            elif action == 'a':
                page_no -= 1
            elif action == 'd':
                page_no += 1
            elif action == 'b':
                self.__to_browser(message_no)
            elif action == 'f':
                self.__to_file(message_no)

    def __update_window(self, width, height, message_no, page_no):
        """ Update the window with the menu and the new text """
        file_exists_label = '-F-ILE'
        if not os.path.exists(self.__create_file_name(message_no)):
            file_exists_label = '(f)ile'

        # Clear the screen
        if PLATFORM == 'win32':
            # Ugly hack until someone figures out a better way for Windows
            # probably something with a cls command, but I cannot test it
            for _ in range(50):
                print
        else:
            sys.stdout.write('\x1b[2J\x1b[H')  # Clear screen

        # Content
        content = self.messages[message_no].output.rstrip('\n')
        out = content
        if self.args.color:
            out = pygments.highlight(content, XmlLexer(), TerminalFormatter())

        # Paging functionality
        if message_no not in self.pages:
            self._form_pages(message_no, content, out, height, width)
        # Coerce in range
        page_no = max(min(len(self.pages[message_no]) - 1, page_no), 0)
        page_content = self.pages[message_no][page_no]

        # Menu
        max_message = str(len(self.messages) - 1)
        position_string = u'{{0: >{0}}}/{{1: <{0}}}'.format(len(max_message))
        position_string = position_string.format(message_no, max_message)
        # Assume less than 100 pages
        current_max_page = len(self.pages[message_no]) - 1
        pages_string = u'{0: >2}/{1: <2}'.format(page_no, current_max_page)
        menu = (u'(b)rowser | {0} | Message {1} \u2193 (s)\u2191 (w) | '
                u'Page {2} \u2190 (a)\u2192 (d) | (q)uit\n{3}').\
            format(file_exists_label, position_string, pages_string,
                   '-' * width)

        print menu
        print page_content
        return page_no

    def _form_pages(self, message_no, content, out, height, width):
        """ Form the pages """
        self.pages[message_no] = []
        page_height = height - 4  # 2-3 for menu, 1 for cursor
        outline = u''
        no_lines_page = 0
        for original, formatted in zip(content.split('\n'), out.split('\n')):
            no_lines_original = int(math.ceil(len(original) / float(width)))

            # Blank line
            if len(original) == 0:
                if no_lines_page + 1 <= page_height:
                    outline += u'\n'
                    no_lines_page += 1
                else:
                    self.pages[message_no].append(outline)
                    outline = u'\n'
                    no_lines_page = 1
                original = formatted = u'\n'
            # Too large line
            elif no_lines_original > page_height:
                if len(outline) > 0:
                    self.pages[message_no].append(outline)
                    outline = u''
                    no_lines_page = 0
                self.pages[message_no].append(formatted)
            # The line(s) can be added to the current page
            elif no_lines_page + no_lines_original <= page_height:
                if len(outline) > 0:
                    outline += u'\n'
                outline += formatted
                no_lines_page += no_lines_original
            # End the page and start a new
            else:
                self.pages[message_no].append(outline)
                outline = formatted
                no_lines_page = no_lines_original
        # Add the remainder
        if len(outline) > 0:
            self.pages[message_no].append(outline)
        if len(self.pages[message_no]) == 0:
            self.pages[message_no].append(u'')


class WSPart(object):
    """ This class parses and represents a single Sonos UPnP message """

    def __init__(self, captured, args):
        self.external_inner_xml = args.external_inner_xml
        self.inner_xml = []
        self.body_formatted = u''
        self.output = u''
        self.write_closed = False
        # Analyze initial xml part
        try:
            raw_head, self.raw_body = captured.split('\r\n\r\n')
        except ValueError:
            raw_head = ''
            self.raw_body = captured
        # Get encoding
        search = re.search(r'.*charset="(.*)"', raw_head)
        try:
            self.encoding = search.group(1)
        except AttributeError:
            self.encoding = 'utf-8'

    def add_content(self, captured):
        """ Adds content to the main UPnP message """
        self.raw_body += captured

    def finalize_content(self):
        """ Finalize the additons """
        self.write_closed = True
        body = self.raw_body.decode(self.encoding)
        self._init_xml(body)
        self._form_output()

    def _init_xml(self, body):
        """ Parse the present body as xml """
        tree = etree.fromstring(body.encode(self.encoding), PARSER)
        # Extract and replace inner DIDL xml in tags
        for text in tree.xpath('.//text()[contains(., "DIDL")]'):
            item = text.getparent()
            didl_tree = etree.fromstring(item.text)
            if self.external_inner_xml:
                item.text = 'DIDL_REPLACEMENT_{0}'.format(len(self.inner_xml))
                self.inner_xml.append(didl_tree)
            else:
                item.text = None
                item.append(didl_tree)

        # Extract and replace inner DIDL xml in properties in inner xml
        for inner_tree in self.inner_xml:
            for item in inner_tree.xpath('//*[contains(@val, "DIDL")]'):
                if self.external_inner_xml:
                    didl_tree = etree.fromstring(item.attrib['val'])
                    item.attrib['val'] = 'DIDL_REPLACEMENT_{0}'.\
                        format(len(self.inner_xml))
                    self.inner_xml.append(didl_tree)

        self.body_formatted = etree.tostring(tree, pretty_print=True).decode(
            self.encoding)
        #print tree
        #print repr(self.body_formatted)
        #sys.exit(1)

    def _form_output(self):
        """ Form the output """
        self.output = u''
        if self.external_inner_xml:
            self.output += u'<Dummy_tag_to_create_valid_xml_on_external_inner'\
                           '_xml>\n'
        self.output += u'<!-- BODY -->\n{0}'.format(self.body_formatted)

        if self.external_inner_xml:
            for number, didl in enumerate(self.inner_xml):
                self.output += u'\n<!-- DIDL_{0} -->\n{1}'.\
                    format(number, etree.tostring(didl, pretty_print=True))
            self.output += u'</Dummy_tag_to_create_valid_xml_on_external_'\
                           'inner_xml>'


def __build_option_parser():
    """ Build the option parser for this script """
    description = """
    Tool to analyze Wireshark dumps of Sonos traffic.

    The files that are input to this script must be in the
    "Wireshark/tcpdump/...-libpcap" format, which can be exported from
    Wireshark.

    To use the open in browser function, a configuration file must be
    written. It should be in the same directory as this script and have the
    name "analyse_ws.ini". An example of such a file is given below ({0}
    indicates the file):
    [General]
    browser_command: epiphany {0}

    The browser command should be any command that opens a new tab in
    the program you wish to read the Wireshark dumps in.

    Separating Sonos traffic out from the rest of the network traffic is
    tricky. Therefore, it will in all likelyhood increase the succes of
    this tool, if the traffic is filtered in Wireshark to only show
    traffic to and from the Sonos unit. Still, if the analysis fails,
    then use the debug mode. This will show you the analysis of the
    traffic packet by packet and give you packet numbers so you can find
    and analyze problematic packets in Wireshark.
    """
    description = textwrap.dedent(description).strip()

    parser = \
        argparse.ArgumentParser(description=description,
                                formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('file_', metavar='FILE', type=str, nargs=1,
                        help='the file to analyze')
    parser.add_argument('-o', '--output-prefix', type=str,
                        help='the output filename prefix to use')
    parser.add_argument('-f', '--to-file', action='store_const', const=True,
                        help='output xml to files', default=False)
    parser.add_argument('-d', '--debug-analysis', action='store_const',
                        const=True,
                        help='writes debug information to file.debug',
                        default=False)
    parser.add_argument('-m', '--disable-color', action='store_const',
                        const=False, help='disable color in interactive mode',
                        default=COLOR, dest='color')
    parser.add_argument('-c', '--enable-color', action='store_const',
                        const=True, help='disable color in interactive mode',
                        default=COLOR, dest='color')
    parser.add_argument('-b', '--to-browser', action='store_const', const=True,
                        help='output xml to browser, implies --to-file',
                        default=False)
    parser.add_argument('-e', '--external-inner-xml', action='store_const',
                        const=True, help='show the internal separately '
                        'encoded xml externally instead of re-integrating it',
                        default=False)
    return parser


def getch():
    """ Read a single character non-echoed and return it. Recipy from:
    http://code.activestate.com/recipes/
    134892-getch-like-unbuffered-character-reading-from-stdin/
    """
    filedescriptor = sys.stdin.fileno()
    old_settings = termios.tcgetattr(filedescriptor)
    if PLATFORM == 'win32':
        character = msvcrt.getch()
    else:
        try:
            tty.setraw(sys.stdin.fileno())
            character = sys.stdin.read(1)
        finally:
            termios.tcsetattr(filedescriptor, termios.TCSADRAIN, old_settings)
    return character


def main():
    """ Main method of the script """
    parser = __build_option_parser()
    args = parser.parse_args()
    analyze_ws = AnalyzeWS(args)
    try:
        analyze_ws.set_file(args.file_[0])
    except IOError:
        print 'IOError raised while reading file. Exiting!'
        sys.exit(3)

    # Start the chosen mode
    if args.to_file or args.to_browser:
        analyze_ws.to_file_mode()
        if args.to_browser:
            analyze_ws.to_browser_mode()
    else:
        analyze_ws.interactive_mode()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Sonos Controller (SoCo) documentation build configuration file, created by
# sphinx-quickstart on Sun Feb 24 10:28:22 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.join(os.path.abspath('.'), '..'))

import soco

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx',
              'sphinx.ext.inheritance_diagram']
intersphinx_mapping = {'python': ('http://docs.python.org/2', None)}

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'SoCo (Sonos Controller)'
copyright = u'2013, Rahim Sonawalla, et al.'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = soco.__version__
# The full version, including alpha/beta/rc tags.
release = soco.__version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

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
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

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
htmlhelp_basename = 'SoCoDoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'SonosControllerSoCo.tex', u'SoCo (Sonos Controller) Documentation',
   u'Rahim Sonawalla, et al.', 'manual'),
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

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'sonoscontrollersoco', u'SoCo (Sonos Controller) Documentation',
     [u'Rahim Sonawalla, et al.'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'SonosControllerSoCo', u'SoCo (Sonos Controller) Documentation',
   u'Rahim Sonawalla, et al.', 'SonosControllerSoCo', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = tunein
#!/usr/bin/env python
"""
Play a selected favorite radio station from the TuneIn service on your Sonos
system, or a short clip from each favorite.

Pass an IP address as the first command-line argument. If you specify a preset
as the second argument, that radio station will be played. Otherwise a short
clip from each preset will be played.

"""
import sys
import time

from soco import SoCo

meta_template = """
<DIDL-Lite xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"
    xmlns:r="urn:schemas-rinconnetworks-com:metadata-1-0/"
    xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/">
    <item id="R:0/0/0" parentID="R:0/0" restricted="true">
        <dc:title>{title}</dc:title>
        <upnp:class>object.item.audioItem.audioBroadcast</upnp:class>
        <desc id="cdudn" nameSpace="urn:schemas-rinconnetworks-com:metadata-1-0/">
            {service}
        </desc>
    </item>
</DIDL-Lite>' """

tunein_service = 'SA_RINCON65031_'

if __name__ == '__main__':

    if (len(sys.argv) < 2):
        print 'Please pass the IP address of a Zone Player as the first argument'
        sys.exit()

    speaker_ip = sys.argv[1]
    preset = 0
    limit = 12

    if (len(sys.argv) == 3):
        preset = int(sys.argv[2]) - 1
        limit = 1

    mySonos = SoCo(speaker_ip)

    if mySonos:
        stations = mySonos.get_favorite_radio_stations(preset, limit)
        print 'returned %s of a possible %s radio stations:' % (
            stations['returned'], stations['total'])
    for station in stations['favorites']:
        print station['title']
        uri = station['uri']
        # TODO seems at least & needs to be escaped - should move this to
        # play_uri and maybe escape other chars.
        uri = uri.replace('&', '&amp;')

        metadata = meta_template.format(title=station['title'], service=tunein_service)

        print mySonos.play_uri(uri, metadata)

        if (len(sys.argv) == 2):
            time.sleep(10)

########NEW FILE########
__FILENAME__ = socoplugins
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This illustrates how to use SoCo plugins
# an example plugin is provided in soco.plugins.example.ExamplePlugin

import time

from soco import SoCo, SonosDiscovery
from soco.plugins import SoCoPlugin


def main():
    sd = SonosDiscovery()
    speakers = sd.get_speaker_ips()

    if not speakers:
        print 'no speakers found, exiting.'
        return

    soco = SoCo(speakers[0])

    # get a plugin by name (eg from a config file)
    myplugin = SoCoPlugin.from_name('soco.plugins.example.ExamplePlugin',
                                    soco, 'some user')

    # do something with your plugin
    print 'Testing', myplugin.name
    myplugin.music_plugin_play()


    time.sleep(5)

    # create a plugin by normal instantiation
    from soco.plugins.example import ExamplePlugin

    # create a new plugin, pass the soco instance to it
    myplugin = ExamplePlugin(soco, 'a user')

    print 'Testing', myplugin.name

    # do something with your plugin
    myplugin.music_plugin_stop()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = index
import time
import hashlib
import json

import requests
from flask import Flask, render_template, url_for

from soco import SoCo

app = Flask(__name__)

app.config.from_pyfile('settings.py')

sonos = SoCo(app.config['SPEAKER_IP'])


def gen_sig():
    return hashlib.md5(
        app.config['ROVI_API_KEY'] +
        app.config['ROVI_SHARED_SECRET'] +
        repr(int(time.time()))).hexdigest()


def get_track_image(artist, album):
    blank_image = url_for('static', filename='img/blank.jpg')
    if 'ROVI_SHARED_SECRET' not in app.config:
        return blank_image
    elif 'ROVI_API_KEY' not in app.config:
        return blank_image

    headers = {
        "Accept-Encoding": "gzip"
    }
    req = requests.get(
        'http://api.rovicorp.com/recognition/v2.1/music/match/album?apikey=' +
        app.config['ROVI_API_KEY'] + '&sig=' + gen_sig() + '&name= ' +
        album + '&performername=' + artist + '&include=images&size=1',
        headers=headers)

    if req.status_code != requests.codes.ok:
        return blank_image

    result = json.loads(req.content)
    try:
        return result['matchResponse']['results'][0]['album']['images']\
            [0]['front'][3]['url']
    except (KeyError, IndexError):
        return blank_image


@app.route("/play")
def play():
    sonos.play()
    return 'Ok'


@app.route("/pause")
def pause():
    sonos.pause()
    return 'Ok'


@app.route("/next")
def next():
    sonos.next()
    return 'Ok'


@app.route("/previous")
def previous():
    sonos.previous()
    return 'Ok'


@app.route("/info-light")
def info_light():
    track = sonos.get_current_track_info()
    return json.dumps(track)


@app.route("/info")
def info():
    track = sonos.get_current_track_info()
    track['image'] = get_track_image(track['artist'], track['album'])
    return json.dumps(track)


@app.route("/")
def index():
    track = sonos.get_current_track_info()
    track['image'] = get_track_image(track['artist'], track['album'])
    return render_template('index.html', track=track)


if __name__ == '__main__':
    app.run(debug=True)

########NEW FILE########
__FILENAME__ = compat

""" Module that contains various compatability definitions and imports """

# pylint: disable=unused-import,import-error,no-name-in-module


try:  # python 3
    from http.server import SimpleHTTPRequestHandler  # nopep8
    from urllib.request import urlopen  # nopep8
    from urllib.error import URLError  # nopep8
    from urllib.parse import quote_plus  # nopep8
    import socketserver  # nopep8
    from queue import Queue  # nopep8
    StringType = bytes  # nopep8
    UnicodeType = str  # nopep8

except ImportError:  # python 2.7
    from SimpleHTTPServer import SimpleHTTPRequestHandler  # nopep8
    from urllib2 import urlopen, URLError  # nopep8
    from urllib import quote_plus  # nopep8
    import SocketServer as socketserver  # nopep8
    from Queue import Queue  # nopep8
    from types import StringType, UnicodeType  # nopep8

try:  # python 2.7 - this has to be done the other way rund
    from cPickle import dumps  # nopep8
except ImportError:  # python 3
    from pickle import dumps  # nopep8

########NEW FILE########
__FILENAME__ = core
# -*- coding: utf-8 -*-
# pylint: disable=C0302,fixme, protected-access
""" The core module contains SonosDiscovery and SoCo classes that implement
the main entry to the SoCo functionality
"""

from __future__ import unicode_literals

import select
import socket
import logging
import traceback
from textwrap import dedent
import re
import itertools
import requests

from .services import DeviceProperties, ContentDirectory
from .services import RenderingControl, AVTransport, ZoneGroupTopology
from .groups import ZoneGroup
from .exceptions import CannotCreateDIDLMetadata
from .data_structures import get_ml_item, QueueItem
from .utils import really_utf8, camel_to_underscore
from .xml import XML

LOGGER = logging.getLogger(__name__)


def discover(timeout=1, include_invisible=False):
    """ Discover Sonos zones on the local network.

    Return an set of visible SoCo instances for each zone found.
    Include invisible zones (bridges and slave zones in stereo pairs if
    `include_invisible` is True. Will block for up to `timeout` seconds, after
    which return `None` if no zones found.

    """

    # pylint: disable=invalid-name
    PLAYER_SEARCH = dedent(b"""\
        M-SEARCH * HTTP/1.1
        HOST: 239.255.255.250:reservedSSDPport
        MAN: "ssdp:discover"
        MX: 1
        ST: urn:schemas-upnp-org:device:ZonePlayer:1
        """)
    MCAST_GRP = "239.255.255.250"
    MCAST_PORT = 1900

    _sock = socket.socket(
        socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    _sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    _sock.sendto(really_utf8(PLAYER_SEARCH), (MCAST_GRP, MCAST_PORT))

    response, _, _ = select.select([_sock], [], [], timeout)
    # Only Zone Players will respond, given the value of ST in the
    # PLAYER_SEARCH message. It doesn't matter what response they make. All
    # we care about is the IP address
    if response:
        _, addr = _sock.recvfrom(1024)
        # Now we have an IP, we can build a SoCo instance and query the
        # topology to find the other players.
        zone = SoCo(addr[0])
        if include_invisible:
            return zone.all_zones
        else:
            return zone.visible_zones
    else:
        return None


class SonosDiscovery(object):  # pylint: disable=R0903
    """Retained for backward compatibility only. Will be removed in future
    releases

    .. deprecated:: 0.7
       Use :func:`discover` instead.

    """

    def __init__(self):
        import warnings
        warnings.warn("SonosDiscovery is deprecated. Use discover instead.")

    @staticmethod
    def get_speaker_ips():
        """ Deprecated in favour of discover() """
        import warnings
        warnings.warn("get_speaker_ips is deprecated. Use discover instead.")
        return [i.ip_address for i in discover()]


class _ArgsSingleton(type):
    """ A metaclass which permits only a single instance of each derived class
    to exist for any given set of positional arguments.

    Attempts to instantiate a second instance of a derived class will return
    the existing instance.

    For example:

    >>> class ArgsSingletonBase(object):
    ...     __metaclass__ = _ArgsSingleton
    ...
    >>> class First(ArgsSingletonBase):
    ...     def __init__(self, param):
    ...         pass
    ...
    >>> assert First('hi') is First('hi')
    >>> assert First('hi') is First('bye')
    AssertionError

     """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = {}
        if args not in cls._instances[cls]:
            cls._instances[cls][args] = super(_ArgsSingleton, cls).__call__(
                *args, **kwargs)
        return cls._instances[cls][args]


class _SocoSingletonBase(  # pylint: disable=too-few-public-methods
        _ArgsSingleton(str('ArgsSingletonMeta'), (object,), {})):
    """ The base class for the SoCo class.

    Uses a Python 2 and 3 compatible method of declaring a metaclass. See, eg,
    here: http://www.artima.com/weblogs/viewpost.jsp?thread=236234 and
    here: http://mikewatkins.ca/2008/11/29/python-2-and-3-metaclasses/

    """
    pass


# pylint: disable=R0904,too-many-instance-attributes
class SoCo(_SocoSingletonBase):
    """A simple class for controlling a Sonos speaker.

    For any given set of arguments to __init__, only one instance of this class
    may be created. Subsequent attempts to create an instance with the same
    arguments will return the previously created instance. This means that all
    SoCo instances created with the same ip address are in fact the *same* SoCo
    instance, reflecting the real world position.

    Public functions::

        play -- Plays the current item.
        play_uri -- Plays a track or a music stream by URI.
        play_from_queue -- Plays an item in the queue.
        pause -- Pause the currently playing track.
        stop -- Stop the currently playing track.
        seek -- Move the currently playing track a given elapsed time.
        next -- Go to the next track.
        previous -- Go back to the previous track.
        switch_to_line_in -- Switch the speaker's input to line-in.
        switch_to_tv -- Switch the speaker's input to TV.
        get_current_track_info -- Get information about the currently playing
                                  track.
        get_speaker_info -- Get information about the Sonos speaker.
        partymode -- Put all the speakers in the network in the same group.
        join -- Join this speaker to another "master" speaker.
        unjoin -- Remove this speaker from a group.
        get_queue -- Get information about the queue.
        get_folders -- Get search folders from the music library
        get_artists -- Get artists from the music library
        get_album_artists -- Get album artists from the music library
        get_albums -- Get albums from the music library
        get_genres -- Get genres from the music library
        get_composers -- Get composers from the music library
        get_tracks -- Get tracks from the music library
        get_playlists -- Get playlists from the music library
        get_music_library_information -- Get information from the music library
        get_current_transport_info -- get speakers playing state
        add_to_queue -- Add a track to the end of the queue
        remove_from_queue -- Remove a track from the queue
        clear_queue -- Remove all tracks from queue
        get_favorite_radio_shows -- Get favorite radio shows from Sonos'
                                    Radio app.
        get_favorite_radio_stations -- Get favorite radio stations.

    Properties::

        uid -- The speaker's unique identifier
        mute -- The speaker's mute status.
        volume -- The speaker's volume.
        bass -- The speaker's bass EQ.
        treble -- The speaker's treble EQ.
        loudness -- The status of the speaker's loudness compensation.
        status_light -- The state of the Sonos status light.
        player_name  -- The speaker's name.
        play_mode -- The queue's repeat/shuffle settings.

    .. warning::

        These properties are not cached and will obtain information over the
        network, so may take longer than expected to set or return a value. It
        may be a good idea for you to cache the value in your own code.

    """

    def __init__(self, ip_address):
        # Note: Creation of a SoCo instance should be as cheap and quick as
        # possible. Do not make any network calls here
        super(SoCo, self).__init__()
        # Check if ip_address is a valid IPv4 representation.
        # Sonos does not (yet) support IPv6
        try:
            socket.inet_aton(ip_address)
        except socket.error:
            raise ValueError("Not a valid IP address string")
        #: The speaker's ip address
        self.ip_address = ip_address
        self.speaker_info = {}  # Stores information about the current speaker

        # The services which we use
        # pylint: disable=invalid-name
        self.avTransport = AVTransport(self)
        self.contentDirectory = ContentDirectory(self)
        self.deviceProperties = DeviceProperties(self)
        self.renderingControl = RenderingControl(self)
        self.zoneGroupTopology = ZoneGroupTopology(self)

        # Some private attributes
        self._all_zones = set()
        self._groups = set()
        self._is_bridge = None
        self._player_name = None
        self._uid = None
        self._visible_zones = set()
        self._zgs_cache = None

    def __str__(self):
        return "<SoCo object at ip {}>".format(self.ip_address)

    def __repr__(self):
        return '{}("{}")'.format(self.__class__.__name__, self.ip_address)

    @property
    def player_name(self):
        """  The speaker's name. A string. """
        # We could get the name like this:
        # result = self.deviceProperties.GetZoneAttributes()
        # return result["CurrentZoneName"]
        # but it is probably quicker to get it from the group topology
        # and take advantage of any caching
        self._parse_zone_group_state()
        return self._player_name

    @player_name.setter
    def player_name(self, playername):
        """ Set the speaker's name """
        self.deviceProperties.SetZoneAtrributes([
            ('DesiredZoneName', playername),
            ('DesiredIcon', ''),
            ('DesiredConfiguration', '')
            ])

    @property
    def uid(self):
        """ A unique identifier.  Looks like: RINCON_000XXXXXXXXXX1400 """
        # Since this does not change over time (?) check whether we already
        # know the answer. If so, there is no need to go further
        if self._uid is not None:
            return self._uid
        # if not, we have to get it from the zone topology, which
        # is probably quicker than any alternative, since the zgt is probably
        # cached. This will set self._uid for us for next time, so we won't
        # have to do this again
        self._parse_zone_group_state()
        return self._uid
        # An alternative way of getting the uid is as follows:
        # self.device_description_url = \
        #    'http://{}:1400/xml/device_description.xml'.format(
        #     self.ip_address)
        # response = requests.get(self.device_description_url).text
        # tree = XML.fromstring(response.encode('utf-8'))
        # udn = tree.findtext('.//{urn:schemas-upnp-org:device-1-0}UDN')
        # # the udn has a "uuid:" prefix before the uid, so we need to strip it
        # self._uid = uid = udn[5:]
        # return uid

    @property
    def is_visible(self):
        """ Is this zone visible? A zone might be invisible if, for example it
        is a bridge, or the slave part of stereo pair.

        return True or False

        """
        # We could do this:
        # invisible = self.deviceProperties.GetInvisible()['CurrentInvisible']
        # but it is better to do it in the following way, which uses the
        # zone group topology, to capitalise on any caching.
        return self in self.visible_zones

    @property
    def is_bridge(self):
        """ Is this zone a bridge? """
        # Since this does not change over time (?) check whether we already
        # know the answer. If so, there is no need to go further
        if self._is_bridge is not None:
            return self._is_bridge
        # if not, we have to get it from the zone topology. This will set
        # self._is_bridge for us for next time, so we won't have to do this
        # again
        self._parse_zone_group_state()
        return self._is_bridge

    @property
    def play_mode(self):
        """ The queue's play mode. Case-insensitive options are::

        NORMAL -- Turns off shuffle and repeat.
        REPEAT_ALL -- Turns on repeat and turns off shuffle.
        SHUFFLE -- Turns on shuffle *and* repeat. (It's strange, I know.)
        SHUFFLE_NOREPEAT -- Turns on shuffle and turns off repeat.

        """
        result = self.avTransport.GetTransportSettings([
            ('InstanceID', 0),
            ])
        return result['PlayMode']

    @play_mode.setter
    def play_mode(self, playmode):
        """ Set the speaker's mode """
        modes = ('NORMAL', 'SHUFFLE_NOREPEAT', 'SHUFFLE', 'REPEAT_ALL')
        playmode = playmode.upper()
        if playmode not in modes:
            raise KeyError('invalid play mode')

        self.avTransport.SetPlayMode([
            ('InstanceID', 0),
            ('NewPlayMode', playmode)
            ])

    @property
    def speaker_ip(self):
        """Retained for backward compatibility only. Will be removed in future
        releases

        .. deprecated:: 0.7
           Use :attr:`ip_address` instead.

        """
        import warnings
        warnings.warn("speaker_ip is deprecated. Use ip_address instead.")
        return self.ip_address

    def play_from_queue(self, index):
        """ Play a track from the queue by index. The index number is
        required as an argument, where the first index is 0.

        index: the index of the track to play; first item in the queue is 0

        Returns:
        True if the Sonos speaker successfully started playing the track.

        Raises SoCoException (or a subclass) upon errors.

        """
        # Grab the speaker's information if we haven't already since we'll need
        # it in the next step.
        if not self.speaker_info:
            self.get_speaker_info()

        # first, set the queue itself as the source URI
        uri = 'x-rincon-queue:{0}#0'.format(self.uid)
        self.avTransport.SetAVTransportURI([
            ('InstanceID', 0),
            ('CurrentURI', uri),
            ('CurrentURIMetaData', '')
            ])

        # second, set the track number with a seek command
        self.avTransport.Seek([
            ('InstanceID', 0),
            ('Unit', 'TRACK_NR'),
            ('Target', index + 1)
            ])

        # finally, just play what's set
        return self.play()

    def play(self):
        """Play the currently selected track.

        Returns:
        True if the Sonos speaker successfully started playing the track.

        Raises SoCoException (or a subclass) upon errors.

        """
        self.avTransport.Play([
            ('InstanceID', 0),
            ('Speed', 1)
            ])

    def play_uri(self, uri='', meta=''):
        """ Play a given stream. Pauses the queue.

        Arguments:
        uri -- URI of a stream to be played.
        meta --- The track metadata to show in the player, DIDL format.

        Returns:
        True if the Sonos speaker successfully started playing the track.

        Raises SoCoException (or a subclass) upon errors.

        """

        self.avTransport.SetAVTransportURI([
            ('InstanceID', 0),
            ('CurrentURI', uri),
            ('CurrentURIMetaData', meta)
            ])
        # The track is enqueued, now play it.
        return self.play()

    def pause(self):
        """ Pause the currently playing track.

        Returns:
        True if the Sonos speaker successfully paused the track.

        Raises SoCoException (or a subclass) upon errors.

        """
        self.avTransport.Pause([
            ('InstanceID', 0),
            ('Speed', 1)
            ])

    def stop(self):
        """ Stop the currently playing track.

        Returns:
        True if the Sonos speaker successfully stopped the playing track.

        Raises SoCoException (or a subclass) upon errors.

        """
        self.avTransport.Stop([
            ('InstanceID', 0),
            ('Speed', 1)
            ])

    def seek(self, timestamp):
        """ Seeks to a given timestamp in the current track, specified in the
        format of HH:MM:SS or H:MM:SS.

        Returns:
        True if the Sonos speaker successfully seeked to the timecode.

        Raises SoCoException (or a subclass) upon errors.

        """
        if not re.match(r'^[0-9][0-9]?:[0-9][0-9]:[0-9][0-9]$', timestamp):
            raise ValueError('invalid timestamp, use HH:MM:SS format')

        self.avTransport.Seek([
            ('InstanceID', 0),
            ('Unit', 'REL_TIME'),
            ('Target', timestamp)
            ])

    def next(self):
        """ Go to the next track.

        Returns:
        True if the Sonos speaker successfully skipped to the next track.

        Raises SoCoException (or a subclass) upon errors.

        Keep in mind that next() can return errors
        for a variety of reasons. For example, if the Sonos is streaming
        Pandora and you call next() several times in quick succession an error
        code will likely be returned (since Pandora has limits on how many
        songs can be skipped).

        """
        self.avTransport.Next([
            ('InstanceID', 0),
            ('Speed', 1)
            ])

    def previous(self):
        """ Go back to the previously played track.

        Returns:
        True if the Sonos speaker successfully went to the previous track.

        Raises SoCoException (or a subclass) upon errors.

        Keep in mind that previous() can return errors
        for a variety of reasons. For example, previous() will return an error
        code (error code 701) if the Sonos is streaming Pandora since you can't
        go back on tracks.

        """
        self.avTransport.Previous([
            ('InstanceID', 0),
            ('Speed', 1)
            ])

    @property
    def mute(self):
        """ The speaker's mute state. True if muted, False otherwise """

        response = self.renderingControl.GetMute([
            ('InstanceID', 0),
            ('Channel', 'Master')
            ])
        mute_state = response['CurrentMute']
        return True if int(mute_state) else False

    @mute.setter
    def mute(self, mute):
        """ Mute (or unmute) the speaker """
        mute_value = '1' if mute else '0'
        self.renderingControl.SetMute([
            ('InstanceID', 0),
            ('Channel', 'Master'),
            ('DesiredMute', mute_value)
            ])

    @property
    def volume(self):
        """ The speaker's volume. An integer between 0 and 100. """

        response = self.renderingControl.GetVolume([
            ('InstanceID', 0),
            ('Channel', 'Master'),
            ])
        volume = response['CurrentVolume']
        return int(volume)

    @volume.setter
    def volume(self, volume):
        """ Set the speaker's volume """
        volume = int(volume)
        volume = max(0, min(volume, 100))  # Coerce in range
        self.renderingControl.SetVolume([
            ('InstanceID', 0),
            ('Channel', 'Master'),
            ('DesiredVolume', volume)
            ])

    @property
    def bass(self):
        """ The speaker's bass EQ. An integer between -10 and 10. """

        response = self.renderingControl.GetBass([
            ('InstanceID', 0),
            ('Channel', 'Master'),
            ])
        bass = response['CurrentBass']
        return int(bass)

    @bass.setter
    def bass(self, bass):
        """ Set the speaker's bass """
        bass = int(bass)
        bass = max(-10, min(bass, 10))  # Coerce in range
        self.renderingControl.SetBass([
            ('InstanceID', 0),
            ('DesiredBass', bass)
            ])

    @property
    def treble(self):
        """ The speaker's treble EQ. An integer between -10 and 10. """

        response = self.renderingControl.GetTreble([
            ('InstanceID', 0),
            ('Channel', 'Master'),
            ])
        treble = response['CurrentTreble']
        return int(treble)

    @treble.setter
    def treble(self, treble):
        """ Set the speaker's treble """
        treble = int(treble)
        treble = max(-10, min(treble, 10))  # Coerce in range
        self.renderingControl.SetTreble([
            ('InstanceID', 0),
            ('DesiredTreble', treble)
            ])

    @property
    def loudness(self):
        """ The Sonos speaker's loudness compensation. True if on, otherwise
        False.

        Loudness is a complicated topic. You can find a nice summary about this
        feature here: http://forums.sonos.com/showthread.php?p=4698#post4698

        """
        response = self.renderingControl.GetLoudness([
            ('InstanceID', 0),
            ('Channel', 'Master'),
            ])
        loudness = response["CurrentLoudness"]
        return True if int(loudness) else False

    @loudness.setter
    def loudness(self, loudness):
        """ Switch on/off the speaker's loudness compensation """
        loudness_value = '1' if loudness else '0'
        self.renderingControl.SetLoudness([
            ('InstanceID', 0),
            ('Channel', 'Master'),
            ('DesiredLoudness', loudness_value)
            ])

    def _parse_zone_group_state(self):
        """ The Zone Group State contains a lot of useful information. Retrieve
        and parse it, and populate the relevant properties. """

# zoneGroupTopology.GetZoneGroupState()['ZoneGroupState'] returns XML like
# this:
#
# <ZoneGroups>
#   <ZoneGroup Coordinator="RINCON_000XXX1400" ID="RINCON_000XXXX1400:0">
#     <ZoneGroupMember
#         BootSeq="33"
#         Configuration="1"
#         Icon="x-rincon-roomicon:zoneextender"
#         Invisible="1"
#         IsZoneBridge="1"
#         Location="http://192.168.1.100:1400/xml/device_description.xml"
#         MinCompatibleVersion="22.0-00000"
#         SoftwareVersion="24.1-74200"
#         UUID="RINCON_000ZZZ1400"
#         ZoneName="BRIDGE"/>
#   </ZoneGroup>
#   <ZoneGroup Coordinator="RINCON_000XXX1400" ID="RINCON_000XXX1400:46">
#     <ZoneGroupMember
#         BootSeq="44"
#         Configuration="1"
#         Icon="x-rincon-roomicon:living"
#         Location="http://192.168.1.101:1400/xml/device_description.xml"
#         MinCompatibleVersion="22.0-00000"
#         SoftwareVersion="24.1-74200"
#         UUID="RINCON_000XXX1400"
#         ZoneName="Living Room"/>
#     <ZoneGroupMember
#         BootSeq="52"
#         Configuration="1"
#         Icon="x-rincon-roomicon:kitchen"
#         Location="http://192.168.1.102:1400/xml/device_description.xml"
#         MinCompatibleVersion="22.0-00000"
#         SoftwareVersion="24.1-74200"
#         UUID="RINCON_000YYY1400"
#         ZoneName="Kitchen"/>
#   </ZoneGroup>
# </ZoneGroups>
#

        # This is called quite frequently, so it is worth optimising it.
        # Maintain a private cache. If the zgt has not changed, there is no
        # need to repeat all the XML parsing. In addition, switch on network
        # caching for a short interval (5 secs).
        zgs = self.zoneGroupTopology.GetZoneGroupState(
            cache_timeout=5)['ZoneGroupState']
        if zgs == self._zgs_cache:
            return
        self._zgs_cache = zgs
        tree = XML.fromstring(zgs.encode('utf-8'))
        # Empty the set of all zone_groups
        self._groups.clear()
        # and the set of all members
        self._all_zones.clear()
        self._visible_zones.clear()
        # Loop over each ZoneGroup Element
        for group_element in tree.iter('ZoneGroup'):
            coordinator_uid = group_element.attrib['Coordinator']
            group_uid = group_element.attrib['ID']
            members = set()
            for member_element in group_element.iter('ZoneGroupMember'):
                # Create a SoCo instance for each member. Because SoCo
                # instances are singletons, this is cheap if they have already
                # been created, and useful if they haven't. We can then
                # update various properties for that instance.
                member_attribs = member_element.attrib
                ip_addr = member_attribs['Location'].\
                    split('//')[1].split(':')[0]
                zone = SoCo(ip_addr)
                zone._uid = member_attribs['UUID']
                # If this element has the same UUID as the coordinator, it is
                # the coordinator
                if zone._uid == coordinator_uid:
                    group_coordinator = zone
                zone._player_name = member_attribs['ZoneName']
                # uid and is_bridge do not change, but it does no real harm to
                # set/reset them here, just in case the zone has not been seen
                # before
                zone._is_bridge = True if member_attribs.get(
                    'IsZoneBridge') == '1' else False
                is_visible = False if member_attribs.get(
                    'Invisible') == '1' else True
                # add the zone to the members for this group, and to the set of
                # all members, and to the set of visible members if appropriate
                members.add(zone)
                self._all_zones.add(zone)
                if is_visible:
                    self._visible_zones.add(zone)
                # Now create a ZoneGroup with this info and add it to the list
                # of groups
            self._groups.add(ZoneGroup(group_uid, group_coordinator, members))

    @property
    def all_groups(self):
        """  Return a set of all the available groups"""
        self._parse_zone_group_state()
        return self._groups

    @property
    def group(self):
        """The Zone Group of which this device is a member.

        group will be None if this zone is a slave in a stereo pair."""

        for group in self.all_groups:
            if self in group:
                return group
        return None

        # To get the group directly from the network, try the code below
        # though it is probably slower than that above
        # current_group_id = self.zoneGroupTopology.GetZoneGroupAttributes()[
        #     'CurrentZoneGroupID']
        # if current_group_id:
        #     for group in self.all_groups:
        #         if group.uid == current_group_id:
        #             return group
        # else:
        #     return None

    @property
    def all_zones(self):
        """ Return a set of all the available zones"""
        self._parse_zone_group_state()
        return self._all_zones

    @property
    def visible_zones(self):
        """ Return an set of all visible zones"""
        self._parse_zone_group_state()
        return self._visible_zones

    def partymode(self):
        """ Put all the speakers in the network in the same group, a.k.a Party
        Mode.

        This blog shows the initial research responsible for this:
        http://blog.travelmarx.com/2010/06/exploring-sonos-via-upnp.html

        The trick seems to be (only tested on a two-speaker setup) to tell each
        speaker which to join. There's probably a bit more to it if multiple
        groups have been defined.

        """
        # Tell every other visible zone to join this one
        # pylint: disable = expression-not-assigned
        [zone.join(self) for zone in self.visible_zones if zone is not self]

    def join(self, master):
        """ Join this speaker to another "master" speaker.

        ..  note:: The signature of this method has changed in 0.8. It now
            requires a SoCo instance to be passed as `master`, not an IP
            address

        """
        self.avTransport.SetAVTransportURI([
            ('InstanceID', 0),
            ('CurrentURI', 'x-rincon:{}'.format(master.uid)),
            ('CurrentURIMetaData', '')
            ])

    def unjoin(self):
        """ Remove this speaker from a group.

        Seems to work ok even if you remove what was previously the group
        master from it's own group. If the speaker was not in a group also
        returns ok.

        Returns:
        True if this speaker has left the group.

        Raises SoCoException (or a subclass) upon errors.

        """

        self.avTransport.BecomeCoordinatorOfStandaloneGroup([
            ('InstanceID', 0)
            ])

    def switch_to_line_in(self):
        """ Switch the speaker's input to line-in.

        Returns:
        True if the Sonos speaker successfully switched to line-in.

        If an error occurs, we'll attempt to parse the error and return a UPnP
        error code. If that fails, the raw response sent back from the Sonos
        speaker will be returned.

        Raises SoCoException (or a subclass) upon errors.

        """

        self.avTransport.SetAVTransportURI([
            ('InstanceID', 0),
            ('CurrentURI', 'x-rincon-stream:{}'.format(self.uid)),
            ('CurrentURIMetaData', '')
            ])

    def switch_to_tv(self):
        """ Switch the speaker's input to TV.

        Returns:
        True if the Sonos speaker successfully switched to TV.

        If an error occurs, we'll attempt to parse the error and return a UPnP
        error code. If that fails, the raw response sent back from the Sonos
        speaker will be returned.

        Raises SoCoException (or a subclass) upon errors.

        """

        self.avTransport.SetAVTransportURI([
            ('InstanceID', 0),
            ('CurrentURI', 'x-sonos-htastream:{}:spdif'.format(self.uid)),
            ('CurrentURIMetaData', '')
            ])

    @property
    def status_light(self):
        """ The white Sonos status light between the mute button and the volume
        up button on the speaker. True if on, otherwise False.

        """
        result = self.deviceProperties.GetLEDState()
        LEDState = result["CurrentLEDState"]  # pylint: disable=invalid-name
        return True if LEDState == "On" else False

    @status_light.setter
    def status_light(self, led_on):
        """ Switch on/off the speaker's status light """
        led_state = 'On' if led_on else 'Off'
        self.deviceProperties.SetLEDState([
            ('DesiredLEDState', led_state),
            ])

    def get_current_track_info(self):
        """ Get information about the currently playing track.

        Returns:
        A dictionary containing the following information about the currently
        playing track: playlist_position, duration, title, artist, album,
        position and a link to the album art.

        If we're unable to return data for a field, we'll return an empty
        string. This can happen for all kinds of reasons so be sure to check
        values. For example, a track may not have complete metadata and be
        missing an album name. In this case track['album'] will be an empty
        string.

        """
        response = self.avTransport.GetPositionInfo([
            ('InstanceID', 0),
            ('Channel', 'Master')
            ])

        track = {'title': '', 'artist': '', 'album': '', 'album_art': '',
                 'position': ''}
        track['playlist_position'] = response['Track']
        track['duration'] = response['TrackDuration']
        track['uri'] = response['TrackURI']
        track['position'] = response['RelTime']

        metadata = response['TrackMetaData']
        # Duration seems to be '0:00:00' when listening to radio
        if metadata != '' and track['duration'] == '0:00:00':
            metadata = XML.fromstring(really_utf8(metadata))
            # Try parse trackinfo
            trackinfo = metadata.findtext('.//{urn:schemas-rinconnetworks-com:'
                                          'metadata-1-0/}streamContent')
            index = trackinfo.find(' - ')

            if index > -1:
                track['artist'] = trackinfo[:index]
                track['title'] = trackinfo[index + 3:]
            else:
                LOGGER.warning('Could not handle track info: "%s"', trackinfo)
                LOGGER.warning(traceback.format_exc())
                track['title'] = trackinfo

        # If the speaker is playing from the line-in source, querying for track
        # metadata will return "NOT_IMPLEMENTED".
        elif metadata not in ('', 'NOT_IMPLEMENTED', None):
            # Track metadata is returned in DIDL-Lite format
            metadata = XML.fromstring(really_utf8(metadata))
            md_title = metadata.findtext(
                './/{http://purl.org/dc/elements/1.1/}title')
            md_artist = metadata.findtext(
                './/{http://purl.org/dc/elements/1.1/}creator')
            md_album = metadata.findtext(
                './/{urn:schemas-upnp-org:metadata-1-0/upnp/}album')

            track['title'] = ""
            if md_title:
                track['title'] = md_title
            track['artist'] = ""
            if md_artist:
                track['artist'] = md_artist
            track['album'] = ""
            if md_album:
                track['album'] = md_album

            album_art = metadata.findtext(
                './/{urn:schemas-upnp-org:metadata-1-0/upnp/}albumArtURI')
            if album_art is not None:
                url = metadata.findtext(
                    './/{urn:schemas-upnp-org:metadata-1-0/upnp/}albumArtURI')
                if url.startswith(('http:', 'https:')):
                    track['album_art'] = url
                else:
                    track['album_art'] = 'http://' + self.ip_address + ':1400'\
                        + url

        return track

    def get_speaker_info(self, refresh=False):
        """ Get information about the Sonos speaker.

        Arguments:
        refresh -- Refresh the speaker info cache.

        Returns:
        Information about the Sonos speaker, such as the UID, MAC Address, and
        Zone Name.

        """
        if self.speaker_info and refresh is False:
            return self.speaker_info
        else:
            response = requests.get('http://' + self.ip_address +
                                    ':1400/status/zp')
            dom = XML.fromstring(response.content)

        if dom.findtext('.//ZoneName') is not None:
            self.speaker_info['zone_name'] = \
                dom.findtext('.//ZoneName')
            self.speaker_info['zone_icon'] = dom.findtext('.//ZoneIcon')
            self.speaker_info['uid'] = self.uid
            self.speaker_info['serial_number'] = \
                dom.findtext('.//SerialNumber')
            self.speaker_info['software_version'] = \
                dom.findtext('.//SoftwareVersion')
            self.speaker_info['hardware_version'] = \
                dom.findtext('.//HardwareVersion')
            self.speaker_info['mac_address'] = dom.findtext('.//MACAddress')

            return self.speaker_info

    def get_group_coordinator(self, zone_name):
        """     .. deprecated:: 0.8
                   Use :meth:`group` or :meth:`all_groups` instead.

        """
        import warnings
        warnings.warn(
            "get_group_coordinator is deprecated. "
            "Use the group or all_groups methods instead")
        for group in self.all_groups:
            for member in group:
                if member.player_name == zone_name:
                    return group.coordinator.ip_address
        return None

    def get_speakers_ip(self, refresh=False):
        """ Get the IP addresses of all the Sonos speakers in the network.

        Arguments:
        refresh -- Refresh the speakers IP cache. Ignored. For backward
            compatibility only

        Returns:
        a set of IP addresses of the Sonos speakers.

        .. deprecated:: 0.8


        """
        # pylint: disable=star-args, unused-argument
        return {zone.ip_address for zone in itertools.chain(*self.all_groups)}

    def get_current_transport_info(self):
        """ Get the current playback state

        Returns:
        A dictionary containing the following information about the speakers
        playing state
        current_transport_state (PLAYING, PAUSED_PLAYBACK, STOPPED),
        current_trasnport_status (OK, ?), current_speed(1,?)

        This allows us to know if speaker is playing or not. Don't know other
        states of CurrentTransportStatus and CurrentSpeed.

        """
        response = self.avTransport.GetTransportInfo([
            ('InstanceID', 0),
            ])

        playstate = {
            'current_transport_status': '',
            'current_transport_state': '',
            'current_transport_speed': ''
        }

        playstate['current_transport_state'] = \
            response['CurrentTransportState']
        playstate['current_transport_status'] = \
            response['CurrentTransportStatus']
        playstate['current_transport_speed'] = response['CurrentSpeed']

        return playstate

    def get_queue(self, start=0, max_items=100):
        """ Get information about the queue

        :param start: Starting number of returned matches
        :param max_items: Maximum number of returned matches
        :returns: A list of :py:class:`~.soco.data_structures.QueueItem`.

        This method is heavly based on Sam Soffes (aka soffes) ruby
        implementation

        """
        queue = []
        response = self.contentDirectory.Browse([
            ('ObjectID', 'Q:0'),
            ('BrowseFlag', 'BrowseDirectChildren'),
            ('Filter', '*'),
            ('StartingIndex', start),
            ('RequestedCount', max_items),
            ('SortCriteria', '')
            ])
        result = response['Result']
        if not result:
            return queue

        result_dom = XML.fromstring(really_utf8(result))
        for element in result_dom.findall(
                './/{urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/}item'):
            item = QueueItem.from_xml(element)
            queue.append(item)

        return queue

    def get_sonos_playlists(self, start=0, max_items=100):
        """ Convenience method for:
            get_music_library_information('sonos_playlists')
            Refer to the docstring for that method

        """
        out = self.get_music_library_information(
            'sonos_playlists',
            start,
            max_items)
        return out

    def get_artists(self, start=0, max_items=100):
        """ Convinience method for :py:meth:`get_music_library_information`
        with `search_type='artists'`. For details on remaining arguments refer
        to the docstring for that method.

        """
        out = self.get_music_library_information('artists', start, max_items)
        return out

    def get_album_artists(self, start=0, max_items=100):
        """ Convinience method for :py:meth:`get_music_library_information`
        with `search_type='album_artists'`. For details on remaining arguments
        refer to the docstring for that method.

        """
        out = self.get_music_library_information('album_artists',
                                                 start, max_items)
        return out

    def get_albums(self, start=0, max_items=100):
        """ Convinience method for :py:meth:`get_music_library_information`
        with `search_type='albums'`. For details on remaining arguments refer
        to the docstring for that method.

        """
        out = self.get_music_library_information('albums', start, max_items)
        return out

    def get_genres(self, start=0, max_items=100):
        """ Convinience method for :py:meth:`get_music_library_information`
        with `search_type='genres'`. For details on remaining arguments refer
        to the docstring for that method.

        """
        out = self.get_music_library_information('genres', start, max_items)
        return out

    def get_composers(self, start=0, max_items=100):
        """ Convinience method for :py:meth:`get_music_library_information`
        with `search_type='composers'`. For details on remaining arguments
        refer to the docstring for that method.

        """
        out = self.get_music_library_information('composers', start, max_items)
        return out

    def get_tracks(self, start=0, max_items=100):
        """ Convinience method for :py:meth:`get_music_library_information`
        with `search_type='tracks'`. For details on remaining arguments refer
        to the docstring for that method.

        """
        out = self.get_music_library_information('tracks', start, max_items)
        return out

    def get_playlists(self, start=0, max_items=100):
        """ Convinience method for :py:meth:`get_music_library_information`
        with `search_type='playlists'`. For details on remaining arguments
        refer to the docstring for that method.

        NOTE: The playlists that are referred to here are the playlist (files)
        imported from the music library, they are not the Sonos playlists.

        """
        out = self.get_music_library_information('playlists', start, max_items)
        return out

    def get_music_library_information(self, search_type, start=0,
                                      max_items=100):
        """ Retrieve information about the music library

        :param search_type: The kind of information to retrieve. Can be one of:
            'artists', 'album_artists', 'albums', 'genres', 'composers',
            'tracks', 'share', 'sonos_playlists', and 'playlists', where
            playlists are the imported file based playlists from the
            music library
        :param start: Starting number of returned matches
        :param max_items: Maximum number of returned matches. NOTE: The maximum
            may be restricted by the unit, presumably due to transfer
            size consideration, so check the returned number against the
            requested.
        :returns: A dictionary with metadata for the search, with the
            keys 'number_returned', 'update_id', 'total_matches' and an
            'item_list' list with the search results. The search results
            are instances of one of
            :py:class:`~.soco.data_structures.MLArtist`,
            :py:class:`~.soco.data_structures.MLAlbumArtist`,
            :py:class:`~.soco.data_structures.MLAlbum`,
            :py:class:`~.soco.data_structures.MLGenre`,
            :py:class:`~.soco.data_structures.MLComposer`,
            :py:class:`~.soco.data_structures.MLTrack`,
            :py:class:`~.soco.data_structures.MLShare`,
            :py:class:`~.soco.data_structures.MLSonosPlaylist and
            :py:class:`~.soco.data_structures.MLPlaylist` depending on the
            type of the search.
        :raises: :py:class:`SoCoException` upon errors

        NOTE: The playlists that are returned with the 'playlists' search, are
        the playlists imported from (files in) the music library, they are not
        the Sonos playlists.

        The information about the which searches can be performed and the form
        of the query has been gathered from the Janos project:
        http://sourceforge.net/projects/janos/ Props to the authors of that
        project.

        """
        search_translation = {'artists': 'A:ARTIST',
                              'album_artists': 'A:ALBUMARTIST',
                              'albums': 'A:ALBUM', 'genres': 'A:GENRE',
                              'composers': 'A:COMPOSER', 'tracks': 'A:TRACKS',
                              'playlists': 'A:PLAYLISTS', 'share': 'S:',
                              'sonos_playlists': 'SQ:'}
        search = search_translation[search_type]
        response = self.contentDirectory.Browse([
            ('ObjectID', search),
            ('BrowseFlag', 'BrowseDirectChildren'),
            ('Filter', '*'),
            ('StartingIndex', start),
            ('RequestedCount', max_items),
            ('SortCriteria', '')
            ])

        dom = XML.fromstring(really_utf8(response['Result']))

        # Get result information
        out = {'item_list': [], 'search_type': search_type}
        for tag in ['NumberReturned', 'TotalMatches', 'UpdateID']:
            out[camel_to_underscore(tag)] = int(response[tag])

        # Parse the results
        for container in dom:
            item = get_ml_item(container)
            # Append the item to the list
            out['item_list'].append(item)

        return out

    def add_to_queue(self, queueable_item):
        """ Adds a queueable item to the queue """
        # Check if teh required attributes are there
        for attribute in ['didl_metadata', 'uri']:
            if not hasattr(queueable_item, attribute):
                message = 'queueable_item has no attribute {}'.\
                    format(attribute)
                raise AttributeError(message)
        # Get the metadata
        try:
            metadata = XML.tostring(queueable_item.didl_metadata)
        except CannotCreateDIDLMetadata as exception:
            message = ('The queueable item could not be enqueued, because it '
                       'raised a CannotCreateDIDLMetadata exception with the '
                       'following message:\n{0}').format(str(exception))
            raise ValueError(message)
        if isinstance(metadata, str):
            metadata = metadata.encode('utf-8')

        response = self.avTransport.AddURIToQueue([
            ('InstanceID', 0),
            ('EnqueuedURI', queueable_item.uri),
            ('EnqueuedURIMetaData', metadata),
            ('DesiredFirstTrackNumberEnqueued', 0),
            ('EnqueueAsNext', 1)
            ])
        qnumber = response['FirstTrackNumberEnqueued']
        return int(qnumber)

    def remove_from_queue(self, index):
        """ Remove a track from the queue by index. The index number is
        required as an argument, where the first index is 0.

        index: the index of the track to remove; first item in the queue is 0

        Returns:
            True if the Sonos speaker successfully removed the track

        Raises SoCoException (or a subclass) upon errors.

        """
        # TODO: what do these parameters actually do?
        updid = '0'
        objid = 'Q:0/' + str(index + 1)
        self.avTransport.RemoveTrackFromQueue([
            ('InstanceID', 0),
            ('ObjectID', objid),
            ('UpdateID', updid),
            ])

    def clear_queue(self):
        """ Removes all tracks from the queue.

        Returns:
        True if the Sonos speaker cleared the queue.

        Raises SoCoException (or a subclass) upon errors.

        """
        self.avTransport.RemoveAllTracksFromQueue([
            ('InstanceID', 0),
            ])

    def get_favorite_radio_shows(self, start=0, max_items=100):
        """ Get favorite radio shows from Sonos' Radio app.

        Returns:
        A list containing the total number of favorites, the number of
        favorites returned, and the actual list of favorite radio shows,
        represented as a dictionary with `title` and `uri` keys.

        Depending on what you're building, you'll want to check to see if the
        total number of favorites is greater than the amount you
        requested (`max_items`), if it is, use `start` to page through and
        get the entire list of favorites.

        """

        return self.__get_radio_favorites(RADIO_SHOWS, start, max_items)

    def get_favorite_radio_stations(self, start=0, max_items=100):
        """ Get favorite radio stations from Sonos' Radio app.

        Returns:
        A list containing the total number of favorites, the number of
        favorites returned, and the actual list of favorite radio stations,
        represented as a dictionary with `title` and `uri` keys.

        Depending on what you're building, you'll want to check to see if the
        total number of favorites is greater than the amount you
        requested (`max_items`), if it is, use `start` to page through and
        get the entire list of favorites.

        """
        return self.__get_radio_favorites(RADIO_STATIONS, start, max_items)

    def __get_radio_favorites(self, favorite_type, start=0, max_items=100):
        """ Helper method for `get_favorite_radio_*` methods.

        Arguments:
        favorite_type -- Specify either `RADIO_STATIONS` or `RADIO_SHOWS`.
        start -- Which number to start the retrieval from. Used for paging.
        max_items -- The total number of results to return.

        """
        if favorite_type != RADIO_SHOWS or RADIO_STATIONS:
            favorite_type = RADIO_STATIONS

        response = self.contentDirectory.Browse([
            ('ObjectID', 'R:0/{}'.format(favorite_type)),
            ('BrowseFlag', 'BrowseDirectChildren'),
            ('Filter', '*'),
            ('StartingIndex', start),
            ('RequestedCount', max_items),
            ('SortCriteria', '')
            ])
        result = {}
        favorites = []
        results_xml = response['Result']

        if results_xml != '':
            # Favorites are returned in DIDL-Lite format
            metadata = XML.fromstring(really_utf8(results_xml))

            for item in metadata.findall(
                    './/{urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/}item'):
                favorite = {}
                favorite['title'] = item.findtext(
                    './/{http://purl.org/dc/elements/1.1/}title')
                favorite['uri'] = item.findtext(
                    './/{urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/}res')
                favorites.append(favorite)

        result['total'] = response['TotalMatches']
        result['returned'] = len(favorites)
        result['favorites'] = favorites

        return result


# definition section

RADIO_STATIONS = 0
RADIO_SHOWS = 1

NS = {'dc': '{http://purl.org/dc/elements/1.1/}',
      'upnp': '{urn:schemas-upnp-org:metadata-1-0/upnp/}',
      '': '{urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/}'}

########NEW FILE########
__FILENAME__ = data_structures
# pylint: disable=too-many-lines,R0903,W0142,R0913,C0302
# -*- coding: utf-8 -*-


""" This module contains all the data structures for the information objects
such as music tracks or genres

"""

from __future__ import unicode_literals

from .xml import XML
from .exceptions import CannotCreateDIDLMetadata
from .utils import really_unicode, camel_to_underscore


def ns_tag(ns_id, tag):
    """Return a namespace/tag item. The ns_id is translated to a full name
    space via the NS module variable.

    """
    return '{{{0}}}{1}'.format(NS[ns_id], tag)


def get_ml_item(xml):
    """Return the music library item that corresponds to xml. The class is
    identified by getting the parentID and making a lookup in the
    PARENT_ID_TO_CLASS module variable dictionary.

    """
    cls = PARENT_ID_TO_CLASS[xml.get('parentID')]
    return cls.from_xml(xml=xml)


def get_ms_item(xml, service, parent_id):
    """Return the music service item that corresponds to xml. The class is
    identified by getting the type from the 'itemType' tag
    """
    cls = MS_TYPE_TO_CLASS.get(xml.findtext(ns_tag('ms', 'itemType')))
    out = cls.from_xml(xml, service, parent_id)
    return out


def tags_with_text(xml, tags=None):
    """Return a list of tags that contain text retrieved recursively from an
    XML tree
    """
    if tags is None:
        tags = []
    for element in xml:
        if element.text is not None:
            tags.append(element)
        elif len(element) > 0:
            tags_with_text(element, tags)
        else:
            message = 'Unknown XML structure: {}'.format(element)
            raise ValueError(message)
    return tags


class MusicInfoItem(object):
    """Abstract class for all data structure classes"""

    def __init__(self):
        """Initialize the content as an empty dict."""
        self.content = {}

    def __eq__(self, playable_item):
        """Return the equals comparison result to another ``playable_item``."""
        return self.content == playable_item.content

    def __ne__(self, playable_item):
        """Return the not equals comparison result to another ``playable_item``
        """
        return self.content != playable_item.content

    def __repr__(self):
        """Return the repr value for the item.

        The repr is on the form::

          <class_name 'middle_part[0:40]' at id_in_hex>

        where middle_part is either the title item in content, if it is set,
        or ``str(content)``. The output is also cleared of non-ascii
        characters.

        """
        # 40 originates from terminal width (78) - (15) for address part and
        # (19) for the longest class name and a little left for buffer
        if self.content.get('title') is not None:
            middle = self.content['title'].encode('ascii', 'replace')[0:40]
        else:
            middle = str(self.content).encode('ascii', 'replace')[0:40]
        return '<{0} \'{1}\' at {2}>'.format(self.__class__.__name__,
                                             middle,
                                             hex(id(self)))

    def __str__(self):
        """Return the str value for the item::

         <class_name 'middle_part[0:40]' at id_in_hex>

        where middle_part is either the title item in content, if it is set, or
        ``str(content)``. The output is also cleared of non-ascii characters.

        """
        return self.__repr__()


###############################################################################
# MUSIC LIBRARY                                                               #
###############################################################################
class MusicLibraryItem(MusicInfoItem):
    """Abstract class for a queueable item from the music library.

    :ivar parent_id: The parent ID for the music library item is ``None``,
        since it is a abstract class and it should be overwritten in the sub
        classes
    :ivar _translation: The dictionary-key-to-xml-tag-and-namespace-
        translation used when instantiating a MusicLibraryItems from XML. The
        default value is shown below. This default value applies to most sub
        classes and the rest should overwrite it.

        .. code-block:: python

            # key: (ns, tag)
            _translation = {
                'title': ('dc', 'title'),
                'uri': ('', 'res'),
                'item_class': ('upnp', 'class')
            }

    """
    parent_id = None
    # key: (ns, tag)
    _translation = {
        'title': ('dc', 'title'),
        'uri': ('', 'res'),
        'item_class': ('upnp', 'class')
    }

    def __init__(self, uri, title, item_class, **kwargs):
        r"""Initialize the MusicLibraryItem from parameter arguments.

        :param uri: The URI for the item
        :param title: The title for the item
        :param item_class: The UPnP class for the item
        :param \*\*kwargs: Extra information items to form the music library
            item from. Valid keys are ``album``, ``album_art_uri``,
            ``creator`` and ``original_track_number``.
            ``original_track_number`` is an int, all other values are
            unicode objects.

        """
        super(MusicLibraryItem, self).__init__()

        # Parse the input arguments
        arguments = {'uri': uri, 'title': title, 'item_class': item_class}
        arguments.update(kwargs)
        for key, value in arguments.items():
            if key in self._translation:
                self.content[key] = value
            else:
                raise ValueError(
                    'The key \'{0}\' is not allowed as an argument. Only '
                    'these keys are allowed: {1}'.
                    format(key, str(self._translation.keys())))

    @classmethod
    def from_xml(cls, xml):
        """Return an instance of this class, created from xml.

        :param xml: An :py:class:`xml.etree.ElementTree.Element` object. The
            top element usually is a DIDL-LITE item (NS['']) element. Inside
            the item element should be the (namespace, tag_name) elements
            in the dictionary-key-to-xml-tag-and-namespace-translation
            described in the class docstring.

        """
        content = {}
        for key, value in cls._translation.items():
            result = xml.find(ns_tag(*value))
            if result is None:
                content[key] = None
            else:
                # The xml objects should contain utf-8 internally
                content[key] = really_unicode(result.text)
        args = [content.pop(arg) for arg in ['uri', 'title', 'item_class']]
        if content.get('original_track_number') is not None:
            content['original_track_number'] = \
                int(content['original_track_number'])
        return cls(*args, **content)

    @classmethod
    def from_dict(cls, content):
        """Return an instance of this class, created from a dict with
        parameters.

        :param content: Dict with information for the music library item.
            Required and valid arguments are the same as for the
            ``__init__`` method.

        """
        # Make a copy since this method will modify the input dict
        content_in = content.copy()
        args = [content_in.pop(arg) for arg in ['uri', 'title', 'item_class']]
        return cls(*args, **content_in)

    @property
    def to_dict(self):
        """Get the dict representation of the instance."""
        return self.content.copy()

    @property
    def item_id(self):  # pylint: disable=C0103
        """Return the id.

        The id is extracted as the part of the URI after the first # character.
        For the few music library types where that is not correct, this method
        should be overwritten.
        """
        out = self.content['uri']
        try:
            out = out[out.index('#') + 1:]
        except ValueError:
            out = None
        return out

    @property
    def didl_metadata(self):
        """Produce the DIDL metadata XML.

        This method uses the :py:attr:`~.MusicLibraryItem.item_id`
        attribute (and via that the :py:attr:`~.MusicLibraryItem.uri`
        attribute), the :py:attr:`~.MusicLibraryItem.item_class` attribute
        and the :py:attr:`~.MusicLibraryItem.title`  attribute. The
        metadata will be on the form:

        .. code :: xml

         <DIDL-Lite ..NS_INFO..>
           <item id="...self.item_id..."
             parentID="...cls.parent_id..." restricted="true">
             <dc:title>...self.title...</dc:title>
             <upnp:class>...self.item_class...</upnp:class>
             <desc id="cdudn"
               nameSpace="urn:schemas-rinconnetworks-com:metadata-1-0/">
               RINCON_AssociatedZPUDN
             </desc>
           </item>
         </DIDL-Lite>

        """
        # Check the id_info method and via that, the self.to_dict['uri'] value
        if self.item_id is None:
            raise CannotCreateDIDLMetadata(
                'DIDL Metadata cannot be created when item_id returns None '
                '(most likely because uri is not set)')

        # Main element, ugly yes, but I have given up on using namespaces with
        # xml.etree.ElementTree
        item_attrib = {
            'xmlns:dc': 'http://purl.org/dc/elements/1.1/',
            'xmlns:upnp': 'urn:schemas-upnp-org:metadata-1-0/upnp/',
            'xmlns': 'urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/'
        }
        xml = XML.Element('DIDL-Lite', item_attrib)
        # Item sub element
        item_attrib = \
            {'parentID': self.parent_id, 'restricted': 'true',
             'id': self.item_id}
        item = XML.SubElement(xml, 'item', item_attrib)
        # Add content from self.content to item
        XML.SubElement(item, 'dc:title').text = self.title
        XML.SubElement(item, 'upnp:class').text = self.item_class
        # Add the desc element
        desc_attrib = {'id': 'cdudn', 'nameSpace':
                       'urn:schemas-rinconnetworks-com:metadata-1-0/'}
        desc = XML.SubElement(item, 'desc', desc_attrib)
        desc.text = 'RINCON_AssociatedZPUDN'
        return xml

    @property
    def title(self):
        """Get and set the title as an unicode object."""
        return self.content['title']

    @title.setter
    def title(self, title):  # pylint: disable=C0111
        self.content['title'] = title

    @property
    def uri(self):
        """Get and set the URI as an unicode object."""
        return self.content['uri']

    @uri.setter
    def uri(self, uri):  # pylint: disable=C0111
        self.content['uri'] = uri

    @property
    def item_class(self):
        """Get and set the UPnP object class as an unicode object."""
        return self.content['item_class']

    @item_class.setter
    def item_class(self, item_class):  # pylint: disable=C0111
        self.content['item_class'] = item_class


class MLTrack(MusicLibraryItem):
    """Class that represents a music library track.

    :ivar parent_id: The parent ID for the MLTrack is 'A:TRACKS'
    :ivar _translation: The dictionary-key-to-xml-tag-and-namespace-
        translation used when instantiating a MLTrack from XML. The value is
        shown below

        .. code-block:: python

            # key: (ns, tag)
            _translation = {
                'title': ('dc', 'title'),
                'creator': ('dc', 'creator'),
                'album': ('upnp', 'album'),
                'album_art_uri': ('upnp', 'albumArtURI'),
                'uri': ('', 'res'),
                'original_track_number': ('upnp', 'originalTrackNumber'),
                'item_class': ('upnp', 'class')
            }

    """

    parent_id = 'A:TRACKS'
    # name: (ns, tag)
    _translation = {
        'title': ('dc', 'title'),
        'creator': ('dc', 'creator'),
        'album': ('upnp', 'album'),
        'album_art_uri': ('upnp', 'albumArtURI'),
        'uri': ('', 'res'),
        'original_track_number': ('upnp', 'originalTrackNumber'),
        'item_class': ('upnp', 'class')
    }

    def __init__(self, uri, title,
                 item_class='object.item.audioItem.musicTrack', **kwargs):
        r"""Instantiate the MLTrack item by passing the arguments to the
        super class :py:meth:`.MusicLibraryItem.__init__`.

        :param uri: The URI for the track
        :param title: The title of the track
        :param item_class: The UPnP class for the track. The default value is:
            ``object.item.audioItem.musicTrack``
        :param \*\*kwargs: Optional extra information items, valid keys are:
            ``album``, ``album_art_uri``, ``creator``,
            ``original_track_number``. ``original_track_number`` is an ``int``.
            All other values are unicode objects.
        """
        MusicLibraryItem.__init__(self, uri, title, item_class, **kwargs)

    @property
    def item_id(self):  # pylint: disable=C0103
        """Return the id."""
        out = self.content['uri']
        if 'x-file-cifs' in out:
            # URI's for MusicTracks starts with x-file-cifs, where cifs most
            # likely refer to Common Internet File System. For unknown reasons
            # that part must be replaces with an S to form the item_id
            out = out.replace('x-file-cifs', 'S')
        else:
            out = None
        return out

    @property
    def creator(self):
        """Get and set the creator as an unicode object."""
        return self.content.get('creator')

    @creator.setter
    def creator(self, creator):  # pylint: disable=C0111
        self.content['creator'] = creator

    @property
    def album(self):
        """Get and set the album as an unicode object."""
        return self.content.get('album')

    @album.setter
    def album(self, album):  # pylint: disable=C0111
        self.content['album'] = album

    @property
    def album_art_uri(self):
        """Get and set the album art URI as an unicode object."""
        return self.content.get('album_art_uri')

    @album_art_uri.setter
    def album_art_uri(self, album_art_uri):  # pylint: disable=C0111
        self.content['album_art_uri'] = album_art_uri

    @property
    def original_track_number(self):
        """Get and set the original track number as an ``int``."""
        return self.content.get('original_track_number')

    @original_track_number.setter
    # pylint: disable=C0111
    def original_track_number(self, original_track_number):
        self.content['original_track_number'] = original_track_number


class MLAlbum(MusicLibraryItem):
    """Class that represents a music library album.

    :ivar parent_id: The parent ID for the MLTrack is 'A:ALBUM'
    :ivar _translation: The dictionary-key-to-xml-tag-and-namespace-
        translation used when instantiating a MLAlbum from XML. The value is
        shown below

        .. code-block :: python

            # key: (ns, tag)
            _translation = {
                'title': ('dc', 'title'),
                'creator': ('dc', 'creator'),
                'album_art_uri': ('upnp', 'albumArtURI'),
                'uri': ('', 'res'),
                'item_class': ('upnp', 'class')
            }

    """

    parent_id = 'A:ALBUM'
    # name: (ns, tag)
    _translation = {
        'title': ('dc', 'title'),
        'creator': ('dc', 'creator'),
        'album_art_uri': ('upnp', 'albumArtURI'),
        'uri': ('', 'res'),
        'item_class': ('upnp', 'class')
    }

    def __init__(self, uri, title,
                 item_class='object.container.album.musicAlbum', **kwargs):
        r"""Instantiate the MLAlbum item by passing the arguments to the
        super class :py:meth:`.MusicLibraryItem.__init__`.

        :param uri: The URI for the alum
        :param title: The title of the album
        :param item_class: The UPnP class for the album. The default value is:
            ``object.container.album.musicAlbum``
        :param \*\*kwargs: Optional extra information items, valid keys are:
            ``album_art_uri`` and ``creator``. All value should be unicode
            objects.
        """
        MusicLibraryItem.__init__(self, uri, title, item_class, **kwargs)

    @property
    def creator(self):
        """Get and set the creator as an unicode object."""
        return self.content.get('creator')

    @creator.setter
    def creator(self, creator):  # pylint: disable=C0111
        self.content['creator'] = creator

    @property
    def album_art_uri(self):
        """Get and set the album art URI as an unicode object."""
        return self.content.get('album_art_uri')

    @album_art_uri.setter
    def album_art_uri(self, album_art_uri):  # pylint: disable=C0111
        self.content['album_art_uri'] = album_art_uri


class MLArtist(MusicLibraryItem):
    """Class that represents a music library artist.

    :ivar parent_id: The parent ID for the MLArtist is 'A:ARTIST'
    :ivar _translation: The dictionary-key-to-xml-tag-and-namespace-
        translation used when instantiating a MLArtist from XML is inherited
        from :py:class:`.MusicLibraryItem`.
    """

    parent_id = 'A:ARTIST'

    def __init__(self, uri, title,
                 item_class='object.container.person.musicArtist'):
        """Instantiate the MLArtist item by passing the arguments to the
        super class :py:meth:`.MusicLibraryItem.__init__`.

        :param uri: The URI for the artist
        :param title: The title of the artist
        :param item_class: The UPnP class for the artist. The default value is:
            ``object.container.person.musicArtist``
        """
        MusicLibraryItem.__init__(self, uri, title, item_class)


class MLAlbumArtist(MusicLibraryItem):
    """Class that represents a music library album artist.

    :ivar parent_id: The parent ID for the MLAlbumArtist is 'A:ALBUMARTIST'
    :ivar _translation: The dictionary-key-to-xml-tag-and-namespace-
        translation used when instantiating a MLAlbumArtist from XML is
        inherited from :py:class:`.MusicLibraryItem`.

    """

    parent_id = 'A:ALBUMARTIST'

    def __init__(self, uri, title,
                 item_class='object.container.person.musicArtist'):
        """Instantiate the MLAlbumArtist item by passing the arguments to the
        super class :py:meth:`.MusicLibraryItem.__init__`.

        :param uri: The URI for the alum artist
        :param title: The title of the album artist
        :param item_class: The UPnP class for the album artist. The default
            value is: ``object.container.person.musicArtist``

        """
        MusicLibraryItem.__init__(self, uri, title, item_class)


class MLGenre(MusicLibraryItem):
    """Class that represents a music library genre.

    :ivar parent_id: The parent ID for the MLGenre is 'A:GENRE'
    :ivar _translation: The dictionary-key-to-xml-tag-and-namespace-
        translation used when instantiating a MLGenre from XML is inherited
        from :py:class:`.MusicLibraryItem`.

    """

    parent_id = 'A:GENRE'

    def __init__(self, uri, title,
                 item_class='object.container.genre.musicGenre'):
        """Instantiate the MLGenre item by passing the arguments to the
        super class :py:meth:`.MusicLibraryItem.__init__`.

        :param uri: The URI for the genre
        :param title: The title of the genre
        :param item_class: The UPnP class for the genre. The default value is:
            ``object.container.genre.musicGenre``

        """
        MusicLibraryItem.__init__(self, uri, title, item_class)


class MLComposer(MusicLibraryItem):
    """Class that represents a music library composer.

    :ivar parent_id: The parent ID for the MLComposer is 'A:COMPOSER'
    :ivar _translation: The dictionary-key-to-xml-tag-and-namespace-
        translation used when instantiating a MLComposer from XML is inherited
        from :py:class:`.MusicLibraryItem`.

    """

    parent_id = 'A:COMPOSER'

    def __init__(self, uri, title,
                 item_class='object.container.person.composer'):
        """Instantiate the MLComposer item by passing the arguments to the
        super class :py:meth:`.MusicLibraryItem.__init__`.

        :param uri: The URI for the composer
        :param title: The title of the composer
        :param item_class: The UPnP class for the composer. The default value
            is: ``object.container.person.composer``

        """
        MusicLibraryItem.__init__(self, uri, title, item_class)


class MLPlaylist(MusicLibraryItem):
    """Class that represents a music library play list.

    :ivar parent_id: The parent ID for the MLPlaylist is 'A:PLAYLIST'
    :ivar _translation: The dictionary-key-to-xml-tag-and-namespace-
        translation used when instantiating a MLPlaylist from XML is inherited
        from :py:class:`.MusicLibraryItem`.

    """

    parent_id = 'A:PLAYLISTS'

    def __init__(self, uri, title,
                 item_class='object.container.playlistContainer'):
        """Instantiate the MLPlaylist item by passing the arguments to the
        super class :py:meth:`.MusicLibraryItem.__init__`.

        :param uri: The URI for the playlist
        :param title: The title of the playlist
        :param item_class: The UPnP class for the playlist. The default value
            is: ``object.container.playlistContainer``

        """
        MusicLibraryItem.__init__(self, uri, title, item_class)

    @property
    def item_id(self):  # pylint: disable=C0103
        """Returns the id."""
        out = self.content['uri']
        if 'x-file-cifs' in out:
            out = out.replace('x-file-cifs', 'S')
        else:
            out = None
        return out


class MLSonosPlaylist(MusicLibraryItem):
    """ Class that represents a sonos playlist.

    :ivar parent_id: The parent ID for the MLSonosPlaylist is 'SQ:'
    :ivar _translation: The dictionary-key-to-xml-tag-and-namespace-
        translation used when instantiating MLSonosPlaylist from
        XML is inherited from :py:class:`.MusicLibraryItem`.

    """

    parent_id = 'SQ:'

    def __init__(self, uri, title,
                 item_class='object.container.playlistContainer'):
        """ Instantiate the MLSonosPlaylist item by passing the arguments to
        the super class :py:meth:`.MusicLibraryItem.__init__`.

        :param uri: The URI for the playlist
        :param title: The title of the playlist
        :param item_class: The UPnP class for the playlist. The default value
            is: ``object.container.playlistContainer``

        """
        MusicLibraryItem.__init__(self, uri, title, item_class)


class MLShare(MusicLibraryItem):
    """Class that represents a music library share.

    :ivar parent_id: The parent ID for the MLShare is 'S:'
    :ivar _translation: The dictionary-key-to-xml-tag-and-namespace-
        translation used when instantiating a MLShare from XML is inherited
        from :py:class:`.MusicLibraryItem`.

    """

    parent_id = 'S:'

    def __init__(self, uri, title, item_class='object.container'):
        """Instantiate the MLShare item by passing the arguments to the
        super class :py:meth:`.MusicLibraryItem.__init__`.

        :param uri: The URI for the share
        :param title: The title of the share
        :param item_class: The UPnP class for the share. The default value is:
            ``object.container``

        """
        MusicLibraryItem.__init__(self, uri, title, item_class)


###############################################################################
# QUEUE                                                                       #
###############################################################################
class QueueItem(MusicInfoItem):
    """Class that represents a queue item.

    :ivar parent_id: The parent ID for the QueueItem is 'Q:0'
    :ivar _translation: The dictionary-key-to-xml-tag-and-namespace-
        translation used when instantiating a QueueItem from XML. The value is
        shown below

        .. code-block:: python

            # key: (ns, tag)
            _translation = {
                'title': ('dc', 'title'),
                'creator': ('dc', 'creator'),
                'album': ('upnp', 'album'),
                'album_art_uri': ('upnp', 'albumArtURI'),
                'uri': ('', 'res'),
                'original_track_number': ('upnp', 'originalTrackNumber'),
                'item_class': ('upnp', 'class')
            }

    """

    parent_id = 'Q:0'
    _translation = {
        'title': ('dc', 'title'),
        'creator': ('dc', 'creator'),
        'album': ('upnp', 'album'),
        'album_art_uri': ('upnp', 'albumArtURI'),
        'uri': ('', 'res'),
        'original_track_number': ('upnp', 'originalTrackNumber'),
        'item_class': ('upnp', 'class')
    }

    def __init__(self, uri, title,
                 item_class="object.item.audioItem.musicTrack", **kwargs):
        r"""Instantiate the QueueItem by passing the arguments to the super
        class :py:meth:`.MusicInfoItem.__init__`.

        :param uri: The URI for the queue item
        :param title: The title of the queue item
        :param item_class: The UPnP class for the queue item. The default value
            is: ``object.item.audioItem.musicTrack``
        :param \*\*kwargs: Optional extra information items, valid keys are:
            ``album``, ``album_art_uri``, ``creator``,
            ``original_track_number``. ``original_track_number`` is an ``int``.
            All other values are unicode objects.
        """
        super(QueueItem, self).__init__()

        # Parse the input arguments
        arguments = {'uri': uri, 'title': title, 'item_class': item_class}
        arguments.update(kwargs)
        for key, value in arguments.items():
            if key in self._translation:
                self.content[key] = value
            else:
                raise ValueError(
                    'The key \'{0}\' is not allowed as an argument. Only '
                    'these keys are allowed: {1}'.
                    format(key, str(self._translation.keys())))

    @classmethod
    def from_xml(cls, xml):
        """Return an instance of this class, created from xml.

        :param xml: An :py:class:`xml.etree.ElementTree.Element` object. The
            top element usually is a DIDL-LITE item (NS['']) element. Inside
            the item element should be the (namespace, tag_name) elements
            in the dictionary-key-to-xml-tag-and-namespace-translation
            described in the class docstring.

        """
        content = {}
        for key, value in cls._translation.items():
            result = xml.find(ns_tag(*value))
            if result is None:
                content[key] = None
            else:
                # The xml objects should contain utf-8 internally
                content[key] = really_unicode(result.text)

        args = [content.pop(arg) for arg in ['uri', 'title', 'item_class']]

        if content.get('original_track_number') is not None:
            content['original_track_number'] = \
                int(content['original_track_number'])
        return cls(*args, **content)

    @classmethod
    def from_dict(cls, content):
        """Return an instance of this class, created from a dict with
        parameters.

        :param content: Dict with information for the music library item.
            Required and valid arguments are the same as for the
            ``__init__`` method.

        """
        # Make a copy since this method will modify the input dict
        content_in = content.copy()
        args = [content_in.pop(arg) for arg in ['uri', 'title', 'item_class']]
        return cls(*args, **content_in)

    @property
    def to_dict(self):
        """Get the dict representation of the instance."""
        return self.content.copy()

    @property
    # pylint: disable=no-self-use
    def didl_metadata(self):
        """Produce the DIDL metadata XML."""
        message = 'Queueitems are not meant to be re-added to the queue and '\
            'therefore cannot create their own didl_metadata'
        raise CannotCreateDIDLMetadata(message)

    @property
    def title(self):
        """Get and set the title as an unicode object."""
        return self.content['title']

    @title.setter
    def title(self, title):  # pylint: disable=C0111
        self.content['title'] = title

    @property
    def uri(self):
        """Get and set the URI as an unicode object."""
        return self.content['uri']

    @uri.setter
    def uri(self, uri):  # pylint: disable=C0111
        self.content['uri'] = uri

    @property
    def item_class(self):
        """Get and set the UPnP object class as an unicode object."""
        return self.content['item_class']

    @item_class.setter
    def item_class(self, item_class):  # pylint: disable=C0111
        self.content['item_class'] = item_class

    @property
    def creator(self):
        """Get and set the creator as an unicode object."""
        return self.content.get('creator')

    @creator.setter
    def creator(self, creator):  # pylint: disable=C0111
        self.content['creator'] = creator

    @property
    def album(self):
        """Get and set the album as an unicode object."""
        return self.content.get('album')

    @album.setter
    def album(self, album):  # pylint: disable=C0111
        self.content['album'] = album

    @property
    def album_art_uri(self):
        """Get and set the album art URI as an unicode object."""
        return self.content.get('album_art_uri')

    @album_art_uri.setter
    def album_art_uri(self, album_art_uri):  # pylint: disable=C0111
        self.content['album_art_uri'] = album_art_uri

    @property
    def original_track_number(self):
        """Get and set the original track number as an ``int``."""
        return self.content.get('original_track_number')

    @original_track_number.setter
    # pylint: disable=C0111
    def original_track_number(self, original_track_number):
        self.content['original_track_number'] = original_track_number


###############################################################################
# MUSIC LIBRARY                                                               #
###############################################################################
class MusicServiceItem(MusicInfoItem):
    """Class that represents a music service item"""

    # These fields must be overwritten in the sub classes
    item_class = None
    valid_fields = None
    required_fields = None

    def __init__(self, **kwargs):
        super(MusicServiceItem, self).__init__()
        self.content = kwargs

    @classmethod
    def from_xml(cls, xml, service, parent_id):
        """Return a Music Service item generated from xml

        :param xml: Object XML. All items containing text are added to the
            content of the item. The class variable ``valid_fields`` of each of
            the classes list the valid fields (after translating the camel
            case to underscore notation). Required fields are listed in the
            class variable by that name (where 'id' has been renamed to
            'item_id').
        :type xml: :py:class:`xml.etree.ElementTree.Element`
        :param service: The music service (plugin) instance that retrieved the
            element. This service must contain ``id_to_extended_id`` and
            ``form_uri`` methods and ``description`` and ``service_id``
            attributes.
        :type service: Instance of sub-class of
            :class:`soco.plugins.SoCoPlugin`
        :param parent_id: The parent ID of the item, will either be the
            extended ID of another MusicServiceItem or of a search
        :type parent_id: str

        For a track the XML can e.g. be on the following form:

        .. code :: xml

         <mediaMetadata xmlns="http://www.sonos.com/Services/1.1">
           <id>trackid_141359</id>
           <itemType>track</itemType>
           <mimeType>audio/aac</mimeType>
           <title>Teacher</title>
           <trackMetadata>
             <artistId>artistid_10597</artistId>
             <artist>Jethro Tull</artist>
             <composerId>artistid_10597</composerId>
             <composer>Jethro Tull</composer>
             <albumId>albumid_141358</albumId>
             <album>MU - The Best Of Jethro Tull</album>
             <albumArtistId>artistid_10597</albumArtistId>
             <albumArtist>Jethro Tull</albumArtist>
             <duration>229</duration>
             <albumArtURI>http://varnish01.music.aspiro.com/sca/
              imscale?h=90&amp;w=90&amp;img=/content/music10/prod/wmg/
              1383757201/094639008452_20131105025504431/resources/094639008452.
              jpg</albumArtURI>
             <canPlay>true</canPlay>
             <canSkip>true</canSkip>
             <canAddToFavorites>true</canAddToFavorites>
           </trackMetadata>
         </mediaMetadata>
        """
        # Add a few extra pieces of information
        content = {'description': service.description,
                   'service_id': service.service_id,
                   'parent_id': parent_id}
        # Extract values from the XML
        all_text_elements = tags_with_text(xml)
        for item in all_text_elements:
            tag = item.tag[len(NS['ms']) + 2:]  # Strip namespace
            tag = camel_to_underscore(tag)  # Convert to nice names
            if tag not in cls.valid_fields:
                message = 'The info tag \'{}\' is not allowed for this item'.\
                    format(tag)
                raise ValueError(message)
            content[tag] = item.text

        # Convert values for known types
        for key, value in content.items():
            if key == 'duration':
                content[key] = int(value)
            if key in ['can_play', 'can_skip', 'can_add_to_favorites',
                       'can_enumerate']:
                content[key] = True if value == 'true' else False
        # Rename a single item
        content['item_id'] = content.pop('id')
        # And get the extended id
        content['extended_id'] = service.id_to_extended_id(content['item_id'],
                                                           cls)
        # Add URI if there is one for the relevant class
        uri = service.form_uri(content, cls)
        if uri:
            content['uri'] = uri

        # Check for all required values
        for key in cls.required_fields:
            if key not in content:
                message = 'An XML field that correspond to the key \'{}\' is '\
                    'required. See the docstring for help.'.format(key)

        return cls.from_dict(content)

    @classmethod
    def from_dict(cls, dict_in):
        """Initialize the class from a dict

        :param dict_in: The dictionary that contains the item content. Required
            fields are listed class variable by that name
        :type dict_in: dict
        """
        kwargs = dict_in.copy()
        args = [kwargs.pop(key) for key in cls.required_fields]
        return cls(*args, **kwargs)

    @property
    def to_dict(self):
        """Return a copy of the content dict"""
        return self.content.copy()

    @property
    def didl_metadata(self):
        """Return the DIDL metadata for a Music Service Track

        The metadata is on the form:

        .. code :: xml

         <DIDL-Lite xmlns:dc="http://purl.org/dc/elements/1.1/"
              xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"
              xmlns:r="urn:schemas-rinconnetworks-com:metadata-1-0/"
              xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/">
           <item id="...self.extended_id..."
              parentID="...self.parent_id..."
              restricted="true">
             <dc:title>...self.title...</dc:title>
             <upnp:class>...self.item_class...</upnp:class>
             <desc id="cdudn"
                nameSpace="urn:schemas-rinconnetworks-com:metadata-1-0/">
               self.content['description']
             </desc>
           </item>
         </DIDL-Lite>
        """
        # Check if this item is meant to be played
        if not self.can_play:
            message = 'This item is not meant to be played and therefore '\
                'also not to create its own didl_metadata'
            raise CannotCreateDIDLMetadata(message)
        # Check if we have the attributes to create the didl metadata:
        for key in ['extended_id', 'title', 'item_class']:
            if not hasattr(self, key):
                message = 'The property \'{}\' is not present on this item. '\
                    'This indicates that this item was not meant to create '\
                    'didl_metadata'.format(key)
                raise CannotCreateDIDLMetadata(message)
        if 'description' not in self.content:
            message = 'The item for \'description\' is not present in '\
                'self.content. This indicates that this item was not meant '\
                'to create didl_metadata'
            raise CannotCreateDIDLMetadata(message)

        # Main element, ugly? yes! but I have given up on using namespaces
        # with xml.etree.ElementTree
        item_attrib = {
            'xmlns:dc': 'http://purl.org/dc/elements/1.1/',
            'xmlns:upnp': 'urn:schemas-upnp-org:metadata-1-0/upnp/',
            'xmlns:r': 'urn:schemas-rinconnetworks-com:metadata-1-0/',
            'xmlns': 'urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/'
        }
        xml = XML.Element('DIDL-Lite', item_attrib)
        # Item sub element
        item_attrib = {
            'parentID': '',
            'restricted': 'true',
            'id': self.extended_id
        }
        # Only add the parent_id if we have it
        if self.parent_id:
            item_attrib['parentID'] = self.parent_id
        item = XML.SubElement(xml, 'item', item_attrib)

        # Add title and class
        XML.SubElement(item, 'dc:title').text = self.title
        XML.SubElement(item, 'upnp:class').text = self.item_class
        # Add the desc element
        desc_attrib = {
            'id': 'cdudn',
            'nameSpace': 'urn:schemas-rinconnetworks-com:metadata-1-0/'
        }
        desc = XML.SubElement(item, 'desc', desc_attrib)
        desc.text = self.content['description']

        return xml

    @property
    def item_id(self):
        """Return the item id"""
        return self.content['item_id']

    @property
    def extended_id(self):
        """Return the extended id"""
        return self.content['extended_id']

    @property
    def title(self):
        """Return the title"""
        return self.content['title']

    @property
    def service_id(self):
        """Return the service ID"""
        return self.content['service_id']

    @property
    def can_play(self):
        """Return a boolean for whether the item can be played"""
        return bool(self.content.get('can_play'))

    @property
    def parent_id(self):
        """Return the extended parent_id, if set, otherwise return None"""
        return self.content.get('parent_id')

    @property
    def album_art_uri(self):
        """Return the album art URI if set, otherwise return None"""
        return self.content.get('album_art_uri')


class MSTrack(MusicServiceItem):
    """Class that represents a music service track"""

    item_class = 'object.item.audioItem.musicTrack'
    valid_fields = [
        'album', 'can_add_to_favorites', 'artist', 'album_artist_id', 'title',
        'album_id', 'album_art_uri', 'album_artist', 'composer_id',
        'item_type', 'composer', 'duration', 'can_skip', 'artist_id',
        'can_play', 'id', 'mime_type', 'description'
    ]
    # IMPORTANT. Keep this list, __init__ args and content in __init__ in sync
    required_fields = ['title', 'item_id', 'extended_id', 'uri', 'description',
                       'service_id']

    def __init__(self, title, item_id, extended_id, uri, description,
                 service_id, **kwargs):
        """Initialize MSTrack item"""
        content = {
            'title': title, 'item_id': item_id, 'extended_id': extended_id,
            'uri': uri, 'description': description, 'service_id': service_id,
        }
        content.update(kwargs)
        super(MSTrack, self).__init__(**content)

    @property
    def album(self):
        """Return the album title if set, otherwise return None"""
        return self.content.get('album')

    @property
    def artist(self):
        """Return the artist if set, otherwise return None"""
        return self.content.get('artist')

    @property
    def duration(self):
        """Return the duration if set, otherwise return None"""
        return self.content.get('duration')

    @property
    def uri(self):
        """Return the URI"""
        # x-sonos-http:trackid_19356232.mp4?sid=20&amp;flags=32
        return self.content['uri']


class MSAlbum(MusicServiceItem):
    """Class that represents a Music Service Album"""

    item_class = 'object.container.album.musicAlbum'
    valid_fields = [
        'username', 'can_add_to_favorites', 'artist', 'title', 'album_art_uri',
        'can_play', 'item_type', 'service_id', 'id', 'description',
        'can_cache', 'artist_id', 'can_skip'
    ]
    # IMPORTANT. Keep this list, __init__ args and content in __init__ in sync
    required_fields = ['title', 'item_id', 'extended_id', 'uri', 'description',
                       'service_id']

    def __init__(self, title, item_id, extended_id, uri, description,
                 service_id, **kwargs):
        content = {
            'title': title, 'item_id': item_id, 'extended_id': extended_id,
            'uri': uri, 'description': description, 'service_id': service_id,
        }
        content.update(kwargs)
        super(MSAlbum, self).__init__(**content)

    @property
    def artist(self):
        """Return the artist if set, otherwise return None"""
        return self.content.get('artist')

    @property
    def uri(self):
        """Return the URI"""
        # x-rincon-cpcontainer:0004002calbumid_22757081
        return self.content['uri']


class MSAlbumList(MusicServiceItem):
    """Class that represents a Music Service Album List"""

    item_class = 'object.container.albumlist'
    valid_fields = [
        'id', 'title', 'item_type', 'artist', 'artist_id', 'can_play',
        'can_enumerate', 'can_add_to_favorites', 'album_art_uri', 'can_cache'
    ]
    # IMPORTANT. Keep this list, __init__ args and content in __init__ in sync
    required_fields = ['title', 'item_id', 'extended_id', 'uri', 'description',
                       'service_id']

    def __init__(self, title, item_id, extended_id, uri, description,
                 service_id, **kwargs):
        content = {
            'title': title, 'item_id': item_id, 'extended_id': extended_id,
            'uri': uri, 'description': description, 'service_id': service_id,
        }
        content.update(kwargs)
        super(MSAlbumList, self).__init__(**content)

    @property
    def uri(self):
        """Return the URI"""
        # x-rincon-cpcontainer:000d006cplaylistid_26b18dbb-fd35-40bd-8d4f-
        # 8669bfc9f712
        return self.content['uri']


class MSPlaylist(MusicServiceItem):
    """Class that represents a Music Service Play List"""

    item_class = 'object.container.albumlist'
    valid_fields = ['id', 'item_type', 'title', 'can_play', 'can_cache',
                    'album_art_uri', 'artist', 'can_enumerate',
                    'can_add_to_favorites', 'artist_id']
    # IMPORTANT. Keep this list, __init__ args and content in __init__ in sync
    required_fields = ['title', 'item_id', 'extended_id', 'uri', 'description',
                       'service_id']

    def __init__(self, title, item_id, extended_id, uri, description,
                 service_id, **kwargs):
        content = {
            'title': title, 'item_id': item_id, 'extended_id': extended_id,
            'uri': uri, 'description': description, 'service_id': service_id,
        }
        content.update(kwargs)
        super(MSPlaylist, self).__init__(**content)

    @property
    def uri(self):
        """Return the URI"""
        # x-rincon-cpcontainer:000d006cplaylistid_c86ddf26-8ec5-483e-b292-
        # abe18848e89e
        return self.content['uri']


class MSArtistTracklist(MusicServiceItem):
    """Class that represents a Music Service Artist Track List"""

    item_class = 'object.container.playlistContainer.sameArtist'
    valid_fields = ['id', 'title', 'item_type', 'can_play', 'album_art_uri']
    # IMPORTANT. Keep this list, __init__ args and content in __init__ in sync
    required_fields = ['title', 'item_id', 'extended_id', 'uri', 'description',
                       'service_id']

    def __init__(self, title, item_id, extended_id, uri, description,
                 service_id, **kwargs):
        content = {
            'title': title, 'item_id': item_id, 'extended_id': extended_id,
            'uri': uri, 'description': description, 'service_id': service_id,
        }
        content.update(kwargs)
        super(MSArtistTracklist, self).__init__(**content)

    @property
    def uri(self):
        """Return the URI"""
        # x-rincon-cpcontainer:100f006cartistpopsongsid_1566
        return 'x-rincon-cpcontainer:100f006c{}'.format(self.item_id)


class MSArtist(MusicServiceItem):
    """Class that represents a Music Service Artist"""

    valid_fields = [
        'username', 'can_add_to_favorites', 'artist', 'title', 'album_art_uri',
        'item_type', 'id', 'service_id', 'description', 'can_cache'
    ]
    # Since MSArtist cannot produce didl_metadata, they are not strictly
    # required, but it makes sense to require them anyway, since they are the
    # fields that that describe the item
    # IMPORTANT. Keep this list, __init__ args and content in __init__ in sync
    required_fields = ['title', 'item_id', 'extended_id', 'service_id']

    def __init__(self, title, item_id, extended_id, service_id, **kwargs):
        content = {'title': title, 'item_id': item_id,
                   'extended_id': extended_id, 'service_id': service_id}
        content.update(kwargs)
        super(MSArtist, self).__init__(**content)


class MSFavorites(MusicServiceItem):
    """Class that represents a Music Service Favorite"""

    valid_fields = ['id', 'item_type', 'title', 'can_play', 'can_cache',
                    'album_art_uri']
    # Since MSFavorites cannot produce didl_metadata, they are not strictly
    # required, but it makes sense to require them anyway, since they are the
    # fields that that describe the item
    # IMPORTANT. Keep this list, __init__ args and content in __init__ in sync
    required_fields = ['title', 'item_id', 'extended_id', 'service_id']

    def __init__(self, title, item_id, extended_id, service_id, **kwargs):
        content = {'title': title, 'item_id': item_id,
                   'extended_id': extended_id, 'service_id': service_id}
        content.update(kwargs)
        super(MSFavorites, self).__init__(**content)


class MSCollection(MusicServiceItem):
    """Class that represents a Music Service Collection"""

    valid_fields = ['id', 'item_type', 'title', 'can_play', 'can_cache',
                    'album_art_uri']
    # Since MSCollection cannot produce didl_metadata, they are not strictly
    # required, but it makes sense to require them anyway, since they are the
    # fields that that describe the item
    # IMPORTANT. Keep this list, __init__ args and content in __init__ in sync
    required_fields = ['title', 'item_id', 'extended_id', 'service_id']

    def __init__(self, title, item_id, extended_id, service_id, **kwargs):
        content = {'title': title, 'item_id': item_id,
                   'extended_id': extended_id, 'service_id': service_id}
        content.update(kwargs)
        super(MSCollection, self).__init__(**content)


PARENT_ID_TO_CLASS = {'A:TRACKS': MLTrack, 'A:ALBUM': MLAlbum,
                      'A:ARTIST': MLArtist, 'A:ALBUMARTIST': MLAlbumArtist,
                      'A:GENRE': MLGenre, 'A:COMPOSER': MLComposer,
                      'A:PLAYLISTS': MLPlaylist, 'S:': MLShare,
                      'SQ:': MLSonosPlaylist}

MS_TYPE_TO_CLASS = {'artist': MSArtist, 'album': MSAlbum, 'track': MSTrack,
                    'albumList': MSAlbumList, 'favorites': MSFavorites,
                    'collection': MSCollection, 'playlist': MSPlaylist,
                    'artistTrackList': MSArtistTracklist}

NS = {
    'dc': 'http://purl.org/dc/elements/1.1/',
    'upnp': 'urn:schemas-upnp-org:metadata-1-0/upnp/',
    '': 'urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/',
    'ms': 'http://www.sonos.com/Services/1.1'
}

########NEW FILE########
__FILENAME__ = events
# -*- coding: utf-8 -*-
# pylint: disable=too-many-public-methods

"""

Classes to handle Sonos UPnP Events and Subscriptions

"""

from __future__ import unicode_literals


import threading
import socket
import logging
import weakref
from collections import namedtuple
import time

import requests

from .compat import (SimpleHTTPRequestHandler, urlopen, URLError, socketserver,
                     Queue,)
from .xml import XML
from .exceptions import SoCoException


log = logging.getLogger(__name__)  # pylint: disable=C0103


def parse_event_xml(xml_event):
    """ Parse a unicode xml_event and return a dict with keys representing the
    event properties"""

    result = {}
    tree = XML.fromstring(xml_event.encode('utf-8'))
    properties = tree.iterfind(
        './/{urn:schemas-upnp-org:event-1-0}property')
    for prop in properties:
        for variable in prop:
            result[variable.tag] = variable.text
    return result


Event = namedtuple('Event', ['sid', 'seq', 'service', 'variables'])
# pylint: disable=pointless-string-statement
""" A namedtuple representing a received event.

sid is the subscription id
seq is the event sequence number for that subscription
service is the service which is subscribed to the event
variables is a dict containing the {names: values} of the evented variables
"""


class EventServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """ A TCP server which handles each new request in a new thread """
    allow_reuse_address = True


class EventNotifyHandler(SimpleHTTPRequestHandler):
    """ Handles HTTP NOTIFY Verbs sent to the listener server """

    def do_NOTIFY(self):  # pylint: disable=invalid-name
        """ Handle a NOTIFY request.  See the UPnP Spec for details."""
        headers = requests.structures.CaseInsensitiveDict(self.headers)
        seq = headers['seq']  # Event sequence number
        sid = headers['sid']  # Event Subscription Identifier
        content_length = int(headers['content-length'])
        content = self.rfile.read(content_length)
        log.debug("Event %s received for sid: %s", seq, sid)
        log.debug("Current thread is %s", threading.current_thread())
        # find the relevant service from the sid
        with _sid_to_service_lock:
            service = _sid_to_service.get(sid)
        variables = parse_event_xml(content)
        # Build the Event tuple
        event = Event(sid, seq, service, variables)
        # pass the event details on to the service so it can update its cache.
        if service is not None:  # It might have been removed by another thread
            # pylint: disable=protected-access
            service._update_cache_on_event(event)
        # Find the right queue, and put the event on it
        with _sid_to_event_queue_lock:
            try:
                _sid_to_event_queue[sid].put(event)
            except KeyError:  # The key have been deleted in another thread
                pass
        self.send_response(200)
        self.end_headers()

    def log_message(self, fmt, *args):
        # Divert standard webserver logging to the debug log
        log.debug(fmt, *args)


class EventServerThread(threading.Thread):
    """The thread in which the event listener server will run"""

    def __init__(self, address):
        super(EventServerThread, self).__init__()
        #: used to signal that the server should stop
        self.stop_flag = threading.Event()
        #: The (ip, port) address on which the server should listen
        self.address = address

    def run(self):
        # Start the server on the local IP at port 1400.  Handling of requests
        # is delegated to instances of the EventNotifyHandler class
        listener = EventServer(self.address, EventNotifyHandler)
        log.debug("Event listener running on %s", listener.server_address)
        # Listen for events untill told to stop
        while not self.stop_flag.is_set():
            listener.handle_request()


class EventListener(object):
    """The Event Listener.

    Runs an http server in a thread which is an endpoint for NOTIFY messages
    from sonos devices"""

    def __init__(self):
        super(EventListener, self).__init__()
        #: Indicates whether the server is currently running
        self.is_running = False
        self._listener_thread = None
        #: The address (ip, port) on which the server will listen. Empty for
        #  the moment. (It is set in `meth`:start)
        self.address = ()

    def start(self, any_zone):
        """Start the event listener listening on the local machine at port 1400

        Make sure that your firewall allows connections to this port

        any_zone is any Sonos device on the network. It does not matter which
        device. It is used only to find a local IP address reachable by the
        Sonos net.

        """

        # Find our local network IP address which is accessible to the
        # Sonos net, see http://stackoverflow.com/q/166506

        temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        temp_sock.connect((any_zone.ip_address, 1400))
        ip_address = temp_sock.getsockname()[0]
        temp_sock.close()
        # Start the event listener server in a separate thread.
        # Hardcoded to listen on port 1400. Any free port could
        # be used but this seems appropriate for Sonos, and avoids the need
        # to find a free port.
        self.address = (ip_address, 1400)
        self._listener_thread = EventServerThread(self.address)
        self._listener_thread.daemon = True
        self._listener_thread.start()
        self.is_running = True
        log.info("Event listener started")

    def stop(self):
        """Stop the event listener"""
        # Signal the thread to stop before handling the next request
        self._listener_thread.stop_flag.set()
        # Send a dummy request in case the http server is currently listening
        try:
            urlopen(
                'http://%s:%s/' % (self.address[0], self.address[1]))
        except URLError:
            # If the server is already shut down, we receive a socket error,
            # which we ignore.
            pass
        # wait for the thread to finish
        self._listener_thread.join()
        self.is_running = False
        log.info("Event listener stopped")


class Subscription(object):
    """ A class representing the subscription to a UPnP event

    """

    def __init__(self, service, event_queue=None):
        """ Pass a SoCo Service instance as a parameter. If event_queue is
        specified, use it for the queue """
        super(Subscription, self).__init__()
        self.service = service
        #: A unique ID for this subscription
        self.sid = None
        #: The amount of time until the subscription expires
        self.timeout = None
        #: An indication of whether the subscription is subscribed
        self.is_subscribed = False
        #: A queue of events received
        self.events = Queue() if event_queue is None else event_queue
        # A flag to make sure that an unsubscribed instance is not
        # resubscribed
        self._has_been_unsubscribed = False
        # The time when the subscription was made
        self._timestamp = None

    def subscribe(self, requested_timeout=None):
        """ Subscribe to the service.

        If requested_timeout is provided, a subscription valid for that number
        of seconds will be requested, but not guaranteed. Check
        :attrib:`timeout` on return to find out what period of validity is
        actually allocated. """

        # TIMEOUT is provided for in the UPnP spec, but it is not clear if
        # Sonos pays any attention to it. A timeout of 86400 secs always seems
        # to be allocated

        if self._has_been_unsubscribed:
            raise SoCoException(
                'Cannot resubscribe instance once unsubscribed')
        service = self.service
        # The event listener must be running, so start it if not
        if not event_listener.is_running:
            event_listener.start(service.soco)
        # an event subscription looks like this:
        # SUBSCRIBE publisher path HTTP/1.1
        # HOST: publisher host:publisher port
        # CALLBACK: <delivery URL>
        # NT: upnp:event
        # TIMEOUT: Second-requested subscription duration (optional)

        # pylint: disable=unbalanced-tuple-unpacking
        ip_address, port = event_listener.address
        headers = {
            'Callback': '<http://{0}:{1}>'.format(ip_address, port),
            'NT': 'upnp:event'
        }
        if requested_timeout is not None:
            headers["TIMEOUT"] = "Seconds-{}".format(requested_timeout)
        response = requests.request(
            'SUBSCRIBE', service.base_url + service.event_subscription_url,
            headers=headers)
        response.raise_for_status()
        self.sid = response.headers['sid']
        timeout = response.headers['timeout']
        # According to the spec, timeout can be "infinite" or "second-123"
        # where 123 is a number of seconds.  Sonos uses "Seconds-123" (with an
        # 's') and a capital letter
        if timeout.lower() == 'infinite':
            self.timeout = None
        else:
            self.timeout = int(timeout.lstrip('Seconds-'))
        self._timestamp = time.time()
        self.is_subscribed = True
        log.debug(
            "Subscribed to %s, sid: %s",
            service.base_url + service.event_subscription_url, self.sid)
        # Add the queue to the master dict of queues so it can be looked up
        # by sid
        with _sid_to_event_queue_lock:
            _sid_to_event_queue[self.sid] = self.events
        # And do the same for the sid to service mapping
        with _sid_to_service_lock:
            _sid_to_service[self.sid] = self.service

    def renew(self, requested_timeout=None):
        """Renew the event subscription.

        You should not try to renew a subscription which has been
        unsubscribed

        """
        if self._has_been_unsubscribed:
            raise SoCoException(
                'Cannot renew instance once unsubscribed')

        # SUBSCRIBE publisher path HTTP/1.1
        # HOST: publisher host:publisher port
        # SID: uuid:subscription UUID
        # TIMEOUT: Second-requested subscription duration (optional)

        headers = {
            'SID': self.sid
        }
        if requested_timeout is not None:
            headers["TIMEOUT"] = "Seconds-{}".format(requested_timeout)
        response = requests.request(
            'SUBSCRIBE',
            self.service.base_url + self.service.event_subscription_url,
            headers=headers)
        response.raise_for_status()
        timeout = response.headers['timeout']
        # According to the spec, timeout can be "infinite" or "second-123"
        # where 123 is a number of seconds.  Sonos uses "Seconds-123" (with an
        # 's') and a capital letter
        if timeout.lower() == 'infinite':
            self.timeout = None
        else:
            self.timeout = int(timeout.lstrip('Seconds-'))
        self._timestamp = time.time()
        self.is_subscribed = True
        log.debug(
            "Renewed subscription to %s, sid: %s",
            self.service.base_url + self.service.event_subscription_url,
            self.sid)

    def unsubscribe(self):
        """Unsubscribe from the service's events

        Once unsubscribed, a Subscription instance should not be reused

        """
        # UNSUBSCRIBE publisher path HTTP/1.1
        # HOST: publisher host:publisher port
        # SID: uuid:subscription UUID
        headers = {
            'SID': self.sid
        }
        response = requests.request(
            'UNSUBSCRIBE',
            self.service.base_url + self.service.event_subscription_url,
            headers=headers)
        response.raise_for_status()
        self.is_subscribed = False
        self._timestamp = None
        log.debug(
            "Unsubscribed from %s, sid: %s",
            self.service.base_url + self.service.event_subscription_url,
            self.sid)
        # remove queue from event queues and sid to service mappings
        with _sid_to_event_queue_lock:
            try:
                del _sid_to_event_queue[self.sid]
            except KeyError:
                pass
        with _sid_to_service_lock:
            try:
                del _sid_to_service[self.sid]
            except KeyError:
                pass
        self._has_been_unsubscribed = True

    @property
    def time_left(self):
        """
        The amount of time left until the subscription expires, in seconds

        If the subscription is unsubscribed (or not yet subscribed) return 0

        """
        if self._timestamp is None:
            return 0
        else:
            return self.timeout-(time.time()-self._timestamp)

# pylint: disable=C0103
event_listener = EventListener()

# Thread safe mappings.
# Used to store a mapping of sids to event queues
_sid_to_event_queue = weakref.WeakValueDictionary()
# Used to store a mapping of sids to service instances
_sid_to_service = weakref.WeakValueDictionary()

# The locks to go with them
# You must only ever access the mapping in the context of this lock, eg:
#   with _sid_to_event_queue_lock:
#       queue = _sid_to_event_queue[sid]
_sid_to_event_queue_lock = threading.Lock()
_sid_to_service_lock = threading.Lock()

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-

""" Exceptions that are used by SoCo """


class SoCoException(Exception):
    """ base exception raised by SoCo, containing the UPnP error code """


class UnknownSoCoException(SoCoException):
    """ raised if reason of the error can not be extracted

    The exception object will contain the raw response sent back from the
    speaker """


class SoCoUPnPException(SoCoException):
    """ encapsulates UPnP Fault Codes raised in response to actions sent over
    the network """

    def __init__(self, message, error_code, error_xml, error_description=""):
        super(SoCoUPnPException, self).__init__()
        self.message = message
        self.error_code = error_code
        self.error_description = error_description
        self.error_xml = error_xml

    def __str__(self):
        return self.message


class CannotCreateDIDLMetadata(SoCoException):
    """ Raised if a data container class cannot create the DIDL metadata due to
    missing information

    """


class UnknownXMLStructure(SoCoException):
    """Raised if XML with and unknown or unexpected structure is returned"""

########NEW FILE########
__FILENAME__ = groups
# -*- coding: utf-8 -*-
# pylint: disable=too-few-public-methods
"""
Classes and functionality relating to Sonos Groups

"""

from __future__ import unicode_literals


class ZoneGroup(object):
    """
    A class representing a Sonos Group. It looks like this::

        ZoneGroup(
            uid='RINCON_000E5879136C01400:58',
            coordinator=SoCo("192.168.1.101"),
            members=set([SoCo("192.168.1.101"), SoCo("192.168.1.102")])
            )


    Any SoCo instance can tell you what group it is in::

        >>>my_player.group
        ZoneGroup(
            uid='RINCON_000E5879136C01400:58',
            coordinator=SoCo("192.168.1.101"),
            members=set([SoCo("192.168.1.101"), SoCo("192.168.1.102")])
        )

    From there, you can find the coordinator for the current group::

        >>>my_player.group.coordinator
        SoCo("192.168.1.101")

    or, for example, its name::

        >>>my_player.group.coordinator.player_name
        Kitchen

    or a set of the members::

        >>>my_player.group.members
        {SoCo("192.168.1.101"), SoCo("192.168.1.102")}

    For convenience, ZoneGroup is also a container::

        >>>for player in my_player.group:
        ...   print player.player_name
        Living Room
        Kitchen

    If you need it, you can get an iterator over all groups on the network::

        >>>my_player.all_groups
        <generator object all_groups at 0x108cf0c30>

    """
    def __init__(self, uid, coordinator, members=None):
        #: The unique Sonos ID for this group
        self.uid = uid
        #: The :class:`Soco` instance which coordiantes this group
        self.coordinator = coordinator
        if members is not None:
            #: A set of :class:`Soco` instances which are members
            #  of the group
            self.members = set(members)
        else:
            self.members = set()

    def __iter__(self):
        return self.members.__iter__()

    def __contains__(self, member):
        return member in self.members

    def __repr__(self):
        return "{}(uid='{}', coordinator={!r}, members={!r})".format(
            self.__class__.__name__, self.uid, self.coordinator, self.members)

########NEW FILE########
__FILENAME__ = example
# -*- coding: utf-8 -*-

""" Example implementation of a plugin """

from __future__ import unicode_literals, print_function

from ..plugins import SoCoPlugin


__all__ = ['ExamplePlugin']


class ExamplePlugin(SoCoPlugin):
    """ This file serves as an example of a SoCo plugin """

    def __init__(self, soco, username):
        """ Initialize the plugin

        The plugin can accept any arguments it requires. It should at least
        accept a soco instance which it passes on to the base class when
        calling super's __init__.  """
        super(ExamplePlugin, self).__init__(soco)
        self.username = username

    @property
    def name(self):
        return 'Example Plugin for {name}'.format(name=self.username)

    def music_plugin_play(self):
        """ Play some music

        This is just a reimplementation of the ordinary play function, to show
        how we can use the general upnp methods from soco """

        print('Hi,', self.username)

        self.soco.avTransport.Play([
            ('InstanceID', 0),
            ('Speed', 1)
            ])

    def music_plugin_stop(self):
        """ Stop the music

        This methods shows how, if we need it, we can use the soco
        functionality from inside the plugins """

        print('Bye,', self.username)
        self.soco.stop()

########NEW FILE########
__FILENAME__ = spotify
# -*- coding: utf-8 -*-
# pylint: disable=R0913,W0142

""" Spotify Plugin """

import requests

from ..xml import XML
from ..compat import quote_plus
from . import SoCoPlugin


__all__ = ['Spotify']


class SpotifyTrack(object):
    """ Class that represents a Spotify track

    usage example: SpotifyTrack('spotify:track:20DfkHC5grnKNJCzZQB6KC') """

    def __init__(self, spotify_uri):
        self.data = {}
        self.data['spotify_uri'] = spotify_uri

    @property
    def spotify_uri(self):
        """ The track's Spotify URI """
        return self.data['spotify_uri']

    @spotify_uri.setter
    def spotify_uri(self, uri):
        """ Set the track's Spotify URI """
        self.data['spotify_uri'] = uri

    @property
    def album_uri(self):
        """ The album's URI """
        return self.data['album_uri']

    @album_uri.setter
    def album_uri(self, uri):
        """ Set the album's URI """
        self.data['album_uri'] = uri

    @property
    def title(self):
        """ The track's title """
        return self.data['title']

    @title.setter
    def title(self, title):
        """ Set the track's title """
        self.data['title'] = title.encode('utf-8')

    @property
    def didl_metadata(self):
        """ DIDL Metadata """
        if ('spotify_uri' in self.data and 'title' in self.data and
                'album_uri' in self.data):

            didl_metadata = """\
<DIDL-Lite xmlns:dc="http://purl.org/dc/elements/1.1/"
           xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"
           xmlns:r="urn:schemas-rinconnetworks-com:metadata-1-0/"
           xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/">
    <item id="{0}" parentID="{1}" restricted="true">
        <dc:title>{2}</dc:title>
        <upnp:class>object.item.audioItem.musicTrack</upnp:class>
        <desc id="cdudn"
            nameSpace="urn:schemas-rinconnetworks-com:metadata-1-0/">
            SA_RINCON2311_X_#Svc2311-0-Token
        </desc>
    </item>
</DIDL-Lite>""".format(quote_plus(self.data['spotify_uri']),
                       quote_plus(self.data['album_uri']),
                       quote_plus(self.data['title']))
            didl_metadata = didl_metadata.encode('utf-8')
            return XML.fromstring(didl_metadata)
        else:
            return None

    @property
    def uri(self):
        """ Sonos-Spotify URI """
        if 'spotify_uri' in self.data:
            track = self.data['spotify_uri']
            track = track.encode('utf-8')
            track = quote_plus(track)
            return 'x-sonos-spotify:' + track
        else:
            return ''

    def satisfied(self):
        """ Checks if necessary track data is available """
        return 'title' in self.data and 'didl_metadata' in self.data


class SpotifyAlbum(object):
    """ Class that represents a Spotifyalbum

    usage example: SpotifyAlbum('spotify:album:6a50SaJpvdWDp13t0wUcPU') """

    def __init__(self, spotify_uri):
        self.data = {}
        self.data['spotify_uri'] = spotify_uri

    @property
    def spotify_uri(self):
        """ The album's Spotify URI """
        return self.data['spotify_uri']

    @spotify_uri.setter
    def spotify_uri(self, uri):
        """ Set the album's Spotify URI """
        self.data['spotify_uri'] = uri

    @property
    def artist_uri(self):
        """ The artist's URI """
        return self.data['artist_uri']

    @artist_uri.setter
    def artist_uri(self, artist_uri):
        """ Set the artist's URI """
        self.data['artist_uri'] = artist_uri

    @property
    def title(self):
        """ The album's title """
        return self.data['title']

    @title.setter
    def title(self, title):
        """ Set the album's title """
        self.data['title'] = title.encode('utf-8')

    @property
    def uri(self):
        """ Sonos-Spotify URI """
        if 'spotify_uri' in self.data:
            album = self.data['spotify_uri']
            album = album.encode('utf-8')
            album = quote_plus(album)
            return "x-rincon-cpcontainer:" + album
        else:
            return ""

    @property
    def didl_metadata(self):
        """ DIDL Metadata """
        if self.satisfied:
            didl_metadata = """\
<DIDL-Lite xmlns:dc="http://purl.org/dc/elements/1.1/"
           xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"
           xmlns:r="urn:schemas-rinconnetworks-com:metadata-1-0/"
           xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/">
    <item id="{0}" parentID="{1}" restricted="true">
        <dc:title>{2}</dc:title>
        <upnp:class>object.container.album.musicAlbum</upnp:class>
        <desc id="cdudn"
              nameSpace="urn:schemas-rinconnetworks-com:metadata-1-0/">
            SA_RINCON2311_X_#Svc2311-0-Token
        </desc>
    </item>
</DIDL-Lite>""".format(quote_plus(self.data['spotify_uri']),
                       quote_plus(self.data['artist_uri']),
                       quote_plus(self.data['title']))
            didl_metadata = didl_metadata.encode('utf-8')
            return XML.fromstring(didl_metadata)
        else:
            return None

    def satisfied(self):
        """ Checks if necessary album data is available """
        return ('spotify_uri' in self.data and
                'artist' in self.data and
                'title' in self.data)


class Spotify(SoCoPlugin):
    """ Class that implements spotify plugin"""

    sid = '9'
    api_lookup_url = 'http://ws.spotify.com/lookup/1/.json'

    def __init__(self, soco):
        """ Initialize the plugin"""
        super(Spotify, self).__init__(soco)

    @property
    def name(self):
        return 'Spotify plugin'

    def _add_track_metadata(self, spotify_track):
        """ Adds metadata by using the spotify public API """
        track = SpotifyTrack(spotify_track.spotify_uri)
        params = {'uri': spotify_track.spotify_uri}
        res = requests.get(self.api_lookup_url, params=params)
        data = res.json()

        if 'track' in data:
            track.title = data['track']['name']
            track.album_uri = data['track']['album']['href']

        return track

    def _add_album_metadata(self, spotify_album):
        """ Adds metadata by using the spotify public API """
        album = SpotifyAlbum(spotify_album.spotify_uri)
        params = {'uri': spotify_album.spotify_uri}
        res = requests.get(self.api_lookup_url, params=params)
        data = res.json()

        if 'album' in data:
            album.title = data['album']['name']
            album.artist_uri = data['album']['artist-id']

        return album

    def add_track_to_queue(self, spotify_track):
        """ Add a spotify track to the queue using the SpotifyTrack class"""
        if not spotify_track.satisfied():
            spotify_track = self._add_track_metadata(spotify_track)

        return self.soco.add_to_queue(spotify_track)

    def add_album_to_queue(self, spotify_album):
        """ Add a spotify album to the queue using the SpotifyAlbum class """
        if not spotify_album.satisfied():
            spotify_album = self._add_album_metadata(spotify_album)

        return self.soco.add_to_queue(spotify_album)

########NEW FILE########
__FILENAME__ = wimp
# -*- coding: utf-8 -*-
# pylint: disable=R0913,W0142,fixme

""" Plugin for the Wimp music service (Service ID 20) """

from __future__ import unicode_literals
import socket
import locale

import requests

from ..services import MusicServices
from ..xml import XML
from ..data_structures import get_ms_item, MSTrack, MSAlbum, MSArtist, \
    MSAlbumList, MSFavorites, MSCollection, MSPlaylist, MSArtistTracklist
from ..utils import really_utf8
from ..exceptions import SoCoUPnPException, UnknownXMLStructure
from .__init__ import SoCoPlugin


__all__ = ['Wimp']


def _post(url, headers, body, retries=3, timeout=3.0):
    """Try 3 times to request the content

    :param headers: The HTTP headers
    :type headers: dict
    :param body: The body of the HTTP post
    :type body: str
    :param retries: The number of times to retry before giving up
    :type retries: int
    :param timeout: The time to wait for the post to complete, before timing
        out
    :type timeout: float

    """
    retry = 0
    out = None
    while out is None:
        try:
            out = requests.post(url, headers=headers, data=body,
                                timeout=timeout)
        # Due to a bug in requests, the post command will sometimes fail to
        # properly wrap a socket.timeout exception in requests own exception.
        # See https://github.com/kennethreitz/requests/issues/2045
        # Until this is fixed, we need to catch both types of exceptions
        except (requests.exceptions.Timeout, socket.timeout) as exception:
            retry += 1
            if retry == retries:
                # pylint: disable=maybe-no-member
                raise requests.exceptions.Timeout(exception.message)
    return out


def _ns_tag(ns_id, tag):
    """Return a namespace/tag item. The ns_id is translated to a full name
    space via the NS module variable.

    :param ns_id: The name space ID. Translated to a namespace via the module
        variable NS
    :type ns_id: str
    :param tag: The tag
    :type str: str

    """
    return '{{{0}}}{1}'.format(NS[ns_id], tag)


def _get_header(soap_action):
    """Return the HTTP for SOAP Action

    :param soap_action: The soap action to include in the header. Can be either
        'search' or 'get_metadata'
    :type soap_action: str
    """
    # This way of setting accepted language is obviously flawed, in that it
    # depends on the locale settings of the system. However, I'm unsure if
    # they are actually used. The character coding is set elsewhere and I think
    # the available music in each country is bound to the account.
    language, _ = locale.getdefaultlocale()
    if language is None:
        language = ''
    else:
        language = language.replace('_', '-') + ', '

    header = {
        'CONNECTION': 'close',
        'ACCEPT-ENCODING': 'gzip',
        'ACCEPT-LANGUAGE': '{}en-US;q=0.9'.format(language),
        'Content-Type': 'text/xml; charset="utf-8"',
        'SOAPACTION': SOAP_ACTION[soap_action]
    }
    return header


class Wimp(SoCoPlugin):
    """Class that implements a Wimp plugin

    .. note:: There is an (apparent) in-consistency in the use of one data
    type from the Wimp service. When searching for playlists, the XML returned
    by the Wimp server indicates, that the type is an 'album list', and it
    thus suggest, that this type is used for a list of tracks (as expected for
    a playlist), and this data type is reported to be playable. However, when
    browsing the music tree, the Wimp server will return items of 'album list'
    type, but in this case it is used for a list of albums and it is not
    playable. This plugin maintains this (apparent) in-consistency to stick
    as close to the reported data as possible, so search for playlists returns
    MSAlbumList that are playable and while browsing the content tree the
    MSAlbumList items returned to you are not playable.

    .. note:: Wimp in some cases lists tracks that are not available. In these
    cases, while it will correctly report these tracks as not being playable,
    the containing data structure like e.g. the album they are on may report
    that they are playable. Trying to add one of these to the queue will
    return a SoCoUPnPException with error code '802'.

    """

    def __init__(self, soco, username, retries=3, timeout=3.0):
        """ Initialize the plugin

        :param soco: The soco instance to retrieve the session ID for the music
            service
        :type: :py:class:`soco.SoCo`
        :param username: The username for the music service
        :type username: str
        :param retries: The number of times to retry before giving up
        :type retries: int
        :param timeout: The time to wait for the post to complete, before
            timing out. The Wimp server seems either slow to respond or to
            make the queries internally, so the timeout should probably not be
            shorter than 3 seconds.
        :type timeout: float

        .. note:: If you are using a phone number as the username and are
        experiencing problems connecting, then try to prepend the area code
        (no + or 00). I.e. if your phone number is 12345678 and you are from
        denmark, then use 4512345678. This must be set up the same way in the
        Sonos device.  For details see:
        https://wimp.zendesk.com/entries/23198372-Hvorfor-kan-jeg-ikke-logge-
        p%C3%A5-WiMP-med-min-Sonos-n%C3%A5r-jeg-har-et-gyldigt-abonnement- (In
        Danish)
        """
        super(Wimp, self).__init__(soco)

        # Instantiate variables
        self._url = 'http://client.wimpmusic.com/sonos/services/Sonos'
        self._serial_number = soco.get_speaker_info()['serial_number']
        self._username = username
        self._service_id = 20
        self._http_vars = {'retries': retries, 'timeout': timeout}

        # Get a session id for the searches
        self._music_services = MusicServices(soco)
        response = self._music_services.GetSessionId([
            ('ServiceId', 20),
            ('Username', username)
        ])
        self._session_id = response['SessionId']

    @property
    def name(self):
        """Return the human read-able name for the plugin"""
        return 'Wimp Plugin for {}'.format(self._username)

    @property
    def username(self):
        """Return the username"""
        return self._username

    @property
    def service_id(self):
        """Return the service id"""
        return self._service_id

    @property
    def description(self):
        """Return the music service description for the DIDL metadata on the
        form SA_RINCON5127_...self.username...
        """
        return 'SA_RINCON5127_{}'.format(self._username)

    def get_tracks(self, search, start=0, max_items=100):
        """Search for tracks

        See get_music_service_information for details on the arguments
        """
        return self.get_music_service_information('tracks', search, start,
                                                  max_items)

    def get_albums(self, search, start=0, max_items=100):
        """Search for albums

        See get_music_service_information for details on the arguments
        """
        return self.get_music_service_information('albums', search, start,
                                                  max_items)

    def get_artists(self, search, start=0, max_items=100):
        """Search for artists

        See get_music_service_information for details on the arguments
        """
        return self.get_music_service_information('artists', search, start,
                                                  max_items)

    def get_playlists(self, search, start=0, max_items=100):
        """Search for playlists

        See get_music_service_information for details on the arguments.

        .. note:: Un-intuitively this method returns MSAlbumList items. See
        note in class doc string for details.
        """
        return self.get_music_service_information('playlists', search, start,
                                                  max_items)

    def get_music_service_information(self, search_type, search, start=0,
                                      max_items=100):
        """Search for music service information items

        :param search_type: The type of search to perform, possible values are:
            'artists', 'albums', 'tracks' and 'playlists'
        :type search_type: str
        :param search: The search string to use
        :type search: str
        :param start: The starting index of the returned items
        :type start: int
        :param max_items: The maximum number of returned items
        :type max_items: int

        .. note:: Un-intuitively the playlist search returns MSAlbumList
        items. See note in class doc string for details.
        """
        # Check input
        if search_type not in ['artists', 'albums', 'tracks', 'playlists']:
            message = 'The requested search {} is not valid'\
                .format(search_type)
            raise ValueError(message)
        # Transform search: tracks -> tracksearch
        search_type = '{}earch'.format(search_type)
        parent_id = SEARCH_PREFIX.format(search_type=search_type,
                                         search=search)

        # Perform search
        body = self._search_body(search_type, search, start, max_items)
        headers = _get_header('search')
        response = _post(self._url, headers, body, **self._http_vars)
        self._check_for_errors(response)
        result_dom = XML.fromstring(response.text.encode('utf-8'))

        # Parse results
        search_result = result_dom.find('.//' + _ns_tag('', 'searchResult'))
        out = {'item_list': []}
        for element in ['index', 'count', 'total']:
            out[element] = search_result.findtext(_ns_tag('', element))

        if search_type == 'tracksearch':
            item_name = 'mediaMetadata'
        else:
            item_name = 'mediaCollection'
        for element in search_result.findall(_ns_tag('', item_name)):
            out['item_list'].append(get_ms_item(element, self, parent_id))

        return out

    def browse(self, ms_item=None):
        """Return the sub-elements of item or of the root if item is None

        :param item: Instance of sub-class of
        :py:class:`soco.data_structures.MusicServiceItem`. This object must
        have item_id, service_id and extended_id properties

        .. note:: Browsing a MSTrack item will return itself.

        .. note:: This plugin cannot yet set the parent ID of the results
        correctly when browsing :py:class:`soco.data_structures.MSFavorites`
        and :py:class:`soco.data_structures.MSCollection` elements.

        """
        # Check for correct service
        if ms_item is not None and ms_item.service_id != self._service_id:
            message = 'This music service item is not for this service'
            raise ValueError(message)

        # Form HTTP body and set parent_id
        if ms_item:
            body = self._browse_body(ms_item.item_id)
            parent_id = ms_item.extended_id
            if parent_id is None:
                parent_id = ''
        else:
            body = self._browse_body('root')
            parent_id = '0'

        # Get HTTP header and post
        headers = _get_header('get_metadata')
        response = _post(self._url, headers, body, **self._http_vars)

        # Check for errors and get XML
        self._check_for_errors(response)
        result_dom = XML.fromstring(really_utf8(response.text))
        # Find the getMetadataResult item ...
        xpath_search = './/' + _ns_tag('', 'getMetadataResult')
        metadata_result = list(result_dom.findall(xpath_search))
        # ... and make sure there is exactly 1
        if len(metadata_result) != 1:
            raise UnknownXMLStructure(
                'The results XML has more than 1 \'getMetadataResult\'. This '
                'is unexpected and parsing will dis-continue.'
            )
        metadata_result = metadata_result[0]

        # Browse the children of metadata result
        out = {'item_list': []}
        for element in ['index', 'count', 'total']:
            out[element] = metadata_result.findtext(_ns_tag('', element))
        for result in metadata_result:
            if result.tag in [_ns_tag('', 'mediaCollection'),
                              _ns_tag('', 'mediaMetadata')]:
                out['item_list'].append(get_ms_item(result, self, parent_id))
        return out

    @staticmethod
    def id_to_extended_id(item_id, item_class):
        """Return the extended ID from an ID

        :param item_id: The ID of the music library item
        :type item_id: str
        :param cls: The class of the music service item
        :type cls: Sub-class of
            :py:class:`soco.data_structures.MusicServiceItem`

        The extended id can be something like 00030020trackid_22757082
        where the id is just trackid_22757082. For classes where the prefix is
        not known returns None.
        """
        out = ID_PREFIX[item_class]
        if out:
            out += item_id
        return out

    @staticmethod
    def form_uri(item_content, item_class):
        """Form the URI for a music service element

        :param item_content: The content dict of the item
        :type item_content: dict
        :param item_class: The class of the item
        :type item_class: Sub-class of
        :py:class:`soco.data_structures.MusicServiceItem`

        """
        extension = None
        if 'mime_type' in item_content:
            extension = MIME_TYPE_TO_EXTENSION[item_content['mime_type']]
        out = URIS.get(item_class)
        if out:
            out = out.format(extension=extension, **item_content)
        return out

    def _search_body(self, search_type, search_term, start, max_items):
        """Return the search XML body

        :param search_type: The search type
        :type search_type: str
        :param search_term: The search term e.g. 'Jon Bon Jovi'
        :type search_term: str
        :param start: The start index of the returned results
        :type start: int
        :param max_items: The maximum number of returned results
        :type max_items: int

        The XML is formed by adding, to the envelope of the XML returned by
        ``self._base_body``, the following ``Body`` part:

        .. code :: xml

         <s:Body>
           <search xmlns="http://www.sonos.com/Services/1.1">
             <id>search_type</id>
             <term>search_term</term>
             <index>start</index>
             <count>max_items</count>
           </search>
         </s:Body>
        """
        xml = self._base_body()

        # Add the Body part
        XML.SubElement(xml, 's:Body')
        item_attrib = {
            'xmlns': 'http://www.sonos.com/Services/1.1'
        }
        search = XML.SubElement(xml[1], 'search', item_attrib)
        XML.SubElement(search, 'id').text = search_type
        XML.SubElement(search, 'term').text = search_term
        XML.SubElement(search, 'index').text = str(start)
        XML.SubElement(search, 'count').text = str(max_items)

        return XML.tostring(xml)

    def _browse_body(self, search_id):
        """Return the browse XML body

        The XML is formed by adding, to the envelope of the XML returned by
        ``self._base_body``, the following ``Body`` part:

        .. code :: xml

         <s:Body>
           <getMetadata xmlns="http://www.sonos.com/Services/1.1">
             <id>root</id>
             <index>0</index>
             <count>100</count>
           </getMetadata>
         </s:Body>

        .. note:: The XML contains index and count, but the service does not
        seem to respect them, so therefore they have not been included as
        arguments.

        """
        xml = self._base_body()

        # Add the Body part
        XML.SubElement(xml, 's:Body')
        item_attrib = {
            'xmlns': 'http://www.sonos.com/Services/1.1'
        }
        search = XML.SubElement(xml[1], 'getMetadata', item_attrib)
        XML.SubElement(search, 'id').text = search_id
        # Investigate this index, count stuff more
        XML.SubElement(search, 'index').text = '0'
        XML.SubElement(search, 'count').text = '100'

        return XML.tostring(xml)

    def _base_body(self):
        """Return the base XML body, which has the following form:

        .. code :: xml

         <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
           <s:Header>
             <credentials xmlns="http://www.sonos.com/Services/1.1">
               <sessionId>self._session_id</sessionId>
               <deviceId>self._serial_number</deviceId>
               <deviceProvider>Sonos</deviceProvider>
             </credentials>
           </s:Header>
         </s:Envelope>
        """
        item_attrib = {
            'xmlns:s': 'http://schemas.xmlsoap.org/soap/envelope/',
        }
        xml = XML.Element('s:Envelope', item_attrib)

        # Add the Header part
        XML.SubElement(xml, 's:Header')
        item_attrib = {
            'xmlns': 'http://www.sonos.com/Services/1.1'
        }
        credentials = XML.SubElement(xml[0], 'credentials', item_attrib)
        XML.SubElement(credentials, 'sessionId').text = self._session_id
        XML.SubElement(credentials, 'deviceId').text = self._serial_number
        XML.SubElement(credentials, 'deviceProvider').text = 'Sonos'

        return xml

    def _check_for_errors(self, response):
        """Check a response for errors

        :param response: the response from requests.post()

        """
        if response.status_code != 200:
            xml_error = really_utf8(response.text)
            error_dom = XML.fromstring(xml_error)
            fault = error_dom.find('.//' + _ns_tag('s', 'Fault'))
            error_description = fault.find('faultstring').text
            error_code = EXCEPTION_STR_TO_CODE[error_description]
            message = 'UPnP Error {} received: {} from {}'.format(
                error_code, error_description, self._url)
            raise SoCoUPnPException(
                message=message,
                error_code=error_code,
                error_description=error_description,
                error_xml=really_utf8(response.text)
            )


SOAP_ACTION = {
    'get_metadata': '"http://www.sonos.com/Services/1.1#getMetadata"',
    'search': '"http://www.sonos.com/Services/1.1#search"'
}
# Note UPnP exception 802 while trying to add a Wimp track indicates that these
# are tracks that not available in Wimp. Do something with that.
EXCEPTION_STR_TO_CODE = {
    'unknown': 20000,
    'ItemNotFound': 20001
}
SEARCH_PREFIX = '00020064{search_type}:{search}'
ID_PREFIX = {
    MSTrack: '00030020',
    MSAlbum: '0004002c',
    MSArtist: '10050024',
    MSAlbumList: '000d006c',
    MSPlaylist: '0006006c',
    MSArtistTracklist: '100f006c',
    MSFavorites: None,  # This one is unknown
    MSCollection: None  # This one is unknown

}
MIME_TYPE_TO_EXTENSION = {
    'audio/aac': 'mp4'
}
URIS = {
    MSTrack: 'x-sonos-http:{item_id}.{extension}?sid={service_id}&flags=32',
    MSAlbum: 'x-rincon-cpcontainer:{extended_id}',
    MSAlbumList: 'x-rincon-cpcontainer:{extended_id}',
    MSPlaylist: 'x-rincon-cpcontainer:{extended_id}',
    MSArtistTracklist: 'x-rincon-cpcontainer:{extended_id}'
}
NS = {
    's': 'http://schemas.xmlsoap.org/soap/envelope/',
    '': 'http://www.sonos.com/Services/1.1'
}

########NEW FILE########
__FILENAME__ = services
# -*- coding: utf-8 -*-
# pylint: disable=fixme, invalid-name

"""
Classes representing Sonos UPnP services.

>>> s = SoCo('192.168.1.102')
>>> print s.RenderingControl.GetMute([('InstanceID', 0),
...     ('Channel', 'Master')])

>>> r = s.ContentDirectory.Browse([
...    ('ObjectID', 'Q:0'),
...    ('BrowseFlag', 'BrowseDirectChildren'),
...    ('Filter', '*'),
...    ('StartingIndex', '0'),
...    ('RequestedCount', '100'),
...    ('SortCriteria', '')
...    ])

>>> print prettify(r['Result'])

>>> for action, in_args, out_args in s.QPlay.iter_actions():
...    print action, in_args, out_args

"""
# UPnP Spec at http://upnp.org/specs/arch/UPnP-arch-DeviceArchitecture-v1.0.pdf

from __future__ import unicode_literals, absolute_import

# UNICODE NOTE
# UPnP requires all XML to be transmitted/received with utf-8 encoding. All
# strings used in this module are unicode. The Requests library should take
# care of all of the necessary encoding (on sending) and decoding (on
# receiving) for us, provided that we specify the correct encoding headers
# (which, hopefully, we do).
# But since ElementTree seems to prefer being fed bytes to unicode, at least
# for Python 2.x, we have to encode strings specifically before using it. see
# http://bugs.python.org/issue11033 TODO: Keep an eye on this when it comes to
# Python 3 compatibility


from collections import namedtuple
from xml.sax.saxutils import escape
import logging

import requests
from .exceptions import SoCoUPnPException, UnknownSoCoException
from .utils import prettify, TimedCache
from .events import Subscription
from .xml import XML

log = logging.getLogger(__name__)  # pylint: disable=C0103
# logging.basicConfig()
# log.setLevel(logging.INFO)

Action = namedtuple('Action', 'name, in_args, out_args')
Argument = namedtuple('Argument', 'name, vartype')

# A shared cache for ZoneGroupState. Each zone has the same info, so when a
# SoCo instance is asked for group info, we can cache it and return it when
# another instance is asked. To do this we need a cache to be shared between
# instances
zone_group_state_shared_cache = TimedCache()


# pylint: disable=too-many-instance-attributes
class Service(object):
    """ An class representing a UPnP service. The base class for all Sonos
    Service classes

    This class has a dynamic method dispatcher. Calls to methods which are not
    explicitly defined here are dispatched automatically to the service action
    with the same name.

    """
    # pylint: disable=bad-continuation
    soap_body_template = (
        '<?xml version="1.0"?>'
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"'
        ' s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            '<s:Body>'
                '<u:{action} xmlns:u="urn:schemas-upnp-org:service:'
                    '{service_type}:{version}">'
                    '{arguments}'
                '</u:{action}>'
            '</s:Body>'
        '</s:Envelope>')  # noqa PEP8

    def __init__(self, soco):
        self.soco = soco
        # Some defaults. Some or all these will need to be overridden
        # specifically in a sub-class. There is other information we could
        # record, but this will do for the moment. Info about a Sonos device is
        # available at <IP_address>/xml/device_description.xml in the
        # <service> tags
        self.service_type = self.__class__.__name__
        self.version = 1
        self.service_id = self.service_type
        self.base_url = 'http://{}:1400'.format(self.soco.ip_address)
        self.control_url = '/{}/Control'.format(self.service_type)
        # Service control protocol description
        self.scpd_url = '/xml/{}{}.xml'.format(self.service_type, self.version)
        # Eventing subscription
        self.event_subscription_url = '/{}/Event'.format(self.service_type)
        #: A cache for storing the result of network calls. By default, this is
        #: TimedCache(default_timeout=0). See :class:`TimedCache`
        self.cache = TimedCache(default_timeout=0)
        log.debug(
            "Created service %s, ver %s, id %s, base_url %s, control_url %s",
            self.service_type, self.version, self.service_id, self.base_url,
            self.control_url)

        # From table 3.3 in
        # http://upnp.org/specs/arch/UPnP-arch-DeviceArchitecture-v1.1.pdf
        # This list may not be complete, but should be good enough to be going
        # on with.  Error codes between 700-799 are defined for particular
        # services, and may be overriden in subclasses. Error codes >800
        # are generally SONOS specific. NB It may well be that SONOS does not
        # use some of these error codes.

        # pylint: disable=invalid-name
        self.UPNP_ERRORS = {
            400: 'Bad Request',
            401: 'Invalid Action',
            402: 'Invalid Args',
            404: 'Invalid Var',
            412: 'Precondition Failed',
            501: 'Action Failed',
            600: 'Argument Value Invalid',
            601: 'Argument Value Out of Range',
            602: 'Optional Action Not Implemented',
            603: 'Out Of Memory',
            604: 'Human Intervention Required',
            605: 'String Argument Too Long',
            606: 'Action Not Authorized',
            607: 'Signature Failure',
            608: 'Signature Missing',
            609: 'Not Encrypted',
            610: 'Invalid Sequence',
            611: 'Invalid Control URL',
            612: 'No Such Session',
        }

    def __getattr__(self, action):
        """ A Python magic method which is called whenever an undefined method
        is invoked on the instance.

        The name of the unknown method called is passed as a parameter, and the
        return value is the callable to be invoked.

        """

        # Define a function to be invoked as the method, which calls
        # send_command.
        def _dispatcher(self, *args, **kwargs):
            """ Dispatch to send_command """
            return self.send_command(action, *args, **kwargs)

        # rename the function so it appears to be the called method. We
        # probably don't need this, but it doesn't harm
        _dispatcher.__name__ = action

        # _dispatcher is now an unbound menthod, but we need a bound method.
        # This turns an unbound method into a bound method (i.e. one that
        # takes self - an instance of the class - as the first parameter)
        # pylint: disable=no-member
        method = _dispatcher.__get__(self, self.__class__)
        # Now we have a bound method, we cache it on this instance, so that
        # next time we don't have to go through this again
        setattr(self, action, method)
        log.debug("Dispatching method %s", action)

        # return our new bound method, which will be called by Python
        return method

    @staticmethod
    def wrap_arguments(args=None):
        """ Wrap a list of tuples in xml ready to pass into a SOAP request.

        args is a list of (name, value) tuples specifying the name of each
        argument and its value, eg [('InstanceID', 0), ('Speed', 1)]. The value
        can be a string or something with a string representation. The
        arguments are escaped and wrapped in <name> and <value> tags.

        >>> from soco import SoCo
        >>> device = SoCo('192.168.1.101')
        >>> s = Service(device)
        >>> s.wrap_arguments([('InstanceID', 0), ('Speed', 1)])
        <InstanceID>0</InstanceID><Speed>1</Speed>'

        """
        if args is None:
            args = []

        tags = []
        for name, value in args:
            tag = "<{name}>{value}</{name}>".format(
                name=name, value=escape("%s" % value, {'"': "&quot;"}))
            # % converts to unicode because we are using unicode literals.
            # Avoids use of 'unicode' function which does not exist in python 3
            tags.append(tag)

        xml = "".join(tags)
        return xml

    @staticmethod
    def unwrap_arguments(xml_response):
        """ Extract arguments and their values from a SOAP response.

        Given an soap/xml response, return a dict of {argument_name, value)}
        items

        """

        # A UPnP SOAP response (including headers) looks like this:

        # HTTP/1.1 200 OK
        # CONTENT-LENGTH: bytes in body
        # CONTENT-TYPE: text/xml; charset="utf-8" DATE: when response was
        # generated
        # EXT:
        # SERVER: OS/version UPnP/1.0 product/version
        #
        # <?xml version="1.0"?>
        # <s:Envelope
        #   xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
        #   s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
        #   <s:Body>
        #       <u:actionNameResponse
        #           xmlns:u="urn:schemas-upnp-org:service:serviceType:v">
        #           <argumentName>out arg value</argumentName>
        #               ... other out args and their values go here, if any
        #       </u:actionNameResponse>
        #   </s:Body>
        # </s:Envelope>

        # Get all tags in order. Elementree (in python 2.x) seems to prefer to
        # be fed bytes, rather than unicode
        xml_response = xml_response.encode('utf-8')
        tree = XML.fromstring(xml_response)

        # Get the first child of the <Body> tag which will be
        # <{actionNameResponse}> (depends on what actionName is). Turn the
        # children of this into a {tagname, content} dict. XML unescaping
        # is carried out for us by elementree.
        action_response = tree.find(
            ".//{http://schemas.xmlsoap.org/soap/envelope/}Body")[0]
        return {i.tag: i.text or "" for i in action_response}

    def build_command(self, action, args=None):
        """ Build a SOAP request.

        Given the name of an action (a string as specified in the service
        description XML file) to be sent, and the relevant arguments as a list
        of (name, value) tuples, return a tuple containing the POST headers (as
        a dict) and a string containing the relevant SOAP body. Does not set
        content-length, or host headers, which are completed upon sending.

        """

        # A complete request should look something like this:

        # POST path of control URL HTTP/1.1
        # HOST: host of control URL:port of control URL
        # CONTENT-LENGTH: bytes in body
        # CONTENT-TYPE: text/xml; charset="utf-8"
        # SOAPACTION: "urn:schemas-upnp-org:service:serviceType:v#actionName"
        #
        # <?xml version="1.0"?>
        # <s:Envelope
        #   xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
        #   s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
        #   <s:Body>
        #       <u:actionName
        #           xmlns:u="urn:schemas-upnp-org:service:serviceType:v">
        #           <argumentName>in arg value</argumentName>
        #           ... other in args and their values go here, if any
        #       </u:actionName>
        #   </s:Body>
        # </s:Envelope>

        arguments = self.wrap_arguments(args)
        body = self.soap_body_template.format(
            arguments=arguments, action=action, service_type=self.service_type,
            version=self.version)
        soap_action_template = \
            "urn:schemas-upnp-org:service:{service_type}:{version}#{action}"
        soap_action = soap_action_template.format(
            service_type=self.service_type, version=self.version,
            action=action)
        headers = {'Content-Type': 'text/xml; charset="utf-8"',
                   'SOAPACTION': soap_action}
        return (headers, body)

    def send_command(self, action, args=None, cache=None, cache_timeout=None):
        """ Send a command to a Sonos device.

        Given the name of an action (a string as specified in the service
        description XML file) to be sent, and the relevant arguments as a list
        of (name, value) tuples, send the command to the Sonos device. args
        can be empty.

        A cache is operated so that the result will be stored for up to
        `cache_timeout` seconds, and a subsequent call with the same arguments
        within that period will be returned from the cache, saving a further
        network call. The cache may be invalidated or even primed from another
        thread (for example if a UPnP event is received to indicate that the
        state of the Sonos device has changed). If `cache_timeout` is missing
        or `None`, the cache will use a default value (which may be 0 - see
        :attribute:`cache`). By default, the cache identified by the service's
        :attribute:`cache` attribute will be used, but a different cache object
        may be specified in the `cache` parameter.

        Return a dict of {argument_name, value)} items or True on success.
        Raise an exception on failure.

        """
        if cache is None:
            cache = self.cache
        result = cache.get(action, args)
        if result is not None:
            log.debug("Cache hit")
            return result
        # Cache miss, so go ahead and make a network call
        headers, body = self.build_command(action, args)
        log.info("Sending %s %s to %s", action, args, self.soco.ip_address)
        log.debug("Sending %s, %s", headers, prettify(body))
        response = requests.post(
            self.base_url + self.control_url, headers=headers, data=body)
        log.debug("Received %s, %s", response.headers, response.text)
        status = response.status_code
        if status == 200:
            # The response is good. Get the output params, and return them.
            # NB an empty dict is a valid result. It just means that no
            # params are returned.
            result = self.unwrap_arguments(response.text) or True
            # Store in the cache. There is no need to do this if there was an
            # error, since we would want to try a network call again.
            cache.put(result, action, args, timeout=cache_timeout)
            log.info(
                "Received status %s from %s", status, self.soco.ip_address)
            return result
        elif status == 500:
            # Internal server error. UPnP requires this to be returned if the
            # device does not like the action for some reason. The returned
            # content will be a SOAP Fault. Parse it and raise an error.
            try:
                self.handle_upnp_error(response.text)
            except Exception as exc:
                log.exception(str(exc))
                raise
        else:
            # Something else has gone wrong. Probably a network error. Let
            # Requests handle it
            response.raise_for_status()

    def handle_upnp_error(self, xml_error):
        """ Disect a UPnP error, and raise an appropriate exception

        xml_error is a unicode string containing the body of the UPnP/SOAP
        Fault response. Raises an exception containing the error code

        """

        # An error code looks something like this:

        # HTTP/1.1 500 Internal Server Error
        # CONTENT-LENGTH: bytes in body
        # CONTENT-TYPE: text/xml; charset="utf-8"
        # DATE: when response was generated
        # EXT:
        # SERVER: OS/version UPnP/1.0 product/version

        # <?xml version="1.0"?>
        # <s:Envelope
        #   xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
        #   s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
        #   <s:Body>
        #       <s:Fault>
        #           <faultcode>s:Client</faultcode>
        #           <faultstring>UPnPError</faultstring>
        #           <detail>
        #               <UPnPError xmlns="urn:schemas-upnp-org:control-1-0">
        #                   <errorCode>error code</errorCode>
        #                   <errorDescription>error string</errorDescription>
        #               </UPnPError>
        #           </detail>
        #       </s:Fault>
        #   </s:Body>
        # </s:Envelope>
        #
        # All that matters for our purposes is the errorCode.
        # errorDescription is not required, and Sonos does not seem to use it.

        # NB need to encode unicode strings before passing to ElementTree
        xml_error = xml_error.encode('utf-8')
        error = XML.fromstring(xml_error)
        log.debug("Error %s", xml_error)
        error_code = error.findtext(
            './/{urn:schemas-upnp-org:control-1-0}errorCode')
        if error_code is not None:
            description = self.UPNP_ERRORS.get(int(error_code), '')
            raise SoCoUPnPException(
                message='UPnP Error {} received: {} from {}'.format(
                    error_code, description, self.soco.ip_address),
                error_code=error_code,
                error_description=description,
                error_xml=xml_error
                )
        else:
            # Unknown error, so just return the entire response
            log.error("Unknown error received from %s", self.soco.ip_address)
            raise UnknownSoCoException(xml_error)

    def subscribe(self, requested_timeout=None, event_queue=None):
        """Subscribe to the service's events.

        If requested_timeout is provided, a subscription valid for that number
        of seconds will be requested, but not guaranteed. Check
        :attrib:`Subscription.timeout` on return to find out what period of
        validity is actually allocated.

        event_queue is a thread-safe queue object onto which events will be
        put. If None, a Queue object will be created and used.

        Returns a Subscription object, representing the new subscription

        To unsubscribe, call the `unsubscribe` method on the returned object.

        """
        subscription = Subscription(
            self, event_queue)
        subscription.subscribe(requested_timeout=requested_timeout)
        return subscription

    def _update_cache_on_event(self, event):
        """ Update the cache when an event is received.

        This will be called before an event is put onto the event queue. Events
        will often indicate that the Sonos device's state has changed, so this
        opportunity is made availabe for the service to update its cache. The
        event will be put onto the event queue once this method returns.

        `event` is an Event namedtuple: ('sid', 'seq', 'service', 'variables')

        ..  warning:: This method will not be called from the main thread but
            by one or more threads, which handle the events as they come in.
            You *must not* access any class, instance or global variables
            without appropriate locks. Treat all parameters passed to this
            method as read only.

        """
        pass

    def iter_actions(self):
        """ Yield the service's actions with their in_arguments (ie parameters
        to pass to the action) and out_arguments (ie returned values).

        Each action is an Action namedtuple, consisting of action_name (a
        string), in_args (a list of Argument namedtuples consisting of name and
        argtype), and out_args (ditto), eg:

        Action(name='SetFormat',
            in_args=[Argument(name='DesiredTimeFormat', vartype='string'),
                     Argument(name='DesiredDateFormat', vartype='string')],
            out_args=[]) """

        # pylint: disable=too-many-locals
        # TODO: Provide for Allowed value list, Allowed value range,
        # default value
        # pylint: disable=invalid-name
        ns = '{urn:schemas-upnp-org:service-1-0}'
        scpd_body = requests.get(self.base_url + self.scpd_url).text
        tree = XML.fromstring(scpd_body.encode('utf-8'))
        # parse the state variables to get the relevant variable types
        statevars = tree.iterfind('.//{}stateVariable'.format(ns))
        vartypes = {}
        for state in statevars:
            name = state.findtext('{}name'.format(ns))
            vartypes[name] = state.findtext('{}dataType'.format(ns))
        # find all the actions
        actions = tree.iterfind('.//{}action'.format(ns))
        for i in actions:
            action_name = i.findtext('{}name'.format(ns))
            args_iter = i.iterfind('.//{}argument'.format(ns))
            in_args = []
            out_args = []
            for arg in args_iter:
                arg_name = arg.findtext('{}name'.format(ns))
                direction = arg.findtext('{}direction'.format(ns))
                related_variable = arg.findtext(
                    '{}relatedStateVariable'.format(ns))
                vartype = vartypes[related_variable]
                if direction == "in":
                    in_args.append(Argument(arg_name, vartype))
                else:
                    out_args.append(Argument(arg_name, vartype))
            yield Action(action_name, in_args, out_args)

    def iter_event_vars(self):
        """ Yield an iterator over the services eventable variables.

        Yields a tuple of (variable name, data type)

        """

        # pylint: disable=invalid-name
        ns = '{urn:schemas-upnp-org:service-1-0}'
        scpd_body = requests.get(self.base_url + self.scpd_url).text
        tree = XML.fromstring(scpd_body.encode('utf-8'))
        # parse the state variables to get the relevant variable types
        statevars = tree.iterfind('.//{}stateVariable'.format(ns))
        for state in statevars:
            # We are only interested if 'sendEvents' is 'yes', i.e this
            # is an eventable variable
            if state.attrib['sendEvents'] == "yes":
                name = state.findtext('{}name'.format(ns))
                vartype = state.findtext('{}dataType'.format(ns))
                yield (name, vartype)


class AlarmClock(Service):
    """ Sonos alarm service, for setting and getting time and alarms. """
    def __init__(self, soco):
        super(AlarmClock, self).__init__(soco)


class MusicServices(Service):
    """ Sonos music services service, for functions related to 3rd party
    music services. """
    def __init__(self, soco):
        super(MusicServices, self).__init__(soco)


class DeviceProperties(Service):
    """ Sonos device properties service, for functions relating to zones,
    LED state, stereo pairs etc. """
    def __init__(self, soco):
        super(DeviceProperties, self).__init__(soco)


class SystemProperties(Service):
    """ Sonos system properties service, for functions relating to
    authentication etc """
    def __init__(self, soco):
        super(SystemProperties, self).__init__(soco)


class ZoneGroupTopology(Service):
    """ Sonos zone group topology service, for functions relating to network
    topology, diagnostics and updates. """
    def __init__(self, soco):
        super(ZoneGroupTopology, self).__init__(soco)

    def GetZoneGroupState(self, *args, **kwargs):
        """ Overrides default handling to use the global shared zone group
        state cache, unless another cache is speciified """
        kwargs['cache'] = kwargs.get('cache', zone_group_state_shared_cache)
        return self.send_command('GetZoneGroupState', *args, **kwargs)


class GroupManagement(Service):
    """ Sonos group management service, for services relating to groups. """
    def __init__(self, soco):
        super(GroupManagement, self).__init__(soco)


class QPlay(Service):
    """ Sonos Tencent QPlay service (a Chinese music service) """
    def __init__(self, soco):
        super(QPlay, self).__init__(soco)


class ContentDirectory(Service):
    """ UPnP standard Content Directory service, for functions relating to
    browsing, searching and listing available music. """
    def __init__(self, soco):
        super(ContentDirectory, self).__init__(soco)
        self.control_url = "/MediaServer/ContentDirectory/Control"
        self.event_subscription_url = "/MediaServer/ContentDirectory/Event"
        # For error codes, see table 2.7.16 in
        # http://upnp.org/specs/av/UPnP-av-ContentDirectory-v1-Service.pdf
        self.UPNP_ERRORS.update({
            701: 'No such object',
            702: 'Invalid CurrentTagValue',
            703: 'Invalid NewTagValue',
            704: 'Required tag',
            705: 'Read only tag',
            706: 'Parameter Mismatch',
            708: 'Unsupported or invalid search criteria',
            709: 'Unsupported or invalid sort criteria',
            710: 'No such container',
            711: 'Restricted object',
            712: 'Bad metadata',
            713: 'Restricted parent object',
            714: 'No such source resource',
            715: 'Resource access denied',
            716: 'Transfer busy',
            717: 'No such file transfer',
            718: 'No such destination resource',
            719: 'Destination resource access denied',
            720: 'Cannot process the request',
        })


class MS_ConnectionManager(Service):  # pylint: disable=invalid-name
    """ UPnP standard connection manager service for the media server."""
    def __init__(self, soco):
        super(MS_ConnectionManager, self).__init__(soco)
        self.service_type = "ConnectionManager"
        self.control_url = "/MediaServer/ConnectionManager/Control"
        self.event_subscription_url = "/MediaServer/ConnectionManager/Event"


class RenderingControl(Service):
    """ UPnP standard redering control service, for functions relating to
    playback rendering, eg bass, treble, volume and EQ. """
    def __init__(self, soco):
        super(RenderingControl, self).__init__(soco)
        self.control_url = "/MediaRenderer/RenderingControl/Control"
        self.event_subscription_url = "/MediaRenderer/RenderingControl/Event"


class MR_ConnectionManager(Service):  # pylint: disable=invalid-name
    """ UPnP standard connection manager service for the media renderer."""
    def __init__(self, soco):
        super(MR_ConnectionManager, self).__init__(soco)
        self.service_type = "ConnectionManager"
        self.control_url = "/MediaRenderer/ConnectionManager/Control"
        self.event_subscription_url = "/MediaRenderer/ConnectionManager/Event"


class AVTransport(Service):
    """ UPnP standard AV Transport service, for functions relating to
    transport management, eg play, stop, seek, playlists etc. """
    def __init__(self, soco):
        super(AVTransport, self).__init__(soco)
        self.control_url = "/MediaRenderer/AVTransport/Control"
        self.event_subscription_url = "/MediaRenderer/AVTransport/Event"
        # For error codes, see
        # http://upnp.org/specs/av/UPnP-av-AVTransport-v1-Service.pdf
        self.UPNP_ERRORS.update({
            701: 'Transition not available',
            702: 'No contents',
            703: 'Read error',
            704: 'Format not supported for playback',
            705: 'Transport is locked',
            706: 'Write error',
            707: 'Media is protected or not writeable',
            708: 'Format not supported for recording',
            709: 'Media is full',
            710: 'Seek mode not supported',
            711: 'Illegal seek target',
            712: 'Play mode not supported',
            713: 'Record quality not supported',
            714: 'Illegal MIME-Type',
            715: 'Content "BUSY"',
            716: 'Resource Not found',
            717: 'Play speed not supported',
            718: 'Invalid InstanceID',
            737: 'No DNS Server',
            738: 'Bad Domain Name',
            739: 'Server Error',
            })


class Queue(Service):
    """ Sonos queue service, for functions relating to queue management, saving
    queues etc. """
    def __init__(self, soco):
        super(Queue, self).__init__(soco)
        self.control_url = "/MediaRenderer/Queue/Control"
        self.event_subscription_url = "/MediaRenderer/Queue/Event"


class GroupRenderingControl(Service):
    """ Sonos group rendering control service, for functions relating to
    group volume etc. """
    def __init__(self, soco):
        super(GroupRenderingControl, self).__init__(soco)
        self.control_url = "/MediaRenderer/GroupRenderingControl/Control"
        self.event_subscription_url = \
            "/MediaRenderer/GroupRenderingControl/Event"

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

""" Provides general utility functions to be used across modules """

from __future__ import unicode_literals, absolute_import

import re
import threading
from time import time
from .compat import StringType, UnicodeType, dumps


def really_unicode(in_string):
    """
    Ensures s is returned as a unicode string and not just a string through
    a series of progressively relaxed decodings

    """
    if type(in_string) is StringType:
        for args in (('utf-8',), ('latin-1',), ('ascii', 'replace')):
            try:
                # pylint: disable=star-args
                in_string = in_string.decode(*args)
                break
            except UnicodeDecodeError:
                continue
    if type(in_string) is not UnicodeType:
        raise ValueError('%s is not a string at all.' % in_string)
    return in_string


def really_utf8(in_string):
    """ First decodes s via really_unicode to ensure it can successfully be
    encoded as utf-8 This is required since just calling encode on a string
    will often cause python to perform a coerced strict auto-decode as ascii
    first and will result in a UnicodeDecodeError being raised After
    really_unicode returns a safe unicode string, encode as 'utf-8' and return
    the utf-8 encoded string.

    """
    return really_unicode(in_string).encode('utf-8')


FIRST_CAP_RE = re.compile('(.)([A-Z][a-z]+)')
ALL_CAP_RE = re.compile('([a-z0-9])([A-Z])')


def camel_to_underscore(string):
    """ Convert camelcase to lowercase and underscore
    Recipy from http://stackoverflow.com/a/1176023
    """
    string = FIRST_CAP_RE.sub(r'\1_\2', string)
    return ALL_CAP_RE.sub(r'\1_\2', string).lower()


def prettify(unicode_text):
    """Return a pretty-printed version of a unicode XML string. Useful for
    debugging.

    """
    import xml.dom.minidom
    reparsed = xml.dom.minidom.parseString(unicode_text.encode('utf-8'))
    return reparsed.toprettyxml(indent="  ", newl="\n")


class TimedCache(object):

    """ A simple thread-safe cache for caching method return values

    At present, the cache can theoretically grow and grow, since entries are
    not automatically purged, though in practice this is unlikely since there
    are not that many different combinations of arguments in the places where
    it is used in SoCo, so not that many different cache entries will be
    created. If this becomes a problem, use a thread and timer to purge the
    cache, or rewrite this to use LRU logic!

    """

    def __init__(self, default_timeout=0):
        super(TimedCache, self).__init__()
        self._cache = {}
        # A thread lock for the cache
        self._cache_lock = threading.Lock()
        #: The default caching interval in seconds. Set to 0
        #: to disable the cache by default
        self.default_timeout = default_timeout

    @staticmethod
    def make_key(args, kwargs):
        """
        Generate a unique, hashable, representation of the args and kwargs

        """
        # This is not entirely straightforward, since args and kwargs may
        # contain mutable items and unicode. Possibiities include using
        # __repr__, frozensets, and code from Py3's LRU cache. But pickle
        # works, and although it is not as fast as some methods, it is good
        # enough at the moment
        cache_key = dumps((args, kwargs))
        return cache_key

    def get(self, *args, **kwargs):

        """

        Get an item from the cache for this combination of args and kwargs.

        Return None if no unexpired item is found. This means that there is no
        point storing an item in the cache if it is None.

        """
        # Look in the cache to see if there is an unexpired item. If there is
        # we can just return the cached result.
        cache_key = self.make_key(args, kwargs)
        # Lock and load
        with self._cache_lock:
            if cache_key in self._cache:
                expirytime, item = self._cache[cache_key]

                if expirytime >= time():
                    return item
                else:
                    # An expired item is present - delete it
                    del self._cache[cache_key]
        # Nothing found
        return None

    def put(self, item, *args, **kwargs):

        """ Put an item into the cache, for this combination of args and
        kwargs.

        If `timeout` is specified as one of the keyword arguments, the item
        will remain available for retrieval for `timeout` seconds. If `timeout`
        is None or not specified, the default cache timeout for this cache will
        be used. Specify a `timeout` of 0 (or ensure that the default timeout
        for this cache is 0) if this item is not to be cached."""

        # Check for a timeout keyword, store and remove it.
        timeout = kwargs.pop('timeout', None)
        if timeout is None:
            timeout = self.default_timeout
        cache_key = self.make_key(args, kwargs)
        # Store the item, along with the time at which it will expire
        with self._cache_lock:
            self._cache[cache_key] = (time() + timeout, item)

    def delete(self, *args, **kwargs):
        """Delete an item from the cache for this combination of args and
        kwargs"""
        cache_key = self.make_key(args, kwargs)
        with self._cache_lock:
            try:
                del self._cache[cache_key]
            except KeyError:
                pass

    def clear(self):
        """Empty the whole cache"""
        with self._cache_lock:
            self._cache.clear()

########NEW FILE########
__FILENAME__ = xml

""" Module that contains XML related utility functions """

# pylint: disable=unused-import

from __future__ import absolute_import

try:
    import xml.etree.cElementTree as XML  # nopep8
except ImportError:
    import xml.etree.ElementTree as XML  # nopep8

########NEW FILE########
__FILENAME__ = conftest
""" py.test hooks

Add the --ip command line option, and skip all tests marked the with
'integration' marker unless the option is included

"""
import pytest


def pytest_addoption(parser):
    """ Add the --ip commandline option """
    parser.addoption(
        '--ip',
        type=str,
        default=None,
        action='store',
        dest='IP',
        help='the IP address for the zone to be used for the integration tests'
        )


def pytest_runtest_setup(item):
    """ Skip tests marked 'integration' unless an ip address is given """
    if "integration" in item.keywords and not item.config.getoption("--ip"):
        pytest.skip("use --ip and an ip address to run integration tests.")

########NEW FILE########
__FILENAME__ = execute_unittests
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable-msg=W0142

""" This file is a executable script that executes unit tests for different
parts of soco and provide statistics on the unit test coverage.

Exit codes are as follows:
0  Succesful execution
1  Unknown unit test module requested
2  Missing information argument for the unit tests
3  Unit test module init method raised an exception
"""

import re
import sys
import inspect
import argparse
import unittest
# Our own imports
import soco
import soco_unittest
from soco_unittest import SoCoUnitTestInitError

TERMINAL_COLORS = {'yellow': '1;33',
                   'green': '0;32',
                   'light red': '1;31',
                   'light green': '1;32',
                   'white': '1;37',
                   'red': '0;31'
                   }


def __get_ips_and_names():
    """ Return a list of zone ips and names """
    discovery = soco.SonosDiscovery()
    ips = discovery.get_speaker_ips()
    names = [soco.SoCo(ip).get_speaker_info()['zone_name'] for ip in ips]
    return zip(ips, names)


def __build_option_parser():
    """ Build the option parser for this script """
    description = ('Unit tests for SoCo.\n\nIn order to be able to control '
        'which zone the unit tests are\nperformed on, an IP address must be '
        'provided. For a list of all\npossible IP adresses use the --list '
        'argument.\n\nExamples: python soco_unittest.py --ip 192.168.0.110\n'
        '          python soco_unittest.py --list')
    parser = argparse.ArgumentParser(description=description,
                            formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--ip', type=str, default=None, help='the IP address '
                        'for the zone to be used for the unit tests')
    parser.add_argument('--modules', type=str, default=None, help='the '
                        'modules to run unit test for, can be \'soco\' or '
                        '\'all\'')
    parser.add_argument('--list', action='store_const', const=True,
                        dest='zone_list', help='lists all the available zones'
                        ' and their IP addresses')
    parser.add_argument('--coverage', action='store_const', const=True,
                        help='unit test coverage statistics')
    parser.add_argument('--wiki-format', action='store_const', const=True,
                        help='print coverage in wiki format')
    parser.add_argument('--color', action='store_const', const=True,
                        help='print coverage information in color')
    parser.add_argument('--verbose', type=int, default=1, help='Verbosity '
                        'level for the unit tests (1 or 2). 1 is default.')
    return parser


def __get_modules_to_run(args, unittest_modules):
    """ Form the list of unit test modules to run depending on the commandline
    input
    """
    modules_to_run = []
    if args.modules == 'all' or args.modules is None:
        modules_to_run = unittest_modules.values()
    else:
        for name in args.modules.split(','):
            try:
                modules_to_run.append(unittest_modules[name])
            except KeyError:
                sys.stdout.write('Unit test module "{0}" is not present in '
                    'the unit test definitions. Exiting!\n'.format(name))
                sys.exit(1)
    return modules_to_run


def __coverages(modules_to_run, args):
    """ Outputs coverage statistics """
    sys.stdout.write('\n')
    for current in modules_to_run:
        string = 'Coverage for module: {0}\n\n'.format(current['name'])
        sys.stdout.write(colorize(string, args.color, 'white'))

        # Get all the methods in the class to be tested
        methods = __get_methods_in_class(current['class'])
        # Get all the unittest classes
        classes = {}
        for name, obj in inspect.getmembers(current['unittest_module'],
                                            predicate=inspect.isclass):
            if issubclass(obj, unittest.TestCase):
                classes[name.lower()] = name

        # Print out stats for methods in the class
        if args.wiki_format:
            sys.stdout.write('Method'.ljust(28, ' ') + '| Status\n')
            sys.stdout.write('-' * 27 + ' | ------\n')
        for method in methods.keys():
            __print_coverage_line(methods, method, classes, args)

        # Check is there are unused tests in the unit test module
        for class_ in list(set(classes.keys()) - set(methods.keys())):
            print('WARNING: The unit test {0} is no longer used'\
                .format(classes[class_]))

        percentage = float(len(classes)) / len(methods) * 100
        string = '\n{0:.1f}% methods covered\n'.format(percentage)
        for number, color_ in zip([0, 50, 99],
                                  ['light red', 'yellow', 'light green']):
            if percentage > number:
                color = color_
        sys.stdout.write(colorize(string, args.color, color))


def __get_methods_in_class(class_):
    """ Gets all the names of all the methods in a class """
    methods = {}
    for name, _ in inspect.getmembers(
            class_,
            predicate=inspect.ismethod
            ):
        if name != '__init__':
            # Replaces _ and the class name
            without_classname = re.sub('^_{0}'.format(class_.__name__), '',
                name)
            # Replaces 1 or 2 _ at the beginning of the line with the word
            # 'private'
            with_replacement = re.sub(r'^_{1,2}', 'private', without_classname)
            # Strips all remaining _
            with_replacement = with_replacement.replace('_', '')
            methods[with_replacement] = without_classname
    return methods


def __print_coverage_line(methods, method, classes, args):
    """ Prints out a single line of coverage information """
    if args.wiki_format:
        padding = ' '
        output_string = '{0}|{1}\n'
    else:
        padding = '.'
        output_string = '{0}{1}\n'
    string = methods[method].ljust(28, padding)
    if method in classes.keys():
        outcome = colorize(' COVERED', args.color, 'green')
        sys.stdout.write(output_string.format(string, outcome))
    else:
        outcome = colorize(' NOT COVERED', args.color, 'red')
        sys.stdout.write(output_string.format(string, outcome))


def colorize(string, use_colors=False, color=None):
    """ Colorizes the output"""
    if not use_colors or color is None:
        return string
    tokens = []
    for line in string.split('\n'):
        if len(line) > 0:
            line = '\x1b[{0}m{1}\x1b[0m'.format(TERMINAL_COLORS[color], line)
        tokens.append(line)
    return '\n'.join(tokens)


def __check_argument_present(current):
    """ Check if all the necessary information for this module is present """
    for arg_key, arg_val in current['arguments'].items():
        if arg_val is None:
            sys.stdout.write('Unit tests for the module {0} require '
                'the "{1}" command line argument. Exiting!\n'.format(
                current['name'], arg_key))
            sys.exit(2)


### MAIN SCRIPT
# Parse arguments
PARSER = __build_option_parser()
ARGS = PARSER.parse_args()

# Unit test group definitions
UNITTEST_MODULES = {'soco': {'name': 'SoCo',
                             'unittest_module': soco_unittest,
                             'class': soco.SoCo,
                             'arguments': {'ip': ARGS.ip}
                             }
                    }
MODULES_TO_RUN = __get_modules_to_run(ARGS, UNITTEST_MODULES)

# Switch execution depending on command line input
if ARGS.zone_list:
    # Print out a list of available zones
    PATTERN = '{0: <18}{1}\n'
    NAMES_AND_IPS = __get_ips_and_names()
    sys.stdout.write(PATTERN.format('IP', 'Name'))
    sys.stdout.write('{0}\n'.format('-' * 30))
    for items in NAMES_AND_IPS:
        sys.stdout.write(PATTERN.format(items[0], items[1]))
elif ARGS.coverage:
    # Print out the test coverage for the selected modules
    __coverages(MODULES_TO_RUN, ARGS)
else:
    sys.stdout.write('\n')
    for CURRENT in MODULES_TO_RUN:
        string_ = 'Running unit tests for module: {0}\n'\
                  '\n'.format(CURRENT['name'])
        sys.stdout.write(colorize(string_, ARGS.color, 'white'))

        # Check if all the necessary information for this module is present
        __check_argument_present(CURRENT)

        # Run the unit tests
        MODULE = CURRENT['unittest_module']
        if hasattr(MODULE, 'init'):
            try:
                MODULE.init(**CURRENT['arguments'])
            except SoCoUnitTestInitError as exception:
                string_ = 'The init method in the unit test module returned '\
                    'the following error:\n{0}\n'.format(str(exception))
                sys.stdout.write(colorize(string_, ARGS.color, 'light red'))
                sys.stdout.write('Exiting!\n')
                sys.exit(3)
        SUITE = unittest.TestLoader().loadTestsFromModule(MODULE)
        unittest.TextTestRunner(verbosity=ARGS.verbose).run(SUITE)

########NEW FILE########
__FILENAME__ = soco_unittest
# -*- coding: utf-8 -*-
# pylint: disable-msg=R0904

""" This file contains the classes used to perform unit tests on the methods
in the SoCo class.

PLEASE TAKE NOTE: All of these unit tests are designed to run on a sonos
system without interfering with normal service. This means that they will not
raise the volume or leave the player in another state than it started in. They
have been made this way, since sonos is developed by volounteers, that in all
likelyhood does not have a dedicated test system, so the tests must be able to
run on an ordinary system without annoying the neighboors and it should return
to its original state because those same developers will likely want to listen
to music while coding, without having it interrupted at every unit test.
PLEASE RESPECT THIS.
"""
from __future__ import unicode_literals

import unittest
import time
import pytest
import soco

SOCO = None
pytestmark = pytest.mark.integration

class SoCoUnitTestInitError(Exception):
    """ Exception for incomplete unit test initialization """
    def __init__(self, message):
        Exception.__init__(self, message)


def init(**kwargs):
    """ Initialize variables for the unittests that are only known at run time
    """
    global SOCO  # pylint: disable-msg=W0603
    SOCO = soco.SoCo(kwargs['ip'])

    if len(SOCO.get_queue()) == 0:
        raise SoCoUnitTestInitError('Unit tests on the SoCo class must be run '
                                    'with at least 1 item in the playlist')

    transport_info = SOCO.get_current_transport_info()
    if transport_info['current_transport_state'] != 'PLAYING':
        raise SoCoUnitTestInitError('Unit tests on the SoCo class must be run '
                                    'with the sonos unit playing')


def get_state():
    """ Utility function to get the entire playing state before the unit tests
    starts to change it
    """
    state = {'queue': SOCO.get_queue(0, 1000),
             'current_track_info': SOCO.get_current_track_info()}
    return state


def set_state(state):
    """ Utility function to set the entire state. Used to reset the unit after
    the unit tests have changed it
    """
    SOCO.stop()
    SOCO.clear_queue()
    for track in state['queue']:
        SOCO.add_to_queue(track['uri'])
    SOCO.play_from_queue(
        int(state['current_track_info']['playlist_position']) - 1)
    SOCO.seek(state['current_track_info']['position'])
    SOCO.play()


def wait(interval=0.1):
    """ Convinience function to adjust sleep interval for all tests """
    time.sleep(interval)


# Test return strings that are used a lot
NOT_TRUE = 'The method did not return True'
NOT_EXP = 'The method did not return the expected value'
NOT_TYPE = 'The return value of the method did not have the expected type: {0}'
NOT_IN_RANGE = 'The returned value is not in the expected range'


# functions for running via pytest
def setup_module(module):
    ip = pytest.config.option.IP
    if ip is None:
        pytest.fail("No ip address specified. Use the --ip option.")
    init(ip=ip)
    state = get_state()
    module.state = state

def teardown_module(module):
    state = module.state
    set_state(state)



class Volume(unittest.TestCase):
    """ Unit tests for the volume method """

    def setUp(self):  # pylint: disable-msg=C0103
        self.valid_values = range(101)

    def test_get_and_set(self):
        """ Tests if the set functionlity works when given valid arguments """
        old = SOCO.volume
        self.assertIn(old, self.valid_values, NOT_IN_RANGE)
        if old == self.valid_values[0]:
            new = old + 1
        else:
            new = old - 1
        SOCO.volume = new
        wait()
        self.assertEqual(SOCO.volume, new, NOT_EXP)
        SOCO.volume = old
        wait()

    def test_invalid_arguments(self):
        """ Tests if the set functionality coerces into range when given
        integers outside of allowed range
        """
        old = SOCO.volume
        # NOTE We don't test coerce from too large values, since that would
        # put the unit at full volume
        SOCO.volume = self.valid_values[0] - 1
        wait()
        self.assertEqual(SOCO.volume, 0, NOT_EXP)
        SOCO.volume = old
        wait()

    def test_set_0(self):
        """ Tests whether the volume can be set to 0. Regression test for:
        https://github.com/rahims/SoCo/issues/29
        """
        old = SOCO.volume
        SOCO.volume = 0
        wait()
        self.assertEqual(SOCO.volume, 0, NOT_EXP)
        SOCO.volume = old
        wait()


class Bass(unittest.TestCase):
    """ Unit tests for the bass method. This class implements a full boundary
    value test.
    """

    def setUp(self):  # pylint: disable-msg=C0103
        self.valid_values = range(-10, 11)

    def test_get_and_set(self):
        """ Tests if the set functionlity works when given valid arguments """
        old = SOCO.bass
        self.assertIn(old, self.valid_values, NOT_IN_RANGE)
        # Values on the boundaries of the valid equivalence partition
        for value in [self.valid_values[0], self.valid_values[-1]]:
            SOCO.bass = value
            wait()
            self.assertEqual(SOCO.bass, value, NOT_EXP)
        SOCO.bass = old
        wait()

    def test_invalid_arguments(self):
        """ Tests if the set functionality produces the expected "coerce in
        range" functionality when given a value outside of its range
        """
        old = SOCO.bass
        # Values on the boundaries of the two invalid equivalence partitions
        SOCO.bass = self.valid_values[0] - 1
        wait()
        self.assertEqual(SOCO.bass, self.valid_values[0], NOT_EXP)
        SOCO.bass = self.valid_values[-1] + 1
        wait()
        self.assertEqual(SOCO.bass, self.valid_values[-1], NOT_EXP)
        SOCO.bass = old
        wait()


class Treble(unittest.TestCase):
    """ Unit tests for the treble method This class implements a full boundary
    value test.
    """

    def setUp(self):  # pylint: disable-msg=C0103
        self.valid_values = range(-10, 11)

    def test_get_and_set(self):
        """ Tests if the set functionlity works when given valid arguments """
        old = SOCO.treble
        self.assertIn(old, self.valid_values, NOT_IN_RANGE)
        # Values on the boundaries of the valid equivalence partition
        for value in [self.valid_values[0], self.valid_values[-1]]:
            SOCO.treble = value
            wait()
            self.assertEqual(SOCO.treble, value, NOT_EXP)
        SOCO.treble = old
        wait()

    def test_invalid_arguments(self):
        """ Tests if the set functionality produces the expected "coerce in
        range" functionality when given a value outside its range
        """
        old = SOCO.treble
        # Values on the boundaries of the two invalid equivalence partitions
        SOCO.treble = self.valid_values[0] - 1
        wait()
        self.assertEqual(SOCO.treble, self.valid_values[0], NOT_EXP)
        SOCO.treble = self.valid_values[-1] + 1
        wait()
        self.assertEqual(SOCO.treble, self.valid_values[-1], NOT_EXP)
        SOCO.treble = old
        wait()


class GetCurrentTrackInfo(unittest.TestCase):
    """ Unit test for the get_current_track_info method """

    def setUp(self):  # pylint: disable-msg=C0103
        # The value in this list must be kept up to date with the values in
        # the test_get doc string
        self.info_keys = sorted(['album', 'artist', 'title', 'uri',
                                 'playlist_position', 'duration', 'album_art',
                                 'position'])

    def test_get(self):
        """ Test is the return value is a dictinary and contains the following
        keys: album, artist, title, uri, playlist_position, duration,
        album_art and position
        """
        info = SOCO.get_current_track_info()
        self.assertIsInstance(info, dict, 'Returned info is not a dict')
        self.assertEqual(sorted(info.keys()), self.info_keys,
                         'Info does not contain the proper keys')


class AddToQueue(unittest.TestCase):
    """ Unit test for the add_to_queue method """

    def test(self):
        """ Gets the current queue, adds the last item of the current queue
        and then compares the length of the old queue with the new and
        checks that the last two elements are identical
        """
        state = get_state()
        SOCO.pause()
        old_queue = SOCO.get_queue(0, 1000)
        # Add new element and check
        self.assertEqual(SOCO.add_to_queue(old_queue[-1]['uri']),
                         len(old_queue) + 1, '')
        wait()
        new_queue = SOCO.get_queue()
        self.assertEqual(len(new_queue) - 1, len(old_queue))
        self.assertEqual(new_queue[-1], new_queue[-2])
        # Clean up
        set_state(state)
        wait()


class GetQueue(unittest.TestCase):
    """ Unit test for the get_queue method """

    def setUp(self):  # pylint: disable-msg=C0103
        # The values in this list must be kept up to date with the values in
        # the test_get doc string
        self.qeueu_element_keys = sorted(['album', 'artist', 'uri',
                                          'album_art', 'title'])

    def test_get(self):
        """ Tests is return value is a list of dictionaries and if each of
        the dictionaries contain the keys: album, artist, uri, album_art and
        title
        """
        queue = SOCO.get_queue()
        self.assertIsInstance(queue, list, NOT_TYPE.format('list'))
        for item in queue:
            self.assertIsInstance(item, dict,
                                  'Item in queue is not a dictionary')
            self.assertEqual(sorted(item.keys()), self.qeueu_element_keys,
                             'The keys in the queue element dict are not the '
                             'expected ones: {0}'.
                             format(self.qeueu_element_keys))


class GetCurrentTransportInfo(unittest.TestCase):
    """ Unit test for the get_current_transport_info method """

    def setUp(self):  # pylint: disable-msg=C0103
        # The values in this list must be kept up to date with the values in
        # the test doc string
        self.transport_info_keys = sorted(['current_transport_status',
                                           'current_transport_state',
                                           'current_transport_speed'])

    def test(self):
        """ Tests if the return value is a dictionary that contains the keys:
        current_transport_status, current_transport_state,
        current_transport_speed
        and that values have been found for all keys, i.e. they are not None
        """
        transport_info = SOCO.get_current_transport_info()
        self.assertIsInstance(transport_info, dict, NOT_TYPE.format('dict'))
        self.assertEqual(self.transport_info_keys,
                         sorted(transport_info.keys()),
                         'The keys in the speaker info dict are not the '
                         'expected ones: {0}'.format(self.transport_info_keys))
        for key, value in transport_info.items():
            self.assertIsNotNone(value, 'The value for the key "{0}" is None '
                                 'which indicate that no value was found for '
                                 'it'.format(key))


class GetSpeakerInfo(unittest.TestCase):
    """ Unit test for the get_speaker_info method """

    def setUp(self):  # pylint: disable-msg=C0103
        # The values in this list must be kept up to date with the values in
        # the test doc string
        self.info_keys = sorted(['zone_name', 'zone_icon', 'uid',
                                 'serial_number', 'software_version',
                                 'hardware_version', 'mac_address'])

    def test(self):
        """ Tests if the return value is a dictionary that contains the keys:
        zone_name, zone_icon, uid, serial_number, software_version,
        hardware_version, mac_address
        and that values have been found for all keys, i.e. they are not None
        """
        speaker_info = SOCO.get_speaker_info()
        self.assertIsInstance(speaker_info, dict, NOT_TYPE.format('dict'))
        self.assertEqual(self.info_keys, sorted(speaker_info.keys()), 'The '
                         'keys in speaker info are not the expected ones: {0}'
                         ''.format(self.info_keys))
        for key, value in speaker_info.items():
            self.assertIsNotNone(value, 'The value for the key "{0}" is None '
                                 'which indicate that no value was found for '
                                 'it'.format(key))


#class GetSpeakersIp(unittest.TestCase):
    #""" Unit tests for the get_speakers_ip method """

    ## TODO: Awaits https://github.com/rahims/SoCo/issues/26

    #def test(self):
        #print SOCO.get_speakers_ip()


class Pause(unittest.TestCase):
    """ Unittest for the pause method """

    def test(self):
        """ Tests if the pause method works """
        SOCO.pause()
        wait(1)
        new = SOCO.get_current_transport_info()['current_transport_state']
        self.assertEqual(new, 'PAUSED_PLAYBACK', 'State after pause is not '
                         '"PAUSED_PLAYBACK"')
        SOCO.play()
        wait(1)


class Stop(unittest.TestCase):
    """ Unittest for the stop method """

    def test(self):
        """ Tests if the stop method works """
        state = get_state()
        SOCO.stop()
        wait(1)
        new = SOCO.get_current_transport_info()['current_transport_state']
        self.assertEqual(new, 'STOPPED', 'State after stop is not "STOPPED"')
        set_state(state)  # Reset unit the way it was before the test
        wait(1)


class Play(unittest.TestCase):
    """ Unit test for the play method """

    def test(self):
        """ Tests if the play method works """
        SOCO.pause()
        wait(1)
        on_pause = SOCO.get_current_transport_info()['current_transport_state']
        self.assertEqual(on_pause, 'PAUSED_PLAYBACK', 'State after pause is '
                         'not "PAUSED_PLAYBACK"')
        SOCO.play()
        wait(1)
        on_play = SOCO.get_current_transport_info()['current_transport_state']
        self.assertEqual(on_play, 'PLAYING', 'State after play is not '
                         '"PAUSED_PLAYBACK"')


class Mute(unittest.TestCase):
    """ Unit test for the mute method """

    def test(self):
        """ Tests of the mute method works """
        old = SOCO.mute
        self.assertEqual(old, 0, 'The unit should not be muted when running '
                         'the unit tests')
        SOCO.mute = True
        wait()
        new = SOCO.mute
        self.assertEqual(new, 1, 'The unit did not succesfully mute')
        SOCO.mute = False
        wait()


class RemoveFromQueue(unittest.TestCase):
    """ Unit test for the remove_from_queue method """

    def test(self):
        """ Tests if the remove_from_queue method works """
        old_queue = SOCO.get_queue()
        track_to_remove = old_queue[-1]
        SOCO.remove_from_queue(len(old_queue))
        wait()
        new_queue = SOCO.get_queue()
        self.assertNotEqual(old_queue, new_queue, 'No difference between '
                            'queues before and after removing the last item')
        self.assertEqual(len(new_queue), len(old_queue) - 1, 'The length of '
                         'queue after removing a track is not lenght before - '
                         '1')
        # Clean up
        SOCO.add_to_queue(track_to_remove['uri'])
        wait()
        self.assertEqual(old_queue, SOCO.get_queue(), 'Clean up unsuccessful')


class Seek(unittest.TestCase):
    """ Unit test for the seek method """

    def test_valid(self):
        """ Tests if the seek method works with valid input """
        original_position = SOCO.get_current_track_info()['position']
        # Format 1
        SOCO.seek('0:00:00')
        wait()
        position = SOCO.get_current_track_info()['position']
        self.assertIn(position, ['0:00:00', '0:00:01'])
        # Reset and format 2
        SOCO.seek(original_position)
        SOCO.seek('00:00:00')
        wait()
        position = SOCO.get_current_track_info()['position']
        self.assertIn(position, ['0:00:00', '0:00:01'])
        # Clean up
        SOCO.seek(original_position)
        wait()

    def test_invald(self):
        """ Tests if the seek method properly fails with invalid input """
        for string in ['invalid_time_string', '5:12', '6', 'aa:aa:aa']:
            with self.assertRaises(ValueError):
                SOCO.seek(string)

########NEW FILE########
__FILENAME__ = test_data_structures
# -*- coding: utf-8 -*-
# pylint: disable=R0913,W0142

"""Module to test the data structure classes with pytest"""

from __future__ import unicode_literals
try:
    import xml.etree.cElementTree as XML
except ImportError:
    import xml.etree.ElementTree as XML
import textwrap

from soco import data_structures

TITLE = 'Dummy title with non ascii chars æøå'
ALBUM = '«Album title with fancy characters»'
ART_URI = 'http://fake_address.jpg'
CREATOR = 'Creative Ŋ Ħ̛ Þ dummy'
XML_TEMPLATE = """
    <DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"
     xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">
    <item id="{item_id}" parentID="{parent_id}"
     restricted="true">
    <dc:title>{title}</dc:title>
    <upnp:class>{item_class}</upnp:class>
    <desc id="cdudn"
     nameSpace="urn:schemas-rinconnetworks-com:metadata-1-0/">
    RINCON_AssociatedZPUDN</desc></item></DIDL-Lite>
    """
XML_TEMPLATE = textwrap.dedent(XML_TEMPLATE).replace('\n', '').strip()

# Example XML and the content dict to compare with
TRACK_XML = """
<item xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"
 id="S://TLE-SERVER/share/ogg/Mozart%20-%20Orpheus%20Orchestra_convert/
5-Mozart-...%20-II%20Adagio.ogg" parentID="A:TRACKS" restricted="true">
  <res protocolInfo="x-file-cifs:*:application/ogg:*">x-file-cifs://TLE-SERVER/
share/ogg/Mozart%20-%20Orpheus%20Orchestra_convert/5-Mozart-...%20-II%20
Adagio.ogg</res>
  <upnp:albumArtURI>/getaa?u=x-file-cifs%3a%2f%2fTLE-SERVER
%2fshare%2fogg%2fMozart%2520-%2520Orpheus%2520Orchestra_convert%2f5-Mozart-
...%2520-II%2520Adagio.ogg&amp;v=2</upnp:albumArtURI>
  <dc:title>... - II  Adagio</dc:title>
  <upnp:class>object.item.audioItem.musicTrack</upnp:class>
  <dc:creator>Mozart</dc:creator>
  <upnp:album>Orpheus Orchestra</upnp:album>
  <upnp:originalTrackNumber>5</upnp:originalTrackNumber>
</item>"""
TRACK_DICT = {
    'album': 'Orpheus Orchestra',
    'creator': 'Mozart',
    'title': '... - II  Adagio',
    'uri': 'x-file-cifs://TLE-SERVER/\nshare/ogg/Mozart'
           '%20-%20Orpheus%20Orchestra_convert/5-Mozart-...%20-II%20'
           '\nAdagio.ogg',
    'album_art_uri': '/getaa?u=x-file-cifs%3a%2f%2fTLE-SERVER'
                     '\n%2fshare%2fogg%2fMozart%2520-%2520Orpheus%2520'
                     'Orchestra_convert%2f5-Mozart-\n...%2520-II%2520'
                     'Adagio.ogg&v=2',
    'item_class': 'object.item.audioItem.musicTrack',
    'original_track_number': 5}
ALBUM_XML = """
<container xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"
 id="A:ALBUM/...and%20Justice%20for%20All" parentID="A:ALBUM"
 restricted="true">
  <dc:title>...and Justice for All</dc:title>
  <upnp:class>object.container.album.musicAlbum</upnp:class>
  <res protocolInfo="x-rincon-playlist:*:*:*">x-rincon-playlist:
RINCON_000E5884455C01400#A:ALBUM/...and%20Justice%20for%20All</res>
  <dc:creator>Metallica</dc:creator>
  <upnp:albumArtURI>/getaa?u=x-file-cifs%3a%2f%2fTLE-SERVER%2fshare%2fogg%2f
Metallica%2520-%2520and%2520Justice%2520for%2520All%2f01%2520-%2520Blackened.
ogg&amp;v=2</upnp:albumArtURI>
</container>"""
ALBUM_XML = ALBUM_XML.replace('\n', '')
ALBUM_DICT = {
    'title': '...and Justice for All',
    'item_class': 'object.container.album.musicAlbum',
    'uri': 'x-rincon-playlist:RINCON_000E5884455C01400#A:ALBUM/...and%20'
           'Justice%20for%20All',
    'album_art_uri': '/getaa?u=x-file-cifs%3a%2f%2fTLE-SERVER%2fshare%2fogg'
                     '%2fMetallica%2520-%2520and%2520Justice%2520for%2520All'
                     '%2f01%2520-%2520Blackened.ogg&v=2',
    'creator': 'Metallica'}
ARTIST_XML = """
<container xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/" id="A:ARTIST/10%20Years"
 parentID="A:ARTIST" restricted="true">
  <dc:title>10 Years</dc:title>
  <upnp:class>object.container.person.musicArtist</upnp:class>
  <res protocolInfo="x-rincon-playlist:*:*:*">x-rincon-playlist:
RINCON_000E5884455C01400#A:ARTIST/10%20Years</res>
</container>"""
ARTIST_XML = ARTIST_XML.replace('\n', '')
ARTIST_DICT = {
    'item_class': 'object.container.person.musicArtist',
    'uri': 'x-rincon-playlist:RINCON_000E5884455C01400#A:ARTIST/10%20Years',
    'title': '10 Years'
}
ALBUMARTIST_XML = """
<container xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"
 id="A:ALBUMARTIST/3%20Doors%20Down" parentID="A:ALBUMARTIST"
 restricted="true">
  <dc:title>3 Doors Down</dc:title>
  <upnp:class>object.container.person.musicArtist</upnp:class>
  <res protocolInfo="x-rincon-playlist:*:*:*">x-rincon-playlist:RINCON_
000E5884455C01400#A:ALBUMARTIST/3%20Doors%20Down</res>
</container>"""
ALBUMARTIST_XML = ALBUMARTIST_XML.replace('\n', '')
ALBUMARTIST_DICT = {
    'item_class': 'object.container.person.musicArtist',
    'uri': 'x-rincon-playlist:RINCON_000E5884455C01400#A:ALBUMARTIST/'
           '3%20Doors%20Down',
    'title': '3 Doors Down'
}
GENRE_XML = """
<container xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/" id="A:GENRE/Acid"
 parentID="A:GENRE" restricted="true">
  <dc:title>Acid</dc:title>
  <upnp:class>object.container.genre.musicGenre</upnp:class>
  <res protocolInfo="x-rincon-playlist:*:*:*">x-rincon-playlist:
RINCON_000E5884455C01400#A:GENRE/Acid</res>
</container>"""
GENRE_XML = GENRE_XML.replace('\n', '')
GENRE_DICT = {
    'item_class': 'object.container.genre.musicGenre',
    'uri': 'x-rincon-playlist:RINCON_000E5884455C01400#A:GENRE/Acid',
    'title': 'Acid'
}
COMPOSER_XML = """
<container xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"
 id="A:COMPOSER/A.%20Kiedis%2fFlea%2fJ.%20Frusciante%2fC.%20Smith"
 parentID="A:COMPOSER" restricted="true">
  <dc:title>A. Kiedis/Flea/J. Frusciante/C. Smith</dc:title>
  <upnp:class>object.container.person.composer</upnp:class>
  <res protocolInfo="x-rincon-playlist:*:*:*">x-rincon-playlist:RINCON_
000E5884455C01400#A:COMPOSER/A.%20Kiedis%2fFlea%2fJ.%20Frusciante%2fC.%20
Smith</res>
</container>"""
COMPOSER_XML = COMPOSER_XML.replace('\n', '')
COMPOSER_DICT = {
    'item_class': 'object.container.person.composer',
    'uri': 'x-rincon-playlist:RINCON_000E5884455C01400#A:COMPOSER/'
           'A.%20Kiedis%2fFlea%2fJ.%20Frusciante%2fC.%20Smith',
    'title': 'A. Kiedis/Flea/J. Frusciante/C. Smith'
}
PLAYLIST_XML = """
<container xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"
 id="S://TLE-SERVER/share/mp3/Trentem%c3%b8ller%20-%20The%20
Trentem%c3%b8ller%20Chronicles/-%3dTrentem%c3%b8ller%20-%20The%20
Trentem%c3%b8ller%20Chronicles%20(CD%201).m3u" parentID="A:PLAYLISTS"
 restricted="true">
  <res protocolInfo="x-file-cifs:*:audio/mpegurl:*">x-file-cifs://TLE-SERVER/
share/mp3/Trentem%c3%b8ller%20-%20The%20Trentem%c3%b8ller%20Chronicles/
-%3dTrentem%c3%b8ller%20-%20The%20Trentem%c3%b8ller%20Chronicles%20(CD%201)
.m3u</res>
  <dc:title>-=Trentem&#248;ller - The Trentem&#248;ller Chronicles (CD 1).m3u
</dc:title>
  <upnp:class>object.container.playlistContainer</upnp:class>
</container>"""
PLAYLIST_XML = PLAYLIST_XML.replace('\n', '')
PLAYLIST_DICT = {
    'item_class': 'object.container.playlistContainer',
    'uri': 'x-file-cifs://TLE-SERVER/share/mp3/Trentem%c3%b8ller%20-%20The%20'
           'Trentem%c3%b8ller%20Chronicles/-%3dTrentem%c3%b8ller%20-%20The%20'
           'Trentem%c3%b8ller%20Chronicles%20(CD%201).m3u',
    'title': '-=Trentem\xf8ller - The Trentem\xf8ller Chronicles (CD 1).m3u'}
SONOS_PLAYLIST_XML = """
<container xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"
 id="file:///jffs/settings/savedqueues.rsq#13 title: Koop" parentID="SQ:"
 restricted="true">
  <res protocolInfo="x-file-cifs:*:audio/mpegurl:*">file:///jffs/settings/savedqueues.rsq#13 title: Koop</res>
  <dc:title>Koop</dc:title>
  <upnp:class>object.container.playlistContainer</upnp:class>
</container>"""
SONOS_PLAYLIST_XML = SONOS_PLAYLIST_XML.replace('\n', '')
SONOS_PLAYLIST_DICT = {
    'item_class': 'object.container.playlistContainer',
    'uri': 'file:///jffs/settings/savedqueues.rsq#13 title: Koop',
    'title': 'Koop'}
SHARE_XML = """
<container xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/" id="S://TLE-SERVER/share"
 parentID="S:" restricted="true">
  <dc:title>//TLE-SERVER/share</dc:title>
  <upnp:class>object.container</upnp:class>
  <res protocolInfo="x-rincon-playlist:*:*:*">x-rincon-playlist:RINCON_
000E5884455C01400#S://TLE-SERVER/share</res>
</container>"""
SHARE_XML = SHARE_XML.replace('\n', '')
SHARE_DICT = {
    'item_class': 'object.container',
    'uri': 'x-rincon-playlist:RINCON_000E5884455C01400#S://TLE-SERVER/share',
    'title': '//TLE-SERVER/share'
}
QUEUE_XML1 = """
<item xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/" id="Q:0/1" parentID="Q:0"
 restricted="true">
  <res duration="0:04:43" protocolInfo="sonos.com-mms:*:audio/x-ms-wma:*">
x-sonos-mms:AnyArtistTrack%3a126778459?sid=50&amp;flags=32</res>
  <upnp:albumArtURI>/getaa?s=1&amp;u=x-sonos-mms%3aAnyArtistTrack%253a126778459
%3fsid%3d50%26flags%3d32</upnp:albumArtURI>
  <dc:title>Airworthy</dc:title>
  <upnp:class>object.item.audioItem.musicTrack</upnp:class>
  <dc:creator>Randi Laubek</dc:creator>
  <upnp:album>Almost Gracefully</upnp:album>
</item>"""
QUEUE_XML1 = QUEUE_XML1.replace('\n', '')
QUEUE_DICT1 = {
    'album': 'Almost Gracefully',
    'creator': 'Randi Laubek',
    'title': 'Airworthy',
    'uri': 'x-sonos-mms:AnyArtistTrack%3a126778459?sid=50&flags=32',
    'album_art_uri': '/getaa?s=1&u=x-sonos-mms%3aAnyArtistTrack%253a126778459'
    '%3fsid%3d50%26flags%3d32',
    'item_class': 'object.item.audioItem.musicTrack',
    'original_track_number': None
}

QUEUE_XML2 = """
<item xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/" id="Q:0/2" parentID="Q:0"
 restricted="true">
  <res protocolInfo="x-file-cifs:*:audio/flac:*">x-file-cifs://TLE-SERVER/
share/flac/Agnes%20Obel%20-%20Philharmonics/1%20-%20Falling,%20Catching.flac
</res>
  <upnp:albumArtURI>/getaa?u=x-file-cifs%3a%2f%2fTLE-SERVER%2fshare%2fflac%2f
Agnes%2520Obel%2520-%2520Philharmonics%2f1%2520-%2520Falling,%2520
Catching.flac&amp;v=2</upnp:albumArtURI>
  <dc:title>Falling, Catching</dc:title>
  <upnp:class>object.item.audioItem.musicTrack</upnp:class>
  <dc:creator>Agnes Obel</dc:creator>
  <upnp:album>Philharmonics</upnp:album>
  <upnp:originalTrackNumber>1</upnp:originalTrackNumber>
</item>
"""
QUEUE_XML2 = QUEUE_XML2.replace('\n', '')
QUEUE_DICT2 = {
    'album': 'Philharmonics',
    'creator': 'Agnes Obel',
    'title': 'Falling, Catching',
    'uri': 'x-file-cifs://TLE-SERVER/share/flac/Agnes%20Obel%20-%20'
    'Philharmonics/1%20-%20Falling,%20Catching.flac',
    'album_art_uri': '/getaa?u=x-file-cifs%3a%2f%2fTLE-SERVER%2fshare%2fflac'
    '%2fAgnes%2520Obel%2520-%2520Philharmonics%2f1%2520-%2520Falling,'
    '%2520Catching.flac&v=2',
    'item_class': 'object.item.audioItem.musicTrack',
    'original_track_number': 1
}


# Helper test functions
def set_and_get_test(instance, content, key):
    """Test get and set of a single unicode attribute

    :param instance: The object to be tested
    :param content: The content dict that contains the test values
    :param key: The name of the attribute and key in content to test
    """
    # Test if the attribute has the correct value
    original = getattr(instance, key)
    assert original == content[key]
    # Test if the attribute value can be changed and return the new value
    setattr(instance, key, original + '!addition¡')
    assert getattr(instance, key) == original + '!addition¡'
    # Reset
    setattr(instance, key, original)


def common_tests(parent_id, item_id, instance, content, item_xml, item_dict):
    """Test all the common methods inherited from MusicLibraryItem

    :param parent_id: The parent ID of the class
    :param item_id: The expected item_id result for instance
    :param instance: The main object to be tested
    :param content: The content dict that corresponds to instance
    :param item_xml: A real XML example for from_xml
    :param item_dict: The content dict result corresponding to item_xml
    """
    # from_xml, this test uses real data examples
    instance2 = instance.__class__.from_xml(
        XML.fromstring(item_xml.encode('utf8')))
    assert instance2.to_dict == item_dict

    # from_dict and to_dict
    instance3 = instance.__class__.from_dict(content)
    assert instance3.to_dict == content

    # Test item_id
    assert instance.item_id == item_id

    # Test didl_metadata
    content1 = content.copy()
    content1.pop('title')
    title = 'Dummy title with non ascii chars &#230;&#248;&#229;'
    xml = XML_TEMPLATE.format(parent_id=parent_id, item_id=item_id,
                              title=title, **content1)
    assert XML.tostring(instance.didl_metadata).decode() == xml

    # Test common attributes
    for key in ['uri', 'title', 'item_class']:
        set_and_get_test(instance, content, key)

    # Test equals (should fail if we change any attribute)
    assert instance == instance3
    for key in content.keys():
        original = getattr(instance3, key)
        if key == 'original_track_number':
            setattr(instance3, key, original + 1)
        else:
            setattr(instance3, key, original + '!addition¡')
        assert instance != instance3
        setattr(instance3, key, original)

    # Test default class and None for un-assigned attributes
    instance4 = instance.__class__(content['uri'], content['title'])
    assert instance4.item_class == item_dict['item_class']
    for key in content.keys():
        if key not in ['uri', 'title', 'item_class']:
            assert getattr(instance4, key) is None


def common_tests_queue(parent_id, instance, content, item_xml,
                       item_dict):
    """Test all the common methods inherited from MusicLibraryItem

    :param parent_id: The parent ID of the class
    :param item_id: The expected item_id result for instance
    :param instance: The main object to be tested
    :param content: The content dict that corresponds to instance
    :param item_xml: A real XML example for from_xml
    :param item_dict: The content dict result corresponding to item_xml
    """
    # from_xml, this test uses real data examples
    instance2 = instance.__class__.from_xml(
        XML.fromstring(item_xml.encode('utf8')))
    assert instance2.to_dict == item_dict

    # from_dict and to_dict
    instance3 = instance.__class__.from_dict(content)
    assert instance3.to_dict == content

    # Test common attributes
    for key in ['uri', 'title', 'item_class']:
        set_and_get_test(instance, content, key)

    # Test equals (should fail if we change any attribute)
    assert instance == instance3
    for key in content.keys():
        original = getattr(instance3, key)
        if key == 'original_track_number':
            setattr(instance3, key, original + 1)
        else:
            setattr(instance3, key, original + '!addition¡')
        assert instance != instance3
        setattr(instance3, key, original)

    # Test default class and None for un-assigned attributes
    instance4 = instance.__class__(content['uri'], content['title'])
    assert instance4.item_class == item_dict['item_class']
    for key in content.keys():
        if key not in ['uri', 'title', 'item_class']:
            assert getattr(instance4, key) is None


# The functions that test the different classes
def test_mltrack():
    """Test the MLTrack class"""
    # Set the tests up
    uri = 'x-file-cifs://dummy_uri'
    kwargs = {'album': ALBUM, 'album_art_uri': ART_URI, 'creator': CREATOR,
              'original_track_number': 47}
    content = {'uri': uri, 'title': TITLE, 'item_class': 'dummy.class'}
    content.update(kwargs)
    track = data_structures.MLTrack(uri, TITLE, 'dummy.class', **kwargs)

    # Run tests on inherited methods and attributes
    common_tests('A:TRACKS', 'S://dummy_uri', track, content, TRACK_XML,
                 TRACK_DICT)

    # Test class specific attributes
    for key in ['album', 'album_art_uri', 'creator']:
        set_and_get_test(track, content, key)

    assert track.original_track_number == 47
    track.original_track_number = 42
    assert track.original_track_number == 42
    track.original_track_number = 47


def test_mlalbum():
    """Test the MLAlbum class"""
    # Set the tests up
    uri = 'x-rincon-playlist:RINCON_000E5884455C01400#A:ALBUM/dummy_album'
    kwargs = {'album_art_uri': ART_URI, 'creator': CREATOR}
    album = data_structures.MLAlbum(uri, TITLE, 'dummy.class', **kwargs)

    # Run tests on inherited methods and attributes
    content = {'uri': uri, 'title': TITLE, 'item_class': 'dummy.class'}
    content.update(kwargs)
    common_tests('A:ALBUM', 'A:ALBUM/dummy_album', album, content, ALBUM_XML,
                 ALBUM_DICT)

    # Test class specific attributes
    for key in ['album_art_uri', 'creator']:
        set_and_get_test(album, content, key)


def test_mlartist():
    """Test the MLArtist class"""
    # Set the tests up
    uri = 'x-rincon-playlist:RINCON_000E5884455C01400#A:ARTIST/10%20Years'
    artist = data_structures.MLArtist(uri, TITLE, 'dummy.class')

    # Run tests on inherited methods and attributes
    content = {'uri': uri, 'title': TITLE, 'item_class': 'dummy.class'}
    common_tests('A:ARTIST', 'A:ARTIST/10%20Years', artist, content,
                 ARTIST_XML, ARTIST_DICT)


def test_mlalbumartist():
    """Test the MLAlbumArtist class"""
    # Set the tests up
    uri = 'x-rincon-playlist:RINCON_000E5884455C01400#A:ALBUMARTIST/'\
          '3%20Doors%20Down'
    albumartist = data_structures.MLAlbumArtist(uri, TITLE, 'dummy.class')

    # Run tests on inherited methods and attributes
    content = {'uri': uri, 'title': TITLE, 'item_class': 'dummy.class'}
    common_tests('A:ALBUMARTIST', 'A:ALBUMARTIST/3%20Doors%20Down',
                 albumartist, content, ALBUMARTIST_XML, ALBUMARTIST_DICT)


def test_mlgenre():
    """Test the MLGenre class"""
    # Set the tests up
    uri = 'x-rincon-playlist:RINCON_000E5884455C01400#A:GENRE/Acid'
    genre = data_structures.MLGenre(uri, TITLE, 'dummy.class')

    # Run tests on inherited methods and attributes
    content = {'uri': uri, 'title': TITLE, 'item_class': 'dummy.class'}
    common_tests('A:GENRE', 'A:GENRE/Acid', genre, content,
                 GENRE_XML, GENRE_DICT)


def test_mlcomposer():
    """Test the MLComposer class"""
    # Set the tests up
    uri = 'x-rincon-playlist:RINCON_000E5884455C01400#A:COMPOSER/A.%20Kiedis'\
          '%2fFlea%2fJ.%20Frusciante%2fC.%20Smith'
    composer = data_structures.MLComposer(uri, TITLE, 'dummy.class')

    # Run tests on inherited methods and attributes
    content = {'uri': uri, 'title': TITLE, 'item_class': 'dummy.class'}
    common_tests(
        'A:COMPOSER',
        'A:COMPOSER/A.%20Kiedis%2fFlea%2fJ.%20Frusciante%2fC.%20Smith',
        composer, content, COMPOSER_XML, COMPOSER_DICT
    )


def test_mlplaylist():
    """Test the MLPlaylist class"""
    # Set the tests up
    uri = 'x-file-cifs://TLE-SERVER/share/mp3/Trentem%c3%b8ller%20-%20The%20'\
          'Trentem%c3%b8ller%20Chronicles/-%3dTrentem%c3%b8ller%20-%20The%20'\
          'Trentem%c3%b8ller%20Chronicles%20(CD%201).m3u'
    playlist = data_structures.MLPlaylist(uri, TITLE, 'dummy.class')

    # Run tests on inherited methods and attributes
    content = {'uri': uri, 'title': TITLE, 'item_class': 'dummy.class'}
    common_tests('A:PLAYLISTS', 'S://TLE-SERVER/share/mp3/Trentem%c3%b8ller'
                 '%20-%20The%20Trentem%c3%b8ller%20Chronicles/-%3d'
                 'Trentem%c3%b8ller%20-%20The%20Trentem%c3%b8ller%20'
                 'Chronicles%20(CD%201).m3u', playlist, content,
                 PLAYLIST_XML, PLAYLIST_DICT)


def test_mlsonosplaylist():
    """Test the MLSonosPlaylist class"""
    # Set the tests up
    uri = 'file:///jffs/settings/savedqueues.rsq#13 title: Koop'
    playlist = data_structures.MLSonosPlaylist(uri, TITLE, 'dummy.class')

    # Run tests on inherited methods and attributes
    content = {'uri': uri, 'title': TITLE, 'item_class': 'dummy.class'}
    common_tests('SQ:', '13 title: Koop',
                 playlist, content, SONOS_PLAYLIST_XML, SONOS_PLAYLIST_DICT)


def test_mlshare():
    """Test the MLShare class"""
    # Set the tests up
    uri = 'x-rincon-playlist:RINCON_000E5884455C01400#S://TLE-SERVER/share'
    share = data_structures.MLShare(uri, TITLE, 'dummy.class')

    # Run tests on inherited methods and attributes
    content = {'uri': uri, 'title': TITLE, 'item_class': 'dummy.class'}
    common_tests('S:', 'S://TLE-SERVER/share', share, content,
                 SHARE_XML, SHARE_DICT)


def test_ns_tag():
    """Test the ns_tag module function"""
    namespaces = ['http://purl.org/dc/elements/1.1/',
                  'urn:schemas-upnp-org:metadata-1-0/upnp/',
                  'urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/']
    for ns_in, namespace in zip(['dc', 'upnp', ''], namespaces):
        res = data_structures.ns_tag(ns_in, 'testtag')
        correct = '{{{}}}{}'.format(namespace, 'testtag')
        assert res == correct


def test_get_ml_item():
    """Test the get_ml_item medule function"""
    xmls = [TRACK_XML, ALBUM_XML, ARTIST_XML, ALBUMARTIST_XML, GENRE_XML,
            COMPOSER_XML, PLAYLIST_XML, SHARE_XML]
    classes = [data_structures.MLTrack, data_structures.MLAlbum,
               data_structures.MLArtist, data_structures.MLAlbumArtist,
               data_structures.MLGenre, data_structures.MLComposer,
               data_structures.MLPlaylist, data_structures.MLShare]
    for xml, class_ in zip(xmls, classes):
        etree = XML.fromstring(xml.encode('utf-8'))
        item = data_structures.get_ml_item(etree)
        assert item.__class__ == class_


def test_queue_item():
    """Test the QueueItem class"""
    # Set the tests up
    uri = 'x-file-cifs://dummy_uri'
    kwargs = {'album': ALBUM, 'album_art_uri': ART_URI, 'creator': CREATOR,
              'original_track_number': 47}
    content = {'uri': uri, 'title': TITLE, 'item_class': 'dummy.class'}
    content.update(kwargs)
    track = data_structures.QueueItem(uri, TITLE, 'dummy.class', **kwargs)

    # Run tests on inherited methods and attributes
    common_tests_queue('Q:0', track, content, QUEUE_XML1, QUEUE_DICT1)

    # Test class specific attributes
    for key in ['album', 'album_art_uri', 'creator']:
        set_and_get_test(track, content, key)

    assert track.original_track_number == 47
    track.original_track_number = 42
    assert track.original_track_number == 42
    track.original_track_number = 47

########NEW FILE########
__FILENAME__ = test_events
# -*- coding: utf-8 -*-
""" Tests for the services module """

from __future__ import unicode_literals
from soco.events import parse_event_xml

DUMMY_EVENT = """
<e:propertyset xmlns:e="urn:schemas-upnp-org:event-1-0">
    <e:property>
        <ZoneGroupState>&lt;ZoneGroups&gt;&lt;
            ZoneGroup Coordinator="RINCON_000XXX01400"
            ID="RINCON_000XXX1400:56"&gt;&lt;
            ZoneGroupMember UUID="RINCON_000XXX400"
            Location="http://XXX" ZoneName="Living Room"
            Icon="x-rincon-roomicon:living" Configuration="1"
            SoftwareVersion="XXXX"
            MinCompatibleVersion="XXXX"
            LegacyCompatibleVersion="XXXX" BootSeq="48"/&gt;&lt;
            /ZoneGroup&gt;&lt;ZoneGroup Coordinator="RINCON_000XXXX01400"
            ID="RINCON_000XXXX1400:0"&gt;&lt;
            ZoneGroupMember UUID="RINCON_000XXXX1400"
            Location="http://192.168.1.100:1400/xml/device_description.xml"
            ZoneName="BRIDGE" Icon="x-rincon-roomicon:zoneextender"
            Configuration="1" Invisible="1" IsZoneBridge="1"
            SoftwareVersion="XXXX" MinCompatibleVersion="XXXX"
            LegacyCompatibleVersion="XXXX" BootSeq="37"/&gt;&lt;
            /ZoneGroup&gt;&lt;ZoneGroup Coordinator="RINCON_000XXXX1400"
            ID="RINCON_000XXXX1400:57"&gt;&lt;
            ZoneGroupMember UUID="RINCON_000XXXX01400"
            Location="http://192.168.1.102:1400/xml/device_description.xml"
            ZoneName="Kitchen" Icon="x-rincon-roomicon:kitchen"
            Configuration="1" SoftwareVersion="XXXX"
            MinCompatibleVersion="XXXX" LegacyCompatibleVersion="XXXX"
            BootSeq="56"/&gt;&lt;/ZoneGroup&gt;&lt;/ZoneGroups&gt;
         </ZoneGroupState>
    </e:property>
    <e:property>
        <ThirdPartyMediaServersX>...s+3N9Lby8yoJD/QOC4W</ThirdPartyMediaServersX>
    </e:property>
    <e:property>
        <AvailableSoftwareUpdate>&lt;UpdateItem
            xmlns="urn:schemas-rinconnetworks-com:update-1-0"
            Type="Software" Version="XXXX"
            UpdateURL="http://update-firmware.sonos.com/XXXX"
            DownloadSize="0"
            ManifestURL="http://update-firmware.sonos.com/XX"/&gt;
         </AvailableSoftwareUpdate>
    </e:property>
    <e:property>
        <AlarmRunSequence>RINCON_000EXXXXXX0:56:0</AlarmRunSequence>
    </e:property>
    <e:property>
        <ZoneGroupName>Kitchen</ZoneGroupName>
    </e:property>
    <e:property>
        <ZoneGroupID>RINCON_000XXXX01400:57</ZoneGroupID>
    </e:property>
    <e:property>
        <ZonePlayerUUIDsInGroup>RINCON_000XXX1400</ZonePlayerUUIDsInGroup>
    </e:property>
</e:propertyset>
"""


def test_event_parsing():
    event_dict = parse_event_xml(DUMMY_EVENT)
    assert event_dict['ZoneGroupState']
    assert event_dict['AlarmRunSequence'] == 'RINCON_000EXXXXXX0:56:0'
    assert event_dict['ZoneGroupID'] == "RINCON_000XXXX01400:57"


########NEW FILE########
__FILENAME__ = test_integration
# -*- coding: utf-8 -*-
# pylint: disable-msg=too-few-public-methods, redefined-outer-name, no-self-use

""" This file contains the classes used to perform integration tests on the
methods in the SoCo class. They access a real Sonos system.

PLEASE TAKE NOTE: All of these tests are designed to run on a Sonos system
without interfering with normal service. This means that they must not raise
the volume or must leave the player in the same state as they found it in. They
have been made this way since SoCo is developed by volunteers who in all
likelihood do not have a dedicated test system. Accordingly the tests must not
annoy the neighbors, and should return the system to its original state so that
the developers can listen to their music while coding, without having it
interrupted at every unit test!

PLEASE RESPECT THIS.

"""

from __future__ import unicode_literals

import time
import pytest

import soco as soco_module

# Mark all tests in this module with the pytest custom "integration" marker so
# they can be selected or deselected as a whole, eg:
# py.test -m "integration"
# or
# py.test -m "no integration"
pytestmark = pytest.mark.integration


@pytest.yield_fixture(scope='session')
def soco():
    """ Set up and tear down the soco fixture used by all tests. """
    # Get the ip address from the command line, and create the soco object
    # Only one is used per test session, hence the decorator
    ip = pytest.config.option.IP
    if ip is None:
        pytest.fail("No ip address specified. Use the --ip option.")
    soco = soco_module.SoCo(ip)
    # Check the device is playing and has items in the queue
    if len(soco.get_queue()) == 0:
        pytest.fail('Integration tests on the SoCo class must be run '
                    'with at least 1 item in the playlist.')

    transport_info = soco.get_current_transport_info()
    if transport_info['current_transport_state'] != 'PLAYING':
        pytest.fail('Integration tests on the SoCo class must be run '
                    'with the Sonos unit playing.')
    # Save the device's state
    state = {'queue': soco.get_queue(0, 1000),
             'current_track_info': soco.get_current_track_info()}

    # Yield the device to the test function
    yield soco

    # Tear down. Restore state
    soco.stop()
    soco.clear_queue()
    for track in state['queue']:
        soco.add_to_queue(track['uri'])
    soco.play_from_queue(
        int(state['current_track_info']['playlist_position']) - 1)
    soco.seek(state['current_track_info']['position'])
    soco.play()


def wait(interval=0.1):
    """ Convenience function to adjust sleep interval for all tests. """
    time.sleep(interval)


class TestVolume(object):
    """ Integration tests for the volume property """

    valid_values = range(101)

    @pytest.yield_fixture(autouse=True)
    def restore_volume(self, soco):
        """ A fixture which restores volume after each test in the class is
        run. """
        old = soco.volume
        yield
        soco.volume = old
        wait()

    def test_get_and_set(self, soco):
        """ Test if the set functionlity works when given valid arguments. """
        old = soco.volume
        assert old in self.valid_values
        if old == self.valid_values[0]:
            new = old + 1
        else:
            new = old - 1
        soco.volume = new
        wait()
        assert soco.volume == new

    def test_invalid_arguments(self, soco):
        """ Test if the set functionality coerces into range when given
        integers outside of allowed range.
        """

        # NOTE We don't test coerce from too large values, since that would
        # put the unit at full volume
        soco.volume = self.valid_values[0] - 1
        wait()
        assert soco.volume == 0

    def test_set_0(self):
        """ Test whether the volume can be set to 0. Regression test for:
        https://github.com/rahims/soco/issues/29
        """

        soco.volume = 0
        wait()
        assert soco.volume == 0


class TestBass(object):
    """ Integration tests for the bass property. This class implements a full
    boundary value test.
    """

    valid_values = range(-10, 11)

    @pytest.yield_fixture(autouse=True)
    def restore_bass(self, soco):
        """ A fixture which restores bass EQ after each test in the class is
        run. """
        old = soco.bass
        yield
        soco.bass = old
        wait()

    def test_get_and_set(self, soco):
        """ Test if the set functionlity works when given valid arguments. """
        assert soco.bass in self.valid_values
        # Values on the boundaries of the valid equivalence partition
        for value in [self.valid_values[0], self.valid_values[-1]]:
            soco.bass = value
            wait()
            assert soco.bass == value

    def test_invalid_arguments(self, soco):
        """ Test if the set functionality produces the expected "coerce in
        range" functionality when given a value outside of its range.
        """
        # Values on the boundaries of the two invalid equivalence partitions
        soco.bass = self.valid_values[0] - 1
        wait()
        assert soco.bass == self.valid_values[0]
        soco.bass = self.valid_values[-1] + 1
        wait()
        assert soco.bass == self.valid_values[-1]


class TestTreble(object):
    """ Integration tests for the treble property. This class implements a full
    boundary value test.
    """

    valid_values = range(-10, 11)

    @pytest.yield_fixture(autouse=True)
    def restore_treble(self, soco):
        """ A fixture which restores treble EQ after each test in the class is
        run. """
        old = soco.treble
        yield
        soco.treble = old
        wait()

    def test_get_and_set(self, soco):
        """ Test if the set functionlity works when given valid arguments. """
        assert soco.treble in self.valid_values
        # Values on the boundaries of the valid equivalence partition
        for value in [self.valid_values[0], self.valid_values[-1]]:
            soco.treble = value
            wait()
            assert soco.treble == value

    def test_invalid_arguments(self, soco):
        """ Test if the set functionality produces the expected "coerce in
        range" functionality when given a value outside its range.
        """
         # Values on the boundaries of the two invalid equivalence partitions
        soco.treble = self.valid_values[0] - 1
        wait()
        assert soco.treble == self.valid_values[0]
        soco.treble = self.valid_values[-1] + 1
        wait()
        assert soco.treble == self.valid_values[-1]


class TestMute(object):
    """ Integration test for the mute method. """

    def test(self, soco):
        """ Test if the mute method works """
        old = soco.mute
        assert old is False, ('The unit should not be muted when running '
                              'the unit tests.')
        soco.mute = True
        wait()
        new = soco.mute
        assert new is True
        soco.mute = False
        wait()
        assert soco.mute is False


class TestGetCurrentTransportInfo(object):
    """ Integration test for the get_current_transport_info method. """

    # The values in this list must be kept up to date with the values in
    # the test doc string
    transport_info_keys = sorted(['current_transport_status',
                                  'current_transport_state',
                                  'current_transport_speed'])

    def test(self, soco):
        """ Test if the return value is a dictionary that contains the keys:
        current_transport_status, current_transport_state,
        current_transport_speed and that values have been found for all keys,
        i.e. they are not None.
        """
        transport_info = soco.get_current_transport_info()
        assert isinstance(transport_info, dict)
        assert self.transport_info_keys == sorted(transport_info.keys())
        for _, value in transport_info.items():
            assert value is not None


class TestTransport(object):
    """ Integration tests for transport methods (play, pause etc). """

    def test_pause_and_play(self, soco):
        """ Test if the pause and play methods work """
        soco.pause()
        wait(1)
        on_pause = soco.get_current_transport_info()['current_transport_state']
        assert on_pause == 'PAUSED_PLAYBACK'
        soco.play()
        wait(1)
        on_play = soco.get_current_transport_info()['current_transport_state']
        assert on_play == 'PLAYING'

    def test_stop(self, soco):
        """ Test if the stop method works """
        soco.stop()
        wait(1)
        new = soco.get_current_transport_info()['current_transport_state']
        assert new == 'STOPPED'
        soco.play()
        wait(1)
        on_play = soco.get_current_transport_info()['current_transport_state']
        assert on_play == 'PLAYING'

    def test_seek_valid(self, soco):
        """ Test if the seek method works with valid input """
        original_position = soco.get_current_track_info()['position']
        # Format 1
        soco.seek('0:00:00')
        wait()
        position = soco.get_current_track_info()['position']
        assert position in ['0:00:00', '0:00:01']
        # Reset and format 2
        soco.seek(original_position)
        soco.seek('00:00:00')
        wait()
        position = soco.get_current_track_info()['position']
        assert position in ['0:00:00', '0:00:01']
        # Clean up
        soco.seek(original_position)
        wait()

    def test_seek_invald(self, soco):
        """ Test if the seek method properly fails with invalid input. """
        for string in ['invalid_time_string', '5:12', '6', 'aa:aa:aa']:
            with pytest.raises(ValueError):
                soco.seek(string)


class TestGetCurrentTrackInfo(object):
    """ Integration test for the get_current_track_info method. """

    info_keys = sorted(['album', 'artist', 'title', 'uri',
                        'playlist_position', 'duration', 'album_art',
                        'position'])

    def test_get(self, soco):
        """ Test is the return value is a dictinary and contains the following
        keys: album, artist, title, uri, playlist_position, duration,
        album_art and position.
        """
        info = soco.get_current_track_info()
        assert isinstance(info, dict)
        assert sorted(info.keys()) == self.info_keys


class TestGetSpeakerInfo(object):
    """ Integration test for the get_speaker_info method. """

    # The values in this list must be kept up to date with the values in
    # the test doc string
    info_keys = sorted(['zone_name', 'zone_icon', 'uid',
                        'serial_number', 'software_version',
                        'hardware_version', 'mac_address'])

    def test(self, soco):
        """ Test if the return value is a dictionary that contains the keys:
        zone_name, zone_icon, uid, serial_number, software_version,
        hardware_version, mac_address
        and that values have been found for all keys, i.e. they are not None.
        """
        speaker_info = soco.get_speaker_info()
        assert isinstance(speaker_info, dict)
        for _, value in speaker_info.items():
            assert value is not None

# TODO: test GetSpeakersIp


class TestGetQueue(object):
    """ Integration test for the get_queue method. """

    # The values in this list must be kept up to date with the values in
    # the test doc string
    queue_element_keys = sorted(['album', 'artist', 'uri',
                                'album_art', 'title'])

    def test_get(self, soco):
        """ Test is return value is a list of dictionaries and if each of
        the dictionaries contain the keys: album, artist, uri, album_art and
        title.
        """
        queue = soco.get_queue(0, 100)
        assert isinstance(queue, list)
        for item in queue:
            assert isinstance(item, dict)
            assert sorted(item.keys()) == self.queue_element_keys


class TestAddToQueue(object):
    """ Integration test for the add_to_queue method. """

    def test_add_to_queue(self, soco):
        """ Get the current queue, add the last item of the current queue
        and then compare the length of the old queue with the new and
        check that the last two elements are identical.
        """

        old_queue = soco.get_queue(0, 1000)
        # Add new element and check
        assert (soco.add_to_queue(old_queue[-1]['uri'])) == len(old_queue) + 1
        wait()
        new_queue = soco.get_queue()
        assert (len(new_queue) - 1) == len(old_queue)
        assert (new_queue[-1]) == (new_queue[-2])
        # Restore queue again? Probably no need, since queue is restored on
        # tear down anyway.


class TestRemoveFromQueue(object):
    """ Integration test for the remove_from_queue method. """

    def test(self, soco):
        """ Test if the remove_from_queue method works. """
        old_queue = soco.get_queue()
        track_to_remove = old_queue[-1]
        soco.remove_from_queue(len(old_queue))
        wait()
        new_queue = soco.get_queue()
        assert old_queue != new_queue, (
            'No difference between '
            'queues before and after removing the last item')
        assert len(new_queue) == len(old_queue) - 1
        # Clean up
        soco.add_to_queue(track_to_remove['uri'])
        wait()
        assert old_queue == soco.get_queue()

########NEW FILE########
__FILENAME__ = test_services
# -*- coding: utf-8 -*-
""" Tests for the services module """

# These tests require pytest, and mock. Mock comes with Python 3.3, but has
# also been backported for Python 2.7. It is available on pypi.

from __future__ import unicode_literals

import pytest
from soco.services import Service
from soco.exceptions import SoCoUPnPException

try:
    from unittest import mock
except:
    import mock  # TODO: add mock to requirements

# Dummy known-good errors/responses etc.  These are not necessarily valid as
# actual commands, but are valid XML/UPnP. They also contain unicode characters
# to test unicode handling.

DUMMY_ERROR = "".join([
    '<?xml version="1.0"?>',
    '<s:Envelope ',
    'xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" ',
    's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">',
        '<s:Body>',
            '<s:Fault>',
                '<faultcode>s:Client</faultcode>',
                '<faultstring>UPnPError</faultstring>',
                '<detail>',
                    '<UPnPError xmlns="urn:schemas-upnp-org:control-1-0">',
                        '<errorCode>607</errorCode>',
                        '<errorDescription>Oops μИⅠℂ☺ΔЄ💋</errorDescription>',
                    '</UPnPError>',
                '</detail>',
            '</s:Fault>',
        '</s:Body>',
    '</s:Envelope>'])  # noqa PEP8

DUMMY_VALID_RESPONSE = "".join([
    '<?xml version="1.0"?>',
    '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"',
        ' s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">',
        '<s:Body>',
            '<u:GetLEDStateResponse ',
                'xmlns:u="urn:schemas-upnp-org:service:DeviceProperties:1">',
                '<CurrentLEDState>On</CurrentLEDState>',
                '<Unicode>μИⅠℂ☺ΔЄ💋</Unicode>',
        '</u:GetLEDStateResponse>',
        '</s:Body>',
    '</s:Envelope>'])  # noqa PEP8

DUMMY_VALID_ACTION = "".join([
    '<?xml version="1.0"?>',
    '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"',
        ' s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">',
        '<s:Body>',
            '<u:SetAVTransportURI ',
                'xmlns:u="urn:schemas-upnp-org:service:Service:1">',
                '<InstanceID>0</InstanceID>',
                '<CurrentURI>URI</CurrentURI>',
                '<CurrentURIMetaData></CurrentURIMetaData>',
                '<Unicode>μИⅠℂ☺ΔЄ💋</Unicode>'
            '</u:SetAVTransportURI>',
        '</s:Body>'
    '</s:Envelope>'])  # noqa PEP8


@pytest.fixture()
def service():
    """ A mock Service, for use as a test fixture """

    mock_soco = mock.MagicMock()
    mock_soco.ip_address = "192.168.1.101"
    return Service(mock_soco)


def test_init_defaults(service):
    """ Check default properties are set up correctly """
    assert service.service_type == "Service"
    assert service.version == 1
    assert service.service_id == "Service"
    assert service.base_url == "http://192.168.1.101:1400"
    assert service.control_url == "/Service/Control"
    assert service.scpd_url == "/xml/Service1.xml"
    assert service.event_subscription_url == "/Service/Event"


def test_method_dispatcher_function_creation(service):
    """ Testing __getattr__ functionality """
    import inspect
    # There should be no testing method
    assert 'testing' not in service.__dict__.keys()
    # but we should be able to inspect it
    assert inspect.ismethod(service.testing)
    # and then, having examined it, the method should be cached on the instance
    assert 'testing' in service.__dict__.keys()
    assert service.testing.__name__ == "testing"
    # check that send_command is actually called when we invoke a method
    service.send_command = lambda x, y: "Hello {}".format(x)
    assert service.testing(service) == "Hello testing"


def test_method_dispatcher_arg_count(service):
    """ _dispatcher should pass its args to send_command """
    service.send_command = mock.Mock()
    # http://bugs.python.org/issue7688
    # __name__ must be a string in python 2
    method = service.__getattr__(str('test'))
    assert method('onearg')
    service.send_command.assert_called_with('test', 'onearg')
    assert method()  # no args
    service.send_command.assert_called_with('test')
    assert method('one', cache_timeout=4) # one arg + cache_timeout
    service.send_command.assert_called_with('test', 'one', cache_timeout=4)


def test_wrap(service):
    """ wrapping args in XML properly """
    assert service.wrap_arguments([('first', 'one'), ('second', 2)]) == \
        "<first>one</first><second>2</second>"
    assert service.wrap_arguments() == ""
    # Unicode
    assert service.wrap_arguments([('unicode', "μИⅠℂ☺ΔЄ💋")]) == \
        "<unicode>μИⅠℂ☺ΔЄ💋</unicode>"
    # XML escaping - do we also need &apos; ?
    assert service.wrap_arguments([('weird', '&<"2')]) == \
        "<weird>&amp;&lt;&quot;2</weird>"


def test_unwrap(service):
    """ unwrapping args from XML """
    assert service.unwrap_arguments(DUMMY_VALID_RESPONSE) == {
        "CurrentLEDState": "On",
        "Unicode": "μИⅠℂ☺ΔЄ💋"}


def test_build_command(service):
    """ Test creation of SOAP body and headers from a command """
    headers, body = service.build_command('SetAVTransportURI', [
        ('InstanceID', 0),
        ('CurrentURI', 'URI'),
        ('CurrentURIMetaData', ''),
        ('Unicode', 'μИⅠℂ☺ΔЄ💋')
        ])
    assert body == DUMMY_VALID_ACTION
    assert headers == {
        'Content-Type': 'text/xml; charset="utf-8"',
        'SOAPACTION':
        'urn:schemas-upnp-org:service:Service:1#SetAVTransportURI'}


def test_send_command(service):
    """ Calling a command should result in a http request, unless the cache
    is hit """
    response = mock.MagicMock()
    response.headers = {}
    response.status_code = 200
    response.text = DUMMY_VALID_RESPONSE
    with mock.patch('requests.post', return_value=response) as fake_post:
        result = service.send_command('SetAVTransportURI', [
            ('InstanceID', 0),
            ('CurrentURI', 'URI'),
            ('CurrentURIMetaData', ''),
            ('Unicode', 'μИⅠℂ☺ΔЄ💋')
            ], cache_timeout=2)
        assert result == {'CurrentLEDState': 'On', 'Unicode': "μИⅠℂ☺ΔЄ💋"}
        fake_post.assert_called_once_with(
            'http://192.168.1.101:1400/Service/Control',
            headers=mock.ANY, data=DUMMY_VALID_ACTION)
        # Now the cache should be primed, so try it again
        fake_post.reset_mock()
        result = service.send_command('SetAVTransportURI', [
            ('InstanceID', 0),
            ('CurrentURI', 'URI'),
            ('CurrentURIMetaData', ''),
            ('Unicode', 'μИⅠℂ☺ΔЄ💋')
            ], cache_timeout=0)
        # The cache should be hit, so there should be no http request
        assert not fake_post.called
        # but this should not affefct a call with different params
        fake_post.reset_mock()
        result = service.send_command('SetAVTransportURI', [
            ('InstanceID', 1),
            ('CurrentURI', 'URI2'),
            ('CurrentURIMetaData', 'abcd'),
            ('Unicode', 'μИⅠℂ☺ΔЄ💋')
            ])
        assert fake_post.called
        # calling again after the time interval will avoid the cache
        fake_post.reset_mock()
        import time
        time.sleep(2)
        result = service.send_command('SetAVTransportURI', [
            ('InstanceID', 0),
            ('CurrentURI', 'URI'),
            ('CurrentURIMetaData', ''),
            ('Unicode', 'μИⅠℂ☺ΔЄ💋')
            ])
        assert fake_post.called

def test_handle_upnp_error(service):
    """ Check errors are extracted properly """
    with pytest.raises(SoCoUPnPException) as E:
        service.handle_upnp_error(DUMMY_ERROR)
    assert "UPnP Error 607 received: Signature Failure from 192.168.1.101" \
        == E.value.message
    assert E.value.error_code == '607'
    assert E.value.error_description == 'Signature Failure'
    # TODO: Try this with a None Error Code

# TODO: test iter_actions

########NEW FILE########
__FILENAME__ = test_singleton
# -*- coding: utf-8 -*-
""" Tests for the SoCoSingletonBase and _ArgsSingleton classes in core"""

from __future__ import unicode_literals

import pytest
from soco.core import _SocoSingletonBase as Base

class ASingleton(Base):
    def __init__(self, arg):
        pass

class AnotherSingleton(ASingleton):
    pass


def test_singleton():
    """ Check basic functionality. For a given arg, there is only one instance"""
    assert ASingleton('aa') == ASingleton('aa')
    assert ASingleton('aa') != ASingleton('bb')
    
def test_singleton_inherit():
    """ Check that subclasses behave properly"""
    assert ASingleton('aa') != AnotherSingleton('aa')
    assert AnotherSingleton('aa') == AnotherSingleton('aa')

########NEW FILE########
__FILENAME__ = test_utils
# -*- coding: utf-8 -*-
""" Tests for the utils module """

from __future__ import unicode_literals
from soco.utils import TimedCache

def test_cache_put_get():
    "Test putting items into, and getting them from, the cache"
    from time import sleep
    cache = TimedCache()
    cache.put("item", 'some', kw='args', timeout=3)
    assert not cache.get('some', 'otherargs') == "item"
    assert cache.get('some', kw='args') == "item"
    sleep(2)
    assert cache.get('some', kw='args') == "item"
    sleep(2)
    assert not cache.get('some', kw='args') == "item"


    cache.put("item", 'some', 'args', and_a='keyword', timeout=3)
    assert cache.get('some', 'args', and_a='keyword') == "item"
    assert not cache.get(
        'some', 'otherargs', and_a='keyword') == "item"

def test_cache_clear_del():
    "Test removal of items and clearing the cache"
    cache = TimedCache()
    cache.put("item", "some", kw="args", timeout=2)
    # Check it's there
    assert cache.get('some', kw='args') == "item"
    # delete it
    cache.delete('some', kw='args')
    assert not cache.get('some', kw='args') == "item"
    # put it back
    cache.put("item", "some", kw="args", timeout=3)
    cache.clear()
    assert not cache.get('some', kw='args') == "item"

def test_with_typical_args():
    cache = TimedCache()
    cache.put ("result", 'SetAVTransportURI', [
            ('InstanceID', 1),
            ('CurrentURI', 'URI2'),
            ('CurrentURIMetaData', 'abcd'),
            ('Unicode', 'μИⅠℂ☺ΔЄ💋')
            ], timeout=3)
    assert cache.get('SetAVTransportURI', [
            ('InstanceID', 1),
            ('CurrentURI', 'URI2'),
            ('CurrentURIMetaData', 'abcd'),
            ('Unicode', 'μИⅠℂ☺ΔЄ💋')
            ]) == "result"


########NEW FILE########
