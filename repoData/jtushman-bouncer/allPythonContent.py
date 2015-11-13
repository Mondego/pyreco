__FILENAME__ = constants
# Actions
MANAGE = 'manage'
READ = 'read'
UPDATE = 'update'
EDIT = 'edit'
CREATE = 'create'

# OLD SCHOOL
GET = 'get'
PUT = 'put'
PATCH = 'patch'
POST = 'post'
DELETE = 'delete'

# NEW SCHOOL
INDEX = 'index'
SHOW = 'show'
NEW = 'new'
CREATE = 'create'


# Special Target
ALL = 'all'
########NEW FILE########
__FILENAME__ = exceptions



class AccessDenied(Exception):
    """ This error is raised when a user is not allowed to access a resource
    """
    pass
########NEW FILE########
__FILENAME__ = models
from bouncer.constants import *
import inspect
import sys

PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
else:
    string_types = basestring,


def listify(list_or_single):
    if isinstance(list_or_single, (list, tuple)):
        return list_or_single
    else:
        return [list_or_single]


class Rule(object):
    def __init__(self, base_behavior, action, subject, conditions=None, **conditions_hash):
        self.base_behavior = base_behavior
        self.actions = listify(action)
        self.subjects = listify(subject)
        self.conditions = None

        if conditions is not None and len(conditions_hash) > 0:
            raise TypeError('cannot provide both a condition method and hash -- pick one')
        elif conditions is not None:
            self.conditions = conditions
        elif len(conditions_hash) > 0:
            self.conditions = conditions_hash

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

    # Matches both the subject and action, not necessarily the conditions
    def is_relavant(self, action, subject):
        # print "Maches Action: [{}]".format(self.matches_action(action))
        # print "Maches Subject: [{}]".format(self.matches_subject(subject))
        return self.matches_action(action) and self.matches_subject(subject)

    @property
    def expanded_actions(self):
        return self._expanded_actions

    @expanded_actions.setter
    def expanded_actions(self, value):
        self._expanded_actions = value

    def matches_action(self, action):
        return MANAGE in self.expanded_actions or action in self.expanded_actions

    def matches_subject(self, subject):
        return ALL in self.subjects or subject in self.subjects or self.matches_subject_class(subject)

    # Matches the conditions
    def matches_conditions(self, action, subject):
        if self.conditions is None:
            return True
        elif inspect.isclass(subject):
            # IMPORTANT we only check conditions if we are testing specific instances of a class NOT of the classes
            # themselves
            return True
        elif isinstance(self.conditions, dict):
            return self.matches_dict_conditions(action, subject)
        else:
            return self.matches_function_conditions(action, subject)

    def matches_dict_conditions(self, action, subject):
        return all(self.matches_hash_condition(subject, key, self.conditions[key]) for key in self.conditions)

    def matches_hash_condition(self, subject, key, value):
        return getattr(subject, key) == value

    def matches_function_conditions(self, action, subject):
        return self.conditions(subject)

    def matches_subject_class(self, subject):
        """
        subject can be either Classes or instances of classes
        self.subjects can either be string or Classes
        """
        for sub in self.subjects:
            if inspect.isclass(sub):
                if inspect.isclass(subject):
                    return issubclass(subject, sub)
                else:
                    return isinstance(subject, sub)
            elif isinstance(sub, string_types):
                if inspect.isclass(subject):
                    return subject.__name__ == sub
                else:
                    return subject.__class__.__name__ == sub
        return False



class RuleList(list):
    def append(self, *item_description_or_rule, **kwargs):
        # Will check it a Rule or a description of a rule
        # construct a rule if necessary then append
        if len(item_description_or_rule) == 1 and isinstance(item_description_or_rule[0], Rule):
            item = item_description_or_rule[0]
            super(RuleList, self).append(item)
        else:
            # try to construct a rule
            item = Rule(True, *item_description_or_rule, **kwargs)
            super(RuleList, self).append(item)

    # alias append
    # so you can do things like this:
    #     @authorization_method
    # def authorize(user, they):
    #
    #     if user.is_admin:
    #         # self.can_manage(ALL)
    #         they.can(MANAGE, ALL)
    #     else:
    #         they.can(READ, ALL)
    #
    #         def if_author(article):
    #             return article.author == user
    #
    #         they.can(EDIT, Article, if_author)
    can = append

    def cannot(self, *item_description_or_rule, **kwargs):
        # Will check it a Rule or a description of a rule
        # construct a rule if necessary then append
        if len(item_description_or_rule) == 1 and isinstance(item_description_or_rule[0], Rule):
            item = item_description_or_rule[0]
            super(RuleList, self).append(item)
        else:
            # try to construct a rule
            item = Rule(False, *item_description_or_rule, **kwargs)
            super(RuleList, self).append(item)


class Ability(object):

    def __init__(self, user, authorization_method=None):
        from . import get_authorization_method
        self.rules = RuleList()
        self.user = user
        self._aliased_actions = self.default_alias_actions

        if authorization_method is not None:
            self.authorization_method = authorization_method
        else:
            # see if one has been set globaly
            self.authorization_method = get_authorization_method()

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

    @property
    def authorization_method(self):
        return self._authorization_method

    @authorization_method.setter
    def authorization_method(self, value):
        self._authorization_method = value
        # Now that we have it run use it to set the rules
        if self._authorization_method is not None:
            self._authorization_method(self.user, self.rules)

    def can(self, action, subject):
        matches = [rule for rule in self.relevant_rules_for_match(action, subject) if rule.matches_conditions(action, subject)]
        if matches:
            match = matches[0]
            return match.base_behavior
        else:
            return False

    def cannot(self, action, subject):
        return not self.can(action, subject)

    def relevant_rules_for_match(self, action, subject):
        matching_rules = []
        for rule in self.rules:
            rule.expanded_actions = self.expand_actions(rule.actions)
            if rule.is_relavant(action, subject):
                matching_rules.append(rule)

        # reverse it (better than .reverse() for it does not return None if list is empty
        # later rules take precidence to earlier defined rules
        return matching_rules[::-1]

    def expand_actions(self, actions):
        """Accepts an array of actions and returns an array of actions which match.
        This should be called before "matches?" and other checking methods since they
        rely on the actions to be expanded."""
        results = list()

        for action in actions:
            if action in self.aliased_actions:
                results.append(action)
                for item in self.expand_actions(self.aliased_actions[action]):
                    results.append(item)
            else:
                results.append(action)

        return results

    @property
    def aliased_actions(self):
        return self._aliased_actions

    @aliased_actions.setter
    def aliased_actions(self, value):
        self._aliased_actions = value

    @property
    def default_alias_actions(self):
        return {
            READ: [INDEX, SHOW],
            CREATE: [NEW],
            UPDATE: [EDIT]
        }

########NEW FILE########
__FILENAME__ = models
class User(object):

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 1)
        self.name = kwargs['name']
        self.admin = kwargs['admin']
        pass

    @property
    def is_admin(self):
        return self.admin


class Article(object):

    def __init__(self, **kwargs):
        self.author = kwargs['author']


class BlogPost(object):

    def __init__(self, **kwargs):
        self.author_id = kwargs['author_id']
        self.visible = kwargs.get('visible', True)
        self.active = kwargs.get('active', True)
########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# bouncer documentation build configuration file, created by
# sphinx-quickstart on Fri Apr  4 07:49:37 2014.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))
sys.path.append(os.path.abspath('_themes'))
html_theme_path = ['_themes']

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'bouncer'
copyright = u'2014, Jonathan Tushman'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1.10'
# The full version, including alpha/beta/rc tags.
release = '0.1.10'

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

# The reST default role (used for this markup: `text`) to use for all
# documents.
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

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'flask'

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

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#html_extra_path = []

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
htmlhelp_basename = 'bouncerdoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  ('index', 'bouncer.tex', u'bouncer Documentation',
   u'Jonathan Tushman', 'manual'),
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


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'bouncer', u'bouncer Documentation',
     [u'Jonathan Tushman'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'bouncer', u'bouncer Documentation',
   u'Jonathan Tushman', 'bouncer', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

########NEW FILE########
__FILENAME__ = flask_theme_support
# flasky extensions.  flasky pygments style based on tango style
from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, \
     Number, Operator, Generic, Whitespace, Punctuation, Other, Literal


class FlaskyStyle(Style):
    background_color = "#f8f8f8"
    default_style = ""

    styles = {
        # No corresponding class for the following:
        #Text:                     "", # class:  ''
        Whitespace:                "underline #f8f8f8",      # class: 'w'
        Error:                     "#a40000 border:#ef2929", # class: 'err'
        Other:                     "#000000",                # class 'x'

        Comment:                   "italic #8f5902", # class: 'c'
        Comment.Preproc:           "noitalic",       # class: 'cp'

        Keyword:                   "bold #004461",   # class: 'k'
        Keyword.Constant:          "bold #004461",   # class: 'kc'
        Keyword.Declaration:       "bold #004461",   # class: 'kd'
        Keyword.Namespace:         "bold #004461",   # class: 'kn'
        Keyword.Pseudo:            "bold #004461",   # class: 'kp'
        Keyword.Reserved:          "bold #004461",   # class: 'kr'
        Keyword.Type:              "bold #004461",   # class: 'kt'

        Operator:                  "#582800",   # class: 'o'
        Operator.Word:             "bold #004461",   # class: 'ow' - like keywords

        Punctuation:               "bold #000000",   # class: 'p'

        # because special names such as Name.Class, Name.Function, etc.
        # are not recognized as such later in the parsing, we choose them
        # to look the same as ordinary variables.
        Name:                      "#000000",        # class: 'n'
        Name.Attribute:            "#c4a000",        # class: 'na' - to be revised
        Name.Builtin:              "#004461",        # class: 'nb'
        Name.Builtin.Pseudo:       "#3465a4",        # class: 'bp'
        Name.Class:                "#000000",        # class: 'nc' - to be revised
        Name.Constant:             "#000000",        # class: 'no' - to be revised
        Name.Decorator:            "#888",           # class: 'nd' - to be revised
        Name.Entity:               "#ce5c00",        # class: 'ni'
        Name.Exception:            "bold #cc0000",   # class: 'ne'
        Name.Function:             "#000000",        # class: 'nf'
        Name.Property:             "#000000",        # class: 'py'
        Name.Label:                "#f57900",        # class: 'nl'
        Name.Namespace:            "#000000",        # class: 'nn' - to be revised
        Name.Other:                "#000000",        # class: 'nx'
        Name.Tag:                  "bold #004461",   # class: 'nt' - like a keyword
        Name.Variable:             "#000000",        # class: 'nv' - to be revised
        Name.Variable.Class:       "#000000",        # class: 'vc' - to be revised
        Name.Variable.Global:      "#000000",        # class: 'vg' - to be revised
        Name.Variable.Instance:    "#000000",        # class: 'vi' - to be revised

        Number:                    "#990000",        # class: 'm'

        Literal:                   "#000000",        # class: 'l'
        Literal.Date:              "#000000",        # class: 'ld'

        String:                    "#4e9a06",        # class: 's'
        String.Backtick:           "#4e9a06",        # class: 'sb'
        String.Char:               "#4e9a06",        # class: 'sc'
        String.Doc:                "italic #8f5902", # class: 'sd' - like a comment
        String.Double:             "#4e9a06",        # class: 's2'
        String.Escape:             "#4e9a06",        # class: 'se'
        String.Heredoc:            "#4e9a06",        # class: 'sh'
        String.Interpol:           "#4e9a06",        # class: 'si'
        String.Other:              "#4e9a06",        # class: 'sx'
        String.Regex:              "#4e9a06",        # class: 'sr'
        String.Single:             "#4e9a06",        # class: 's1'
        String.Symbol:             "#4e9a06",        # class: 'ss'

        Generic:                   "#000000",        # class: 'g'
        Generic.Deleted:           "#a40000",        # class: 'gd'
        Generic.Emph:              "italic #000000", # class: 'ge'
        Generic.Error:             "#ef2929",        # class: 'gr'
        Generic.Heading:           "bold #000080",   # class: 'gh'
        Generic.Inserted:          "#00A000",        # class: 'gi'
        Generic.Output:            "#888",           # class: 'go'
        Generic.Prompt:            "#745334",        # class: 'gp'
        Generic.Strong:            "bold #000000",   # class: 'gs'
        Generic.Subheading:        "bold #800080",   # class: 'gu'
        Generic.Traceback:         "bold #a40000",   # class: 'gt'
    }

########NEW FILE########
