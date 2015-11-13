__FILENAME__ = build_html
#!/usr/bin/env python

import os
import glob
import shutil

from conf import bib_dir, template_dir, html_dir, static_dir, pdf_dir
from options import get_config, mkdir_p
from build_template import bib_from_tmpl, html_from_tmpl, from_template

config = get_config()
mkdir_p(bib_dir)
for file in glob.glob(os.path.join(static_dir,'*.css')):
    shutil.copy(file, html_dir)
html_pdfs = os.path.join(html_dir, 'pdfs')
mkdir_p(html_pdfs)
for file in glob.glob(os.path.join(pdf_dir,'*.pdf')):
    shutil.copy(file, html_pdfs)

citation_key = config['proceedings']['citation_key'] # e.g. proc-scipy-2010

bib_from_tmpl('proceedings', config, citation_key)

proc_dict = dict(config.items() +
                {'pdf': 'pdfs/proceedings.pdf'}.items() +
                {'bibtex': 'bib/' + citation_key}.items())

for dest_fn in ['index', 'organization', 'students']:
    html_from_tmpl(dest_fn+'.html', proc_dict, dest_fn)

for article in config['toc']:
    art_dict = dict(config.items() +
                    {'article': article}.items() +
                    {'pdf': 'pdfs/'+article['paper_id']+'.pdf'}.items() +
                    {'bibtex': 'bib/'+article['paper_id']+'.bib'}.items())
    bib_from_tmpl('article', art_dict, article['paper_id'])
    html_from_tmpl('article.html',art_dict, article['paper_id'])

########NEW FILE########
__FILENAME__ = build_paper
#!/usr/bin/env python

import docutils.core as dc
import os.path
import sys
import re
import tempfile
import glob
import shutil

from writer import writer
from conf import papers_dir, output_dir
import options

header = r'''
.. role:: ref

.. role:: label

.. raw::  latex

  \InputIfFileExists{page_numbers.tex}{}{}
  \newcommand*{\docutilsroleref}{\ref}
  \newcommand*{\docutilsrolelabel}{\label}

.. |---| unicode:: U+2014  .. em dash, trimming surrounding whitespace
   :trim:

.. |--| unicode:: U+2013   .. en dash
   :trim:

'''


def rst2tex(in_path, out_path):

    options.mkdir_p(out_path)
    for file in glob.glob(os.path.join(in_path, '*')):
        shutil.copy(file, out_path)

    base_dir = os.path.dirname(__file__)
    scipy_status = os.path.join(base_dir, '_static/status.sty')
    shutil.copy(scipy_status, out_path)
    scipy_style = os.path.join(base_dir, '_static/scipy.sty')
    shutil.copy(scipy_style, out_path)
    preamble = r'''\usepackage{scipy}'''

    # Add the LaTeX commands required by Pygments to do syntax highlighting

    pygments = None

    try:
        import pygments
    except ImportError:
        import warnings
        warnings.warn(RuntimeWarning('Could not import Pygments. '
                                     'Syntax highlighting will fail.'))

    if pygments:
        from pygments.formatters import LatexFormatter
        from writer.sphinx_highlight import SphinxStyle

        preamble += LatexFormatter(style=SphinxStyle).get_style_defs()

    settings = {'documentclass': 'IEEEtran',
                'use_verbatim_when_possible': True,
                'use_latex_citations': True,
                'latex_preamble': preamble,
                'documentoptions': 'letterpaper,compsoc,twoside',
                'halt_level': 3,  # 2: warn; 3: error; 4: severe
                }

    try:
        rst, = glob.glob(os.path.join(in_path, '*.rst'))
    except ValueError:
        raise RuntimeError("Found more than one input .rst--not sure which "
                           "one to use.")

    content = header + open(rst, 'r').read()

    tex = dc.publish_string(source=content, writer=writer,
                            settings_overrides=settings)

    stats_file = os.path.join(out_path, 'paper_stats.json')
    d = options.cfg2dict(stats_file)
    d.update(writer.document.stats)
    options.dict2cfg(d, stats_file)

    tex_file = os.path.join(out_path, 'paper.tex')
    with open(tex_file, 'w') as f:
        f.write(tex)


def tex2pdf(out_path):

    import subprocess
    command_line = 'cd "%s" ' % out_path + \
                   ' ; pdflatex -halt-on-error paper.tex'

    # -- dummy tempfile is a hacky way to prevent pdflatex
    #    from asking for any missing files via stdin prompts,
    #    which mess up our build process.
    dummy = tempfile.TemporaryFile()
    run = subprocess.Popen(command_line, shell=True,
            stdin=dummy,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
    out, err = run.communicate()

    # -- returncode always 0, have to check output for error
    if "Fatal" not in out:
        # -- pdflatex has to run twice to actually work
        run = subprocess.Popen(command_line, shell=True,
                stdin=dummy,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        out, err = run.communicate()

    if "Fatal" in out or run.returncode:
        print "PDFLaTeX error output:"
        print "=" * 80
        print out
        print "=" * 80
        if err:
            print err
            print "=" * 80

    return out


def page_count(pdflatex_stdout, paper_dir):
    """
    Parse pdflatex output for paper count, and store in a .ini file.
    """
    if pdflatex_stdout is None:
        print "*** WARNING: PDFLaTeX failed to generate output."
        return

    regexp = re.compile('Output written on paper.pdf \((\d+) pages')
    cfgname = os.path.join(paper_dir, 'paper_stats.json')

    d = options.cfg2dict(cfgname)

    for line in pdflatex_stdout.splitlines():
        m = regexp.match(line)
        if m:
            pages = m.groups()[0]
            d.update({'pages': int(pages)})
            break

    options.dict2cfg(d, cfgname)


def build_paper(paper_id):
    out_path = os.path.join(output_dir, paper_id)
    in_path = os.path.join(papers_dir, paper_id)
    print "Building:", paper_id

    rst2tex(in_path, out_path)
    pdflatex_stdout = tex2pdf(out_path)
    page_count(pdflatex_stdout, out_path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Usage: build_paper.py paper_directory"
        sys.exit(-1)

    in_path = os.path.normpath(sys.argv[1])
    if not os.path.isdir(in_path):
        print("Cannot open directory: %s" % in_path)
        sys.exit(-1)

    paper_id = os.path.basename(in_path)
    build_paper(paper_id)

########NEW FILE########
__FILENAME__ = build_papers
#!/usr/bin/env python

import os
import sys
import shutil
import subprocess

import conf
import options
from build_paper import build_paper

output_dir = conf.output_dir
build_dir  = conf.build_dir
bib_dir    = conf.bib_dir
pdf_dir    = conf.pdf_dir
toc_conf   = conf.toc_conf
proc_conf  = conf.proc_conf
dirs       = conf.dirs


def paper_stats(paper_id, start):
    stats = options.cfg2dict(os.path.join(output_dir, paper_id, 'paper_stats.json'))

    # Write page number snippet to be included in the LaTeX output
    if 'pages' in stats:
        pages = stats['pages']
    else:
        pages = 1

    stop = start + pages - 1

    print '"%s" from p. %s to %s' % (paper_id, start, stop)

    with open(os.path.join(output_dir, paper_id, 'page_numbers.tex'), 'w') as f:
        f.write('\setcounter{page}{%s}' % start)

    # Build table of contents
    stats.update({'page': {'start': start,
                           'stop': stop}})
    stats.update({'paper_id': paper_id})

    return stats, stop

if __name__ == "__main__":

    start = 0
    toc_entries = []

    options.mkdir_p(pdf_dir)
    for paper_id in dirs:
        build_paper(paper_id)

        stats, start = paper_stats(paper_id, start + 1)
        toc_entries.append(stats)

        build_paper(paper_id)

        src_pdf = os.path.join(output_dir, paper_id, 'paper.pdf')
        dest_pdf = os.path.join(pdf_dir, paper_id+'.pdf')
        shutil.copy(src_pdf, dest_pdf)

        command_line = 'cd '+pdf_dir+' ; pdfannotextractor '+paper_id+'.pdf'
        run = subprocess.Popen(command_line, shell=True, stdout=subprocess.PIPE)
        out, err = run.communicate()

    toc = {'toc': toc_entries}
    options.dict2cfg(toc, toc_conf)

########NEW FILE########
__FILENAME__ = build_template
#!/usr/bin/env python

import os
import sys
import shlex, subprocess

import tempita
from conf import bib_dir, build_dir, template_dir, html_dir
from options import get_config

def _from_template(tmpl_basename, config):
    tmpl = os.path.join(template_dir, tmpl_basename + '.tmpl')
    template = tempita.HTMLTemplate(open(tmpl, 'r').read())
    return template.substitute(config)

def from_template(tmpl_basename, config, dest_fn):

    outfile = _from_template(tmpl_basename, config)
    extension = os.path.splitext(dest_fn)[1][1:]
    outname = os.path.join(build_dir, extension, dest_fn)

    with open(outname, mode='w') as f:
        f.write(outfile)

def bib_from_tmpl(bib_type, config, target):
    tmpl_basename = bib_type + '.bib'
    dest_path = os.path.join(bib_dir, target + '.bib')
    from_template(tmpl_basename, config, dest_path)
    command_line = 'recode -d u8..ltex ' + dest_path
    run = subprocess.Popen(command_line, shell=True, stdout=subprocess.PIPE)
    out, err = run.communicate()

def get_html_header(config):
    return _from_template('header.html', config)

def get_html_content(tmpl, config):
    return _from_template(tmpl, config)

def html_from_tmpl(src, config, target):

    header = get_html_header(config)
    content =  _from_template(src, config)

    outfile = header+content
    dest_fn = os.path.join(html_dir, target + '.html')
    extension = os.path.splitext(dest_fn)[1][1:]
    outname = os.path.join(build_dir, extension, dest_fn)
    with open(outname, mode='w') as f:
        f.write(outfile)

if __name__ == "__main__":

    if not len(sys.argv) == 2:
        print "Usage: build_template.py destination_name"
        sys.exit(-1)

    dest_fn = sys.argv[1]
    template_fn = os.path.join(template_dir, dest_fn+'.tmpl')

    if not os.path.exists(template_fn):
        print "Cannot find template."
        sys.exit(-1)

    config = get_config()
    from_template(dest_fn, config, dest_fn)

########NEW FILE########
__FILENAME__ = conf
import glob
import os

excludes = ['vanderwalt',]

work_dir      = os.path.dirname(__file__)
papers_dir    = os.path.join(work_dir,'../papers')
output_dir    = os.path.join(work_dir,'../output')
template_dir  = os.path.join(work_dir,'_templates')
static_dir    = os.path.join(work_dir,'_static')
css_file      = os.path.join(static_dir,'scipy-proc.css')
toc_list      = os.path.join(static_dir,'toc.txt')
build_dir     = os.path.join(work_dir,'_build')
pdf_dir       = os.path.join(build_dir, 'pdfs')
html_dir      = os.path.join(build_dir, 'html')
bib_dir       = os.path.join(html_dir, 'bib')
toc_conf      = os.path.join(build_dir, 'toc.json')
proc_conf     = os.path.join(work_dir,'../scipy_proc.json')

if os.path.isfile(toc_list):
    with open(toc_list) as f:
        dirs = f.read().splitlines()
else:
    dirs = sorted([os.path.basename(d)
                   for d in glob.glob('%s/*' % papers_dir)
                   if os.path.isdir(d) and not any(e in d for e in excludes)])

########NEW FILE########
__FILENAME__ = mail_authors
#!/usr/bin/env python

import _mailer as mailer

args = mailer.parse_args()
config = mailer.load_config('email.json')

for author in config['authors']:
    to = mailer.email_addr_from(author)
    mailer.send_template(config['sender'], to, args.template, config)

print "Mail for %d authors." % len(config['authors'])

########NEW FILE########
__FILENAME__ = mail_reviewers
#!/usr/bin/env python

import _mailer as mailer
import os
from conf import work_dir

args = mailer.parse_args()
config = mailer.load_config('email.json')


for reviewer_info in config['reviewers']:
    for p in reviewer_info['papers']:
        if not os.path.isdir(os.path.join(work_dir, '../papers/', p)):
            raise RuntimeError("Paper %s not found..refusing to generate emails." % p)


for reviewer_info in config['reviewers']:
    reviewer_config = config.copy()
    reviewer_config.update(reviewer_info)
    reviewer = reviewer_info['email']

    to = mailer.email_addr_from(reviewer_info)
    mailer.send_template(config['sender'], to + ', ' + config['cced'],
                         'reviewer-invite.txt', reviewer_config)


# Generate a summary of emails sent

paper_reviewers = {}
for reviewer_info in config['reviewers']:
    for paper in reviewer_info['papers']:
        d = paper_reviewers.setdefault(paper, [])
        d.append(reviewer_info['name'])

for paper in paper_reviewers:
    print "%s:" % paper
    for reviewer in paper_reviewers[paper]:
        print "->", reviewer
    print

print "Papers:", len(paper_reviewers)
print "Reviewers:", len(config['reviewers'])
print

########NEW FILE########
__FILENAME__ = _mailer
import argparse
import smtplib
import os
import getpass
from email.mime.text import MIMEText

import sys
sys.path.insert(0, '..')
from conf import work_dir
from options import cfg2dict
from build_template import _from_template


args = None
password = None


def parse_args():
    parser = argparse.ArgumentParser(description="Invite reviewers.")
    parser.add_argument('--send', action='store_true')
    parser.add_argument('--template', default=None)

    global args
    args = parser.parse_args()
    args.dry_run = not args.send

    if args.dry_run:
        print '*** This is a dry run.  Use --send to send emails.'

    return args


def load_config(conf_file):
    return cfg2dict(conf_file)


def get_password(sender):
    global password
    if not args.dry_run and not password:
        password = getpass.getpass(sender + "'s password:  ")


def email_addr_from(name_email):
    return '"%s" <%s>' % (name_email['name'], name_email['email'])


def send_template(sender, recipient, template, template_data,
                  smtp_server='smtp.gmail.com', smtp_port=587):
    if args.dry_run:
        print 'Dry run -> not sending mail to %s' % recipient
    else:
        get_password(sender['login'])
        print '-> %s' % recipient

    template_data['email'] = recipient
    message = _from_template('../mail/templates/' + template, template_data)

    if args.dry_run:
        print "=" * 80
        print message
        print "=" * 80

        return

    session = smtplib.SMTP(smtp_server, smtp_port)

    session.ehlo()
    session.starttls()
    session.ehlo
    session.login(sender['login'], password)

    session.sendmail(sender['name'], recipient, message)
    session.quit()

########NEW FILE########
__FILENAME__ = options
"""
Configuration utilities.
"""

__all__ = ['options']

import os.path
import json
import codecs

import conf
toc_conf   = conf.toc_conf
proc_conf  = conf.proc_conf

def get_config():
    config = cfg2dict(proc_conf)
    config.update(cfg2dict(toc_conf))
    return config

def cfg2dict(filename):
    """Return the content of a JSON config file as a dictionary.

    """
    if not os.path.exists(filename):
        print '*** Warning: %s does not exist.' % filename
        return {}

    return json.loads(codecs.open(filename, 'r', 'utf-8').read())

def dict2cfg(d, filename):
    """Write dictionary out to config file.

    """
    json.dump(d, codecs.open(filename, 'w', 'utf-8'), ensure_ascii=False)

def mkdir_p(dir):
    if os.path.isdir(dir):
        return
    os.makedirs(dir)

options = cfg2dict(proc_conf)

########NEW FILE########
__FILENAME__ = compat3
import sys

__all__ = ['b', 'basestring_', 'bytes', 'next', 'is_unicode']

if sys.version < "3":
    b = bytes = str
    basestring_ = basestring
else:

    def b(s):
        if isinstance(s, str):
            return s.encode('latin1')
        return bytes(s)
    basestring_ = (bytes, str)
    bytes = bytes
text = str

if sys.version < "3":

    def next(obj):
        return obj.next()
else:
    next = next

if sys.version < "3":

    def is_unicode(obj):
        return isinstance(obj, unicode)
else:

    def is_unicode(obj):
        return isinstance(obj, str)


def coerce_text(v):
    if not isinstance(v, basestring_):
        if sys.version < "3":
            attr = '__unicode__'
        else:
            attr = '__str__'
        if hasattr(v, attr):
            return unicode(v)
        else:
            return bytes(v)
    return v

########NEW FILE########
__FILENAME__ = _looper
"""
Helper for looping over sequences, particular in templates.

Often in a loop in a template it's handy to know what's next up,
previously up, if this is the first or last item in the sequence, etc.
These can be awkward to manage in a normal Python loop, but using the
looper you can get a better sense of the context.  Use like::

    >>> for loop, item in looper(['a', 'b', 'c']):
    ...     print loop.number, item
    ...     if not loop.last:
    ...         print '---'
    1 a
    ---
    2 b
    ---
    3 c

"""

import sys
from tempita.compat3 import basestring_

__all__ = ['looper']


class looper(object):
    """
    Helper for looping (particularly in templates)

    Use this like::

        for loop, item in looper(seq):
            if loop.first:
                ...
    """

    def __init__(self, seq):
        self.seq = seq

    def __iter__(self):
        return looper_iter(self.seq)

    def __repr__(self):
        return '<%s for %r>' % (
            self.__class__.__name__, self.seq)


class looper_iter(object):

    def __init__(self, seq):
        self.seq = list(seq)
        self.pos = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.pos >= len(self.seq):
            raise StopIteration
        result = loop_pos(self.seq, self.pos), self.seq[self.pos]
        self.pos += 1
        return result

    if sys.version < "3":
        next = __next__


class loop_pos(object):

    def __init__(self, seq, pos):
        self.seq = seq
        self.pos = pos

    def __repr__(self):
        return '<loop pos=%r at %r>' % (
            self.seq[self.pos], self.pos)

    def index(self):
        return self.pos
    index = property(index)

    def number(self):
        return self.pos + 1
    number = property(number)

    def item(self):
        return self.seq[self.pos]
    item = property(item)

    def __next__(self):
        try:
            return self.seq[self.pos + 1]
        except IndexError:
            return None
    __next__ = property(__next__)

    if sys.version < "3":
        next = __next__

    def previous(self):
        if self.pos == 0:
            return None
        return self.seq[self.pos - 1]
    previous = property(previous)

    def odd(self):
        return not self.pos % 2
    odd = property(odd)

    def even(self):
        return self.pos % 2
    even = property(even)

    def first(self):
        return self.pos == 0
    first = property(first)

    def last(self):
        return self.pos == len(self.seq) - 1
    last = property(last)

    def length(self):
        return len(self.seq)
    length = property(length)

    def first_group(self, getter=None):
        """
        Returns true if this item is the start of a new group,
        where groups mean that some attribute has changed.  The getter
        can be None (the item itself changes), an attribute name like
        ``'.attr'``, a function, or a dict key or list index.
        """
        if self.first:
            return True
        return self._compare_group(self.item, self.previous, getter)

    def last_group(self, getter=None):
        """
        Returns true if this item is the end of a new group,
        where groups mean that some attribute has changed.  The getter
        can be None (the item itself changes), an attribute name like
        ``'.attr'``, a function, or a dict key or list index.
        """
        if self.last:
            return True
        return self._compare_group(self.item, self.__next__, getter)

    def _compare_group(self, item, other, getter):
        if getter is None:
            return item != other
        elif (isinstance(getter, basestring_)
              and getter.startswith('.')):
            getter = getter[1:]
            if getter.endswith('()'):
                getter = getter[:-2]
                return getattr(item, getter)() != getattr(other, getter)()
            else:
                return getattr(item, getter) != getattr(other, getter)
        elif hasattr(getter, '__call__'):
            return getter(item) != getter(other)
        else:
            return item[getter] != other[getter]

########NEW FILE########
__FILENAME__ = code_block
# --- Code-block directive from Sphinx ---

from docutils import nodes
from docutils.parsers.rst import Directive, directives

class CodeBlock(Directive):
    """
    Directive for a code block with special highlighting or line numbering
    settings.
    """

    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        'linenos': directives.flag,
        'linenostart': directives.nonnegative_int,
    }

    def run(self):
        code = u'\n'.join(self.content)
        literal = nodes.literal_block(code, code)
        literal['language'] = self.arguments[0]
        literal['linenos'] = 'linenos' in self.options
        literal['linenostart'] = self.options.get('linenostart', 1)
        return [literal]

directives.register_directive('code-block', CodeBlock)

# --- End code-block directive from Sphinx ---

########NEW FILE########
__FILENAME__ = rstmath
# This code is from: http://pypi.python.org/pypi/rstex/

#!/usr/bin/python2
from docutils import utils, nodes
from docutils.core import publish_cmdline
from docutils.writers.latex2e import Writer, LaTeXTranslator
from docutils.parsers.rst import roles, Directive, directives


class InlineMath(nodes.Inline, nodes.TextElement):
    pass

class PartMath(nodes.Part, nodes.Element):
    pass

class PartLaTeX(nodes.Part, nodes.Element):
    pass

def mathEnv(math, label, type):
    if label:
        eqn_star = ''
    else:
        eqn_star = '*'

    if type in ("split", "gathered"):
        begin = "\\begin{equation%s}\n\\begin{%s}\n" % (type, eqn_star)
        end = "\\end{%s}\n\\end{equation%s}\n" % (type, eqn_star)
    else:
        begin = "\\begin{%s%s}\n" % (type, eqn_star)
        end = "\\end{%s%s}" % (type, eqn_star)
    if label:
        begin += "\\label{%s}\n" % label
    return begin + math + '\n' + end

def mathRole(role, rawtext, text, lineno, inliner, options={}, content=[]):
    latex = utils.unescape(text, restore_backslashes=True)
    return [InlineMath(latex=latex)], []

class MathDirective(Directive):
    has_content = True
    required_arguments = 0
    optional_arguments = 2
    final_argument_whitespace = True
    option_spec = {
        'type': directives.unchanged,
        'label': directives.unchanged,
    }
    def run(self):
        latex = '\n'.join(self.content)
        if self.arguments and self.arguments[0]:
            latex = self.arguments[0] + '\n\n' + latex
        node = PartMath()
        node['latex'] = latex
        node['label'] = self.options.get('label', None)
        node['type'] = self.options.get('type', "equation")
        ret = [node]
        return ret

class LaTeXDirective(Directive):
    has_content = True
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {
        'usepackage': directives.unchanged
    }
    def run(self):
        latex = '\n'.join(self.content)
        if self.arguments and self.arguments[0]:
            latex = self.arguments[0] + '\n\n' + latex
        node = PartLaTeX()
        node['latex'] = latex
        node['usepackage'] = self.options.get("usepackage", "").split(",")
        ret = [node]
        return ret


roles.register_local_role("math", mathRole)
directives.register_directive("math", MathDirective)
directives.register_directive("latex", LaTeXDirective)


########NEW FILE########
__FILENAME__ = sphinx_highlight
from pygments.style import Style
from pygments.styles.friendly import FriendlyStyle
from pygments.token import Generic, Comment, Number

class SphinxStyle(Style):
    """
    Like friendly, but a bit darker to enhance contrast on the green
    background.
    """

    background_color = '#eeffcc'
    default_style = ''

    styles = FriendlyStyle.styles
    styles.update({
        Generic.Output: '#333',
        Comment: 'italic #408090',
        Number: '#208050',
    })

########NEW FILE########
