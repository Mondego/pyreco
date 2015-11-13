__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Django documentation build configuration file, created by
# sphinx-quickstart on Thu Mar 27 09:06:53 2008.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

import sys
import os

# If your extensions are in another directory, add it here.
sys.path.append(os.path.join(os.path.dirname(__file__), "_ext"))

# General configuration
# ---------------------

language = 'ja'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ["djangodocs"]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix of source filenames.
source_suffix = '.txt'

# The master toctree document.
master_doc = 'contents'

# General substitutions.
project = 'Django'
copyright = 'Django Software Foundation and contributors'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '1.4'
# The full version, including alpha/beta/rc tags.
release = version

# The next version to be released
django_next_version = '1.5'

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = False

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'trac'

# Sphinx will recurse into subversion configuration folders and try to read  
# any document file within. These should be ignored. 
# Note: exclude_dirnames is new in Sphinx 0.5 
exclude_dirnames = ['.svn']

# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
html_use_smartypants = True

# HTML translator class for the builder
html_translator_class = "djangodocs.DjangoHTMLTranslator"

# Content template for the index page.
#html_index = ''

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If true, the reST sources are included in the HTML build as _sources/<name>.
html_copy_source = True

# Output file base name for HTML help builder.
htmlhelp_basename = 'Djangodoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
#latex_documents = []
latex_documents = [
  ('contents', 'django.tex', 'Django Documentation', 'Django Software Foundation', 'manual'),
]

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
# If this isn't set to True, the LaTex writer can only handle six levels of headers.
latex_use_parts = True


########NEW FILE########
__FILENAME__ = diffgen
#!/usr/bin/env python

from optparse import OptionParser
import commands
import re
import sys
import cPickle as pickle

parser = OptionParser()
parser.add_option("--debug", dest="debug", default=False, action="store_true")
parser.add_option("--svk", dest="svk_basepath", default="//jk/django/docs/",
    help="default `%default`.")
parser.add_option("--sync", dest="sync", default=False, action="store_true",
    help="update revision map.")
parser.add_option("-l", "--log", dest="log", default="5",
    help="default `%default`.")
parser.add_option("-p", "--path", dest="path", default="")
parser.add_option("-r", "--rev", dest="rev", default="")
parser.add_option("-w", "--workspace", dest="workspace", default="works/",
    help="default `%default`.")
(_options,  argv) = parser.parse_args()
options = _options.__dict__
options["-"] = ""

log_cmd = "svk log %(log_flag)s %(rev)s %(svk_basepath)s%(path)s"
diffoutput_path = "%(workspace)s%(path)s%(-)s%(rev)s.diff"
diff_cmd = "svk diff %(diff_flag)s %(rev)s %(svk_basepath)s%(path)s >" + diffoutput_path
sync_cmd = "svk sync %(svk_basepath)s"
loghead_cmd = "svk log -q %(svk_basepath)s"


def dump_revs():
    revs = dict()
    rev = re.compile(ur"r\d+")
    for line in commands.getoutput(loghead_cmd % options).splitlines():
        if line.startswith("-"):
            continue
        try:
            (local, orig) = rev.findall(line)[:2]
        except ValueError:
            continue
        revs[int(orig[1:])] = int(local[1:])
    pickle.dump(revs, open("%(workspace)s_revs" % options, "w"))

def conv_rev(rev, revs=dict()):
    if not revs:
        try:
            revs.update(pickle.load(open("%(workspace)s_revs" % options)))
        except IOError, e:
            print "%s: Does not saved revision map. rerun with `--sync` option." % e
    result = revs.get(int(rev))
    if result is None:
        revs_keys = sorted(revs.keys())
        result = revs[filter(lambda x: x > int(rev), revs_keys)[0] or revs_keys[-1]]
    return str(result)


if options.get("path"):
    options["-"] = "-"

rev = options.get("rev")
if ":" in rev:
    diff_flag = "-r"
    options["rev"] = ":".join(map(conv_rev, rev.split(":")))
elif rev:
    diff_flag = "-c"
    options["rev"] = conv_rev(rev)
else:
    diff_flag = None
options["diff_flag"] = diff_flag


log_flag = "-r"
if options.get("sync"):
    cmd = sync_cmd
elif options["diff_flag"]:
    cmd = "%s; %s" % (log_cmd, diff_cmd)
    print "Writing to", diffoutput_path % options
else:
    options["rev"] = "%s" % options["log"]
    log_flag = "-l"
    cmd = log_cmd
options["log_flag"] = log_flag

if _options.debug:
    print "DEBUG:", cmd % options
print commands.getoutput(cmd % options)
if options.get("sync"):
    dump_revs()

########NEW FILE########
__FILENAME__ = applyxrefs
"""Adds xref targets to the top of files."""

import sys
import os

testing = False

DONT_TOUCH = (
        './index.txt',
        )

def target_name(fn):
    if fn.endswith('.txt'):
        fn = fn[:-4]
    return '_' + fn.lstrip('./').replace('/', '-')

def process_file(fn, lines):
    lines.insert(0, '\n')
    lines.insert(0, '.. %s:\n' % target_name(fn))
    try:
        f = open(fn, 'w')
    except IOError:
        print("Can't open %s for writing. Not touching it." % fn)
        return
    try:
        f.writelines(lines)
    except IOError:
        print("Can't write to %s. Not touching it." % fn)
    finally:
        f.close()

def has_target(fn):
    try:
        f = open(fn, 'r')
    except IOError:
        print("Can't open %s. Not touching it." % fn)
        return (True, None)
    readok = True
    try:
        lines = f.readlines()
    except IOError:
        print("Can't read %s. Not touching it." % fn)
        readok = False
    finally:
        f.close()
        if not readok:
            return (True, None)

    #print fn, len(lines)
    if len(lines) < 1:
        print("Not touching empty file %s." % fn)
        return (True, None)
    if lines[0].startswith('.. _'):
        return (True, None)
    return (False, lines)

def main(argv=None):
    if argv is None:
        argv = sys.argv

    if len(argv) == 1:
        argv.extend('.')

    files = []
    for root in argv[1:]:
        for (dirpath, dirnames, filenames) in os.walk(root):
            files.extend([(dirpath, f) for f in filenames])
    files.sort()
    files = [os.path.join(p, fn) for p, fn in files if fn.endswith('.txt')]
    #print files

    for fn in files:
        if fn in DONT_TOUCH:
            print("Skipping blacklisted file %s." % fn)
            continue

        target_found, lines = has_target(fn)
        if not target_found:
            if testing:
                print '%s: %s' % (fn, lines[0]),
            else:
                print "Adding xref to %s" % fn
                process_file(fn, lines)
        else:
            print "Skipping %s: already has a xref" % fn

if __name__ == '__main__':
    sys.exit(main())
########NEW FILE########
__FILENAME__ = djangodocs
# coding: utf-8
"""
Sphinx plugins for Django documentation.
"""
import os
import re

from docutils import nodes, transforms
try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        try:
            from django.utils import simplejson as json
        except ImportError:
            json = None

from sphinx import addnodes, roles, __version__ as sphinx_ver
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.writers.html import SmartyPantsHTMLTranslator
from sphinx.util.console import bold
from sphinx.util.compat import Directive

# RE for option descriptions without a '--' prefix
simple_option_desc_re = re.compile(
    r'([-_a-zA-Z0-9]+)(\s*.*?)(?=,\s+(?:/|-|--)|$)')

def setup(app):
    app.add_crossref_type(
        directivename = "setting",
        rolename      = "setting",
        indextemplate = u"pair: %s; 設定",
    )
    app.add_crossref_type(
        directivename = "templatetag",
        rolename      = "ttag",
        indextemplate = u"pair: %s; テンプレートタグ"
    )
    app.add_crossref_type(
        directivename = "templatefilter",
        rolename      = "tfilter",
        indextemplate = u"pair: %s; テンプレートフィルタ"
    )
    app.add_crossref_type(
        directivename = "fieldlookup",
        rolename      = "lookup",
        indextemplate = u"pair: %s, フィールド照合タイプ",
    )
    app.add_description_unit(
        directivename = "django-admin",
        rolename      = "djadmin",
        indextemplate = u"pair: %s; django-admin コマンド",
        parse_node    = parse_django_admin_node,
    )
    app.add_description_unit(
        directivename = "django-admin-option",
        rolename      = "djadminopt",
        indextemplate = u"pair: %s; django-admin コマンドラインオプション",
        parse_node    = parse_django_adminopt_node,
    )
    app.add_config_value('django_next_version', '0.0', True)
    app.add_directive('versionadded', VersionDirective)
    app.add_directive('versionchanged', VersionDirective)
    app.add_builder(DjangoStandaloneHTMLBuilder)


class VersionDirective(Directive):
    has_content = True
    required_arguments = 1
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {}

    def run(self):
        env = self.state.document.settings.env
        arg0 = self.arguments[0]
        is_nextversion = env.config.django_next_version == arg0
        ret = []
        node = addnodes.versionmodified()
        ret.append(node)
        if not is_nextversion:
            if len(self.arguments) == 1:
                linktext = u'リリースノートを参照してください </releases/%s>' % (arg0)
                xrefs = roles.XRefRole()('doc', linktext, linktext, self.lineno, self.state)
                node.extend(xrefs[0])
            node['version'] = arg0
        else:
            node['version'] = "Development version"
        node['type'] = self.name
        if len(self.arguments) == 2:
            inodes, messages = self.state.inline_text(self.arguments[1], self.lineno+1)
            node.extend(inodes)
            if self.content:
                self.state.nested_parse(self.content, self.content_offset, node)
            ret = ret + messages
        env.note_versionchange(node['type'], node['version'], node, self.lineno)
        return ret


class DjangoHTMLTranslator(SmartyPantsHTMLTranslator):
    """
    Django-specific reST to HTML tweaks.
    """

    # Don't use border=1, which docutils does by default.
    def visit_table(self, node):
        self.context.append(self.compact_p)
        self.compact_p = True
        self._table_row_index = 0 # Needed by Sphinx
        self.body.append(self.starttag(node, 'table', CLASS='docutils'))

    # avoid error with docutils 0.11 or later
    def depart_table(self, node):
        self.compact_p = self.context.pop()
        self.body.append('</table>\n')

    # <big>? Really?
    def visit_desc_parameterlist(self, node):
        self.body.append('(')
        self.first_param = 1
        self.param_separator = node.child_text_separator

    def depart_desc_parameterlist(self, node):
        self.body.append(')')

    if sphinx_ver < '1.0.8':
        #
        # Don't apply smartypants to literal blocks
        #
        def visit_literal_block(self, node):
            self.no_smarty += 1
            SmartyPantsHTMLTranslator.visit_literal_block(self, node)

        def depart_literal_block(self, node):
            SmartyPantsHTMLTranslator.depart_literal_block(self, node)
            self.no_smarty -= 1

    #
    # Turn the "new in version" stuff (versionadded/versionchanged) into a
    # better callout -- the Sphinx default is just a little span,
    # which is a bit less obvious that I'd like.
    #
    # FIXME: these messages are all hardcoded in English. We need to change
    # that to accomodate other language docs, but I can't work out how to make
    # that work.
    #
    version_text = {
        'deprecated':       u'Django %s で撤廃されました',
        'versionchanged':   u'Django %s で変更されました',
        'versionadded':     u'Django %s で新たに登場しました',
    }

    def visit_versionmodified(self, node):
        self.body.append(
            self.starttag(node, 'div', CLASS=node['type'])
        )
        title = "%s%s" % (
            self.version_text[node['type']] % node['version'],
            len(node) and ":" or "."
        )
        self.body.append('<span class="title">%s</span> ' % title)

    def depart_versionmodified(self, node):
        self.body.append("</div>\n")

    # Give each section a unique ID -- nice for custom CSS hooks
    def visit_section(self, node):
        old_ids = node.get('ids', [])
        node['ids'] = ['s-' + i for i in old_ids]
        node['ids'].extend(old_ids)
        SmartyPantsHTMLTranslator.visit_section(self, node)
        node['ids'] = old_ids

def parse_django_admin_node(env, sig, signode):
    command = sig.split(' ')[0]
    env._django_curr_admin_command = command
    title = "django-admin.py %s" % sig
    signode += addnodes.desc_name(title, title)
    return sig

def parse_django_adminopt_node(env, sig, signode):
    """A copy of sphinx.directives.CmdoptionDesc.parse_signature()"""
    from sphinx.domains.std import option_desc_re
    count = 0
    firstname = ''
    for m in option_desc_re.finditer(sig):
        optname, args = m.groups()
        if count:
            signode += addnodes.desc_addname(', ', ', ')
        signode += addnodes.desc_name(optname, optname)
        signode += addnodes.desc_addname(args, args)
        if not count:
            firstname = optname
        count += 1
    if not count:
        for m in simple_option_desc_re.finditer(sig):
            optname, args = m.groups()
            if count:
                signode += addnodes.desc_addname(', ', ', ')
            signode += addnodes.desc_name(optname, optname)
            signode += addnodes.desc_addname(args, args)
            if not count:
                firstname = optname
            count += 1
    if not firstname:
        raise ValueError
    return firstname


class DjangoStandaloneHTMLBuilder(StandaloneHTMLBuilder):
    """
    Subclass to add some extra things we need.
    """

    name = 'djangohtml'

    def finish(self):
        super(DjangoStandaloneHTMLBuilder, self).finish()
        if json is None:
            self.warn("cannot create templatebuiltins.js due to missing simplejson dependency")
            return
        self.info(bold("writing templatebuiltins.js..."))
        xrefs = self.env.domaindata["std"]["objects"]
        templatebuiltins = {
            "ttags": [n for ((t, n), (l, a)) in xrefs.items()
                        if t == "templatetag" and l == "ref/templates/builtins"],
            "tfilters": [n for ((t, n), (l, a)) in xrefs.items()
                        if t == "templatefilter" and l == "ref/templates/builtins"],
        }
        outfilename = os.path.join(self.outdir, "templatebuiltins.js")
        f = open(outfilename, 'wb')
        f.write('var django_template_builtins = ')
        json.dump(templatebuiltins, f)
        f.write(';\n')
        f.close();

########NEW FILE########
__FILENAME__ = literals_to_xrefs
"""
Runs through a reST file looking for old-style literals, and helps replace them
with new-style references.
"""

import re
import sys
import shelve

refre = re.compile(r'``([^`\s]+?)``')

ROLES = (
    'attr',
    'class',
    "djadmin",
    'data',
    'exc',
    'file',
    'func',
    'lookup',
    'meth',
    'mod' ,
    "djadminopt",
    "ref",
    "setting",
    "term",
    "tfilter",
    "ttag",
    
    # special
    "skip"
)

ALWAYS_SKIP = [
    "NULL",
    "True",
    "False",
]

def fixliterals(fname):
    data = open(fname).read()
    
    last = 0
    new = []
    storage = shelve.open("/tmp/literals_to_xref.shelve")
    lastvalues = storage.get("lastvalues", {})
    
    for m in refre.finditer(data):
        
        new.append(data[last:m.start()])
        last = m.end()
        
        line_start = data.rfind("\n", 0, m.start())
        line_end = data.find("\n", m.end())
        prev_start = data.rfind("\n", 0, line_start)
        next_end = data.find("\n", line_end + 1)
        
        # Skip always-skip stuff
        if m.group(1) in ALWAYS_SKIP:
            new.append(m.group(0))
            continue
            
        # skip when the next line is a title
        next_line = data[m.end():next_end].strip()
        if next_line[0] in "!-/:-@[-`{-~" and all(c == next_line[0] for c in next_line):
            new.append(m.group(0))
            continue
        
        sys.stdout.write("\n"+"-"*80+"\n")
        sys.stdout.write(data[prev_start+1:m.start()])
        sys.stdout.write(colorize(m.group(0), fg="red"))
        sys.stdout.write(data[m.end():next_end])
        sys.stdout.write("\n\n")
        
        replace_type = None
        while replace_type is None:
            replace_type = raw_input(
                colorize("Replace role: ", fg="yellow")
            ).strip().lower()
            if replace_type and replace_type not in ROLES:
                replace_type = None
        
        if replace_type == "":
            new.append(m.group(0))
            continue
            
        if replace_type == "skip":
            new.append(m.group(0))
            ALWAYS_SKIP.append(m.group(1))
            continue
        
        default = lastvalues.get(m.group(1), m.group(1))
        if default.endswith("()") and replace_type in ("class", "func", "meth"):
            default = default[:-2]        
        replace_value = raw_input(
            colorize("Text <target> [", fg="yellow") + default + colorize("]: ", fg="yellow")
        ).strip()
        if not replace_value: 
            replace_value = default
        new.append(":%s:`%s`" % (replace_type, replace_value))
        lastvalues[m.group(1)] = replace_value
    
    new.append(data[last:])
    open(fname, "w").write("".join(new))
    
    storage["lastvalues"] = lastvalues
    storage.close()
    
#
# The following is taken from django.utils.termcolors and is copied here to
# avoid the dependancy.
#


def colorize(text='', opts=(), **kwargs):
    """
    Returns your text, enclosed in ANSI graphics codes.

    Depends on the keyword arguments 'fg' and 'bg', and the contents of
    the opts tuple/list.

    Returns the RESET code if no parameters are given.

    Valid colors:
        'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'

    Valid options:
        'bold'
        'underscore'
        'blink'
        'reverse'
        'conceal'
        'noreset' - string will not be auto-terminated with the RESET code

    Examples:
        colorize('hello', fg='red', bg='blue', opts=('blink',))
        colorize()
        colorize('goodbye', opts=('underscore',))
        print colorize('first line', fg='red', opts=('noreset',))
        print 'this should be red too'
        print colorize('and so should this')
        print 'this should not be red'
    """
    color_names = ('black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white')
    foreground = dict([(color_names[x], '3%s' % x) for x in range(8)])
    background = dict([(color_names[x], '4%s' % x) for x in range(8)])

    RESET = '0'
    opt_dict = {'bold': '1', 'underscore': '4', 'blink': '5', 'reverse': '7', 'conceal': '8'}

    text = str(text)
    code_list = []
    if text == '' and len(opts) == 1 and opts[0] == 'reset':
        return '\x1b[%sm' % RESET
    for k, v in kwargs.iteritems():
        if k == 'fg':
            code_list.append(foreground[v])
        elif k == 'bg':
            code_list.append(background[v])
    for o in opts:
        if o in opt_dict:
            code_list.append(opt_dict[o])
    if 'noreset' not in opts:
        text = text + '\x1b[%sm' % RESET
    return ('\x1b[%sm' % ';'.join(code_list)) + text

if __name__ == '__main__':
    try:
        fixliterals(sys.argv[1])
    except (KeyboardInterrupt, SystemExit):
        print
########NEW FILE########
