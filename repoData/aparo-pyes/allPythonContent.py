__FILENAME__ = archive_and_index
#!/usr/bin/env python
#
# Copyright (C) 2010 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

"""This is a template for constructing an external archiver for situations
where one wants to archive posts in Mailman's pipermail archive, but also
wants to invoke some other process on the archived message after its URL
and/or path are known.

It assumes this is invoked by mm_cfg.py settings like
PUBLIC_EXTERNAL_ARCHIVER = '/path/to/Ext_Arch.py %(hostname)s %(listname)s'
PRIVATE_EXTERNAL_ARCHIVER = '/path/to/Ext_Arch.py %(hostname)s %(listname)s'

The path in the sys.path.insert() below must be adjusted to the actual path
to Mailman's bin/ directory, or you can simply put this script in Mailman's
bin/ directory and it will work without the sys.path.insert() and of course,
you must add the code you want to the ext_process function.
"""

import sys
sys.path.insert(0, '/usr/local/mailman/bin') # path to your mailman dir
import paths

import os
import email
import time

from cStringIO import StringIO

from Mailman import Message
from Mailman import MailList
from Mailman.Archiver import HyperArch
from Mailman.Logging.Syslog import syslog
from Mailman.Logging.Utils import LogStdErr

# For debugging, log stderr to Mailman's 'debug' log
LogStdErr('debug', 'mailmanctl', manual_reprime=0)

def ext_process(listname, hostname, url, filepath, msg):
    """Here's where you put your code to deal with the just archived message.

    Arguments here are the list name, the host name, the URL to the just
    archived message, the file system path to the just archived message and
    the message object.

    These can be replaced or augmented as needed.
    """
    from pyes import ES
    from pyes.exceptions import ClusterBlockException, NoServerAvailable
    import datetime

    #CHANGE this settings to reflect your configuration
    _ES_SERVERS = ['127.0.0.1:9500'] # I prefer thrift
    _indexname = "mailman"
    _doctype = "mail"
    date = datetime.datetime.today()

    try:
        iconn = ES(_ES_SERVERS)
        status = None
        try:
            status = iconn.status(_indexname)
            logger.debug("Indexer status:%s" % status)
        except:
            iconn.create_index(_indexname)
            time.sleep(1)
            status = iconn.status(_indexname)
            mappings = { u'text': {'boost': 1.0,
                                     'index': 'analyzed',
                                     'store': 'yes',
                                     'type': u'string',
                                     "term_vector" : "with_positions_offsets"},
                             u'url': {'boost': 1.0,
                                        'index': 'not_analyzed',
                                        'store': 'yes',
                                        'type': u'string',
                                        "term_vector" : "no"},
                             u'title': {'boost': 1.0,
                                        'index': 'analyzed',
                                        'store': 'yes',
                                        'type': u'string',
                                        "term_vector" : "with_positions_offsets"},
                             u'date': {'store': 'yes',
                                        'type': u'date'}}
            time.sleep(1)
            status = iconn.put_mapping(_doctype, mappings, _indexname)


        data = dict(url=url,
                    title=msg.get('subject'),
                    date=date,
                    text=str(msg)
                    )
        iconn.index(data, _indexname, _doctype)

        syslog('debug', 'listname: %s, hostname: %s, url: %s, path: %s, msg: %s',
               listname, hostname, url, filepath, msg)
    except ClusterBlockException:
        syslog('error', 'Cluster in revocery state: listname: %s, hostname: %s, url: %s, path: %s, msg: %s',
               listname, hostname, url, filepath, msg)
    except NoServerAvailable:
        syslog('error', 'No server available: listname: %s, hostname: %s, url: %s, path: %s, msg: %s',
               listname, hostname, url, filepath, msg)
    except:
        import traceback
        syslog('error', 'Unknown: listname: %s, hostname: %s, url: %s, path: %s, msg: %s\nstacktrace: %s',
               listname, hostname, url, filepath, msg, repr(traceback.format_exc()))

    return

def main():
    """This is the mainline.

    It first invokes the pipermail archiver to add the message to the archive,
    then calls the function above to do whatever with the archived message
    after it's URL and path are known.
    """

    listname = sys.argv[2]
    hostname = sys.argv[1]

    # We must get the list unlocked here because it is already locked in
    # ArchRunner. This is safe because we aren't actually changing our list
    # object. ArchRunner's lock plus pipermail's archive lock will prevent
    # any race conditions.
    mlist = MailList.MailList(listname, lock=False)

    # We need a seekable file for processUnixMailbox()
    f = StringIO(sys.stdin.read())

    # If we don't need a Message.Message instance, we can skip the next and
    # the imports of email and Message above.
    msg = email.message_from_file(f, Message.Message)

    h = HyperArch.HyperArchive(mlist)
    # Get the message number for the next message
    sequence = h.sequence
    # and add the message.
    h.processUnixMailbox(f)
    f.close()

    # Get the archive name, etc.
    archive = h.archive
    msgno = '%06d' % sequence
    filename = msgno + '.html'
    filepath = os.path.join(h.basedir, archive, filename)
    h.close()

    url = '%s%s/%s' % (mlist.GetBaseArchiveURL(), archive, filename)

    ext_process(listname, hostname, url, filepath, msg)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-

import sys
import os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
currpath = os.path.dirname(os.path.abspath(__file__))
pyespath = os.path.join(currpath, "pyes")
sys.path.append(pyespath)

#import settings
#from django.core.management import setup_environ
# Commenting out the following line as it is not used.
#from django.conf import settings as dsettings
#setup_environ(settings)
#dsettings.configure()
import pyes as info
sys.path.append(os.path.join(os.path.dirname(__file__), "_ext"))

# -- General configuration -----------------------------------------------------

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage', 'djangodocs']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'PyES Documentation'
copyright = u'2010, Alberto Paro and Elastic Search. All Rights Reserved.'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = info.__version__
# The full version, including alpha/beta/rc tags.
release = info.version_with_meta()

exclude_trees = ['.build']

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'trac'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

html_use_smartypants = True

# If false, no module index is generated.
html_use_modindex = True

# If false, no index is generated.
html_use_index = True

latex_documents = [
  ('index', 'pyes.tex', ur'PyES Documentation',
   ur'Elastic Search', 'manual'),
]

########NEW FILE########
__FILENAME__ = settings

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
"""
Sphinx plugins for Django documentation.
"""

import docutils.nodes
import docutils.transforms
import sphinx
import sphinx.addnodes
import sphinx.directives
import sphinx.environment
import sphinx.roles
from docutils import nodes


def setup(app):
    app.add_crossref_type(
        directivename = "setting",
        rolename = "setting",
        indextemplate = "pair: %s; setting",
    )
    app.add_crossref_type(
        directivename = "templatetag",
        rolename = "ttag",
        indextemplate = "pair: %s; template tag",
    )
    app.add_crossref_type(
        directivename = "templatefilter",
        rolename = "tfilter",
        indextemplate = "pair: %s; template filter",
    )
    app.add_crossref_type(
        directivename = "fieldlookup",
        rolename = "lookup",
        indextemplate = "pair: %s, field lookup type",
    )
    app.add_description_unit(
        directivename = "django-admin",
        rolename = "djadmin",
        indextemplate = "pair: %s; django-admin command",
        parse_node = parse_django_admin_node,
    )
    app.add_description_unit(
        directivename = "django-admin-option",
        rolename = "djadminopt",
        indextemplate = "pair: %s; django-admin command-line option",
        parse_node = lambda env, sig, signode: \
                sphinx.directives.parse_option_desc(signode, sig),
    )
    app.add_config_value('django_next_version', '0.0', True)
    app.add_directive('versionadded', parse_version_directive, 1, (1, 1, 1))
    app.add_directive('versionchanged', parse_version_directive, 1, (1, 1, 1))
    app.add_transform(SuppressBlockquotes)


def parse_version_directive(name, arguments, options, content, lineno,
                      content_offset, block_text, state, state_machine):
    env = state.document.settings.env
    is_nextversion = env.config.django_next_version == arguments[0]
    ret = []
    node = sphinx.addnodes.versionmodified()
    ret.append(node)
    if not is_nextversion:
        if len(arguments) == 1:
            linktext = 'Please, see the release notes <releases-%s>' % (
                    arguments[0])
            xrefs = sphinx.roles.xfileref_role('ref', linktext, linktext,
                                               lineno, state)
            node.extend(xrefs[0])
        node['version'] = arguments[0]
    else:
        node['version'] = "Development version"
    node['type'] = name
    if len(arguments) == 2:
        inodes, messages = state.inline_text(arguments[1], lineno+1)
        node.extend(inodes)
        if content:
            state.nested_parse(content, content_offset, node)
        ret = ret + messages
    env.note_versionchange(node['type'], node['version'], node, lineno)
    return ret


class SuppressBlockquotes(docutils.transforms.Transform):
    """
    Remove the default blockquotes that encase indented list, tables, etc.
    """
    default_priority = 300

    suppress_blockquote_child_nodes = (
        docutils.nodes.bullet_list,
        docutils.nodes.enumerated_list,
        docutils.nodes.definition_list,
        docutils.nodes.literal_block,
        docutils.nodes.doctest_block,
        docutils.nodes.line_block,
        docutils.nodes.table,
    )

    def apply(self):
        for node in self.document.traverse(docutils.nodes.block_quote):
            if len(node.children) == 1 and \
                    isinstance(node.children[0],
                               self.suppress_blockquote_child_nodes):
                node.replace_self(node.children[0])


def parse_django_admin_node(env, sig, signode):
    command = sig.split(' ')[0]
    env._django_curr_admin_command = command
    title = "django-admin.py %s" % sig
    signode += sphinx.addnodes.desc_name(title, title)
    return sig

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
    'mod',
    "djadminopt",
    "ref",
    "setting",
    "term",
    "tfilter",
    "ttag",

    # special
    "skip",
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
        if next_line[0] in "!-/:-@[-`{-~" and \
                all(c == next_line[0] for c in next_line):
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
                colorize("Replace role: ", fg="yellow")).strip().lower()
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
        if default.endswith("()") and \
                replace_type in ("class", "func", "meth"):
            default = default[:-2]
        replace_value = raw_input(
            colorize("Text <target> [", fg="yellow") + default + \
                    colorize("]: ", fg="yellow")).strip()
        if not replace_value:
            replace_value = default
        new.append(":%s:`%s`" % (replace_type, replace_value))
        lastvalues[m.group(1)] = replace_value

    new.append(data[last:])
    open(fname, "w").write("".join(new))

    storage["lastvalues"] = lastvalues
    storage.close()


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
    color_names = ('black', 'red', 'green', 'yellow',
                   'blue', 'magenta', 'cyan', 'white')
    foreground = dict([(color_names[x], '3%s' % x) for x in range(8)])
    background = dict([(color_names[x], '4%s' % x) for x in range(8)])

    RESET = '0'
    opt_dict = {'bold': '1',
                'underscore': '4',
                'blink': '5',
                'reverse': '7',
                'conceal': '8'}

    text = str(text)
    code_list = []
    if text == '' and len(opts) == 1 and opts[0] == 'reset':
        return '\x1b[%sm' % RESET
    for k, v in kwargs.items():
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
__FILENAME__ = migrate_deprecation
__author__ = 'alberto'
import os
import sys
from difflib import unified_diff

MIGRATIONS = [
    ("aliases", "indices.aliases"),
    ("status", "indices.status"),
    ("create_index", "indices.create_index"),
    ("create_index_if_missing", "indices.create_index_if_missing"),
    ("delete_index", "indices.delete_index"),
    ("exists_index", "indices.exists_index"),
    ("delete_index_if_exists", "indices.delete_index_if_exists"),
    ("get_indices", "indices.get_indices"),
    ("get_closed_indices", "indices.get_closed_indices"),
    ("get_alias", "indices.get_alias"),
    ("change_aliases", "indices.change_aliases"),
    ("add_alias", "indices.add_alias"),
    ("delete_alias", "indices.delete_alias"),
    ("set_alias", "indices.set_alias"),
    ("close_index", "indices.close_index"),
    ("open_index", "indices.open_index"),
    ("flush", "indices.flush"),
    ("refresh", "indices.refresh"),
    ("optimize", "indices.optimize"),
    ("analyze", "indices.analyze"),
    ("gateway_snapshot", "indices.gateway_snapshot"),
    ("put_mapping", "indices.put_mapping"),
    ("get_mapping", "indices.get_mapping"),
    ("delete_mapping", "indices.delete_mapping"),
    ("get_settings", "indices.get_settings"),
    ("update_settings", "indices.update_settings"),

    # ("index_stats", "indices.index_stats"),
    # ("put_warmer", "indices.put_warmer"),
    # ("get_warmer", "indices.get_warmer"),
    # ("delete_warmer", "indices.delete_warmer"),
    # update_mapping_meta
    ("cluster_health", "cluster.health"),
    ("cluster_state", "cluster.state"),
    ("cluster_nodes", "cluster.nodes"),
    ("cluster_stats", "cluster.stats"),
]

filenames = [filename for filename in os.listdir("tests") if filename.endswith(".py")]
for filename in filenames:
    print "processing", filename
    path = os.path.join("tests", filename)
    ndata = data = open(path).read()
    for old_name, new_name in MIGRATIONS:
        pos = ndata.find(old_name + "(")
        if ndata[pos - 1] != '.':
            pos = ndata.find(old_name, pos + 1)
            continue
        prefix = new_name.split(".")[0]
        while pos != -1:
            #check if already fixed
            ppos = pos - len(prefix) - 1
            if ppos > 0 and ndata[ppos:pos] == "." + prefix:
                pos = ndata.find(old_name, pos + 1)
                continue
            ndata = ndata[:pos] + new_name + ndata[pos + len(old_name):]
            pos = ndata.find(old_name, pos + len(new_name))
    if data != ndata:
        for line in unified_diff(data.splitlines(1), ndata.splitlines(1), fromfile=path, tofile=path):
            sys.stdout.write(line)
        with open(path, "wb") as fo:
            fo.write(ndata)
########NEW FILE########
__FILENAME__ = generate_dataset
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

def generate_datafile_old(number_items=1000):
    """
    Create the samples.py file
    """
    from utils import get_names, generate_dataset
    from pprint import pprint
    filename = "samples.py"
    dataset = generate_dataset(number_items)
    fo = open(filename, "wb")
    fo.write("#!/usr/bin/env python\n")
    fo.write("# -*- coding: utf-8 -*-\n")
    fo.write("#Brainaetic: http://www.thenetplanet.com\n\n")
    fo.write("SAMPLES = ")
    pprint(dataset, fo)
    fo.close()
    print "%s generated with %d samples" % (filename, number_items)

def generate_datafile(number_items=20000):
    """
    Create the samples.py file
    """
    from utils import generate_dataset_shelve
    filename = "samples.shelve"
    dataset = generate_dataset_shelve(filename, number_items)
    print "%s generated with %d samples" % (filename, number_items)

if __name__ == '__main__':
    """
    Usage: 
            python generate_dataset.py 60000

    (Dataset size defaults to 1000 if not specified)
    """
    try:
        generate_datafile(int(sys.argv[1]))
    except IndexError:
        generate_datafile()

########NEW FILE########
__FILENAME__ = performance
import sys

#sys.path.insert(0, "../")

#from pyes import ES
from brainaetic.echidnasearch.es import ES
from datetime import datetime
import shelve
conn = ES('127.0.0.1:9500')
#conn = ES('192.168.2.50:9200')
try:
    conn.delete_index("test-index")
except:
    pass

dataset = shelve.open("samples.shelve")

mapping = {u'description': {'boost': 1.0,
                            'index': 'analyzed',
                            'store': 'yes',
                            'type': u'string',
                            "term_vector": "with_positions_offsets"
},
           u'name': {'boost': 1.0,
                     'index': 'analyzed',
                     'store': 'yes',
                     'type': u'string',
                     "term_vector": "with_positions_offsets"
           },
           u'age': {'store': 'yes',
                    'type': u'integer'},
           }
conn.create_index("test-index")
conn.put_mapping("test-type", {'properties': mapping}, ["test-index"])

start = datetime.now()
for k, userdata in dataset.items():
#    conn.index(userdata, "test-index", "test-type", k)
    conn.index(userdata, "test-index", "test-type", k, bulk=True)
conn.force_bulk()
end = datetime.now()

print "time:", end - start
dataset.close()


########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
import os
from django.contrib.webdesign.lorem_ipsum import words as li_words
import shelve
import codecs

def get_names():
    """
    Return a list of names.
    """
    return [n.strip() for n in codecs.open(os.path.join("data", "names.txt"),"rb",'utf8').readlines()]

def generate_dataset(number_items=1000):
    """
    Generate a dataset with number_items elements.
    """
    data = []
    names = get_names()
    totalnames = len(names)
    #init random seeder
    random.seed()
    #calculate items
#    names = random.sample(names, number_items)
    for i in range(number_items):
        data.append({"name":names[random.randint(0,totalnames-1)],
                     "age":random.randint(1,100),
                     "description":li_words(50, False)})
    return data

def generate_dataset_shelve(filename, number_items=1000):
    """
    Generate a dataset with number_items elements.
    """
    if os.path.exists(filename):
        os.remove(filename)
    data = shelve.open(filename)
    names = get_names()
    totalnames = len(names)
    #init random seeder
    random.seed()
    #calculate items
#    names = random.sample(names, number_items)
    for i in range(number_items):
        data[str(i+1)] = {"name":names[random.randint(0,totalnames-1)],
                     "age":random.randint(1,100),
                     "description":li_words(50, False)}
    data.close()


########NEW FILE########
__FILENAME__ = aggs
from .utils import EqualityComparableUsingAttributeDictionary
from .filters import Filter, TermFilter, TermsFilter, ANDFilter, NotFilter


class AggFactory(EqualityComparableUsingAttributeDictionary):

    def __init__(self):
        self.aggs = []

    def add(self, agg):
        """Add a term factory"""
        self.aggs.append(agg)

    def reset(self):
        """Reset the aggs"""
        self.aggs = []

    def serialize(self):
        res = {}
        for agg in self.aggs:
            res.update(agg.serialize())
        return res


class Agg(EqualityComparableUsingAttributeDictionary):

    def __init__(self, name, scope=None, nested=None, is_global=None,
                 agg_filter=None, **kwargs):
        self.name = name
        self.scope = scope
        self.nested = nested
        self.is_global = is_global
        self.agg_filter = agg_filter

    def serialize(self):
        data = {self._internal_name: self._serialize()}
        if self.scope is not None:
            data["scope"] = self.scope
        if self.nested is not None:
            data["nested"] = self.nested
        if self.is_global:
            data['global'] = self.is_global
        if self.agg_filter:
            data['agg_filter'] = self.agg_filter.serialize()
        if isinstance(self, BucketAgg):
            return {self.name: data}
        return {self.name: data}

    def _serialize(self):
        raise NotImplementedError

    @property
    def _internal_name(self):
        raise NotImplementedError

    @property
    def _name(self):
        return self.name


class BucketAgg(Agg):
    def __init__(self, name, sub_aggs=None, **kwargs):
        super(BucketAgg, self).__init__(name, **kwargs)
        self.sub_aggs = sub_aggs
        self.name = name

    def serialize(self):
        data = super(BucketAgg, self).serialize()
        sub_data = {}
        if self.sub_aggs is not None:
            for sub_agg in self.sub_aggs:
                if isinstance(sub_agg, Agg):
                    sub_data.update(sub_agg.serialize())
                else:
                    raise RuntimeError("Invalid Agg: Only Stats-Aggregations allowed as Sub-Aggregations")
            data[self.name].update({"aggs": sub_data})
        return data

    @property
    def _internal_name(self):
        raise NotImplementedError


class FilterAgg(BucketAgg):

    _internal_name = "filter"

    def __init__(self, name, filter, **kwargs):
        super(FilterAgg, self).__init__(name, **kwargs)
        self.filter = filter

    def _serialize(self):
        return self.filter.serialize()


class HistogramAgg(BucketAgg):

    _internal_name = "histogram"

    def __init__(self, name, field=None, interval=None, time_interval=None,
                 key_field=None, value_field=None, key_script=None,
                 value_script=None, params=None, **kwargs):
        super(HistogramAgg, self).__init__(name, **kwargs)
        self.field = field
        self.interval = interval
        self.time_interval = time_interval
        self.key_field = key_field
        self.value_field = value_field
        self.key_script = key_script
        self.value_script = value_script
        self.params = params

    def _add_interval(self, data):
        if self.interval:
            data['interval'] = self.interval
        elif self.time_interval:
            data['time_interval'] = self.time_interval
        else:
            raise RuntimeError("Invalid field: interval or time_interval required")

    def _serialize(self):
        data = {}
        if self.field:
            data['field'] = self.field
            self._add_interval(data)
        elif self.key_field:
            data['key_field'] = self.key_field
            if self.value_field:
                data['value_field'] = self.value_field
            else:
                raise RuntimeError("Invalid key_field: value_field required")
            self._add_interval(data)
        elif self.key_script:
            data['key_script'] = self.key_script
            if self.value_script:
                data['value_script'] = self.value_script
            else:
                raise RuntimeError("Invalid key_script: value_script required")
            if self.params:
                data['params'] = self.params
            if self.interval:
                data['interval'] = self.interval
            elif self.time_interval:
                data['time_interval'] = self.time_interval
        return data


class DateHistogramAgg(BucketAgg):

    _internal_name = "date_histogram"

    def __init__(self, name, field=None, interval=None, time_zone=None, pre_zone=None,
                 post_zone=None, factor=None, pre_offset=None, post_offset=None,
                 key_field=None, value_field=None, value_script=None, params=None, **kwargs):
        super(DateHistogramAgg, self).__init__(name, **kwargs)
        self.field = field
        self.interval = interval
        self.time_zone = time_zone
        self.pre_zone = pre_zone
        self.post_zone = post_zone
        self.factor = factor
        self.pre_offset = pre_offset
        self.post_offset = post_offset
        self.key_field = key_field
        self.value_field = value_field
        self.value_script = value_script
        self.params = params


    def _serialize(self):
        data = {}
        if self.interval:
            data['interval'] = self.interval
        else:
            raise RuntimeError("interval required")
        if self.time_zone:
            data['time_zone'] = self.time_zone
        if self.pre_zone:
            data['pre_zone'] = self.pre_zone
        if self.post_zone:
            data['post_zone'] = self.post_zone
        if self.factor:
            data['factor'] = self.factor
        if self.pre_offset:
            data['pre_offset'] = self.pre_offset
        if self.post_offset:
            data['post_offset'] = self.post_offset
        if self.field:
            data['field'] = self.field
        elif self.key_field:
            data['key_field'] = self.key_field
            if self.value_field:
                data['value_field'] = self.value_field
            elif self.value_script:
                data['value_script'] = self.value_script
                if self.params:
                    data['params'] = self.params
            else:
                raise RuntimeError("Invalid key_field: value_field or value_script required")
        return data

class NestedAgg(BucketAgg):
    _internal_name = "nested"

    def __init__(self, name, path, **kwargs):
        super(NestedAgg, self).__init__(name, **kwargs)
        self.path = path

    def _serialize(self):
        data = {}
        data['path'] = self.path
        return data


class RangeAgg(BucketAgg):

    _internal_name = "range"

    def __init__(self, name, field=None, ranges=None, key_field=None, value_field=None,
                 key_script=None, value_script=None, params=None, **kwargs):
        super(RangeAgg, self).__init__(name, **kwargs)
        self.field = field
        self.ranges = ranges or []
        self.key_field = key_field
        self.value_field = value_field
        self.key_script = key_script
        self.value_script = value_script
        self.params = params

    def _serialize(self):
        data = {}
        if not self.ranges:
            raise RuntimeError("Invalid ranges")
        data['ranges'] = self.ranges
        if self.field:
            data['field'] = self.field
        elif self.key_field:
            data['key_field'] = self.key_field
            if self.value_field:
                data['value_field'] = self.value_field
            else:
                raise RuntimeError("Invalid key_field: value_field required")
        elif self.key_script:
            data['key_script'] = self.key_script
            if self.value_script:
                data['value_script'] = self.value_script
            else:
                raise RuntimeError("Invalid key_script: value_script required")
            if self.params:
                data['params'] = self.params
        return data



class StatsAgg(Agg):

    _internal_name = "stats"

    def __init__(self, name, field=None, script=None, params=None, **kwargs):
        super(StatsAgg, self).__init__(name, **kwargs)
        self.field = field
        self.script = script
        self.params = params

    def _serialize(self):
        data = {}
        if self.field:
            data['field'] = self.field
        elif self.script:
            data['script'] = self.script
            if self.params:
                data['params'] = self.params
        return data

class ValueCountAgg(Agg):

    _internal_name = "value_count"

    def __init__(self, name, field=None, script=None, params=None, **kwargs):
        super(ValueCountAgg, self).__init__(name, **kwargs)
        self.field = field
        self.script = script
        self.params = params

    def _serialize(self):
        data = {}
        if self.field:
            data['field'] = self.field
        elif self.script:
            data['script'] = self.script
            if self.params:
                data['params'] = self.params
        return data

class SumAgg(Agg):

    _internal_name = "sum"

    def __init__(self, name, field=None, script=None, params=None, **kwargs):
        super(SumAgg, self).__init__(name, **kwargs)
        self.field = field
        self.script = script
        self.params = params

    def _serialize(self):
        data = {}
        if self.field:
            data['field'] = self.field
        elif self.script:
            data['script'] = self.script
            if self.params:
                data['params'] = self.params
        return data


class AvgAgg(Agg):

    _internal_name = "avg"

    def __init__(self, name, field=None, script=None, params=None, **kwargs):
        super(AvgAgg, self).__init__(name, **kwargs)
        self.field = field
        self.script = script
        self.params = params

    def _serialize(self):
        data = {}
        if self.field:
            data['field'] = self.field
        elif self.script:
            data['script'] = self.script
            if self.params:
                data['params'] = self.params
        return data

class TermsAgg(BucketAgg):

    _internal_name = "terms"

    def __init__(self, name, field=None, fields=None, size=100, order=None,
                 exclude=None, regex=None, regex_flags="DOTALL", script=None,
                 lang=None, all_terms=None, **kwargs):
        super(TermsAgg, self).__init__(name, **kwargs)
        self.field = field
        self.fields = fields
        self.size = size
        self.order = order
        self.exclude = exclude or []
        self.regex = regex
        self.regex_flags = regex_flags
        self.script = script
        self.lang = lang
        self.all_terms = all_terms

    def _serialize(self):
        if not self.fields and not self.field and not self.script:
            raise RuntimeError("Field, Fields or Script is required:%s" % self.order)

        data = {}
        if self.fields:
            data['fields'] = self.fields
        elif self.field:
            data['field'] = self.field

        if self.script:
            data['script'] = self.script
            if self.lang:
                data['lang'] = self.lang
        if self.size is not None:
            data['size'] = self.size
        if self.order:
            if self.order not in ['count', 'term', 'reverse_count', 'reverse_term']:
                raise RuntimeError("Invalid order value:%s" % self.order)
            data['order'] = self.order
        if self.exclude:
            data['exclude'] = self.exclude
        if (self.fields or self.field) and self.regex:
            data['regex'] = self.regex
            if self.regex_flags:
                data['regex_flags'] = self.regex_flags
        if self.all_terms:
            data['all_terms'] = self.all_terms
        return data


class TermStatsAgg(Agg):

    _internal_name = "terms_stats"

    def __init__(self, name, size=10, order=None, key_field=None, value_field=None,
                 key_script=None, value_script=None, params=None, **kwargs):
        super(TermStatsAgg, self).__init__(name, **kwargs)
        self.size = size
        self.ORDER_VALUES = ['term', 'reverse_term', 'count', 'reverse_count',
                             'total', 'reverse_total', 'min', 'reverse_min',
                             'max', 'reverse_max', 'mean', 'reverse_mean']
        self.order = order if order is not None else self.ORDER_VALUES[0]
        self.key_field = key_field
        self.value_field = value_field
        self.key_script = key_script
        self.value_script = value_script
        self.params = params

    def _serialize(self):
        data = {}
        if self.size is not None:
            data['size'] = self.size
        if self.order:
            if self.order not in self.ORDER_VALUES:
                raise RuntimeError("Invalid order value:%s" % self.order)
            data['order'] = self.order

        if self.key_field:
            data['key_field'] = self.key_field
        else:
            raise RuntimeError("key_field required")

        if self.value_field:
            data['value_field'] = self.value_field
        elif self.value_script:
            data['value_script'] = self.value_script
            if self.params:
                data['params'] = self.params
        else:
            raise RuntimeError("Invalid value: value_field OR value_script required")

        return data


class AggQueryWrap(EqualityComparableUsingAttributeDictionary):

    def __init__(self, wrap_object, **kwargs):
        """Base Object for every Filter Object"""
        self.wrap_object = wrap_object

    def serialize(self):
        return {"query": self.wrap_object.serialize()}


########NEW FILE########
__FILENAME__ = connection
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import random
import socket
import threading
import time

from thrift import Thrift
from thrift.transport import TTransport
from thrift.transport import TSocket
from thrift.protocol import TBinaryProtocol
from .pyesthrift import Rest

from .exceptions import NoServerAvailable
from . import logger

__all__ = ['connect', 'connect_thread_local', 'NoServerAvailable']

"""
Work taken from pycassa.

You need installed "thrift" to use this.
Just do a "pip install thrift".

"""

DEFAULT_SERVER = ("thrift", "127.0.0.1", 9500)

class ClientTransport(object):
    """Encapsulation of a client session."""

    def __init__(self, server, framed_transport, timeout, recycle):
        socket = TSocket.TSocket(server.hostname, server.port)
        if timeout is not None:
            socket.setTimeout(timeout * 1000.0)
        if framed_transport:
            transport = TTransport.TFramedTransport(socket)
        else:
            transport = TTransport.TBufferedTransport(socket)
        protocol = TBinaryProtocol.TBinaryProtocolAccelerated(transport)
        client = Rest.Client(protocol)
        transport.open()

        #        server_api_version = client.describe_version().split('.', 1)
        #        assert server_api_version[0] == API_VERSION[0], \
        #                "Thrift API version mismatch. " \
        #                 "(Client: %s, Server: %s)" % (API_VERSION[0], server_api_version[0])

        self.client = client
        self.transport = transport

        if recycle:
            self.recycle = time.time() + recycle + random.uniform(0, recycle * 0.1)
        else:
            self.recycle = None


def connect(servers=None, framed_transport=False, timeout=None,
            retry_time=60, recycle=None, round_robin=None, max_retries=3):
    """
    Constructs a single ElasticSearch connection. Connects to a randomly chosen
    server on the list.

    If the connection fails, it will attempt to connect to each server on the
    list in turn until one succeeds. If it is unable to find an active server,
    it will throw a NoServerAvailable exception.

    Failing servers are kept on a separate list and eventually retried, no
    sooner than `retry_time` seconds after failure.

    :keyword servers: [server]
                      List of ES servers with format: "hostname:port"
                      Default: [("127.0.0.1",9500)]

    :keyword framed_transport: If True, use a TFramedTransport instead of a TBufferedTransport

    :keyword timeout: Timeout in seconds (e.g. 0.5)
                      Default: None (it will stall forever)

    :keyword retry_time: Minimum time in seconds until a failed server is reinstated. (e.g. 0.5)
                         Default: 60

    :keyword recycle:  Max time in seconds before an open connection is closed and returned to the pool.
                       Default: None (Never recycle)

    :keyword max_retries: Max retry time on connection down

    :keyword round_robin: *DEPRECATED*

    :return ES client
    """

    if servers is None:
        servers = [DEFAULT_SERVER]
    return ThreadLocalConnection(servers, framed_transport, timeout,
        retry_time, recycle, max_retries=max_retries)

connect_thread_local = connect


class ServerSet(object):
    """Automatically balanced set of servers.
       Manages a separate stack of failed servers, and automatic
       retrial."""

    def __init__(self, servers, retry_time=10):
        self._lock = threading.RLock()
        self._servers = list(servers)
        self._retry_time = retry_time
        self._dead = []

    def get(self):
        with self._lock:
            if self._dead:
                ts, revived = self._dead.pop()
                if ts > time.time():  # Not yet, put it back
                    self._dead.append((ts, revived))
                else:
                    self._servers.append(revived)
                    logger.info('Server %r reinstated into working pool', revived)
            if not self._servers:
                logger.critical('No servers available')
                raise NoServerAvailable()
            return random.choice(self._servers)

    def mark_dead(self, server):
        with self._lock:
            try:
                self._servers.remove(server)
                self._dead.insert(0, (time.time() + self._retry_time, server))
            except ValueError:
                pass



class ThreadLocalConnection(object):
    def __init__(self, servers, framed_transport=False, timeout=None,
                 retry_time=10, recycle=None, max_retries=3):
        self._servers = ServerSet(servers, retry_time)
        self._framed_transport = framed_transport
        self._timeout = timeout
        self._recycle = recycle
        self._max_retries = max_retries
        self._local = threading.local()

    def __getattr__(self, attr):
        def _client_call(*args, **kwargs):
            for retry in range(self._max_retries + 1):
                try:
                    conn = self._ensure_connection()
                    return getattr(conn.client, attr)(*args, **kwargs)
                except (Thrift.TException, socket.timeout, socket.error) as exc:
                    logger.exception('Client error: %s', exc)
                    self.close()

                    if retry < self._max_retries:
                        continue

                    raise NoServerAvailable(exc)

        setattr(self, attr, _client_call)
        return getattr(self, attr)

    def _ensure_connection(self):
        """Make certain we have a valid connection and return it."""
        conn = self.connect()
        if conn.recycle and conn.recycle < time.time():
            logger.debug('Client session expired after %is. Recycling.', self._recycle)
            self.close()
            conn = self.connect()
        return conn

    def connect(self):
        """Create new connection unless we already have one."""
        if not getattr(self._local, 'conn', None):
            try:
                server = self._servers.get()
                logger.debug('Connecting to %s', server)
                self._local.conn = ClientTransport(server, self._framed_transport,
                    self._timeout, self._recycle)
            except (Thrift.TException, socket.timeout, socket.error):
                logger.warning('Connection to %s failed.', server)
                self._servers.mark_dead(server)
                return self.connect()
        return self._local.conn

    def close(self):
        """If a connection is open, close its transport."""
        if self._local.conn:
            self._local.conn.transport.close()
        self._local.conn = None

########NEW FILE########
__FILENAME__ = connection_http
# -*- coding: utf-8 -*-

from . import logger
from .exceptions import NoServerAvailable
from .fakettypes import Method, RestResponse
from time import time
try:
    #python 2.6/2.7
    from urllib import urlencode
    from urlparse import urlparse
except ImportError:
    #python 3
    from urllib.parse import urlencode
    from urllib.parse import urlparse

import random
import threading
import urllib3
import heapq
from multiprocessing import current_process

__all__ = ["connect"]

DEFAULT_SERVER = ("http", "127.0.0.1", 9200)

POOLS = {}

CERT_REQS = 'CERT_OPTIONAL'

def get_pool():
    if not current_process() in POOLS:
        POOLS[current_process()] = urllib3.PoolManager(cert_reqs=CERT_REQS)
    return POOLS[current_process()]

def update_connection_pool(maxsize=1):
    """Update the global connection pool manager parameters.

    maxsize: Number of connections to save that can be reused (default=1).
             More than 1 is useful in multithreaded situations.
    """
    get_pool().connection_pool_kw.update(maxsize=maxsize)

class Connection(object):
    """An ElasticSearch connection to a randomly chosen server of the list.

    If the connection fails, it attempts to connect to another random server
    of the list until one succeeds. If it is unable to find an active server,
    it throws a NoServerAvailable exception.

    Failing servers are kept on a separate list and eventually retried, no
    sooner than `retry_time` seconds after failure.

    Parameters
    ----------

    servers: List of ES servers represented as (`scheme`, `hostname`, `port`)
             tuples. Default: [("http", "127.0.0.1", 9200)]

    retry_time: Minimum time in seconds until a failed server is reinstated.
                Default: 60

    max_retries: Max number of attempts to connect to some server.

    timeout: Timeout in seconds. Default: None (wait forever)

    basic_auth: Use HTTP Basic Auth. A (`username`, `password`) tuple or a dict
                with `username` and `password` keys.
    """

    def __init__(self, servers=None, retry_time=60, max_retries=3, timeout=None,
                 basic_auth=None):
        if servers is None:
            servers = [DEFAULT_SERVER]
        self._active_servers = [server.geturl() for server in servers]
        self._inactive_servers = []
        self._retry_time = retry_time
        self._max_retries = max_retries
        self._timeout = timeout
        if basic_auth:
            self._headers = urllib3.make_headers(basic_auth="%(username)s:%(password)s" % basic_auth)
        else:
            self._headers = {}
        self._lock = threading.RLock()
        self._local = threading.local()

    def execute(self, request):
        """Execute a request and return a response"""
        url = request.uri
        if request.parameters:
            url += '?' + urlencode(request.parameters)

        if request.headers:
            headers = dict(self._headers, **request.headers)
        else:
            headers = self._headers

        kwargs = dict(
            method=Method._VALUES_TO_NAMES[request.method],
            url=url,
            body=request.body,
            headers=headers,
            timeout=self._timeout,
        )

        retry = 0
        server = getattr(self._local, "server", None)
        while True:
            if not server:
                self._local.server = server = self._get_server()
            try:
                parse_result = urlparse(server)
                conn = get_pool().connection_from_host(parse_result.hostname,
                                                         parse_result.port,
                                                         parse_result.scheme)
                response = conn.urlopen(**kwargs)
                return RestResponse(status=response.status,
                                    body=response.data,
                                    headers=response.headers)
            except (IOError, urllib3.exceptions.HTTPError) as ex:
                self._drop_server(server)
                self._local.server = server = None
                if retry >= self._max_retries:
                    logger.error("Client error: bailing out after %d failed retries",
                                 self._max_retries, exc_info=1)
                    raise NoServerAvailable(ex)
                logger.exception("Client error: %d retries left", self._max_retries - retry)
                retry += 1

    def _get_server(self):
        with self._lock:
            try:
                ts, server = heapq.heappop(self._inactive_servers)
            except IndexError:
                pass
            else:
                if ts > time():  # Not yet, put it back
                    heapq.heappush(self._inactive_servers, (ts, server))
                else:
                    self._active_servers.append(server)
                    logger.info("Restored server %s into active pool", server)

            try:
                return random.choice(self._active_servers)
            except IndexError as ex:
                raise NoServerAvailable(ex)

    def _drop_server(self, server):
        with self._lock:
            try:
                self._active_servers.remove(server)
            except ValueError:
                pass
            else:
                heapq.heappush(self._inactive_servers, (time() + self._retry_time, server))
                logger.warning("Removed server %s from active pool", server)

connect = Connection

########NEW FILE########
__FILENAME__ = mappings
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from future import print_function

from pyes.es import ES
from pyes import mappings

def mappings_to_code(obj, doc_count=0):
    result = []
    odict = obj.as_dict()
    if isinstance(obj, (mappings.DocumentObjectField, mappings.ObjectField, mappings.NestedObject)):
        properties = odict.pop("properties", [])
        doc_count += 1
        kwargs = ["name=%r" % obj.name,
                  "type=%r" % odict.pop("type")] +\
                 ["%s=%r" % (k, odict[k]) for k in sorted(odict.keys())]
        result.append(
            "doc%d=" % doc_count + str(type(obj)).split(".")[-1].strip("'>") + "(" + ', '.join(kwargs) + ")")
        for k in sorted(obj.properties.keys()):
            result.extend(mappings_to_code(obj.properties[k], doc_count))
    else:
        kwargs = ["name=%r" % obj.name,
                  "type=%r" % odict.pop("type"),
                  "store=%r" % obj.store,
                  "index=%r" % odict.pop("index")] +\
                 ["%s=%r" % (k, odict[k]) for k in sorted(odict.keys())]
        result.append("doc%d.add_property(" % doc_count +\
                      str(type(obj)).split(".")[-1].strip("'>") + "(" +\
                      ', '.join(kwargs) + "))")

    return result

if __name__ == '__main__':
    es = ES("192.168.1.1:9200")
    res = mappings_to_code(es.mappings.get_doctype("twitter", "twitter"))
    print("\n".join(res))

########NEW FILE########
__FILENAME__ = convert_errors
# -*- coding: utf-8 -*-


"""
Routines for converting error responses to appropriate exceptions.
"""
from . import exceptions

__all__ = ['raise_if_error']

# Patterns used to map exception strings to classes.

# First, exceptions for which the messages start with the error name,
# and then contain the error description wrapped in [].
exceptions_by_name = dict((name, getattr(exceptions, name))
for name in (
    "DocumentAlreadyExistsEngineException",
    "DocumentAlreadyExistsException",
    "TypeMissingException",
    "VersionConflictEngineException",
    'ClusterBlockException',
    'ElasticSearchIllegalArgumentException',
    'IndexAlreadyExistsException',
    'IndexMissingException',
    'InvalidIndexNameException',
    'MapperParsingException',
    'ReduceSearchPhaseException',
    'ReplicationShardOperationFailedException',
    'SearchPhaseExecutionException',
    'DocumentMissingException',
    )
)

# Second, patterns for exceptions where the message is just the error
# description, and doesn't contain an error name.  These patterns are matched
# at the end of the exception.
exception_patterns_trailing = {
    '] missing': exceptions.NotFoundException,
    '] Already exists': exceptions.AlreadyExistsException,
    }

def raise_if_error(status, result, request=None):
    """Raise an appropriate exception if the result is an error.

    Any result with a status code of 400 or higher is considered an error.

    The exception raised will either be an ElasticSearchException, or a more
    specific subclass of ElasticSearchException if the type is recognised.

    The status code and result can be retrieved from the exception by accessing its
    status and result properties.

    Optionally, this can take the original RestRequest instance which generated
    this error, which will then get included in the exception.

    """
    assert isinstance(status, int)

    if status < 400:
        return

    if status == 404 and isinstance(result, dict) and 'error' not in result:
        raise exceptions.NotFoundException("Item not found", status, result, request)

    if not isinstance(result, dict) or 'error' not in result:
        raise exceptions.ElasticSearchException("Unknown exception type: %d, %s" % (status, result), status,
            result, request)

    error = result['error']
    if '; nested: ' in error:
        error_list = error.split('; nested: ')
        error = error_list[len(error_list) - 1]

    bits = error.split('[', 1)
    if len(bits) == 2:
        excClass = exceptions_by_name.get(bits[0], None)
        if excClass is not None:
            msg = bits[1]
            if msg.endswith(']'):
                msg = msg[:-1]
            '''
            if request:
                msg += ' (' + str(request) + ')'
            '''
            raise excClass(msg, status, result, request)

    for pattern, excClass in list(exception_patterns_trailing.items()):
        if not error.endswith(pattern):
            continue
            # For these exceptions, the returned value is the whole descriptive
        # message.
        raise excClass(error, status, result, request)

    raise exceptions.ElasticSearchException(error, status, result, request)

########NEW FILE########
__FILENAME__ = decorators
#!/usr/bin/env python
# -*- coding: utf-8 -*-


import warnings

from functools import wraps

from .exceptions import ESPendingDeprecationWarning, ESDeprecationWarning

PENDING_DEPRECATION_FMT = """
    %(description)s is scheduled for deprecation in \
    version %(deprecation)s and removal in version v%(removal)s. \
    %(alternative)s
"""

DEPRECATION_FMT = """
    %(description)s is deprecated and scheduled for removal in
    version %(removal)s. %(alternative)s
"""

def warn_deprecated(description=None, deprecation=None, removal=None,
        alternative=None):
    ctx = {"description": description,
           "deprecation": deprecation, "removal": removal,
           "alternative": alternative}
    if deprecation is not None:
        w = ESPendingDeprecationWarning(PENDING_DEPRECATION_FMT % ctx)
    else:
        w = ESDeprecationWarning(DEPRECATION_FMT % ctx)
    warnings.warn(w)


def deprecated(description=None, deprecation=None, removal=None,
        alternative=None):

    def _inner(fun):

        @wraps(fun)
        def __inner(*args, **kwargs):
            from .utils.imports import qualname
            warn_deprecated(description=description or qualname(fun),
                            deprecation=deprecation,
                            removal=removal,
                            alternative=alternative)
            return fun(*args, **kwargs)
        return __inner
    return _inner

########NEW FILE########
__FILENAME__ = djangoutils
# -*- coding: utf-8 -*-
from __future__ import absolute_import

from types import NoneType
import datetime
from django.db import models
import uuid

__author__ = 'Alberto Paro'
__all__ = ["get_values"]


#--- taken from http://djangosnippets.org/snippets/2278/

def get_values(instance, go_into={}, exclude=(), extra=(), skip_none=False):
    """
    Transforms a django model instance into an object that can be used for
    serialization.
    @param instance(django.db.models.Model) - the model in question
    @param go_into(dict) - relations with other models that need expanding
    @param exclude(tuple) - fields that will be ignored
    @param extra(tuple) - additional functions/properties which are not fields
    @param skip_none(bool) - skip None field

    Usage:
    get_values(MyModel.objects.get(pk=187),
               {'user': {'go_into': ('clan',),
                         'exclude': ('crest_blob',),
                         'extra': ('get_crest_path',)}},
               ('image'))

    """
    from django.db.models.manager import Manager
    from django.db.models import Model

    SIMPLE_TYPES = (int, long, str, list, dict, tuple, bool, float, bool,
                    unicode, NoneType)

    if not isinstance(instance, Model):
        raise TypeError("Argument is not a Model")

    value = {
        'pk': instance.pk,
        }

    # check for simple string instead of tuples
    # and dicts; this is shorthand syntax
    if isinstance(go_into, str):
        go_into = {go_into: {}}

    if isinstance(exclude, str):
        exclude = (exclude,)

    if isinstance(extra, str):
        extra = (extra,)

    # process the extra properties/function/whatever
    for field in extra:
        property = getattr(instance, field)

        if callable(property):
            property = property()

        if skip_none and property is None:
            continue
        elif isinstance(property, SIMPLE_TYPES):
            value[field] = property
        else:
            value[field] = repr(property)

    field_options = instance._meta.get_all_field_names()
    for field in field_options:
        try:
            property = getattr(instance, field)
        except:
            continue
        if skip_none and property is None:
            continue

        if field in exclude or field[0] == '_' or isinstance(property, Manager):
            # if it's in the exclude tuple, ignore it
            # if it's a "private" field, ignore it
            # if it's an instance of manager (this means a more complicated
            # relationship), ignore it
            continue
        elif go_into.has_key(field):
            # if it's in the go_into dict, make a recursive call for that field
            try:
                field_go_into = go_into[field].get('go_into', {})
            except AttributeError:
                field_go_into = {}

            try:
                field_exclude = go_into[field].get('exclude', ())
            except AttributeError:
                field_exclude = ()

            try:
                field_extra = go_into[field].get('extra', ())
            except AttributeError:
                field_extra = ()

            value[field] = get_values(property,
                field_go_into,
                field_exclude,
                field_extra, skip_none=skip_none)
        else:
            if isinstance(property, Model):
                # if it's a model, we need it's PK #
                value[field] = property.pk
            elif isinstance(property, (datetime.date,
                                       datetime.time,
                                       datetime.datetime)):
                value[field] = property
            else:
                # else, we just put the value #
                if callable(property):
                    property = property()

                if isinstance(property, SIMPLE_TYPES):
                    value[field] = property
                else:
                    value[field] = repr(property)

    return value


class EmbeddedModel(models.Model):
    _embedded_in = None

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk is None:
            self.pk = str(uuid.uuid4())
        if self._embedded_in  is None:
            raise RuntimeError("Invalid save")
        self._embedded_in.save()

    def serialize(self):
        if self.pk is None:
            self.pk = "TODO"
            self.id = self.pk
        result = {'_app': self._meta.app_label,
                  '_model': self._meta.model_name,
                  '_id': self.pk}
        for field in self._meta.fields:
            result[field.attname] = getattr(self, field.attname)
        return result

########NEW FILE########
__FILENAME__ = es
# -*- coding: utf-8 -*-

import six

from datetime import date, datetime
from decimal import Decimal
if six.PY2:
    from six.moves.urllib.parse import urlencode, urlunsplit, urlparse
else:
    from urllib.parse import urlencode, urlunsplit, urlparse
#    import urllib.request, urllib.parse, urllib.error


import base64
import codecs
import random
import time
import weakref
try:
    import simplejson as json
except ImportError:
    import json

from . import logger
from . import connection_http
from .connection_http import connect as http_connect
from .convert_errors import raise_if_error
#from .decorators import deprecated
from .exceptions import ElasticSearchException, ReduceSearchPhaseException, \
    InvalidQuery, VersionConflictEngineException
from .helpers import SettingsBuilder
from .managers import Indices, Cluster
from .mappings import Mapper
from .models import ElasticSearchModel, DotDict, ListBulker
from .query import Search, Query
from .rivers import River
from .utils import make_path
try:
    from .connection import connect as thrift_connect
    from .pyesthrift.ttypes import Method, RestRequest
except ImportError:
    thrift_connect = None
    from .fakettypes import Method, RestRequest

import six

def file_to_attachment(filename, filehandler=None):
    """
    Convert a file to attachment
    """
    if filehandler:
        return {'_name': filename,
                'content': base64.b64encode(filehandler.read())
        }
    with open(filename, 'rb') as _file:
        return {'_name': filename,
                'content': base64.b64encode(_file.read())
        }


def expand_suggest_text(suggest):
    from itertools import product

    suggested = set()
    all_segments = {}
    for field, tokens in suggest.items():
        if field.startswith(u"_"):
            #we skip _shards
            continue
        if len(tokens) == 1 and not tokens[0]["options"]:
            continue
        texts = []
        for token in tokens:
            if not token["options"]:
                texts.append([(1.0, 1, token["text"])])
                continue
            values = []
            for option in token["options"]:
                values.append((option["score"], option.get("freq", option["score"]), option["text"]))
            texts.append(values)
        for terms in product(*texts):
            score = sum([v for v, _, _ in terms])
            freq = sum([v for _, v, _ in terms])
            text = u' '.join([t for _, _, t in terms])
            if text in all_segments:
                olds, oldf = all_segments[text]
                all_segments[text] = (score + olds, freq + oldf)
            else:
                all_segments[text] = (score, freq)
        #removing dupped
    for t, (s, f) in all_segments.items():
        suggested.add((s, f, t))

    return sorted(suggested, reverse=True)


class ESJsonEncoder(json.JSONEncoder):
    def default(self, value):
        """Convert rogue and mysterious data types.
        Conversion notes:

        - ``datetime.date`` and ``datetime.datetime`` objects are
        converted into datetime strings.
        """

        if isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, date):
            dt = datetime(value.year, value.month, value.day, 0, 0, 0)
            return dt.isoformat()
        elif isinstance(value, Decimal):
            return float(str(value))
        elif isinstance(value, set):
            return list(value)
        # raise TypeError
        return super(ESJsonEncoder, self).default(value)


class ESJsonDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        kwargs['object_hook'] = self.dict_to_object
        super(ESJsonDecoder, self).__init__(*args, **kwargs)

    def string_to_datetime(self, obj):
        """
        Decode a datetime string to a datetime object
        """
        if isinstance(obj, str) and len(obj) == 19:
            try:
                return datetime(*time.strptime(obj, "%Y-%m-%dT%H:%M:%S")[:6])
            except ValueError:
                pass
        if isinstance(obj, str) and len(obj) == 10:
            try:
                return datetime(*time.strptime(obj, "%Y-%m-%d")[:3])
            except ValueError:
                pass
        return obj


    def dict_to_object(self, d):
        """
        Decode datetime value from string to datetime
        """
        for k, v in list(d.items()):
            if isinstance(v, str) and len(v) == 19:
                # Decode a datetime string to a datetime object
                try:
                    d[k] = datetime(*time.strptime(v, "%Y-%m-%dT%H:%M:%S")[:6])
                except ValueError:
                    pass
            elif isinstance(v, list):
                d[k] = [self.string_to_datetime(elem) for elem in v]
        return DotDict(d)


def get_id(text):
    return str(uuid.uuid3(DotDict(bytes=""), text))


class ES(object):
    """
    ES connection object.
    """
    #static to easy overwrite
    encoder = ESJsonEncoder
    decoder = ESJsonDecoder

    def __init__(self, server="localhost:9200", timeout=30.0, bulk_size=400,
                 encoder=None, decoder=None,
                 max_retries=3,
                 default_indices=None,
                 default_types=None,
                 log_curl=False,
                 dump_curl=False,
                 model=ElasticSearchModel,
                 basic_auth=None,
                 raise_on_bulk_item_failure=False,
                 document_object_field=None,
                 bulker_class=ListBulker,
                 cert_reqs='CERT_OPTIONAL'):
        """
        Init a es object.
        Servers can be defined in different forms:

        - host:port with protocol guess (i.e. 127.0.0.1:9200 protocol -> http
                                            127.0.0.1:9500  protocol -> thrift )
        - type://host:port (i.e. http://127.0.0.1:9200  https://127.0.0.1:9200 thrift://127.0.0.1:9500)

        - (type, host, port) (i.e. tuple ("http", "127.0.0.1", "9200") ("https", "127.0.0.1", "9200")
                                         ("thrift", "127.0.0.1", "9500")). This is the prefered form.

        :param server: the server name, it can be a list of servers.
        :param timeout: timeout for a call
        :param bulk_size: size of bulk operation
        :param encoder: tojson encoder
        :param max_retries: number of max retries for server if a server is down
        :param basic_auth: Dictionary with 'username' and 'password' keys for HTTP Basic Auth.
        :param model: used to objectify the dictinary. If None, the raw dict is returned.


        :param dump_curl: If truthy, this will dump every query to a curl file.  If
        this is set to a string value, it names the file that output is sent
        to.  Otherwise, it should be set to an object with a write() method,
        which output will be written to.

        :param raise_on_bulk_item_failure: raises an exception if an item in a
        bulk operation fails

        :param document_object_field: a class to use as base document field in mapper
        """
        if default_indices is None:
            default_indices = ["_all"]
        self.timeout = timeout
        self.default_indices = default_indices
        self.max_retries = max_retries
        self.cluster = None
        self.debug_dump = False
        self.cluster_name = "undefined"
        self.basic_auth = basic_auth
        self.connection = None
        self._mappings = None
        self.document_object_field = document_object_field

        if model is None:
            model = lambda connection, model: model
        self.model = model
        self.log_curl = log_curl
        if dump_curl:
            if isinstance(dump_curl, str):
                self.dump_curl = codecs.open(dump_curl, "wb", "utf8")
            elif hasattr(dump_curl, 'write'):
                self.dump_curl = dump_curl
            else:
                raise TypeError("dump_curl parameter must be supplied with a "
                                "string or an object with a write() method")
        else:
            self.dump_curl = None

        #used in bulk
        self._bulk_size = bulk_size  #size of the bulk
        self.bulker = bulker_class(weakref.proxy(self), bulk_size=bulk_size,
                                   raise_on_bulk_item_failure=raise_on_bulk_item_failure)
        self.bulker_class = bulker_class
        self._raise_on_bulk_item_failure = raise_on_bulk_item_failure

        connection_http.CERT_REQS = cert_reqs

        self.info = {}  #info about the current server
        if encoder:
            self.encoder = encoder
        if decoder:
            self.decoder = decoder
        if isinstance(server, six.string_types):
            self.servers = [server]
        elif isinstance(server, tuple):
            self.servers = [server]
        else:
            self.servers = server

        #init managers
        self.indices = Indices(weakref.proxy(self))
        self.cluster = Cluster(weakref.proxy(self))

        self.default_types = default_types or []
        #check the servers variable
        self._check_servers()
        #init connections
        self._init_connection()


    def __del__(self):
        """
        Destructor
        """
        # Don't bother getting the lock
        if self.bulker and self.bulker.bulk_size>0:
            # It's not safe to rely on the destructor to flush the queue:
            # the Python documentation explicitly states "It is not guaranteed
            # that __del__() methods are called for objects that still exist "
            # when the interpreter exits."
            logger.error("pyes object %s is being destroyed, but bulk "
                         "operations have not been flushed. Call force_bulk()!",
                         self)
            # Do our best to save the client anyway...
            self.bulker.flush_bulk(True)

    def _check_servers(self):
        """Check the servers variable and convert in a valid tuple form"""
        new_servers = []

        def check_format(server):
            if server.scheme not in ["thrift", "http", "https"]:
                raise RuntimeError("Unable to recognize protocol: \"%s\"" % _type)

            if server.scheme == "thrift":
                if not thrift_connect:
                    raise RuntimeError("If you want to use thrift, please install thrift. \"pip install thrift\"")
                if server.port is None:
                    raise RuntimeError("If you want to use thrift, please provide a port number")

            new_servers.append(server)

        for server in self.servers:
            if isinstance(server, (tuple, list)):
                if len(list(server)) != 3:
                    raise RuntimeError("Invalid server definition: \"%s\"" % repr(server))
                _type, host, port = server
                server = urlparse('%s://%s:%s' % (_type, host, port))
                check_format(server)
            elif isinstance(server, six.string_types):
                if server.startswith(("thrift:", "http:", "https:")):
                    server = urlparse(server)
                    check_format(server)
                    continue
                else:
                    tokens = [t for t in server.split(":") if t.strip()]
                    if len(tokens) == 2:
                        host = tokens[0]
                        try:
                            port = int(tokens[1])
                        except ValueError:
                            raise RuntimeError("Invalid port: \"%s\"" % port)

                        if 9200 <= port <= 9299:
                            _type = "http"
                        elif 9500 <= port <= 9599:
                            _type = "thrift"
                        else:
                            raise RuntimeError("Unable to recognize port-type: \"%s\"" % port)

                        server = urlparse('%s://%s:%s' % (_type, host, port))
                        check_format(server)

        self.servers = new_servers

    def _init_connection(self):
        """
        Create initial connection pool
        """
        #detect connectiontype
        if not self.servers:
            raise RuntimeError("No server defined")

        server = random.choice(self.servers)
        if server.scheme in ["http", "https"]:
            self.connection = http_connect(
                [server for server in self.servers if server.scheme in ["http", "https"]],
                timeout=self.timeout, basic_auth=self.basic_auth, max_retries=self.max_retries)
            return
        elif server.scheme == "thrift":
            self.connection = thrift_connect(
                [server for server in self.servers if server.scheme == "thrift"],
                timeout=self.timeout, max_retries=self.max_retries)

    def _discovery(self):
        """
        Find other servers asking nodes to given server
        """
        data = self.cluster_nodes()
        self.cluster_name = data["cluster_name"]
        for _, nodedata in list(data["nodes"].items()):
            server = nodedata['http_address'].replace("]", "").replace("inet[", "http:/")
            if server not in self.servers:
                self.servers.append(server)
        self._init_connection()
        return self.servers

    def _get_bulk_size(self):
        """
        Get the current bulk_size

        :return a int: the size of the bulk holder
        """
        return self._bulk_size

    def _set_bulk_size(self, bulk_size):
        """
        Set the bulk size

        :param bulk_size the bulker size
        """
        self._bulk_size = bulk_size
        self.bulker.bulk_size = bulk_size

    bulk_size = property(_get_bulk_size, _set_bulk_size)

    def _get_raise_on_bulk_item_failure(self):
        """
        Get the raise_on_bulk_item_failure status

        :return a bool: the status of raise_on_bulk_item_failure
        """
        return self._bulk_size

    def _set_raise_on_bulk_item_failure(self, raise_on_bulk_item_failure):
        """
        Set the raise_on_bulk_item_failure parameter

        :param raise_on_bulk_item_failure a bool the status of the raise_on_bulk_item_failure
        """
        self._raise_on_bulk_item_failure = raise_on_bulk_item_failure
        self.bulker.raise_on_bulk_item_failure = raise_on_bulk_item_failure

    raise_on_bulk_item_failure = property(_get_raise_on_bulk_item_failure, _set_raise_on_bulk_item_failure)

    def _send_request(self, method, path, body=None, params=None, headers=None, raw=False, return_response=False):
        if params is None:
            params = {}
        elif "routing" in params and params["routing"] is None:
            del params["routing"]

        path = path.replace("%2C", ",")
        if headers is None:
            headers = {}
        if not path.startswith("/"):
            path = "/" + path
        if not self.connection:
            self._init_connection()
        if body:
            if not isinstance(body, dict) and hasattr(body, "as_dict"):
                body = body.as_dict()
            if isinstance(body, dict):
               body = json.dumps(body, cls=self.encoder)
        else:
            body = ""

        if params:
            for k in params:
                params[k] = str(params[k])
        request = RestRequest(method=Method._NAMES_TO_VALUES[method.upper()],
                              uri=path, parameters=params, headers=headers, body=body)
        if self.dump_curl is not None:
            self.dump_curl.write(("# [%s]" % datetime.now().isoformat()).encode('utf-8'))
            self.dump_curl.write(self._get_curl_request(request).encode('utf-8'))

        if self.log_curl:
            logger.debug(self._get_curl_request(request))

        # execute the request
        response = self.connection.execute(request)

        if self.dump_curl is not None:
            self.dump_curl.write(("# response status: %s"%response.status).encode('utf-8'))
            self.dump_curl.write(("# response body: %s"%response.body).encode('utf-8'))

        if return_response:
            return response

        if method == "HEAD":
            return response.status == 200

        # handle the response
        response_body=response.body
        if six.PY3:
            response_body=response_body.decode(encoding='UTF-8')

        try:
            decoded = json.loads(response_body, cls=self.decoder)
        except ValueError:
            try:
                decoded = json.loads(response_body, cls=ESJsonDecoder)
            except ValueError:
                # The only known place where we get back a body which can't be
                # parsed as JSON is when no handler is found for a request URI.
                # In this case, the body is actually a good message to return
                # in the exception.
                raise ElasticSearchException(response_body, response.status, response_body)
        if response.status not in [200, 201]:
            raise_if_error(response.status, decoded)
        if not raw and isinstance(decoded, dict):
            decoded = DotDict(decoded)
        return decoded

    def _make_path(self, indices, doc_types, *components, **kwargs):
        indices = self._validate_indices(indices)
        if 'allow_all_indices' in kwargs:
            allow_all_indices = kwargs.pop('allow_all_indices')
            if not allow_all_indices and indices == ['_all']:
                indices = []
        if doc_types is None:
            doc_types = self.default_types
        if isinstance(doc_types, str):
            doc_types = [doc_types]
        return make_path(','.join(indices), ','.join(doc_types), *components)

    def _validate_indices(self, indices=None):
        """Return a valid list of indices.

        `indices` may be a string or a list of strings.
        If `indices` is not supplied, returns the default_indices.
        """
        if indices is None:
            indices = self.default_indices
        if isinstance(indices, str):
            indices = [indices]
        return indices

    def validate_types(self, types=None):
        """Return a valid list of types.

        `types` may be a string or a list of strings.
        If `types` is not supplied, returns the default_types.

        """
        types = types or self.default_types
        if types is None:
            types = []
        if isinstance(types, six.string_types):
            types = [types]
        return types

    def _get_curl_request(self, request):
        params = {'pretty': 'true'}
        params.update(request.parameters)
        method = Method._VALUES_TO_NAMES[request.method]
        server = self.servers[0]
        url = urlunsplit((server.scheme, server.netloc, request.uri, urlencode(params), ''))
        curl_cmd = "curl -X%s '%s'" % (method, url)
        body = request.body
        if body:
            if not isinstance(body, str):
                body = str(body, "utf8")
            curl_cmd += " -d '%s'" % body
        return curl_cmd

    def _get_default_indices(self):
        return self._default_indices

    def _set_default_indices(self, indices):
        if indices is None:
            raise ValueError("default_indices cannot be set to None")
        self._default_indices = self._validate_indices(indices)

    default_indices = property(_get_default_indices, _set_default_indices)
    del _get_default_indices, _set_default_indices

    @property
    def mappings(self):
        if self._mappings is None:
            self._mappings = Mapper(self.indices.get_mapping(indices=self.default_indices),
                                    connection=self,
                                    document_object_field=self.document_object_field)
        return self._mappings

    def create_bulker(self):
        """
        Create a bulker object and return it to allow to manage custom bulk policies
        """
        return  self.bulker_class(self, bulk_size=self.bulk_size,
                                  raise_on_bulk_item_failure=self.raise_on_bulk_item_failure)

    def ensure_index(self, index, mappings=None, settings=None, clear=False):
        """
        Ensure if an index with mapping exists
        """
        mappings = mappings or []
        if isinstance(mappings, dict):
            mappings = [mappings]
        exists = self.indices.exists_index(index)
        if exists and not mappings and not clear:
            return
        if exists and clear:
            self.indices.delete_index(index)
            exists = False

        if exists:
            if not mappings:
                self.indices.delete_index(index)
                self.indices.refresh()
                self.indices.create_index(index, settings)
                return

            if clear:
                for maps in mappings:
                    for key in list(maps.keys()):
                        self.indices.delete_mapping(index, doc_type=key)
                self.indices.refresh()
            if isinstance(mappings, SettingsBuilder):
                for name, data in list(mappings.mappings.items()):
                    self.indices.put_mapping(doc_type=name, mapping=data, indices=index)

            else:
                from brainaetic.echidnasearch.mappings import DocumentObjectField, ObjectField

                for maps in mappings:
                    if isinstance(maps, tuple):
                        name, mapping = maps
                        self.indices.put_mapping(doc_type=name, mapping=mapping, indices=index)
                    elif isinstance(maps, dict):
                        for name, data in list(maps.items()):
                            self.indices.put_mapping(doc_type=name, mapping=maps, indices=index)
                    elif isinstance(maps, (DocumentObjectField, ObjectField)):
                        self.put_mapping(doc_type=maps.name, mapping=maps.as_dict(), indices=index)

                return

        if settings:
            if isinstance(settings, dict):
                settings = SettingsBuilder(settings, mappings)
        else:
            if isinstance(mappings, SettingsBuilder):
                settings = mappings
            else:
                settings = SettingsBuilder(mappings=mappings)
        if not exists:
            self.indices.create_index(index, settings)
            self.indices.refresh(index, timesleep=1)

    def put_warmer(self, doc_types=None, indices=None, name=None, warmer=None, querystring_args=None):
        """
        Put new warmer into index (or type)

        :param doc_types: list of document types
        :param warmer: anything with ``serialize`` method or a dictionary
        :param name: warmer name
        :param querystring_args: additional arguments passed as GET params to ES
        """
        if not querystring_args:
            querystring_args = {}
        doc_types_str=''
        if doc_types:
            doc_types_str = '/' + ','.join(doc_types)
        path = '/{0}{1}/_warmer/{2}'.format(','.join(indices), doc_types_str, name)
        if hasattr(warmer, 'serialize'):
            body=warmer.serialize()
        else:
            body=warmer
        return self._send_request(method='PUT', path=path, body=body, params=querystring_args)

    def get_warmer(self, doc_types=None, indices=None, name=None, querystring_args=None):
        """
        Retrieve warmer

        :param doc_types: list of document types
        :param warmer: anything with ``serialize`` method or a dictionary
        :param name: warmer name. If not provided, all warmers will be returned
        :param querystring_args: additional arguments passed as GET params to ES
        """
        name = name or ''
        if not querystring_args:
            querystring_args = {}
        doc_types_str=''
        if doc_types:
            doc_types_str = '/' + ','.join(doc_types)
        path = '/{0}{1}/_warmer/{2}'.format(','.join(indices), doc_types_str, name)

        return self._send_request(method='GET', path=path, params=querystring_args)

    def delete_warmer(self, doc_types=None, indices=None, name=None, querystring_args=None):
        """
        Retrieve warmer

        :param doc_types: list of document types
        :param warmer: anything with ``serialize`` method or a dictionary
        :param name: warmer name. If not provided, all warmers for given indices will be deleted
        :param querystring_args: additional arguments passed as GET params to ES
        """
        name = name or ''
        if not querystring_args:
            querystring_args = {}
        doc_types_str=''
        if doc_types:
            doc_types_str = '/' + ','.join(doc_types)
        path = '/{0}{1}/_warmer/{2}'.format(','.join(indices), doc_types_str, name)

        return self._send_request(method='DELETE', path=path, params=querystring_args)

    def collect_info(self):
        """
        Collect info about the connection and fill the info dictionary.
        """
        try:
            info = {}
            res = self._send_request('GET', "/")
            info['server'] = {}
            info['server']['name'] = res['name']
            info['server']['version'] = res['version']
            info['allinfo'] = res
            info['status'] = self.cluster.status()
            info['aliases'] = self.indices.aliases()
            self.info = info
            return True
        except:
            self.info = {}
            return False

    def index_raw_bulk(self, header, document):
        """
        Function helper for fast inserting

        :param header: a string with the bulk header must be ended with a newline
        :param header: a json document string must be ended with a newline
        """
        self.bulker.add("%s%s" % (header, document))
        return self.flush_bulk()

    def index(self, doc, index, doc_type, id=None, parent=None, force_insert=False,
              op_type=None, bulk=False, version=None, querystring_args=None, ttl=None):
        """
        Index a typed JSON document into a specific index and make it searchable.
        """
        if querystring_args is None:
            querystring_args = {}

        if bulk:
            if op_type is None:
                op_type = "index"
            if force_insert:
                op_type = "create"
            cmd = {op_type: {"_index": index, "_type": doc_type}}
            if parent:
                cmd[op_type]['_parent'] = parent
            if version:
                cmd[op_type]['_version'] = version
            if 'routing' in querystring_args:
                cmd[op_type]['_routing'] = querystring_args['routing']
            if 'percolate' in querystring_args:
                cmd[op_type]['percolate'] = querystring_args['percolate']
            if id is not None:  #None to support 0 as id
                cmd[op_type]['_id'] = id
            if ttl is not None:
                cmd[op_type]['_ttl'] = ttl

            if isinstance(doc, dict):
                doc = json.dumps(doc, cls=self.encoder)
            command = "%s\n%s" % (json.dumps(cmd, cls=self.encoder), doc)
            self.bulker.add(command)
            return self.flush_bulk()

        if force_insert:
            querystring_args['op_type'] = 'create'
        if op_type:
            querystring_args['op_type'] = op_type

        if parent:
            if not isinstance(parent, str):
                parent = str(parent)
            querystring_args['parent'] = parent

        if version:
            if not isinstance(version, str):
                version = str(version)
            querystring_args['version'] = version

        if ttl is not None:
            if not isinstance(ttl, str):
                ttl = str(ttl)
            querystring_args['ttl'] = ttl

        if id is None:
            request_method = 'POST'
        else:
            request_method = 'PUT'

        path = make_path(index, doc_type, id)
        return self._send_request(request_method, path, doc, querystring_args)

    def flush_bulk(self, forced=False):
        """
        Send pending operations if forced or if the bulk threshold is exceeded.
        """
        return self.bulker.flush_bulk(forced)

    def force_bulk(self):
        """
        Force executing of all bulk data.

        Return the bulk response
        """
        return self.flush_bulk(True)

    def put_file(self, filename, index, doc_type, id=None, name=None):
        """
        Store a file in a index
        """
        if id is None:
            request_method = 'POST'
        else:
            request_method = 'PUT'
        path = make_path(index, doc_type, id)
        doc = file_to_attachment(filename)
        if name:
            doc["_name"] = name
        return self._send_request(request_method, path, doc)

    def get_file(self, index, doc_type, id=None):
        """
        Return the filename and memory data stream
        """
        data = self.get(index, doc_type, id)
        return data['_name'], base64.standard_b64decode(data['content'])

    def update(self, index, doc_type, id, script=None, lang="mvel", params=None, document=None, upsert=None,
               model=None, bulk=False, querystring_args=None, retry_on_conflict=None, routing=None, doc_as_upsert=None):
        if querystring_args is None:
            querystring_args = {}

        body = {}
        if script:
            body.update({"script": script, "lang": lang})
        if params:
            body["params"] = params
        if upsert:
            body["upsert"] = upsert
        if document:
            body["doc"] = document
        if doc_as_upsert is not None:
            body["doc_as_upsert"] = doc_as_upsert

        if bulk:
            cmd = {"update": {"_index": index, "_type": doc_type, "_id": id}}
            if retry_on_conflict:
                cmd["update"]['_retry_on_conflict'] = retry_on_conflict
            if routing:
                cmd["update"]['routing'] = routing
            for arg in ("routing", "percolate", "retry_on_conflict"):
                if arg in querystring_args:
                    cmd["update"]['_%s' % arg] = querystring_args[arg]

            command = "%s\n%s" % (json.dumps(cmd, cls=self.encoder), json.dumps(body, cls=self.encoder))
            self.bulker.add(command)
            return self.flush_bulk()
        else:
            if routing is not None:
                querystring_args['routing'] = routing
            if retry_on_conflict is not None:
                body["retry_on_conflict"] = retry_on_conflict

        path = make_path(index, doc_type, id, "_update")
        model = model or self.model
        return model(self, self._send_request('POST', path, body, querystring_args))

    def update_by_function(self, extra_doc, index, doc_type, id, querystring_args=None,
                           update_func=None, attempts=2):
        """
        Update an already indexed typed JSON document.

        The update happens client-side, i.e. the current document is retrieved,
        updated locally and finally pushed to the server. This may repeat up to
        ``attempts`` times in case of version conflicts.

        :param update_func: A callable ``update_func(current_doc, extra_doc)``
            that computes and returns the updated doc. Alternatively it may
            update ``current_doc`` in place and return None. The default
            ``update_func`` is ``dict.update``.

        :param attempts: How many times to retry in case of version conflict.
        """
        if querystring_args is None:
            querystring_args = {}

        if update_func is None:
            update_func = dict.update

        for attempt in range(attempts - 1, -1, -1):
            current_doc = self.get(index, doc_type, id, **querystring_args)
            new_doc = update_func(current_doc, extra_doc)
            if new_doc is None:
                new_doc = current_doc
            try:
                return self.index(new_doc, index, doc_type, id,
                                  version=current_doc._meta.version, querystring_args=querystring_args)
            except VersionConflictEngineException:
                if attempt <= 0:
                    raise
                self.refresh(index)

    def partial_update(self, index, doc_type, id, script, params=None,
                       upsert=None, querystring_args=None):
        """
        Partially update a document with a script
        """
        if querystring_args is None:
            querystring_args = {}

        cmd = {"script": script}

        if params:
            cmd["params"] = params

        if upsert:
            cmd["upsert"] = upsert

        path = make_path(index, doc_type, id, "_update")

        return self._send_request('POST', path, cmd, querystring_args)

    def delete(self, index, doc_type, id, bulk=False, **query_params):
        """
        Delete a typed JSON document from a specific index based on its id.
        If bulk is True, the delete operation is put in bulk mode.
        """
        if bulk:
            cmd = {"delete": {"_index": index, "_type": doc_type,
                              "_id": id}}
            self.bulker.add(json.dumps(cmd, cls=self.encoder))
            return self.flush_bulk()

        path = make_path(index, doc_type, id)
        return self._send_request('DELETE', path, params=query_params)

    def delete_by_query(self, indices, doc_types, query, **query_params):
        """
        Delete documents from one or more indices and one or more types based on a query.
        """
        path = self._make_path(indices, doc_types, '_query')
        body = {"query":self._encode_query(query)}
        return self._send_request('DELETE', path, body, query_params)

    def exists(self, index, doc_type, id, **query_params):
        """
        Return if a document exists
        """
        path = make_path(index, doc_type, id)
        return self._send_request('HEAD', path, params=query_params)

    def get(self, index, doc_type, id, fields=None, model=None, **query_params):
        """
        Get a typed JSON document from an index based on its id.
        """
        path = make_path(index, doc_type, id)
        if fields is not None:
            query_params["fields"] = ",".join(fields)
        model = model or self.model
        return model(self, self._send_request('GET', path, params=query_params))

    def factory_object(self, index, doc_type, data=None, id=None):
        """
        Create a stub object to be manipulated
        """
        data = data or {}
        obj = self.model()
        obj._meta.index = index
        obj._meta.type = doc_type
        obj._meta.connection = self
        if id:
            obj._meta.id = id
        if data:
            obj.update(data)
        return obj

    def mget(self, ids, index=None, doc_type=None, **query_params):
        """
        Get multi JSON documents.

        ids can be:
            list of tuple: (index, type, id)
            list of ids: index and doc_type are required
        """
        if not ids:
            return []

        body = []
        for value in ids:
            if isinstance(value, tuple):
                if len(value) == 3:
                    a, b, c = value
                    body.append({"_index": a,
                                 "_type": b,
                                 "_id": c})
                elif len(value) == 4:
                    a, b, c, d = value
                    body.append({"_index": a,
                                 "_type": b,
                                 "_id": c,
                                 "fields": d})

            else:
                if index is None:
                    raise InvalidQuery("index value is required for id")
                if doc_type is None:
                    raise InvalidQuery("doc_type value is required for id")
                body.append({"_index": index,
                             "_type": doc_type,
                             "_id": value})

        results = self._send_request('GET', "/_mget", body={'docs': body},
                                     params=query_params)
        if 'docs' in results:
            model = self.model
            return [model(self, item) for item in results['docs']]
        return []

    def search_raw(self, query, indices=None, doc_types=None, headers=None, **query_params):
        """Execute a search against one or more indices to get the search hits.

        `query` must be a Search object, a Query object, or a custom
        dictionary of search parameters using the query DSL to be passed
        directly.
        """
        from .query import Search, Query

        if isinstance(query, Query):
            query = query.search()
        if isinstance(query, Search):
            query = query.serialize()
        body = self._encode_query(query)
        path = self._make_path(indices, doc_types, "_search")
        return self._send_request('GET', path, body, params=query_params, headers=headers)

    def search_raw_multi(self, queries, indices_list=None, doc_types_list=None,
                         routing_list=None, search_type_list=None):
        if indices_list is None:
            indices_list = [None] * len(queries)

        if doc_types_list is None:
            doc_types_list = [None] * len(queries)

        if routing_list is None:
            routing_list = [None] * len(queries)

        if search_type_list is None:
            search_type_list = [None] * len(queries)

        queries = [query.search() if isinstance(query, Query)
                   else query.serialize() for query in queries]
        queries = list(map(self._encode_query, queries))
        headers = []
        for index_name, doc_type, routing, search_type in zip(indices_list,
                                                              doc_types_list,
                                                              routing_list,
                                                              search_type_list):
            d = {}
            if index_name is not None:
                d['index'] = index_name
            if doc_type is not None:
                d['type'] = doc_type
            if routing is not None:
                d['routing'] = routing
            if search_type is not None:
                d['search_type'] = search_type

            if d:
                headers.append(d)
            else:
                headers.append('')

        headers = [json.dumps(header) for header in headers]

        body = '\n'.join(['%s\n%s' % (h_q[0], h_q[1]) for h_q in zip(headers, queries)])
        body = '%s\n' % body
        path = self._make_path(None, None, '_msearch')

        return body, self._send_request('GET', path, body)

    def search(self, query, indices=None, doc_types=None, model=None, scan=False, headers=None, **query_params):
        """Execute a search against one or more indices to get the resultset.

        `query` must be a Search object, a Query object, or a custom
        dictionary of search parameters using the query DSL to be passed
        directly.
        """
        if isinstance(query, Search):
            search = query
        elif isinstance(query, (Query, dict)):
            search = Search(query)
        else:
            raise InvalidQuery("search() must be supplied with a Search or Query object, or a dict")

        if scan:
            query_params.setdefault("search_type", "scan")
            query_params.setdefault("scroll", "10m")

        return ResultSet(self, search, indices=indices, doc_types=doc_types,
                         model=model, query_params=query_params, headers=headers)

    def search_multi(self, queries, indices_list=None, doc_types_list=None,
                     routing_list=None, search_type_list=None, models=None, scans=None):
        searches = [query if isinstance(query, Search) else Search(query) for query in queries]

        return ResultSetMulti(self, searches, indices_list=indices_list,
                              doc_types_list=doc_types_list,
                              routing_list=routing_list, search_type_list=None, models=models)


    #    scan method is no longer working due to change in ES.search behavior.  May no longer warrant its own method.
    #    def scan(self, query, indices=None, doc_types=None, scroll="10m", **query_params):
    #        """Return a generator which will scan against one or more indices and iterate over the search hits. (currently support only by ES Master)
    #
    #        `query` must be a Search object, a Query object, or a custom
    #        dictionary of search parameters using the query DSL to be passed
    #        directly.
    #
    #        """
    #        results = self.search(query=query, indices=indices, doc_types=doc_types, search_type="scan", scroll=scroll, **query_params)
    #        while True:
    #            scroll_id = results["_scroll_id"]
    #            results = self._send_request('GET', "_search/scroll", scroll_id, {"scroll":scroll})
    #            total = len(results["hits"]["hits"])
    #            if not total:
    #                break
    #            yield results

    def search_scroll(self, scroll_id, scroll="10m"):
        """
        Executes a scrolling given an scroll_id
        """
        return self._send_request('GET', "_search/scroll", scroll_id, {"scroll": scroll})

    def suggest_from_object(self, suggest, indices=None, preference=None, routing=None, raw=False, **kwargs):
        indices = self.validate_indices(indices)

        path = make_path(','.join(indices), "_suggest")
        querystring_args = {}
        if routing:
            querystring_args["routing"] = routing
        if preference:
            querystring_args["preference"] = preference

        result = self._send_request('POST', path, suggest.serialize(), querystring_args)
        if raw:
            return result
        return expand_suggest_text(result)


    def suggest(self, name, text, field, size=None, **kwargs):
        from .query import Suggest

        suggest = Suggest()
        suggest.add_field(text, name=name, field=field, size=size)
        return self.suggest_from_object(suggest, **kwargs)


    def count(self, query=None, indices=None, doc_types=None, **query_params):
        """
        Execute a query against one or more indices and get hits count.
        """
        from .query import MatchAllQuery

        if query is None:
            query = MatchAllQuery()
        body = self._encode_query(query)
        path = self._make_path(indices, doc_types, "_count")
        return self._send_request('GET', path, body, params=query_params)

    #--- river management
    def create_river(self, river, river_name=None):
        """
        Create a river
        """
        if isinstance(river, River):
            body = river.serialize()
            river_name = river.name
        else:
            body = river
        return self._send_request('PUT', '/_river/%s/_meta' % river_name, body)

    def delete_river(self, river, river_name=None):
        """
        Delete a river
        """
        if isinstance(river, River):
            river_name = river.name
        return self._send_request('DELETE', '/_river/%s/' % river_name)

    #--- settings management

    def update_mapping_meta(self, doc_type, values, indices=None):
        """
        Update mapping meta
        :param doc_type: a doc type or a list of doctypes
        :param values: the dict of meta
        :param indices: a list of indices
        :return:
        """
        indices = self._validate_indices(indices)
        for index in indices:
            mapping = self.mappings.get_doctype(index, doc_type)
            if mapping is None:
                continue
            meta = mapping.get_meta()
            meta.update(values)
            mapping = {doc_type:{"_meta":meta}}
            self.indices.put_mapping(doc_type=doc_type, mapping=mapping, indices=indices)

    def morelikethis(self, index, doc_type, id, fields, **query_params):
        """
        Execute a "more like this" search query against one or more fields and get back search hits.
        """
        path = make_path(index, doc_type, id, '_mlt')
        query_params['fields'] = ','.join(fields)
        body = query_params["body"] if "body" in query_params else None
        return self._send_request('GET', path, body=body, params=query_params)

    def create_percolator(self, index, name, query, **kwargs):
        """
        Create a percolator document

        Any kwargs will be added to the document as extra properties.
        """
        if isinstance(query, Query):
            query = {"query": query.serialize()}
        if not isinstance(query, dict):
            raise InvalidQuery("create_percolator() must be supplied with a Query object or dict")
        if kwargs:
            query.update(kwargs)

        path = make_path('_percolator', index, name)
        body = json.dumps(query, cls=self.encoder)
        return self._send_request('PUT', path, body)

    def delete_percolator(self, index, name):
        """
        Delete a percolator document
        """
        return self.delete('_percolator', index, name)

    def percolate(self, index, doc_types, query):
        """
        Match a query with a document
        """
        if doc_types is None:
            raise RuntimeError('percolate() must be supplied with at least one doc_type')

        path = self._make_path(index, doc_types, '_percolate')
        body = self._encode_query(query)
        return self._send_request('GET', path, body)

    def encode_json(self, serializable):
        """
        Serialize to json a serializable object (Search, Query, Filter, etc).
        """
        return json.dumps(serializable.serialize(), cls=self.encoder)

    def _encode_query(self, query):
        from .query import Query

        if isinstance(query, Query):
            query = query.serialize()
        if isinstance(query, dict):
            return json.dumps(query, cls=self.encoder)

        raise InvalidQuery("`query` must be Query or dict instance, not %s"
                           % query.__class__)

class ResultSetList(object):
    def __init__(self, items, model=None):
        """
        results: an es query results dict
        fix_keys: remove the "_" from every key, useful for django views
        clean_highlight: removed empty highlight
        search: a Search object.
        """

        self.items = items
        self.model = model or self.connection.model
        self.iterpos = 0  #keep track of iterator position
        self._current_item = 0

    @property
    def total(self):
        return len(self.items)

    @property
    def facets(self):
        return {}

    def __len__(self):
        return len(self.items)

    def count(self):
        return len(self.items)

    def __getattr__(self, name):
        if name == "facets":
            return {}
        elif name == "hits":
            return self.items

        # elif name in self._results:
        #     #we manage took, timed_out, _shards
        #     return self._results[name]
        #
        # elif name == "shards" and "_shards" in self._results:
        #     #trick shards -> _shards
        #     return self._results["_shards"]
        # return self._results['hits'][name]
        return None

    def __getitem__(self, val):
        if not isinstance(val, (int, long, slice)):
            raise TypeError('%s indices must be integers, not %s' % (
                self.__class__.__name__, val.__class__.__name__))

        def get_start_end(val):
            if isinstance(val, slice):
                start = val.start
                if not start:
                    start = 0
                end = val.stop or len(self.items)
                if end < 0:
                    end = len(self.items) + end
                if end > len(self.items):
                    end = len(self.items)
                return start, end
            return val, val + 1


        start, end = get_start_end(val)

        if not isinstance(val, slice):
            if len(self.items) == 1:
                return self.items[0]
            raise IndexError
        return [hit for hit in self.items[start:end]]


    def __next__(self):

        if len(self.items) == self.iterpos:
            raise StopIteration
        res = self.items[self.iterpos]
        self.iterpos += 1
        return res

    def __iter__(self):
        self.iterpos = 0
        self._current_item = 0
        return self

    def _search_raw(self, start=None, size=None):

        if start is None and size is None:
            query_params = self.query_params
        else:
            query_params = dict(self.query_params)
            if start is not None:
                query_params["from"] = start
            if size is not None:
                query_params["size"] = size

        return self.connection.search_raw(self.search, indices=self.indices,
                                          doc_types=self.doc_types, **query_params)

    if six.PY2:
        next = __next__

class ResultSet(object):

    def __init__(self, connection, search, indices=None, doc_types=None, query_params=None,
                 headers=None, auto_fix_keys=False, auto_clean_highlight=False, model=None):
        """
        results: an es query results dict
        fix_keys: remove the "_" from every key, useful for django views
        clean_highlight: removed empty highlight
        search: a Search object.
        """
        from .query import Search

        if not isinstance(search, Search):
            raise InvalidQuery("ResultSet must be supplied with a Search object")

        self.search = search
        self.connection = connection
        self.indices = indices
        self.doc_types = doc_types
        self.query_params = query_params or {}
        self.headers = headers
        self.scroller_parameters = {}
        self.scroller_id = None
        self._results = None
        self.model = model or self.connection.model
        self._total = None
        self._max_score = None
        self.valid = False
        self._facets = {}
        self._aggs = {}
        self._hits = []
        self.auto_fix_keys = auto_fix_keys
        self.auto_clean_highlight = auto_clean_highlight

        self.iterpos = 0  #keep track of iterator position
        self.start = query_params.get("start", search.start) or 0
        self._max_item = query_params.get("size", search.size)
        self._current_item = 0
        if search.bulk_read is not None:
            self.chuck_size = search.bulk_read
        elif search.size is not None:
            self.chuck_size = search.size
        else:
            self.chuck_size = 10

    def _do_search(self, auto_increment=False):
        self.iterpos = 0
        process_post_query = True  #used to skip results in first scan
        if self.scroller_id is None:
            if auto_increment:
                self.start += self.chuck_size

            self._results = self._search_raw(self.start, self.chuck_size)

            do_scan = self.query_params.pop("search_type", None) == "scan"
            if do_scan:
                self.scroller_parameters['search_type'] = "scan"
                if 'scroll' in self.query_params:
                    self.scroller_parameters['scroll'] = self.query_params.pop('scroll')
                if 'size' in self.query_params:
                    self.chuck_size = self.scroller_parameters['size'] = self.query_params.pop('size')

            if '_scroll_id' in self._results:
                #scan query, let's load the first bulk of data
                self.scroller_id = self._results['_scroll_id']
                self._do_search()
                process_post_query = False
        else:
            try:
                self._results = self.connection.search_scroll(self.scroller_id,
                                                              self.scroller_parameters.get("scroll", "10m"))
                self.scroller_id = self._results['_scroll_id']
            except ReduceSearchPhaseException:
                #bad hack, should be not hits on the last iteration
                self._results['hits']['hits'] = []

        if process_post_query:
            self._post_process_query()

    def _post_process_query(self):
            self._facets = self._results.get('facets', {})
            self._aggs = self._results.get('aggregations', {})
            if 'hits' in self._results:
                self.valid = True
                self._hits = self._results['hits']['hits']
            else:
                self._hits = []
            if self.auto_fix_keys:
                self._fix_keys()
            if self.auto_clean_highlight:
                self.clean_highlight()

    @property
    def total(self):
        if self._results is None:
            self._do_search()
        if self._total is None:
            self._total = 0
            if self.valid:
                self._total = self._results.get("hits", {}).get('total', 0)
        return self._total

    @property
    def max_score(self):
        if self._results is None:
            self._do_search()
        if self._max_score is None:
            self._max_score = 1.0
            if self.valid:
                self._max_score = self._results.get("hits", {}).get('max_score', 1.0)
        return self._max_score

    @property
    def facets(self):
        if self._results is None:
            self._do_search()
        return self._facets

    @property
    def aggs(self):
        if self._results is None:
            self._do_search()
        return self._aggs

    def fix_facets(self):
        """
        This function convert date_histogram facets to datetime
        """
        facets = self.facets
        for key in list(facets.keys()):
            _type = facets[key].get("_type", "unknown")
            if _type == "date_histogram":
                for entry in facets[key].get("entries", []):
                    for k, v in list(entry.items()):
                        if k in ["count", "max", "min", "total_count", "mean", "total"]:
                            continue
                        if not isinstance(entry[k], datetime):
                            entry[k] = datetime.utcfromtimestamp(v / 1e3)

    def fix_aggs(self):
        """
        This function convert date_histogram aggs to datetime
        """
        aggs = self.aggs
        for key in list(aggs.keys()):
            _type = aggs[key].get("_type", "unknown")
            if _type == "date_histogram":
                for entry in aggs[key].get("entries", []):
                    for k, v in list(entry.items()):
                        if k in ["count", "max", "min", "total_count", "mean", "total"]:
                            continue
                        if not isinstance(entry[k], datetime):
                            entry[k] = datetime.utcfromtimestamp(v / 1e3)

    def __len__(self):
        return self.total

    def count(self):
        return self.total

    def fix_keys(self):
        """
        Remove the _ from the keys of the results
        """
        if not self.valid:
            return

        for hit in self._results['hits']['hits']:
            for key, item in list(hit.items()):
                if key.startswith("_"):
                    hit[key[1:]] = item
                    del hit[key]

    def clean_highlight(self):
        """
        Remove the empty highlight
        """
        if not self.valid:
            return

        for hit in self._results['hits']['hits']:
            if 'highlight' in hit:
                hl = hit['highlight']
                for key, item in list(hl.items()):
                    if not item:
                        del hl[key]

    def __getattr__(self, name):
        if self._results is None:
            self._do_search()
        if name == "facets":
            return self._facets

        elif name == "aggs":
            return self._aggs

        elif name == "hits":
            return self._hits

        elif name in self._results:
            #we manage took, timed_out, _shards
            return self._results[name]

        elif name == "shards" and "_shards" in self._results:
            #trick shards -> _shards
            return self._results["_shards"]
        return self._results['hits'][name]

    def __getitem__(self, val):
        if not isinstance(val, (int, slice)):
            raise TypeError('%s indices must be integers, not %s' % (
                self.__class__.__name__, val.__class__.__name__))

        def get_start_end(val):
            if isinstance(val, slice):
                start = val.start
                if not start:
                    start = 0
                end = val.stop or self.total
                if end < 0:
                    end = self.total + end
                if self._max_item is not None and end > self._max_item:
                    end = self._max_item
                return start, end
            return val, val + 1

        start, end = get_start_end(val)
        model = self.model

        if self._results:
            if start >= 0 and end <= self.start + self.chuck_size and len(self._results['hits']['hits']) > 0 and \
                ("_source" in self._results['hits']['hits'][0] or "_fields" in self._results['hits']['hits'][0]):
                if not isinstance(val, slice):
                    return model(self.connection, self._results['hits']['hits'][val - self.start])
                else:
                    return [model(self.connection, hit) for hit in self._results['hits']['hits'][start:end]]

        results = self._search_raw(start + self.start, end - start)
        hits = results['hits']['hits']
        if not isinstance(val, slice):
            if len(hits) == 1:
                return model(self.connection, hits[0])
            raise IndexError
        return [model(self.connection, hit) for hit in hits]

    def __next__(self):
        if self._max_item is not None and self._current_item == self._max_item:
            raise StopIteration
        if self._results is None:
            self._do_search()
        if "_scroll_id" in self._results and self._total != 0 and self._current_item == 0 and len(
                    self._results["hits"].get("hits", [])) == 0:
            self._do_search()
        if len(self.hits) == 0:
            raise StopIteration
        if self.iterpos < len(self.hits):
            res = self.hits[self.iterpos]
            self.iterpos += 1
            self._current_item += 1
            return self.model(self.connection, res)

        if self.start + self.iterpos == self.total:
            raise StopIteration
        self._do_search(auto_increment=True)
        self.iterpos = 0
        if len(self.hits) == 0:
            raise StopIteration
        res = self.hits[self.iterpos]
        self.iterpos += 1
        self._current_item += 1
        return self.model(self.connection, res)

    if six.PY2:
        next = __next__


    def __iter__(self):
        self.iterpos = 0
        if self._current_item != 0:
            self._results = None
        self._current_item = 0

        return self

    def _search_raw(self, start=None, size=None):
        if start is None and size is None:
            query_params = self.query_params
        else:
            query_params = dict(self.query_params)
            if start is not None:
                query_params["from"] = start
            if size is not None:
                query_params["size"] = size

        return self.connection.search_raw(self.search, indices=self.indices,
                                          doc_types=self.doc_types, headers=self.headers, **query_params)

    def get_suggested_texts(self):
        return expand_suggest_text(self.suggest)


class EmptyResultSet(object):
    def __init__(self, *args, **kwargs):
        """
        An empty resultset
        """


    @property
    def total(self):
        return 0

    @property
    def facets(self):
        return {}

    @property
    def aggs(self):
        return {}

    def __len__(self):
        return self.total

    def count(self):
        return self.total

    def __getitem__(self, val):
        raise IndexError

    def __next__(self):
        raise StopIteration

    def __iter__(self):
        return self

class ResultSetMulti(object):
    def __init__(self, connection, searches, indices_list=None,
                 doc_types_list=None, routing_list=None, search_type_list=None, models=None):
        """
        results: an es query results dict
        fix_keys: remove the "_" from every key, useful for django views
        clean_highlight: removed empty highlight
        search: a Search object.
        """
        for search in searches:
            if not isinstance(search, Search):
                raise InvalidQuery("ResultSet must be supplied with a Search object")

        self.searches = searches
        num_searches = len(self.searches)
        self.connection = connection

        if indices_list is None:
            self.indices_list = [None] * num_searches
        else:
            self.indices_list = indices_list

        if doc_types_list is None:
            self.doc_types_list = [None] * num_searches
        else:
            self.doc_types_list = doc_types_list
        if routing_list is None:
            self.routing_list = [None] * num_searches
        else:
            self.routing_list = routing_list
        if search_type_list is None:
            self.search_type_list = [None] * num_searches
        else:
            self.search_type_list = search_type_list
        self._results_list = None
        self.models = models or self.connection.model
        self._total = None
        self.valid = False
        self.error = None

        self.multi_search_query = None

        self.iterpos = 0
        self._max_item = None

    def _do_search(self):
        self.iterpos = 0

        response = self._search_raw_multi()

        if 'responses' in response:
            responses = response['responses']
            self._results_list = [ResultSet(self.connection, search,
                                            indices=indices, query_params={},
                                            doc_types=doc_types)
                for search, indices, doc_types in
                    zip(self.searches, self.indices_list,
                        self.doc_types_list)]

            for rs, rsp in zip(self._results_list, responses):
                if 'error' in rsp:
                    rs.error = rsp['error']
                else:
                    rs._results = rsp
                    rs._post_process_query()

            self.valid = True

            self._max_item = len(self._results_list or [])
        else:
            self.error = response

    def _search_raw_multi(self):
        self.multi_search_query, result = self.connection.search_raw_multi(
            self.searches, indices_list=self.indices_list,
            doc_types_list=self.doc_types_list, routing_list=self.routing_list,
            search_type_list=self.search_type_list)

        return result

    def __len__(self):
        if self._results_list is None:
            self._do_search()

        return len(self._results_list or [])

    def __getitem__(self, val):
        if not isinstance(val, (int, slice)):
            raise TypeError('%s indices must be integers, not %s' % (
                self.__class__.__name__, val.__class__.__name__))

        if self._results_list is None:
            self._do_search()

        if isinstance(val, slice):
            return self._results_list[val.start:val.stop]

        return self._results_list[val]

    def __iter__(self):
        self.iterpos = 0

        return self

    def __next__(self):
        if self._results_list is None:
            self._do_search()

        if self._max_item is not None and self.iterpos == self._max_item:
            raise StopIteration

        if self._max_item == 0:
            raise StopIteration

        if self.iterpos < self._max_item:
            res = self._results_list[self.iterpos]
            self.iterpos += 1
            return res

        raise StopIteration

    if six.PY2:
        next = __next__


########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-


from .utils import EqualityComparableUsingAttributeDictionary

__author__ = 'Alberto Paro'

__all__ = [
    'ESPendingDeprecationWarning',
    'ESDeprecationWarning',
    'NoServerAvailable',
    "QueryError",
    "NotFoundException",
    "AlreadyExistsException",
    "IndexAlreadyExistsException",
    "IndexMissingException",
    "SearchPhaseExecutionException",
    "InvalidIndexNameException",
    "InvalidSortOrder",
    "InvalidQuery",
    "InvalidParameterQuery",
    "InvalidParameter",
    "QueryParameterError",
    "ScriptFieldsError",
    "ReplicationShardOperationFailedException",
    "ClusterBlockException",
    "MapperParsingException",
    "ElasticSearchException",
    'ReduceSearchPhaseException',
    "VersionConflictEngineException",
    'DocumentAlreadyExistsEngineException',
    "DocumentAlreadyExistsException",
    "TypeMissingException",
    "BulkOperationException",
    "DocumentMissingException"
]

class ESPendingDeprecationWarning(PendingDeprecationWarning):
    pass


class ESDeprecationWarning(DeprecationWarning):
    pass


class NoServerAvailable(Exception):
    pass


class InvalidQuery(Exception):
    pass


class InvalidParameterQuery(InvalidQuery):
    pass


class QueryError(Exception):
    pass


class QueryParameterError(Exception):
    pass


class ScriptFieldsError(Exception):
    pass


class InvalidParameter(Exception):
    pass


class InvalidSortOrder(Exception):
    pass


class ElasticSearchException(Exception):
    """Base class of exceptions raised as a result of parsing an error return
    from ElasticSearch.

    An exception of this class will be raised if no more specific subclass is
    appropriate.

    """

    def __init__(self, error, status=None, result=None, request=None):
        super(ElasticSearchException, self).__init__(error)
        self.status = status
        self.result = result
        self.request = request


class ElasticSearchIllegalArgumentException(ElasticSearchException):
    pass


class IndexMissingException(ElasticSearchException):
    pass


class NotFoundException(ElasticSearchException):
    pass


class AlreadyExistsException(ElasticSearchException):
    pass


class IndexAlreadyExistsException(AlreadyExistsException):
    pass


class InvalidIndexNameException(ElasticSearchException):
    pass


class SearchPhaseExecutionException(ElasticSearchException):
    pass


class ReplicationShardOperationFailedException(ElasticSearchException):
    pass


class ClusterBlockException(ElasticSearchException):
    pass


class MapperParsingException(ElasticSearchException):
    pass


class ReduceSearchPhaseException(ElasticSearchException):
    pass


class VersionConflictEngineException(ElasticSearchException):
    pass


class DocumentAlreadyExistsEngineException(ElasticSearchException):
    pass


class DocumentAlreadyExistsException(ElasticSearchException):
    pass


class TypeMissingException(ElasticSearchException):
    pass


class BulkOperationException(ElasticSearchException, EqualityComparableUsingAttributeDictionary):
    def __init__(self, errors, bulk_result):
        super(BulkOperationException, self).__init__(
            "At least one operation in the bulk request has failed: %s" % errors)
        self.errors = errors
        self.bulk_result = bulk_result

class DocumentMissingException(ElasticSearchException):
    pass

########NEW FILE########
__FILENAME__ = facets
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from .utils import EqualityComparableUsingAttributeDictionary
from .filters import Filter, TermFilter, TermsFilter, ANDFilter, NotFilter


class FacetFactory(EqualityComparableUsingAttributeDictionary):

    def __init__(self):
        self.facets = []

    def add_term_facet(self, *args, **kwargs):
        """Add a term factory facet"""
        self.facets.append(TermFacet(*args, **kwargs))

    def add_date_facet(self, *args, **kwargs):
        """Add a date factory facet"""
        self.facets.append(DateHistogramFacet(*args, **kwargs))

    def add_geo_facet(self, *args, **kwargs):
        """Add a geo factory facet"""
        self.facets.append(GeoDistanceFacet(*args, **kwargs))

    def add(self, facet):
        """Add a term factory"""
        self.facets.append(facet)

    def reset(self):
        """Reset the facets"""
        self.facets = []

    def serialize(self):
        res = {}
        for facet in self.facets:
            res.update(facet.serialize())
        return res


class Facet(EqualityComparableUsingAttributeDictionary):

    def __init__(self, name, scope=None, nested=None, is_global=None,
                 facet_filter=None, **kwargs):
        self.name = name
        self.scope = scope
        self.nested = nested
        self.is_global = is_global
        self.facet_filter = facet_filter

    def serialize(self):
        data = {self._internal_name: self._serialize()}
        if self.scope is not None:
            data["scope"] = self.scope
        if self.nested is not None:
            data["nested"] = self.nested
        if self.is_global:
            data['global'] = self.is_global
        if self.facet_filter:
            data['facet_filter'] = self.facet_filter.serialize()
        return {self.name: data}

    def _serialize(self):
        raise NotImplementedError

    @property
    def _internal_name(self):
        raise NotImplementedError


# TODO: remove these
FacetFilter = Filter
TermFacetFilter = TermFilter
TermsFacetFilter = TermsFilter
ANDFacetFilter = ANDFilter
NotFacetFilter = NotFilter


class QueryFacet(Facet):

    _internal_name = "query"

    def __init__(self, name, query, **kwargs):
        super(QueryFacet, self).__init__(name, **kwargs)
        self.query = query

    def _serialize(self):
        return self.query.serialize()


class FilterFacet(Facet):

    _internal_name = "filter"

    def __init__(self, name, filter, **kwargs):
        super(FilterFacet, self).__init__(name, **kwargs)
        self.filter = filter

    def _serialize(self):
        return self.filter.serialize()


class HistogramFacet(Facet):

    _internal_name = "histogram"

    def __init__(self, name, field=None, interval=None, time_interval=None,
                 key_field=None, value_field=None, key_script=None,
                 value_script=None, params=None, **kwargs):
        super(HistogramFacet, self).__init__(name, **kwargs)
        self.field = field
        self.interval = interval
        self.time_interval = time_interval
        self.key_field = key_field
        self.value_field = value_field
        self.key_script = key_script
        self.value_script = value_script
        self.params = params

    def _add_interval(self, data):
        if self.interval:
            data['interval'] = self.interval
        elif self.time_interval:
            data['time_interval'] = self.time_interval
        else:
            raise RuntimeError("Invalid field: interval or time_interval required")

    def _serialize(self):
        data = {}
        if self.field:
            data['field'] = self.field
            self._add_interval(data)
        elif self.key_field:
            data['key_field'] = self.key_field
            if self.value_field:
                data['value_field'] = self.value_field
            else:
                raise RuntimeError("Invalid key_field: value_field required")
            self._add_interval(data)
        elif self.key_script:
            data['key_script'] = self.key_script
            if self.value_script:
                data['value_script'] = self.value_script
            else:
                raise RuntimeError("Invalid key_script: value_script required")
            if self.params:
                data['params'] = self.params
            if self.interval:
                data['interval'] = self.interval
            elif self.time_interval:
                data['time_interval'] = self.time_interval
        return data


class DateHistogramFacet(Facet):

    _internal_name = "date_histogram"

    def __init__(self, name, field=None, interval=None, time_zone=None, pre_zone=None,
                 post_zone=None, factor=None, pre_offset=None, post_offset=None,
                 key_field=None, value_field=None, value_script=None, params=None, **kwargs):
        super(DateHistogramFacet, self).__init__(name, **kwargs)
        self.field = field
        self.interval = interval
        self.time_zone = time_zone
        self.pre_zone = pre_zone
        self.post_zone = post_zone
        self.factor = factor
        self.pre_offset = pre_offset
        self.post_offset = post_offset
        self.key_field = key_field
        self.value_field = value_field
        self.value_script = value_script
        self.params = params

    def _serialize(self):
        data = {}
        if self.interval:
            data['interval'] = self.interval
        else:
            raise RuntimeError("interval required")
        if self.time_zone:
            data['time_zone'] = self.time_zone
        if self.pre_zone:
            data['pre_zone'] = self.pre_zone
        if self.post_zone:
            data['post_zone'] = self.post_zone
        if self.factor:
            data['factor'] = self.factor
        if self.pre_offset:
            data['pre_offset'] = self.pre_offset
        if self.post_offset:
            data['post_offset'] = self.post_offset
        if self.field:
            data['field'] = self.field
        elif self.key_field:
            data['key_field'] = self.key_field
            if self.value_field:
                data['value_field'] = self.value_field
            elif self.value_script:
                data['value_script'] = self.value_script
                if self.params:
                    data['params'] = self.params
            else:
                raise RuntimeError("Invalid key_field: value_field or value_script required")
        return data


class RangeFacet(Facet):

    _internal_name = "range"

    def __init__(self, name, field=None, ranges=None, key_field=None, value_field=None,
                 key_script=None, value_script=None, params=None, **kwargs):
        super(RangeFacet, self).__init__(name, **kwargs)
        self.field = field
        self.ranges = ranges or []
        self.key_field = key_field
        self.value_field = value_field
        self.key_script = key_script
        self.value_script = value_script
        self.params = params

    def _serialize(self):
        data = {}
        if not self.ranges:
            raise RuntimeError("Invalid ranges")
        data['ranges'] = self.ranges
        if self.field:
            data['field'] = self.field
        elif self.key_field:
            data['key_field'] = self.key_field
            if self.value_field:
                data['value_field'] = self.value_field
            else:
                raise RuntimeError("Invalid key_field: value_field required")
        elif self.key_script:
            data['key_script'] = self.key_script
            if self.value_script:
                data['value_script'] = self.value_script
            else:
                raise RuntimeError("Invalid key_script: value_script required")
            if self.params:
                data['params'] = self.params
        return data


class GeoDistanceFacet(RangeFacet):

    _internal_name = "geo_distance"

    def __init__(self, name, field, pin, ranges=None, value_field=None,
                 value_script=None, distance_unit=None, distance_type=None,
                 params=None, **kwargs):
        super(RangeFacet, self).__init__(name, **kwargs)
        self.field = field
        self.pin = pin
        self.distance_unit = distance_unit
        self.distance_type = distance_type
        self.ranges = ranges or []
        self.value_field = value_field
        self.value_script = value_script
        self.params = params
        self.DISTANCE_TYPES = ['arc', 'plane']
        self.UNITS = ['km', 'mi', 'miles']

    def _serialize(self):
        if not self.ranges:
            raise RuntimeError("Invalid ranges")
        data = {}
        data['ranges'] = self.ranges
        data[self.field] = self.pin
        if self.distance_type:
            if self.distance_type not in self.DISTANCE_TYPES:
                raise RuntimeError("Invalid distance_type: must be one of %s" %
                    self.DISTANCE_TYPES)
            data['distance_type'] = self.distance_type
        if self.distance_unit:
            if self.distance_unit not in self.UNITS:
                raise RuntimeError("Invalid unit: must be one of %s" %
                    self.DISTANCE_TYPES)
            data['unit'] = self.distance_unit
        if self.value_field:
            data['value_field'] = self.value_field
        elif self.value_script:
            data['value_script'] = self.value_script
            if self.params:
                data['params'] = self.params
        return data


class StatisticalFacet(Facet):

    _internal_name = "statistical"

    def __init__(self, name, field=None, script=None, params=None, **kwargs):
        super(StatisticalFacet, self).__init__(name, **kwargs)
        self.field = field
        self.script = script
        self.params = params

    def _serialize(self):
        data = {}
        if self.field:
            data['field'] = self.field
        elif self.script:
            data['script'] = self.script
            if self.params:
                data['params'] = self.params
        return data


class TermFacet(Facet):

    _internal_name = "terms"

    def __init__(self, field=None, fields=None, name=None, size=10, order=None,
                 exclude=None, regex=None, regex_flags="DOTALL", script=None,
                 lang=None, all_terms=None, **kwargs):
        super(TermFacet, self).__init__(name or field, **kwargs)
        self.field = field
        self.fields = fields
        self.size = size
        self.order = order
        self.exclude = exclude or []
        self.regex = regex
        self.regex_flags = regex_flags
        self.script = script
        self.lang = lang
        self.all_terms = all_terms

    def _serialize(self):
        if not self.fields and not self.field and not self.script:
            raise RuntimeError("Field, Fields or Script is required:%s" % self.order)

        data = {}
        if self.fields:
            data['fields'] = self.fields
        elif self.field:
            data['field'] = self.field

        if self.script:
            data['script'] = self.script
            if self.lang:
                data['lang'] = self.lang
        if self.size is not None:
            data['size'] = self.size
        if self.order:
            if self.order not in ['count', 'term', 'reverse_count', 'reverse_term']:
                raise RuntimeError("Invalid order value:%s" % self.order)
            data['order'] = self.order
        if self.exclude:
            data['exclude'] = self.exclude
        if (self.fields or self.field) and self.regex:
            data['regex'] = self.regex
            if self.regex_flags:
                data['regex_flags'] = self.regex_flags
        if self.all_terms:
            data['all_terms'] = self.all_terms
        return data


class TermStatsFacet(Facet):

    _internal_name = "terms_stats"

    def __init__(self, name, size=10, order=None, key_field=None, value_field=None,
                 key_script=None, value_script=None, params=None, **kwargs):
        super(TermStatsFacet, self).__init__(name, **kwargs)
        self.size = size
        self.ORDER_VALUES = ['term', 'reverse_term', 'count', 'reverse_count',
                             'total', 'reverse_total', 'min', 'reverse_min',
                             'max', 'reverse_max', 'mean', 'reverse_mean']
        self.order = order if order is not None else self.ORDER_VALUES[0]
        self.key_field = key_field
        self.value_field = value_field
        self.key_script = key_script
        self.value_script = value_script
        self.params = params

    def _serialize(self):
        data = {}
        if self.size is not None:
            data['size'] = self.size
        if self.order:
            if self.order not in self.ORDER_VALUES:
                raise RuntimeError("Invalid order value:%s" % self.order)
            data['order'] = self.order

        if self.key_field:
            data['key_field'] = self.key_field
        else:
            raise RuntimeError("key_field required")

        if self.value_field:
            data['value_field'] = self.value_field
        elif self.value_script:
            data['value_script'] = self.value_script 
            if self.params:
                data['params'] = self.params
        else:
            raise RuntimeError("Invalid value: value_field OR value_script required")

        return data


class FacetQueryWrap(EqualityComparableUsingAttributeDictionary):

    def __init__(self, wrap_object, **kwargs):
        """Base Object for every Filter Object"""
        self.wrap_object = wrap_object

    def serialize(self):
        return {"query": self.wrap_object.serialize()}

########NEW FILE########
__FILENAME__ = fakettypes
# -*- coding: utf-8 -*-
from __future__ import absolute_import

#
# Fake ttypes to use in http protocol to simulate thrift ones
#

class Method(object):
    GET = 0
    PUT = 1
    POST = 2
    DELETE = 3
    HEAD = 4
    OPTIONS = 5

    _VALUES_TO_NAMES = {
        0: "GET",
        1: "PUT",
        2: "POST",
        3: "DELETE",
        4: "HEAD",
        5: "OPTIONS",
        }

    _NAMES_TO_VALUES = {
        "GET": 0,
        "PUT": 1,
        "POST": 2,
        "DELETE": 3,
        "HEAD": 4,
        "OPTIONS": 5,
        }


class Status(object):
    CONTINUE = 100
    SWITCHING_PROTOCOLS = 101
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NON_AUTHORITATIVE_INFORMATION = 203
    NO_CONTENT = 204
    RESET_CONTENT = 205
    PARTIAL_CONTENT = 206
    MULTI_STATUS = 207
    MULTIPLE_CHOICES = 300
    MOVED_PERMANENTLY = 301
    FOUND = 302
    SEE_OTHER = 303
    NOT_MODIFIED = 304
    USE_PROXY = 305
    TEMPORARY_REDIRECT = 307
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    PAYMENT_REQUIRED = 402
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    NOT_ACCEPTABLE = 406
    PROXY_AUTHENTICATION = 407
    REQUEST_TIMEOUT = 408
    CONFLICT = 409
    GONE = 410
    LENGTH_REQUIRED = 411
    PRECONDITION_FAILED = 412
    REQUEST_ENTITY_TOO_LARGE = 413
    REQUEST_URI_TOO_LONG = 414
    UNSUPPORTED_MEDIA_TYPE = 415
    REQUESTED_RANGE_NOT_SATISFIED = 416
    EXPECTATION_FAILED = 417
    UNPROCESSABLE_ENTITY = 422
    LOCKED = 423
    FAILED_DEPENDENCY = 424
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504
    INSUFFICIENT_STORAGE = 506

    _VALUES_TO_NAMES = {
        100: "CONTINUE",
        101: "SWITCHING_PROTOCOLS",
        200: "OK",
        201: "CREATED",
        202: "ACCEPTED",
        203: "NON_AUTHORITATIVE_INFORMATION",
        204: "NO_CONTENT",
        205: "RESET_CONTENT",
        206: "PARTIAL_CONTENT",
        207: "MULTI_STATUS",
        300: "MULTIPLE_CHOICES",
        301: "MOVED_PERMANENTLY",
        302: "FOUND",
        303: "SEE_OTHER",
        304: "NOT_MODIFIED",
        305: "USE_PROXY",
        307: "TEMPORARY_REDIRECT",
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        402: "PAYMENT_REQUIRED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        406: "NOT_ACCEPTABLE",
        407: "PROXY_AUTHENTICATION",
        408: "REQUEST_TIMEOUT",
        409: "CONFLICT",
        410: "GONE",
        411: "LENGTH_REQUIRED",
        412: "PRECONDITION_FAILED",
        413: "REQUEST_ENTITY_TOO_LARGE",
        414: "REQUEST_URI_TOO_LONG",
        415: "UNSUPPORTED_MEDIA_TYPE",
        416: "REQUESTED_RANGE_NOT_SATISFIED",
        417: "EXPECTATION_FAILED",
        422: "UNPROCESSABLE_ENTITY",
        423: "LOCKED",
        424: "FAILED_DEPENDENCY",
        500: "INTERNAL_SERVER_ERROR",
        501: "NOT_IMPLEMENTED",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT",
        506: "INSUFFICIENT_STORAGE",
        }

    _NAMES_TO_VALUES = {
        "CONTINUE": 100,
        "SWITCHING_PROTOCOLS": 101,
        "OK": 200,
        "CREATED": 201,
        "ACCEPTED": 202,
        "NON_AUTHORITATIVE_INFORMATION": 203,
        "NO_CONTENT": 204,
        "RESET_CONTENT": 205,
        "PARTIAL_CONTENT": 206,
        "MULTI_STATUS": 207,
        "MULTIPLE_CHOICES": 300,
        "MOVED_PERMANENTLY": 301,
        "FOUND": 302,
        "SEE_OTHER": 303,
        "NOT_MODIFIED": 304,
        "USE_PROXY": 305,
        "TEMPORARY_REDIRECT": 307,
        "BAD_REQUEST": 400,
        "UNAUTHORIZED": 401,
        "PAYMENT_REQUIRED": 402,
        "FORBIDDEN": 403,
        "NOT_FOUND": 404,
        "METHOD_NOT_ALLOWED": 405,
        "NOT_ACCEPTABLE": 406,
        "PROXY_AUTHENTICATION": 407,
        "REQUEST_TIMEOUT": 408,
        "CONFLICT": 409,
        "GONE": 410,
        "LENGTH_REQUIRED": 411,
        "PRECONDITION_FAILED": 412,
        "REQUEST_ENTITY_TOO_LARGE": 413,
        "REQUEST_URI_TOO_LONG": 414,
        "UNSUPPORTED_MEDIA_TYPE": 415,
        "REQUESTED_RANGE_NOT_SATISFIED": 416,
        "EXPECTATION_FAILED": 417,
        "UNPROCESSABLE_ENTITY": 422,
        "LOCKED": 423,
        "FAILED_DEPENDENCY": 424,
        "INTERNAL_SERVER_ERROR": 500,
        "NOT_IMPLEMENTED": 501,
        "BAD_GATEWAY": 502,
        "SERVICE_UNAVAILABLE": 503,
        "GATEWAY_TIMEOUT": 504,
        "INSUFFICIENT_STORAGE": 506,
        }


class RestRequest(object):
    """
    Attributes:
     - method
     - uri
     - parameters
     - headers
     - body
    """

    def __init__(self, method=None, uri=None, parameters=None, headers=None, body=None):
        self.method = method
        self.uri = uri
        self.parameters = parameters
        self.headers = headers
        self.body = body

    def __repr__(self):
        full_url = 'http://localhost:9200' + self.uri
        if len(self.parameters) > 0:
            full_url += '?'
            for k, v in self.parameters.items():
                full_url += k + '&' + v

        return "curl -X%s %s -d '%s'" % (
            Method._VALUES_TO_NAMES[self.method],
            full_url,
            self.body,
            )


class RestResponse(object):
    """
    Attributes:
     - status
     - headers
     - body
    """

    def __init__(self, status=None, headers=None, body=None):
        self.status = status
        self.headers = headers
        self.body = body



########NEW FILE########
__FILENAME__ = filters
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import copy

from .exceptions import QueryParameterError
from .utils import ESRange, EqualityComparableUsingAttributeDictionary
from .es import json
import six

class Filter(EqualityComparableUsingAttributeDictionary):

    _extra_properties = ("_cache", "cache_key", "_name")

    def __init__(self, **kwargs):
        self._extra_values = dict((key, kwargs.pop(key))
                              for key in self._extra_properties
                              if kwargs.get(key) is not None)
        if kwargs:
            raise ValueError("Unknown properties: %s" % list(kwargs.keys()))

    def serialize(self):
        data = self._serialize()
        if self._extra_values:
            data.update(self._extra_values)
        return {self._internal_name: data}

    def _serialize(self):
        raise NotImplementedError

    @property
    def _internal_name(self):
        raise NotImplementedError


class FilterList(Filter):

    def __init__(self, filters, **kwargs):
        super(FilterList, self).__init__(**kwargs)
        self.filters = filters

    def _serialize(self):
        if not self.filters:
            raise RuntimeError("At least one filter must be declared")
        serialized = [filter.serialize() for filter in self.filters]
        if self._extra_values:
            serialized = {"filters": serialized}
        return serialized

    def __iter__(self):
        return iter(self.filters)


class ANDFilter(FilterList):
    """
    A filter that matches combinations of other filters using the AND operator

    Example:

    t1 = TermFilter('name', 'john')
    t2 = TermFilter('name', 'smith')
    f = ANDFilter([t1, t2])
    q = FilteredQuery(MatchAllQuery(), f)
    results = conn.search(q)

    """
    _internal_name = "and"


class ORFilter(FilterList):
    """
    A filter that matches combinations of other filters using the OR operator

    Example:

    t1 = TermFilter('name', 'john')
    t2 = TermFilter('name', 'smith')
    f = ORFilter([t1, t2])
    q = FilteredQuery(MatchAllQuery(), f)
    results = conn.search(q)

    """
    _internal_name = "or"


class BoolFilter(Filter):
    """
    A filter that matches documents matching boolean combinations of other
    queries. Similar in concept to Boolean query, except that the clauses are
    other filters. Can be placed within queries that accept a filter.
    """

    _internal_name = "bool"

    def __init__(self, must=None, must_not=None, should=None,
                 minimum_number_should_match=None,
                 **kwargs):
        super(BoolFilter, self).__init__(**kwargs)

        self._must = []
        self._must_not = []
        self._should = []
        self.minimum_number_should_match = minimum_number_should_match
        if must:
            self.add_must(must)

        if must_not:
            self.add_must_not(must_not)

        if should:
            self.add_should(should)

    def add_must(self, queries):
        if isinstance(queries, list):
            self._must.extend(queries)
        else:
            self._must.append(queries)

    def add_must_not(self, queries):
        if isinstance(queries, list):
            self._must_not.extend(queries)
        else:
            self._must_not.append(queries)

    def add_should(self, queries):
        if isinstance(queries, list):
            self._should.extend(queries)
        else:
            self._should.append(queries)

    def is_empty(self):
        return not any([self._must, self._must_not, self._should])

    def _serialize(self):
        filters = {}
        if self.minimum_number_should_match:
            filters["minimum_number_should_match"] = self.minimum_number_should_match
        if self._must:
            filters["must"] = [f.serialize() for f in self._must]
        if self._must_not:
            filters["must_not"] = [f.serialize() for f in self._must_not]
        if self._should:
            filters["should"] = [f.serialize() for f in self._should]
        if not filters:
            raise RuntimeError("A least a filter must be declared")
        return filters


class NotFilter(Filter):

    _internal_name = "not"

    def __init__(self, filter, **kwargs):
        super(NotFilter, self).__init__(**kwargs)
        self.filter = filter

    def _serialize(self):
        if not isinstance(self.filter, Filter):
            raise RuntimeError("NotFilter argument should be a Filter")
        return {"filter": self.filter.serialize()}


class RangeFilter(Filter):

    _internal_name = "range"

    def __init__(self, qrange=None, **kwargs):
        super(RangeFilter, self).__init__(**kwargs)
        self.ranges = []
        if qrange:
            self.add(qrange)

    def add(self, qrange):
        if isinstance(qrange, list):
            self.ranges.extend(qrange)
        elif isinstance(qrange, ESRange):
            self.ranges.append(qrange)

    def negate(self):
        """Negate some ranges: useful to resolve a NotFilter(RangeFilter(**))"""
        for r in self.ranges:
            r.negate()

    def _serialize(self):
        if not self.ranges:
            raise RuntimeError("A least a range must be declared")
        return dict([r.serialize() for r in self.ranges])

NumericRangeFilter = RangeFilter


class PrefixFilter(Filter):

    _internal_name = "prefix"

    def __init__(self, field=None, prefix=None, **kwargs):
        super(PrefixFilter, self).__init__(**kwargs)
        self._values = {}

        if field is not None and prefix is not None:
            self.add(field, prefix)

    def add(self, field, prefix):
        self._values[field] = prefix

    def _serialize(self):
        if not self._values:
            raise RuntimeError("A least a field/prefix pair must be added")
        return self._values


class ScriptFilter(Filter):

    _internal_name = "script"

    def __init__(self, script, params=None, lang=None, **kwargs):
        super(ScriptFilter, self).__init__(**kwargs)
        self.script = script
        self.params = params
        self.lang = lang

    def add(self, field, value):
        self.params[field] = {"value": value}

    def _serialize(self):
        data = {"script": self.script}
        if self.params is not None:
            data["params"] = self.params
        if self.lang is not None:
            data["lang"] = self.lang
        return data


class TermFilter(Filter):

    _internal_name = "term"

    def __init__(self, field=None, value=None, **kwargs):
        super(TermFilter, self).__init__(**kwargs)
        self._values = {}
        if field is not None and value is not None:
            self.add(field, value)

    def add(self, field, value):
        self._values[field] = value

    def _serialize(self):
        if not self._values:
            raise RuntimeError("A least a field/value pair must be added")
        return self._values


class TypeFilter(Filter):

    _internal_name = "type"

    def __init__(self, type, **kwargs):
        super(TypeFilter, self).__init__(**kwargs)
        self.type = type

    def _serialize(self):
        return {"value": self.type}


class ExistsFilter(Filter):

    _internal_name = "exists"

    def __init__(self, field, **kwargs):
        super(ExistsFilter, self).__init__(**kwargs)
        self.field = field

    def _serialize(self):
        return {"field": self.field}


class MissingFilter(Filter):

    _internal_name = "missing"

    def __init__(self, field, existence=None, null_value=None, **kwargs):
        super(MissingFilter, self).__init__(**kwargs)
        self.field = field
        self.existence = existence
        self.null_value = null_value

    def _serialize(self):
        ret = {"field": self.field}

        if self.existence is not None:
            ret['existence'] = self.existence
        if self.null_value is not None:
            ret['null_value'] = self.null_value

        return ret


class RegexTermFilter(Filter):

    _internal_name = "regex_term"

    def __init__(self, field=None, value=None, ignorecase=False, **kwargs):
        super(RegexTermFilter, self).__init__(**kwargs)
        self._values = {}
        self.ignorecase = ignorecase
        if field is not None and value is not None:
            self.add(field, value, ignorecase=ignorecase)

    def add(self, field, value, ignorecase=False):
        if ignorecase:
            self._values[field] = {"term":value, "ignorecase":ignorecase}
        else:
            self._values[field] = value

    def _serialize(self):
        if not self._values:
            raise RuntimeError("A least a field/value pair must be added")
        return self._values


class LimitFilter(Filter):

    _internal_name = "limit"

    def __init__(self, value=100, **kwargs):
        super(LimitFilter, self).__init__(**kwargs)
        self.value = value

    def _serialize(self):
        return {"value": self.value}


class TermsFilter(Filter):

    _internal_name = "terms"

    def __init__(self, field=None, values=None, execution=None, **kwargs):
        super(TermsFilter, self).__init__(**kwargs)
        self._values = {}
        self.execution = execution
        if field is not None and values is not None:
            self.add(field, values)

    def add(self, field, values):
        self._values[field] = values

    def _serialize(self):
        if not self._values:
            raise RuntimeError("A least a field/value pair must be added")
        data = self._values.copy()
        if self.execution:
            data["execution"] = self.execution
        return data


class QueryFilter(Filter):

    _internal_name = "query"

    def __init__(self, query, **kwargs):
        super(QueryFilter, self).__init__(**kwargs)
        self._query = query

    def _serialize(self):
        if not self._query:
            raise RuntimeError("A least a field/value pair must be added")
        return self._query.serialize()

#
#--- Geo Queries
#http://www.elasticsearch.com/blog/2010/08/16/geo_location_and_search.html

class GeoDistanceFilter(Filter):
    """http://github.com/elasticsearch/elasticsearch/issues/279"""

    _internal_name = "geo_distance"

    def __init__(self, field, location, distance, distance_type="arc", distance_unit=None, optimize_bbox="memory", **kwargs):
        super(GeoDistanceFilter, self).__init__(**kwargs)
        self.field = field
        self.location = location
        self.distance = distance
        self.distance_type = distance_type
        self.distance_unit = distance_unit
        self.optimize_bbox = optimize_bbox

    def _serialize(self):
        if self.distance_type not in ["arc", "plane"]:
            raise QueryParameterError("Invalid distance_type")

        params = {"distance": self.distance, self.field: self.location}
        if self.distance_type != "arc":
            params["distance_type"] = self.distance_type

        if self.distance_unit:
            if self.distance_unit not in ["km", "mi", "miles"]:
                raise QueryParameterError("Invalid distance_unit")
            params["unit"] = self.distance_unit

        if self.optimize_bbox:
            if self.optimize_bbox not in ["memory", "indexed"]:
                raise QueryParameterError("Invalid optimize_bbox")
            params['optimize_bbox'] = self.optimize_bbox

        return params


class GeoBoundingBoxFilter(Filter):
    """http://github.com/elasticsearch/elasticsearch/issues/290"""

    _internal_name = "geo_bounding_box"

    def __init__(self, field, location_tl, location_br, **kwargs):
        super(GeoBoundingBoxFilter, self).__init__(**kwargs)
        self.field = field
        self.location_tl = location_tl
        self.location_br = location_br

    def _serialize(self):
        return {self.field: {"top_left": self.location_tl,
                             "bottom_right": self.location_br}}


class GeoPolygonFilter(Filter):
    """http://github.com/elasticsearch/elasticsearch/issues/294"""

    _internal_name = "geo_polygon"

    def __init__(self, field, points, **kwargs):
        super(GeoPolygonFilter, self).__init__(**kwargs)
        self.field = field
        self.points = points

    def _serialize(self):
        return {self.field: {"points": self.points}}


class GeoShapeFilter(Filter):
    """http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/query-dsl-geo-shape-filter.html"""

    _internal_name = 'geo_shape'

    def __init__(self, field=None, coordinates=None, type=None, **kwargs):
        super(GeoShapeFilter, self).__init__(**kwargs)
        self.field = field
        self.coordinates = coordinates
        self.type = type

    def _serialize(self):
        return {
            self.field: {
                'shape': {
                    'type': self.type,
                    'coordinates': self.coordinates
                }
            }
        }


class MatchAllFilter(Filter):
    """A filter that matches on all documents"""

    _internal_name = "match_all"

    def __init__(self, **kwargs):
        super(MatchAllFilter, self).__init__(**kwargs)

    def _serialize(self):
        return {}


class HasFilter(Filter):

    def __init__(self, type, query, _scope=None, **kwargs):
        super(HasFilter, self).__init__(**kwargs)
        self.query = query
        self.type = type
        self._scope = _scope

    def _serialize(self):
        data = {"query": self.query.serialize(), "type": self.type}
        if self._scope is not None:
            data["_scope"] = self._scope
        return data


class HasChildFilter(HasFilter):
    """
    The has_child filter accepts a query and the child type to run against,
    and results in parent documents that have child docs matching the query
    """

    _internal_name = "has_child"


class HasParentFilter(HasFilter):
    """
    The has_parent filter accepts a query and the parent type to run against,
    and results in child documents that have parent docs matching the query
    """

    _internal_name = "has_parent"


class NestedFilter(Filter):
    """
    A nested filter, works in a similar fashion to the nested query, except
    used as a filter. It follows exactly the same structure, but also allows
    to cache the results (set _cache to true), and have it named
    (set the _name value).
    """

    _internal_name = "nested"

    def __init__(self, path, filter, **kwargs):
        super(NestedFilter, self).__init__(**kwargs)
        self.path = path
        self.filter = filter

    def _serialize(self):
        return {"path": self.path, "query": self.filter.serialize()}


class IdsFilter(Filter):

    _internal_name = "ids"

    def __init__(self, values, type=None, **kwargs):
        super(IdsFilter, self).__init__(**kwargs)
        self.type = type
        self.values = values

    def _serialize(self):
        data = {}
        if self.type:
            data["type"] = self.type
        if isinstance(self.values, six.string_types):
            data["values"] = [self.values]
        else:
            data["values"] = self.values
        return data


class RawFilter(Filter):
    """Uses exactly the filter provided as an ES filter."""

    def __init__(self, filter_text_or_dict, **kwargs):
        super(RawFilter, self).__init__(**kwargs)
        if isinstance(filter_text_or_dict, six.string_types):
            self._filter = json.loads(filter_text_or_dict)
        else:
            self._filter = filter_text_or_dict

    def serialize(self):
        return self._filter

########NEW FILE########
__FILENAME__ = helpers
# -*- coding: utf-8 -*-

class SettingsBuilder(object):
    def __init__(self, settings=None, mappings=None):
        self.settings = settings or {'index.number_of_replicas': 1,
                                     "index.number_of_shards": 5}
        self.mappings = {}
        if mappings:
            self.add_mapping(mappings)

    def add_mapping(self, data, name=None):
        """
        Add a new mapping
        """
        from .mappings import DocumentObjectField
        from .mappings import NestedObject
        from .mappings import ObjectField

        if isinstance(data, (DocumentObjectField, ObjectField, NestedObject)):
            self.mappings[data.name] = data.as_dict()
            return

        if name:
            self.mappings[name] = data
            return
            if isinstance(data, dict):
                self.mappings.update(data)
            elif isinstance(data, list):
                for d in data:
                    if isinstance(d, dict):
                        self.mappings.update(d)
                    elif isinstance(d, DocumentObjectField):
                        self.mappings[d.name] = d.as_dict()
                    else:
                        name, data = d
                        self.add_mapping(data, name)

    def as_dict(self):
        """Returns a dict"""
        return {"settings": self.settings,
                "mappings": self.mappings}


class StatusProcessor(object):
    def __init__(self, connection):
        self.connection = connection
        self.cstate = connection.cluster_state()
        self.cstatus = connection.status()
        self.cnodes = connection.cluster_nodes()
        nodes = [({"code":k, "name":v["name"]}, v["transport_address"]) for k, v in self.cstate.nodes.items()]
        nodes = sorted(nodes, key=lambda v: v[0]["name"])
        self.node_names = [k for k, v in nodes]

    def get_indices_data(self):
        indices_names = sorted(self.cstatus.indices.keys())
        data = {}
        for indexname in indices_names:
            data['name'] = indexname
            data['data'] = self.cstatus.indices[indexname]
            nodes = []
            for nodename in self.node_names:
                shards = []
                for shardid, shards_replica in sorted(data['data']['shards'].items()):
                    for shard in shards_replica:
                        if shard["routing"]['node'] == nodename["code"]:
                            shards.append((shardid, shard))
                nodes.append((nodename["name"], shards))
            data['nodes'] = nodes
            yield data
            data = {}

########NEW FILE########
__FILENAME__ = highlight
# -*- coding: utf-8 -*-

class HighLighter(object):
    """
    This object manage the highlighting

    :arg pre_tags: list of tags before the highlighted text.
        importance is ordered..  ex. ``['<b>']``
    :arg post_tags: list of end tags after the highlighted text.
        should line up with pre_tags.  ex. ``['</b>']``
    :arg fields: list of fields to highlight
    :arg fragment_size: the size of the grament
    :arg number_or_fragments: the maximum number of fragments to
        return; if 0, then no fragments are returned and instead the
        entire field is returned and highlighted.
    :arg fragment_offset: controls the margin to highlight from

    Use this with a :py:class:`pyes.query.Search` like this::

        h = HighLighter(['<b>'], ['</b>'])
        s = Search(TermQuery('foo'), highlight=h)
    """

    def __init__(self, pre_tags=None, post_tags=None, fields=None, fragment_size=None, number_of_fragments=None,
                 fragment_offset=None, encoder=None):
        self.pre_tags = pre_tags
        self.post_tags = post_tags
        self.fields = fields or {}
        self.fragment_size = fragment_size
        self.number_of_fragments = number_of_fragments
        self.fragment_offset = fragment_offset
        self.encoder = encoder

    def add_field(self, name, fragment_size=150, number_of_fragments=3, fragment_offset=None, order="score", type=None):
        """
        Add a field to Highlinghter
        """
        data = {}
        if fragment_size:
            data['fragment_size'] = fragment_size
        if number_of_fragments is not None:
            data['number_of_fragments'] = number_of_fragments
        if fragment_offset is not None:
            data['fragment_offset'] = fragment_offset
        if type is not None:
            data['type'] = type
        data['order'] = order
        self.fields[name] = data

    def serialize(self):
        res = {}
        if self.pre_tags:
            res["pre_tags"] = self.pre_tags
        if self.post_tags:
            res["post_tags"] = self.post_tags
        if self.fragment_size:
            res["fragment_size"] = self.fragment_size
        if self.number_of_fragments:
            res["number_of_fragments"] = self.number_of_fragments
        if self.fragment_offset:
            res["fragment_offset"] = self.fragment_offset
        if self.encoder:
            res["encoder"] = self.encoder
        if self.fields:
            res["fields"] = self.fields
        else:
            res["fields"] = {"_all": {}}
        return res

########NEW FILE########
__FILENAME__ = managers
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
from .exceptions import IndexAlreadyExistsException, IndexMissingException
from .utils import make_path
from .filters import Filter
from .mappings import Mapper
import six

class Indices(object):
    alias_params = ['filter', 'routing', 'search_routing', 'index_routing']

    def __init__(self, conn):
        self.conn = conn

    #TODO: clearcache segments templates

    #Alias Management - START
    def aliases(self, indices=None):
        """
        Retrieve the aliases of one or more indices.
        ( See :ref:`es-guide-reference-api-admin-indices-aliases`)

        :keyword indices: an index or a list of indices

        """
        path = self.conn._make_path(indices, (), '_aliases')
        return self.conn._send_request('GET', path)

    def get_alias(self, alias):
        """
        Get the index or indices pointed to by a given alias.
        (See :ref:`es-guide-reference-api-admin-indices-aliases`)

        :param alias: the name of an alias

        :return returns a list of index names.
        :raise IndexMissingException if the alias does not exist.

        """
        status = self.status([alias])
        return status['indices'].keys()

    def change_aliases(self, commands):
        """
        Change the aliases stored.
        (See :ref:`es-guide-reference-api-admin-indices-aliases`)

        :param commands: is a list of 3-tuples; (command, index, alias), where
                         `command` is one of "add" or "remove", and `index` and
                         `alias` are the index and alias to add or remove.

        """
        body = {'actions': [{command: dict(index=index, alias=alias, **params)}
                            for (command, index, alias, params) in commands]}
        return self.conn._send_request('POST', "_aliases", body)

    def _get_alias_params(self, **kwargs):
        ret = {}
        for name, value in kwargs.items():
            if name in self.alias_params and value:
                if isinstance(value, Filter):
                    ret[name] = value.serialize()
                else:
                    ret[name] = value

        return ret

    def add_alias(self, alias, indices, **kwargs):
        """
        Add an alias to point to a set of indices.
        (See :ref:`es-guide-reference-api-admin-indices-aliases`)

        :param alias: the name of an alias
        :param indices: a list of indices

        """
        indices = self.conn._validate_indices(indices)

        return self.change_aliases(['add', index, alias,
                                    self._get_alias_params(**kwargs)]
                                    for index in indices)

    def delete_alias(self, alias, indices):
        """
        Delete an alias.
        (See :ref:`es-guide-reference-api-admin-indices-aliases`)

        The specified index or indices are deleted from the alias, if they are
        in it to start with.  This won't report an error even if the indices
        aren't present in the alias.

        :param alias: the name of an alias
        :param indices: a list of indices
        """
        indices = self.conn._validate_indices(indices)

        return self.change_aliases(['remove', index, alias, {}] for index in indices)

    def set_alias(self, alias, indices, **kwargs):
        """
        Set an alias.
        (See :ref:`es-guide-reference-api-admin-indices-aliases`)

        This handles removing the old list of indices pointed to by the alias.

        Warning: there is a race condition in the implementation of this
        function - if another client modifies the indices which this alias
        points to during this call, the old value of the alias may not be
        correctly set.

        :param alias: the name of an alias
        :param indices: a list of indices
        """
        indices = self.conn._validate_indices(indices)
        try:
            old_indices = self.get_alias(alias)
        except IndexMissingException:
            old_indices = []
        commands = [['remove', index, alias, {}] for index in old_indices]
        commands.extend([['add', index, alias,
                          self._get_alias_params(**kwargs)] for index in indices])
        if len(commands) > 0:
            return self.change_aliases(commands)

    def stats(self, indices=None):
        """
        Retrieve the statistic of one or more indices
        (See :ref:`es-guide-reference-api-admin-indices-stats`)

        :keyword indices: an index or a list of indices
        """
        path = self.conn._make_path(indices, (), "_stats")
        return self.conn._send_request('GET', path)

    def status(self, indices=None):
        """
        Retrieve the status of one or more indices
        (See :ref:`es-guide-reference-api-admin-indices-status`)

        :keyword indices: an index or a list of indices
        """
        path = self.conn._make_path(indices, (), '_status', allow_all_indices=False)
        return self.conn._send_request('GET', path)

    def create_index(self, index, settings=None):
        """
        Creates an index with optional settings.
        :ref:`es-guide-reference-api-admin-indices-create-index`

        :param index: the name of the index
        :keyword settings: a settings object or a dict containing settings

        """
        return self.conn._send_request('PUT', index, settings)

    def create_index_if_missing(self, index, settings=None):
        """Creates an index if it doesn't already exist.

        If supplied, settings must be a dictionary.

        :param index: the name of the index
        :keyword settings: a settings object or a dict containing settings
        """
        try:
            return self.create_index(index, settings)
        except IndexAlreadyExistsException as e:
            return e.result

    def delete_index(self, index):
        """
        Deletes an index.
        :ref:`es-guide-reference-api-admin-indices-delete-index`

        :param index: the name of the index

        """
        return self.conn._send_request('DELETE', index)

    def exists_index(self, index):
        """
        Check if an index exists.
        (See :ref:`es-guide-reference-api-admin-indices-indices-exists`)

        :param index: the name of the index
        """
        return self.conn._send_request('HEAD', index)

    def delete_index_if_exists(self, index):
        """
        Deletes an index if it exists.

        :param index: the name of the index

        """
        if self.exists_index(index):
            return self.delete_index(index)

    def get_indices(self, include_aliases=False):
        """
        Get a dict holding an entry for each index which exists.

        If include_alises is True, the dict will also contain entries for
        aliases.

        The key for each entry in the dict is the index or alias name.  The
        value is a dict holding the following properties:

         - num_docs: Number of documents in the index or alias.
         - alias_for: Only present for an alias: holds a list of indices which
           this is an alias for.

        """
        state = self.conn.cluster.state()
        status = self.status()
        result = {}
        indices_status = status['indices']
        indices_metadata = state['metadata']['indices']
        for index in sorted(indices_status.keys()):
            info = indices_status[index]
            try:
                num_docs = info['docs']['num_docs']
            except KeyError:
                num_docs = 0
            result[index] = dict(num_docs=num_docs)

            if not include_aliases:
                continue
            try:
                metadata = indices_metadata[index]
            except KeyError:
                continue
            for alias in metadata.get('aliases', []):
                try:
                    alias_obj = result[alias]
                except KeyError:
                    alias_obj = {}
                    result[alias] = alias_obj
                alias_obj['num_docs'] = alias_obj.get('num_docs', 0) + num_docs
                try:
                    alias_obj['alias_for'].append(index)
                except KeyError:
                    alias_obj['alias_for'] = [index]
        return result

    def get_closed_indices(self):
        """
        Get all closed indices.
        """
        state = self.conn.cluster.state()
        status = self.status()

        indices_metadata = set(state['metadata']['indices'].keys())
        indices_status = set(status['indices'].keys())

        return indices_metadata.difference(indices_status)

    def close_index(self, index):
        """
        Close an index.
        (See :ref:`es-guide-reference-api-admin-indices-open-close`)


        :param index: the name of the index

        """
        return self.conn._send_request('POST', "/%s/_close" % index)

    def open_index(self, index):
        """
        Open an index.
        (See :ref:`es-guide-reference-api-admin-indices-open-close`)

        :param index: the name of the index
        """
        return self.conn._send_request('POST', "/%s/_open" % index)

    def flush(self, indices=None, refresh=None):
        """
        Flushes one or more indices (clear memory)
        If a bulk is full, it sends it.

        (See :ref:`es-guide-reference-api-admin-indices-flush`)


        :keyword indices: an index or a list of indices
        :keyword refresh: set the refresh parameter

        """
        self.conn.force_bulk()
        path = self.conn._make_path(indices, '_flush')
        args = {}
        if refresh is not None:
            args['refresh'] = refresh
        return self.conn._send_request('POST', path, params=args)

    def refresh(self, indices=None, timesleep=None, timeout=0):
        """
        Refresh one or more indices
        If a bulk is full, it sends it.
        (See :ref:`es-guide-reference-api-admin-indices-refresh`)

        :keyword indices: an index or a list of indices
        :keyword timesleep: seconds to wait
        :keyword timeout: seconds to wait before timing out when waiting for
            the cluster's health.
        """
        self.conn.force_bulk()
        path = self.conn._make_path(indices, (), '_refresh', allow_all_indices=False)
        result = self.conn._send_request('POST', path)
        if timesleep:
            time.sleep(timesleep)
        self.conn.cluster.health(wait_for_status='green', timeout=timeout)
        return result

    def optimize(self, indices=None,
                 wait_for_merge=False,
                 max_num_segments=None,
                 only_expunge_deletes=False,
                 refresh=True,
                 flush=True):
        """
        Optimize one or more indices.
        (See :ref:`es-guide-reference-api-admin-indices-optimize`)


        :keyword indices: the list of indices to optimise.  If not supplied, all
                          default_indices are optimised.

        :keyword wait_for_merge: If True, the operation will not return until the merge has been completed.
                                 Defaults to False.

        :keyword max_num_segments: The number of segments to optimize to. To fully optimize the index, set it to 1.
                                   Defaults to half the number configured by the merge policy (which in turn defaults
                                   to 10).


        :keyword only_expunge_deletes: Should the optimize process only expunge segments with deletes in it.
                                       In Lucene, a document is not deleted from a segment, just marked as deleted.
                                       During a merge process of segments, a new segment is created that does have
                                       those deletes.
                                       This flag allow to only merge segments that have deletes. Defaults to false.

        :keyword refresh: Should a refresh be performed after the optimize. Defaults to true.

        :keyword flush: Should a flush be performed after the optimize. Defaults to true.

        """
        path = self.conn._make_path(indices, (), '_optimize')
        params = dict(
            wait_for_merge=wait_for_merge,
            only_expunge_deletes=only_expunge_deletes,
            refresh=refresh,
            flush=flush,
            )
        for k, v in params.items():
            params[k] = v and "true" or "false"
        if max_num_segments is not None:
            params['max_num_segments'] = max_num_segments
        return self.conn._send_request('POST', path, params=params)

    def analyze(self, text, index=None, analyzer=None, tokenizer=None, filters=None, field=None):
        """
        Performs the analysis process on a text and return the tokens breakdown of the text

        (See :ref:`es-guide-reference-api-admin-indices-optimize`)

        """
        if filters is None:
            filters = []
        argsets = 0
        args = {}

        if analyzer:
            args['analyzer'] = analyzer
            argsets += 1
        if tokenizer or filters:
            if tokenizer:
                args['tokenizer'] = tokenizer
            if filters:
                args['filters'] = ','.join(filters)
            argsets += 1
        if field:
            args['field'] = field
            argsets += 1

        if argsets > 1:
            raise ValueError('Argument conflict: Specify either analyzer, tokenizer/filters or field')

        if field and index is None:
            raise ValueError('field can only be specified with an index')

        path = make_path(index, '_analyze')
        return self.conn._send_request('POST', path, text, args)

    def gateway_snapshot(self, indices=None):
        """
        Gateway snapshot one or more indices
        (See :ref:`es-guide-reference-api-admin-indices-gateway-snapshot`)

        :keyword indices: a list of indices or None for default configured.
        """
        path = self.conn._make_path(indices, (), '_gateway', 'snapshot')
        return self.conn._send_request('POST', path)

    def put_mapping(self, doc_type=None, mapping=None, indices=None):
        """
        Register specific mapping definition for a specific type against one or more indices.
        (See :ref:`es-guide-reference-api-admin-indices-put-mapping`)

        """
        if not isinstance(mapping, dict):
            if mapping is None:
                mapping = {}
            if hasattr(mapping, "as_dict"):
                mapping = mapping.as_dict()

        if doc_type:
            path = self.conn._make_path(indices, doc_type, "_mapping")
            if doc_type not in mapping:
                mapping = {doc_type: mapping}
        else:
            path = self.conn._make_path(indices, (), "_mapping")

        return self.conn._send_request('PUT', path, mapping)

    def get_mapping(self, doc_type=None, indices=None, raw=False):
        """
        Register specific mapping definition for a specific type against one or more indices.
        (See :ref:`es-guide-reference-api-admin-indices-get-mapping`)

        """
        if doc_type is None and indices is None:
            path = make_path("_mapping")
            is_mapping = False
        else:
            indices = self.conn._validate_indices(indices)
            if doc_type:
                path = make_path(','.join(indices), doc_type, "_mapping")
                is_mapping = True
            else:
                path = make_path(','.join(indices), "_mapping")
                is_mapping = False
        result = self.conn._send_request('GET', path)
        if raw:
            return result
        from pyes.mappings import Mapper
        mapper = Mapper(result['mappings'], is_mapping=is_mapping,
                        connection=self.conn,
                        document_object_field=self.conn.document_object_field)
        if doc_type:
            return mapper.mappings[doc_type]
        return mapper

    def delete_mapping(self, index, doc_type):
        """
        Delete a typed JSON document type from a specific index.
        (See :ref:`es-guide-reference-api-admin-indices-delete-mapping`)

        """
        path = make_path(index, doc_type)
        return self.conn._send_request('DELETE', path)

    def get_settings(self, index=None):
        """
        Returns the current settings for an index.
        (See :ref:`es-guide-reference-api-admin-indices-get-settings`)

        """
        path = make_path(index, "_settings")
        return self.conn._send_request('GET', path)

    def update_settings(self, index, newvalues):
        """
        Update Settings of an index.
        (See  :ref:`es-guide-reference-api-admin-indices-update-settings`)

        """
        path = make_path(index, "_settings")
        return self.conn._send_request('PUT', path, newvalues)

class Cluster(object):
    def __init__(self, conn):
        self.conn = conn

    #TODO: node shutdown, update settings

    def shutdown(self, all_nodes=False, master=False, local=False, nodes=[],
                 delay=None):
        if all_nodes:
            path = make_path('_shutdown')
        elif master:
            path = make_path("_cluster", "nodes", "_master", "_shutdown")
        elif nodes:
            path = make_path("_cluster", "nodes", ",".join(nodes), "_shutdown")
        elif local:
            path = make_path("_cluster", "nodes", "_local", "_shutdown")
        if delay:
            try:
                int(delay)
                path += "?%s"%delay
            except ValueError:
                raise ValueError("%s is not a valid delay time"%delay)
            except TypeError:
                raise TypeError("%s is not of type int or string"%delay)
        if not path:
            # default action
            path = make_path('_shutdown')
        return self.conn._send_request('GET', path)



    def health(self, indices=None, level="cluster", wait_for_status=None,
               wait_for_relocating_shards=None, timeout=30):
        """
        Check the current :ref:`cluster health <es-guide-reference-api-admin-cluster-health>`.
        Request Parameters

        The cluster health API accepts the following request parameters:

        :param level: Can be one of cluster, indices or shards. Controls the
                        details level of the health information returned.
                        Defaults to *cluster*.
        :param wait_for_status: One of green, yellow or red. Will wait (until
                                the timeout provided) until the status of the
                                cluster changes to the one provided.
                                By default, will not wait for any status.
        :param wait_for_relocating_shards: A number controlling to how many
                                           relocating shards to wait for.
                                           Usually will be 0 to indicate to
                                           wait till all relocation have
                                           happened. Defaults to not to wait.
        :param timeout: A time based parameter controlling how long to wait
                        if one of the wait_for_XXX are provided.
                        Defaults to 30s.
        """
        if indices:
            path = make_path("_cluster", "health", ",".join(indices))
        else:
            path = make_path("_cluster", "health")
        mapping = {}
        if level != "cluster":
            if level not in ["cluster", "indices", "shards"]:
                raise ValueError("Invalid level: %s" % level)
            mapping['level'] = level
        if wait_for_status:
            if wait_for_status not in ["green", "yellow", "red"]:
                raise ValueError("Invalid wait_for_status: %s" % wait_for_status)
            mapping['wait_for_status'] = wait_for_status

            mapping['timeout'] = "%ds" % timeout
        return self.conn._send_request('GET', path, params=mapping)

    def state(self, filter_nodes=None, filter_routing_table=None,
                      filter_metadata=None, filter_blocks=None,
                      filter_indices=None):
        """
        Retrieve the :ref:`cluster state <es-guide-reference-api-admin-cluster-state>`.

        :param filter_nodes: set to **true** to filter out the **nodes** part
                             of the response.
        :param filter_routing_table: set to **true** to filter out the
                                     **routing_table** part of the response.
        :param filter_metadata: set to **true** to filter out the **metadata**
                                part of the response.
        :param filter_blocks: set to **true** to filter out the **blocks**
                              part of the response.
        :param filter_indices: when not filtering metadata, a comma separated
                               list of indices to include in the response.

        """
        path = make_path("_cluster", "state")
        parameters = {}

        if filter_nodes is not None:
            parameters['filter_nodes'] = filter_nodes

        if filter_routing_table is not None:
            parameters['filter_routing_table'] = filter_routing_table

        if filter_metadata is not None:
            parameters['filter_metadata'] = filter_metadata

        if filter_blocks is not None:
            parameters['filter_blocks'] = filter_blocks

        if filter_blocks is not None:
            if isinstance(filter_indices, six.string_types):
                parameters['filter_indices'] = filter_indices
            else:
                parameters['filter_indices'] = ",".join(filter_indices)

        return self.conn._send_request('GET', path, params=parameters)

    def nodes_info(self, nodes=None):
        """
        The cluster :ref:`nodes info <es-guide-reference-api-admin-cluster-state>` API allows to retrieve one or more (or all) of
        the cluster nodes information.
        """
        parts = ["_cluster", "nodes"]
        if nodes:
            parts.append(",".join(nodes))
        path = make_path(*parts)
        return self.conn._send_request('GET', path)


    def info(self):
        """
        The cluster :ref:`nodes info <es-guide-reference-api-admin-cluster-state>` API allows to retrieve one or more (or all) of
        the cluster nodes information.
        """
        return self.conn._send_request('GET', "/")


    def node_stats(self, nodes=None):
        """
        The cluster :ref:`nodes info <es-guide-reference-api-admin-cluster-nodes-stats>` API allows to retrieve one or more (or all) of
        the cluster nodes information.
        """
        parts = ["_cluster", "nodes", "stats"]
        if nodes:
            parts = ["_cluster", "nodes", ",".join(nodes), "stats"]

        path = make_path(*parts)
        return self.conn._send_request('GET', path)

########NEW FILE########
__FILENAME__ = mappings
# -*- coding: utf-8 -*-


import threading
from collections import OrderedDict
from .models import SortedDict, DotDict



_thread_locals = threading.local()
#store threadsafe data
from .utils import keys_to_string

def to_bool(value):
    """
    Convert a value to boolean
    :param value: the value to convert
    :type value: any type
    :return: a boolean value
    :rtype: a boolean
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    elif isinstance(value, str):
        if value=="no":
            return False
        elif value=="yes":
            return True

check_values = {
    'index': ['no', 'analyzed', 'not_analyzed'],
    'term_vector': ['no', 'yes', 'with_offsets', 'with_positions', 'with_positions_offsets'],
    'type': ['float', 'double', 'byte', 'short', 'integer', 'long'],
    'store': ['yes', 'no'],
    'index_analyzer': [],
    'search_analyzer': [],
    }


class AbstractField(object):
    def __init__(self, index=True, store=False, boost=1.0,
                 term_vector=False,
                 term_vector_positions=False,
                 term_vector_offsets=False,
                 omit_norms=True, tokenize=True,
                 omit_term_freq_and_positions=True,
                 type=None, index_name=None,
                 index_options=None,
                 path=None,
                 norms=None,
                 analyzer=None,
                 index_analyzer=None,
                 search_analyzer=None,
                 name=None,
                 locale=None,
                 fields=None):
        self.tokenize = tokenize
        self.store = to_bool(store)
        self.boost = boost
        self.term_vector = term_vector
        self.term_vector_positions = term_vector_positions
        self.term_vector_offsets = term_vector_offsets
        self.index = index
        self.index_options = index_options
        self.omit_norms = omit_norms
        self.omit_term_freq_and_positions = omit_term_freq_and_positions
        self.index_name = index_name
        self.type = type
        self.analyzer = analyzer
        self.index_analyzer = index_analyzer
        self.search_analyzer = search_analyzer
        self.name = name
        self.path = path
        self.meta = meta or {}
        self.locale = locale
        self.permission = permission or []
        #back compatibility
        if isinstance(store, six.string_types):
            self.store = to_bool(store)
        if isinstance(index, six.string_types):
            if index == "no":
                self.index = False
                self.tokenize = False
            elif index == "not_analyzed":
                self.index = True
                self.tokenize = False
            elif index == "analyzed":
                self.index = True
                self.tokenize = True
        self.fields=[]
        if fields and isinstance(fields, dict):
            _fs=[]
            for n,v in fields.items():
                _fs.append(get_field(n,v))
            self.fields=_fs
        self.norms=norms

    def as_dict(self):
        result = {"type": self.type,
                  'index': self.index}
        if self.store != "no":
            if isinstance(self.store, bool):
                if self.store:
                    result['store'] = "yes"
                else:
                    result['store'] = "no"
            else:
                result['store'] = self.store
        if self.boost != 1.0:
            result['boost'] = self.boost
        if self.required:
            result['required'] = self.required
        if self.permission:
            result['permission'] = self.permission
        if self.term_vector:
            result['term_vector'] = self.term_vector
        if self.term_vector_positions:
            result['term_vector_positions'] = self.term_vector_positions
        if self.term_vector_offsets:
            result['term_vector_offsets'] = self.term_vector_offsets
        if self.index_options:
            result['index_options'] = self.index_options

        if self.omit_norms != True:
            result['omit_norms'] = self.omit_norms
        if self.omit_term_freq_and_positions != True:
            result['omit_term_freq_and_positions'] = self.omit_term_freq_and_positions
        if self.index_name:
            result['index_name'] = self.index_name
        if self.norms:
            result['norms'] = self.norms
        if self.analyzer:
            result['analyzer'] = self.analyzer
        if self.index_analyzer:
            result['index_analyzer'] = self.index_analyzer
        if self.search_analyzer:
            result['search_analyzer'] = self.search_analyzer
        if self.path is not None:
            result['path'] = self.path
        if self.meta:
            result['meta'] = self.meta
        if self.locale:
            result['locale'] = self.locale
        if self.fields:
            result['fields'] = dict([(f.name,t.as_dict()) for f in self.fields])

        return result

    def get_code(self, num=0):
        data = SortedDict(self.as_dict())
        if "store" in data:
            data["store"]=to_bool(data["store"])
        var_name = "prop_"+self.name
        return var_name, var_name+" = "+self.__class__.__name__+"(name=%r, "%self.name+", ".join(["%s=%r"%(k,v) for k,v in list(data.items())])+")"

class StringField(AbstractField):
    def __init__(self, null_value=None, include_in_all=None, *args, **kwargs):
        super(StringField, self).__init__(*args, **kwargs)
        self.null_value = null_value
        self.include_in_all = include_in_all
        self.type = "string"

    def as_dict(self):
        result = super(StringField, self).as_dict()
        if self.null_value is not None:
            result['null_value'] = self.null_value
        if self.include_in_all is not None:
            result['include_in_all'] = self.include_in_all
        if self.term_vector_positions:
            result['term_vector_positions'] = self.term_vector_positions
        if self.term_vector_offsets:
            result['term_vector_offsets'] = self.term_vector_offsets
        return result


class GeoPointField(AbstractField):
    def __init__(self, null_value=None, include_in_all=None,
                 lat_lon=None, geohash=None, geohash_precision=None,
                 normalize_lon=None, normalize_lat=None,
                 validate_lon=None, validate_lat=None,
                 *args, **kwargs):
        super(GeoPointField, self).__init__(*args, **kwargs)
        self.null_value = null_value
        self.include_in_all = include_in_all
        self.lat_lon = lat_lon
        self.geohash = geohash
        self.geohash_precision = geohash_precision
        self.normalize_lon = normalize_lon
        self.normalize_lat = normalize_lat
        self.validate_lat = validate_lat
        self.validate_lon = validate_lon
        self.type = "geo_point"

    def as_dict(self):
        result = super(GeoPointField, self).as_dict()
        if self.null_value is not None:
            result['null_value'] = self.null_value
        if self.include_in_all is not None:
            result['include_in_all'] = self.include_in_all
        if self.lat_lon is not None:
            result['lat_lon'] = self.lat_lon
        if self.geohash is not None:
            result['geohash'] = self.geohash
        if self.normalize_lon is not None:
            result['normalize_lon'] = self.normalize_lon
        if self.normalize_lat is not None:
            result['normalize_lat'] = self.normalize_lat

        if self.validate_lon is not None:
            result['validate_lon'] = self.validate_lon

        if self.validate_lat is not None:
            result['validate_lat'] = self.validate_lat

        if self.geohash_precision is not None:
            try:
                int(self.geohash_precision)
            except ValueError:
                raise ValueError("geohash_precision must be an integer")
            result['geohash_precision'] = self.geohash_precision
        return result


class NumericFieldAbstract(AbstractField):
    def __init__(self, null_value=None, include_in_all=None, precision_step=4,
                 numeric_resolution=None, ignore_malformed=None, **kwargs):
        super(NumericFieldAbstract, self).__init__(**kwargs)
        self.null_value = null_value
        self.include_in_all = include_in_all
        self.precision_step = precision_step
        self.numeric_resolution = numeric_resolution
        self.ignore_malformed=ignore_malformed

    def as_dict(self):
        result = super(NumericFieldAbstract, self).as_dict()
        if self.null_value is not None:
            result['null_value'] = self.null_value
        if self.include_in_all is not None:
            result['include_in_all'] = self.include_in_all
        if self.precision_step != 4:
            result['precision_step'] = self.precision_step
        if self.numeric_resolution:
            result['numeric_resolution'] = self.numeric_resolution
        if self.ignore_malformed is not None:
            result['ignore_malformed'] = self.ignore_malformed
        return result


class IpField(NumericFieldAbstract):
    def __init__(self, *args, **kwargs):
        super(IpField, self).__init__(*args, **kwargs)
        self.type = "ip"

class ByteField(NumericFieldAbstract):
    def __init__(self, *args, **kwargs):
        super(ByteField, self).__init__(*args, **kwargs)
        self.type = "byte"

class ShortField(NumericFieldAbstract):
    def __init__(self, *args, **kwargs):
        super(ShortField, self).__init__(*args, **kwargs)
        self.type = "short"


class IntegerField(NumericFieldAbstract):
    def __init__(self, *args, **kwargs):
        super(IntegerField, self).__init__(*args, **kwargs)
        self.type = "integer"


class LongField(NumericFieldAbstract):
    def __init__(self, *args, **kwargs):
        super(LongField, self).__init__(*args, **kwargs)
        self.type = "long"


class FloatField(NumericFieldAbstract):
    def __init__(self, *args, **kwargs):
        super(FloatField, self).__init__(*args, **kwargs)
        self.type = "float"


class DoubleField(NumericFieldAbstract):
    def __init__(self, *args, **kwargs):
        super(DoubleField, self).__init__(*args, **kwargs)
        self.type = "double"


class DateField(NumericFieldAbstract):
    def __init__(self, format=None, **kwargs):
        super(DateField, self).__init__(**kwargs)
        self.format = format
        self.type = "date"

    def as_dict(self):
        result = super(DateField, self).as_dict()
        if self.format:
            result['format'] = self.format
        return result

    def to_es(self, value):
        if isinstance(value, datetime):
            if value.microsecond:
                value = value.replace(microsecond=0)
            return value.isoformat()
        elif isinstance(value, date):
            return date.isoformat()

    def to_python(self, value):
        if isinstance(value, six.string_types) and len(value) == 19:
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        elif isinstance(value, six.string_types) and len(value) == 10:
            return date.strptime(value, "%Y-%m-%d")

class BooleanField(AbstractField):
    def __init__(self, null_value=None, include_in_all=None, *args, **kwargs):
        super(BooleanField, self).__init__(*args, **kwargs)
        self.null_value = null_value
        self.include_in_all = include_in_all
        self.type = "boolean"

    def as_dict(self):
        result = super(BooleanField, self).as_dict()
        if self.null_value is not None:
            result['null_value'] = self.null_value
        if self.include_in_all is not None:
            result['include_in_all'] = self.include_in_all
        return result

class BinaryField(AbstractField):
    def __init__(self, *args, **kwargs):
        kwargs["tokenize"] = False
        super(BinaryField, self).__init__(*args, **kwargs)
        self.type = "binary"


    def as_dict(self):
        result = super(BinaryField, self).as_dict()
        return result

class MultiField(object):
    def __init__(self, name, type=None, path=None, fields=None):
        self.name = name
        self.type = "multi_field"
        self.path = path
        self.fields = {}
        if fields:
            if isinstance(fields, dict):
                self.fields = dict([(name, get_field(name, data)) for name, data in list(fields.items())])
            elif isinstance(fields, list):
                for field in fields:
                    self.fields[field.name] = field.as_dict()

    def add_fields(self, fields):
        if isinstance(fields, list):
            for field in fields:
                if isinstance(field, AbstractField):
                    self.fields[field.name] = field.as_dict()
                elif isinstance(field, tuple):
                    name, data = field
                    self.fields[name] = data


    def as_dict(self):
        result = {"type": self.type,
                  "fields": {}}
        if self.fields:
            for name, value in list(self.fields.items()):
                if isinstance(value, dict):
                    result['fields'][name] = value
                else:
                    result['fields'][name] = value.as_dict()
        if self.path:
            result['path'] = self.path
        return result
    def get_diff(self, other_mapping):
        """
        Returns a Multifield with diff fields. If not changes, returns None
        :param other_mapping:
        :return: a Multifield or None
        """
        result = MultiField(name=self.name)
        new_fields = set(self.fields.keys())
        if not isinstance(other_mapping, MultiField):
            n_mapping = MultiField(name=self.name)
            n_mapping.add_fields([other_mapping])
            other_mapping = n_mapping

        old_fields = set(other_mapping.fields.keys())
        #we propagate new fields
        added = new_fields - old_fields
        if added:
            result.add_fields([(add, self.fields[add]) for add in added])
            #TODO: raise in field changed
        if len(result.fields) > 0:
            return result
        return None


class AttachmentField(object):
    """An attachment field.

    Requires the mapper-attachments plugin to be installed to be used.

    """

    def __init__(self, name, type=None, path=None, fields=None):
        self.name = name
        self.type = "attachment"
        self.path = path
        #        self.fields = dict([(name, get_field(name, data)) for name, data in fields.items()])
        self.fields = fields

    def as_dict(self):
    #        result_fields = dict((name, value.as_dict())
    #                             for (name, value) in self.fields.items())
        result_fields = self.fields
        result = dict(type=self.type, fields=result_fields)
        if self.path:
            result['path'] = self.path
        return result


class ObjectField(object):
    def __init__(self, name=None, type=None, path=None, properties=None,
                 dynamic=None, enabled=None, include_in_all=None, dynamic_templates=None,
                 include_in_parent=None, include_in_root=None,
                 connection=None, index_name=None, *args, **kwargs):
        self.name = name
        self.type = "object"
        self.path = path
        self.properties = properties
        self.include_in_all = include_in_all
        self.dynamic = dynamic
        self.dynamic_templates = dynamic_templates or []
        self.enabled = enabled
        self.include_in_all = include_in_all
        self.include_in_parent = include_in_parent
        self.include_in_root = include_in_root
        self.connection = connection
        self.index_name = index_name
        if properties:
            self.properties = OrderedDict(sorted([(name, get_field(name, data)) for name, data in properties.items()]))
        else:
            self.properties = {}

    def add_property(self, prop):
        """
        Add a property to the object
        """
        self.properties[prop.name] = prop

    def as_dict(self):
        result = {"type": self.type,
                  "properties": {}}
        if self.dynamic is not None:
            result['dynamic'] = self.dynamic
        if self.enabled is not None:
            result['enabled'] = self.enabled
        if self.include_in_all is not None:
            result['include_in_all'] = self.include_in_all
        if self.include_in_parent is not None:
            result['include_in_parent'] = self.include_in_parent
        if self.include_in_root is not None:
            result['include_in_root'] = self.include_in_root

        if self.path is not None:
            result['path'] = self.path

        if self.properties:
            for name, value in list(self.properties.items()):
                result['properties'][name] = value.as_dict()
        return result

    def __str__(self):
        return str(self.as_dict())

    def clear_properties(self):
        """
        Helper function to reset properties
        """
        self.properties = OrderedDict()

    def save(self):
        if self.connection is None:
            raise RuntimeError("No connection available")

        self.connection.put_mapping(doc_type=self.name, mapping=self.as_dict(), indices=self.index_name)

    def get_properties_by_type(self, type, recursive=True, parent_path=""):
        """
        Returns a sorted list of fields that match the type.

        :param type the type of the field "string","integer" or a list of types
        :param recursive recurse to sub object
        :returns a sorted list of fields the match the type

        """
        if parent_path:
            parent_path += "."

        if isinstance(type, str):
            if type == "*":
                type = set(MAPPING_NAME_TYPE.keys()) - set(["nested", "multi_field", "multifield"])
            else:
                type = [type]
        properties = []
        for prop in list(self.properties.values()):
            if prop.type in type:
                properties.append((parent_path + prop.name, prop))
                continue
            elif prop.type == "multi_field" and prop.name in prop.fields and prop.fields[prop.name].type in type:
                properties.append((parent_path + prop.name, prop))
                continue

            if not recursive:
                continue
            if prop.type in ["nested", "object"]:
                properties.extend(
                    prop.get_properties_by_type(type, recursive=recursive, parent_path=parent_path + prop.name))
        return sorted(properties)

    def get_property_by_name(self, name):
        """
        Returns a mapped object.

        :param name the name of the property
        :returns the mapped object or exception NotFoundMapping

        """
        if "." not in name and name in self.properties:
            return self.properties[name]

        tokens = name.split(".")
        object = self
        for token in tokens:
            if isinstance(object, (DocumentObjectField, ObjectField, NestedObject)):
                if token in object.properties:
                    object = object.properties[token]
                    continue
            elif isinstance(object, MultiField):
                if token in object.fields:
                    object = object.fields[token]
                    continue
            raise MappedFieldNotFoundException(token)
        if isinstance(object, (AbstractField, MultiField)):
            return object
        raise MappedFieldNotFoundException(object)


    def get_available_facets(self):
        """
        Returns Available facets for the document
        """
        result = []
        for k, v in list(self.properties.items()):
            if isinstance(v, DateField):
                if not v.tokenize:
                    result.append((k, "date"))
            elif isinstance(v, NumericFieldAbstract):
                result.append((k, "numeric"))
            elif isinstance(v, StringField):
                if not v.tokenize:
                    result.append((k, "term"))
            elif isinstance(v, GeoPointField):
                if not v.tokenize:
                    result.append((k, "geo"))
            elif isinstance(v, ObjectField):
                for n, t in self.get_available_facets():
                    result.append((self.name + "." + k, t))
        return result

    def get_datetime_properties(self, recursive=True):
        """
        Returns a dict of property.path and property.

        :param recursive the name of the property
        :returns a dict

        """
        res = {}
        for name, field in self.properties.items():
            if isinstance(field, DateField):
                res[name] = field
            elif recursive and isinstance(field, ObjectField):
                for n, f in field.get_datetime_properties(recursive=recursive):
                    res[name + "." + n] = f
        return res

    def get_code(self, num=1):
        data = SortedDict(self.as_dict())
        data.pop("properties", [])
        var_name ="obj_%s"%self.name
        code= [var_name+" = "+self.__class__.__name__+"(name=%r, "%self.name+", ".join(["%s=%r"%(k,v) for k,v in list(data.items())])+")"]
        for name, field in list(self.properties.items()):
            num+=1
            vname, vcode = field.get_code(num)
            code.append(vcode)
            code.append("%s.add_property(%s)"%(var_name, vname))

        return var_name, '\n'.join(code)

    def get_diff(self, new_mapping):
        """
        Given two mapping it extracts a schema evolution mapping. Returns None if no evolutions are required
        :param new_mapping: the new mapping
        :return: a new evolution mapping or None
        """
        result = copy.deepcopy(new_mapping)
        result.clear_properties()

        no_check_types = (BooleanField, IntegerField, FloatField, DateField, LongField, BinaryField,
                          GeoPointField, IpField)

        old_fields = set(self.properties.keys())
        new_fields = set(new_mapping.properties.keys())
        #we propagate new fields
        added = new_fields - old_fields
        if added:
            for add in added:
                result.add_property(new_mapping.properties[add])

        #we check common fields
        common_fields = new_fields & old_fields

        #removing standard data
        common_fields = [c for c in common_fields if not isinstance(new_mapping.properties[c], no_check_types)]

        for field in common_fields:
            prop = new_mapping.properties[field]
            if isinstance(prop, StringField):
                continue
            if isinstance(prop, MultiField):
                diff = prop.get_diff(self.properties[field])
                if diff:
                    result.add_property(diff)
            elif isinstance(prop, ObjectField):
                diff = self.properties[field].get_diff(prop)
                if diff:
                    result.add_property(diff)

        if len(result.properties) > 0:
            return result
        return None

class NestedObject(ObjectField):
    def __init__(self, *args, **kwargs):
        super(NestedObject, self).__init__(*args, **kwargs)
        self.type = "nested"


class DocumentObjectField(ObjectField):
    def __init__(self, _all=None, _boost=None, _id=None,
                 _index=None, _source=None, _type=None, date_formats=None, _routing=None, _ttl=None,
                 _parent=None, _timestamp=None, _analyzer=None, _size=None, date_detection=None,
                 numeric_detection=None, dynamic_date_formats=None, _meta=None, *args, **kwargs):
        super(DocumentObjectField, self).__init__(*args, **kwargs)
        self._timestamp = _timestamp
        self._all = _all
        self._boost = _boost
        self._id = _id
        self._index = _index
        self._source = _source
        self._routing = _routing
        self._ttl = _ttl
        self._analyzer = _analyzer
        self._size = _size

        self._type = _type
        if self._type is None:
            self._type = {"store": "yes"}

        self._parent = _parent
        self.date_detection = date_detection
        self.numeric_detection = numeric_detection
        self.dynamic_date_formats = dynamic_date_formats
        self._meta = DotDict(_meta or {})


    def get_meta(self, subtype=None):
        """
        Return the meta data.
        """
        if subtype:
            return DotDict(self._meta.get(subtype, {}))
        return  self._meta

    def enable_compression(self, threshold="5kb"):
        self._source.update({"compress": True, "compression_threshold": threshold})

    def as_dict(self):
        result = super(DocumentObjectField, self).as_dict()
        result['_type'] = self._type
        if self._all is not None:
            result['_all'] = self._all
        if self._source is not None:
            result['_source'] = self._source
        if self._boost is not None:
            result['_boost'] = self._boost
        if self._routing is not None:
            result['_routing'] = self._routing
        if self._ttl is not None:
            result['_ttl'] = self._ttl
        if self._id is not None:
            result['_id'] = self._id
        if self._timestamp is not None:
            result['_timestamp'] = self._timestamp
        if self._index is not None:
            result['_index'] = self._index
        if self._parent is not None:
            result['_parent'] = self._parent
        if self._analyzer is not None:
            result['_analyzer'] = self._analyzer
        if self._size is not None:
            result['_size'] = self._size

        if self.date_detection is not None:
            result['date_detection'] = self.date_detection
        if self.numeric_detection is not None:
            result['numeric_detection'] = self.numeric_detection
        if self.dynamic_date_formats is not None:
            result['dynamic_date_formats'] = self.dynamic_date_formats

        return result

    def add_property(self, prop):
        """
        Add a property to the object
        """
        self.properties[prop.name] = prop

    def __repr__(self):
        return "<DocumentObjectField:%s>" % self.name


    def save(self):
        if self.connection is None:
            raise RuntimeError("No connection available")
        self.connection.put_mapping(doc_type=self.name, mapping=self.as_dict(), indices=self.index_name)

    def get_code(self, num=1):
        data = SortedDict(self.as_dict())
        data.pop("properties", [])
        var_name ="doc_%s"%self.name
        code= [var_name+" = "+self.__class__.__name__+"(name=%r, "%self.name+", ".join(["%s=%r"%(k,v) for k,v in list(data.items())])+")"]
        for name, field in list(self.properties.items()):
            num+=1
            vname, vcode = field.get_code(num)
            code.append(vcode)
            code.append("%s.add_property(%s)"%(var_name, vname))

        return '\n'.join(code)

def get_field(name, data, default="object", document_object_field=None, is_document=False):
    """
    Return a valid Field by given data
    """
    if isinstance(data, AbstractField):
        return data
    data = keys_to_string(data)
    _type = data.get('type', default)
    if _type == "string":
        return StringField(name=name, **data)
    elif _type == "binary":
        return BinaryField(name=name, **data)
    elif _type == "boolean":
        return BooleanField(name=name, **data)
    elif _type == "byte":
        return ByteField(name=name, **data)
    elif _type == "short":
        return ShortField(name=name, **data)
    elif _type == "integer":
        return IntegerField(name=name, **data)
    elif _type == "long":
        return LongField(name=name, **data)
    elif _type == "float":
        return FloatField(name=name, **data)
    elif _type == "double":
        return DoubleField(name=name, **data)
    elif _type == "ip":
        return IpField(name=name, **data)
    elif _type == "date":
        return DateField(name=name, **data)
    elif _type == "multi_field":
        return MultiField(name=name, **data)
    elif _type == "geo_point":
        return GeoPointField(name=name, **data)
    elif _type == "attachment":
        return AttachmentField(name=name, **data)
    elif is_document or _type == "document":
        if document_object_field:
            return document_object_field(name=name, **data)
        else:
            data.pop("name",None)
            return DocumentObjectField(name=name, **data)

    elif _type == "object":
        if '_timestamp' in data or "_all" in data:
            if document_object_field:
                return document_object_field(name=name, **data)
            else:
                return DocumentObjectField(name=name, **data)

        return ObjectField(name=name, **data)
    elif _type == "nested":
        return NestedObject(name=name, **data)
    raise RuntimeError("Invalid type: %s" % _type)


class Mapper(object):
    def __init__(self, data, connection=None, is_mapping=False, document_object_field=None):
        """
        Create a mapper object

        :param data: a dict containing the mappings
        :param connection: a connection object
        :param is_mapping: if it's a mapping or index/mapping
        :param document_object_field: the kind of object to be used for document object Field
        :return:
        """
        self.indices = OrderedDict()
        self.mappings = OrderedDict()
        self.is_mapping = is_mapping
        self.connection = connection
        self.full_mappings = False
        self.document_object_field = document_object_field
        self._process(data)

    def _process(self, data):
        """
        Process indexer data
        """
        indices = []
        for indexname, indexdata in list(data.items()):
            idata = []
            for docname, docdata in list(indexdata.items()):
                o = get_field(docname, docdata, document_object_field=self.document_object_field, is_document=True)
                o.connection = self.connection
                o.index_name = indexname
                idata.append((docname, o))
            idata.sort()
            indices.append((indexname, idata))
        indices.sort()
        self.indices = indices


    def get_doctypes(self, index, edges=True):
        """
        Returns a list of doctypes given an index
        """
        if index not in self.indices:
            self.get_all_indices()
        return self.indices.get(index, {})

    def get_doctype(self, index, name):
        """
        Returns a doctype given an index and a name
        """
        if index not in self.indices:
            self.get_all_indices()
        return self.indices.get(index, {}).get(name, None)

    def get_property(self, index, doctype, name):
        """
        Returns a property of a given type

        :return a mapped property
        """

        return self.indices[index][doctype].properties[name]

    def get_all_indices(self):
        if not self.full_mappings:
            mappings = self.connection.indices.get_mapping(raw=True)
            self._process(mappings)
            self.full_mappings = True
        return self.indices.keys()

    def migrate(self, mapping, index, doc_type):
        """
        Migrate a ES mapping


        :param mapping: new mapping
        :param index: index of old mapping
        :param doc_type: type of old mapping
        :return: The diff mapping
        """
        old_mapping = self.get_doctype(index, doc_type)
        #case missing
        if not old_mapping:
            self.connection.indices.put_mapping(doc_type=doc_type, mapping=mapping, indices=index)
            return mapping
            # we need to calculate the diff
        mapping_diff = old_mapping.get_diff(mapping)
        if not mapping_diff:
            return None
        from pprint import pprint

        pprint(mapping_diff.as_dict())
        mapping_diff.connection = old_mapping.connection
        mapping_diff.save()


MAPPING_NAME_TYPE = {
    "attachment": AttachmentField,
    "boolean": BooleanField,
    "date": DateField,
    "double": DoubleField,
    "float": FloatField,
    "geopoint": GeoPointField,
    "integer": IntegerField,
    "int": IntegerField,
    "ip": IpField,
    "long": LongField,
    "multifield": MultiField,
    "nested": NestedObject,
    "short": ShortField,
    "string": StringField,
    "binary":BinaryField
}


########NEW FILE########
__FILENAME__ = models
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import with_statement

import copy
import threading
try:
    import simplejson as json
except ImportError:
    import json
from types import GeneratorType

from .exceptions import BulkOperationException

__author__ = 'alberto'

class DotDict(dict):
    def __getattr__(self, attr):
        if attr.startswith('__'):
            raise AttributeError
        return self.get(attr, None)

    __setattr__ = dict.__setitem__

    __delattr__ = dict.__delitem__

    def __deepcopy__(self, memo):
        return DotDict([(copy.deepcopy(k, memo), copy.deepcopy(v, memo)) for k, v in self.items()])


class ElasticSearchModel(DotDict):
    def __init__(self, *args, **kwargs):
        from pyes import ES
        self._meta = DotDict()
        self.__initialised = True
        if len(args) == 2 and isinstance(args[0], ES):
            item = args[1]
            self.update(item.pop("_source", DotDict()))
            self.update(item.pop("fields", {}))
            self._meta = DotDict([(k.lstrip("_"), v) for k, v in item.items()])
            self._meta.parent = self.pop("_parent", None)
            self._meta.connection = args[0]
        else:
            self.update(dict(*args, **kwargs))

    def __setattr__(self, key, value):
        if '_ElasticSearchModel__initialised' not in list(self.__dict__.keys()):  # this test allows attributes to be set in the __init__ method
            return dict.__setattr__(self, key, value)
        elif key in list(self.__dict__.keys()):       # any normal attributes are handled normally
            dict.__setattr__(self, key, value)
        else:
            self.__setitem__(key, value)

    def get_meta(self):
        return self._meta

    def delete(self, bulk=False):
        """
        Delete the object
        """
        meta = self._meta
        conn = meta['connection']
        conn.delete(meta.index, meta.type, meta.id, bulk=bulk)

    def save(self, bulk=False, id=None, parent=None, routing=None, force=False):
        """
        Save the object and returns id
        """
        meta = self._meta
        conn = meta['connection']
        id = id or meta.get("id", None)
        parent = parent or meta.get('parent', None)
        routing = routing or meta.get('routing', None)
        qargs = None
        if routing:
            qargs={'routing': routing}
        version = meta.get('version', None)
        if force:
            version = None
        res = conn.index(self,
                         meta.index, meta.type, id, parent=parent, bulk=bulk,
                         version=version, force_insert=force,
                         querystring_args=qargs)
        if not bulk:
            self._meta.id = res._id
            self._meta.version = res._version
            return res._id
        return id

    def reload(self):
        meta = self._meta
        conn = meta['connection']
        res = conn.get(meta.index, meta.type, meta["id"])
        self.update(res)


    def get_id(self):
        """ Force the object saveing to get an id"""
        _id = self._meta.get("id", None)
        if _id is None:
            _id = self.save()
        return _id

    def get_bulk(self, create=False):
        """Return bulk code"""
        result = []
        op_type = "index"
        if create:
            op_type = "create"
        meta = self._meta
        cmd = {op_type: {"_index": meta.index, "_type": meta.type}}
        if meta.parent:
            cmd[op_type]['_parent'] = meta.parent
        if meta.version:
            cmd[op_type]['_version'] = meta.version
        if meta.id:
            cmd[op_type]['_id'] = meta.id
        result.append(json.dumps(cmd, cls=self._meta.connection.encoder))
        result.append("\n")
        result.append(json.dumps(self, cls=self._meta.connection.encoder))
        result.append("\n")
        return ''.join(result)




#--------
# Bulkers
#--------

class BaseBulker(object):
    """
    Base class to implement a bulker strategy

    """

    def __init__(self, conn, bulk_size=400, raise_on_bulk_item_failure=False):
        self.conn = conn
        self._bulk_size = bulk_size
        # protects bulk_data
        self.bulk_lock = threading.RLock()
        with self.bulk_lock:
            self.bulk_data = []
        self.raise_on_bulk_item_failure = raise_on_bulk_item_failure

    def get_bulk_size(self):
        """
        Get the current bulk_size

        :return a int: the size of the bulk holder
        """
        return self._bulk_size

    def set_bulk_size(self, bulk_size):
        """
        Set the bulk size

        :param bulk_size the bulker size
        """
        self._bulk_size = bulk_size
        self.flush_bulk()

    bulk_size = property(get_bulk_size, set_bulk_size)

    def add(self, content):
        raise NotImplementedError

    def flush_bulk(self, forced=False):
        raise NotImplementedError


class ListBulker(BaseBulker):
    """
    A bulker that store data in a list
    """

    def __init__(self, conn, bulk_size=400, raise_on_bulk_item_failure=False):
        super(ListBulker, self).__init__(conn=conn, bulk_size=bulk_size,
                                         raise_on_bulk_item_failure=raise_on_bulk_item_failure)
        with self.bulk_lock:
            self.bulk_data = []

    def __nonzero__(self):
        # This is needed for __del__ in ES to correctly detect if there is
        # unsaved bulk data left over.
        return not not self.bulk_data

    def add(self, content):
        with self.bulk_lock:
            self.bulk_data.append(content)

    def flush_bulk(self, forced=False):
        with self.bulk_lock:
            if forced or len(self.bulk_data) >= self.bulk_size:
                batch = self.bulk_data
                self.bulk_data = []
            else:
                return None

        if len(batch) > 0:
            bulk_result = self.conn._send_request("POST",
                                                  "/_bulk",
                                                  "\n".join(batch) + "\n")

            if self.raise_on_bulk_item_failure:
                _raise_exception_if_bulk_item_failed(bulk_result)

            return bulk_result


def _is_bulk_item_ok(item):
    # this becomes messier if we're supporting pre-1.0 ElasticSearch
    # alongside 1.0 ones.
    if "create" in item:
        if 'ok' in item['create']:
            return True
        elif 'status' in item['create']:
            return item["create"]['status'] in [200,201]
        else:
            return False
    if "index" in item:
        if 'ok' in item['index']:
            return True
        elif "status" in item['index']:
            return item["index"]['status'] in [200,201]
        else:
            return False
    elif "delete" in item:
        if 'ok' in item['delete']:
            return True
        elif 'status' in item['delete']:
            return item['delete']['status'] in [200,201]
        else:
            return False
    else:
        # unknown response type; be conservative
        return False


def _raise_exception_if_bulk_item_failed(bulk_result):
    errors = [item for item in bulk_result["items"] if not _is_bulk_item_ok(item)]
    if len(errors) > 0:
        raise BulkOperationException(errors, bulk_result)
    return None

class SortedDict(dict):
    """
    A dictionary that keeps its keys in the order in which they're inserted.

    Taken from django
    """
    def __new__(cls, *args, **kwargs):
        instance = super(SortedDict, cls).__new__(cls, *args, **kwargs)
        instance.keyOrder = []
        return instance

    def __init__(self, data=None):
        if data is None:
            data = {}
        elif isinstance(data, GeneratorType):
            # Unfortunately we need to be able to read a generator twice.  Once
            # to get the data into self with our super().__init__ call and a
            # second time to setup keyOrder correctly
            data = list(data)
        super(SortedDict, self).__init__(data)
        if isinstance(data, dict):
            self.keyOrder = data.keys()
        else:
            self.keyOrder = []
            seen = set()
            for key, value in data:
                if key not in seen:
                    self.keyOrder.append(key)
                    seen.add(key)

    def __deepcopy__(self, memo):
        return self.__class__([(key, copy.deepcopy(value, memo))
                               for key, value in self.items()])

    def __setitem__(self, key, value):
        if key not in self:
            self.keyOrder.append(key)
        super(SortedDict, self).__setitem__(key, value)

    def __delitem__(self, key):
        super(SortedDict, self).__delitem__(key)
        self.keyOrder.remove(key)

    def __iter__(self):
        return iter(self.keyOrder)

    def pop(self, k, *args):
        result = super(SortedDict, self).pop(k, *args)
        try:
            self.keyOrder.remove(k)
        except ValueError:
            # Key wasn't in the dictionary in the first place. No problem.
            pass
        return result

    def popitem(self):
        result = super(SortedDict, self).popitem()
        self.keyOrder.remove(result[0])
        return result

    def items(self):
        return zip(self.keyOrder, self.values())

    def items(self):
        for key in self.keyOrder:
            yield key, self[key]

    def keys(self):
        return self.keyOrder[:]

    def iterkeys(self):
        return iter(self.keyOrder)

    def values(self):
        return map(self.__getitem__, self.keyOrder)

    def itervalues(self):
        for key in self.keyOrder:
            yield self[key]

    def update(self, dict_):
        for k, v in dict_.items():
            self[k] = v

    def setdefault(self, key, default):
        if key not in self:
            self.keyOrder.append(key)
        return super(SortedDict, self).setdefault(key, default)

    def value_for_index(self, index):
        """Returns the value of the item at the given zero-based index."""
        return self[self.keyOrder[index]]

    def insert(self, index, key, value):
        """Inserts the key, value pair before the item with the given index."""
        if key in self.keyOrder:
            n = self.keyOrder.index(key)
            del self.keyOrder[n]
            if n < index:
                index -= 1
        self.keyOrder.insert(index, key)
        super(SortedDict, self).__setitem__(key, value)

    def copy(self):
        """Returns a copy of this object."""
        # This way of initializing the copy means it works for subclasses, too.
        obj = self.__class__(self)
        obj.keyOrder = self.keyOrder[:]
        return obj

    def __repr__(self):
        """
        Replaces the normal dict.__repr__ with a version that returns the keys
        in their sorted order.
        """
        return '{%s}' % ', '.join(['%r: %r' % (k, v) for k, v in self.items()])

    def clear(self):
        super(SortedDict, self).clear()
        self.keyOrder = []

########NEW FILE########
__FILENAME__ = exceptions
__author__ = 'alberto'
class DoesNotExist(Exception):
    pass


class MultipleObjectsReturned(Exception):
    pass


########NEW FILE########
__FILENAME__ = queryset
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The main QuerySet implementation. This provides the public API for the ORM.
"""

import copy
from pyes.es import ResultSetList, EmptyResultSet, ResultSet
from pyes.filters import ANDFilter, ORFilter, NotFilter, Filter, TermsFilter, TermFilter, RangeFilter, ExistsFilter, RegexTermFilter, IdsFilter, PrefixFilter, MissingFilter
from pyes.facets import Facet, TermFacet, StatisticalFacet, HistogramFacet, DateHistogramFacet, TermStatsFacet
from pyes.query import MatchAllQuery, BoolQuery, FilteredQuery, Search
from pyes.utils import ESRange, make_id
from pyes.exceptions import NotFoundException
try:
    from django.db.models import Q
except ImportError:
    class Q:pass

import six
from pyes_engine import logger

from brainaetic.documental import get_model_from_str
import re
from django.utils.functional import SimpleLazyObject

REPR_OUTPUT_SIZE = 20

# Calculate the verbose_name by converting from InitialCaps to "lowercase with spaces".
get_verbose_name = lambda class_name: re.sub('(((?<=[a-z])[A-Z])|([A-Z](?![A-Z]|$)))', ' \\1',
                                             class_name).lower().strip()
FIELD_SEPARATOR = "__"

from pyes.scriptfields import ScriptField
from pyes.exceptions import InvalidParameter


class QuerySet(object):
    """
    Represents a lazy database lookup for a set of objects.
    """

    def __init__(self, model=None, using=None, connection=None):
        #TODO: dfix
        self.model = model
        # EmptyQuerySet instantiates QuerySet with model as None
        self._using = using
        self._index = using
        self._size = 10
        self._type = None
        self._connection = connection
        self._queries = []
        self._filters = []
        self._facets = []
        self._ordering = []
        self._scan = None
        self._rescorer = None
        self._fields = [] #fields to load
        self._result_cache = None #hold the resultset
        if model:
            self._using = model._meta.using
            if connection:
                self._index = connection.database
            if model._meta.ordering:
                self._insert_ordering(self, *model._meta.ordering)

    def get_queryset(self):
        return self

    def using(self, using):
        self._using = using
        return self

    def scan(self, active=True):
        self._scan = active
        return self

    def _clear_ordering(self):
        #reset ordering
        self._ordering = []

    @property
    def type(self):
        if self._type:
            return self._type
        return self.model._meta.db_table

    def _next_is_sticky(self):
        return self

    def select_related(self, *fields, **kwargs):
        return self

        ########################

    # PYTHON MAGIC METHODS #
    ########################

    def __deepcopy__(self, memo):
        """
        Deep copy of a QuerySet doesn't populate the cache
        """
        obj = self.__class__()
        for k, v in self.__dict__.items():
            if k in ('_iter', '_result_cache'):
                obj.__dict__[k] = None
            else:
                obj.__dict__[k] = copy.deepcopy(v, memo)
        return obj

    def __getstate__(self):
        """
        Allows the QuerySet to be pickled.
        """
        # Force the cache to be fully populated.
        len(self)

        obj_dict = self.__dict__.copy()
        obj_dict['_iter'] = None
        return obj_dict

    def __repr__(self):
        data = list(self[:REPR_OUTPUT_SIZE + 1])
        if len(data) > REPR_OUTPUT_SIZE:
            data[-1] = "...(remaining elements truncated)..."
        return repr(data)

    def _build_query(self):
        if not self._queries and not self._filters:
            return MatchAllQuery()
        query = MatchAllQuery()
        if self._queries:
            if len(self._queries) == 1:
                query = self._queries[0]
            else:
                query = BoolQuery(must=self._queries)
        if not self._filters:
            return query
        if len(self._filters) == 1:
            return FilteredQuery(query, self._filters[0])
        return FilteredQuery(query, ANDFilter(self._filters))

    def _build_search(self):
        query = Search(self._build_query(), version=True)

        if self._ordering:
            query.sort = self._ordering
        if self._facets:
            for facet in self._facets:
                query.facet.add(facet)
        if self._size==0:
            query.size=0
        if self._rescorer:
            query.rescore=self._rescorer

        return query

    def _build_model(self, m, record):
        from django.db import models

        data = record["_source"]
        data["id"] = record["_id"]
        fields = self.model._meta.fields
        for field in fields:
            if field.attname not in data:
                continue

            if isinstance(field, models.ListField):
                model = field.item_field.model
                if isinstance(model, six.string_types):
                    model = get_model_from_str(model)
                if isinstance(field.item_field, models.ForeignKey):
                    #data[field.attname] = ModelIteratorResolver(field.item_field.model, data[field.attname])
                    if data[field.attname]:
                        data[field.attname] = [model.objects.get(pk=id) for id in data[field.attname]]
                    else:
                        data[field.attname] = []
            elif isinstance(field, models.SetField):
                model = field.item_field.model
                if isinstance(model, six.string_types):
                    model = get_model_from_str(model)
                if isinstance(field.item_field, models.ForeignKey):
                    if data[field.attname]:
                    #data[field.attname] = ModelIteratorResolver(field.item_field.model, data[field.attname])
                        data[field.attname] = set([model.objects.get(pk=id) for id in data[field.attname]])
                    else:
                        data[field.attname] = []
                else:
                    data[field.attname] = set(data[field.attname])
        value = self.model(**data)
        setattr(value, "_index", record["_index"])
        setattr(value, "_type", record["_type"])

        if "_score" in record:
            setattr(value, "_score", record["_score"])
        if "sort" in record:
            setattr(value, "_sort", record["sort"])
        return value

    def _is_valid_scan(self):
        """
        Detect if a type
        :return: a boolean
        """
        if self._scan is not None:
            return self._scan
        if self._ordering:
            return False
        if self._facets:
            return False
            #TODO check for child or nested query
        return True

    def _do_query(self):
        connection = self.model._meta.dj_connection
        index = self.get_index(connection)
        from pyes.es import ES

        if not isinstance(connection.connection, ES):
            print("Strange connection object", connection)
            #refresh data
        if connection._dirty:
            connection.connection.refresh(indices=index)
            connection._dirty = False

        #check ids
        if not self._facets and not self._queries and len(self._filters) == 1 and isinstance(self._filters[0],
                                                                                             IdsFilter):
            filter = self._filters[0]
            if len(filter.values) == 1:
                try:
                    return ResultSetList(items=[
                        connection.connection.get(index, self.type, str(filter.values[0]),
                                                  model=self._build_model)],
                                         model=self._build_model)
                except NotFoundException:
                    return EmptyResultSet()

        search = self._build_search()
        # if isinstance(search.query, FilteredQuery) and isinstance(search.query.query, MatchAllQuery) and \
        #     isinstance(search.query.filter, IdsFilter) and len(search.query.filter.values) == 1:
        #     results = [connection.connection.get(index, self.type,search.query.filter.values[0], model=self._build_model)]
        #     #iterator

        # show query
        scan = self._is_valid_scan()
        if scan:
            search.sort = {}
        #print "scan?", scan, index, self.type, search.serialize()
        return connection.connection.search(search, indices=index, doc_types=self.type,
                                            model=self._build_model, scan=scan)


    def __len__(self):
        # Since __len__ is called quite frequently (for example, as part of
        # list(qs), we make some effort here to be as efficient as possible
        # whilst not messing up any existing iterators against the QuerySet.
        if self._result_cache is None:
            self._result_cache = self._do_query()
        return self._result_cache.total

    def __iter__(self):
        if self._result_cache is None:
            len(self)
            # Python's list iterator is better than our version when we're just
        # iterating over the cache.
        return iter(self._result_cache)


    def __nonzero__(self):
        if self._result_cache is not None:
            len(self)
            return bool(self._result_cache.total != 0)
        try:
            next(iter(self))
        except StopIteration:
            return False
        return True

    #    def __contains__(self, val):
    #        # The 'in' operator works without this method, due to __iter__. This
    #        # implementation exists only to shortcut the creation of Model
    #        # instances, by bailing out early if we find a matching element.
    #        pos = 0
    #        if self._result_cache is not None:
    #            if val in self._result_cache:
    #                return True
    #            elif self._iter is None:
    #                # iterator is exhausted, so we have our answer
    #                return False
    #            # remember not to check these again:
    #            pos = len(self._result_cache)
    #        else:
    #            # We need to start filling the result cache out. The following
    #            # ensures that self._iter is not None and self._result_cache is not
    #            # None
    #            it = iter(self)
    #
    #        # Carry on, one result at a time.
    #        while True:
    #            if len(self._result_cache) <= pos:
    #                self._fill_cache(num=1)
    #            if self._iter is None:
    #                # we ran out of items
    #                return False
    #            if self._result_cache[pos] == val:
    #                return True
    #            pos += 1

    def __getitem__(self, k):
        """
        Retrieves an item or slice from the set of results.
        """
        if not isinstance(k, (slice,) + six.integer_types):
            raise TypeError
        assert ((not isinstance(k, slice) and (k >= 0))
                or (isinstance(k, slice) and (k.start is None or k.start >= 0)
                    and (k.stop is None or k.stop >= 0))), \
            "Negative indexing is not supported."

        if self._result_cache is None:
            len(self)
        return self._result_cache.__getitem__(k)

    def __and__(self, other):
        combined = self._clone()
        if not other._filters:
            return combined
        if other._filters:
            combined._filters.extend(other._filters)
        return combined

    def __or__(self, other):
        combined = self._clone()
        if not other._filters:
            return other._clone()
        combined._filters = ORFilter([combined._filters, other._filters])
        return combined

    ####################################
    # METHODS THAT DO DATABASE QUERIES #
    ####################################

    def iterator(self):
        """
        An iterator over the results from applying this QuerySet to the
        database.
        """
        if not self._result_cache:
            len(self)
        for r in self._result_cache:
            yield r

    def aggregate(self, *args, **kwargs):
        """
        Returns a dictionary containing the calculations (aggregation)
        over the current queryset

        If args is present the expression is passed as a kwarg using
        the Aggregate object's default alias.
        """
        obj = self._clone()
        obj._facets = [] #reset facets
        from django.db.models import Avg, Max, Min

        for arg in args:
            if isinstance(arg, (Avg, Max, Min)):

                field, djfield = self._django_to_es_field(arg.lookup)
                if not djfield:
                    obj = obj.annotate(field)
                from pyes.facets import StatisticalFacet

                obj = obj.annotate(StatisticalFacet(field, field))
        facets = obj.get_facets()
        #collecting results
        result = {}
        for name, values in facets.items():
            for k, v in values.items():
                if k.startswith("_"):
                    continue
                result[u'%s__%s' % (name, k)] = v

        return result

    def count(self):
        """
        Performs a SELECT COUNT() and returns the number of records as an
        integer.

        If the QuerySet is already fully cached this simply returns the length
        of the cached results set to avoid multiple SELECT COUNT(*) calls.
        """
        return len(self)

    def get(self, *args, **kwargs):
        """
        Performs the query and returns a single object matching the given
        keyword arguments.
        """
        clone = self.filter(*args, **kwargs)
        num = len(clone)
        if num == 1:
            return clone._result_cache[0]
        if not num:
            raise self.model.DoesNotExist(
                "%s matching query does not exist. "
                "Lookup parameters were %s" %
                #(self.model._meta.object_name, kwargs))
                (self.model.__class__.__name__, kwargs))
        raise self.model.MultipleObjectsReturned(
            "get() returned more than one %s -- it returned %s! "
            "Lookup parameters were %s" %
            #(self.model._meta.object_name, num, kwargs))
            (self.model.__class__.__name__, num, kwargs))

    def create(self, **kwargs):
        """
        Creates a new object with the given kwargs, saving it to the database
        and returning the created object.
        """
        obj = self.model(**kwargs)
        obj.save(force_insert=True, using=self._using)
        return obj

    def bulk_create(self, objs, batch_size=None):
        """
        Inserts each of the instances into the database. This does *not* call
        save() on each of the instances, does not send any pre/post save
        signals, and does not set the primary key attribute if it is an
        autoincrement field.
        """
        self._insert(objs, batch_size=batch_size, return_id=False, force_insert=True)
        self.refresh()

    def get_or_create(self, **kwargs):
        """
        Looks up an object with the given kwargs, creating one if necessary.
        Returns a tuple of (object, created), where created is a boolean
        specifying whether an object was created.
        """
        assert kwargs, \
            'get_or_create() must be passed at least one keyword argument'
        defaults = kwargs.pop('defaults', {})
        lookup = kwargs.copy()
        #TODO: check fields
        try:
            return self.get(**lookup), False
        except self.model.DoesNotExist:
            params = dict([(k, v) for k, v in kwargs.items() if '__' not in k])
            params.update(defaults)
            obj = self.model(**params)
            obj.save(force_insert=True)
            return obj, True

    def latest(self, field_name=None):
        """
        Returns the latest object, according to the model's 'get_latest_by'
        option or optional given field_name.
        """
        latest_by = field_name or "_id"#self.model._meta.get_latest_by
        assert bool(latest_by), "latest() requires either a field_name parameter or 'get_latest_by' in the model"
        obj = self._clone()
        obj.size = 1
        obj._clear_ordering()
        obj._ordering.append({latest_by: "desc"})
        return obj.get()

    def in_bulk(self, id_list):
        """
        Returns a dictionary mapping each of the given IDs to the object with
        that ID.
        """
        if not id_list:
            return {}
        qs = self._clone()
        qs.add_filter(('pk__in', id_list))
        qs._clear_ordering(force_empty=True)
        return dict([(obj._get_pk_val(), obj) for obj in qs])

    def delete(self):
        """
        Deletes the records in the current QuerySet.
        """
        del_query = self._clone()

        # The delete is actually 2 queries - one to find related objects,
        # and one to delete. Make sure that the discovery of related
        # objects is performed on the same database as the deletion.
        del_query._clear_ordering()
        connection = self.model._meta.dj_connection

        connection.connection.delete_by_query(indices=connection.database, doc_types=self.model._meta.db_table,
                                              query=del_query._build_query())
        connection.connection.indices.refresh(indices=connection.database)
        # Clear the result cache, in case this QuerySet gets reused.
        self._result_cache = None

    def update(self, *args, **kwargs):
        """
        Updates all elements in the current QuerySet, setting all the given
        fields to the appropriate values.
        """
        if args:
            for arg in args:
                if not isinstance(arg, ScriptField):
                    raise InvalidParameter("%s this must be a ScriptField or derivated" % arg)

        query = self._build_query()
        connection = self.model._meta.dj_connection
        query.fields = ["_id", "_type", "_index"]
        # results = connection.connection.search(query, indices=connection.database, doc_types=self.type,
        #                             model=self.model, scan=True)

        conn = connection.connection
        results = conn.search(query, indices=connection.database, doc_types=self.type, scan=True)

        for item in results:
            if kwargs:
                conn.update(item._meta.index, item._meta.type, item._meta.id, document=kwargs, bulk=True)
            for script in args:
                conn.update(item._meta.index, item._meta.type, item._meta.id,
                            script=script.script, lang=script.lang, params=script.params, bulk=True)

        connection.connection.flush_bulk(True)
        # Clear the result cache, in case this QuerySet gets reused.
        self._result_cache = None

    def exists(self):
        if self._result_cache is None:
            len(self)
        return bool(self._result_cache.total != 0)

    ##################################################
    # PUBLIC METHODS THAT RETURN A QUERYSET SUBCLASS #
    ##################################################

    def _django_to_es_field(self, field):
        """We use this function in value_list and ordering to get the correct fields name"""
        from django.db import models

        prefix = ""
        if field.startswith("-"):
            prefix = "-"
            field = field.lstrip("-")

        if field in ["id", "pk"]:
            return "_id", models.AutoField

        try:
            dj_field, _, _, _ = self.model._meta.get_field_by_name(field)
            if isinstance(dj_field, models.ForeignKey):
                return prefix + field + "_id", models.ForeignKey
            else:
                return prefix + field, dj_field
        except models.FieldDoesNotExist:
            pass

        return prefix + field.replace(FIELD_SEPARATOR, "."), None


    def _django_to_es_fields(self, dj_fields):
        """We use this function in value_list and ordering to get the correct fields name"""
        return [self._django_to_es_field(field)[0] for field in dj_fields]

    def _cooked_fields(self, dj_fields):
        """
        Returns a tuple of cooked fields
        :param dj_fields: a list of django name fields
        :return:
        """
        from django.db import models

        valids = []
        for field in dj_fields:
            try:
                dj_field, _, _, _ = self.model._meta.get_field_by_name(field)
                if isinstance(dj_field, models.ForeignKey):
                    valids.append((field + "_id", field, dj_field))
                else:
                    valids.append((field, field, dj_field))
            except models.FieldDoesNotExist:
                valids.append((field, field, None))
        return valids


    def values(self, *fields):
        assert fields, "A least a field is required"
        search = self._build_search()
        search.facet.reset()
        search.fields = self._django_to_es_fields(fields)
        connection = self.model._meta.dj_connection

        return connection.connection.search(search, indices=connection.database, doc_types=self.type)

    def values_list(self, *fields, **kwargs):
        flat = kwargs.pop('flat', False)
        if kwargs:
            raise TypeError('Unexpected keyword arguments to values_list: %s'
                            % (kwargs.keys(),))
        if flat and len(fields) > 1:
            raise TypeError("'flat' is not valid when values_list is called with more than one field.")
        assert fields, "A least a field is required"
        search = self._build_search()
        search.facet.reset()
        search.fields = self._django_to_es_fields(fields)
        connection = self.model._meta.dj_connection

        values_resolver = ValueListResolver(self.model, self._cooked_fields(fields), flat)
        return connection.connection.search(search, indices=connection.database, doc_types=self.type,
                                            model=values_resolver)

    def dates(self, field_name, kind, order='ASC'):
        """
        Returns a list of datetime objects representing all available dates for
        the given field_name, scoped to 'kind'.
        """

        assert kind in ("month", "year", "day", "week", "hour", "minute"), \
            "'kind' must be one of 'year', 'month', 'day', 'week', 'hour' and 'minute'."
        assert order in ('ASC', 'DESC'), \
            "'order' must be either 'ASC' or 'DESC'."

        search = self._build_search()
        search.facet.reset()
        search.facet.add_date_facet(name=field_name.replace("__", "."),
                                    field=field_name, interval=kind)
        search.size = 0
        connection = self.model._meta.dj_connection

        resulset = connection.connection.search(search, indices=connection.database, doc_types=self.type)
        resulset.fix_facets()
        entries = []
        for val in resulset.facets.get(field_name.replace("__", ".")).get("entries", []):
            if "time" in val:
                entries.append(val["time"])
        if order == "ASC":
            return sorted(entries)

        return sorted(entries, reverse=True)

    def none(self):
        """
        Returns an empty QuerySet.
        """
        return EmptyQuerySet(model=self.model, using=self._using, connection=self._connection)


    ##################################################################
    # PUBLIC METHODS THAT ALTER ATTRIBUTES AND RETURN A NEW QUERYSET #
    ##################################################################

    def all(self):
        """
        Returns a new QuerySet that is a copy of the current one. This allows a
        QuerySet to proxy for a model manager in some cases.
        """
        return self._clone()

    def query(self, *args, **kwargs):
        """
        Returns a new QuerySet instance with the args ANDed to the existing
        set.
        """
        clone = self._clone()
        queries = []
        from pyes.query import Query

        if args:
            for f in args:
                if isinstance(f, Query):
                    queries.append(f)
                else:
                    raise TypeError('Only Query objects can be passed as argument')

        for field, value in kwargs.items():
            if value == [None]:
                value = ["$$$$"]
            queries.append(self._build_inner_query(field, value))

        clone._queries.extend(queries)
        return clone

    def rescorer(self, rescorer):
        """
        Returns a new QuerySet with a set rescorer.
        """
        clone = self._clone()
        clone._rescorer=rescorer
        return clone

    def filter(self, *args, **kwargs):
        """
        Returns a new QuerySet instance with the args ANDed to the existing
        set.
        """
        return self._filter_or_exclude(False, *args, **kwargs)

    def exclude(self, *args, **kwargs):
        """
        Returns a new QuerySet instance with NOT (args) ANDed to the existing
        set.
        """
        return self._filter_or_exclude(True, *args, **kwargs)


    def _filter_or_exclude(self, negate, *args, **kwargs):
        clone = self._clone()
        filters = self._build_filter(*args, **kwargs)

        if negate:
            if len(filters) > 1:
                filters = ANDFilter(filters)
            else:
                filters = filters[0]
            clone._filters.append(NotFilter(filters))
        else:
            clone._filters.extend(filters)
        return clone

    FILTER_OPERATORS = {
        'exact': '',
        'iexact': "",
        'contains': "",
        'icontains': "",
        'regex': '',
        'iregex': "",
        'gt': '',
        'gte': '',
        'lt': '',
        'lte': '',
        'startswith': "",
        'endswith': "",
        'istartswith': "",
        'iendswith': "",
        'in': "",
        'ne': "",
        'isnull': "",
        'ismissing': "",
        'exists': "",
        'year': "",
        'prefix': "",
        'match': "",
    }

    def _get_filter_modifier(self, field):
        """Detect the filter modifier"""
        tokens = field.split(FIELD_SEPARATOR)
        if len(tokens) == 1:
            return field, ""
        if tokens[-1] in self.FILTER_OPERATORS.keys():
            return u'.'.join(tokens[:-1]), tokens[-1]
        return u'.'.join(tokens), ""

    def _prepare_value(self, value, dj_field=None):
        """Cook the value"""
        from django.db import models

        if isinstance(value, (six.string_types, int, float)):
            return value
        elif isinstance(value, SimpleLazyObject):
            return value.pk
        elif isinstance(value, models.Model):
            if dj_field:
                if isinstance(dj_field, models.ForeignKey):
                    return value.pk
                    #TODO validate other types
            return value
        elif isinstance(value, (ResultSet, EmptyQuerySet, EmptyResultSet, list)):
            return [self._prepare_value(v, dj_field=dj_field) for v in value]
        elif isinstance(value, QuerySet):
            value = value._clone()
            return [self._prepare_value(v, dj_field=dj_field) for v in value]
        return value

    def _build_inner_filter(self, field, value):
        from django.db import models


        field, modifier = self._get_filter_modifier(field)
        dj_field = None
        try:
            dj_field, _, _, _ = self.model._meta.get_field_by_name(field)
            if isinstance(dj_field, models.ForeignKey):
                field += "_id"
                if isinstance(value, models.Model):
                    if not value.pk:
                        value.save()
                    value = value.pk
            if dj_field:
                if isinstance(dj_field, models.ForeignKey) and modifier == "id":
                    field += "_id"
                    modifier = ""
                elif isinstance(dj_field, models.ListField) and isinstance(dj_field.item_field, models.ForeignKey):
                    dj_field = dj_field.item_field

        except models.FieldDoesNotExist:
            pass

        #calculating lazy resultset
        value = self._prepare_value(value, dj_field=dj_field)

        pk_column = self.model._meta.pk.column
        #case filter id
        if modifier in ["", "in"] and field in ["pk", pk_column]:
            if isinstance(value, list):
                return IdsFilter(value)
            return IdsFilter([value])

        if not modifier:
            if isinstance(value, list):
                return TermsFilter(field, value)
            return TermFilter(field, value)

        if modifier == "in":
            return TermsFilter(field, value)
        elif modifier == "gt":
            return RangeFilter(ESRange(field, from_value=value, include_lower=False))
        elif modifier == "gte":
            return RangeFilter(ESRange(field, from_value=value, include_lower=True))
        elif modifier == "lte":
            return RangeFilter(ESRange(field, to_value=value, include_upper=True))
        elif modifier == "lt":
            return RangeFilter(ESRange(field, to_value=value, include_upper=False))
        elif modifier == "in":
            return TermsFilter(field, values=value)
        elif modifier == "ne":
            return NotFilter(TermFilter(field, value))
        elif modifier == "exists":
            if isinstance(value, bool) and value:
                return ExistsFilter(field)
            return NotFilter(ExistsFilter(field))
        elif modifier in ["startswith", "istartswith"]:
            return RegexTermFilter(field, "^" + value + ".*",
                                   ignorecase=modifier == "istartswith")
        elif modifier in ["endswith", "iendswith"]:
            return RegexTermFilter(field, ".*" + value + "$",
                                   ignorecase=modifier == "iendswith")
        elif modifier in ["contains", "icontains"]:
            return RegexTermFilter(field, ".*" + value + ".*",
                                   ignorecase=modifier == "icontains")
        elif modifier in ["regex", "iregex"]:
            return RegexTermFilter(field, value,
                                   ignorecase=modifier == "iregex")
        elif modifier == "prefix":
            return PrefixFilter(field, value)

        elif modifier in ["exact", "iexact"]:
            return TermFilter(field, value)
        elif modifier == "year":
            if isinstance(value, list):
                return RangeFilter(ESRange(field, value[0], value[1], True, True))
            if isinstance(value, tuple):
                return RangeFilter(ESRange(field, value[0], value[1], True, True))
            else:
                import datetime
                from dateutil.relativedelta import relativedelta

                start = datetime.datetime(value, 1, 1)
                end = start + relativedelta(years=1)
                return RangeFilter(ESRange(field, start, end, True, False))
        elif modifier in ["isnull"]:
            if value:
                return MissingFilter(field)
            return ExistsFilter(field)

        raise NotImplementedError()

    def _build_inner_query(self, field, value):
        from django.db import models
        from pyes.query import IdsQuery, TermQuery, TermsQuery, RangeQuery, RegexTermQuery, PrefixQuery, MatchQuery

        field, modifier = self._get_filter_modifier(field)
        dj_field = None
        try:
            dj_field, _, _, _ = self.model._meta.get_field_by_name(field)
            if isinstance(dj_field, models.ForeignKey):
                field += "_id"
                if isinstance(value, models.Model):
                    if not value.pk:
                        value.save()
                    value = value.pk
            if dj_field:
                if isinstance(dj_field, models.ForeignKey) and modifier == "id":
                    field += "_id"
                    modifier = ""
                elif isinstance(dj_field, models.ListField) and isinstance(dj_field.item_field, models.ForeignKey):
                    dj_field = dj_field.item_field

        except models.FieldDoesNotExist:
            pass

        #calculating lazy resultset
        value = self._prepare_value(value, dj_field=dj_field)

        pk_column = self.model._meta.pk.column
        #case filter id
        if modifier in ["", "in"] and field in ["pk", pk_column]:
            if isinstance(value, list):
                return IdsQuery(value)
            return IdsQuery([value])

        if not modifier:
            if isinstance(value, list):
                return TermsQuery(field, value)
            return TermQuery(field, value)

        if modifier == "in":
            return TermsQuery(field, value)
        elif modifier == "gt":
            return RangeQuery(ESRange(field, from_value=value, include_lower=False))
        elif modifier == "gte":
            return RangeQuery(ESRange(field, from_value=value, include_lower=True))
        elif modifier == "lte":
            return RangeQuery(ESRange(field, to_value=value, include_upper=True))
        elif modifier == "lt":
            return RangeQuery(ESRange(field, to_value=value, include_upper=False))
        elif modifier == "in":
            return TermsQuery(field, values=value)
        elif modifier in ["startswith", "istartswith"]:
            return RegexTermQuery(field, "^" + value + ".*",
                                  ignorecase=modifier == "istartswith")
        elif modifier in ["endswith", "iendswith"]:
            return RegexTermQuery(field, ".*" + value + "$",
                                  ignorecase=modifier == "iendswith")
        elif modifier in ["contains", "icontains"]:
            return RegexTermQuery(field, ".*" + value + ".*",
                                  ignorecase=modifier == "icontains")
        elif modifier in ["regex", "iregex"]:
            return RegexTermQuery(field, value,
                                  ignorecase=modifier == "iregex")
        elif modifier == "prefix":
            return PrefixQuery(field, value)

        elif modifier in ["exact", "iexact"]:
            return TermQuery(field, value)
        elif modifier == "year":
            if isinstance(value, list):
                return RangeQuery(ESRange(field, value[0], value[1], True, True))
            if isinstance(value, tuple):
                return RangeQuery(ESRange(field, value[0], value[1], True, True))
            else:
                import datetime
                from dateutil.relativedelta import relativedelta

                start = datetime.datetime(value, 1, 1)
                end = start + relativedelta(years=1)
                return RangeQuery(ESRange(field, start, end, True, False))
        elif modifier in ["match"]:
            return MatchQuery(field, value)
        raise NotImplementedError()

    def _Q_to_filter(self, q):
        """
        Convert a Q object to filter
        :param q: a Q Object
        :return: a filter object
        """
        default_filter = ANDFilter
        if q.connector == "OR":
            default_filter = ORFilter
        filters = []
        for child in q.children:
            if isinstance(child, Q):
                if child.children:
                    filters.append(self._Q_to_filter(child))
            elif isinstance(child, tuple):
                field, value = child
                filters.append(self._build_inner_filter(field, value))
        if len(filters) == 1:
            filter = filters[0]
            if q.negated:
                return NotFilter(filter)
            return filter
        if q.negated:
            return NotFilter(default_filter(filters))
        return default_filter(filters)


    def _build_filter(self, *args, **kwargs):
        filters = []

        if args:
            for f in args:
                if isinstance(f, Filter):
                    filters.append(f)
                    #elif isinstance(f, dict):
                    #TODO: dict parser
                elif isinstance(f, Q):
                    filters.append(self._Q_to_filter(f))
                else:
                    raise TypeError('Only Filter objects can be passed as argument')

        for field, value in kwargs.items():
            if value == [None]:
                value = ["$$$$"]
                # if FIELD_SEPARATOR in field:
            #     if field.rsplit(FIELD_SEPARATOR, 1)[1] == 'isnull' and value == False:
            #         return filters
            filters.append(self._build_inner_filter(field, value))
        return filters

    def connection(self, connection):
        self._connection = connection
        return self

    def complex_filter(self, filter_obj):
        """
        Returns a new QuerySet instance with filter_obj added to the filters.

        filter_obj can be a Q object (or anything with an add_to_query()
        method) or a dictionary of keyword lookup arguments.

        This exists to support framework features such as 'limit_choices_to',
        and usually it will be more natural to use other methods.
        """
        if isinstance(filter_obj, Filter):
            clone = self._clone()
            clone._filters.add(filter_obj)
            return clone
        return self._filter_or_exclude(None, **filter_obj)


    def facet(self, *args, **kwargs):
        return self.annotate(*args, **kwargs)

    def annotate(self, *args, **kwargs):
        """
        Return a query set in which the returned objects have been annotated
        with data aggregated from related fields.
        """
        obj = self._clone()
        if args:
            for arg in args:
                if isinstance(arg, Facet):
                    obj._facets.append(arg)
                elif isinstance(arg, six.string_types):
                    modifier = "term"
                    tokens = arg.split("__")
                    if len(tokens)>1 and tokens[-1] in ["term", "stat", "histo", "date"]:
                        modifier=tokens[-1]
                        tokens=tokens[:-1]
                    field, djfield = self._django_to_es_field("__".join(tokens))
                    if modifier=="term":
                        obj._facets.append(TermFacet(name=arg, field=field, **kwargs))
                    elif modifier=="term_stat":
                        obj._facets.append(TermStatsFacet(name=arg, **kwargs))
                    elif modifier=="stat":
                        obj._facets.append(StatisticalFacet(name=arg, field=field, **kwargs))
                    elif modifier=="histo":
                        obj._facets.append(HistogramFacet(name=arg, field=field, **kwargs))
                    elif modifier=="date":
                        obj._facets.append(DateHistogramFacet(name=arg, field=field, **kwargs))
                else:
                    raise NotImplementedError("invalid type")
        else:
            # Add the aggregates/facet to the query
            for name, field in kwargs.items():
                obj._facets.append(
                    TermFacet(field=field.replace(FIELD_SEPARATOR, "."), name=name.replace(FIELD_SEPARATOR, ".")))

        return obj

    def order_by(self, *field_names):
        """
        Returns a new QuerySet instance with the ordering changed.
        We have a special field "_random"
        """
        obj = self._clone()
        obj._clear_ordering()
        self._insert_ordering(obj, *field_names)
        return obj


    def _insert_ordering(self, obj, *field_names):

        for field in field_names:
            if isinstance(field, dict):
                obj._clear_ordering()
                obj._ordering.append(field)
            elif field == "_random":
                obj._clear_ordering()
                obj._ordering.append({
                    "_script": {
                        "script": "Math.random()",
                        "type": "number",
                        "params": {},
                        "order": "asc"
                    }
                })
                break
            elif field.startswith("-"):
                obj._ordering.append({field.lstrip("-"): {"order": "desc", "ignore_unmapped": True}})
            else:
                obj._ordering.append({field: {"order": "asc", "ignore_unmapped": True}})
        return obj


    def distinct(self, *field_names):
        """
        Returns a new QuerySet instance that will select only distinct results.
        """
        return self


    def reverse(self):
        """
        Reverses the ordering of the QuerySet.
        """
        clone = self._clone()
        assert self._ordering, "You need to set an ordering for reverse"
        ordering = []
        for order in self._ordering:
            for k, v in order.items():
                if v == "asc":
                    ordering.append({k: "desc"})
                else:
                    ordering.append({k: "asc"})
        clone._ordering = ordering
        return clone

    def defer(self, *fields):
        """
        Defers the loading of data for certain fields until they are accessed.
        The set of fields to defer is added to any existing set of deferred
        fields. The only exception to this is if None is passed in as the only
        parameter, in which case all deferrals are removed (None acts as a
        reset option).
        """
        raise NotImplementedError()

    #        clone = self._clone()
    #        if fields == (None,):
    #            clone.query.clear_deferred_loading()
    #        else:
    #            clone.query.add_deferred_loading(fields)
    #        return clone

    def only(self, *fields):
        """
        Essentially, the opposite of defer. Only the fields passed into this
        method and that are not already specified as deferred are loaded
        immediately when the queryset is evaluated.
        """
        clone = self._clone()
        clone._fields = fields
        return clone

    def index(self, alias):
        """
        Selects which database this QuerySet should execute its query against.
        """
        clone = self._clone()
        clone._index = alias
        return clone

    def size(self, size):
        """
        Set the query size of  this QuerySet should execute its query against.
        """
        clone = self._clone()
        clone._size = size
        return clone

    ###################################
    # PUBLIC INTROSPECTION ATTRIBUTES #
    ###################################

    def ordered(self):
        """
        Returns True if the QuerySet is ordered -- i.e. has an order_by()
        clause or a default ordering on the model.
        """
        return len(self._ordering) > 0

    ordered = property(ordered)


    ###################
    # PUBLIC METHODS  #
    ###################

    @classmethod
    def from_qs(cls, qs, **kwargs):
        """
        Creates a new queryset using class `cls` using `qs'` data.

        :param qs: The query set to clone
        :keyword kwargs: The kwargs to pass to _clone method
        """
        assert issubclass(cls, QuerySet), "%s is not a QuerySet subclass" % cls
        assert isinstance(qs, QuerySet), "qs has to be an instance of queryset"
        return qs._clone(klass=cls, **kwargs)

    def evaluated(self):
        """
        Lets check if the queryset was already evaluated without accessing
        private methods / attributes
        """
        return not self._result_cache is None

    ###################
    # PRIVATE METHODS #
    ###################
    def _batched_insert(self, objs, fields, batch_size):
        """
        A little helper method for bulk_insert to insert the bulk one batch
        at a time. Inserts recursively a batch from the front of the bulk and
        then _batched_insert() the remaining objects again.
        """
        raise NotImplementedError()

    #        if not objs:
    #            return
    #        ops = connections[self.db].ops
    #        batch_size = (batch_size or max(ops.bulk_batch_size(fields, objs), 1))
    #        for batch in [objs[i:i+batch_size]
    #                      for i in range(0, len(objs), batch_size)]:
    #            self.model._base_manager._insert(batch, fields=fields,
    #                                             using=self.db)

    def _get_hash_id(self, record, uniq_together):
        valid_fields = []
        if isinstance(uniq_together, six.string_types):
            valid_fields.append(uniq_together)
        elif isinstance(uniq_together, (list, tuple)):
            for v in uniq_together:
                if isinstance(v, six.string_types):
                    valid_fields.append(v)
                else:
                    valid_fields.extend(list(v))
        if not valid_fields:
            return None

        values = []
        for f in valid_fields:
            val = record.get(f, u"")
            if val:
                values.append(unicode(val))
        if not values:
            return None

        return make_id("_".join(values).strip().lower())

    def _insert(self, objs, fields=None, **kwargs):

        single = False
        using = kwargs.get("using")
        if not isinstance(objs, list):
            single = True
            objs = [objs]
        if len(objs) == 1:
            single = True

        #get fields
        if not fields:
            fields = self.model._meta.concrete_fields

        connection = self.model._meta.dj_connection

        if using and using not in ["default", "echidnasearch"]:
            database = using
        else:
            database=connection.database

        meta = self.model._meta

        db_table = meta.db_table
        bulk = not kwargs.get("return_id", False)
        force_insert = kwargs.get("force_insert", False)
        pk_column = meta.pk.column
        unique_together_name = []
        valid_fields = []
        if isinstance(meta.unique_together, six.string_types):
            valid_fields.append(meta.uniq_together)
        elif isinstance(meta.unique_together, (list, tuple)):
            for v in meta.unique_together:
                if isinstance(v, six.string_types):
                    valid_fields.append(v)
                else:
                    valid_fields.extend(list(v))
                    # for field in fields:
                    #     if field.name in valid_fields:
                    #         unique_together_name.append(field.attname)

        ids = []
        for obj in objs:
            record = obj.to_dict(fields, **kwargs)
            pk = record.get(pk_column, None)
            record.pop("_id", None)
            #remove empty values
            if pk is None:
                # pk = self._get_hash_id(record, meta.unique_together)
                pk = obj.calc_pk()

            res = connection.connection.index(record, index=database, doc_type=db_table, id=pk, bulk=bulk,
                                              force_insert=force_insert)
            if not bulk:
                ids.append(res._id)
        if connection.force_refresh:
            connection.connection.refresh()
        else:
            connection._dirty = True
        if bulk:
            return []
        if single:
            return ids[0]
        return ids

    _insert.queryset_only = False

    def _clone(self, klass=None, setup=False, **kwargs):
        params = dict(model=self.model, using=self.index)
        if klass is None:
            klass = self.__class__
        if repr(klass) == "<class 'django.db.models.fields.related.RelatedManager'>":
            params["instance"] = getattr(self, "instance", None)# only for RelatedManager
        c = klass(**params)
        #copy filters/queries/facet????
        c.__dict__.update(kwargs)
        c._queries = list(self._queries)
        c._filters = list(self._filters)
        c._facets = list(self._facets)
        c._fields = list(self._fields)
        c._ordering = list(self._ordering)
        c._size = self._size
        c._scan = self._scan
        c._rescorer = self._rescorer
        c._connection = self._connection
        c._using = self._using
        return c

    # When used as part of a nested query, a queryset will never be an "always
    # empty" result.
    value_annotation = True

    def get_facets(self):
        len(self)
        if isinstance(self._result_cache, ResultSetList):
            self._result_cache = None
            len(self)
        self._result_cache.fix_facets()
        return FacetHelper(self.model, self._result_cache.facets)

    #converting functions
    #TODO: remove
    def convert_value_for_db(self, db_type, value):
        if db_type == "unicode" and not isinstance(value, six.string_types):
            return unicode(value)
        return value

    #def _build_objects(self, objs, fields=None, raw=False, **kwargs):
    #    from django.db import connections
    #
    #    connection = connections[self.model._meta.using]
    #    from django.db.models import AutoField
    #
    #    for obj in objs:
    #        data = {}
    #        for f in fields:
    #            val = f.get_db_prep_save(getattr(obj, f.attname) if raw else f.pre_save(obj, True),
    #                                     connection=connection)
    #
    #            if not f.null and val is None:
    #                if isinstance(f, AutoField):
    #                    continue
    #                raise IntegrityError("You can't set %s (a non-nullable field) to None!" % f.name)
    #
    #            db_type = f.db_type(connection=connection)
    #            value = self.convert_value_for_db(db_type, val)
    #            if value is None:
    #                continue
    #            data[f.column] = value
    #        yield (obj, data)
    #
    #    raise StopIteration

    def refresh(self):
        """Refresh an index"""
        connection = self.model._meta.dj_connection
        return connection.connection.indices.refresh(indices=connection.database)


    def terms(self, field):
        connection = self.model._meta.dj_connection
        return connection.connection.terms(connection.database, self.model._meta.db_table, field=field)["terms"]

    def _update(self, values):

        connection = self.model._meta.dj_connection
        index = self.get_index(connection)

        meta = self.model._meta
        db_table = meta.db_table
        updated = False
        for obj in self:
            record = {}
            for field, boh, new_value in values:
                record[field.attname] = field.get_db_prep_save(new_value, connection=connection)
            res = connection.connection.update(index=index, doc_type=self.type, id=obj.pk,
                                               document=record)
            updated = True
        return updated

    _update.queryset_only = False

    def get_objects_for_user(self, user, perms=None):
        if user.is_superuser:
            return self.all()
        prefix = "u.%s" % user.pk
        group_perms = user.get_group_cooked_perm_list()

        return self.filter(perms__startswith=prefix)

        # if perms is None:
        #     perms = [u'%s.%s.view' % (self.model._meta.app_label, self.model._meta.model_name)]
        #
        # return get_objects_for_user(user, perms=perms, klass=self.model)

    def get_index(self, connection=None):
        if self.model._meta.index :
            return self.model._meta.index
        if self._using and self._using not in ["default", "echidnasearch"]:
            return self._using
        return self.model._meta.get_index(connection=connection)


class EmptyQuerySet(QuerySet):
    def _do_query(self):
        return EmptyResultSet()


class ValueListResolver(object):
    """
    Class to resolve vertices in django objects
    """

    def __init__(self, model, fields, flat=False):
        """
        :param model: the current model
        :param fields: a cooked fields set (es_field, djfield, field)
        """
        self.fields = fields
        self.model = model
        self.flat = flat

    def __call__(self, *args, **kwargs):
        results = []
        from django.db import models

        es_fields = args[1].get("fields", {})
        for es_name, dj_name, djfield in self.fields:
            if es_name == "pk":
                value = args[1]["_id"]
            elif es_name == "id":
                value = es_fields.get(es_name, args[1]["_id"])
            else:
                value = es_fields.get(es_name, None)
            if value and isinstance(djfield, models.ForeignKey):
                djfield.rel.to.objects.get(pk=value)
            if self.flat:
                return value
            results.append(value)
        return tuple(results)


class ModelIteratorResolver(object):
    def __init__(self, model, items=None):
        self.model = model
        self.items = items
        self.iterpos = 0
        self._current_item = 0

    def __len__(self):
        return len(self.items)

    def count(self):
        return len(self.items)

    def total(self):
        return len(self.items)

    def __call__(self, *args, **kwargs):
        return list(self)

    def __getitem__(self, val):
        if not isinstance(val, (int, long, slice)):
            raise TypeError('%s indices must be integers, not %s' % (
                self.__class__.__name__, val.__class__.__name__))

        def get_start_end(val):
            if isinstance(val, slice):
                start = val.start
                if not start:
                    start = 0
                end = val.stop or len(self.items)
                if end < 0:
                    end = len(self.items) + end
                if end > len(self.items):
                    end = len(self.items)
                return start, end
            return val, val + 1

        start, end = get_start_end(val)

        if not isinstance(val, slice):
            if len(self.items) == 1:
                val = self.get_model(self.items[0])
                if val:
                    return val
                raise StopIteration
            raise IndexError
        return [v for v in [self.get_model(hit) for hit in self.items[start:end]] if v]

    def next(self):
        if len(self.items) == self.iterpos:
            raise StopIteration

        res = self.items[self.iterpos]
        val = self.get_model(res)
        if not val:
            return self.next()

        self.iterpos += 1
        if len(self.items) == self.iterpos:
            raise StopIteration
        return val

    def __iter__(self):
        self.iterpos = 0
        self._current_item = 0
        return self

    def get_model(self, object_id):
        try:
            return self.model.objects.get(pk=object_id)
        except self.model.DoesNotExist:
            self.items.remove(object_id)
            return None


class FacetHelper(dict):
    def __init__(self, model, facets):
        self._model = model
        self.update(facets)

    def __setattr__(self, key, value):
        if not self.__dict__.has_key(
                '_FacetHelper__initialised'):  # this test allows attributes to be set in the __init__ method
            return dict.__setattr__(self, key, value)
        elif self.__dict__.has_key(key):       # any normal attributes are handled normally
            dict.__setattr__(self, key, value)
        else:
            self.__setitem__(key, value)

    def get_as_list(self, name):
        terms = self.get(name, {}).get("terms", [])
        for term in terms:
            yield term["term"]
        raise StopIteration

########NEW FILE########
__FILENAME__ = constants
#
# Autogenerated by Thrift
#
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING
#
from __future__ import absolute_import

from thrift.Thrift import *
from .ttypes import *


########NEW FILE########
__FILENAME__ = Rest
#
# Autogenerated by Thrift
#
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING
#
from __future__ import absolute_import

from thrift.Thrift import *
from .ttypes import *
from thrift.Thrift import TProcessor
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol, TProtocol
try:
  from thrift.protocol import fastbinary
except ImportError:
  fastbinary = None


class Iface:
  def execute(self, request):
    """
    Parameters:
     - request
    """
    pass


class Client(Iface):
  def __init__(self, iprot, oprot=None):
    self._iprot = self._oprot = iprot
    if oprot != None:
      self._oprot = oprot
    self._seqid = 0

  def execute(self, request):
    """
    Parameters:
     - request
    """
    self.send_execute(request)
    return self.recv_execute()

  def send_execute(self, request):
    self._oprot.writeMessageBegin('execute', TMessageType.CALL, self._seqid)
    args = execute_args()
    args.request = request
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_execute(self):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = execute_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    raise TApplicationException(TApplicationException.MISSING_RESULT, "execute failed: unknown result");


class Processor(Iface, TProcessor):
  def __init__(self, handler):
    self._handler = handler
    self._processMap = {}
    self._processMap["execute"] = Processor.process_execute

  def process(self, iprot, oprot):
    (name, type, seqid) = iprot.readMessageBegin()
    if name not in self._processMap:
      iprot.skip(TType.STRUCT)
      iprot.readMessageEnd()
      x = TApplicationException(TApplicationException.UNKNOWN_METHOD, 'Unknown function %s' % (name))
      oprot.writeMessageBegin(name, TMessageType.EXCEPTION, seqid)
      x.write(oprot)
      oprot.writeMessageEnd()
      oprot.trans.flush()
      return
    else:
      self._processMap[name](self, seqid, iprot, oprot)
    return True

  def process_execute(self, seqid, iprot, oprot):
    args = execute_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = execute_result()
    result.success = self._handler.execute(args.request)
    oprot.writeMessageBegin("execute", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()


# HELPER FUNCTIONS AND STRUCTURES

class execute_args:
  """
  Attributes:
   - request
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'request', (RestRequest, RestRequest.thrift_spec), None, ), # 1
  )

  def __init__(self, request=None):
    self.request = request

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.request = RestRequest()
          self.request.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('execute_args')
    if self.request != None:
      oprot.writeFieldBegin('request', TType.STRUCT, 1)
      self.request.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      if self.request is None:
        raise TProtocol.TProtocolException(message='Required field request is unset!')
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.items()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class execute_result:
  """
  Attributes:
   - success
  """

  thrift_spec = (
    (0, TType.STRUCT, 'success', (RestResponse, RestResponse.thrift_spec), None, ), # 0
  )

  def __init__(self, success=None):
    self.success = success

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.STRUCT:
          self.success = RestResponse()
          self.success.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('execute_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.STRUCT, 0)
      self.success.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.items()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

########NEW FILE########
__FILENAME__ = simple_test
#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import print_function

import sys
import pprint
from urlparse import urlparse
from thrift.transport import TTransport
from thrift.transport import TSocket
from thrift.transport import THttpClient
from thrift.protocol import TBinaryProtocol

from .Rest import Client
from .ttypes import *

pp = pprint.PrettyPrinter(indent = 4)
host = '127.0.0.1'
port = 9500
uri = ''
framed = False
http = False
argi = 1

socket = TSocket.TSocket(host, port)
transport = TTransport.TBufferedTransport(socket)
protocol = TBinaryProtocol.TBinaryProtocol(transport)
client = Client(protocol)
transport.open()

res = RestRequest(0, "/test-index/test-type/1", {}, {})
print(client.execute(res))

transport.close()

########NEW FILE########
__FILENAME__ = ttypes
#
# Autogenerated by Thrift
#
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING
#

from thrift.Thrift import *

from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol, TProtocol
try:
  from thrift.protocol import fastbinary
except ImportError:
  fastbinary = None


class Method(object):
  GET = 0
  PUT = 1
  POST = 2
  DELETE = 3
  HEAD = 4
  OPTIONS = 5

  _VALUES_TO_NAMES = {
    0: "GET",
    1: "PUT",
    2: "POST",
    3: "DELETE",
    4: "HEAD",
    5: "OPTIONS",
  }

  _NAMES_TO_VALUES = {
    "GET": 0,
    "PUT": 1,
    "POST": 2,
    "DELETE": 3,
    "HEAD": 4,
    "OPTIONS": 5,
  }

class Status(object):
  CONT = 100
  SWITCHING_PROTOCOLS = 101
  OK = 200
  CREATED = 201
  ACCEPTED = 202
  NON_AUTHORITATIVE_INFORMATION = 203
  NO_CONTENT = 204
  RESET_CONTENT = 205
  PARTIAL_CONTENT = 206
  MULTI_STATUS = 207
  MULTIPLE_CHOICES = 300
  MOVED_PERMANENTLY = 301
  FOUND = 302
  SEE_OTHER = 303
  NOT_MODIFIED = 304
  USE_PROXY = 305
  TEMPORARY_REDIRECT = 307
  BAD_REQUEST = 400
  UNAUTHORIZED = 401
  PAYMENT_REQUIRED = 402
  FORBIDDEN = 403
  NOT_FOUND = 404
  METHOD_NOT_ALLOWED = 405
  NOT_ACCEPTABLE = 406
  PROXY_AUTHENTICATION = 407
  REQUEST_TIMEOUT = 408
  CONFLICT = 409
  GONE = 410
  LENGTH_REQUIRED = 411
  PRECONDITION_FAILED = 412
  REQUEST_ENTITY_TOO_LARGE = 413
  REQUEST_URI_TOO_LONG = 414
  UNSUPPORTED_MEDIA_TYPE = 415
  REQUESTED_RANGE_NOT_SATISFIED = 416
  EXPECTATION_FAILED = 417
  UNPROCESSABLE_ENTITY = 422
  LOCKED = 423
  FAILED_DEPENDENCY = 424
  INTERNAL_SERVER_ERROR = 500
  NOT_IMPLEMENTED = 501
  BAD_GATEWAY = 502
  SERVICE_UNAVAILABLE = 503
  GATEWAY_TIMEOUT = 504
  INSUFFICIENT_STORAGE = 506

  _VALUES_TO_NAMES = {
    100: "CONT",
    101: "SWITCHING_PROTOCOLS",
    200: "OK",
    201: "CREATED",
    202: "ACCEPTED",
    203: "NON_AUTHORITATIVE_INFORMATION",
    204: "NO_CONTENT",
    205: "RESET_CONTENT",
    206: "PARTIAL_CONTENT",
    207: "MULTI_STATUS",
    300: "MULTIPLE_CHOICES",
    301: "MOVED_PERMANENTLY",
    302: "FOUND",
    303: "SEE_OTHER",
    304: "NOT_MODIFIED",
    305: "USE_PROXY",
    307: "TEMPORARY_REDIRECT",
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    402: "PAYMENT_REQUIRED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    406: "NOT_ACCEPTABLE",
    407: "PROXY_AUTHENTICATION",
    408: "REQUEST_TIMEOUT",
    409: "CONFLICT",
    410: "GONE",
    411: "LENGTH_REQUIRED",
    412: "PRECONDITION_FAILED",
    413: "REQUEST_ENTITY_TOO_LARGE",
    414: "REQUEST_URI_TOO_LONG",
    415: "UNSUPPORTED_MEDIA_TYPE",
    416: "REQUESTED_RANGE_NOT_SATISFIED",
    417: "EXPECTATION_FAILED",
    422: "UNPROCESSABLE_ENTITY",
    423: "LOCKED",
    424: "FAILED_DEPENDENCY",
    500: "INTERNAL_SERVER_ERROR",
    501: "NOT_IMPLEMENTED",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
    504: "GATEWAY_TIMEOUT",
    506: "INSUFFICIENT_STORAGE",
  }

  _NAMES_TO_VALUES = {
    "CONT": 100,
    "SWITCHING_PROTOCOLS": 101,
    "OK": 200,
    "CREATED": 201,
    "ACCEPTED": 202,
    "NON_AUTHORITATIVE_INFORMATION": 203,
    "NO_CONTENT": 204,
    "RESET_CONTENT": 205,
    "PARTIAL_CONTENT": 206,
    "MULTI_STATUS": 207,
    "MULTIPLE_CHOICES": 300,
    "MOVED_PERMANENTLY": 301,
    "FOUND": 302,
    "SEE_OTHER": 303,
    "NOT_MODIFIED": 304,
    "USE_PROXY": 305,
    "TEMPORARY_REDIRECT": 307,
    "BAD_REQUEST": 400,
    "UNAUTHORIZED": 401,
    "PAYMENT_REQUIRED": 402,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "METHOD_NOT_ALLOWED": 405,
    "NOT_ACCEPTABLE": 406,
    "PROXY_AUTHENTICATION": 407,
    "REQUEST_TIMEOUT": 408,
    "CONFLICT": 409,
    "GONE": 410,
    "LENGTH_REQUIRED": 411,
    "PRECONDITION_FAILED": 412,
    "REQUEST_ENTITY_TOO_LARGE": 413,
    "REQUEST_URI_TOO_LONG": 414,
    "UNSUPPORTED_MEDIA_TYPE": 415,
    "REQUESTED_RANGE_NOT_SATISFIED": 416,
    "EXPECTATION_FAILED": 417,
    "UNPROCESSABLE_ENTITY": 422,
    "LOCKED": 423,
    "FAILED_DEPENDENCY": 424,
    "INTERNAL_SERVER_ERROR": 500,
    "NOT_IMPLEMENTED": 501,
    "BAD_GATEWAY": 502,
    "SERVICE_UNAVAILABLE": 503,
    "GATEWAY_TIMEOUT": 504,
    "INSUFFICIENT_STORAGE": 506,
  }


class RestRequest(object):
  """
  Attributes:
   - method
   - uri
   - parameters
   - headers
   - body
  """

  thrift_spec = (
    None, # 0
    (1, TType.I32, 'method', None, None, ), # 1
    (2, TType.STRING, 'uri', None, None, ), # 2
    (3, TType.MAP, 'parameters', (TType.STRING,None,TType.STRING,None), None, ), # 3
    (4, TType.MAP, 'headers', (TType.STRING,None,TType.STRING,None), None, ), # 4
    (5, TType.STRING, 'body', None, None, ), # 5
  )

  def __init__(self, method=None, uri=None, parameters=None, headers=None, body=None):
    self.method = method
    self.uri = uri
    self.parameters = parameters
    self.headers = headers
    self.body = body

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.I32:
          self.method = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.uri = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.MAP:
          self.parameters = {}
          (_ktype1, _vtype2, _size0 ) = iprot.readMapBegin() 
          for _i4 in range(_size0):
            _key5 = iprot.readString();
            _val6 = iprot.readString();
            self.parameters[_key5] = _val6
          iprot.readMapEnd()
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.MAP:
          self.headers = {}
          (_ktype8, _vtype9, _size7 ) = iprot.readMapBegin() 
          for _i11 in range(_size7):
            _key12 = iprot.readString();
            _val13 = iprot.readString();
            self.headers[_key12] = _val13
          iprot.readMapEnd()
        else:
          iprot.skip(ftype)
      elif fid == 5:
        if ftype == TType.STRING:
          self.body = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('RestRequest')
    if self.method != None:
      oprot.writeFieldBegin('method', TType.I32, 1)
      oprot.writeI32(self.method)
      oprot.writeFieldEnd()
    if self.uri != None:
      oprot.writeFieldBegin('uri', TType.STRING, 2)
      oprot.writeString(self.uri)
      oprot.writeFieldEnd()
    if self.parameters != None:
      oprot.writeFieldBegin('parameters', TType.MAP, 3)
      oprot.writeMapBegin(TType.STRING, TType.STRING, len(self.parameters))
      for kiter14,viter15 in self.parameters.items():
        oprot.writeString(kiter14)
        oprot.writeString(viter15)
      oprot.writeMapEnd()
      oprot.writeFieldEnd()
    if self.headers != None:
      oprot.writeFieldBegin('headers', TType.MAP, 4)
      oprot.writeMapBegin(TType.STRING, TType.STRING, len(self.headers))
      for kiter16,viter17 in self.headers.items():
        oprot.writeString(kiter16)
        oprot.writeString(viter17)
      oprot.writeMapEnd()
      oprot.writeFieldEnd()
    if self.body != None:
      oprot.writeFieldBegin('body', TType.STRING, 5)
      oprot.writeString(self.body)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      if self.method is None:
        raise TProtocol.TProtocolException(message='Required field method is unset!')
      if self.uri is None:
        raise TProtocol.TProtocolException(message='Required field uri is unset!')
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.items()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class RestResponse(object):
  """
  Attributes:
   - status
   - headers
   - body
  """

  thrift_spec = (
    None, # 0
    (1, TType.I32, 'status', None, None, ), # 1
    (2, TType.MAP, 'headers', (TType.STRING,None,TType.STRING,None), None, ), # 2
    (3, TType.STRING, 'body', None, None, ), # 3
  )

  def __init__(self, status=None, headers=None, body=None):
    self.status = status
    self.headers = headers
    self.body = body

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.I32:
          self.status = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.MAP:
          self.headers = {}
          (_ktype19, _vtype20, _size18 ) = iprot.readMapBegin() 
          for _i22 in range(_size18):
            _key23 = iprot.readString();
            _val24 = iprot.readString();
            self.headers[_key23] = _val24
          iprot.readMapEnd()
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.body = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('RestResponse')
    if self.status != None:
      oprot.writeFieldBegin('status', TType.I32, 1)
      oprot.writeI32(self.status)
      oprot.writeFieldEnd()
    if self.headers != None:
      oprot.writeFieldBegin('headers', TType.MAP, 2)
      oprot.writeMapBegin(TType.STRING, TType.STRING, len(self.headers))
      for kiter25,viter26 in self.headers.items():
        oprot.writeString(kiter25)
        oprot.writeString(viter26)
      oprot.writeMapEnd()
      oprot.writeFieldEnd()
    if self.body != None:
      oprot.writeFieldBegin('body', TType.STRING, 3)
      oprot.writeString(self.body)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      if self.status is None:
        raise TProtocol.TProtocolException(message='Required field status is unset!')
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.items()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

########NEW FILE########
__FILENAME__ = query
# -*- coding: utf-8 -*-

import six
from .exceptions import InvalidQuery, InvalidParameterQuery, QueryError, \
    ScriptFieldsError
from .sort import SortFactory
from .facets import FacetFactory
from .aggs import AggFactory
from .filters import ANDFilter, Filter
from .highlight import HighLighter
from .scriptfields import ScriptFields
from .utils import clean_string, ESRange, EqualityComparableUsingAttributeDictionary

class Suggest(EqualityComparableUsingAttributeDictionary):
    def __init__(self, fields=None):
        self.fields = fields or {}

    def add(self, text, name, field, size=None):
        """
        Set the suggester with autodetect
        :param text: text
        :param name: name of suggest
        :param field: field to be used
        :param size: number of phrases
        :return: None
        """
        num_tokens = text.count(' ') + 1
        if num_tokens > 1:
            self.add_phrase(text=text, name=name, field=field, size=size)
        else:
            self.add_term(text=text, name=name, field=field, size=size)

    def add_term(self, text, name, field, size=None):
        data = {"field": field}

        if size:
            data["size"] = size
        self.fields[name] = {"text": text, "term": data}

    def add_phrase(self, text, name, field, size=10):
        tokens = text.split()
        gram = field + ".bigram"
        # if len(tokens) > 3:
        #     gram = field + ".trigram"

        data = {
            "analyzer": "standard_lower",
            "field": gram,
            "size": 4,
            "real_word_error_likelihood": 0.95,
            "confidence": 2.0,
            "gram_size": 2,
            "direct_generator": [{
                                     "field": field + ".tkl",
                                     "suggest_mode": "always",
                                     "min_word_len": 1
                                 }, {
                                     "field": field + ".reverse",
                                     "suggest_mode": "always",
                                     "min_word_len": 1,
                                     "pre_filter": "reverse",
                                     "post_filter": "reverse"
                                 }]
        }

        if size:
            data["size"] = size
        self.fields[name] = {"text": text, "phrase": data}

    def is_valid(self):
        return len(self.fields) > 0

    def serialize(self):
        return self.fields

class FieldParameter(EqualityComparableUsingAttributeDictionary):

    def __init__(self, field, query, default_operator="OR", analyzer=None,
                 allow_leading_wildcard=True, lowercase_expanded_terms=True,
                 enable_position_increments=True, fuzzy_prefix_length=0,
                 fuzzy_min_sim=0.5, phrase_slop=0, boost=1.0):
        self.query = query
        self.field = field
        self.default_operator = default_operator
        self.analyzer = analyzer
        self.allow_leading_wildcard = allow_leading_wildcard
        self.lowercase_expanded_terms = lowercase_expanded_terms
        self.enable_position_increments = enable_position_increments
        self.fuzzy_prefix_length = fuzzy_prefix_length
        self.fuzzy_min_sim = fuzzy_min_sim
        self.phrase_slop = phrase_slop
        self.boost = boost

    def serialize(self):
        filters = {}

        if self.default_operator != "OR":
            filters["default_operator"] = self.default_operator
        if self.analyzer:
            filters["analyzer"] = self.analyzer
        if not self.allow_leading_wildcard:
            filters["allow_leading_wildcard"] = self.allow_leading_wildcard
        if not self.lowercase_expanded_terms:
            filters["lowercase_expanded_terms"] = self.lowercase_expanded_terms
        if not self.enable_position_increments:
            filters["enable_position_increments"] = self.enable_position_increments
        if self.fuzzy_prefix_length:
            filters["fuzzy_prefix_length"] = self.fuzzy_prefix_length
        if self.fuzzy_min_sim != 0.5:
            filters["fuzzy_min_sim"] = self.fuzzy_min_sim
        if self.phrase_slop:
            filters["phrase_slop"] = self.phrase_slop

        if self.boost != 1.0:
            filters["boost"] = self.boost
        if filters:
            filters["query"] = self.query
        else:
            filters = self.query
        return self.field, filters


class Search(EqualityComparableUsingAttributeDictionary):
    """A search to be performed.

    This contains a query, and has additional parameters which are used to
    control how the search works, what it should return, etc.

    The rescore parameter takes a Search object created from a RescoreQuery.

    Example:

    q = QueryStringQuery('elasticsearch')
    s = Search(q, fields=['title', 'author'], start=100, size=50)
    results = conn.search(s)
    """

    def __init__(self, query=None, filter=None, fields=None, start=None,
                 size=None, highlight=None, sort=None, explain=False, facet=None, agg=None, rescore=None,
                 window_size=None, version=None, track_scores=None, script_fields=None, index_boost=None,
                 min_score=None, stats=None, bulk_read=None, partial_fields=None, _source=None, timeout=None):
        """
        fields: if is [], the _source is not returned
        """
        if not index_boost: index_boost = {}
        self.query = query
        self.filter = filter
        self.fields = fields
        self.start = start
        self.size = size
        self._highlight = highlight
        self.sort = sort or SortFactory()
        self.explain = explain
        self.facet = facet or FacetFactory()
        self.agg = agg or AggFactory()
        self.rescore = rescore
        self.window_size = window_size
        self.version = version
        self.track_scores = track_scores
        self._script_fields = script_fields
        self.index_boost = index_boost
        self.min_score = min_score
        self.stats = stats
        self.bulk_read = bulk_read
        self.partial_fields = partial_fields
        self._source = _source
        self.timeout = timeout

    def get_facet_factory(self):
        """
        Returns the facet factory
        """
        return self.facet

    def get_agg_factory(self):
        """
        Returns the agg factory
        """
        return self.agg

    def serialize(self):
        """Serialize the search to a structure as passed for a search body."""
        res = {}
        if self.query:
            if isinstance(self.query, dict):
                res["query"] = self.query
            elif isinstance(self.query, Query):
                res["query"] = self.query.serialize()
            else:
                raise InvalidQuery("Invalid query")
        if self.filter:
            res['filter'] = self.filter.serialize()
        if self.facet.facets:
            res['facets'] = self.facet.serialize()
        if self.agg.aggs:
            res['aggs'] = self.agg.serialize()
        if self.rescore:
            res['rescore'] = self.rescore.serialize()
        if self.window_size:
            res['window_size'] = self.window_size
        if self.fields is not None: #Deal properly with self.fields = []
            res['fields'] = self.fields
        if self.size is not None:
            res['size'] = self.size
        if self.start is not None:
            res['from'] = self.start
        if self._highlight:
            res['highlight'] = self._highlight.serialize()
        if self.sort:
            if isinstance(self.sort, SortFactory):
                sort = self.sort.serialize()
                if sort:
                    res['sort'] = sort
            else:
                res['sort'] = self.sort
        if self.explain:
            res['explain'] = self.explain
        if self.version:
            res['version'] = self.version
        if self.track_scores:
            res['track_scores'] = self.track_scores
        if self._script_fields:
            if isinstance(self.script_fields, ScriptFields):
                res['script_fields'] = self.script_fields.serialize()
            elif isinstance(self.script_fields, dict):
                res['script_fields'] = self.script_fields.serialize()
            else:
                raise ScriptFieldsError("Parameter script_fields should of type ScriptFields or dict")
        if self.index_boost:
            res['indices_boost'] = self.index_boost
        if self.min_score:
            res['min_score'] = self.min_score
        if self.stats:
            res['stats'] = self.stats
        if self.partial_fields:
            res['partial_fields'] = self.partial_fields
        if self._source:
            res['_source'] = self._source
        if self.timeout:
            res['timeout'] = self.timeout
        return res

    @property
    def highlight(self):
        if self._highlight is None:
            self._highlight = HighLighter("<b>", "</b>")
        return self._highlight

    @property
    def script_fields(self):
        if self._script_fields is None:
            self._script_fields = ScriptFields()
        return self._script_fields

    def add_highlight(self, field, fragment_size=None,
                      number_of_fragments=None, fragment_offset=None, type=None):
        """Add a highlight field.

        The Search object will be returned, so calls to this can be chained.

        """
        if self._highlight is None:
            self._highlight = HighLighter("<b>", "</b>")
        self._highlight.add_field(field, fragment_size, number_of_fragments, fragment_offset, type=type)
        return self

    def add_index_boost(self, index, boost):
        """Add a boost on an index.

        The Search object will be returned, so calls to this can be chained.

        """
        if boost is None:
            if index in self.index_boost:
                del(self.index_boost[index])
        else:
            self.index_boost[index] = boost
        return self

    def __repr__(self):
        return str(self.serialize())


class Query(EqualityComparableUsingAttributeDictionary):
    """Base class for all queries."""

    def __init__(self, *args, **kwargs):
        if len(args) > 0 or len(kwargs) > 0:
            raise RuntimeWarning("No all parameters are processed by derivated query object")

    def search(self, **kwargs):
        """Return this query wrapped in a Search object.

        Any keyword arguments supplied to this call will be passed to the
        Search object.
        """
        return Search(query=self, **kwargs)

    def serialize(self):
        """Serialize the query to a structure using the query DSL."""
        return {self._internal_name: self._serialize()}

    def _serialize(self):
        raise NotImplementedError

    @property
    def _internal_name(self):
        raise NotImplementedError


class BoolQuery(Query):
    """A boolean combination of other queries.

    BoolQuery maps to Lucene **BooleanQuery**. It is built using one or more
    boolean clauses, each clause with a typed occurrence.  The occurrence types
    are:

    ================  ========================================================
     Occur             Description
    ================  ========================================================
    **must**          The clause (query) must appear in matching documents.
    **should**        The clause (query) should appear in the matching
                      document. A boolean query with no **must** clauses, one
                      or more **should** clauses must match a document. The
                      minimum number of should clauses to match can be set
                      using **minimum_number_should_match** parameter.
    **must_not**      The clause (query) must not appear in the matching
                      documents. Note that it is not possible to search on
                      documents that only consists of a **must_not** clauses.
    ================  ========================================================

    The bool query also supports **disable_coord** parameter (defaults to
    **false**).
    """

    _internal_name = "bool"

    def __init__(self, must=None, must_not=None, should=None, boost=None,
                 minimum_number_should_match=1, disable_coord=None, **kwargs):
        super(BoolQuery, self).__init__(**kwargs)
        self._must = []
        self._must_not = []
        self._should = []
        self.boost = boost
        self.minimum_number_should_match = minimum_number_should_match
        self.disable_coord = disable_coord
        if must:
            self.add_must(must)
        if must_not:
            self.add_must_not(must_not)
        if should:
            self.add_should(should)

    def add_must(self, queries):
        """Add a query to the "must" clause of the query.

        The Query object will be returned, so calls to this can be chained.
        """
        if isinstance(queries, list):
            self._must.extend(queries)
        else:
            self._must.append(queries)
        return self

    def add_should(self, queries):
        """Add a query to the "should" clause of the query.

        The Query object will be returned, so calls to this can be chained.
        """
        if isinstance(queries, list):
            self._should.extend(queries)
        else:
            self._should.append(queries)
        return self

    def add_must_not(self, queries):
        """Add a query to the "must_not" clause of the query.

        The Query object will be returned, so calls to this can be chained.
        """
        if isinstance(queries, list):
            self._must_not.extend(queries)
        else:
            self._must_not.append(queries)
        return self

    def is_empty(self):
        if self._must:
            return False
        if self._must_not:
            return False
        if self._should:
            return False
        return True

    def _serialize(self):
        filters = {}
        if self._must:
            filters['must'] = [f.serialize() for f in self._must]
        if self._must_not:
            filters['must_not'] = [f.serialize() for f in self._must_not]
        if self._should:
            filters['should'] = [f.serialize() for f in self._should]
            filters['minimum_number_should_match'] = self.minimum_number_should_match
        if self.boost:
            filters['boost'] = self.boost
        if self.disable_coord is not None:
            filters['disable_coord'] = self.disable_coord
        if not filters:
            raise RuntimeError("A least a filter must be declared")
        return filters


class ConstantScoreQuery(Query):
    """Returns a constant score for all documents matching a filter.

    Multiple filters may be supplied by passing a sequence or iterator as the
    filter parameter.  If multiple filters are supplied, documents must match
    all of them to be matched by this query.
    """

    _internal_name = "constant_score"

    def __init__(self, filter=None, boost=1.0, **kwargs):
        super(ConstantScoreQuery, self).__init__(**kwargs)
        self.filters = []
        self.queries = []
        self.boost = boost
        if filter:
            self.add(filter)

    def add(self, filter_or_query):
        """Add a filter, or a list of filters, to the query.

        If a sequence of filters is supplied, they are all added, and will be
        combined with an ANDFilter.

        If a sequence of queries is supplied, they are all added, and will be
        combined with an BooleanQuery(must) .

        """
        if isinstance(filter_or_query, Filter):
            if self.queries:
                raise QueryError("A Query is required")
            self.filters.append(filter_or_query)
        elif isinstance(filter_or_query, Query):
            if self.filters:
                raise QueryError("A Filter is required")
            self.queries.append(filter_or_query)
        else:
            for item in filter_or_query:
                self.add(item)
        return self

    def is_empty(self):
        """Returns True if the query is empty.

        """
        if self.filters:
            return False
        if self.queries:
            return False
        return True

    def _serialize(self):
        data = {}
        if self.boost != 1.0:
            data["boost"] = self.boost

        if self.filters:
            filters = {}
            if len(self.filters) == 1:
                filters.update(self.filters[0].serialize())
            else:
                filters.update(ANDFilter(self.filters).serialize())
            if not filters:
                raise QueryError("A filter is required")
            data['filter'] = filters
        else:
            queries = {}
            if len(self.queries) == 1:
                queries.update(self.queries[0].serialize())
            else:
                queries.update(BooleanQuery(must=self.queries).serialize())
            data['query'] = queries

        return data


class HasQuery(Query):

    def __init__(self, type, query, _scope=None, **kwargs):
        super(HasQuery, self).__init__(**kwargs)
        self.type = type
        self._scope = _scope
        self.query = query

    def _serialize(self):
        data = {'type': self.type, 'query': self.query.serialize()}
        if self._scope is not None:
            data['_scope'] = self._scope
        return data


class HasChildQuery(HasQuery):

    _internal_name = "has_child"


class HasParentQuery(HasQuery):

    _internal_name = "has_parent"


class TopChildrenQuery(ConstantScoreQuery):

    _internal_name = "top_children"

    def __init__(self, type, score="max", factor=5, incremental_factor=2, **kwargs):
        super(TopChildrenQuery, self).__init__(**kwargs)
        self.type = type
        self.score = score
        self.factor = factor
        self.incremental_factor = incremental_factor

    def _serialize(self):
        if self.score not in ["max", "min", "avg", "sum"]:
            raise InvalidParameterQuery("Invalid value '%s' for score" % self.score)

        filters = {}
        if self.boost != 1.0:
            filters["boost"] = self.boost
        for f in self.filters:
            filters.update(f.serialize())
        return {
            'type': self.type,
            'query': filters,
            'score': self.score,
            'factor': self.factor,
            'incremental_factor': self.incremental_factor,
        }


class NestedQuery(Query):
    """
    Nested query allows to query nested objects / docs (see nested mapping).
    The query is executed against the nested objects / docs as if they were
    indexed as separate docs (they are, internally) and resulting in the root
    parent doc (or parent nested mapping).

    The query path points to the nested object path, and the query (or filter)
    includes the query that will run on the nested docs matching the direct
    path, and joining with the root parent docs.

    The score_mode allows to set how inner children matching affects scoring of
    parent. It defaults to avg, but can be total, max and none.

    Multi level nesting is automatically supported, and detected, resulting in
    an inner nested query to automatically match the relevant nesting level
    (and not root) if it exists within another nested query.
    """

    _internal_name = "nested"

    def __init__(self, path, query, _scope=None, score_mode="avg", **kwargs):
        super(NestedQuery, self).__init__(**kwargs)
        self.path = path
        self.score_mode = score_mode
        self.query = query
        self._scope = _scope

    def _serialize(self):
        if self.score_mode and self.score_mode not in ['avg', "total", "max"]:
            raise InvalidParameterQuery("Invalid score_mode: %s" % self.score_mode)
        data = {
            'path': self.path,
            'score_mode': self.score_mode,
            'query': self.query.serialize()}
        if self._scope is not None:
            data['_scope'] = self._scope
        return data


class DisMaxQuery(Query):

    _internal_name = "dis_max"

    def __init__(self, query=None, tie_breaker=0.0, boost=1.0, queries=None, **kwargs):
        super(DisMaxQuery, self).__init__(**kwargs)
        self.queries = queries or []
        self.tie_breaker = tie_breaker
        self.boost = boost
        if query:
            self.add(query)

    def add(self, query):
        if isinstance(query, list):
            self.queries.extend(query)
        else:
            self.queries.append(query)
        return self

    def _serialize(self):
        filters = {}
        if self.tie_breaker != 0.0:
            filters["tie_breaker"] = self.tie_breaker
        if self.boost != 1.0:
            filters["boost"] = self.boost
        filters["queries"] = [q.serialize() for q in self.queries]
        if not filters["queries"]:
            raise InvalidQuery("A least a query is required")
        return filters

#Removed in ES 1.x
# class FieldQuery(Query):
#
#     _internal_name = "field"
#
#     def __init__(self, fieldparameters=None, default_operator="OR", analyzer=None,
#                  allow_leading_wildcard=True, lowercase_expanded_terms=True,
#                  enable_position_increments=True, fuzzy_prefix_length=0,
#                  fuzzy_min_sim=0.5, phrase_slop=0, boost=1.0, use_dis_max=True,
#                  tie_breaker=0, **kwargs):
#         super(FieldQuery, self).__init__(**kwargs)
#         self.field_parameters = []
#         self.default_operator = default_operator
#         self.analyzer = analyzer
#         self.allow_leading_wildcard = allow_leading_wildcard
#         self.lowercase_expanded_terms = lowercase_expanded_terms
#         self.enable_position_increments = enable_position_increments
#         self.fuzzy_prefix_length = fuzzy_prefix_length
#         self.fuzzy_min_sim = fuzzy_min_sim
#         self.phrase_slop = phrase_slop
#         self.boost = boost
#         self.use_dis_max = use_dis_max
#         self.tie_breaker = tie_breaker
#         if fieldparameters:
#             if isinstance(fieldparameters, list):
#                 self.field_parameters.extend(fieldparameters)
#             else:
#                 self.field_parameters.append(fieldparameters)
#
#     def add(self, field, query, **kwargs):
#         fp = FieldParameter(field, query, **kwargs)
#         self.field_parameters.append(fp)
#
#     def _serialize(self):
#         result = {}
#         for f in self.field_parameters:
#             val, filters = f.serialize()
#             result[val] = filters
#         return result


class FilteredQuery(Query):
    """
    FilteredQuery allows for results to be filtered using the various filter classes.

    Example:

    t = TermFilter('name', 'john')
    q = FilteredQuery(MatchAllQuery(), t)
    results = conn.search(q)
    """

    _internal_name = "filtered"

    def __init__(self, query, filter, **kwargs):
        super(FilteredQuery, self).__init__(**kwargs)
        self.query = query
        self.filter = filter

    def _serialize(self):
        return {
            'query': self.query.serialize(),
            'filter': self.filter.serialize(),
        }


class MoreLikeThisFieldQuery(Query):

    _internal_name = "more_like_this_field"

    def __init__(self, field, like_text, percent_terms_to_match=0.3,
                 min_term_freq=2, max_query_terms=25, stop_words=None,
                 min_doc_freq=5, max_doc_freq=None, min_word_len=0, max_word_len=0,
                 boost_terms=1, boost=1.0, **kwargs):
        super(MoreLikeThisFieldQuery, self).__init__(**kwargs)
        self.field = field
        self.like_text = like_text
        self.percent_terms_to_match = percent_terms_to_match
        self.min_term_freq = min_term_freq
        self.max_query_terms = max_query_terms
        self.stop_words = stop_words or []
        self.min_doc_freq = min_doc_freq
        self.max_doc_freq = max_doc_freq
        self.min_word_len = min_word_len
        self.max_word_len = max_word_len
        self.boost_terms = boost_terms
        self.boost = boost

    def _serialize(self):
        filters = {'like_text': self.like_text}
        if self.percent_terms_to_match != 0.3:
            filters["percent_terms_to_match"] = self.percent_terms_to_match
        if self.min_term_freq != 2:
            filters["min_term_freq"] = self.min_term_freq
        if self.max_query_terms != 25:
            filters["max_query_terms"] = self.max_query_terms
        if self.stop_words:
            filters["stop_words"] = self.stop_words
        if self.min_doc_freq != 5:
            filters["min_doc_freq"] = self.min_doc_freq
        if self.max_doc_freq:
            filters["max_doc_freq"] = self.max_doc_freq
        if self.min_word_len:
            filters["min_word_len"] = self.min_word_len
        if self.max_word_len:
            filters["max_word_len"] = self.max_word_len
        if self.boost_terms:
            filters["boost_terms"] = self.boost_terms
        if self.boost != 1.0:
            filters["boost"] = self.boost
        return {self.field: filters}


class FuzzyLikeThisQuery(Query):

    _internal_name = "fuzzy_like_this"

    def __init__(self, fields, like_text, ignore_tf=False, max_query_terms=25,
                 min_similarity=0.5, prefix_length=0, boost=1.0, **kwargs):
        super(FuzzyLikeThisQuery, self).__init__(**kwargs)
        self.fields = fields
        self.like_text = like_text
        self.ignore_tf = ignore_tf
        self.max_query_terms = max_query_terms
        self.min_similarity = min_similarity
        self.prefix_length = prefix_length
        self.boost = boost

    def _serialize(self):
        filters = {'fields': self.fields, 'like_text': self.like_text}
        if self.ignore_tf:
            filters["ignore_tf"] = self.ignore_tf
        if self.max_query_terms != 25:
            filters["max_query_terms"] = self.max_query_terms
        if self.min_similarity != 0.5:
            filters["min_similarity"] = self.min_similarity
        if self.prefix_length:
            filters["prefix_length"] = self.prefix_length
        if self.boost != 1.0:
            filters["boost"] = self.boost
        return filters


class FuzzyQuery(Query):
    """
    A fuzzy based query that uses similarity based on Levenshtein (edit distance) algorithm.

    Note
        Warning: this query is not very scalable with its default prefix
        length of 0 - in this case, every term will be enumerated and cause an
        edit score calculation. Here is a simple example:
    """

    _internal_name = "fuzzy"

    def __init__(self, field, value, boost=None, min_similarity=0.5,
                 prefix_length=0, **kwargs):
        super(FuzzyQuery, self).__init__(**kwargs)
        self.field = field
        self.value = value
        self.boost = boost
        self.min_similarity = min_similarity
        self.prefix_length = prefix_length

    def _serialize(self):
        data = {
            'value': self.value,
            'min_similarity': self.min_similarity,
            'prefix_length': self.prefix_length,
            }
        if self.boost:
            data['boost'] = self.boost
        return {self.field: data}


class FuzzyLikeThisFieldQuery(Query):

    _internal_name = "fuzzy_like_this_field"

    def __init__(self, field, like_text, ignore_tf=False, max_query_terms=25,
                 boost=1.0, min_similarity=0.5, **kwargs):
        super(FuzzyLikeThisFieldQuery, self).__init__(**kwargs)
        self.field = field
        self.like_text = like_text
        self.ignore_tf = ignore_tf
        self.max_query_terms = max_query_terms
        self.min_similarity = min_similarity
        self.boost = boost

    def _serialize(self):
        filters = {'like_text': self.like_text}
        if self.ignore_tf:
            filters["ignore_tf"] = self.ignore_tf
        if self.max_query_terms != 25:
            filters["max_query_terms"] = self.max_query_terms
        if self.boost != 1.0:
            filters["boost"] = self.boost
        if self.min_similarity != 0.5:
            filters["min_similarity"] = self.min_similarity
        return {self.field: filters}


class MatchAllQuery(Query):
    """
    Query used to match all

    Example:

    q = MatchAllQuery()
    results = conn.search(q)
    """

    _internal_name = "match_all"

    def __init__(self, boost=None, **kwargs):
        super(MatchAllQuery, self).__init__(**kwargs)
        self.boost = boost

    def _serialize(self):
        filters = {}
        if self.boost:
            if isinstance(self.boost, (float, int)):
                filters['boost'] = self.boost
            else:
                filters['boost'] = float(self.boost)
        return filters


class MoreLikeThisQuery(Query):

    _internal_name = "more_like_this"

    def __init__(self, fields, like_text, percent_terms_to_match=0.3,
                 min_term_freq=2, max_query_terms=25, stop_words=None,
                 min_doc_freq=5, max_doc_freq=None, min_word_len=0, max_word_len=0,
                 boost_terms=1, boost=1.0, **kwargs):
        super(MoreLikeThisQuery, self).__init__(**kwargs)
        self.fields = fields
        self.like_text = like_text
        self.stop_words = stop_words or []
        self.percent_terms_to_match = percent_terms_to_match
        self.min_term_freq = min_term_freq
        self.max_query_terms = max_query_terms
        self.min_doc_freq = min_doc_freq
        self.max_doc_freq = max_doc_freq
        self.min_word_len = min_word_len
        self.max_word_len = max_word_len
        self.boost_terms = boost_terms
        self.boost = boost

    def _serialize(self):
        filters = {'fields': self.fields, 'like_text': self.like_text}
        if self.percent_terms_to_match != 0.3:
            filters["percent_terms_to_match"] = self.percent_terms_to_match
        if self.min_term_freq != 2:
            filters["min_term_freq"] = self.min_term_freq
        if self.max_query_terms != 25:
            filters["max_query_terms"] = self.max_query_terms
        if self.stop_words:
            filters["stop_words"] = self.stop_words
        if self.min_doc_freq != 5:
            filters["min_doc_freq"] = self.min_doc_freq
        if self.max_doc_freq:
            filters["max_doc_freq"] = self.max_doc_freq
        if self.min_word_len:
            filters["min_word_len"] = self.min_word_len
        if self.max_word_len:
            filters["max_word_len"] = self.max_word_len
        if self.boost_terms:
            filters["boost_terms"] = self.boost_terms
        if self.boost != 1.0:
            filters["boost"] = self.boost
        return filters


class FilterQuery(Query):

    _internal_name = "query"

    def __init__(self, filters=None, **kwargs):
        super(FilterQuery, self).__init__(**kwargs)
        self._filters = []
        if filters is not None:
            self.add(filters)

    def add(self, filterquery):
        if isinstance(filterquery, list):
            self._filters.extend(filterquery)
        else:
            self._filters.append(filterquery)

    def _serialize(self):
        filters = [f.serialize() for f in self._filters]
        if not filters:
            raise RuntimeError("A least one filter must be declared")
        return {"filter": filters}


class PrefixQuery(Query):

    _internal_name = "prefix"

    def __init__(self, field=None, prefix=None, boost=None, **kwargs):
        super(PrefixQuery, self).__init__(**kwargs)
        self._values = {}
        if field is not None and prefix is not None:
            self.add(field, prefix, boost)

    def add(self, field, prefix, boost=None):
        match = {'prefix': prefix}
        if boost:
            if isinstance(boost, (float, int)):
                match['boost'] = boost
            else:
                match['boost'] = float(boost)
        self._values[field] = match

    def _serialize(self):
        if not self._values:
            raise RuntimeError("A least a field/prefix pair must be added")
        return self._values


class TermQuery(Query):
    """Match documents that have fields that contain a term (not analyzed).

    A boost may be supplied.

    Example:

    q = TermQuery('name', 'john')
    results = conn.search(q)

    With boost:

    q = TermQuery('name', 'john', boost=0.75)
    results = conn.search(q)
    """

    _internal_name = "term"

    def __init__(self, field=None, value=None, boost=None, **kwargs):
        super(TermQuery, self).__init__(**kwargs)
        self._values = {}
        if field is not None and value is not None:
            self.add(field, value, boost=boost)

    def add(self, field, value, boost=None):
        match = {'value': value}
        if boost:
            if isinstance(boost, (float, int)):
                match['boost'] = boost
            else:
                match['boost'] = float(boost)
            self._values[field] = match
        else:
            self._values[field] = value

    def _serialize(self):
        if not self._values:
            raise RuntimeError("A least a field/value pair must be added")
        return self._values


class TermsQuery(TermQuery):

    _internal_name = "terms"

    def __init__(self, *args, **kwargs):
        minimum_match = kwargs.pop('minimum_match', 1)

        super(TermsQuery, self).__init__(*args, **kwargs)

        if minimum_match is not None:
            self._values['minimum_match'] = int(minimum_match)

    def add(self, field, value, minimum_match=1, boost=None):
        if not isinstance(value, list):
            raise InvalidParameterQuery("value %r must be valid list" % value)
        self._values[field] = value
        if minimum_match:
            if isinstance(minimum_match, int):
                self._values['minimum_match'] = minimum_match
            else:
                self._values['minimum_match'] = int(minimum_match)


class TextQuery(Query):
    """
    A new family of text queries that accept text, analyzes it, and constructs a query out of it.

    Examples:

    q = TextQuery('book_title', 'elasticsearch')
    results = conn.search(q)

    q = TextQuery('book_title', 'elasticsearch python', operator='and')
    results = conn.search(q)
    """

    _internal_name = "text"
    _valid_types = ['boolean', "phrase", "phrase_prefix"]
    _valid_operators = ['or', "and"]

    def __init__(self, field, text, type="boolean", slop=0, fuzziness=None,
                 prefix_length=0, max_expansions=2147483647, operator="or",
                 analyzer=None, boost=1.0, minimum_should_match=None, cutoff_frequency=None, **kwargs):
        super(TextQuery, self).__init__(**kwargs)
        self.queries = {}
        self.add_query(field, text, type, slop, fuzziness,
                       prefix_length, max_expansions,
                       operator, analyzer, boost, minimum_should_match,
                       cutoff_frequency=cutoff_frequency)

    def add_query(self, field, text, type="boolean", slop=0, fuzziness=None,
                  prefix_length=0, max_expansions=2147483647,
                  operator="or", analyzer=None, boost=1.0, minimum_should_match=None,
                  cutoff_frequency=None):
        if type not in self._valid_types:
            raise QueryError("Invalid value '%s' for type: allowed values are %s" % (type, self._valid_types))
        if operator not in self._valid_operators:
            raise QueryError(
                "Invalid value '%s' for operator: allowed values are %s" % (operator, self._valid_operators))

        query = {'type': type, 'query': text}
        if slop:
            query["slop"] = slop
        if fuzziness is not None:
            query["fuzziness"] = fuzziness
        if prefix_length:
            query["prefix_length"] = prefix_length
        if max_expansions != 2147483647:
            query["max_expansions"] = max_expansions
        if operator:
            query["operator"] = operator
        if boost != 1.0:
            query["boost"] = boost
        if analyzer:
            query["analyzer"] = analyzer
        if cutoff_frequency is not None:
            query["cutoff_frequency"] = cutoff_frequency
        if minimum_should_match:
            query["minimum_should_match"] = minimum_should_match
        self.queries[field] = query

    def _serialize(self):
        return self.queries

class MatchQuery(TextQuery):
    """
    Replaces TextQuery
    """
    _internal_name = "match"

class MultiMatchQuery(Query):
    """
    A family of match queries that accept text/numerics/dates, analyzes it, and constructs a query out of it.
    Replaces TextQuery.

    Examples:

    q = MatchQuery('book_title', 'elasticsearch')
    results = conn.search(q)

    q = MatchQuery('book_title', 'elasticsearch python', type='phrase')
    results = conn.search(q)
    """
    _internal_name = "multi_match"
    _valid_types = ['boolean', "phrase", "phrase_prefix"]
    _valid_operators = ['or', "and"]

    def __init__(self, fields, text, type="boolean", slop=0, fuzziness=None,
                 prefix_length=0, max_expansions=2147483647, rewrite=None,
                 operator="or", analyzer=None, use_dis_max=True, minimum_should_match=None,
                 **kwargs):
        super(MultiMatchQuery, self).__init__(**kwargs)

        if type not in self._valid_types:
            raise QueryError("Invalid value '%s' for type: allowed values are %s" % (type, self._valid_types))
        if operator not in self._valid_operators:
            raise QueryError(
                "Invalid value '%s' for operator: allowed values are %s" % (operator, self._valid_operators))
        if not fields:
            raise QueryError("At least one field must be defined for multi_match")

        query = {'type': type, 'query': text, 'fields': fields, 'use_dis_max': use_dis_max}
        if slop:
            query["slop"] = slop
        if fuzziness is not None:
            query["fuzziness"] = fuzziness
        if prefix_length:
            query["prefix_length"] = prefix_length
        if max_expansions != 2147483647:
            query["max_expansions"] = max_expansions
        if operator:
            query["operator"] = operator
        if analyzer:
            query["analyzer"] = analyzer
        if rewrite:
            query["rewrite"] = rewrite
        if minimum_should_match:
            query['minimum_should_match'] = minimum_should_match
        self.query = query

    def _serialize(self):
        return self.query


class RegexTermQuery(TermQuery):

    _internal_name = "regex_term"


class QueryStringQuery(Query):
    """
    Query to match values on all fields for a given string

    Example:

    q = QueryStringQuery('elasticsearch')
    results = conn.search(q)
    """

    _internal_name = "query_string"

    def __init__(self, query, default_field=None, search_fields=None,
                 default_operator="OR", analyzer=None, allow_leading_wildcard=True,
                 lowercase_expanded_terms=True, enable_position_increments=True,
                 fuzzy_prefix_length=0, fuzzy_min_sim=0.5, phrase_slop=0,
                 boost=1.0, analyze_wildcard=False, use_dis_max=True,
                 tie_breaker=0, clean_text=False, minimum_should_match=None,
                 **kwargs):
        super(QueryStringQuery, self).__init__(**kwargs)
        self.clean_text = clean_text
        self.search_fields = search_fields or []
        self.query = query
        self.default_field = default_field
        self.default_operator = default_operator
        self.analyzer = analyzer
        self.allow_leading_wildcard = allow_leading_wildcard
        self.lowercase_expanded_terms = lowercase_expanded_terms
        self.enable_position_increments = enable_position_increments
        self.fuzzy_prefix_length = fuzzy_prefix_length
        self.fuzzy_min_sim = fuzzy_min_sim
        self.phrase_slop = phrase_slop
        self.boost = boost
        self.analyze_wildcard = analyze_wildcard
        self.use_dis_max = use_dis_max
        self.tie_breaker = tie_breaker
        self.minimum_should_match = minimum_should_match

    def _serialize(self):
        filters = {}
        if self.default_field:
            filters["default_field"] = self.default_field
            if not isinstance(self.default_field, six.string_types) and isinstance(self.default_field, list):
                if not self.use_dis_max:
                    filters["use_dis_max"] = self.use_dis_max
                if self.tie_breaker:
                    filters["tie_breaker"] = self.tie_breaker

        if self.default_operator != "OR":
            filters["default_operator"] = self.default_operator
        if self.analyzer:
            filters["analyzer"] = self.analyzer
        if not self.allow_leading_wildcard:
            filters["allow_leading_wildcard"] = self.allow_leading_wildcard
        if not self.lowercase_expanded_terms:
            filters["lowercase_expanded_terms"] = self.lowercase_expanded_terms
        if not self.enable_position_increments:
            filters["enable_position_increments"] = self.enable_position_increments
        if self.fuzzy_prefix_length:
            filters["fuzzy_prefix_length"] = self.fuzzy_prefix_length
        if self.fuzzy_min_sim != 0.5:
            filters["fuzzy_min_sim"] = self.fuzzy_min_sim
        if self.phrase_slop:
            filters["phrase_slop"] = self.phrase_slop
        if self.search_fields:
            if isinstance(self.search_fields, six.string_types):
                filters["fields"] = [self.search_fields]
            else:
                filters["fields"] = self.search_fields

            if len(filters["fields"]) > 1:
                if not self.use_dis_max:
                    filters["use_dis_max"] = self.use_dis_max
                if self.tie_breaker:
                    filters["tie_breaker"] = self.tie_breaker
        if self.boost != 1.0:
            filters["boost"] = self.boost
        if self.analyze_wildcard:
            filters["analyze_wildcard"] = self.analyze_wildcard
        if self.clean_text:
            query = clean_string(self.query)
            if not query:
                raise InvalidQuery("The query is empty")
            filters["query"] = query
        else:
            if not self.query.strip():
                raise InvalidQuery("The query is empty")
            filters["query"] = self.query
        if self.minimum_should_match:
          filters['minimum_should_match']=self.minimum_should_match
        return filters

class SimpleQueryStringQuery(Query):
    """
    A query that uses the SimpleQueryParser to parse its context. Unlike the regular query_string query,
    the simple_query_string query will never throw an exception, and discards invalid parts of the query.

    Example:

    q = SimpleQueryStringQuery('elasticsearch')
    results = conn.search(q)
    """

    _internal_name = "simple_query_string"

    def __init__(self, query, default_field=None, search_fields=None,
                 default_operator="OR", analyzer=None, allow_leading_wildcard=True,
                 lowercase_expanded_terms=True, enable_position_increments=True,
                 fuzzy_prefix_length=0, fuzzy_min_sim=0.5, phrase_slop=0,
                 boost=1.0, analyze_wildcard=False, use_dis_max=True,
                 tie_breaker=0, clean_text=False, minimum_should_match=None,
                 **kwargs):
        super(SimpleQueryStringQuery, self).__init__(**kwargs)
        self.clean_text = clean_text
        self.search_fields = search_fields or []
        self.query = query
        self.default_field = default_field
        self.default_operator = default_operator
        self.analyzer = analyzer
        self.allow_leading_wildcard = allow_leading_wildcard
        self.lowercase_expanded_terms = lowercase_expanded_terms
        self.enable_position_increments = enable_position_increments
        self.fuzzy_prefix_length = fuzzy_prefix_length
        self.fuzzy_min_sim = fuzzy_min_sim
        self.phrase_slop = phrase_slop
        self.boost = boost
        self.analyze_wildcard = analyze_wildcard
        self.use_dis_max = use_dis_max
        self.tie_breaker = tie_breaker
        self.minimum_should_match = minimum_should_match

    def _serialize(self):
        filters = {}
        if self.default_field:
            filters["default_field"] = self.default_field
            if not isinstance(self.default_field, six.string_types) and isinstance(self.default_field, list):
                if not self.use_dis_max:
                    filters["use_dis_max"] = self.use_dis_max
                if self.tie_breaker:
                    filters["tie_breaker"] = self.tie_breaker

        if self.default_operator != "OR":
            filters["default_operator"] = self.default_operator
        if self.analyzer:
            filters["analyzer"] = self.analyzer
        if not self.allow_leading_wildcard:
            filters["allow_leading_wildcard"] = self.allow_leading_wildcard
        if not self.lowercase_expanded_terms:
            filters["lowercase_expanded_terms"] = self.lowercase_expanded_terms
        if not self.enable_position_increments:
            filters["enable_position_increments"] = self.enable_position_increments
        if self.fuzzy_prefix_length:
            filters["fuzzy_prefix_length"] = self.fuzzy_prefix_length
        if self.fuzzy_min_sim != 0.5:
            filters["fuzzy_min_sim"] = self.fuzzy_min_sim
        if self.phrase_slop:
            filters["phrase_slop"] = self.phrase_slop
        if self.search_fields:
            if isinstance(self.search_fields, six.string_types):
                filters["fields"] = [self.search_fields]
            else:
                filters["fields"] = self.search_fields

            if len(filters["fields"]) > 1:
                if not self.use_dis_max:
                    filters["use_dis_max"] = self.use_dis_max
                if self.tie_breaker:
                    filters["tie_breaker"] = self.tie_breaker
        if self.boost != 1.0:
            filters["boost"] = self.boost
        if self.analyze_wildcard:
            filters["analyze_wildcard"] = self.analyze_wildcard
        if self.clean_text:
            query = clean_string(self.query)
            if not query:
                raise InvalidQuery("The query is empty")
            filters["query"] = query
        else:
            if not self.query.strip():
                raise InvalidQuery("The query is empty")
            filters["query"] = self.query
        if self.minimum_should_match:
          filters['minimum_should_match']=self.minimum_should_match
        return filters

class RangeQuery(Query):

    _internal_name = "range"

    def __init__(self, qrange=None, **kwargs):
        super(RangeQuery, self).__init__(**kwargs)
        self.ranges = []
        if qrange:
            self.add(qrange)

    def add(self, qrange):
        if isinstance(qrange, list):
            self.ranges.extend(qrange)
        elif isinstance(qrange, ESRange):
            self.ranges.append(qrange)

    def _serialize(self):
        if not self.ranges:
            raise RuntimeError("A least a range must be declared")
        return dict([r.serialize() for r in self.ranges])


class SpanFirstQuery(TermQuery):

    _internal_name = "span_first"

    def __init__(self, field=None, value=None, end=3, **kwargs):
        super(SpanFirstQuery, self).__init__(**kwargs)
        self._values = {}
        self.end = end
        if field is not None and value is not None:
            self.add(field, value)

    def _serialize(self):
        if not self._values:
            raise RuntimeError("A least a field/value pair must be added")
        return {"match": {"span_first": self._values}, "end": self.end}


class SpanMultiQuery(Query):
    """
    This query allows you to wrap multi term queries (fuzzy, prefix, wildcard, range).
    
    The query element is either of type WildcardQuery, FuzzyQuery, PrefixQuery or RangeQuery.
    A boost can also be associated with the element query
    """
    
    _internal_name = "span_multi"
    
    def __init__(self, query, **kwargs):
        super(SpanMultiQuery, self).__init__(**kwargs)
        self.query = query

    def _validate(self):
        if not isinstance(self.query, (WildcardQuery, FuzzyQuery, PrefixQuery, RangeQuery)):
            raise RuntimeError("Invalid query:%r" % self.query)

    def _serialize(self):
        self._validate()
        return {'match': self.query.serialize()}


class SpanNearQuery(Query):
    """
    Matches spans which are near one another. One can specify _slop_,
    the maximum number of intervening unmatched positions, as well as
    whether matches are required to be in-order.

    The clauses element is a list of one or more other span type queries and
    the slop controls the maximum number of intervening unmatched positions
    permitted.
    """

    _internal_name = "span_near"

    def __init__(self, clauses=None, slop=1, in_order=None,
                 collect_payloads=None, **kwargs):
        super(SpanNearQuery, self).__init__(**kwargs)
        self.clauses = clauses or []
        self.slop = slop
        self.in_order = in_order
        self.collect_payloads = collect_payloads

    def _validate(self):
        for clause in self.clauses:
            if not is_a_spanquery(clause):
                raise RuntimeError("Invalid clause:%r" % clause)

    def _serialize(self):
        if not self.clauses or len(self.clauses) == 0:
            raise RuntimeError("A least a Span*Query must be added to clauses")
        data = {"slop": self.slop}
        if self.in_order is not None:
            data["in_order"] = self.in_order
        if self.collect_payloads is not None:
            data["collect_payloads"] = self.collect_payloads
        data['clauses'] = [clause.serialize() for clause in self.clauses]
        return data


class SpanNotQuery(Query):
    """
    Removes matches which overlap with another span query.

    The include and exclude clauses can be any span type query. The include
    clause is the span query whose matches are filtered, and the exclude
    clause is the span query whose matches must not overlap those returned.
    """

    _internal_name = "span_not"

    def __init__(self, include, exclude, **kwargs):
        super(SpanNotQuery, self).__init__(**kwargs)
        self.include = include
        self.exclude = exclude

    def _validate(self):
        if not is_a_spanquery(self.include):
            raise RuntimeError("Invalid clause:%r" % self.include)
        if not is_a_spanquery(self.exclude):
            raise RuntimeError("Invalid clause:%r" % self.exclude)

    def _serialize(self):
        self._validate()
        return {'include': self.include.serialize(),
                'exclude': self.exclude.serialize()}


def is_a_spanquery(obj):
    """
    Returns if the object is a span query
    """
    return isinstance(obj, (SpanTermQuery, SpanFirstQuery, SpanOrQuery, SpanMultiQuery))


class SpanOrQuery(Query):
    """
    Matches the union of its span clauses.

    The clauses element is a list of one or more other span type queries.
    """

    _internal_name = "span_or"

    def __init__(self, clauses=None, **kwargs):
        super(SpanOrQuery, self).__init__(**kwargs)
        self.clauses = clauses or []

    def _validate(self):
        for clause in self.clauses:
            if not is_a_spanquery(clause):
                raise RuntimeError("Invalid clause:%r" % clause)

    def _serialize(self):
        if not self.clauses or len(self.clauses) == 0:
            raise RuntimeError("A least a Span*Query must be added to clauses")
        clauses = [clause.serialize() for clause in self.clauses]
        return {"clauses": clauses}


class SpanTermQuery(TermQuery):

    _internal_name = "span_term"


class WildcardQuery(TermQuery):

    _internal_name = "wildcard"


class CustomScoreQuery(Query):

    _internal_name = "custom_score"

    def __init__(self, query=None, script=None, params=None, lang=None, **kwargs):
        super(CustomScoreQuery, self).__init__(**kwargs)
        self.query = query
        self.script = script
        self.lang = lang
        self.params = params or {}

    def add_param(self, name, value):
        self.params[name] = value

    def _serialize(self):
        if not self.query:
            raise RuntimeError("A least a query must be declared")
        if not self.script:
            raise RuntimeError("A script must be provided")
        data = {}
        data['query'] = self.query.serialize()
        data['script'] = self.script
        if self.params:
            data['params'] = self.params
        if self.lang:
            data['lang'] = self.lang
        return data


class IdsQuery(Query):

    _internal_name = "ids"

    def __init__(self, values, type=None, **kwargs):
        super(IdsQuery, self).__init__(**kwargs)
        self.type = type
        self.values = values

    def _serialize(self):
        data = {}
        if self.type is not None:
            data['type'] = self.type
        if isinstance(self.values, list):
            data['values'] = self.values
        else:
            data['values'] = [self.values]
        return data


class PercolatorQuery(Query):
    """A percolator query is used to determine which registered
    PercolatorDoc's match the document supplied.
    """

    def __init__(self, doc, query=None, **kwargs):
        """Constructor

        doc - the doc to match against, dict
        query - an additional query that can be used to filter the percolated
        queries used to match against.
        """
        super(PercolatorQuery, self).__init__(**kwargs)
        self.doc = doc
        self.query = query

    def serialize(self):
        """Serialize the query to a structure using the query DSL."""
        data = {'doc': self.doc}
        if isinstance(self.query, Query):
            data['query'] = self.query.serialize()
        return data

    def search(self, **kwargs):
        """Disable this as it is not allowed in percolator queries."""
        raise NotImplementedError()

class RescoreQuery(Query):
    """
    A rescore query is used to rescore top results from another query.
    """

    _internal_name = "rescore_query"

    def __init__(self, query, window_size=None, query_weight=None, rescore_query_weight=None, **kwargs):
        """
        Constructor
        """
        super(RescoreQuery, self).__init__(**kwargs)
        self.query = query
        self.window_size = window_size
        self.query_weight = query_weight
        self.rescore_query_weight = rescore_query_weight

    def serialize(self):
        """Serialize the query to a structure using the query DSL."""

        data = {self._internal_name: self.query.serialize()}
        if self.query_weight:
            data['query_weight'] = self.query_weight
        if self.rescore_query_weight:
            data['rescore_query_weight'] = self.rescore_query_weight

        return data


# class CustomFiltersScoreQuery(Query):
#
#     _internal_name = "custom_filters_score"
#
#     class ScoreMode(object):
#         FIRST = "first"
#         MIN = "min"
#         MAX = "max"
#         TOTAL = "total"
#         AVG = "avg"
#         MULTIPLY = "multiply"
#
#     class Filter(EqualityComparableUsingAttributeDictionary):
#
#         def __init__(self, filter_, boost=None, script=None):
#             if (boost is None) == (script is None):
#                 raise ValueError("Exactly one of boost and script must be specified")
#             self.filter_ = filter_
#             self.boost = boost
#             self.script = script
#
#         def serialize(self):
#             data = {'filter': self.filter_.serialize()}
#             if self.boost is not None:
#                 data['boost'] = self.boost
#             if self.script is not None:
#                 data['script'] = self.script
#             return data
#
#     def __init__(self, query, filters, score_mode=None, params=None, lang=None,
#                  **kwargs):
#         super(CustomFiltersScoreQuery, self).__init__(**kwargs)
#         self.query = query
#         self.filters = filters
#         self.score_mode = score_mode
#         self.params = params
#         self.lang = lang
#
#     def _serialize(self):
#         data = {'query': self.query.serialize(),
#                 'filters': [filter_.serialize() for filter_ in self.filters]}
#         if self.score_mode is not None:
#             data['score_mode'] = self.score_mode
#         if self.params is not None:
#             data['params'] = self.params
#         if self.lang is not None:
#             data['lang'] = self.lang
#         return data
#
#
# class CustomBoostFactorQuery(Query):
#     _internal_name = "custom_boost_factor"
#
#     def __init__(self, query, boost_factor, **kwargs):
#         super(CustomBoostFactorQuery, self).__init__(**kwargs)
#         self.boost_factor = boost_factor
#         self.query = query
#
#     def _serialize(self):
#         data = {'query': self.query.serialize()}
#
#         if isinstance(self.boost_factor, (float, int)):
#             data['boost_factor'] = self.boost_factor
#         else:
#             data['boost_factor'] = float(self.boost_factor)
#
#         return data


class FunctionScoreQuery(Query):
    """The functoin_score query exists since 0.90.4.
    It replaces CustomScoreQuery and some other.
    """

    class FunctionScoreFunction(EqualityComparableUsingAttributeDictionary):

        def serialize(self):
            """Serialize the function to a structure using the query DSL."""
            return {self._internal_name: self._serialize()}

    class DecayFunction(FunctionScoreFunction):

        def __init__(self, decay_function, field, origin, scale,  decay=None, offset=None, filter=None):

            decay_functions = ["gauss", "exp", "linear"]
            if decay_function not in decay_functions:
                raise RuntimeError("The decay_function  %s is not allowed" % decay_function)

            self.__internal_name = decay_function
            self.decay_function = decay_function
            self.field = field
            self.origin = origin
            self.scale = scale
            self.decay = decay
            self.filter = filter
            self.offset = offset

        def _serialize(self):

            field_data = {'origin': self.origin, 'scale': self.scale}
            if self.decay:
                field_data['decay'] = self.decay

            if self.offset:
                field_data['offset'] = self.offset

            return {self.field: field_data }

    class BoostFunction(FunctionScoreFunction):
        """Boost by a factor"""
        _internal_name = 'boost_factor'

        def __init__(self, boost_factor, filter=None):
            self.boost_factor = boost_factor
            self.filter = filter

        def serialize(self):
            return {
                self._internal_name: self.boost_factor,
                'filter': self.filter.serialize()
            }

    class RandomFunction(FunctionScoreFunction):
        """Is a random boost based on a seed value"""
        _internal_name = 'random_Score'

        def __init__(self, seed, filter=None):
            self.seed = seed
            self.filter = filter

        def _serialize(self):
            data = {'seed': self.seed}
            if self.filter:
                data['filter'] = self.filter.serialize()
            return data


    class ScriptScoreFunction(FunctionScoreFunction):
        """Scripting function with params and a script.
        Also possible to switch the script language"""
        _internal_name = "script_score"

        def __init__(self, script=None, params=None, lang=None, filter=None):

            self.filter = filter
            self.params = params
            self.lang = lang
            self.script = script

        def _serialize(self):
            data = {}
            if self.filter:
                data['filter'] = self.filter.serialize()
            if self.params is not None:
                data['params'] = self.params
            if self.script is not None:
                data['script'] = self.script
            if self.lang is not None:
                data['lang'] = self.lang
            return data

    class ScoreModes(object):
        """Some helper object to show the possibility of
        score_mode"""
        MULTIPLY = "multiply"
        SUM = "sum"
        AVG = "avg"
        FIRST = "first"
        MAX = "max"
        MIN = "min"

    class BoostModes(object):
        """Some helper object to show the possibility of
        boost_mode"""
        MULTIPLY = "multiply"
        REPLACE = "replace"
        SUM = "sum"
        AVG = "avg"
        MAX = "max"
        MIN = "min"

    _internal_name = "function_score"

    def __init__(
            self, functions=None, query=None, filter=None, max_boost=None, boost=None,
            score_mode=None, boost_mode=None, params=None):

        if not functions:
            functions = list()

        if max_boost:
            self.max_boost = int(max_boost)

        self.score_mode = score_mode
        self.boost_mode = boost_mode
        self.params = params
        self.functions = functions
        self.filter = filter
        self.query = query

    def _serialize(self):

        data = {}
        if self.params:
            data['params'] = dict(self.params)
        if self.functions:
            data['functions'] = []
            for function in self.functions:
                data['functions'].append(function.serialize())

        if self.score_mode:
            data['score_mode'] = self.score_mode

        if self.boost_mode:
            data['boost_mode'] = self.boost_mode

        if self.query:
            data['query'] = self.query.serialize()

        if self.filter:
            data['filter'] = self.filter.serialize()

        return data

########NEW FILE########
__FILENAME__ = queryset
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
The main QuerySet implementation. This provides the public API for the ORM.

Taken from django one and from django-elasticsearch.
"""


import copy
import six

# The maximum number of items to display in a QuerySet.__repr__
from .es import ES
from .filters import ANDFilter, ORFilter, NotFilter, Filter, TermsFilter, TermFilter, RangeFilter, ExistsFilter
from .facets import Facet, TermFacet
from .aggs import Agg, TermsAgg
from .models import ElasticSearchModel
from .query import MatchAllQuery, BoolQuery, FilteredQuery, Search
from .utils import ESRange
from .utils.compat import integer_types
REPR_OUTPUT_SIZE = 20


def get_es_connection(es_url, es_kwargs):
    #import pdb;pdb.set_trace()
    if es_url:
        es_kwargs.update(server=es_url)
    return ES(**es_kwargs)


class ESModel(ElasticSearchModel):

    def __init__(self, index, type, es_url=None, es_kwargs={}):
        self._index = index
        self._type = type
        self.objects = QuerySet(self, es_url=es_url, es_kwargs=es_kwargs)
        setattr(self, "DoesNotExist", DoesNotExist)
        setattr(self, "MultipleObjectsReturned", MultipleObjectsReturned)


def generate_model(index, doc_type, es_url=None, es_kwargs={}):
    MyModel = type('MyModel', (ElasticSearchModel,), {})

    setattr(MyModel, "objects", QuerySet(MyModel, index=index, type=doc_type, es_url=es_url, es_kwargs=es_kwargs))
    setattr(MyModel, "DoesNotExist", DoesNotExist)
    setattr(MyModel, "MultipleObjectsReturned", MultipleObjectsReturned)
    return MyModel


class QuerySet(object):
    """
    Represents a lazy database lookup for a set of objects.
    """
    def __init__(self, model=None, using=None, index=None, type=None, es_url=None, es_kwargs={}):
        self.es_url = es_url
        self.es_kwargs = es_kwargs
        if model is None and index and type:
            model = ESModel(index, type, es_url=self.es_url, es_kwargs=self.es_kwargs)
        self.model = model

        # EmptyQuerySet instantiates QuerySet with model as None
        self._index = index
        if using:
            self._index = using
        self._type=type
        self._queries = []
        self._filters = []
        self._facets = []
        self._aggs = []
        self._ordering = []
        self._fields = [] #fields to load
        self._size=None
        self._start=0
        self._result_cache = None #hold the resultset

    def _clear_ordering(self):
        #reset ordering
        self._ordering=[]

    @property
    def index(self):
        if self._index:
            return self._index
        return self.model._index

    @property
    def type(self):
        if self._type:
            return self._type
        return self.model._type

    ########################
    # PYTHON MAGIC METHODS #
    ########################

    def __deepcopy__(self, memo):
        """
        Deep copy of a QuerySet doesn't populate the cache
        """
        obj = self.__class__()
        for k,v in self.__dict__.items():
            if k in ('_iter','_result_cache'):
                obj.__dict__[k] = None
            else:
                obj.__dict__[k] = copy.deepcopy(v, memo)
        return obj

    def __getstate__(self):
        """
        Allows the QuerySet to be pickled.
        """
        # Force the cache to be fully populated.
        len(self)

        obj_dict = self.__dict__.copy()
        obj_dict['_iter'] = None
        return obj_dict

    def __repr__(self):
        data = list(self[:REPR_OUTPUT_SIZE + 1])
        if len(data) > REPR_OUTPUT_SIZE:
            data[-1] = "...(remaining elements truncated)..."
        return repr(data)

    def _build_query(self):
        if not self._queries and not self._filters:
            return MatchAllQuery()
        query = MatchAllQuery()
        if self._queries:
            if len(self._queries)==1:
                query=self._queries[0]
            else:
                query=BoolQuery(must=self._queries)
        if not self._filters:
            return query
        if len(self._filters)==1:
            return FilteredQuery(query, self._filters[0])
        return FilteredQuery(query, ANDFilter(self._filters))

    def _build_search(self):
        query=Search(self._build_query())
        if self._ordering:
            query.sort=self._ordering
        if self._facets:
            for facet in self._facets:
                query.facet.add(facet)
        if self._aggs:
            for agg in self._aggs:
                query.agg.add(agg)
        if self._start is not None:
            query.start = self._start
        if self._size is not None:
            query.size = self._size
        return query

    def _do_query(self):
        return get_es_connection(self.es_url, self.es_kwargs).search(self._build_search(), indices=self.index, doc_types=self.type)


    def __len__(self):
        # Since __len__ is called quite frequently (for example, as part of
        # list(qs), we make some effort here to be as efficient as possible
        # whilst not messing up any existing iterators against the QuerySet.
        if self._result_cache is None:
            self._result_cache = self._do_query()

        return self._result_cache.total

    def __iter__(self):
        if self._result_cache is None:
            len(self)
        # Python's list iterator is better than our version when we're just
        # iterating over the cache.
        return iter(self._result_cache)

#    def _result_iter(self):
#        pos = 0
#        while 1:
#            upper = len(self._result_cache)
#            while pos < upper:
#                yield self._result_cache[pos]
#                pos = pos + 1
#            if not self._iter:
#                raise StopIteration
#            if len(self._result_cache) <= pos:
#                self._fill_cache()

    def __nonzero__(self):
        if self._result_cache is not None:
            len(self)
            return bool(self._result_cache.total!=0)
        try:
            next(iter(self))
        except StopIteration:
            return False
        return True

#    def __contains__(self, val):
#        # The 'in' operator works without this method, due to __iter__. This
#        # implementation exists only to shortcut the creation of Model
#        # instances, by bailing out early if we find a matching element.
#        pos = 0
#        if self._result_cache is not None:
#            if val in self._result_cache:
#                return True
#            elif self._iter is None:
#                # iterator is exhausted, so we have our answer
#                return False
#            # remember not to check these again:
#            pos = len(self._result_cache)
#        else:
#            # We need to start filling the result cache out. The following
#            # ensures that self._iter is not None and self._result_cache is not
#            # None
#            it = iter(self)
#
#        # Carry on, one result at a time.
#        while True:
#            if len(self._result_cache) <= pos:
#                self._fill_cache(num=1)
#            if self._iter is None:
#                # we ran out of items
#                return False
#            if self._result_cache[pos] == val:
#                return True
#            pos += 1

    def __getitem__(self, k):
        """
        Retrieves an item or slice from the set of results.
        """
        if not isinstance(k, (slice,) + integer_types):
            raise TypeError
        assert ((not isinstance(k, slice) and (k >= 0))
                or (isinstance(k, slice) and (k.start is None or k.start >= 0)
                    and (k.stop is None or k.stop >= 0))), \
                "Negative indexing is not supported."

        if self._result_cache is None:
            len(self)
        return self._result_cache.__getitem__(k)

    def __and__(self, other):
        combined = self._clone()
        if not other._filters:
            return combined
        if other._filters:
            combined._filters.extend(other._filters)
        return combined

    def __or__(self, other):
        combined = self._clone()
        if not other._filters:
            return other._clone()
        combined._filters = ORFilter([combined._filters, other._filters])
        return combined

    ####################################
    # METHODS THAT DO DATABASE QUERIES #
    ####################################

    def size(self, number):
        clone = self._clone()
        clone._size=number
        return clone

    def start(self, number):
        clone = self._clone()
        clone._start=number
        return clone

    def iterator(self):
        """
        An iterator over the results from applying this QuerySet to the
        database.
        """
        if not self._result_cache:
            len(self)
        for r in self._result_cache:
            yield r

    def aggregate(self, *args, **kwargs):
        """
        Returns a dictionary containing the calculations (aggregation)
        over the current queryset

        If args is present the expression is passed as a kwarg using
        the Aggregate object's default alias.
        """
        raise NotImplementedError()

    def count(self):
        """
        Performs a SELECT COUNT() and returns the number of records as an
        integer.

        If the QuerySet is already fully cached this simply returns the length
        of the cached results set to avoid multiple SELECT COUNT(*) calls.
        """
        return len(self)

    def get(self, *args, **kwargs):
        """
        Performs the query and returns a single object matching the given
        keyword arguments.
        """
        clone = self.filter(*args, **kwargs)
        num = len(clone)
        if num == 1:
            return clone._result_cache[0]
        if not num:
            raise self.model.DoesNotExist(
                "%s matching query does not exist. "
                "Lookup parameters were %s" %
                #(self.model._meta.object_name, kwargs))
                (self.model.__class__.__name__, kwargs))
        raise self.model.MultipleObjectsReturned(
            "get() returned more than one %s -- it returned %s! "
            "Lookup parameters were %s" %
            #(self.model._meta.object_name, num, kwargs))
            (self.model.__class__.__name__, num, kwargs))

    def create(self, **kwargs):
        """
        Creates a new object with the given kwargs, saving it to the database
        and returning the created object.
        """
        obj = self.model(**kwargs)
        obj.save(force_insert=True, using=self.index)
        return obj

    def bulk_create(self, objs, batch_size=None):
        """
        Inserts each of the instances into the database. This does *not* call
        save() on each of the instances, does not send any pre/post save
        signals, and does not set the primary key attribute if it is an
        autoincrement field.
        """
        # So this case is fun. When you bulk insert you don't get the primary
        # keys back (if it's an autoincrement), so you can't insert into the
        # child tables which references this. There are two workarounds, 1)
        # this could be implemented if you didn't have an autoincrement pk,
        # and 2) you could do it by doing O(n) normal inserts into the parent
        # tables to get the primary keys back, and then doing a single bulk
        # insert into the childmost table. Some databases might allow doing
        # this by using RETURNING clause for the insert query. We're punting
        # on these for now because they are relatively rare cases.
#        assert batch_size is None or batch_size > 0
#        if self.model._meta.parents:
#            raise ValueError("Can't bulk create an inherited model")
#        if not objs:
#            return objs
#        self._for_write = True
#        connection = connections[self.db]
#        fields = self.model._meta.local_fields
#        if not transaction.is_managed(using=self.db):
#            transaction.enter_transaction_management(using=self.db)
#            forced_managed = True
#        else:
#            forced_managed = False
#        try:
#            if (connection.features.can_combine_inserts_with_and_without_auto_increment_pk
#                and self.model._meta.has_auto_field):
#                self._batched_insert(objs, fields, batch_size)
#            else:
#                objs_with_pk, objs_without_pk = partition(lambda o: o.pk is None, objs)
#                if objs_with_pk:
#                    self._batched_insert(objs_with_pk, fields, batch_size)
#                if objs_without_pk:
#                    fields= [f for f in fields if not isinstance(f, AutoField)]
#                    self._batched_insert(objs_without_pk, fields, batch_size)
#            if forced_managed:
#                transaction.commit(using=self.db)
#            else:
#                transaction.commit_unless_managed(using=self.db)
#        finally:
#            if forced_managed:
#                transaction.leave_transaction_management(using=self.db)
#
#        return objs
        raise NotImplementedError()

    def get_or_create(self, **kwargs):
        """
        Looks up an object with the given kwargs, creating one if necessary.
        Returns a tuple of (object, created), where created is a boolean
        specifying whether an object was created.
        """
        assert kwargs, \
                'get_or_create() must be passed at least one keyword argument'
        defaults = kwargs.pop('defaults', {})
        lookup = kwargs.copy()
        #TODO: check fields
        try:
            return self.get(**lookup), False
        except self.model.DoesNotExist:
            params = dict([(k, v) for k, v in kwargs.items() if '__' not in k])
            params.update(defaults)
            obj = self.model(**params)
            meta = obj.get_meta()
            meta.connection = get_es_connection(self.es_url, self.es_kwargs)
            meta.index=self.index
            meta.type=self.type
            obj.save(force=True)
            return obj, True

    def latest(self, field_name=None):
        """
        Returns the latest object, according to the model's 'get_latest_by'
        option or optional given field_name.
        """
        latest_by = field_name or "_id"#self.model._meta.get_latest_by
        assert bool(latest_by), "latest() requires either a field_name parameter or 'get_latest_by' in the model"
        obj = self._clone()
        obj._size=1
        obj._clear_ordering()
        obj._ordering.append({ latest_by : "desc" })
        return obj.get()

    def in_bulk(self, id_list):
        """
        Returns a dictionary mapping each of the given IDs to the object with
        that ID.
        """
        if not id_list:
            return {}
        qs = self._clone()
        qs.add_filter(('pk__in', id_list))
        qs._clear_ordering(force_empty=True)
        return dict([(obj._get_pk_val(), obj) for obj in qs])

    def delete(self):
        """
        Deletes the records in the current QuerySet.
        """
        del_query = self._clone()

        # The delete is actually 2 queries - one to find related objects,
        # and one to delete. Make sure that the discovery of related
        # objects is performed on the same database as the deletion.
        del_query._clear_ordering()
        get_es_connection(self.es_url, self.es_kwargs).delete_by_query(self._build_query())
        # Clear the result cache, in case this QuerySet gets reused.
        self._result_cache = None

    def update(self, **kwargs):
        """
        Updates all elements in the current QuerySet, setting all the given
        fields to the appropriate values.
        """
        query = self._build_query()
        connection = get_es_connection(self.es_url, self.es_kwargs)
        results = connection.search(query, indices=self.index, doc_types=self.type,
                                             model=self.model, scan=True)
        for item in results:
            item.update(kwargs)
            item.save(bulk=True)
        connection.flush_bulk(True)
        # Clear the result cache, in case this QuerySet gets reused.
        self._result_cache = None


    def exists(self):
        if self._result_cache is None:
            len(self)
        return bool(self._result_cache.total!=0)

    ##################################################
    # PUBLIC METHODS THAT RETURN A QUERYSET SUBCLASS #
    ##################################################

    def values(self, *fields):
        search = self._build_search()
        search.facet.reset()
        search.agg.reset()
        search.fields=fields
        return get_es_connection(self.es_url, self.es_kwargs).search(search, indices=self.index, doc_types=self.type)

    def values_list(self, *fields, **kwargs):
        flat = kwargs.pop('flat', False)
        if kwargs:
            raise TypeError('Unexpected keyword arguments to values_list: %s'
                    % (kwargs.keys(),))
        if flat and len(fields) > 1:
            raise TypeError("'flat' is not valid when values_list is called with more than one field.")
        assert fields, "A least a field is required"
        search = self._build_search()
        search.facet.reset()
        search.agg.reset()
        search.fields=fields
        if flat:
            return get_es_connection(self.es_url, self.es_kwargs).search(search, indices=self.index, doc_types=self.type,
                                              model=lambda x,y: y.get("fields", {}).get(fields[0], None))

        return get_es_connection(self.es_url, self.es_kwargs).search(search, indices=self.index, doc_types=self.type)

    def dates(self, field_name, kind, order='ASC'):
        """
        Returns a list of datetime objects representing all available dates for
        the given field_name, scoped to 'kind'.
        """

        assert kind in ("month", "year", "day", "week", "hour", "minute"), \
                "'kind' must be one of 'year', 'month', 'day', 'week', 'hour' and 'minute'."
        assert order in ('ASC', 'DESC'), \
                "'order' must be either 'ASC' or 'DESC'."

        search= self._build_search()
        search.facet.reset()
        search.facet.add_date_facet(name=field_name.replace("__", "."),
                 field=field_name, interval=kind)
        search.agg.reset()
        search.agg.add_date_agg(name=field_name.replace("__", "."),
                 field=field_name, interval=kind)
        search.size=0
        resulset = get_es_connection(self.es_url, self.es_kwargs).search(search, indices=self.index, doc_types=self.type)
        resulset.fix_aggs()
        entries = []
        for val in resulset.aggs.get(field_name.replace("__", ".")).get("entries", []):
            if "time" in val:
                entries.append(val["time"])
        if order=="ASC":
            return sorted(entries)

        return sorted(entries, reverse=True)

    def none(self):
        """
        Returns an empty QuerySet.
        """
        #return self._clone(klass=EmptyQuerySet)
        raise NotImplementedError()

    ##################################################################
    # PUBLIC METHODS THAT ALTER ATTRIBUTES AND RETURN A NEW QUERYSET #
    ##################################################################

    def all(self):
        """
        Returns a new QuerySet that is a copy of the current one. This allows a
        QuerySet to proxy for a model manager in some cases.
        """
        return self._clone()

    def filter(self, *args, **kwargs):
        """
        Returns a new QuerySet instance with the args ANDed to the existing
        set.
        """
        return self._filter_or_exclude(False, *args, **kwargs)

    def exclude(self, *args, **kwargs):
        """
        Returns a new QuerySet instance with NOT (args) ANDed to the existing
        set.
        """
        return self._filter_or_exclude(True, *args, **kwargs)


    def _filter_or_exclude(self, negate, *args, **kwargs):
        clone = self._clone()
        filters = self._build_filter(*args, **kwargs)
        if negate:
            if len(filters)>1:
                filters=ANDFilter(filters)
            else:
                filters=filters[0]
            clone._filters.append(NotFilter(filters))
        else:
            clone._filters.extend(filters)
        return clone

    def _build_inner_filter(self, field, value):
        modifiers = ('in', 'gt', 'gte', 'lte', 'lt', 'in', 'ne', 'exists', 'exact')
        if field.endswith(tuple(['__{0}'.format(m) for m in modifiers])):
            field, modifier = field.rsplit("__", 1)
        else:
            modifier=""
        field=field.replace("__", ".")
        if not modifier or modifier == 'exact':
            if isinstance(value, list):
                return TermsFilter(field, value)
            return TermFilter(field, value)

        if modifier=="in":
            return TermsFilter(field, value)
        elif modifier == "gt":
            return RangeFilter(ESRange(field, from_value=value, include_lower=False))
        elif modifier == "gte":
            return RangeFilter(ESRange(field, from_value=value, include_lower=True))
        elif modifier == "lte":
            return RangeFilter(ESRange(field, to_value=value, include_upper=True))
        elif modifier == "lt":
            return RangeFilter(ESRange(field, to_value=value, include_upper=False))
        elif modifier == "in":
            return TermsFilter(field, values=value)
        elif modifier == "ne":
            return NotFilter(TermFilter(field, value))
        elif modifier=="exists":
            if isinstance(value, bool) and value:
                return ExistsFilter(field)
            return NotFilter(ExistsFilter(field))

        raise NotImplementedError()



    def _build_filter(self, *args, **kwargs):
        filters = []
        if args:
            for f in args:
                if isinstance(f, Filter):
                    filters.append(f)
                #elif isinstance(f, dict):
                    #TODO: dict parser
                else:
                    raise TypeError('Only Filter objects can be passed as argument')
        for field, value in kwargs.items():
            filters.append(self._build_inner_filter(field, value))
        return filters

    def complex_filter(self, filter_obj):
        """
        Returns a new QuerySet instance with filter_obj added to the filters.

        filter_obj can be a Q object (or anything with an add_to_query()
        method) or a dictionary of keyword lookup arguments.

        This exists to support framework features such as 'limit_choices_to',
        and usually it will be more natural to use other methods.
        """
        if isinstance(filter_obj, Filter):
            clone = self._clone()
            clone._filters.add(filter_obj)
            return clone
        return self._filter_or_exclude(None, **filter_obj)


    def facet(self, *args, **kwargs):
        return self.annotate(*args, **kwargs)

    def agg(self, *args, **kwargs):
        return self.annotate(*args, **kwargs)

    def annotate(self, *args, **kwargs):
        """
        Return a query set in which the returned objects have been annotated
        with data aggregated from related fields.
        """
        obj = self._clone()

        for arg in args:
            if isinstance(arg, Facet):
                obj._facets.append(arg)
            elif isinstance(arg, six.string_types):
                obj._facets.append(TermFacet(arg.replace("__", ".")))
            elif isinstance(arg, Agg):
                obj._aggs.append(arg)
            elif isinstance(arg, six.string_types):
                obj._facets.append(TermFacet(arg.replace("__", ".")))
            else:
                raise NotImplementedError("invalid type")


        # Add the aggregates/facet to the query
        for name, field in kwargs.items():
            obj._facets.append(TermFacet(field=field.replace("__", "."), name=name.replace("__", ".")))
            obj._aggs.append(TermsAgg(field=field.replace("__", "."), name=name.replace("__", ".")))
        return obj

    def order_by(self, *field_names):
        """
        Returns a new QuerySet instance with the ordering changed.
        """
        obj = self._clone()
        obj._clear_ordering()
        for field in field_names:
            if field.startswith("-"):
                obj._ordering.append({ field.lstrip("-").replace("__", ".") : "desc" })
            else:
                obj._ordering.append({ field : "asc" })
        return obj

    def distinct(self, *field_names):
        """
        Returns a new QuerySet instance that will select only distinct results.
        """
#        assert self.query.can_filter(), \
#                "Cannot create distinct fields once a slice has been taken."
#        obj = self._clone()
#        obj.query.add_distinct_fields(*field_names)
#        return obj
        raise NotImplementedError()


    def reverse(self):
        """
        Reverses the ordering of the QuerySet.
        """
        clone = self._clone()
        assert self._ordering, "You need to set an ordering for reverse"
        ordering = []
        for order in self._ordering:
            for k,v in order.items():
                if v=="asc":
                    ordering.append({k: "desc"})
                else:
                    ordering.append({k: "asc"})
        clone._ordering=ordering
        return clone

    def defer(self, *fields):
        """
        Defers the loading of data for certain fields until they are accessed.
        The set of fields to defer is added to any existing set of deferred
        fields. The only exception to this is if None is passed in as the only
        parameter, in which case all deferrals are removed (None acts as a
        reset option).
        """
        raise NotImplementedError()
#        clone = self._clone()
#        if fields == (None,):
#            clone.query.clear_deferred_loading()
#        else:
#            clone.query.add_deferred_loading(fields)
#        return clone

    def only(self, *fields):
        """
        Essentially, the opposite of defer. Only the fields passed into this
        method and that are not already specified as deferred are loaded
        immediately when the queryset is evaluated.
        """
        clone = self._clone()
        clone._fields=fields
        return clone

    def using(self, alias):
        """
        Selects which database this QuerySet should excecute its query against.
        """
        clone = self._clone()
        clone._index = alias
        return clone

    ###################################
    # PUBLIC INTROSPECTION ATTRIBUTES #
    ###################################

    def ordered(self):
        """
        Returns True if the QuerySet is ordered -- i.e. has an order_by()
        clause or a default ordering on the model.
        """
        return len(self._ordering)>0
    ordered = property(ordered)


    ###################
    # PUBLIC METHODS  #
    ###################

    @classmethod
    def from_qs(cls, qs, **kwargs):
        """
        Creates a new queryset using class `cls` using `qs'` data.

        :param qs: The query set to clone
        :keyword kwargs: The kwargs to pass to _clone method
        """
        assert issubclass(cls, QuerySet), "%s is not a QuerySet subclass" % cls
        assert isinstance(qs, QuerySet), "qs has to be an instance of queryset"
        return qs._clone(klass=cls, **kwargs)

    def evaluated(self):
        """
        Lets check if the queryset was already evaluated without accessing
        private methods / attributes
        """
        return not self._result_cache is None

    @property
    def facets(self):
        if len(self._facets)==0:
            return {}
        if self._result_cache is None:
            len(self)
        return self._result_cache.facets

    @property
    def aggs(self):
        if len(self._aggs)==0:
            return {}
        if self._result_cache is None:
            len(self)
        return self._result_cache.aggs

    ###################
    # PRIVATE METHODS #
    ###################

    def _clone(self, klass=None, setup=False, **kwargs):
        if klass is None:
            klass = self.__class__
        c = klass(model=self.model, using=self.index, index=self.index, type=self.type, es_url=self.es_url, es_kwargs=self.es_kwargs)
        #copy filters/queries/facet????
        c.__dict__.update(kwargs)
        c._queries=list(self._queries)
        c._filters=list(self._filters)
        c._facets=list(self._facets)
        c._aggs=list(self._aggs)
        c._fields=list(self._fields)
        c._ordering=list(self._ordering)
        c._size=self._size
        c._start=self._start
        return c


    # When used as part of a nested query, a queryset will never be an "always
    # empty" result.
    value_annotation = True

########NEW FILE########
__FILENAME__ = rivers
class River(object):
    def __init__(self, index_name=None, index_type=None, bulk_size=100, bulk_timeout=None):
        self.name = index_name
        self.index_name = index_name
        self.index_type = index_type
        self.bulk_size = bulk_size
        self.bulk_timeout = bulk_timeout

    def serialize(self):
        res = self._serialize()
        index = {}
        if self.name:
            index['name'] = self.name
        if self.index_name:
            index['index'] = self.index_name
        if self.index_type:
            index['type'] = self.index_type
        if self.bulk_size:
            index['bulk_size'] = self.bulk_size
        if self.bulk_timeout:
            index['bulk_timeout'] = self.bulk_timeout
        if index:
            res['index'] = index
        return res

    def __repr__(self):
        return str(self.serialize())

    def _serialize(self):
        raise NotImplementedError


class RabbitMQRiver(River):
    type = "rabbitmq"

    def __init__(self, host="localhost", port=5672, user="guest",
                 password="guest", vhost="/", queue="es", exchange="es",
                 routing_key="es", exchange_declare=True, exchange_type="direct",
                 exchange_durable=True, queue_declare=True, queue_durable=True,
                 queue_auto_delete=False, queue_bind=True, **kwargs):
        super(RabbitMQRiver, self).__init__(**kwargs)
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.vhost = vhost
        self.queue = queue
        self.exchange = exchange
        self.routing_key = routing_key
        self.exchange_declare = exchange_declare
        self.exchange_type = exchange_type
        self.exchange_durable = exchange_durable
        self.queue_declare = queue_declare
        self.queue_durable = queue_durable
        self.queue_auto_delete = queue_auto_delete
        self.queue_bind = queue_bind

    def _serialize(self):
        return {
            "type": self.type,
            self.type: {
                "host": self.host,
                "port": self.port,
                "user": self.user,
                "pass": self.password,
                "vhost": self.vhost,
                "queue": self.queue,
                "exchange": self.exchange,
                "routing_key": self.routing_key,
                "exchange_declare": self.exchange_declare,
                "exchange_type": self.exchange_type,
                "exchange_durable": self.exchange_durable,
                "queue_declare": self.queue_declare,
                "queue_durable": self.queue_durable,
                "queue_auto_delete": self.queue_auto_delete,
                "queue_bind": self.queue_bind
            }
        }


class TwitterRiver(River):
    type = "twitter"

    def __init__(self, user=None, password=None, **kwargs):
        self.user = user
        self.password = password
        self.consumer_key = kwargs.pop('consumer_key', None)
        self.consumer_secret = kwargs.pop('consumer_secret', None)
        self.access_token = kwargs.pop('access_token', None)
        self.access_token_secret = kwargs.pop('access_token_secret', None)
        # These filters may be lists or comma-separated strings of values
        self.tracks = kwargs.pop('tracks', None)
        self.follow = kwargs.pop('follow', None)
        self.locations = kwargs.pop('locations', None)
        super(TwitterRiver, self).__init__(**kwargs)

    def _serialize(self):
        result = {"type": self.type}
        if self.user and self.password:
            result[self.type] = {"user": self.user,
                                 "password": self.password}
        elif (self.consumer_key and self.consumer_secret and self.access_token
              and self.access_token_secret):
            result[self.type] = {"oauth": {
                "consumer_key": self.consumer_key,
                "consumer_secret": self.consumer_secret,
                "access_token": self.access_token,
                "access_token_secret": self.access_token_secret,
            }
            }
        else:
            raise ValueError("Twitter river requires authentication by username/password or OAuth")
        filter = {}
        if self.tracks:
            filter['tracks'] = self.tracks
        if self.follow:
            filter['follow'] = self.follow
        if self.locations:
            filter['locations'] = self.locations
        if filter:
            result[self.type]['filter'] = filter
        return result


class CouchDBRiver(River):
    type = "couchdb"

    def __init__(self, host="localhost", port=5984, db="mydb", filter=None,
                 filter_params=None, script=None, user=None, password=None,
                 **kwargs):
        super(CouchDBRiver, self).__init__(**kwargs)
        self.host = host
        self.port = port
        self.db = db
        self.filter = filter
        self.filter_params = filter_params
        self.script = script
        self.user = user
        self.password = password

    def serialize(self):
        result = {
            "type": self.type,
            self.type: {
                "host": self.host,
                "port": self.port,
                "db": self.db,
                "filter": self.filter,
            }
        }
        if self.filter_params is not None:
            result[self.type]["filter_params"] = self.filter_params
        if self.script is not None:
            result[self.type]["script"] = self.script
        if self.user is not None:
            result[self.type]["user"] = self.user
        if self.password is not None:
            result[self.type]["password"] = self.password
        return result


class JDBCRiver(River):
    type = "jdbc"

    def __init__(self, dbhost="localhost", dbport=5432, dbtype="postgresql",
                 dbname=None, dbuser=None, dbpassword=None, poll_time="5s",
                 sql="", name=None, params=None, **kwargs):
        super(JDBCRiver, self).__init__(**kwargs)
        self.dbsettings = {
            'dbhost': dbhost,
            'dbport': dbport,
            'dbtype': dbtype,
            'dbname': dbname,
            'dbuser': dbuser,
            'dbpassword': dbpassword,
        }
        self.poll_time = poll_time
        self.sql = sql
        self.params = params or {}
        if name is not None:
            self.name = name

    def _serialize(self):
        ret = {
            "type": self.type,
            self.type: {
                "driver": "org.%(dbtype)s.Driver" % self.dbsettings,
                "url": "jdbc:%(dbtype)s://%(dbhost)s:%(dbport)s/%(dbname)s" \
                       % self.dbsettings,
                "user": "%(dbuser)s" % self.dbsettings,
                "password": "%(dbpassword)s" % self.dbsettings,
                "strategy": "simple",
                "poll": self.poll_time,
                "sql": self.sql.replace('\n', ' '),
            }
        }

        ret.update(self.params)

        return ret


class MongoDBRiver(River):
    type = "mongodb"

    def __init__(self, servers, db, collection, index_name, mapping_type, gridfs=False, options=None, bulk_size=1000,
                 filter=None, **kwargs):
        super(MongoDBRiver, self).__init__(**kwargs)
        self.name = index_name
        self.index_type = mapping_type
        self.bulk_size = bulk_size
        self.mongodb = {
            "servers": servers,
            "db": db,
            "collection": collection,
            "options": options or {},
            "gridfs": gridfs,
            "filter": filter
        }

    def serialize(self):
        result = {
            'type': self.type,
            'mongodb': self.mongodb
        }
        return result
########NEW FILE########
__FILENAME__ = scriptfields
# -*- coding: utf-8 -*-
from __future__ import absolute_import

from .exceptions import ScriptFieldsError


class ScriptField(object):
    def __init__(self, script, lang="mvel", params=None):
        self.script = script
        self.lang = lang
        self.params = params


class ScriptFields(object):
    """
    This object create the script_fields definition
    """
    _internal_name = "script_fields"

    def __init__(self, name=None, script=None, lang=None, params=None):
        self.fields = {}
        if name:
            self.add_field(name, script, lang, params or {})

    def add_field(self, name, script, lang=None, params=None):
        """
        Add a field to script_fields
        """
        data = {}
        if lang:
            data["lang"] = lang

        if script:
            data['script'] = script
        else:
            raise ScriptFieldsError("Script is required for script_fields definition")
        if params:
            if isinstance(params, dict):
                if len(params):
                    data['params'] = params
            else:
                raise ScriptFieldsError("Parameters should be a valid dictionary")

        self.fields[name] = data

    def add_parameter(self, field_name, param_name, param_value):
        """
        Add a parameter to a field into script_fields

        The ScriptFields object will be returned, so calls to this can be chained.
        """
        try:
            self.fields[field_name]['params'][param_name] = param_value
        except Exception as ex:
            raise ScriptFieldsError("Error adding parameter %s with value %s :%s" % (param_name, param_value, ex))

        return self

    def serialize(self):
        return self.fields

########NEW FILE########
__FILENAME__ = sort
# -*- coding: utf-8 -*-
from .exceptions import InvalidSortOrder
from .utils import EqualityComparableUsingAttributeDictionary


class SortOrder(EqualityComparableUsingAttributeDictionary):
    """
    Defines sort order
    """
    MODE_MIN = 'min'
    MODE_MAX = 'max'
    MODE_SUM = 'sum'  # not available for geo sorting
    MODE_AVG = 'avg'
    MODES = (MODE_MIN, MODE_MAX, MODE_SUM, MODE_AVG)

    def __init__(self, field=None, order=None, mode=None, nested_path=None,
                 nested_filter=None, missing=None, ignore_unmapped=None):
        self.field = field
        self.mode = mode
        self.order = order
        self.nested_path = nested_path
        self.nested_filter = nested_filter
        self.missing = missing
        self.ignore_unmapped = ignore_unmapped

    def serialize_order_params(self):
        res = {}
        if self.order:
            res['order'] = self.order
        if self.mode:
            res['mode'] = self.mode
        if self.nested_path:
            res['nested_path'] = self.nested_path
        if self.nested_filter:
            res['nested_filter'] = self.nested_filter.serialize()
        if self.missing:
            res['missing'] = self.missing
        if self.ignore_unmapped is not None:
            res['ignore_unmapped'] = self.ignore_unmapped

        return res

    def serialize(self):
        """Serialize the search to a structure as passed for a search body."""
        if not self.field:
            raise InvalidSortOrder('sort order must contain field name')

        return {self.field: self.serialize_order_params()}

    def __repr__(self):
        return str(self.serialize())


class GeoSortOrder(SortOrder):

    def __init__(self, lat=None, lon=None, geohash=None, unit=None,
                 **kwargs):
            super(GeoSortOrder, self).__init__(**kwargs)
            self.lat = lat
            self.lon = lon
            self.geohash = geohash
            self.unit = unit

    def serialize_order_params(self):
        res = super(GeoSortOrder, self).serialize_order_params()
        if self.geohash:
            res[self.field] = self.geohash
        elif self.lat is not None and self.lon is not None:
            res[self.field] = [self.lat, self.lon]
        else:
            raise InvalidSortOrder('Either geohash or lat and lon must be set')
        if self.unit:
            res['unit'] = self.unit

        return res

    def serialize(self):
        res = {
            '_geo_distance': self.serialize_order_params()
        }

        return res


class ScriptSortOrder(SortOrder):

    def __init__(self, script, type=None, params=None, **kwargs):
        super(ScriptSortOrder, self).__init__(**kwargs)
        self.script = script
        self.type = type
        self.params = params

    def serialize(self):
        res = {
            'script': self.script
        }
        if self.type:
            res['type'] = self.type
        if self.params:
            res['params'] = self.params
        if self.order:
            res['order'] = self.order

        res = {'_script': res}
        return res


class SortFactory(EqualityComparableUsingAttributeDictionary):
    """
    Container for SortOrder objects
    """

    def __init__(self):
        self.sort_orders = []

    def __bool__(self):
            return bool(self.sort_orders)

    def serialize(self):
        """Serialize the search to a structure as passed for a search body."""
        res = []
        for _sort in self.sort_orders:
            res.append(_sort.serialize())
        return res or None

    def __repr__(self):
        return str(self.serialize())

    def add(self, sort_order):
        """Add sort order"""
        self.sort_orders.append(sort_order)

    def reset(self):
        """Reset sort orders"""
        self.sort_orders = []

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import logging
import unittest
from pprint import pprint
from pyes.es import ES
from pyes.helpers import SettingsBuilder

"""
Unit tests for pyes.  These require an es server with thrift plugin running on the default port (localhost:9500).
"""

def get_conn(*args, **kwargs):
    return ES(("http", "127.0.0.1", 9200), *args, **kwargs)


class ESTestCase(unittest.TestCase):
    def setUp(self):
        self.log = open("/tmp/%s.sh"%self._testMethodName, "wb")
        self.conn = get_conn(timeout=300.0, log_curl=True, dump_curl=self.log)#incremented timeout for debugging
        self.index_name = "test-index"
        self.document_type = "test-type"
        self.conn.indices.delete_index_if_exists(self.index_name)

    def tearDown(self):
        self.conn.indices.delete_index_if_exists(self.index_name)
        if self.log:
            self.log.close()

    def assertResultContains(self, result, expected):
        for (key, value) in expected.items():
            found = False
            try:
                found = value == result[key]
            except KeyError:
                if result.has_key('meta'):
                    found = value == result['meta'][key]
            self.assertEqual(True, found)

    def checkRaises(self, excClass, callableObj, *args, **kwargs):
        """Assert that calling callableObj with *args and **kwargs raises an
        exception of type excClass, and return the exception object so that
        further tests on it can be performed.
        """
        try:
            callableObj(*args, **kwargs)
        except excClass as e:
            return e
        else:
            raise self.failureException("Expected exception %s not raised" % excClass)

    def get_datafile(self, filename):
        """
        Returns a the content of a test file
        """
        return open(os.path.join(os.path.dirname(__file__), "data", filename), "rb").read()

    def get_datafile_path(self, filename):
        """
        Returns a the content of a test file
        """
        return os.path.join(os.path.dirname(__file__), "data", filename)

    def dump(self, result):
        """
        dump to stdout the result
        """
        pprint(result)

    def init_default_index(self):
        settings = SettingsBuilder({'index.number_of_replicas': 0,
                                     "index.number_of_shards": 1})
        from pyes.mappings import DocumentObjectField
        from pyes.mappings import IntegerField
        from pyes.mappings import NestedObject
        from pyes.mappings import StringField, DateField

        docmapping = DocumentObjectField(name=self.document_type)
        docmapping.add_property(
            StringField(name="parsedtext", store=True, term_vector="with_positions_offsets", index="analyzed"))
        docmapping.add_property(
            StringField(name="name", store=True, term_vector="with_positions_offsets", index="analyzed"))
        docmapping.add_property(
            StringField(name="title", store=True, term_vector="with_positions_offsets", index="analyzed"))
        docmapping.add_property(IntegerField(name="position", store=True))
        docmapping.add_property(DateField(name="date", store=True))
        docmapping.add_property(StringField(name="uuid", store=True, index="not_analyzed"))
        nested_object = NestedObject(name="nested")
        nested_object.add_property(StringField(name="name", store=True))
        nested_object.add_property(StringField(name="value", store=True))
        nested_object.add_property(IntegerField(name="num", store=True))
        docmapping.add_property(nested_object)
        settings.add_mapping(docmapping)

        self.conn.ensure_index(self.index_name, settings)


def setUp():
    """Package level setup.

    For tests which don't modify the index, we don't want to have the overhead
    of setting up a test index, so we just set up test-pindex once, and use it
    for all tests.

    """
    mapping = {
        u'parsedtext': {
            'boost': 1.0,
            'index': 'analyzed',
            'store': 'yes',
            'type': u'string',
            "term_vector": "with_positions_offsets"},
        u'name': {
            'boost': 1.0,
            'index': 'analyzed',
            'store': 'yes',
            'type': u'string',
            "term_vector": "with_positions_offsets"},
        u'title': {
            'boost': 1.0,
            'index': 'analyzed',
            'store': 'yes',
            'type': u'string',
            "term_vector": "with_positions_offsets"},
        u'pos': {
            'store': 'yes',
            'type': u'integer'},
        u'doubles': {
            'store': 'yes',
            'type': u'double'},
        u'uuid': {
            'boost': 1.0,
            'index': 'not_analyzed',
            'store': 'yes',
            'type': u'string'}}

    conn = get_conn(log_curl=True)
    conn.indices.delete_index_if_exists("test-pindex")
    conn.indices.create_index("test-pindex")
    conn.indices.put_mapping("test-type", {'properties': mapping}, ["test-pindex"])
    conn.index({"name": "Joe Tester", "parsedtext": "Joe Testere nice guy", "uuid": "11111", "position": 1,
                "doubles": [1.0, 2.0, 3.0]}, "test-pindex", "test-type", 1)
    conn.index({"name": "Bill Baloney", "parsedtext": "Joe Testere nice guy", "uuid": "22222", "position": 2,
                "doubles": [0.1, 0.2, 0.3]}, "test-pindex", "test-type", 2)
    conn.indices.refresh(["test-pindex"])


def tearDown():
    """Remove the package level index.

    """
    conn = get_conn()
    conn.indices.delete_index_if_exists("test-pindex")

########NEW FILE########
__FILENAME__ = compat
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    pyes.utils.compat
    ~~~~~~~~~~~~~~~~~

    Taken from celery.utils.compat
    Backward compatible implementations of features
    only available in newer Python versions.

    :copyright: (c) 2009 - 2012 by Ask Solem.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import absolute_import

############## py3k #########################################################
import sys, types
is_py3k = sys.version_info[0] == 3

try:
    reload = reload                         # noqa
except NameError:                           # pragma: no cover
    from imp import reload                  # noqa

try:
    from UserList import UserList           # noqa
except ImportError:                         # pragma: no cover
    from collections import UserList        # noqa

try:
    from UserDict import UserDict           # noqa
except ImportError:                         # pragma: no cover
    from collections import UserDict        # noqa

if is_py3k:                                 # pragma: no cover
    from io import StringIO, BytesIO
    from .encoding import bytes_to_str

    class WhateverIO(StringIO):

        def write(self, data):
            StringIO.write(self, bytes_to_str(data))
else:
    from StringIO import StringIO           # noqa
    BytesIO = WhateverIO = StringIO         # noqa

if is_py3k:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes
else:
    string_types = basestring,
    integer_types = int, long
    class_types = type, types.ClassType
    text_type = unicode
    binary_type = str

############## itertools.zip_longest #######################################

try:
    from itertools import izip_longest as zip_longest
except ImportError:                         # pragma: no cover
    import itertools

    def zip_longest(*args, **kwds):  # noqa
        fillvalue = kwds.get("fillvalue")

        def sentinel(counter=([fillvalue] * (len(args) - 1)).pop):
            yield counter()     # yields the fillvalue, or raises IndexError

        fillers = itertools.repeat(fillvalue)
        iters = [itertools.chain(it, sentinel(), fillers)
                    for it in args]
        try:
            for tup in itertools.izip(*iters):
                yield tup
        except IndexError:
            pass


############## itertools.chain.from_iterable ################################
from itertools import chain


def _compat_chain_from_iterable(iterables):  # pragma: no cover
    for it in iterables:
        for element in it:
            yield element

try:
    chain_from_iterable = getattr(chain, "from_iterable")
except AttributeError:   # pragma: no cover
    chain_from_iterable = _compat_chain_from_iterable


############## logging.handlers.WatchedFileHandler ##########################
import logging
import os
from stat import ST_DEV, ST_INO
import platform as _platform

if _platform.system() == "Windows":  # pragma: no cover
    #since windows doesn't go with WatchedFileHandler use FileHandler instead
    WatchedFileHandler = logging.FileHandler
else:
    try:
        from logging.handlers import WatchedFileHandler
    except ImportError:  # pragma: no cover
        class WatchedFileHandler(logging.FileHandler):  # noqa
            """
            A handler for logging to a file, which watches the file
            to see if it has changed while in use. This can happen because of
            usage of programs such as newsyslog and logrotate which perform
            log file rotation. This handler, intended for use under Unix,
            watches the file to see if it has changed since the last emit.
            (A file has changed if its device or inode have changed.)
            If it has changed, the old file stream is closed, and the file
            opened to get a new stream.

            This handler is not appropriate for use under Windows, because
            under Windows open files cannot be moved or renamed - logging
            opens the files with exclusive locks - and so there is no need
            for such a handler. Furthermore, ST_INO is not supported under
            Windows; stat always returns zero for this value.

            This handler is based on a suggestion and patch by Chad J.
            Schroeder.
            """
            def __init__(self, *args, **kwargs):
                logging.FileHandler.__init__(self, *args, **kwargs)

                if not os.path.exists(self.baseFilename):
                    self.dev, self.ino = -1, -1
                else:
                    stat = os.stat(self.baseFilename)
                    self.dev, self.ino = stat[ST_DEV], stat[ST_INO]

            def emit(self, record):
                """
                Emit a record.

                First check if the underlying file has changed, and if it
                has, close the old stream and reopen the file to get the
                current stream.
                """
                if not os.path.exists(self.baseFilename):
                    stat = None
                    changed = 1
                else:
                    stat = os.stat(self.baseFilename)
                    changed = ((stat[ST_DEV] != self.dev) or
                               (stat[ST_INO] != self.ino))
                if changed and self.stream is not None:
                    self.stream.flush()
                    self.stream.close()
                    self.stream = self._open()
                    if stat is None:
                        stat = os.stat(self.baseFilename)
                    self.dev, self.ino = stat[ST_DEV], stat[ST_INO]
                logging.FileHandler.emit(self, record)


############## format(int, ',d') ##########################

if sys.version_info >= (2, 7):
    def format_d(i):
        return format(i, ',d')
else:
    def format_d(i):  # noqa
        s = '%d' % i
        groups = []
        while s and s[-1].isdigit():
            groups.append(s[-3:])
            s = s[:-3]
        return s + ','.join(reversed(groups))

########NEW FILE########
__FILENAME__ = encoding
# -*- coding: utf-8 -*-
"""
File taken from:
kombu.utils.encoding
~~~~~~~~~~~~~~~~~~~~~

Utilities to encode text, and to safely emit text from running
applications without crashing with the infamous :exc:`UnicodeDecodeError`
exception.

"""
from __future__ import absolute_import

import sys
import traceback

from .five import text_t

is_py3k = sys.version_info >= (3, 0)

#: safe_str takes encoding from this file by default.
#: :func:`set_default_encoding_file` can used to set the
#: default output file.
default_encoding_file = None


def set_default_encoding_file(file):
    global default_encoding_file
    default_encoding_file = file


def get_default_encoding_file():
    return default_encoding_file


if sys.platform.startswith('java'):     # pragma: no cover

    def default_encoding(file=None):
        return 'utf-8'
else:

    def default_encoding(file=None):  # noqa
        file = file or get_default_encoding_file()
        return getattr(file, 'encoding', None) or sys.getfilesystemencoding()

if is_py3k:  # pragma: no cover

    def str_to_bytes(s):
        if isinstance(s, str):
            return s.encode()
        return s

    def bytes_to_str(s):
        if isinstance(s, bytes):
            return s.decode()
        return s

    def from_utf8(s, *args, **kwargs):
        return s

    def ensure_bytes(s):
        if not isinstance(s, bytes):
            return str_to_bytes(s)
        return s

    def default_encode(obj):
        return obj

    str_t = str

else:

    def str_to_bytes(s):                # noqa
        if isinstance(s, unicode):
            return s.encode()
        return s

    def bytes_to_str(s):                # noqa
        return s

    def from_utf8(s, *args, **kwargs):  # noqa
        return s.encode('utf-8', *args, **kwargs)

    def default_encode(obj, file=None):            # noqa
        return unicode(obj, default_encoding(file))

    str_t = unicode
    ensure_bytes = str_to_bytes


try:
    bytes_t = bytes
except NameError:  # pragma: no cover
    bytes_t = str  # noqa


def safe_str(s, errors='replace'):
    s = bytes_to_str(s)
    if not isinstance(s, (text_t, bytes)):
        return safe_repr(s, errors)
    return _safe_str(s, errors)


if is_py3k:

    def _safe_str(s, errors='replace', file=None):
        if isinstance(s, str):
            return s
        try:
            return str(s)
        except Exception as exc:
            return '<Unrepresentable {0!r}: {1!r} {2!r}>'.format(
                type(s), exc, '\n'.join(traceback.format_stack()))
else:
    def _safe_str(s, errors='replace', file=None):  # noqa
        encoding = default_encoding(file)
        try:
            if isinstance(s, unicode):
                return s.encode(encoding, errors)
            return unicode(s, encoding, errors)
        except Exception as exc:
            return '<Unrepresentable {0!r}: {1!r} {2!r}>'.format(
                type(s), exc, '\n'.join(traceback.format_stack()))


def safe_repr(o, errors='replace'):
    try:
        return repr(o)
    except Exception:
        return _safe_str(o, errors)

########NEW FILE########
__FILENAME__ = five
# -*- coding: utf-8 -*-
"""
    celery.five
    ~~~~~~~~~~~

    Compatibility implementations of features
    only available in newer Python versions.


"""
from __future__ import absolute_import

############## py3k #########################################################
import sys
PY3 = sys.version_info[0] == 3

try:
    reload = reload                         # noqa
except NameError:                           # pragma: no cover
    from imp import reload                  # noqa

try:
    from collections import UserList        # noqa
except ImportError:                         # pragma: no cover
    from UserList import UserList           # noqa

try:
    from collections import UserDict        # noqa
except ImportError:                         # pragma: no cover
    from UserDict import UserDict           # noqa

try:
    bytes_t = bytes
except NameError:  # pragma: no cover
    bytes_t = str  # noqa

############## time.monotonic ################################################

if sys.version_info < (3, 3):

    import platform
    SYSTEM = platform.system()

    if SYSTEM == 'Darwin':
        import ctypes
        from ctypes.util import find_library
        libSystem = ctypes.CDLL('libSystem.dylib')
        CoreServices = ctypes.CDLL(find_library('CoreServices'),
                                   use_errno=True)
        mach_absolute_time = libSystem.mach_absolute_time
        mach_absolute_time.restype = ctypes.c_uint64
        absolute_to_nanoseconds = CoreServices.AbsoluteToNanoseconds
        absolute_to_nanoseconds.restype = ctypes.c_uint64
        absolute_to_nanoseconds.argtypes = [ctypes.c_uint64]

        def _monotonic():
            return absolute_to_nanoseconds(mach_absolute_time()) * 1e-9

    elif SYSTEM == 'Linux':
        # from stackoverflow:
        # questions/1205722/how-do-i-get-monotonic-time-durations-in-python
        import ctypes
        import os

        CLOCK_MONOTONIC = 1  # see <linux/time.h>

        class timespec(ctypes.Structure):
            _fields_ = [
                ('tv_sec', ctypes.c_long),
                ('tv_nsec', ctypes.c_long),
            ]

        librt = ctypes.CDLL('librt.so.1', use_errno=True)
        clock_gettime = librt.clock_gettime
        clock_gettime.argtypes = [
            ctypes.c_int, ctypes.POINTER(timespec),
        ]

        def _monotonic():  # noqa
            t = timespec()
            if clock_gettime(CLOCK_MONOTONIC, ctypes.pointer(t)) != 0:
                errno_ = ctypes.get_errno()
                raise OSError(errno_, os.strerror(errno_))
            return t.tv_sec + t.tv_nsec * 1e-9
    else:
        from time import time as _monotonic
try:
    from time import monotonic
except ImportError:
    monotonic = _monotonic  # noqa

############## Py3 <-> Py2 ###################################################

if PY3:  # pragma: no cover
    import builtins

    from queue import Queue, Empty, Full, LifoQueue
    from itertools import zip_longest
    from io import StringIO, BytesIO

    map = map
    zip = zip
    string = str
    string_t = str
    long_t = int
    text_t = str
    range = range
    int_types = (int, )
    module_name_t = str

    open_fqdn = 'builtins.open'

    def items(d):
        return d.items()

    def keys(d):
        return d.keys()

    def values(d):
        return d.values()

    def nextfun(it):
        return it.__next__

    exec_ = getattr(builtins, 'exec')

    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

    class WhateverIO(StringIO):

        def write(self, data):
            if isinstance(data, bytes):
                data = data.encode()
            StringIO.write(self, data)

else:
    import __builtin__ as builtins  # noqa
    from Queue import Queue, Empty, Full, LifoQueue  # noqa
    from itertools import (               # noqa
        imap as map,
        izip as zip,
        izip_longest as zip_longest,
    )
    try:
        from cStringIO import StringIO  # noqa
    except ImportError:  # pragma: no cover
        from StringIO import StringIO   # noqa

    string = unicode                # noqa
    string_t = basestring           # noqa
    text_t = unicode
    long_t = long                   # noqa
    range = xrange
    int_types = (int, long)
    module_name_t = str

    open_fqdn = '__builtin__.open'

    def items(d):                   # noqa
        return d.iteritems()

    def keys(d):                    # noqa
        return d.iterkeys()

    def values(d):                  # noqa
        return d.itervalues()

    def nextfun(it):                # noqa
        return it.next

    def exec_(code, globs=None, locs=None):  # pragma: no cover
        """Execute code in a namespace."""
        if globs is None:
            frame = sys._getframe(1)
            globs = frame.f_globals
            if locs is None:
                locs = frame.f_locals
            del frame
        elif locs is None:
            locs = globs
        exec("""exec code in globs, locs""")

    exec_("""def reraise(tp, value, tb=None): raise tp, value, tb""")

    BytesIO = WhateverIO = StringIO         # noqa


def with_metaclass(Type, skip_attrs=set(['__dict__', '__weakref__'])):
    """Class decorator to set metaclass.

    Works with both Python 3 and Python 3 and it does not add
    an extra class in the lookup order like ``six.with_metaclass`` does
    (that is -- it copies the original class instead of using inheritance).

    """

    def _clone_with_metaclass(Class):
        attrs = dict((key, value) for key, value in items(vars(Class))
                     if key not in skip_attrs)
        return Type(Class.__name__, Class.__bases__, attrs)

    return _clone_with_metaclass

########NEW FILE########
__FILENAME__ = imports
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import with_statement

"""
    pyes.utils.imports
    ~~~~~~~~~~~~~~~~~~

    Taken from celery.utils.imports

    :copyright: (c) 2009 - 2012 by Ask Solem.
    :license: BSD, see LICENSE for more details.

"""

import imp as _imp
import importlib
import os
import sys
import six

from contextlib import contextmanager

from .compat import reload


class NotAPackage(Exception):
    pass


if sys.version_info >= (3, 3):  # pragma: no cover

    def qualname(obj):
        return obj.__qualname__

else:

    def qualname(obj):  # noqa
        if not hasattr(obj, "__name__") and hasattr(obj, "__class__"):
            return qualname(obj.__class__)

        return '.'.join([obj.__module__, obj.__name__])


def symbol_by_name(name, aliases={}, imp=None, package=None,
        sep='.', default=None, **kwargs):
    """Get symbol by qualified name.

    The name should be the full dot-separated path to the class::

        modulename.ClassName

    Example::

        celery.concurrency.processes.TaskPool
                                    ^- class name

    or using ':' to separate module and symbol::

        celery.concurrency.processes:TaskPool

    If `aliases` is provided, a dict containing short name/long name
    mappings, the name is looked up in the aliases first.

    Examples:

        >>> symbol_by_name("celery.concurrency.processes.TaskPool")
        <class 'celery.concurrency.processes.TaskPool'>

        >>> symbol_by_name("default", {
        ...     "default": "celery.concurrency.processes.TaskPool"})
        <class 'celery.concurrency.processes.TaskPool'>

        # Does not try to look up non-string names.
        >>> from celery.concurrency.processes import TaskPool
        >>> symbol_by_name(TaskPool) is TaskPool
        True

    """
    if imp is None:
        imp = importlib.import_module

    if not isinstance(name, six.string_types):
        return name                                 # already a class

    name = aliases.get(name) or name
    sep = ':' if ':' in name else sep
    module_name, _, cls_name = name.rpartition(sep)
    if not module_name:
        cls_name, module_name = None, package if package else cls_name
    try:
        try:
            module = imp(module_name, package=package, **kwargs)
        except ValueError as exc:
            raise ValueError("Couldn't import %r: %s" % (name, exc)) from sys.exc_info()[2]
        return getattr(module, cls_name) if cls_name else module
    except (ImportError, AttributeError):
        if default is None:
            raise
    return default


def instantiate(name, *args, **kwargs):
    """Instantiate class by name.

    See :func:`symbol_by_name`.

    """
    return symbol_by_name(name)(*args, **kwargs)


@contextmanager
def cwd_in_path():
    cwd = os.getcwd()
    if cwd in sys.path:
        yield
    else:
        sys.path.insert(0, cwd)
        try:
            yield cwd
        finally:
            try:
                sys.path.remove(cwd)
            except ValueError:  # pragma: no cover
                pass


def find_module(module, path=None, imp=None):
    """Version of :func:`imp.find_module` supporting dots."""
    if imp is None:
        imp = importlib.import_module
    with cwd_in_path():
        if "." in module:
            last = None
            parts = module.split(".")
            for i, part in enumerate(parts[:-1]):
                mpart = imp(".".join(parts[:i + 1]))
                try:
                    path = mpart.__path__
                except AttributeError:
                    raise NotAPackage(module)
                last = _imp.find_module(parts[i + 1], path)
            return last
        return _imp.find_module(module)


def import_from_cwd(module, imp=None, package=None):
    """Import module, but make sure it finds modules
    located in the current directory.

    Modules located in the current directory has
    precedence over modules located in `sys.path`.
    """
    if imp is None:
        imp = importlib.import_module
    with cwd_in_path():
        return imp(module, package=package)


def reload_from_cwd(module, reloader=None):
    if reloader is None:
        reloader = reload
    with cwd_in_path():
        return reloader(module)


def module_file(module):
    name = module.__file__
    return name[:-1] if name.endswith(".pyc") else name

########NEW FILE########
__FILENAME__ = test_200
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pyes

index = "test2"
doc_type = "test"

es = pyes.ES(["http://127.0.0.1:9200"])

es.create_index_if_missing(index)
for i in range(1, 100):
    es.index({"number":i}, index=index, doc_type=doc_type)

es.refresh([index])

query = pyes.QueryStringQuery("*")
search = pyes.query.Search(query=query, start=0, size=10, sort=[{"number":"asc"}], fields=["number"])
results = es.search(search, indices=[index], doc_types=[doc_type])
print [i for i in results]

query2 = pyes.QueryStringQuery("*")
search2 = pyes.query.Search(query=query2, start=20, size=20, sort=[{"number":"asc"}], fields=["number"])
results2 = es.search(search2, indices=[index], doc_types=[doc_type])
print [i for i in results2]

es.delete_index_if_exists(index)

########NEW FILE########
__FILENAME__ = test_aliases
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from pyes.tests import ESTestCase
from pyes import exceptions

class ErrorReportingTestCase(ESTestCase):
    def setUp(self):
        super(ErrorReportingTestCase, self).setUp()
        #self.conn.indices.set_alias('test-alias', ['_river'])
        #self.conn.indices.delete_alias('test-alias', ['_river'])
        self.conn.indices.delete_index_if_exists('test-index2')

    def tearDown(self):
        #self.conn.indices.set_alias('test-alias', ['_river'])
        #self.conn.indices.delete_alias('test-alias', ['_river'])
        self.conn.indices.delete_index_if_exists('test-index2')

    def testCreateDeleteAliases(self):
        """Test errors thrown when creating or deleting aliases.

        """
        self.assertTrue('acknowledged' in self.conn.indices.create_index(self.index_name))

        # Check initial output of get_indices.
        result = self.conn.indices.get_indices(include_aliases=True)
        self.assertTrue('test-index' in result)
        self.assertEqual(result['test-index'], {'num_docs': 0})
        self.assertTrue('test-alias' not in result)

        # Check getting a missing alias.
        err = self.checkRaises(exceptions.IndexMissingException,
            self.conn.indices.get_alias, 'test-alias')
        self.assertEqual(str(err), '[test-alias] missing')

        # Check deleting a missing alias (doesn't return a error).
        self.conn.indices.delete_alias("test-alias", self.index_name)

        # Add an alias from test-alias to test-index
        self.conn.indices.change_aliases([['add', 'test-index', 'test-alias', {}]])
        self.assertEqual(self.conn.indices.get_alias("test-alias"), ['test-index'])

        # Adding an alias to a missing index fails
        err = self.checkRaises(exceptions.IndexMissingException,
            self.conn.indices.change_aliases,
            [['add', 'test-missing-index', 'test-alias', {}]])
        self.assertEqual(str(err), '[test-missing-index] missing')
        self.assertEqual(self.conn.indices.get_alias("test-alias"), ['test-index'])

        #        # An alias can't be deleted using delete_index.
        #        err = self.checkRaises(exceptions.NotFoundException,
        #                               self.conn.delete_index, 'test-alias')
        #        self.assertEqual(str(err), '[test-alias] missing')

        # Check return value from indices.get_indices now.
        result = self.conn.indices.get_indices(include_aliases=True)
        self.assertTrue('test-index' in result)
        self.assertEqual(result['test-index'], {'num_docs': 0})
        self.assertTrue('test-alias' in result)
        self.assertEqual(result['test-alias'], {'alias_for': ['test-index'], 'num_docs': 0})

        result = self.conn.indices.get_indices(include_aliases=False)
        self.assertTrue('test-index' in result)
        self.assertEqual(result['test-index'], {'num_docs': 0})
        self.assertTrue('test-alias' not in result)

        # Add an alias to test-index2.
        self.assertTrue('ok' in self.conn.indices.create_index("test-index2"))
        self.conn.indices.change_aliases([['add', 'test-index2', 'test-alias', {}]])
        self.assertEqual(sorted(self.conn.indices.get_alias("test-alias")),
            ['test-index', 'test-index2'])

        # Check deleting multiple indices from an alias.
        self.conn.indices.delete_alias("test-alias", [self.index_name, "test-index2"])
        self.checkRaises(exceptions.IndexMissingException, self.conn.indices.get_alias, 'test-alias')

        # Check deleting multiple indices from a missing alias (still no error)
        self.conn.indices.delete_alias("test-alias", [self.index_name, "test-index2"])

        # Check that we still get an error for a missing alias.
        err = self.checkRaises(exceptions.IndexMissingException,
            self.conn.indices.get_alias, 'test-alias')
        self.assertEqual(str(err), '[test-alias] missing')

    def testWriteToAlias(self):
        self.assertTrue('acknowledged' in self.conn.indices.create_index(self.index_name))
        self.assertTrue('acknowledged' in self.conn.indices.create_index("test-index2"))
        self.assertTrue('acknowledged' in self.conn.indices.set_alias("test-alias", ['test-index']))
        self.assertTrue('acknowledged' in self.conn.indices.set_alias("test-alias2", ['test-index', 'test-index2']))

        # Can write to indices.aliases only if they point to exactly one index.
        self.conn.index(dict(title='doc1'), 'test-index', 'testtype')
        self.conn.index(dict(title='doc1'), 'test-index2', 'testtype')
        self.conn.index(dict(title='doc1'), 'test-alias', 'testtype')
        self.checkRaises(exceptions.ElasticSearchIllegalArgumentException,
            self.conn.index, dict(title='doc1'),
            'test-alias2', 'testtype')

        self.conn.indices.refresh() # ensure that the documents have been indexed.
        # Check the document counts for each index or alias.
        result = self.conn.indices.get_indices(include_aliases=True)
        self.assertEqual(result['test-index'], {'num_docs': 2})
        self.assertEqual(result['test-index2'], {'num_docs': 1})
        self.assertEqual(result['test-alias'], {'alias_for': ['test-index'], 'num_docs': 2})
        self.assertEqual(result['test-alias2'], {'alias_for': ['test-index', 'test-index2'], 'num_docs': 3})

if __name__ == "__main__":
    import unittest
    unittest.main()


########NEW FILE########
__FILENAME__ = test_attachments
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from pyes.tests import ESTestCase
from pyes.query import TermQuery
from pyes.es import file_to_attachment

class TestFileSaveTestCase(ESTestCase):
    def test_filesave(self):
        mapping = {
            "my_attachment": {"type": "attachment",
                              'fields': {
                                  "file": {'store': "yes"},
                                  "date": {'store': "yes"},
                                  "author": {'store': "yes"},
                                  "title": {'store': "yes"}, }
            }
        }
        self.conn.indices.create_index(self.index_name)
        self.conn.indices.put_mapping(self.document_type, {self.document_type: {'properties': mapping}}, self.index_name)
        self.conn.indices.refresh(self.index_name)
        self.conn.indices.get_mapping(self.document_type, self.index_name)
        name = "map.json"
        content = self.get_datafile(name)
        self.conn.put_file(self.get_datafile_path(name), self.index_name, self.document_type, 1, name=name)
        self.conn.indices.refresh(self.index_name)
        _ = self.conn.indices.get_mapping(self.document_type, self.index_name)
        nname, ncontent = self.conn.get_file(self.index_name, self.document_type, 1)
        self.assertEqual(name, nname)
        self.assertEqual(content, ncontent)


class QueryAttachmentTestCase(ESTestCase):
    def setUp(self):
        super(QueryAttachmentTestCase, self).setUp()
        mapping = {
            "attachment": {"type": "attachment",
                           'fields': {
                               "file": {'store': "yes"},
                               "date": {'store': "yes"},
                               "author": {'store': "yes"},
                               "title": {'store': "yes", "term_vector": "with_positions_offsets"},
                               "attachment": {'store': "yes"},
                               }
            },
            'uuid': {'boost': 1.0,
                     'index': 'not_analyzed',
                     'store': 'yes',
                     'type': u'string'}
        }
        #        mapping = {
        #            self.document_type: {
        #                "_index": {"enabled": "yes"},
        #                "_id": {"store": "yes"},
        #                "properties": {
        #                    "attachment": {
        #                        "type": "attachment",
        #                        "fields": {
        #                            "title": {"store": "yes", "term_vector" : "with_positions_offsets"},
        #                            "attachment": {"store":"yes", "term_vector" : "with_positions_offsets"}
        #                        },
        #                        "store":"yes"
        #
        #                    },
        #                    "uuid": {"type": "string", "store": "yes", "index": "not_analyzed"}
        #                },
        #                "_all": {"store": "yes", "term_vector": "with_positions_offsets"}
        #            }
        #        }
        self.conn.debug_dump = True
        self.conn.indices.create_index(self.index_name)
        self.conn.indices.put_mapping(self.document_type, {self.document_type: {'properties': mapping}}, self.index_name)
        self.conn.indices.refresh(self.index_name)
        self.conn.indices.get_mapping(self.document_type, self.index_name)
        self.conn.index({"attachment": file_to_attachment(self.get_datafile_path("testXHTML.html")), "uuid": "1"}
            , self.index_name, self.document_type, 1)
        self.conn.indices.refresh(self.index_name)

    def test_TermQuery(self):
        q = TermQuery("uuid", "1").search(
            fields=['attachment', 'attachment.author', 'attachment.title', 'attachment.date'])
        #        q = TermQuery("uuid", "1", fields=['*'])
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 1)
        self.assertEqual(resultset.hits[0]['fields']['attachment.author'], u'Tika Developers')

########NEW FILE########
__FILENAME__ = test_bulk
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from pyes.tests import ESTestCase
from pyes.models import _is_bulk_item_ok, _raise_exception_if_bulk_item_failed
from pyes.query import TermQuery
from pyes.exceptions import BulkOperationException

class BulkTestCase(ESTestCase):
    def setUp(self):
        super(BulkTestCase, self).setUp()
        mapping = {u'parsedtext': {'boost': 1.0,
                                   'index': 'analyzed',
                                   'store': 'yes',
                                   'type': u'string',
                                   "term_vector": "with_positions_offsets"},
                   u'name': {'boost': 1.0,
                             'index': 'analyzed',
                             'store': 'yes',
                             'type': u'string',
                             "term_vector": "with_positions_offsets"},
                   u'title': {'boost': 1.0,
                              'index': 'analyzed',
                              'store': 'yes',
                              'type': u'string',
                              "term_vector": "with_positions_offsets"},
                   u'pos': {'store': 'yes',
                            'type': u'integer'},
                   u'uuid': {'boost': 1.0,
                             'index': 'not_analyzed',
                             'store': 'yes',
                             'type': u'string'}}
        self.conn.indices.create_index(self.index_name)
        self.conn.indices.put_mapping(self.document_type, {'properties': mapping}, self.index_name)

    def test_force(self):
        self.conn.raise_on_bulk_item_failure = False
        self.conn.index({"name": "Joe Tester", "parsedtext": "Joe Testere nice guy", "uuid": "11111", "position": 1},
            self.index_name, self.document_type, 1, bulk=True)
        self.conn.index({"name": "Bill Baloney", "parsedtext": "Bill Testere nice guy", "uuid": "22222", "position": 2},
            self.index_name, self.document_type, 2, bulk=True)
        self.conn.index({"name": "Bill Clinton", "parsedtext": """Bill is not
                nice guy""", "uuid": "33333", "position": 3}, self.index_name, self.document_type, 3, bulk=True)
        bulk_result = self.conn.force_bulk()
        self.assertEqual(len(bulk_result['items']), 3)
        self.conn.indices.refresh(self.index_name)
        q = TermQuery("name", "bill")
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 2)

    def test_automatic_flush(self):
        self.conn.force_bulk()
        self.conn.bulk_size = 3
        self.conn.raise_on_bulk_item_failure = False

        self.assertIsNone(
            self.conn.index({"name": "Joe Tester", "parsedtext": "Joe Testere nice guy", "uuid": "11111", "position": 1}
                ,
                self.index_name, self.document_type, 4, bulk=True))
        self.assertIsNone(self.conn.flush_bulk(False))
        self.assertEqual(len(self.conn.bulker.bulk_data), 1)

        self.assertIsNone(
            self.conn.index(
                    {"name": "Bill Baloney", "parsedtext": "Bill Testere nice guy", "uuid": "22222", "position": 2},
                self.index_name, self.document_type, 5, bulk=True))
        self.assertIsNone(self.conn.flush_bulk(False))
        self.assertEqual(len(self.conn.bulker.bulk_data), 2)

        bulk_result = self.conn.index(
                {"name": "Bill Clinton", "parsedtext": """Bill is not nice guy""", "uuid": "33333", "position": 3},
            self.index_name, self.document_type, 6, bulk=True)
        self.assertEqual(len(bulk_result['items']), 3)
        self.assertEqual(self.conn.bulker.bulk_data, [])

        self.conn.bulk_size = 3

        self.assertIsNone(self.conn.delete(self.index_name, self.document_type, 4, True))
        self.assertIsNone(self.conn.flush_bulk(False))
        self.assertEqual(len(self.conn.bulker.bulk_data), 1)

        self.assertIsNone(self.conn.delete(self.index_name, self.document_type, 5, True))
        self.assertIsNone(self.conn.flush_bulk(False))
        self.assertEqual(len(self.conn.bulker.bulk_data), 2)

        bulk_result = self.conn.delete(self.index_name, self.document_type, 6, True)
        self.assertIsNone(self.conn.flush_bulk(False))
        self.assertEqual(len(bulk_result['items']), 3)
        self.assertEqual(self.conn.bulker.bulk_data, [])

        self.conn.indices.refresh(self.index_name)

    def test_error(self):
        self.conn.force_bulk()
        self.conn.bulk_size = 2

        self.assertIsNone(
            self.conn.index(
                    {"name": "Bill Baloney", "parsedtext": "Bill Testere nice guy", "uuid": "22222", "position": 2},
                self.index_name, self.document_type, 7, bulk=True))
        self.assertIsNone(self.conn.flush_bulk(False))
        self.assertEqual(len(self.conn.bulker.bulk_data), 1)

        bulk_result = self.conn.index(
            "invalid", self.index_name, self.document_type, 8, bulk=True)
        self.assertEqual(len(bulk_result['items']), 2)
        self.assertTrue(bulk_result["items"][0]["index"]["ok"])
        self.assertTrue("error" in bulk_result["items"][1]["index"])
        self.assertEqual(self.conn.bulker.bulk_data, [])

        self.conn.bulk_size = 2
        self.assertIsNone(self.conn.delete(
            self.index_name, self.document_type, 9, bulk=True))
        bulk_result = self.conn.delete(
            self.index_name, "#foo", 9, bulk=True)
        self.assertEqual(len(bulk_result['items']), 2)
        self.assertTrue(bulk_result["items"][0]["delete"]["ok"])
        self.assertTrue("error" in bulk_result["items"][1]["delete"])
        self.assertEqual(self.conn.bulker.bulk_data, [])

    def test_raise_exception_if_bulk_item_failed(self):
        index_ok_1 = {'index': {'_type': 'test-type', '_id': '4', 'ok': True, '_version': 1, '_index': 'test-index'}}
        self.assertTrue(_is_bulk_item_ok(index_ok_1))
        index_ok_2 = {'index': {'_type': 'test-type', '_id': '5', 'ok': True, '_version': 1, '_index': 'test-index'}}
        self.assertTrue(_is_bulk_item_ok(index_ok_2))
        index_ok_3 = {'index': {'_type': 'test-type', '_id': '6', 'ok': True, '_version': 1, '_index': 'test-index'}}
        self.assertTrue(_is_bulk_item_ok(index_ok_3))

        index_error_1 = {'index': {'_type': 'test-type', '_id': '8', '_index': 'test-index',
                                   'error': 'ElasticSearchParseException[Failed to derive xcontent from (offset=0, length=7): [105, 110, 118, 97, 108, 105, 100]]'}}
        self.assertFalse(_is_bulk_item_ok(index_error_1))
        index_error_2 = {'index': {'_type': 'test-type', '_id': '9', '_index': 'test-index',
                                   'error': 'ElasticSearchParseException[Failed to derive xcontent from (offset=0, length=7): [105, 110, 118, 97, 108, 105, 100]]'}}
        self.assertFalse(_is_bulk_item_ok(index_error_2))

        delete_ok_1 = {'delete': {'_type': 'test-type', '_id': '4', 'ok': True, '_version': 2, '_index': 'test-index'}}
        self.assertTrue(_is_bulk_item_ok(delete_ok_1))
        delete_ok_2 = {'delete': {'_type': 'test-type', '_id': '5', 'ok': True, '_version': 2, '_index': 'test-index'}}
        self.assertTrue(_is_bulk_item_ok(delete_ok_2))
        delete_ok_3 = {'delete': {'_type': 'test-type', '_id': '6', 'ok': True, '_version': 2, '_index': 'test-index'}}
        self.assertTrue(_is_bulk_item_ok(delete_ok_3))
        delete_error_1 = {'delete': {'_type': '#foo', '_id': '9', '_index': 'test-index',
                                     'error': "InvalidTypeNameException[mapping type name [#foo] should not include '#' in it]"}}
        self.assertFalse(_is_bulk_item_ok(delete_error_1))
        delete_error_2 = {'delete': {'_type': '#foo', '_id': '10', '_index': 'test-index',
                                     'error': "InvalidTypeNameException[mapping type name [#foo] should not include '#' in it]"}}
        self.assertFalse(_is_bulk_item_ok(delete_error_1))

        index_all_ok = {'items': [
            index_ok_1,
            index_ok_2,
            index_ok_3],
                        'took': 4}
        delete_all_ok = {'items': [
            delete_ok_1,
            delete_ok_2,
            delete_ok_3],
                         'took': 0}
        index_one_error = {'items': [
            index_ok_1,
            index_error_1],
                           'took': 156}
        index_two_errors = {'items': [
            index_ok_2,
            index_error_1,
            index_error_2],
                            'took': 156}
        delete_one_error = {'items': [
            delete_ok_1,
            delete_error_1],
                            'took': 1}
        delete_two_errors = {'items': [
            delete_ok_2,
            delete_error_1,
            delete_error_2],
                             'took': 1}
        mixed_errors = {'items': [
            delete_ok_3,
            index_ok_1,
            index_error_1,
            delete_error_1,
            delete_error_2],
                        'took': 1}
        oops_all_errors = {'items': [
            index_error_1,
            delete_error_1,
            delete_error_2],
                           'took': 1}

        self.assertIsNone(_raise_exception_if_bulk_item_failed(index_all_ok))
        self.assertIsNone(_raise_exception_if_bulk_item_failed(delete_all_ok))

        with self.assertRaises(BulkOperationException) as cm:
            _raise_exception_if_bulk_item_failed(index_one_error)
        self.assertEqual(cm.exception, BulkOperationException(
            [index_error_1], index_one_error))

        with self.assertRaises(BulkOperationException) as cm:
            _raise_exception_if_bulk_item_failed(index_two_errors)
        self.assertEqual(cm.exception, BulkOperationException(
            [index_error_1, index_error_2], index_two_errors))

        with self.assertRaises(BulkOperationException) as cm:
            _raise_exception_if_bulk_item_failed(delete_one_error)
        self.assertEqual(cm.exception, BulkOperationException(
            [delete_error_1], delete_one_error))

        with self.assertRaises(BulkOperationException) as cm:
            _raise_exception_if_bulk_item_failed(delete_two_errors)
        self.assertEqual(cm.exception, BulkOperationException(
            [delete_error_1, delete_error_2], delete_two_errors))

        with self.assertRaises(BulkOperationException) as cm:
            _raise_exception_if_bulk_item_failed(mixed_errors)
        self.assertEqual(cm.exception, BulkOperationException(
            [index_error_1, delete_error_1, delete_error_2], mixed_errors))

        with self.assertRaises(BulkOperationException) as cm:
            _raise_exception_if_bulk_item_failed(oops_all_errors)
        self.assertEqual(cm.exception, BulkOperationException(
            [index_error_1, delete_error_1, delete_error_2], oops_all_errors))

        # now, try it against a real index...
        self.conn.force_bulk()
        self.conn.raise_on_bulk_item_failure = False
        self.conn.bulk_size = 1

        bulk_result = self.conn.delete(self.index_name, "#bogus", 9, bulk=True)
        self.assertFalse(_is_bulk_item_ok(bulk_result["items"][0]))

        bulk_result = self.conn.index("invalid", self.index_name, self.document_type, 8, bulk=True)
        self.assertFalse(_is_bulk_item_ok(bulk_result["items"][0]))

        self.conn.raise_on_bulk_item_failure = True

        with self.assertRaises(BulkOperationException) as cm:
            self.conn.delete(
                self.index_name, "#bogus", 9, bulk=True)

        with self.assertRaises(BulkOperationException) as cm:
            self.conn.index(
                "invalid", self.index_name, self.document_type, 8, bulk=True)

if __name__ == "__main__":
    import unittest
    unittest.main()

########NEW FILE########
__FILENAME__ = test_cluster
# -*- coding: utf-8 -*-
from pyes.tests import ESTestCase

class ClusterTestCase(ESTestCase):
    def setUp(self):
        super(ClusterTestCase, self).setUp()
        mapping = {u'parsedtext': {'boost': 1.0,
                                   'index': 'analyzed',
                                   'store': 'yes',
                                   'type': u'string',
                                   "term_vector": "with_positions_offsets"},
                   u'name': {'boost': 1.0,
                             'index': 'analyzed',
                             'store': 'yes',
                             'type': u'string',
                             "term_vector": "with_positions_offsets"},
                   u'title': {'boost': 1.0,
                              'index': 'analyzed',
                              'store': 'yes',
                              'type': u'string',
                              "term_vector": "with_positions_offsets"},
                   u'pos': {'store': 'yes',
                            'type': u'integer'},
                   u'uuid': {'boost': 1.0,
                             'index': 'not_analyzed',
                             'store': 'yes',
                             'type': u'string'}}
        self.conn.indices.create_index(self.index_name)
        self.conn.indices.put_mapping(self.document_type, {'properties': mapping}, self.index_name)
        self.conn.index({"name": "Joe Tester", "parsedtext": "Joe Testere nice guy", "uuid": "11111", "position": 1},
            self.index_name, self.document_type, 1)
        self.conn.index({"name": "Bill Baloney", "parsedtext": "Bill Testere nice guy", "uuid": "22222", "position": 2},
            self.index_name, self.document_type, 2)
        self.conn.index({"name": "Bill Clinton", "parsedtext": """Bill is not
                nice guy""", "uuid": "33333", "position": 3}, self.index_name, self.document_type, 3)
        self.conn.indices.refresh(self.index_name)

    def test_ClusterState(self):
        result = self.conn.cluster.state()
        self.assertTrue('blocks' in result)
        self.assertTrue('routing_table' in result)

    def test_ClusterNodes(self):
        result = self.conn.cluster.nodes_info()
        self.assertTrue('cluster_name' in result)
        self.assertTrue('nodes' in result)

    def test_ClusterHealth(self):
        # Make sure that when we get the cluster health, that we get the
        # default keys that we'd expect...
        result = self.conn.cluster.health()
        for key in ['cluster_name', 'status', 'timed_out', 'number_of_nodes',
                    'number_of_data_nodes', 'active_primary_shards',
                    'active_shards', 'relocating_shards', 'initializing_shards',
                    'unassigned_shards']:
            self.assertIn(key, result)

        # We should also make sure that at least /some/ of the keys are
        # the values that we'd expect
        self.assertEqual(result['cluster_name'], 'elasticsearch')
        # Make sure we see the number of active shards we expect
        #self.assertEqual(result['active_shards'], 24)

        # Now let's test that the indices bit actually works
        result = self.conn.cluster.health(indices=['non-existent-index'],
                                          timeout=0, wait_for_status='green')
        # There shouldn't be any active shards on this index
        self.assertEqual(result['active_shards'], 0)

if __name__ == "__main__":
    import unittest
    unittest.main()
########NEW FILE########
__FILENAME__ = test_convert_errors
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from pyes.tests import ESTestCase
from pyes.exceptions import (NotFoundException, IndexAlreadyExistsException)
from pyes import convert_errors


class RaiseIfErrorTestCase(ESTestCase):
    def test_not_found_exception(self):
        self.assertRaises(
            NotFoundException,
            convert_errors.raise_if_error,
            404, {u'_type': u'a_type', u'_id': u'1', u'_index': u'_all'})

    def test_nested_index_already_exists_exception(self):
        self.assertRaises(
            IndexAlreadyExistsException,
            convert_errors.raise_if_error,
            400, {u'status': 400,
                  u'error': (u'RemoteTransportException[[name][inet' +
                             u'[/127.0.0.1:9300]][indices/createIndex]]; ' +
                             u'nested: IndexAlreadyExistsException[' +
                             u'[test-index] Already exists]; ')})

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_dump_curl
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from pyes.tests import ESTestCase, get_conn
import six
if six.PY2:
    from io import StringIO
else:
    from io import BytesIO as StringIO

class DumpCurlTestCase(ESTestCase):
    def setUp(self):
        super(DumpCurlTestCase, self).setUp()

    def testDumpCurl(self):
        """Test errors thrown when creating or deleting indices.

        """
        dump = StringIO()
        conn = get_conn(dump_curl=dump)
        result = conn.index(dict(title="Hi"), self.index_name, self.document_type)
        self.assertTrue('ok' in result)
        self.assertTrue('error' not in result)
        dump = dump.getvalue().decode("utf-8")
        self.assertTrue("""
            curl -XPOST 'http://127.0.0.1:9200/test-index/test-type?pretty=true' -d '{"title": "Hi"}'
            """.strip() in dump)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_errors
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from pyes.tests import ESTestCase
from pyes import exceptions

class ErrorReportingTestCase(ESTestCase):
    def setUp(self):
        super(ErrorReportingTestCase, self).setUp()
        self.conn.indices.delete_index_if_exists(self.index_name)

    def tearDown(self):
        self.conn.indices.delete_index_if_exists(self.index_name)

    def testCreateDelete(self):
        """Test errors thrown when creating or deleting indices.

        """
        result = self.conn.indices.create_index(self.index_name)
        self.assertTrue('acknowledge' in result)
        self.assertTrue('error' not in result)

        err = self.checkRaises(exceptions.IndexAlreadyExistsException,
            self.conn.indices.create_index, self.index_name)
        self.assertEqual(str(err), "[test-index] already exists")
        self.assertEqual(err.status, 400)
        self.assertTrue('error' in err.result)
        self.assertTrue('ok' not in err.result)

        result = self.conn.indices.delete_index(self.index_name)
        self.assertTrue('ok' in result)
        self.assertTrue('error' not in result)

        err = self.checkRaises(exceptions.IndexMissingException,
            self.conn.indices.delete_index, self.index_name)
        self.assertEqual(str(err), "[test-index] missing")
        self.assertEqual(err.status, 404)
        self.assertTrue('error' in err.result)
        self.assertTrue('ok' not in err.result)

    def testMissingIndex(self):
        """Test generation of a IndexMissingException.

        """
        err = self.checkRaises(exceptions.IndexMissingException,
            self.conn.indices.flush, self.index_name)
        self.assertEqual(str(err), "[test-index] missing")
        self.assertEqual(err.status, 404)
        self.assertTrue('error' in err.result)
        self.assertTrue('ok' not in err.result)

    def testBadRequest(self):
        """Test error reported by doing a bad request.

        """
        err = self.checkRaises(exceptions.ElasticSearchException,
            self.conn._send_request, 'GET', '_bad_request')
        self.assertEqual(str(err), "No handler found for uri [/_bad_request] and method [GET]")
        self.assertEqual(err.status, 400)
        self.assertEqual(err.result, 'No handler found for uri [/_bad_request] and method [GET]')

    def testDelete(self):
        """Test error reported by deleting a missing document.

        """
        self.checkRaises(exceptions.NotFoundException,
            self.conn.delete, self.index_name, "flibble",
            "asdf")


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_esmodel
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from copy import deepcopy
import unittest
from pyes.tests import ESTestCase
from pyes.models import DotDict

class ElasticSearchModelTestCase(ESTestCase):
    def setUp(self):
        super(ElasticSearchModelTestCase, self).setUp()
        self.init_default_index()

    def test_ElasticSearchModel_init(self):
        obj = self.conn.factory_object(self.index_name, self.document_type, {"name": "test", "val": 1})
        self.assertEqual(obj.name, "test")
        obj.name = "aaa"
        self.assertEqual(obj.name, "aaa")
        self.assertEqual(obj.val, 1)
        self.assertEqual(obj._meta.id, None)
        obj._meta.id = "dasdas"
        self.assertEqual(obj._meta.id, "dasdas")
        self.assertEqual(sorted(obj.keys()), ["name", "val"])
        obj.save()
        obj.name = "test2"
        obj.save()

        reloaded = self.conn.get(self.index_name, self.document_type, obj._meta.id)
        self.assertEqual(reloaded.name, "test2")

    def test_DotDict(self):
        dotdict = DotDict(foo="bar")
        dotdict2 = deepcopy(dotdict)
        dotdict2["foo"] = "baz"
        self.assertEqual(dotdict["foo"], "bar")
        self.assertEqual(dotdict2["foo"], "baz")
        self.assertEqual(type(dotdict2), DotDict)

        dotdict = DotDict(foo="bar", bar=DotDict(baz="qux"))
        dotdict2 = deepcopy(dotdict)
        dotdict2["bar"]["baz"] = "foo"
        self.assertEqual(dotdict["bar"]["baz"], "qux")
        self.assertEqual(dotdict2["bar"]["baz"], "foo")
        self.assertEqual(type(dotdict2), DotDict)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_facets
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from pyes.tests import ESTestCase
from pyes.facets import DateHistogramFacet, TermFacet
from pyes.filters import TermFilter, RangeFilter, BoolFilter
from pyes.query import FilteredQuery, MatchAllQuery, Search, TermQuery
from pyes.utils import ESRange
import datetime

class FacetSearchTestCase(ESTestCase):
    def setUp(self):
        super(FacetSearchTestCase, self).setUp()
        mapping = {u'parsedtext': {'boost': 1.0,
                                   'index': 'analyzed',
                                   'store': 'yes',
                                   'type': u'string',
                                   "term_vector": "with_positions_offsets"},
                   u'name': {'boost': 1.0,
                             'index': 'analyzed',
                             'store': 'yes',
                             'type': u'string',
                             "term_vector": "with_positions_offsets"},
                   u'title': {'boost': 1.0,
                              'index': 'analyzed',
                              'store': 'yes',
                              'type': u'string',
                              "term_vector": "with_positions_offsets"},
                   u'position': {'store': 'yes',
                                 'type': u'integer'},
                   u'tag': {'store': 'yes',
                            'type': u'string'},
                   u'date': {'store': 'yes',
                             'type': u'date'},
                   u'uuid': {'boost': 1.0,
                             'index': 'not_analyzed',
                             'store': 'yes',
                             'type': u'string'}}
        self.conn.indices.create_index(self.index_name)
        self.conn.indices.put_mapping(self.document_type, {'properties': mapping}, self.index_name)
        self.conn.index({"name": "Joe Tester",
                         "parsedtext": "Joe Testere nice guy",
                         "uuid": "11111",
                         "position": 1,
                         "tag": "foo",
                         "date": datetime.date(2011, 5, 16)},
            self.index_name, self.document_type, 1)
        self.conn.index({"name": " Bill Baloney",
                         "parsedtext": "Bill Testere nice guy",
                         "uuid": "22222",
                         "position": 2,
                         "tag": "foo",
                         "date": datetime.date(2011, 4, 16)},
            self.index_name, self.document_type, 2)
        self.conn.index({"name": "Bill Clinton",
                         "parsedtext": "Bill is not nice guy",
                         "uuid": "33333",
                         "position": 3,
                         "tag": "bar",
                         "date": datetime.date(2011, 4, 28)},
            self.index_name, self.document_type, 3)
        self.conn.indices.refresh(self.index_name)

    def test_terms_facet(self):
        q = MatchAllQuery()
        q = q.search()
        q.facet.add_term_facet('tag')
        resultset = self.conn.search(query=q, indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 3)
        self.assertEqual(resultset.facets.tag.terms, [{u'count': 2, u'term': u'foo'},
                {u'count': 1, u'term': u'bar'}])

        q2 = MatchAllQuery()
        q2 = q2.search()
        q2.facet.add_term_facet('tag')
        q3 = MatchAllQuery()
        q3 = q3.search()
        q3.facet.add_term_facet('tag')
        self.assertEqual(q2, q3)

        q4 = MatchAllQuery()
        q4 = q4.search()
        q4.facet.add_term_facet('bag')
        self.assertNotEqual(q2, q4)

    def test_terms_facet_filter(self):
        q = MatchAllQuery()
        q = FilteredQuery(q, TermFilter('tag', 'foo'))
        q = q.search()
        q.facet.add_term_facet('tag')
        resultset = self.conn.search(query=q, indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 2)
        self.assertEqual(resultset.facets['tag']['terms'], [{u'count': 2, u'term': u'foo'}])
        self.assertEqual(resultset.facets.tag.terms, [{u'count': 2, u'term': u'foo'}])

        q2 = MatchAllQuery()
        q2 = FilteredQuery(q2, TermFilter('tag', 'foo'))
        q2 = q2.search()
        q2.facet.add_term_facet('tag')
        q3 = MatchAllQuery()
        q3 = FilteredQuery(q3, TermFilter('tag', 'foo'))
        q3 = q3.search()
        q3.facet.add_term_facet('tag')
        self.assertEqual(q2, q3)

        q4 = MatchAllQuery()
        q4 = FilteredQuery(q4, TermFilter('tag', 'foo'))
        q4 = q4.search()
        q4.facet.add_term_facet('bag')
        self.assertNotEqual(q3, q4)

    def test_date_facet(self):
        q = MatchAllQuery()
        q = q.search()
        q.facet.facets.append(DateHistogramFacet('date_facet',
            field='date',
            interval='month'))
        resultset = self.conn.search(query=q, indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 3)
        self.assertEqual(resultset.facets.date_facet.entries, [{u'count': 2, u'time': 1301616000000},
                {u'count': 1, u'time': 1304208000000}])
        self.assertEqual(datetime.datetime.utcfromtimestamp(1301616000000 / 1000.).date(),
            datetime.date(2011, 4, 1))
        self.assertEqual(datetime.datetime.utcfromtimestamp(1304208000000 / 1000.).date(),
            datetime.date(2011, 5, 1))

    def test_date_facet_filter(self):
        q = MatchAllQuery()
        q = FilteredQuery(q, RangeFilter(qrange=ESRange('date',
            datetime.date(2011, 4, 1),
            datetime.date(2011, 5, 1),
            include_upper=False)))
        q = q.search()
        q.facet.facets.append(DateHistogramFacet('date_facet',
            field='date',
            interval='month'))
        resultset = self.conn.search(query=q, indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 2)
        self.assertEqual(resultset.facets['date_facet']['entries'], [{u'count': 2, u'time': 1301616000000}])

    def test_facet_filter_is_serialized_correctly(self):
        query = MatchAllQuery().search(size=0)
        query.facet.add(TermFacet(field='topic', facet_filter=BoolFilter(must_not=TermQuery(field='reviewed', value=True))))
        serialized = query.serialize()
        self.assertTrue(serialized['facets']['topic']['facet_filter']['bool'])

    def test_term_facet_zero_size(self):
        facet = TermFacet(field='topic', size=0)
        serialized = facet.serialize()
        self.assertEqual(0, serialized['topic']['terms']['size'])


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_filters
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from pyes.tests import ESTestCase


class ScriptFilterTestCase(ESTestCase):

    def test_lang(self):
        from pyes.filters import ScriptFilter
        f = ScriptFilter(
            'name',
            params={
                'param_1': 1,
                'param_2': 'boo',
            },
            lang='native'
        )
        expected = {
            'script': {
                'params': {
                    'param_1': 1,
                    'param_2': 'boo'},
                'script': 'name',
                'lang': 'native',
            }
        }
        self.assertEqual(expected, f.serialize())

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_geoloc
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from pyes.tests import ESTestCase
from pyes.filters import GeoBoundingBoxFilter, GeoDistanceFilter, GeoPolygonFilter
from pyes.query import FilteredQuery, MatchAllQuery

#--- Geo Queries Test case
class GeoQuerySearchTestCase(ESTestCase):

    def setUp(self):
        super(GeoQuerySearchTestCase, self).setUp()
        mapping = {
            "pin" : {
                "properties" : {
                    "location" : {
                        "type" : "geo_point"
                    }
                }
            }
        }
        self.conn.indices.delete_index_if_exists("test-mindex")
        self.conn.indices.create_index("test-mindex")
        self.conn.indices.put_mapping(self.document_type, {'properties':mapping}, ["test-mindex"])
        self.conn.index({
            "pin" : {
                "location" : {
                    "lat" : 40.12,
                    "lon" :-71.34
                }
            }
        }, "test-mindex", self.document_type, 1)
        self.conn.index({
            "pin" : {
                "location" : {
                    "lat" : 40.12,
                    "lon" : 71.34
                }
            }
        }, "test-mindex", self.document_type, 2)

        self.conn.indices.refresh(["test-mindex"])

    def tearDown(self):
        self.conn.indices.delete_index_if_exists("test-mindex")

    def test_GeoDistanceFilter(self):
        gq = GeoDistanceFilter("pin.location", {"lat" : 40, "lon" :70}, "200km")
        q = FilteredQuery(MatchAllQuery(), gq)
        resultset = self.conn.search(query=q, indices=["test-mindex"])
        self.assertEqual(resultset.total, 1)

        gq = GeoDistanceFilter("pin.location", [70, 40], "200km")
        q = FilteredQuery(MatchAllQuery(), gq)
        resultset = self.conn.search(query=q, indices=["test-mindex"])
        self.assertEqual(resultset.total, 1)

    def test_GeoBoundingBoxFilter(self):
        gq = GeoBoundingBoxFilter("pin.location", location_tl={"lat" : 40.717, "lon" : 70.99}, location_br={"lat" : 40.03, "lon" : 72.0})
        q = FilteredQuery(MatchAllQuery(), gq)
        resultset = self.conn.search(query=q, indices=["test-mindex"])
        self.assertEqual(resultset.total, 1)

        gq = GeoBoundingBoxFilter("pin.location", [70.99, 40.717], [74.1, 40.03])
        q = FilteredQuery(MatchAllQuery(), gq)
        result2 = self.conn.search(query=q, indices=["test-mindex"])
        self.assertEqual(result2.total, 1)
#        del result['took']
#        del result2['took']
#        self.assertEqual(result, result2)

    def test_GeoPolygonFilter(self):
        gq = GeoPolygonFilter("pin.location", [{"lat" : 50, "lon" :-30},
                                                {"lat" : 30, "lon" :-80},
                                                {"lat" : 80, "lon" :-90}]
                                                )
        q = FilteredQuery(MatchAllQuery(), gq)
        resultset = self.conn.search(query=q, indices=["test-mindex"])
        self.assertEqual(resultset.total, 1)

        gq = GeoPolygonFilter("pin.location", [[ -30, 50],
                                              [ -80, 30],
                                              [ -90, 80]]
                                                )
        q = FilteredQuery(MatchAllQuery(), gq)
        resultset = self.conn.search(query=q, indices=["test-mindex"])
        self.assertEqual(resultset.total, 1)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_highlight
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from pyes.tests import ESTestCase
from pyes.query import Search, QueryStringQuery, HighLighter

class QuerySearchTestCase(ESTestCase):
    def setUp(self):
        super(QuerySearchTestCase, self).setUp()
        mapping = {u'parsedtext': {'boost': 1.0,
                                   'index': 'analyzed',
                                   'store': 'yes',
                                   'type': u'string',
                                   "term_vector": "with_positions_offsets"},
                   u'name': {'boost': 1.0,
                             'index': 'analyzed',
                             'store': 'yes',
                             'type': u'string',
                             "term_vector": "with_positions_offsets"},
                   u'title': {'boost': 1.0,
                              'index': 'analyzed',
                              'store': 'yes',
                              'type': u'string',
                              "term_vector": "with_positions_offsets"},
                   u'pos': {'store': 'yes',
                            'type': u'integer'},
                   u'uuid': {'boost': 1.0,
                             'index': 'not_analyzed',
                             'store': 'yes',
                             'type': u'string'}}
        self.conn.indices.create_index(self.index_name)
        self.conn.indices.put_mapping(self.document_type, {'properties': mapping}, self.index_name)
        self.conn.index({"name": "Joe Tester", "parsedtext": "Joe Testere nice guy", "uuid": "11111", "position": 1},
            self.index_name, self.document_type, 1)
        self.conn.index({"name": "Bill Baloney", "parsedtext": "Joe Testere nice guy", "uuid": "22222", "position": 2},
            self.index_name, self.document_type, 2)
        self.conn.index({"parsedtext": "Joe Testere nice guy", "uuid": "22222", "position": 2}, self.index_name,
            self.document_type, 2)
        self.conn.indices.refresh(self.index_name)

    def test_QueryHighlight(self):
        q = Search(QueryStringQuery("joe"))
        q.add_highlight("parsedtext")
        q.add_highlight("name")
        resultset = self.conn.search(q, indices=self.index_name)
        self.assertEqual(resultset.total, 2)
        self.assertNotEqual(resultset[0]._meta.highlight, None)

        self.assertEqual(resultset[0]._meta.highlight[u"parsedtext"][0].strip(),
            u'<em>Joe</em> Testere nice guy')

    def test_QueryHighlightWithHighLighter(self):
        h = HighLighter(['<b>'], ['</b>'])
        q = Search(QueryStringQuery("joe"), highlight=h)
        q.add_highlight("parsedtext")
        q.add_highlight("name")
        resultset = self.conn.search(q, indices=self.index_name)
        self.assertEqual(resultset.total, 2)
        self.assertNotEqual(resultset[0]._meta.highlight, None)

        self.assertEqual(resultset[0]._meta.highlight[u"parsedtext"][0].strip(),
            u'<b>Joe</b> Testere nice guy')

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_indexing
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from pyes.tests import ESTestCase

from pyes.query import TermQuery
from pyes.exceptions import (IndexAlreadyExistsException,
                          VersionConflictEngineException, DocumentAlreadyExistsException)
from time import sleep

class IndexingTestCase(ESTestCase):
    def setUp(self):
        super(IndexingTestCase, self).setUp()
        self.conn.indices.delete_index_if_exists(self.index_name)
        self.conn.indices.delete_index_if_exists("test-index2")
        self.conn.indices.delete_index_if_exists("another-index")
        self.conn.indices.create_index(self.index_name)
        self.conn.indices.create_index("test-index2")

    def tearDown(self):
        self.conn.indices.delete_index_if_exists(self.index_name)
        self.conn.indices.delete_index_if_exists("test-index2")
        self.conn.indices.delete_index_if_exists("another-index")

    def testExists(self):
        self.assertTrue(self.conn.indices.exists_index(self.index_name))
        self.assertFalse(self.conn.indices.exists_index("test-index5"))

    # def testCollectInfo(self):
    #     """
    #     Testing collecting server info
    #     """
    #     self.conn.collect_info()
    #     result = self.conn.info
    #     self.assertTrue('server' in result.keys())
    #     self.assertTrue('aliases' in result.keys())
    #     self.assertTrue("name" in result['server'].keys())
    #     self.assertTrue('version' in result['server'].keys())

    def testIndexingWithID(self):
        """
        Testing an indexing given an ID
        """
        result = self.conn.index({"name": "Joe Tester"}, self.index_name, self.document_type, 1)
        self.assertResultContains(result, {
            '_type': 'test-type',
            '_id': '1', 'ok': True,
            '_index': 'test-index'})

    def testIndexingWithoutID(self):
        """Testing an indexing given without ID"""
        result = self.conn.index({"name": "Joe Tester"}, self.index_name, self.document_type)
        self.assertResultContains(result, {
            '_type': 'test-type',
            'ok': True,
            '_index': 'test-index'})
        # should have an id of some value assigned.
        self.assertTrue('_id' in result.keys() and result['_id'])

    def testExplicitIndexCreate(self):
        """Creazione indice"""
        self.conn.indices.delete_index("test-index2")
        result = self.conn.indices.create_index("test-index2")
        self.assertResultContains(result, {'acknowledged': True, 'ok': True})

    def testDeleteByID(self):
        self.conn.index({"name": "Joe Tester"}, self.index_name, self.document_type, 1)
        self.conn.indices.refresh(self.index_name)
        result = self.conn.delete(self.index_name, self.document_type, 1)
        self.assertResultContains(result, {
            '_type': 'test-type',
            '_id': '1', 'ok': True,
            '_index': 'test-index'})

    def testDeleteByIDWithEncoding(self):
        self.conn.index({"name": "Joe Tester"}, self.index_name, self.document_type, "http://hello/?#'there")
        self.conn.indices.refresh(self.index_name)
        result = self.conn.delete(self.index_name, self.document_type, "http://hello/?#'there")
        self.assertResultContains(result, {
            '_type': 'test-type',
            '_id': 'http://hello/?#\'there',
            'ok': True,
            '_index': 'test-index'})

    def testDeleteIndex(self):
        self.conn.indices.create_index("another-index")
        result = self.conn.indices.delete_index("another-index")
        self.assertResultContains(result, {'acknowledged': True, 'ok': True})

    def testCannotCreateExistingIndex(self):
        self.conn.indices.create_index("another-index")
        self.assertRaises(IndexAlreadyExistsException, self.conn.indices.create_index, "another-index")
        self.conn.indices.delete_index("another-index")

    def testPutMapping(self):
        result = self.conn.indices.put_mapping(self.document_type,
                {self.document_type: {"properties": {"name": {"type": "string", "store": "yes"}}}},
            indices=self.index_name)
        self.assertResultContains(result, {'acknowledged': True, 'ok': True})

    def testIndexStatus(self):
        self.conn.indices.create_index("another-index")
        result = self.conn.indices.status(["another-index"])
        self.conn.indices.delete_index("another-index")
        self.assertTrue('indices' in result.keys())
        self.assertResultContains(result, {'ok': True})

    def testIndexFlush(self):
        self.conn.indices.create_index("another-index")
        result = self.conn.indices.flush(["another-index"])
        self.conn.indices.delete_index("another-index")
        self.assertResultContains(result, {'ok': True})

    def testIndexRefresh(self):
        self.conn.indices.create_index("another-index")
        result = self.conn.indices.refresh(["another-index"])
        self.conn.indices.delete_index("another-index")
        self.assertResultContains(result, {'ok': True})

    def testIndexOptimize(self):
        self.conn.indices.create_index("another-index")
        result = self.conn.indices.optimize(["another-index"])
        self.conn.indices.delete_index("another-index")
        self.assertResultContains(result, {'ok': True})

    def testUpdate(self):
        # Use these query strings for all, so we test that it works on all the calls
        querystring_args = {"routing": 1}

        self.conn.index({"name": "Joe Tester", "sex": "male"},
            self.index_name, self.document_type, 1, querystring_args=querystring_args)
        self.conn.indices.refresh(self.index_name)
        self.conn.update(self.index_name, self.document_type, 1, document={"name": "Joe The Tester", "age": 23}, querystring_args=querystring_args)
        self.conn.indices.refresh(self.index_name)
        result = self.conn.get(self.index_name, self.document_type, 1, **querystring_args)
        self.assertResultContains(result, {"name": "Joe The Tester", "sex": "male", "age": 23})
        self.assertResultContains(result._meta,
                {"index": "test-index", "type": "test-type", "id": "1"})

        # Test bulk update
        self.conn.update(self.index_name, self.document_type, 1, document={"name": "Christian The Hacker", "age": 24},
                         querystring_args=querystring_args, bulk=True)
        self.conn.indices.refresh(self.index_name)
        result = self.conn.get(self.index_name, self.document_type, 1, **querystring_args)
        self.assertResultContains(result, {"name": "Christian The Hacker", "sex": "male", "age": 24})
        self.assertResultContains(result._meta,
                {"index": "test-index", "type": "test-type", "id": "1"})

    def testUpdateUsingFunc(self):
        def update_list_values(current, extra):
            for k, v in extra.items():
                if isinstance(current.get(k), list):
                    current[k].extend(v)
                else:
                    current[k] = v

        self.conn.index({"name": "Joe Tester", "age": 23, "skills": ["QA"]},
            self.index_name, self.document_type, 1)
        self.conn.indices.refresh(self.index_name)
        self.conn.update_by_function({"age": 24, "skills": ["cooking"]}, self.index_name,
            self.document_type, 1, update_func=update_list_values)
        self.conn.indices.refresh(self.index_name)
        result = self.conn.get(self.index_name, self.document_type, 1)
        self.assertResultContains(result, {"name": "Joe Tester", "age": 24,
                                           "skills": ["QA", "cooking"]})
        self.assertResultContains(result._meta,
                {"index": "test-index", "type": "test-type", "id": "1"})

    def testGetByID(self):
        self.conn.index({"name": "Joe Tester"}, self.index_name, self.document_type, 1)
        self.conn.index({"name": "Bill Baloney"}, self.index_name, self.document_type, 2)
        self.conn.indices.refresh(self.index_name)
        result = self.conn.get(self.index_name, self.document_type, 1)
        self.assertResultContains(result, {"name": "Joe Tester"})
        self.assertResultContains(result._meta, {"index": "test-index",
                                                 "type": "test-type", "id": "1"})
    def testExists(self):
        self.conn.index({"name": "Joe Tester"}, self.index_name, self.document_type, 1)
        self.conn.index({"name": "Bill Baloney"}, self.index_name, self.document_type, "http://example.com")
        self.conn.indices.refresh(self.index_name)
        self.assertTrue(self.conn.exists(self.index_name, self.document_type, 1))
        self.assertTrue(self.conn.exists(self.index_name, self.document_type, "http://example.com"))

    def testMultiGet(self):
        self.conn.index({"name": "Joe Tester"}, self.index_name, self.document_type, 1)
        self.conn.index({"name": "Bill Baloney"}, self.index_name, self.document_type, 2)
        self.conn.indices.refresh(self.index_name)
        results = self.conn.mget(["1", "2"], self.index_name, self.document_type)
        self.assertEqual(len(results), 2)

    def testGetCountBySearch(self):
        self.conn.index({"name": "Joe Tester"}, self.index_name, self.document_type, 1)
        self.conn.index({"name": "Bill Baloney"}, self.index_name, self.document_type, 2)
        self.conn.indices.refresh(self.index_name)
        q = TermQuery("name", "joe")
        result = self.conn.count(q, indices=self.index_name)
        self.assertResultContains(result, {'count': 1})


    #    def testSearchByField(self):
    #        resultset = self.conn.search("name:joe")
    #        self.assertResultContains(result, {'hits': {'hits': [{'_type': 'test-type', '_id': '1', '_source': {'name': 'Joe Tester'}, '_index': 'test-index'}], 'total': 1}})

    #    def testTermsByField(self):
    #        result = self.conn.terms(['name'])
    #        self.assertResultContains(result, {'docs': {'max_doc': 2, 'num_docs': 2, 'deleted_docs': 0}, 'fields': {'name': {'terms': [{'term': 'baloney', 'doc_freq': 1}, {'term': 'bill', 'doc_freq': 1}, {'term': 'joe', 'doc_freq': 1}, {'term': 'tester', 'doc_freq': 1}]}}})
    #
    #    def testTermsByIndex(self):
    #        result = self.conn.terms(['name'], indices=['test-index'])
    #        self.assertResultContains(result, {'docs': {'max_doc': 2, 'num_docs': 2, 'deleted_docs': 0}, 'fields': {'name': {'terms': [{'term': 'baloney', 'doc_freq': 1}, {'term': 'bill', 'doc_freq': 1}, {'term': 'joe', 'doc_freq': 1}, {'term': 'tester', 'doc_freq': 1}]}}})
    #
    #    def testTermsMinFreq(self):
    #        result = self.conn.terms(['name'], min_freq=2)
    #        self.assertResultContains(result, {'docs': {'max_doc': 2, 'num_docs': 2, 'deleted_docs': 0}, 'fields': {'name': {'terms': []}}})

    def testMLT(self):
        self.conn.index({"name": "Joe Test"}, self.index_name, self.document_type, 1)
        self.conn.index({"name": "Joe Tester"}, self.index_name, self.document_type, 2)
        self.conn.index({"name": "Joe did the test"}, self.index_name, self.document_type, 3)
        self.conn.indices.refresh(self.index_name)
        sleep(0.5)
        result = self.conn.morelikethis(self.index_name, self.document_type, 1, ['name'], min_term_freq=1,
            min_doc_freq=1)
        del result[u'took']
        self.assertResultContains(result, {u'_shards': {u'successful': 5, u'failed': 0, u'total': 5}})
        self.assertTrue(u'hits' in result)
        self.assertResultContains(result["hits"], {"hits": [
                {"_score": 0.2169777, "_type": "test-type", "_id": "3", "_source": {"name": "Joe did the test"},
                 "_index": "test-index"},
                {"_score": 0.19178301, "_type": "test-type", "_id": "2", "_source": {"name": "Joe Tester"},
                 "_index": "test-index"},
        ], "total": 2, "max_score": 0.2169777})

        # fails because arrays don't work. fucking annoying.
        '''
        self.assertEqual(2, result['hits']['total'])
        self.assertEqual(0.19178301, result['hits']['max_score'])
        self.assertResultContains({'wtf':result['hits']['hits']}, {'wtf':[
            {u'_score': 0.19178301, u'_type': u'test-type', u'_id': u'3', u'_source': {u'name': u'Joe Tested'}, u'_index': u'test-index'},
            {u'_score': 0.19178301, u'_type': u'test-type', u'_id': u'2', u'_source': {u'name': u'Joe Tester'}, u'_index': u'test-index'},
            ]})
        '''

    def testVersion(self):
        self.conn.index({"name": "Joe Test"}, self.index_name, self.document_type, 1, force_insert=True)
        self.assertRaises(DocumentAlreadyExistsException, self.conn.index,
            {"name": "Joe Test2"}, self.index_name, self.document_type, 1, force_insert=True)
        self.conn.index({"name": "Joe Test"}, self.index_name, self.document_type, 1, version=1)
        self.conn.index({"name": "Joe Test"}, self.index_name, self.document_type, 1, version=2)
        self.assertRaises(VersionConflictEngineException, self.conn.index,
            {"name": "Joe Test2"}, self.index_name, self.document_type, 1, version=2)
        item = self.conn.get(self.index_name, self.document_type, 1)
        self.assertEqual(item._meta.version, 3)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_index_stats
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from pyes.tests import ESTestCase

class IndexStatsTestCase(ESTestCase):
    def setUp(self):
        super(IndexStatsTestCase, self).setUp()
        mapping = {u'parsedtext': {'boost': 1.0,
                                   'index': 'analyzed',
                                   'store': 'yes',
                                   'type': u'string',
                                   "term_vector": "with_positions_offsets"},
                   u'name': {'boost': 1.0,
                             'index': 'analyzed',
                             'store': 'yes',
                             'type': u'string',
                             "term_vector": "with_positions_offsets"},
                   u'title': {'boost': 1.0,
                              'index': 'analyzed',
                              'store': 'yes',
                              'type': u'string',
                              "term_vector": "with_positions_offsets"},
                   u'pos': {'store': 'yes',
                            'type': u'integer'},
                   u'uuid': {'boost': 1.0,
                             'index': 'not_analyzed',
                             'store': 'yes',
                             'type': u'string'}}
        self.conn.indices.create_index(self.index_name)
        self.conn.indices.put_mapping(self.document_type, {'properties': mapping}, self.index_name)
        self.conn.indices.put_mapping("test-type2", {"_parent": {"type": self.document_type}}, self.index_name)
        self.conn.index({"name": "Joe Tester", "parsedtext": "Joe Testere nice guy", "uuid": "11111", "position": 1},
            self.index_name, self.document_type, 1)
        self.conn.index({"name": "data1", "value": "value1"}, self.index_name, "test-type2", 1, parent=1)
        self.conn.index({"name": "Bill Baloney", "parsedtext": "Bill Testere nice guy", "uuid": "22222", "position": 2},
            self.index_name, self.document_type, 2)
        self.conn.index({"name": "data2", "value": "value2"}, self.index_name, "test-type2", 2, parent=2)
        self.conn.index({"name": "Bill Clinton", "parsedtext": """Bill is not
                nice guy""", "uuid": "33333", "position": 3}, self.index_name, self.document_type, 3)

        self.conn.default_indices = self.index_name

        self.conn.indices.refresh()

    def test_all_indices(self):
        result = self.conn.indices.stats()
        self.assertEqual(5, result._all.total.docs.count)

    def test_select_indices(self):
        result = self.conn.indices.stats(self.index_name)
        self.assertEqual(5, result._all.total.docs.count)

    def test_optimize(self):
        result = self.conn.indices.optimize(indices=self.index_name, wait_for_merge=True, max_num_segments=1)
        self.assertEqual(result.ok, True)
        self.assertEqual(result._shards["failed"], 0)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_mapping_parser
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from pyes.tests import ESTestCase
from pyes import json, ES
from pyes.mappings import Mapper

class MapperTestCase(ESTestCase):
    def test_parser(self):
        self.datamap = json.loads(self.get_datafile("map.json"), cls=ES.decoder)
        _ = Mapper(self.datamap)

        #mapping = self.conn.indices.get_mapping()
        #self.dump(mapping)

########NEW FILE########
__FILENAME__ = test_multifield
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from pyes.tests import ESTestCase
from pyes.query import TermQuery

class MultifieldTestCase(ESTestCase):
    def setUp(self):
        super(MultifieldTestCase, self).setUp()
        mapping = {u'parsedtext': {'boost': 1.0,
                                   'index': 'analyzed',
                                   'store': 'yes',
                                   'type': u'string',
                                   "term_vector": "with_positions_offsets"},
                   u'title': {'boost': 1.0,
                              'index': 'analyzed',
                              'store': 'yes',
                              'type': u'string',
                              "term_vector": "with_positions_offsets"},
                   u'name': {"type": "multi_field",
                             "fields": {
                                 u'name': {
                                     u'boost': 1.0,
                                     u'index': u'analyzed',
                                     u'omit_norms': False,
                                     u'omit_term_freq_and_positions': False,
                                     u'store': u'yes',
                                     "term_vector": "with_positions_offsets",
                                     u'type': u'string'},
                                 u'untouched': {u'boost': 1.0,
                                                u'index': u'not_analyzed',
                                                u'omit_norms': False,
                                                u'omit_term_freq_and_positions': False,
                                                u'store': u'yes',
                                                "term_vector": "no",
                                                u'type': u'string'}

                             }

                   },

                   u'pos': {'store': 'yes',
                            'type': u'integer'},
                   u'uuid': {'boost': 1.0,
                             'index': 'not_analyzed',
                             'store': 'yes',
                             'type': u'string'}}
        self.conn.indices.create_index(self.index_name)
        self.conn.indices.put_mapping(self.document_type, {'properties': mapping}, self.index_name)
        self.conn.index({"name": "Joe Tester", "parsedtext": "Joe Testere nice guy", "uuid": "11111", "position": 1},
            self.index_name, self.document_type, 1)
        self.conn.index({"name": "Bill Baloney", "parsedtext": "Joe Testere nice guy", "uuid": "22222", "position": 2},
            self.index_name, self.document_type, 2)
        self.conn.index({"value": "Joe Tester"}, self.index_name, self.document_type)
        self.conn.index({"value": 123343543536}, self.index_name, self.document_type)
        self.conn.index({"value": True}, self.index_name, self.document_type)
        self.conn.index({"value": 43.32}, self.index_name, self.document_type)
        #self.conn.index({"value": datetime.now()}, self.index_name, self.document_type)
        self.conn.indices.refresh(self.index_name)

    def test_TermQuery(self):
        q = TermQuery("name", "joe")
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 1)

        q = TermQuery("name", "joe", 3)
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 1)

        q = TermQuery("name", "joe", "3")
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 1)

        q = TermQuery("value", 43.32)
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 1)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_multisearch
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import six
import io
import unittest
from pyes.tests import ESTestCase
from pyes.es import json
from pyes.query import *
from pyes.filters import TermFilter, ANDFilter, ORFilter, RangeFilter, RawFilter, IdsFilter, MatchAllFilter, NotFilter
from pyes.utils import ESRangeOp

if six.PY2:
    class UnicodeWriter(io.StringIO):
        def write(self, ss, *args, **kwargs):
            super(UnicodeWriter, self).write(unicode(ss), *args, **kwargs)
else:
    class UnicodeWriter(io.BytesIO):
        def write(self, ss, *args, **kwargs):
            super(UnicodeWriter, self).write(ss, *args, **kwargs)


class MultiSearchTestCase(ESTestCase):
    def setUp(self):
        super(MultiSearchTestCase, self).setUp()
        mapping = {u'name': {'boost': 1.0,
                             'index': 'analyzed',
                             'store': 'yes',
                             'type': u'string',
                             "term_vector": "with_positions_offsets"},
                   u'title': {'boost': 1.0,
                              'index': 'analyzed',
                              'store': 'yes',
                              'type': u'string',
                              "term_vector": "with_positions_offsets"}}
        self.conn.indices.create_index(self.index_name)
        self.conn.indices.put_mapping(self.document_type, {'properties': mapping}, self.index_name)
        self.conn.index({"name": "Joe Tester", "title": "Joe Testere nice guy"},
            self.index_name, self.document_type, 1)
        self.conn.index({"name": "Bill Baloney", "title": "Bill Testere nice guy"},
            self.index_name, self.document_type, 2)
        self.conn.index({"name": "Bill Clinton", "title": """Bill is not
                nice guy"""}, self.index_name, self.document_type, 3)

        #self.conn.default_indices = self.index_name

        self.curl_writer = UnicodeWriter()
        self.conn.dump_curl = self.curl_writer

        self.conn.indices.refresh()

    def _compute_num_requests(self):
        self.curl_writer.flush()
        self.curl_writer.seek(0)

        return len(self.curl_writer.read().decode("utf8").split('\n'))

    def test_TermQuery_simple_multi(self):
        """Compare multi search with simple single query."""
        # make sure single search returns something
        q = TermQuery("name", "joe")
        resultset_single = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset_single.total, 1)

        # now check that multi query returns the same results
        resultset_multi = self.conn.search_multi([q], indices_list=[self.index_name])
        # perform the search
        resultset_multi._do_search()

        self.assertTrue(resultset_multi.valid)
        self.assertEqual(resultset_multi[0].total, 1)
        self.assertDictEqual(resultset_multi[0][0], resultset_single[0])

    def test_TermQuery_double_multi(self):
        """Perform two multi searches."""
        q1 = TermQuery("name", "joe")
        q2 = TermQuery("name", "clinton")

        resultset_single1 = self.conn.search(query=q1, indices=self.index_name)
        resultset_single2 = self.conn.search(query=q2, indices=self.index_name)
        self.assertEqual(resultset_single1.total, 1)
        self.assertEqual(resultset_single2.total, 1)

        # now check that multi query returns the same results
        resultset_multi = self.conn.search_multi([q1, q2],
                                                 indices_list=[self.index_name] * 2)
        resultset_multi._do_search()

        self.assertTrue(resultset_multi.valid)
        self.assertEqual(resultset_multi[0].total, 1)
        self.assertEqual(resultset_multi[1].total, 1)
        self.assertDictEqual(resultset_multi[0][0], resultset_single1[0])
        self.assertDictEqual(resultset_multi[1][0], resultset_single2[0])

    def test_size_multi(self):
        """Make sure that 'size' parameter works correctly."""
        q = TermQuery("name", "bill")
        resultset_single = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset_single.total, 2)

        s = Search(query=q, size=1)
        resultset_multi = self.conn.search_multi([s], indices_list=[self.index_name])
        resultset_multi._do_search()

        num_curl_requests = self._compute_num_requests()

        self.assertTrue(resultset_multi.valid)
        self.assertEqual(len(resultset_multi[0].hits), 1)
        self.assertIn(resultset_multi[0][0], resultset_single)

        # no curl requests should have been triggered when doing
        # resultset_multi[0][0]
        self.assertEqual(num_curl_requests,
                         self._compute_num_requests())

        # make sure that getting more than 'size' elements triggers
        # an ES request
        self.assertIn(resultset_multi[0][1], resultset_single)
        self.assertLess(num_curl_requests-1,
                        self._compute_num_requests())

    def test_start_multi(self):
        """Make sure that 'start' parameter works correctly."""
        q = TermQuery("name", "bill")
        resultset_single = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset_single.total, 2)

        s = Search(query=q, start=1)
        resultset_multi = self.conn.search_multi([s], indices_list=[self.index_name])
        resultset_multi._do_search()

        self.assertTrue(resultset_multi.valid)
        self.assertEqual(len(resultset_multi[0].hits), 1)
        self.assertIn(resultset_multi[0][0], resultset_single)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_nested
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from pyes.tests import ESTestCase
from pyes.filters import TermFilter, NestedFilter
from pyes.query import FilteredQuery, MatchAllQuery, BoolQuery, TermQuery

class NestedSearchTestCase(ESTestCase):
    def setUp(self):
        super(NestedSearchTestCase, self).setUp()

        mapping = {
            'nested1': {
                'type': 'nested'
            }
        }
        self.conn.indices.create_index(self.index_name)
        self.conn.indices.put_mapping(self.document_type, {'properties': mapping}, self.index_name)
        self.conn.index({"field1": "value1",
                         "nested1": [{"n_field1": "n_value1_1",
                                      "n_field2": "n_value2_1"},
                                 {"n_field1": "n_value1_2",
                                  "n_field2": "n_value2_2"}]},
            self.index_name, self.document_type, 1)
        self.conn.index({"field1": "value1",
                         "nested1": [{"n_field1": "n_value1_1",
                                      "n_field2": "n_value2_2"},
                                 {"n_field1": "n_value1_2",
                                  "n_field2": "n_value2_1"}]},
            self.index_name, self.document_type, 2)
        self.conn.indices.refresh(self.index_name)

    def test_nested_filter(self):
        q = FilteredQuery(MatchAllQuery(),
            TermFilter('_all', 'n_value1_1'))
        resultset = self.conn.search(query=q, indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 2)

        q = FilteredQuery(MatchAllQuery(),
            TermFilter('nested1.n_field1', 'n_value1_1'))
        resultset = self.conn.search(query=q, indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 0)

        q = FilteredQuery(MatchAllQuery(),
            TermFilter('nested1.n_field1', 'n_value1_1'))
        resultset = self.conn.search(query=q, indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 0)

        q = FilteredQuery(MatchAllQuery(),
            NestedFilter('nested1',
                BoolQuery(must=[TermQuery('nested1.n_field1', 'n_value1_1')])))
        resultset = self.conn.search(query=q, indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 2)

        q = FilteredQuery(MatchAllQuery(),
            NestedFilter('nested1',
                BoolQuery(must=[TermQuery('nested1.n_field1', 'n_value1_1'),
                                TermQuery('nested1.n_field2', 'n_value2_1')])))
        resultset = self.conn.search(query=q, indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 1)


if __name__ == "__main__":
    unittest.main()


########NEW FILE########
__FILENAME__ = test_percolator
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from pyes.tests import ESTestCase
from pyes.query import *
import unittest

class PercolatorTestCase(ESTestCase):
    def setUp(self):
        super(PercolatorTestCase, self).setUp()
        mapping = { u'parsedtext': {'boost': 1.0,
                         'index': 'analyzed',
                         'store': 'yes',
                         'type': u'string',
                         "term_vector" : "with_positions_offsets"},
                 u'name': {'boost': 1.0,
                            'index': 'analyzed',
                            'store': 'yes',
                            'type': u'string',
                            "term_vector" : "with_positions_offsets"},
                 u'title': {'boost': 1.0,
                            'index': 'analyzed',
                            'store': 'yes',
                            'type': u'string',
                            "term_vector" : "with_positions_offsets"},
                 u'pos': {'store': 'yes',
                            'type': u'integer'},
                 u'uuid': {'boost': 1.0,
                           'index': 'not_analyzed',
                           'store': 'yes',
                           'type': u'string'}}
        self.conn.indices.create_index(self.index_name)
        self.conn.indices.put_mapping(self.document_type, {'properties':mapping}, self.index_name)
        self.conn.create_percolator(
            'test-index',
            'test-perc1',
            QueryStringQuery(query='apple', search_fields='_all')
        )
        self.conn.create_percolator(
            'test-index',
            'test-perc2',
            QueryStringQuery(query='apple OR iphone', search_fields='_all')
        )
        self.conn.create_percolator(
            'test-index',
            'test-perc3',
            QueryStringQuery(query='apple AND iphone', search_fields='_all')
        )
        self.conn.indices.refresh(self.index_name)

    def test_percolator(self):
        results = self.conn.percolate('test-index', 'test-type', PercolatorQuery({'name': 'iphone'}))
        self.assertTrue('test-perc1' not in results['matches'])
        self.assertTrue('test-perc2' in results['matches'])
        self.assertTrue('test-perc3' not in results['matches'])

    def test_or(self):
        results = self.conn.percolate('test-index', 'test-type', PercolatorQuery({'name': 'apple'}))
        self.assertTrue('test-perc1' in results['matches'])
        self.assertTrue('test-perc2' in results['matches'])
        self.assertTrue('test-perc3' not in results['matches'])

    def test_and(self):
        results = self.conn.percolate('test-index', 'test-type', PercolatorQuery({'name': 'apple iphone'}))
        self.assertTrue('test-perc1' in results['matches'])
        self.assertTrue('test-perc2' in results['matches'])
        self.assertTrue('test-perc3' in results['matches'])

    def tearDown(self):
        self.conn.delete_percolator('test-index', 'test-perc1')
        self.conn.delete_percolator('test-index', 'test-perc2')
        self.conn.delete_percolator('test-index', 'test-perc3')
        super(PercolatorTestCase, self).tearDown()


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_queries
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from pyes.tests import ESTestCase
from pyes.es import json
from pyes.query import *
from pyes.filters import TermFilter, ANDFilter, ORFilter, RangeFilter, RawFilter, IdsFilter, MatchAllFilter, NotFilter
from pyes.utils import ESRangeOp

class QuerySearchTestCase(ESTestCase):
    def setUp(self):
        super(QuerySearchTestCase, self).setUp()
        mapping = {u'parsedtext': {'boost': 1.0,
                                   'index': 'analyzed',
                                   'store': 'yes',
                                   'type': u'string',
                                   "term_vector": "with_positions_offsets"},
                   u'name': {'boost': 1.0,
                             'index': 'analyzed',
                             'store': 'yes',
                             'type': u'string',
                             "term_vector": "with_positions_offsets"},
                   u'title': {'boost': 1.0,
                              'index': 'analyzed',
                              'store': 'yes',
                              'type': u'string',
                              "term_vector": "with_positions_offsets"},
                   u'pos': {'store': 'yes',
                            'type': u'integer'},
                   u'uuid': {'boost': 1.0,
                             'index': 'not_analyzed',
                             'store': 'yes',
                             'type': u'string'}}
        self.conn.indices.create_index(self.index_name)
        self.conn.indices.put_mapping(self.document_type, {'properties': mapping}, self.index_name)
        self.conn.indices.put_mapping("test-type2", {"_parent": {"type": self.document_type}}, self.index_name)
        self.conn.index({"name": "Joe Tester", "parsedtext": "Joe Testere nice guy", "uuid": "11111", "position": 1},
            self.index_name, self.document_type, 1)
        self.conn.index({"name": "data1", "value": "value1"}, self.index_name, "test-type2", 1, parent=1)
        self.conn.index({"name": "Bill Baloney", "parsedtext": "Bill Testere nice guy", "uuid": "22222", "position": 2},
            self.index_name, self.document_type, 2)
        self.conn.index({"name": "data2", "value": "value2"}, self.index_name, "test-type2", 2, parent=2)
        self.conn.index({"name": "Bill Clinton", "parsedtext": """Bill is not
                nice guy""", "uuid": "33333", "position": 3}, self.index_name, self.document_type, 3)

        self.conn.default_indices = self.index_name

        self.conn.indices.refresh()

    def test_RescoreQuery(self):
        q = FunctionScoreQuery(functions=[FunctionScoreQuery.ScriptScoreFunction(
            lang="mvel",
            script="doc.position.value"
        )])

        resultset = self.conn.search(query=q, indices=self.index_name, doc_types=self.document_type)
        original_results = [x for x in resultset]

        rescore_search = Search(query=q, rescore=RescoreQuery(q, query_weight=1, rescore_query_weight=-10).search(window_size=3))
        rescore_resultset = self.conn.search(query=rescore_search, indices=self.index_name, doc_types=self.document_type)
        rescore_results = [x for x in rescore_resultset]

        rescore_results.reverse()
        self.assertEqual(rescore_search.serialize()['rescore']['window_size'], 3)
        self.assertEqual(original_results, rescore_results)

    def test_TermQuery(self):
        q = TermQuery("name", "joe")
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 1)
        self.assertEqual(q, TermQuery("name", "joe"))
        self.assertNotEquals(q, TermQuery("name", "job"))

        q = TermQuery("name", "joe", 3)
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 1)
        self.assertEqual(q, TermQuery("name", "joe", 3))
        self.assertNotEquals(q, TermQuery("name", "joe", 4))

        q = TermQuery("name", "joe", "3")
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 1)
        self.assertEqual(q, TermQuery("name", "joe", "3"))
        self.assertNotEquals(q, TermQuery("name", "joe", "4"))

    def test_WildcardQuery(self):
        q = WildcardQuery("name", "jo*")
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 1)
        self.assertEqual(q, WildcardQuery("name", "jo*"))
        self.assertNotEquals(q, WildcardQuery("name", "bo*"))

        q = WildcardQuery("name", "jo*", 3)
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 1)
        self.assertEqual(q, WildcardQuery("name", "jo*", 3))
        self.assertNotEquals(q, WildcardQuery("name", "jo*", 4))

        q = WildcardQuery("name", "jo*", "3")
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 1)
        self.assertEqual(q, WildcardQuery("name", "jo*", "3"))
        self.assertNotEquals(q, WildcardQuery("name", "jo*", "4"))

    def test_PrefixQuery(self):
        q = PrefixQuery("name", "jo")
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 1)
        self.assertEqual(q, PrefixQuery("name", "jo"))
        self.assertNotEquals(q, PrefixQuery("name", "bo"))

        q = PrefixQuery("name", "jo", 3)
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 1)
        self.assertEqual(q, PrefixQuery("name", "jo", 3))
        self.assertNotEquals(q, PrefixQuery("name", "jo", 4))

        q = PrefixQuery("name", "jo", "3")
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 1)
        self.assertEqual(q, PrefixQuery("name", "jo", "3"))
        self.assertNotEquals(q, PrefixQuery("name", "jo", "4"))

    def test_SpanMultiQuery(self):
        clause1 = SpanMultiQuery(PrefixQuery("parsedtext", "bi"))
        clause2 = SpanMultiQuery(PrefixQuery("parsedtext", "ni"))
        clauses = [clause1, clause2]
        q = SpanNearQuery(clauses, 1)
        resultset = self.conn.search(query=q, indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 1)
        self.assertEqual(clause1, SpanMultiQuery(PrefixQuery("parsedtext", "bi")))
        self.assertNotEquals(clause1, clause2)

        clause1 = SpanMultiQuery(WildcardQuery("parsedtext", "bi*"))
        clause2 = SpanMultiQuery(WildcardQuery("parsedtext", "ni*"))
        clauses = [clause1, clause2]
        q = SpanNearQuery(clauses, 1)
        resultset = self.conn.search(query=q, indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 1)
        self.assertEqual(clause1, SpanMultiQuery(WildcardQuery("parsedtext", "bi*")))
        self.assertNotEquals(clause1, clause2)

        clause1 = SpanMultiQuery(PrefixQuery("parsedtext", "bi"))
        clause2 = SpanMultiQuery(WildcardQuery("parsedtext", "ni*"))
        clauses = [clause1, clause2]
        q = SpanNearQuery(clauses, 1)
        resultset = self.conn.search(query=q, indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 1)
        self.assertEqual(clause1, SpanMultiQuery(PrefixQuery("parsedtext", "bi")))
        self.assertNotEquals(clause1, clause2)

    def test_MatchAllQuery(self):
        q = MatchAllQuery()
        resultset = self.conn.search(query=q, indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 3)
        self.assertEqual(q, MatchAllQuery())

    def test_StringQuery(self):
        q = QueryStringQuery("joe AND test")
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 0)
        self.assertEqual(q, QueryStringQuery("joe AND test"))
        self.assertNotEquals(q, QueryStringQuery("moe AND test"))

        q = QueryStringQuery("joe OR test")
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 1)
        self.assertEqual(q, QueryStringQuery("joe OR test"))
        self.assertNotEquals(q, QueryStringQuery("moe OR test"))

        q1 = QueryStringQuery("joe")
        q2 = QueryStringQuery("test")
        q = BoolQuery(must=[q1, q2])
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 0)
        self.assertEqual(q, BoolQuery(must=[QueryStringQuery("joe"), QueryStringQuery("test")]))
        self.assertNotEquals(q, BoolQuery(must=[QueryStringQuery("moe"), QueryStringQuery("test")]))

        q = BoolQuery(should=[q1, q2])
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 1)
        self.assertEqual(q, BoolQuery(should=[QueryStringQuery("joe"), QueryStringQuery("test")]))
        self.assertNotEquals(q, BoolQuery(should=[QueryStringQuery("moe"), QueryStringQuery("test")]))

        q = QueryStringQuery("joe OR Testere OR guy OR pizza", minimum_should_match="100%")
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 0)

        q = QueryStringQuery("joe OR Testere OR guy OR pizza", minimum_should_match="80%")
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 1)

        q = QueryStringQuery("joe OR Testere OR guy OR pizza", minimum_should_match="50%")
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 2)

    def test_OR_AND_Filters(self):
        q1 = TermFilter("position", 1)
        q2 = TermFilter("position", 2)
        andq = ANDFilter([q1, q2])

        q = FilteredQuery(MatchAllQuery(), andq)
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 0)
        self.assertEqual(q, FilteredQuery(MatchAllQuery(),
            ANDFilter([TermFilter("position", 1), TermFilter("position", 2)])))
        self.assertNotEquals(q, FilteredQuery(MatchAllQuery(),
            ANDFilter([TermFilter("position", 1), TermFilter("position", 3)])))

        orq = ORFilter([q1, q2])
        q = FilteredQuery(MatchAllQuery(), orq)
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 2)
        self.assertEqual(q, FilteredQuery(MatchAllQuery(),
            ORFilter([TermFilter("position", 1), TermFilter("position", 2)])))
        self.assertNotEquals(q, FilteredQuery(MatchAllQuery(),
            ORFilter([TermFilter("position", 1), TermFilter("position", 3)])))


    def test_DisMaxQuery(self):
        q = DisMaxQuery(QueryStringQuery(default_field="name", query="+joe"))
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 1)
        self.assertEqual(q, DisMaxQuery(QueryStringQuery(default_field="name", query="+joe")))
        self.assertNotEquals(q, DisMaxQuery(QueryStringQuery(default_field="name", query="+job")))

    def test_FuzzyQuery(self):
        q = FuzzyQuery('name', 'data')
        resultset = self.conn.search(query=q, indices=self.index_name)

        self.assertEqual(resultset.total, 2)
        self.assertEqual(q, FuzzyQuery('name', 'data'))
        self.assertNotEquals(q, FuzzyQuery('name', 'data2'))

    def test_HasChildQuery(self):
        q = HasChildQuery(type="test-type2", query=TermQuery("name", "data1"))
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 1)
        self.assertEqual(q, HasChildQuery(type="test-type2", query=TermQuery("name", "data1")))
        self.assertNotEquals(q, HasChildQuery(type="test-type2", query=TermQuery("name", "data2")))

    def test_RegexTermQuery(self):
        # Don't run this test, because it depends on the RegexTermQuery
        # feature which is not currently in elasticsearch trunk.
        return

    #        q = RegexTermQuery("name", "jo.")
    #        resultset = self.conn.search(query=q, indices=self.index_name)
    #        self.assertEqual(resultset.total, 1)
    #        # When this test is re-enabled, be sure to add equality and inequality tests (issue 128)

    def test_CustomScoreQueryMvel(self):
        q = FunctionScoreQuery(functions=[FunctionScoreQuery.ScriptScoreFunction(
            lang="mvel",
            script="_score*(5+doc.position.value)"
        )])
        self.assertEqual(q,
            FunctionScoreQuery(functions=[FunctionScoreQuery.ScriptScoreFunction(
                lang="mvel",
                script="_score*(5+doc.position.value)"
            )]))
        self.assertNotEqual(q,
            FunctionScoreQuery(functions=[FunctionScoreQuery.ScriptScoreFunction(
                lang="mvel",
                script="_score*(6+doc.position.value)"
            )]))
        resultset = self.conn.search(query=q, indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 3)
        self.assertEqual(resultset[0]._meta.score, 8.0)
        self.assertEqual(resultset[1]._meta.score, 7.0)
        self.assertEqual(resultset.max_score, 8.0)

    def test_CustomScoreQueryJS(self):
        q = FunctionScoreQuery(functions=[FunctionScoreQuery.ScriptScoreFunction(
            lang="js",
            script="parseFloat(_score*(5+doc.position.value))"
        )])
        resultset = self.conn.search(query=q, indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 3)
        self.assertEqual(resultset[0]._meta.score, 8.0)
        self.assertEqual(resultset[1]._meta.score, 7.0)
        self.assertEqual(resultset.max_score, 8.0)

    def test_CustomScoreQueryPython(self):
        q = FunctionScoreQuery(functions=[FunctionScoreQuery.ScriptScoreFunction(
            lang="python",
            script="_score*(5+doc['position'].value)"
        )])
        resultset = self.conn.search(query=q, indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 3)
        self.assertEqual(resultset[0]._meta.score, 8.0)
        self.assertEqual(resultset[1]._meta.score, 7.0)
        self.assertEqual(resultset.max_score, 8.0)

    def test_Search_stats(self):
        no_stats_group = Search(TermQuery("foo", "bar"))
        one_stats_group = Search(TermQuery("foo", "bar"), stats="hello")
        many_stats_groups = Search(TermQuery("foo", "bar"), stats=["hello", "there", "test"])

        self.assertEqual(no_stats_group.stats, None)
        self.assertEqual(one_stats_group.stats, "hello")
        self.assertEqual(many_stats_groups.stats, ["hello", "there", "test"])

        self.assertEqual(no_stats_group.serialize(),
                {"query": {"term": {"foo": "bar"}}})
        self.assertEqual(one_stats_group.serialize(),
                {"query": {"term": {"foo": "bar"}}, "stats": "hello"})
        self.assertEqual(many_stats_groups.serialize(),
                {"query": {"term": {"foo": "bar"}}, "stats": ["hello", "there", "test"]})

    def test_Search_equality(self):
        self.assertEqual(Search(),
            Search())
        self.assertNotEquals(Search(),
            Search(query=TermQuery("h", "ello")))
        self.assertEqual(Search(query=TermQuery("h", "ello")),
            Search(query=TermQuery("h", "ello")))
        self.assertNotEquals(Search(query=TermQuery("h", "ello")),
            Search(query=TermQuery("j", "ello")))
        self.assertEqual(Search(filter=TermFilter("h", "ello")),
            Search(filter=TermFilter("h", "ello")))
        self.assertNotEquals(Search(filter=TermFilter("h", "ello")),
            Search(filter=TermFilter("j", "ello")))
        self.assertEqual(Search(query=TermQuery("h", "ello"), filter=TermFilter("h", "ello")),
            Search(query=TermQuery("h", "ello"), filter=TermFilter("h", "ello")))
        self.assertNotEquals(Search(query=TermQuery("h", "ello"), filter=TermFilter("h", "ello")),
            Search(query=TermQuery("j", "ello"), filter=TermFilter("j", "ello")))

    def test_ESRange_equality(self):
        self.assertEqual(RangeQuery(),
            RangeQuery())
        self.assertEqual(RangeQuery(ESRange("foo", 1, 2)),
            RangeQuery(ESRange("foo", 1, 2)))
        self.assertNotEquals(RangeQuery(ESRange("foo", 1, 2)),
            RangeQuery(ESRange("bar", 1, 2)))
        self.assertEqual(RangeFilter(),
            RangeFilter())
        self.assertEqual(RangeFilter(ESRange("foo", 1, 2)),
            RangeFilter(ESRange("foo", 1, 2)))
        self.assertNotEquals(RangeFilter(ESRange("foo", 1, 2)),
            RangeFilter(ESRange("bar", 1, 2)))
        self.assertEqual(ESRange("foo"),
            ESRange("foo"))
        self.assertNotEquals(ESRange("foo"),
            ESRange("bar"))
        self.assertEqual(ESRange("foo", 1),
            ESRange("foo", 1))
        self.assertNotEquals(ESRange("foo", 1),
            ESRange("foo", 2))
        self.assertEqual(ESRange("foo", 1, 2),
            ESRange("foo", 1, 2))
        self.assertNotEquals(ESRange("foo", 1, 2),
            ESRange("foo", 1, 3))
        self.assertEqual(ESRange("foo", 1, 2, True, False),
            ESRange("foo", 1, 2, True, False))
        self.assertNotEquals(ESRange("foo", 1, 2, True, False),
            ESRange("foo", 1, 2, False, True))
        self.assertEqual(ESRangeOp("foo", "gt", 5),
            ESRangeOp("foo", "gt", 5))
        self.assertEqual(ESRangeOp("bar", "lt", 6),
            ESRangeOp("bar", "lt", 6))
        self.assertEqual(ESRangeOp("bar", "gt", 3, "lt", 6),
            ESRangeOp("bar", "lt", 6, "gt", 3))

    def test_RawFilter_dict(self):
        filter_ = dict(ids=dict(type="my_type", values=["1", "4", "100"]))
        self.assertEqual(RawFilter(filter_), RawFilter(filter_))
        self.assertEqual(RawFilter(filter_).serialize(), filter_)
        self.assertEqual(RawFilter(filter_).serialize(),
            IdsFilter(type="my_type", values=["1", "4", "100"]).serialize())

    def test_RawFilter_string(self):
        filter_ = dict(ids=dict(type="my_type", values=["1", "4", "100"]))
        filter_string = json.dumps(filter_)
        self.assertEqual(RawFilter(filter_string), RawFilter(filter_string))
        self.assertEqual(RawFilter(filter_string), RawFilter(filter_))
        self.assertEqual(RawFilter(filter_string).serialize(), filter_)
        self.assertEqual(RawFilter(filter_string).serialize(),
            IdsFilter(type="my_type", values=["1", "4", "100"]).serialize())

    def test_RawFilter_search(self):
        filter_ = dict(ids=dict(type="my_type", values=["1", "4", "100"]))
        filter_string = json.dumps(filter_)

        self.assertEqual(Search(filter=RawFilter(filter_)).serialize(),
            dict(filter=filter_))
        self.assertEqual(Search(filter=RawFilter(filter_string)).serialize(),
            dict(filter=filter_))

    # def test_CustomFiltersScoreQuery_ScoreMode(self):
    #     self.assertEqual(CustomFiltersScoreQuery.ScoreMode.FIRST, "first")
    #     self.assertEqual(CustomFiltersScoreQuery.ScoreMode.MIN, "min")
    #     self.assertEqual(CustomFiltersScoreQuery.ScoreMode.MAX, "max")
    #     self.assertEqual(CustomFiltersScoreQuery.ScoreMode.TOTAL, "total")
    #     self.assertEqual(CustomFiltersScoreQuery.ScoreMode.AVG, "avg")
    #     self.assertEqual(CustomFiltersScoreQuery.ScoreMode.MULTIPLY, "multiply")
    #
    # def test_CustomFiltersScoreQuery_Filter(self):
    #     with self.assertRaises(ValueError) as cm:
    #         CustomFiltersScoreQuery.Filter(MatchAllFilter())
    #     self.assertEqual(cm.exception.message, "Exactly one of boost and script must be specified")
    #
    #     with self.assertRaises(ValueError) as cm:
    #         CustomFiltersScoreQuery.Filter(MatchAllFilter(), 5.0, "someScript")
    #     self.assertEqual(cm.exception.message, "Exactly one of boost and script must be specified")
    #
    #     filter1 = CustomFiltersScoreQuery.Filter(MatchAllFilter(), 5.0)
    #     self.assertEqual(filter1, CustomFiltersScoreQuery.Filter(MatchAllFilter(), 5.0))
    #     self.assertEqual(filter1.filter_, MatchAllFilter())
    #     self.assertEqual(filter1.boost, 5.0)
    #     self.assertIsNone(filter1.script)
    #     self.assertEqual(filter1.serialize(), {'filter': {'match_all': {}}, 'boost': 5.0})
    #
    #     filter2 = CustomFiltersScoreQuery.Filter(NotFilter(MatchAllFilter()), script="hello")
    #     self.assertEqual(filter2, CustomFiltersScoreQuery.Filter(NotFilter(MatchAllFilter()), script="hello"))
    #     self.assertEqual(filter2.filter_, NotFilter(MatchAllFilter()))
    #     self.assertEqual(filter2.script, "hello")
    #     self.assertIsNone(filter2.boost)
    #     self.assertEqual(filter2.serialize(), {'filter': {'not': {'filter': {'match_all': {}}}}, 'script': 'hello'})

    def test_CustomFiltersScoreQuery(self):
        script1 = "max(1,2)"
        script2 = "min(1,2)"

        filter1 = FunctionScoreQuery.BoostFunction(boost_factor=5.0, filter=MatchAllFilter())

        filter2 = FunctionScoreQuery.ScriptScoreFunction(script=script1, filter=NotFilter(MatchAllFilter()))
        filter3 = FunctionScoreQuery.ScriptScoreFunction(script=script2, filter=NotFilter(MatchAllFilter()))

        q1 = MatchAllQuery()
        q2 = TermQuery("foo", "bar")

        cfsq1 = FunctionScoreQuery(query=q1, functions=[filter1, filter2])
        self.assertEqual(cfsq1, FunctionScoreQuery(query=q1, functions=[filter1, filter2]))
        self.assertEqual(cfsq1.query, q1)
        self.assertEqual(cfsq1.functions, [filter1, filter2])
        self.assertIsNone(cfsq1.score_mode)
        self.assertIsNone(cfsq1.params)
        # self.assertEqual(cfsq1.serialize(),
        #         {'custom_filters_score': {
        #         'query': {'match_all': {}},
        #         'filters': [
        #             filter1.serialize(),
        #             filter2.serialize()
        #         ]}})
        #
        # params1 = {"foo": "bar"}
        # cfsq2 = FunctionScoreQuery(query=q2, functions=[filter1, filter2, filter3],
        #     score_mode=FunctionScoreQuery.ScoreMode.MAX,
        #     params=params1)
        # self.assertEqual(cfsq2,
        #     FunctionScoreQuery(query=q2, functions=[filter1, filter2, filter3],
        #         score_mode=FunctionScoreQuery.ScoreMode.MAX,
        #         params=params1))
        # self.assertEqual(cfsq2.query, q2)
        # self.assertEqual(cfsq2.filters, [filter1, filter2, filter3])
        # self.assertEqual(cfsq2.score_mode, FunctionScoreQuery.ScoreMode.MAX)
        # self.assertEqual(cfsq2.params, params1)
        # self.assertEqual(cfsq2.serialize(),
        #         {'custom_filters_score': {
        #         'query': {'term': {'foo': 'bar'}},
        #         'filters': [
        #             filter1.serialize(),
        #             filter2.serialize(),
        #             filter3.serialize()
        #         ],
        #         'score_mode': 'max',
        #         'lang': 'mvel',
        #         'params': {"foo": "bar"}}})

    def test_Search_fields(self):
        q = MatchAllQuery()
        all_fields = ["name", "parsedtext", "uuid", "position"]
        resultset = self.conn.search(query=Search(q), indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 3)
        for result in resultset:
            for field in all_fields:
                self.assertTrue(result.get(field))
        resultset = self.conn.search(query=Search(q,fields=[]), indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 3)
        for result in resultset:
            for field in all_fields:
                self.assertTrue(not result.get(field))
        resultset = self.conn.search(query=Search(q,fields=['name','position']), indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 3)
        for result in resultset:
            for field in ['parsedtext','uuid']:
                self.assertTrue(not result.get(field))
            for field in ['name','position']:
                self.assertTrue( result.get(field))

    def test_MatchQuery(self):
        q = MatchQuery("_all", "nice")
        serialized = q.serialize()
        self.assertTrue("match" in serialized)
        self.assertTrue("_all" in serialized["match"])
        self.assertTrue(serialized["match"]["_all"]["query"], "nice")

        resultset = self.conn.search(query=q, indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 3)

        q = MatchQuery("_all", "Baloney Testere pizza", operator="and")
        resultset = self.conn.search(query=q, indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 0)

        q = MatchQuery("_all", "Baloney Testere pizza", operator="or", minimum_should_match="70%")
        resultset = self.conn.search(query=q, indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 1)

        q = MatchQuery("parsedtext", "Bill guy", type="phrase", slop=2)
        resultset = self.conn.search(query=q, indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 1)

        q = MatchQuery("parsedtext", "guy Bill", type="phrase", slop=2)
        resultset = self.conn.search(query=q, indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 0)

        q = MatchQuery("name", "Tester")
        resultset = self.conn.search(query=q, indices=self.index_name, doc_types=[self.document_type])
        self.assertEqual(resultset.total, 1)

    # def test_CustomBoostFactorQuery(self):
    #     q = CustomBoostFactorQuery(query=TermQuery("name", "joe"),
    #         boost_factor=1.0)
    #
    #     resultset = self.conn.search(query=q, indices=self.index_name)
    #
    #     self.assertEqual(resultset.total, 1)
    #     score = resultset.hits[0]['_score']
    #
    #     q = CustomBoostFactorQuery(query=TermQuery("name", "joe"),
    #         boost_factor=2.0)
    #     resultset = self.conn.search(query=q, indices=self.index_name)
    #
    #     score_boosted = resultset.hits[0]['_score']
    #     self.assertEqual(score*2, score_boosted)

    def test_FunctionScoreQuery(self):

        functions = [FunctionScoreQuery.BoostFunction(boost_factor=20, filter=TermFilter('uuid', '33333'))]
        q = FunctionScoreQuery(functions=functions, score_mode=FunctionScoreQuery.ScoreModes.AVG)
        resultset = self.conn.search(query=q, indices=self.index_name)

        self.assertEqual(resultset.hits[0]['_score'], 20)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_queryset
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pyes.tests import ESTestCase
from pyes.queryset import DoesNotExist, generate_model
from datetime import datetime

class QuerySetTests(ESTestCase):
    def setUp(self):
        super(QuerySetTests, self).setUp()
        self.init_default_index()
        self.init_default_data()
        self.conn.indices.refresh(self.index_name)

    def init_default_data(self):
        """
        Init default index data
        """
        self.conn.index({"name": ["Joe Tester", "J. Tester"], "parsedtext": "Joe Testere nice guy", "uuid": "11111",
                         "position": 1, "date":datetime(2012, 9, 1, 12, 34, 33)},
                                       self.index_name, self.document_type, 1)
        self.conn.index({"name": "data1", "value": "value1"}, self.index_name, "test-type2", 1, parent=1)
        self.conn.index({"name": "Bill Baloney",
                         "parsedtext": "Bill Testere nice guy",
                         "uuid": "22222", "position": 2, "date":datetime(2012, 8, 1, 10, 34, 33)},
                                                                                                                       self.index_name
                                                                                                                       ,
                                                                                                                       self.document_type
                                                                                                                       ,
                                                                                                                       2)
        self.conn.index({"name": "data2", "value": "value2"}, self.index_name, "test-type2", 2, parent=2)
        self.conn.index({"name": ["Bill Clinton", "B. Clinton"], "parsedtext": """Bill is not
                nice guy""", "uuid": "33333", "position": 3, "date":datetime(2012, 6, 2, 11, 34, 3)}, self.index_name, self.document_type, 3)

    def test_get(self):
        model = generate_model(self.index_name, self.document_type)
        queryset = model.objects
        self.assertEqual(len(queryset), 3)
        queryset = model.objects.all()
        self.assertEqual(len(queryset), 3)
        queryset = model.objects.filter(uuid="33333")
        self.assertEqual(len(queryset), 1)
        queryset = model.objects.filter(position=1)
        self.assertEqual(len(queryset), 1)
        queryset = model.objects.filter(position=1).filter(position=3)
        self.assertEqual(len(queryset), 0)
        queryset = model.objects.filter(uuid="33333", position=3)
        self.assertEqual(len(queryset), 1)
        queryset = model.objects.filter(position__gt=1, position__lt=3)
        self.assertEqual(len(queryset), 1)
        self.assertEqual(queryset.count(), 1)
        self.assertEqual([r.position for r in queryset], [2])
        queryset = model.objects.exclude(position=1)
        self.assertEqual(len(queryset), 2)
        self.assertEqual(queryset.count(), 2)
        self.assertEqual([r.position for r in queryset], [2, 3])
        queryset = model.objects.exclude(position__in=[1, 2])
        self.assertEqual(len(queryset), 1)
        self.assertEqual(queryset.count(), 1)
        self.assertEqual([r.position for r in queryset], [3])

        item = model.objects.get(position=1)
        self.assertEqual(item.position, 1)
        self.assertRaises(DoesNotExist, model.objects.get, position=0)

        queryset = model.objects.order_by("position")
        self.assertEqual(queryset[0].position, 1)
        queryset = model.objects.order_by("-position")
        self.assertEqual(queryset[0].position, 3)

        item, created = model.objects.get_or_create(position=1, defaults={"name": "nasty"})
        self.assertEqual(created, False)
        self.assertEqual(item.position, 1)
        self.assertEqual(item.get_meta().id, "1")
        item, created = model.objects.get_or_create(position=10, defaults={"name": "nasty"})
        self.assertEqual(created, True)
        self.assertEqual(item.position, 10)

        values = list(model.objects.values("uuid", "position"))
        self.assertEqual(len(values), 3)
        self.assertEqual([dict(t) for t in values], [{u'position': 1, u'uuid': u'11111'},
                {u'position': 2, u'uuid': u'22222'},
                {u'position': 3, u'uuid': u'33333'}])

        values = list(model.objects.values_list("uuid", flat=True))
        self.assertEqual(len(values), 3)
        self.assertEqual(values, [u'11111', u'22222',u'33333'])
        values = model.objects.dates("date", kind="year")
        self.assertEqual(len(values), 1)
        self.assertEqual(values, [datetime(2012, 1, 1, 0, 0)])

        facets = model.objects.facet("uuid").size(0).facets
        uuid_facets=facets["uuid"]
        self.assertEqual(uuid_facets["total"], 3)
        self.assertEqual(uuid_facets["terms"][0]["count"], 1)

if __name__ == "__main__":
    import unittest
    unittest.main()

########NEW FILE########
__FILENAME__ = test_resultset
# -*- coding: utf-8 -*-
from pyes.tests import ESTestCase
from pyes.query import MatchAllQuery, Search

class ResultsetTestCase(ESTestCase):
    def setUp(self):
        super(ResultsetTestCase, self).setUp()
        self.init_default_index()

        for i in range(1000):
            self.conn.index(
                    {"name": "Joe Tester%d" % i, "parsedtext": "Joe Testere nice guy", "uuid": "11111", "position": i},
                self.index_name, self.document_type, i, bulk=True)
        self.conn.indices.refresh(self.index_name)

    def test_iterator(self):
        resultset = self.conn.search(Search(MatchAllQuery(), size=20), self.index_name, self.document_type)
        self.assertEqual(len([p for p in resultset]), 20)
        resultset = self.conn.search(Search(MatchAllQuery(), size=10), self.index_name, self.document_type)
        self.assertEqual(len([p for p in resultset[:10]]), 10)
        self.assertEqual(resultset[10].uuid, "11111")
        self.assertEqual(resultset.total, 1000)

    def test_iterator_offset(self):
        # Query for a block of 10, starting at position 10:
        #
        resultset = self.conn.search(Search(MatchAllQuery(), start=10, size=10, sort={'position': {'order': 'asc'}}),
            self.index_name, self.document_type,
            start=10, size=10)

        self.assertGreater(resultset.took, 0.0)
        # Ensure that there are 1000 results:
        #
        self.assertEqual(len(resultset), 1000)

        # Now check that we actually have records 10-19, rather than 0-9:
        #
        position = 0
        for r in resultset:
            self.assertEqual(r.position, position + 10)
            position += 1

        range = resultset[0:1]
        self.assertEqual(len(range), 1)
        self.assertEqual(range[0].position, 10)
        range = resultset[1:1]
        self.assertEqual(len(range), 0)

        range = resultset[9:10]
        self.assertEqual(len(range), 1)
        self.assertEqual(range[0].position, 19)


if __name__ == "__main__":
    import unittest
    unittest.main()
########NEW FILE########
__FILENAME__ = test_rivers
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from pyes.tests import ESTestCase
from pyes.rivers import CouchDBRiver, RabbitMQRiver, TwitterRiver

class RiversTestCase(ESTestCase):
    def setUp(self):
        super(RiversTestCase, self).setUp()

    def testCreateCouchDBRiver(self):
        """
        Testing deleting a river
        """
        test_river = CouchDBRiver(index_name='text_index', index_type='test_type')
        result = self.conn.create_river(test_river, river_name='test_index')
        self.assertResultContains(result, {'ok': True})

    def testDeleteCouchDBRiver(self):
        """
        Testing deleting a river
        """
        test_river = CouchDBRiver(index_name='text_index', index_type='test_type')
        result = self.conn.delete_river(test_river, river_name='test_index')
        self.assertResultContains(result, {'ok': True})

    def testCreateRabbitMQRiver(self):
        """
        Testing deleting a river
        """
        test_river = RabbitMQRiver(index_name='text_index', index_type='test_type')
        result = self.conn.create_river(test_river, river_name='test_index')
        self.assertResultContains(result, {'ok': True})

    def testDeleteRabbitMQRiver(self):
        """
        Delete RabbitMQ river
        """
        test_river = RabbitMQRiver(index_name='text_index', index_type='test_type')
        result = self.conn.create_river(test_river, river_name='test_index')
        result = self.conn.delete_river(test_river, river_name='test_index')
        self.assertResultContains(result, {'ok': True})

    def testCreateTwitterRiver(self):
        """
        Create twitter river
        """
        test_river = TwitterRiver('test', 'test', index_name='text_index', index_type='status')
        result = self.conn.create_river(test_river, river_name='test_index')
        self.assertResultContains(result, {'ok': True})

    def testDeleteTwitterRiver(self):
        """
        Delete Twitter river
        """
        test_river = TwitterRiver('test', 'test', index_name='text_index', index_type='status')
        result = self.conn.create_river(test_river, river_name='test_index')
        result = self.conn.delete_river(test_river, river_name='test_index')
        self.assertResultContains(result, {'ok': True})

    def testCreateTwitterRiverOAuth(self):
        test_river = TwitterRiver('test', 'test', index_name='text_index', index_type='test_type',
                                 consumer_key="aaa",
                                 consumer_secret="aaa",
                                 access_token="aaa",
                                 access_token_secret="aaa",
                                 )
        result = self.conn.create_river(test_river, river_name='test_index')
        self.assertResultContains(result, {'ok': True})


if __name__ == "__main__":
    unittest.main()


########NEW FILE########
__FILENAME__ = test_scriptfields
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from pyes import scriptfields

class ScriptFieldsTest(unittest.TestCase):
    def test_scriptfieldserror_imported(self):
        self.assertTrue(hasattr(scriptfields, 'ScriptFieldsError'))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_serialize
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from pyes.tests import ESTestCase
from pyes.query import TermQuery, RangeQuery
from pyes.utils import ESRange
from datetime import datetime

class SerializationTestCase(ESTestCase):
    def setUp(self):
        super(SerializationTestCase, self).setUp()
        mapping = {u'parsedtext': {'boost': 1.0,
                                   'index': 'analyzed',
                                   'store': 'yes',
                                   'type': u'string',
                                   "term_vector": "with_positions_offsets"},
                   u'name': {'boost': 1.0,
                             'index': 'analyzed',
                             'store': 'yes',
                             'type': u'string',
                             "term_vector": "with_positions_offsets"},
                   u'title': {'boost': 1.0,
                              'index': 'analyzed',
                              'store': 'yes',
                              'type': u'string',
                              "term_vector": "with_positions_offsets"},
                   u'pos': {'store': 'yes',
                            'type': u'integer'},
                   u'inserted': {'store': 'yes',
                                 'type': u'date'},
                   u'uuid': {'boost': 1.0,
                             'index': 'not_analyzed',
                             'store': 'yes',
                             'type': u'string'}}
        self.conn.indices.create_index(self.index_name)
        self.conn.indices.put_mapping(self.document_type, {'properties': mapping}, self.index_name)
        self.conn.index({"name": "Joe Tester", "parsedtext": "Joe Testere nice guy", "uuid": "11111", "position": 1,
                         'inserted': datetime(2010, 10, 22, 12, 12, 12)}, self.index_name, self.document_type, 1)
        self.conn.index({"name": "Bill Baloney", "parsedtext": "Joe Testere nice guy", "uuid": "22222", "position": 2,
                         'inserted': datetime(2010, 10, 22, 12, 12, 10)}, self.index_name, self.document_type, 2)
        self.conn.index({"name": "Jesus H Christ", "parsedtext": "Bible guy", "uuid": "33333", "position": 3,
                         'inserted': datetime(1, 1, 1, 0, 0, 0)}, self.index_name, self.document_type, 3)
        self.conn.indices.refresh(self.index_name)

    def test_TermQuery(self):
        q = TermQuery("name", "joe")
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 1)
        hit = resultset[0]
        self.assertEqual(hit.inserted, datetime(2010, 10, 22, 12, 12, 12))

    def test_DateBefore1900(self):
        q = RangeQuery(ESRange("inserted", datetime(1, 1, 1), datetime(2, 1, 1)))
        resultset = self.conn.search(query=q, indices=self.index_name)
        self.assertEqual(resultset.total, 1)
        hit = resultset[0]
        self.assertEqual(hit.inserted, datetime(1, 1, 1, 0, 0, 0))


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_sort
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from pyes.tests import ESTestCase
from pyes.sort import SortFactory, SortOrder, GeoSortOrder, ScriptSortOrder
from pyes.query import Search, MatchAllQuery


class SortFactoryTestCase(unittest.TestCase):

    def test_sort_factory_empty(self):
        sort_factory = SortFactory()
        self.assertEqual(sort_factory.serialize(), None)

    def test_sort_factory_with_sort_order(self):
        sort_factory = SortFactory()
        sort_factory.add(SortOrder('foo'))
        self.assertEqual(sort_factory.serialize(), [{'foo': {}}])

    def test_sort_factory_reset(self):
        sort_factory = SortFactory()
        sort_factory.add(SortOrder('foo'))
        self.assertEqual(len(sort_factory.sort_orders), 1)
        sort_factory.reset()
        self.assertEqual(len(sort_factory.sort_orders), 0)


class SortOrderTestCase(unittest.TestCase):

    def test_sort_order_serialization(self):
        sort_order = SortOrder('foo')
        self.assertEqual(sort_order.serialize(), {'foo': {}})

    def test_sort_order_serialization_with_order(self):
        sort_order = SortOrder('foo', 'asc')
        self.assertEqual(sort_order.serialize(), {'foo': {'order': 'asc'}})

    def test_sort_order_serialization_with_missing(self):
        sort_order = SortOrder('foo', missing='_last')
        self.assertEqual(sort_order.serialize(), {'foo': {'missing': '_last'}})

    def test_sort_order_serialization_with_nested_path(self):
        sort_order = SortOrder('foo', mode='avg', nested_path='bar')
        self.assertEqual(
            sort_order.serialize(),
            {'foo': {'nested_path': 'bar', 'mode': 'avg'}}
        )


class GeoSortOrderTestCase(unittest.TestCase):

    def test_geo_sort_order_serialization(self):
        sort_order = GeoSortOrder(field='foo', lat=1, lon=1)
        self.assertEqual(
            sort_order.serialize(),
            {'_geo_distance': {'foo': [1, 1]}}
        )

    def test_geo_sort_order_serialization_with_unit(self):
        sort_order = GeoSortOrder(field='foo', lat=1, lon=1, unit='km')
        self.assertEqual(
            sort_order.serialize(),
            {'_geo_distance': {'foo': [1, 1], 'unit': 'km'}}
        )

    def test_geo_sort_order_serialization_with_order(self):
        sort_order = GeoSortOrder(field='foo', lat=1, lon=1, order='desc')
        self.assertEqual(
            sort_order.serialize(),
            {'_geo_distance': {'foo': [1, 1], 'order': 'desc'}}
        )

    def test_geo_sort_order_serialization_geohash(self):
        sort_order = GeoSortOrder(field='foo', geohash='drm3btev3e86')
        self.assertEqual(
            sort_order.serialize(),
            {'_geo_distance': {'foo': 'drm3btev3e86'}}
        )


class ScriptSortOrderTestCase(unittest.TestCase):

    def test_script_sort_order_serialization(self):
        sort_order = ScriptSortOrder("doc[foo].value + 1", type='number')
        self.assertEqual(
            sort_order.serialize(),
            {'_script': {'script': "doc[foo].value + 1", 'type': 'number'}}
        )


class SortOrderESTestCase(ESTestCase):

    def setUp(self):
        super(SortOrderESTestCase, self).setUp()
        self.conn.indices.create_index(self.index_name)
        #my es config has disabled automatic mapping creation
        mapping = {
            self.document_type: {
                'properties': {
                    'location': {
                        'type': 'geo_point'
                    }
                }
            }
        }
        self.conn.indices.put_mapping(self.document_type, mapping)
        self.conn.index(
            {'foo': 1, 'location': {'lat': 1, 'lon': 1}},
            self.index_name,
            self.document_type,
            1
        )
        self.conn.index(
            {'foo': 2, 'location': {'lat': 2, 'lon': 2}},
            self.index_name,
            self.document_type,
            2
        )
        self.conn.index(
            {'foo': 3, 'location': {'lat': 3, 'lon': 3}},
            self.index_name,
            self.document_type,
            3
        )

        self.conn.indices.refresh(self.index_name)

    def test_sorting_by_foo(self):
        search = Search(MatchAllQuery())
        search.sort.add(SortOrder('foo', order='desc'))
        resultset = self.conn.search(
            search,
            indices=self.index_name,
            doc_types=[self.document_type]
        )
        ids = [doc['_id'] for doc in resultset.hits]
        self.assertEqual(ids, ['3', '2', '1'])

    def test_sorting_by_script(self):
        search = Search(MatchAllQuery())
        search.sort.add(ScriptSortOrder("1.0/doc['foo'].value", type='number'))
        resultset = self.conn.search(
            search,
            indices=self.index_name,
            doc_types=[self.document_type]
        )
        ids = [doc['_id'] for doc in resultset.hits]
        self.assertEqual(ids, ['3', '2', '1'])

    def test_sorting_by_geolocation(self):
        search = Search(MatchAllQuery())
        search.sort.add(GeoSortOrder(field='location', lat=1, lon=1))
        resultset = self.conn.search(
            search,
            indices=self.index_name,
            doc_types=[self.document_type]
        )
        ids = [doc['_id'] for doc in resultset.hits]
        self.assertEqual(ids, ['1', '2', '3'])

if __name__ == "__main__":
    import unittest
    unittest.main()
########NEW FILE########
__FILENAME__ = test_update
# -*- coding: utf-8 -*-
from pyes.tests import ESTestCase

class UpdateTestCase(ESTestCase):
    def setUp(self):
        super(UpdateTestCase, self).setUp()
        self.conn.indices.create_index(self.index_name)
        self.conn.index({"counter": 0}, self.index_name, self.document_type, 1)

    def testPartialUpdateWithoutParams(self):
        self.conn.partial_update(self.index_name, self.document_type, 1, "ctx._source.counter = 2")
        doc = self.conn.get(self.index_name, self.document_type, 1)
        self.assertEqual(doc["counter"], 2)

    def testPartialUpdateWithParams(self):
        self.conn.partial_update(self.index_name, self.document_type, 1, "ctx._source.counter = param1", params={"param1": 3})
        doc = self.conn.get(self.index_name, self.document_type, 1)
        self.assertEqual(doc["counter"], 3)

    def testPartialUpdateWithUpsert(self):
        self.conn.partial_update(self.index_name, self.document_type, 2, "ctx._source.counter += 1", upsert={"counter": 5})
        doc = self.conn.get(self.index_name, self.document_type, 2)
        self.assertEqual(doc["counter"], 5)

if __name__ == "__main__":
    import unittest
    unittest.main()

########NEW FILE########
__FILENAME__ = test_utils
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from pyes.tests import ESTestCase
from pyes.utils import clean_string, make_id
from pyes.es import ES

class UtilsTestCase(ESTestCase):
    def test_cleanstring(self):
        self.assertEqual(clean_string("senthil("), "senthil")
        self.assertEqual(clean_string("senthil&"), "senthil")
        self.assertEqual(clean_string("senthil-"), "senthil")
        self.assertEqual(clean_string("senthil:"), "senthil")

    def test_servers(self):
        geturls = lambda servers: [server.geturl() for server in servers]
        es = ES("127.0.0.1:9200")
        self.assertEqual(geturls(es.servers), ["http://127.0.0.1:9200"])
        es = ES("127.0.0.1:9500")
        self.assertEqual(geturls(es.servers), ["thrift://127.0.0.1:9500"])
        es = ES(("http", "127.0.0.1", 9400))
        self.assertEqual(geturls(es.servers), ["http://127.0.0.1:9400"])
        es = ES(("thrift", "127.0.0.1", 9100))
        self.assertEqual(geturls(es.servers), ["thrift://127.0.0.1:9100"])
        es = ES(["http://127.0.0.1:9100",
                 "127.0.0.1:9200",
                 ("thrift", "127.0.0.1", 9000),
                 "127.0.0.1:9500",
                 ])
        self.assertEqual(geturls(sorted(es.servers)),
                          ["http://127.0.0.1:9100",
                           "http://127.0.0.1:9200",
                           "thrift://127.0.0.1:9000",
                           "thrift://127.0.0.1:9500"])

    def test_make_id(self):
        self.assertEqual(make_id("prova"), "GJu7sAxfT7e7qa2ShfGT0Q")

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_warmers
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from pyes.tests import ESTestCase
import pyes

class WarmerTestCase(ESTestCase):

    def setUp(self):
        super(WarmerTestCase, self).setUp()
        self.conn.indices.create_index(self.index_name)
        self.conn.indices.refresh(self.index_name)

    def test_put_get_warmer(self):
        warmer1 = pyes.Search(pyes.MatchAllQuery())
        #ES fails if the index is empty
        self.conn.index({'a':1}, self.index_name, self.document_type)
        self.conn.indices.refresh(self.index_name)
        self.conn.put_warmer(indices=[self.index_name], name='w1', warmer=warmer1)
        result = self.conn.get_warmer(indices=[self.index_name], name='w1')
        expected = {
            self.index_name: {
                'warmers': {
                    'w1': {
                        'source': {
                            'query': {'match_all': {}}
                        },
                        'types': []
                    }
                }
            }
        }
        self.assertEqual(result, expected)

    def test_delete_warmer(self):
        warmer1 = pyes.Search(pyes.MatchAllQuery())
        self.conn.put_warmer(indices=[self.index_name], name='w1', warmer=warmer1)
        self.conn.delete_warmer(indices=[self.index_name], name='w1')
        self.assertRaises(
            pyes.exceptions.ElasticSearchException,
            self.conn.get_warmer,
            indices=[self.index_name],
            name='w1'
        )

if __name__ == "__main__":
    import unittest
    unittest.main()

########NEW FILE########
